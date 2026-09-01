"""
constraint_sync.py — Zaman Tablosu / Kısıtlamalar ekranları ve otomatik planlayıcı için
TEK ortak müsaitlik kaynağı (single source of truth).

Neden bu modül var
------------------
Müsaitlik verisi tarihsel olarak İKİ ayrı yerde tutuluyordu:

  1. entity["timeoff"][gun][saat]  -> 2 = açık, 1 = tercih edilmez, 0 = kapalı  (3 durumlu)
  2. data_store["kisitlamalar"][ad]["gun,saat"] -> True/False                   (2 durumlu)

Zaman Tablosu ekranı ikisini birden yazıyor, Kısıtlamalar ekranı ise (2) yi asıl kaynak
kabul edip (1) i ondan yeniden üretiyordu. (2) sarı "?" durumunu taşıyamadığı için,
Kısıtlamalar ekranını açıp kaydetmek "tercih edilmez" işaretlerini sessizce "açık" a
çeviriyordu; iki ekran birbirini eziyordu.

Bu modül 3 durumlu matrisi tek gerçek kabul eder, iki gösterimi HER ZAMAN birlikte
yazar (drift imkânsız hale gelir) ve aynı öğretmen birden fazla kurumda çalışıyorsa
kısıtlamaların kurumlar arası birleşimini sağlar.

Geriye dönük uyumluluk: kisitlamalar sözlüğü artık int (0/1/2) tutar, ama okuyucular
eski bool değerleri de kabul eder (True -> 2, False -> 0). Eski kayıtlar sorunsuz açılır.
"""

import json
import os
import threading
import uuid as _uuid

# Guards the read-modify-write cycle on the shared ledgers. Both files are updated by
# reading the whole thing, changing one institution's slice and writing it all back —
# so two threads doing that at once (a dialog saving while save_db's background thread
# publishes) would each write a copy based on stale content, and whoever finished last
# would silently drop the other's changes.
_STORE_LOCK = threading.RLock()

OPEN = 2      # ✔ Müsait
AVOID = 1     # ? Zorunlu olmadıkça atanmasın (yumuşak kısıt)
CLOSED = 0    # ✖ Kapalı (sert kısıt)


def _coerce_state(value) -> int:
    """Bir hücre değerini 0/1/2 durumuna çevirir.

    kisitlamalar sözlüğü eskiden bool tutuyordu; hem eski (True/False) hem yeni
    (0/1/2) kayıtların aynı anda okunabilmesi için tek giriş noktası burasıdır.
    """
    if isinstance(value, bool):
        return OPEN if value else CLOSED
    try:
        ival = int(value)
    except (TypeError, ValueError):
        return OPEN
    if ival in (OPEN, AVOID, CLOSED):
        return ival
    return OPEN if ival > 0 else CLOSED


def grid_dimensions(data_store: dict) -> tuple:
    """(gun_sayisi, saat_sayisi) — her iki diyalog ve planlayıcı aynı kaynağı kullansın diye
    tek yerde hesaplanır. settings boş olabilir; o zaman kök seviyedeki alanlara düşer."""
    settings = (data_store or {}).get("settings", {}) or {}

    days = settings.get("days")
    if days:
        day_count = len(days)
    else:
        day_count = settings.get("days_count", settings.get("day_count"))
        if not day_count:
            day_count = (data_store or {}).get("gun_sayisi", 5)
        try:
            day_count = int(day_count)
        except (TypeError, ValueError):
            day_count = 5
    if day_count <= 0:
        day_count = 5

    periods = settings.get("periods")
    if not periods:
        periods = (data_store or {}).get("ders_saati", 8)
    try:
        periods = int(periods)
    except (TypeError, ValueError):
        periods = 8
    if periods <= 0:
        periods = 8

    return day_count, periods


def day_names(data_store: dict) -> list:
    """Diyaloglarda başlık olarak kullanılan gün adları."""
    settings = (data_store or {}).get("settings", {}) or {}
    days = settings.get("days")
    if days:
        return list(days)
    day_count, _ = grid_dimensions(data_store)
    try:
        from timetable_grid import DAYS
    except Exception:
        DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    return list(DAYS[:day_count])


