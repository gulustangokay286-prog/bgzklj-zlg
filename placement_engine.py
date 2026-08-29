"""
placement_engine.py — "bu ders buraya konabilir mi?" sorusunun TEK cevabı.

Sürükleme sırasında her hedef hücrenin yeşil / mavi / kırmızı / gri yanmasını
sağlayan analiz motoru. Renk bir sonuçtur: önce yerleşim SEMANTİK olarak
sınıflandırılır (VALID / QUESTIONABLE / CONFLICT / FORBIDDEN / ...), görsel eşleme
en sonda yapılır. Arayüz burada iş kuralı barındırmaz.

Neden ayrı bir modül:

Aynı soru bugün üç ayrı yerde, üç ayrı şekilde cevaplanıyordu — otomatik
planlayıcı kendi kurallarıyla, bırakma anındaki kontrol kendi kurallarıyla,
ekran ise hiç sormadan. Sürüklerken kullanıcı hiçbir şey göremiyor, bıraktıktan
sonra "burası dolu" uyarısıyla karşılaşıyordu. Motor tek yerde toplandı;
planlayıcı ile bırakma kontrolü aynı kaynaktan okuduğu için birinin "olur"
dediğine diğeri "olmaz" diyemez.

Mimari:

    TimetableSnapshot     donmuş çizelge + doluluk/müsaitlik indeksleri
    CandidatePlacement    denenen yerleşimin TAM ayak izi (bütün saatleri)
    analyze()             saf fonksiyon: durum + gerekçeler + puan
    PlacementAnalysisResult   motor ile arayüz arasındaki sözleşme

Kurallar:
  * Hiçbir şey mutasyona uğramaz. Analiz spekülatiftir, atılabilir.
  * Sürüklenen dersin KENDİ yeri çakışma sayılmaz (kendi kendine çakışma yok).
  * 2 saatlik ders tek hücre değil, bütün ayak izi birlikte değerlendirilir.
  * "Başkası oturuyor" ile "buraya asla konamaz" AYRI durumlardır.
"""
from collections import defaultdict

# ── Durumlar ────────────────────────────────────────────────────────────────
VALID = "VALID"                       # yeşil  — konabilir
QUESTIONABLE = "QUESTIONABLE"         # mavi   — konur ama tercih edilmez
CONFLICT = "CONFLICT"                 # kırmızı — çakışma var (dolu/meşgul)
FORBIDDEN = "FORBIDDEN"               # gri    — kapalı, asla konamaz
CURRENT = "CURRENT"                   # dersin şu anki yeri
OUT_OF_RANGE = "OUT_OF_RANGE"         # ızgara dışı
INVALID_GEOMETRY = "INVALID_GEOMETRY"  # gün sonuna taşıyor
ANALYSIS_ERROR = "ANALYSIS_ERROR"     # bozuk veri — sessizce "olur" deme

# ── Şiddet ──────────────────────────────────────────────────────────────────
SEV_NONE, SEV_INFO, SEV_PREFERENCE, SEV_SOFT, SEV_HARD = 0, 1, 2, 3, 4
SEVERITY_NAMES = {SEV_NONE: "NONE", SEV_INFO: "INFO", SEV_PREFERENCE: "PREFERENCE",
                  SEV_SOFT: "SOFT", SEV_HARD: "HARD"}

# ── Görsel ──────────────────────────────────────────────────────────────────
V_GREEN, V_BLUE, V_RED, V_GREY, V_SELECTED, V_NONE = (
    "GREEN", "BLUE", "RED", "GREY", "SELECTED", "NONE")

_VISUAL_BY_STATUS = {
    VALID: V_GREEN,
    QUESTIONABLE: V_BLUE,
    CONFLICT: V_RED,
    FORBIDDEN: V_GREY,
    CURRENT: V_SELECTED,
    OUT_OF_RANGE: V_NONE,
    INVALID_GEOMETRY: V_GREY,
    ANALYSIS_ERROR: V_GREY,
}

# Güçlüden zayıfa: aynı anda birden çok durum çıkarsa hangisi kazanır.
# Sıra sabittir — aynı girdi her zaman aynı rengi verir.
_STATUS_RANK = {
    ANALYSIS_ERROR: 70,
    INVALID_GEOMETRY: 60,
    OUT_OF_RANGE: 55,
    FORBIDDEN: 50,
    CONFLICT: 40,
    QUESTIONABLE: 20,
    CURRENT: 10,
    VALID: 0,
}

