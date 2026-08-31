"""
version_store.py — Kurum, Versiyon, Şifreli Erişim ve Çapraz Çakışma Yönetim Modülü
Her kurum bir klasör, her oto/manuel kayıt bir .roz versiyon dosyası.
"""
import copy
import os
import json
import re
import shutil
import hashlib
from datetime import datetime

def _base_dir():
    return os.path.join(os.path.expanduser("~"), ".chenki_akademi", "institutions")


def _institution_dir(slug: str) -> str:
    return os.path.join(_base_dir(), slug)


def _atomic_write_json(path: str, payload) -> bool:
    """Writes JSON via a temp file + os.replace so a crash can't leave a half file."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    import time
    tmp_path = f"{path}.{os.getpid()}_{int(time.time()*1000)}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        replaced = False
        for attempt in range(5):
            try:
                os.replace(tmp_path, path)
                replaced = True
                break
            except OSError:
                time.sleep(0.02 * (attempt + 1))

        if not replaced:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
                f.flush()
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
        return True
    except Exception as exc:
        print(f"[version_store] atomic write failed for {path}: {exc}")
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return False

def _ensure_base():
    d = _base_dir()
    os.makedirs(d, exist_ok=True)
    return d

def slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[ğ]", "g", s)
    s = re.sub(r"[ü]", "u", s)
    s = re.sub(r"[ş]", "s", s)
    s = re.sub(r"[ı]", "i", s)
    s = re.sub(r"[ö]", "o", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[İ]", "i", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s or "kurum"

def normalize_teacher_name(name: str) -> str:
    """Normalizes teacher names for cross-institution comparison (case and whitespace insensitive)."""
    if not name:
        return ""
    s = name.strip().upper()
    s = s.replace("İ", "I").replace("ı", "I")
    s = s.replace("Ş", "S").replace("ş", "S")
    s = s.replace("Ğ", "G").replace("ğ", "G")
    s = s.replace("Ü", "U").replace("ü", "U")
    s = s.replace("Ö", "O").replace("ö", "O")
    s = s.replace("Ç", "C").replace("ç", "C")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def _matches_teacher(t1: str, t2: str) -> bool:
    """Smart fuzzy/normalized teacher name matcher."""
    if not t1 or not t2:
        return False
    n1 = normalize_teacher_name(t1)
    n2 = normalize_teacher_name(t2)
    if n1 == n2:
        return True
    # Strip non-alphanumeric
    c1 = "".join(c for c in n1 if c.isalnum())
    c2 = "".join(c for c in n2 if c.isalnum())
    if c1 == c2:
        return True
    # Handle single name / middle name variations (e.g. Şeyma Aker vs Şeyma Nur Aker)
    p1 = [p for p in n1.split() if len(p) > 1]
    p2 = [p for p in n2.split() if len(p) > 1]
    if len(p1) >= 2 and len(p2) >= 2:
        # If first and last words match
        if p1[0] == p2[0] and p1[-1] == p2[-1]:
            return True
    return False

def rename_teacher_in_data_store(data_store: dict, old_name: str, new_name: str) -> bool:
    """
    Atomically cascades teacher renaming across the entire data_store and institution version files.
    """
    if not old_name or not new_name or old_name.strip() == new_name.strip():
        return False
        
    old_clean = old_name.strip()
    new_clean = new_name.strip()
    old_norm = normalize_teacher_name(old_clean)
    
    # 1. Update in ogretmenler list
    for t in data_store.get("ogretmenler", []):
        if normalize_teacher_name(t.get("ad", "")) == old_norm or t.get("ad", "").strip() == old_clean:
            t["ad"] = new_clean
            
    # 2. Update in atamalar list
    for a in data_store.get("atamalar", []):
        raw_t = a.get("teacher") or a.get("ogretmen") or a.get("teacher_name") or ""
        parts = [p.strip() for p in raw_t.split(",") if p.strip()]
        new_parts = []
        for p in parts:
            if normalize_teacher_name(p) == old_norm or p == old_clean:
                new_parts.append(new_clean)
            else:
                new_parts.append(p)
        if new_parts:
            a["teacher"] = ", ".join(new_parts)
            if "teacher_name" in a:
                a["teacher_name"] = ", ".join(new_parts)
                
    # 3. Update in grid_placements list
    for p in data_store.get("grid_placements", []):
        t_name = p.get("teacher_name") or p.get("teacher") or ""
        if normalize_teacher_name(t_name) == old_norm or t_name.strip() == old_clean:
            p["teacher_name"] = new_clean
            p["teacher"] = new_clean
            
    # 4. Update in siniflar (sinif_ogretmeni / rehberlik)
    for s in data_store.get("siniflar", []):
        so = s.get("sinif_ogretmeni", "")
        if normalize_teacher_name(so) == old_norm or so.strip() == old_clean:
            s["sinif_ogretmeni"] = new_clean
            
    # 5. Update in yerlesim
    yerlesim = data_store.get("yerlesim", {})
    if isinstance(yerlesim, dict):
        for k, v in yerlesim.items():
            if isinstance(v, dict):
                t_val = v.get("teacher_name") or v.get("teacher") or ""
                if normalize_teacher_name(t_val) == old_norm or t_val.strip() == old_clean:
                    v["teacher_name"] = new_clean
                    v["teacher"] = new_clean
                    
    # 6. Update in kisitlamalar
    kisit = data_store.get("kisitlamalar", {})
    if isinstance(kisit, dict):
        if old_clean in kisit:
            kisit[new_clean] = kisit.pop(old_clean)
        if old_norm in kisit:
            kisit[new_clean] = kisit.pop(old_norm)
            
    return True

def sanitize_atamalar(atamalar: list) -> list:
    """
    Sanitizes, validates, and strictly deduplicates lesson assignments (atamalar).
    Guarantees:
    - No duplicate (subject, teacher, class) entries.
    - Cleans comma-separated duplicates in teacher strings (e.g. 'Beyza Bulut, Beyza Bulut' -> 'Beyza Bulut').
    - Standardizes duration and type fields.
    """
    if not atamalar or not isinstance(atamalar, list):
        return []
        
    seen = {}
    for a in atamalar:
        if not isinstance(a, dict):
            continue
            
        subj = str(a.get("subject") or a.get("ders") or a.get("subject_name") or "").strip()
        if not subj:
            continue
            
        raw_t = str(a.get("teacher") or a.get("ogretmen") or a.get("teacher_name") or "").strip()
        # Deduplicate comma-separated teacher strings e.g. "Beyza Bulut, Beyza Bulut"
        t_parts = [p.strip() for p in raw_t.split(",") if p.strip()]
        unique_t_parts = []
        for p in t_parts:
            if p not in unique_t_parts:
                unique_t_parts.append(p)
        teacher = ", ".join(unique_t_parts)
        
        cls_name = str(a.get("class") or a.get("sinif") or a.get("class_name") or "").strip()
        
        # Calculate duration and type
        raw_type = str(a.get("type", "")).strip()
        if raw_type == "0" or raw_type == "None":
            raw_type = ""
            
        parts = [int(p.strip()) for p in raw_type.split("+") if p.strip().isdigit()]
        if parts:
            dur = sum(parts)
        elif raw_type.isdigit():
            dur = int(raw_type)
        else:
            dur_val = a.get("duration") if a.get("duration") is not None else a.get("saat")
            dur = int(dur_val) if (dur_val is not None and str(dur_val).isdigit()) else 0
            if dur > 0 and not raw_type:
                raw_type = str(dur)
        
        key = (subj.upper(), teacher.upper(), cls_name.upper())
        clean_entry = dict(a)
        clean_entry["subject"] = subj
        clean_entry["teacher"] = teacher
        clean_entry["class"] = cls_name
        clean_entry["duration"] = dur
        clean_entry["type"] = raw_type

        # Aynı bilgiyi taşıyan ESKİ alanları da güncelle. Satır bir kez öğretmen
        # ekranından kaydedildiğinde ders_sayisi/saat/dagilim alanları da yazılıyor;
        # sonra sınıf ekranı yalnızca duration+type güncellediği için o alanlar eski
        # değerde kalıyordu. Öğretmen ekranı, öğretmen kartı ve otomatik planlayıcı
        # ders_sayisi'ni ÖNCE okuduğundan, iki ekran aynı ders için farklı saat
        # gösteriyor, planlayıcı da yanlış sayıda saat yerleştiriyordu.
        try:
            import lesson_hours
            lesson_hours.sync_keys(clean_entry)
        except Exception:
            pass

        seen[key] = clean_entry
        
    return list(seen.values())

_cross_busy_cache = {}  # exclude_slug -> (monotonic_timestamp, result_dict)
_CROSS_BUSY_CACHE_TTL = 4.0  # seconds

def invalidate_cross_busy_cache():
    """Drops the cross-institution conflict map. Called whenever a schedule is saved."""
    _cross_busy_cache.clear()

def get_cross_institution_teacher_busy_slots(exclude_slug: str = None) -> dict:
    """Busy slots for every teacher across all OTHER institutions.

    Key:   (normalized_teacher_name, day_index, period_index)
    Value: dict describing the clashing lesson.

    main_window._on_lesson_dropped calls this synchronously on every single manual
    lesson placement, and it reads and JSON-parses each other institution's entire
    active schedule from disk. With a handful of institutions that is tens of
    megabytes of parsing per drop, on the GUI thread, which is a large part of why
    releasing a lesson felt like it froze.

    A short TTL cache fixes that: cross-institution schedules are not being edited
    from under you mid-drag, so a few seconds of staleness costs nothing, while the
    disk work per drag is what actually hurt. save_db invalidates it explicitly, so
    an edit here is reflected immediately rather than after the TTL.

    NOTE: this module previously defined this function TWICE. The second definition
    (further down the file) silently replaced this one at import time, so the cache
    above was dead code that never ran. The two also returned different key names —
    the caller reads "subject"/"class", which only the second version emitted. Both
    naming schemes are emitted below so either caller shape keeps working.
    """
    import time as _time
    now = _time.monotonic()
    cached = _cross_busy_cache.get(exclude_slug)
    if cached and (now - cached[0]) < _CROSS_BUSY_CACHE_TTL:
        return cached[1]

    busy_slots = {}

    for inst in list_institutions():
        inst_slug = inst["slug"]
        if exclude_slug and inst_slug == exclude_slug:
            continue

        active_ver = inst.get("active_version")
        if not active_ver:
            vers = list_versions(inst_slug, source_filter="all")
            if vers:
                active_ver = vers[0]["filename"]
        if not active_ver:
            continue

        data = load_version(inst_slug, active_ver)
        if not data:
            continue

        inst_name = inst.get("name", inst_slug)
        periods = int((data.get("settings") or {}).get("periods", 8)) or 8

        for item in data.get("grid_placements", []):
            t_name = (item.get("teacher_name") or item.get("teacher") or item.get("ogretmen") or "").strip()
            if not t_name:
                continue
            norm_t = normalize_teacher_name(t_name)
            if not norm_t:
                continue

            if "day" in item:
                day = int(item.get("day") or 0)
            else:
                day = int(item.get("col", 0)) // periods
            if "period" in item:
                period = int(item.get("period") or 0)
            elif "col" in item:
                period = int(item.get("col", 0)) % periods
            else:
                period = int(item.get("row", 0))

            dur = max(1, int(item.get("duration", 1) or 1))
            c_name = item.get("class_name") or item.get("class") or ""
            s_name = item.get("subject_name") or item.get("subject") or "Ders"
            clean_k = "".join(c for c in norm_t.lower() if c.isalnum())

            for off in range(dur):
                slot_p = period + off
                key = (norm_t, day, slot_p)
                existing = busy_slots.get(key)
                if existing is not None:
                    # Same teacher already double-booked at this slot by another
                    # institution: merge the names rather than hiding one of them.
                    if inst_name not in existing["institution_name"]:
                        existing["institution_name"] += f", {inst_name}"
                    if c_name and c_name not in (existing.get("class") or ""):
                        existing["class"] = f"{existing['class']} / {c_name}" if existing.get("class") else c_name
                        existing["class_name"] = existing["class"]
                    continue

                slot_info = {
                    "institution_slug": inst_slug,
                    "institution_name": inst_name,
                    "teacher_name": t_name,
                    # Both key spellings: "subject"/"class" is what the conflict
                    # dialog reads, "subject_name"/"class_name" matches the rest of
                    # the data model.
                    "subject": s_name,
                    "subject_name": s_name,
                    "class": c_name,
                    "class_name": c_name,
                    "version_filename": active_ver,
                    "day": day,
                    "period": slot_p,
                }
                busy_slots[key] = slot_info
                busy_slots[(clean_k, day, slot_p)] = slot_info

    _cross_busy_cache[exclude_slug] = (now, busy_slots)
    return busy_slots

# ── Password & Security ──────────────────────────────────────────────

def _hash_password(password: str) -> str:
    salt = "chenki_akademi_secure_salt_2026"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

# Keys that change on every save without the schedule itself changing. Must match
# sync_core.VOLATILE_KEYS on the VDS exactly, or the two sides disagree about what a
# duplicate is and dedup silently stops working.
_VOLATILE_KEYS = ("_version_meta", "_sync_meta", "last_modified", "data_hash")


def compute_data_hash(data_store: dict) -> str:
    """Deterministic content hash used for change detection AND duplicate detection.

    Byte-for-byte identical to the server's sync_core.canonical_hash, so a version
    the client considers a duplicate is one the server will fold together too.

    Runs on the GUI thread on every grid edit (save_db -> update_version_in_place),
    so it stays a shallow filter plus one json.dumps: json.dumps only reads the
    nested structures, so there is no need to deep-copy them first.
    """
    if not data_store:
        return hashlib.sha256(b"").hexdigest()
    stripped = {k: v for k, v in data_store.items() if k not in _VOLATILE_KEYS}
    try:
        canonical = json.dumps(
            stripped, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), default=str,
        )
    except Exception:
        canonical = repr(sorted(stripped.keys()))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

# ── Device Password Cache ────────────────────────────────────────────

import uuid as _uuid

def _get_device_id() -> str:
    """Returns a persistent device UUID, creating one if it doesn't exist."""
    device_path = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "device_id.json")
    if os.path.exists(device_path):
        try:
            with open(device_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                did = data.get("device_id", "")
                if did:
                    return did
        except Exception:
            pass
    did = str(_uuid.uuid4())
    try:
        os.makedirs(os.path.dirname(device_path), exist_ok=True)
        with open(device_path, "w", encoding="utf-8") as f:
            json.dump({"device_id": did}, f)
    except Exception:
        pass
    return did

def save_device_password_cache(slug: str, password: str):
    """Caches a successful password entry for this device so the user won't be asked again."""
    cache_path = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "device_pwd_cache.json")
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}
    device_id = _get_device_id()
    cache[f"{device_id}_{slug}"] = _hash_password(password)
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def check_device_password_cache(slug: str) -> bool:
    """Returns True if this device has previously entered the correct password for this institution."""
    meta = get_institution_meta(slug)
    if not meta.get("has_password", False) or not meta.get("password_hash"):
        return True  # No password required
    cache_path = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "device_pwd_cache.json")
    if not os.path.exists(cache_path):
        return False
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        device_id = _get_device_id()
        cached_hash = cache.get(f"{device_id}_{slug}", "")
        return cached_hash == meta.get("password_hash", "")
    except Exception:
        return False

