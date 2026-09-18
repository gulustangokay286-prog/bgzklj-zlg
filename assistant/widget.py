"""Asistan arayüzü: daire düğme, genie animasyonu, hap giriş kutusu, cevap balonu.

Akış
----
Araç çubuğundaki küçük mavi daireye (parıltı ikonu) tıklanınca pencerenin
üstüne şeffaf bir katman (AssistantOverlay) gelir. Katman kendisi çizer:

  * Alttan yukarı SOLAN GÖLGE — ilerlemeyle koyulaşır.
  * GENIE — hap giriş kutusunun GÖRÜNTÜSÜ (arka plan + yazı + düğme) yatay
    dilimlere bölünür; her dilim daireden çıkan bir huni boyunca aşağı akar,
    dar boyundan geniş ağza doğru esneyerek altta hapın kendisine oturur.
    macOS küçültme efektinin tersi: bir gölge değil, kutunun kendisi bükülür.
    Boyun daireden kopup aşağı çekilince yalnızca hap kalır. Kapanış aynı
    yolun tersidir.
  * GÖKKUŞAĞI PARILTI — alt kenardan yukarı doğru solan mavi→mor→pembe→turuncu
    ışık (Gemini'deki gibi); açılışla belirir, model düşünürken hafifçe
    nefes alır.

Gölge ve parıltı boyuta göre bir kez piksel haritasına çizilir, her karede
yalnızca kopyalanır: animasyon boyunca kare başına iş küçük kalır, akış
takılmaz.

Hapın içi (＋, metin kutusu, ↑ gönder) gerçek widget'lardır; genie hap hâline
gelince solarak görünürler. Gönder düğmesi yazı yokken soluktur, yazınca
dolar, model düşünürken "durdur" olur. Cevap balonu hapın üstünde durur.
"""
import math

from PySide6.QtCore import (Qt, QRect, QRectF, QPointF, QPropertyAnimation, QEasingCurve,
                            Property, QTimer, Signal, QAbstractAnimation)
from PySide6.QtGui import (QPainter, QColor, QLinearGradient, QPainterPath, QPen, QBrush,
                           QFont, QRadialGradient, QPixmap, QPolygonF)
from PySide6.QtWidgets import (QWidget, QToolButton, QLineEdit, QLabel, QHBoxLayout,
                               QGraphicsOpacityEffect, QMenu)

BLUE = QColor("#2F6BE4")
BLUE_HI = QColor("#4A85F0")
PILL_BG = QColor(30, 30, 32)
PILL_BORDER = QColor(255, 255, 255, 22)

PILL_H = 56
PILL_MAX_W = 720
PILL_BOTTOM = 26
OPEN_MS = 600
CLOSE_MS = 380
SLICES_MIN = 28
SLICES_MAX = 112
GLOW_H = 170
GLOW_COLORS = ("#4285F4", "#8E6BD9", "#D96570", "#F2A93B", "#4285F4")


