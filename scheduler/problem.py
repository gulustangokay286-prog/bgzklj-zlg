"""Compile the current rules to a finite-domain problem for the native search.

Days and periods remain one decision. Domains contain whole blocks only.
The C++ executable receives numbers, never school names or saved solutions.
"""
from collections import defaultdict
from dataclasses import dataclass
from . import rules as R

PAIR_KINDS = {R.X_SUBJECT_ONCE_DAY, R.X_TEACHER_ONCE_DAY,
              R.X_PAIR_NOT_SAME_DAY, R.X_HARD_NOT_ADJACENT, R.X_MIN_DAYS_BETWEEN}
FACTOR_KINDS = {R.X_SUBJECT_MAX_HOURS, R.X_PRACTICAL_MAX_HOURS,
                R.X_SUBJECT_MAX_SESSIONS, R.X_CLASS_MAX_HOURS,
                R.X_TEACHER_MAX_HOURS, R.X_TEACHER_MAX_DAYS,
                R.X_SAME_DAY_ADJACENT, R.X_NO_CLASS_GAP,
                R.X_NO_TEACHER_GAP, R.X_TEACHER_MAX_RUN, R.X_EVEN_SPREAD,
                R.Y_SUBJECT_MAX_PARALLEL, R.Y_TEACHER_MAX_PARALLEL}
CORE_KINDS = {R.Y_CLASS_CLASH, R.Y_TEACHER_CLASH, R.Y_CLOSED_CELL, R.Y_CROSS_INSTITUTION}

@dataclass
class Factor:
    kind: int  # hours/day, cards/day, used days, contiguous, run, spread, parallel
    limit: int
    hard: bool
    weight: int
    cards: list
    label: str

# Tamamlanma öncelikli kipte sert X kuralları bu ağırlıkla cezaya çevrilir.
# Tek bir kural ihlali, yerleşemeyen tek bir saatten çok daha pahalıdır; bu
# yüzden arama kuralı ancak başka çaresi kalmadığında deler ve deldiği yerde
# de mümkün olan en az sayıda deler.
FORCED_WEIGHT = 1_000_000


