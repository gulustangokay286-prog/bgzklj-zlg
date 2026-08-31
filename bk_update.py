"""In-process update engine for BK Planner.

Replaces the standalone Updater.exe background service entirely — that
service (spawned by Launcher, kept alive independently, holding its own
WebSocket connection) was the "bir sürü updater arka planda çalışıyor"
complaint made real: Task Manager legitimately showed extra always-on
processes for something the user never asked to run.

Every update check, download, verify, stage, and activate now happens
INSIDE this process, using the ReleaseSystem client package directly (same
engine, same crash-safety guarantees, same content-defined-chunking speed —
none of that changes) — just called as a library instead of run as a
separate exe, from two places:

  1. Synchronously on the splash screen at startup (see splash_screen.py),
     with real progress, so a stale install catches up and finishes BEFORE
     the dashboard ever shows — exactly "loading ekranında güncellemeleri
     indirmeli ve uygulamalıdır".
  2. On a background thread while the app is already open, polling
     periodically. When something new is found and staged, this shows
     UpdateAvailableSheet ("Şimdi Güncelle" / "Daha Sonra") instead of
     silently applying — the user asked explicitly never to be surprised
     by a restart, only offered one.

Trade-off worth stating plainly: dropping the standalone agent means
dropping its always-open WebSocket, so a release published while the app
is running is noticed within one polling interval (IN_SESSION_POLL_MS)
rather than within the same second. Given the explicit ask to eliminate
background processes, that's the right trade for this app.

Everything here no-ops safely under `python main.py` (dev, unfrozen) —
install_root() returns None and every public function checks for that.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

import bk_branding
from version import APP_VERSION

IN_SESSION_POLL_MS = 10 * 60 * 1000  # 10 minutes


def _release_system_root() -> Path | None:
    """Only meaningful in dev (`python main.py`) — in a frozen build the
    `client` package is compiled straight into this exe's own archive by
    the PyInstaller spec's `pathex`, so no filesystem path is needed."""
    if getattr(sys, "frozen", False):
        return None
    candidate = Path(__file__).resolve().parent.parent / "ReleaseSystem"
    return candidate if candidate.is_dir() else None


_rs_root = _release_system_root()
if _rs_root is not None and str(_rs_root) not in sys.path:
    sys.path.insert(0, str(_rs_root))

try:
    from client.config import ClientConfig, ca_bundle_path
    from client.networking.http_client import HttpClient
    from client.state.paths import Layout
    from client.updater.downloader import DownloadProgress
    from client.updater.engine import UpdateEngine

    _HAS_UPDATE_ENGINE = True
except Exception:
    _HAS_UPDATE_ENGINE = False


def install_root() -> Path | None:
    """BKPlanner.exe (frozen) lives at <ROOT>/Versions/<version>/ when
    launched through Launcher.exe — walk up to <ROOT>. None for a dev run
    or a copy not installed under that layout; callers must treat that as
    "updates unavailable here", not an error."""
    if not getattr(sys, "frozen", False) or not _HAS_UPDATE_ENGINE:
        return None
    exe_dir = Path(sys.executable).resolve().parent
    candidate = exe_dir.parent.parent
    if (candidate / "State").is_dir() and (candidate / "Versions").is_dir():
        return candidate
    return None


def _make_engine(root: Path) -> "UpdateEngine":
    layout = Layout(root)
    cfg = ClientConfig()
    http = HttpClient(cfg.api_base_url, verify_tls=ca_bundle_path() or True)
    engine = UpdateEngine(layout, cfg, http)
    engine.recover()
    if not engine.is_registered:
        engine.register()
    return engine


class UpdateCheckWorker(QObject):
    """One full check-and-update pass, run on a background QThread so the
    caller's UI (splash progress bar, or the rest of the app) never
    blocks. `applied` means a new version was downloaded, verified, staged
    AND activated (current.json now points at it) — not that this running
    process is executing it; that still needs a relaunch, see
    relaunch_via_launcher()."""

    progress = Signal(int, int)  # downloaded_bytes, total_bytes
    finished = Signal(bool, str)  # applied, new_version_or_empty

    def __init__(self, root: Path):
        super().__init__()
        self._root = root

    def run(self) -> None:
        applied = False
        new_version = ""
        try:
            engine = _make_engine(self._root)

            def on_progress(p: "DownloadProgress") -> None:
                self.progress.emit(p.downloaded_bytes, p.total_bytes)

            applied = engine.check_and_update(on_progress=on_progress)
            if applied:
                new_version = engine.layout.read_current().get("active_version", "")
        except Exception:
            applied = False
        self.finished.emit(applied, new_version)


def run_blocking_check(root: Path, on_progress=None) -> tuple[bool, str]:
    """Splash-screen use: runs the check on a worker thread but blocks the
    CALLING thread until it's done (via a local Qt event loop), so splash's
    existing exec()-based flow doesn't need restructuring — it just calls
    this once, synchronously, and gets back whether an update landed."""
    from PySide6.QtCore import QEventLoop

    result = {"applied": False, "version": ""}
    loop = QEventLoop()
    thread = QThread()
    worker = UpdateCheckWorker(root)
    worker.moveToThread(thread)

    def _done(applied: bool, version: str) -> None:
        result["applied"] = applied
        result["version"] = version
        loop.quit()

    worker.finished.connect(_done)
    if on_progress:
        worker.progress.connect(on_progress)
    thread.started.connect(worker.run)
    thread.start()
    loop.exec()
    thread.quit()
    thread.wait(2000)
    return result["applied"], result["version"]


