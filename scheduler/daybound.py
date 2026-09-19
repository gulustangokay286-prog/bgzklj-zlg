"""Gün-seviyesi gevşetme: bu kurallarla EN FAZLA kaç saat yerleşebilir?

Neden var
---------
Boğaziçi v212'de "İki ders aynı güne gelmesin: Matematik1 + Matematik2" kuralı
12 A/B/C/D için açıkken motor 282-284 arasında turlar atıyor, kanıt
veremiyordu; kullanıcı "tavana çıkamıyor" diye bekliyordu. Oysa tavan 285
değil 284'tü: Hüseyin Arman haftada yalnızca Salı (5) ve Perşembe (8) açık,
12 A ve 12 B'de 8 saat Matematik2'si var; kural bu iki sınıfta Matematik1'i o
günlerden kovunca zincir bir saati dışarıda bırakıyor. Bunu saat-seviyesi
CP-SAT dakikalarca kanıtlayamıyor; gün-seviyesi model 0.2 saniyede kanıtlıyor.

Ne yapar
--------
Kartları GÜNE atayan küçük bir CP-SAT modeli kurar (saat yok, bitişiklik yok):

  * her kartın saatleri günlere dağılır (bölme serbest: 2 saat 1+1 olabilir),
  * sınıfın ve öğretmenin o gün açık saat sayısı aşılamaz,
  * "aynı ders / aynı öğretmen aynı gün tekrar etmesin": sınıfta o gün en
    fazla bir kart (esas modelin ESNETTİĞİ aritmetik-imkânsız gruplar hariç),
  * "iki ders aynı güne gelmesin": seçilen derslerden o gün en fazla biri,
  * kilitli kart kendi gününde.

Esas modelin her kısıtı burada ya aynen var ya da gevşetilmiş; fazladan hiçbir
kısıt YOK. Bu yüzden bulunan sayı geçerli bir ÜST SINIRDIR: esas motor bundan
fazlasını asla bulamaz. Motor bu sayıya ulaşınca durur — "daha fazlası bu
kurallarla yok" demek için dakikalarca beklemesi gerekmez.

Sınır eksikse ikinci adımda sebep aranır: hangi kural, hangi sınıflarda, hangi
öğretmenin zaman tablosu yüzünden. Her deneme yine gün-seviyesi model, her biri
saniyenin altında.
"""
import time
from collections import defaultdict

from . import rules as R

DAY_RULE_KINDS = (R.X_SUBJECT_ONCE_DAY, R.X_TEACHER_ONCE_DAY, R.X_PAIR_NOT_SAME_DAY,
                  R.X_SUBJECT_MAX_HOURS, R.X_PRACTICAL_MAX_HOURS, R.X_CLASS_MAX_HOURS,
                  R.X_TEACHER_MAX_HOURS)


def _open_hours(mask, d, P):
    return sum(1 for p in range(P) if not (mask >> (d * P + p)) & 1)