class Problem:
    def __init__(self, world, rules, completion_first=True):
        self.world = world
        self.rules = rules
        # Y ekseni — öğretmen/sınıf çakışması, kapalı hücre, kilit — HER ZAMAN
        # serttir ve bu bayraktan etkilenmez; ihlali geçersiz çizelge demektir.
        #
        # X ekseni — planlama ilişkileri — tamamlanma öncelikli kipte çok ağır
        # cezaya çevrilir. Gerekçesi şu: bir dersin hiç yerleşmemesi, okulda
        # o dersin yapılmaması demektir; bir kuralın tek bir yerde delinmesi
        # ise çizelgenin o noktada ideal olmaması demektir. İkisi aynı ağırlıkta
        # değildir. Sert tutulduğunda motor, tek bir aritmetik imkânsızlık
        # yüzünden (9A Matematik: üç kart, öğretmene iki gün açık) saatleri
        # boş bırakıp duruyordu.
        #
        # Kip kapatıldığında eski davranış aynen geri gelir: kural asla
        # delinmez, yerleşemeyen ders yerleşmez ve raporlanır.
        self.completion_first = completion_first
        # Aritmetiğin imkânsız kıldığı gruplar.
        #
        # "Aynı ders aynı gün tekrar etmesin" bir dersin kartlarını ayrı
        # günlere dağıtmayı ister. Ama bir dersin kart sayısı, o dersi veren
        # öğretmenin okulda olduğu gün sayısını aşıyorsa bu istek hiçbir
        # çizelgede karşılanamaz — v188'de 9A Matematik üç karta bölünmüş,
        # öğretmeni ise yalnızca Salı ve Perşembe okulda.
        #
        # Kuralı bütün okulda gevşetmek yanlış olur: sorun tek bir yerdedir.
        # Bu yüzden yalnızca o grubun kart çiftleri cezaya çevrilir; kuralın
        # geri kalan bütün uygulamaları sert kalır. Esneyen grup rapora yazılır,
        # kullanıcı isterse öğretmenin gününü açarak sorunu kaynağında çözer.
        self.forced_groups = self._impossible_groups() if completion_first else set()
        self.edges = []
        self.factors = []
        self.soft_unary = []
        self.domains = [[p for p, _ in c.slots] for c in world.cards]
        self.errors = []
        for r in rules:
            if r.kind not in PAIR_KINDS | FACTOR_KINDS | CORE_KINDS | R.WINDOW_RULES:
                self.errors.append(f"Desteklenmeyen kural: {r.label}")
        self._compile_unary()
        self._compile_pairs()
        self._compile_factors()

    def _compile_unary(self):
        w = self.world
        for c in w.cards:
            costs = []
            for idx, fp in c.slots:
                p = idx % w.P
                cost = sum(bin(fp & w.class_avoid[ci]).count('1') for ci in c.classes)
                if c.teacher >= 0:
                    cost += bin(fp & w.teacher_avoid[c.teacher]).count('1')
                for r in self.rules:
                    if r.is_hard() or r.kind not in R.WINDOW_RULES or not r.applies_card(c):
                        continue
                    noon = 4 if w.P >= 6 else (w.P + 1) // 2
                    bad = ((r.kind == R.X_MORNING_ONLY and p+c.duration > noon)
                        or (r.kind == R.X_AFTERNOON_ONLY and p < noon)
                        or (r.kind == R.X_NOT_LAST_PERIOD and p+c.duration > w.P-1)
                        or (r.kind == R.X_NOT_FIRST_PERIOD and p == 0)
                        or (r.kind == R.X_TIME_WINDOW and (p < r.param or p+c.duration-1 > r.param2)))
                    cost += int(bad) * r.penalty()
                costs.append(cost)
            self.soft_unary.append(costs)


    def _impossible_groups(self):
        """Kart sayısı, öğretmenin açık gün sayısını aşan (sınıf, ders) grupları."""
        w = self.world
        groups = defaultdict(list)
        for c in w.cards:
            for ci in c.classes:
                groups[(ci, c.subject)].append(c)
        out = set()
        for (ci, si), items in groups.items():
            if len(items) < 2:
                continue
            t = items[0].teacher
            days = set()
            for c in items:
                for idx, _ in c.slots:
                    days.add(idx // w.P)
            if len(items) > len(days):
                out.add((ci, si))
        return out

    def _compile_pairs(self):
        w = self.world
        for i, a in enumerate(w.cards):
            for j in range(i):
                b = w.cards[j]
                shared = set(a.classes) & set(b.classes)
                teacher = a.teacher >= 0 and a.teacher == b.teacher
                if not shared and not teacher:
                    continue
                relevant = [r for r in self.rules if r.kind in PAIR_KINDS
                            and r.applies_card(a) and r.applies_card(b)
                            and any(r.applies_class(ci) for ci in shared)]
                checks = []
                for r in relevant:
                    if r.kind == R.X_SUBJECT_ONCE_DAY and a.subject == b.subject:
                        checks.append((0, r))
                    elif r.kind == R.X_TEACHER_ONCE_DAY and teacher:
                        checks.append((0, r))
                    elif r.kind == R.X_PAIR_NOT_SAME_DAY and a.subject != b.subject:
                        checks.append((0, r))
                    elif r.kind == R.X_HARD_NOT_ADJACENT and a.subject != b.subject:
                        checks.append((1, r))
                    elif r.kind == R.X_MIN_DAYS_BETWEEN and a.subject == b.subject:
                        checks.append((2, r))
                shared = set(a.classes) & set(b.classes)
                forced_pair = (a.subject == b.subject and
                               any((ci, a.subject) in self.forced_groups for ci in shared))
                hard, soft = [], []
                for ax, af in a.slots:
                    ad, ap = divmod(ax, w.P)
                    for bx, bf in b.slots:
                        bd, bp = divmod(bx, w.P)
                        h = int(bool(af & bf))
                        s = 0
                        for kind, r in checks:
                            hit = ((kind == 0 and ad == bd)
                                   or (kind == 1 and ad == bd and
                                       (ap+a.duration == bp or bp+b.duration == ap))
                                   or (kind == 2 and abs(ad-bd) < max(1, r.param)))
                            if hit:
                                if not r.is_hard():
                                    s += r.penalty()
                                elif forced_pair:
                                    # Bu grup aritmetik olarak sağlanamıyor:
                                    # kural burada ağır ceza olur, yasak olmaz.
                                    s += FORCED_WEIGHT
                                else:
                                    h = 1
                        hard.append(h)
                        soft.append(s)
                if any(hard) or any(soft):
                    self.edges.append((i, j, hard, soft))

    def _compile_factors(self):
        w = self.world
        for r in self.rules:
            if r.kind not in FACTOR_KINDS:
                continue
            groups = defaultdict(list)
            for c in w.cards:
                if not r.applies_card(c): continue
                if r.kind in (R.X_TEACHER_MAX_HOURS, R.X_TEACHER_MAX_DAYS,
                               R.X_NO_TEACHER_GAP, R.X_TEACHER_MAX_RUN):
                    if c.teacher >= 0: groups[c.teacher].append(c.cid)
                elif r.kind in (R.Y_SUBJECT_MAX_PARALLEL, R.Y_TEACHER_MAX_PARALLEL):
                    groups[c.subject if r.kind == R.Y_SUBJECT_MAX_PARALLEL else c.teacher].append(c.cid)
                else:
                    for ci in c.classes:
                        if not r.applies_class(ci): continue
                        key = (ci, c.subject) if r.kind in (R.X_SUBJECT_MAX_HOURS,
                            R.X_PRACTICAL_MAX_HOURS, R.X_SUBJECT_MAX_SESSIONS,
                            R.X_EVEN_SPREAD) else ci
                        groups[key].append(c.cid)
            kind = {R.X_SUBJECT_MAX_HOURS: 0, R.X_PRACTICAL_MAX_HOURS: 0,
                    R.X_CLASS_MAX_HOURS: 0, R.X_TEACHER_MAX_HOURS: 0,
                    R.X_SUBJECT_MAX_SESSIONS: 1, R.X_TEACHER_MAX_DAYS: 2,
                    R.X_SAME_DAY_ADJACENT: 3, R.X_NO_CLASS_GAP: 3,
                    R.X_NO_TEACHER_GAP: 3, R.X_TEACHER_MAX_RUN: 4,
                    R.X_EVEN_SPREAD: 5, R.Y_SUBJECT_MAX_PARALLEL: 6,
                    R.Y_TEACHER_MAX_PARALLEL: 6}[r.kind]
            for cards in groups.values():
                self.factors.append(Factor(kind, max(1, r.param), r.is_hard(),
                                           r.penalty(), cards, r.label))

    def _body(self):
        """Problemin tohumdan BAĞIMSIZ gövdesi — bir kez üretilir, saklanır.

        Gövde kartların domainlerini, kenar maliyet tablolarını ve faktörleri
        taşır ve bu veri her arama çağrısında BİREBİR AYNIDIR; çağrıdan çağrıya
        değişen tek şey başlıktaki tohum ve süredir.

        v188'de gövde 4,5 MB. Sekiz paralel şeridin her biri her kuşakta bunu
        yeniden biçimlendirdiğinde, arama hiç başlamadan önce saniyeler
        harcanıyordu — üstelik Python'da metin biçimleme GIL tuttuğu için
        şeritler bunu paralel bile yapamıyor, sırayla bekliyordu. Altmış
        saniyelik bütçenin yaklaşık on dördü buraya gidiyordu.

        Bir kez üretip saklamak bu maliyeti tek seferliğe indirir.
        """
        if getattr(self, '_body_cache', None) is not None:
            return self._body_cache
        w = self.world
        out = []
        for c, domain, soft in zip(w.cards, self.domains, self.soft_unary):
            # An empty-domain card has only the absent value. It remains in all
            # accounting; absence is never counted as a completed placement.
            out.append(f"{c.duration} {c.duration*len(c.classes)} "
                       f"{int(c.locked_at is not None)} {len(domain) or 1} ")
            out.append(" ".join(f"{p} {s}" for p, s in zip(domain, soft))
                       if domain else "-1 0")
            out.append("\n")
        for i, j, hard, soft in self.edges:
            # Empty domains cannot contribute any pair conflict.
            nh = max(1, len(self.domains[i]))*max(1, len(self.domains[j]))
            if not hard: hard, soft = [0]*nh, [0]*nh
            out.append(f"{i} {j} "+" ".join(f"{h} {s}" for h, s in zip(hard, soft))+"\n")
        for f in self.factors:
            out.append(f"{f.kind} {f.limit} {int(f.hard)} {f.weight} {len(f.cards)} "
                       + " ".join(map(str, f.cards))+"\n")
        self._body_cache = "".join(out)
        return self._body_cache

    def header(self, seconds, seed, upper_bound):
        w = self.world
        return (f"2 {len(w.cards)} {len(self.edges)} {len(self.factors)} "
                f"{w.D} {w.P} {seconds} {seed} {upper_bound}\n")

    def write(self, stream, seconds, seed, upper_bound):
        stream.write(self.header(seconds, seed, upper_bound))
        stream.write(self._body())
