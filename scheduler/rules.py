"""
scheduler/rules.py — Planlama İlişkileri ekranı ile motor arasındaki SÖZLEŞME.

Ekrandaki ham sözlük burada tipli, çözümlenmiş, doğrulanmış bir Rule nesnesine
çevrilir. Motorun geri kalanı "kural" kelimesini sadece bu tip üzerinden görür.

Neden ayrı bir katman:

Eski motorda kural metni doğrudan çözücünün içinde string karşılaştırmasıyla
aranıyordu ("aynı gün tekrar etmesin" in r_type). Bir kural adı değiştiğinde,
bir filtre eşleşmediğinde ya da bir kural yanlış faza düştüğünde HİÇBİR UYARI
çıkmıyor, kural sessizce yok oluyordu. Sessiz kayıp, bu motorun en pahalı
hatasıydı: kullanıcı kuralı açıyor, kaydediyor, çizelge kuralsız çıkıyor ve
hiçbir yerde "bu kural uygulanmadı" yazmıyordu.

Burada her kural derlenirken doğrulanır. Çözülemeyen bir ad, imkânsız bir
parametre, eksik bir seçim ANINDA rapora yazılır. Kural ya uygulanır ya da
neden uygulanmadığı söylenir. Üçüncü ihtimal yoktur.
"""

from dataclasses import dataclass, field
from .model import norm_key, norm_class

# ── Eksen ───────────────────────────────────────────────────────────────────
X = "X"   # gün ekseni  — sayma: "bu sınıfın bu gününde bundan kaç tane var?"
Y = "Y"   # saat ekseni — çakışma: "bu hücrede bu kaynak dolu mu?"

# ── Sertlik ─────────────────────────────────────────────────────────────────
# Y ekseni her zaman HARD'dır; sertlik sadece X ekseni için anlamlıdır.
HARD = 3      # yerleştirmede ELER. İhlal edilemez.
HIGH = 2      # ceza 10_000
NORMAL = 1    # ceza 1_000
LOW = 0       # ceza 100

PENALTY = {HIGH: 10_000, NORMAL: 1_000, LOW: 100}

_ONEM_MAP = {
    "sikikesinlikleuygulanmali": HARD,
    "siki": HARD,
    "yuksek": HIGH,
    "normal": NORMAL,
    "dusukmumkunse": LOW,
    "dusuk": LOW,
}

# ── Kural tipleri ───────────────────────────────────────────────────────────
# X ekseni — SAYMA kuralları (sınıf + gün kapsamında)
X_SUBJECT_ONCE_DAY      = "X_SUBJECT_ONCE_DAY"       # aynı ders aynı güne 1 seans
X_TEACHER_ONCE_DAY      = "X_TEACHER_ONCE_DAY"       # aynı öğretmen aynı güne 1 seans
X_SUBJECT_MAX_HOURS     = "X_SUBJECT_MAX_HOURS"      # ders günde en fazla N saat
X_SUBJECT_MAX_SESSIONS  = "X_SUBJECT_MAX_SESSIONS"   # ders günde en fazla N seans
X_PRACTICAL_MAX_HOURS   = "X_PRACTICAL_MAX_HOURS"    # uygulamalı ders günde N saat
X_PAIR_NOT_SAME_DAY     = "X_PAIR_NOT_SAME_DAY"      # şu dersler aynı güne gelmesin
X_CLASS_MAX_HOURS       = "X_CLASS_MAX_HOURS"        # sınıf günde en fazla N saat
X_TEACHER_MAX_HOURS     = "X_TEACHER_MAX_HOURS"      # öğretmen günde en fazla N saat
X_TEACHER_MAX_DAYS      = "X_TEACHER_MAX_DAYS"       # öğretmen haftada en fazla N gün
X_MIN_DAYS_BETWEEN      = "X_MIN_DAYS_BETWEEN"       # aynı dersin kartları arası N gün
# X ekseni — SIRALAMA kuralları (gün içi konum)
X_EVEN_SPREAD           = "X_EVEN_SPREAD"            # günlere eşit yay
X_SAME_DAY_ADJACENT     = "X_SAME_DAY_ADJACENT"      # aynı güne düşerse bitişik olsun
X_HARD_NOT_ADJACENT     = "X_HARD_NOT_ADJACENT"      # iki zor ders art arda gelmesin
X_NO_CLASS_GAP          = "X_NO_CLASS_GAP"           # sınıfta boş saat kalmasın
X_NO_TEACHER_GAP        = "X_NO_TEACHER_GAP"         # öğretmende boş saat kalmasın
X_TEACHER_MAX_RUN       = "X_TEACHER_MAX_RUN"        # öğretmen art arda en fazla N saat
# X ekseni — PENCERE kuralları (kart domaini daraltır, kurulumda uygulanır)
X_TIME_WINDOW           = "X_TIME_WINDOW"            # şu saatler arasında kalmalı
X_MORNING_ONLY          = "X_MORNING_ONLY"           # öğleden önce
X_AFTERNOON_ONLY        = "X_AFTERNOON_ONLY"         # öğleden sonra
X_NOT_LAST_PERIOD       = "X_NOT_LAST_PERIOD"        # son saate konmasın
X_NOT_FIRST_PERIOD      = "X_NOT_FIRST_PERIOD"       # ilk saate konmasın