# ── Çakışma türleri ─────────────────────────────────────────────────────────
TEACHER_COLLISION = "TEACHER_COLLISION"
CLASS_COLLISION = "CLASS_COLLISION"
GROUP_COLLISION = "GROUP_COLLISION"
ROOM_COLLISION = "ROOM_COLLISION"
TEACHER_UNAVAILABLE = "TEACHER_UNAVAILABLE"
CLASS_UNAVAILABLE = "CLASS_UNAVAILABLE"
ROOM_UNAVAILABLE = "ROOM_UNAVAILABLE"
SUBJECT_UNAVAILABLE = "SUBJECT_UNAVAILABLE"
TEACHER_AVOID = "TEACHER_AVOID"
CLASS_AVOID = "CLASS_AVOID"
CROSS_INSTITUTION = "CROSS_INSTITUTION"
RESERVED_ELSEWHERE = "RESERVED_ELSEWHERE"
LOCKED_TARGET = "LOCKED_TARGET"
LOCKED_SOURCE = "LOCKED_SOURCE"
SAME_SUBJECT_SAME_DAY = "SAME_SUBJECT_SAME_DAY"
SUBJECT_WINDOW = "SUBJECT_WINDOW"
CONSECUTIVE_RULE = "CONSECUTIVE_RULE"
NO_ROOM_AVAILABLE = "NO_ROOM_AVAILABLE"
GEOMETRY = "GEOMETRY"
DATA_ERROR = "DATA_ERROR"


def _norm(value) -> str:
    return " ".join(str(value or "").split()).strip()


def _upper(value) -> str:
    tr = str.maketrans("iıçğöşü", "İIÇĞÖŞÜ")
    return _norm(value).translate(tr).upper()


def class_key(value) -> str:
    """Sınıf adının eşleşme anahtarı — uygulamanın matches_class kuralıyla aynı.

    Aynı sınıf ekrandan ekrana farklı yazılıyor: "12 E(TM)", "12E(TM)", "12 E".
    Motor birebir karşılaştırma yaptığı sürece bu üçü üç ayrı sınıf sayılıyor,
    dolayısıyla ne doluluk görülüyor ne de hangi satırın aday olduğu bulunabiliyor
    — ızgarada hiçbir hücre boyanmadan kalıyordu. Anahtar, auto_scheduler'daki
    normalize_class_name + parantez kırpma kuralının aynısıdır.
    """
    text = str(value or "").strip().upper().replace(" ", "")
    text = text.replace("-", "/").replace("\\", "/")
    base = text.split("(")[0].strip()
    return base or text


def teacher_key(value) -> str:
    """Öğretmen adının eşleşme anahtarı — normalize_clean ile aynı davranış."""
    tr = str.maketrans({'İ': 'i', 'I': 'ı', 'ı': 'i', 'Ş': 's', 'ş': 's',
                        'Ğ': 'g', 'ğ': 'g', 'Ü': 'u', 'ü': 'u', 'Ö': 'o',
                        'ö': 'o', 'Ç': 'c', 'ç': 'c'})
    return "".join(c for c in str(value or "").translate(tr).lower() if c.isalnum())


def _split_multi(value) -> list:
    """'A, B' / 'A + B' -> ['A', 'B']. Çoklu öğretmen ve birleşik sınıf için."""
    text = _norm(value)
    if not text:
        return []
    for sep in (",", "&", "/"):
        text = text.replace(sep, "+")
    return [p.strip() for p in text.split("+") if p.strip()]


class Conflict:
    """Tek bir ihlal. 'çakışma var' demek yetmez; kim, nerede, neden."""

    __slots__ = ("type", "resource_kind", "resource_name", "periods",
                 "severity", "message", "lessons")

    def __init__(self, type, resource_kind="", resource_name="", periods=(),
                 severity=SEV_HARD, message="", lessons=()):
        self.type = type
        self.resource_kind = resource_kind
        self.resource_name = resource_name
        self.periods = tuple(periods)
        self.severity = severity
        self.message = message
        self.lessons = tuple(lessons)

    def as_dict(self):
        return {"type": self.type, "resource_kind": self.resource_kind,
                "resource_name": self.resource_name, "periods": list(self.periods),
                "severity": SEVERITY_NAMES.get(self.severity, self.severity),
                "message": self.message, "lessons": list(self.lessons)}

    def __repr__(self):
        return f"<{self.type} {self.resource_name} {list(self.periods)}>"