def set_institution_password(slug: str, password: str):
    """Sets or updates the password for an institution."""
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {"name": slug}
            
        if password:
            meta["password_hash"] = _hash_password(password)
            meta["has_password"] = True
        else:
            meta.pop("password_hash", None)
            meta["has_password"] = False
            
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
            
        try:
            import cloud_sync
            cloud_sync.push_institution_to_rtdb(slug)
        except Exception as e:
            print(f"Cloud sync error on password set: {e}")

def remove_institution_password(slug: str):
    """Removes the password protection from an institution."""
    set_institution_password(slug, "")

def verify_institution_password(slug: str, password: str) -> bool:
    """Verifies a password against an institution's stored hash."""
    meta = get_institution_meta(slug)
    if not meta.get("has_password", False):
        return True  # No password set
    stored_hash = meta.get("password_hash", "")
    if not stored_hash:
        return True
    return stored_hash == _hash_password(password)

def has_institution_password(slug: str) -> bool:
    meta = get_institution_meta(slug)
    return bool(meta.get("has_password", False) and meta.get("password_hash"))


# ── Account-level institution trust ──────────────────────────────────
#
# The institution password is a barrier for OTHER accounts, not for the
# person who owns/knows it — so "trust" is recorded against the logged-in
# USER (their email), stored in meta.json (which syncs across devices via
# push_institution_to_rtdb), NOT against the machine. That's the fix for
# "I set this institution's password, why am I asked for it again on my
# other PC": once an account has proven it knows the password (or set it),
# that account is trusted on every device it signs into. The per-device
# cache above still exists as a fallback for offline/unsynced cases.

