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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
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
    """Shows a self-dismissing confirmation card and returns immediately.

    Signature is unchanged so the 13 existing call sites keep working, but
    `duration_seconds` now only controls how long the card stays on screen after
    the caller has moved on — it never delays the caller.
    """
    try:
        toast = AppleSaveDialog(title, message, parent=parent, show_spinner=False)
        toast.setWindowOpacity(0.0)
        toast.show()
        toast.raise_()

        fade_in = QPropertyAnimation(toast, b"windowOpacity", toast)
        fade_in.setDuration(90)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.OutCubic)
        fade_in.start()

        _LIVE_TOASTS.append(toast)

        # Cap the on-screen time: some callers asked for 1.2s, which is long enough
        # to feel like the app is stuck even when it is fully responsive underneath.
        visible_ms = int(max(0.12, min(float(duration_seconds or 0.35), 0.7)) * 1000)

        def _dismiss():
            fade_out = QPropertyAnimation(toast, b"windowOpacity", toast)
            fade_out.setDuration(120)
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            fade_out.setEasingCurve(QEasingCurve.InCubic)

            def _finish():
                try:
                    toast.close()
                    toast.deleteLater()
                finally:
                    if toast in _LIVE_TOASTS:
                        _LIVE_TOASTS.remove(toast)

            fade_out.finished.connect(_finish)
            fade_out.start()
            toast._fade_out = fade_out  # keep a reference alive for the animation

        QTimer.singleShot(visible_ms, _dismiss)
        toast._fade_in = fade_in
    except Exception as exc:
        print("[run_apple_save_sequence] note:", exc)