class CandidatePlacement:
    """Denenen yerleşimin tam ayak izi. Tek hücre değil, bütün saatler."""

    __slots__ = ("lesson", "day", "start_period", "duration", "periods",
                 "classes", "teachers", "room", "subject", "groups",
                 "source_day", "source_period", "block_id")

    def __init__(self, lesson, day, start_period, duration=None):
        self.lesson = lesson or {}
        self.day = int(day)
        self.start_period = int(start_period)
        self.duration = int(duration if duration is not None
                            else (self.lesson.get("duration") or 1) or 1)
        if self.duration < 1:
            self.duration = 1
        self.periods = tuple(range(self.start_period,
                                   self.start_period + self.duration))
        self.subject = _norm(self.lesson.get("subject_name")
                             or self.lesson.get("subject"))
        self.teachers = lesson_teachers(self.lesson)
        self.classes = lesson_classes(self.lesson)
        self.room = _norm(self.lesson.get("room_name") or self.lesson.get("room")
                          or self.lesson.get("derslik"))
        self.groups = lesson_groups(self.lesson)
        self.block_id = _norm(self.lesson.get("block_id"))
        src = self.lesson.get("source") or {}
        self.source_day = src.get("day", self.lesson.get("origin_day"))
        self.source_period = src.get("period", self.lesson.get("origin_period"))

    def key(self):
        return (self.block_id, self.day, self.start_period, self.duration,
                tuple(self.classes), tuple(self.teachers))

    def __repr__(self):
        return (f"<Candidate {self.subject} {self.classes} gün{self.day} "
                f"saat{self.start_period}+{self.duration}>")


class PlacementAnalysisResult:
    """Motor ile arayüz arasındaki sözleşme."""

    __slots__ = ("candidate", "status", "severity", "score", "conflicts",
                 "explanation")

    def __init__(self, candidate, status, severity=SEV_NONE, score=0.0,
                 conflicts=(), explanation=""):
        self.candidate = candidate
        self.status = status
        self.severity = severity
        self.score = score
        self.conflicts = list(conflicts)
        self.explanation = explanation

    # -- gerekçelere göre filtreler ------------------------------------
    def _of(self, *types):
        return [c for c in self.conflicts if c.type in types]

    @property
    def hard_violations(self):
        return [c for c in self.conflicts if c.severity >= SEV_HARD]

    @property
    def soft_violations(self):
        return [c for c in self.conflicts if SEV_NONE < c.severity < SEV_HARD]

    @property
    def teacher_conflicts(self):
        return self._of(TEACHER_COLLISION, TEACHER_UNAVAILABLE, TEACHER_AVOID,
                        CROSS_INSTITUTION, RESERVED_ELSEWHERE)

    @property
    def class_conflicts(self):
        return self._of(CLASS_COLLISION, CLASS_UNAVAILABLE, CLASS_AVOID)

    @property
    def group_conflicts(self):
        return self._of(GROUP_COLLISION)

    @property
    def room_conflicts(self):
        return self._of(ROOM_COLLISION, ROOM_UNAVAILABLE, NO_ROOM_AVAILABLE)

    @property
    def availability_conflicts(self):
        return self._of(TEACHER_UNAVAILABLE, CLASS_UNAVAILABLE,
                        ROOM_UNAVAILABLE, SUBJECT_UNAVAILABLE)

    @property
    def relationship_conflicts(self):
        return self._of(SAME_SUBJECT_SAME_DAY, SUBJECT_WINDOW, CONSECUTIVE_RULE,
                        LOCKED_TARGET, LOCKED_SOURCE)

    @property
    def visual(self):
        return _VISUAL_BY_STATUS.get(self.status, V_NONE)

    @property
    def outside_class_hours(self):
        """Aday, sınıfın ders saatlerinin DIŞINDA mı başlıyor?

        Sınıf günde 4 saat çalışıyorsa 5-8. saatler zaten okul günü dışıdır; orayı
        da gri boyamak ekranın yarısını griye çevirip asıl bilgiyi (yeşil/kırmızı)
        görünmez kılıyordu. Bu hücreler artık hiç boyanmıyor — ders saati içindeki
        gerçek engeller (öğretmen kapalı, başka kurumda) gri kalıyor.
        """
        return any(c.type == CLASS_UNAVAILABLE and c.severity >= SEV_HARD
                   and self.candidate is not None
                   and self.candidate.start_period in c.periods
                   for c in self.conflicts)

    @property
    def placeable(self):
        """Kullanıcı bırakabilir mi? Gri ve geçersiz dışında her şey bırakılabilir;
        kırmızı bırakılır ama uyarı çıkar (program engellemez, söyler)."""
        return self.status in (VALID, QUESTIONABLE, CONFLICT, CURRENT)

    def as_dict(self):
        return {"status": self.status, "visual": self.visual,
                "severity": SEVERITY_NAMES.get(self.severity, self.severity),
                "score": self.score, "explanation": self.explanation,
                "conflicts": [c.as_dict() for c in self.conflicts],
                "day": self.candidate.day if self.candidate else None,
                "period": self.candidate.start_period if self.candidate else None,
                "duration": self.candidate.duration if self.candidate else None}

    def __repr__(self):
        return f"<{self.status}/{self.visual} {self.explanation[:60]}>"


