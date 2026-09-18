"""Asistan arayüzü: daire düğme, genie animasyonu, hap giriş kutusu, cevap balonu.

Akış
----
Araç çubuğundaki mavi daireye tıklanınca pencerenin üstüne şeffaf bir katman
(AssistantOverlay) gelir ve üç şey çizilir:

  * ALT GÖLGE — alttan yukarı solan karartma; boyuta göre bir kez piksel
    haritasına çizilir, her karede yalnızca kopyalanır.
  * GENIE — TEK bir pürüzsüz QPainterPath: düğmedeki boyundan aşağı açılan,
    altta hapa oturan gövde. Dilim/piksel bükme YOK, bu yüzden kenarlar
    tırtıklanmaz. Yol t=1'de tam olarak hapın yuvarlatılmış dikdörtgenidir;
    animasyon bittiğinde çizilen şey değişmez, yalnızca yazı ve düğme solarak
    belirir — "oturdu, sonra bir daha oturdu" görüntüsü bu yüzden yoktur.
  * PARILTI — alt kenardan yükselen yumuşak ışık lekeleri (toplamsal karışım;
    yukarı ve yanlara doğru sıfıra iner). Şerit değil, ışık.

Hapın içi (＋, metin kutusu, ↑ gönder) gerçek widget'lardır. Gönder düğmesi
yazı yokken soluktur, yazınca dolar, model düşünürken "durdur" olur.
"""
import math

from PySide6.QtCore import (Qt, QRect, QRectF, QPointF, QPropertyAnimation, QEasingCurve,
                            Property, QTimer, Signal)
from PySide6.QtGui import (QPainter, QColor, QLinearGradient, QPainterPath, QPen, QBrush,
                           QFont, QPixmap, QPolygonF, QRadialGradient)
from PySide6.QtWidgets import (QWidget, QToolButton, QLineEdit, QLabel, QHBoxLayout,
                               QGraphicsOpacityEffect, QMenu)

BLUE = QColor("#2F6BE4")
BLUE_HI = QColor("#4A85F0")
PILL_BG = QColor(30, 30, 32)
PILL_TOP = QColor(40, 40, 44)
PILL_BORDER = QColor(255, 255, 255, 24)

