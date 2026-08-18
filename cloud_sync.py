"""
cloud_sync.py — VDS Backend Senkronizasyon Motoru
Yerel öncelikli (Local-First) mimari: Tüm .roz dosyaları ve kurumlar özel VDS API üzerinden 0 maliyetle senkronize edilir.
Çoklu bilgisayar desteği, anlık veri çekme (pull) ve arka plan kuyruklu yükleme (push).
"""
import os
import re
import json
import time
import requests
from collections import deque
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker
from api_client import api_client

def _sanitize_key(key: str) -> str:
    """Sanitizes string keys for Firebase RTDB and JSON paths."""
    return re.sub(r'[\.\#\$\/\[\]]', '_', str(key))

def _get_auth_params(auth_data: dict = None) -> dict:
    return {}

# ── Standalone API Sync Functions ───────────────────────────────────

def pull_all_from_rtdb(auth_data: dict = None) -> tuple:
    return api_client.pull_all_from_rtdb(auth_data)

def push_version_to_rtdb(slug: str, filename: str, roz_data: dict, auth_data: dict = None) -> bool:
    return api_client.push_version_to_rtdb(slug, filename, roz_data, auth_data)

def push_institution_to_rtdb(slug: str, auth_data: dict = None) -> bool:
    """Pushes an entire local institution (meta + all versions) to API."""
    import version_store
    inst_dir = os.path.join(version_store._ensure_base(), slug)
    if not os.path.isdir(inst_dir):
        return False
        
    meta = version_store.get_institution_meta(slug)
    ver_dir = os.path.join(inst_dir, "versions")
    versions_dict = {}
    if os.path.isdir(ver_dir):
        for fn in os.listdir(ver_dir):
            if fn.endswith(".roz"):
                v_path = os.path.join(ver_dir, fn)
                try:
                    with open(v_path, "r", encoding="utf-8") as f:
                        v_data = json.load(f)
                    v_key = re.sub(r'[\.\$#\[\]/]', '_', fn)
                    versions_dict[v_key] = v_data
                except Exception as e:
                    print(f"Error reading version {fn}: {e}")
                    
    payload = {
        "slug": slug,
        "meta": meta,
        "versions": versions_dict
    }
    url = f"{api_client.base_url}/api/institutions"
    try:
        resp = requests.post(url, json=payload, headers=api_client.get_headers(), timeout=20)
        return resp.status_code in (200, 201)
    except Exception as e:
        print(f"push_institution_to_rtdb error for {slug}: {e}")
        return False

def push_all_to_rtdb(auth_data: dict = None) -> tuple:
    """Pushes all local institutions and their versions to API."""
    import version_store
    base_dir = version_store._ensure_base()
    if not os.path.exists(base_dir):
        return True, "Yüklenecek kurum bulunamadı.", 0
        
    pushed = 0
    total_versions = 0
    for slug in os.listdir(base_dir):
        inst_dir = os.path.join(base_dir, slug)
        if os.path.isdir(inst_dir) and os.path.exists(os.path.join(inst_dir, "meta.json")):
            ver_dir = os.path.join(inst_dir, "versions")
            v_count = len([f for f in os.listdir(ver_dir) if f.endswith(".roz")]) if os.path.isdir(ver_dir) else 0
            if push_institution_to_rtdb(slug, auth_data):
                pushed += 1
                total_versions += v_count
                
    return True, f"{pushed} kurum ve {total_versions} versiyon VDS'e başarıyla yüklendi.", pushed

def delete_version_from_rtdb(slug: str, filename: str, auth_data: dict = None) -> bool:
    v_key = re.sub(r'[\.\$#\[\]/]', '_', filename)
    url = f"{api_client.base_url}/api/sync/{slug}/{v_key}"
    try:
        resp = requests.delete(url, headers=api_client.get_headers(), timeout=10)
        return resp.status_code in (200, 204)
    except Exception:
        return False

def delete_institution_from_rtdb(slug: str, auth_data: dict = None) -> bool:
    url = f"{api_client.base_url}/api/institutions/{slug}"
    try:
        resp = requests.delete(url, headers=api_client.get_headers(), timeout=10)
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
                
                self.sync_status_changed.emit("Veritabanınız korunuyor: Senkronize ediliyor...")
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
                    self.sync_status_changed.emit("Veritabanınız korunuyor: Senkronize")
                else:
                    self.sync_status_changed.emit("Veritabanınız korunuyor: Bağlantı bekleniyor...")
                    self._sleep_interruptible(4)
            else:
                if self._last_ping + 15 < time.time():
                    try:
                        # Dummy ping for connection check
                        resp = requests.get(f"{api_client.base_url}", timeout=3)
                        if resp.status_code in (200, 404):
                            self.sync_status_changed.emit("Veritabanınız korunuyor: Senkronize")
                        else:
                            self.sync_status_changed.emit("Veritabanınız korunuyor: Senkronize")
                    except Exception:
                        self.sync_status_changed.emit("Veritabanı: Çevrimdışı (Yerel Kayıt)")
                    self._last_ping = time.time()
                self._sleep_interruptible(1)

    def stop(self):
        self._is_running = False
        self.wait(1500)
