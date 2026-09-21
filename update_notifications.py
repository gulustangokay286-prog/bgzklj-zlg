""""What's New" toast, shown once, centered on screen, right when the app
opens, if this launch is the first run of a version the updater just
installed. Sourced from State/pending_notes.json (written by
bk_update.apply_and_restart just before the install directory is swapped),
which is consumed (deleted) the moment it's read, so it can never show
twice.

Also `VersionStatusChecker` — a lightweight background query against the
control-plane's own "what should this device be running" endpoint (the
same one ota_update.py uses), for the small "up to date" / "update
available" label next to the version number on the home screen.

The "update is ready, restart now?" case lives in bk_update.py /
update_overlay.py, not here — this module only ever shows a one-time
informational toast, never one that asks for a restart.

Fails silent everywhere: any I/O or network error is swallowed — this must
never be able to crash or block the app.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

import bk_branding
from version import APP_VERSION

WHATS_NEW_DURATION_MS = 3000
VERSION_CHECK_TIMEOUT_S = 5.0


def install_root() -> Path | None:
    """Güncelleme durum dosyalarının kökü.

    Eskiden burada <ROOT>/Versions/<sürüm>/ düzenini arayan ayrı bir kopya
    vardı ve kurulu her makinede None dönüyordu (Chenkron.iss düz kurulum
    yapıyor), yani "yenilikler" bildirimi hiç görünmüyordu. Artık tek
    kaynak ota_update: %LOCALAPPDATA%\Chenkron\OTA."""
    try:
        import ota_update

        if not ota_update.updates_supported():
            return None
        return ota_update.ota_root()
    except Exception:
        return None


class Toast(QWidget):
    """A large, plain white card, centered on the parent window, with no
    icons or emoji. The shrinking bar under the text is the countdown."""

    dismissed = Signal()

    def __init__(self, parent: QWidget, title: str, message: str, duration_ms: int, closable: bool = False):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._duration_ms = duration_ms
        self._elapsed_ms = 0

        container = QWidget(self)
        container.setObjectName("toastContainer")
        container.setStyleSheet("""
            #toastContainer {
                background-color: #FFFFFF;
                border-radius: 14px;
                border: 1px solid #E2E2E2;
            }
            QLabel#toastTitle { color: #111111; font-size: 19px; font-weight: 600; }
            QLabel#toastMessage { color: #333333; font-size: 14px; }
            QPushButton#toastClose {
                color: #9A9A9A; background: transparent; border: none; font-size: 16px;
            }
            QPushButton#toastClose:hover { color: #111111; }
            QProgressBar#toastProgress {
                background-color: #EEEEEE; border: none; border-radius: 2px; max-height: 4px;
            }
            QProgressBar#toastProgress::chunk { background-color: #111111; border-radius: 2px; }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 26, 32, 22)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("toastTitle")
        header.addWidget(title_label)
        header.addStretch(1)
        if closable:
            close_btn = QPushButton("Kapat")
            close_btn.setObjectName("toastClose")
            close_btn.setCursor(Qt.PointingHandCursor)
            close_btn.clicked.connect(self._dismiss)
            header.addWidget(close_btn)
        layout.addLayout(header)

        msg_label = QLabel(message)
        msg_label.setObjectName("toastMessage")
        msg_label.setWordWrap(True)
        msg_label.setMinimumWidth(420)
        msg_label.setMaximumWidth(420)
        layout.addWidget(msg_label)

        self._progress = QProgressBar()
        self._progress.setObjectName("toastProgress")
        self._progress.setTextVisible(False)
        self._progress.setRange(0, duration_ms)
        self._progress.setValue(duration_ms)
        layout.addWidget(self._progress)

        self.setFixedWidth(420 + 64)
        self.adjustSize()

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(100)

    def _tick(self) -> None:
        self._elapsed_ms += 100
        remaining = max(0, self._duration_ms - self._elapsed_ms)
        self._progress.setValue(remaining)
        if remaining <= 0:
            self._dismiss()

    def _dismiss(self) -> None:
        self._tick_timer.stop()
        self.dismissed.emit()
        self.close()

    def show_toast(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            geo = parent.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
        else:
            screen = QApplication.primaryScreen()
            avail = screen.availableGeometry() if screen else None
            if avail is not None:
                x = avail.x() + (avail.width() - self.width()) // 2
                y = avail.y() + (avail.height() - self.height()) // 2
            else:
                x, y = 100, 100
        self.move(max(0, x), max(0, y))
        self.setWindowOpacity(0.0)
        self.show()
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._anim = anim  # keep a reference alive


def check_and_show_whats_new(parent: QWidget) -> None:
    root = install_root()
    if root is None:
        return
    path = root / "State" / "pending_notes.json"
    if not path.exists():
        return

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = None

    try:
        path.unlink()
    except OSError:
        pass  # consumed-once guarantee is best-effort, not load-bearing for correctness

    if not data or data.get("version") != APP_VERSION:
        return
    notes = (data.get("notes") or "").strip()
    if not notes:
        return

    toast = Toast(parent, title=f"Yeni Güncelleme — v{APP_VERSION}", message=notes, duration_ms=WHATS_NEW_DURATION_MS)
    toast.show_toast()


class VersionStatusChecker(QObject):
    """One-shot background check of whether a newer release than the one
    currently running exists on the server, for the small status label on
    the home screen. Runs the network call on a background thread (never
    blocks the UI) and marshals the result back via a Qt signal, since
    touching widgets from a non-GUI thread isn't safe. Uses the same
    client identity and config bk_update.py's engine uses — see that
    module for why there's exactly one code path talking to the
    control-plane now instead of two slightly-different ones.

    result_ready(status, detail):
        status is one of "latest", "update_available", "unknown" (network
        error, offline, or no install-root context to check against —
        treated as "can't tell", not as "out of date").
        detail is the newer version string when status=="update_available",
        else "".
    """

    result_ready = Signal(str, str)

    def start(self) -> None:
        import threading

        threading.Thread(target=self._run, name="version-status-check", daemon=True).start()

    def _run(self) -> None:
        status, detail = "unknown", ""
        try:
            import ota_update

            if not ota_update.updates_supported():
                self.result_ready.emit("unknown", "")
                return

            client = ota_update.OtaClient(APP_VERSION)
            client.http.timeout = VERSION_CHECK_TIMEOUT_S
            info = client.check()
            if info is not None:
                status, detail = "update_available", info.version
            else:
                status = "latest"
        except Exception:
            status = "unknown"
        self.result_ready.emit(status, detail)
