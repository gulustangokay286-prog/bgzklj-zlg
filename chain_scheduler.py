"""
chain_scheduler.py — "yer yoksa yer AÇ": özyinelemeli tahliye zinciri.

Neden gerekti:

Boğaziçi çizelgesinde aritmetik 180/180'e izin veriyor (Sultan Yılmaz 20 saat /
20 müsait saat, Yasemin 16/16, Nuray 16/16, Barış 8/8 — dört öğretmen %100
doluluk). Ama gün→saat ayrıştırmasıyla çalışan arama böyle KATI bir kurulumda
plato yapıyor: blokları önce günlere bölmek, sonra gün içinde dizmek, oynama payı
sıfırken neredeyse her zaman çıkmaza düşüyor.

Bu modül farklı çalışır — profesyonel çizelge programlarının (FET'in "recursive
swapping", aSc'nin benzer mekanizması) yaptığı gibi:

    1. Dersi boş ve uygun bir saate koymayı dene.
    2. Boş yer yoksa: uygun ama DOLU bir saati seç, oradakini SÖK, dersi oraya
       koy, söktüğünü özyinelemeli olarak başka yere yerleştirmeye çalış.
    3. O da yer bulamazsa daha derine in (zincir), olmazsa hepsini geri al ve
       başka aday saati dene.
    4. Tur bitiminde açıkta kalan varsa "sarsma" (shake): rastgele bir kısmı
       söküp yeniden dene. Zaman bütçesi dolana ya da 180/180 olana kadar.

Zincir, tek bir dersi yerleştirmek için onlarca dersi yerinden oynatabilir —
insanın elle yaptığı takas zincirinin aynısı, ama saniyede binlercesi.

Saf Python, Qt yok. Hiçbir şeyi kaydetmez; sonucu yerleşim listesi olarak döner.
"""
import time
from collections import defaultdict


