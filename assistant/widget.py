"""Asistan arayüzü: daire düğme, genie animasyonu, hap giriş kutusu, cevap balonu.

Akış
----
Araç çubuğundaki küçük mavi daireye tıklanınca pencerenin üstüne şeffaf bir
katman (AssistantOverlay) gelir. Katman iki şeyi kendisi çizer:

  * Alttan yukarı SOLAN GÖLGE — ilerlemeyle koyulaşır.
  * GENIE HUNİSİ — macOS'un küçültme efektinin tersi: daireden aşağıya doğru
    bir huni akar, altta hap biçimli giriş kutusuna dönüşür; sonra huninin
    boynu daireden kopup aşağı çekilir ve yalnızca hap kalır. Kapanırken
    aynı yol tersinden oynar.

Hapın içi (＋, metin kutusu, model rozeti, mikrofon, mavi gönder dairesi)
gerçek widget'lardır; huni hap hâline geldiğinde solarak görünürler. Cevap
balonu hapın üstünde durur, araç adımlarını ve modelin cevabını gösterir.
"""
from PySide6.QtCore import (Qt, QRect, QRectF, QPointF, QPropertyAnimation, QEasingCurve,
                            Property, QTimer, Signal, QSize, QParallelAnimationGroup)
from PySide6.QtGui import (QPainter, QColor, QLinearGradient, QPainterPath, QPen, QBrush,
                           QFont, QRadialGradient)
from PySide6.QtWidgets import (QWidget, QToolButton, QLineEdit, QLabel, QHBoxLayout,
                               QGraphicsOpacityEffect, QMenu, QSizePolicy)

FONT = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"
BLUE = QColor("#2F6BE4")
BLUE_HI = QColor("#4A85F0")
PILL_BG = QColor(30, 30, 32)
PILL_BORDER = QColor(255, 255, 255, 22)
TEXT = QColor("#F2F2F2")
MUTED = QColor("#A5A5AA")

PILL_H = 56
PILL_MAX_W = 720
PILL_BOTTOM = 26
OPEN_MS = 520
CLOSE_MS = 380
WAVE = (0.36, 0.72, 1.0, 0.62, 0.30)


def draw_waveform(p, rect, color, phase=0.0, amp=None):
    """Beş dikey çubuk — ses dalgası. amp verilirse çubuk boyları onunla çarpılır."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    n = len(WAVE)
    bw = max(2.0, rect.width() / (n * 2.2))
    gap = (rect.width() - n * bw) / (n - 1)
    x = rect.left()
    for i, h in enumerate(WAVE):
        if amp is not None:
            h = 0.25 + 0.75 * abs(__import__("math").sin(phase + i * 0.9)) * h / max(WAVE)
        bh = max(bw, rect.height() * h)
        y = rect.center().y() - bh / 2
        p.drawRoundedRect(QRectF(x, y, bw, bh), bw / 2, bw / 2)
        x += bw + gap
    p.restore()


class AssistantButton(QToolButton):
    """Araç çubuğundaki mavi daire (26 px)."""

    def __init__(self, parent=None, diameter=26):
        super().__init__(parent)
        self._d = diameter
        self.setFixedSize(diameter, diameter)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Chenkron Asistan — soru sor ya da iş ver")
        self._hover = False
        self._busy = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._tick)

    def set_busy(self, on):
        self._busy = bool(on)
        if self._busy:
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _tick(self):
        self._phase += 0.35
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        g = QRadialGradient(r.center().x(), r.top() + r.height() * 0.3, r.width())
        g.setColorAt(0.0, BLUE_HI if self._hover else QColor("#3F7BEA"))
        g.setColorAt(1.0, QColor("#2458C8"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(r)
        inner = r.adjusted(r.width() * 0.28, r.height() * 0.30, -r.width() * 0.28, -r.height() * 0.30)
        draw_waveform(p, inner, QColor("#FFFFFF"), self._phase, amp=1.0 if self._busy else None)
        p.end()


class _SendButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 38)
        self.setCursor(Qt.PointingHandCursor)
        self._busy = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._tick)
        self.setToolTip("Gönder (Enter)")

    def set_busy(self, on):
        self._busy = bool(on)
        (self._timer.start if self._busy else self._timer.stop)()
        self.setToolTip("Durdur" if self._busy else "Gönder (Enter)")
        self.update()

    def _tick(self):
        self._phase += 0.35
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.NoPen)
        p.setBrush(BLUE_HI if self.underMouse() else BLUE)
        p.drawEllipse(r)
        inner = r.adjusted(11, 12, -11, -12)
        draw_waveform(p, inner, QColor("#FFFFFF"), self._phase, amp=1.0 if self._busy else None)
        p.end()


class _MicLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setToolTip("Sesli giriş — yakında")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QColor("#E8E8EC")
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        w, h = self.width(), self.height()
        p.drawRoundedRect(QRectF(w / 2 - 4, 4, 8, 13), 4, 4)
        pen = QPen(c, 1.8)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(w / 2 - 7.5, 8, 15, 14), 200 * 16, 140 * 16)
        p.drawLine(QPointF(w / 2, 22), QPointF(w / 2, 25))
        p.drawLine(QPointF(w / 2 - 4, 25), QPointF(w / 2 + 4, 25))
        p.end()


class _Bubble(QWidget):
    """Hapın üstündeki cevap balonu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._lines = []      # (tür, metin): "soru" | "arac" | "cevap" | "hata"
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.RichText)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setFont(QFont(".AppleSystemUIFont", 13))
        self.label.setStyleSheet("color: #F2F2F2; background: transparent;")
        self.hide()

    def clear(self):
        self._lines = []
        self._render()

    def add(self, kind, text):
        self._lines.append((kind, text))
        self._render()

    def _render(self):
        html = []
        for kind, text in self._lines[-8:]:
            t = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br>")
            if kind == "soru":
                html.append(f"<div style='color:#A5A5AA; margin-bottom:6px;'>{t}</div>")
            elif kind == "arac":
                html.append(f"<div style='color:#8FB4FF;'>⚙︎ {t}</div>")
            elif kind == "hata":
                html.append(f"<div style='color:#FF8A80;'>{t}</div>")
            else:
                html.append(f"<div style='margin-top:6px;'>{t}</div>")
        self.label.setText("".join(html))
        self.setVisible(bool(self._lines))
        self._relayout()

    def _relayout(self):
        w = self.width()
        self.label.setFixedWidth(max(50, w - 36))
        h = self.label.sizeHint().height() + 28
        self.setFixedHeight(min(h, 320))
        self.label.setGeometry(18, 14, w - 36, min(h, 320) - 28)

    def resizeEvent(self, e):
        self._relayout()
        super().resizeEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(PILL_BORDER, 1))
        p.setBrush(QColor(38, 38, 41, 242))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 18, 18)
        p.end()