# ── Ders → kaynak çıkarımı ──────────────────────────────────────────────────
def lesson_teachers(lesson) -> list:
    """Dersin BÜTÜN öğretmenleri. 'A, B' iki öğretmendir; ilkinde durulmaz."""
    raw = (lesson.get("teacher_name") or lesson.get("teacher")
           or lesson.get("ogretmen") or "")
    names = _split_multi(raw)
    extra = lesson.get("teachers") or lesson.get("ogretmenler")
    if isinstance(extra, (list, tuple)):
        for t in extra:
            n = _norm(t if not isinstance(t, dict) else (t.get("ad") or t.get("name")))
            if n and n not in names:
                names.append(n)
    return names


def lesson_classes(lesson) -> list:
    """Dersin dokunduğu bütün sınıflar (birleşik ders birden çok sınıfa girer)."""
    combined = lesson.get("combined_classes")
    if isinstance(combined, (list, tuple)) and combined:
        names = [_norm(c) for c in combined if _norm(c)]
        if names:
            return names
    raw = (lesson.get("class_name") or lesson.get("class")
           or lesson.get("sinif") or "")
    return _split_multi(raw)


def lesson_groups(lesson) -> list:
    """Dersin öğrenci grupları. Grup yoksa ders TÜM sınıfa aittir."""
    raw = lesson.get("groups") or lesson.get("gruplar") or lesson.get("grup") \
        or lesson.get("group")
    if isinstance(raw, (list, tuple)):
        return [_norm(g) for g in raw if _norm(g)]
    return _split_multi(raw)


def groups_intersect(a, b) -> bool:
    """İki dersin öğrenci kümesi kesişiyor mu?

    Grup belirtilmemiş ders TÜM sınıftır: her grupla kesişir. İki ders de farklı
    gruplara aitse aynı saatte yan yana durabilirler — sınıf adı aynı diye
    çakışma saymak, bölünmüş sınıfı olan okullarda yanlış kırmızı üretir.
    """
    if not a or not b:
        return True
    sa = {_upper(x) for x in a}
    sb = {_upper(x) for x in b}
    return bool(sa & sb)


def _same_block(p, candidate) -> bool:
    """Bu yerleşim, sürüklenen dersin kendisi mi?"""
    bid = _norm(p.get("block_id"))
    if candidate.block_id and bid:
        return bid == candidate.block_id
    return False