# ── KİŞİSEL KISIT (bütün kurumları bağlar) ───────────────────────────────────
#
# Bir öğretmenin bir saatinin kapalı olmasının İKİ ayrı sebebi var ve bunlar
# birbirinin yerine geçemez:
#
#   1) "Bu kurumda o saatte ders vermiyor"  → yalnızca BU kurumu bağlar.
#      Yarım gün burada, öğleden sonra başka şubede çalışan bir öğretmenin
#      durumu budur. Burada kapattığınız saat, diğer kurumda AÇIK olmalıdır —
#      zaten oraya gittiği için burada yok.
#
#   2) "Bu saatte hiçbir yerde yok"          → BÜTÜN kurumları bağlar.
#      Rapor, izin, kendi işi, okula hiç gelmediği yarım gün. Buna "kişisel
#      kısıt" diyoruz ve kurumlar arası ortak deftere yalnızca bu yazılır.
#
# Eskiden ayrım yoktu: bir kurumda kapatılan her saat bütün kurumlarda kapalı
# sayılıyordu. Sonuç, üç dört kurumda çalışan bir öğretmenin hiçbir yerde
# yerleşememesiydi — herkesin kendi kapattığı saatler toplanıp öğretmeni
# tamamen bloke ediyordu.
#
# Kişisel kısıt ayrı bir katmanda tutulur:
#   entity["personal_off"]                        -> [gun][saat] 0/1
#   data_store["kisitlamalar_kisisel"][ad]        -> {"gun,saat": 1}
PERSONAL_KEY = "personal_off"
PERSONAL_STORE = "kisitlamalar_kisisel"


def get_personal(entity: dict, name: str, data_store: dict) -> list:
    """Öğretmenin KİŞİSEL kapalı saatleri: [gun][saat] -> True/False."""
    day_count, periods = grid_dimensions(data_store)
    grid = [[False for _ in range(periods)] for _ in range(day_count)]

    raw = (entity or {}).get(PERSONAL_KEY) or []
    for d in range(day_count):
        if d < len(raw) and isinstance(raw[d], list):
            for p in range(periods):
                if p < len(raw[d]) and raw[d][p]:
                    grid[d][p] = True

    entry = ((data_store or {}).get(PERSONAL_STORE) or {}).get(name)
    if isinstance(entry, dict):
        for key, val in entry.items():
            try:
                d, p = (int(x) for x in str(key).split(","))
            except (ValueError, TypeError):
                continue
            if 0 <= d < day_count and 0 <= p < periods and val:
                grid[d][p] = True
    return grid


def set_personal(entity: dict, name: str, data_store: dict, grid: list):
    """Kişisel kısıtları her iki gösterime birden yazar."""
    if entity is None or not name:
        return
    day_count, periods = grid_dimensions(data_store)
    rows, cells = [], {}
    for d in range(day_count):
        row = []
        for p in range(periods):
            on = bool(grid[d][p]) if (d < len(grid) and p < len(grid[d])) else False
            row.append(1 if on else 0)
            if on:
                cells[f"{d},{p}"] = 1
        rows.append(row)
    entity[PERSONAL_KEY] = rows
    store = data_store.setdefault(PERSONAL_STORE, {})
    if cells:
        store[name] = cells
    else:
        store.pop(name, None)


