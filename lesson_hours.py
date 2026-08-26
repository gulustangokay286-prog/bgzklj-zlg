"""
lesson_hours.py — bir dersin kaç saat olduğunun TEK doğru kaynağı.

Neden ayrı bir modül:

Aynı atama listesi ekrandan ekrana farklı toplam veriyordu. Sınıf ekranı saati
`duration` alanından, öğretmen ekranı ise eski `ders_sayisi` alanından okuyordu;
İstatistik ekranı da hiç yazılmayan `saat`/`ogretmen` alanlarını okuduğu için
"Atanan Toplam Ders Saati: 72" gibi tamamen yanlış bir sayı gösteriyordu.

Bir atama satırı geçmişte birden çok ekran tarafından yazıldığı için aynı bilgiyi
taşıyan üç ayrı alan birikmiş durumda:

    saat / süre   : duration, saat, ders_sayisi, toplam_saat, hours
    dağılım       : type, dagilim
    öğretmen      : teacher, ogretmen, teacher_name
    sınıf         : class, sinif, class_name
    ders          : subject, ders, subject_name

Öğretmen ekranı kaydettiğinde hepsini birden yazıyor, sınıf ekranı yalnızca
`duration` + `type` yazıyordu. Sınıf ekranından bir dersin saati değiştirildiğinde
`ders_sayisi` ESKİ değerinde kalıyor, ondan sonra öğretmen ekranı ve otomatik
planlayıcı o eski değeri okuyordu. İki ekranın farklı toplam göstermesinin ve
planlayıcının sınıfa atanandan farklı sayıda saat yerleştirmesinin sebebi buydu.

Buradaki kurallar:
  * Saat, ÖNCE dağılım metninden ("2+1" -> 3) okunur; sanitize_atamalar da
    duration'ı zaten oradan türetir, dolayısıyla dağılım fiilen ana alandır.
  * Dağılım yoksa duration, o da yoksa eski alanlar kullanılır.
  * `sync_keys()` bir satırdaki bütün eş anlamlı alanları aynı değere getirir;
    böylece hangi ekran hangi alanı okursa okusun aynı sayıyı görür.

Saf Python — Qt yok, veri deposu dışında bağımlılığı yok, headless test edilebilir.
"""
from collections import defaultdict

HOUR_KEYS = ("duration", "saat", "ders_sayisi", "toplam_saat", "hours")
TYPE_KEYS = ("type", "dagilim")
# distribution ayrı tutulur: metin değil, [2, 2, 1] gibi bir LİSTEdir ve gridin
# "Böl / Birleştir" menüsü onu liste olarak okur (2 in dist). Metne çevirmek o menüyü
# kırar, o yüzden sync_keys onu liste olarak yazar.
DIST_KEY = "distribution"
TEACHER_KEYS = ("teacher", "ogretmen", "teacher_name")
CLASS_KEYS = ("class", "sinif", "class_name")
SUBJECT_KEYS = ("subject", "ders", "subject_name")

_CLASS_SEPARATORS = ("+", ",", "&")


def _text(value) -> str:
    return " ".join(str(value or "").split()).strip()


def _first(assignment, keys) -> str:
    for k in keys:
        v = _text(assignment.get(k))
        if v:
            return v
    return ""


def parse_type(value):
    """'2+1' -> 3, '4' -> 4, [2, 2, 1] -> 5, boş/anlamsız -> None."""
    if isinstance(value, (list, tuple)):
        parts = []
        for p in value:
            try:
                n = int(p)
            except (TypeError, ValueError):
                continue
            if n > 0:
                parts.append(n)
        return sum(parts) if parts else None
    text = _text(value).replace(" ", "")
    if not text:
        return None
    if "+" in text:
        parts = [int(p) for p in text.split("+") if p.isdigit()]
        return sum(parts) if parts else None
    return int(text) if text.isdigit() else None


def parts_of(assignment) -> list:
    """Dersin blok dağılımı: 3 saatlik '2+1' dersi -> [2, 1]."""
    if isinstance(assignment, dict):
        for k in TYPE_KEYS:
            text = _text(assignment.get(k)).replace(" ", "")
            if text and parse_type(text):
                if "+" in text:
                    return [int(p) for p in text.split("+") if p.isdigit()]
                return [int(text)]
        dist = assignment.get(DIST_KEY)
        if isinstance(dist, (list, tuple)) and parse_type(dist):
            return [int(p) for p in dist if str(p).strip().isdigit() and int(p) > 0]
    total_hours = hours(assignment)
    parts, rem = [], total_hours
    while rem > 0:
        parts.append(min(2, rem))
        rem -= min(2, rem)
    return parts


def type_str(assignment) -> str:
    for k in TYPE_KEYS:
        if parse_type(assignment.get(k)) is not None:
            return _text(assignment.get(k)).replace(" ", "")
    parts = parts_of(assignment)
    return "+".join(str(p) for p in parts) if parts else ""


def hours(assignment) -> int:
    """Bir atama satırının haftalık saati."""
    if not isinstance(assignment, dict):
        return 0
    for k in TYPE_KEYS:
        parsed = parse_type(assignment.get(k))
        if parsed:
            return parsed
    dist = parse_type(assignment.get(DIST_KEY))
    if dist:
        return dist
    for k in HOUR_KEYS:
        raw = assignment.get(k)
        if raw is None:
            continue
        try:
            value = int(float(str(raw).strip()))
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return 0


def teacher(assignment) -> str:
    return _first(assignment, TEACHER_KEYS) if isinstance(assignment, dict) else ""


def subject(assignment) -> str:
    return _first(assignment, SUBJECT_KEYS) if isinstance(assignment, dict) else ""