class TimetableSnapshot:
    """Donmuş çizelge + hızlı arama indeksleri.

    Sürükleme başında BİR KEZ kurulur. Fare her kıpırdadığında bütün dersleri
    taramak yerine indekse bakılır: öğretmen/sınıf/derslik/grup için
    (gün, saat) -> dersler.
    """

    def __init__(self, data_store, institution_slug=None, exclude_block_id=None,
                 include_cross_institution=True):
        self.data_store = data_store or {}
        self.slug = institution_slug
        self.exclude_block_id = _norm(exclude_block_id)
        self.errors = []

        settings = self.data_store.get("settings", {}) or {}
        try:
            import constraint_sync
            self.day_count, self.periods = constraint_sync.grid_dimensions(self.data_store)
            self._cs = constraint_sync
        except Exception as exc:                      # pragma: no cover
            self._cs = None
            self.errors.append(f"constraint_sync yok: {exc}")
            self.day_count = int(settings.get("days_count") or 5)
            self.periods = int(settings.get("periods") or 8)

        self.days = list(settings.get("days") or [])[:self.day_count]

        self.class_names = [_norm(c.get("ad") or c.get("name"))
                            for c in self.data_store.get("siniflar", []) or []
                            if isinstance(c, dict)]
        self.teacher_names = [_norm(t.get("ad") or t.get("name"))
                              for t in self.data_store.get("ogretmenler", []) or []
                              if isinstance(t, dict)]
        self.room_names = [_norm(r.get("ad") or r.get("name"))
                           for r in self.data_store.get("derslikler", []) or []
                           if isinstance(r, dict)]

        self._build_availability()
        self._build_occupancy()
        self._build_shared()
        self._build_preferences()

    # -- müsaitlik (kapalı / tercih edilmez) ---------------------------
    def _entity_states(self, entities, keyfunc=None, name_key="ad"):
        closed, avoid = {}, {}
        if self._cs is None:
            return closed, avoid
        for ent in entities or []:
            if not isinstance(ent, dict):
                continue
            name = _norm(ent.get(name_key) or ent.get("name"))
            if not name:
                continue
            try:
                matrix = self._cs.get_matrix(ent, name, self.data_store)
            except Exception as exc:                  # pragma: no cover
                self.errors.append(f"{name} müsaitlik okunamadı: {exc}")
                continue
            c_set, a_set = set(), set()
            for d in range(min(self.day_count, len(matrix))):
                row = matrix[d] or []
                for p in range(min(self.periods, len(row))):
                    if row[p] == self._cs.CLOSED:
                        c_set.add((d, p))
                    elif row[p] == self._cs.AVOID:
                        a_set.add((d, p))
            kf = keyfunc or _upper
            closed[kf(name)] = c_set
            avoid[kf(name)] = a_set
        return closed, avoid

    def _build_availability(self):
        self.class_closed, self.class_avoid = self._entity_states(
            self.data_store.get("siniflar"), class_key)
        self.teacher_closed, self.teacher_avoid = self._entity_states(
            self.data_store.get("ogretmenler"), teacher_key)
        self.room_closed, self.room_avoid = self._entity_states(
            self.data_store.get("derslikler"))
        # Ders bazlı müsaitlik: dersin kendi zaman tablosu varsa o da bağlar.
        self.subject_closed, self.subject_avoid = self._entity_states(
            self.data_store.get("dersler"))

    # -- doluluk indeksleri --------------------------------------------
    def _build_occupancy(self):
        self.by_class = defaultdict(list)
        self.by_teacher = defaultdict(list)
        self.by_room = defaultdict(list)
        self.placements = []

        for p in self.data_store.get("grid_placements", []) or []:
            if not isinstance(p, dict):
                continue
            bid = _norm(p.get("block_id"))
            if self.exclude_block_id and bid == self.exclude_block_id:
                continue                       # sürüklenen dersin kendisi
            try:
                day = int(p.get("day", p.get("col", 0)))
                period = int(p.get("period", p.get("row", 0)))
                dur = max(1, int(p.get("duration", 1) or 1))
            except (TypeError, ValueError):
                self.errors.append(f"bozuk yerleşim: {p!r}")
                continue
            entry = {
                "subject": _norm(p.get("subject_name") or p.get("subject")),
                "classes": lesson_classes(p),
                "teachers": lesson_teachers(p),
                "groups": lesson_groups(p),
                "room": _norm(p.get("room_name") or p.get("room") or p.get("derslik")),
                "locked": bool(p.get("locked") or p.get("is_locked")),
                "block_id": bid,
                "day": day, "period": period, "duration": dur,
                "raw": p,
            }
            self.placements.append(entry)
            for off in range(dur):
                slot = (day, period + off)
                for cn in entry["classes"]:
                    self.by_class[(class_key(cn), slot)].append(entry)
                for tn in entry["teachers"]:
                    self.by_teacher[(teacher_key(tn), slot)].append(entry)
                if entry["room"]:
                    self.by_room[(_upper(entry["room"]), slot)].append(entry)

    # -- kurumlar arası ------------------------------------------------
    def _build_shared(self):
        """Başka kurumdaki ders ve rezervasyonlar. Ağ/disk işi burada BİR KEZ."""
        self.cross_busy = {}
        self.reserved = {}
        if not self.slug:
            return
        try:
            import version_store
            raw = version_store.get_cross_institution_teacher_busy_slots(
                exclude_slug=self.slug) or {}
            for (tkey, d, p), info in raw.items():
                self.cross_busy.setdefault(teacher_key(tkey), {})[(d, p)] = info
        except Exception as exc:
            self.errors.append(f"kurumlar arası meşguliyet okunamadı: {exc}")
        try:
            import constraint_sync
            for tname in self.teacher_names:
                owned = constraint_sync.reservations_for(tname) or {}
                for slot, owner in owned.items():
                    if owner and owner != self.slug:
                        self.reserved.setdefault(teacher_key(tname), {})[slot] = owner
        except Exception as exc:
            self.errors.append(f"rezervasyon defteri okunamadı: {exc}")

    # -- yumuşak tercihler ---------------------------------------------
    def _build_preferences(self):
        c = self.data_store.get("constraints", {}) or {}
        self.pref_subject_windows = {
            _upper(k): v for k, v in (c.get("subject_windows") or {}).items()}
        self.pref_max_daily_same_subject = int(c.get("max_daily_same_subject", 4) or 4)
        self.pref_no_consecutive_hard = bool(c.get("no_consecutive_hard"))

    # -- sorgular -------------------------------------------------------
    def class_lessons_on_day(self, class_name, day):
        out = []
        key = class_key(class_name)
        for entry in self.placements:
            if entry["day"] != day:
                continue
            if any(class_key(c) == key for c in entry["classes"]):
                out.append(entry)
        return out

    def teacher_load_on_day(self, teacher_name, day):
        key = teacher_key(teacher_name)
        return sum(e["duration"] for e in self.placements
                   if e["day"] == day and any(teacher_key(t) == key for t in e["teachers"]))


