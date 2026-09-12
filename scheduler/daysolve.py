"""
scheduler/daysolve.py — AŞAMA 2: bir günün saat ataması (Y ekseni).

Gün ataması bittikten sonra geriye kalan soru saftır: bu günün kartları, hangi
saatlere oturacak ki hiçbir öğretmen aynı anda iki sınıfta olmasın?

Bu soru açgözlü aramayla çözülmez ve çözülmeye çalışılmamalıdır. Yapısı bilinen
bir problemdir: sınıflar bir tarafta, öğretmenler diğer tarafta, her kart bir
kenar — yani ÇİFT TARAFLI ÇİZGE. Bir saat dilimi, o çizgede birbirine değmeyen
kenarlardan oluşan bir EŞLEME'dir. Saatleri tek tek doldurmak, çizgeyi
eşlemelere ayırmaktır.

Bunun önemi şu: her saat için EN BÜYÜK eşlemeyi bulmak polinom zamanlıdır ve
kesindir. Açgözlü bir döngü "şu sınıfa şu öğretmeni verdim" der ve sonra
sıkışır; eşleme algoritması o saatte kaç sınıfın aynı anda ders alabileceğinin
matematiksel üst sınırını bulur ve ona ulaşır. Aradaki fark, tıkanan bir
çizelgeyle tamamlanan bir çizelge arasındaki farktır.

İki uzunluk ayrı ele alınır:

  2 SAATLİK BLOKLAR  Önce ve aramayla. Bir blok iki ardışık saati birden
                     kapladığı için sonradan araya sıkıştırılamaz; ızgarada
                     tek sayılı delikler bırakırsa o delikler bir daha
                     kapanmaz.

  1 SAATLİK KARTLAR  Sonra ve eşlemeyle. Blokların bıraktığı boşluklar saat
                     saat, her saatte en büyük eşleme alınarak doldurulur.
"""

import random


def _kuhn(adj, n_left, n_right):
    """Çift taraflı çizgede en büyük eşleme (Kuhn / artırıcı yol).

    adj[i] = i'inci sol düğümün bağlanabileceği sağ düğümler.
    Döner: match_right[j] = j'ye eşlenen sol düğüm, ya da -1.

    Sol taraf sınıflar, sağ taraf o saatte yerleştirilebilecek kartlardır.
    """
    match_right = [-1] * n_right
    match_left = [-1] * n_left

    def try_augment(u, seen):
        for v in adj[u]:
            if seen[v]:
                continue
            seen[v] = True
            if match_right[v] == -1 or try_augment(match_right[v], seen):
                match_right[v] = u
                match_left[u] = v
                return True
        return False

    order = list(range(n_left))
    for u in order:
        if match_left[u] == -1:
            try_augment(u, [False] * n_right)
    return match_left, match_right