# Y ekseni — ÇAKIŞMA kuralları (her zaman HARD, kapatılamaz)
Y_TEACHER_CLASH         = "Y_TEACHER_CLASH"          # öğretmen aynı anda tek yerde
Y_CLASS_CLASH           = "Y_CLASS_CLASH"            # sınıf aynı anda tek derste
Y_CLOSED_CELL           = "Y_CLOSED_CELL"            # kapalı hücreye konmaz
Y_CROSS_INSTITUTION     = "Y_CROSS_INSTITUTION"      # başka kurumda ders var
# Y ekseni — KAPASİTE kuralları (kullanıcı tanımlı)
Y_SUBJECT_MAX_PARALLEL  = "Y_SUBJECT_MAX_PARALLEL"   # aynı saatte bu dersten en fazla N sınıf
Y_TEACHER_MAX_PARALLEL  = "Y_TEACHER_MAX_PARALLEL"   # birleşik ders tavanı

# Pencere kuralları: kart kurulurken domaine işlenir, yerleştirmede bakılmaz.
WINDOW_RULES = {X_TIME_WINDOW, X_MORNING_ONLY, X_AFTERNOON_ONLY,
                X_NOT_LAST_PERIOD, X_NOT_FIRST_PERIOD}

# Sayma kuralları: gün sayaçları üzerinden O(1) kontrol edilir.
COUNT_RULES = {X_SUBJECT_ONCE_DAY, X_TEACHER_ONCE_DAY, X_SUBJECT_MAX_HOURS,
               X_SUBJECT_MAX_SESSIONS, X_PRACTICAL_MAX_HOURS, X_PAIR_NOT_SAME_DAY,
               X_CLASS_MAX_HOURS, X_TEACHER_MAX_HOURS, X_TEACHER_MAX_DAYS,
               X_MIN_DAYS_BETWEEN}

# Sıralama kuralları: yerleşim şekline bakar, sayaçla ölçülemez.
SHAPE_RULES = {X_EVEN_SPREAD, X_SAME_DAY_ADJACENT, X_HARD_NOT_ADJACENT,
               X_NO_CLASS_GAP, X_NO_TEACHER_GAP, X_TEACHER_MAX_RUN}


@dataclass
class Rule:
    kind: str
    axis: str
    hardness: int = HARD
    param: int = 0
    param2: int = 0
    subjects: frozenset = field(default_factory=frozenset)   # ders indeksleri
    teachers: frozenset = field(default_factory=frozenset)   # öğretmen indeksleri
    klasses: frozenset = field(default_factory=frozenset)    # sınıf indeksleri
    label: str = ""

    def is_hard(self) -> bool:
        return self.hardness >= HARD

    def penalty(self) -> int:
        return PENALTY.get(self.hardness, 0)

    def applies_class(self, c: int) -> bool:
        return (not self.klasses) or (c in self.klasses)

    def applies_subject(self, s: int) -> bool:
        return (not self.subjects) or (s in self.subjects)

    def applies_teacher(self, t: int) -> bool:
        return (not self.teachers) or (t in self.teachers)

    def applies_card(self, card) -> bool:
        if self.klasses and not any(c in self.klasses for c in card.classes):
            return False
        if self.subjects and card.subject not in self.subjects:
            return False
        if self.teachers and card.teacher not in self.teachers:
            return False
        return True

    def __repr__(self):
        h = {HARD: "SIKI", HIGH: "YÜKSEK", NORMAL: "NORMAL", LOW: "DÜŞÜK"}[self.hardness]
        return f"<{self.axis}·{self.kind} {h} p={self.param}>"


