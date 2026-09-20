"""
auto_schedule_dialog.py — Otomatik Yerleştirme (Apple Minimalist & BGZ Yapay Zeka Motoru)
"""
import math

import bk_ui
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QWidget, QFrame, QScrollArea, QGraphicsDropShadowEffect,
    QMessageBox
)
from PySide6.QtCore import (Qt, QTimer, QRectF, QPoint, QPointF, QByteArray,
                            QPropertyAnimation, QEasingCurve, Property, Signal)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen, QLinearGradient,
    QRadialGradient, QPainterPath, QPixmap
)
from PySide6.QtSvg import QSvgRenderer


# ═══════════════════════════════════════════════════════════════════════
# 1. PURE 3D ISOMETRIC VECTOR ENGINE ICON (No background box/square)
# ═══════════════════════════════════════════════════════════════════════
ICON_SVG = b'''
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="plateTop" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#60A5FA"/>
      <stop offset="50%" stop-color="#3B82F6"/>
      <stop offset="100%" stop-color="#1D4ED8"/>
    </linearGradient>
    <linearGradient id="plateLeft" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1D4ED8"/>
      <stop offset="100%" stop-color="#1E3A8A"/>
    </linearGradient>
    <linearGradient id="plateRight" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#2563EB"/>
      <stop offset="100%" stop-color="#1D4ED8"/>
    </linearGradient>
    <linearGradient id="boltGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FDE047"/>
      <stop offset="100%" stop-color="#EA580C"/>
    </linearGradient>
  </defs>
  
  <!-- Soft ground shadow -->
  <ellipse cx="32" cy="54" rx="20" ry="4" fill="#000000" fill-opacity="0.18"/>
  
  <!-- Isometric Schedule Cube -->
  <polygon points="32,8 54,20 32,32 10,20" fill="url(#plateTop)"/>
  <polygon points="10,20 32,32 32,48 10,36" fill="url(#plateLeft)"/>
  <polygon points="54,20 32,32 32,48 54,36" fill="url(#plateRight)"/>
  
  <!-- Isometric Grid Lines -->
  <line x1="21" y1="14" x2="43" y2="26" stroke="#FFFFFF" stroke-width="1.2" stroke-opacity="0.55"/>
  <line x1="43" y1="14" x2="21" y2="26" stroke="#FFFFFF" stroke-width="1.2" stroke-opacity="0.55"/>
  
  <!-- Edge Highlights -->
  <line x1="32" y1="8" x2="10" y2="20" stroke="#FFFFFF" stroke-width="1" stroke-opacity="0.6"/>
  <line x1="32" y1="8" x2="54" y2="20" stroke="#FFFFFF" stroke-width="1" stroke-opacity="0.6"/>
  <line x1="32" y1="32" x2="32" y2="48" stroke="#60A5FA" stroke-width="1" stroke-opacity="0.7"/>
  
  <!-- Center 3D Lightning Energy Core -->
  <polygon points="34,14 24,28 31,28 28,42 40,26 33,26" fill="url(#boltGrad)"/>
</svg>
'''

class PlannerArtWidget(QWidget):
    """Planlayıcının 3B resmi; motor çalışırken altında nefes alan bir ışık.

    Başlık resmi QLabel'a çevrilince start_pulse/stop_pulse kayboldu ve
    "Planlamayı Başlat" AttributeError ile düşüyordu — planlama daha
    başlamadan. Resim yine pixmap ama artık kendi widget'ı: aynı iki
    metot burada, ışık da tablanın ALTINDAN geliyor, ikonu yıkamıyor.
    """

    def __init__(self, size=84, parent=None):
        super().__init__(parent)
        self._pix = bk_ui.autoplan_3d(size)
        self._size = size
        # Resmin TAMAMI sığmalı: yükseklik kısıldığında tablanın alt
        # kenarı kesiliyor ve bina duvara gömülmüş gibi duruyordu.
        self.setFixedHeight(size + 18)
        self.setMinimumWidth(size + 24)
        self._phase = 0.0
        self._active = False
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

    def start_pulse(self):
        self._active = True
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def stop_pulse(self):
        self._active = False
        self._timer.stop()
        self.update()

    def _tick(self):
        self._phase += 0.09
        if self._phase > 2 * math.pi:
            self._phase -= 2 * math.pi
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        px = self._pix
        pw = px.width() / px.devicePixelRatio()
        ph = px.height() / px.devicePixelRatio()
        x, y = (w - pw) / 2.0, (h - ph) / 2.0

        # Işık KALDIRILDI. Resmin arkasında nefes alan halka, başlıkta
        # bulanık bir leke olarak duruyordu: ne "çalışıyor" diyordu ne de
        # resme bir şey katıyordu — çalıştığını zaten altındaki sahne ve
        # akan çubuk söylüyor. start_pulse/stop_pulse duruyor çünkü
        # çağrılıyorlar; artık yalnızca durumu tutuyorlar.
        p.drawPixmap(QPointF(x, y), px)
        p.end()


class _RunScene(QWidget):
    """Çalışırken izlenen sahne: tablaya sırayla düşen kartlar.

    Beklemenin kendisi kısalmıyor ama boş bir çubuğa bakmakla dolmakta
    olan bir çizelgeye bakmak aynı şey değil. Sahne döngüsel: sekiz kart
    yerine oturuyor, sonra sayfa tazeleniyor ve yeniden başlıyor.
    """

    SLOTS = [(30, 62), (50, 70), (70, 62), (40, 54),
             (60, 54), (50, 46), (34, 48), (66, 48)]

    def __init__(self, parent=None):
        super().__init__(parent)
        # 100 birimlik çizimin en alt noktası tablanın kalınlığıyla
        # birlikte 104'e iniyor; yükseklik ona göre veriliyor, yoksa
        # tablanın ön yüzü kırpılıyor.
        self.setFixedHeight(108)
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

    def start(self):
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        self._timer.stop()
        self.update()

    def _tick(self):
        self._t += 0.04
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        u = h / 108.0
        ox = w / 2.0 - 50 * u

        def pt(x, y):
            return QPointF(ox + x * u, y * u)

        def iso(cx, cy, hw, hd):
            return [pt(cx - hw, cy), pt(cx, cy - hd), pt(cx + hw, cy), pt(cx, cy + hd)]

        def poly(points, colour, outline=True):
            path = QPainterPath(points[0])
            for q in points[1:]:
                path.lineTo(q)
            path.closeSubpath()
            p.setBrush(QBrush(colour))
            p.setPen(QPen(QColor(18, 26, 43, 50), max(0.7, u * 0.5)) if outline else Qt.NoPen)
            p.drawPath(path)

        # Tabla
        L, B, R, F = iso(50, 78, 42, 21)
        th = 5 * u
        poly([L, F, QPointF(F.x(), F.y() + th), QPointF(L.x(), L.y() + th)], QColor("#C9D2E0"))
        poly([F, R, QPointF(R.x(), R.y() + th), QPointF(F.x(), F.y() + th)], QColor("#B7C2D4"))
        poly([L, B, R, F], QColor("#E8EDF5"))
        p.setPen(QPen(QColor(120, 135, 160, 95), max(0.6, u * 0.35)))
        for i in range(1, 4):
            t = i / 4.0
            p.drawLine(QPointF(L.x() + (B.x() - L.x()) * t, L.y() + (B.y() - L.y()) * t),
                       QPointF(F.x() + (R.x() - F.x()) * t, F.y() + (R.y() - F.y()) * t))
            p.drawLine(QPointF(L.x() + (F.x() - L.x()) * t, L.y() + (F.y() - L.y()) * t),
                       QPointF(B.x() + (R.x() - B.x()) * t, B.y() + (R.y() - B.y()) * t))

        colours = ["#3E6FD4", "#4DA37A", "#E8A33D", "#C9556B",
                   "#7C5AC8", "#2F9EB5", "#D2793C", "#5E9E45"]
        CYCLE, STEP = 0.55, 0.55
        cycle_len = len(self.SLOTS) * STEP + 1.1
        phase = self._t % cycle_len

        for i, (cx, cy) in enumerate(self.SLOTS):
            appear = i * STEP
            k = (phase - appear) / CYCLE
            if k <= 0:
                continue
            drop = max(0.0, 1.0 - min(1.0, k))
            # Yerine otururken yukarıdan iniyor ve son anda hızlanıyor.
            dy = -26 * (drop ** 2)
            alpha = int(255 * min(1.0, k * 2.2))
            base = QColor(colours[i % len(colours)])
            base.setAlpha(alpha)
            side = base.darker(118); side.setAlpha(alpha)
            front = base.darker(134); front.setAlpha(alpha)
            l, b, r, f = iso(cx, cy + dy, 9.5, 4.8)
            cth = 3.0 * u
            poly([l, f, QPointF(f.x(), f.y() + cth), QPointF(l.x(), l.y() + cth)], side, False)
            poly([f, r, QPointF(r.x(), r.y() + cth), QPointF(f.x(), f.y() + cth)], front, False)
            poly([l, b, r, f], base, False)
        p.end()


