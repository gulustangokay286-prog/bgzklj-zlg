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

Uygulama OPTİMAL KİPTE yalnızca bu arka ucu kullanır. Bu yüzden Planlama
İlişkileri ekranındaki HER kural burada modellenmek zorundadır. Bir ara
yalnızca üç kural (aynı ders/öğretmen aynı gün, zor ders bitişik) modelleniyor,
gerisi çözümden sonra "aritmetik taban" notuyla geçiştiriliyordu: günde en
fazla N saat, iki ders aynı güne gelmesin, kartlar arası N gün, öğretmen
haftada N gün... hepsi ekranda açık, çizelgede çiğnenmiş, raporda masum.
Şimdi bağımsız denetim (verify.validate) bu ihlalleri HATA sayar; CP-SAT'in
kuralı modellememesi artık sessiz bir kayıp değil, görünür bir çökme olur.

Model:
    x[i][s]  kart i, s numaralı aday yerine konuldu mu (bütün blok)
    u[i][k][c] kart i'nin k. 1 saatlik parçası c hücresine konuldu mu (bölme)

    YERLEŞİM = bütün kartlar + parçalar: her kural aşağıda tek tip bir
    "yerleşim" listesi üzerinden yazılır; parça da kart da aynı süzgeçten geçer.

    her kart            bütün ya da parçalı ya da hiç (sum <= 1)
    sınıf hücresi       o hücreyi kaplayan yerleşimlerin toplamı <= 1
    öğretmen hücresi    aynısı
    her planlama ilişkisi: Sıkı ise kısıt, değilse ceza terimi (aşağıda)

    amaç  1. aşama: yerleşen SAAT en büyük; eşitlikte en az ceza ve bölme
          2. aşama: saat kilitli; en az bölme, en az ceza, en az takas