# ── Analiz ──────────────────────────────────────────────────────────────────
def _slot_label(snapshot, day, period):
    name = snapshot.days[day] if day < len(snapshot.days) else f"{day + 1}. gün"
    return f"{name} {period + 1}. saat"


def _evaluate_geometry(snapshot, candidate, conflicts):
    if candidate.day < 0 or candidate.day >= snapshot.day_count:
        return OUT_OF_RANGE
    if candidate.start_period < 0 or candidate.start_period >= snapshot.periods:
        return OUT_OF_RANGE
    if candidate.start_period + candidate.duration > snapshot.periods:
        conflicts.append(Conflict(
            GEOMETRY, "gün", _slot_label(snapshot, candidate.day, candidate.start_period),
            candidate.periods, SEV_HARD,
            f"{candidate.duration} saatlik ders buraya sığmıyor: gün "
            f"{snapshot.periods}. saatte bitiyor."))
        return INVALID_GEOMETRY
    if not candidate.classes:
        conflicts.append(Conflict(DATA_ERROR, "ders", candidate.subject,
                                  candidate.periods, SEV_HARD,
                                  "Dersin sınıfı belli değil."))
        return ANALYSIS_ERROR
    return None


def _check_availability(snapshot, candidate, conflicts):
    """Kapalı saat 'gri', tercih edilmeyen saat 'mavi'.

    Etkin müsaitlik bütün zorunlu kısıtların KESİŞİMİdir: öğretmen müsait ama
    sınıf kapalıysa saat kapalıdır.
    """
    hard = False
    checks = (
        (candidate.classes, snapshot.class_closed, snapshot.class_avoid,
         "sınıf", CLASS_UNAVAILABLE, CLASS_AVOID, class_key),
        (candidate.teachers, snapshot.teacher_closed, snapshot.teacher_avoid,
         "öğretmen", TEACHER_UNAVAILABLE, TEACHER_AVOID, teacher_key),
        ([candidate.room] if candidate.room else [], snapshot.room_closed,
         snapshot.room_avoid, "derslik", ROOM_UNAVAILABLE, ROOM_UNAVAILABLE, _upper),
        ([candidate.subject] if candidate.subject else [], snapshot.subject_closed,
         snapshot.subject_avoid, "ders", SUBJECT_UNAVAILABLE, SUBJECT_UNAVAILABLE,
         _upper),
    )
    for names, closed_map, avoid_map, kind, hard_type, soft_type, kf in checks:
        for name in names:
            key = kf(name)
            closed = closed_map.get(key) or set()
            avoid = avoid_map.get(key) or set()
            hits = [p for p in candidate.periods if (candidate.day, p) in closed]
            if hits:
                hard = True
                if candidate.duration > 1 and hits[0] != candidate.start_period:
                    msg = (f"{candidate.duration} saatlik ders "
                           f"{candidate.start_period + 1}. saatten başlayınca "
                           f"{hits[0] + 1}. saate taşıyor; {name} o saatte kapalı.")
                else:
                    msg = (f"{name}: {_slot_label(snapshot, candidate.day, hits[0])} "
                           f"kapalı işaretli.")
                conflicts.append(Conflict(hard_type, kind, name, hits, SEV_HARD, msg))
            soft_hits = [p for p in candidate.periods if (candidate.day, p) in avoid]
            if soft_hits:
                conflicts.append(Conflict(
                    soft_type, kind, name, soft_hits, SEV_SOFT,
                    f"{name} bu saatte 'tercih edilmez' işaretli."))
    return hard


def _check_shared_teacher(snapshot, candidate, conflicts):
    """Öğretmen başka kurumda ders veriyor ya da o saat başka kuruma rezerve."""
    hard = False
    for tname in candidate.teachers:
        key = teacher_key(tname)
        busy = snapshot.cross_busy.get(key) or {}
        hits = [p for p in candidate.periods if (candidate.day, p) in busy]
        if hits:
            hard = True
            info = busy[(candidate.day, hits[0])] or {}
            conflicts.append(Conflict(
                CROSS_INSTITUTION, "öğretmen", tname, hits, SEV_HARD,
                f"{tname} bu saatte {info.get('institution_name', 'başka kurum')} "
                f"kurumunda {info.get('class', '')} {info.get('subject', 'ders')} "
                f"dersinde."))
        res = snapshot.reserved.get(key) or {}
        r_hits = [p for p in candidate.periods if (candidate.day, p) in res]
        if r_hits:
            hard = True
            conflicts.append(Conflict(
                RESERVED_ELSEWHERE, "öğretmen", tname, r_hits, SEV_HARD,
                f"{tname} bu saati başka bir kuruma rezerve etmiş."))
    return hard