class DaySolver:
    """Tek bir günün saat atamasını çözer."""

    def __init__(self, world, day, cards, rng=None):
        self.w = world
        self.d = day
        self.P = world.P
        self.cards = list(cards)
        self.rng = rng or random.Random(1)
        base = day * world.P

        # Bu günün dilimindeki açık saatler.
        self.cls_open = {}
        for ci in range(len(world.classes)):
            self.cls_open[ci] = [p for p in range(self.P)
                                 if not ((world.class_closed[ci] >> (base + p)) & 1)]
        self.tch_open = {}
        for ti in range(len(world.teachers)):
            self.tch_open[ti] = set(p for p in range(self.P)
                                    if not ((world.teacher_closed[ti] >> (base + p)) & 1))

    # ── yerleşim durumu ─────────────────────────────────────────────────────

    def _fresh(self):
        return {
            "cls": {ci: [None] * self.P for ci in range(len(self.w.classes))},
            "tch": {ti: [None] * self.P for ti in range(len(self.w.teachers))},
            "at": {},          # cid -> başlangıç saati
        }

    def _free(self, st, card, p):
        if p + card.duration > self.P:
            return False
        for off in range(card.duration):
            q = p + off
            for ci in card.classes:
                if q not in self.cls_open[ci] or st["cls"][ci][q] is not None:
                    return False
            t = card.teacher
            if t >= 0 and (q not in self.tch_open[t] or st["tch"][t][q] is not None):
                return False
        return True

    def _put(self, st, card, p):
        for off in range(card.duration):
            q = p + off
            for ci in card.classes:
                st["cls"][ci][q] = card.cid
            if card.teacher >= 0:
                st["tch"][card.teacher][q] = card.cid
        st["at"][card.cid] = p

    def _pull(self, st, card):
        p = st["at"].pop(card.cid, None)
        if p is None:
            return
        for off in range(card.duration):
            q = p + off
            for ci in card.classes:
                st["cls"][ci][q] = None
            if card.teacher >= 0:
                st["tch"][card.teacher][q] = None

    # ── 1 saatlik kartlar: saat saat en büyük eşleme ────────────────────────

    def _fill_singles(self, st, singles):
        """Kalan tek saatlik kartları, her saatte en büyük eşlemeyi alarak yerleştirir.

        Saat sırası rastgeledir: sabit sırayla gidilirse hep aynı sıkışma
        noktasına varılır, karıştırmak yeniden denemeleri anlamlı kılar.
        """
        remaining = list(singles)
        periods = list(range(self.P))
        self.rng.shuffle(periods)

        for p in periods:
            if not remaining:
                break
            # Bu saatte hangi sınıf boş, hangi kart konabilir?
            open_classes = [ci for ci in range(len(self.w.classes))
                            if p in self.cls_open[ci] and st["cls"][ci][p] is None]
            if not open_classes:
                continue
            cls_ix = {ci: i for i, ci in enumerate(open_classes)}

            cand = []
            for card in remaining:
                if all(ci in cls_ix for ci in card.classes) and self._free(st, card, p):
                    cand.append(card)
            if not cand:
                continue

            # Sol: sınıflar. Sağ: bu saatte konabilecek kartlar.
            adj = [[] for _ in open_classes]
            for j, card in enumerate(cand):
                for ci in card.classes:
                    adj[cls_ix[ci]].append(j)
            for a in adj:
                self.rng.shuffle(a)

            match_left, _ = _kuhn(adj, len(open_classes), len(cand))

            used = set()
            for i, j in enumerate(match_left):
                if j < 0 or j in used:
                    continue
                card = cand[j]
                if self._free(st, card, p):
                    self._put(st, card, p)
                    used.add(j)
                    remaining.remove(card)
        return remaining

    # ── 2 saatlik bloklar: aramayla ─────────────────────────────────────────

    def _place_blocks(self, st, blocks, singles, depth=0, budget=None):
        """Blokları ardışık saat çiftlerine oturtur.

        Blok yerleşimi sonradan düzeltilemez: bir blok iki saati birden tutar
        ve ızgarada tek sayılı delik bırakırsa o delik bir daha kapanmaz.
        Bu yüzden bloklar önce ve geri izlemeli olarak yerleşir; tek saatlik
        kartlar sonra, artan boşluklara eşlemeyle dağılır.
        """
        if budget is not None:
            if budget[0] <= 0:
                return False
            budget[0] -= 1
        if not blocks:
            return True

        # En az yeri olan blok önce.
        best_i, best_slots = None, None
        for i, card in enumerate(blocks):
            slots = [p for p in range(self.P - card.duration + 1) if self._free(st, card, p)]
            if not slots:
                return False
            if best_slots is None or len(slots) < len(best_slots):
                best_i, best_slots = i, slots
                if len(slots) == 1:
                    break

        card = blocks[best_i]
        rest = blocks[:best_i] + blocks[best_i + 1:]
        self.rng.shuffle(best_slots)

        for p in best_slots:
            self._put(st, card, p)
            if self._blocks_leave_room(st, rest, singles) and \
               self._place_blocks(st, rest, singles, depth + 1, budget):
                return True
            self._pull(st, card)
        return False

    def _blocks_leave_room(self, st, rest_blocks, singles):
        """Budama: kalan bloklar ve tek saatler kalan boşluğa sığıyor mu?

        Sınıf başına iki şey kontrol edilir: toplam saat tutuyor mu, ve kalan
        boşluk 2 saatlik blokları alacak ARDIŞIK çiftler içeriyor mu. İkincisi
        önemlidir; toplam saat tutsa bile boşluklar tek tek dağılmışsa blok
        yerleşemez.
        """
        for ci in range(len(self.w.classes)):
            free = [p for p in self.cls_open[ci] if st["cls"][ci][p] is None]
            need = sum(c.duration for c in rest_blocks if ci in c.classes) + \
                   sum(c.duration for c in singles if ci in c.classes)
            if len(free) < need:
                return False
            n_blocks = sum(1 for c in rest_blocks if ci in c.classes)
            if n_blocks:
                fs = set(free)
                pairs = sum(1 for p in free if (p + 1) in fs)
                if pairs < n_blocks:
                    return False
        return True

    # ── dışa açık ───────────────────────────────────────────────────────────

    def _greedy_blocks(self, st, blocks):
        """Geri izleme tükenince: sığan bloğu sığdığı yere koy, sığmayanı bırak.

        Tam arama başarısız olduğunda hiçbir şey yerleştirmemek en kötü
        seçenektir — o günün otuz küçük kartı da o yüzden yerleşemez ve
        çizelge bir anda elli saat birden kaybeder. Kısmi sonuç, sonraki
        denemeye ve onarım turuna gerçek bir başlangıç noktası verir.
        """
        left = []
        order = sorted(blocks, key=lambda c: -c.duration)
        for card in order:
            slots = [p for p in range(self.P - card.duration + 1) if self._free(st, card, p)]
            if not slots:
                left.append(card)
                continue
            self.rng.shuffle(slots)
            # Tek sayılı delik açmayan yeri tercih et.
            def waste(p):
                w = 0
                for ci in card.classes:
                    before = p - 1
                    after = p + card.duration
                    if before in self.cls_open[ci] and st["cls"][ci][before] is None:
                        if before - 1 < 0 or st["cls"][ci][before - 1] is not None:
                            w += 1
                    if after in self.cls_open[ci] and st["cls"][ci][after] is None:
                        if after + 1 >= self.P or st["cls"][ci][after + 1] is not None:
                            w += 1
                return w
            slots.sort(key=waste)
            self._put(st, card, slots[0])
        return left

    def solve(self, tries=200, block_budget=30_000):
        """Günü çözer. Döner: (yerleşim {cid: saat}, yerleşemeyen kartlar)."""
        blocks = [c for c in self.cards if c.duration >= 2]
        singles = [c for c in self.cards if c.duration == 1]
        best = None

        for _ in range(max(1, tries)):
            st = self._fresh()
            self.rng.shuffle(blocks)
            ok = self._place_blocks(st, list(blocks), singles, budget=[block_budget])
            if ok:
                left_blocks = []
            else:
                # Tam arama tükendi: elde kalanı açgözlüyle yerleştir.
                st = self._fresh()
                left_blocks = self._greedy_blocks(st, list(blocks))
            left_singles = self._fill_singles(st, singles)
            left = left_blocks + left_singles

            if best is None or len(left) < len(best[1]):
                best = (dict(st["at"]), list(left))
            if not left:
                break
        return best
