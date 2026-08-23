# -*- coding: utf-8 -*-
"""
save_dialog.py — non-blocking progress feedback.

This module used to hold the single largest source of the app's perceived lag.
run_apple_save_sequence() ran a busy-wait on the GUI thread:

    t_end = time.time() + dur
    while time.time() < t_end:
        QApplication.processEvents()
        time.sleep(0.016)

and clamped `dur` to a 0.25s MINIMUM, so a caller asking for 0.1s still froze the
interface for a quarter second. It sat on every navigation path — Ana Sayfa, close,
save, set-active, opening a schedule, deleting a folder — which is exactly the set
of buttons that felt terrible to press. On top of that the card carried a 40px-blur
drop shadow and repainted an antialiased spinner every 16ms, which on a 2GB machine
costs more than the work being waited for.

Nothing was ever waiting on that loop; the actual saving is synchronous and already
finished before the dialog appeared. The delay was pure theatre.

The replacement shows the same card, dismisses itself on a QTimer, and returns
immediately, so the caller's next line runs on the very next frame.
"""
from PySide6.QtWidgets import (
    QApplication, QDialog, QLabel, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt, QTimer, QRectF, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QFont, QPen

# Toasts are parented to the app, not to a local variable, so they survive the
# function returning without being garbage-collected mid-animation.
_LIVE_TOASTS = []


class MiniLoadingSpinner(QWidget):
    """Kept for the manual-sync dialog, which genuinely does wait on the network.

    Repaints at 20 FPS rather than 60: the arc rotates visibly either way, and this
    is a third of the paint cost on low-end hardware.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(50)

    def _rotate(self):
        self._angle = (self._angle + 18) % 360
        self.update()

    def stop(self):
        self._timer.stop()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.translate(self.width() / 2, self.height() / 2)
        p.rotate(self._angle)
        p.setPen(QPen(QColor("#0071E3"), 3.0, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(QRectF(-13, -13, 26, 26), 0, 270 * 16)


class AppleSaveDialog(QDialog):
    """Blocking-capable card, still used where the app really is waiting on I/O
    (the manual 'sync now' action drives it via show()/close() itself)."""

    def __init__(self, title="Değişiklikler Kaydediliyor",
                 message="Veritabanı ve bulut senkronizasyonu yapılıyor...",
                 parent=None, show_spinner=True):
        super().__init__(parent)
        # NoDropShadowWindowHint: on macOS a frameless + translucent window still gets a
        # native Cocoa shadow layer, and that layer is what paints as an opaque black
        # rectangle when the compositor cannot resolve the window's alpha. The in-app
        # QGraphicsDropShadowEffects were removed for this same symptom; this is the
        # remaining shadow source. The cards draw their own border, so nothing is lost.
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 170 if show_spinner else 120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        container = QWidget(self)
        container.setObjectName("saveCard")
        # A painted 1px border instead of a QGraphicsDropShadowEffect: the blur was
        # re-rendered on every repaint and is one of the most expensive things you
        # can attach to a widget on a machine without a GPU.
        container.setStyleSheet("""
            #saveCard {
                background: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.14);
                border-radius: 16px;
            }
        """)

        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(26, 18, 26, 18)
        c_lay.setSpacing(7)
        c_lay.setAlignment(Qt.AlignCenter)

        self.spinner = None
        if show_spinner:
            self.spinner = MiniLoadingSpinner(self)
            c_lay.addWidget(self.spinner, 0, Qt.AlignCenter)

        self.title_lbl = QLabel(title)
        self.title_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.title_lbl.setStyleSheet("color: #1D1D1F; background: transparent; border: none;")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setWordWrap(True)
        c_lay.addWidget(self.title_lbl)

        self.msg_lbl = QLabel(message)
        self.msg_lbl.setFont(QFont("Segoe UI", 9))
        self.msg_lbl.setStyleSheet("color: #636366; background: transparent; border: none;")
        self.msg_lbl.setAlignment(Qt.AlignCenter)
        self.msg_lbl.setWordWrap(True)
        c_lay.addWidget(self.msg_lbl)

        layout.addWidget(container)
        self._center_on(parent)

    def _center_on(self, parent):
        anchor = None
        if parent is not None:
            try:
                window = parent.window()
                if window is not None and window.isVisible():
                    anchor = window.geometry()
            except Exception:
                anchor = None
        if anchor is None:
            screen = QApplication.primaryScreen()
            if screen is None:
                return
            anchor = screen.availableGeometry()
        self.move(
            anchor.center().x() - self.width() // 2,
            anchor.center().y() - self.height() // 2,
        )

    def closeEvent(self, event):
        if self.spinner is not None:
            self.spinner.stop()
        super().closeEvent(event)


def run_apple_save_sequence(parent, duration_seconds=0.35,
                            title="Değişiklikler Kaydediliyor",
                            message="Veritabanı ve bulut senkronizasyonu yapılıyor...",
                            **_ignored):
    """Reports progress in the status bar. Opens no window.

    This used to put a 420x120 frameless, translucent, always-on-top card in the
    dead centre of the screen on every save, every navigation, every close — 13 call
    sites in all. Users saw it as "a square in the middle of the screen", on every
    platform, because that is exactly what it is: a borderless rectangle that
    appears over whatever they were looking at.

    It existed to cover a wait that no longer happens. The work it was hiding —
    saving a version, returning to the dashboard, syncing — now completes in
    milliseconds, so there is nothing to show progress for. Feedback goes to the
    status bar instead, where it is visible without covering anything and without
    stealing focus.

    The signature is unchanged so all 13 call sites keep working untouched, and
    `duration_seconds` now only controls how long the status message lingers.
    """
    try:
        window = None
        if parent is not None:
            try:
                window = parent.window()
            except Exception:
                window = None

        bar = None
        if window is not None and hasattr(window, "statusBar"):
            try:
                bar = window.statusBar()
            except Exception:
                bar = None

        if bar is not None:
            text = f"{title} — {message}" if message else title
            bar.showMessage(text.replace("\n", " "), int(max(0.5, float(duration_seconds or 0.35)) * 1000))
            return

        # No status bar (the dashboard is a plain QWidget). Its own inline strip is
        # the right place; falling back to silence is still better than a window.
        flash = getattr(window, "_flash_status", None) or getattr(parent, "_flash_status", None)
        if callable(flash):
            flash(title)
    except Exception as exc:
        print("[run_apple_save_sequence] note:", exc)
