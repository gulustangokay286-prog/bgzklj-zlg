"""
cloud_sync.py — VDS Backend Gerçek Zamanlı (Realtime Live Event) Senkronizasyon Motoru
Tüm .roz dosyaları ve kurumlar özel VDS API üzerinden çift yönlü anlık senkronize edilir.
"""
import os
import re
import json
import time
import requests
import threading
from collections import deque
from PySide6.QtCore import QObject, Signal, QUrl, QTimer
from api_client import api_client

_push_lock = threading.Lock()

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
    with _push_lock:
        try:
            return api_client.push_version_to_rtdb(slug, filename, roz_data, auth_data)
        except Exception:
            return False

def push_institution_to_rtdb(slug: str, auth_data: dict = None) -> bool:
    """Pushes an institution's SETTINGS only — name, colour, folders, active version.

    It used to read and upload every .roz the institution had ever had on each call,
    and this runs on rename, recolour, set-primary, set-active-version, password
    change and every save. Re-uploading the entire schedule history for a colour
    change is what made those actions hang, and it is what fed the server the nested
    version blob that then came back down and bloated the local meta.json.

    Version payloads travel through push_version_to_rtdb, one version at a time.
    """
    import version_store
    inst_dir = os.path.join(version_store._ensure_base(), slug)
    if not os.path.isdir(inst_dir):
        return False
    return api_client.push_institution_meta(slug, version_store.get_institution_meta(slug))