def relaunch_via_launcher(root: Path) -> None:
    """Hands off to Launcher.exe (which re-reads current.json fresh and
    supervises the new version's first seconds — same crash-safe path any
    normal start takes) and hard-exits this process immediately after.
    os._exit, not sys.exit: skips atexit/cleanup that could hang on
    whatever background thread is still winding down — the new process is
    already on its way up, nothing here needs to finish gracefully."""
    launcher_exe = root / "Launcher" / "Launcher.exe"
    try:
        import subprocess

        if launcher_exe.exists():
            subprocess.Popen([str(launcher_exe)], cwd=str(launcher_exe.parent), close_fds=True)
    except Exception:
        pass
    os._exit(0)


class UpdateAvailableSheet(QWidget):
    """A modal-feeling sheet, centered on the parent window: "a new update
    is ready — update now, or later?" Never appears without the update
    already fully downloaded and verified — clicking "Şimdi Güncelle" is
    just a relaunch, not a fresh download, so it's fast."""

    def __init__(self, parent: QWidget, new_version: str):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._choice_made = False

        container = QWidget(self)
        container.setObjectName("sheetContainer")
        container.setStyleSheet(f"""
            #sheetContainer {{
                background-color: #FFFFFF;
                border-radius: 16px;
                border: 1px solid #E5E5E5;
            }}
            QLabel#sheetTitle {{ color: #111111; font-size: 19px; font-weight: 600; }}
            QLabel#sheetMessage {{ color: #444444; font-size: 14px; }}
            QPushButton#sheetPrimary {{
                background-color: {bk_branding.BRAND_BLUE}; color: #FFFFFF;
                border: none; border-radius: 10px; padding: 11px 22px; font-size: 14px; font-weight: 600;
            }}
            QPushButton#sheetPrimary:hover {{ background-color: {bk_branding.BRAND_BLUE_DARK}; }}
            QPushButton#sheetSecondary {{
                background-color: transparent; color: #666666;
                border: none; padding: 11px 18px; font-size: 14px;
            }}
            QPushButton#sheetSecondary:hover {{ color: #111111; }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(34, 28, 34, 24)
        layout.setSpacing(10)

        title = QLabel("Yeni Güncelleme Hazır")
        title.setObjectName("sheetTitle")
        layout.addWidget(title)

        msg = QLabel(f"{bk_branding.PRODUCT_NAME} {new_version} indirildi ve doğrulandı. Şimdi güncellensin mi?")
        msg.setObjectName("sheetMessage")
        msg.setWordWrap(True)
        msg.setMinimumWidth(380)
        msg.setMaximumWidth(380)
        layout.addWidget(msg)

        layout.addSpacing(8)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        btn_later = QPushButton("Daha Sonra")
        btn_later.setObjectName("sheetSecondary")
        btn_later.setCursor(Qt.PointingHandCursor)
        btn_later.clicked.connect(self._dismiss)
        btn_row.addWidget(btn_later)

        btn_now = QPushButton("Şimdi Güncelle")
        btn_now.setObjectName("sheetPrimary")
        btn_now.setCursor(Qt.PointingHandCursor)
        btn_now.clicked.connect(self._update_now)
        btn_row.addWidget(btn_now)

        layout.addLayout(btn_row)
        self.setFixedWidth(380 + 68)
        self.adjustSize()

        self.on_update_now = None  # set by the caller

    def _dismiss(self) -> None:
        self.close()

    def _update_now(self) -> None:
        self.close()
        if self.on_update_now:
            self.on_update_now()

    def show_centered(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            geo = parent.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
        else:
            x, y = 200, 200
        self.move(max(0, x), max(0, y))
        self.show()


class InSessionUpdateChecker(QObject):
    """Started once the dashboard is up. Polls on a timer; when a check
    lands a new version, shows UpdateAvailableSheet. Keeps itself alive by
    being parented to the main window, matching the pattern already used
    for the version-status checker and the old restart watcher."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._parent = parent
        self._root = install_root()
        self._busy = False
        self._notified = False
        self._thread: QThread | None = None
        self._worker: UpdateCheckWorker | None = None
        self._timer = QTimer(parent)
        self._timer.timeout.connect(self._check)
        if self._root is not None:
            self._timer.start(IN_SESSION_POLL_MS)

    def _check(self) -> None:
        if self._busy or self._notified or self._root is None:
            return
        self._busy = True
        self._thread = QThread()
        self._worker = UpdateCheckWorker(self._root)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._thread.start()

    def _on_finished(self, applied: bool, new_version: str) -> None:
        self._busy = False
        if self._thread:
            self._thread.quit()
            self._thread.wait(2000)
        if applied and new_version and new_version != APP_VERSION and not self._notified:
            self._notified = True
            sheet = UpdateAvailableSheet(self._parent, new_version)
            sheet.on_update_now = lambda: relaunch_via_launcher(self._root)
            sheet.show_centered()


def start_in_session_checker(parent: QWidget) -> None:
    parent._bk_update_checker = InSessionUpdateChecker(parent)  # noqa: SLF001