def _check_occupancy(snapshot, candidate, conflicts):
    """Kaynak doluluğu: sınıf, öğretmen, grup, derslik — her biri ayrı ayrı.

    Kullanıcının sorduğu asıl durum burada: sınıfın hücresi BOŞ olsa bile,
    dersin öğretmeni o saatte BAŞKA bir sınıfta ders veriyorsa burası kırmızıdır.
    """
    conflicting = False

    for cn in candidate.classes:
        for p in candidate.periods:
            for other in snapshot.by_class.get((class_key(cn), (candidate.day, p)), ()):
                if _same_block(other["raw"], candidate):
                    continue
                if not groups_intersect(candidate.groups, other["groups"]):
                    conflicts.append(Conflict(
                        GROUP_COLLISION, "grup", cn, (p,), SEV_INFO,
                        f"{cn} aynı saatte {other['subject']} dersini görüyor ama "
                        f"farklı grup — çakışma sayılmadı."))
                    continue
                conflicting = True
                sev = SEV_HARD if other["locked"] else SEV_HARD
                conflicts.append(Conflict(
                    CLASS_COLLISION, "sınıf", cn, (p,), sev,
                    f"{cn} sınıfında {_slot_label(snapshot, candidate.day, p)}: "
                    f"{other['subject']} ({', '.join(other['teachers'])}) var.",
                    lessons=(other["block_id"],)))
                if other["locked"]:
                    conflicts.append(Conflict(
                        LOCKED_TARGET, "ders", other["subject"], (p,), SEV_HARD,
                        f"{other['subject']} dersi kilitli, yerinden oynatılamaz.",
                        lessons=(other["block_id"],)))

    for tn in candidate.teachers:
        for p in candidate.periods:
            for other in snapshot.by_teacher.get((teacher_key(tn), (candidate.day, p)), ()):
                if _same_block(other["raw"], candidate):
                    continue
                if any(class_key(c) in {class_key(x) for x in candidate.classes}
                       for c in other["classes"]):
                    continue          # aynı sınıf: zaten sınıf çakışması yazıldı
                conflicting = True
                conflicts.append(Conflict(
                    TEACHER_COLLISION, "öğretmen", tn, (p,), SEV_HARD,
                    f"{tn} bu saatte {', '.join(other['classes'])} sınıfında "
                    f"{other['subject']} dersinde.",
                    lessons=(other["block_id"],)))

    if candidate.room:
        for p in candidate.periods:
            for other in snapshot.by_room.get((_upper(candidate.room),
                                               (candidate.day, p)), ()):
                if _same_block(other["raw"], candidate):
                    continue
                conflicting = True
                conflicts.append(Conflict(
                    ROOM_COLLISION, "derslik", candidate.room, (p,), SEV_HARD,
                    f"{candidate.room} dersliği bu saatte "
                    f"{', '.join(other['classes'])} {other['subject']} ile dolu.",
                    lessons=(other["block_id"],)))
    return conflicting


def _check_relationships(snapshot, candidate, conflicts):
    """Yumuşak kurallar: aynı gün aynı ders, ders için tercih edilen zaman dilimi."""
    for cn in candidate.classes:
        same_day = [e for e in snapshot.class_lessons_on_day(cn, candidate.day)
                    if _upper(e["subject"]) == _upper(candidate.subject)
                    and not _same_block(e["raw"], candidate)]
        if same_day:
            conflicts.append(Conflict(
                SAME_SUBJECT_SAME_DAY, "ders", candidate.subject,
                candidate.periods, SEV_PREFERENCE,
                f"{cn} sınıfı {candidate.subject} dersini bugün zaten görüyor."))
        if len(same_day) + 1 > snapshot.pref_max_daily_same_subject:
            conflicts.append(Conflict(
                SAME_SUBJECT_SAME_DAY, "ders", candidate.subject,
                candidate.periods, SEV_SOFT,
                f"{candidate.subject} bir günde en fazla "
                f"{snapshot.pref_max_daily_same_subject} saat olmalı."))

    window = snapshot.pref_subject_windows.get(_upper(candidate.subject))
    if window:
        half = snapshot.periods // 2 or 1
        wrong = ((window == "morning" and candidate.start_period >= half)
                 or (window == "afternoon" and candidate.start_period < half))
        if wrong:
            conflicts.append(Conflict(
                SUBJECT_WINDOW, "ders", candidate.subject, candidate.periods,
                SEV_PREFERENCE,
                f"{candidate.subject} için tercih edilen zaman dilimi: "
                f"{'sabah' if window == 'morning' else 'öğleden sonra'}."))


