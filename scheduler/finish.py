"""
scheduler/finish.py — bitirme geçişi: son kartları derinlemesine ara.

Ana arama (tabu) çizelgenin tamamına yayılmış bir optimizasyon yapar ve
neredeyse tam bir sonuca çok hızlı varır. Ama son bir iki kartta tıkanır ve
orada kalır: v188'de 60 saniyeyle de 180 saniyeyle de aynı 283/285 çıkıyor —
yani sorun süre değil, aramanın o noktada yapabildiği hamlenin sınırlı olması.

Tabu araması her adımda TEK bir kartı oynatır. Son kartın yerleşebilmesi için
çoğu zaman üç dört kartın birlikte kayması gerekir ve böyle bir hamle, tek
kartlık adımların hiçbir dizilişinde ara durumu kötüleştirmeden görünmez.

Bu geçiş tam olarak o hamleyi arar ve yalnızca onu: açıkta kalan kart için
bütün yerleri dener, her yerde engelleyenleri söker, onları da özyinelemeli
olarak yeniden yerleştirir. Arama alanı küçüktür (bir iki kart), bu yüzden
tüketici arama burada hesaplıdır — bütün çizelgede olmazdı.

Sonuç, ana aramanın kurduğu çizelgeyi BOZMAZ: dal başarısızsa her şey birebir
eski hâline döner, başarılıysa yalnızca gereken kartlar yer değiştirmiş olur.
"""

from collections import defaultdict
from . import rules as R
from .model import subject_family


class Finisher:
    def __init__(self, world, rule_list, positions):
        self.w = world
        self.P = world.P
        self.D = world.D
        self.pos = list(positions)

        self.subject_once = any(r.kind == R.X_SUBJECT_ONCE_DAY and r.is_hard()
                                for r in rule_list)
        self.teacher_once = any(r.kind == R.X_TEACHER_ONCE_DAY and r.is_hard()
                                for r in rule_list)
        self.hard_adj = set()
        for r in rule_list:
            if r.kind == R.X_HARD_NOT_ADJACENT and r.is_hard():
                self.hard_adj |= set(r.subjects)

        n = len(world.cards)
        self.cls_cell = {}      # (sınıf, hücre) -> kart
        self.tch_cell = {}      # (öğretmen, hücre) -> kart
        self.fam_day = defaultdict(set)   # (sınıf, gün) -> {aile}
        self.tch_day = defaultdict(set)   # (sınıf, gün) -> {öğretmen}
        for i, idx in enumerate(self.pos):
            if idx >= 0:
                self._occupy(i, idx, True)

    def _occupy(self, i, idx, on):
        c = self.w.cards[i]
        d = idx // self.P
        for off in range(c.duration):
            cell = idx + off
            for ci in c.classes:
                if on: self.cls_cell[(ci, cell)] = i
                else: self.cls_cell.pop((ci, cell), None)
            if c.teacher >= 0:
                if on: self.tch_cell[(c.teacher, cell)] = i
                else: self.tch_cell.pop((c.teacher, cell), None)
        for ci in c.classes:
            key = (ci, d)
            if on:
                self.fam_day[key].add(c.family)
                if c.teacher >= 0: self.tch_day[key].add(c.teacher)
            else:
                # sayım gerektiği için yeniden kur
                self.fam_day[key] = {self.w.cards[j].family
                                     for (cj, cell), j in self.cls_cell.items()
                                     if cj == ci and cell // self.P == d}
                self.tch_day[key] = {self.w.cards[j].teacher
                                     for (cj, cell), j in self.cls_cell.items()
                                     if cj == ci and cell // self.P == d
                                     and self.w.cards[j].teacher >= 0}

    def _rules_ok(self, i, idx):
        c = self.w.cards[i]
        d, p = divmod(idx, self.P)
        for ci in c.classes:
            if self.subject_once and c.family in self.fam_day[(ci, d)]:
                return False
            if self.teacher_once and c.teacher >= 0 and c.teacher in self.tch_day[(ci, d)]:
                return False
            if c.subject in self.hard_adj:
                for nb in (p - 1, p + c.duration):
                    if 0 <= nb < self.P:
                        j = self.cls_cell.get((ci, d * self.P + nb))
                        if j is not None and self.w.cards[j].subject in self.hard_adj:
                            return False
        return True

    def _blockers(self, i, idx):
        c = self.w.cards[i]
        out = set()
        for off in range(c.duration):
            cell = idx + off
            for ci in c.classes:
                j = self.cls_cell.get((ci, cell))
                if j is not None: out.add(j)
            if c.teacher >= 0:
                j = self.tch_cell.get((c.teacher, cell))
                if j is not None: out.add(j)
        return out

    def _free(self, i, idx):
        return not self._blockers(i, idx)

    def place(self, i, depth, max_depth, banned):
        """Kartı yerleştirmeyi dener; gerekirse engelleyenleri taşır."""
        c = self.w.cards[i]
        # Önce boş bir yer
        for idx, _ in c.slots:
            if self._free(i, idx) and self._rules_ok(i, idx):
                self.pos[i] = idx; self._occupy(i, idx, True)
                return True
        if depth >= max_depth:
            return False
        # Sonra tahliyeyle
        for idx, _ in c.slots:
            if not self._rules_ok(i, idx):
                continue
            blk = self._blockers(i, idx)
            if not blk or len(blk) > 2 or (blk & banned):
                continue
            snap = list(self.pos)
            moved = []
            for j in blk:
                old = self.pos[j]
                self._occupy(j, old, False); self.pos[j] = -1
                moved.append((j, old))
            if self._free(i, idx) and self._rules_ok(i, idx):
                self.pos[i] = idx; self._occupy(i, idx, True)
                ok = True
                nb = banned | blk | {i}
                for j, _ in moved:
                    if not self.place(j, depth + 1, max_depth, nb):
                        ok = False; break
                if ok:
                    return True
            self._restore(snap)
        return False

    def _restore(self, snap):
        """Çizelgeyi anlık görüntüye birebir döndürür.

        Önce farklı olan her kart sökülür, sonra hepsi eski yerine konur; tek
        geçişte yapmak henüz sökülmemiş bir kartın üstüne yazma riski taşır.
        """
        for i, idx in enumerate(self.pos):
            if idx >= 0 and snap[i] != idx:
                self._occupy(i, idx, False); self.pos[i] = -1
        for i, idx in enumerate(snap):
            if idx >= 0 and self.pos[i] < 0 and self._free(i, idx):
                self.pos[i] = idx; self._occupy(i, idx, True)

    def run(self, max_depth=4):
        eksik = [i for i, idx in enumerate(self.pos)
                 if idx < 0 and self.w.cards[i].slots]
        kazanc = 0
        for i in sorted(eksik, key=lambda k: len(self.w.cards[k].slots)):
            if self.pos[i] >= 0:
                continue
            if self.place(i, 0, max_depth, frozenset()):
                kazanc += self.w.cards[i].duration * len(self.w.cards[i].classes)
        return self.pos, kazanc
