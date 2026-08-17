"""
version_store.py — Kurum, Versiyon, Şifreli Erişim ve Çapraz Çakışma Yönetim Modülü
Her kurum bir klasör, her oto/manuel kayıt bir .roz versiyon dosyası.
"""
import os
import json
import re
import shutil
import hashlib
from datetime import datetime

def _base_dir():
    return os.path.join(os.path.expanduser("~"), ".chenki_akademi", "institutions")

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

# ── Password & Security ──────────────────────────────────────────────

def _hash_password(password: str) -> str:
    salt = "chenki_akademi_secure_salt_2026"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def set_institution_password(slug: str, password: str):
    """Sets or updates the password for an institution."""
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if password:
            meta["password_hash"] = _hash_password(password)
            meta["has_password"] = True
        else:
            meta.pop("password_hash", None)
            meta["has_password"] = False
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
            
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

# ── Institution CRUD ─────────────────────────────────────────────────

INSTITUTION_COLORS = [
    "#0071E3", "#34C759", "#AF52DE", "#FF9500", "#FF2D55",
    "#5856D6", "#00C7BE", "#32ADE6", "#A2845E", "#64D2FF",
]

def list_institutions():
    """Returns list of dicts: {slug, name, created, color, version_count, path, has_password, active_version}"""
    base = _ensure_base()
    result = []
    for entry in sorted(os.listdir(base)):
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
            result.append({
                "slug": entry,
                "name": meta.get("name", entry),
                "created": meta.get("created", ""),
                "color": meta.get("color", "#0071E3"),
                "version_count": ver_count,
                "has_password": bool(meta.get("has_password", False) and meta.get("password_hash")),
                "active_version": meta.get("active_version", ""),
                "path": inst_dir,
            })
    return result

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
    
    return {"slug": slug, **meta, "version_count": 1, "path": inst_dir}

def rename_institution(slug: str, new_name: str):
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["name"] = new_name.strip()
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

def set_institution_color(slug: str, color: str):
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["color"] = color
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

def delete_institution(slug: str):
    inst_dir = os.path.join(_base_dir(), slug)
    if os.path.isdir(inst_dir):
        shutil.rmtree(inst_dir)

def get_institution_meta(slug: str) -> dict:
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

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