# ── Ekrandaki kural adları → motor kural tipi ───────────────────────────────
# Eşleştirme normalize edilmiş ad üzerinden yapılır; ekranda yazım değişse bile
# eşleşme bozulmaz. Eşleşmeyen ad SESSİZCE ATLANMAZ, rapora yazılır.

_UI_MAP = [
    # ── ekrandaki 11 kural ──
    ("gundemaksimumderssayisi",                 X_SUBJECT_MAX_HOURS),
    ("bedenegitimiuygulamalidersleragundeenfazla2saatolsun", X_PRACTICAL_MAX_HOURS),
    ("uygulamalidersler",                       X_PRACTICAL_MAX_HOURS),
    ("aynidersayniguntekraretmesin",            X_SUBJECT_ONCE_DAY),
    ("derslerhaftaningunlerineesitdagitilsin",  X_EVEN_SPREAD),
    ("secilendersleraynigunpespesegelsin",      X_SAME_DAY_ADJACENT),
    ("ikidersaynigunegelmesin",                 X_PAIR_NOT_SAME_DAY),
    ("ogretmenindersleriogledenoncetoplansin",  X_MORNING_ONLY),
    ("ogretmenindersleriogledensonratoplansin", X_AFTERNOON_ONLY),
    ("sonderssaatinezorderskonulmasin",         X_NOT_LAST_PERIOD),
    ("xdersibelirlisaatlerdekalmali",           X_TIME_WINDOW),
    ("ikizordersartardagelmesin",               X_HARD_NOT_ADJACENT),
    # ── genişletilmiş katalog (yeni kurallar) ──
    ("ayniogretmenayniguntekraretmesin",        X_TEACHER_ONCE_DAY),
    ("ayniogretmenaynigunegelmesin",            X_TEACHER_ONCE_DAY),
    ("dersgundeenfazlanseans",                  X_SUBJECT_MAX_SESSIONS),
    ("sinifgundeenfazlansaat",                  X_CLASS_MAX_HOURS),
    ("ogretmengundeenfazlansaat",               X_TEACHER_MAX_HOURS),
    ("ogretmenhaftadaenfazlangun",              X_TEACHER_MAX_DAYS),
    ("ayniderskartlariarasindaenaznguolsun",    X_MIN_DAYS_BETWEEN),
    ("ayniderskartlariarasindaenazngun",        X_MIN_DAYS_BETWEEN),
    ("siniftabossaatkalmasin",                  X_NO_CLASS_GAP),
    ("ogretmendebossaatkalmasin",               X_NO_TEACHER_GAP),
    ("ogretmenartardaenfazlansaat",             X_TEACHER_MAX_RUN),
    ("aynisaatteendersfazlansinifalabilir",     Y_SUBJECT_MAX_PARALLEL),
    ("aynisaatteenfazlansinif",                 Y_SUBJECT_MAX_PARALLEL),
    ("ilkderssaatinekonulmasin",                X_NOT_FIRST_PERIOD),
    # ── kısa takma adlar (son çare, en sonda) ──
    ("pespesegelsin",                           X_SAME_DAY_ADJACENT),
    ("esitdagitilsin",                          X_EVEN_SPREAD),
    ("ogledenoncetoplansin",                    X_MORNING_ONLY),
    ("ogledensonratoplansin",                   X_AFTERNOON_ONLY),
    ("belirlisaatlerdekalmali",                 X_TIME_WINDOW),
    ("zorderartarda",                           X_HARD_NOT_ADJACENT),
    ("zordersartarda",                          X_HARD_NOT_ADJACENT),
]

_AXIS = {k: (Y if k.startswith("Y_") else X)
         for _, k in _UI_MAP}

# Uygulamalı ders anahtar kelimeleri — TEK yerde tanımlı.
PRACTICAL_KEYWORDS = ("beden", "muzik", "gorsel", "resim", "sanat", "spor",
                      "uygulama", "atolye", "teknoloji", "tasarim")