def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


def add_trusted_user(slug: str, email: str):
    """Records that this account is trusted for this institution and syncs
    it. Called both when someone SETS the password (they own it) and when
    someone successfully ENTERS it (they've proven they know it)."""
    email = _norm_email(email)
    if not slug or not email:
        return
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    if not os.path.exists(meta_path):
        return
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return
    trusted = meta.get("trusted_users") or []
    if email in trusted:
        return
    trusted.append(email)
    meta["trusted_users"] = trusted
    try:
        _atomic_write_json(meta_path, meta)
        _invalidate_meta_cache(slug)
    except Exception:
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            return
    try:
        import cloud_sync
        cloud_sync.push_institution_to_rtdb(slug)
    except Exception as e:
        print(f"Cloud sync error on trusted-user add: {e}")


def is_trusted_user(slug: str, email: str) -> bool:
    email = _norm_email(email)
    if not email:
        return False
    meta = get_institution_meta(slug)
    return email in (meta.get("trusted_users") or [])

# ── Institution CRUD ─────────────────────────────────────────────────

INSTITUTION_COLORS = [
    "#0071E3", "#34C759", "#AF52DE", "#FF9500", "#FF2D55",
    "#5856D6", "#00C7BE", "#32ADE6", "#A2845E", "#64D2FF",
]

def touch_institution_timestamp(slug: str) -> str:
    """Stamps meta.json with the current time. Returns the display string."""
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    now = datetime.now()
    upd_str = now.strftime("%d %b %H:%M")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["last_modified"] = now.isoformat()
            meta["last_updated_str"] = upd_str
            meta.pop("versions", None)  # never let version payloads settle in here
            _atomic_write_json(meta_path, meta)
            _invalidate_meta_cache(slug)
        except Exception:
            pass
    return upd_str


