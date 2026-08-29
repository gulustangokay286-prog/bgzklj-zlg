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

from PySide6.QtCore import QObject, QPointF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QDialog, QWidget

import bk_branding
import bk_update
from version import APP_VERSION

# Animation timing (ms)
LETTER_STAGGER_MS = 118      # gap between one letter starting and the next
LETTER_TRACE_MS = 500        # how long one letter's outline takes to draw
LETTER_INK_MS = 300          # fill fade-in, begins as that letter's trace ends
LETTER_SETTLE_PX = 7.0       # how far a letter drifts up as it inks in
SUBTITLE_FADE_MS = 560
TAIL_HOLD_MS = 380           # beat after the last letter before status text appears

# (family, point size, trace pen width). Gabriola is a calligraphic face
# with delicate strokes — it needs a larger point size than a UI sans to
# hold the same optical weight, and a thinner tracing pen so the outline
# pass doesn't read heavier than the finished letter.
_WORDMARK_FONTS = [
    ("Gabriola", 78, 1.15),
    ("Palatino Linotype", 54, 1.35),
    ("Georgia", 52, 1.35),
    ("Segoe UI", 50, 1.5),
]


def _pick_wordmark_font() -> tuple[QFont, float]:
    from PySide6.QtGui import QFontDatabase

    families = set(QFontDatabase.families())
    for name, size, pen_w in _WORDMARK_FONTS:
        if name in families:
            f = QFont(name, size)
            f.setStyleStrategy(QFont.PreferAntialias)
            return f, pen_w
    return QFont("Segoe UI", 50), 1.5