def analyze(snapshot, lesson, candidate):
    """Saf analiz. Hiçbir şeyi değiştirmez, atılabilir bir sonuç döndürür."""
    if candidate is None:
        return PlacementAnalysisResult(None, OUT_OF_RANGE, SEV_NONE, -1e9, (),
                                       "Izgara dışı.")
    conflicts = []
    try:
        if lesson is not None and (lesson.get("locked") or lesson.get("is_locked")):
            conflicts.append(Conflict(
                LOCKED_SOURCE, "ders", candidate.subject, candidate.periods,
                SEV_HARD, "Bu ders kilitli; taşınamaz."))
            return _finish(snapshot, candidate, FORBIDDEN, conflicts)

        geometry = _evaluate_geometry(snapshot, candidate, conflicts)
        if geometry:
            return _finish(snapshot, candidate, geometry, conflicts)

        # KAPALI SAAT (gri) ile MEŞGUL (kırmızı) ayrımı burada belirlenir:
        #
        #   kapalı  = öğretmen/sınıf/derslik o saatte YOK   -> elle bile konamaz
        #   meşgul  = o saatte başka bir ders var           -> uyar, kullanıcı çözsün
        #
        # Başka kurumda ders vermek "meşgul"dür: uygulamanın "Diğer Kurumları
        # Yoksay" seçeneği bilerek var, dolayısıyla kullanıcı bunu aşabilmeli.
        blocked = _check_availability(snapshot, candidate, conflicts)
        busy_elsewhere = _check_shared_teacher(snapshot, candidate, conflicts)
        occupied = _check_occupancy(snapshot, candidate, conflicts) or busy_elsewhere
        _check_relationships(snapshot, candidate, conflicts)

        if any(c.type == LOCKED_SOURCE for c in conflicts):
            status = FORBIDDEN
        elif blocked:
            status = FORBIDDEN
        elif occupied:
            status = CONFLICT
        elif (candidate.source_day == candidate.day
              and candidate.source_period == candidate.start_period):
            status = CURRENT
        elif any(c.severity >= SEV_PREFERENCE for c in conflicts):
            status = QUESTIONABLE
        else:
            status = VALID
        return _finish(snapshot, candidate, status, conflicts)
    except Exception as exc:                          # pragma: no cover
        conflicts.append(Conflict(DATA_ERROR, "", "", (), SEV_HARD,
                                  f"Analiz hatası: {exc}"))
        return _finish(snapshot, candidate, ANALYSIS_ERROR, conflicts)


def _finish(snapshot, candidate, status, conflicts):
    severity = max([c.severity for c in conflicts], default=SEV_NONE)
    score = 0.0
    for c in conflicts:
        score -= {SEV_HARD: 1000.0, SEV_SOFT: 25.0, SEV_PREFERENCE: 8.0,
                  SEV_INFO: 0.0, SEV_NONE: 0.0}.get(c.severity, 0.0)
    hard = [c for c in conflicts if c.severity >= SEV_HARD]
    soft = [c for c in conflicts if SEV_NONE < c.severity < SEV_HARD]
    if hard:
        explanation = hard[0].message
        if len(hard) > 1:
            explanation += f"  (+{len(hard) - 1} sorun daha)"
    elif soft:
        explanation = soft[0].message
    elif status == CURRENT:
        explanation = "Dersin şu anki yeri."
    elif status == VALID:
        explanation = "Buraya konabilir."
    else:
        explanation = ""
    return PlacementAnalysisResult(candidate, status, severity, score,
                                   conflicts, explanation)


def analyze_row(snapshot, lesson, day_periods, duration=None, cache=None):
    """Bir satırdaki BÜTÜN başlangıç saatlerini değerlendirir.

    day_periods: [(gün, saat), ...] — ızgaranın o satırdaki hücreleri.
    Dönen: {(gün, saat): PlacementAnalysisResult}
    """
    out = {}
    for (day, period) in day_periods:
        cand = CandidatePlacement(lesson, day, period, duration)
        key = cand.key()
        if cache is not None and key in cache:
            out[(day, period)] = cache[key]
            continue
        res = analyze(snapshot, lesson, cand)
        if cache is not None:
            cache[key] = res
        out[(day, period)] = res
    return out


def explain(result) -> str:
    """Hata ayıklama / ipucu metni: bu hücre neden bu renk?"""
    if result is None:
        return ""
    lines = [f"{result.status} ({result.visual}) — {result.explanation}"]
    for c in result.conflicts:
        lines.append(f"  • [{SEVERITY_NAMES.get(c.severity, c.severity)}] "
                     f"{c.type}: {c.message}")
    return "\n".join(lines)