def draw_sparkle(p, center, size, color, rot=0.0):
    """Dört uçlu parıltı (AI işareti): içbükey kenarlı yıldız."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(center)
    p.rotate(rot)
    r, k = size / 2.0, size * 0.14
    path = QPainterPath(QPointF(0, -r))
    path.quadTo(QPointF(k, -k), QPointF(r, 0))
    path.quadTo(QPointF(k, k), QPointF(0, r))
    path.quadTo(QPointF(-k, k), QPointF(-r, 0))
    path.quadTo(QPointF(-k, -k), QPointF(0, -r))
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawPath(path)
    p.restore()


class AssistantButton(QToolButton):
    """Araç çubuğundaki mavi daire (26 px): büyük + küçük parıltı."""

    def __init__(self, parent=None, diameter=26):
        super().__init__(parent)
        self.setFixedSize(diameter, diameter)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Chenkron Asistan — soru sor ya da iş ver")
        self._hover = False
        self._busy = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

    def set_busy(self, on):
        self._busy = bool(on)
        (self._timer.start if self._busy else self._timer.stop)()
        self.update()

    def _tick(self):
        self._phase += 0.12
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
        # Düz renk: gölge yok, derinlik yok — araç çubuğundaki diğer haplar gibi.
        p.setPen(Qt.NoPen)
        p.setBrush(BLUE_HI if self._hover else BLUE)
        p.drawEllipse(r)
        c = r.center()
        big = r.width() * 0.56
        pulse = 1.0 + (0.08 * math.sin(self._phase * 4) if self._busy else 0.0)
        draw_sparkle(p, QPointF(c.x() - r.width() * 0.05, c.y() + r.height() * 0.05),
                     big * pulse, QColor("#FFFFFF"), rot=self._phase * 40 if self._busy else 0)
        draw_sparkle(p, QPointF(c.x() + r.width() * 0.24, c.y() - r.height() * 0.24),
                     big * 0.42, QColor(255, 255, 255, 230))
        p.end()


class _SendButton(QToolButton):
    """↑ gönder: yazı yokken soluk, yazınca dolu; meşgulken ■ durdur."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(34, 34)
        self.setCursor(Qt.PointingHandCursor)
        self._busy = False
        self._has_text = False
        self.setToolTip("Gönder (Enter)")
        self.setStyleSheet("background: transparent; border: none;")

    def set_busy(self, on):
        self._busy = bool(on)
        self.setToolTip("Durdur" if self._busy else "Gönder (Enter)")
        self.update()

    def set_has_text(self, on):
        self._has_text = bool(on)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.NoPen)
        if self._busy:
            p.setBrush(QColor("#F2F2F2"))
            p.drawEllipse(r)
            p.setBrush(QColor("#1E1E20"))
            p.drawRoundedRect(QRectF(r.center().x() - 5, r.center().y() - 5, 10, 10), 2, 2)
        else:
            alpha = 255 if self._has_text else 70
            p.setBrush(QColor(242, 242, 242, alpha))
            p.drawEllipse(r)
            pen = QPen(QColor(30, 30, 32, alpha), 2.2)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            cx, cy = r.center().x(), r.center().y()
            p.drawLine(QPointF(cx, cy + 6), QPointF(cx, cy - 6))
            p.drawPolyline(QPolygonF([QPointF(cx - 5, cy - 1), QPointF(cx, cy - 6), QPointF(cx + 5, cy - 1)]))
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

    @staticmethod
    def _md(text):
        """Modelin hafif Markdown'ını HTML'e çevirir: kalın, madde, satır."""
        import re as _re
        t = (text or "").replace("&", "&amp;").replace("<", "&lt;")
        t = _re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = _re.sub(r"`([^`]+)`", r"<span style='color:#C9D6FF'>\1</span>", t)
        lines = []
        for ln in t.split("\n"):
            m = _re.match(r"^\s*[\*\-•]\s+(.*)$", ln)
            if m:
                ln = "&nbsp;&nbsp;• " + m.group(1)
            lines.append(ln)
        return "<br>".join(lines)

    def _render(self):
        html = []
        for kind, text in self._lines[-10:]:
            t = self._md(text) if kind == "cevap" else \
                (text or "").replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br>")
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
        self.setFixedHeight(min(h, 340))
        self.label.setGeometry(18, 14, w - 36, min(h, 340) - 28)

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
    """Pencerenin üstündeki katman: gölge + genie + hap + balon."""

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
        self._pix_full = None           # hap + yazı + düğme (animasyon için)
        self._pix_bg = None             # yalnızca hap zemini (dururken)
        self._shadow_pix = None         # alt gölge (boyuta göre bir kez)
        self._glow_pix = None           # gökkuşağı parıltı (boyuta göre bir kez)
        self._glow_phase = 0.0
        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(50)
        self._glow_timer.timeout.connect(self._glow_tick)
        self.hide()

        # ── hap içi ──
        self.content = QWidget(self)
        self.content.setAttribute(Qt.WA_TranslucentBackground)
        self._content_fx = QGraphicsOpacityEffect(self.content)
        self._content_fx.setOpacity(0.0)
        self.content.setGraphicsEffect(self._content_fx)
        lay = QHBoxLayout(self.content)
        lay.setContentsMargins(14, 0, 11, 0)
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
        self.edit.textChanged.connect(lambda t: self.btn_send.set_has_text(bool(t.strip())))
        lay.addWidget(self.edit, 1)

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

    def _glow_tick(self):
        self._glow_phase += 0.06
        self.update(QRect(0, self.height() - GLOW_H, self.width(), GLOW_H))

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
        self._pix_full = self._pix_bg = None
        self._shadow_pix = self._glow_pix = None
        super().resizeEvent(e)

    # ── gölge ve parıltı (boyuta göre bir kez) ──
    def _build_layers(self):
        W, H = max(1, self.width()), max(1, self.height())
        dpr = float(self.devicePixelRatioF()) if hasattr(self, "devicePixelRatioF") else 1.0
        sh = QPixmap(int(W * dpr), int(H * dpr))
        sh.setDevicePixelRatio(dpr)
        sh.fill(Qt.transparent)
        p = QPainter(sh)
        p.fillRect(QRect(0, 0, W, H), QColor(0, 0, 0, 22))
        g = QLinearGradient(0, H * 0.45, 0, H)
        g.setColorAt(0.0, QColor(0, 0, 0, 0))
        g.setColorAt(1.0, QColor(0, 0, 0, 150))
        p.fillRect(QRect(0, int(H * 0.45), W, H - int(H * 0.45)), g)
        p.end()
        self._shadow_pix = sh

        # Parıltı: alt kenardan yükselen yumuşak ışık lekeleri. Her renk bir
        # elips gradyan (merkezde yoğun, kenara doğru sıfıra iner); lekeler
        # TOPLAMSAL karışır — ışık gibi üst üste biner, keskin kenar oluşmaz.
        # Genişlik iki kat ve düzen periyodik: faz ile kaydırınca akar.
        gw = W * 2
        gl = QPixmap(int(gw * dpr), int(GLOW_H * dpr))
        gl.setDevicePixelRatio(dpr)
        gl.fill(Qt.transparent)
        p = QPainter(gl)
        p.setRenderHint(QPainter.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode_Plus)
        p.setPen(Qt.NoPen)
        blobs = list(zip((0.08, 0.30, 0.52, 0.74, 0.96), GLOW_COLORS))
        rx, ry = W * 0.34, GLOW_H * 1.15
        for rep in (0, 1):
            for fx, col in blobs:
                cx, cy = (fx + rep) * W, GLOW_H + ry * 0.35     # merkez alt kenarın altında
                c = QColor(col)
                rg = QRadialGradient(0, 0, 1.0)
                rg.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), 150))
                rg.setColorAt(0.45, QColor(c.red(), c.green(), c.blue(), 70))
                rg.setColorAt(0.8, QColor(c.red(), c.green(), c.blue(), 18))
                rg.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
                p.save()
                p.translate(cx, cy)
                p.scale(rx, ry)
                p.setBrush(QBrush(rg))
                p.drawEllipse(QRectF(-1, -1, 2, 2))
                p.restore()
        p.end()
        self._glow_pix = gl

    # ── hap görüntüsü (genie için) ──
    def _render_pill(self, with_glyphs):
        pr = self.pill_rect()
        dpr = float(self.devicePixelRatioF()) if hasattr(self, "devicePixelRatioF") else 1.0
        pix = QPixmap(int(pr.width() * dpr), int(pr.height() * dpr))
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, pr.width(), pr.height()).adjusted(0.5, 0.5, -0.5, -0.5)
        rad = r.height() / 2
        p.setPen(QPen(PILL_BORDER, 1))
        p.setBrush(PILL_BG)
        p.drawRoundedRect(r, rad, rad)
        if with_glyphs:
            p.setPen(QColor("#F2F2F2"))
            p.setFont(QFont(".AppleSystemUIFont", 18))
            p.drawText(QRectF(14, 0, 30, r.height()), Qt.AlignCenter, "＋")
            p.setPen(QColor("#8E8E93"))
            p.setFont(QFont(".AppleSystemUIFont", 15))
            p.drawText(QRectF(56, 0, r.width() - 120, r.height()),
                       Qt.AlignVCenter | Qt.AlignLeft, "Chenkron'a sor")
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(242, 242, 242, 70))
            p.drawEllipse(QRectF(r.right() - 11 - 32, r.center().y() - 16, 32, 32))
        p.end()
        return pix

    # ── açma / kapama ──
    def open_from(self, button):
        """Düğmenin merkezinden aşağı akan genie ile açılır."""
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        if button is not None:
            # Düğme bu katmanın çocuğu değil; mapTo çalışmaz. Global üzerinden:
            # küçültülmüş pencerede de kaynak tam dairenin merkezidir.
            g = button.mapToGlobal(button.rect().center())
            self._origin = QPointF(self.mapFromGlobal(g))
            self._radius = button.width() / 2.0
        else:
            self._origin = QPointF(self.width() / 2, 40)
            self._radius = 13.0
        self._place_children()
        self._pix_full = self._render_pill(True)
        self._pix_bg = self._render_pill(False)
        self.bubble.clear()
        self.content.hide()
        self._content_fx.setOpacity(0.0)
        if self._shadow_pix is None:
            self._build_layers()
        self._glow_timer.start()
        self.show()
        self.raise_()
        self.setFocus()
        self._opening = True
        self._anim.stop()
        self._anim.setDuration(OPEN_MS)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
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
            self.update()
        elif not self._opening and self._progress <= 0.001:
            self._glow_timer.stop()
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
        for ex in ("Sultan Yılmaz hocasının pazartesini aç",
                   "Birey'de Mesut Çolak'ın hangi saatleri kapalı?",
                   "Otomatik planlamayı başlat",
                   "Çizelgeyi sıfırla",
                   "Açıkta kalan dersler hangileri?",
                   "Matematik1 ile Matematik2 aynı güne gelmesin kuralı ekle",
                   "12 A sınıfının programını göster",
                   "Son kontrol yap"):
            a = menu.addAction(ex)
            a.triggered.connect(lambda _=False, t=ex: (self.edit.setText(t), self.edit.setFocus()))
        menu.exec(self.btn_plus.mapToGlobal(self.btn_plus.rect().topLeft()))

    # ── ajan geri bildirimi ──
    def set_busy(self, on):
        self._busy = bool(on)
        self.btn_send.set_busy(self._busy)
        self.edit.setPlaceholderText("Düşünüyor…" if self._busy else "Chenkron'a sor")

    _PRETTY = {
        "set_teacher_day": "Öğretmen günü", "set_teacher_period": "Öğretmen saati",
        "set_class_day": "Sınıf günü", "set_class_period": "Sınıf saati",
        "start_auto_schedule": "Otomatik planlama", "open_screen": "Ekran",
        "save_schedule": "Kaydet", "undo": "Geri al", "redo": "Yinele",
        "list_teachers": "Öğretmenler", "teacher_availability": "Zaman tablosu",
        "schedule_summary": "Çizelge özeti", "unlock_all_lessons": "Kilitler",
        "clear_schedule": "Çizelgeyi sıfırla", "list_institutions": "Kurumlar",
        "institution_teacher_availability": "Diğer kurum", "add_rule": "Kural ekle",
        "remove_rule": "Kural sil", "set_rule_active": "Kural aç/kapat",
        "add_assignment": "Atama", "remove_assignment": "Atama sil",
        "move_lesson": "Ders taşı", "lock_lesson": "Kilit", "remove_lesson_from_grid": "Çizelgeden al",
        "precheck": "Ön kontrol", "verify_schedule": "Son kontrol",
        "unplaced_lessons": "Açıkta kalanlar", "free_slots": "Boş saatler",
        "teacher_schedule": "Öğretmen programı", "class_schedule": "Sınıf programı",
        "list_rules": "Kurallar", "list_assignments": "Atamalar", "list_classes": "Sınıflar",
        "list_subjects": "Dersler", "add_subject": "Ders ekle", "add_teacher": "Öğretmen ekle",
        "go_home": "Anasayfa", "print_preview": "Önizleme",
    }

    def show_tool(self, name, args):
        pretty = self._PRETTY.get(name, name)
        arg = ", ".join(f"{v}" for k, v in (args or {}).items()
                        if isinstance(v, (str, int)) and not isinstance(v, bool))
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
    def _funnel_geometry(self, t):
        """t anındaki huni: pürüzsüz yol (maske) ve y -> (sol, sağ) kenar tablosu."""
        pr = QRectF(self.pill_rect())
        ox, oy, r = self._origin.x(), self._origin.y(), self._radius
        a = min(1.0, t / 0.62)                  # akış / büyüme
        b = max(0.0, (t - 0.62) / 0.38)         # boyun kopar, iner, genişler
        ea = 1 - (1 - a) ** 3
        eb = b * b * (3 - 2 * b)
        pw = pr.width() * (0.10 + 0.90 * ea)
        ph = pr.height() * (0.45 + 0.55 * ea)
        x0, x1 = pr.center().x() - pw / 2, pr.center().x() + pw / 2
        bottom = pr.bottom()
        top = bottom - ph
        rad = ph / 2
        # üst kapak: boyunda daire (2r), sonda hapın üst kenarı (pw, köşe rad)
        cw = 2 * r + (pw - 2 * r) * eb
        cr = min(cw / 2, r + (rad - r) * eb)
        ncx = ox + (pr.center().x() - ox) * eb
        neck_top = (oy - r) + (top - (oy - r)) * eb
        NLx, NLy = ncx - cw / 2, neck_top + cr          # sol köşe yayının bittiği nokta
        NRx = ncx + cw / 2
        SLy = top + rad                                  # hap sol kenarının başladığı nokta
        dy = max(0.0, SLy - NLy)

        path = QPainterPath()
        path.moveTo(x0, SLy)
        path.cubicTo(QPointF(x0, SLy - dy * 0.5), QPointF(NLx, NLy + dy * 0.5), QPointF(NLx, NLy))
        path.arcTo(QRectF(NLx, neck_top, 2 * cr, 2 * cr), 180, -90)
        path.lineTo(NRx - cr, neck_top)
        path.arcTo(QRectF(NRx - 2 * cr, neck_top, 2 * cr, 2 * cr), 90, -90)
        path.cubicTo(QPointF(NRx, NLy + dy * 0.5), QPointF(x1, SLy - dy * 0.5), QPointF(x1, SLy))
        path.lineTo(x1, bottom - rad)
        path.arcTo(QRectF(x1 - 2 * rad, bottom - 2 * rad, 2 * rad, 2 * rad), 0, -90)
        path.lineTo(x0 + rad, bottom)
        path.arcTo(QRectF(x0, bottom - 2 * rad, 2 * rad, 2 * rad), 270, -90)
        path.closeSubpath()

        # kenar tablosu: y artan sırada (y, sol, sağ)
        lut = []
        steps = 24
        for i in range(steps + 1):
            yy = neck_top + cr * i / steps
            dxx = math.sqrt(max(0.0, cr * cr - (cr - (yy - neck_top)) ** 2))
            lut.append((yy, NLx + cr - dxx, NRx - cr + dxx))
        if dy > 0.5:
            for i in range(1, 61):
                u = i / 60.0
                mu = 1 - u
                bx = (mu ** 3) * NLx + 3 * mu * mu * u * NLx + 3 * mu * u * u * x0 + (u ** 3) * x0
                by = (mu ** 3) * NLy + 3 * mu * mu * u * (NLy + dy * 0.5) + 3 * mu * u * u * (SLy - dy * 0.5) + (u ** 3) * SLy
                bxr = (mu ** 3) * NRx + 3 * mu * mu * u * NRx + 3 * mu * u * u * x1 + (u ** 3) * x1
                lut.append((by, bx, bxr))
        lut.append((max(SLy, bottom - rad), x0, x1))
        for i in range(1, steps + 1):
            yy = bottom - rad + rad * i / steps
            dxx = math.sqrt(max(0.0, rad * rad - (yy - (bottom - rad)) ** 2))
            lut.append((yy, x0 + rad - dxx, x1 - rad + dxx))
        lut.sort(key=lambda e: e[0])
        return path, lut, neck_top, bottom

    @staticmethod
    def _edges_at(lut, y):
        lo, hi = 0, len(lut) - 1
        if y <= lut[0][0]:
            return lut[0][1], lut[0][2]
        if y >= lut[-1][0]:
            return lut[-1][1], lut[-1][2]
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if lut[mid][0] <= y:
                lo = mid
            else:
                hi = mid
        y0, l0, r0 = lut[lo]
        y1, l1, r1 = lut[hi]
        f = 0.0 if y1 <= y0 else (y - y0) / (y1 - y0)
        return l0 + (l1 - l0) * f, r0 + (r1 - r0) * f

    def _draw_genie(self, p, t, pix, alpha=1.0):
        """Hap görüntüsünü huni boyunca dilim dilim büker; kenarı pürüzsüz yolla maskeler."""
        path, lut, y_top, y_bottom = self._funnel_geometry(t)
        span = max(1.0, y_bottom - y_top)
        bounds = path.boundingRect().adjusted(-2, -2, 2, 2)
        dpr = pix.devicePixelRatio()
        buf = QPixmap(int(bounds.width() * dpr) + 1, int(bounds.height() * dpr) + 1)
        buf.setDevicePixelRatio(dpr)
        buf.fill(Qt.transparent)
        q = QPainter(buf)
        q.setRenderHint(QPainter.SmoothPixmapTransform)
        q.translate(-bounds.left(), -bounds.top())
        sw = pix.width() / dpr
        n = int(max(SLICES_MIN, min(SLICES_MAX, pix.height(), span / 2.0)))
        sh = pix.height() / dpr / n
        for j in range(n):
            y0 = y_top + span * j / n
            y1 = y_top + span * (j + 1) / n
            # Dilim, kendi yüksekliği boyunca yolu TAMAMEN kaplamalı; kenarı
            # maske belirler. Aksi hâlde eğimli yerde dilim yolun içinde kalır
            # ve basamak görünür.
            l0, r0 = self._edges_at(lut, y0)
            l1, r1 = self._edges_at(lut, y1)
            lm, rm = self._edges_at(lut, (y0 + y1) / 2)
            xl, xr = min(l0, l1, lm), max(r0, r1, rm)
            src = QRectF(0, j * sh * dpr, sw * dpr, sh * dpr)
            dst = QRectF(xl - 1.0, y0, (xr - xl) + 2.0, (y1 - y0) + 0.8)
            q.drawPixmap(dst, pix, src)
        # maske: yolun DIŞI silinir (DestinationOut), kenar antialias.
        q.setRenderHint(QPainter.Antialiasing)
        q.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        q.setPen(Qt.NoPen)
        q.setBrush(QColor(0, 0, 0, 255))
        outer = QPainterPath()
        outer.addRect(bounds.adjusted(-4, -4, 4, 4))
        q.drawPath(outer.subtracted(path))
        q.end()
        p.setOpacity(alpha)
        p.drawPixmap(bounds.topLeft(), buf)
        p.setOpacity(1.0)

    def paintEvent(self, e):
        t = max(0.0, min(1.0, self._progress))
        if t <= 0.0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        W, H = self.width(), self.height()
        if self._shadow_pix is None:
            self._build_layers()

        # 1) alttan solan gölge (önbellekten, ilerlemeyle saydamlık)
        p.setOpacity(t)
        p.drawPixmap(0, 0, self._shadow_pix)
        # 2) gökkuşağı parıltı: alt kenardan yukarı; faz ile yatay kayma
        glow_w = self._glow_pix.width() / self._glow_pix.devicePixelRatio()
        shift = (math.sin(self._glow_phase) * 0.5 + 0.5) * (glow_w / 2)
        breathe = 0.85 + (0.15 * math.sin(self._glow_phase * 2.2) if self._busy else 0.0)
        p.setOpacity(t * breathe)
        p.drawPixmap(QRectF(0, H - GLOW_H, W, GLOW_H), self._glow_pix,
                     QRectF(shift * self._glow_pix.devicePixelRatio(), 0,
                            W * self._glow_pix.devicePixelRatio(), GLOW_H * self._glow_pix.devicePixelRatio()))
        p.setOpacity(1.0)

        if self._pix_full is None:
            self._pix_full = self._render_pill(True)
            self._pix_bg = self._render_pill(False)

        pr = QRectF(self.pill_rect())
        rad = pr.height() / 2
        if t >= 0.999 and self._anim.state() != QAbstractAnimation.Running:
            # dururken: yumuşak gölge + zemin; içerik widget'ları üstte
            p.setPen(Qt.NoPen)
            for i in range(3, 0, -1):
                p.setBrush(QColor(0, 0, 0, int(16 / i)))
                p.drawRoundedRect(pr.adjusted(-i * 2, i * 2, i * 2, i * 3), rad + i, rad + i)
            p.drawPixmap(pr.topLeft(), self._pix_bg)
            p.end()
            return

        # 3) genie
        self._draw_genie(p, t, self._pix_full, alpha=1.0)
        p.end()
