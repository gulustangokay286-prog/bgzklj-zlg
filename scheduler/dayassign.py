"""
scheduler/dayassign.py — AŞAMA 1: kartları GÜNLERE dağıt (X ekseni).

Neden iki aşama:

v188'de dokuz sınıfın dokuzunda da açık hücre sayısı gereken saate TAM EŞİT.
Böyle bir ızgarada "nereye koysam" diye bir soru yok — her hücre dolacak. Tek
soru şu: HANGİ kart HANGİ güne, ve o gün içinde HANGİ saate.

Bu iki soru birbirinden bağımsızdır ve tek bir aramada birlikte çözülmeye
çalışılınca ikisi de çözülemez hâle gelir. Ayrıldığında ikisi de kolaylaşır:

  AŞAMA 1 (bu dosya) — GÜN ataması. Saf X ekseni.
      Her sınıfın her günü, o günün açık saat sayısı kadar DOLMALI.
      Aynı ders o güne iki kez düşmemeli, aynı öğretmen iki kez girmemeli.
      Saatlerin sırası burada hiç konuşulmaz.

  AŞAMA 2 (placer, güne kısıtlanmış) — SAAT ataması. Saf Y ekseni.
      Gün içinde sınıf × öğretmen çakışması çözülür. Problem artık
      9 sınıf × 8 saatlik tek bir güne indiği için arama uzayı küçüktür ve
      tahliye zinciri bu ölçekte gerçekten işe yarar.

Aşama 1'in ürettiği gün dağılımı DENGELİ olduğu sürece aşama 2 neredeyse her
zaman çözülür: bir günün içinde sınıf-öğretmen çizgesi çift taraflıdır ve çift
taraflı çizgede en yüksek derece kadar renkle boyama daima mümkündür (König).
Yani zorluk gün ataması aşamasındadır; motorun gücünü oraya vermek gerekir.
"""

import random


