# -*- coding: utf-8 -*-
"""splash_screen.py — BK Planner startup screen.

The wordmark is DRAWN, not faded in: each letter's outline is traced along
its real glyph contours (the iPhone "hello" effect), then inked in, one
letter after another. No logo, no sliding progress bar — the animation is
the type itself.

How the trace works: QPainterPath.addText() gives a glyph's outline as
one or more closed contours. toSubpathPolygons() flattens those to
polylines, which can be measured and walked by arc length — so "draw 43%
of this letter" is exact, and contours are walked separately so the pen
never jumps across a gap (the dot of an "i", the counter of a "B") and
leaves a stray connecting line.

This screen is also where updates actually happen. It is not "emek payı"
(fake padding to look busy) — every second on screen is real work: session
check, then update check, then, if one is found, the full
download+verify+stage+activate cycle with the percentage shown as text.
Nothing needs downloading? It leaves as soon as the animation finishes.
Something big does? It stays exactly as long as that takes. If an update
IS applied, this never returns to main.py at all — it relaunches into the
new version via Launcher.exe and hard-exits (see bk_update.py).
"""
import time
import os

from PySide6.QtCore import QObject, QPointF, Qt, QThread, QTimer, Signal, QRectF
from PySide6.QtGui import (
    QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen,
    QPixmap, QImage, QConicalGradient, QTransform
)
from PySide6.QtWidgets import QDialog, QWidget

import bk_branding
import bk_update
from version import APP_VERSION

# Animation timing (ms)
INTRO_TOTAL_MS = 4500  # Longer duration for the labor share screen

def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def _ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3

