"""
scheduler/placer.py — yerleştirici: sıralama + tahliye zinciri + yeniden başlatma.

Motorun kalbi. CP-SAT'ın yaptığı gibi "bütün ihtimalleri tarayıp optimali
KANITLAMAYA" çalışmaz. Kanıtlama, problemin zor yarısıdır ve kimse istemiyor:
istenen şey %100 dolu, çakışmasız, kurallara uyan bir çizelge — matematiksel
olarak en iyisi olduğu ispatlanmış bir çizelge değil.

Üç mekanizma üzerine kurulu:

  1. EN ZOR KART ÖNCE (most-constrained-first)
     Kolay kartları önce yerleştirmek, zor kartlara yer bırakmaz. Bu sıralama
     tek başına çözüm süresini kat kat etkiler.

  2. TAHLİYE ZİNCİRİ (ejection chain)
     Kart yerleşemiyorsa PES ETMEZ, YER AÇAR: hücreyi tutan kartları geçici
     olarak çıkarır, kartı koyar, çıkardıklarını özyinelemeli olarak yeniden
     yerleştirir. Olmazsa hepsini geri alır. "Dolu bir çizelgeye tek kart
     sokma" probleminin doğru çözümü budur.

  3. YENİDEN BAŞLATMA
     Zincir de yetmezse farklı bir rastgele tohumla baştan. Her denemede
     sıralama biraz değişir; takılınan yerel tıkanıklık dağılır.

Bu üçlü, aSc TimeTables'ın gözlenen davranışını üreten klasik yapıdır ve
repoda zaten yazılmış olan chain_scheduler.py'nin mantığını sürdürür.
"""

import random
import time


