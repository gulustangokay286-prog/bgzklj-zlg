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
from PySide6.QtCore import QObject, Signal, QUrl, QTimer
from api_client import api_client

try:
    from PySide6.QtWebSockets import QWebSocket
    _HAS_WEBSOCKETS = True
except ImportError:
    QWebSocket = None
    _HAS_WEBSOCKETS = False

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
        # Push all versions for complete cross-device synchronization
        for fn in all_files:
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
        resp = api_client._request_with_retry("POST", url, json=payload, timeout=5)
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
import threading

class CloudSyncWorker(QObject):
    sync_status_changed = Signal(str)
    remote_data_updated = Signal(str, str) # slug, filename
    institutions_list_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self._queue = deque()
        self._lock = threading.Lock()
        self.auth_data = None
        self._last_pull_time = 0
        self._thread = None
        
    def set_auth(self, auth_data):
        self.auth_data = auth_data
        
    def add_to_queue(self, action: str, slug: str, filename: str = "", data: dict = None):
        with self._lock:
            self._queue.append({
                "action": action,
                "slug": slug,
                "filename": filename,
                "data": data,
                "timestamp": time.time()
            })
            
    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._is_running = True
            self._thread = threading.Thread(target=self.run, daemon=True)
            self._thread.start()

    def _sleep_interruptible(self, seconds):
        end_time = time.time() + seconds
        while self._is_running and time.time() < end_time:
            time.sleep(0.05)

    def run(self):
        while self._is_running:
            item = None
            with self._lock:
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
                    with self._lock:
                        if len(self._queue) > 0:
                            self._queue.popleft()
                    self.sync_status_changed.emit("Veritabanınız korunuyor: Canlı Senkronize (VDS Aktif)")
                else:
                    self.sync_status_changed.emit("Veritabanınız korunuyor: Bağlantı bekleniyor...")
                    self._sleep_interruptible(3)
            else:
                # Live Poller: Pull remote changes every 15 seconds smoothly
                now = time.time()
                if self._last_pull_time + 15 < now:
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
                self._sleep_interruptible(1.0)

    def stop(self):
        self._is_running = False


# ── Real-time push notifications (WebSocket) ──────────────────────────
class RealtimeSyncClient(QObject):
    """Watches ONE institution over a WebSocket connection to the VDS backend, so a change
    another device pushes shows up within a fraction of a second instead of waiting for the
    CloudSyncWorker's ~15s poll. Runs on the Qt event loop (no extra thread needed — QWebSocket
    is fully async via signals). If the connection can't be made or the server doesn't support
    it yet, this simply stays quiet and the existing poll loop remains the safety net either
    way, so it degrades gracefully.
    """
    sync_notified = Signal(str)          # slug that changed
    connection_state_changed = Signal(bool)  # True once connected, False on drop

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slug = None
        self._socket = None
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._reconnect)
        self._reconnect_delay_ms = 3000

    def watch(self, slug: str):
        """Start (or switch to) watching this institution's slug for live changes."""
        if not _HAS_WEBSOCKETS or not slug:
            return
        if slug == self._slug and self._socket is not None:
            return  # already watching this one
        self.stop()
        self._slug = slug
        self._open()

    def _open(self):
        if not self._slug:
            return
        token = api_client.token
        if not token:
            return  # not logged in to the VDS yet -- nothing to authenticate the socket with
        ws_base = api_client.base_url.replace("https://", "wss://").replace("http://", "ws://")
        url = QUrl(f"{ws_base}/ws/{self._slug}?token={token}")

        self._socket = QWebSocket()
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.textMessageReceived.connect(self._on_message)
        self._socket.errorOccurred.connect(self._on_error)
        self._socket.open(url)

    def _on_connected(self):
        self._reconnect_delay_ms = 3000  # reset backoff after a successful connection
        self.connection_state_changed.emit(True)

    def _on_disconnected(self):
        self.connection_state_changed.emit(False)
        self._schedule_reconnect()

    def _on_error(self, *_args):
        # disconnected() usually follows a connection error too, but schedule a reconnect
        # here as well in case it doesn't (e.g. the handshake itself was rejected).
        self._schedule_reconnect()

    def _schedule_reconnect(self):
        if not self._slug:
            return  # stop() was called -- we're not supposed to be watching anything
        self._reconnect_timer.start(self._reconnect_delay_ms)
        self._reconnect_delay_ms = min(self._reconnect_delay_ms * 2, 30000)

    def _reconnect(self):
        if self._slug:
            self._open()

    def _on_message(self, text):
        try:
            msg = json.loads(text)
        except Exception:
            return
        if msg.get("type") == "sync" and msg.get("slug"):
            self.sync_notified.emit(msg["slug"])

    def stop(self):
        """Stop watching entirely (e.g. the dashboard is closing)."""
        self._reconnect_timer.stop()
        self._slug = None
        self._close_socket()

    def _close_socket(self):
        if self._socket is not None:
            sock = self._socket
            self._socket = None
            try:
                sock.disconnected.disconnect(self._on_disconnected)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass
            sock.deleteLater()