class AssistantOverlay(QWidget):
    """Pencerenin üstündeki katman: gölge + genie hunisi + hap + balon."""

    submitted = Signal(str)
    closed = Signal()
    cancel_requested = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)
        self._progress = 0.0
        self._origin = QPointF(0, 0)
        self._radius = 13.0
        self._opening = False
        self._busy = False
        self.hide()

        # ── hap içi ──
        self.content = QWidget(self)
        self.content.setAttribute(Qt.WA_TranslucentBackground)
        self._content_fx = QGraphicsOpacityEffect(self.content)
        self._content_fx.setOpacity(0.0)
        self.content.setGraphicsEffect(self._content_fx)
        lay = QHBoxLayout(self.content)
        lay.setContentsMargins(14, 0, 9, 0)
        lay.setSpacing(8)

        self.btn_plus = QToolButton(self.content)
        self.btn_plus.setText("＋")
        self.btn_plus.setFont(QFont(".AppleSystemUIFont", 18))
        self.btn_plus.setCursor(Qt.PointingHandCursor)
        self.btn_plus.setToolTip("Örnek komutlar")
        self.btn_plus.setStyleSheet("QToolButton { color: #F2F2F2; background: transparent; "
                                    "border: none; padding: 0 4px; }"
                                    "QToolButton:hover { color: #FFFFFF; }")
        self.btn_plus.clicked.connect(self._show_examples)
        lay.addWidget(self.btn_plus, 0)

        self.edit = QLineEdit(self.content)
        self.edit.setPlaceholderText("Chenkron'a sor")
        self.edit.setFont(QFont(".AppleSystemUIFont", 15))
        self.edit.setFrame(False)
        self.edit.setStyleSheet("QLineEdit { background: transparent; color: #F2F2F2; "
                                "border: none; selection-background-color: #2F6BE4; }")
        self.edit.returnPressed.connect(self._submit)
        lay.addWidget(self.edit, 1)

        self.lbl_model = QLabel("Flash Lite  ⌄", self.content)
        self.lbl_model.setFont(QFont(".AppleSystemUIFont", 13))
        self.lbl_model.setStyleSheet("color: #D0D0D4; background: transparent;")
        self.lbl_model.setToolTip("Model: gemini-3.1-flash-lite")
        lay.addWidget(self.lbl_model, 0)

        self.mic = _MicLabel(self.content)
        lay.addWidget(self.mic, 0)

        self.btn_send = _SendButton(self.content)
        self.btn_send.clicked.connect(self._send_or_stop)
        lay.addWidget(self.btn_send, 0)
        self.content.hide()

        self.bubble = _Bubble(self)

        self._anim = QPropertyAnimation(self, b"progress", self)
        self._anim.finished.connect(self._on_anim_done)
        self._fade = QPropertyAnimation(self._content_fx, b"opacity", self)
        self._fade.setDuration(160)

    # ── animasyon özelliği ──
    def _get_progress(self):
        return self._progress

    def _set_progress(self, v):
        self._progress = float(v)
        self.update()

    progress = Property(float, _get_progress, _set_progress)

    # ── geometri ──
    def pill_rect(self):
        w = min(PILL_MAX_W, self.width() - 48)
        x = (self.width() - w) // 2
        y = self.height() - PILL_BOTTOM - PILL_H
        return QRect(x, y, w, PILL_H)

    def _place_children(self):
        pr = self.pill_rect()
        self.content.setGeometry(pr)
        self.bubble.setFixedWidth(pr.width())
        self.bubble._relayout()
        self.bubble.move(pr.x(), pr.y() - 12 - self.bubble.height())

    def resizeEvent(self, e):
        self._place_children()
        super().resizeEvent(e)

    # ── açma / kapama ──
    def open_from(self, button):
        """Düğmenin merkezinden aşağı akan genie ile açılır."""
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        c = button.mapTo(self, button.rect().center()) if button is not None else None
        self._origin = QPointF(c) if c is not None else QPointF(self.width() / 2, 40)
        self._radius = (button.width() / 2.0) if button is not None else 13.0
        self._place_children()
        self.bubble.clear()
        self.content.hide()
        self._content_fx.setOpacity(0.0)
        self.show()
        self.raise_()
        self.setFocus()
        self._opening = True
        self._anim.stop()
        self._anim.setDuration(OPEN_MS)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def close_overlay(self):
        if not self.isVisible():
            return
        self._opening = False
        self.content.hide()
        self.bubble.hide()
        self._anim.stop()
        self._anim.setDuration(CLOSE_MS)
        self._anim.setEasingCurve(QEasingCurve.InCubic)
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _on_anim_done(self):
        if self._opening and self._progress >= 0.999:
            self._place_children()
            self.content.show()
            self._fade.stop()
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
            self._fade.start()
            self.edit.setFocus()
            if self.bubble._lines:
                self.bubble.show()
        elif not self._opening and self._progress <= 0.001:
            self.hide()
            self.closed.emit()

    # ── etkileşim ──
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close_overlay()
            return
        super().keyPressEvent(e)

    def mousePressEvent(self, e):
        pr = self.pill_rect()
        if not pr.contains(e.pos()) and not self.bubble.geometry().contains(e.pos()):
            self.close_overlay()
        super().mousePressEvent(e)

    def _submit(self):
        text = self.edit.text().strip()
        if not text or self._busy:
            return
        self.bubble.clear()
        self.bubble.add("soru", text)
        self.bubble.show()
        self._place_children()
        self.edit.clear()
        self.submitted.emit(text)

    def _send_or_stop(self):
        if self._busy:
            self.cancel_requested.emit()
        else:
            self._submit()

    def _show_examples(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background: #2A2A2D; color: #F2F2F2; border: 1px solid #3A3A3E; "
                           "border-radius: 8px; padding: 6px; } QMenu::item { padding: 6px 14px; "
                           "border-radius: 6px; } QMenu::item:selected { background: #2F6BE4; }")
        for ex in ("Ahmet Yılmaz hocasının pazartesini aç",
                   "Sultan Yılmaz'ın salı 3. saatini kapat",
                   "Otomatik planlamayı başlat",
                   "Çizelge durumu ne?",
                   "Zaman tablosunu nasıl açarım?",
                   "İki dersin aynı güne gelmemesini nasıl ayarlarım?"):
            a = menu.addAction(ex)
            a.triggered.connect(lambda _=False, t=ex: (self.edit.setText(t), self.edit.setFocus()))
        menu.exec(self.btn_plus.mapToGlobal(self.btn_plus.rect().topLeft()))

    # ── ajan geri bildirimi ──
    def set_busy(self, on):
        self._busy = bool(on)
        self.btn_send.set_busy(self._busy)
        self.edit.setPlaceholderText("Düşünüyor…" if self._busy else "Chenkron'a sor")

    def show_tool(self, name, args):
        pretty = {"set_teacher_day": "Gün ayarlanıyor", "set_teacher_period": "Saat ayarlanıyor",
                  "start_auto_schedule": "Otomatik planlama", "open_screen": "Ekran açılıyor",
                  "save_schedule": "Kaydediliyor", "undo": "Geri alınıyor", "redo": "Yineleniyor",
                  "list_teachers": "Öğretmenler okunuyor", "teacher_availability": "Zaman tablosu okunuyor",
                  "schedule_summary": "Çizelge özeti", "unlock_all_lessons": "Kilitler açılıyor"}.get(name, name)
        arg = ", ".join(f"{v}" for k, v in (args or {}).items() if isinstance(v, (str, int)))
        self.bubble.add("arac", f"{pretty}{' — ' + arg if arg else ''}")
        self._place_children()

    def show_tool_result(self, name, result):
        msg = (result or {}).get("message")
        if msg:
            self.bubble.add("arac" if result.get("ok") else "hata", msg)
            self._place_children()

    def show_answer(self, text):
        self.bubble.add("cevap", text)
        self._place_children()

    def show_error(self, text):
        self.bubble.add("hata", text)
        self._place_children()

    # ── çizim ──
    def paintEvent(self, e):
        t = max(0.0, min(1.0, self._progress))
        if t <= 0.0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        # 1) alttan solan gölge
        g = QLinearGradient(0, H * 0.45, 0, H)
        g.setColorAt(0.0, QColor(0, 0, 0, 0))
        g.setColorAt(1.0, QColor(0, 0, 0, int(150 * t)))
        p.fillRect(QRect(0, int(H * 0.45), W, H - int(H * 0.45)), g)
        p.fillRect(self.rect(), QColor(0, 0, 0, int(22 * t)))

        # 2) genie hunisi + hap
        pr = QRectF(self.pill_rect())
        ox, oy, r = self._origin.x(), self._origin.y(), self._radius
        # A: huni akar, hap büyür (0 → 0.62); B: boyun daireden kopup iner (0.62 → 1)
        a = min(1.0, t / 0.62)
        b = max(0.0, (t - 0.62) / 0.38)
        ea = 1 - (1 - a) ** 3
        pw = pr.width() * (0.12 + 0.88 * ea)
        ph = pr.height() * (0.35 + 0.65 * ea)
        pill = QRectF(pr.center().x() - pw / 2, pr.bottom() - ph, pw, ph)

        path = QPainterPath()
        if b < 1.0:
            # boyun: daire etrafından başlar; B aşamasında aşağı çekilir ve incelir
            neck_y = oy + (pill.top() - oy) * b
            neck_r = r * (1.0 - b) + 2.0 * b
            # huni geometrisi
            top_l = QPointF(ox - neck_r, neck_y)
            top_r = QPointF(ox + neck_r, neck_y)
            bot_l = QPointF(pill.left() + pill.height() / 2, pill.top())
            bot_r = QPointF(pill.right() - pill.height() / 2, pill.top())
            dy = max(1.0, pill.top() - neck_y)
            path.moveTo(bot_l)
            path.cubicTo(QPointF(bot_l.x(), bot_l.y() - dy * 0.55),
                         QPointF(top_l.x(), top_l.y() + dy * 0.45), top_l)
            # dairenin üst yayı
            path.arcTo(QRectF(ox - neck_r, neck_y - neck_r, 2 * neck_r, 2 * neck_r), 180, -180)
            path.cubicTo(QPointF(top_r.x(), top_r.y() + dy * 0.45),
                         QPointF(bot_r.x(), bot_r.y() - dy * 0.55), bot_r)
            path.closeSubpath()
            # Huni yarı saydam ve aşağı doğru koyulaşır: altındaki çizelge
            # seçilir, akış hapta toplanıyor hissi verir.
            fg = QLinearGradient(0, neck_y, 0, pill.top())
            fg.setColorAt(0.0, QColor(PILL_BG.red(), PILL_BG.green(), PILL_BG.blue(), int(120 * (1 - b * 0.7))))
            fg.setColorAt(1.0, QColor(PILL_BG.red(), PILL_BG.green(), PILL_BG.blue(), int(215 * (1 - b * 0.7))))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(fg))
            p.drawPath(path)

        # hap gölgesi (yumuşak), sonra hap
        rad = pill.height() / 2
        p.setPen(Qt.NoPen)
        for i in range(3, 0, -1):
            p.setBrush(QColor(0, 0, 0, int(16 * ea / i)))
            p.drawRoundedRect(pill.adjusted(-i * 2, i * 2, i * 2, i * 3), rad + i, rad + i)
        p.setPen(QPen(PILL_BORDER, 1))
        p.setBrush(QColor(PILL_BG.red(), PILL_BG.green(), PILL_BG.blue(), int(200 + 55 * ea)))
        p.drawRoundedRect(pill, rad, rad)
        p.end()