PILL_H = 56
PILL_MAX_W = 720
PILL_BOTTOM = 26
OPEN_MS = 520
CLOSE_MS = 340
SETTLED = 0.90             # bu ilerlemeden sonra şekil HİÇ değişmez
GLOW_H = 280
GLOW_COLORS = ("#4285F4", "#9B72CB", "#D96570", "#F2A93B")
CONTENT_MS = 180           # içerik solma süresi (şekil oturduktan SONRA)


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
    """Araç çubuğundaki düz mavi daire (26 px): büyük + küçük parıltı."""

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
        # Düz renk: gölge yok, derinlik yok — araç çubuğundaki haplarla aynı dil.
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
            p.drawPolyline(QPolygonF([QPointF(cx - 5, cy - 1), QPointF(cx, cy - 6),
                                      QPointF(cx + 5, cy - 1)]))
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
        out = []
        for ln in t.split("\n"):
            m = _re.match(r"^\s*[\*\-•]\s+(.*)$", ln)
            out.append("&nbsp;&nbsp;• " + m.group(1) if m else ln)
        return "<br>".join(out)

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
        h = min(self.label.sizeHint().height() + 28, 340)
        self.setFixedHeight(h)
        self.label.setGeometry(18, 14, w - 36, h - 28)

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
    """Pencerenin üstündeki katman: gölge + parıltı + genie + hap + balon."""

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
        self._layer_size = None
        self._shadow_pix = None
        self._glow_pix = None
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
        self._fade.setDuration(CONTENT_MS)
        # Solma sırasında hapın zemini de her adımda yeniden çizilir; yoksa
        # yarı saydam içerik ile altındaki gövde arasında iz kalıyor.
        self._fade.valueChanged.connect(lambda _v: self.update(self.pill_rect().adjusted(-8, -8, 8, 8)))

    # ── animasyon özelliği ──
    def _get_progress(self):
        return self._progress

    def _set_progress(self, v):
        self._progress = float(v)
        self.update()

    progress = Property(float, _get_progress, _set_progress)

    def _glow_tick(self):
        self._glow_phase += 0.05
        self.update(QRect(0, self.height() - GLOW_H, self.width(), GLOW_H))

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
        # Aynı boyut için katmanlar yeniden kurulmaz: pencere gösterilirken
        # gelen tekrarlı resize olayları animasyonu sıçratıyordu.
        size = (self.width(), self.height())
        if size != self._layer_size:
            self._layer_size = size
            self._shadow_pix = self._glow_pix = None
        self._place_children()
        super().resizeEvent(e)

    # ── gölge ve parıltı (boyuta göre bir kez) ──
    def _build_layers(self):
        W, H = max(1, self.width()), max(1, self.height())
        dpr = float(self.devicePixelRatioF()) if hasattr(self, "devicePixelRatioF") else 1.0

        sh = QPixmap(int(W * dpr), int(H * dpr))
        sh.setDevicePixelRatio(dpr)
        sh.fill(Qt.transparent)
        p = QPainter(sh)
        p.fillRect(QRect(0, 0, W, H), QColor(0, 0, 0, 20))
        # Karartma parıltının BAŞLADIĞI yerde durur; aşağısı ışığın alanı.
        g = QLinearGradient(0, H * 0.40, 0, H - GLOW_H * 0.55)
        g.setColorAt(0.0, QColor(0, 0, 0, 0))
        g.setColorAt(1.0, QColor(0, 0, 0, 105))
        p.fillRect(QRect(0, int(H * 0.40), W, H - int(H * 0.40)), g)
        p.end()
        self._shadow_pix = sh

        # Parıltı: alt kenarın ALTINDA duran geniş, yumuşak ışık lekeleri.
        # Toplamsal karışır (Plus) — ışık gibi üst üste biner, keskin kenarı
        # olmaz. Sonda yatay ve düşey maske: yanlara ve yukarı doğru sıfıra
        # iner, böylece şerit değil yayılan bir ışık olur.
        gw = int(W * 1.6)
        gl = QPixmap(int(gw * dpr), int(GLOW_H * dpr))
        gl.setDevicePixelRatio(dpr)
        gl.fill(Qt.transparent)
        p = QPainter(gl)
        p.setRenderHint(QPainter.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode_Plus)
        p.setPen(Qt.NoPen)
        # Lekelerin merkezi görünen alanın ALT KENARINA yakın durur: daha
        # aşağıda olursa ekranda yalnızca zayıf kuyruğu kalıyor ve ışık
        # soluk bir gri gibi görünüyordu.
        rx, ry = gw * 0.26, GLOW_H * 0.95
        for i, col in enumerate(GLOW_COLORS):
            c = QColor(col)
            cx = gw * (0.16 + 0.23 * i)
            cy = GLOW_H * 1.02
            rg = QRadialGradient(0, 0, 1.0)
            rg.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), 235))
            rg.setColorAt(0.38, QColor(c.red(), c.green(), c.blue(), 130))
            rg.setColorAt(0.72, QColor(c.red(), c.green(), c.blue(), 40))
            rg.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
            p.save()
            p.translate(cx, cy)
            p.scale(rx, ry)
            p.setBrush(QBrush(rg))
            p.drawEllipse(QRectF(-1, -1, 2, 2))
            p.restore()
        p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        hm = QLinearGradient(0, 0, gw, 0)
        hm.setColorAt(0.00, QColor(0, 0, 0, 0))
        hm.setColorAt(0.18, QColor(0, 0, 0, 255))
        hm.setColorAt(0.82, QColor(0, 0, 0, 255))
        hm.setColorAt(1.00, QColor(0, 0, 0, 0))
        p.fillRect(QRect(0, 0, gw, GLOW_H), hm)
        vm = QLinearGradient(0, 0, 0, GLOW_H)
        vm.setColorAt(0.00, QColor(0, 0, 0, 0))
        vm.setColorAt(0.40, QColor(0, 0, 0, 90))
        vm.setColorAt(0.78, QColor(0, 0, 0, 215))
        vm.setColorAt(1.00, QColor(0, 0, 0, 255))
        p.fillRect(QRect(0, 0, gw, GLOW_H), vm)
        p.end()
        self._glow_pix = gl

    # ── şekil ──
    def _genie_path(self, t):
        """t anındaki şekil: TEK pürüzsüz QPainterPath.

        Dilim ve piksel bükme yok — Qt tek bir yolu antialias çizdiği için
        kenar tırtıklanmaz. Şekil, düğmedeki boyundan aşağı açılan ve altta
        hapa oturan gövdedir; t=1'de TAM OLARAK hapın yuvarlatılmış
        dikdörtgenidir, dolayısıyla bitişte hiçbir sıçrama olmaz.
        """
        pr = QRectF(self.pill_rect())
        ox, oy, r = self._origin.x(), self._origin.y(), self._radius
        # Zamanlama genie'nin okunmasını belirler: gövde ÖNCE dar kalır
        # (huni ince bir akış gibi görünür), boyun sonra düğmeden kopup
        # inerken gövde asıl genişlemesini yapar, boynun genişlemesi en sona
        # kalır. Tersi olursa şekil huni değil, ekranı kaplayan kütle olur.
        #
        # ÜÇÜ DE t = SETTLED'DE BİTER. Son dilim tamamen sabittir: eskiden
        # boyun kapağı son %20'de hâlâ genişliyordu ve hap oturmuş görünürken
        # üst kenarı boyunca gecikmeli bir hareket kalıyordu.
        # SIRA ÖNEMLİ: boynun GENİŞLEMESİ inişten ÖNCE biter. Tersi olduğunda
        # hap oturmuş görünürken üst kenarın iki ucunda tümsekler kalıyor ve
        # son anda içeri çekiliyordu — "silindirin üst yarısı hizasında
        # gecikmeli gelen şey" buydu.
        a = min(1.0, t / (SETTLED * 0.80))                      # gövde genişler
        bw = max(0.0, (t - SETTLED * 0.40) / (SETTLED * 0.46))  # boyun genişler
        b = max(0.0, (t - SETTLED * 0.30) / (SETTLED * 0.70))   # boyun iner (en son)
        a, b, bw = min(1.0, a), min(1.0, b), min(1.0, bw)
        ea = a * a * (3 - 2 * a)
        eb = b * b * (3 - 2 * b)
        ebw = bw * bw * (3 - 2 * bw)

        pw = pr.width() * (0.09 + 0.91 * ea)
        ph = pr.height() * (0.62 + 0.38 * ea)
        cx_p = pr.center().x()
        x0, x1 = cx_p - pw / 2, cx_p + pw / 2
        bottom = pr.bottom()
        top = bottom - ph
        rad = ph / 2

        cw = 2 * r + (pw - 2 * r) * ebw            # boyun genişliği (en sonda)
        cr = min(cw / 2, r + (rad - r) * ebw)
        ncx = ox + (cx_p - ox) * eb
        ntop = (oy - r) + (top - (oy - r)) * eb
        nl, nr = ncx - cw / 2, ncx + cw / 2
        y_neck = ntop + cr
        y_side = top + rad
        dy = max(0.0, y_side - y_neck)

        path = QPainterPath()
        path.moveTo(x0, y_side)
        path.cubicTo(QPointF(x0, y_side - dy * 0.62),
                     QPointF(nl, y_neck + dy * 0.38), QPointF(nl, y_neck))
        path.arcTo(QRectF(nl, ntop, 2 * cr, 2 * cr), 180, -90)
        if nr - cr > nl + cr:
            path.lineTo(nr - cr, ntop)
        path.arcTo(QRectF(nr - 2 * cr, ntop, 2 * cr, 2 * cr), 90, -90)
        path.cubicTo(QPointF(nr, y_neck + dy * 0.38),
                     QPointF(x1, y_side - dy * 0.62), QPointF(x1, y_side))
        path.lineTo(x1, bottom - rad)
        path.arcTo(QRectF(x1 - 2 * rad, bottom - 2 * rad, 2 * rad, 2 * rad), 0, -90)
        path.lineTo(x0 + rad, bottom)
        path.arcTo(QRectF(x0, bottom - 2 * rad, 2 * rad, 2 * rad), 270, -90)
        path.closeSubpath()
        return path, QRectF(x0, top, pw, ph)

    # ── açma / kapama ──
    def open_from(self, button):
        if self.isVisible() and self._opening:
            return                                  # zaten açık ya da açılıyor
        parent = self.parentWidget()
        if parent is not None and self.geometry() != parent.rect():
            self.setGeometry(parent.rect())
        if button is not None:
            # Düğme bu katmanın çocuğu değil; global koordinat üzerinden
            # eşlenir — küçültülmüş pencerede de kaynak tam dairenin merkezi.
            g = button.mapToGlobal(button.rect().center())
            self._origin = QPointF(self.mapFromGlobal(g))
            self._radius = button.width() / 2.0
        else:
            self._origin = QPointF(self.width() / 2, 40)
            self._radius = 13.0
        self._place_children()
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
        if not self.isVisible() or not self._opening:
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

    def _show_content(self):
        """Yazı ve düğmeler yalnızca ŞEKİL TAM HAP OLDUĞUNDA gelir.

        Daha erken gösterilince içerik hapın son genişliğine göre yerleşiyor,
        ama arkasındaki gövde hâlâ büyümekte oluyordu: yazı ve düğme kutunun
        dışına taşıyor, sonra kutu yetişiyordu — "yarısından warping" denen
        bozulma buydu.
        """
        self._place_children()
        self.content.show()
        self._fade.stop()
        self._fade.setStartValue(self._content_fx.opacity())
        self._fade.setEndValue(1.0)
        self._fade.start()
        self.edit.setFocus()
        if self.bubble._lines:
            self.bubble.show()

    def _on_anim_done(self):
        if self._opening:
            if not self.content.isVisible():
                self._show_content()
        elif self._progress <= 0.001:
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
        if not self.pill_rect().contains(e.pos()) and not self.bubble.geometry().contains(e.pos()):
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
        "move_lesson": "Ders taşı", "lock_lesson": "Kilit",
        "remove_lesson_from_grid": "Çizelgeden al", "precheck": "Ön kontrol",
        "verify_schedule": "Son kontrol", "unplaced_lessons": "Açıkta kalanlar",
        "free_slots": "Boş saatler", "teacher_schedule": "Öğretmen programı",
        "class_schedule": "Sınıf programı", "list_rules": "Kurallar",
        "list_assignments": "Atamalar", "list_classes": "Sınıflar",
        "list_subjects": "Dersler", "add_subject": "Ders ekle",
        "add_teacher": "Öğretmen ekle", "go_home": "Anasayfa",
        "print_preview": "Önizleme",
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

        # Gölge ve ışığın saydamlığı da SETTLED'de biter: şekil donduğu hâlde
        # arka plan koyulaşmaya devam ederse "son anda bir şey daha geliyor"
        # gibi görünüyordu.
        ft = min(1.0, t / SETTLED)

        # 1) alt gölge
        p.setOpacity(ft)
        p.drawPixmap(0, 0, self._shadow_pix)

        # 2) parıltı: faz ile yavaşça kayar, model düşünürken nefes alır
        gp = self._glow_pix
        dpr = gp.devicePixelRatio()
        gw = gp.width() / dpr
        shift = (math.sin(self._glow_phase) * 0.5 + 0.5) * max(0.0, gw - W)
        breathe = 0.9 + (0.1 * math.sin(self._glow_phase * 2.0) if self._busy else 0.0)
        # TOPLAMSAL: altındaki karartmayı aydınlatır — boyanmış bir şerit
        # değil, pozlama gibi bir ışık olur.
        p.setCompositionMode(QPainter.CompositionMode_Plus)
        p.setOpacity(ft * breathe)
        p.drawPixmap(QRectF(0, H - GLOW_H, W, GLOW_H), gp,
                     QRectF(shift * dpr, 0, W * dpr, GLOW_H * dpr))
        p.setOpacity(1.0)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)

        # 3) gövde: tek pürüzsüz yol (t=1'de hapın kendisi)
        path, body = self._genie_path(t)
        p.setPen(Qt.NoPen)
        for i in range(3, 0, -1):
            p.setBrush(QColor(0, 0, 0, int(14 * ft / i)))
            p.translate(0, i * 1.5)
            p.drawPath(path)
            p.translate(0, -i * 1.5)
        g = QLinearGradient(0, body.top(), 0, body.bottom())
        g.setColorAt(0.0, PILL_TOP)
        g.setColorAt(1.0, PILL_BG)
        p.setBrush(QBrush(g))
        p.setPen(QPen(PILL_BORDER, 1))
        p.drawPath(path)
        p.end()
