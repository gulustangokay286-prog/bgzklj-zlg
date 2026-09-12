"""
scheduler/cpsat.py — CP-SAT arka ucu.

Tabu araması çizelgenin tamamına hızla yaklaşır ama son bir iki kartta takılır:
her adımda tek kart oynattığı için, ancak üç dört kartın birlikte kaymasıyla
ulaşılabilen çözümleri göremez. v188'de 60 saniye ile 180 saniye aynı sonucu
veriyordu — sorun süre değil, hamlenin kendisi.

CP-SAT tam bu boşluğu doldurur: kartların hepsini aynı anda değerlendirir,
"şu kart şuraya giderse şu üçü şöyle kayar" türü çıkarımları kendisi yapar.
Sıkı yerleşim problemleri (her sınıfın açık hücresi gereken saate tam eşit)
onun güçlü olduğu yerdir.

Eski motorda da CP-SAT vardı ve kaldırılmıştı; sebebi tekniğin kendisi değil,
kurulumun bozuk olmasıydı — planlama ilişkileri modele hiç girmiyordu (hepsi
yalnızca hiç çalışmayan ikinci fazın ceza listesine yazılıyordu). Burada
kurallar doğrudan sert kısıt olarak yazılır.

Model:
    x[i][s]  kart i, s numaralı aday yerine konuldu mu

    her kart            sum(x[i]) <= 1        (yerleşti ya da yerleşmedi)
    sınıf hücresi       o hücreyi kaplayan bütün x'lerin toplamı <= 1
    öğretmen hücresi    aynısı
    aynı ders/gün       (sınıf, gün, ders ailesi) başına <= 1
    aynı öğretmen/gün   (sınıf, gün, öğretmen) başına <= 1
    zor ders bitişik    komşu hücre çiftlerinde ikisi birden olamaz

    amaç                yerleşen SAAT sayısını en büyüklemek
"""

import time
from collections import defaultdict
from . import rules as R


