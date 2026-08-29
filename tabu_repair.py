"""
tabu_repair.py — çakışmaya izin ver, sonra hafızalı aramayla erit.

Yaklaşım (aSc'nin Auto Planner'ı için tarif edilen aileyle aynı):

  * Her ders MUTLAKA bir yerdedir — "yerleşemedi" diye bir durum yok. Sınıfın
    bütün açık hücreleri doldurulur; ihlallere geçici olarak İZİN verilir.
  * Bir maliyet fonksiyonu tanımlanır:
        maliyet = öğretmen çakışması + öğretmenin kapalı saatinde ders
  * Komşuluk zengindir: aynı sınıf içinde iki dersin yerini değiştir, bir dersi
    boş hücreye taşı, 2 saatlik bloğu iki ayrı 1 saatlikle takas et.
  * TABU HAFIZASI: son yapılan hamleler bir süre yasaklanır. Hafızasız yerel
    arama aynı iki hamleyi sonsuza kadar tekrar edip duruyordu — 179'da takılma
    kalıbının sebebi buydu.
  * Özlem ölçütü (aspiration): tabu bir hamle şimdiye kadarki en iyiyi geçerse
    yine de yapılır.

Maliyet ARTIMLI hesaplanır: her hamlede bütün çizelgeyi taramak saniyede birkaç
yüz hamleye düşürüyordu, artımlı hesap yüz binlere çıkarıyor. Sıkışık çizelgede
kazandıran şey bu.

Saf Python. Girdi olarak "sınıf hücreleri dolu" bir başlangıç ister; çıktısı
çakışmasız bir çizelge ya da en iyi bulduğu hâldir.
"""
import time
from collections import defaultdict


