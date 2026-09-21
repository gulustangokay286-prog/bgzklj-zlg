"""placement_identity.py — her yerleşmiş kartın kalıcı bir kimliği olsun.

Çizelgede bir kartı "hangi ders" diye tanımanın tek sağlam yolu blok
kimliği (block_id). Ad + sınıf + saat ile tanımak, aynı öğretmenin aynı
dersi yan yana iki kez verdiği yerde çuvallıyordu: kullanıcı 6. saatteki
Fizik'i tepsiye indiriyor, 4. saatteki Fizik de onunla birlikte iniyordu;
ya da başka bir sınıftaki, aynı hocanın aynı dersi de.

Kimlik iki yerde kayboluyordu:

  * Izgara → mağaza senkronu (main_window._sync_grid_to_store) mağazayı
    ekrandaki hücrelerden yeniden kuruyor, hücrede kimlik olmadığı için
    her kayıt kimliksiz kalıyordu; iki saatlik bloklar da birer saatlik
    iki kayda bölünüyordu. O senkron artık mağazaya yazmıyor.
  * Eski dosyalar (bu senkronun yazdıkları) diskte hâlâ kimliksiz. Bu
    modül onları açılışta onarıyor: yan yana duran, aynı derse ait
    saatler tek blokta toplanıyor ve her bloğa yeni bir kimlik veriliyor.

Bloklama kuralı ızgaranın kendi birleştirme kuralıyla bire bir aynı
(main_window._refresh_grid: aynı ders/sınıf/öğretmen/birleşik, ardışık
saat, en çok iki saat). Böylece onarım ekranda hiçbir şeyi değiştirmez;
yalnızca zaten birlikte çizilen saatlere ortak bir ad verir.

Ayrıca ızgaradan mağazaya sızmış çizim defteri alanları (origin_row,
origin_col, day_idx) siliniyor: bunlar ekranın o anki satırına bağlı
sayılardı ve aynı çizelgenin iki farklı görünümü farklı "içerik"
sayılıyor, kullanıcı hiçbir şey değiştirmeden "kaydet" sorusu çıkıyordu.
"""
import uuid

# Izgaradan sızan, içerik olmayan alanlar.
RENDER_KEYS = ("origin_row", "origin_col", "day_idx")

# Bir blok en çok bu kadar saat (ızgaranın birleştirme sınırı).
MAX_BLOCK_HOURS = 2


def _day(p):
    try:
        return int(p.get("day") if "day" in p else p.get("col", 0))
    except (TypeError, ValueError):
        return 0


def _period(p):
    try:
        return int(p.get("period") if "period" in p else p.get("row", 0))
    except (TypeError, ValueError):
        return 0


def _duration(p):
    try:
        return max(1, int(p.get("duration", 1) or 1))
    except (TypeError, ValueError):
        return 1


def _identity_key(p):
    """Aynı bloğa ait olabilecek kayıtları bir araya getiren anahtar."""
    return (
        _day(p),
        (p.get("class_name") or p.get("class") or "").strip(),
        (p.get("subject_name") or p.get("subject") or "").strip(),
        (p.get("teacher_name") or p.get("teacher") or "").strip(),
        bool(p.get("is_combined")),
    )


def new_block_id():
    return f"blk_{uuid.uuid4().hex[:12]}"


def strip_render_keys(placements):
    """Çizim defteri alanlarını siler; silinen alan sayısını döndürür."""
    removed = 0
    for p in placements or []:
        if not isinstance(p, dict):
            continue
        for k in RENDER_KEYS:
            if k in p:
                del p[k]
                removed += 1
    return removed


def assign_block_ids(placements):
    """Kimliksiz kayıtlara blok kimliği verir; verilen kayıt sayısını döndürür.

    Kimliği olan kayıtlara dokunulmaz. Kimliksizler gün + sınıf + ders +
    öğretmen + birleşiklik anahtarıyla gruplanır, saat sırasına dizilir ve
    ardışık olanlar (en çok MAX_BLOCK_HOURS saat) aynı kimliği paylaşır.
    """
    groups = {}
    for p in placements or []:
        if not isinstance(p, dict):
            continue
        if str(p.get("block_id") or "").strip():
            continue
        groups.setdefault(_identity_key(p), []).append(p)

    assigned = 0
    for members in groups.values():
        members.sort(key=_period)
        block = []          # şu an büyüyen blok
        block_end = None    # bloğun kapsadığı son saat + 1
        block_hours = 0

        def close():
            nonlocal assigned
            if not block:
                return
            bid = new_block_id()
            for m in block:
                m["block_id"] = bid
                assigned += 1

        for p in members:
            start, dur = _period(p), _duration(p)
            if block and start == block_end and block_hours + dur <= MAX_BLOCK_HOURS:
                block.append(p)
                block_end = start + dur
                block_hours += dur
            else:
                close()
                block = [p]
                block_end = start + dur
                block_hours = dur
        close()
    return assigned


def mirror_block_ids(source, target):
    """target'taki kimliksiz kayıtlara, aynı hücredeki source kaydının
    kimliğini kopyalar (auto_schedule_results mağazanın aynası)."""
    if not source or not target:
        return 0
    by_slot = {}
    for p in source:
        if not isinstance(p, dict) or not p.get("block_id"):
            continue
        by_slot[(_identity_key(p), _period(p))] = p["block_id"]
    copied = 0
    for p in target:
        if not isinstance(p, dict) or str(p.get("block_id") or "").strip():
            continue
        bid = by_slot.get((_identity_key(p), _period(p)))
        if bid:
            p["block_id"] = bid
            copied += 1
    return copied


def normalize_store(store):
    """Mağazadaki yerleşimleri onarır. Değişiklik sayısını döndürür.

    Sıfır dönerse mağazaya hiç dokunulmamıştır; çağıran taraf içeriği
    "değişti" saymaz.
    """
    if not isinstance(store, dict):
        return 0
    placements = store.get("grid_placements")
    if not isinstance(placements, list):
        return 0
    changed = strip_render_keys(placements)
    changed += assign_block_ids(placements)
    results = store.get("auto_schedule_results")
    if isinstance(results, list) and results:
        changed += strip_render_keys(results)
        changed += mirror_block_ids(placements, results)
        changed += assign_block_ids(results)
    return changed