class ChainSolver:
    """Saat saat yerleştirir; tıkandığında zincirleme takasla yer açar."""

    def __init__(self, classes, class_blocks, class_open, teacher_ok,
                 D, P, rng, deadline, max_depth=10, max_eject=2):
        self.classes = list(classes)
        self.D, self.P = D, P
        self.rng = rng
        self.deadline = deadline
        self.max_depth = max_depth
        self.max_eject = max_eject
        self.nodes = 0

        # class_open[cls] -> açık (gün, saat) kümesi
        self.class_open = class_open
        # teacher_ok(tkey, day, period) -> öğretmen o saatte çalışabilir mi
        self.teacher_ok = teacher_ok

        self.blocks = []
        for cls in self.classes:
            for blk in class_blocks.get(cls, []):
                self.blocks.append({
                    "cls": cls,
                    "tk": blk.get("_tk", ""),
                    "size": max(1, int(blk.get("duration") or 1)),
                    "subject": blk.get("subject", ""),
                    "raw": blk,
                })
        self.n = len(self.blocks)
        self.pos = [None] * self.n            # blok -> (gün, başlangıç saati)
        self.cell = {}                        # (sınıf, gün, saat) -> blok
        self.tcell = {}                       # (öğretmen, gün, saat) -> blok

        # Adaylar STATİK: sınıfın açık olduğu ve öğretmenin çalışabildiği,
        # gün sınırını aşmayan bütün başlangıçlar. Doluluk burada bakılmaz —
        # zincir zaten doluyu boşaltmak için var.
        self.starts = [self._compute_starts(i) for i in range(self.n)]

    # ── temel sorgular ────────────────────────────────────────────────
    def _compute_starts(self, i):
        b = self.blocks[i]
        out = []
        opens = self.class_open.get(b["cls"], set())
        for d in range(self.D):
            for p in range(self.P - b["size"] + 1):
                ok = True
                for off in range(b["size"]):
                    if (d, p + off) not in opens:
                        ok = False
                        break
                    if b["tk"] and not self.teacher_ok(b["tk"], d, p + off):
                        ok = False
                        break
                if ok:
                    out.append((d, p))
        return out

    def _blockers(self, i, day, start):
        """Bu bloğu buraya koymak için sökülmesi gereken bloklar."""
        b = self.blocks[i]
        out = set()
        for off in range(b["size"]):
            slot = (day, start + off)
            occ = self.cell.get((b["cls"],) + slot)
            if occ is not None and occ != i:
                out.add(occ)
            if b["tk"]:
                busy = self.tcell.get((b["tk"],) + slot)
                if busy is not None and busy != i:
                    out.add(busy)
        return out

    def _put(self, i, day, start):
        b = self.blocks[i]
        for off in range(b["size"]):
            slot = (day, start + off)
            self.cell[(b["cls"],) + slot] = i
            if b["tk"]:
                self.tcell[(b["tk"],) + slot] = i
        self.pos[i] = (day, start)

    def snapshot(self):
        """Bütün yerleşim durumunun kopyası.

        Zincir denemesi başarısızsa YALNIZCA söktüğümüz blokları geri koymak
        yetmez: özyineleme sırasında başka bloklar da yer değiştirmiş olabilir.
        Kısmi geri alma, üst üste binen yerleşimlere yol açıyordu (180/180
        görünüp 7 öğretmen + 13 sınıf çakışması çıkması bu yüzdendi). Tek doğru
        yol tam durumu geri yüklemek.
        """
        return tuple(self.pos)

    def restore(self, snap):
        self.cell.clear()
        self.tcell.clear()
        for i, pos in enumerate(snap):
            self.pos[i] = None
        for i, pos in enumerate(snap):
            if pos is not None:
                self._put(i, pos[0], pos[1])

    def _take(self, i):
        b = self.blocks[i]
        if self.pos[i] is None:
            return
        day, start = self.pos[i]
        for off in range(b["size"]):
            slot = (day, start + off)
            if self.cell.get((b["cls"],) + slot) == i:
                del self.cell[(b["cls"],) + slot]
            if b["tk"] and self.tcell.get((b["tk"],) + slot) == i:
                del self.tcell[(b["tk"],) + slot]
        self.pos[i] = None

    def adopt(self, positions):
        """Hazır bir çizelgeyi devral (tabu aramasının bıraktığı taban)."""
        self.cell.clear()
        self.tcell.clear()
        self.pos = [None] * self.n
        for i, pos in enumerate(positions):
            if pos is not None:
                self._put(i, pos[0], pos[1])

    # ── zincir ────────────────────────────────────────────────────────
    def place(self, i, depth):
        """Bloğu yerleştir; gerekirse başkalarını söküp zincirleme taşı."""
        if self.pos[i] is not None:
            return True
        self.nodes += 1
        # Zaman kontrolü HER düğümde: seyrek kontrol, derin zincirlerde bütçenin
        # kat kat aşılmasına yol açıyordu (12 sn bütçe 64 sn sürüyordu).
        if time.time() > self.deadline:
            return False

        options = list(self.starts[i])
        self.rng.shuffle(options)

        # 1) Bedava yer varsa oraya.
        for (d, p) in options:
            if not self._blockers(i, d, p):
                self._put(i, d, p)
                return True
        if depth <= 0:
            return False

        # 2) Yer yoksa AÇ: en az kişiyi rahatsız eden adaylar önce.
        scored = []
        for (d, p) in options:
            blockers = self._blockers(i, d, p)
            if 0 < len(blockers) <= self.max_eject:
                scored.append((len(blockers), self.rng.random(), d, p, blockers))
        scored.sort()

        for _cnt, _r, d, p, blockers in scored[:5]:
            snap = self.snapshot()
            for j in blockers:
                self._take(j)
            self._put(i, d, p)

            ok = True
            for j in blockers:
                if not self.place(j, depth - 1):
                    ok = False
                    break
            if ok:
                return True
            self.restore(snap)          # TAM geri alma (kısmi geri alma çakışma üretir)
        return False

    # ── ana döngü ─────────────────────────────────────────────────────
    def solve(self, shakes=100000, strategy=0):
        """Önce sırayla yerleştir, sonra açıkta kalan için HEDEFLİ sarsma.

        Sarsma rastgele değil: yerleşemeyen dersin aday saatlerini işgal eden
        blokları söker (ruin), sonra hepsini yeniden yerleştirmeye çalışır
        (recreate). Rastgele blok söküp denemek, sıkışık bir çizelgede zaman
        harcamaktan başka işe yaramıyordu.
        """
        # Restartlar arası ÇEŞİTLİLİK: aynı sırayla başlamak aynı çıkmazlara
        # götürüyor. Dört farklı başlangıç sırası, dört farklı arama ağacı demek.
        if strategy % 4 == 0:      # en az seçeneği olan önce (klasik MRV)
            order = sorted(range(self.n),
                           key=lambda i: (len(self.starts[i]), -self.blocks[i]["size"]))
        elif strategy % 4 == 1:    # önce uzun bloklar
            order = sorted(range(self.n),
                           key=lambda i: (-self.blocks[i]["size"], len(self.starts[i])))
        elif strategy % 4 == 2:    # sınıf sınıf
            order = sorted(range(self.n),
                           key=lambda i: (self.blocks[i]["cls"], -self.blocks[i]["size"]))
        else:                      # tamamen rastgele
            order = list(range(self.n))
            self.rng.shuffle(order)
        for i in order:
            if time.time() > self.deadline:
                break
            self.place(i, self.max_depth)

        missing = [i for i in range(self.n) if self.pos[i] is None]
        best_snap, best_count = self.snapshot(), len(missing)

        for _ in range(shakes):
            if not missing or time.time() > self.deadline:
                break
            victim = missing[self.rng.randrange(len(missing))]

            # RUIN: kurbanın gidebileceği saatleri tutanları sök.
            opts = list(self.starts[victim])
            self.rng.shuffle(opts)
            doomed = set()
            for (d, p) in opts[:6]:
                doomed |= self._blockers(victim, d, p)
                if len(doomed) >= 8:
                    break
            for j in doomed:
                self._take(j)

            # RECREATE: önce kurban. Son birkaç ders en zorudur — açıkta ne kadar
            # az kaldıysa zinciri o kadar derinleştir ve daha çok dersi yerinden
            # oynatmaya izin ver. Kolay olanlar zaten oturdu; kalanlar için
            # "biraz daha uğraş" doğru strateji.
            deep = self.max_depth * (4 if len(missing) <= 2 else 2)
            eject_backup = self.max_eject
            if len(missing) <= 2:
                self.max_eject = 3
            self.place(victim, deep)
            self.max_eject = eject_backup
            for j in range(self.n):
                if time.time() > self.deadline:
                    break
                if self.pos[j] is None:
                    self.place(j, self.max_depth)

            missing = [i for i in range(self.n) if self.pos[i] is None]
            if len(missing) < best_count:
                best_snap, best_count = self.snapshot(), len(missing)
            elif len(missing) > best_count + 2:
                self.restore(best_snap)          # çok kötüleştiyse en iyiye dön
                missing = [i for i in range(self.n) if self.pos[i] is None]

        if len([i for i in range(self.n) if self.pos[i] is None]) > best_count:
            self.restore(best_snap)
        return [i for i in range(self.n) if self.pos[i] is None]

    # ── ÇAKIŞMAYA İZİN VEREN FAZ: zorla doldur, sonra takasla erit ──────
    #
    # "Ders açıkta kalsın" formülasyonu son 1-2 derste tıkanıyor: yerleştirilmemiş
    # bir ders varken hamle kümesi dar. Tersini yapmak çok daha güçlü: BÜTÜN
    # dersleri sınıfın boş hücrelerine zorla koy (öğretmen çakışsa bile), sonra
    # çakışmaları aynı sınıf içi takaslarla erit. Sınıf doluluğu her hamlede
    # korunur, arama uzayı zengindir, takılma olmaz.
    def force_fill(self):
        for i in range(self.n):
            if self.pos[i] is not None:
                continue
            b = self.blocks[i]
            opens = sorted(self.class_open.get(b["cls"], set()))
            for (d, p) in opens:
                if p + b["size"] - 1 >= self.P:
                    continue
                free = True
                for off in range(b["size"]):
                    if (d, p + off) not in self.class_open.get(b["cls"], set()):
                        free = False
                        break
                    if (b["cls"], d, p + off) in self.cell:
                        free = False
                        break
                if free:
                    for off in range(b["size"]):
                        self.cell[(b["cls"], d, p + off)] = i
                    self.pos[i] = (d, p)
                    break
        # tcell'i baştan kur (çakışmalar bilerek göz ardı edilerek)
        self.tcell = {}
        self._clash_map = defaultdict(list)
        for i, b in enumerate(self.blocks):
            if self.pos[i] is None or not b["tk"]:
                continue
            d, p = self.pos[i]
            for off in range(b["size"]):
                self._clash_map[(b["tk"], d, p + off)].append(i)
        return sum(1 for i in range(self.n) if self.pos[i] is None)

    def clash_cost(self):
        """Öğretmen çakışması + öğretmenin kapalı saatinde ders sayısı."""
        cost = 0
        for i, b in enumerate(self.blocks):
            if self.pos[i] is None or not b["tk"]:
                continue
            d, p = self.pos[i]
            for off in range(b["size"]):
                if not self.teacher_ok(b["tk"], d, p + off):
                    cost += 1
        seen = defaultdict(int)
        for i, b in enumerate(self.blocks):
            if self.pos[i] is None or not b["tk"]:
                continue
            d, p = self.pos[i]
            for off in range(b["size"]):
                seen[(b["tk"], d, p + off)] += 1
        cost += sum(v - 1 for v in seen.values() if v > 1)
        return cost

    def _swap_positions(self, i, j):
        b1, b2 = self.blocks[i], self.blocks[j]
        p1, p2 = self.pos[i], self.pos[j]
        for off in range(b1["size"]):
            self.cell.pop((b1["cls"], p1[0], p1[1] + off), None)
        for off in range(b2["size"]):
            self.cell.pop((b2["cls"], p2[0], p2[1] + off), None)
        for off in range(b1["size"]):
            self.cell[(b1["cls"], p2[0], p2[1] + off)] = i
        for off in range(b2["size"]):
            self.cell[(b2["cls"], p1[0], p1[1] + off)] = j
        self.pos[i], self.pos[j] = p2, p1

    def repair_clashes(self, rounds=400000):
        """Aynı sınıf içi takaslarla çakışmaları erit (min-conflicts)."""
        by_class = defaultdict(list)
        for i, b in enumerate(self.blocks):
            if self.pos[i] is not None:
                by_class[b["cls"]].append(i)
        cost = self.clash_cost()
        best_cost, best_snap = cost, self.snapshot()
        for it in range(rounds):
            if cost == 0 or time.time() > self.deadline:
                break
            # Çakışan bir dersi seç
            bad = []
            seen = defaultdict(list)
            for i, b in enumerate(self.blocks):
                if self.pos[i] is None or not b["tk"]:
                    continue
                d, p = self.pos[i]
                for off in range(b["size"]):
                    seen[(b["tk"], d, p + off)].append(i)
                    if not self.teacher_ok(b["tk"], d, p + off):
                        bad.append(i)
            for v in seen.values():
                if len(v) > 1:
                    bad.extend(v)
            if not bad:
                break
            i = bad[self.rng.randrange(len(bad))]
            mates = [j for j in by_class[self.blocks[i]["cls"]]
                     if j != i and self.blocks[j]["size"] == self.blocks[i]["size"]]
            if not mates:
                continue
            j = mates[self.rng.randrange(len(mates))]
            self._swap_positions(i, j)
            new_cost = self.clash_cost()
            if new_cost <= cost or self.rng.random() < 0.02:
                cost = new_cost
                if cost < best_cost:
                    best_cost, best_snap = cost, self.snapshot()
            else:
                self._swap_positions(i, j)
        if self.clash_cost() > best_cost:
            self.restore(best_snap)
        return best_cost

    def verify(self):
        """Yerleşimde çakışma var mı? (olmamalı; olursa sonuç çöpe atılır)"""
        cells, tcells = set(), set()
        for i, b in enumerate(self.blocks):
            if self.pos[i] is None:
                continue
            day, start = self.pos[i]
            for off in range(b["size"]):
                ck = (b["cls"], day, start + off)
                if ck in cells:
                    return False
                cells.add(ck)
                if (day, start + off) not in self.class_open.get(b["cls"], set()):
                    return False
                if b["tk"]:
                    tkk = (b["tk"], day, start + off)
                    if tkk in tcells:
                        return False
                    tcells.add(tkk)
                    if not self.teacher_ok(b["tk"], day, start + off):
                        return False
        return True

    def placements(self):
        out = []
        for i, b in enumerate(self.blocks):
            if self.pos[i] is None:
                continue
            day, start = self.pos[i]
            out.append({"cls": b["cls"], "day": day, "period": start,
                        "duration": b["size"], "subject": b["subject"],
                        "teacher": b["raw"].get("teacher", ""),
                        "block_id": b["raw"].get("block_id", ""),
                        "raw": b["raw"]})
        return out