def get_matrix(entity: dict, name: str, data_store: dict) -> list:
    """Bir birimin (öğretmen/sınıf/derslik) 3 durumlu müsaitlik matrisini döndürür.

    Zaman Tablosu (entity["timeoff"]) birincil ve mutlak gerçektir (single source of truth).
    Eğer timeoff tanımlıysa doğrudan kullanılır; tanımlı değilse kisitlamalar sözlüğünden okunur.
    
    Dönen matris [gun][saat] şeklindedir ve her zaman tam boyutludur.
    """
    day_count, periods = grid_dimensions(data_store)
    matrix = [[OPEN for _ in range(periods)] for _ in range(day_count)]

    toff = (entity or {}).get("timeoff")
    if toff and isinstance(toff, list) and len(toff) > 0:
        for d in range(day_count):
            if d < len(toff) and isinstance(toff[d], list):
                # Günün mevcut tüm saatleri kapalı mıydı?
                all_closed_in_day = len(toff[d]) > 0 and all(_coerce_state(x) == CLOSED for x in toff[d])
                for p in range(periods):
                    if p < len(toff[d]):
                        matrix[d][p] = _coerce_state(toff[d][p])
                    else:
                        matrix[d][p] = CLOSED if all_closed_in_day else OPEN
            else:
                matrix[d] = [OPEN for _ in range(periods)]
    else:
        # Geriye dönük uyumluluk: entity'de timeoff yoksa kisitlamalar'dan oku
        entry = ((data_store or {}).get("kisitlamalar") or {}).get(name)
        if isinstance(entry, dict):
            for key, raw in entry.items():
                try:
                    d_str, p_str = str(key).split(",")
                    d, p = int(d_str), int(p_str)
                except (ValueError, TypeError):
                    continue
                if 0 <= d < day_count and 0 <= p < periods:
                    matrix[d][p] = _coerce_state(raw)

    # Kişisel kısıt her şeyin üstündedir: öğretmen o saatte hiçbir yerde yoksa
    # burada da yoktur.
    personal = get_personal(entity, name, data_store)
    for d in range(day_count):
        for p in range(periods):
            if personal[d][p]:
                matrix[d][p] = CLOSED

    return matrix


def set_matrix(entity: dict, name: str, data_store: dict, matrix: list):
    """3 durumlu matrisi HER İKİ gösterime birden ve aynı ada sahip tüm kopyalara yazar.

    Tek yazma noktası olduğu için iki ekranın birbirini ezmesi veya kopya öğretmenlerin
    ayrışması imkânsızdır.
    """
    if entity is None or not name:
        return
    day_count, periods = grid_dimensions(data_store)

    toff = []
    for d in range(day_count):
        row = []
        all_closed_in_day = False
        if d < len(matrix) and isinstance(matrix[d], list) and len(matrix[d]) > 0:
            all_closed_in_day = all(_coerce_state(x) == CLOSED for x in matrix[d])
        for p in range(periods):
            if d < len(matrix) and p < len(matrix[d]):
                row.append(_coerce_state(matrix[d][p]))
            else:
                row.append(CLOSED if all_closed_in_day else OPEN)
        toff.append(row)
    entity["timeoff"] = toff

    kis = data_store.setdefault("kisitlamalar", {})
    cell_map = {}
    for d in range(day_count):
        for p in range(periods):
            cell_map[f"{d},{p}"] = toff[d][p]
    kis[name] = cell_map

    # Aynı ada sahip diğer öğretmen/birim kopyalarını da eşitle
    try:
        from version_store import normalize_teacher_name
        n_target = normalize_teacher_name(name)
    except Exception:
        n_target = name.strip().lower()

    for grp in ("ogretmenler", "siniflar", "derslikler"):
        for other in (data_store.get(grp, []) or []):
            if isinstance(other, dict):
                o_ad = (other.get("ad") or other.get("name") or "").strip()
                try:
                    from version_store import normalize_teacher_name
                    o_norm = normalize_teacher_name(o_ad)
                except Exception:
                    o_norm = o_ad.lower()
                if o_norm == n_target and other is not entity:
                    other["timeoff"] = [list(r) for r in toff]
                    kis[o_ad] = cell_map


def sync_all(data_store: dict):
    """data_store içindeki tüm birimlerin iki gösterimini yeniden hizalar.

    Bir diyalog kaydedildiğinde çağrılır: yalnızca düzenlenen birim değil, hepsi
    tutarlı hale gelir; böylece eski sürümlerden gelmiş yarım kalmış kayıtlar da
    tek seferde düzelir.
    """
    if not isinstance(data_store, dict):
        return
    for key in ("ogretmenler", "siniflar", "derslikler"):
        for entity in data_store.get(key, []) or []:
            if not isinstance(entity, dict):
                continue
            name = (entity.get("ad") or entity.get("name") or "").strip()
            if not name:
                continue
            set_matrix(entity, name, data_store, get_matrix(entity, name, data_store))


