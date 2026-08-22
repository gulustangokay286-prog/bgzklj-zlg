"""
auto_schedule_dialog.py — Otomatik Yerleştirme (Apple Minimalist & BGZ Yapay Zeka Motoru)
"""
import math
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QWidget, QFrame, QScrollArea, QGraphicsDropShadowEffect,
    QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QRectF, QByteArray, QPropertyAnimation, QEasingCurve, Property, Signal
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
        
        if not self.isEnabled():
            bg_color = QColor("#E5E5EA")
        elif self._checked:
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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
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
            k = (c["teacher"], c["day"], c["period"], c["other_institution"])
            if k in seen:
                continue
            seen.add(k)
            
            c_row = QFrame()
            c_row.setStyleSheet("background: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 6px;")
            r_lay = QVBoxLayout(c_row)
            r_lay.setContentsMargins(10, 6, 10, 6)
            r_lay.setSpacing(2)
            
            lbl_t = QLabel(f"<b>{c['teacher']}</b> — {c['day']} {c['period']}. Ders Saati")
            lbl_t.setStyleSheet("font-size: 11px; color: #1D1D1F; background: transparent; border: none;")
            
            lbl_d = QLabel(f"• Diğer Kurum: <b>{c['other_institution']}</b> ({c['other_class']} - {c['other_subject']})\n• Bu Kurumdaki Hedef: <b>{c['this_class']} - {c['this_subject']}</b>")
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
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F7;
            }
            QFrame#card {
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 12px;
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
                background: #FFFFFF;
                color: #1D1D1F;
                border: 1px solid #D2D2D7;
                border-radius: 8px;
                padding: 8px 22px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton#btnCancel:hover {
                background: #F5F5F7;
            }
            QPushButton#btnStart {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0077ED, stop:1 #0071E3);
                color: #FFFFFF;
                border: 1px solid #0062C4;
                border-radius: 8px;
                padding: 8px 26px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#btnStart:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0082FB, stop:1 #0077ED);
            }
            QPushButton#btnStart:pressed {
                background: #0062C4;
            }
            QPushButton#btnStart:disabled {
                background: #E5E5EA;
                color: #8E8E93;
                border: none;
            }
        """)
        
        self._build_ui()
        self.adjustSize()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(12)
        
        # ═══ 1. SEAMLESS HEADER (Pure 3D Vector Icon + BGZ Branding) ═══
        header_lay = QHBoxLayout()
        header_lay.setContentsMargins(4, 2, 4, 4)
        header_lay.setSpacing(14)
        
        self.icon_3d = Apple3DIconWidget(self)
        header_lay.addWidget(self.icon_3d, 0, Qt.AlignVCenter)
        
        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_col.setContentsMargins(0, 0, 0, 0)
        
        lbl_title = QLabel("Otomatik Ders Programı")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1D1D1F; letter-spacing: -0.3px;")
        
        lbl_sub = QLabel("BGZ Yapay Zeka Optimizasyon Motoru")
        lbl_sub.setStyleSheet("color: #86868B; font-size: 11.5px;")
        
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_sub)
        header_lay.addLayout(title_col, 1)
        root_layout.addLayout(header_lay)
        
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
            "BGZ Optimizasyon Motoru (Yüksek Performans & Akıllı Çözücü — Önerilen)",
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
        
        row_ignore, self.sw_ignore_cross = make_switch_row(
            "Diğer Kurumları Yoksay",
            "Aynı öğretmen başka kurumda derste olsa bile bu kuruma yerleştir",
            False
        )

        p_lay.addLayout(row_vds)
        p_lay.addLayout(row_zero)
        p_lay.addLayout(row_fill)
        p_lay.addLayout(row_ignore)
        
        root_layout.addWidget(param_card)
        
        # ═══ 4. SKELETON AWAITING & LIVE PROGRESS CARD ═══
        prog_card = QFrame()
        prog_card.setObjectName("card")
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
        self.lbl_info.setText("BGZ Yapay Zeka Motoru çalışıyor (Canlı kısıt optimizasyonu)...")
        self.lbl_info.setStyleSheet("color: #0071E3; font-weight: 500;")
        
        self.icon_3d.start_pulse()
        self.skeleton.set_active(True)
        self.skeleton.set_placed_ratio(0.0)
        
        from auto_scheduler import AutoSchedulerWorker
        fill_empty = True
        chosen_target = self.cb_target_class.currentData()
        inst_slug = getattr(self.parent(), "institution_slug", None)
        use_vds = self.sw_vds.isChecked()
        
        self.worker = AutoSchedulerWorker(
            self.data_store, target_class=chosen_target, parent=self,
            fill_empty=fill_empty, institution_slug=inst_slug, use_vds=use_vds,
            infinite_mode=True,
            ignore_other_institutions=self.sw_ignore_cross.isChecked()
        )
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.iteration_updated.connect(self._on_iteration)
        self.worker.finished_successfully.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

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
        if conflicts == 0 and placed > 0:
            self.lbl_val_conf.setStyleSheet("color: #34C759; font-weight: bold; font-size: 10px;")
        else:
            self.lbl_val_conf.setStyleSheet("color: #E11D48; font-weight: bold; font-size: 10px;" if conflicts > 3 else "color: #D97706; font-weight: bold; font-size: 10px;")

    def _on_progress(self, placed, total):
        pct = int((placed / max(1, total)) * 100) if total > 0 else 100
        self.progress.setValue(pct)
        self.lbl_pct.setText(f"{pct}%")
        ratio = (placed / float(max(1, total))) if total > 0 else 1.0
        self.skeleton.set_placed_ratio(ratio)

    def _on_failed(self, err_msg):
        self.icon_3d.stop_pulse()
        self.skeleton.set_active(False)
        self.btn_start.setEnabled(True)
        self.btn_cancel.setText("Kapat")
        self.lbl_info.setText(f"Hata: {err_msg}")
        self.lbl_info.setStyleSheet("color: #DC2626; font-weight: 500;")

    def _on_finished(self, result):
        self.progress.setValue(100)
        self.lbl_pct.setText("100%")
        self.icon_3d.stop_pulse()
        self.skeleton.set_active(False)
        self.skeleton.set_placed_ratio(1.0)
        
        schedule = result.get("schedule", [])
        total_hrs = result.get("placed_hours") or sum(item.get("duration", 1) for item in schedule)
        target_hrs = result.get("total_hours", total_hrs)
        cross_conflicts = result.get("cross_conflicts", [])
        
        # If cross-institution conflicts detected, ask the user interactively
        if cross_conflicts:
            c_dlg = CrossConflictResolutionDialog(cross_conflicts, parent=self)
            ignore_and_place = (c_dlg.exec() == QDialog.Accepted)
            if not ignore_and_place:
                conflicting_keys = {(c["day_idx"], c["period_idx"], c["teacher"]) for c in cross_conflicts}
                filtered_schedule = []
                for item in schedule:
                    t = item.get("teacher_name") or item.get("teacher") or ""
                    d = item.get("day_idx") if "day_idx" in item else item.get("day", 0)
                    p = item.get("period", 0)
                    dur = int(item.get("duration", 1))
                    has_c = any((d, p + off, t) in conflicting_keys for off in range(dur))
                    if not has_c:
                        filtered_schedule.append(item)
                schedule = filtered_schedule
                total_hrs = sum(item.get("duration", 1) for item in schedule)
            
        self.data_store["auto_schedule_results"] = schedule
        # Carried through so the window can explain, right after the run, exactly why
        # any cell was left empty instead of just announcing success.
        self.data_store["auto_schedule_report"] = {
            "understaffed_slots": result.get("understaffed_slots", []),
            "unplaced_summary": result.get("unplaced_summary", []),
            "placed_real_hours": result.get("placed_real_hours", 0),
            "total_assigned_hours": result.get("total_hours", 0),
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
                color = get_subject_color(s)
                is_locked = bool(item.get("locked", False))
                new_placements.append({
                    "row": r, "col": c, "period": r, "day": c,
                    "teacher_name": t, "teacher": t,
                    "subject_name": s, "subject": s,
                    "class_name": cl, "class": cl,
                    "color": color,
                    "duration": dur,
                    "locked": is_locked,
                    "block_id": item.get("block_id", ""),
                    "is_combined": bool(item.get("is_combined", False)),
                    "is_filler": bool(item.get("is_filler", False))
                })
                
        self.data_store["grid_placements"] = new_placements
        
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
            "target_hrs": target_hrs
        }
        
        self.accept()
    
    def accept(self):
        violations = getattr(self, "_pending_violations", [])
        summary = getattr(self, "_result_summary", {})
        total_hrs = summary.get("total_hrs", 0)
        target_hrs = summary.get("target_hrs", 0)
        parent = self.parent()
        
        super().accept()
        
        if parent and violations:
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
        elif parent and total_hrs > 0:
            if hasattr(parent, "statusBar"):
                parent.statusBar().showMessage(f"Otomatik çizelge oluşturuldu! ({total_hrs}/{target_hrs} saat yerleştirildi)", 5000)

    def reject(self):
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        super().reject()
