"""
updater.py — background over-the-air updates.

The previous arrangement had two halves that were never connected:

  * push_ota.py published a manifest to a Firebase Realtime Database the app had
    already stopped using, and
  * main_window._act_check_updates polled {base_url}/api/updates on the VDS, which
    did not exist — so the request always failed, always fell into the "you are on
    the newest version" branch, and no user could ever be told about an update.

The VDS now serves /api/updates (see Bogazici_Backend/main.py). This module polls
it, downloads the package in the background while the user keeps working, verifies
its SHA-256, and stages it. Installation happens on exit, because a running .exe
cannot overwrite itself on Windows.

Nothing here blocks the GUI thread and nothing installs without the user agreeing.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import threading

import requests
from PySide6.QtCore import QObject, Signal

from version import APP_BUILD, APP_VERSION


def _staging_dir() -> str:
    path = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "updates")
    os.makedirs(path, exist_ok=True)
    return path


def is_frozen() -> bool:
    """True when running as a PyInstaller bundle rather than from source."""
    return getattr(sys, "frozen", False)


class UpdateChecker(QObject):
    """Checks for, and downloads, a newer build without interrupting the user.

    update_available fires once a package is downloaded AND verified, so the user is
    only ever offered an update that is actually ready to install.
    """

    update_available = Signal(dict)     # manifest, package already staged
    download_progress = Signal(int)     # 0-100
    check_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._staged_path = None
        self._manifest = None

    # ── Public API ────────────────────────────────────────────────────────

    def check_async(self, auto_download: bool = True):
        """Starts a check on a background thread. Safe to call repeatedly."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._check, args=(auto_download,), daemon=True
        )
        self._thread.start()

    @property
    def staged_package(self):
        return self._staged_path

    @property
    def manifest(self):
        return self._manifest

    # ── Worker ────────────────────────────────────────────────────────────

    def _check(self, auto_download: bool):
        try:
            from api_client import api_client
            manifest = api_client.get_latest_release()
        except Exception as exc:
            self.check_failed.emit(str(exc))
            return

        if not manifest:
            self.check_failed.emit("no-release")
            return

        try:
            remote_build = int(manifest.get("build") or 0)
        except (TypeError, ValueError):
            remote_build = 0

        if remote_build <= APP_BUILD:
            self.check_failed.emit("up-to-date")
            return

        self._manifest = manifest
        if not auto_download:
            self.update_available.emit(manifest)
            return

        url = manifest.get("url") or ""
        if not url:
            self.check_failed.emit("no-package-url")
            return

        try:
            path = self._download(url, manifest.get("sha256") or "")
        except Exception as exc:
            self.check_failed.emit(f"download-failed: {exc}")
            return

        if path:
            self._staged_path = path
            self.update_available.emit(manifest)

    def _download(self, url: str, expected_sha: str):
        """Streams the package to disk, verifying it before it is trusted.

        Downloads to a .part file and only renames on success, so an interrupted
        download can never be mistaken for a complete package.
        """
        target = os.path.join(_staging_dir(), "update_package")
        part = target + ".part"

        digest = hashlib.sha256()
        downloaded = 0
        last_pct = -1

        with requests.get(url, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length") or 0)
            with open(part, "wb") as f:
                for chunk in resp.iter_content(chunk_size=256 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = int(downloaded * 100 / total)
                        if pct != last_pct:
                            last_pct = pct
                            self.download_progress.emit(pct)

        actual = digest.hexdigest()
        if expected_sha and actual.lower() != expected_sha.lower():
            os.remove(part)
            # Refusing here is the whole point of publishing a hash: without this
            # check, anything that can answer the download URL can ship code.
            raise ValueError(
                f"checksum mismatch (expected {expected_sha[:12]}…, got {actual[:12]}…)"
            )

        if os.path.exists(target):
            os.remove(target)
        os.replace(part, target)
        return target


def install_staged_update(package_path: str, manifest: dict) -> bool:
    """Schedules the staged package to replace this installation, then returns.

    On Windows a running executable holds a lock on its own file, so the swap is
    handed to a small batch script that waits for this process to exit first. The
    caller should quit immediately afterwards.

    Returns False (changing nothing) when running from source, where there is no
    bundle to replace.
    """
    if not package_path or not os.path.exists(package_path):
        return False

    if not is_frozen():
        # From source, the sane action is to show the user where the package is
        # rather than to start overwriting .py files underneath a live interpreter.
        print(f"[updater] package ready at {package_path} (source checkout — not applying)")
        return False

    app_exe = sys.executable
    app_dir = os.path.dirname(app_exe)
    staging = _staging_dir()

    if package_path.lower().endswith(".zip"):
        extract_dir = os.path.join(staging, "unpacked")
        shutil.rmtree(extract_dir, ignore_errors=True)
        shutil.unpack_archive(package_path, extract_dir)
        source = extract_dir
    else:
        source = package_path

    script = os.path.join(staging, "apply_update.bat")
    with open(script, "w", encoding="utf-8") as f:
        f.write(f"""@echo off
rem Wait for the application to release its own executable before replacing it.
:waitloop
tasklist /FI "PID eq {os.getpid()}" 2>nul | find "{os.getpid()}" >nul
if not errorlevel 1 (
    ping -n 2 127.0.0.1 >nul
    goto waitloop
)
robocopy "{source}" "{app_dir}" /E /IS /R:3 /W:2 >nul
start "" "{app_exe}"
""")

    subprocess.Popen(
        ["cmd", "/c", script],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        close_fds=True,
    )
    return True


def current_version_string() -> str:
    return f"{APP_VERSION} (build {APP_BUILD})"