def _solve(world, rules, forced, seconds, skip=None, open_teachers=(),
           allow_split=True, seed=0, want_solution=False, avoid=None):
    """Gevşetmeyi kurar ve çözer.

    skip: {(kural indeksi, sınıf indeksi ya da None)} — o kuralı o sınıfta
          (None: her yerde) uygulama.
    open_teachers: bu öğretmenlerin zaman tablosu tamamen açık sayılsın.
    allow_split: kart 1 saatlik parçalara bölünüp AYRI günlere dağılabilir
          (esas modelle aynı: ya bütün blok tek günde ya da her parça ayrı
          günde; aynı güne iki parça yok).
    avoid: {(kart, gün)} — bu gün seçimlerinden kaçın (yumuşak; çeşitlilik).
    Döner (durum, üst sınır, en iyi[, atama]) ya da None (OR-Tools yoksa).
    atama: {kart: {'whole': gün} | {'pieces': [gün...]}} — yerleşen kartlar.
    """
    try:
        from ortools.sat.python import cp_model
    except Exception:
        return None
    w = world
    D, P = w.D, w.P
    skip = skip or set()
    forced = forced or set()
    open_teachers = set(open_teachers)
    avoid = avoid or set()

    def t_closed(ti):
        return 0 if ti in open_teachers else w.teacher_closed[ti]

    m = cp_model.CpModel()
    h = {}      # (kart, gün) -> o gün o karttan kaç saat
    whole = {}  # (kart, gün) -> bütün blok o günde
    piece = {}  # (kart, gün) -> 1 saatlik parça o günde
    cezalar = []
    for c in w.cards:
        if c.locked_at is not None:
            days = [c.locked_at // P]
        else:
            days = [d for d in range(D)
                    if any(not (w.class_closed[ci] >> (d * P + p)) & 1
                           and (c.teacher < 0 or not (t_closed(c.teacher) >> (d * P + p)) & 1)
                           for ci in c.classes for p in range(P))]
        if not days:
            continue
        if c.locked_at is not None:
            d = days[0]
            h[c.cid, d] = m.NewIntVar(c.duration, c.duration, f"h{c.cid}_{d}")
            whole[c.cid, d] = m.NewBoolVar(f"w{c.cid}_{d}")
            m.Add(whole[c.cid, d] == 1)
            continue
        ws = []
        for d in days:
            wv = m.NewBoolVar(f"w{c.cid}_{d}")
            whole[c.cid, d] = wv
            ws.append(wv)
            if (c.cid, d) in avoid:
                cezalar.append(wv)
        m.Add(sum(ws) <= 1)
        can_split = allow_split and c.duration >= 2
        for d in days:
            hv = m.NewIntVar(0, c.duration, f"h{c.cid}_{d}")
            h[c.cid, d] = hv
            if can_split:
                # Bir günde 0..süre parça saati (3 saatlik kart 2+1 olarak iki
                # güne yayılabilir; aynı gündeki parçalar bitişik tek bloktur).
                # Bool olsaydı bu yerleşim gün modelinde ifade edilemez, sınır
                # ulaşılabilir bir çözümü imkânsız gösterirdi.
                pv = m.NewIntVar(0, c.duration, f"p{c.cid}_{d}")
                piece[c.cid, d] = pv
                m.Add(pv + c.duration * sum(ws) <= c.duration)   # parça varsa bütün blok yok
                m.Add(hv == c.duration * whole[c.cid, d] + pv)
                if (c.cid, d) in avoid:
                    cezalar.append(pv)
            else:
                m.Add(hv == c.duration * whole[c.cid, d])
        if can_split:
            m.Add(sum(piece[c.cid, d] for d in days) <= c.duration)
        # LP gevşetmesini sıkılaştırır: toplam saat ≤ süre (mantıken zaten
        # öyle, ama kesirli çözümde bütün+parça karışımı bunu aşabiliyor ve
        # CP-SAT kanıtı bulamıyordu).
        m.Add(sum(h[c.cid, d] for d in days) <= c.duration)

    def used(v, name):
        a = m.NewBoolVar(name)
        m.Add(v >= 1).OnlyEnforceIf(a)
        m.Add(v == 0).OnlyEnforceIf(a.Not())
        return a

    for ri, r in enumerate(rules):
        if not r.is_hard() or r.kind not in DAY_RULE_KINDS:
            continue
        if (ri, None) in skip:
            continue
        if r.kind in (R.X_SUBJECT_ONCE_DAY, R.X_TEACHER_ONCE_DAY):
            which = 's' if r.kind == R.X_SUBJECT_ONCE_DAY else 't'
            groups = defaultdict(list)
            for c in w.cards:
                if not r.applies_card(c):
                    continue
                res = c.family if which == 's' else c.teacher
                if res < 0:
                    continue
                for ci in c.classes:
                    if r.applies_class(ci) and (ri, ci) not in skip:
                        groups[ci, res].append(c)
            # Bitişiklik istisnası yalnızca AYNI ATAMANIN (origin) kartları
            # için geçerli (bkz. cpsat._once_day). Gün modelinde bu şöyle
            # ifade edilir: bir günde o (sınıf, aile) için EN FAZLA BİR atama
            # ders yapar. Aynı atamanın kartları aynı güne (yan yana) gelebilir;
            # farklı atamalar gelemez. Esas modelin gevşetmesi, sınır GEÇERLİ.
            # Aritmetik-imkânsız (forced) gruplar esas modelde esnediği için
            # burada da kısıtlanmaz.
            for (ci, res), cards in groups.items():
                if (which, ci, res) in forced:
                    continue
                by_origin = defaultdict(list)
                for c in cards:
                    by_origin[c.origin].append(c)
                if len(by_origin) < 2:
                    continue
                for d in range(D):
                    flags = []
                    for g, cs in by_origin.items():
                        vs = [h[c.cid, d] for c in cs if (c.cid, d) in h]
                        if vs:
                            flags.append(used(sum(vs), f"o{which}{ci}_{res}_{d}_{g}"))
                    if len(flags) > 1:
                        m.Add(sum(flags) <= 1)
            continue
        elif r.kind in (R.X_SUBJECT_MAX_HOURS, R.X_PRACTICAL_MAX_HOURS):
            # Günde en fazla N saat (sınıf, aile): saat modeliyle birebir aynı
            # anlam, gün modelinde doğrudan ifade edilir.
            lim = max(1, int(r.param or 0))
            groups = defaultdict(list)
            for c in w.cards:
                if not r.applies_card(c) or c.family < 0:
                    continue
                for ci in c.classes:
                    if r.applies_class(ci) and (ri, ci) not in skip:
                        groups[ci, c.family].append(c)
            for (ci, f), cards in groups.items():
                for d in range(D):
                    vs = [h[c.cid, d] for c in cards if (c.cid, d) in h]
                    if vs:
                        m.Add(sum(vs) <= lim)
        elif r.kind == R.X_CLASS_MAX_HOURS:
            lim = max(1, int(r.param or 0))
            for ci in range(len(w.classes)):
                if not r.applies_class(ci) or (ri, ci) in skip:
                    continue
                for d in range(D):
                    vs = [h[c.cid, d] for c in w.cards if ci in c.classes and r.applies_card(c) and (c.cid, d) in h]
                    if vs:
                        m.Add(sum(vs) <= lim)
        elif r.kind == R.X_TEACHER_MAX_HOURS:
            lim = max(1, int(r.param or 0))
            for ti in range(len(w.teachers)):
                if not r.applies_teacher(ti):
                    continue
                for d in range(D):
                    vs = [h[c.cid, d] for c in w.cards if c.teacher == ti and r.applies_card(c) and (c.cid, d) in h]
                    if vs:
                        m.Add(sum(vs) <= lim)
        elif r.kind == R.X_PAIR_NOT_SAME_DAY:
            for ci in range(len(w.classes)):
                if not r.applies_class(ci) or (ri, ci) in skip:
                    continue
                for d in range(D):
                    has = []
                    by_subj = defaultdict(list)
                    for c in w.cards:
                        if ci in c.classes and r.applies_card(c) and (c.cid, d) in h:
                            by_subj[c.subject].append(h[c.cid, d])
                    if len(by_subj) < 2:
                        continue
                    for s, vs in by_subj.items():
                        has.append(used(sum(vs), f"p{ri}_{ci}_{d}_{s}"))
                    m.Add(sum(has) <= 1)

    for ti in range(len(w.teachers)):
        mask = t_closed(ti)
        for d in range(D):
            vs = [h[c.cid, d] for c in w.cards if c.teacher == ti and (c.cid, d) in h]
            if vs:
                m.Add(sum(vs) <= _open_hours(mask, d, P))
    for ci in range(len(w.classes)):
        for d in range(D):
            vs = [h[c.cid, d] for c in w.cards if ci in c.classes and (c.cid, d) in h]
            if vs:
                m.Add(sum(vs) <= _open_hours(w.class_closed[ci], d, P))

    # 1. AŞAMA — amaç yalnızca yerleşen saat: sınır ancak böyle geçerli olur
    # (bölme cezası amaca karışsaydı amaç sınırı saat sınırının altına
    # inebilirdi).
    saat = sum(len(w.cards[cid].classes) * v for (cid, d), v in h.items())
    m.Maximize(saat)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = max(0.2, float(seconds))
    s.parameters.num_workers = 8
    if seed:
        s.parameters.random_seed = int(seed) & 0x7fffffff
    st = s.Solve(m)
    name = s.StatusName(st)
    if name in ("OPTIMAL", "FEASIBLE"):
        bound = int(s.BestObjectiveBound())
        best = int(s.Value(saat))
        if not want_solution:
            return name, bound, best
        # 2. AŞAMA — saat sabit, en az bölme ve kaçınılan gün: atama için.
        m.Add(saat == best)
        bolme = sum(piece.values()) if piece else 0
        m.Minimize(10 * bolme + sum(cezalar))
        s2 = cp_model.CpSolver()
        s2.parameters.max_time_in_seconds = max(0.2, float(seconds) / 2)
        s2.parameters.num_workers = 8
        if seed:
            s2.parameters.random_seed = int(seed) & 0x7fffffff
        st2 = s2.Solve(m)
        if s2.StatusName(st2) in ("OPTIMAL", "FEASIBLE"):
            s = s2
        atama = {}
        for (cid, d), wv in whole.items():
            if s.Value(wv):
                atama[cid] = {'whole': d}
        for c in w.cards:
            if c.cid in atama:
                continue
            gunler = [d for d in range(D) if (c.cid, d) in piece and s.Value(piece[c.cid, d])]
            if len(gunler) == c.duration:
                atama[c.cid] = {'pieces': sorted(gunler)}
        return name, bound, best, atama
    if name == "INFEASIBLE":
        return (name, 0, 0, {}) if want_solution else (name, 0, 0)
    return (name, None, None, {}) if want_solution else (name, None, None)


def day_bound(world, rules, forced=None, seconds=2.0):
    """Kanıtlanmış üst sınır (saat) ya da None.

    Gevşetme süre içinde OPTIMAL'e varmasa bile BestObjectiveBound geçerli bir
    üst sınırdır; onu döndürür. OR-Tools yoksa None.
    """
    if not world.cards:
        return 0
    out = _solve(world, rules, forced, seconds)
    if out is None:
        return None
    _, bound, _ = out
    return bound


def explain_day_bound(world, rules, forced, bound, seconds=5.0):
    """Sınır toplamın altındaysa nedenini bulur: kural, sınıflar, öğretmen.

    Döner: [dict(message, rule, classes, teachers, hours)] — motorun tanı
    listesiyle aynı biçimde; boş liste = sebep bulunamadı (süre yetmedi ya da
    sebep gün-seviyesi kuralların dışında: kapasite, pencere vb.).
    """
    w = world
    total = w.total_hours()
    if bound is None or bound >= total:
        return []
    deadline = time.monotonic() + seconds
    per = 0.6
    out = []

    def probe(**kw):
        """Değişiklikle gün-seviyesinde ULAŞILAN saat (bulunan çözüm; kanıt değil)."""
        if time.monotonic() > deadline:
            return None
        r = _solve(w, rules, forced, per, **kw)
        return None if r is None or r[2] is None else r[2]

    def open_total(ti):
        return sum(_open_hours(w.teacher_closed[ti], d, w.P) for d in range(w.D))

    # En dar kapsamlı kural önce: "Mat1+Mat2 aynı güne gelmesin" (8 kart),
    # bütün dersleri kapsayan "aynı ders aynı gün tekrar etmesin"den (200 kart)
    # önce anlatılır — kullanıcının son eklediği kural çoğu zaman odur.
    candidates = [(sum(1 for c in w.cards if r.applies_card(c)), ri, r)
                  for ri, r in enumerate(rules)
                  if r.is_hard() and r.kind in DAY_RULE_KINDS]
    for _, ri, r in sorted(candidates, key=lambda x: x[0]):
        without = probe(skip={(ri, None)})
        if without is None or without <= bound:
            continue
        kazanc = without - bound
        # Hangi sınıflarda? Tek başına kaldırılınca sınırı yükselten sınıflar.
        involved = sorted({ci for c in w.cards if r.applies_card(c)
                           for ci in c.classes if r.applies_class(ci)})
        classes = []
        for ci in involved:
            b2 = probe(skip={(ri, ci)})
            if b2 is not None and b2 > bound:
                classes.append(ci)
        if not classes:
            classes = involved
        # Hangi öğretmen? Tablosu tamamen açık sayılınca sınırı yükselten;
        # en az açık saati olan üçü.
        teachers = sorted({c.teacher for c in w.cards if r.applies_card(c) and c.teacher >= 0
                           and any(ci in classes for ci in c.classes)}, key=open_total)
        bottleneck = []
        for ti in teachers:
            if len(bottleneck) >= 3:
                break
            b3 = probe(open_teachers=(ti,))
            if b3 is not None and b3 > bound:
                bottleneck.append(ti)
        label = r.label or r.kind
        if r.kind == R.X_PAIR_NOT_SAME_DAY and r.subjects:
            label += " (" + " + ".join(w.subjects[s] for s in sorted(r.subjects)
                                      if 0 <= s < len(w.subjects)) + ")"
        cls_txt = ", ".join(w.classes[ci] for ci in classes)
        msg = (f"'{label}' kuralı {cls_txt} için {kazanc} saati dışarıda bırakıyor: "
               f"kural bu sınıf(lar)da kalkınca {without}/{total} saat mümkün.")
        if bottleneck:
            parts = []
            for ti in bottleneck:
                days = [f"{_day_name(w, d)} {_open_hours(w.teacher_closed[ti], d, w.P)}"
                        for d in range(w.D) if _open_hours(w.teacher_closed[ti], d, w.P) > 0]
                load = sum(c.duration for c in w.cards if c.teacher == ti)
                parts.append(f"{w.teachers[ti]} haftada {open_total(ti)} saat açık "
                             f"({', '.join(days)}), {load} saat yükü var")
            msg += " Darboğaz: " + "; ".join(parts) + "."
        out.append(dict(message=msg, rule=label, classes=[w.classes[ci] for ci in classes],
                        teachers=[w.teachers[ti] for ti in bottleneck], hours=kazanc,
                        cards=[]))
        if time.monotonic() > deadline:
            break
    return out


def _day_name(world, d):
    names = getattr(world, "day_names", None) or []
    if d < len(names) and names[d]:
        return str(names[d])
    return ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")[d] \
        if d < 7 else f"{d + 1}. gün"