def get_last_active_institution_slug() -> str:
    path = os.path.join(_base_dir(), "active_institution.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("last_active_slug", "")
        except Exception:
            return ""
    return ""

def set_last_active_institution_slug(slug: str):
    if not slug: return
    path = os.path.join(_base_dir(), "active_institution.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"last_active_slug": slug}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def list_institutions():
    """Returns list of dicts: {slug, name, created, color, version_count, path, has_password, active_version, last_updated_str}"""
    base = _ensure_base()
    result = []
    for entry in sorted(os.listdir(base)):
        if entry.startswith("_system_") or entry.startswith("_auth_") or entry in ("backups", "temp", "cache"):
            continue
        inst_dir = os.path.join(base, entry)
        meta_path = os.path.join(inst_dir, "meta.json")
        if os.path.isdir(inst_dir) and os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}
            ver_dir = os.path.join(inst_dir, "versions")
            ver_count = 0
            if os.path.isdir(ver_dir):
                ver_count = len([v for v in os.listdir(ver_dir) if v.endswith(".roz")])
                
            last_upd_str = meta.get("last_updated_str")
            if not last_upd_str:
                vers = list_versions(entry, source_filter="all")
                if vers:
                    last_upd_str = f"{vers[0]['date_str']} {vers[0]['time_str']}"
                else:
                    last_upd_str = meta.get("created", "")
                    
            is_prim = bool(meta.get("is_primary", False))
            result.append({
                "slug": entry,
                "name": meta.get("name", entry),
                "created": meta.get("created", ""),
                "color": meta.get("color", "#0071E3"),
                "version_count": ver_count,
                "has_password": bool(meta.get("has_password", False) and meta.get("password_hash")),
                "active_version": meta.get("active_version", ""),
                "last_updated_str": last_upd_str or "",
                "is_primary": is_prim,
                "path": inst_dir,
            })
    # If no primary is set, auto-designate bogazici_egitim_kurumlari or first institution
    has_primary = any(x.get("is_primary") for x in result)
    if not has_primary and result:
        bogazici_found = False
        for x in result:
            if x["slug"] == "bogazici_egitim_kurumlari":
                x["is_primary"] = True
                set_primary_institution("bogazici_egitim_kurumlari")
                bogazici_found = True
                break
        if not bogazici_found and result:
            result[0]["is_primary"] = True
            set_primary_institution(result[0]["slug"])
            
    last_slug = get_last_active_institution_slug()
    result.sort(key=lambda x: (
        0 if x.get("is_primary") else (1 if (last_slug and x["slug"] == last_slug) else 2),
        -(os.path.getmtime(x["path"]) if os.path.exists(x["path"]) else 0)
    ))
    return result

def set_primary_institution(primary_slug: str):
    """Marks the specified institution as the primary 'Ana Kurum', and unmarks all others."""
    base = _ensure_base()
    if not os.path.exists(base):
        return
    for entry in os.listdir(base):
        meta_path = os.path.join(base, entry, "meta.json")
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["is_primary"] = (entry == primary_slug)
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                try:
                    import threading
                    import cloud_sync
                    threading.Thread(target=cloud_sync.push_institution_to_rtdb, args=(entry,), daemon=True).start()
                except Exception:
                    pass
            except Exception as e:
                print(f"Error setting primary institution for {entry}: {e}")

def get_primary_institution_slug() -> str:
    """Returns the slug of the primary 'Ana Kurum' institution."""
    base = _ensure_base()
    if not os.path.exists(base):
        return "bogazici_egitim_kurumlari"
    for entry in os.listdir(base):
        meta_path = os.path.join(base, entry, "meta.json")
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if meta.get("is_primary"):
                    return entry
            except Exception:
                pass
    if os.path.exists(os.path.join(base, "bogazici_egitim_kurumlari")):
        set_primary_institution("bogazici_egitim_kurumlari")
        return "bogazici_egitim_kurumlari"
    insts = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
    return insts[0] if insts else "bogazici_egitim_kurumlari"

def create_institution(name: str, color: str = None, password: str = "") -> dict:
    """Creates a new institution folder. Returns its metadata dict."""
    base = _ensure_base()
    slug = slugify(name)
    
    # Ensure unique slug
    existing = set(os.listdir(base))
    orig_slug = slug
    counter = 2
    while slug in existing:
        slug = f"{orig_slug}_{counter}"
        counter += 1
    
    inst_dir = os.path.join(base, slug)
    os.makedirs(os.path.join(inst_dir, "versions"), exist_ok=True)
    
    if not color:
        idx = len(existing) % len(INSTITUTION_COLORS)
        color = INSTITUTION_COLORS[idx]
    
    meta = {
        "name": name.strip(),
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "color": color,
        "active_version": None,
        "has_password": bool(password),
        "password_hash": _hash_password(password) if password else "",
    }
    with open(os.path.join(inst_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    # Automatically create initial empty version for this institution
    ensure_institution_has_version(slug)
    
    try:
        import threading
        import cloud_sync
        threading.Thread(target=cloud_sync.push_institution_to_rtdb, args=(slug,), daemon=True).start()
    except Exception:
        pass
        
    return {"slug": slug, **meta, "version_count": 1, "path": inst_dir}

def rename_institution(slug: str, new_name: str):
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {"name": slug}
            
        meta["name"] = new_name.strip()
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
            
        try:
            import threading
            import cloud_sync
            threading.Thread(target=cloud_sync.push_institution_to_rtdb, args=(slug,), daemon=True).start()
        except Exception:
            pass

def set_institution_color(slug: str, color: str):
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {"name": slug}
            
        meta["color"] = color
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
            
        try:
            import threading
            import cloud_sync
            threading.Thread(target=cloud_sync.push_institution_to_rtdb, args=(slug,), daemon=True).start()
        except Exception:
            pass

def delete_institution(slug: str):
    inst_dir = os.path.join(_base_dir(), slug)
    if os.path.isdir(inst_dir):
        try:
            shutil.rmtree(inst_dir, ignore_errors=True)
        except Exception:
            pass
        if os.path.isdir(inst_dir):
            try:
                for root, dirs, files in os.walk(inst_dir, topdown=False):
                    for name in files:
                        try:
                            os.remove(os.path.join(root, name))
                        except Exception:
                            pass
                    for name in dirs:
                        try:
                            os.rmdir(os.path.join(root, name))
                        except Exception:
                            pass
                os.rmdir(inst_dir)
            except Exception:
                pass

    _invalidate_meta_cache(slug)
        
    tomb_file = os.path.join(_base_dir(), "deleted_institutions.json")
    try:
        tomb = []
        if os.path.exists(tomb_file):
            with open(tomb_file, "r", encoding="utf-8") as f:
                tomb = json.load(f)
        if slug not in tomb:
            tomb.append(slug)
        with open(tomb_file, "w", encoding="utf-8") as f:
            json.dump(tomb, f)
    except Exception:
        pass
        
    try:
        import threading
        import cloud_sync
        threading.Thread(target=cloud_sync.delete_institution_from_rtdb, args=(slug,), daemon=True).start()
    except Exception:
        pass

# slug -> (mtime_ns, size, meta_dict). get_institution_meta is called on nearly every
# code path (list_institutions, get_active_version, has_institution_password,
# touch_institution_timestamp, each dashboard card...), so a single refresh reads and
# parses the same meta.json dozens of times.
_meta_cache = {}


def _invalidate_meta_cache(slug: str = None):
    if slug:
        _meta_cache.pop(slug, None)
    else:
        _meta_cache.clear()


def get_institution_meta(slug: str) -> dict:
    """The institution's meta.json.

    Returns a fresh copy each call: callers mutate what they get back (adding
    folders, setting active_version) and handing out the cached dict would let one
    caller's edit leak into everyone else's read.
    """
    if not slug:
        return {}
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    try:
        stat = os.stat(meta_path)
        signature = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        _meta_cache.pop(slug, None)
        return {}

    cached = _meta_cache.get(slug)
    if cached is not None and cached[0] == signature:
        return copy.deepcopy(cached[1])

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return {}
    if not isinstance(meta, dict):
        return {}

    # Defence in depth against the bug that bloated these files: the server used to
    # return the whole version history nested inside "meta", and the client wrote it
    # straight back out here. Drop it on read so an already-damaged install recovers
    # instead of carrying megabytes around forever.
    if "versions" in meta:
        meta.pop("versions", None)
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            stat = os.stat(meta_path)
            signature = (stat.st_mtime_ns, stat.st_size)
        except Exception:
            pass

    _meta_cache[slug] = (signature, meta)
    return copy.deepcopy(meta)

# ── Version Folders ──────────────────────────────────────────────────
# Folders group saved versions under a user-given name (e.g. "Yaz Çizelgesi").
# The folder registry lives in the institution's meta.json (meta["folders"] =
# [{id, name, created}, ...]); which folder a given version belongs to is stored
# inside that version's own _version_meta["folder_id"] (None = no folder / "Genel").

def list_folders(slug: str) -> list:
    """Returns this institution's folders, newest created first: [{id, name, created}, ...]."""
    raw = get_institution_meta(slug).get("folders", [])
    return list(reversed(raw))

def create_folder(slug: str, name: str) -> tuple:
    """Creates a new named folder for organizing versions.

    Returns (folder_dict, created) — created=False means a folder with that name
    (case-insensitive) already existed and was reused rather than duplicated, so the
    caller can warn the user instead of silently pretending a new one was made.
    """
    name = (name or "").strip()
    if not slug or not name:
        return {}, False
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        meta = {"name": slug}

    folders = meta.setdefault("folders", [])
    # Reuse an existing folder with the same (case-insensitive) name instead of duplicating it
    for existing in folders:
        if existing.get("name", "").strip().lower() == name.lower():
            return existing, False

    new_folder = {
        "id": _uuid.uuid4().hex[:10],
        "name": name,
        "created": datetime.now().isoformat(),
    }
    folders.append(new_folder)

    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    try:
        import threading
        import cloud_sync
        threading.Thread(target=cloud_sync.push_institution_to_rtdb, args=(slug,), daemon=True).start()
    except Exception:
        pass

    return new_folder, True

def rename_folder(slug: str, folder_id: str, new_name: str) -> bool:
    """Renames a folder. Returns False (no-op) if new_name is empty or collides
    case-insensitively with a DIFFERENT existing folder; True on success."""
    new_name = (new_name or "").strip()
    if not slug or not folder_id or not new_name:
        return False
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return False

    folders = meta.get("folders", [])
    for other in folders:
        if other.get("id") != folder_id and other.get("name", "").strip().lower() == new_name.lower():
            return False

    changed = False
    for folder in folders:
        if folder.get("id") == folder_id:
            folder["name"] = new_name
            changed = True
            break
    if not changed:
        return False

    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    try:
        import threading
        import cloud_sync
        threading.Thread(target=cloud_sync.push_institution_to_rtdb, args=(slug,), daemon=True).start()
    except Exception:
        pass
    return True

def delete_folder(slug: str, folder_id: str) -> int:
    """Deletes a folder AND every version filed under it (cascading, incl. from the
    cloud) — a folder like "Ağustos ayı" groups a batch of schedules on purpose, so
    removing it should remove what's in it rather than scattering it back into
    "Genel". Returns the number of versions that were deleted."""
    if not slug or not folder_id:
        return 0

    deleted = 0
    for v in list_versions(slug):
        if v.get("folder_id") == folder_id:
            delete_version(slug, v["filename"])
            deleted += 1

    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return deleted

    folders = meta.get("folders", [])
    new_folders = [f for f in folders if f.get("id") != folder_id]
    if len(new_folders) == len(folders):
        return deleted
    meta["folders"] = new_folders

    tomb = meta.setdefault("deleted_folders", [])
    if folder_id not in tomb:
        tomb.append(folder_id)

    try:
        _atomic_write_json(meta_path, meta)
        _invalidate_meta_cache(slug)
    except Exception:
        pass

    try:
        import threading
        import cloud_sync
        threading.Thread(target=cloud_sync.push_institution_to_rtdb, args=(slug,), daemon=True).start()
    except Exception:
        pass
    return deleted

def get_version_folder_id(slug: str, filename: str) -> str | None:
    """Returns the folder_id for a given version filename, or None."""
    if not slug or not filename:
        return None
    try:
        ver_dir = _versions_dir(slug)
        filepath = os.path.join(ver_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("_version_meta", {}).get("folder_id")
    except Exception:
        pass
    return None

def get_folder_name(slug: str, folder_id: str | None) -> str:
    """Returns the human-readable name of a folder (or 'Genel (Klasörsüz)')."""
    if folder_id is None:
        return "Genel (Klasörsüz)"
    for f in list_folders(slug):
        if f.get("id") == folder_id:
            return f.get("name", "Klasör")
    return "Klasör"

def assign_version_folder(slug: str, filename: str, folder_id: str):
    """Moves an already-saved version into a folder (folder_id=None takes it out)."""
    if not slug or not filename:
        return False
    filepath = os.path.join(_versions_dir(slug), filename)
    if not os.path.exists(filepath):
        return False
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False

    meta = data.setdefault("_version_meta", {})
    meta["folder_id"] = folder_id
    # Bump last_modified so the change wins the reconciliation in the cloud pull.
    # Without this the pull compares an unchanged last_modified against the server's
    # copy, decides nothing happened, and silently overwrites the file — putting the
    # version straight back into the folder it was just dragged out of.
    meta["last_modified"] = datetime.now().isoformat()

    if not _atomic_write_json(filepath, data):
        return False

    invalidate_version_summary(slug, filename)

    try:
        import threading
        from cloud_sync import push_version_to_rtdb, push_institution_to_rtdb
        def _sync_bg():
            push_version_to_rtdb(slug, filename, data)
            push_institution_to_rtdb(slug)
        threading.Thread(target=_sync_bg, daemon=True).start()
    except Exception:
        pass
    return True

# ── Version CRUD ─────────────────────────────────────────────────────

def _versions_dir(slug: str) -> str:
    d = os.path.join(_base_dir(), slug, "versions")
    os.makedirs(d, exist_ok=True)
    return d

def _next_version_number(slug: str) -> int:
    ver_dir = _versions_dir(slug)
    max_num = 0
    for f in os.listdir(ver_dir):
        m = re.match(r"v(\d+)_", f)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return max_num + 1

def find_version_by_content(slug: str, data_store: dict) -> str:
    """Filename of an existing version holding identical content, or "".

    Compares the same canonical hash the VDS uses, so client and server agree on
    what counts as a duplicate.
    """
    target = compute_data_hash(data_store)
    if not target:
        return ""
    ver_dir = _versions_dir(slug)
    if not os.path.isdir(ver_dir):
        return ""
    for fn in sorted(os.listdir(ver_dir)):
        if not fn.endswith(".roz"):
            continue
        try:
            with open(os.path.join(ver_dir, fn), "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            continue
        if compute_data_hash(existing) == target:
            return fn
    return ""


def save_version(slug: str, data_store: dict, source: str = "manual", note: str = "",
                 folder_id: str = None, allow_duplicate: bool = False) -> str:
    """Saves a new version and returns its filename.

    If an existing version already holds byte-identical content, that one is
    returned instead of writing a second copy. Saving twice without changing
    anything — closing the editor, pressing save, coming back via Ana Sayfa, each of
    which triggers a save — was creating a fresh v-numbered file every time, which is
    where the run of near-identical "Versiyon 12, 13, 14" entries came from.

    Pass allow_duplicate=True for a deliberate checkpoint the user asked for.
    """
    orig_meta = data_store.get("_version_meta", {}) if isinstance(data_store, dict) else {}
    if folder_id is None and orig_meta.get("folder_id"):
        folder_id = orig_meta.get("folder_id")

    save_data = dict(data_store)
    if "atamalar" in save_data:
        save_data["atamalar"] = sanitize_atamalar(save_data["atamalar"])
    save_data.pop("_version_meta", None)

    if not allow_duplicate:
        twin = find_version_by_content(slug, save_data)
        if twin:
            # Refresh the note/folder on the existing version rather than cloning it.
            if note or folder_id:
                try:
                    twin_path = os.path.join(_versions_dir(slug), twin)
                    with open(twin_path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                    meta = existing.setdefault("_version_meta", {})
                    if note:
                        meta["note"] = note
                    if folder_id:
                        meta["folder_id"] = folder_id
                    with open(twin_path, "w", encoding="utf-8") as f:
                        json.dump(existing, f, ensure_ascii=False, indent=2)
                    invalidate_version_summary(slug, twin)
                except Exception:
                    pass
            set_active_version(slug, twin)
            touch_institution_timestamp(slug)
            return twin

    ver_dir = _versions_dir(slug)
    num = _next_version_number(slug)
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d_%H-%M-%S")
    src_tag = "auto" if source == "auto" else "manual"
    filename = f"v{num:03d}_{ts}_{src_tag}.roz"
    filepath = os.path.join(ver_dir, filename)

    save_data["_version_meta"] = {
        "version_number": num,
        "timestamp": now.isoformat(),
        "last_modified": now.isoformat(),
        "source": src_tag,
        "note": note,
        "filename": filename,
        "folder_id": folder_id,
        "data_hash": compute_data_hash(save_data),
    }

    _atomic_write_json(filepath, save_data)
    invalidate_version_summary(slug, filename)
    _last_written_hash[(slug, filename)] = save_data["_version_meta"]["data_hash"]
    invalidate_cross_busy_cache()

    set_active_version(slug, filename)
    touch_institution_timestamp(slug)

    try:
        import threading
        from cloud_sync import push_version_to_rtdb
        import database
        threading.Thread(target=push_version_to_rtdb, args=(slug, filename, save_data), daemon=True).start()
        threading.Thread(target=database.create_database_backup, args=(slug, "auto_save"), daemon=True).start()
        threading.Thread(target=propagate_primary_timeoff_to_secondary, args=(slug, save_data), daemon=True).start()
    except Exception:
        pass

    return filename

def propagate_primary_timeoff_to_secondary(primary_slug: str, primary_data: dict):
    """
    Boğaziçi'nde (ana kurumda) kısıtlamalar veya dersler değiştiğinde diğer bağlı kurumlara (Birey vb.)
    tam tersi olarak otomatik yansır.
    İkincil kurumlardaki (Birey) değişimler asla ana kuruma (Boğaziçi) yansımaz.
    """
    if not primary_slug or not primary_data:
        return
    if primary_slug != "bogazici_egitim_kurumlari":
        meta = get_institution_meta(primary_slug)
        if not meta.get("is_primary"):
            return  # Yalnızca ana kurum dışa doğru yayılım yapar

    bgz_teachers = {normalize_teacher_name(t.get("ad", "")): t for t in primary_data.get("ogretmenler", []) if t.get("ad")}
    bgz_kisit = primary_data.get("kisitlamalar", {})

    bgz_busy = {}
    for p in primary_data.get("grid_placements", []):
        t_name = p.get("teacher_name") or p.get("teacher") or ""
        if t_name:
            tk = normalize_teacher_name(t_name)
            try:
                d = int(p.get("day", p.get("col", 0)))
                per = int(p.get("period", p.get("row", 0)))
                dur = int(p.get("duration", 1))
                for off in range(dur):
                    bgz_busy.setdefault(tk, set()).add((d, per + off))
            except Exception:
                pass

    for inst in list_institutions():
        sec_slug = inst.get("slug")
        if not sec_slug or sec_slug == primary_slug:
            continue

        sec_active = get_active_version(sec_slug)
        if not sec_active:
            continue
        sec_data = load_version(sec_slug, sec_active)
        if not sec_data:
            continue

        changed = False
        sec_kisit = sec_data.setdefault("kisitlamalar", {})

        for t in sec_data.get("ogretmenler", []):
            t_name = t.get("ad", "").strip()
            if not t_name:
                continue
            tk = normalize_teacher_name(t_name)
            if tk not in bgz_teachers and t_name not in bgz_kisit:
                continue

            bgz_t = bgz_teachers.get(tk)
            bgz_mat = None
            if bgz_t and bgz_t.get("timeoff"):
                bgz_mat = bgz_t.get("timeoff")
            elif t_name in bgz_kisit:
                bgz_mat = [[bgz_kisit[t_name].get(f"{d},{p}", 2) for p in range(4)] for d in range(5)]
            else:
                bgz_mat = [[2, 2, 2, 2] for _ in range(5)]

            inv_mat = []
            inv_dict = {}
            for d in range(5):
                row = []
                for p in range(4):
                    k = f"{d},{p}"
                    v = bgz_mat[d][p] if d < len(bgz_mat) and p < len(bgz_mat[d]) else 2
                    if (d, p) in bgz_busy.get(tk, set()):
                        inv_v = 0
                    elif v == 2:
                        inv_v = 0
                    elif v == 0:
                        inv_v = 2
                    else:
                        inv_v = 1
                    row.append(inv_v)
                    inv_dict[k] = inv_v
                inv_mat.append(row)

            # Tamamen kapalı olanları tam açık bırak
            if all(c == 0 for r in inv_mat for c in r):
                inv_mat = [[2, 2, 2, 2] for _ in range(5)]
                inv_dict = {f"{d},{p}": 2 for d in range(5) for p in range(4)}

            if t.get("timeoff") != inv_mat or sec_kisit.get(t_name) != inv_dict:
                t["timeoff"] = inv_mat
                sec_kisit[t_name] = inv_dict
                changed = True

        if changed:
            update_version_in_place(sec_slug, sec_active, sec_data)
            try:
                import cloud_sync
                cloud_sync.push_version_to_rtdb(sec_slug, sec_active, sec_data)
            except Exception:
                pass


def update_version_in_place(slug: str, filename: str, data_store: dict) -> bool:
    """Overwrites an existing version file with updated data and pushes to cloud with conflict backup.
    Uses hash-based change detection to avoid unnecessary writes and pushes."""
    if not slug or not filename or not data_store:
        return False
    ver_dir = _versions_dir(slug)
    filepath = os.path.join(ver_dir, filename)
    os.makedirs(ver_dir, exist_ok=True)
            
    save_data = dict(data_store)
    if "atamalar" in save_data:
        save_data["atamalar"] = sanitize_atamalar(save_data["atamalar"])

    new_hash = compute_data_hash(save_data)

    cache_key = (slug, filename)
    if new_hash:
        remembered = _last_written_hash.get(cache_key)
        if remembered is not None:
            if remembered == new_hash:
                return True
        elif os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                if compute_data_hash(existing_data) == new_hash:
                    _last_written_hash[cache_key] = new_hash
                    return True
            except Exception:
                pass

    now = datetime.now()
    meta = save_data.setdefault("_version_meta", {})
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                disk_meta = json.load(f).get("_version_meta", {})
            if disk_meta.get("folder_id") and not meta.get("folder_id"):
                meta["folder_id"] = disk_meta["folder_id"]
            if disk_meta.get("note") and not meta.get("note"):
                meta["note"] = disk_meta["note"]
            if disk_meta.get("version_number") and not meta.get("version_number"):
                meta["version_number"] = disk_meta["version_number"]
        except Exception:
            pass
    meta["last_modified"] = now.isoformat()
    meta["data_hash"] = new_hash
    meta.setdefault("filename", filename)

    if not _atomic_write_json(filepath, save_data):
        _last_written_hash.pop(cache_key, None)
        return False

    invalidate_version_summary(slug, filename)
    _last_written_hash[cache_key] = new_hash
    invalidate_cross_busy_cache()
    touch_institution_timestamp(slug)

    try:
        import threading
        from cloud_sync import push_version_to_rtdb
        import database
        threading.Thread(target=push_version_to_rtdb, args=(slug, filename, save_data), daemon=True).start()
        threading.Thread(target=database.create_database_backup, args=(slug, "in_place_update"), daemon=True).start()
        threading.Thread(target=propagate_primary_timeoff_to_secondary, args=(slug, save_data), daemon=True).start()
    except Exception:
        pass
    return True

# filepath -> (mtime, size, parsed_summary_dict)
#
# list_versions() has to look inside each .roz for its note, folder and hour counts,
# which meant fully JSON-parsing every schedule an institution has ever had — on the
# GUI thread, on every dashboard refresh, and refreshes happen on institution
# select, on each cloud poll, after every save and after every folder change. An
# institution with 60 versions of a real timetable is tens of megabytes of parsing
# per click, which is the bulk of the "Anasayfa is unusable" complaint.
#
# The file name and mtime identify the content completely (versions are rewritten in
# place, never appended), so a cache keyed on (mtime, size) is exact rather than
# merely probable — a stale entry is impossible without the file changing.
_version_summary_cache = {}
_VERSION_SUMMARY_CACHE_MAX = 4000


def _version_summary(filepath: str) -> dict:
    """Note, folder and hour counts for one .roz, parsed at most once per revision."""
    try:
        stat = os.stat(filepath)
        signature = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        return {"note": "", "folder_id": None, "total_hours": 0,
                "placed_hours": 0, "unplaced_hours": 0, "size_kb": 0.0}

    cached = _version_summary_cache.get(filepath)
    if cached is not None and cached[0] == signature:
        return cached[1]

    summary = {"note": "", "folder_id": None, "total_hours": 0,
               "placed_hours": 0, "unplaced_hours": 0,
               "size_kb": round(stat.st_size / 1024, 1),
               "last_modified": None}
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        v_meta = d.get("_version_meta", {}) or {}
        summary["note"] = v_meta.get("note", "") or ""
        summary["folder_id"] = v_meta.get("folder_id")
        summary["last_modified"] = v_meta.get("last_modified")
        placed = sum(int(p.get("duration", 1) or 1) for p in d.get("grid_placements", []))
        # Toplam saat, ekranlarla AYNI kaynaktan: dagilimi ("2+1") olan bir satirda
        # duration bos ya da bayat olabiliyor; anasayfa kartinin "x/y saat" yazisi
        # o zaman sinif ekranindakinden farkli cikiyordu.
        try:
            import lesson_hours
            total = lesson_hours.total(d)
        except Exception:
            total = sum(int(a.get("duration", 2) or 2) for a in d.get("atamalar", []))
        summary["placed_hours"] = placed
        summary["total_hours"] = total
        summary["unplaced_hours"] = max(0, total - placed)
    except Exception:
        pass

    if len(_version_summary_cache) > _VERSION_SUMMARY_CACHE_MAX:
        _version_summary_cache.clear()
    _version_summary_cache[filepath] = (signature, summary)
    return summary


# (slug, filename) -> hash of what THIS process last wrote to that file. Lets
# update_version_in_place answer "has anything changed?" without re-reading and
# re-hashing the whole schedule from disk on every single grid edit.
_last_written_hash = {}


def invalidate_version_summary(slug: str = None, filename: str = None):
    """Forgets cached data for a version file. Call after ANY write to it.

    This also drops the remembered content hash, which matters most when the writer
    was someone else — a cloud pull replacing the file, say. Keeping a stale hash
    there would make the next local save believe its data already matched what is on
    disk and skip the write entirely, silently losing the user's edit.
    """
    if slug and filename:
        _version_summary_cache.pop(os.path.join(_versions_dir(slug), filename), None)
        _last_written_hash.pop((slug, filename), None)
    elif slug:
        prefix = _versions_dir(slug)
        for key in [k for k in _version_summary_cache if k.startswith(prefix)]:
            _version_summary_cache.pop(key, None)
        for key in [k for k in _last_written_hash if k[0] == slug]:
            _last_written_hash.pop(key, None)
    else:
        _version_summary_cache.clear()
        _last_written_hash.clear()


_VERSION_FILENAME_RE = re.compile(
    r"v(\d+)_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_(auto|manual)\.roz"
)


def list_versions(slug: str, source_filter: str = "all") -> list:
    """Version dicts, newest first, optionally filtered by source ('all'/'auto'/'manual')."""
    ver_dir = _versions_dir(slug)
    if not os.path.exists(ver_dir):
        return []

    folders_by_id = {f.get("id"): f.get("name", "") for f in list_folders(slug)}
    # Last line of defence: a deleted version is never listed, even if some sync
    # path managed to put the file back on disk. Whatever else goes wrong, the user
    # does not see something they deleted.
    tombstoned = list_tombstones(slug)
    versions = []

    for f in sorted(os.listdir(ver_dir), reverse=True):
        if not f.endswith(".roz"):
            continue
        if f in tombstoned:
            continue
        filepath = os.path.join(ver_dir, f)

        summary = _version_summary(filepath)
        folder_id = summary["folder_id"]
        
        last_mod = summary.get("last_modified")

        # v001_2026-08-17_15-30-00_auto.roz
        m = _VERSION_FILENAME_RE.match(f)
        if m:
            num = int(m.group(1))
            source = m.group(4)
            if last_mod:
                try:
                    dt = datetime.fromisoformat(last_mod)
                except Exception:
                    try:
                        dt = datetime.strptime(
                            f"{m.group(2)} {m.group(3).replace('-', ':')}", "%Y-%m-%d %H:%M:%S"
                        )
                    except Exception:
                        dt = datetime.fromtimestamp(os.path.getmtime(filepath))
            else:
                try:
                    dt = datetime.strptime(
                        f"{m.group(2)} {m.group(3).replace('-', ':')}", "%Y-%m-%d %H:%M:%S"
                    )
                except Exception:
                    dt = datetime.fromtimestamp(os.path.getmtime(filepath))
        else:
            num = 0
            source = "manual"
            if last_mod:
                try:
                    dt = datetime.fromisoformat(last_mod)
                except Exception:
                    dt = datetime.fromtimestamp(os.path.getmtime(filepath))
            else:
                dt = datetime.fromtimestamp(os.path.getmtime(filepath))

        if source_filter != "all" and source != source_filter:
            continue

        versions.append({
            "filename": f,
            "filepath": filepath,
            "number": num,
            "datetime": dt,
            "date_str": dt.strftime("%d %b %Y"),
            "time_str": dt.strftime("%H:%M:%S"),
            "month_key": dt.strftime("%Y-%m"),
            "month_label": _turkish_month(dt),
            "source": source,
            "size_kb": summary["size_kb"],
            "note": summary["note"],
            "total_hours": summary["total_hours"],
            "placed_hours": summary["placed_hours"],
            "unplaced_hours": summary["unplaced_hours"],
            "folder_id": folder_id,
            "folder_name": folders_by_id.get(folder_id, ""),
        })

    _assign_display_labels(versions)
    return versions


def _assign_display_labels(versions: list):
    """Gives every version a label that is unique within its institution.

    Version numbers are allocated as (highest local number + 1), which is only
    unique per machine. Two devices editing the same institution offline both mint
    "v082", then sync — and both machines end up holding two genuinely different
    schedules that the home screen labels "Versiyon 82". That reads as a duplicate
    even though the content differs, and it is a large part of what "duplicated
    versions" looks like from the outside.

    Renumbering the files would break the folder assignments and cloud identities
    that reference them, so the collision is resolved at display time instead: the
    oldest keeps the plain number, later ones get a letter — "Versiyon 82", then
    "Versiyon 82-B", "Versiyon 82-C".
    """
    by_number = {}
    for v in versions:
        by_number.setdefault(v["number"], []).append(v)

    for number, group in by_number.items():
        if len(group) == 1:
            group[0]["label"] = f"Versiyon {number}"
            group[0]["has_number_collision"] = False
            continue
        # Oldest first, so the version the user has known longest keeps the bare number.
        group.sort(key=lambda v: v["datetime"])
        for index, v in enumerate(group):
            suffix = "" if index == 0 else f"-{chr(ord('B') + index - 1)}"
            v["label"] = f"Versiyon {number}{suffix}"
            v["has_number_collision"] = True

def load_version(slug: str, version_filename: str) -> dict:
    """Loads a version's data_store."""
    filepath = os.path.join(_versions_dir(slug), version_filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "atamalar" in data:
                    data["atamalar"] = sanitize_atamalar(data["atamalar"])
                return data
        except Exception as e:
            print(f"Error loading version {version_filename}: {e}")
            return {}

def delete_version(slug: str, version_filename: str) -> bool:
    """Deletes a version permanently, on this device and everywhere else.

    A delete has to survive three separate things that were each individually
    capable of undoing it:

      1. The local file coming back on the next cloud pull. Handled by the
         tombstone written below, which every read and write path now consults.
      2. The cloud DELETE silently failing (offline, expired token, timeout). The
         old code fired it into a daemon thread and never looked at the result, so
         a delete made on a laptop with no connection simply never happened. It is
         now queued and retried until the server confirms it.
      3. Another device that still holds the file uploading it again. It cannot:
         a tombstoned filename is refused by the push path, and the tombstone list
         travels between devices inside the institution meta.
    """
    if not slug or not version_filename:
        return False

    add_tombstone(slug, version_filename)

    filepath = os.path.join(_versions_dir(slug), version_filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except OSError as exc:
            print(f"[version_store] could not remove {version_filename}: {exc}")
    invalidate_version_summary(slug, version_filename)

    queue_cloud_delete(slug, version_filename)

    # If the deleted version was the active one, promote whatever remains.
    try:
        meta = get_institution_meta(slug)
        if meta.get("active_version") == version_filename:
            remaining = list_versions(slug)
            set_active_version(slug, remaining[0]["filename"] if remaining else None)
    except Exception:
        pass

    return True


# ── Tombstones ───────────────────────────────────────────────────────
# A tombstone is the record that a version was deliberately deleted. It has to
# outlive the file itself, because the whole problem is other copies of that file
# trying to come back. Stored in the institution's meta.json, which is pushed to and
# pulled from the VDS, so the deletion reaches other devices even when the server is
# running an older build that cannot express one itself.

def list_tombstones(slug: str) -> set:
    """Filenames deleted from this institution."""
    if not slug:
        return set()
    return set(get_institution_meta(slug).get("tombstones", []) or [])


def is_tombstoned(slug: str, filename: str) -> bool:
    return bool(slug and filename and filename in list_tombstones(slug))


def add_tombstone(slug: str, filename: str) -> bool:
    if not slug or not filename:
        return False
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        meta = {"name": slug}

    tombstones = list(meta.get("tombstones", []) or [])
    if filename in tombstones:
        return True
    tombstones.append(filename)
    # Keep the list bounded; the oldest entries are for versions no device can still
    # be holding. 2000 is far more than any real institution accumulates.
    meta["tombstones"] = tombstones[-2000:]

    if not _atomic_write_json(meta_path, meta):
        return False
    _invalidate_meta_cache(slug)

    try:
        import threading
        import cloud_sync
        threading.Thread(target=cloud_sync.push_institution_to_rtdb, args=(slug,), daemon=True).start()
    except Exception:
        pass
    return True


def remove_tombstone(slug: str, filename: str) -> bool:
    """Lifts a tombstone, so the version may sync back down again.

    Only for an explicit "restore this" action — never call it to make a sync
    succeed, which would recreate exactly the bug tombstones exist to prevent.
    """
    if not slug or not filename:
        return False
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return False
    tombstones = [t for t in (meta.get("tombstones", []) or []) if t != filename]
    meta["tombstones"] = tombstones
    if not _atomic_write_json(meta_path, meta):
        return False
    _invalidate_meta_cache(slug)
    return True


def merge_tombstones(slug: str, incoming) -> set:
    """Unions tombstones arriving from the cloud into the local list.

    Union, never replace: a device that deleted something a moment ago has a
    tombstone the server has not heard about yet, and overwriting the local list
    with the server's copy would drop it and let the file come straight back.
    """
    if not slug:
        return set()
    incoming = {t for t in (incoming or []) if t}
    if not incoming:
        return list_tombstones(slug)

    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        meta = {"name": slug}

    current = list(meta.get("tombstones", []) or [])
    merged = list(current)
    for name in incoming:
        if name not in merged:
            merged.append(name)
    if len(merged) != len(current):
        meta["tombstones"] = merged[-2000:]
        _atomic_write_json(meta_path, meta)
        _invalidate_meta_cache(slug)
    return set(merged)


def enforce_tombstones(slug: str) -> int:
    """Deletes any local file that is tombstoned. Returns how many were removed.

    A safety net for files an older build restored before the tombstone rules
    existed, and for anything a partially-completed sync left behind.
    """
    removed = 0
    tombstones = list_tombstones(slug)
    if not tombstones:
        return 0
    ver_dir = _versions_dir(slug)
    for filename in tombstones:
        path = os.path.join(ver_dir, filename)
        if os.path.exists(path):
            try:
                os.remove(path)
                invalidate_version_summary(slug, filename)
                removed += 1
            except OSError:
                pass
    return removed


# ── Durable cloud-delete queue ───────────────────────────────────────
# Deletions used to be fired at the server from a daemon thread whose result was
# never checked. Anything that made that one request fail — being offline, an
# expired token, a timeout — meant the server kept the version and handed it back on
# the next poll. Queued deletions are retried until the server actually confirms.

def _pending_deletes_path() -> str:
    return os.path.join(os.path.expanduser("~"), ".chenki_akademi", "pending_deletes.json")


def _load_pending_deletes() -> list:
    try:
        with open(_pending_deletes_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_pending_deletes(items: list):
    _atomic_write_json(_pending_deletes_path(), items)


def queue_cloud_delete(slug: str, filename: str):
    """Records a deletion to push to the VDS, and tries once immediately."""
    items = _load_pending_deletes()
    if not any(i.get("slug") == slug and i.get("filename") == filename for i in items):
        items.append({
            "slug": slug,
            "filename": filename,
            "queued_at": datetime.now().isoformat(),
            "attempts": 0,
        })
        _save_pending_deletes(items)

    try:
        import threading
        threading.Thread(target=flush_pending_deletes, daemon=True).start()
    except Exception:
        pass


def flush_pending_deletes() -> int:
    """Retries every queued deletion. Returns how many the server confirmed.

    Safe to call from a background thread and safe to call often — an entry is only
    dropped once the server has actually accepted the delete.
    """
    items = _load_pending_deletes()
    if not items:
        return 0

    try:
        from api_client import api_client
    except Exception:
        return 0

    confirmed = 0
    remaining = []
    for item in items:
        slug = item.get("slug")
        filename = item.get("filename")
        if not (slug and filename):
            continue

        if not item.get("deleted_on_server"):
            try:
                item["deleted_on_server"] = bool(api_client.delete_version_from_rtdb(slug, filename))
            except Exception:
                item["deleted_on_server"] = False

        # Removing the version from the server is only half a delete. The OTHER
        # computers never drop their own copy on the strength of it being absent from
        # the server — that rule exists so a partial upload cannot wipe local history —
        # they drop it because of the tombstone, and the tombstone only travels inside
        # the institution meta. add_tombstone pushes that meta once, from a daemon
        # thread: if the machine was offline or the app closed straight after the
        # delete, the push was simply lost and the version lived on everywhere else
        # forever. So the meta push is retried here alongside the delete, and the entry
        # is kept until BOTH have been confirmed.
        if item["deleted_on_server"] and not item.get("tombstone_pushed"):
            try:
                import cloud_sync
                item["tombstone_pushed"] = bool(cloud_sync.push_institution_to_rtdb(slug))
            except Exception:
                item["tombstone_pushed"] = False

        if item.get("deleted_on_server") and item.get("tombstone_pushed"):
            confirmed += 1
            continue

        item["attempts"] = int(item.get("attempts", 0)) + 1
        # Keep retrying for a long time, but not forever: after ~200 failed attempts
        # the institution itself has almost certainly been deleted server-side, and
        # the local tombstone already keeps the file from coming back regardless.
        if item["attempts"] < 200:
            remaining.append(item)

    _save_pending_deletes(remaining)
    return confirmed


def pending_delete_count() -> int:
    return len(_load_pending_deletes())
    
    # If deleted version was active, set to latest remaining
    meta = get_institution_meta(slug)
    if meta.get("active_version") == version_filename:
        rem = list_versions(slug)
        if rem:
            set_active_version(slug, rem[0]["filename"])
        else:
            set_active_version(slug, None)

def get_active_version(slug: str) -> str:
    """Returns the filename of the active/official version."""
    if not slug:
        return ""
    meta = get_institution_meta(slug)
    active = meta.get("active_version")
    if active:
        # Verify it still exists
        if os.path.exists(os.path.join(_versions_dir(slug), active)):
            return active
    # Fallback to latest
    try:
        versions = list_versions(slug)
        if versions:
            new_active = versions[0]["filename"]
            set_active_version(slug, new_active)
            return new_active
    except Exception:
        pass
    return ""

def set_active_version(slug: str, version_filename: str):
    if not slug:
        return
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    if not os.path.exists(meta_path):
        # Create minimal meta if missing
        meta_dir = os.path.dirname(meta_path)
        os.makedirs(meta_dir, exist_ok=True)
        meta = {"name": slug, "active_version": version_filename}
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as e:
        print(f"[version_store] Corrupted meta.json detected, resetting. Error: {e}")
        meta = {"name": slug}

    if meta.get("active_version") == version_filename:
        return  # already active — skip the write and the cloud push entirely

    meta["active_version"] = version_filename
    if not _atomic_write_json(meta_path, meta):
        return
    _invalidate_meta_cache(slug)

    try:
        import threading
        import cloud_sync
        threading.Thread(target=cloud_sync.push_institution_to_rtdb, args=(slug,), daemon=True).start()
    except Exception:
        pass


def ensure_institution_has_version(slug: str) -> str:
    """Ensures that the institution has at least one active version. Returns version filename."""
    active = get_active_version(slug)
    if active:
        return active
    
    # Create empty base version
    meta = get_institution_meta(slug)
    inst_name = meta.get("name", slug)
    empty_data = {
        "dersler": [], "siniflar": [], "derslikler": [],
        "ogretmenler": [], "atamalar": [], "settings": {
            "school_name": inst_name,
            "days": ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"],
            "periods": 8
        },
        "grid_placements": [], "kisitlamalar": {},
    }
    return save_version(slug, empty_data, source="manual", note="Başlangıç çizelgesi")


def import_master_data_from_institution(target_slug: str, source_slug: str,
                                        include_subjects: bool = True,
                                        include_classes: bool = True,
                                        include_rooms: bool = True,
                                        include_teachers: bool = True,
                                        include_assignments: bool = True,
                                        invert_timeoff: bool = True) -> tuple:
    """
    Belirtilen kurumdan seçilen temel tanımları hedef kuruma aktarır.
    Zaman tablosu / kısıtlamalar seçeneğe göre tersine çevrilerek çakışmalar önlenir.
    Returns: (bool success, str message, dict updated_data)
    """
    if target_slug == source_slug:
        return False, "Kaynak ve hedef kurum aynı olamaz.", None
        
    src_active = get_active_version(source_slug)
    if not src_active:
        return False, "Kaynak kurumda aktif bir versiyon bulunamadı.", None
        
    src_data = load_version(source_slug, src_active)
    if not src_data:
        return False, "Kaynak verisi yüklenemedi.", None
        
    tgt_active = ensure_institution_has_version(target_slug)
    tgt_data = load_version(target_slug, tgt_active)
    if not tgt_data:
        tgt_data = {
            "dersler": [], "siniflar": [], "derslikler": [],
            "ogretmenler": [], "atamalar": [], "settings": {},
            "grid_placements": [], "kisitlamalar": {}
        }
    
    counts = []
    
    # 1. Dersler
    if include_subjects:
        existing_subjs = {s.get("ad", "").strip().upper() for s in tgt_data.get("dersler", []) if s.get("ad")}
        added_s = 0
        for s in src_data.get("dersler", []):
            if s.get("ad") and s.get("ad").strip().upper() not in existing_subjs:
                tgt_data.setdefault("dersler", []).append(dict(s))
                existing_subjs.add(s.get("ad").strip().upper())
                added_s += 1
        counts.append(f"{added_s} ders")
        
    # 2. Sınıflar
    if include_classes:
        existing_cls = {c.get("ad", "").strip().upper() for c in tgt_data.get("siniflar", []) if c.get("ad")}
        added_c = 0
        for c in src_data.get("siniflar", []):
            if c.get("ad") and c.get("ad").strip().upper() not in existing_cls:
                tgt_data.setdefault("siniflar", []).append(dict(c))
                existing_cls.add(c.get("ad").strip().upper())
                added_c += 1
        counts.append(f"{added_c} sınıf")
        
    # 3. Derslikler
    if include_rooms:
        existing_rooms = {r.get("ad", "").strip().upper() for r in tgt_data.get("derslikler", []) if r.get("ad")}
        added_r = 0
        for r in src_data.get("derslikler", []):
            if r.get("ad") and r.get("ad").strip().upper() not in existing_rooms:
                tgt_data.setdefault("derslikler", []).append(dict(r))
                existing_rooms.add(r.get("ad").strip().upper())
                added_r += 1
        counts.append(f"{added_r} derslik")
        
    # 4. Öğretmenler ve Kısıtlamalar
    if include_teachers:
        existing_t = {t.get("ad", "").strip().upper() for t in tgt_data.get("ogretmenler", []) if t.get("ad")}
        added_t = 0
        for t in src_data.get("ogretmenler", []):
            if t.get("ad") and t.get("ad").strip().upper() not in existing_t:
                tgt_data.setdefault("ogretmenler", []).append(dict(t))
                existing_t.add(t.get("ad").strip().upper())
                added_t += 1
        counts.append(f"{added_t} öğretmen")
        
    # 5. Atamalar (Dağıtımlar) - Çizelge yerleşimleri hariç
    if include_assignments:
        tgt_data["atamalar"] = [dict(a) for a in src_data.get("atamalar", [])]
        counts.append(f"{len(tgt_data['atamalar'])} ders ataması")
        
    # Kaynak kurumun adını alıp not ekleyerek yeni versiyon oluştur
    src_meta = get_institution_meta(source_slug)
    src_name = src_meta.get("name", source_slug)
    note = f"'{src_name}' kurumundan veri aktarıldı: " + ", ".join(counts)
    
    new_vf = save_version(target_slug, tgt_data, source="manual", note=note)
    return True, f"Başarıyla aktarıldı: {', '.join(counts)}.", tgt_data

# ── Migration ────────────────────────────────────────────────────────

def migrate_existing_data():
    """If no institutions exist yet, create a default one from existing .roz data."""
    institutions = list_institutions()
    if institutions:
        return  # Already migrated
    
    # Find existing data
    user_dir = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
    candidates = []
    
    # Check common locations
    for fname in ["bgz_database.json"]:
        p = os.path.join(user_dir, fname)
        if os.path.exists(p):
            candidates.append(p)
    
    # Check last used path from config
    config_path = os.path.join(user_dir, "app_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            last_path = cfg.get("last_db_path", "")
            if last_path and os.path.exists(last_path) and last_path not in candidates:
                candidates.insert(0, last_path)
        except Exception:
            pass
    
    if not candidates:
        return
    
    # Create default institution
    inst = create_institution("Varsayılan Kurum")
    
    for cpath in candidates:
        try:
            with open(cpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and any(k in data for k in ["dersler", "siniflar", "ogretmenler", "atamalar"]):
                save_version(inst["slug"], data, source="manual", note="Mevcut veriden aktarıldı")
                break
        except Exception:
            continue

# ── Turkish Month Names ──────────────────────────────────────────────

_TR_MONTHS = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
    5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
    9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık",
}

def _turkish_month(dt: datetime) -> str:
    return f"{_TR_MONTHS.get(dt.month, dt.strftime('%B'))} {dt.year}"


def load_global_kisitlamalar():
    import json, os
    path = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "global_kisitlamalar.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and any(k for k in data.keys() if " " in k or len(k) > 30):
                    return {"bogazici_egitim_kurumlari": data}
                return data
        except Exception:
            pass
    return {}

def save_global_kisitlamalar(institution_slug, kisitlamalar):
    import json, os
    path = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "global_kisitlamalar.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        global_data = load_global_kisitlamalar()
        global_data[institution_slug] = kisitlamalar
        with open(path, "w", encoding="utf-8") as f:
            json.dump(global_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving global_kisitlamalar:", e)

