"""
kempe_scheduler.py — çizelgeyi ŞANSA bırakmayan yöntem: Kempe zinciri.

Neden bu:

Çizelge kurmak aslında bir İKİLİ ÇİZGE KENAR BOYAMA problemidir. Bir yanda
sınıflar, öbür yanda öğretmenler; her ders saati ikisini birleştiren bir kenar;
renkler ise zaman dilimleri. König teoremi der ki: ikili çizgede en büyük derece
kaç ise o kadar renkle KESİN düzgün boyama vardır — ve bunu bulan yapıcı bir
algoritma da vardır: alternating path (Kempe zinciri).

Kempe hamlesi şudur: bir dersi koyacak ortak boş saat yoksa, sınıfın boş olduğu
saat `a` ile öğretmenin boş olduğu saat `b` seçilir; `a` ve `b` renklerinden
oluşan alt çizgede öğretmenden başlayan zincir bulunur ve bu zincirdeki BÜTÜN
derslerin saati a<->b diye takas edilir. Zincir bir yol olduğu için takas hiçbir
çakışma yaratmaz — ve sonunda öğretmen de `a` saatinde boşalır, ders oraya konur.

Farkı şu: tahliye zinciri (eski yöntem) dersleri söküp "umarım başka yere
sığarlar" der; Kempe zinciri ise hiçbir şeyi sökmez, tümünü aynı anda kaydırır ve
sonuç YAPISI GEREĞİ geçerlidir. Sıkışık çizelgelerde fark buradan çıkıyor.

Öğretmen müsaitliği işin içine girince teorik garanti kalkar (liste boyama, NP),
o yüzden zincir bir kısıtlamaya çarparsa başka (a, b) çifti denenir. Pratikte
bütün çiftleri denemek, tek bir dersi yerleştirmek için yüzlerce farklı yapısal
hamle demektir.

İki faz:
    FAZ 1 — 2 saatlik bloklar, renk = hizalı saat ÇİFTİ (1-2, 3-4, ...)
    FAZ 2 — 1 saatlik dersler, renk = kalan tek saatler
Her fazın kendi içinde renk kümesi tek tiptir; Kempe böylece temiz çalışır.

Saf Python. Hiçbir şeyi kaydetmez.
"""
import time
from collections import defaultdict