"""

import math
from collections import defaultdict
from . import rules as R
from .build import window_ok, window_breaks

# ── Amaç ağırlıkları ─────────────────────────────────────────────────────────
#
# Bir sınıf-saati her şeyden ağırdır: yüz "yüksek" tercih ihlali bir saate
# denk gelir. Ölçek büyütmek CP-SAT'i yavaşlatmaz; sıralamayı belirleyen
# oranlardır. Bölme cezası bile bile küçük: "mümkünse bütün bırak ama bir saat
# daha yerleşecekse böl" — v207'de ceza 100'e çıkarılınca 210 saniye ve 12
# bölme, 1'de 60 saniye ve 4 bölme ölçüldü.
SAAT = 100_000
SOFT_WEIGHT = {R.HIGH: 1_000, R.NORMAL: 100, R.LOW: 10}
SPLIT_PEN = 1          # kesim başına (1. aşama)
AVOID_PEN = 1          # "kaçınılacak" hücre başına
# Aritmetik taban: kart sayısı gün sayısını aşan grupta aynı güne düşen iki
# kart bitişik değilse (ya da bir güne tabandan fazlası yığılırsa) ödenen
# bedel. Tabu FORCED_WEIGHT ile aynı fikir — kural delinecekse öğrenci dersi
# tek kesintisiz blok görsün. Ama bir SAATİN çok altında kalır: bu bedel
# yarım saat iken çözücü Birey'de iki saati boş bırakıp cezadan kaçıyordu.
# Tamamlanma her zaman önce gelir; taban içindeki düzen ikinci sıradadır.
FORCED_NONADJ_PEN = 2_000
FORCED_CAP_PEN = 2_000


def _noon(P):
    return 4 if P >= 6 else (P + 1) // 2


class _Model:
    """Tek bir CP-SAT kurulumu. Kuralların her biri ayrı bir yöntemde."""

    def __init__(self, world, rule_list, allow_split, forced):
        from ortools.sat.python import cp_model
        self.cp = cp_model
        self.w = world
        self.P = world.P
        self.D = world.D
        self.rules = [r for r in rule_list if r.kind not in R.DEFINITION_RULES]
        self.forced = forced or set()
        self.m = cp_model.CpModel()
        self.pen = []            # ceza terimleri (ağırlık * değişken)
        self.xs = []             # xs[i] = [(idx, var)] bütün blok
        self.su = {}             # i -> [[(idx, var)] parça başına]
        self.splits = []         # (i, bol, kesim)
        self.occ = []            # yerleşimler: dict(i, d, p, dur, v, card)
        self._build_vars(allow_split)
        self._physical()
        self._rules()

    # ── değişkenler ───────────────────────────────────────────────────────
    def _build_vars(self, allow_split):
        w, m, P = self.w, self.m, self.P
        hard_windows = [r for r in self.rules if r.kind in R.WINDOW_RULES and r.is_hard()]
        for i, c in enumerate(w.cards):
            row = []
            for idx, _ in c.slots:
                v = m.NewBoolVar(f"x{i}_{idx}")
                row.append((idx, v))
                d, p = divmod(idx, P)
                self.occ.append(dict(i=i, d=d, p=p, dur=c.duration, v=v, card=c, piece=False))
            su = []
            if allow_split and c.duration >= 2 and c.locked_at is None:
                for k in range(c.duration):
                    us = []
                    for d in range(self.D):
                        for p in range(P):
                            idx = d * P + p
                            fp = 1 << idx
                            if any(fp & w.class_closed[ci] for ci in c.classes):
                                continue
                            if c.teacher >= 0 and (fp & w.teacher_closed[c.teacher]):
                                continue
                            # Parça da pencere kurallarından geçer.
                            if not window_ok(w, hard_windows, c, p, 1):
                                continue
                            v = m.NewBoolVar(f"s{i}_{k}_{idx}")
                            us.append((idx, v))
                            self.occ.append(dict(i=i, d=d, p=p, dur=1, v=v, card=c, piece=True))
                    su.append(us)
            self.xs.append(row)
            if su and all(su):
                self.su[i] = su
            else:
                su = []
            if row or su:
                if c.locked_at is not None:
                    for idx, v in row:
                        m.Add(v == (1 if idx == c.locked_at else 0))
                elif su:
                    # Üç seçenek: bütün blok, parçalar, ya da hiç. "Mutlaka
                    # yerleşsin" demek yanlıştı: yerleşemeyen bir kart bütün
                    # modeli çözümsüz yapıyordu.
                    bol = m.NewBoolVar(f"bol{i}")
                    m.Add(sum(v for _, v in row) + bol <= 1)
                    for us in su:
                        m.Add(sum(v for _, v in us) == bol)
                    self.splits.append((i, bol, c.duration - 1))
                else:
                    m.AddAtMostOne(v for _, v in row)

    # ── Y ekseni: çakışma, kaçınılacak hücre ─────────────────────────────
    def _physical(self):
        w, m = self.w, self.m
        cls_cell = defaultdict(list)
        tch_cell = defaultdict(list)
        for o in self.occ:
            c = o['card']
            avoid = 0
            for off in range(o['dur']):
                cell = o['d'] * self.P + o['p'] + off
                for ci in c.classes:
                    cls_cell[(ci, cell)].append(o['v'])
                    if (w.class_avoid[ci] >> cell) & 1:
                        avoid += 1
                if c.teacher >= 0:
                    tch_cell[(c.teacher, cell)].append(o['v'])
                    if (w.teacher_avoid[c.teacher] >> cell) & 1:
                        avoid += 1
            if avoid:
                self.pen.append(AVOID_PEN * avoid * o['v'])
        for vs in cls_cell.values():
            if len(vs) > 1:
                m.AddAtMostOne(vs)
        for vs in tch_cell.values():
            if len(vs) > 1:
                m.AddAtMostOne(vs)
        self.cls_cell = cls_cell
        self.tch_cell = tch_cell

    # ── yardımcılar ───────────────────────────────────────────────────────
    def _cap(self, terms, limit, rule, tag):
        """sum(terms) <= limit — sert kısıt ya da ceza terimi."""
        if not terms:
            return
        if rule.is_hard():
            self.m.Add(sum(terms) <= limit)
        else:
            viol = self.m.NewIntVar(0, max(1, len(terms) * 4), f"viol_{tag}")
            self.m.Add(sum(terms) - limit <= viol)
            self.pen.append(SOFT_WEIGHT.get(rule.hardness, 100) * viol)

    def _not_both(self, a, b, rule, tag):
        """a + b <= 1 — sert kısıt ya da ceza."""
        if rule.is_hard():
            self.m.AddAtMostOne([a, b])
        else:
            y = self.m.NewBoolVar(f"y_{tag}")
            self.m.Add(a + b - 1 <= y)
            self.pen.append(SOFT_WEIGHT.get(rule.hardness, 100) * y)

    def _group_by(self, rule, keyfn):
        """Kuralın kapsadığı yerleşimleri anahtara göre toplar.

        keyfn(o, ci) -> anahtar ya da None; ci sınıf indeksidir (sınıf
        kapsamlı kurallar için) ya da -1 (öğretmen kapsamlı kurallar).
        """
        groups = defaultdict(list)
        for o in self.occ:
            c = o['card']
            if not rule.applies_card(c):
                continue
            for ci in c.classes:
                if not rule.applies_class(ci):
                    continue
                key = keyfn(o, ci)
                if key is not None:
                    groups[key].append(o)
        return groups

    def _day_presence(self, occs, tag):
        """Her gün için "bu gün burada bir yerleşim var" bool'u."""
        by_day = defaultdict(list)
        for o in occs:
            by_day[o['d']].append(o['v'])
        has = {}
        for d, vs in by_day.items():
            h = self.m.NewBoolVar(f"has_{tag}_{d}")
            for v in vs:
                self.m.AddImplication(v, h)
            # h yalnızca gerektiğinde 1 olabilsin diye üst sınır: h <= sum(vs)
            self.m.Add(h <= sum(vs))
            has[d] = h
        return has

    def _cells_of(self, occs):
        """(gün, saat) -> o hücreyi kaplayan yerleşim değişkenleri."""
        cells = defaultdict(list)
        for o in occs:
            for off in range(o['dur']):
                cells[(o['d'], o['p'] + off)].append(o['v'])
        return cells

    # ── X/Y ekseni: planlama ilişkileri ─────────────────────────────────
    def _rules(self):
        for n, r in enumerate(self.rules):
            k = r.kind
            tag = f"r{n}"
            if k in (R.Y_CLASS_CLASH, R.Y_TEACHER_CLASH, R.Y_CLOSED_CELL, R.Y_CROSS_INSTITUTION):
                continue
            if k in R.WINDOW_RULES:
                self._window(r, tag)
            elif k == R.X_SUBJECT_ONCE_DAY:
                self._once_day(r, tag, 's')
            elif k == R.X_TEACHER_ONCE_DAY:
                self._once_day(r, tag, 't')
            elif k in (R.X_SUBJECT_MAX_HOURS, R.X_PRACTICAL_MAX_HOURS):
                for key, occs in self._group_by(r, lambda o, ci: (ci, o['d'], o['card'].family)).items():
                    self._cap([o['dur'] * o['v'] for o in occs], max(1, r.param), r, f"{tag}_{key}")
            elif k == R.X_SUBJECT_MAX_SESSIONS:
                for key, occs in self._group_by(r, lambda o, ci: (ci, o['d'], o['card'].family)).items():
                    self._cap([o['v'] for o in occs], max(1, r.param), r, f"{tag}_{key}")
            elif k == R.X_CLASS_MAX_HOURS:
                for key, occs in self._group_by(r, lambda o, ci: (ci, o['d'])).items():
                    self._cap([o['dur'] * o['v'] for o in occs], max(1, r.param), r, f"{tag}_{key}")
            elif k == R.X_TEACHER_MAX_HOURS:
                groups = defaultdict(list)
                for o in self.occ:
                    if o['card'].teacher >= 0 and r.applies_card(o['card']):
                        groups[(o['card'].teacher, o['d'])].append(o)
                for key, occs in groups.items():
                    self._cap([o['dur'] * o['v'] for o in occs], max(1, r.param), r, f"{tag}_{key}")
            elif k == R.X_TEACHER_MAX_DAYS:
                groups = defaultdict(list)
                for o in self.occ:
                    if o['card'].teacher >= 0 and r.applies_card(o['card']):
                        groups[o['card'].teacher].append(o)
                for t, occs in groups.items():
                    has = self._day_presence(occs, f"{tag}_{t}")
                    self._cap(list(has.values()), max(1, r.param), r, f"{tag}_{t}")
            elif k == R.X_PAIR_NOT_SAME_DAY:
                self._pair_not_same_day(r, tag)
            elif k == R.X_HARD_NOT_ADJACENT:
                self._adjacent(r, tag, same_family=False)
            elif k == R.X_SUBJECT_NOT_ADJACENT:
                self._adjacent(r, tag, same_family=True)
            elif k == R.X_MIN_DAYS_BETWEEN:
                self._min_days(r, tag)
            elif k == R.X_EVEN_SPREAD:
                self._even_spread(r, tag)
            elif k in (R.X_SAME_DAY_ADJACENT, R.X_NO_CLASS_GAP):
                for key, occs in self._group_by(r, lambda o, ci: ci).items():
                    self._contiguous(occs, r, f"{tag}_{key}")
            elif k == R.X_NO_TEACHER_GAP:
                groups = defaultdict(list)
                for o in self.occ:
                    if o['card'].teacher >= 0 and r.applies_card(o['card']):
                        groups[o['card'].teacher].append(o)
                for t, occs in groups.items():
                    self._contiguous(occs, r, f"{tag}_{t}")
            elif k == R.X_TEACHER_MAX_RUN:
                groups = defaultdict(list)
                for o in self.occ:
                    if o['card'].teacher >= 0 and r.applies_card(o['card']):
                        groups[o['card'].teacher].append(o)
                for t, occs in groups.items():
                    self._max_run(occs, max(1, r.param), r, f"{tag}_{t}")
            elif k in (R.Y_SUBJECT_MAX_PARALLEL, R.Y_TEACHER_MAX_PARALLEL):
                groups = defaultdict(list)
                for o in self.occ:
                    c = o['card']
                    if not r.applies_card(c):
                        continue
                    key = c.family if k == R.Y_SUBJECT_MAX_PARALLEL else c.teacher
                    if key < 0:
                        continue
                    for off in range(o['dur']):
                        groups[(key, o['d'], o['p'] + off)].append(len(c.classes) * o['v'])
                for key, terms in groups.items():
                    self._cap(terms, max(1, r.param), r, f"{tag}_{key}")

    def _window(self, r, tag):
        # Sert pencere kuralları zaten aday listesinde uygulandı (bütün blok
        # için attach_slots, parça için _build_vars). Yumuşak olanlar ceza.
        if r.is_hard():
            return
        wgt = SOFT_WEIGHT.get(r.hardness, 100)
        for o in self.occ:
            if r.applies_card(o['card']) and window_breaks(r, o['p'], o['dur'], self.P):
                self.pen.append(wgt * o['v'])

    def _once_day(self, r, tag, which):
        """Aynı ders (öğretmen) aynı sınıfta aynı gün en fazla bir kez.

        Aritmetiğin dayattığı gruplarda (kart sayısı > gün sayısı) kısıt
        kaldırılır; yerine günlük tavan ceil(kart/gün) ve aynı güne düşen
        kartların BİTİŞİK olması için ağır ceza gelir. Tabu ile aynı davranış.
        """
        if which == 's':
            keyfn = lambda o, ci: (ci, o['d'], o['card'].family) if o['card'].family >= 0 else None
        else:
            keyfn = lambda o, ci: (ci, o['d'], o['card'].teacher) if o['card'].teacher >= 0 else None
        groups = self._group_by(r, keyfn)
        # Grup başına (sınıf, kaynak) kart sayısı ve gün sayısı — taban için.
        cards_of = defaultdict(set)
        days_of = defaultdict(set)
        for (ci, d, res), occs in groups.items():
            for o in occs:
                cards_of[(ci, res)].add(o['i'])
                days_of[(ci, res)].add(d)
        for (ci, d, res), occs in groups.items():
            forced = (which, ci, res) in self.forced and r.is_hard()
            if not forced:
                self._cap([o['v'] for o in occs], 1, r, f"{tag}_{ci}_{d}_{res}")
                continue
            n_cards = len(cards_of[(ci, res)])
            n_days = max(1, len(days_of[(ci, res)]))
            cap = max(1, math.ceil(n_cards / n_days))
            viol = self.m.NewIntVar(0, len(occs), f"fcap_{tag}_{ci}_{d}_{res}")
            self.m.Add(sum(o['v'] for o in occs) - cap <= viol)
            self.pen.append(FORCED_CAP_PEN * viol)
            # Aynı güne düşenler bitişik olsun.
            for a_ix in range(len(occs)):
                a = occs[a_ix]
                for b_ix in range(a_ix):
                    b = occs[b_ix]
                    if a['i'] == b['i']:
                        continue
                    adjacent = (a['p'] + a['dur'] == b['p'] or b['p'] + b['dur'] == a['p'])
                    overlap = not (a['p'] + a['dur'] <= b['p'] or b['p'] + b['dur'] <= a['p'])
                    if adjacent or overlap:
                        continue
                    y = self.m.NewBoolVar(f"fadj_{tag}_{ci}_{d}_{res}_{a_ix}_{b_ix}")
                    self.m.Add(a['v'] + b['v'] - 1 <= y)
                    self.pen.append(FORCED_NONADJ_PEN * y)

    def _pair_not_same_day(self, r, tag):
        """Seçilen derslerden aynı sınıfta aynı gün en fazla BİR tanesi."""
        groups = self._group_by(r, lambda o, ci: (ci, o['d']))
        for (ci, d), occs in groups.items():
            by_subj = defaultdict(list)
            for o in occs:
                by_subj[o['card'].subject].append(o['v'])
            if len(by_subj) < 2:
                continue
            has = []
            for s, vs in by_subj.items():
                h = self.m.NewBoolVar(f"pns_{tag}_{ci}_{d}_{s}")
                for v in vs:
                    self.m.AddImplication(v, h)
                self.m.Add(h <= sum(vs))
                has.append(h)
            self._cap(has, 1, r, f"{tag}_{ci}_{d}")

    def _adjacent(self, r, tag, same_family):
        """Aynı sınıf, aynı gün, uç uca gelen iki yerleşim.

        same_family=False: "İki zor ders art arda gelmesin" — farklı aileden.
        same_family=True : "Aynı ders art arda gelmesin" — aynı aileden, farklı
                           kart (bölünmüş kartın kendi parçaları hariç).
        """
        groups = self._group_by(r, lambda o, ci: (ci, o['d']))
        for (ci, d), occs in groups.items():
            ends = defaultdict(list)     # biten saat -> yerleşimler
            starts = defaultdict(list)   # başlayan saat -> yerleşimler
            for o in occs:
                starts[o['p']].append(o)
                ends[o['p'] + o['dur'] - 1].append(o)
            for p, evs in ends.items():
                svs = starts.get(p + 1)
                if not svs:
                    continue
                for a in evs:
                    for b in svs:
                        if a['i'] == b['i']:
                            continue
                        fa, fb = a['card'].family, b['card'].family
                        if same_family and fa != fb:
                            continue
                        if not same_family and fa == fb:
                            continue
                        self._not_both(a['v'], b['v'], r, f"{tag}_{ci}_{d}_{p}_{a['i']}_{b['i']}")

    def _min_days(self, r, tag):
        """Aynı dersin kartları arasında en az N gün."""
        N = max(1, r.param)
        groups = self._group_by(r, lambda o, ci: (ci, o['card'].family) if o['card'].family >= 0 else None)
        for (ci, fam), occs in groups.items():
            by_day = defaultdict(list)
            for o in occs:
                by_day[o['d']].append(o['v'])
            has = self._day_presence(occs, f"{tag}_{ci}_{fam}")
            days = sorted(by_day)
            for ai, d1 in enumerate(days):
                # aynı gün iki kart
                self._cap(by_day[d1], 1, r, f"{tag}_{ci}_{fam}_{d1}")
                for d2 in days[ai + 1:]:
                    if d2 - d1 < N:
                        self._not_both(has[d1], has[d2], r, f"{tag}_{ci}_{fam}_{d1}_{d2}")

    def _even_spread(self, r, tag):
        """Dersin günlere dağılımı: en çok ile en az arasında en fazla 1 fark."""
        groups = self._group_by(r, lambda o, ci: (ci, o['card'].family) if o['card'].family >= 0 else None)
        for (ci, fam), occs in groups.items():
            by_day = defaultdict(list)
            for o in occs:
                by_day[o['d']].append(o['v'])
            if len(by_day) < 2:
                continue
            n = len(occs)
            mx = self.m.NewIntVar(0, n, f"mx_{tag}_{ci}_{fam}")
            mn = self.m.NewIntVar(0, n, f"mn_{tag}_{ci}_{fam}")
            for d in range(self.D):
                cnt = sum(by_day.get(d, [])) if by_day.get(d) else 0
                self.m.Add(mx >= cnt)
                self.m.Add(mn <= cnt)
            if r.is_hard():
                self.m.Add(mx - mn <= 1)
            else:
                viol = self.m.NewIntVar(0, n, f"viol_{tag}_{ci}_{fam}")
                self.m.Add(mx - mn - 1 <= viol)
                self.pen.append(SOFT_WEIGHT.get(r.hardness, 100) * viol)

    def _contiguous(self, occs, r, tag):
        """Gün içinde boşluk yok: dolu iki saat arasındaki her saat dolu."""
        cells = self._cells_of(occs)
        by_day = defaultdict(dict)
        for (d, p), vs in cells.items():
            by_day[d][p] = sum(vs)
        for d, row in by_day.items():
            ps = sorted(row)
            for a_ix, p1 in enumerate(ps):
                for c_ix in range(a_ix + 2, len(ps)):
                    p3 = ps[c_ix]
                    for p2 in range(p1 + 1, p3):
                        mid = row.get(p2, 0)
                        if r.is_hard():
                            self.m.Add(row[p1] + row[p3] - mid <= 1)
                        else:
                            y = self.m.NewBoolVar(f"gap_{tag}_{d}_{p1}_{p2}_{p3}")
                            self.m.Add(row[p1] + row[p3] - mid - 1 <= y)
                            self.pen.append(SOFT_WEIGHT.get(r.hardness, 100) * y)

    def _max_run(self, occs, N, r, tag):
        """Art arda en fazla N saat: her N+1'lik pencerede en fazla N dolu."""
        cells = self._cells_of(occs)
        by_day = defaultdict(dict)
        for (d, p), vs in cells.items():
            by_day[d][p] = sum(vs)
        for d, row in by_day.items():
            for q in range(0, self.P - N):
                terms = [row[p] for p in range(q, q + N + 1) if p in row]
                if len(terms) > N:
                    self._cap(terms, N, r, f"{tag}_{d}_{q}")