# ── Kurumlar arası paylaşım ────────────────────────────────────────────

def _global_path() -> str:
    return os.path.join(os.path.expanduser("~"), ".chenki_akademi", "global_kisitlamalar.json")


class SharedStoreUnreadable(Exception):
    """Ortak dosya var ama okunamadı — üzerine yazmak diğer kurumların verisini siler."""


def _read_shared(path: str, strict: bool = False) -> dict:
    """Ortak JSON dosyasını okur.

    strict=True iken, dosya VAR ama okunamıyorsa boş sözlük dönmek yerine hata
    fırlatır. Bu ayrım kritik: bu dosyalar "oku → kendi payını değiştir → tamamını
    yaz" düzeniyle güncelleniyor. Okuma sessizce {} dönerse, yazma adımı diğer
    kurumların (B, C, D) kayıtlarını kalıcı olarak silerdi — yani tek bir geçici
    okuma hatası tüm kurumların kısıtlamalarını uçururdu.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        if strict:
            raise SharedStoreUnreadable(str(e))
        return {}
    if not isinstance(data, dict):
        if strict:
            raise SharedStoreUnreadable("beklenen sözlük değil")
        return {}
    return data


def _write_shared(path: str, data: dict):
    """Dosyayı atomik yazar: önce geçici dosyaya, sonra tek adımda yerine koyar.

    Doğrudan yazarken süreç/işletim sistemi araya girerse dosya yarım kalır ve bir
    daha okunamaz. os.replace aynı dizinde atomiktir; okuyucular ya eski ya yeni
    tam hali görür, asla yarısını.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # The temp name must be unique per CALL, not per process: two threads writing at
    # once would otherwise pick the same path, and the first os.replace would move the
    # file out from under the second, failing its write entirely.
    tmp = f"{path}.tmp{os.getpid()}.{_uuid.uuid4().hex[:8]}"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def load_global() -> dict:
    """{slug: {birim_adi: {"gun,saat": durum}}}"""
    data = _read_shared(_global_path())
    # Çok eski biçim: doğrudan birim adlarıyla kaydedilmiş, kurum sarmalayıcısı yok.
    if data and any(" " in k or len(k) > 30 for k in data.keys()):
        return {"bogazici_egitim_kurumlari": data}
    return data


def candidate_store(data_store: dict, entity: dict, name: str, matrix: list,
                    personal: list = None) -> dict:
    """Henüz KAYDEDİLMEMİŞ bir kısıtlama değişikliğinin uygulanmış hâlini üretir.

    Ekranlar "kaydedersem ne olur?" sorusunu bunun üzerinden sorar: gerçek veriye
    dokunmadan, yalnızca planlayıcının bakacağı alanları kopyalayıp yeni matrisi
    işler. Kopya sığdır — grid_placements gibi büyük listeler taşınmaz, çünkü
    fizibilite hesabı onlara bakmaz.
    """
    import copy as _copy

    probe = {
        "settings": (data_store or {}).get("settings", {}),
        "atamalar": (data_store or {}).get("atamalar", []),
        "siniflar": _copy.deepcopy((data_store or {}).get("siniflar", []) or []),
        "ogretmenler": _copy.deepcopy((data_store or {}).get("ogretmenler", []) or []),
        "derslikler": (data_store or {}).get("derslikler", []),
        "kisitlamalar": _copy.deepcopy((data_store or {}).get("kisitlamalar", {}) or {}),
        PERSONAL_STORE: _copy.deepcopy((data_store or {}).get(PERSONAL_STORE, {}) or {}),
        "gun_sayisi": (data_store or {}).get("gun_sayisi"),
        "ders_saati": (data_store or {}).get("ders_saati"),
    }

    target = None
    for group in ("ogretmenler", "siniflar"):
        for item in probe.get(group) or []:
            if isinstance(item, dict) and (item.get("ad") or item.get("name") or "").strip() == name:
                target = item
                break
        if target:
            break
    if target is None:
        target = _copy.deepcopy(entity) if entity else {"ad": name}

    if personal is not None:
        set_personal(target, name, probe, personal)
    if matrix is not None:
        set_matrix(target, name, probe, matrix)
        if personal is not None:
            # set_matrix kisitlamalar'ı yeniden yazdığı için kişisel katman
            # tekrar uygulanmalı; kişisel kısıt her zaman en kısıtlayıcıdır.
            set_personal(target, name, probe, personal)
    return probe


