# -*- coding: utf-8 -*-
"""
save_dialog.py — 60 FPS smooth progress feedback and Apple loading transitions.
"""
from PySide6.QtWidgets import (
    QApplication, QDialog, QLabel, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt, QTimer, QRectF, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QPainterPath

import bk_ui


class MiniLoadingSpinner(QWidget):
    """Silky smooth 60 FPS Apple-style circular spinner with zero frame drops."""

    def __init__(self, parent=None, size=34, color="#0071E3"):
        super().__init__(parent)
        self._size = size
        self._color = QColor(color)
        self.setFixedSize(size, size)
        self._angle = 0.0
        
        # 60 FPS = 16ms timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(16)

    def _step(self):
        self._angle = (self._angle + 4.8) % 360.0
        self.update()

    def stop(self):
        self._timer.stop()

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        
        cx, cy = self.width() / 2.0, self.height() / 2.0
        r = (self._size / 2.0) - 3.5
        
        p.translate(cx, cy)
        p.rotate(self._angle)
        
        # Soft background track
        c = self._color
        pen_bg = QPen(QColor(c.red(), c.green(), c.blue(), 25), 2.8)
        pen_bg.setCapStyle(Qt.RoundCap)
        p.setPen(pen_bg)
        p.drawArc(QRectF(-r, -r, r * 2, r * 2), 0, 360 * 16)
        
        # Smooth conical gradient active arc (no harsh edge cutoffs)
        from PySide6.QtGui import QConicalGradient
        grad = QConicalGradient(0, 0, 0)
        grad.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), 255))
        grad.setColorAt(0.65, QColor(c.red(), c.green(), c.blue(), 80))
        grad.setColorAt(0.9, QColor(c.red(), c.green(), c.blue(), 0))
        grad.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
        
        pen_fg = QPen(grad, 2.8)
        pen_fg.setCapStyle(Qt.RoundCap)
        p.setPen(pen_fg)
        p.drawArc(QRectF(-r, -r, r * 2, r * 2), 0, int(320 * 16))
        p.end()


class AppleSaveDialog(QDialog):
    """Modal loading & preparation card running with smooth 60 FPS animation."""

    def __init__(self, title="Hazırlanıyor...",
                 message="Çalışma alanı ve ders programı hazırlanıyor...",
                 parent=None, show_spinner=True):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 160 if show_spinner else 115)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        container = QWidget(self)
        container.setObjectName("saveCard")
        container.setStyleSheet(f"""
            #saveCard {{
                background: #FFFFFF;
                border: 1px solid {bk_ui.HAIRLINE_STRONG};
                border-radius: 14px;
            }}
        """)

        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(24, 18, 24, 18)
        c_lay.setSpacing(8)
        c_lay.setAlignment(Qt.AlignCenter)

        self.spinner = None
        if show_spinner:
            self.spinner = MiniLoadingSpinner(parent=self, size=32, color=bk_ui.BRAND)
            c_lay.addWidget(self.spinner, 0, Qt.AlignCenter)
            c_lay.addSpacing(2)

        self.title_lbl = QLabel(title)
        self.title_lbl.setFont(bk_ui.font(11.5, QFont.DemiBold))
        self.title_lbl.setStyleSheet(f"color: {bk_ui.INK}; background: transparent; border: none;")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setWordWrap(True)
        c_lay.addWidget(self.title_lbl)

        self.msg_lbl = QLabel(message)
        self.msg_lbl.setFont(bk_ui.font(8.8))
        self.msg_lbl.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent; border: none;")
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

    def showEvent(self, event):
        super().showEvent(event)
        self.setWindowOpacity(0.0)
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(160)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def close_smooth(self):
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(180)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(self.close)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def closeEvent(self, event):
        if self.spinner is not None:
            self.spinner.stop()
        super().closeEvent(event)


def run_apple_save_sequence(parent, duration_seconds=0.35,
                            title="Değişiklikler Kaydediliyor",
                            message="Veritabanı ve bulut senkronizasyonu yapılıyor...",
                            **_ignored):
    """Reports progress cleanly in the status bar or dashboard inline strip."""
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

        flash = getattr(window, "_flash_status", None) or getattr(parent, "_flash_status", None)
        if callable(flash):
            flash(title)
    except Exception as exc:
        print("[run_apple_save_sequence] note:", exc)


def __getattr__(name):
    if name == "AppleConfirmDialog":
        from home_dashboard import AppleConfirmDialog
        return AppleConfirmDialog
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