def push_all_to_rtdb(auth_data: dict = None) -> tuple:
    """Uploads everything held locally. Used by the manual "sync now" action."""
    import version_store
    base_dir = version_store._ensure_base()
    if not os.path.exists(base_dir):
        return True, "Yüklenecek kurum bulunamadı.", 0

    pushed = 0
    pushed_versions = 0
    for slug in sorted(os.listdir(base_dir)):
        if slug.startswith("_system_") or slug.startswith("_auth_") or slug in ("backups", "temp", "cache"):
            continue
        inst_dir = os.path.join(base_dir, slug)
        if not (os.path.isdir(inst_dir) and os.path.exists(os.path.join(inst_dir, "meta.json"))):
            continue
        if not push_institution_to_rtdb(slug, auth_data):
            continue
        pushed += 1

        ver_dir = os.path.join(inst_dir, "versions")
        if not os.path.isdir(ver_dir):
            continue
        for fn in sorted(f for f in os.listdir(ver_dir) if f.endswith(".roz")):
            try:
                with open(os.path.join(ver_dir, fn), "r", encoding="utf-8") as f:
                    v_data = json.load(f)
            except Exception as exc:
                print(f"[cloud_sync] skipping unreadable version {fn}: {exc}")
                continue
            if push_version_to_rtdb(slug, fn, v_data, auth_data):
                pushed_versions += 1

    return True, f"{pushed} kurum ve {pushed_versions} versiyon buluta yüklendi.", pushed

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
        self._pull_requested = False
        self._offline_streak = 0
        # Set to break the idle sleep the moment there is something to do.
        self._wake = threading.Event()
        
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
        # Send it now rather than after the current idle sleep, so a change made here
        # reaches other devices as fast as one made elsewhere reaches this one.
        self._wake.set()
            
    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._is_running = True
            self._thread = threading.Thread(target=self.run, daemon=True)
            self._thread.start()

    def _sleep_interruptible(self, seconds):
        """Sleeps, but wakes the instant a pull is requested or the worker stops.

        This used to poll a flag every 50ms, so a realtime nudge could sit unnoticed
        for up to half a second before the loop looked at it — on top of the network
        round trip. An Event wakes immediately and burns no CPU while idle, which
        matters on the low-end machines this app runs on.
        """
        self._wake.wait(timeout=seconds)
        self._wake.clear()

    def _safe_emit(self, signal, *args):
        if not getattr(self, "_is_running", True):
            return
        try:
            signal.emit(*args)
        except Exception:
            pass

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
                
                self._safe_emit(self.sync_status_changed, "Veritabanı senkronize ediliyor...")
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
                    self._safe_emit(self.sync_status_changed, "Veritabanı korunuyor")
                else:
                    self._safe_emit(self.sync_status_changed, "Bağlantı bekleniyor...")
                    self._sleep_interruptible(3)
            else:
                now = time.time()
                if self._pull_requested or self._last_pull_time + self._poll_interval() < now:
                    self._pull_requested = False

                    # Retire any deletions that never reached the server — the app
                    # may have been offline, or closed before the request completed.
                    # This runs BEFORE the pull, so a still-pending delete is pushed
                    # up before the server has a chance to hand the version back.
                    try:
                        import version_store
                        confirmed = version_store.flush_pending_deletes()
                        if confirmed:
                            print(f"[CloudSync] {confirmed} bekleyen silme işlemi tamamlandı")
                    except Exception as exc:
                        print(f"[CloudSync] pending delete flush note: {exc}")

                    # Session revocation check disabled per user setting


                    try:
                        pull_ok, msg, new_count = api_client.pull_all_from_rtdb(self.auth_data)
                        if pull_ok:
                            self._offline_streak = 0
                            self._safe_emit(self.sync_status_changed, "Veritabanı korunuyor")
                            if new_count > 0:
                                self._safe_emit(self.institutions_list_changed)
                                self._safe_emit(self.remote_data_updated, "", "")
                        else:
                            self._offline_streak += 1
                            self._safe_emit(self.sync_status_changed, "Veritabanı: Çevrimdışı (Yerel Mod)")
                    except Exception:
                        self._offline_streak += 1
                        self._safe_emit(self.sync_status_changed, "Veritabanı: Çevrimdışı (Yerel Mod)")
                    self._last_pull_time = now
                self._sleep_interruptible(0.5)

    def _poll_interval(self) -> float:
        """Seconds between polls.

        Was 60s, and had to be: each poll pulled the entire cloud (11.59 MB, ~7s),
        so anything faster kept the app permanently busy downloading. That is what
        made changes take a minute to cross between devices — or appear only after a
        logout/login, which forces a fresh pull.

        With /api/sync/index a poll is ~27 KB and ~0.5s, so 3 seconds is affordable
        and the app feels live even if the WebSocket is blocked by a firewall. When
        the socket IS connected its nudge triggers an immediate pull, so this is just
        the safety net.

        The backoff on failure stays: a laptop that is simply offline should not
        hammer a dead connection every three seconds.
        """
        if self._offline_streak:
            return min(10.0 * (2 ** min(self._offline_streak, 5)), 300.0)
        return 3.0

    def request_pull(self):
        """Asks the worker to sync now — called when a realtime nudge arrives."""
        self._pull_requested = True
        self._wake.set()

    def stop(self):
        self._is_running = False
        self._wake.set()  # don't make shutdown wait out the current sleep


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
        # Starts at 1s rather than 3s: the common cause of a first-attempt failure is
        # the auth token not being written yet, which resolves in well under a second.
        self._reconnect_delay_ms = 1000

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
        token = api_client.token or api_client.load_token()
        if not token:
            # No usable token YET. This used to just return, permanently — nothing
            # rescheduled the attempt, so if the socket was opened a moment before
            # the token landed on disk, realtime stayed dead for the whole session
            # and only the poll loop kept working. Retry instead.
            self._schedule_reconnect()
            return
        ws_base = api_client.base_url.replace("https://", "wss://").replace("http://", "ws://")
        url = QUrl(f"{ws_base}/ws/{self._slug}?token={token}")

        self._socket = QWebSocket()
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.textMessageReceived.connect(self._on_message)
        self._socket.errorOccurred.connect(self._on_error)
        self._socket.open(url)

    def _on_connected(self):
        self._reconnect_delay_ms = 1000  # reset backoff after a successful connection
        self.connection_state_changed.emit(True)
        # Sync straight away. While the socket was down this device heard about
        # nothing, so the first thing to do once it is back is find out what it
        # missed — otherwise a change made during the outage waits for the next poll.
        self.sync_notified.emit(self._slug or "")

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