def _smoothstep(t: float) -> float:
    """Ease-in-out. A pen accelerating out of rest and decelerating into
    the end of a stroke reads as drawn; constant velocity reads as a
    machine sweeping a mask across the glyph."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


class _Letter:
    """One glyph: its filled path, its contours pre-flattened to polylines,
    and the cumulative arc lengths that make partial tracing exact."""

    __slots__ = ("path", "contours", "lengths", "total_length", "start_ms")

    def __init__(self, path: QPainterPath, start_ms: int):
        self.path = path
        self.start_ms = start_ms
        self.contours = []
        self.lengths = []
        self.total_length = 0.0
        for poly in path.toSubpathPolygons():
            pts = [poly.at(i) for i in range(poly.count())]
            if len(pts) < 2:
                continue
            seg = []
            run = 0.0
            for i in range(1, len(pts)):
                dx = pts[i].x() - pts[i - 1].x()
                dy = pts[i].y() - pts[i - 1].y()
                run += (dx * dx + dy * dy) ** 0.5
                seg.append(run)
            self.contours.append(pts)
            self.lengths.append(seg)
            self.total_length += run

    def traced_path(self, fraction: float) -> QPainterPath:
        """The portion of this glyph's outline drawn so far. Contours are
        consumed in order and each is walked by real arc length, so the
        pen never teleports between them mid-stroke."""
        out = QPainterPath()
        if fraction <= 0.0 or self.total_length <= 0.0:
            return out
        budget = self.total_length * min(1.0, fraction)

        for pts, seg in zip(self.contours, self.lengths):
            contour_len = seg[-1]
            if budget <= 0.0:
                break
            if budget >= contour_len:
                out.moveTo(pts[0])
                for p in pts[1:]:
                    out.lineTo(p)
                budget -= contour_len
                continue

            out.moveTo(pts[0])
            for i in range(1, len(pts)):
                if seg[i - 1] <= budget:
                    out.lineTo(pts[i])
                    continue
                prev_run = seg[i - 2] if i >= 2 else 0.0
                span = seg[i - 1] - prev_run
                t = (budget - prev_run) / span if span > 0 else 0.0
                a, b = pts[i - 1], pts[i]
                out.lineTo(QPointF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t))
                break
            budget = 0.0
            break
        return out


class _WordmarkCanvas(QWidget):
    """Draws the whole screen's typography and owns the animation clock."""

    finished_intro = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_text = ""
        self._elapsed_ms = 0
        self._intro_done_emitted = False

        word = bk_branding.PRODUCT_NAME
        font, self._pen_width = _pick_wordmark_font()
        fm = QFontMetricsF(font)

        total_w = fm.horizontalAdvance(word)
        baseline_y = 0.0
        x = -total_w / 2.0

        self._letters: list[_Letter] = []
        idx = 0
        for ch in word:
            adv = fm.horizontalAdvance(ch)
            if ch.strip():
                p = QPainterPath()
                p.addText(x, baseline_y, font, ch)
                self._letters.append(_Letter(p, start_ms=idx * LETTER_STAGGER_MS))
                idx += 1
            x += adv

        self._intro_total_ms = (
            (len(self._letters) - 1) * LETTER_STAGGER_MS + LETTER_TRACE_MS + LETTER_INK_MS
        )

        self._subtitle_font = QFont("Segoe UI", 10.5)
        self._status_font = QFont("Segoe UI", 9)
        self._version_font = QFont("Segoe UI", 8)

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

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#FFFFFF"))

        cx = self.width() / 2.0
        cy = self.height() / 2.0 - 26

        p.save()
        p.translate(cx, cy)

        blue = QColor(bk_branding.BRAND_BLUE)
        pen = QPen(blue, self._pen_width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)

        for letter in self._letters:
            local = self._elapsed_ms - letter.start_ms
            if local <= 0:
                continue

            # Still being drawn: outline only, pen eased so the stroke
            # starts and lands softly instead of at constant speed.
            trace_raw = local / LETTER_TRACE_MS
            if trace_raw < 1.0:
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawPath(letter.traced_path(_smoothstep(trace_raw)))
                continue

            # Drawn: ink floods in while the letter settles a few pixels
            # up into place, so it arrives rather than just appearing.
            ink_raw = (local - LETTER_TRACE_MS) / LETTER_INK_MS
            ink_f = _ease_out_cubic(ink_raw)
            settle = LETTER_SETTLE_PX * (1.0 - ink_f)

            p.save()
            p.translate(0.0, settle)

            if ink_f < 1.0:
                # Outline lingers under the filling ink and fades out as
                # the fill takes over — without it the letter visibly
                # "pops" from hairline to solid.
                outline = QColor(blue)
                outline.setAlphaF(1.0 - ink_f)
                fading_pen = QPen(outline, self._pen_width)
                fading_pen.setCapStyle(Qt.RoundCap)
                fading_pen.setJoinStyle(Qt.RoundJoin)
                p.setPen(fading_pen)
                p.setBrush(Qt.NoBrush)
                p.drawPath(letter.path)

            fill = QColor(blue)
            fill.setAlphaF(ink_f)
            p.setPen(Qt.NoPen)
            p.setBrush(fill)
            p.drawPath(letter.path)
            p.restore()

        p.restore()

        # Subtitle and status sit as one optical group under the wordmark
        # rather than being pinned to the window edge — a block of type
        # with a lot of white beneath it reads as composed; the same type
        # spread to the corners reads as leftover space.
        sub_local = self._elapsed_ms - self._intro_total_ms
        if sub_local > 0:
            eased = _ease_out_cubic(sub_local / SUBTITLE_FADE_MS)
            c = QColor("#8A8A8E")
            c.setAlphaF(eased)
            p.setPen(c)
            p.setFont(self._subtitle_font)
            rise = int(10 * (1 - eased))
            p.drawText(
                0, int(cy + 36 + rise), self.width(), 22,
                Qt.AlignHCenter | Qt.AlignTop,
                "Ders Dağıtım ve Yönetim Sistemi",
            )

        # Status line — text only, no bar
        status_local = sub_local - TAIL_HOLD_MS
        if status_local > 0 and self._status_text:
            f = min(1.0, status_local / 320)
            c = QColor("#B0B0B4")
            c.setAlphaF(f)
            p.setPen(c)
            p.setFont(self._status_font)
            p.drawText(
                0, int(cy + 74), self.width(), 20,
                Qt.AlignHCenter | Qt.AlignTop, self._status_text,
            )

        c = QColor("#D8D8DB")
        p.setPen(c)
        p.setFont(self._version_font)
        p.drawText(0, self.height() - 38, self.width(), 18, Qt.AlignHCenter | Qt.AlignTop, f"v{APP_VERSION}")
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
