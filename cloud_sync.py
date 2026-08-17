"""
cloud_sync.py — Firebase Realtime Database (RTDB) Bulut Senkronizasyon Motoru
Yerel öncelikli (Local-First) mimari: Tüm .roz dosyaları ve kurumlar RTDB üzerinden 0 maliyetle senkronize edilir.
Çoklu bilgisayar desteği, anlık veri çekme (pull) ve arka plan kuyruklu yükleme (push).
"""
import os
import re
import json
import time
import requests
from collections import deque
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

# Firebase Web Config
FIREBASE_PROJECT_ID = "bogazicidersyonetim"
FIREBASE_API_KEY = "AIzaSyCyJzdfiv6ezzpfrsuwsuY84Ri2KTMO4bU"

# Realtime Database URL
RTDB_URL = "https://bogazicidersyonetim-default-rtdb.firebaseio.com"

def _sanitize_key(key: str) -> str:
    """Sanitizes strings for use as RTDB keys (replaces ., $, #, [, ], / with _)"""
    return re.sub(r'[\.\$#\[\]/]', '_', key)

def _get_auth_params(auth_data: dict = None) -> dict:
    params = {}
    if auth_data and isinstance(auth_data, dict) and "idToken" in auth_data:
        params["auth"] = auth_data["idToken"]
    return params

# ── Standalone RTDB Sync Functions ───────────────────────────────────

def pull_all_from_rtdb(auth_data: dict = None) -> tuple:
    """
    Downloads all institutions and .roz versions from RTDB to local storage.
    Returns (success: bool, message: str, count: int)
    """
    import version_store
    base_dir = version_store._ensure_base()
    url = f"{RTDB_URL}/institutions.json"
    params = _get_auth_params(auth_data)
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return False, f"Buluttan veri çekilemedi (HTTP {resp.status_code})", 0
            
        data = resp.json()
        if not data or not isinstance(data, dict):
            return True, "Bulutta kayıtlı kurum bulunamadı.", 0
            
        synced_count = 0
        for slug, inst_obj in data.items():
            if not isinstance(inst_obj, dict):
                continue
                
            inst_dir = os.path.join(base_dir, slug)
            ver_dir = os.path.join(inst_dir, "versions")
            os.makedirs(ver_dir, exist_ok=True)
            
            # Save meta.json
            meta_data = inst_obj.get("meta", {})
            if meta_data and isinstance(meta_data, dict):
                with open(os.path.join(inst_dir, "meta.json"), "w", encoding="utf-8") as f:
                    json.dump(meta_data, f, ensure_ascii=False, indent=2)
                    
            # Save versions (.roz files)
            cloud_versions = inst_obj.get("versions", {})
            if isinstance(cloud_versions, dict):
                for v_key, roz_content in cloud_versions.items():
                    if isinstance(roz_content, dict):
                        orig_fn = roz_content.get("_version_meta", {}).get("filename", "")
                        if not orig_fn:
                            orig_fn = f"{v_key.replace('_roz', '.roz')}"
                        if not orig_fn.endswith(".roz"):
                            orig_fn += ".roz"
                            
                        target_file = os.path.join(ver_dir, orig_fn)
                        # Write local .roz
                        with open(target_file, "w", encoding="utf-8") as f:
                            json.dump(roz_content, f, ensure_ascii=False, indent=2)
                        synced_count += 1
                        
        return True, f"Bulut senkronizasyonu tamamlandı ({len(data)} kurum, {synced_count} versiyon).", synced_count
    except Exception as e:
        return False, f"Bulut bağlantı hatası: {e}", 0


def push_version_to_rtdb(slug: str, filename: str, roz_data: dict, auth_data: dict = None) -> bool:
    """Pushes a single .roz version to RTDB."""
    v_key = _sanitize_key(filename)
    url = f"{RTDB_URL}/institutions/{slug}/versions/{v_key}.json"
    params = _get_auth_params(auth_data)
    
    try:
        resp = requests.put(url, json=roz_data, params=params, timeout=8)
        if resp.status_code in (200, 201):
            # Also update meta
            import version_store
            meta = version_store.get_institution_meta(slug)
            meta_url = f"{RTDB_URL}/institutions/{slug}/meta.json"
            requests.put(meta_url, json=meta, params=params, timeout=5)
            return True
    except Exception as e:
        print(f"[CloudSync] push_version_to_rtdb error: {e}")
    return False