class KempeSolver:
    def __init__(self, blocks, class_open, teacher_ok, D, P, rng, deadline):
        """blocks: [{cls, tk, size, ...}] — sınıf/öğretmen anahtarları hazır."""
        self.blocks = blocks
        self.n = len(blocks)
        self.class_open = class_open
        self.teacher_ok = teacher_ok
        self.D, self.P = D, P
        self.rng = rng
        self.deadline = deadline

        self.pos = [None] * self.n
        self.cell = {}      # (cls, day, period) -> blok
        self.tcell = {}     # (tk, day, period)  -> blok

    # ── temel ────────────────────────────────────────────────────────
    def slots_of(self, i, day, start):
        return [(day, start + o) for o in range(self.blocks[i]["size"])]

    def legal(self, i, day, start, aligned=False):
        """Sınıf açık mı, öğretmen çalışabilir mi, gün taşmıyor mu."""
        b = self.blocks[i]
        if start + b["size"] > self.P:
            return False
        if aligned and b["size"] > 1 and start % b["size"]:
            return False
        opens = self.class_open.get(b["cls"], ())
        for (d, p) in self.slots_of(i, day, start):
            if (d, p) not in opens:
                return False
            if b["tk"] and not self.teacher_ok(b["tk"], d, p):
                return False
        return True

    def class_free(self, i, day, start):
        b = self.blocks[i]
        return all((b["cls"], d, p) not in self.cell
                   for (d, p) in self.slots_of(i, day, start))

    def teacher_free(self, i, day, start):
        b = self.blocks[i]
        if not b["tk"]:
            return True
        return all((b["tk"], d, p) not in self.tcell
                   for (d, p) in self.slots_of(i, day, start))

    def put(self, i, day, start):
        b = self.blocks[i]
        for (d, p) in self.slots_of(i, day, start):
            self.cell[(b["cls"], d, p)] = i
            if b["tk"]:
                self.tcell[(b["tk"], d, p)] = i
        self.pos[i] = (day, start)

    def take(self, i):
        if self.pos[i] is None:
            return
        b = self.blocks[i]
        day, start = self.pos[i]
        for (d, p) in self.slots_of(i, day, start):
            self.cell.pop((b["cls"], d, p), None)
            if b["tk"]:
                self.tcell.pop((b["tk"], d, p), None)
        self.pos[i] = None

    # ── Kempe zinciri ────────────────────────────────────────────────
    def kempe_chain(self, i, a, b):
        """`a` ve `b` renkleri arasında, öğretmenden başlayan zinciri topla.

        Zincir: öğretmenin `a` saatindeki dersi -> o dersin sınıfının `b`
        saatindeki dersi -> onun öğretmeninin `a` saatindeki dersi -> ...
        Dönen: zincirdeki blok listesi ve her birinin yeni saati; zincir bir
        kısıtlamaya çarparsa None.
        """
        blk = self.blocks[i]
        chain = []
        seen = set()
        # Zincirin ilk halkası: öğretmeni `a` saatinde meşgul eden ders.
        cur = self.tcell.get((blk["tk"], a[0], a[1])) if blk["tk"] else None
        cur_from, cur_to = a, b
        while cur is not None:
            if cur in seen:
                return None                     # döngü: bu çift işe yaramaz
            seen.add(cur)
            cb = self.blocks[cur]
            if cb["size"] != blk["size"]:
                return None                     # farklı boy: temiz takas olmaz
            new_start = cur_to[1]
            if not self.legal(cur, cur_to[0], new_start):
                return None                     # takas kısıtlamayı ihlal eder
            chain.append((cur, (cur_to[0], new_start)))
            # Zincir devam: bu dersin SINIFI hedef saatte kimle dolu?
            nxt = self.cell.get((cb["cls"], cur_to[0], cur_to[1]))
            if nxt is None or nxt == cur:
                break
            cur = nxt
            cur_from, cur_to = cur_to, cur_from  # renkleri değiştir
        return chain

    def place(self, i, aligned=False):
        b = self.blocks[i]
        starts = [(d, p) for d in range(self.D) for p in range(self.P)
                  if self.legal(i, d, p, aligned=aligned)]
        self.rng.shuffle(starts)

        # 1) Ortak boş saat
        for (d, p) in starts:
            if self.class_free(i, d, p) and self.teacher_free(i, d, p):
                self.put(i, d, p)
                return True
        if not b["tk"]:
            return False

        # 2) Kempe: sınıfın boş olduğu saat `a`, öğretmenin boş olduğu saat `b`
        free_for_class = [(d, p) for (d, p) in starts if self.class_free(i, d, p)]
        free_for_teacher = [(d, p) for (d, p) in starts if self.teacher_free(i, d, p)]
        self.rng.shuffle(free_for_class)
        self.rng.shuffle(free_for_teacher)

        for a in free_for_class[:24]:
            for bcol in free_for_teacher[:24]:
                if time.time() > self.deadline:
                    return False
                if a == bcol:
                    continue
                chain = self.kempe_chain(i, a, bcol)
                if chain is None:
                    continue
                # Zinciri uygula
                saved = [(j, self.pos[j]) for j, _ in chain]
                for j, _ in chain:
                    self.take(j)
                ok = True
                for j, (nd, np_) in chain:
                    if not (self.class_free(j, nd, np_) and self.teacher_free(j, nd, np_)):
                        ok = False
                        break
                    self.put(j, nd, np_)
                if ok and self.class_free(i, a[0], a[1]) and self.teacher_free(i, a[0], a[1]):
                    self.put(i, a[0], a[1])
                    return True
                # geri al
                for j, _ in chain:
                    self.take(j)
                for (j, old) in saved:
                    if old is not None:
                        self.put(j, old[0], old[1])
        return False

    def adopt(self, positions):
        """Hazır bir çizelgeyi devral (zincir çözücüsünün bıraktığı taban)."""
        self.cell.clear()
        self.tcell.clear()
        self.pos = [None] * self.n
        for i, pos in enumerate(positions):
            if pos is not None:
                self.put(i, pos[0], pos[1])

    def solve(self, order=None):
        idx = order if order is not None else sorted(
            range(self.n), key=lambda i: -self.blocks[i]["size"])
        for i in idx:
            if time.time() > self.deadline:
                break
            self.place(i)
        return [i for i in range(self.n) if self.pos[i] is None]

    def solve_by_size(self, rng=None):
        """BOY BOY boya: önce bütün 2 saatlikler, sonra 1 saatlikler.

        Kempe zinciri ancak AYNI boydaki bloklar arasında kurulabilir — 2 saatlik
        bir dersle 1 saatlik dersin saatini takas etmek çizelgeyi bozar. Karışık
        sırayla ilerlerken zincir neredeyse her seferinde boy uyuşmazlığına
        çarpıyor ve hamle üretilemiyordu. Aynı boyları bir arada işlemek, her
        fazın içinde renk kümesini tek tipleştirir; Kempe teoremdeki gibi çalışır.

        Ayrıca 2 saatlikler HİZALI saatlere (1-2, 3-4 ...) konur: araya sıkışan
        tek saatler, gün içinde 2 saatlik bloğa yer bırakmayan delikler açıyordu.
        """
        rng = rng or self.rng
        sizes = sorted({b["size"] for b in self.blocks}, reverse=True)
        for size in sizes:
            group = [i for i in range(self.n)
                     if self.blocks[i]["size"] == size and self.pos[i] is None]
            rng.shuffle(group)
            # En az yeri olan önce
            group.sort(key=lambda i: sum(
                1 for d in range(self.D) for p in range(self.P)
                if self.legal(i, d, p, aligned=(size > 1))))
            for i in group:
                if time.time() > self.deadline:
                    break
                if not self.place(i, aligned=(size > 1)):
                    # Hizalı yer bulunamadıysa hizasız da dene
                    self.place(i, aligned=False)
        return [i for i in range(self.n) if self.pos[i] is None]

    def verify(self):
        cells, tcells = set(), set()
        for i, b in enumerate(self.blocks):
            if self.pos[i] is None:
                continue
            d0, s0 = self.pos[i]
            if not self.legal(i, d0, s0):
                return False
            for (d, p) in self.slots_of(i, d0, s0):
                if (b["cls"], d, p) in cells:
                    return False
                cells.add((b["cls"], d, p))
                if b["tk"]:
                    if (b["tk"], d, p) in tcells:
                        return False
                    tcells.add((b["tk"], d, p))
        return True

    def placements(self):
        out = []
        for i, b in enumerate(self.blocks):
            if self.pos[i] is None:
                continue
            d, p = self.pos[i]
            out.append({"cls": b["cls"], "day": d, "period": p,
                        "duration": b["size"], "subject": b.get("subject", ""),
                        "teacher": b.get("teacher", ""),
                        "block_id": b.get("block_id", ""), "raw": b.get("raw", b)})
        return out


