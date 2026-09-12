"""
scheduler/polish.py — onarım: yerleşemeyen kartı ZORLA yerleştir, kırılanı tamir et.

Açgözlü yerleştirme + tahliye zinciri, ızgarada boşluk varken çok iyi çalışır.
Ama v188 gibi sınıfların açık hücre sayısının gereken saate TAM EŞİT olduğu bir
veride boşluk hiç yoktur: her hücre dolmak zorundadır. Böyle bir ızgarada
"uygun yer bulunamadı" durumu neredeyse her zaman gerçek bir imkânsızlık değil,
yanlış bir erken karardır — biri, çok önce, yanlış hücreyi kapattı.

Bu modül o kararı geri alır. Yöntem klasik min-conflicts + tahliye:

    1. Yerleşemeyen bir kart al.
    2. EN AZ kartı rahatsız eden yere ZORLA koy (çakışanları söküp at).
    3. Sökülenleri kuyruğa ekle; onlar da aynı işlemi görsün.
    4. Tabu listesi son hamleleri yasaklar; yoksa iki kart birbirini
       sonsuza kadar yerinden eder.
    5. Kuyruk boşalırsa çizelge tamam; bütçe biterse en iyi hâl döner.

Bu döngü, yerleşim sayısını monoton artırmaz — geçici olarak kötüleşebilir.
Kötüleşmeye izin vermek, yerel tıkanıklıktan çıkmanın tek yoludur; her adımda
iyileşme dayatan bir arama tam da burada takılır.
"""

import time
from collections import deque


class Repair:
    def __init__(self, world, occ, dayrules, placer, rng, tabu_size=64):
        self.w = world
        self.occ = occ
        self.dr = dayrules
        self.pl = placer
        self.rng = rng
        self.P = world.P
        self.tabu = deque(maxlen=tabu_size)
        self.tabu_set = set()
        self.iterations = 0
        self.forced = 0

    def _tabu_push(self, key):
        if len(self.tabu) == self.tabu.maxlen and self.tabu:
            self.tabu_set.discard(self.tabu[0])
        self.tabu.append(key)
        self.tabu_set.add(key)

    def _best_forced_slot(self, card):
        """Kartı koymak için en az zarar veren yer.

        Maliyet: sökülecek kart sayısı (ağır) + X ceza puanı (hafif). Kapalı
        hücreye denk gelen yer hiç değerlendirilmez — orası tahliye edilemez.
        """
        best = None
        occ, dr = self.occ, self.dr
        for idx, fp in card.slots:
            d, p = divmod(idx, self.P)
            if not dr.hard_ok(card, d, p):
                continue
            if (card.cid, idx) in self.tabu_set:
                continue
            blockers = occ.blockers(card, fp)
            if blockers is None:
                continue
            cost = len(blockers) * 10_000 + dr.penalty(card, d, p) + self.rng.randint(0, 99)
            if best is None or cost < best[0]:
                best = (cost, idx, fp, blockers)
        return best

    def _snapshot(self):
        """Çizelgenin o anki hâli — kart -> yer eşlemesi."""
        return dict(self.occ.placed)

    def _restore(self, snap):
        """Çizelgeyi verilen hâle geri sarar.

        Sayaçlar ve maskeler birlikte geri alınır; ikisinden biri geride
        kalırsa motor kendi defteriyle gerçeği birbirine karıştırır.
        """
        for cid in list(self.occ.placed.keys()):
            self.pl.remove(self.w.cards[cid])
        for cid, (idx, fp) in snap.items():
            card = self.w.cards[cid]
            d, p = divmod(idx, self.P)
            self.occ.place(card, idx, fp)
            self.dr.apply(card, d, p)

    def run(self, unplaced, deadline, max_iter=200_000):
        """unplaced: Card listesi. Döner: hâlâ yerleşemeyenler.

        Arama geçici olarak KÖTÜLEŞEBİLİR — tıkanıklıktan çıkmanın yolu bu.
        Ama dönen sonuç asla kötüleşmez: görülen en iyi hâl ayrıca saklanır ve
        bütçe biterken o geri yüklenir. Yoksa onarım, elindeki iyi çizelgeyi
        bozup yarım bırakabilir.
        """
        queue = deque(unplaced)
        best_missing = len(queue)
        best_state = self._snapshot()
        best_queue = list(queue)
        stall = 0

        while queue and time.time() < deadline and self.iterations < max_iter:
            self.iterations += 1
            card = queue.popleft()

            # Önce dürüstçe dene — belki bu arada yer açıldı.
            if self.pl.place_with_chain(card):
                if len(queue) < best_missing:
                    best_missing = len(queue)
                    best_state = self._snapshot()
                    best_queue = list(queue)
                    stall = 0
                continue

            choice = self._best_forced_slot(card)
            if choice is None:
                queue.append(card)
                stall += 1
                if stall > len(queue) * 4 + 32:
                    break
                continue

            _, idx, fp, blockers = choice
            for bid in blockers:
                bcard = self.w.cards[bid]
                self.pl.remove(bcard)
                queue.append(bcard)

            d, p = divmod(idx, self.P)
            if self.occ.fits(card, fp) and self.dr.hard_ok(card, d, p):
                self.occ.place(card, idx, fp)
                self.dr.apply(card, d, p)
                self._tabu_push((card.cid, idx))
                self.forced += 1
            else:
                queue.append(card)

            if len(queue) < best_missing:
                best_missing = len(queue)
                best_state = self._snapshot()
                best_queue = list(queue)
                stall = 0
            else:
                stall += 1

        if len(queue) > best_missing:
            self._restore(best_state)
            return list(best_queue)
        return list(queue)
