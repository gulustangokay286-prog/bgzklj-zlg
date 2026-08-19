"""
cloud_sync.py — VDS Backend Gerçek Zamanlı (Realtime Live Event) Senkronizasyon Motoru
Tüm .roz dosyaları ve kurumlar özel VDS API üzerinden çift yönlü anlık senkronize edilir.
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
    return re.sub(r'[\.\#\$\/\[\]]', '_', str(key))

def pull_all_from_rtdb(auth_data: dict = None) -> tuple:
    return api_client.pull_all_from_rtdb(auth_data)

def push_version_to_rtdb(slug: str, filename: str, roz_data: dict, auth_data: dict = None) -> bool:
    try:
        return api_client.push_version_to_rtdb(slug, filename, roz_data, auth_data)
    except Exception:
        return False

def push_institution_to_rtdb(slug: str, auth_data: dict = None) -> bool:
    import version_store
    inst_dir = os.path.join(version_store._ensure_base(), slug)
    if not os.path.isdir(inst_dir):
        return False
        
    meta = version_store.get_institution_meta(slug)
    ver_dir = os.path.join(inst_dir, "versions")
    versions_dict = {}
    if os.path.isdir(ver_dir):
        all_files = sorted([f for f in os.listdir(ver_dir) if f.endswith(".roz")], reverse=True)
        # Include top 12 most recent versions in root payload for high performance
        for fn in all_files[:12]:
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
        resp = api_client._request_with_retry("POST", url, json=payload, timeout=12)
        return resp is not None and resp.status_code in (200, 201)
    except Exception as e:
        print(f"push_institution_to_rtdb error for {slug}: {e}")
        return False

def push_all_to_rtdb(auth_data: dict = None) -> tuple:
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
                
    return True, f"{pushed} kurum ve {total_versions} versiyon merkezi buluta başarıyla yüklendi.", pushed

def delete_version_from_rtdb(slug: str, filename: str, auth_data: dict = None) -> bool:
    return api_client.delete_version_from_rtdb(slug, filename, auth_data)

def delete_institution_from_rtdb(slug: str, auth_data: dict = None) -> bool:
    return api_client.delete_institution_from_rtdb(slug, auth_data)


# ── Background Realtime Live Event Sync Worker ────────────────────────

class CloudSyncWorker(QThread):
    sync_status_changed = Signal(str)
    remote_data_updated = Signal(str, str) # slug, filename
    institutions_list_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self._queue = deque()
        self._mutex = QMutex()
        self.auth_data = None
        self._last_pull_time = 0
        
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
                    self.sync_status_changed.emit("Veritabanınız korunuyor: Canlı Senkronize (VDS Aktif)")
                else:
                    self.sync_status_changed.emit("Veritabanınız korunuyor: Bağlantı bekleniyor...")
                    self._sleep_interruptible(3)
            else:
                # Live Poller: Pull remote changes every 4 seconds
                now = time.time()
                if self._last_pull_time + 4 < now:
                    try:
                        pull_ok, msg, new_count = api_client.pull_all_from_rtdb(self.auth_data)
                        if pull_ok:
                            self.sync_status_changed.emit("Veritabanınız korunuyor: Canlı Senkronize (VDS Aktif)")
                            if new_count > 0:
                                self.institutions_list_changed.emit()
                                self.remote_data_updated.emit("", "")
                        else:
                            self.sync_status_changed.emit("Veritabanı: Çevrimdışı (Yerel Mod)")
                    except Exception:
                        self.sync_status_changed.emit("Veritabanı: Çevrimdışı (Yerel Mod)")
                    self._last_pull_time = now
                self._sleep_interruptible(0.5)

    def stop(self):
        self._is_running = False
        self.wait(1500)