class PlannerRunPanel(QFrame):
    """Motor çalışırken görünen ekran.

    Bekleme üç şeyle yönetiliyor:

    1) SAHNE — tablaya kartlar düşüyor. Çubuğa bakmakla dolan bir
       çizelgeye bakmak aynı şey değil.
    2) AKIŞ — ilerleme, gerçek yüzdeyi BEKLEMEDEN kıpırdıyor. Motorun ilk
       haberi saniyeler sonra geliyor; o zamana kadar duran bir çubuk
       "takıldı" demektir. Gösterilen değer bir eğriyle kendi ilerliyor,
       gerçek haber geldiğinde ikisinin büyüğü alınıyor. Yani hızlandıran
       bir şey yok, yalnızca BAŞLADIĞI görünüyor — ve bu doğru: motor
       gerçekten çalışıyor.
    3) SÜRE — "yaklaşık 40 saniye" diyor ve geri sayıyor. Bilinmeyen bir
       bekleme, bilinen bir beklemeden uzun hissettirir.
    """

    STAGES = [
        (0.00, "Veriler okunuyor"),
        (0.08, "Öğretmen müsaitlikleri çözümleniyor"),
        (0.20, "Kısıtlar modele çevriliyor"),
        (0.36, "Bloklar yerleştiriliyor"),
        (0.58, "Çakışmalar gideriliyor"),
        (0.74, "Boşluklar toplanıyor"),
        (0.88, "Sonuç iyileştiriliyor"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._elapsed = 0.0
        self._estimate = 45.0
        self._real = 0.0
        self._shown = 0.0
        self._done = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(0)

        self.scene = _RunScene(self)
        lay.addWidget(self.scene)
        lay.addSpacing(10)

        self.lbl_stage = QLabel("Veriler okunuyor")
        self.lbl_stage.setAlignment(Qt.AlignCenter)
        self.lbl_stage.setStyleSheet("font-size: 13px; font-weight: 600; color: #0F172A;"
                                     " background: transparent; border: none;")
        lay.addWidget(self.lbl_stage)
        lay.addSpacing(4)

        self.lbl_eta = QLabel("")
        self.lbl_eta.setAlignment(Qt.AlignCenter)
        self.lbl_eta.setStyleSheet("font-size: 11.5px; color: #8A8A93;"
                                   " background: transparent; border: none;")
        lay.addWidget(self.lbl_eta)
        lay.addSpacing(12)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.bar = AppleProgressBar(self)
        self.bar.setRange(0, 1000)
        self.bar.setValue(0)
        row.addWidget(self.bar, 1)
        self.lbl_pct = QLabel("0%")
        self.lbl_pct.setFixedWidth(46)
        self.lbl_pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_pct.setStyleSheet("font-size: 12.5px; font-weight: 700; color: #0F4AAB;"
                                   " background: transparent; border: none;")
        row.addWidget(self.lbl_pct)
        lay.addLayout(row)
        lay.addSpacing(10)

        self.lbl_detail = QLabel("")
        self.lbl_detail.setAlignment(Qt.AlignCenter)
        self.lbl_detail.setStyleSheet("font-size: 10.5px; color: #9A9AA2;"
                                      " background: transparent; border: none;")
        lay.addWidget(self.lbl_detail)

        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

    # ── dışarıdan ────────────────────────────────────────────────────
    def start(self, estimate_seconds=45.0):
        self._elapsed = 0.0
        self._real = 0.0
        self._shown = 0.0
        self._done = False
        self._estimate = max(6.0, float(estimate_seconds or 45.0))
        self.scene.start()
        self._timer.start()
        self._tick()

    def set_progress(self, pct, detail=""):
        try:
            self._real = max(self._real, float(pct))
        except (TypeError, ValueError):
            pass
        if detail:
            self.lbl_detail.setText(str(detail))

    def finish(self):
        self._done = True
        self._real = 100.0
        self.scene.stop()
        self._timer.stop()
        self.bar.setValue(1000)
        self.lbl_pct.setText("100%")
        self.lbl_stage.setText("Tamamlandı")
        self.lbl_eta.setText("")

    # ── içeride ──────────────────────────────────────────────────────
    def _tick(self):
        if self._done:
            return
        self._elapsed += 0.05

        # Kendi kendine ilerleyen eğri: başta hızlı, sonra yavaşlıyor ve
        # %94'ü hiç geçmiyor — gerçek bitişi o söyleyecek.
        t = self._elapsed / (self._estimate * 0.55)
        curve = 94.0 * (1.0 - math.exp(-t))
        target = max(curve, self._real)
        self._shown += (target - self._shown) * 0.12
        pct = max(0.0, min(100.0, self._shown))

        self.bar.setValue(int(pct * 10))
        self.lbl_pct.setText(f"{int(pct)}%")

        frac = pct / 100.0
        stage = self.STAGES[0][1]
        for edge, name in self.STAGES:
            if frac >= edge:
                stage = name
        self.lbl_stage.setText(stage)

        # SÜRE, GEÇEN ZAMANDAN DEĞİL YÜZDEDEN.
        #
        # Geri sayım baştaki tahmine bağlıydı: yüzde bir anda 90'a
        # çıktığında ekran hâlâ "yaklaşık 40 saniye" diyordu. Şimdi kalan
        # süre, o ana kadar geçen sürenin yüzdeye oranından çıkıyor —
        # gerçekten ne kadar kaldığının en iyi tahmini bu. Yüzde yeterince
        # ilerlediyse sayı bırakılıp söz söyleniyor.
        if pct >= 92:
            self.lbl_eta.setText("bitmek üzere")
        elif pct >= 78:
            self.lbl_eta.setText("az kaldı")
        else:
            if pct > 6:
                left = self._elapsed * (100.0 - pct) / pct
                left = min(left, self._estimate * 2.0)
            else:
                left = self._estimate
            if left >= 90:
                self.lbl_eta.setText(f"yaklaşık {int(round(left / 60))} dakika")
            elif left >= 8:
                self.lbl_eta.setText(f"yaklaşık {int(left / 5 + 0.5) * 5} saniye")
            else:
                self.lbl_eta.setText("birkaç saniye")


class Apple3DIconWidget(QWidget):
    """Isometric 3D Schedule Core Icon (Pure floating vector, no square background)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 50)
        self._glow_phase = 0.0
        self._is_active = False
        self._renderer = QSvgRenderer(QByteArray(ICON_SVG), self)
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(35)

    def start_pulse(self):
        self._is_active = True

    def stop_pulse(self):
        self._is_active = False
        self.update()

    def _on_tick(self):
        if self._is_active:
            self._glow_phase += 0.08
            if self._glow_phase > 2 * math.pi:
                self._glow_phase -= 2 * math.pi
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        
        if self._is_active:
            glow_rad = QRadialGradient(w / 2, h / 2, w / 2)
            alpha = int(60 + 35 * math.sin(self._glow_phase))
            glow_rad.setColorAt(0.0, QColor(0, 113, 227, alpha))
            glow_rad.setColorAt(1.0, QColor(0, 113, 227, 0))
            painter.setBrush(QBrush(glow_rad))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, w, h)
            
        self._renderer.render(painter, QRectF(0, 0, w, h))


# ═══════════════════════════════════════════════════════════════════════
# 2. APPLE NATIVE COMBOBOX WITH CLEAN CHEVRON
# ═══════════════════════════════════════════════════════════════════════
class AppleComboBox(QComboBox):
    """macOS Apple Styled ComboBox with crisp vector chevron indicator."""
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        cx = w - 18
        cy = h / 2
        
        is_open = self.view().isVisible() if self.view() else False
        color = QColor("#0071E3" if is_open else "#86868B")
        pen = QPen(color, 1.8)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        path = QPainterPath()
        if is_open:
            # Up Chevron
            path.moveTo(cx - 4.5, cy + 2.5)
            path.lineTo(cx, cy - 2)
            path.lineTo(cx + 4.5, cy + 2.5)
        else:
            # Down Chevron
            path.moveTo(cx - 4.5, cy - 2.5)
            path.lineTo(cx, cy + 2)
            path.lineTo(cx + 4.5, cy - 2.5)
        painter.drawPath(path)


# ═══════════════════════════════════════════════════════════════════════
# 3. APPLE NATIVE TOGGLE SWITCH WIDGET
# ═══════════════════════════════════════════════════════════════════════
class AppleSwitch(QWidget):
    """Sleek macOS Apple Switch Toggle Control (40x22px)."""
    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.PointingHandCursor)
        self._checked = bool(checked)
        self._handle_x = 20.0 if self._checked else 2.0
        
        self._anim = QPropertyAnimation(self, b"handle_position", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)

    def get_handle_position(self) -> float:
        return self._handle_x

    def set_handle_position(self, pos: float):
        self._handle_x = pos
        self.update()

    handle_position = Property(float, get_handle_position, set_handle_position)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self._anim.stop()
            self._anim.setStartValue(self._handle_x)
            self._anim.setEndValue(20.0 if checked else 2.0)
            self._anim.start()
            self.toggled.emit(checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isEnabled():
            self.setChecked(not self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        
        # Track Background
        track_rect = QRectF(0, 0, w, h)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, h / 2, h / 2)
        
        if self._checked:
            bg_color = QColor("#34C759")  # Apple Green
        else:
            bg_color = QColor("#E5E5EA")  # Apple Light Grey
            
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(track_path)
        
        # Knob
        knob_size = h - 4
        knob_rect = QRectF(self._handle_x, 2, knob_size, knob_size)
        
        # Subtle Knob Shadow
        shadow_rect = QRectF(self._handle_x, 3, knob_size, knob_size)
        painter.setBrush(QBrush(QColor(0, 0, 0, 30)))
        painter.drawEllipse(shadow_rect)
        
        # Knob Body
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(knob_rect)


# ═══════════════════════════════════════════════════════════════════════
# 4. SKELETON AWAITING GRID (Animated Shimmer Wave)
# ═══════════════════════════════════════════════════════════════════════
class AppleSkeletonLoader(QWidget):
    """Shimmering Apple-style Timetable matrix skeleton awaiting resolution."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self._phase = 0.0
        self._is_active = False
        self._placed_ratio = 0.0
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(30)

    def set_active(self, active: bool):
        self._is_active = active
        self.update()

    def set_placed_ratio(self, ratio: float):
        self._placed_ratio = max(0.0, min(1.0, ratio))
        self.update()

    def _on_tick(self):
        if self._is_active:
            self._phase += 0.032
            if self._phase > 1.4:
                self._phase = -0.4
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        
        # Matrix container card
        card_rect = QRectF(0, 0, w, h)
        card_path = QPainterPath()
        card_path.addRoundedRect(card_rect, 10, 10)
        painter.setBrush(QBrush(QColor("#F5F5F7")))
        painter.setPen(QPen(QColor("#E5E5EA"), 1))
        painter.drawPath(card_path)
        
        cols = 5
        rows = 2
        pad_x = 10
        pad_y = 6
        gap = 6
        
        slot_w = (w - (2 * pad_x) - (cols - 1) * gap) / cols
        slot_h = (h - (2 * pad_y) - (rows - 1) * gap) / rows
        
        shimmer_x = self._phase * w
        slot_idx = 0
        total_slots = cols * rows
        
        for r in range(rows):
            for c in range(cols):
                sx = pad_x + c * (slot_w + gap)
                sy = pad_y + r * (slot_h + gap)
                s_rect = QRectF(sx, sy, slot_w, slot_h)
                
                is_filled = (slot_idx / float(total_slots)) < self._placed_ratio
                slot_idx += 1
                
                s_path = QPainterPath()
                s_path.addRoundedRect(s_rect, 5, 5)
                
                if is_filled:
                    painter.setBrush(QBrush(QColor("#0071E3" if self._is_active else "#34C759")))
                    painter.setPen(Qt.NoPen)
                    painter.drawPath(s_path)
                else:
                    base_color = QColor("#E5E5EA")
                    if self._is_active:
                        dist = abs((sx + slot_w / 2) - shimmer_x)
                        if dist < 65:
                            intensity = int(255 - (dist / 65.0) * 60)
                            shimmer_color = QColor(intensity, intensity, intensity)
                            painter.setBrush(QBrush(shimmer_color))
                        else:
                            painter.setBrush(QBrush(base_color))
                    else:
                        painter.setBrush(QBrush(base_color))
                        
                    painter.setPen(Qt.NoPen)
                    painter.drawPath(s_path)


# ═══════════════════════════════════════════════════════════════════════
# 5. SLEEK APPLE PROGRESS BAR (6px)
# ═══════════════════════════════════════════════════════════════════════
class AppleProgressBar(QWidget):
    """Sleek minimalist 6px progress bar with gradient fill."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(6)
        self._value = 0
        self._max = 100

    def setValue(self, val: int):
        self._value = max(0, min(self._max, val))
        self.update()

    def setRange(self, min_val: int, max_val: int):
        self._max = max(1, max_val)
        self.update()

    def value(self) -> int:
        return self._value

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        
        # Track
        track_rect = QRectF(0, 0, w, h)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, h / 2, h / 2)
        painter.setBrush(QBrush(QColor("#E5E5EA")))
        painter.setPen(Qt.NoPen)
        painter.drawPath(track_path)
        
        # Active Fill
        fill_w = (self._value / float(self._max)) * w
        if fill_w > 1:
            fill_rect = QRectF(0, 0, fill_w, h)
            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill_rect, h / 2, h / 2)
            
            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0.0, QColor("#0071E3"))
            grad.setColorAt(1.0, QColor("#38BDF8"))
            
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            painter.drawPath(fill_path)


# ═══════════════════════════════════════════════════════════════════════
# 6. CROSS CONFLICT RESOLUTION DIALOG
# ═══════════════════════════════════════════════════════════════════════
class CrossConflictResolutionDialog(QDialog):
    def __init__(self, conflicts, parent=None):
        super().__init__(parent)
        # NoDropShadowWindowHint: on macOS a frameless + translucent window still gets a
        # native Cocoa shadow layer, and that layer is what paints as an opaque black
        # rectangle when the compositor cannot resolve the window's alpha. The in-app
        # QGraphicsDropShadowEffects were removed for this same symptom; this is the
        # remaining shadow source. The cards draw their own border, so nothing is lost.
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(540, 420)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        card = QFrame()
        card.setObjectName("conflictCard")
        card.setStyleSheet("""
            #conflictCard {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 18px;
            }
        """)
        
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(24, 20, 24, 20)
        c_lay.setSpacing(12)
        
        # Header
        hdr = QHBoxLayout()
        icon_lbl = QLabel()
        icon_svg = QByteArray(b'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="#FF9500" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        ''')
        r = QSvgRenderer(icon_svg)
        pm = QPixmap(28, 28)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        r.render(p)
        p.end()
        icon_lbl.setPixmap(pm)
        hdr.addWidget(icon_lbl)
        
        t_col = QVBoxLayout()
        title = QLabel("Çapraz Kurum Öğretmen Çakışması")
        title.setStyleSheet("font-size: 13.5px; font-weight: bold; color: #1D1D1F; background: transparent; border: none;")
        sub = QLabel("Aşağıdaki öğretmen(ler) diğer kurumlarda aynı saatte derstedir:")
        sub.setStyleSheet("font-size: 10px; color: #86868B; background: transparent; border: none;")
        t_col.addWidget(title)
        t_col.addWidget(sub)
        hdr.addLayout(t_col)
        hdr.addStretch(1)
        c_lay.addLayout(hdr)
        
        # Scroll area with conflicts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #E5E5EA; border-radius: 8px; background: #F9F9FB; }")
        
        list_w = QWidget()
        list_w.setStyleSheet("background: transparent;")
        list_lay = QVBoxLayout(list_w)
        list_lay.setContentsMargins(8, 8, 8, 8)
        list_lay.setSpacing(6)
        
        seen = set()
        for c in conflicts:
            t_name = c.get("teacher", "")
            d_idx = c.get("day", 0)
            p_idx = c.get("period", 0)
            other_inst = c.get("other_institution") or c.get("institution", "Diğer Kurum")
            other_cls = c.get("other_class") or c.get("class", "")
            other_sub = c.get("other_subject") or c.get("subject", "")
            this_cls = c.get("this_class", "")
            this_sub = c.get("this_subject", "")
            
            k = (t_name, d_idx, p_idx, other_inst)
            if k in seen:
                continue
            seen.add(k)
            
            from timetable_grid import DAYS
            d_name = DAYS[d_idx] if 0 <= d_idx < len(DAYS) else f"{d_idx+1}. Gün"
            
            c_row = QFrame()
            c_row.setStyleSheet("background: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 6px;")
            r_lay = QVBoxLayout(c_row)
            r_lay.setContentsMargins(10, 6, 10, 6)
            r_lay.setSpacing(2)
            
            lbl_t = QLabel(f"<b>{t_name}</b> — {d_name} {p_idx+1}. Ders Saati")
            lbl_t.setStyleSheet("font-size: 11px; color: #1D1D1F; background: transparent; border: none;")
            
            det_text = f"• Diğer Kurum: <b>{other_inst}</b>"
            if other_cls or other_sub:
                det_text += f" ({other_cls} - {other_sub})"
            if this_cls or this_sub:
                det_text += f"\n• Bu Kurumdaki Hedef: <b>{this_cls} - {this_sub}</b>"
            lbl_d = QLabel(det_text)
            lbl_d.setStyleSheet("font-size: 10px; color: #D97706; background: transparent; border: none;")
            
            r_lay.addWidget(lbl_t)
            r_lay.addWidget(lbl_d)
            list_lay.addWidget(c_row)
            
        list_lay.addStretch(1)
        scroll.setWidget(list_w)
        c_lay.addWidget(scroll, 1)
        
        # Action Buttons
        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(10)
        
        btn_block = QPushButton("Engelle / Diğerlerine Devam Et")
        btn_block.setCursor(Qt.PointingHandCursor)
        btn_block.setStyleSheet("""
            QPushButton {
                background: #F5F5F7; color: #DC2626; border: 1px solid #FCA5A5;
                border-radius: 8px; padding: 8px 16px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: #FEE2E2; }
        """)
        btn_block.clicked.connect(self.reject)
        
        btn_ignore = QPushButton("Yoksay ve Yerleştir (Devam Et)")
        btn_ignore.setCursor(Qt.PointingHandCursor)
        btn_ignore.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 8px 18px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        btn_ignore.clicked.connect(self.accept)
        
        btn_lay.addWidget(btn_block)
        btn_lay.addWidget(btn_ignore)
        c_lay.addLayout(btn_lay)
        
        layout.addWidget(card)


# ═══════════════════════════════════════════════════════════════════════
# 7. MAIN AUTO SCHEDULE DIALOG (Pure Apple Minimalism & BGZ Engine)
# ═══════════════════════════════════════════════════════════════════════
def _teachers_with_capacity(data_store, needed_subjects=None):
    """Boş saati olan öğretmenler: (ad, boş saat, branş, dersi verebilir mi).

    Açıkta kalan dersleri kimin devralabileceğini söylemek için. Müsaitlik
    tablosundaki açık saat sayısından, o öğretmene atanmış toplam ders saati
    düşülüyor; kalan, gerçekten devralabileceği yük.
    """
    import constraint_sync
    import lesson_hours
    from auto_scheduler import norm_teacher, normalize_clean

    D, P = constraint_sync.grid_dimensions(data_store)
    assigned = {}
    for a in data_store.get("atamalar", []) or []:
        if not isinstance(a, dict):
            continue
        tk = norm_teacher(a.get("teacher") or a.get("ogretmen") or a.get("teacher_name") or "")
        if tk:
            assigned[tk] = assigned.get(tk, 0) + (lesson_hours.hours(a) or 0)

    wanted = {normalize_clean(x) for x in (needed_subjects or set()) if x}
    out = []
    seen = set()
    for t in data_store.get("ogretmenler", []) or []:
        if not isinstance(t, dict):
            continue
        name = (t.get("ad") or t.get("name") or "").strip()
        tk = norm_teacher(name)
        if not name or tk in seen:
            continue
        seen.add(tk)
        matrix = constraint_sync.get_matrix(t, name, data_store)
        open_slots = sum(1 for d in range(min(D, len(matrix)))
                         for p in range(min(P, len(matrix[d])))
                         if matrix[d][p] != constraint_sync.CLOSED)
        spare = open_slots - assigned.get(tk, 0)
        if spare <= 0:
            continue
        branch = (t.get("brans") or "").strip()
        bn = normalize_clean(branch)
        fits = bool(wanted and bn and any(w and (w in bn or bn in w) for w in wanted))
        out.append((name, spare, branch, fits))

    # Dersi verebilecekler önce, sonra en çok boş saati olan.
    out.sort(key=lambda x: (not x[3], -x[1]))
    return out


class AutoScheduleDialog(QDialog):
    """
    Apple Minimalist & Pure 3D Vector BGZ Yapay Zeka Optimizasyon Motoru Sheet.
    """
    def __init__(self, data_store=None, parent=None, target_class=None):
        super().__init__(parent)
        self.data_store = data_store
        self.target_class = target_class
        self.worker = None
        self.setWindowTitle("Otomatik Ders Programı Oluşturucu")
        self.setFixedWidth(560)
        self.setModal(True)
        
        # Clean Apple Sheet Design System
        # Çizelge sıfırlama sayfasıyla aynı kabuk: çerçevesiz, saydam
        # zemin, içeride tek bir kart. Sistem başlık çubuğu ve sistem
        # gölgesi yok — ikisi de kartın kendi gölgesiyle çakışıyor ve
        # etrafında ikinci bir pencere varmış gibi duruyordu.
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint
                            | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self._drag_from = None

        self.setStyleSheet("""
            QDialog {
                background: transparent;
            }
            QFrame#sheetCard {
                background-color: #FFFFFF;
                border: 1px solid rgba(15, 23, 42, 0.08);
                border-radius: 20px;
            }
            QFrame#card {
                background-color: #FBFCFD;
                border: 1px solid rgba(15, 23, 42, 0.07);
                border-radius: 14px;
            }
            #etutPanel {
                background-color: #F8F9FA;
                border: 1px solid #E5E5EA;
                border-radius: 10px;
            }
            #etutPanel QLabel {
                background: transparent;
                border: none;
            }
            QLabel {
                color: #1D1D1F;
                background: transparent;
                border: none;
            }
            QLabel#sectionLabel {
                font-size: 11px;
                font-weight: 700;
                color: #86868B;
                letter-spacing: 0.6px;
            }
            QComboBox {
                border: 1px solid #D2D2D7;
                border-radius: 8px;
                padding-left: 12px;
                padding-right: 34px;
                background: #FFFFFF;
                color: #1D1D1F;
                font-size: 13px;
                font-weight: 400;
                height: 34px;
            }
            QComboBox:hover {
                border-color: #0071E3;
            }
            QComboBox:focus {
                border: 1.5px solid #0071E3;
            }
            QComboBox::drop-down {
                border: none;
                width: 0px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #D2D2D7;
                border-radius: 8px;
                background: #FFFFFF;
                selection-background-color: #0071E3;
                selection-color: #FFFFFF;
                padding: 4px;
                outline: none;
            }
            QPushButton#btnCancel {
                background: transparent;
                color: #6E6E76;
                border: none;
                border-radius: 19px;
                padding: 0 16px;
                min-height: 38px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton#btnCancel:hover {
                background: rgba(15, 23, 42, 0.05);
                color: #0F172A;
            }
            QPushButton#btnStart {
                background: #0F4AAB;
                color: #FFFFFF;
                border: none;
                border-radius: 19px;
                padding: 0 24px;
                min-height: 38px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#btnStart:hover {
                background: #0C3C8C;
            }
            QPushButton#btnStart:pressed {
                background: #082B67;
            }
            QPushButton#btnStart:disabled {
                background: #E2E8F0;
                color: #94A3B8;
            }
        """)
        
        self._build_ui()
        self.adjustSize()
        self._center_on(parent)

    # Çerçevesiz pencere elle taşınır ve elle ortalanır; sistem başlık
    # çubuğu olmadığı için ikisini de Qt yapmıyor.
    def _center_on(self, parent):
        from PySide6.QtWidgets import QApplication
        self.adjustSize()
        ref = None
        if parent is not None:
            try:
                w = parent.window()
                if w is not None and w.isVisible():
                    ref = w.frameGeometry()
            except Exception:
                ref = None
        if ref is None:
            screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
            if screen is None:
                return
            ref = screen.availableGeometry()
        self.move(ref.center() - QPoint(self.width() // 2, self.height() // 2))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_from = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_from is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_from)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_from = None
        super().mouseReleaseEvent(e)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)

        sheet = QFrame(self)
        sheet.setObjectName("sheetCard")
        _sh = QGraphicsDropShadowEffect(sheet)
        _sh.setBlurRadius(34)
        _sh.setOffset(0, 10)
        _sh.setColor(QColor(15, 23, 42, 52))
        sheet.setGraphicsEffect(_sh)
        outer.addWidget(sheet)

        root_layout = QVBoxLayout(sheet)
        root_layout.setContentsMargins(24, 22, 24, 20)
        root_layout.setSpacing(13)

        # ═══ BAŞLIK: 3B resim üstte, yazı ortada ═══
        #
        # Önce solda küçük bir kutu ikonu ve yanında iki satır vardı.
        # Sıfırlama sayfasıyla aynı dil: resim ortada ve büyük, çünkü
        # anlatacağı bir şey var — kartlar tablaya sırayla oturuyor.
        self.icon_3d = PlannerArtWidget(84, self)
        root_layout.addWidget(self.icon_3d)

        lbl_title = QLabel("Otomatik Ders Programı")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("font-size: 17px; font-weight: 700; color: #0F172A;"
                                " letter-spacing: -0.3px; background: transparent; border: none;")
        root_layout.addWidget(lbl_title)

        lbl_sub = QLabel("Chenkron Optimizasyon Motoru")
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet("color: #8A8A93; font-size: 11.5px;"
                              " background: transparent; border: none;")
        root_layout.addWidget(lbl_sub)
        root_layout.addSpacing(2)
        
        # ═══ 2. PARAMETERS CARD ═══
        param_card = QFrame()
        param_card.setObjectName("card")
        p_lay = QVBoxLayout(param_card)
        p_lay.setContentsMargins(16, 14, 16, 14)
        p_lay.setSpacing(10)
        
        lbl_sec1 = QLabel("PLANLAMA PARAMETRELERİ")
        lbl_sec1.setObjectName("sectionLabel")
        p_lay.addWidget(lbl_sec1)
        
        # Scope Selector
        col_scope = QVBoxLayout()
        col_scope.setSpacing(4)
        lbl_scope = QLabel("Planlanacak Kapsam")
        lbl_scope.setStyleSheet("font-size: 11.5px; font-weight: 500; color: #48484A;")
        
        self.cb_target_class = AppleComboBox()
        self.cb_target_class.setFixedHeight(34)
        self.cb_target_class.addItem("Tüm Okul (Tüm Sınıflar & Öğretmenler — Önerilen)", None)
        
        all_cls = []
        for c in (self.data_store.get("siniflar", []) if self.data_store else []):
            cad = c.get("ad", "").strip()
            if cad and cad not in all_cls:
                all_cls.append(cad)
        for a in (self.data_store.get("atamalar", []) if self.data_store else []):
            cad = (a.get("class") or a.get("sinif") or a.get("class_name") or "").strip()
            if cad and cad not in all_cls:
                all_cls.append(cad)
                
        for cn in sorted(all_cls):
            self.cb_target_class.addItem(f"Sadece {cn}", cn)
            
        if self.target_class:
            idx = self.cb_target_class.findData(self.target_class)
            if idx >= 0:
                self.cb_target_class.setCurrentIndex(idx)
        else:
            self.cb_target_class.setCurrentIndex(0)
            
        col_scope.addWidget(lbl_scope)
        col_scope.addWidget(self.cb_target_class)
        p_lay.addLayout(col_scope)
        
        # Algorithm Selector
        col_algo = QVBoxLayout()
        col_algo.setSpacing(4)
        lbl_algo = QLabel("Arama Algoritması")
        lbl_algo.setStyleSheet("font-size: 11.5px; font-weight: 500; color: #48484A;")
        
        self.cb_complexity = AppleComboBox()
        self.cb_complexity.setFixedHeight(34)
        self.cb_complexity.addItems([
            "Chenkron Optimizasyon Motoru (Yüksek Performans & Akıllı Çözücü — Önerilen)",
            "Hızlı Sezgisel Arama (Fast Heuristic)",
            "Katı Kural Kısıt Çözücü (Strict CSP)"
        ])
        col_algo.addWidget(lbl_algo)
        col_algo.addWidget(self.cb_complexity)
        p_lay.addLayout(col_algo)
        
        # Divider line
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #E5E5EA;")
        p_lay.addWidget(div)
        
        # ═══ 3. APPLE TOGGLE SWITCHES ═══
        def make_switch_row(title_text, sub_text, init_val, is_disabled=False, badge_text=None):
            row = QHBoxLayout()
            row.setSpacing(12)
            
            text_col = QVBoxLayout()
            text_col.setSpacing(1)
            
            title_r = QHBoxLayout()
            title_r.setSpacing(6)
            t_lbl = QLabel(title_text)
            t_lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
            title_r.addWidget(t_lbl)
            
            if badge_text:
                b_lbl = QLabel(badge_text)
                b_lbl.setStyleSheet("background: #E5E5EA; color: #6E6E73; border-radius: 4px; padding: 1px 5px; font-size: 9px; font-weight: 600;")
                title_r.addWidget(b_lbl)
                
            title_r.addStretch(1)
            text_col.addLayout(title_r)
            
            s_lbl = QLabel(sub_text)
            s_lbl.setStyleSheet("color: #86868B; font-size: 10px;")
            text_col.addWidget(s_lbl)
            
            sw = AppleSwitch(checked=init_val)
            if is_disabled:
                sw.setEnabled(False)
                
            row.addLayout(text_col, 1)
            row.addWidget(sw, 0, Qt.AlignVCenter)
            return row, sw
            
        row_vds, self.sw_vds = make_switch_row(
            "VDS Bulut Sunucu Desteği",
            "Hesaplama yükünü harici yüksek performanslı sunucuya aktar",
            False
        )
        row_zero, self.sw_zero_gap = make_switch_row(
            "Sıfır Boşluklu Gün Düzeni",
            "1. dersten itibaren dersleri aralıksız / penceressiz yerleştir",
            True, is_disabled=True
        )
        row_fill, self.sw_fill_empty = make_switch_row(
            "Boş Saatleri Etüt ile Doldur",
            "Gelişmiş etüt & soru çözüm dağıtım motoru",
            False, is_disabled=True, badge_text="Bakımda"
        )
        
        # Her zaman açık ve kapatılamaz: kurumlar zaman tablosu bakımından
        # bağımsızdır (constraint_sync.INSTITUTIONS_INDEPENDENT). Ortak
        # öğretmenin başka kurumdaki dersi burada dikkate alınmaz.
        row_ignore, self.sw_ignore_cross = make_switch_row(
            "Diğer Kurumları Yoksay",
            "Kurumlar birbirinden bağımsızdır — bu ayar her zaman açıktır, kapatılamaz",
            True, is_disabled=True
        )

        # Off by default, and deliberately worded so the cost is visible before it is
        # switched on: it fills the grid by allowing the same teacher to be booked in
        # two classes at the same hour. The result is a complete-LOOKING timetable
        # that cannot actually be run, so every such lesson is flagged on the grid and
        # counted in the summary rather than quietly blending in.
        row_independent, self.sw_independent = make_switch_row(
            "Sınıfları Bağımsız Doldur",
            "Her sınıfı diğerlerinden bağımsız doldurur — öğretmen çakışmaları "
            "oluşur ve işaretlenir",
            False
        )

        # Süre bir hedef değil: motor CP-SAT'in OPTIMAL kanıtını bekler ve
        # kanıt gelince durur. Karşılığında "şu an elde edilebilecek en iyi
        # sonuç bu" denebilir — normal kipte bu söylenemez, çünkü bütçe
        # dolduğu için durmuş olabilir.
        row_optimal, self.sw_optimal = make_switch_row(
            "Optimale Kadar Çalış",
            "Kanıt gelene kadar durmaz, takas yapa yapa ilerler — uzun sürebilir",
            True, is_disabled=True
        )
        # 2 saatlik ders 1+1, 2+2+1 ise 1+1+1+1+1 olabilir. Sınıfın gününde
        # tek saatlik bir açıklık kaldığında bütün blok oraya sığmaz ve o saat
        # ölü kalır; bölme tam bu boşluğu doldurur. Bedelli, ancak gerektiğinde
        # devreye girer.
        row_split, self.sw_split = make_switch_row(
            "Blokları Bölebilsin",
            "2 saatlik dersi 1+1, 2+2+1'i 1+1+1+1+1 yapabilir — yalnızca gerekirse",
            True, is_disabled=True
        )

        p_lay.addLayout(row_vds)
        p_lay.addLayout(row_zero)
        p_lay.addLayout(row_fill)
        p_lay.addLayout(row_ignore)
        p_lay.addLayout(row_optimal)
        p_lay.addLayout(row_split)
        self.sw_independent.setChecked(False)
        self.sw_independent.setEnabled(False)
        for i in range(row_independent.count()):
            widget = row_independent.itemAt(i).widget()
            if widget:
                widget.hide()
        
        root_layout.addWidget(param_card)
        self.param_card = param_card

        # Çalışma ekranı: başlatana kadar gizli. Başlatınca parametrelerin
        # YERİNE geçiyor — o sırada ayar değiştirilemeyeceği için onları
        # ekranda tutmanın anlamı yok, üstelik sahne yer istiyor.
        self.run_panel = PlannerRunPanel(self)
        self.run_panel.setVisible(False)
        root_layout.addWidget(self.run_panel)

        # ═══ 4. SKELETON AWAITING & LIVE PROGRESS CARD ═══
        prog_card = QFrame()
        prog_card.setObjectName("card")
        self.prog_card = prog_card
        pr_lay = QVBoxLayout(prog_card)
        pr_lay.setContentsMargins(16, 12, 16, 12)
        pr_lay.setSpacing(8)
        
        # Status message + percentage
        stat_top = QHBoxLayout()
        self.lbl_info = QLabel("Program oluşturmaya hazır. Mevcut kilitli dersler korunacaktır.")
        self.lbl_info.setStyleSheet("font-size: 11px; color: #6E6E73;")
        
        self.lbl_pct = QLabel("0%")
        self.lbl_pct.setStyleSheet("font-size: 11.5px; font-weight: bold; color: #0071E3;")
        
        stat_top.addWidget(self.lbl_info, 1)
        stat_top.addWidget(self.lbl_pct)
        pr_lay.addLayout(stat_top)
        
        # Apple Slim Progress Bar (6px)
        self.progress = AppleProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        pr_lay.addWidget(self.progress)
        
        # Skeleton Shimmering Timetable Matrix
        self.skeleton = AppleSkeletonLoader(self)
        self.skeleton.setFixedHeight(48)
        pr_lay.addWidget(self.skeleton)
        
        # Live Metrics Chips
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(8)
        
        def make_chip(title, init_val):
            chip = QFrame()
            chip.setStyleSheet("background: #F5F5F7; border-radius: 6px; padding: 2px 8px;")
            c_lay = QHBoxLayout(chip)
            c_lay.setContentsMargins(4, 2, 4, 2)
            c_lay.setSpacing(5)
            
            lbl_t = QLabel(title)
            lbl_t.setStyleSheet("font-size: 9.5px; color: #86868B;")
            
            lbl_v = QLabel(init_val)
            lbl_v.setStyleSheet("font-size: 10px; font-weight: bold; color: #1D1D1F;")
            
            c_lay.addWidget(lbl_t)
            c_lay.addWidget(lbl_v)
            return chip, lbl_v
            
        self.chip_iter, self.lbl_val_iter = make_chip("İterasyon", "0")
        self.chip_conf, self.lbl_val_conf = make_chip("Çakışma", "0")
        self.chip_placed, self.lbl_val_placed = make_chip("Yerleşen", "0 Saat")
        
        metrics_row.addWidget(self.chip_iter)
        metrics_row.addWidget(self.chip_conf)
        metrics_row.addWidget(self.chip_placed)
        metrics_row.addStretch(1)
        pr_lay.addLayout(metrics_row)
        
        root_layout.addWidget(prog_card)
        
        # ═══ 5. ACTION BUTTONS ═══
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 2, 0, 0)
        btn_layout.setSpacing(10)
        
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self._on_cancel_or_stop)
        
        self.btn_start = QPushButton("Planlamayı Başlat")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._start_generation)
        
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_start)
        root_layout.addLayout(btn_layout)

    def _start_generation(self):
        from auto_scheduler import format_tr_name, normalize_clean
        teachers = self.data_store.get("ogretmenler", []) if self.data_store else []
        atamalar = self.data_store.get("atamalar", []) if self.data_store else []
        teacher_names = [t.get("ad", "").strip() for t in teachers if t.get("ad", "").strip()]
        assigned_teachers = set()
        for a in atamalar:
            t = (a.get("teacher") or a.get("ogretmen") or "").strip()
            if t:
                assigned_teachers.add(t)
                assigned_teachers.add(format_tr_name(t))
                assigned_teachers.add(normalize_clean(t))
        
        unassigned = []
        for tn in teacher_names:
            if (tn not in assigned_teachers and 
                format_tr_name(tn) not in assigned_teachers and
                normalize_clean(tn) not in assigned_teachers):
                unassigned.append(tn)
        
        if unassigned:
            msg = (f"Aşağıdaki {len(unassigned)} öğretmenin hiçbir ders ataması bulunamadı:\n\n"
                   + "\n".join(f"• {t}" for t in sorted(unassigned))
                   + "\n\nBu öğretmenler programa dahil edilemeyecektir. "
                   "Lütfen önce 'Atamalar' bölümünden bu öğretmenlere ders atayın.\n\n"
                   "Devam etmek istiyor musunuz?")
            reply = QMessageBox.warning(self, "Ataması Olmayan Öğretmenler", msg,
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        # Transition UI to Running State
        self.progress.setValue(0)
        self.lbl_pct.setText("0%")
        self.btn_start.setEnabled(False)
        self.btn_cancel.setText("Durdur ve Kaydet")
        self.lbl_info.setText("Chenkron Yapay Zeka Motoru çalışıyor (Canlı kısıt optimizasyonu)...")
        self.lbl_info.setStyleSheet("color: #0071E3; font-weight: 500;")
        
        self.icon_3d.start_pulse()
        self.skeleton.set_active(True)
        self.skeleton.set_placed_ratio(0.0)

        # Parametreler gidiyor, sahne geliyor. Tahmin ders saatinden
        # çıkarılıyor; "optimale kadar çalış" açıksa motor kanıt arayana
        # kadar durmadığı için süre kabaca ikiye katlanıyor.
        try:
            _hours = 0
            for _a in (self.data_store.get("atamalar", []) if self.data_store else []):
                try:
                    _hours += int(_a.get("duration", 0) or 0)
                except (TypeError, ValueError):
                    pass
            _est = max(10.0, min(240.0, _hours * 0.16 or 30.0))
            if getattr(self, "sw_optimal", None) is not None and self.sw_optimal.isChecked():
                _est *= 2.0
            self.param_card.setVisible(False)
            if getattr(self, "prog_card", None) is not None:
                # Eski ilerleme kartı da gizleniyor: iki ilerleme çubuğu
                # aynı anda ekrandaysa hangisinin doğru olduğu sorulur.
                self.prog_card.setVisible(False)
            self.run_panel.setVisible(True)
            self.run_panel.start(_est)
            self.adjustSize()
        except Exception as exc:
            print(f"[AUTO] çalışma ekranı açılamadı: {exc}")
        
        # Check the input BEFORE building anything. Without this the run produces a
        # grid with holes and the user cannot tell whether the scheduler gave up or
        # the timetable is arithmetically impossible — two problems with completely
        # different fixes. Say which it is, up front, and let them decide.
        if not self._confirm_feasibility():
            return

        from auto_scheduler import AutoSchedulerWorker
        fill_empty = True
        chosen_target = self.cb_target_class.currentData()
        inst_slug = getattr(self.parent(), "institution_slug", None)
        use_vds = self.sw_vds.isChecked()
        
        self.worker = AutoSchedulerWorker(
            self.data_store, target_class=chosen_target, parent=self,
            fill_empty=fill_empty, institution_slug=inst_slug, use_vds=use_vds,
            infinite_mode=True,
            ignore_other_institutions=True,
            independent_classes=False,
            optimal_mode=True,
            allow_split=True,
        )
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.iteration_updated.connect(self._on_iteration)
        self.worker.finished_successfully.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.ask_continue_requested.connect(self._on_ask_continue)
        self.worker.start()

    def _on_ask_continue(self, info):
        """Motor tam çizelgeye ulaşamadı; beklemeye devam edilsin mi?"""
        if getattr(self, "_closing", False) or self.worker is None or not self.worker.isRunning():
            if self.worker is not None:
                self.worker.answer_continue(False)
            return
        saat, toplam = info.get("saat", 0), info.get("toplam", 0)
        gecen = int(info.get("gecen", 0))
        eksik = max(0, toplam - saat)
        ust = info.get("ust")
        self.lbl_info.setText(f"{saat}/{toplam} saat — karar bekleniyor")
        self.lbl_info.setStyleSheet("color: #B45309; font-weight: 600;")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Beklemeye devam edilsin mi?")
        box.setText(f"{saat}/{toplam} saat yerleşti ({eksik} saat açıkta), {gecen} sn geçti.")
        # Tavan biliniyorsa söylenir: "285'e çıkamıyor" diye beklemek yerine
        # kullanıcı en fazla kaçın mümkün olduğunu görür (sebebi bitince
        # raporda yazar).
        if isinstance(ust, int) and ust < toplam:
            tavan = (f"Mevcut kurallar ve zaman tablolarıyla motor en fazla {ust}/{toplam} "
                     f"saatin yerleşebildiğini hesapladı; hangi kuralın/öğretmenin "
                     f"{toplam - ust} saati dışarıda bıraktığı bitişte raporda yazar. ")
            if saat >= ust:
                tavan += "Bu sayıya ulaşıldı. "
            else:
                tavan += f"Bu sayıya {ust - saat} saat kaldı. "
        else:
            tavan = ""
        box.setInformativeText(tavan + "Motor son turda ilerleme kaydedemedi. Bir tur daha "
                               "arayabilirim (en fazla 1 dk) ya da bu hâliyle bitirip açıkta "
                               "kalanları yerleştirilemeyen dersler listesine koyabilirim.")
        b_wait = box.addButton("Bir tur daha bekle", QMessageBox.AcceptRole)
        b_stop = box.addButton("Bu hâliyle bitir", QMessageBox.RejectRole)
        box.setDefaultButton(b_stop)
        box.exec()
        devam = box.clickedButton() is b_wait
        if devam:
            self.lbl_info.setText("Aramaya devam ediliyor…")
            self.lbl_info.setStyleSheet("color: #0071E3; font-weight: 500;")
        self.worker.answer_continue(devam)

    def _confirm_feasibility(self):
        """Başlamadan önce kuralları derler; uygulanamayacak olanları SÖYLER.

        "İki ders aynı güne gelmesin" ders seçilmeden kaydedilmişse motor onu
        atlar. Eskiden bu yalnızca raporun içinde bir satırdı; kullanıcı kuralı
        ekranda açık görüyor, çizelgede uygulanmadığını sanıyor ve motorun
        kuralı görmediğini düşünüyordu. Şimdi planlama başlamadan önce hangi
        kuralın neden uygulanamayacağı yüzüne söylenir, karar ona kalır.
        """
        try:
            from scheduler.build import build_world
            from scheduler.rules import compile_rules
            w = build_world(self.data_store)
            _rules, rep = compile_rules(self.data_store.get("planlama_iliskileri", []), w)
        except Exception as exc:
            QMessageBox.critical(self, "Planlama İlişkileri", f"Kurallar derlenemedi:\n{exc}")
            return False
        if rep.errors:
            QMessageBox.critical(self, "Planlama İlişkileri",
                                 "Şu kurallar hatalı; düzeltmeden planlama başlatılamaz:\n\n"
                                 + "\n".join(f"• {e}" for e in rep.errors[:10]))
            return False
        if rep.skipped:
            body = ("Aşağıdaki kurallar ekranda açık ama bu hâliyle UYGULANAMAZ, "
                    "motor bunları atlayacak:\n\n"
                    + "\n".join(f"• {label}: {why}" for label, why in rep.skipped[:10])
                    + "\n\nPlanlama İlişkileri ekranında kuralı çift tıklayıp dersleri seçerseniz uygulanır."
                    "\n\nBu kurallar olmadan devam edilsin mi?")
            reply = QMessageBox.warning(self, "Uygulanamayan kurallar", body,
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                self.btn_start.setEnabled(True)
                self.btn_cancel.setText("Kapat")
                self.lbl_info.setText("Planlama başlatılmadı; kuralları düzenleyin.")
                self.lbl_info.setStyleSheet("color: #B45309; font-weight: 500;")
                self.icon_3d.stop_pulse()
                self.skeleton.set_active(False)
                return False
        return True

    def _on_cancel_or_stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.lbl_info.setText("Durduruluyor, en iyi çözüm kaydediliyor...")
        else:
            self.reject()

    def _on_iteration(self, iteration, conflicts, placed):
        self.lbl_val_iter.setText(str(iteration))
        self.lbl_val_conf.setText(str(conflicts))
        self.lbl_val_placed.setText(f"{placed} Saat")
        panel = getattr(self, "run_panel", None)
        if panel is not None and panel.isVisible():
            # Sayaçlar çalışma ekranında tek satırda: rakamların
            # kıpırdaması da "duruyor mu?" sorusuna cevap veriyor.
            bits = [f"{placed} saat yerleşti"]
            if iteration:
                bits.append(f"{iteration}. tur")
            if conflicts:
                bits.append(f"{conflicts} çakışma çözülüyor")
            panel.lbl_detail.setText("  ·  ".join(bits))
        if conflicts == 0 and placed > 0:
            self.lbl_val_conf.setStyleSheet("color: #34C759; font-weight: bold; font-size: 10px;")
        else:
            self.lbl_val_conf.setStyleSheet("color: #E11D48; font-weight: bold; font-size: 10px;" if conflicts > 3 else "color: #D97706; font-weight: bold; font-size: 10px;")

    def _close_run_panel(self):
        """Çalışma ekranını kapatır, parametreleri geri getirir.

        Sahne ve sahte akış yalnızca motor çalışırken var; bittiğinde
        ekran başladığı yere dönüyor ki kullanıcı ayarları görüp yeniden
        çalıştırabilsin.
        """
        panel = getattr(self, "run_panel", None)
        if panel is None or not panel.isVisible():
            return
        try:
            panel.finish()
            panel.setVisible(False)
            if getattr(self, "param_card", None) is not None:
                self.param_card.setVisible(True)
            if getattr(self, "prog_card", None) is not None:
                self.prog_card.setVisible(True)
            self.adjustSize()
        except Exception as exc:
            print(f"[AUTO] çalışma ekranı kapatılamadı: {exc}")

    def _on_progress(self, placed, total):
        pct = int((placed / max(1, total)) * 100) if total > 0 else 100
        self.progress.setValue(pct)
        self.lbl_pct.setText(f"{pct}%")
        self.lbl_val_placed.setText(f"{placed} Saat")
        ratio = (placed / float(max(1, total))) if total > 0 else 1.0
        self.skeleton.set_placed_ratio(ratio)
        panel = getattr(self, "run_panel", None)
        if panel is not None and panel.isVisible():
            panel.set_progress(pct, f"{placed} / {total} saat yerleşti" if total else "")

    def _on_failed(self, err_msg):
        self.icon_3d.stop_pulse()
        self.skeleton.set_active(False)
        self._close_run_panel()
        self.btn_start.setEnabled(True)
        self.btn_cancel.setText("Kapat")
        self.lbl_info.setText(f"Hata: {err_msg}")
        self.lbl_info.setStyleSheet("color: #DC2626; font-weight: 500;")

    def _on_finished(self, result):
        # Çarpıyla kapatılırken gelen kısmi sonuç uygulanmaz; "Durdur ve
        # Kaydet" ise normal yoldan gelir ve en iyi çözüm kaydedilir.
        if getattr(self, "_closing", False):
            return
        placed = result.get("placed_hours", 0)
        demand = result.get("total_assigned_hours", result.get("total_hours", 0))
        self._on_progress(placed, demand)
        self.icon_3d.stop_pulse()
        self.skeleton.set_active(False)
        self._close_run_panel()
        self.skeleton.set_placed_ratio(placed / max(1, demand))
        
        schedule = result.get("schedule", [])
        total_hrs = result.get("placed_hours", 0)
        target_hrs = result.get("total_assigned_hours", result.get("total_hours", total_hrs))
        self.lbl_val_placed.setText(f"{total_hrs} Saat")
        complete = bool(result.get("complete", total_hrs == target_hrs))
        self.lbl_info.setText(f"{'Planlama tamamlandı' if complete else 'Planlama eksik'} ({total_hrs}/{target_hrs} saat).")
        self.lbl_info.setStyleSheet(f"color: {'#34C759' if complete else '#B45309'}; font-weight: 600;")
        self.data_store["auto_schedule_results"] = schedule
        # Carried through so the window can explain, right after the run, exactly why
        # any cell was left empty instead of just announcing success.
        self.data_store["auto_schedule_report"] = {
            "understaffed_slots": result.get("understaffed_slots", []),
            "unplaced_summary": result.get("unplaced_summary", []),
            "placed_real_hours": result.get("placed_real_hours", 0),
            "total_assigned_hours": target_hrs,
            "status": result.get("status"),
            "diagnostics": result.get("diagnostics", []),
            "warnings": result.get("warnings", []),
        }
        
        new_placements = []
        try:
            from main_window import get_subject_color, format_tr_name
        except ImportError:
            get_subject_color = lambda s: "#1E88E5"
            format_tr_name = lambda t: t
            
        for item in schedule:
            if isinstance(item, dict):
                r = item.get("period") if "period" in item else item.get("row", 0)
                c = item.get("day_idx") if "day_idx" in item else item.get("day", item.get("col", 0))
                t = format_tr_name(item.get("teacher_name") or item.get("teacher") or "")
                s = item.get("subject_name") or item.get("subject") or ""
                cl = item.get("class_name") or item.get("class") or ""
                dur = int(item.get("duration", 1))
                # Renk yerleştirmeye YAZILMAZ. Tek doğru kaynak resolve_class_color /
                # resolve_subject_color; buraya bir hex çakılırsa oto ile manuel
                # aynı sınıfa farklı renk verir ve çarşaf değiştirince bayat kalır.
                color = None
                is_locked = bool(item.get("locked", False))
                new_placements.append({
                    "row": r, "col": c, "period": r, "day": c,
                    "teacher_name": t, "teacher": t,
                    "subject_name": s, "subject": s,
                    "class_name": cl, "class": cl,

                    "duration": dur,
                    "locked": is_locked,
                    "block_id": item.get("block_id", ""),
                    "is_combined": bool(item.get("is_combined", False)),
                    "is_filler": bool(item.get("is_filler", False))
                })
                
        self.data_store["grid_placements"] = new_placements

        # Everything the scheduler could not place drops into the dock automatically,
        # each card carrying the reason it was blocked.
        #
        # Previously these hours just vanished: the grid came back with holes and the
        # owed lessons existed only in a console line nobody sees. The user had no way
        # to place them by hand, because there was nothing to drag. Now they are all
        # sitting at the bottom, and dropping one explains the clash and offers to
        # override it (see _on_lesson_dropped).
        import uuid as _uuid_unplaced

        leftovers = result.get("unplaced_cards", result.get("unplaced_summary", [])) or []
        existing = self.data_store.setdefault("loose_unplaced_cards", [])
        existing[:] = [c for c in existing if not c.get("from_scheduler")]

        if not leftovers or total_hrs >= target_hrs:
            self.data_store["loose_unplaced_cards"] = []
            self.data_store["unplaced_lessons"] = []
            self.data_store["suppress_unplaced_dock"] = True
        else:
            capacity = {c["teacher"]: c for c in (result.get("capacity_problems", []) or [])}
            for item in leftovers:
                subject = item.get("subject", "")
                teacher = item.get("teacher", "")
                cls = item.get("class", "")
                cap = capacity.get(teacher)
                if cap:
                    reason = (f"{teacher} öğretmenine {cap['assigned']} saat ders atanmış "
                              f"ama müsait olduğu saat {cap['available']}. "
                              f"Bu ders sığmadığı için yerleştirilemedi.")
                else:
                    reason = (f"{teacher} öğretmeninin müsait olduğu saatlerde "
                              f"{cls} sınıfının boş yeri kalmadı.")
                related = [x["message"] for x in result.get("diagnostics", [])
                           if item.get("card_id") in x.get("cards", [])]
                if related:
                    reason = "\n".join(related)
                elif result.get("status") == "timeout":
                    reason = "Arama süresi içinde uygun yer bulunamadı; bu, çözümün imkânsız olduğu anlamına gelmez."
                durations = [item["duration"]] if "duration" in item else [1] * max(1, int(item.get("hours", 1) or 1))
                for block_duration in durations:
                    existing.append({
                        "id": f"loose_{_uuid_unplaced.uuid4().hex[:8]}",
                        "subject_name": subject, "subject": subject,
                        "teacher_name": teacher, "teacher": teacher,
                        "class_name": cls, "class": cls,
                        "duration": block_duration,
                        "block_id": item.get("block_id", ""),
                        "color": get_subject_color(subject) if subject else "#94A3B8",
                        "is_filler": False,
                        "is_combined": False,
                        "combined_classes": [],
                        "from_scheduler": True,
                        "blocked_reason": reason,
                    })
            self.data_store["suppress_unplaced_dock"] = False

        p = self.parent()
        if p:
            if hasattr(p, "save_db"):
                p.save_db(sync_from_grid=False)
            if hasattr(p, "mark_dirty"):
                p.mark_dirty()
            if hasattr(p, "_refresh_grid"):
                p._refresh_grid()
            if hasattr(p, "_refresh_tree"):
                p._refresh_tree()
            
            slug = getattr(p, "institution_slug", None)
            ver_fn = getattr(p, "version_filename", None)
            if slug and ver_fn:
                try:
                    import version_store
                    version_store.update_version_in_place(slug, ver_fn, self.data_store)
                    version_store.touch_institution_timestamp(slug)
                    if hasattr(p, "mark_dirty"):
                        p.mark_dirty()
                except Exception as ve:
                    print(f"[AUTO_SCHEDULE] In-place update error: {ve}")
        
        self._pending_violations = result.get("constraint_violations", [])
        self._result_summary = {
            "total_hrs": total_hrs,
            "target_hrs": target_hrs,
            "capacity_problems": result.get("capacity_problems", []),
            "unplaced_summary": result.get("unplaced_summary", []),
            "teacher_clashes": result.get("teacher_clashes", []),
            "diagnostics": result.get("diagnostics", []),
            "warnings": result.get("warnings", []),
        }
        
        self.accept()
    
    def accept(self):
        violations = getattr(self, "_pending_violations", [])
        summary = getattr(self, "_result_summary", {})
        total_hrs = summary.get("total_hrs", 0)
        target_hrs = summary.get("target_hrs", 0)
        parent = self.parent()
        
        super().accept()

        complete = target_hrs > 0 and total_hrs >= target_hrs
        if parent and summary.get("diagnostics") and not complete:
            message = f"{total_hrs}/{target_hrs} saat yerleşti. Aktif kurallar korundu.\n\n" + "\n\n".join(
                x["message"] for x in summary["diagnostics"])
            QMessageBox.warning(parent, "Planlama kısıtları", message)
        elif parent and violations:
            days_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            viol_teachers = set()
            viol_details = []
            for v in violations[:15]:
                t = v.get("teacher", "?")
                s = v.get("subject", "?")
                c = v.get("class", "?")
                d_name = days_tr[v.get("day", 0)] if v.get("day", 0) < len(days_tr) else "?"
                p_num = v.get("period", 0) + 1
                viol_teachers.add(t)
                viol_details.append(f"• {t} → {c} {s} ({d_name} {p_num}. saat)")
            
            msg = (f"Çizelge oluşturuldu! ({total_hrs}/{target_hrs} saat yerleştirildi)\n\n"
                   f"{len(violations)} adet öğretmen kısıtlaması "
                   f"(izinli gün/saat) yoksayıldı ve devam edildi.\n\n"
                   f"Etkilenen öğretmenler: {', '.join(sorted(unassigned if 'unassigned' in locals() else viol_teachers))}\n\n"
                   + "\n".join(viol_details[:10]))
            if len(violations) > 15:
                msg += f"\n... ve {len(violations) - 15} adet daha."
            msg += "\n\nBu dersleri öğretmenler görünümünden manuel olarak kontrol edip düzeltmeniz önerilir."
            
            def show_warning():
                QMessageBox.warning(parent, "Kısıtlama Bildirimi", msg, QMessageBox.Ok)
            QTimer.singleShot(100, show_warning)
        elif parent and summary.get("teacher_clashes"):
            # Independent mode was on: the grid is fuller, but only because teachers
            # were allowed to be in two places at once. Say so plainly and list them,
            # so the schedule is not printed and handed out as if it were runnable.
            clashes = summary["teacher_clashes"]
            days_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            per_teacher = {}
            for c in clashes:
                per_teacher.setdefault(c["teacher"], []).append(c)

            lines = [
                f"Çizelge oluşturuldu: {total_hrs}/{target_hrs} saat yerleşti.",
                "",
                f"'Sınıfları Bağımsız Doldur' açıktı, bu yüzden {len(clashes)} saatte",
                "öğretmen çakışması var — aynı öğretmen aynı saatte birden fazla sınıfta.",
                "",
                "Bu çizelge bu haliyle UYGULANAMAZ. Çakışan dersler gridde işaretli;",
                "yazdırmadan önce elle düzeltmeniz gerekir.",
                "",
            ]
            for teacher, items in sorted(per_teacher.items(), key=lambda kv: -len(kv[1]))[:8]:
                sample = items[0]
                d_name = days_tr[sample["day"]] if sample["day"] < len(days_tr) else "?"
                lines.append(
                    f"   • {teacher}: {len(items)} çakışma "
                    f"(örn. {d_name} {sample['period'] + 1}. saat → "
                    f"{', '.join(sample['classes'])})"
                )
            if len(per_teacher) > 8:
                lines.append(f"   ... ve {len(per_teacher) - 8} öğretmen daha.")
            lines += [
                "",
                "Çakışmasız bir çizelge için bu seçeneği kapatın; o zaman yerleşemeyen",
                "dersler 'Yerleştirilmeyenler' listesine düşer.",
            ]
            msg = "\n".join(lines)

            def show_clashes():
                QMessageBox.warning(parent, "Öğretmen Çakışmaları Var", msg, QMessageBox.Ok)
            QTimer.singleShot(100, show_clashes)
        elif parent and total_hrs < target_hrs and summary.get("unplaced_summary"):
            # The week did not fill and we know exactly why. Without this the user is
            # left staring at empty cells with no way to tell whether the scheduler
            # gave up or the schedule is genuinely impossible — and the assignment
            # screen cannot show it, because it counts hours per CLASS while the limit
            # that actually binds is per TEACHER.
            # Report what ACTUALLY could not be placed, grouped by teacher, rather
            # than a theoretical bound: these are the real leftover hours, so the
            # numbers add up to the empty cells the user is looking at.
            unplaced = summary["unplaced_summary"]
            by_teacher = {}
            for u in unplaced:
                name = u.get("teacher") or "(öğretmensiz)"
                entry = by_teacher.setdefault(name, {"hours": 0, "classes": set()})
                entry["hours"] += int(u.get("hours", 0) or 0)
                if u.get("class"):
                    entry["classes"].add(u["class"])
            ranked = sorted(by_teacher.items(), key=lambda kv: -kv[1]["hours"])
            missing = sum(v["hours"] for v in by_teacher.values())

            # Where available, pair each teacher with how many hours they can actually
            # work — that is the number that explains the shortfall.
            capacity = {c["teacher"]: c for c in summary.get("capacity_problems", [])}

            lines = [
                f"Çizelge oluşturuldu: {total_hrs}/{target_hrs} saat yerleşti.",
                "",
                f"{missing} saat yerleştirilemedi.",
                "",
                "Sebep sınıflarda değil, ÖĞRETMEN yükünde.",
                "",
                "Bir öğretmen aynı anda tek sınıfta olabilir. Sınıflar haftada kaç saat",
                "açıksa, bir öğretmen de en fazla o kadar saat ders verebilir.",
                "Aşağıdakilere bu tavandan fazla ders atanmış:",
                "",
            ]
            for name, info in ranked[:8]:
                cap = capacity.get(name)
                detail = ""
                if cap:
                    detail = (f"  (toplam {cap['assigned']} saat atanmış, "
                              f"{cap['available']} saat müsait)")
                cls_list = ", ".join(sorted(info["classes"])[:4])
                if len(info["classes"]) > 4:
                    cls_list += f" +{len(info['classes']) - 4}"
                lines.append(f"   • {name}: {info['hours']} saat açıkta{detail}")
                if cls_list:
                    lines.append(f"       etkilenen sınıflar: {cls_list}")
            if len(ranked) > 8:
                lines.append(f"   ... ve {len(ranked) - 8} öğretmen daha.")
            lines += [
                "",
                "Çözüm için şunlardan biri:",
                "   1) Bu öğretmenlerin Zaman Tablosunda kapalı saatlerini açın,",
                "   2) sınıfların kapalı ders saatlerini açın (örn. 5-8. saatler),",
                "   3) veya bu derslerin bir kısmını başka bir öğretmene atayın.",
            ]

            # 3. maddeyi somutlaştır: "başka bir öğretmene atayın" demek, kimin
            # boş saati olduğunu bilmeyen kullanıcı için bir tavsiye değil.
            # Boştaki öğretmenleri, açıkta kalan dersi verebilecek olanları öne
            # alarak isim isim yaz.
            try:
                free = _teachers_with_capacity(self.data_store,
                                               {u.get("subject") for u in unplaced})
            except Exception:
                free = []
            if free:
                lines += ["", "Yükü devralabilecek öğretmenler:"]
                for nm, spare, branch, fits in free[:6]:
                    mark = "  ← dersi verebilir" if fits else ""
                    br = f", branş: {branch}" if branch else ""
                    lines.append(f"   • {nm}: {spare} saat boş{br}{mark}")

            lines += [
                "",
                "Yerleşemeyen dersler 'Yerleştirilmeyenler' listesinde duruyor;",
                "oradan sürükleyerek elle de yerleştirebilirsiniz.",
            ]
            msg = "\n".join(lines)

            def show_capacity():
                QMessageBox.information(parent, "Çizelge Neden Dolmadı?", msg, QMessageBox.Ok)
            QTimer.singleShot(100, show_capacity)
        elif parent and total_hrs > 0:
            if hasattr(parent, "statusBar"):
                parent.statusBar().showMessage(f"Otomatik çizelge oluşturuldu! ({total_hrs}/{target_hrs} saat yerleştirildi)", 5000)

    def reject(self):
        """Çarpı / Esc / İptal.

        Motor çalışırken arayüz iş parçacığında worker.wait() ÇAĞRILMAZ: CP-SAT
        turunu bitirene kadar bloklar ve pencere donar, "kapanmıyor, çöküyor"
        görünür. Bunun yerine durdurma bayrağı kaldırılır (CP-SAT bayrağı
        saniyede beş kez yoklar ve aramayı anında keser), pencere iş parçacığı
        bitince kendiliğinden kapanır.
        """
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            if not getattr(self, "_closing", False):
                self._closing = True
                self.worker.stop()
                self.btn_start.setEnabled(False)
                self.btn_cancel.setEnabled(False)
                self.lbl_info.setText("Durduruluyor…")
                self.lbl_info.setStyleSheet("color: #B45309; font-weight: 500;")
                try:
                    self.worker.finished.connect(self._close_after_stop)
                except Exception:
                    QTimer.singleShot(300, self._close_after_stop)
            return
        super().reject()

    def _close_after_stop(self):
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            QTimer.singleShot(200, self._close_after_stop)
            return
        self._closing = False
        super().reject()

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            event.ignore()
            self.reject()
            return
        super().closeEvent(event)