# "Zor" ders anahtar kelimeleri — TEK yerde tanımlı.
HARD_KEYWORDS = ("mat", "fizik", "kimya", "biyo", "geometri", "fen", "geo")


def is_practical(name: str) -> bool:
    n = norm_key(name)
    return any(k in n for k in PRACTICAL_KEYWORDS)


def is_hard_subject(name: str) -> bool:
    n = norm_key(name)
    return any(k in n for k in HARD_KEYWORDS)


def _match_rule_name(key: str):
    """Ekrandaki kural adını motor tipine eşler.

    Önce birebir, sonra EN UZUN kapsayan desen kazanır. Kısa bir takma adın
    uzun ve daha kesin bir deseni gölgelemesi böyle engellenir; eşleşme
    sırasının tesadüfüne bırakılmaz.
    """
    if not key:
        return None
    for pat, k in _UI_MAP:
        if pat == key:
            return k
    best, best_len = None, 0
    for pat, k in _UI_MAP:
        if (pat in key or key in pat) and len(pat) > best_len:
            best, best_len = k, len(pat)
    return best


def _hardness_from(onem: str) -> int:
    k = norm_key(onem)
    for key, val in _ONEM_MAP.items():
        if k.startswith(key) or key in k:
            return val
    return HARD


def _resolve(names, lookup, kind, label, report):
    """Ad listesini indeks kümesine çevirir; eşleşmeyeni rapora yazar."""
    out = set()
    for raw in names or []:
        key = lookup["norm"](raw)
        idx = lookup["map"].get(key)
        if idx is None:
            # gevşek eşleşme: biri diğerini içeriyorsa
            cands = [i for k, i in lookup["map"].items() if key and (key in k or k in key)]
            if len(cands) == 1:
                idx = cands[0]
        if idx is None:
            msg = f"{label}: '{raw}' adında {kind} bulunamadı. Kuralın kapsamı çözülemedi."
            report.warn(msg)
            report.errors.append(msg)
        else:
            out.add(idx)
    return frozenset(out)


class RuleReport:
    """Derleme sırasında biriken uyarılar. Sessiz kayıp burada biter."""

    def __init__(self):
        self.warnings = []
        self.compiled = []
        self.skipped = []
        self.errors = []

    def warn(self, msg):
        self.warnings.append(msg)

    def skip(self, label, why):
        self.skipped.append((label, why))
        self.warnings.append(f"UYGULANMADI — {label}: {why}")

    def ok(self, label, rule):
        self.compiled.append((label, rule))