SHARE_KIND = "personal"     # ortak deftere yalnızca kişisel kısıt yazılır


def publish(slug: str, data_store: dict):
    """Bu kurumun ÖĞRETMEN KİŞİSEL kısıtlarını kurumlar arası ortak deftere yazar.

    Sadece öğretmenler paylaşılır: aynı öğretmen birden çok kurumda ders verebilir,
    ama bir sınıf yalnızca kendi kurumuna aittir — sınıf kısıtlamalarını paylaşmak
    farklı kurumlardaki aynı adlı sınıfları (ör. her kurumda bir "9A") yanlışlıkla
    birbirine bağlardı.

    YALNIZCA kişisel kısıt yayınlanır. Bu kurumun kendi çalışma saatleri (öğretmen
    burada sabahçı, orada öğleden sonracı) diğer kurumları ilgilendirmez; onları da
    kapatmak, üç dört kurumda çalışan bir öğretmeni hiçbir yere yerleştirilemez hale
    getiriyordu. Başka kurumun saatini kapatan iki meşru şey vardır ve ikisi de
    ayrıca yürür: kişisel kısıt (burası) ve o kurumun gerçekten ders koyduğu /
    rezerve ettiği saat (rezervasyon defteri).
    """
    if not slug or not isinstance(data_store, dict) or not _institution_exists(slug):
        return
    day_count, periods = grid_dimensions(data_store)

    payload = {}
    for teacher in data_store.get("ogretmenler", []) or []:
        if not isinstance(teacher, dict):
            continue
        name = (teacher.get("ad") or teacher.get("name") or "").strip()
        if not name:
            continue
        personal = get_personal(teacher, name, data_store)
        cells = {f"{d},{p}": CLOSED
                 for d in range(day_count) for p in range(periods)
                 if personal[d][p]}
        if cells:
            payload[name] = cells

    # Also store it on the institution itself. meta.json rides the existing VDS sync,
    # so another computer sees this institution's teacher availability without having
    # to open and save the institution there first — which is all the local
    # global_kisitlamalar.json cache below could ever offer.
    with _STORE_LOCK:
        try:
            meta = _read_inst_meta(slug, strict=True)
            if meta:
                from datetime import datetime as _dt
                meta["teacher_availability"] = {"updated": _dt.now().isoformat(),
                                                "kind": SHARE_KIND, "slots": payload}
                _write_shared(_inst_meta_path(slug), meta)
        except SharedStoreUnreadable as e:
            print(f"[constraint_sync] meta okunamadı, müsaitlik yazılmadı: {e}")
        except Exception as e:
            print(f"[constraint_sync] meta müsaitlik yazımı başarısız: {e}")

    path = _global_path()
    with _STORE_LOCK:
        try:
            global_data = _read_shared(path, strict=True)
        except SharedStoreUnreadable as e:
            # Refuse to publish rather than overwrite the other institutions' entries
            # with a file we could not read.
            print(f"[constraint_sync] ortak kısıtlama dosyası okunamadı, yazma atlandı: {e}")
            return

        if global_data and any(" " in k or len(k) > 30 for k in global_data.keys()):
            global_data = {"bogazici_egitim_kurumlari": global_data}

        # Zarflı yazım: okuyan taraf bunun KİŞİSEL kısıt olduğunu bilmeli. Eski
        # düz kayıtlar (zarfsız) kurum kısıtlarını taşıyordu ve okunduklarında
        # diğer kurumları haksız yere kapatıyorlardı; okuma tarafı artık onları
        # yok sayıyor, ilk kayıtta da bu zarfla değişiyorlar.
        global_data[slug] = {"kind": SHARE_KIND, "slots": payload}
        try:
            _write_shared(path, global_data)
        except Exception as e:
            print(f"[constraint_sync] global publish failed: {e}")


