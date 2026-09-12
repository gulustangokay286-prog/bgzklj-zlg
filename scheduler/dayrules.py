"""
scheduler/dayrules.py — X EKSENİ: gün ekseni çekirdeği.

Y ekseni "bu hücre dolu mu?" sorar. X ekseni bambaşka bir soru sorar:

    "Bu sınıfın bu gününde bundan kaç tane var?"

Bütün Planlama İlişkileri buradadır. Y fiziksel imkânsızlığı engeller; X
pedagojik kaliteyi belirler. Bu yüzden X'te SERTLİK DERECESİ vardır: "Sıkı"
işaretli kural yerleştirmede eler, diğerleri ceza puanı verir. Ekrandaki
"Önem Derecesi" alanı tam olarak buraya bağlanır — eski motorda bu alan hiç
okunmuyordu.

Veri yapısı sayaçtır, maske değil. Çünkü soru "var mı" değil "kaç tane":

    subj_sessions[sınıf][gün][ders]   kaç SEANS
    subj_hours   [sınıf][gün][ders]   kaç SAAT
    tch_sessions [sınıf][gün][öğr]    kaç SEANS
    tch_hours    [öğr][gün]           öğretmenin o günkü toplam saati

SEANS ile SAAT ayrımı kritiktir ve eski motorda karışıyordu:
    2 saatlik bitişik Matematik kartı = 1 SEANS, 2 SAAT
    "aynı ders aynı gün tekrar etmesin" SEANS sayar.
    "günde en fazla 2 saat"             SAAT sayar.
Aynı sayaçla ikisini birden ölçmeye çalışmak, 2 saatlik tek bloğu "günde iki
kez matematik" sanmaya yol açar.

Bütün kontroller O(1)'dir. Bir kart denendiğinde sayaçlara bakılır, kabul
edilirse artırılır, geri alınırken azaltılır. Hiçbir yerde tarama yoktur.
"""

from collections import defaultdict
from . import rules as R