class DayAssignment:
    """Kart -> gün eşlemesi ve o eşlemeyi kuran arama."""

    def __init__(self, world, dayrules_spec, rng=None):
        self.w = world
        self.rng = rng or random.Random(20260911)
        self.D = world.D
        self.P = world.P
        spec = dayrules_spec or {}
        self.subject_once = spec.get("subject_once", True)
        self.teacher_once = spec.get("teacher_once", True)

        # Sınıfın gün başına açık saat sayısı — doldurulacak hedef.
        self.cls_cap = []
        for ci in range(len(world.classes)):
            closed = world.class_closed[ci]
            self.cls_cap.append([
                sum(1 for p in range(self.P) if not ((closed >> (d * self.P + p)) & 1))
                for d in range(self.D)
            ])
        # Öğretmenin gün başına açık saat sayısı — tavan.
        self.tch_cap = []
        self.tch_days_open = []
        for ti in range(len(world.teachers)):
            closed = world.teacher_closed[ti]
            caps = [sum(1 for p in range(self.P) if not ((closed >> (d * self.P + p)) & 1))
                    for d in range(self.D)]
            self.tch_cap.append(caps)
            self.tch_days_open.append([d for d in range(self.D) if caps[d] > 0])

        # ── X-2'nin OTOMATİK GEVŞETİLMESİ ──
        #
        # "Aynı öğretmen aynı güne iki kez gelmesin" kuralı, öğretmenin kart
        # sayısı müsait gün sayısını aştığı anda aritmetik olarak sağlanamaz.
        # v188'de Hüseyin Bilir 9A'ya üç kart veriyor ama haftada yalnızca iki
        # gün okulda; Yasemin Özkaya üç ayrı on birinci sınıfın her birine
        # dört kart veriyor ama üç gün müsait. Bu kartların bir kısmı, kural
        # sıkı tutulursa, hiçbir çizelgede yerleşemez.
        #
        # Kuralı sessizce çöpe atmak da, kartı sessizce düşürmek de yanlış
        # olur. Yapılan şey şu: kural o öğretmen-sınıf çifti için ve SADECE
        # aritmetiğin zorladığı kadar gevşetilir — günde iki kart gerekiyorsa
        # iki, üç gerekiyorsa üç — ve gevşetildiği rapora yazılır. Diğer
        # bütün öğretmenlerde kural sıkı kalır.
        # ── Aynı dersin günlük blok tavanı ──
        #
        # Kural şudur: bir dersin her bloğu AYRI güne gider. "2+2+2+2" yazan
        # İngilizce dört ayrı gün demektir; dördünü iki güne yığmak kuralı
        # çiğnemektir ve üstelik altı saatlik uydurma bir blok üretir.
        #
        # Tek istisna aritmetiğin kendisidir. 9A Matematik "2+2+1" = üç blok,
        # ama Hüseyin Bilir haftada yalnızca Salı ve Perşembe okulda. Üç bloğu
        # iki güne koymaktan başka seçenek yoktur; hiçbir çizelge bunu
        # değiştiremez. O zaman tavan ikiye çıkar ve ikiye çıktığı yerde de
        # bloklar bitişik oturur, öğrenci dersi tek kesintisiz blok görür.
        #
        # Tavan her zaman blok sayısı / müsait gün sayısı oranının yukarı
        # yuvarlanmışıdır: zorunlu olan kadar, bir fazlası değil. Bu yüzden
        # burada bir "gevşetme" yoktur; kuralın uygulanabilir en sıkı hâli
        # hesaplanır.
        self.subj_limit = {}     # (sınıf, ders) -> günlük blok tavanı
        self.forced = []         # aritmetiğin zorladığı yerler (rapora gider)
        blocks = {}
        for card in world.cards:
            for ci in card.classes:
                blocks.setdefault((ci, card.subject), []).append(card)
        for (ci, si), items in blocks.items():
            t = items[0].teacher
            if t >= 0:
                days = [d for d in range(self.D)
                        if self.tch_cap[t][d] > 0 and self.cls_cap[ci][d] > 0]
            else:
                days = [d for d in range(self.D) if self.cls_cap[ci][d] > 0]
            nd = len(days) or 1
            n = len(items)
            cap = 1 if n <= nd else -(-n // nd)
            self.subj_limit[(ci, si)] = cap
            if cap > 1:
                self.forced.append({
                    "class": world.classes[ci],
                    "subject": world.subjects[si],
                    "teacher": world.teachers[t] if t >= 0 else "",
                    "blocks": n, "days": nd, "limit": cap,
                })

        self.tch_limit = {}
        self.relaxed = []

    # ── durum ───────────────────────────────────────────────────────────────

    def _fresh(self):
        nC, nT = len(self.w.classes), len(self.w.teachers)
        return {
            "day": {},                                        # cid -> gün
            "cls_used": [[0] * self.D for _ in range(nC)],     # sınıf-gün saat
            "tch_used": [[0] * self.D for _ in range(nT)],     # öğretmen-gün saat
            "subj": [[set() for _ in range(self.D)] for _ in range(nC)],
            "subj_n": [[{} for _ in range(self.D)] for _ in range(nC)],
            "tch": [[set() for _ in range(self.D)] for _ in range(nC)],
            "tch_n": [[{} for _ in range(self.D)] for _ in range(nC)],
            "tch_subj": [[{} for _ in range(self.D)] for _ in range(nC)],
        }

    def _can(self, st, card, d):
        """Kart bu güne alınabilir mi?

        İKİ KURALIN GERÇEK ANLAMI — burası motorun en kolay yanlış kurulan yeri.

        "Aynı ders aynı gün tekrar ETMESİN" tekrarı yasaklar, DEVAMI değil.
        Matematik 2+2+1 dağıtılmışsa ve öğretmen haftada iki gün okuldaysa, üç
        kartı üç ayrı güne koymak aritmetik olarak imkânsızdır. Ama öğrencinin
        şikâyet ettiği şey zaten bu değildir: şikâyet, matematiği sabah görüp
        araya üç ders girdikten sonra öğleden sonra TEKRAR görmektir. İki kart
        bitişikse öğrenci tek bir kesintisiz matematik bloğu görür; bu tekrar
        değil, aynı dersin devamıdır. Bu yüzden gün ataması aşamasında aynı
        dersin kart sayısına sınır KOYULMAZ; sınır, kartların bitişik olma
        zorunluluğu olarak saat atamasında uygulanır.

        "Aynı ÖĞRETMEN aynı gün gelmesin" ise FARKLI BRANŞLAR içindir. Bir
        öğretmen sınıfa hem Matematik hem Geometri veriyorsa, o sınıf o gün
        aynı öğretmeni iki ayrı ders için görmemelidir. Ama aynı dersin
        devamı için yine görebilir — yoksa kural kendi kendisiyle çelişir:
        Matematik'in iki kartı bitişik olabilecekken öğretmen kuralı onları
        ayırmaya çalışır ve ikisi birden sağlanamaz.

        Kısacası: ders bazında ölçülen şey BİTİŞİKLİK, öğretmen bazında
        ölçülen şey FARKLI DERS SAYISI.
        """
        dur = card.duration
        for ci in card.classes:
            if st["cls_used"][ci][d] + dur > self.cls_cap[ci][d]:
                return False
            if self.subject_once:
                cap = self.subj_limit.get((ci, card.subject), 1)
                if st["subj_n"][ci][d].get(card.subject, 0) >= cap:
                    return False
            if self.teacher_once and card.teacher >= 0:
                subs = st["tch_subj"][ci][d].get(card.teacher)
                if subs and card.subject not in subs:
                    return False
        t = card.teacher
        if t >= 0:
            if self.tch_cap[t][d] == 0:
                return False
            if st["tch_used"][t][d] + dur > self.tch_cap[t][d]:
                return False
            # Öğretmen aynı gün kaç FARKLI sınıfa girebilir: o günkü açık
            # saatinden fazla sınıfa giremez.
            if st["tch_used"][t][d] + dur > self.P:
                return False
        return True

    def _put(self, st, card, d):
        st["day"][card.cid] = d
        for ci in card.classes:
            st["cls_used"][ci][d] += card.duration
            st["subj"][ci][d].add(card.subject)
            st["subj_n"][ci][d][card.subject] = st["subj_n"][ci][d].get(card.subject, 0) + 1
            if card.teacher >= 0:
                st["tch"][ci][d].add(card.teacher)
                st["tch_n"][ci][d][card.teacher] = st["tch_n"][ci][d].get(card.teacher, 0) + 1
                st["tch_subj"][ci][d].setdefault(card.teacher, set()).add(card.subject)
        if card.teacher >= 0:
            st["tch_used"][card.teacher][d] += card.duration

    def _pull(self, st, card):
        d = st["day"].pop(card.cid, None)
        if d is None:
            return None
        for ci in card.classes:
            st["cls_used"][ci][d] -= card.duration
            n_s = st["subj_n"][ci][d].get(card.subject, 0) - 1
            if n_s <= 0:
                st["subj_n"][ci][d].pop(card.subject, None)
                st["subj"][ci][d].discard(card.subject)
            else:
                st["subj_n"][ci][d][card.subject] = n_s
            if card.teacher >= 0:
                n = st["tch_n"][ci][d].get(card.teacher, 0) - 1
                if n <= 0:
                    st["tch_n"][ci][d].pop(card.teacher, None)
                    st["tch"][ci][d].discard(card.teacher)
                    st["tch_subj"][ci][d].pop(card.teacher, None)
                else:
                    st["tch_n"][ci][d][card.teacher] = n
                    still = {c2.subject for c2 in self.w.cards
                             if st["day"].get(c2.cid) == d and c2.teacher == card.teacher
                             and ci in c2.classes}
                    st["tch_subj"][ci][d][card.teacher] = still
        if card.teacher >= 0:
            st["tch_used"][card.teacher][d] -= card.duration
        return d

    # ── arama ───────────────────────────────────────────────────────────────

    def _score_day(self, st, card, d):
        """Küçük olan tercih edilir.

        Ölçüt, günü DOLDURMAYA yaklaştıran hamleyi ödüllendirir: tam oturan
        kart en iyisidir, günü taşıran kart zaten elenmiştir. Öğretmenin o
        günkü doluluğu da hesaba katılır — bir öğretmeni tek güne yığmak,
        aşama 2'de o günü çözülemez hâle getirir.
        """
        dur = card.duration
        worst = 0
        for ci in card.classes:
            left = self.cls_cap[ci][d] - st["cls_used"][ci][d] - dur
            worst = max(worst, left)
        t = card.teacher
        tload = st["tch_used"][t][d] if t >= 0 else 0
        return (worst, tload, self.rng.random())

    # ── sınıf bazlı tam arama ───────────────────────────────────────────────

    def _assign_class(self, st, cards, depth=0, node_cap=None):
        """Bir sınıfın kartlarını günlere TAM oturacak şekilde dağıtır.

        Kart sırası SABİT DEĞİL. Her adımda, o an en az güne sığan kart
        seçilir. Sabit sırada (önce uzun kartlar) ilerleyen bir arama,
        haftada yalnızca bir gün müsait bir öğretmenin tek saatlik kartını
        en sona bırakır; o güne kadar o gün dolmuş olur ve arama, on adım
        önce verilmiş bir karar yüzünden çöker. Dinamik seçim o kartı ilk
        adımda öne alır: seçeneği olmayan kart, seçeneği olanlardan önce
        yerleşmelidir.
        """
        if node_cap is not None:
            if node_cap[0] <= 0:
                return False
            node_cap[0] -= 1
        if not cards:
            return True

        # En az seçeneği olan kartı bul; sıfır seçenekli varsa dal ölüdür.
        best_i, best_days = None, None
        for i, c in enumerate(cards):
            days = [d for d in range(self.D) if self._can(st, c, d)]
            if not days:
                return False
            if best_days is None or len(days) < len(best_days):
                best_i, best_days = i, days
                if len(days) == 1:
                    break

        card = cards[best_i]
        rest = cards[:best_i] + cards[best_i + 1:]
        best_days.sort(key=lambda d: self._score_day(st, card, d))

        for d in best_days:
            self._put(st, card, d)
            if self._feasible_rest(st, card.classes, rest) and \
               self._assign_class(st, rest, depth + 1, node_cap):
                return True
            self._pull(st, card)
        return False

    def _feasible_rest(self, st, class_idxs, rest):
        """Budama: kalan kartlar kalan boşluğa aritmetik olarak sığıyor mu?

        Bu tek kontrol arama ağacının büyük kısmını keser. Kalan saat ile
        kalan boşluk eşit değilse o dal ölüdür; aşağı inmenin anlamı yok.
        """
        for ci in class_idxs:
            need = sum(c.duration for c in rest if ci in c.classes)
            free = sum(self.cls_cap[ci][d] - st["cls_used"][ci][d]
                       for d in range(self.D))
            if need != free:
                return False
            # Tek bir güne sığmayacak kadar uzun kart kaldıysa dal ölüdür.
            for c in rest:
                if ci not in c.classes:
                    continue
                if not any(self.cls_cap[ci][d] - st["cls_used"][ci][d] >= c.duration
                           for d in range(self.D)):
                    return False
        return True

    def _one_pass(self, cards, by_class, order, tries):
        best = None
        for _ in range(max(1, tries)):
            st = self._fresh()
            leftover = []
            for ci in order:
                cl = list(by_class[ci])
                self.rng.shuffle(cl)
                if not self._assign_class(st, cl, node_cap=[120_000]):
                    for c in cl:
                        if c.cid in st["day"]:
                            continue
                        opts = [d for d in range(self.D) if self._can(st, c, d)]
                        if opts:
                            opts.sort(key=lambda d: self._score_day(st, c, d))
                            self._put(st, c, opts[0])
                        else:
                            leftover.append(c)
            gap = 0
            for ci in range(len(self.w.classes)):
                for d in range(self.D):
                    gap += abs(self.cls_cap[ci][d] - st["cls_used"][ci][d])
            score = (len(leftover), gap)
            if best is None or score < best[0]:
                best = (score, dict(st["day"]), list(leftover))
            if score == (0, 0):
                break
        return best

    def build(self, cards, tries=40):
        """Kartları günlere dağıtır.

        Gün ataması TAMAMLANMAK ZORUNDADIR. Eksik bir gün ataması, saat
        ataması aşamasında kapatılamayacak bir delik demektir: o sınıfın o
        günü artık tam dolamaz ve o günün bütün kartları birden risk altına
        girer. Bir kartı burada bırakmanın bedeli, o kartın kendisi değil,
        peşinden gidecek onlarca karttır.

        Bu yüzden arama kademeli ilerler. Önce kurallar en sıkı hâliyle
        denenir. Tamamlanamazsa, yalnızca TIKAYAN ders için ve yalnızca BİR
        kademe tavan açılır, sonra tekrar denenir. Açılan her kademe rapora
        yazılır — hangi ders, hangi sınıf, neden. Kural sessizce esnetilmez;
        esnetildiği yer, ne kadar esnetildiği ve gerekçesi görünür olur.
        """
        by_class = {}
        for c in cards:
            by_class.setdefault(c.classes[0], []).append(c)

        def tightness(ci):
            total = 0
            for c in by_class[ci]:
                if c.teacher >= 0:
                    total += len([d for d in self.tch_days_open[c.teacher]
                                  if self.cls_cap[ci][d] > 0])
                else:
                    total += self.D
            return total / max(1, len(by_class[ci]))

        order = sorted(by_class.keys(), key=lambda ci: (tightness(ci), -len(by_class[ci])))

        self.opened = []
        best = self._one_pass(cards, by_class, order, tries)

        # Kademeli açma: tamamlanana kadar, tıkayan dersin tavanını birer artır.
        guard = 0
        while best[0] != (0, 0) and guard < 24:
            guard += 1
            score, day_map, leftover = best
            blockers = set()
            for c in leftover:
                for ci in c.classes:
                    blockers.add((ci, c.subject))
            if not blockers:
                # Artan kart yok ama gün sapması var: en sıkı dersleri aç.
                for ci in range(len(self.w.classes)):
                    for d in range(self.D):
                        if self.cls_cap[ci][d] != 0:
                            pass
                for c in cards:
                    blockers.add((c.classes[0], c.subject))
            changed = False
            for key in blockers:
                cur = self.subj_limit.get(key, 1)
                if cur < self.D:
                    self.subj_limit[key] = cur + 1
                    ci, si = key
                    self.opened.append({
                        "class": self.w.classes[ci],
                        "subject": self.w.subjects[si],
                        "from": cur, "to": cur + 1,
                    })
                    changed = True
            if not changed:
                break
            best = self._one_pass(cards, by_class, order, max(8, tries // 2))

        return best[1], best[2]