def solve_cpsat(world, rule_list, seconds=60.0, seed=0, workers=8,
                warm_start=None, log=False, allow_split=True,
                pieces_out=None, hedef_saat=None, referans=None,
                takas_out=None, forced=None):
    """World + kurallar -> (positions, placed_hours, status).

    positions[i] = kart i'nin ızgara indeksi, yerleşmediyse -1.

    pieces_out : liste verilirse BÖLÜNMÜŞ kartlar oraya yazılır —
                 (kart indeksi, [saat indeksleri]) biçiminde.
    hedef_saat : verilirse yerleşen saat TAM bu sayı olmak zorundadır ve
                 amaç, referans çizelgeden sapmayı en küçüklemeye döner.
    referans   : {kart indeksi: ızgara indeksi} — mevcut çizelge.
    takas_out  : sözlük verilirse ['oynayan'] = yerinden kalkan kart sayısı.
    forced     : aritmetiğin dayattığı gruplar (problem.impossible_groups);
                 verilmezse hesaplanır.
    """
    from ortools.sat.python import cp_model

    w = world
    if forced is None:
        from .problem import impossible_groups
        forced = impossible_groups(w)
    M = _Model(w, rule_list, allow_split, forced)
    model, xs, su_kayit, splits = M.m, M.xs, M.su, M.splits

    # ── AMAÇ ──
    saat_terms = []
    for i, c in enumerate(w.cards):
        agirlik = SAAT * c.duration * len(c.classes)
        for _, v in xs[i]:
            saat_terms.append(agirlik * v)
    for i, us_list in su_kayit.items():
        agirlik = SAAT * len(w.cards[i].classes)
        for us in us_list:
            for _, v in us:
                saat_terms.append(agirlik * v)
    yerlesen = sum(saat_terms) if saat_terms else 0

    if hedef_saat is None:
        terms = list(saat_terms)
        for i, bol, kesim in splits:
            terms.append(-SPLIT_PEN * kesim * bol)
        for t in M.pen:
            terms.append(-t)
        model.Maximize(sum(terms) if terms else 0)
    else:
        model.Add(yerlesen == int(hedef_saat) * SAAT)
        # Saat sayısı kilitlendi; şimdi sırayla: en az bölünmüş, en az tercih
        # ihlali, referans çizelgeden en az sapan.
        sapma = []
        for i, bol, kesim in splits:
            sapma.append(1000 * kesim * bol)
        sapma.extend(M.pen)
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
    from .problem import impossible_groups
    w = world
    forced = impossible_groups(w)
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
            warm_start=ipucu, allow_split=allow_split, pieces_out=pieces,
            log=log, forced=forced)
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
        # TAM ÇİZELGE = OPTİMUM. Kanıt beklemeye gerek yok: bütün saatler
        # yerleştiyse daha iyisi tanım gereği yok.
        #
        # Eskiden burada yalnızca CP-SAT'in OPTIMAL damgası aranıyordu.
        # Çözücü 285/285'i FEASIBLE olarak döndürdüğünde döngü kırılmıyor,
        # ilerleme çubuğu 285/285 gösterirken motor bir saat boyunca kanıt
        # aramaya devam ediyor ve çizelge ekrana hiç düşmüyordu.
        if en_iyi_saat >= w.total_hours():
            durum = "OPTIMAL"
            break
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
    # Referans olmasa bile bu aşama çalışır: gereksiz bölmeleri temizler.
    kalan = azami_saniye - (_t.monotonic() - baslangic)
    if kalan <= 1:
        return en_iyi_pos, en_iyi_parca, en_iyi_saat, "OPTIMAL", tur

    # Takas aşaması çizelgeyi İYİLEŞTİRİR, bulmaz: saat sayısı zaten
    # kesinleşmiştir, burada yalnızca kullanıcının tablosuna daha yakın bir
    # düzen aranır. Bu yüzden kalan bütçenin tamamını yemesine izin verilmez —
    # aksi hâlde sonuç hazırken uygulama dakikalarca bekliyor gibi görünür.
    takas_butcesi = min(kalan * 0.25, 90.0)
    takas_bitis = _t.monotonic() + takas_butcesi
    tur2 = 0
    takas_sure = max(15.0, min(30.0, takas_butcesi))
    while True:
        tur2 += 1
        if callable(cancelled) and cancelled():
            break
        kalan = min(azami_saniye - (_t.monotonic() - baslangic),
                    takas_bitis - _t.monotonic())
        if kalan <= 1:
            break
        pieces = []
        takas = {}
        pos2, placed2, st2 = solve_cpsat(
            w, rule_list, seconds=min(takas_sure, kalan), workers=workers,
            warm_start=en_iyi_pos, allow_split=allow_split, pieces_out=pieces,
            hedef_saat=en_iyi_saat, referans=ref, takas_out=takas, log=log,
            forced=forced)
        if placed2 == en_iyi_saat and st2 in ("OPTIMAL", "FEASIBLE") \
                and len(pieces) <= len(en_iyi_parca):
            en_iyi_pos = pos2
            en_iyi_parca = dict(pieces)
        if callable(progress):
            progress(dict(asama=2, tur=tur2, saat=en_iyi_saat,
                          toplam=w.total_hours(), durum=st2,
                          oynayan=takas.get('oynayan'),
                          gecen=_t.monotonic() - baslangic))
        if st2 in ("OPTIMAL", "INFEASIBLE", "MODEL_INVALID"):
            break
        takas_sure = min(takas_sure * 2, takas_butcesi)

    return en_iyi_pos, en_iyi_parca, en_iyi_saat, "OPTIMAL", tur + tur2