def class_name(assignment) -> str:
    return _first(assignment, CLASS_KEYS) if isinstance(assignment, dict) else ""


def classes(assignment) -> list:
    """Bir atamanın dokunduğu sınıflar; birleşik ders birden çok sınıfa yazılır."""
    if not isinstance(assignment, dict):
        return []
    combined = assignment.get("combined_classes")
    if isinstance(combined, list) and combined:
        names = [_text(c) for c in combined if _text(c)]
        if names:
            return names
    raw = class_name(assignment)
    if not raw:
        return []
    for sep in _CLASS_SEPARATORS[1:]:
        raw = raw.replace(sep, "+")
    parts = [p.strip() for p in raw.split("+") if p.strip()]
    return parts or [class_name(assignment)]


def sync_keys(assignment) -> dict:
    """Satırdaki bütün eş anlamlı alanları tek doğru değere eşitler (yerinde)."""
    if not isinstance(assignment, dict):
        return assignment
    hrs = hours(assignment)
    dist = type_str(assignment)
    t, s, c = teacher(assignment), subject(assignment), class_name(assignment)
    for k in HOUR_KEYS:
        if k in assignment or k in ("duration",):
            assignment[k] = hrs
    for k in TYPE_KEYS:
        if k in assignment or k == "type":
            assignment[k] = dist
    if DIST_KEY in assignment:
        assignment[DIST_KEY] = parts_of(assignment)
    if t:
        for k in TEACHER_KEYS:
            if k in assignment or k == "teacher":
                assignment[k] = t
    if s:
        for k in SUBJECT_KEYS:
            if k in assignment or k == "subject":
                assignment[k] = s
    if c:
        for k in CLASS_KEYS:
            if k in assignment or k == "class":
                assignment[k] = c
    return assignment


def sync_all(atamalar) -> list:
    for a in atamalar or []:
        sync_keys(a)
    return atamalar or []


def rows(data_store) -> list:
    """Ekranların ortak okuduğu normalize satır listesi."""
    out = []
    for a in (data_store or {}).get("atamalar", []) or []:
        if not isinstance(a, dict):
            continue
        hrs = hours(a)
        if hrs <= 0:
            continue
        out.append({
            "teacher": teacher(a),
            "subject": subject(a),
            "class": class_name(a),
            "classes": classes(a),
            "hours": hrs,
            "type": type_str(a),
            "is_combined": bool(a.get("is_combined")) or len(classes(a)) > 1,
            "raw": a,
        })
    return out


def per_class(data_store) -> dict:
    """{sınıf: haftalık saat}. Birleşik ders her sınıfa ayrı ayrı sayılır."""
    out = defaultdict(int)
    for r in rows(data_store):
        for c in r["classes"]:
            out[c] += r["hours"]
    return dict(out)


def per_teacher(data_store) -> dict:
    """{öğretmen: haftalık saat}. Birleşik ders bir kez sayılır — öğretmen o saatte
    tek yerdedir."""
    out = defaultdict(int)
    for r in rows(data_store):
        if r["teacher"]:
            out[r["teacher"]] += r["hours"]
    return dict(out)


def total(data_store) -> int:
    """Atanan toplam ders saati (birleşik dersler bir kez)."""
    return sum(r["hours"] for r in rows(data_store))


def audit(data_store) -> dict:
    """Sınıf tarafı ile öğretmen tarafı gerçekten tutuyor mu?

    Döndürür:
      class_total    sınıflara yazılan toplam (birleşik dersler her sınıfa)
      teacher_total  öğretmenlere yazılan toplam
      lesson_total   atama satırlarının toplamı
      combined_extra birleşik derslerin sınıf tarafında yarattığı fazlalık
      unknown_teachers / unknown_classes  kayıtlarda karşılığı olmayan isimler
      stale_rows     eş anlamlı alanları birbirini tutmayan satırlar
      consistent     True ise iki taraf birbirini tutuyor
    """
    data_store = data_store or {}
    known_t = {_text(t.get("ad") or t.get("name"))
               for t in data_store.get("ogretmenler", []) or [] if isinstance(t, dict)}
    known_c = {_text(c.get("ad") or c.get("name"))
               for c in data_store.get("siniflar", []) or [] if isinstance(c, dict)}
    known_t.discard("")
    known_c.discard("")

    rws = rows(data_store)
    class_total = sum(r["hours"] * len(r["classes"]) for r in rws)
    teacher_total = sum(r["hours"] for r in rws if r["teacher"])
    lesson_total = sum(r["hours"] for r in rws)
    combined_extra = class_total - lesson_total

    unknown_teachers, unknown_classes, stale = [], [], []
    for r in rws:
        if r["teacher"] and known_t and r["teacher"] not in known_t:
            unknown_teachers.append((r["class"], r["subject"], r["teacher"], r["hours"]))
        for c in r["classes"]:
            if known_c and c not in known_c:
                unknown_classes.append((c, r["subject"], r["teacher"], r["hours"]))
        raw = r["raw"]
        seen = set()
        for k in HOUR_KEYS:
            if k in raw:
                try:
                    seen.add(int(float(str(raw.get(k)).strip())))
                except (TypeError, ValueError):
                    pass
        if len(seen) > 1:
            stale.append((r["class"], r["subject"], r["teacher"],
                          {k: raw.get(k) for k in HOUR_KEYS if k in raw}))

    return {
        "class_total": class_total,
        "teacher_total": teacher_total,
        "lesson_total": lesson_total,
        "combined_extra": combined_extra,
        "unknown_teachers": unknown_teachers,
        "unknown_classes": unknown_classes,
        "stale_rows": stale,
        "consistent": (not unknown_teachers and not unknown_classes and not stale
                       and teacher_total == lesson_total),
    }