def polish_with_kempe(blocks, positions, class_open, teacher_ok, D, P, rng,
                      time_budget=20.0):
    """Hazır bir tabandaki AÇIKTA kalanları Kempe hamleleriyle yerleştir.

    Zincir çözücüsü son bir iki derste tıkanıyor: söktüğü dersleri yeniden
    yerleştiremiyor. Kempe zinciri farklı bir hamle — hiçbir dersi limboda
    bırakmadan, bütün bir zinciri birlikte kaydırıp yer açıyor. İkisi arka arkaya
    çalışınca zincirin bıraktığı boşluklar kapanıyor.
    """
    deadline = time.time() + max(1.0, float(time_budget))
    solver = KempeSolver(blocks, class_open, teacher_ok, D, P, rng, deadline)
    solver.adopt(positions)
    missing = [i for i in range(len(blocks)) if solver.pos[i] is None]
    progress = True
    while missing and progress and time.time() < deadline:
        progress = False
        for i in list(missing):
            if time.time() > deadline:
                break
            if solver.place(i):
                progress = True
        missing = [i for i in range(len(blocks)) if solver.pos[i] is None]
    if not solver.verify():
        return None, None
    return solver.placements(), sum(blocks[i]["size"] for i in missing)


def solve_kempe(blocks, class_open, teacher_ok, D, P, rng, time_budget=30.0,
                restarts=40):
    """Kempe zincirli çözüm; farklı sıralarla tekrar dener.

    Dönen: (yerleşimler, açıkta_kalan_saat)
    """
    deadline = time.time() + max(1.0, float(time_budget))
    best, best_missing = [], None
    n = len(blocks)
    for attempt in range(restarts):
        if time.time() > deadline:
            break
        solver = KempeSolver(blocks, class_open, teacher_ok, D, P, rng, deadline)
        if attempt % 3 == 0:            # önce uzun bloklar (en kısıtlı olanlar)
            order = sorted(range(n), key=lambda i: (-blocks[i]["size"], rng.random()))
        elif attempt % 3 == 1:          # önce en az yeri olanlar
            order = sorted(range(n), key=lambda i: (
                sum(1 for d in range(D) for p in range(P)
                    if solver.legal(i, d, p)), rng.random()))
        else:
            order = list(range(n))
            rng.shuffle(order)
        missing = solver.solve(order)
        if not solver.verify():
            continue
        hours = sum(blocks[i]["size"] for i in missing)
        if best_missing is None or hours < best_missing:
            best, best_missing = solver.placements(), hours
        if hours == 0:
            break
    return best, (best_missing if best_missing is not None else -1)