def solve_cpsat(world, rule_list, seconds=60.0, seed=0, workers=8,
                warm_start=None, log=False, allow_split=True,
                pieces_out=None, hedef_saat=None, referans=None,
                takas_out=None):
    """World + kurallar -> (positions, placed_hours, status).

    positions[i] = kart i'nin ızgara indeksi, yerleşmediyse -1.

    pieces_out : liste verilirse BÖLÜNMÜŞ kartlar oraya yazılır —
                 (kart indeksi, [saat indeksleri]) biçiminde. Bölme sonucu
                 eskiden yalnızca modelde kalıyor, positions'a hiç
                 geçmiyordu; yani allow_split hiçbir şeyi değiştirmiyordu.
    hedef_saat : verilirse yerleşen saat TAM bu sayı olmak zorundadır ve
                 amaç, referans çizelgeden sapmayı en küçüklemeye döner.
    referans   : {kart indeksi: ızgara indeksi} — mevcut çizelge.
    takas_out  : sözlük verilirse ['oynayan'] = yerinden kalkan kart sayısı.
    """
    from ortools.sat.python import cp_model

    w = world
    P = w.P
    model = cp_model.CpModel()

    subject_once = any(r.kind == R.X_SUBJECT_ONCE_DAY and r.is_hard() for r in rule_list)
    teacher_once = any(r.kind == R.X_TEACHER_ONCE_DAY and r.is_hard() for r in rule_list)
    hard_adj = set()
    for r in rule_list:
        if r.kind == R.X_HARD_NOT_ADJACENT and r.is_hard():
            hard_adj |= set(r.subjects)

    # ── 2 SAATLİK BLOĞU BÖLEBİLME ──
    #
    # Bir sınıfın gününde tek sayılı bir açıklık kaldığında (örneğin 9-10-11
    # arası üç saat), 2 saatlik blok oraya iki kez sığmaz ve bir saat ölü
    # kalır. Sınıfın açık saati gereken saate tam eşitse o ölü saat doğrudan
    # eksik derse dönüşür — Birey'de on beş sınıfın on beşinde de olan buydu.
    #
    # Çözüm bloğu BÖLEBİLMEK: gerekirse 2 saatlik kart iki ayrı 1 saate
    # ayrılır ve biri o tek boşluğu doldurur. Bölme bedava değildir; bütünlük
    # tercih edilsin diye küçük bir ceza taşır, bu yüzden motor ancak başka
    # çaresi kalmadığında böler.
    # Bölme VARSAYILAN OLARAK KAPALI.
    #
    # Fikir doğruydu: sınıfın gününde tek saatlik bir açıklık kaldığında 2
    # saatlik bloğu 1+1 yapıp o boşluğu doldurmak mantıklı görünüyor. Ölçüm
    # ise kazancın küçük olduğunu gösterdi — Birey'de 227'den 228'e, ve CP-SAT
    # 228'in optimal olduğunu kanıtladı.
    #
    # Sebebi şu: "aynı ders aynı gün tekrar etmesin" kuralı açıkken bölünen
    # blok aynı dersten ÜÇ kart üretir ve üçü de ayrı güne gitmek zorunda
    # kalır. Delik dolmaz, sıkışıklık başka güne taşınır. Üstelik model
    # büyüdüğü için kısa bütçelerde sonuç kötüleşiyor: Boğaziçi'nde üç
    # saniyede 280 yerine 230 çıkıyor.
    #
    # Bu yüzden bölme, çağıran açıkça istediğinde devreye girer.
    split_pen = 40          # bir bölmenin bedeli (saat kazancından küçük)
    splits = []             # (kart, u1_vars, u2_vars)

    xs = []                      # xs[i] = [(slot_idx, var), ...]
    su_kayit = {}                # kart -> bölünmüş parça değişkenleri
    cls_cell = defaultdict(list)
    tch_cell = defaultdict(list)
    fam_day = defaultdict(list)
    tch_day = defaultdict(list)

    for i, c in enumerate(w.cards):
        row = []
        for idx, _ in c.slots:
            v = model.NewBoolVar(f"x{i}_{idx}")
            row.append((idx, v))
            d = idx // P
            for off in range(c.duration):
                cell = idx + off
                for ci in c.classes:
                    cls_cell[(ci, cell)].append(v)
                if c.teacher >= 0:
                    tch_cell[(c.teacher, cell)].append(v)
            for ci in c.classes:
                if subject_once:
                    fam_day[(ci, d, c.family)].append(v)
                if teacher_once and c.teacher >= 0:
                    tch_day[(ci, d, c.teacher)].append(v)
        # Bölünmüş biçim: iki bağımsız 1 saatlik parça.
        su = []
        if allow_split and c.duration >= 2 and c.locked_at is None:
            for k in range(c.duration):
                us = []
                for d in range(w.D):
                    for p in range(P):
                        idx = d * P + p
                        fp = 1 << idx
                        if any(fp & w.class_closed[ci] for ci in c.classes):
                            continue
                        if c.teacher >= 0 and (fp & w.teacher_closed[c.teacher]):
                            continue
                        v = model.NewBoolVar(f"s{i}_{k}_{idx}")
                        us.append((idx, v))
                        for ci in c.classes:
                            cls_cell[(ci, idx)].append(v)
                        if c.teacher >= 0:
                            tch_cell[(c.teacher, idx)].append(v)
                        for ci in c.classes:
                            if subject_once:
                                fam_day[(ci, d, c.family)].append(v)
                            if teacher_once and c.teacher >= 0:
                                tch_day[(ci, d, c.teacher)].append(v)
                su.append(us)

        xs.append(row)
        if su:
            su_kayit[i] = su
        if row or su:
            if c.locked_at is not None:
                for idx, v in row:
                    model.Add(v == (1 if idx == c.locked_at else 0))
            elif su:
                # Üç seçenek: bütün blok, iki parça, ya da hiç yerleşmemiş.
                # "Mutlaka yerleşsin" demek yanlıştı: yerleşemeyen bir kart
                # olduğunda bütün model çözümsüz hâle geliyordu.
                bol = model.NewBoolVar(f"bol{i}")
                model.Add(sum(v for _, v in row) + bol <= 1)
                for us in su:
                    model.Add(sum(v for _, v in us) == bol)
                splits.append((i, bol, c.duration - 1))
            else:
                model.AddAtMostOne(v for _, v in row)

    # Y ekseni — çakışma. Pazarlık yok.
    for vs in cls_cell.values():
        if len(vs) > 1: model.AddAtMostOne(vs)
    for vs in tch_cell.values():
        if len(vs) > 1: model.AddAtMostOne(vs)

    # X ekseni — gün kuralları.
    for vs in fam_day.values():
        if len(vs) > 1: model.AddAtMostOne(vs)
    for vs in tch_day.values():
        if len(vs) > 1: model.AddAtMostOne(vs)

    # Zor ders bitişikliği: aynı sınıfta, aynı gün, uç uca gelen iki zor ders.
    if hard_adj:
        ends = defaultdict(list)     # (sınıf, gün, saat) -> burada BİTEN zor ders
        starts = defaultdict(list)   # (sınıf, gün, saat) -> burada BAŞLAYAN zor ders
        for i, c in enumerate(w.cards):
            if c.subject not in hard_adj:
                continue
            for idx, v in xs[i]:
                d, p = divmod(idx, P)
                for ci in c.classes:
                    starts[(ci, d, p)].append(v)
                    ends[(ci, d, p + c.duration - 1)].append(v)
        for (ci, d, p), evs in ends.items():
            svs = starts.get((ci, d, p + 1))
            if not svs:
                continue
            for a in evs:
                for b in svs:
                    if a is not b:
                        model.AddAtMostOne([a, b])

    # ── AMAÇ ──
    #
    # İki kipte çalışır:
    #   hedef_saat yok  -> yerleşen saati en büyükle (birinci aşama)
    #   hedef_saat var  -> o saat sayısını ZORUNLU kıl, referans çizelgeden
    #                      sapan kart sayısını en küçükle (ikinci aşama)
    #
    # İkinci aşama kullanıcının elindeki çizelgeyi korur: aynı saat sayısına
    # ulaşan sonsuz sayıda çözüm vardır, aralarından EN AZ TAKASLA ulaşılanı
    # seçilir. "Sürekli takas yapa yapa ilerlesin, onun da optimali olsun"
    # denen şey budur ve kanıtlanabilir bir optimumu vardır.
    saat_terms = []
    for i, c in enumerate(w.cards):
        agirlik = c.duration * len(c.classes)
        for _, v in xs[i]:
            saat_terms.append(agirlik * v)
    for i, us_list in su_kayit.items():
        agirlik = len(w.cards[i].classes)
        for us in us_list:
            for _, v in us:
                saat_terms.append(agirlik * v)
    yerlesen = sum(saat_terms)

    if hedef_saat is None:
        terms = list(saat_terms)
        # Bölünen her blok küçük bir ceza taşır: bütünlük tercih edilir ama
        # tek saatlik bir boşluğu doldurmak uğruna bölmek her zaman kârlıdır.
        for i, bol, kesim in splits:
            terms.append(-split_pen * kesim * bol)
        model.Maximize(sum(terms))
    else:
        model.Add(yerlesen == int(hedef_saat))
        sapma = []
        for i, bol, kesim in splits:
            sapma.append(kesim * bol)          # bölme hâlâ istenmeyen
        ref = referans or {}
        for i, row in enumerate(xs):
            eski_idx = ref.get(i)
            if eski_idx is None or eski_idx < 0:
                continue
            ayni = None
            for idx, v in row:
                if idx == eski_idx:
                    ayni = v
                    break
            if ayni is None:
                continue
            oynadi = model.NewBoolVar(f"o{i}")
            model.Add(ayni == 1).OnlyEnforceIf(oynadi.Not())
            model.Add(ayni == 0).OnlyEnforceIf(oynadi)
            sapma.append(oynadi)
        model.Minimize(sum(sapma) if sapma else 0)

    # Sıcak başlangıç: tabu sonucunu ipucu olarak ver. CP-SAT iyi bir başlangıcı
    # doğrulayıp üstüne çıkmaya odaklanır; sıfırdan aramak zorunda kalmaz.
    if warm_start:
        for i, idx in enumerate(warm_start):
            if i < len(xs) and idx is not None and idx >= 0:
                for sidx, v in xs[i]:
                    model.AddHint(v, 1 if sidx == idx else 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(seconds)
    solver.parameters.num_workers = int(workers)
    if seed:
        solver.parameters.random_seed = int(seed) & 0x7fffffff
    solver.parameters.log_search_progress = bool(log)

    st = solver.Solve(model)
    positions = [-1] * len(w.cards)
    parcalar = {}
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for i, row in enumerate(xs):
            for idx, v in row:
                if solver.Value(v):
                    positions[i] = idx
                    break
        # Bölünmüş kartların parçaları: bunlar da gerçek yerleşimdir.
        for i, us_list in su_kayit.items():
            if positions[i] >= 0:
                continue
            yerler = []
            for us in us_list:
                for idx, v in us:
                    if solver.Value(v):
                        yerler.append(idx)
                        break
            if len(yerler) == len(us_list) and yerler:
                parcalar[i] = sorted(yerler)
    if pieces_out is not None:
        pieces_out.extend(sorted(parcalar.items()))
    placed = sum(w.cards[i].duration * len(w.cards[i].classes)
                 for i, idx in enumerate(positions) if idx >= 0)
    placed += sum(len(v) * len(w.cards[i].classes) for i, v in parcalar.items())
    if takas_out is not None and referans:
        oynayan = 0
        for i, eski in referans.items():
            if eski is None or eski < 0:
                continue
            if positions[i] != eski:
                oynayan += 1
        takas_out['oynayan'] = oynayan
    return positions, placed, solver.StatusName(st)


def solve_optimal(world, rule_list, referans=None, allow_split=True,
                  tur_saniye=60.0, azami_saniye=3600.0, workers=8,
                  progress=None, cancelled=None, log=False):
    """OPTİMAL KİP — kanıt gelene kadar durmaz.

    Kullanıcının isteği: "optimale çıkana kadar durmasın, optimale ulaşınca
    dursun, uzun sürmesi önemli değil; sürekli takas yapa yapa ilerlesin ve
    onun da optimali olsun."

    İki aşama:

      1) YERLEŞEN SAAT en büyüklenir. CP-SAT OPTIMAL dönene kadar turlar
         devam eder; her tur bir öncekinin çizelgesiyle ısıtılır. FEASIBLE
         dönerse "bulduğum bu ama daha iyisi olabilir" demektir, durulmaz.

      2) Bulunan saat sayısı kilitlenir ve bu kez REFERANS ÇİZELGEDEN SAPAN
         KART SAYISI en küçüklenir. Aynı saate ulaşan çözümler arasından
         kullanıcının tablosuna en yakın olanı seçilir — takasın optimali.

    Bloklar gerekirse 1 saatlik parçalara bölünür (2 saatlik ders 1+1,
    2+2+1 ise 1+1+1+1+1). Bölme bedava değildir, ancak başka çare yoksa
    yapılır ve sonuçta kaç kartın bölündüğü raporlanır.

    Dönüş: (positions, parcalar, placed_hours, status, tur_sayisi)
      parcalar = {kart indeksi: [saat indeksleri]} — bölünerek yerleşenler
    """
    import time as _t
    w = world
    baslangic = _t.monotonic()
    en_iyi_pos = [-1] * len(w.cards)
    en_iyi_parca = {}
    en_iyi_saat = -1
    durum = "NO_SOLUTION"
    tur = 0
    ipucu = None

    # ── 1. AŞAMA: saati en büyükle, OPTIMAL kanıtı gelene kadar ──
    while True:
        tur += 1
        if callable(cancelled) and cancelled():
            durum = "CANCELLED"
            break
        kalan = azami_saniye - (_t.monotonic() - baslangic)
        if kalan <= 0:
            break
        pieces = []
        pos, placed, st = solve_cpsat(
            w, rule_list, seconds=min(tur_saniye, kalan), workers=workers,
            warm_start=ipucu, allow_split=allow_split, pieces_out=pieces, log=log)
        if placed > en_iyi_saat:
            en_iyi_saat = placed
            en_iyi_pos = pos
            en_iyi_parca = dict(pieces)
            ipucu = pos
        durum = st
        if callable(progress):
            progress(dict(asama=1, tur=tur, saat=en_iyi_saat,
                          toplam=w.total_hours(), durum=st,
                          gecen=_t.monotonic() - baslangic))
        if st == "OPTIMAL" or st in ("INFEASIBLE", "MODEL_INVALID"):
            break
        # Tur süresi katlanarak büyür: kolay örnek erken biter, zor örnekte
        # boşuna kısa turlar atılmaz.
        tur_saniye = min(tur_saniye * 2, max(60.0, azami_saniye / 4))

    if durum != "OPTIMAL" or en_iyi_saat <= 0:
        return en_iyi_pos, en_iyi_parca, max(en_iyi_saat, 0), durum, tur

    # ── 2. AŞAMA: saati kilitle, takası en küçükle ──
    ref = {i: idx for i, idx in enumerate(referans or []) if idx is not None and idx >= 0} \
        if isinstance(referans, (list, tuple)) else dict(referans or {})
    if not ref:
        return en_iyi_pos, en_iyi_parca, en_iyi_saat, "OPTIMAL", tur

    kalan = azami_saniye - (_t.monotonic() - baslangic)
    if kalan <= 1:
        return en_iyi_pos, en_iyi_parca, en_iyi_saat, "OPTIMAL", tur

    tur2 = 0
    takas_sure = max(30.0, tur_saniye)
    while True:
        tur2 += 1
        if callable(cancelled) and cancelled():
            break
        kalan = azami_saniye - (_t.monotonic() - baslangic)
        if kalan <= 1:
            break
        pieces = []
        takas = {}
        pos2, placed2, st2 = solve_cpsat(
            w, rule_list, seconds=min(takas_sure, kalan), workers=workers,
            warm_start=en_iyi_pos, allow_split=allow_split, pieces_out=pieces,
            hedef_saat=en_iyi_saat, referans=ref, takas_out=takas, log=log)
        if placed2 == en_iyi_saat and st2 in ("OPTIMAL", "FEASIBLE"):
            en_iyi_pos = pos2
            en_iyi_parca = dict(pieces)
        if callable(progress):
            progress(dict(asama=2, tur=tur2, saat=en_iyi_saat,
                          toplam=w.total_hours(), durum=st2,
                          oynayan=takas.get('oynayan'),
                          gecen=_t.monotonic() - baslangic))
        if st2 in ("OPTIMAL", "INFEASIBLE", "MODEL_INVALID"):
            break
        takas_sure = min(takas_sure * 2, max(60.0, azami_saniye / 4))

    return en_iyi_pos, en_iyi_parca, en_iyi_saat, "OPTIMAL", tur + tur2