def compile_rules(raw_relations, world, defaults=True) -> tuple:
    """Ham planlama ilişkilerini Rule listesine derler.

    defaults=True yalnızca fiziksel çakışma kurallarını ekler.
    Planlama ilişkileri sadece ekranda etkinleştirilmişse uygulanır.

    Döner: (rules, report)
    """
    rep = RuleReport()
    rules = []

    sub_lookup = {"norm": norm_key,
                  "map": {norm_key(n): i for i, n in enumerate(world.subjects)}}
    tch_lookup = {"norm": norm_key,
                  "map": {norm_key(n): i for i, n in enumerate(world.teachers)}}
    cls_lookup = {"norm": norm_class,
                  "map": {norm_class(n): i for i, n in enumerate(world.classes)}}

    for raw in (raw_relations or []):
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("kural") or "?")
        if not raw.get("aktif", True):
            continue

        key = norm_key(label)
        kind = raw.get("kind") or _match_rule_name(key)
        if kind not in set(_AXIS):
            kind = None
        if kind is None:
            rep.skip(label, "bu kural adı motorda tanımlı değil")
            rep.errors.append(rep.warnings[-1])
            continue

        subs = _resolve(raw.get("dersler"), sub_lookup, "ders", label, rep)
        tchs = _resolve(raw.get("ogretmenler"), tch_lookup, "öğretmen", label, rep)
        klss = _resolve(raw.get("siniflar"), cls_lookup, "sınıf", label, rep)

        hardness = _hardness_from(raw.get("onem"))
        try:
            param = int(raw.get("parametre") or 0)
        except (ValueError, TypeError):
            rep.errors.append(f"{label}: geçersiz parametre")
            continue
        p_start = raw.get("period_start")
        p_end = raw.get("period_end")

        r = Rule(kind=kind, axis=_AXIS.get(kind, X), hardness=hardness,
                 param=param, subjects=subs, teachers=tchs, klasses=klss,
                 label=label)

        # ── kurala özgü doğrulama ──
        if kind == X_PAIR_NOT_SAME_DAY and len(subs) < 2:
            # "İki ders aynı güne gelmesin" ancak HANGİ iki ders olduğu
            # seçildiğinde bir anlam taşır. Ekran da bunu böyle kurar: ders
            # listesi boşsa kullanıcı henüz hiçbir şey seçmemiştir.
            #
            # Böyle bir kaydı başka bir kurala çevirmek — örneğin "aynı
            # öğretmen aynı gün gelmesin" gibi okumak — kullanıcının hiç
            # kurmadığı, çok daha sert bir kısıtı sessizce yürürlüğe sokar.
            # v188'de tam olarak bu oluyordu: seçimi boş bırakılmış tek bir
            # satır, bütün öğretmenleri kapsayan bir kurala dönüşüyor ve
            # çizelgeden saatler eksiltiyordu. Kullanıcı ne böyle bir kural
            # yazmıştı ne de ekranda öyle görüyordu.
            #
            # Doğrusu kuralı uygulamamak ve NEDEN uygulanmadığını söylemek:
            # eksik seçim ekranda düzeltilebilir, sessiz bir yeniden yorum
            # düzeltilemez.
            rep.skip(label, "en az iki ders seçilmeli; ders seçimi boş olduğu "
                            "için kural hiçbir şeyi kısıtlamıyor")
            continue

        if kind == X_TIME_WINDOW:
            if not p_start or not p_end:
                rep.errors.append(f"{label}: saat aralığı girilmemiş")
                continue
            r.param, r.param2 = int(p_start) - 1, int(p_end) - 1
            if r.param > r.param2:
                rep.errors.append(f"{label}: geçersiz aralık ({p_start}-{p_end})")
                continue

        if kind in (X_SUBJECT_MAX_HOURS, X_PRACTICAL_MAX_HOURS,
                    X_CLASS_MAX_HOURS, X_TEACHER_MAX_HOURS,
                    X_TEACHER_MAX_RUN, X_SUBJECT_MAX_SESSIONS):
            if r.param <= 0:
                r.param = 2
                rep.warn(f"{label}: parametre girilmemiş, 2 kabul edildi.")

        if kind == X_PRACTICAL_MAX_HOURS and not subs:
            subs = frozenset(i for i, n in enumerate(world.subjects) if is_practical(n))
            r.subjects = subs
            if not subs:
                rep.skip(label, "uygulamalı ders bulunamadı")
                continue

        if kind == X_HARD_NOT_ADJACENT and not subs:
            subs = frozenset(i for i, n in enumerate(world.subjects) if is_hard_subject(n))
            r.subjects = subs
            if not subs:
                rep.skip(label, "zor ders bulunamadı")
                continue

        if kind == X_NOT_LAST_PERIOD and not subs:
            subs = frozenset(i for i, n in enumerate(world.subjects) if is_hard_subject(n))
            r.subjects = subs

        rules.append(r)
        rep.ok(label, r)

    if defaults:
        have = {r.kind for r in rules}
        # Y ekseni: pazarlık yok, her zaman eklenir.
        for k in (Y_TEACHER_CLASH, Y_CLASS_CLASH, Y_CLOSED_CELL, Y_CROSS_INSTITUTION):
            rules.append(Rule(kind=k, axis=Y, hardness=HARD, label=f"[çekirdek] {k}"))

        # X ekseni kuralları BURAYA GÖMÜLMEZ.
        #
        # Bir ara "aynı ders aynı gün" ve "aynı öğretmen aynı gün" kuralları
        # motorun gizli varsayılanı yapılmıştı. Boğaziçi'nde istenen buydu ama
        # bedeli hemen başka bir kurumda görüldü: Birey'de hiç planlama ilişkisi
        # tanımlı değil, yine de bu iki sert kural yürürlüğe giriyor ve daha önce
        # tamamen dolan çizelge dolmaz hâle geliyordu.
        #
        # Kural, kullanıcının Planlama İlişkileri ekranında gördüğü ve
        # kapatabildiği bir satır olmalıdır. Ekranda olmayan bir kuralın
        # çizelgeyi değiştirmesi, kullanıcının neyi neden alamadığını
        # göremediği bir motor demektir.
    return rules, rep