def solve_chain(classes, class_blocks, class_open, teacher_ok, D, P,
                rng, time_budget=45.0, restarts=40):
    """Bağımsız denemeler; her biri farklı başlangıç sırasıyla.

    Süreyi fazlara bölmek yerine BAĞIMSIZ denemelere ayırmak daha iyi sonuç
    veriyor: çizelge katı olduğu için bir denemenin nereye takılacağı büyük
    ölçüde başlangıç sırasına bağlı; çeşitlilik, tek bir denemeyi uzatmaktan
    daha değerli. Sonuç ancak doğrulamadan geçerse kabul edilir.

    Dönen: (yerleşimler, açıkta_kalan_saat)
    """
    deadline = time.time() + max(1.0, float(time_budget))
    best, best_missing = [], None
    for attempt in range(restarts):
        now = time.time()
        if now >= deadline:
            break
        # Her denemeye eşit dilim; kalan süre azaldıkça dilim küçülür.
        slice_end = min(deadline, now + max(3.0, (deadline - now) / 3.0))
        solver = ChainSolver(classes, class_blocks, class_open, teacher_ok,
                             D, P, rng, slice_end)
        missing_idx = solver.solve(strategy=attempt)
        if not solver.verify():
            continue
        hours = sum(solver.blocks[i]["size"] for i in missing_idx)
        if best_missing is None or hours < best_missing:
            best, best_missing = solver.placements(), hours
        if hours == 0:
            break
    return best, (best_missing if best_missing is not None else -1)