class _WordmarkCanvas(QWidget):
    """Draws the new Chenkron C-Sync logo animation."""
    finished_intro = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_text = ""
        self._elapsed_ms = 0
        self._intro_done_emitted = False
        self._intro_total_ms = INTRO_TOTAL_MS

        self._subtitle_font = QFont("Segoe UI", 11)
        self._subtitle_font.setWeight(QFont.DemiBold)
        self._status_font = QFont("Segoe UI", 9)
        self._version_font = QFont("Segoe UI", 8)

        logo_path = os.path.join(bk_branding._HERE, "resources", "chenkron_logo.png")
        self.logo_pixmap = QPixmap(logo_path)

        self._t0 = time.monotonic()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def set_status(self, text: str) -> None:
        self._status_text = text
        self.update()

    def _tick(self) -> None:
        self._elapsed_ms = int((time.monotonic() - self._t0) * 1000)
        if not self._intro_done_emitted and self._elapsed_ms >= self._intro_total_ms:
            self._intro_done_emitted = True
            self.finished_intro.emit()
        self.update()

    def _paint_timetable_motif(self, p, rect):
        left = rect.left() + 40
        width = rect.width() - 80
        col_w = width / 5
        row_h = 34.0
        top = rect.top() + 60
        rows = int((rect.bottom() - top) / row_h) + 2

        DAYS = ("Pzt", "Sal", "Çar", "Per", "Cum")
        GRID_BLOCKS = (
            (0, 0, 2, False), (2, 0, 1, True),  (4, 0, 1, False),
            (1, 1, 2, False), (3, 1, 1, True),  (2, 2, 2, False),
            (4, 2, 2, False), (0, 3, 1, False), (3, 3, 2, False),
            (1, 4, 1, False), (0, 5, 2, False), (2, 5, 1, False),
            (4, 5, 2, False),
        )

        p.setBrush(Qt.NoBrush)
        p.setPen(QColor(20, 20, 40, 40))
        for i, day in enumerate(DAYS):
            p.drawText(
                QRectF(left + i * col_w, top - 22, col_w, 16),
                Qt.AlignHCenter | Qt.AlignVCenter, day,
            )

        for c, r, span, accent in GRID_BLOCKS:
            block = QRectF(
                left + c * col_w + 3, top + r * row_h + 3,
                col_w - 6, row_h * span - 6,
            )
            col = QColor(bk_branding.BRAND_BLUE) if accent else QColor(20, 20, 40)
            col.setAlpha(25 if accent else 8)
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawRoundedRect(block, 4, 4)

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(20, 20, 40, 12), 1))
        for i in range(6):
            x = left + i * col_w
            p.drawLine(QPointF(x, top), QPointF(x, rect.bottom()))
        for j in range(rows):
            y = top + j * row_h
            if y > rect.bottom():
                break
            p.drawLine(QPointF(left, y), QPointF(left + width, y))

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        
        p.fillRect(self.rect(), QColor("#FFFFFF"))
        
        p.save()
        self._paint_timetable_motif(p, self.rect())
        p.restore()
        
        # Scrim under logo to make it pop and readable
        scrim_y = self.rect().bottom() - 180
        scrim = QRectF(0, scrim_y, self.width(), 180)
        from PySide6.QtGui import QLinearGradient
        sg = QLinearGradient(scrim.topLeft(), scrim.bottomLeft())
        sg.setColorAt(0.0, QColor(255, 255, 255, 0))
        sg.setColorAt(1.0, QColor(255, 255, 255, 240))
        p.fillRect(scrim, sg)

        cx = self.width() / 2.0
        cy = self.height() / 2.0 - 26
        
        anim_progress = min(1.0, self._elapsed_ms / (self._intro_total_ms * 0.7))
        draw_f = _ease_out_cubic(anim_progress)
        
        rotation = self._elapsed_ms * 0.12 
        
        logo_size = 140
        
        if not self.logo_pixmap.isNull():
            p.save()
            p.translate(cx, cy)
            
            # Smooth entrance scaling & opacity without any masking cutoff artifacts
            scale = 0.85 + 0.15 * draw_f
            p.scale(scale, scale)
            p.setOpacity(draw_f)
            
            p.rotate(rotation)
            scaled_pix = self.logo_pixmap.scaled(logo_size, logo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(int(-logo_size / 2), int(-logo_size / 2), scaled_pix)
            p.restore()
        
        sub_local = self._elapsed_ms - 800
        if sub_local > 0:
            eased = _ease_out_cubic(min(1.0, sub_local / 800))
            c = QColor("#5A5A5E")
            c.setAlphaF(eased)
            p.setPen(c)
            p.setFont(self._subtitle_font)
            rise = int(10 * (1 - eased))
            p.drawText(
                0, int(cy + logo_size/2 + 24 + rise), self.width(), 22,
                Qt.AlignHCenter | Qt.AlignTop,
                "Chenkron Ders Dağıtım ve Yönetim Sistemi",
            )
            
        status_local = sub_local - 400
        if status_local > 0 and self._status_text:
            f = min(1.0, status_local / 320)
            c = QColor("#808084")
            c.setAlphaF(f)
            p.setPen(c)
            p.setFont(self._status_font)
            p.drawText(
                0, int(cy + logo_size/2 + 54), self.width(), 20,
                Qt.AlignHCenter | Qt.AlignTop, self._status_text,
            )

        c = QColor("#C8C8CB")
        p.setPen(c)
        p.setFont(self._version_font)
        p.drawText(0, self.height() - 28, self.width(), 18, Qt.AlignHCenter | Qt.AlignTop, f"v{APP_VERSION}")
        p.end()



class _AuthWorker(QObject):
    finished = Signal(bool, object)

    def run(self) -> None:
        ok, auth = False, None
        try:
            from api_client import api_client

            ok, auth = api_client.auto_authenticate()
        except Exception:
            ok, auth = False, None
        self.finished.emit(bool(ok and auth), auth)


class BKSplashScreen(QDialog):
    def __init__(self, root, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
        # NOT WA_DeleteOnClose — accept() must end exec()'s modal loop
        # without the C++ object dying mid-unwind, or the window can be
        # left orphaned on screen with nothing able to close it.
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setFixedSize(640, 440)

        self._root = root
        self.is_valid_token = False
        self.auth_data = None
        self._work_done = False
        self._intro_done = False
        self._pending_relaunch = False

        self.canvas = _WordmarkCanvas(self)
        self.canvas.setGeometry(0, 0, 640, 440)
        self.canvas.finished_intro.connect(self._on_intro_done)

        QTimer.singleShot(40, self._run_sequence)

    # --- Work ---------------------------------------------------------------
    def _run_sequence(self) -> None:
        self.canvas.set_status("Oturum doğrulanıyor...")
        self._auth_thread = QThread()
        self._auth_worker = _AuthWorker()
        self._auth_worker.moveToThread(self._auth_thread)
        self._auth_thread.started.connect(self._auth_worker.run)
        self._auth_worker.finished.connect(self._on_auth_done)
        self._auth_thread.start()

    def _on_auth_done(self, ok: bool, auth) -> None:
        self.is_valid_token = ok
        self.auth_data = auth
        self._auth_thread.quit()
        self._auth_thread.wait(2000)

        if self._root is None:
            self._work_done = True
            self._maybe_finish()
            return

        self.canvas.set_status("Güncellemeler kontrol ediliyor...")

        def on_progress(downloaded: int, total: int) -> None:
            if total > 0:
                pct = int(100 * downloaded / total)
                self.canvas.set_status(f"Güncelleme indiriliyor  %{pct}")

        applied, new_version = bk_update.run_blocking_check(self._root, on_progress=on_progress)
        if applied:
            self.canvas.set_status(f"Güncelleme tamamlandı — v{new_version}")
            self._pending_relaunch = True
            QTimer.singleShot(900, lambda: bk_update.relaunch_via_launcher(self._root))
            return

        self.canvas.set_status("Hazır")
        self._work_done = True
        self._maybe_finish()

    # --- Exit gating --------------------------------------------------------
    def _on_intro_done(self) -> None:
        self._intro_done = True
        self._maybe_finish()

    def _maybe_finish(self) -> None:
        """Leaves only once BOTH the animation has finished and the real
        work is done — so a fast machine never flashes the screen for a
        third of a second, and a slow update never gets cut off."""
        if self._pending_relaunch:
            return
        if self._work_done and self._intro_done:
            QTimer.singleShot(260, self.accept)
