"""Ordered, durable version uploads shared by every editor in this process."""
import copy
import json
import os
import threading
import time
import uuid
from collections import OrderedDict

# Only disk read/modify/write sections hold this lock, never network requests.
version_lock = threading.RLock()
_pending = OrderedDict()
_wake = threading.Event()
_thread = None
_maintenance = OrderedDict()
_maintenance_wake = threading.Event()
_maintenance_thread = None


def file_signature(path):
    try:
        st = os.stat(path)
        return st.st_mtime_ns, st.st_size
    except OSError:
        return None


def is_pending(data):
    return bool((data.get("_sync_meta") or {}).get("local_pending"))


def mark_pending(data):
    metadata = dict(data.get("_sync_meta") or {})
    metadata["local_pending"] = uuid.uuid4().hex
    data["_sync_meta"] = metadata


def enqueue(slug, filename):
    """The .roz file is the journal; repeated edits replace one queued entry."""
    import version_store
    global _thread
    path = os.path.join(version_store._versions_dir(slug), filename)
    with version_lock:
        _pending[path] = (slug, filename)
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_run, name="version-outbox", daemon=True)
            _thread.start()
    _wake.set()


def wait_for_pending(timeout: float = 2.0) -> bool:
    """Blocks until all queued uploads have finished or timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with version_lock:
            if not _pending:
                return True
        time.sleep(0.01)
    return False


def resume_pending():
    """Recover unacknowledged saves after an offline session or restart."""
    import version_store
    base = version_store._ensure_base()
    for slug in os.listdir(base):
        directory = os.path.join(base, slug, "versions")
        if not os.path.isdir(directory):
            continue
        for filename in os.listdir(directory):
            if not filename.endswith(".roz"):
                continue
            try:
                with open(os.path.join(directory, filename), encoding="utf-8") as f:
                    if is_pending(json.load(f)):
                        enqueue(slug, filename)
            except (OSError, ValueError):
                continue


def _send_one(path, slug, filename):
    import version_store
    from api_client import api_client
    with version_lock:
        try:
            with open(path, encoding="utf-8") as f:
                candidate = json.load(f)
        except (OSError, ValueError):
            _pending.pop(path, None)
            return True
        generation = (candidate.get("_sync_meta") or {}).get("local_pending")
        if not generation:
            _pending.pop(path, None)
            return True
        payload = copy.deepcopy(candidate)
        payload["_sync_meta"].pop("local_pending", None)

    ok = api_client.push_version_to_rtdb(slug, filename, payload)
    terminal = api_client.last_error in ("conflict", "deleted")
    if not ok and not terminal:
        return False

    with version_lock:
        try:
            with open(path, encoding="utf-8") as f:
                current = json.load(f)
        except (OSError, ValueError):
            _pending.pop(path, None)
            return True
        if (current.get("_sync_meta") or {}).get("local_pending") == generation:
            current["_sync_meta"].pop("local_pending", None)
            version_store._atomic_write_json(path, current)
            version_store.invalidate_version_summary(slug, filename)
            _pending.pop(path, None)
            if ok:
                _queue_maintenance(path, slug)
        # A newer edit is already on disk. It stays queued and uses the revision
        # from the completed upload; an old acknowledgement never clears it.
    return True


def _run():
    retry_at = {}
    while True:
        _wake.clear()
        with version_lock:
            work = list(_pending.items())
        now = time.monotonic()
        for path, (slug, filename) in work:
            if retry_at.get(path, 0) > now:
                continue
            try:
                ok = _send_one(path, slug, filename)
            except Exception as exc:
                print(f"[outbox] upload deferred: {type(exc).__name__}")
                ok = False
            if not ok:
                retry_at[path] = time.monotonic() + 2
            else:
                retry_at.pop(path, None)
                with version_lock:
                    if path in _pending:
                        _wake.set()
        _wake.wait(0.5 if work else 30)


def _queue_maintenance(path, slug):
    global _maintenance_thread
    _maintenance[path] = slug
    if _maintenance_thread is None or not _maintenance_thread.is_alive():
        _maintenance_thread = threading.Thread(target=_maintain, name="version-maintenance", daemon=True)
        _maintenance_thread.start()
    _maintenance_wake.set()


def _maintain():
    while True:
        _maintenance_wake.wait(30)
        _maintenance_wake.clear()
        with version_lock:
            jobs = list(_maintenance.items())
            _maintenance.clear()
        for path, slug in jobs:
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                import constraint_sync
                import database
                constraint_sync.publish(slug, data)
                # The backup function has its own ten-minute throttle.
                database.create_database_backup(slug, "in_place_update")
            except Exception as exc:
                print(f"[outbox] maintenance deferred: {type(exc).__name__}")