class DayRules:
    """X ekseni sayaçları + kural değerlendirmesi."""

    def __init__(self, world, rule_list):
        self.w = world
        self.D = world.D
        self.P = world.P

        # Kuralları tipine göre ayır — her denemede liste taramak pahalı.
        self.hard = defaultdict(list)
        self.soft = defaultdict(list)
        for r in rule_list:
            if r.axis != R.X:
                continue
            if r.kind in R.WINDOW_RULES:
                continue          # domain kurulumunda uygulandı
            (self.hard if r.is_hard() else self.soft)[r.kind].append(r)

        nC, nT, nS = len(world.classes), len(world.teachers), len(world.subjects)
        D = self.D

        # sınıf × gün × ders
        self.subj_sess = [[defaultdict(int) for _ in range(D)] for _ in range(nC)]
        self.subj_hrs  = [[defaultdict(int) for _ in range(D)] for _ in range(nC)]
        # sınıf × gün × öğretmen
        self.tch_sess  = [[defaultdict(int) for _ in range(D)] for _ in range(nC)]
        # öğretmen × gün (okul geneli)
        self.tch_hrs   = [[0] * D for _ in range(nT)]
        self.tch_days  = [0] * nT          # bitmask: öğretmen hangi günler okulda
        # sınıf × gün toplam saat
        self.cls_hrs   = [[0] * D for _ in range(nC)]
        # ders × sınıf: hangi günlerde var (bitmask) — yayılım ölçümü için
        self.subj_days = [defaultdict(int) for _ in range(nC)]
        # sınıf × gün × ders -> (ilk saat, son saat). Aynı dersin o günkü
        # kartlarının kapladığı KESİNTİSİZ aralık. Bitişiklik kuralı bunun
        # üzerinden ölçülür: yeni kart ya aralığın hemen başına ya hemen
        # sonuna oturur, ortada boşluk bırakamaz.
        self.subj_span = [[{} for _ in range(D)] for _ in range(nC)]
        # sınıf × gün × öğretmen -> o gün verdiği DERS kümesi
        self.tch_subj = [[{} for _ in range(D)] for _ in range(nC)]

        self._pair_rules = self.hard.get(R.X_PAIR_NOT_SAME_DAY, []) + \
                           self.soft.get(R.X_PAIR_NOT_SAME_DAY, [])
        self._mindays = self.hard.get(R.X_MIN_DAYS_BETWEEN, []) + \
                        self.soft.get(R.X_MIN_DAYS_BETWEEN, [])

    # ── SERT KONTROL — eler ─────────────────────────────────────────────────

    def hard_ok(self, card, d: int, p: int) -> bool:
        """'Sıkı' işaretli X kuralları bu kartı bu güne almaya izin veriyor mu?

        Tek bir False yeter; ilk ihlalde çıkılır. Bu fonksiyon motorun en sık
        çağrılan ikinci fonksiyonudur, bu yüzden sıralama en ucuz ve en çok
        eleyen kuraldan başlar.
        """
        s, t, dur = card.subject, card.teacher, card.duration

        # X-1 — aynı ders aynı gün TEKRAR etmesin.
        #
        # Tekrar demek, öğrencinin o dersi gün içinde iki AYRI seferde
        # görmesidir. Aynı dersin ikinci kartı birincinin hemen bitişiğine
        # oturuyorsa öğrenci tek bir kesintisiz blok görür; bu tekrar değil.
        # Bu yüzden ölçülen şey kart sayısı değil, BİTİŞİKLİK.
        for r in self.hard.get(R.X_SUBJECT_ONCE_DAY, ()):
            if not r.applies_card(card):
                continue
            for c in card.classes:
                if not r.applies_class(c):
                    continue
                span = self.subj_span[c][d].get(s)
                if span is None:
                    continue
                lo, hi = span
                if p != hi + 1 and p + dur != lo:
                    return False

        # X-2 — aynı öğretmen aynı gün tekrar etmesin.
        #
        # Bu kural FARKLI BRANŞLAR içindir: öğretmen sınıfa hem Matematik hem
        # Geometri veriyorsa, sınıf o gün onu iki ayrı ders için görmemelidir.
        # Aynı dersin devamı için görebilir — o durumu X-1'in bitişiklik
        # şartı zaten yönetiyor. İki kuralı da "günde tek seans" diye kurmak
        # onları birbiriyle çelişir hâle getirir.
        if t >= 0:
            for r in self.hard.get(R.X_TEACHER_ONCE_DAY, ()):
                if not r.applies_card(card):
                    continue
                for c in card.classes:
                    if not r.applies_class(c):
                        continue
                    subs = self.tch_subj[c][d].get(t)
                    if subs and s not in subs:
                        return False

        # X-3 ders günde en fazla N saat
        for r in self.hard.get(R.X_SUBJECT_MAX_HOURS, ()):
            if not r.applies_card(card):
                continue
            for c in card.classes:
                if r.applies_class(c) and self.subj_hrs[c][d][s] + dur > r.param:
                    return False

        # X-3b ders günde en fazla N seans
        for r in self.hard.get(R.X_SUBJECT_MAX_SESSIONS, ()):
            if not r.applies_card(card):
                continue
            for c in card.classes:
                if r.applies_class(c) and self.subj_sess[c][d][s] + 1 > r.param:
                    return False

        # X-4 uygulamalı ders günde en fazla N saat
        for r in self.hard.get(R.X_PRACTICAL_MAX_HOURS, ()):
            if s not in r.subjects:
                continue
            for c in card.classes:
                if not r.applies_class(c):
                    continue
                tot = sum(self.subj_hrs[c][d][x] for x in r.subjects)
                if tot + dur > r.param:
                    return False

        # X-5 şu dersler aynı güne gelmesin
        for r in self._pair_rules:
            if not r.is_hard() or s not in r.subjects:
                continue
            for c in card.classes:
                if not r.applies_class(c):
                    continue
                for other in r.subjects:
                    if other != s and self.subj_sess[c][d][other] > 0:
                        return False

        # X-6 sınıf günde en fazla N saat
        for r in self.hard.get(R.X_CLASS_MAX_HOURS, ()):
            for c in card.classes:
                if r.applies_class(c) and self.cls_hrs[c][d] + dur > r.param:
                    return False

        # X-7 öğretmen günde en fazla N saat (okul geneli)
        if t >= 0:
            for r in self.hard.get(R.X_TEACHER_MAX_HOURS, ()):
                if r.applies_teacher(t) and self.tch_hrs[t][d] + dur > r.param:
                    return False

            # X-8 öğretmen haftada en fazla N gün
            for r in self.hard.get(R.X_TEACHER_MAX_DAYS, ()):
                if not r.applies_teacher(t):
                    continue
                if not (self.tch_days[t] >> d) & 1:
                    if bin(self.tch_days[t]).count("1") + 1 > r.param:
                        return False

        # X-9 aynı dersin kartları arasında en az N gün
        for r in self._mindays:
            if not r.is_hard() or not r.applies_card(card):
                continue
            for c in card.classes:
                if not r.applies_class(c):
                    continue
                mask = self.subj_days[c][s]
                for dd in range(self.D):
                    if (mask >> dd) & 1 and abs(dd - d) < max(1, r.param):
                        return False
        return True

    # ── YUMUŞAK PUANLAMA — sıralar ──────────────────────────────────────────

    def penalty(self, card, d: int, p: int) -> int:
        """Bu yerleşim ne kadar kötü? 0 = kusursuz. Küçük olan seçilir."""
        s, t, dur = card.subject, card.teacher, card.duration
        cost = 0

        for r in self.soft.get(R.X_SUBJECT_ONCE_DAY, ()):
            if r.applies_card(card):
                for c in card.classes:
                    if r.applies_class(c) and self.subj_sess[c][d][s] >= 1:
                        cost += r.penalty()

        if t >= 0:
            for r in self.soft.get(R.X_TEACHER_ONCE_DAY, ()):
                if r.applies_card(card):
                    for c in card.classes:
                        if r.applies_class(c) and self.tch_sess[c][d][t] >= 1:
                            cost += r.penalty()

        for r in self.soft.get(R.X_SUBJECT_MAX_HOURS, ()):
            if r.applies_card(card):
                for c in card.classes:
                    if r.applies_class(c):
                        over = self.subj_hrs[c][d][s] + dur - r.param
                        if over > 0:
                            cost += r.penalty() * over

        for r in self.soft.get(R.X_PRACTICAL_MAX_HOURS, ()):
            if s in r.subjects:
                for c in card.classes:
                    if r.applies_class(c):
                        tot = sum(self.subj_hrs[c][d][x] for x in r.subjects)
                        over = tot + dur - r.param
                        if over > 0:
                            cost += r.penalty() * over

        for r in self._pair_rules:
            if r.is_hard() or s not in r.subjects:
                continue
            for c in card.classes:
                if r.applies_class(c):
                    for other in r.subjects:
                        if other != s and self.subj_sess[c][d][other] > 0:
                            cost += r.penalty()

        # X-EVEN yayılım: dersin zaten kullandığı bir güne tekrar koymak cezalı
        for r in self.soft.get(R.X_EVEN_SPREAD, []) + self.hard.get(R.X_EVEN_SPREAD, []):
            if r.applies_card(card):
                for c in card.classes:
                    if r.applies_class(c) and (self.subj_days[c][s] >> d) & 1:
                        cost += r.penalty() or 1_000

        # X-KAÇIN: kullanıcının "zorunlu olmadıkça" dediği hücreler
        fp = self.w.footprint(d, p, dur)
        for c in card.classes:
            if fp & self.w.class_avoid[c]:
                cost += 500
        if t >= 0 and fp & self.w.teacher_avoid[t]:
            cost += 500

        return cost

    # ── ŞEKİL KURALLARI — yerleşim sonrası ölçülür ─────────────────────────

    def shape_penalty(self, card, d: int, p: int, occ) -> int:
        """Sıralamaya bakan kurallar: bitişiklik, boşluk, zor ders art arda.

        Bunlar sayaçla ölçülemez; komşu hücrelere bakmak gerekir. Bu yüzden
        ayrı tutulur ve sadece hayatta kalan adaylar için hesaplanır.
        """
        cost = 0
        dur = card.duration
        s = card.subject

        # X-HARD_NOT_ADJACENT: iki zor ders art arda gelmesin
        for r in self.hard.get(R.X_HARD_NOT_ADJACENT, []) + \
                 self.soft.get(R.X_HARD_NOT_ADJACENT, []):
            if s not in r.subjects:
                continue
            for c in card.classes:
                if not r.applies_class(c):
                    continue
                before = self._subject_at(occ, c, d, p - 1)
                after = self._subject_at(occ, c, d, p + dur)
                hit = (before in r.subjects) or (after in r.subjects)
                if hit:
                    cost += r.penalty() if not r.is_hard() else 1_000_000

        # X-SAME_DAY_ADJACENT: aynı güne düşerse bitişik olsun
        for r in self.hard.get(R.X_SAME_DAY_ADJACENT, []) + \
                 self.soft.get(R.X_SAME_DAY_ADJACENT, []):
            if not r.applies_card(card):
                continue
            for c in card.classes:
                if not r.applies_class(c) or self.subj_sess[c][d][s] == 0:
                    continue
                touching = (self._subject_at(occ, c, d, p - 1) == s or
                            self._subject_at(occ, c, d, p + dur) == s)
                if not touching:
                    cost += r.penalty() if not r.is_hard() else 1_000_000

        # X-NO_CLASS_GAP: sınıfın gününde delik bırakma
        for r in self.soft.get(R.X_NO_CLASS_GAP, []) + self.hard.get(R.X_NO_CLASS_GAP, []):
            for c in card.classes:
                if r.applies_class(c):
                    cost += self._gap_count(occ, c, d) * (r.penalty() or 2_000)

        return cost

    def _subject_at(self, occ, class_idx, d, p):
        if p < 0 or p >= self.P:
            return None
        cell = 1 << (d * self.P + p)
        for cid, (idx, fp) in occ.placed.items():
            if fp & cell:
                card = self.w.cards[cid]
                if class_idx in card.classes:
                    return card.subject
        return None

    def _gap_count(self, occ, class_idx, d):
        """Sınıfın o günündeki dolu hücreler arasında kalan boş hücre sayısı."""
        row = 0
        base = d * self.P
        busy = occ.class_busy[class_idx]
        closed = occ.class_closed[class_idx]
        cells = [(busy >> (base + p)) & 1 for p in range(self.P)]
        open_ = [not ((closed >> (base + p)) & 1) for p in range(self.P)]
        first = next((i for i, v in enumerate(cells) if v), None)
        last = next((i for i in range(self.P - 1, -1, -1) if cells[i]), None)
        if first is None or last is None:
            return 0
        for i in range(first, last + 1):
            if not cells[i] and open_[i]:
                row += 1
        return row

    # ── SAYAÇ GÜNCELLEME ────────────────────────────────────────────────────

    def apply(self, card, d: int, p: int):
        s, t, dur = card.subject, card.teacher, card.duration
        for c in card.classes:
            span = self.subj_span[c][d].get(s)
            if span is None:
                self.subj_span[c][d][s] = (p, p + dur - 1)
            else:
                self.subj_span[c][d][s] = (min(span[0], p), max(span[1], p + dur - 1))
            if t >= 0:
                self.tch_subj[c][d].setdefault(t, set()).add(s)
            self.subj_sess[c][d][s] += 1
            self.subj_hrs[c][d][s] += dur
            self.cls_hrs[c][d] += dur
            self.subj_days[c][s] |= (1 << d)
            if t >= 0:
                self.tch_sess[c][d][t] += 1
        if t >= 0:
            self.tch_hrs[t][d] += dur
            self.tch_days[t] |= (1 << d)

    def revert(self, card, d: int, p: int):
        s, t, dur = card.subject, card.teacher, card.duration
        for c in card.classes:
            self.subj_sess[c][d][s] -= 1
            if self.subj_sess[c][d][s] <= 0:
                self.subj_span[c][d].pop(s, None)
                if t >= 0:
                    subs = self.tch_subj[c][d].get(t)
                    if subs:
                        subs.discard(s)
                        if not subs:
                            self.tch_subj[c][d].pop(t, None)
            else:
                span = self.subj_span[c][d].get(s)
                if span:
                    lo, hi = span
                    if p == lo:
                        self.subj_span[c][d][s] = (p + dur, hi)
                    elif p + dur - 1 == hi:
                        self.subj_span[c][d][s] = (lo, p - 1)
            self.subj_hrs[c][d][s] -= dur
            self.cls_hrs[c][d] -= dur
            if self.subj_sess[c][d][s] <= 0:
                self.subj_days[c][s] &= ~(1 << d)
            if t >= 0:
                self.tch_sess[c][d][t] -= 1
        if t >= 0:
            self.tch_hrs[t][d] -= dur
            if all(self.tch_hrs[t][dd] == 0 for dd in range(self.D)):
                self.tch_days[t] = 0
            elif self.tch_hrs[t][d] == 0:
                self.tch_days[t] &= ~(1 << d)

    # ── RAPOR ───────────────────────────────────────────────────────────────

    def violations(self, occ) -> list:
        """Yerleşmiş çizelgedeki X ihlallerini sıfırdan sayar.

        Sayaçlara güvenmez; çizelgeyi yeniden okur. Rapor, motorun kendi
        defterinden değil sonucun kendisinden çıkar.
        """
        out = []
        w = self.w
        seen_subj = defaultdict(list)   # (cls, day, subj) -> [card]
        seen_tch = defaultdict(list)    # (cls, day, teacher) -> [card]
        for cid, (idx, fp) in occ.placed.items():
            card = w.cards[cid]
            d = idx // self.P
            for c in card.classes:
                seen_subj[(c, d, card.subject)].append((card, idx % self.P))
                if card.teacher >= 0:
                    seen_tch[(c, d, card.teacher)].append((card, idx % self.P))

        active_subj_once = self.hard.get(R.X_SUBJECT_ONCE_DAY, []) + \
                           self.soft.get(R.X_SUBJECT_ONCE_DAY, [])
        active_tch_once = self.hard.get(R.X_TEACHER_ONCE_DAY, []) + \
                          self.soft.get(R.X_TEACHER_ONCE_DAY, [])

        if active_subj_once:
            for (c, d, s), lst in seen_subj.items():
                if len(lst) <= 1:
                    continue
                spans = sorted((x[1], x[1] + x[0].duration - 1) for x in lst)
                broken = any(spans[i + 1][0] != spans[i][1] + 1
                             for i in range(len(spans) - 1))
                if broken:
                    out.append(f"X-1 · {w.classes[c]} · {d+1}.gün · "
                               f"{w.subjects[s]} gün içinde bölünmüş hâlde "
                               f"{len(lst)} kez")
        if active_tch_once:
            for (c, d, t), lst in seen_tch.items():
                subs = {x[0].subject for x in lst}
                if len(subs) > 1:
                    names = ", ".join(sorted(w.subjects[x] for x in subs))
                    out.append(f"X-2 · {w.classes[c]} · {d+1}.gün · "
                               f"{w.teachers[t]} aynı gün {len(subs)} farklı ders "
                               f"({names})")
        return out
