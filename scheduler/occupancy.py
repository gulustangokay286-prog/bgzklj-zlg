"""
scheduler/occupancy.py — Y EKSENİ: çakışma çekirdeği.

Bu modül KURAL BİLMEZ. Tek bir soruya cevap verir:

    "Bu kart bu hücreye konabilir mi — birileri orada mı?"

Y ekseni müzakereye kapalıdır. Bir Y ihlali kötü çizelge değil, GEÇERSİZ
çizelgedir: aynı öğretmen aynı anda iki sınıfta olamaz, aynı sınıf aynı anda
iki derste olamaz. Bu yüzden Y burada asla puanlanmaz, asla esnetilmez, asla
objective fonksiyonuna girmez. Sadece eler.

Veri yapısı bitmaskedir. Hafta D*P hücredir (örn. 5x8 = 40 bit) ve tek bir
Python tamsayısına sığar. Çakışma kontrolü tek bir AND işlemidir:

    footprint & (teacher_busy | teacher_closed | class_busy | class_closed)

Eski motorda bu kontrol CP-SAT'a binlerce AddAtMostOne kısıtı olarak
veriliyordu; model kurulumu tek başına saniyeler alıyordu. Burada kurulum yok:
diziler doğrudan indekslenir. aSc'nin saniyeler yerine milisaniyelerde
çalışmasının sebebi tam olarak budur.

BİRLEŞİK DERS: classes birden fazla olan kart öğretmen için TEK doluluk üretir,
çünkü öğretmen gerçekten tek bir derste, tek bir salondadır. İki sınıf için iki
ayrı doluluk yazmak sahte çakışma üretir.
"""


class Occupancy:
    __slots__ = ("D", "P", "N", "class_busy", "teacher_busy",
                 "class_closed", "teacher_closed", "placed", "_full")

    def __init__(self, world):
        self.D = world.D
        self.P = world.P
        self.N = world.D * world.P
        self.class_busy = [0] * len(world.classes)
        self.teacher_busy = [0] * len(world.teachers)
        self.class_closed = list(world.class_closed)
        self.teacher_closed = list(world.teacher_closed)
        self.placed = {}          # cid -> (idx, footprint)
        self._full = (1 << self.N) - 1

    # ── sorgu ───────────────────────────────────────────────────────────────

    def blocked_mask(self, card) -> int:
        """Kartın ASLA giremeyeceği hücrelerin birleşik maskesi."""
        m = 0
        for c in card.classes:
            m |= self.class_busy[c] | self.class_closed[c]
        t = card.teacher
        if t >= 0:
            m |= self.teacher_busy[t] | self.teacher_closed[t]
        return m

    def fits(self, card, footprint: int) -> bool:
        """Tek AND — motorun en sık çağrılan fonksiyonu."""
        if footprint == 0:
            return False
        for c in card.classes:
            if footprint & (self.class_busy[c] | self.class_closed[c]):
                return False
        t = card.teacher
        if t >= 0 and footprint & (self.teacher_busy[t] | self.teacher_closed[t]):
            return False
        return True

    def blockers(self, card, footprint: int) -> set:
        """Bu ayak izini tutan kartların cid kümesi.

        Tahliye zinciri buna göre kimi çıkaracağına karar verir. Kapalı hücre
        bir kart tarafından tutulmuyor demektir — tahliye edilemez, bu yüzden
        kapalı hücreye denk gelen ayak izi için boş küme yerine None döner.
        """
        for c in card.classes:
            if footprint & self.class_closed[c]:
                return None
        t = card.teacher
        if t >= 0 and footprint & self.teacher_closed[t]:
            return None
        out = set()
        for cid, (_, fp) in self.placed.items():
            if fp & footprint:
                out.add(cid)
        return out

    def free_cells(self, class_idx: int) -> int:
        """Sınıfın hâlâ boş ve açık hücrelerinin maskesi."""
        return self._full & ~(self.class_busy[class_idx] | self.class_closed[class_idx])

    # ── değişim ─────────────────────────────────────────────────────────────

    def place(self, card, idx: int, footprint: int):
        for c in card.classes:
            self.class_busy[c] |= footprint
        if card.teacher >= 0:
            self.teacher_busy[card.teacher] |= footprint
        self.placed[card.cid] = (idx, footprint)

    def unplace(self, card):
        rec = self.placed.pop(card.cid, None)
        if rec is None:
            return None
        idx, footprint = rec
        inv = ~footprint
        for c in card.classes:
            self.class_busy[c] &= inv
        if card.teacher >= 0:
            self.teacher_busy[card.teacher] &= inv
        return idx

    def is_placed(self, cid: int) -> bool:
        return cid in self.placed

    # ── doğrulama ───────────────────────────────────────────────────────────

    def verify(self, world) -> list:
        """Bağımsız son kontrol.

        Yerleştirme sırasında tutulan maskelere GÜVENMEZ; çizelgeyi sıfırdan
        yeniden sayar. Maskeyi bozan bir hata varsa burada yakalanır — motorun
        kendi defterine bakarak kendini onaylaması hiçbir şeyi garanti etmez.
        """
        errors = []
        by_card = {c.cid: c for c in world.cards}
        cls_cell = {}     # (class, idx) -> cid
        tch_cell = {}     # (teacher, idx) -> cid

        for cid, (idx, fp) in self.placed.items():
            card = by_card[cid]
            d, p = divmod(idx, self.P)
            for off in range(card.duration):
                cell = idx + off
                for c in card.classes:
                    prev = cls_cell.get((c, cell))
                    if prev is not None:
                        errors.append(
                            f"SINIF ÇAKIŞMASI · {world.classes[c]} · "
                            f"{d+1}.gün {p+off+1}.saat: "
                            f"{by_card[prev].subject_name} ile {card.subject_name}")
                    cls_cell[(c, cell)] = cid
                    if (1 << cell) & self.class_closed[c]:
                        errors.append(
                            f"KAPALI HÜCRE · {world.classes[c]} · "
                            f"{d+1}.gün {p+off+1}.saat: {card.subject_name}")
                t = card.teacher
                if t >= 0:
                    prev = tch_cell.get((t, cell))
                    if prev is not None and prev != cid:
                        errors.append(
                            f"ÖĞRETMEN ÇAKIŞMASI · {world.teachers[t]} · "
                            f"{d+1}.gün {p+off+1}.saat: "
                            f"{'+'.join(by_card[prev].class_names)} ile "
                            f"{'+'.join(card.class_names)}")
                    tch_cell[(t, cell)] = cid
                    if (1 << cell) & self.teacher_closed[t]:
                        errors.append(
                            f"ÖĞRETMEN KAPALI · {world.teachers[t]} · "
                            f"{d+1}.gün {p+off+1}.saat")
        return errors
