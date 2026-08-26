"""
database.py — VDS Bulut Tabanlı ve Yerel Kurum Versiyon Yönetim Modülü
Bu modül tüm veri kalıcılığını VDS (Firebase Realtime Cloud Backend) ve
yerel .roz / JSON versiyon deposu üzerinden yönetir.
"""
import os
import json
import zipfile
from datetime import datetime
import shutil

def get_base_dir():
    base = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return base


def init_db():
    """Ensures necessary local directories exist for VDS and version storage."""
    get_base_dir()
    import version_store
    version_store._ensure_base()


def sync_data_store_to_vds(data_store: dict, auth_data: dict = None):
    """
    Syncs the entire data_store directly to VDS Cloud Backend (Firebase RTDB)
    and persists to institution version file.
    """
    if not isinstance(data_store, dict):
        return
        
    settings = data_store.get("settings", {})
    slug = settings.get("institution_slug") or data_store.get("institution_slug")
    ver_fn = settings.get("version_filename") or data_store.get("version_filename")
    
    # 1. Update version file
    try:
        import version_store
        if slug and ver_fn:
            version_store.update_version_in_place(slug, ver_fn, data_store)
            version_store.touch_institution_timestamp(slug)
    except Exception as e:
        print(f"[VDS_SYNC] Version file update error: {e}")
        
    # 2. Push to VDS Cloud Backend
    try:
        from cloud_sync import push_version_to_rtdb, push_institution_to_rtdb
        auth = auth_data
        if not auth:
            try:
                from api_client import token_manager
                token = token_manager.get_token()
                if token:
                    auth = {"token": token}
            except Exception:
                pass
                
        if slug and ver_fn:
            push_version_to_rtdb(slug, ver_fn, data_store, auth)
        elif slug:
            push_institution_to_rtdb(slug, auth)
    except Exception as e:
        print(f"[VDS_SYNC] Cloud push error: {e}")
        
    # 3. Publish cross-institution constraint sync
    try:
        import constraint_sync
        if slug:
            constraint_sync.publish(slug, data_store)
    except Exception:
        pass


def sync_data_store_to_sqlite(data_store: dict):
    """Compatibility alias routing directly to VDS sync."""
    sync_data_store_to_vds(data_store)


def trigger_save_db(widget, data_store=None):
    """Walks up the Qt parent hierarchy to find MainWindow/AppShell and trigger save_db()."""
    saved = False
    curr = widget
    while curr is not None:
        if hasattr(curr, "save_db") and callable(getattr(curr, "save_db")):
            try:
                curr.save_db(sync_from_grid=False)
                if hasattr(curr, "_refresh_tree") and callable(getattr(curr, "_refresh_tree")):
                    curr._refresh_tree()
                saved = True
                break
            except Exception as e:
                print(f"[SAVE_DB_ERR] {e}")
        if hasattr(curr, "parent") and callable(getattr(curr, "parent")):
            curr = curr.parent()
        else:
            break
            
    if not saved:
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for top in app.topLevelWidgets():
                    if hasattr(top, "save_db") and callable(getattr(top, "save_db")):
                        top.save_db(sync_from_grid=False)
                        if hasattr(top, "_refresh_tree") and callable(getattr(top, "_refresh_tree")):
                            top._refresh_tree()
                        saved = True
                        break
        except Exception:
            pass
        
    if not saved and data_store:
        sync_data_store_to_vds(data_store)
        
    return saved


def get_backup_dir():
    b_dir = os.path.join(get_base_dir(), "backups")
    os.makedirs(b_dir, exist_ok=True)
    return b_dir


def create_database_backup(slug=None, note="auto"):
    """
    Creates a compressed ZIP backup snapshot of all institutions,
    version files (.roz), and metadata.
    """
    b_dir = get_backup_dir()
    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    tag = slug if slug else "all_institutions"
    zip_name = f"backup_{tag}_{now_str}_{note}.zip"
    zip_path = os.path.join(b_dir, zip_name)
    
    try:
        import version_store
        inst_base = version_store._ensure_base()
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            if os.path.exists(inst_base):
                for root, _, files in os.walk(inst_base):
                    for f in files:
                        if f.endswith((".roz", ".json", ".bak")):
                            full_p = os.path.join(root, f)
                            rel_p = os.path.relpath(full_p, inst_base)
                            zipf.write(full_p, arcname=os.path.join("institutions", rel_p))
                            
        all_backups = sorted([
            os.path.join(b_dir, f) for f in os.listdir(b_dir) if f.startswith("backup_") and f.endswith(".zip")
        ], key=os.path.getmtime)
        
        while len(all_backups) > 50:
            oldest = all_backups.pop(0)
            try:
                os.remove(oldest)
            except Exception:
                pass
                
        return zip_path
    except Exception as e:
        print(f"[BACKUP_ERROR] Failed to create database backup: {e}")
        return ""


def restore_database_backup(backup_zip_path: str) -> bool:
    """Restores institutions and versions from a backup ZIP archive safely."""
    if not os.path.exists(backup_zip_path):
        return False
    try:
        import version_store
        inst_base = version_store._ensure_base()
        create_database_backup(note="pre_restore_snapshot")
        
        with zipfile.ZipFile(backup_zip_path, "r") as zipf:
            for member in zipf.namelist():
                if member.startswith("institutions/"):
                    rel = member[len("institutions/"):]
                    target = os.path.join(inst_base, rel)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zipf.open(member) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                        
        return True
    except Exception as e:
        print(f"[RESTORE_ERROR] Failed to restore database backup: {e}")
        return False


def list_database_backups() -> list:
    """Lists all available backup files with timestamps, sizes, and notes."""
    b_dir = get_backup_dir()
    backups = []
    if not os.path.exists(b_dir):
        return []
        
    for f in sorted(os.listdir(b_dir), key=lambda x: os.path.getmtime(os.path.join(b_dir, x)), reverse=True):
        if f.startswith("backup_") and f.endswith(".zip"):
            fp = os.path.join(b_dir, f)
            sz = os.path.getsize(fp)
            mtime = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")
            backups.append({
                "filename": f,
                "path": fp,
                "size_kb": round(sz / 1024, 1),
                "created": mtime
            })
    return backups