def push_institution_to_rtdb(slug: str, auth_data: dict = None) -> bool:
    """Pushes an entire local institution (meta + all versions) to RTDB."""
    import version_store
    inst_dir = os.path.join(version_store._ensure_base(), slug)
    if not os.path.isdir(inst_dir):
        return False
        
    meta = version_store.get_institution_meta(slug)
    ver_dir = os.path.join(inst_dir, "versions")
    
    versions_payload = {}
    if os.path.isdir(ver_dir):
        for f in os.listdir(ver_dir):
            if f.endswith(".roz"):
                fpath = os.path.join(ver_dir, f)
                try:
                    with open(fpath, "r", encoding="utf-8") as fh:
                        v_data = json.load(fh)
                    v_key = _sanitize_key(f)
                    versions_payload[v_key] = v_data
                except Exception:
                    pass
                    
    payload = {
        "meta": meta,
        "versions": versions_payload,
        "updated_at": int(time.time())
    }
    
    url = f"{RTDB_URL}/institutions/{slug}.json"
    params = _get_auth_params(auth_data)
    try:
        resp = requests.put(url, json=payload, params=params, timeout=15)
        return resp.status_code in (200, 201)
    except Exception as e:
        print(f"[CloudSync] push_institution_to_rtdb error: {e}")
        return False


def push_all_to_rtdb(auth_data: dict = None) -> tuple:
    """Pushes all local institutions and their versions to RTDB."""
    import version_store
    base_dir = version_store._ensure_base()
    if not os.path.exists(base_dir):
        return True, "Yüklenecek kurum bulunamadı.", 0
        
    pushed = 0
    for slug in os.listdir(base_dir):
        inst_dir = os.path.join(base_dir, slug)
        if os.path.isdir(inst_dir) and os.path.exists(os.path.join(inst_dir, "meta.json")):
            if push_institution_to_rtdb(slug, auth_data):
                pushed += 1
                
    return True, f"{pushed} kurum buluta başarıyla yüklendi.", pushed


def delete_version_from_rtdb(slug: str, filename: str, auth_data: dict = None) -> bool:
    v_key = _sanitize_key(filename)
    url = f"{RTDB_URL}/institutions/{slug}/versions/{v_key}.json"
    params = _get_auth_params(auth_data)
    try:
        resp = requests.delete(url, params=params, timeout=5)
        return resp.status_code in (200, 204)
    except Exception:
        return False


def delete_institution_from_rtdb(slug: str, auth_data: dict = None) -> bool:
    url = f"{RTDB_URL}/institutions/{slug}.json"
    params = _get_auth_params(auth_data)
    try:
        resp = requests.delete(url, params=params, timeout=5)
        return resp.status_code in (200, 204)
    except Exception:
        return False


# ── Background Local-First Cloud Worker ──────────────────────────────

class CloudSyncWorker(QThread):
    sync_status_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self._queue = deque()
        self._mutex = QMutex()
        self.auth_data = None
        self._last_ping = 0
        
    def set_auth(self, auth_data):
        self.auth_data = auth_data
        
    def add_to_queue(self, action: str, slug: str, filename: str = "", data: dict = None):
        """Adds a sync task (action: 'push_version', 'push_inst', 'del_version', 'del_inst')"""
        with QMutexLocker(self._mutex):
            self._queue.append({
                "action": action,
                "slug": slug,
                "filename": filename,
                "data": data,
                "timestamp": time.time()
            })
            
    def _sleep_interruptible(self, seconds):
        end_time = time.time() + seconds
        while self._is_running and time.time() < end_time:
            time.sleep(0.05)

    def run(self):
        while self._is_running:
            item = None
            with QMutexLocker(self._mutex):
                if len(self._queue) > 0:
                    item = self._queue[0]
                    
            if item:
                act = item["action"]
                slug = item["slug"]
                fn = item.get("filename", "")
                data = item.get("data")
                
                self.sync_status_changed.emit("Bulut: Senkronize ediliyor...")
                success = False
                
                if act == "push_version" and data:
                    success = push_version_to_rtdb(slug, fn, data, self.auth_data)
                elif act == "push_inst":
                    success = push_institution_to_rtdb(slug, self.auth_data)
                elif act == "del_version":
                    success = delete_version_from_rtdb(slug, fn, self.auth_data)
                elif act == "del_inst":
                    success = delete_institution_from_rtdb(slug, self.auth_data)
                else:
                    success = True
                    
                if success:
                    with QMutexLocker(self._mutex):
                        if len(self._queue) > 0:
                            self._queue.popleft()
                    self.sync_status_changed.emit("Bulut: Senkronize (Tüm veriler güvende)")
                else:
                    self.sync_status_changed.emit("Bulut: Bağlantı bekleniyor...")
                    self._sleep_interruptible(4)
            else:
                if self._last_ping + 15 < time.time():
                    try:
                        resp = requests.get(f"{RTDB_URL}/ping.json", timeout=3)
                        if resp.status_code == 200:
                            self.sync_status_changed.emit("Bulut: Bağlı (Eşitlendi)")
                        else:
                            self.sync_status_changed.emit("Bulut: Hazır")
                    except Exception:
                        self.sync_status_changed.emit("Bulut: Çevrimdışı")
                    self._last_ping = time.time()
                self._sleep_interruptible(1)

    def stop(self):
        self._is_running = False
        self.wait(1500)
