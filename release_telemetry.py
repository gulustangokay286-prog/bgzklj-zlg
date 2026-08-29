"""Fire-and-forget device registration + heartbeat against the new release
control-plane (ReleaseSystem/backend, deployed on the VDS alongside the
existing sync API on its own ports/containers — see
ReleaseSystem/README.md).

Deliberately self-contained (no dependency on ReleaseSystem/client/) so this
one small file can ship in ChenKi_v2's normal build without pulling in the
Launcher/Updater package or its Ed25519 signature-verification key — a
heartbeat has nothing to verify, it's just "this device exists, on this
version." Runs on a background thread and swallows every exception: if the
release-system VDS is unreachable or slow, the app must start exactly as
fast as it always has.
"""
import json
import os
import threading
import uuid

import requests

from version import APP_VERSION

RELEASE_API_URL = os.environ.get("CHENKI_RELEASE_API_URL", "https://updates.chenki.net:8443")
PRODUCT = "chenki"
CHANNEL = os.environ.get("CHENKI_RELEASE_CHANNEL", "stable")
PLATFORM = "windows-x64"
_REQUEST_TIMEOUT = 5.0

# updates.chenki.net serves a real Let's Encrypt cert, so normal system
# trust (verify=True below) is enough — no pinning needed. This stays as a
# fallback only: if release_system_ca.pem ever reappears next to this file
# (e.g. testing against a VDS with only a self-signed cert again), it pins
# to that instead of failing closed.
_CA_BUNDLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "release_system_ca.pem")
if not os.path.exists(_CA_BUNDLE):
    _CA_BUNDLE = None


def _config_dir() -> str:
    base_dir = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
    try:
        os.makedirs(base_dir, exist_ok=True)
    except OSError:
        pass
    return base_dir


def _identity_path() -> str:
    return os.path.join(_config_dir(), "release_identity.json")


def _load_or_create_identity() -> dict:
    path = _identity_path()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            if data.get("device_uuid"):
                return data
    except (OSError, json.JSONDecodeError):
        pass

    data = {"device_uuid": str(uuid.uuid4()), "device_id": None, "device_token": None}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass
    return data


def _save_identity(data: dict) -> None:
    try:
        with open(_identity_path(), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


def _run() -> None:
    try:
        identity = _load_or_create_identity()
        session = requests.Session()
        session.verify = _CA_BUNDLE if _CA_BUNDLE else True

        if not identity.get("device_id"):
            resp = session.post(
                f"{RELEASE_API_URL}/v1/devices/register",
                json={
                    "device_uuid": identity["device_uuid"],
                    "product": PRODUCT,
                    "platform": PLATFORM,
                    "channel": CHANNEL,
                    "version": APP_VERSION,
                },
                timeout=_REQUEST_TIMEOUT,
            )
            if resp.status_code < 400:
                body = resp.json()
                identity["device_id"] = body["device_id"]
                identity["device_token"] = body["device_token"]
                _save_identity(identity)
            else:
                return

        session.post(
            f"{RELEASE_API_URL}/v1/devices/heartbeat",
            json={
                "device_id": identity["device_id"],
                "device_token": identity["device_token"],
                "version": APP_VERSION,
                "status": "healthy",
                "uptime_seconds": 0,
            },
            timeout=_REQUEST_TIMEOUT,
        )
    except Exception:
        pass  # telemetry must never affect the app


def report_startup() -> None:
    threading.Thread(target=_run, name="release-telemetry", daemon=True).start()