def save_version(slug: str, data_store: dict, source: str = "manual", note: str = "") -> str:
    """Saves a new version. Returns the version filename."""
    ver_dir = _versions_dir(slug)
    num = _next_version_number(slug)
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d_%H-%M-%S")
    src_tag = "auto" if source == "auto" else "manual"
    filename = f"v{num:03d}_{ts}_{src_tag}.roz"
    filepath = os.path.join(ver_dir, filename)
    
    # Embed version metadata into the data_store copy
    save_data = dict(data_store)
    save_data["_version_meta"] = {
        "version_number": num,
        "timestamp": now.isoformat(),
        "source": src_tag,
        "note": note,
        "filename": filename,
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    
    # Auto-set as active
    set_active_version(slug, filename)
    
    # Push to RTDB in background thread
    try:
        import threading
        from cloud_sync import push_version_to_rtdb
        threading.Thread(target=push_version_to_rtdb, args=(slug, filename, save_data), daemon=True).start()
    except Exception:
        pass
        
    return filename

def update_version_in_place(slug: str, filename: str, data_store: dict) -> bool:
    """Overwrites an existing version file with updated data and pushes to cloud."""
    if not slug or not filename or not data_store:
        return False
    ver_dir = _versions_dir(slug)
    filepath = os.path.join(ver_dir, filename)
    os.makedirs(ver_dir, exist_ok=True)
    
    save_data = dict(data_store)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
            
        # Push to RTDB in background thread
        try:
            import threading
            from cloud_sync import push_version_to_rtdb
            threading.Thread(target=push_version_to_rtdb, args=(slug, filename, save_data), daemon=True).start()
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[version_store] update_version_in_place error: {e}")
        return False

def list_versions(slug: str, source_filter: str = "all") -> list:
    """Returns list of version dicts sorted newest-first, optionally filtered by source ('all', 'auto', 'manual')."""
    ver_dir = _versions_dir(slug)
    versions = []
    if not os.path.exists(ver_dir):
        return []
        
    for f in sorted(os.listdir(ver_dir), reverse=True):
        if not f.endswith(".roz"):
            continue
        filepath = os.path.join(ver_dir, f)
        
        # Parse info from filename: v001_2026-08-17_15-30-00_auto.roz
        m = re.match(r"v(\d+)_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_(auto|manual)\.roz", f)
        if m:
            num = int(m.group(1))
            date_str = m.group(2)
            time_str = m.group(3).replace("-", ":")
            source = m.group(4)
            try:
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            except Exception:
                dt = datetime.fromtimestamp(os.path.getmtime(filepath))
        else:
            num = 0
            source = "manual"
            dt = datetime.fromtimestamp(os.path.getmtime(filepath))
        
        if source_filter != "all" and source != source_filter:
            continue
            
        size_kb = os.path.getsize(filepath) / 1024
        
        note = ""
        total_hours = 0
        placed_hours = 0
        unplaced_hours = 0
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                d = json.load(fh)
                note = d.get("_version_meta", {}).get("note", "")
                atamalar = d.get("atamalar", [])
                for a in atamalar:
                    total_hours += int(a.get("duration", 1))
                placements = d.get("grid_placements", [])
                for p in placements:
                    placed_hours += int(p.get("duration", 1))
                unplaced_hours = max(0, total_hours - placed_hours)
        except Exception:
            pass
        
        versions.append({
            "filename": f,
            "filepath": filepath,
            "number": num,
            "datetime": dt,
            "date_str": dt.strftime("%d %b %Y"),
            "time_str": dt.strftime("%H:%M"),
            "month_key": dt.strftime("%Y-%m"),
            "month_label": _turkish_month(dt),
            "source": source,
            "size_kb": round(size_kb, 1),
            "note": note,
            "total_hours": total_hours,
            "placed_hours": placed_hours,
            "unplaced_hours": unplaced_hours,
        })
    
    return versions

def load_version(slug: str, version_filename: str) -> dict:
    """Loads a version's data_store."""
    filepath = os.path.join(_versions_dir(slug), version_filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading version {version_filename}: {e}")
            return {}
    return {}

def delete_version(slug: str, version_filename: str):
    filepath = os.path.join(_versions_dir(slug), version_filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        
    try:
        import threading
        from cloud_sync import delete_version_from_rtdb
        threading.Thread(target=delete_version_from_rtdb, args=(slug, version_filename), daemon=True).start()
    except Exception:
        pass
    
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
    meta = get_institution_meta(slug)
    active = meta.get("active_version")
    if active:
        # Verify it still exists
        if os.path.exists(os.path.join(_versions_dir(slug), active)):
            return active
    # Fallback to latest
    versions = list_versions(slug)
    if versions:
        new_active = versions[0]["filename"]
        set_active_version(slug, new_active)
        return new_active
    return ""

def set_active_version(slug: str, version_filename: str):
    meta_path = os.path.join(_base_dir(), slug, "meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["active_version"] = version_filename
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

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

# ── Cross-Institution Teacher Conflict Checker ──────────────────────

def get_cross_institution_teacher_busy_slots(exclude_slug: str = None) -> dict:
    """
    Scans all other institutions' active versions and builds a collision map.
    Returns:
        { (normalized_teacher_name, day, period): {
            "institution_name": str,
            "institution_slug": str,
            "teacher_name": str,
            "subject": str,
            "class": str,
            "day": int,
            "period": int
        }}
    """
    institutions = list_institutions()
    busy_slots = {}
    
    for inst in institutions:
        slug = inst["slug"]
        if exclude_slug and slug == exclude_slug:
            continue
            
        active_ver = get_active_version(slug)
        if not active_ver:
            continue
            
        data = load_version(slug, active_ver)
        if not data:
            continue
            
        placements = data.get("grid_placements", [])
        settings = data.get("settings", {})
        periods = int(settings.get("periods", 8))
        
        for p in placements:
            t_raw = p.get("teacher_name") or p.get("teacher") or ""
            if not t_raw:
                continue
                
            t_norm = normalize_teacher_name(t_raw)
            if not t_norm:
                continue
                
            day = int(p.get("day") if "day" in p else (p.get("col", 0) // periods))
            period = int(p.get("period") if "period" in p else (p.get("col", 0) % periods if "col" in p else p.get("row", 0)))
            dur = int(p.get("duration", 1))
            subj = p.get("subject_name") or p.get("subject") or "Ders"
            cls = p.get("class_name") or p.get("class") or ""
            
            for ext in range(dur):
                slot_key = (t_norm, day, period + ext)
                busy_slots[slot_key] = {
                    "institution_name": inst["name"],
                    "institution_slug": slug,
                    "teacher_name": t_raw,
                    "subject": subj,
                    "class": cls,
                    "day": day,
                    "period": period + ext
                }
                
    return busy_slots

# ── Master Data Clone / Import ───────────────────────────────────────

def import_master_data_from_institution(target_slug: str, source_slug: str,
                                        include_subjects: bool = True,
                                        include_classes: bool = True,
                                        include_rooms: bool = True,
                                        include_teachers: bool = True,
                                        include_assignments: bool = True) -> tuple:
    """
    Imports master definitions from source institution into target institution's active version.
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
        
    # 4. Öğretmenler
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