# ── Öğretmen saat sahipliği (rezervasyon defteri) ─────────────────────
# Bir öğretmenin her (gün, saat) hücresi EN FAZLA tek bir kuruma aittir. Sahiplik iki
# yoldan doğar:
#   * otomatik  — bir kurum o saate ders yerleştirdiğinde (aktif çizelgeden okunur),
#   * elle      — kullanıcı "bu saat bizim" diyerek önceden rezerve ettiğinde.
# Bir hücreyi X kurumu tuttuysa, diğer TÜM kurumlarda kapalı görünür. Kurum sayısı
# arttıkça (A, B, C, D...) kural değişmez: defter tek, sahip tek.

def _reservations_path() -> str:
    """Eski, tek bilgisayara özel defterin yolu. Yalnızca göç (migration) için okunur."""
    return os.path.join(os.path.expanduser("~"), ".chenki_akademi", "teacher_reservations.json")


# Rezervasyonlar artık kurumun KENDİ meta.json dosyasında durur:
#   meta["teacher_reservations"] = {"updated": <iso>, "slots": {ogretmen: ["gun,saat", ...]}}
# meta.json zaten VDS ile çift yönlü senkronize edildiği için rezervasyonlar da her
# bilgisayardan görünür ve düzenlenebilir hale gelir; ayrı bir sunucu ucu gerekmez.
#
# Her kurum yalnızca kendi dosyasına yazdığı için "başkasının saatini çalma" koruması
# artık bir kod kontrolü değil, yapının kendisi: X kurumunun rezervasyonlarını
# değiştirebilecek tek yer X'in meta dosyasıdır.

def _inst_meta_path(slug: str) -> str:
    from version_store import _base_dir
    return os.path.join(_base_dir(), slug, "meta.json")


def _read_inst_meta(slug: str, strict: bool = False) -> dict:
    return _read_shared(_inst_meta_path(slug), strict=strict)


def _institution_exists(slug: str) -> bool:
    """A write must never conjure an institution into being.

    _write_shared creates missing parent directories, so writing to the meta path of a
    slug that does not exist would silently create a whole institution folder — one
    that then shows up in the dashboard and gets pushed to the cloud.
    """
    return bool(slug) and os.path.isfile(_inst_meta_path(slug))


def _own_reservations(slug: str) -> dict:
    """{ogretmen_anahtari: set((gun, saat))} — bu kuruma ait rezervasyonlar."""
    block = (_read_inst_meta(slug) or {}).get("teacher_reservations") or {}
    slots = block.get("slots") if isinstance(block, dict) else None
    result = {}
    if not isinstance(slots, dict):
        return result
    for key, cells in slots.items():
        if not isinstance(cells, (list, tuple)):
            continue
        parsed = set()
        for cell in cells:
            try:
                d_str, p_str = str(cell).split(",")
                parsed.add((int(d_str), int(p_str)))
            except (ValueError, TypeError):
                continue
        if parsed:
            result[key] = parsed
    return result


def _all_institution_slugs() -> list:
    try:
        from version_store import list_institutions
        return [i.get("slug") for i in list_institutions() if i.get("slug")]
    except Exception:
        return []


def load_reservations() -> dict:
    """{normalize_edilmis_ogretmen: {"gun,saat": kurum_slug}} — tüm kurumların birleşimi.

    Eski yerel defter hâlâ varsa, henüz göç etmemiş kayıtları için geri dönüş olarak
    okunur; bir kuruma ait kayıt her iki yerde de varsa meta.json kazanır.
    """
    merged = {}
    legacy = _read_shared(_reservations_path())
    for key, cells in (legacy or {}).items():
        if isinstance(cells, dict):
            merged.setdefault(key, {}).update(cells)

    for slug in _all_institution_slugs():
        for key, slots in _own_reservations(slug).items():
            bucket = merged.setdefault(key, {})
            for (d, p) in slots:
                bucket[f"{d},{p}"] = slug
    return merged