class Placer:
    def __init__(self, world, occ, dayrules, rng=None, chain_depth=12,
                 chain_width=8):
        self.w = world
        self.occ = occ
        self.dr = dayrules
        self.rng = rng or random.Random(20260911)
        self.chain_depth = chain_depth
        self.chain_width = chain_width
        self.P = world.P
        self.steps = 0
        self.chain_calls = 0

    # ── aday üretimi ────────────────────────────────────────────────────────

    def candidates(self, card, scored=True):
        """Kartın şu an geçerli olan yerleri; en iyiden kötüye sıralı.

        Sıra: Y filtresi (en ucuz, en çok eler) → X sert filtresi → puanlama.
        Y'yi X'ten önce çalıştırmak bilinçli: Y mutlaktır ve daha çok eler.
        """
        occ, dr = self.occ, self.dr
        blocked = occ.blocked_mask(card)
        out = []
        for idx, fp in card.slots:
            if fp & blocked:
                continue
            d, p = divmod(idx, self.P)
            if not dr.hard_ok(card, d, p):
                continue
            if scored:
                cost = dr.penalty(card, d, p) + dr.shape_penalty(card, d, p, occ)
                out.append((cost, idx, fp))
            else:
                out.append((0, idx, fp))
        if scored:
            self.rng.shuffle(out)
            out.sort(key=lambda x: x[0])
        else:
            self.rng.shuffle(out)
        return out

    def _free_count(self, card, cap=4):
        """Kartın kaç geçerli yeri kaldı — sıralama ölçüsü.

        cap'e ulaşınca sayım durur. MRV için 0 / 1 / 2 / 3 / "bol" ayrımı
        yeterlidir; 37 ile 38 arasındaki farkı öğrenmek için bütün ızgarayı
        taramak, her adımda her kart için yapılan bir israftır.

        Ucuz Y maskesi önce uygulanır; pahalı X kontrolü sadece Y'yi geçen
        hücreler için çalışır.
        """
        blocked = self.occ.blocked_mask(card)
        n = 0
        for idx, fp in card.slots:
            if fp & blocked:
                continue
            d, p = divmod(idx, self.P)
            if self.dr.hard_ok(card, d, p):
                n += 1
                if n >= cap:
                    return n
        return n

    # ── sıralama ────────────────────────────────────────────────────────────

    def order(self, cards):
        """En zor kart önce.

        Ölçüt sırası:
          * aday yeri az olan (en kısıtlı)
          * süresi uzun olan (2 saatlik blok 1 saatlikten zor yerleşir)
          * birleşik kart (birden fazla sınıfı aynı anda tutar)
          * öğretmeni dar olan (açık saati az)
        """
        w = self.w
        def key(c):
            tfree = (bin(~w.teacher_closed[c.teacher] & ((1 << (w.D * w.P)) - 1)).count("1")
                     if c.teacher >= 0 else w.D * w.P)
            return (len(c.slots), -c.duration, -len(c.classes), tfree,
                    self.rng.random())
        return sorted(cards, key=key)

    # ── tek kart yerleştirme ────────────────────────────────────────────────

    def try_place(self, card) -> bool:
        cands = self.candidates(card)
        if not cands:
            return False
        cost, idx, fp = cands[0]
        d, p = divmod(idx, self.P)
        self.occ.place(card, idx, fp)
        self.dr.apply(card, d, p)
        self.steps += 1
        return True

    def remove(self, card):
        idx = self.occ.unplace(card)
        if idx is not None:
            d, p = divmod(idx, self.P)
            self.dr.revert(card, d, p)
        return idx

    # ── tahliye zinciri ─────────────────────────────────────────────────────

    def _capture(self):
        """Çizelgenin tam hâli. Zincir geri sarılırken tek doğru kaynak budur."""
        return dict(self.occ.placed)

    def _rollback(self, snap):
        """Çizelgeyi verilen hâle BİREBİR geri döndürür.

        Zincirin en sinsi hatası buradaydı: özyineleme derinlere indikçe her
        seviye kendi tahliye ettiklerini biliyordu ama ALT seviyelerin
        tahliye ettiklerini bilmiyordu. Başarısız bir dal geri sarılırken
        sadece o seviyenin söktükleri geri konuyor, alt seviyelerde sökülüp
        bir daha yerleştirilemeyen kartlar ızgaradan sessizce düşüyordu.

        Üstelik bu kayıp hiçbir yere rapor edilmiyordu: o kartlar çoktan
        yerleşmiş sayıldığı için bekleyenler listesinde de değillerdi.
        Motor "hepsini yerleştirdim" diyor, ızgarada otuz beş kartın otuz
        biri bulunuyordu.

        Çözüm, seviye seviye geri alma yerine tam anlık görüntüdür: dal
        başarısızsa çizelge, dala girmeden önceki hâline döner. Kart sayısı
        birkaç yüz olduğu için kopyalamanın maliyeti önemsizdir; sessiz kayıp
        ise her zaman pahalıdır.
        """
        for cid in list(self.occ.placed.keys()):
            if cid not in snap or self.occ.placed[cid] != snap[cid]:
                self.remove(self.w.cards[cid])
        for cid, (idx, fp) in snap.items():
            if self.occ.is_placed(cid):
                continue
            card = self.w.cards[cid]
            if self.occ.fits(card, fp):
                self.occ.place(card, idx, fp)
                d, p = divmod(idx, self.P)
                self.dr.apply(card, d, p)

    def place_with_chain(self, card, depth=0, banned=None) -> bool:
        """Yer yoksa yer AÇ.

        banned: bu zincir dalında dokunulmayacak kartlar. Olmadan zincir
        kendi az önce taşıdığı kartı tekrar taşımaya kalkar ve döner durur.
        """
        if self.try_place(card):
            return True
        if depth >= self.chain_depth:
            return False

        self.chain_calls += 1
        banned = banned or set()
        occ, dr = self.occ, self.dr

        # Y'yi ihlal eden ama X'i geçen yerleri, engelleyen kart sayısına göre dene.
        options = []
        for idx, fp in card.slots:
            d, p = divmod(idx, self.P)
            if not dr.hard_ok(card, d, p):
                continue
            blockers = occ.blockers(card, fp)
            if blockers is None:      # kapalı hücre — tahliye edilemez
                continue
            if not blockers:
                continue              # try_place zaten denedi
            if blockers & banned:
                continue
            if len(blockers) > self.chain_width:
                continue
            options.append((len(blockers), dr.penalty(card, d, p), idx, fp, blockers))
        if not options:
            return False
        self.rng.shuffle(options)
        options.sort(key=lambda x: (x[0], x[1]))

        for _, _, idx, fp, blockers in options[:self.chain_width]:
            snap = self._capture()
            evicted = [self.w.cards[bid] for bid in blockers]
            for bcard in evicted:
                self.remove(bcard)

            d, p = divmod(idx, self.P)
            if occ.fits(card, fp) and dr.hard_ok(card, d, p):
                occ.place(card, idx, fp)
                dr.apply(card, d, p)
                nb = banned | {card.cid} | {b.cid for b in evicted}
                ok = True
                for bcard in evicted:
                    if not self.place_with_chain(bcard, depth + 1, nb):
                        ok = False
                        break
                if ok:
                    return True
            self._rollback(snap)
        return False

    # ── tam çalıştırma ──────────────────────────────────────────────────────

    def _place_locked(self, cards):
        for c in cards:
            if c.locked_at is None:
                continue
            d, p = divmod(c.locked_at, self.P)
            fp = self.w.footprint(d, p, c.duration)
            if self.occ.fits(c, fp):
                self.occ.place(c, c.locked_at, fp)
                self.dr.apply(c, d, p)

    def run(self, cards, deadline=None):
        """Bütün kartları yerleştirmeyi dener; yerleşemeyenleri döner.

        Sıralama STATİK DEĞİL. Her adımda o an en az yeri kalan kart seçilir
        (dynamic most-constrained-first). Statik sıralama, çizelge doldukça
        hangi kartın sıkıştığını göremez: baştaki kolay bir kart, ortada
        kilitlenen bir kartın tek yerini kapatmış olabilir ve bunu kimse fark
        etmez. Dinamik seçim, sıkışan kartı sıkıştığı anda öne alır.

        Tek yeri kalan kartlar (naked single) sorgusuz ve hemen yerleşir —
        seçim yoksa geciktirmenin faydası yok, zararı var.
        """
        self._place_locked(cards)
        pending = [c for c in cards if c.locked_at is None and not self.occ.is_placed(c.cid)]
        failed = []

        while pending:
            if deadline and time.time() > deadline:
                failed.extend(pending)
                break

            # UZUN KART ÖNCE. Bu sıralama pazarlık konusu değil.
            #
            # Sınıfların açık hücre sayısı gereken saate TAM EŞİT olduğunda
            # (v188'de dokuz sınıfın dokuzu da öyle) ızgarada tek bir boş
            # hücre bile artmaz. Böyle bir ızgarada 1 saatlik kartı erken
            # yerleştirmek tek sayılı delikler açar ve 2 saatlik kart o
            # deliklere ASLA giremez — çizelge, yer olmadığı için değil, yer
            # yanlış şekle girdiği için tamamlanamaz.
            #
            # Bu yüzden önce en uzun kartlar yerleşir; kısa kartlar sona
            # kalan tek hücreleri doldurur. En kısıtlı kart seçimi (MRV)
            # yalnızca aynı uzunluktaki kartlar arasında yapılır.
            longest = max(c.duration for c in pending)
            tier = [c for c in pending if c.duration == longest]

            counts = []
            forced = None
            for c in tier:
                n = self._free_count(c)
                if n == 1 and forced is None:
                    forced = c
                counts.append((n, c))

            if forced is not None:
                card = forced
            else:
                dead = [c for n, c in counts if n == 0]
                if dead:
                    # Yeri kalmayan kart: zincire ver, o da olmazsa bırak.
                    card = dead[0]
                else:
                    m = min(n for n, _ in counts)
                    tied = [c for n, c in counts if n == m]
                    tied.sort(key=lambda c: (-len(c.classes), len(c.slots), c.cid))
                    card = tied[0]

            pending.remove(card)
            if not self.place_with_chain(card):
                failed.append(card)

        # Izgaradan DOĞRULA. Zincirin bir dalı geri sarılırken daha önce
        # yerleşmiş bir kartı düşürmüş olabilir; o kart ne bekleyenler
        # listesinde ne de başarısızlar listesindedir. Motorun kendi
        # defterine değil çizelgenin kendisine bakmak, bu sessiz kaybı
        # görünür kılan tek kontroldür.
        known = {c.cid for c in failed}
        for c in cards:
            if c.locked_at is None and not self.occ.is_placed(c.cid) and c.cid not in known:
                failed.append(c)

        # Sonraki turlar: çizelge artık dolu, zincirin tahliye edecek malzemesi
        # var. Her turda zincir biraz daha derinleşir — ilk turda bulunamayan
        # yer, iki kart daha oynatılınca bulunabiliyor. Tur ilerleme
        # sağlamıyorsa durulur; aynı derinlikte tekrar denemek zaman israfı.
        round_no = 0
        while failed and round_no < 4 and (not deadline or time.time() < deadline):
            round_no += 1
            before = len(failed)
            retry, failed = failed, []
            retry.sort(key=lambda c: (len(c.slots), -c.duration))
            old_depth, old_width = self.chain_depth, self.chain_width
            self.chain_depth = min(20, old_depth + 4 * round_no)
            self.chain_width = min(16, old_width + 2 * round_no)
            for card in retry:
                if deadline and time.time() > deadline:
                    failed.append(card)
                    continue
                if not self.place_with_chain(card):
                    failed.append(card)
            self.chain_depth, self.chain_width = old_depth, old_width
            if len(failed) >= before:
                break
        return failed