class TabuRepair:
    def __init__(self, blocks, class_open, teacher_ok, D, P, rng, deadline,
                 tabu_len=18):
        self.blocks = blocks
        self.n = len(blocks)
        self.class_open = class_open
        self.teacher_ok = teacher_ok
        self.D, self.P = D, P
        self.rng = rng
        self.deadline = deadline
        self.tabu_len = tabu_len

        self.pos = [None] * self.n
        self.cell = {}
        self.tcount = defaultdict(int)     # (tk, d, p) -> kaç ders
        self.cost = 0
        self.tabu = {}
        self.iter = 0

        self.by_class = defaultdict(list)
        for i, b in enumerate(blocks):
            self.by_class[b["cls"]].append(i)

    # ── maliyet ───────────────────────────────────────────────────────
    def _slots(self, i, day, start):
        return [(day, start + o) for o in range(self.blocks[i]["size"])]

    def _cost_of(self, i, day, start, sign):
        """Bir bloğu koymanın/kaldırmanın maliyete etkisi (artımlı)."""
        b = self.blocks[i]
        delta = 0
        if not b["tk"]:
            return 0
        for (d, p) in self._slots(i, day, start):
            key = (b["tk"], d, p)
            before = self.tcount[key]
            after = before + sign
            delta += max(0, after - 1) - max(0, before - 1)
            self.tcount[key] = after
            if not self.teacher_ok(b["tk"], d, p):
                # Kapalı saatte ders, geçici bir çakışmadan çok daha ağırdır:
                # çakışma sonradan takasla çözülebilir, kapalı saat ise
                # öğretmenin orada OLMAMASI demektir. Ağırlığı yüksek tutmak
                # aramayı önce bunları temizlemeye yöneltiyor.
                delta += sign * 5
        return delta

    def put(self, i, day, start):
        b = self.blocks[i]
        for (d, p) in self._slots(i, day, start):
            self.cell[(b["cls"], d, p)] = i
        self.cost += self._cost_of(i, day, start, +1)
        self.pos[i] = (day, start)

    def take(self, i):
        if self.pos[i] is None:
            return
        b = self.blocks[i]
        day, start = self.pos[i]
        for (d, p) in self._slots(i, day, start):
            self.cell.pop((b["cls"], d, p), None)
        self.cost += self._cost_of(i, day, start, -1)
        self.pos[i] = None

    # ── başlangıç: sınıfları TAM doldur ───────────────────────────────
    def seed(self, positions=None):
        if positions:
            for i, pos in enumerate(positions):
                if pos is not None:
                    self.put(i, pos[0], pos[1])
        for i in range(self.n):
            if self.pos[i] is not None:
                continue
            b = self.blocks[i]
            opens = sorted(self.class_open.get(b["cls"], set()))
            spot = None
            for (d, p) in opens:
                if p + b["size"] > self.P:
                    continue
                if all((d, p + o) in self.class_open.get(b["cls"], set())
                       and (b["cls"], d, p + o) not in self.cell
                       for o in range(b["size"])):
                    spot = (d, p)
                    break
            if spot is None:
                return False           # sınıfta yer yok: veri tutarsız
            self.put(i, spot[0], spot[1])
        return True

    # ── komşuluk ──────────────────────────────────────────────────────
    def _conflicted(self):
        bad = []
        for i, b in enumerate(self.blocks):
            if self.pos[i] is None or not b["tk"]:
                continue
            day, start = self.pos[i]
            for (d, p) in self._slots(i, day, start):
                if self.tcount[(b["tk"], d, p)] > 1 or not self.teacher_ok(b["tk"], d, p):
                    bad.append(i)
                    break
        return bad

    def _try_swap(self, i, j):
        """i ve j'nin yerini değiştir; maliyet farkını döndür (uygulanmış olur)."""
        pi, pj = self.pos[i], self.pos[j]
        before = self.cost
        self.take(i)
        self.take(j)
        self.put(i, pj[0], pj[1])
        self.put(j, pi[0], pi[1])
        return self.cost - before

    def _undo_swap(self, i, j):
        self._try_swap(i, j)

    def _day_blocks(self, cls, day):
        out = []
        for i in self.by_class[cls]:
            if self.pos[i] is not None and self.pos[i][0] == day:
                out.append(i)
        return out

    def try_day_swap(self, cls, d1, d2):
        """Bir sınıfın İKİ GÜNÜNÜ komple takas et.

        Tek tek ders takası, bir öğretmenin o güne yığılmış yükünü dağıtamıyor.
        Günün tamamını başka güne taşımak sınıfın gün yapısını (2+2, 2+1+1 ...)
        aynen korur ama öğretmen yüklerini toptan yeniden dağıtır — sıkışık
        çizelgede en etkili hamle bu.
        """
        opens = self.class_open.get(cls, set())
        p1 = {p for (d, p) in opens if d == d1}
        p2 = {p for (d, p) in opens if d == d2}
        if p1 != p2:
            return None                      # gün yapıları farklı: takas olmaz
        b1 = self._day_blocks(cls, d1)
        b2 = self._day_blocks(cls, d2)
        if not b1 and not b2:
            return None
        before = self.cost
        saved = [(i, self.pos[i]) for i in b1 + b2]
        old_start = {i: pos[1] for i, pos in saved}
        for i in b1 + b2:
            self.take(i)
        for i in b1:
            self.put(i, d2, old_start[i])       # aynı saat, öbür gün
        for i in b2:
            self.put(i, d1, old_start[i])
        return self.cost - before, saved

    def restore_positions(self, saved):
        for i, _ in saved:
            self.take(i)
        for i, pos in saved:
            if pos is not None:
                self.put(i, pos[0], pos[1])

    def try_2for1(self, i):
        """2 saatlik bloğu, aynı sınıfın BİTİŞİK iki 1 saatlik dersiyle takas et.

        Aynı boy takası gün içindeki yapıyı (hangi saat 2'lik, hangisi 1'lik)
        asla değiştiremez. Oysa bir öğretmenin çakışması çoğu zaman tam olarak
        bunu gerektiriyor: 2 saatlik ders başka bir güne, onun yerine iki tek
        saat. Bu hamle olmadan arama son bir iki çakışmada kilitleniyordu.
        """
        b = self.blocks[i]
        if b["size"] != 2 or self.pos[i] is None:
            return None
        d0, p0 = self.pos[i]
        singles = [j for j in self.by_class[b["cls"]]
                   if self.blocks[j]["size"] == 1 and self.pos[j] is not None]
        by_slot = {self.pos[j]: j for j in singles}
        cands = []
        for j in singles:
            dj, pj = self.pos[j]
            k = by_slot.get((dj, pj + 1))
            if k is not None and k != j:
                cands.append((j, k, dj, pj))
        self.rng.shuffle(cands)
        for (j, k, dj, pj) in cands[:12]:
            before = self.cost
            saved = [(i, self.pos[i]), (j, self.pos[j]), (k, self.pos[k])]
            self.take(i)
            self.take(j)
            self.take(k)
            self.put(i, dj, pj)          # 2 saatlik, iki tekin yerine
            self.put(j, d0, p0)          # tekler 2 saatliğin yerine
            self.put(k, d0, p0 + 1)
            if self.cost < before:
                return self.cost - before
            self.restore_positions(saved)
        return None

    def perturb(self, strength=3):
        """Takılınca SARS: rastgele gün takasları yap, sonucu koşulsuz kabul et.

        Tabu hafızası aynı hamlelerin tekrarını engelliyor ama arama yine de bir
        havzada sıkışabiliyor. Sarsma, en iyi çözümün çevresinde yeni bir havzaya
        atlatır (iterated local search). Sarsmadan sonra tabu temizlenir, arama
        oradan devam eder — en iyi hâl zaten saklı olduğu için kaybımız yok.
        """
        classes = list(self.by_class.keys())
        for _ in range(strength):
            cls = classes[self.rng.randrange(len(classes))]
            d1 = self.rng.randrange(self.D)
            d2 = self.rng.randrange(self.D)
            if d1 == d2:
                continue
            self.try_day_swap(cls, d1, d2)      # kabul: geri almıyoruz
        self.tabu.clear()

    def run(self, rounds=2000000):
        best_cost = self.cost
        best_pos = list(self.pos)
        since_improve = 0
        while self.iter < rounds and self.cost > 0:
            self.iter += 1
            since_improve += 1
            if (self.iter & 63) == 0 and time.time() > self.deadline:
                break
            if since_improve > 1500:
                # En iyi hâle dön, oradan sars.
                for i in range(self.n):
                    self.take(i)
                for i, pos in enumerate(best_pos):
                    if pos is not None:
                        self.put(i, pos[0], pos[1])
                self.perturb(strength=2 + self.rng.randrange(4))
                since_improve = 0
            bad = self._conflicted()
            if not bad:
                break
            i = bad[self.rng.randrange(len(bad))]
            b = self.blocks[i]

            # Aynı sınıfta, aynı boyda takas adayları
            mates = [j for j in self.by_class[b["cls"]]
                     if j != i and self.blocks[j]["size"] == b["size"]
                     and self.pos[j] is not None]
            if not mates:
                continue
            self.rng.shuffle(mates)

            best_j, best_delta = None, None
            for j in mates[:24]:
                delta = self._try_swap(i, j)
                tabu_key = (i, self.pos[i])
                is_tabu = self.tabu.get(tabu_key, 0) > self.iter
                # Özlem ölçütü: tabu olsa da rekor kırıyorsa kabul.
                if is_tabu and self.cost >= best_cost:
                    self._undo_swap(i, j)
                    continue
                if best_delta is None or delta < best_delta:
                    best_delta, best_j = delta, j
                self._undo_swap(i, j)

            # Ders takası kazandırmıyorsa önce 2<->1+1, sonra GÜN TAKASI dene.
            if best_delta is None or best_delta >= 0:
                gain = self.try_2for1(i)
                if gain is None:
                    for j2 in self.by_class[b["cls"]]:
                        if self.blocks[j2]["size"] == 2:
                            gain = self.try_2for1(j2)
                            if gain is not None:
                                break
                if gain is not None:
                    if self.cost < best_cost:
                        best_cost = self.cost
                        best_pos = list(self.pos)
                    continue
            if best_delta is None or best_delta >= 0:
                days = list(range(self.D))
                self.rng.shuffle(days)
                for d1 in days:
                    for d2 in days:
                        if d1 >= d2:
                            continue
                        res = self.try_day_swap(b["cls"], d1, d2)
                        if res is None:
                            continue
                        delta, saved = res
                        if delta < 0:
                            if self.cost < best_cost:
                                best_cost = self.cost
                                best_pos = list(self.pos)
                            break
                        self.restore_positions(saved)
                    else:
                        continue
                    break

            if best_j is None:
                continue
            self._try_swap(i, best_j)
            self.tabu[(i, self.pos[i])] = self.iter + self.tabu_len
            self.tabu[(best_j, self.pos[best_j])] = self.iter + self.tabu_len

            if self.cost < best_cost:
                best_cost = self.cost
                best_pos = list(self.pos)
                since_improve = 0

        if self.cost > best_cost:
            for i in range(self.n):
                self.take(i)
            for i, pos in enumerate(best_pos):
                if pos is not None:
                    self.put(i, pos[0], pos[1])
        return self.cost

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


def solve_tabu(blocks, class_open, teacher_ok, D, P, rng, time_budget=40.0,
               restarts=6, seed_positions=None):
    """Tabu aramasıyla çakışmasız TAM çizelge ara.

    Dönen: (yerleşimler, maliyet). Maliyet 0 ise çizelge eksiksiz ve çakışmasız.
    """
    deadline = time.time() + max(1.0, float(time_budget))
    best, best_cost = None, None
    for attempt in range(restarts):
        if time.time() > deadline:
            break
        slice_end = min(deadline, time.time() + max(2.0, time_budget / restarts))
        rep = TabuRepair(blocks, class_open, teacher_ok, D, P, rng, slice_end)
        if not rep.seed(seed_positions if attempt == 0 else None):
            continue
        cost = rep.run()
        if best_cost is None or cost < best_cost:
            best, best_cost = rep.placements(), cost
        if cost == 0:
            break
    return best or [], (best_cost if best_cost is not None else -1)