def _norm_teacher(name: str) -> str:
    try:
        from version_store import normalize_teacher_name
        return normalize_teacher_name(name)
    except Exception:
        return (name or "").strip().upper()


def set_reservation(slug: str, teacher_name: str, slot: tuple, owned: bool):
    """Bir hücreyi bu kuruma rezerve eder ya da rezervasyonu kaldırır.

    Başka bir kuruma ait bir hücre burada devralınmaz — sahipliği o kurum bırakmalıdır;
    aksi halde iki kurum birbirinin saatini sessizce çalabilirdi.
    Dönüş: True = işlem yapıldı, False = hücre başka kuruma ait.
    """
    key = _norm_teacher(teacher_name)
    if not slug or not key or not _institution_exists(slug):
        return False
    d, p = slot
    cell = f"{d},{p}"

    with _STORE_LOCK:
        # Someone else's claim still wins, and it lives in THEIR meta file — which this
        # institution never writes — so the check is a courtesy for the UI, not the
        # thing that keeps the ledgers apart.
        current_owner = load_reservations().get(key, {}).get(cell)
        if current_owner and current_owner != slug:
            return False

        try:
            meta = _read_inst_meta(slug, strict=True)
        except SharedStoreUnreadable as e:
            print(f"[constraint_sync] kurum meta dosyası okunamadı, işlem atlandı: {e}")
            return False
        if not meta:
            return False

        block = meta.get("teacher_reservations")
        if not isinstance(block, dict):
            block = {}
        slots = block.get("slots")
        if not isinstance(slots, dict):
            slots = {}

        cells = [c for c in (slots.get(key) or []) if isinstance(c, str)]
        if owned:
            if cell not in cells:
                cells.append(cell)
        else:
            cells = [c for c in cells if c != cell]

        if cells:
            slots[key] = sorted(set(cells))
        else:
            slots.pop(key, None)

        from datetime import datetime as _dt
        meta["teacher_reservations"] = {"updated": _dt.now().isoformat(), "slots": slots}

        try:
            _write_shared(_inst_meta_path(slug), meta)
        except Exception as e:
            print(f"[constraint_sync] rezervasyon kaydedilemedi: {e}")
            return False

    # Push outside the lock: the network call must not hold up other reservation edits.
    try:
        import threading as _th
        import cloud_sync
        _th.Thread(target=cloud_sync.push_institution_to_rtdb, args=(slug,), daemon=True).start()
    except Exception:
        pass
    return True


def migrate_local_reservations() -> int:
    """Eski tek-bilgisayarlık defteri kurumların meta.json dosyalarına taşır.

    Bir kez çalışır: taşınan kayıtlar artık VDS üzerinden diğer bilgisayarlara da
    gider. Eski dosya, sorun çıkarsa geri dönülebilsin diye silinmez, `.migrated`
    uzantısıyla saklanır.
    """
    path = _reservations_path()
    legacy = _read_shared(path)
    if not legacy:
        return 0

    known = set(_all_institution_slugs())
    by_slug = {}
    for key, cells in legacy.items():
        if not isinstance(cells, dict):
            continue
        for cell, slug in cells.items():
            if slug in known:
                by_slug.setdefault(slug, {}).setdefault(key, []).append(cell)

    moved = 0
    from datetime import datetime as _dt
    for slug, slots in by_slug.items():
        if not _institution_exists(slug):
            continue
        try:
            meta = _read_inst_meta(slug, strict=True)
        except SharedStoreUnreadable:
            continue
        if not meta:
            continue
        block = meta.get("teacher_reservations")
        existing = block.get("slots") if isinstance(block, dict) else None
        if not isinstance(existing, dict):
            existing = {}
        for key, cells in slots.items():
            existing[key] = sorted(set((existing.get(key) or []) + cells))
            moved += len(cells)
        meta["teacher_reservations"] = {"updated": _dt.now().isoformat(), "slots": existing}
        try:
            _write_shared(_inst_meta_path(slug), meta)
        except Exception as e:
            print(f"[constraint_sync] migration write failed for {slug}: {e}")

    if moved:
        try:
            os.replace(path, path + ".migrated")
        except Exception:
            pass
        print(f"[constraint_sync] {moved} rezervasyon kurum meta dosyalarına taşındı (artık VDS ile senkron).")
    return moved


def reservations_for(teacher_name: str) -> dict:
    """{(gun, saat): kurum_slug} — bu öğretmen için tüm elle rezervasyonlar."""
    key = _norm_teacher(teacher_name)
    result = {}
    bucket = load_reservations().get(key)
    if not isinstance(bucket, dict):
        return result
    for cell, slug in bucket.items():
        try:
            d_str, p_str = str(cell).split(",")
            result[(int(d_str), int(p_str))] = slug
        except (ValueError, TypeError):
            continue
    return result


def reserved_by_others(exclude_slug: str) -> dict:
    """{normalize_edilmis_ogretmen: {(gun, saat), ...}} — BAŞKA kurumlara ait saatler."""
    result = {}
    for key, cells in (load_reservations() or {}).items():
        if not isinstance(cells, dict):
            continue
        for cell, slug in cells.items():
            if not slug or slug == exclude_slug:
                continue
            try:
                d_str, p_str = str(cell).split(",")
                result.setdefault(key, set()).add((int(d_str), int(p_str)))
            except (ValueError, TypeError):
                continue
    return result


def shared_teacher_states(exclude_slug: str, day_count: int, periods: int) -> dict:
    """DİĞER kurumlarda tanımlı öğretmen kısıtlamalarının birleşimi.

    Dönen: {normalize_edilmis_ogretmen_adi: {(gun, saat): durum}} — yalnızca açık
    OLMAYAN hücreler yer alır. Bir öğretmen üç, dört kurumda birden çalışsa bile bu
    birleşim doğal olarak ölçeklenir: her kurum kendi payını yazar, okuyan taraf
    hepsinin en kısıtlayıcı halini görür.
    """
    result = {}
    try:
        from version_store import normalize_teacher_name
    except Exception:
        def normalize_teacher_name(x):
            return (x or "").strip().upper()

    def absorb(slug, entries):
        if slug == exclude_slug or not isinstance(entries, dict):
            return
        # Yalnızca KİŞİSEL kısıt zarfı başka kurumu bağlar. Zarfsız (eski) kayıt,
        # o kurumun kendi çalışma saatleridir; onu buraya taşımak, öğretmenin
        # her kurumdaki kapalı saatlerini üst üste bindirip kimsenin ders
        # koyamamasına yol açıyordu.
        if "kind" in entries or "slots" in entries:
            if entries.get("kind") != SHARE_KIND:
                return
            entries = entries.get("slots") or {}
            if not isinstance(entries, dict):
                return
        else:
            return
        for name, cells in entries.items():
            if not isinstance(cells, dict):
                continue
            norm = normalize_teacher_name(name)
            if not norm:
                continue
            bucket = result.setdefault(norm, {})
            for key, raw in cells.items():
                try:
                    d_str, p_str = str(key).split(",")
                    d, p = int(d_str), int(p_str)
                except (ValueError, TypeError):
                    continue
                if not (0 <= d < day_count and 0 <= p < periods):
                    continue
                state = _coerce_state(raw)
                if state == OPEN:
                    continue
                slot = (d, p)
                bucket[slot] = min(bucket.get(slot, OPEN), state)

    # The local cache first, then each institution's own synced copy. The meta files
    # are what make this work on a second computer, where the cache starts out empty.
    for slug, entries in (load_global() or {}).items():
        absorb(slug, entries)

    for slug in _all_institution_slugs():
        block = (_read_inst_meta(slug) or {}).get("teacher_availability") or {}
        if isinstance(block, dict):
            # Zarfın kendisi geçilir: absorb, "kind" etiketine bakarak bunun
            # kişisel kısıt mı yoksa o kurumun kendi saatleri mi olduğunu ayırır.
            absorb(slug, block)

    return result
