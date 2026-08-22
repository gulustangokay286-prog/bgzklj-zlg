"""
home_dashboard.py — Apple Human Interface Guidelines (Apple HIG) Minimalist Tasarımlı Kurum & Versiyon Paneli
Sade, modern, ferah, nötr renk paleti, 3D kurum ikonları ve kristal netliğinde tipografi.
Tek bir emoji barındırmaz, tamamı modern vektörel arayüz öğeleridir.
"""
import os, sys, json
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSplitter, QInputDialog, QMessageBox,
    QLineEdit, QDialog, QCheckBox,
    QMenu, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize, QRectF, QPoint, QMimeData, QEvent
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QIcon, QPixmap,
    QPainterPath, QLinearGradient, QRadialGradient, QDrag
)

import version_store

# ── Monochrome Design Tokens (Notion / Finder Aesthetic) ─────────────
BG_CANVAS        = "#FFFFFF"  # Pure white canvas
BG_CARD          = "#FFFFFF"  # Pure white card
BG_SIDEBAR       = "#FAFAFA"  # Very light gray sidebar
BORDER_HAIRLINE  = "#E8E8E8"  # Subtle gray border
BORDER_SUBTLE    = "rgba(0, 0, 0, 0.06)"
TEXT_PRIMARY     = "#1A1A1A"  # Near-black
TEXT_SECONDARY   = "#6B6B6B"  # Medium gray
TEXT_MUTED       = "#999999"  # Light muted
APPLE_BLUE       = "#0071E3"  # Kept for backward compat in dialogs
APPLE_GREEN      = "#34C759"
APPLE_AMBER      = "#FF9500"
APPLE_RED        = "#FF3B30"
APPLE_PURPLE     = "#AF52DE"

SELECTED_BG      = "#1A1A1A"  # Dark selected state
SELECTED_TEXT    = "#FFFFFF"  # White text on selected
HOVER_BG         = "#F5F5F5"  # Hover state

FONT_FAMILY = '-apple-system, BlinkMacSystemFont, "Inter", "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif'

# ── Monochrome Institution Icon ──────────────────────────────────────

def make_3d_institution_icon(inst_name: str, color_hex: str = "#1A1A1A", size: int = 40) -> QPixmap:
    """Draws a clean monochrome outline building icon (Notion/Finder style)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    
    c = QColor(color_hex)
    pen = QPen(c, max(1.4, size * 0.05))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    
    cx = size / 2.0
    m = size * 0.12  # margin
    
    # Building body
    body_top = size * 0.25
    body_bottom = size - m
    body_left = m + size * 0.05
    body_right = size - m - size * 0.05
    body_w = body_right - body_left
    
    p.drawRect(QRectF(body_left, body_top, body_w, body_bottom - body_top))
    
    # Roof triangle
    roof = QPainterPath()
    roof.moveTo(cx, m)
    roof.lineTo(body_left - size * 0.02, body_top)
    roof.lineTo(body_right + size * 0.02, body_top)
    roof.closeSubpath()
    p.drawPath(roof)
    
    # Door
    door_w = body_w * 0.22
    door_h = (body_bottom - body_top) * 0.35
    p.drawRect(QRectF(cx - door_w / 2, body_bottom - door_h, door_w, door_h))
    
    # Windows (2x2 grid)
    win_w = body_w * 0.16
    win_h = (body_bottom - body_top) * 0.16
    win_y1 = body_top + (body_bottom - body_top) * 0.18
    win_y2 = body_top + (body_bottom - body_top) * 0.45
    win_x1 = body_left + body_w * 0.15
    win_x2 = body_right - body_w * 0.15 - win_w
    
    for wy in [win_y1, win_y2]:
        for wx in [win_x1, win_x2]:
            p.drawRect(QRectF(wx, wy, win_w, win_h))
    
    p.end()
    return pix


def make_apple_lock_badge(size: int = 44) -> QPixmap:
    """Draws a modern Apple-style 3D security lock badge."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    
    # Gradient circle base
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#387EF5"))
    grad.setColorAt(1.0, QColor("#0051C7"))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(QRectF(2, 2, size - 4, size - 4), size / 2, size / 2)
    
    # White shackle (arch)
    mid_x = size / 2.0
    shackle_pen = QPen(QColor("#FFFFFF"), 2.6)
    shackle_pen.setCapStyle(Qt.RoundCap)
    p.setPen(shackle_pen)
    p.setBrush(Qt.NoBrush)
    shackle_rect = QRectF(mid_x - 5.5, 11, 11, 12)
    p.drawArc(shackle_rect, 0 * 16, 180 * 16)
    p.drawLine(mid_x - 5.5, 17, mid_x - 5.5, 20)
    p.drawLine(mid_x + 5.5, 17, mid_x + 5.5, 20)
    
    # White body
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(QRectF(mid_x - 8, 19, 16, 13), 3, 3)
    
    # Keyhole
    p.setBrush(QBrush(QColor("#0051C7")))
    p.drawEllipse(QRectF(mid_x - 1.8, 22.5, 3.6, 3.6))
    p.drawRect(QRectF(mid_x - 1, 24.5, 2, 4))
    
    p.end()
    return pix

# ── Dialogs: Password Prompt, Set Password & Modern Apple White Alerts ─

class PasswordOverlayContainer(QWidget):
    """Clean opaque background styled purely via CSS – no paintEvent override."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: #F8FAFC;")

class PasswordCardWidget(QFrame):
    """Pure white Apple style security card styled via CSS – no paintEvent/QPainter to avoid macOS Cocoa black-box bug."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            PasswordCardWidget {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 16px;
            }
        """)

class AppleInfoDialog(QDialog):
    def __init__(self, title: str, message: str, is_success: bool = True, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(400, 230)
        # NoDropShadowWindowHint: on macOS a frameless + translucent window still gets a
        # native Cocoa shadow layer, and that layer is what paints as an opaque black
        # rectangle when the compositor cannot resolve the window's alpha. The in-app
        # QGraphicsDropShadowEffects were removed for this same symptom; this is the
        # remaining shadow source. The cards draw their own border, so nothing is lost.
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        container = QWidget(self)
        container.setObjectName("infoCard")
        container.setStyleSheet("""
            #infoCard {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 16px;
            }
        """)
        
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(24, 20, 24, 20)
        c_lay.setSpacing(10)
        c_lay.setAlignment(Qt.AlignCenter)
        
        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setPixmap(make_dashboard_icon("check" if is_success else "info", color_hex="#0071E3" if is_success else "#FF3B30", size=36))
        c_lay.addWidget(icon_lbl)
        
        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        t_lbl.setStyleSheet("color: #1D1D1F; font-weight: bold; background: transparent; border: none;")
        t_lbl.setAlignment(Qt.AlignCenter)
        c_lay.addWidget(t_lbl)
        
        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont("Segoe UI", 9.5))
        msg_lbl.setStyleSheet("color: #636366; background: transparent; border: none;")
        msg_lbl.setAlignment(Qt.AlignCenter)
        msg_lbl.setWordWrap(True)
        c_lay.addWidget(msg_lbl)
        
        btn_ok = QPushButton("Tamam")
        btn_ok.setFixedSize(130, 34)
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #0062C4;
            }
        """)
        btn_ok.clicked.connect(self.accept)
        
        h_lay = QHBoxLayout()
        h_lay.addStretch(1)
        h_lay.addWidget(btn_ok)
        h_lay.addStretch(1)
        c_lay.addLayout(h_lay)
        
        layout.addWidget(container)

class AppleConfirmDialog(QDialog):
    def __init__(self, title: str, message: str, confirm_text: str = "Onayla", cancel_text: str = "Vazgeç", is_destructive: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(430, 260)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        container = QWidget(self)
        container.setObjectName("confirmCard")
        container.setStyleSheet("""
            #confirmCard {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 16px;
            }
        """)
        
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(28, 22, 28, 22)
        c_lay.setSpacing(12)
        c_lay.setAlignment(Qt.AlignCenter)
        
        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setPixmap(make_dashboard_icon("warning" if is_destructive else "info", color_hex="#FF3B30" if is_destructive else "#0071E3", size=38))
        c_lay.addWidget(icon_lbl)
        
        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Segoe UI", 12.5, QFont.Bold))
        t_lbl.setStyleSheet("color: #1D1D1F; font-weight: bold; background: transparent; border: none;")
        t_lbl.setAlignment(Qt.AlignCenter)
        c_lay.addWidget(t_lbl)
        
        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont("Segoe UI", 9.5))
        msg_lbl.setStyleSheet("color: #636366; background: transparent; border: none;")
        msg_lbl.setAlignment(Qt.AlignCenter)
        msg_lbl.setWordWrap(True)
        msg_lbl.setMinimumHeight(44)
        c_lay.addWidget(msg_lbl)
        
        c_lay.addSpacing(4)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        
        btn_cancel = QPushButton(cancel_text)
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F2F2F7; color: #1D1D1F; border: 1px solid #E5E5EA;
                border-radius: 8px; padding: 6px 20px; font-weight: 500; font-size: 12px;
            }
            QPushButton:hover { background: #E5E5EA; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        btn_ok = QPushButton(confirm_text)
        btn_ok.setFixedHeight(36)
        btn_ok.setCursor(Qt.PointingHandCursor)
        bg_col = "#FF3B30" if is_destructive else "#0071E3"
        hover_col = "#DC2626" if is_destructive else "#0062C4"
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background: {bg_col}; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 6px 22px; font-weight: 600; font-size: 12px;
            }}
            QPushButton:hover {{ background: {hover_col}; }}
        """)
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)
        
        c_lay.addLayout(btn_box)
        layout.addWidget(container)


class AppleColorPickerDialog(QDialog):
    def __init__(self, current_color="#0071E3", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kurum Rengi Seç")
        self.setFixedSize(360, 200)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.selected_color = current_color
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        container = QWidget(self)
        container.setObjectName("colorCard")
        container.setStyleSheet("""
            #colorCard {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 16px;
            }
        """)
        
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(24, 20, 24, 20)
        c_lay.setSpacing(14)
        
        t_lbl = QLabel("Kurum Rengi Seç")
        t_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        t_lbl.setStyleSheet("color: #1D1D1F; background: transparent; border: none;")
        c_lay.addWidget(t_lbl)
        
        color_row = QHBoxLayout()
        color_row.setSpacing(10)
        self.color_btns = []
        palette = [
            ("#0071E3", "Mavi"),
            ("#34C759", "Yeşil"),
            ("#5856D6", "İndigo"),
            ("#FF9500", "Turuncu"),
            ("#FF3B30", "Kırmızı"),
            ("#30B0C7", "Turkuaz"),
            ("#AF52DE", "Mor"),
        ]
        for hex_code, label in palette:
            btn = QPushButton()
            btn.setFixedSize(30, 30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(label)
            is_sel = (hex_code == self.selected_color)
            btn.setStyleSheet(self._color_btn_style(hex_code, is_sel))
            btn.clicked.connect(lambda _, c=hex_code: self._set_color(c))
            color_row.addWidget(btn)
            self.color_btns.append((btn, hex_code))
        color_row.addStretch(1)
        c_lay.addLayout(color_row)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        
        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFixedHeight(34)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F2F2F7; color: #1D1D1F; border: 1px solid #E5E5EA;
                border-radius: 8px; padding: 6px 16px; font-weight: 500;
            }
            QPushButton:hover { background: #E5E5EA; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        btn_ok = QPushButton("Kaydet")
        btn_ok.setFixedHeight(34)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 6px 20px; font-weight: 600;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)
        
        c_lay.addLayout(btn_box)
        layout.addWidget(container)
        
    def _color_btn_style(self, hex_code: str, is_selected: bool) -> str:
        if is_selected:
            return f"background: {hex_code}; border: 3px solid #1D1D1F; border-radius: 15px;"
        else:
            return f"background: {hex_code}; border: 2px solid #FFFFFF; border-radius: 15px;"
            
    def _set_color(self, hex_code: str):
        self.selected_color = hex_code
        for btn, c in self.color_btns:
            btn.setStyleSheet(self._color_btn_style(c, c == hex_code))
            
    def get_color(self):
        return self.selected_color


def show_apple_info(parent, title: str, message: str, is_success: bool = True):
    dlg = AppleInfoDialog(title, message, is_success=is_success, parent=parent)
    dlg.exec()


class AppleNewInstitutionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Eğitim Kurumu Ekle")
        self.setFixedSize(500, 480)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.selected_color = "#0071E3"
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        container = QWidget(self)
        container.setObjectName("modalCard")
        container.setStyleSheet("""
            #modalCard {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 20px;
            }
        """)
        
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(32, 28, 32, 28)
        c_lay.setSpacing(14)
        
        # Header Row with 3D Icon & Title
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(16)
        
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(48, 48)
        self._update_icon_preview()
        hdr_row.addWidget(self.icon_preview)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        
        t_lbl = QLabel("Yeni Eğitim Kurumu Ekle")
        t_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        t_lbl.setStyleSheet("color: #1D1D1F; background: transparent; border: none;")
        title_box.addWidget(t_lbl)
        
        sub_lbl = QLabel("Bağımsız ders çizelgeleri ve versiyon alanı tanımlayın.")
        sub_lbl.setFont(QFont("Segoe UI", 9))
        sub_lbl.setStyleSheet("color: #86868B; background: transparent; border: none;")
        title_box.addWidget(sub_lbl)
        
        hdr_row.addLayout(title_box, 1)
        c_lay.addLayout(hdr_row)
        
        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: #E5E5EA; border: none;")
        c_lay.addWidget(div)
        
        # Field 1: Name
        name_title = QLabel("KURUM ADI *")
        name_title.setFont(QFont("Segoe UI", 8, QFont.Bold))
        name_title.setStyleSheet("color: #86868B; letter-spacing: 0.5px; background: transparent; border: none;")
        c_lay.addWidget(name_title)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Örn: Boğaziçi Eğitim Kurumları, Birey Kurs...")
        self.name_edit.setFixedHeight(38)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background: #F8FAFC;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 13px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border: 1.5px solid #0071E3;
                background: #FFFFFF;
            }
        """)
        self.name_edit.textChanged.connect(self._on_name_changed)
        c_lay.addWidget(self.name_edit)
        
        # Field 2: Color Picker
        color_title = QLabel("TEMA RENGİ")
        color_title.setFont(QFont("Segoe UI", 8, QFont.Bold))
        color_title.setStyleSheet("color: #86868B; letter-spacing: 0.5px; background: transparent; border: none;")
        c_lay.addWidget(color_title)
        
        color_row = QHBoxLayout()
        color_row.setSpacing(10)
        self.color_btns = []
        palette = [
            ("#0071E3", "Mavi"),
            ("#34C759", "Yeşil"),
            ("#5856D6", "İndigo"),
            ("#FF9500", "Turuncu"),
            ("#FF3B30", "Kırmızı"),
            ("#30B0C7", "Turkuaz"),
            ("#AF52DE", "Mor"),
        ]
        for hex_code, label in palette:
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(label)
            is_sel = (hex_code == self.selected_color)
            btn.setStyleSheet(self._color_btn_style(hex_code, is_sel))
            btn.clicked.connect(lambda _, c=hex_code: self._set_color(c))
            color_row.addWidget(btn)
            self.color_btns.append((btn, hex_code))
        color_row.addStretch(1)
        c_lay.addLayout(color_row)
        
        # Field 3: Password (Optional)
        pwd_title = QLabel("GÜVENLİK / ERİŞİM ŞİFRESİ (İSTEĞE BAĞLI)")
        pwd_title.setFont(QFont("Segoe UI", 8, QFont.Bold))
        pwd_title.setStyleSheet("color: #86868B; letter-spacing: 0.5px; background: transparent; border: none;")
        c_lay.addWidget(pwd_title)
        
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.pwd_edit.setPlaceholderText("Şifresiz bırakmak için boş geçin...")
        self.pwd_edit.setFixedHeight(38)
        self.pwd_edit.setStyleSheet("""
            QLineEdit {
                background: #F8FAFC;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 13px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border: 1.5px solid #0071E3;
                background: #FFFFFF;
            }
        """)
        c_lay.addWidget(self.pwd_edit)
        
        # Bottom Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        
        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setFont(QFont("Segoe UI", 9.5))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F2F2F7; color: #1D1D1F; border: 1px solid #E5E5EA;
                border-radius: 8px; padding: 6px 20px; font-weight: 500;
            }
            QPushButton:hover { background: #E5E5EA; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        self.btn_create = QPushButton("+ Kurumu Oluştur")
        self.btn_create.setFixedHeight(38)
        self.btn_create.setFont(QFont("Segoe UI", 9.5, QFont.Bold))
        self.btn_create.setCursor(Qt.PointingHandCursor)
        self.btn_create.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 6px 26px; font-weight: 600;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        self.btn_create.clicked.connect(self._validate_and_accept)
        btn_box.addWidget(self.btn_create)
        
        c_lay.addLayout(btn_box)
        layout.addWidget(container)
        
        self.name_edit.returnPressed.connect(self._validate_and_accept)
        self.pwd_edit.returnPressed.connect(self._validate_and_accept)
        
    def _color_btn_style(self, hex_code: str, is_selected: bool) -> str:
        if is_selected:
            return f"background: {hex_code}; border: 3px solid #1D1D1F; border-radius: 14px;"
        else:
            return f"background: {hex_code}; border: 2px solid #FFFFFF; border-radius: 14px;"
            
    def _set_color(self, hex_code: str):
        self.selected_color = hex_code
        for btn, c in self.color_btns:
            btn.setStyleSheet(self._color_btn_style(c, c == hex_code))
        self._update_icon_preview()
        
    def _on_name_changed(self, text):
        self._update_icon_preview()
        
    def _update_icon_preview(self):
        text = self.name_edit.text() if hasattr(self, "name_edit") else ""
        name = text.strip() or "Kurum"
        pix = make_3d_institution_icon(name, self.selected_color, 48)
        self.icon_preview.setPixmap(pix)
        
    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            self.name_edit.setStyleSheet("""
                QLineEdit {
                    background: #FEF2F2;
                    border: 1.5px solid #EF4444;
                    border-radius: 8px;
                    padding: 4px 12px;
                    font-size: 13px;
                    color: #0F172A;
                }
            """)
            self.name_edit.setFocus()
            return
        self.accept()
        
    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "color": self.selected_color,
            "password": self.pwd_edit.text().strip(),
        }


class AppleInputDialog(QDialog):
    def __init__(self, title: str, label: str, default_text: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(380, 200)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        container = QWidget(self)
        container.setObjectName("inputCard")
        container.setStyleSheet("""
            #inputCard {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 16px;
            }
        """)
        
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(24, 20, 24, 20)
        c_lay.setSpacing(12)
        
        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        t_lbl.setStyleSheet("color: #1D1D1F; background: transparent; border: none;")
        c_lay.addWidget(t_lbl)
        
        msg_lbl = QLabel(label)
        msg_lbl.setFont(QFont("Segoe UI", 9.5))
        msg_lbl.setStyleSheet("color: #86868B; background: transparent; border: none;")
        c_lay.addWidget(msg_lbl)
        
        self.edit = QLineEdit(default_text)
        self.edit.setFixedHeight(36)
        self.edit.setStyleSheet("""
            QLineEdit {
                background: #F8FAFC;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 13px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border: 1.5px solid #0071E3;
                background: #FFFFFF;
            }
        """)
        c_lay.addWidget(self.edit)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        
        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFixedHeight(34)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F2F2F7; color: #1D1D1F; border: 1px solid #E5E5EA;
                border-radius: 8px; padding: 6px 16px; font-weight: 500;
            }
            QPushButton:hover { background: #E5E5EA; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        btn_ok = QPushButton("Tamam")
        btn_ok.setFixedHeight(34)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 6px 20px; font-weight: 600;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)
        
        c_lay.addLayout(btn_box)
        layout.addWidget(container)
        self.edit.returnPressed.connect(self.accept)
        
    def text_value(self):
        return self.edit.text().strip()


class PasswordPromptDialog(QDialog):
    def __init__(self, inst_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kurum Şifresi")
        self.setFixedSize(400, 250)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
            QLabel {
                background: transparent;
                color: #0F172A;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        
        title_lbl = QLabel(f"Korumalı Kurum: {inst_name}")
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title_lbl.setStyleSheet("color: #0F172A; font-weight: bold;")
        layout.addWidget(title_lbl)
        
        sub_lbl = QLabel("Bu kurum şifre ile korunmaktadır. Lütfen erişim şifresini girin:")
        sub_lbl.setFont(QFont("Segoe UI", 9.5))
        sub_lbl.setStyleSheet("color: #64748B;")
        sub_lbl.setWordWrap(True)
        layout.addWidget(sub_lbl)
        
        self.input_pwd = QLineEdit()
        self.input_pwd.setEchoMode(QLineEdit.Password)
        self.input_pwd.setPlaceholderText("Şifre...")
        self.input_pwd.setFixedHeight(36)
        self.input_pwd.setStyleSheet("""
            QLineEdit {
                background: #F8FAFC;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 13px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border: 1.5px solid #0071E3;
                background: #FFFFFF;
            }
        """)
        layout.addWidget(self.input_pwd)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        
        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFont(QFont("Segoe UI", 9.5))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setFixedHeight(34)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F1F5F9;
                color: #334155;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 6px 18px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #E2E8F0;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        btn_ok = QPushButton("Giriş Yap")
        btn_ok.setFont(QFont("Segoe UI", 9.5, QFont.Bold))
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setFixedHeight(34)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 6px 22px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #0056B3;
            }
        """)
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)
        
        layout.addLayout(btn_box)
        self.input_pwd.returnPressed.connect(self.accept)
        
    def get_password(self):
        return self.input_pwd.text().strip()


class SetPasswordDialog(QDialog):
    def __init__(self, inst_name, has_current=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kurum Şifresi Yönetimi")
        self.setFixedSize(420, 270)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
            QLabel {
                background: transparent;
                color: #0F172A;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        
        title_lbl = QLabel(f"{inst_name} — Şifre Ayarı")
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title_lbl.setStyleSheet("color: #0F172A; font-weight: bold;")
        layout.addWidget(title_lbl)
        
        sub_lbl = QLabel("Kuruma erişimi kısıtlamak için bir şifre belirleyin. Boş bırakıp kaydederseniz şifre kaldırılır.")
        sub_lbl.setFont(QFont("Segoe UI", 9.5))
        sub_lbl.setStyleSheet("color: #64748B;")
        sub_lbl.setWordWrap(True)
        layout.addWidget(sub_lbl)
        
        self.input_pwd = QLineEdit()
        self.input_pwd.setEchoMode(QLineEdit.Password)
        self.input_pwd.setPlaceholderText("Yeni Şifre (boş = şifresiz)...")
        self.input_pwd.setFixedHeight(36)
        self.input_pwd.setStyleSheet("""
            QLineEdit {
                background: #F8FAFC;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 13px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border: 1.5px solid #0071E3;
                background: #FFFFFF;
            }
        """)
        layout.addWidget(self.input_pwd)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        
        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFont(QFont("Segoe UI", 9.5))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setFixedHeight(34)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F1F5F9;
                color: #334155;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 6px 18px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #E2E8F0;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        btn_ok = QPushButton("Kaydet")
        btn_ok.setFont(QFont("Segoe UI", 9.5, QFont.Bold))
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setFixedHeight(34)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 6px 22px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #0056B3;
            }
        """)
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)
        
        layout.addLayout(btn_box)
        
    def get_password(self):
        return self.input_pwd.text().strip()


# ── Dialog: Cross Institution Import ─────────────────────────────────

class CrossImportDialog(QDialog):
    def __init__(self, current_slug, parent=None):
        super().__init__(parent)
        self.current_slug = current_slug
        self.setWindowTitle("Diğer Kurumdan Veri Aktar")
        self.setFixedSize(480, 420)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG_CARD}; border-radius: 14px; font-family: {FONT_FAMILY}; }}
            QLabel {{ color: {TEXT_PRIMARY}; }}
            QCheckBox {{ color: {TEXT_PRIMARY}; font-size: 12px; spacing: 8px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 1.5px solid {BORDER_HAIRLINE}; background: #F5F5F7; }}
            QCheckBox::indicator:checked {{ background: {APPLE_BLUE}; border-color: {APPLE_BLUE}; image: none; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        
        title_lbl = QLabel("Kurumlar Arası Veri Aktarımı")
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        layout.addWidget(title_lbl)
        
        sub_lbl = QLabel("Başka bir kurumun tanımlarını (ders, sınıf, derslik, öğretmen ve atamalar) bağımsız olarak bu kuruma kopyalayabilirsiniz. Çizelge yerleşimleri kopyalanmaz.")
        sub_lbl.setFont(QFont("Segoe UI", 9))
        sub_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        sub_lbl.setWordWrap(True)
        layout.addWidget(sub_lbl)
        
        # Source institution dropdown
        from PySide6.QtWidgets import QComboBox
        self.combo_source = QComboBox()
        self.combo_source.setStyleSheet(f"""
            QComboBox {{
                background: #F5F5F7; border: 1px solid {BORDER_HAIRLINE};
                border-radius: 8px; padding: 8px 12px; font-size: 13px; color: {TEXT_PRIMARY};
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        
        institutions = version_store.list_institutions()
        for inst in institutions:
            if inst["slug"] != current_slug:
                self.combo_source.addItem(f"{inst['name']} ({inst['version_count']} versiyon)", inst["slug"])
                
        if self.combo_source.count() == 0:
            self.combo_source.addItem("Aktarılacak başka kurum bulunamadı", "")
            self.combo_source.setEnabled(False)
            
        layout.addWidget(QLabel("Kaynak Kurum:"))
        layout.addWidget(self.combo_source)
        
        # Checkboxes
        layout.addWidget(QLabel("Aktarılacak Veri Tipleri:"))
        cb_box = QVBoxLayout()
        cb_box.setSpacing(8)
        
        self.cb_subjs = QCheckBox("Dersler (Ad, Kod, Renk)")
        self.cb_subjs.setChecked(True)
        cb_box.addWidget(self.cb_subjs)
        
        self.cb_classes = QCheckBox("Sınıflar (Şubeler, Seviyeler)")
        self.cb_classes.setChecked(True)
        cb_box.addWidget(self.cb_classes)
        
        self.cb_rooms = QCheckBox("Derslikler (Laboratuvar, Atölye vb.)")
        self.cb_rooms.setChecked(True)
        cb_box.addWidget(self.cb_rooms)
        
        self.cb_teachers = QCheckBox("Öğretmenler (Branş, Kısıtlamalar)")
        self.cb_teachers.setChecked(True)
        cb_box.addWidget(self.cb_teachers)
        
        self.cb_assignments = QCheckBox("Ders - Öğretmen Atamaları (Haftalık Dağıtımlar)")
        self.cb_assignments.setChecked(True)
        cb_box.addWidget(self.cb_assignments)
        
        layout.addLayout(cb_box)
        layout.addStretch(1)
        
        # Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        
        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFont(QFont("Segoe UI", 9))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: #E5E5EA; color: {TEXT_PRIMARY}; border: none;
                border-radius: 8px; padding: 8px 16px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #D1D1D6; }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        self.btn_import = QPushButton("Verileri İçe Aktar")
        self.btn_import.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.setEnabled(self.combo_source.isEnabled())
        self.btn_import.setStyleSheet(f"""
            QPushButton {{
                background: {APPLE_BLUE}; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 8px 20px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #0062C4; }}
            QPushButton:disabled {{ background: #C7C7CC; color: #8E8E93; }}
        """)
        self.btn_import.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_import)
        
        layout.addLayout(btn_box)
        
    def get_selection(self):
        src_slug = self.combo_source.currentData()
        return {
            "source_slug": src_slug,
            "subjects": self.cb_subjs.isChecked(),
            "classes": self.cb_classes.isChecked(),
            "rooms": self.cb_rooms.isChecked(),
            "teachers": self.cb_teachers.isChecked(),
            "assignments": self.cb_assignments.isChecked(),
        }


# ── Elided Label (Auto Truncate with Ellipsis) ───────────────────────

class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setToolTip(text)
        
    def setText(self, text):
        self._full_text = text
        self.setToolTip(text)
        super().setText(text)
        self.update()
        
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self._full_text, Qt.ElideRight, max(10, self.width()))
        p.setPen(self.palette().color(self.foregroundRole()))
        p.drawText(self.rect(), self.alignment() if self.alignment() else (Qt.AlignLeft | Qt.AlignVCenter), elided)


# ── Apple Institution List Item ──────────────────────────────────────

class AppleInstitutionCard(QFrame):
    clicked = Signal(str)
    double_clicked = Signal(str)  # slug
    
    def __init__(self, inst_data, is_selected=False, is_master_admin=True, parent=None):
        super().__init__(parent)
        self.inst_data = inst_data
        self.slug = inst_data["slug"]
        self.inst_name = inst_data["name"]
        self.inst_color = inst_data.get("color", "#1A1A1A")
        self.has_password = inst_data.get("has_password", False)
        self.is_primary = bool(inst_data.get("is_primary", False))
        self._selected = is_selected
        self.is_master_admin = is_master_admin
        
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(62)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        
        # Monochrome outline building icon
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(32, 32)
        layout.addWidget(self.icon_lbl)
        
        # Text Info
        t_layout = QVBoxLayout()
        t_layout.setSpacing(2)
        t_layout.setContentsMargins(0, 0, 0, 0)
        
        self.name_lbl = ElidedLabel(self.inst_name)
        self.name_lbl.setFont(QFont(FONT_FAMILY, 10, QFont.DemiBold))
        t_layout.addWidget(self.name_lbl)
        
        v_count = inst_data.get("version_count", 0)
        upd = inst_data.get("last_updated_str", "")
        sub_text = f"{v_count} versiyon • {upd}" if upd else f"{v_count} versiyon"
        self.sub_lbl = QLabel(sub_text)
        self.sub_lbl.setFont(QFont(FONT_FAMILY, 8.5))
        t_layout.addWidget(self.sub_lbl)
        
        layout.addLayout(t_layout, 1)
        self._update_style()
    
    def _update_style(self):
        if self._selected:
            self.setStyleSheet("""
                AppleInstitutionCard {
                    background: #F4F4F6;
                    border: 1px solid #E5E5E8;
                    border-radius: 8px;
                }
            """)
            self.name_lbl.setStyleSheet("color: #111111; font-weight: bold; background: transparent; border: none;")
            self.sub_lbl.setStyleSheet("color: #777777; background: transparent; border: none;")
            self.icon_lbl.setPixmap(make_3d_institution_icon(self.inst_name, "#111111", 28))
        else:
            self.setStyleSheet("""
                AppleInstitutionCard {
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 8px;
                }
                AppleInstitutionCard:hover {
                    background: #F8F8F9;
                    border: 1px solid #EFEFEF;
                }
            """)
            self.name_lbl.setStyleSheet("color: #333333; font-weight: 500; background: transparent; border: none;")
            self.sub_lbl.setStyleSheet("color: #999999; background: transparent; border: none;")
            self.icon_lbl.setPixmap(make_3d_institution_icon(self.inst_name, "#666666", 28))
            
    def set_selected(self, selected):
        self._selected = selected
        self._update_style()
        self._update_style()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.slug)
        super().mousePressEvent(event)
        
    def _context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: #FFFFFF; border: 1px solid {BORDER_HAIRLINE};
                border-radius: 8px; padding: 4px; font-size: 12px; font-family: {FONT_FAMILY};
            }}
            QMenu::item {{ padding: 6px 18px; border-radius: 4px; }}
            QMenu::item:selected {{ background: #EBF5FF; color: {APPLE_BLUE}; }}
        """)
        
        act_primary = None
        if not self.is_primary:
            act_primary = menu.addAction("⭐ Ana Kurum Olarak Ayarla")
        else:
            act_primary_dis = menu.addAction("★ Ana Kurum (Varsayılan)")
            act_primary_dis.setEnabled(False)
        menu.addSeparator()
            
        act_rename = menu.addAction("Yeniden Adlandır")
        act_color = menu.addAction("Renk Değiştir")
        
        menu.addSeparator()
        if self.has_password:
            act_pwd = menu.addAction("Şifreyi Değiştir")
            act_rm_pwd = menu.addAction("Şifreyi Kaldır")
        else:
            act_pwd = menu.addAction("Şifre Belirle (Yönetici)")
            act_rm_pwd = None
            
        menu.addSeparator()
        act_delete = menu.addAction("Kurumu Sil")
        
        action = menu.exec_(self.mapToGlobal(pos))
        if act_primary and action == act_primary:
            version_store.set_primary_institution(self.slug)
            show_apple_info(self, "Ana Kurum Güncellendi", f"'{self.inst_name}' varsayılan ana kurum olarak ayarlandı.", is_success=True)
            self._notify_parent_refresh()
        elif act_rename and action == act_rename:
            dlg = AppleInputDialog("Kurum Adı", "Yeni kurum adı:", default_text=self.inst_name, parent=self)
            if dlg.exec() == QDialog.Accepted and dlg.text_value():
                new_name = dlg.text_value()
                from save_dialog import run_apple_save_sequence
                run_apple_save_sequence(self, duration_seconds=0.25, title="Güncelleniyor", message=f"Kurum adı '{new_name}' olarak kaydediliyor...")
                version_store.rename_institution(self.slug, new_name)
                self._notify_parent_refresh()
        elif action == act_color:
            dlg = AppleColorPickerDialog(current_color=self.inst_color, parent=self)
            if dlg.exec() == QDialog.Accepted:
                new_color = dlg.get_color()
                if new_color:
                    version_store.set_institution_color(self.slug, new_color)
                    self._notify_parent_refresh()
        elif act_pwd and action == act_pwd:
            dlg = SetPasswordDialog(self.inst_name, has_current=self.has_password, parent=self)
            if dlg.exec() == QDialog.Accepted:
                pwd = dlg.get_password()
                version_store.set_institution_password(self.slug, pwd)
                show_apple_info(self, "Bilgi", "Kurum şifresi başarıyla güncellendi.", is_success=True)
                self._notify_parent_refresh()
        elif act_rm_pwd and action == act_rm_pwd:
            version_store.remove_institution_password(self.slug)
            show_apple_info(self, "Bilgi", "Kurum şifresi kaldırıldı.", is_success=True)
            self._notify_parent_refresh()
        elif action == act_delete:
            dlg = AppleConfirmDialog(
                title="Kurumu Sil",
                message=f"'{self.inst_name}' kurumunu ve tüm versiyonlarını silmek istediğinize emin misiniz? Bu işlem geri alınamaz.",
                confirm_text="Kurumu Sil",
                cancel_text="Vazgeç",
                is_destructive=True,
                parent=self
            )
            if dlg.exec() == QDialog.Accepted:
                from save_dialog import run_apple_save_sequence
                run_apple_save_sequence(self, duration_seconds=0.25, title="Kurum Siliniyor", message=f"'{self.inst_name}' sistemden kaldırılıyor...")
                version_store.delete_institution(self.slug)
                self._notify_parent_refresh(deleted_slug=self.slug)
                
    def _notify_parent_refresh(self, deleted_slug=None):
        p = self.parent()
        while p:
            if hasattr(p, "_refresh_institutions"):
                if deleted_slug and getattr(p, "_selected_slug", None) == deleted_slug:
                    p._selected_slug = None
                p._refresh_institutions()
                break
            p = p.parent() if hasattr(p, "parent") and callable(p.parent) else None


# ── Vector Dashboard Icons ───────────────────────────────────────────

def make_dashboard_icon(name: str, color_hex: str = "#0071E3", size: int = 18) -> QPixmap:
    """Draws crisp, minimalist Apple-style vector iconography without relying on emojis."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    c = QColor(color_hex)
    
    if name == "active":
        # Green Shield / Circle Check
        p.setBrush(QBrush(c))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(1, 1, size - 2, size - 2))
        p.setPen(QPen(Qt.white, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        path = QPainterPath()
        path.moveTo(size * 0.28, size * 0.52)
        path.lineTo(size * 0.45, size * 0.68)
        path.lineTo(size * 0.73, size * 0.34)
        p.drawPath(path)
    elif name == "warning":
        # Apple Warning Triangle
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c))
        path = QPainterPath()
        path.moveTo(size / 2.0, 2)
        path.lineTo(size - 2, size - 3)
        path.lineTo(2, size - 3)
        path.closeSubpath()
        p.drawPath(path)
        p.setPen(QPen(Qt.white, 2.0, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(int(size / 2.0), int(size * 0.38), int(size / 2.0), int(size * 0.60))
        p.drawPoint(int(size / 2.0), int(size * 0.76))
    elif name in ("history", "archive"):
        # Clock / Archive circle
        p.setPen(QPen(c, 1.8))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(2, 2, size - 4, size - 4))
        p.drawLine(int(size / 2), int(size / 2), int(size / 2), int(size * 0.28))
        p.drawLine(int(size / 2), int(size / 2), int(size * 0.72), int(size / 2))
    elif name == "folder":
        p.setBrush(QBrush(c))
        p.setPen(Qt.NoPen)
        path = QPainterPath()
        path.moveTo(2, 5)
        path.lineTo(size * 0.45, 5)
        path.lineTo(size * 0.55, 7.5)
        path.lineTo(size - 2, 7.5)
        path.lineTo(size - 2, size - 3)
        path.lineTo(2, size - 3)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "chevron_down":
        p.setPen(QPen(c, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawLine(int(size * 0.25), int(size * 0.38), int(size * 0.5), int(size * 0.65))
        p.drawLine(int(size * 0.5), int(size * 0.65), int(size * 0.75), int(size * 0.38))
    elif name == "chevron_right":
        p.setPen(QPen(c, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawLine(int(size * 0.38), int(size * 0.25), int(size * 0.65), int(size * 0.5))
        p.drawLine(int(size * 0.65), int(size * 0.5), int(size * 0.38), int(size * 0.75))
    elif name == "edit":
        # Pencil
        p.setPen(QPen(c, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(size * 0.18, size * 0.82)
        path.lineTo(size * 0.22, size * 0.62)
        path.lineTo(size * 0.65, size * 0.19)
        path.lineTo(size * 0.81, size * 0.35)
        path.lineTo(size * 0.38, size * 0.78)
        path.closeSubpath()
        p.drawPath(path)
        p.setBrush(QBrush(c))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(size * 0.15, size * 0.77, size * 0.1, size * 0.1))
    elif name == "trash":
        p.setPen(QPen(c, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawLine(int(size * 0.22), int(size * 0.28), int(size * 0.78), int(size * 0.28))
        p.drawLine(int(size * 0.38), int(size * 0.28), int(size * 0.42), int(size * 0.16))
        p.drawLine(int(size * 0.42), int(size * 0.16), int(size * 0.58), int(size * 0.16))
        p.drawLine(int(size * 0.58), int(size * 0.16), int(size * 0.62), int(size * 0.28))
        path = QPainterPath()
        path.moveTo(size * 0.28, size * 0.34)
        path.lineTo(size * 0.32, size * 0.86)
        path.lineTo(size * 0.68, size * 0.86)
        path.lineTo(size * 0.72, size * 0.34)
        p.drawPath(path)
        p.drawLine(int(size * 0.42), int(size * 0.42), int(size * 0.44), int(size * 0.78))
        p.drawLine(int(size * 0.58), int(size * 0.42), int(size * 0.56), int(size * 0.78))
    elif name == "three_dots":
        # Horizontal three dots menu (⋯)
        p.setBrush(QBrush(c))
        p.setPen(Qt.NoPen)
        dot_r = max(1.5, size * 0.09)
        cy = size / 2.0
        for dx in [0.25, 0.5, 0.75]:
            p.drawEllipse(QRectF(size * dx - dot_r, cy - dot_r, dot_r * 2, dot_r * 2))
    elif name == "gear":
        # Settings gear icon
        p.setPen(QPen(c, max(1.4, size * 0.08)))
        p.setBrush(Qt.NoBrush)
        cx, cy = size / 2.0, size / 2.0
        r_outer = size * 0.38
        r_inner = size * 0.22
        import math
        # Draw circle
        p.drawEllipse(QRectF(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2))
        # Draw teeth
        for i in range(6):
            angle = i * 60 * math.pi / 180
            x1 = cx + r_inner * 0.9 * math.cos(angle)
            y1 = cy + r_inner * 0.9 * math.sin(angle)
            x2 = cx + r_outer * math.cos(angle)
            y2 = cy + r_outer * math.sin(angle)
            p.drawLine(int(x1), int(y1), int(x2), int(y2))
    elif name == "document":
        # Document/file icon outline
        p.setPen(QPen(c, max(1.2, size * 0.07)))
        p.setBrush(Qt.NoBrush)
        m = size * 0.18
        fold = size * 0.25
        path = QPainterPath()
        path.moveTo(m, m)
        path.lineTo(size - m - fold, m)
        path.lineTo(size - m, m + fold)
        path.lineTo(size - m, size - m)
        path.lineTo(m, size - m)
        path.closeSubpath()
        p.drawPath(path)
        # Fold triangle
        p.drawLine(int(size - m - fold), int(m), int(size - m - fold), int(m + fold))
        p.drawLine(int(size - m - fold), int(m + fold), int(size - m), int(m + fold))
    elif name == "folder_outline":
        # Outline folder icon (no fill)
        p.setPen(QPen(c, max(1.2, size * 0.07)))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(2, 5)
        path.lineTo(size * 0.42, 5)
        path.lineTo(size * 0.52, 7.5)
        path.lineTo(size - 2, 7.5)
        path.lineTo(size - 2, size - 3)
        path.lineTo(2, size - 3)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "search":
        # Magnifying glass
        p.setPen(QPen(c, max(1.4, size * 0.08)))
        p.setBrush(Qt.NoBrush)
        r = size * 0.28
        cx_s, cy_s = size * 0.42, size * 0.42
        p.drawEllipse(QRectF(cx_s - r, cy_s - r, r * 2, r * 2))
        import math
        end_x = cx_s + r * math.cos(math.pi / 4)
        end_y = cy_s + r * math.sin(math.pi / 4)
        p.drawLine(int(end_x), int(end_y), int(size * 0.82), int(size * 0.82))
    elif name == "bell":
        # Notification bell
        p.setPen(QPen(c, max(1.2, size * 0.07)))
        p.setBrush(Qt.NoBrush)
        cx_b = size / 2.0
        bell_top = size * 0.15
        bell_bottom = size * 0.72
        bell_w = size * 0.55
        path = QPainterPath()
        path.moveTo(cx_b - bell_w / 2, bell_bottom)
        path.quadTo(cx_b - bell_w / 2, bell_top + size * 0.1, cx_b, bell_top)
        path.quadTo(cx_b + bell_w / 2, bell_top + size * 0.1, cx_b + bell_w / 2, bell_bottom)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(int(cx_b - bell_w * 0.65), int(bell_bottom), int(cx_b + bell_w * 0.65), int(bell_bottom))
        # Clapper
        p.drawLine(int(cx_b), int(bell_bottom), int(cx_b), int(size * 0.85))
    elif name == "help":
        # Question mark circle
        p.setPen(QPen(c, max(1.2, size * 0.07)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(2, 2, size - 4, size - 4))
        font = QFont(FONT_FAMILY, int(size * 0.45), QFont.Bold)
        p.setFont(font)
        p.drawText(QRectF(0, -1, size, size), Qt.AlignCenter, "?")
    else:
        p.setBrush(QBrush(c))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(3, 3, size - 6, size - 6))
        
    p.end()
    return pix

def get_user_display_name(email: str, parent=None, auth_data=None) -> str:
    # 1. Check auth_data for full_name or name from VDS backend
    if auth_data and isinstance(auth_data, dict):
        fn = auth_data.get("full_name") or auth_data.get("name")
        if fn and str(fn).strip():
            return str(fn).strip()
            
    clean_email = (email or "").strip().lower()
    
    # 2. Known default accounts
    if not clean_email or "seher" in clean_email or clean_email in ("admin@bgz.local", "admin", "yonetici", "admin@chenki.net", "sehersanli@chenki.net"):
        return "Seher Şanlı"
    if "birey" in clean_email or clean_email in ("bireykurum@chenki.net", "birey@chenki.net"):
        return "Birey Kurum"
        
    # 3. Persistent profile in user directory
    import os, json
    base_dir = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
    os.makedirs(base_dir, exist_ok=True)
    profiles_path = os.path.join(base_dir, "bgz_user_profiles.json")
    
    profiles = {}
    if os.path.exists(profiles_path):
        try:
            with open(profiles_path, "r", encoding="utf-8") as f:
                profiles = json.load(f)
        except Exception:
            profiles = {}
            
    if clean_email in profiles and profiles[clean_email].get("name"):
        return profiles[clean_email]["name"]
        
    # Default name derived from email without popup prompt
    name = clean_email.split("@")[0].capitalize()
    if "seher" in clean_email:
        name = "Seher Şanlı"
    elif "birey" in clean_email:
        name = "Birey Kurum"
        
    profiles[clean_email] = {"name": name, "email": clean_email}
    try:
        with open(profiles_path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return name

# ── Collapsible Version Group with Chevron ───────────────────────────

VERSION_DRAG_MIME = "application/x-chenki-version"

# Logical size of the ghost card that follows the cursor while dragging a version.
_DRAG_PIXMAP_W, _DRAG_PIXMAP_H = 210, 40


class CollapsibleVersionGroup(QFrame):
    """A collapsible section of version rows. When `is_drop_target` is set, dragging an
    AppleVersionRow onto it (anywhere, header included — most useful while collapsed)
    files that version under `folder_id` (folder_id=None means "Klasörsüz"/Genel).
    When `show_folder_actions` is set, a rename (pencil) and delete (trash) icon appear
    in the header for real user-created folders."""

    rename_requested = Signal()
    delete_requested = Signal()
    version_dropped = Signal(str, str)  # slug, filename

    def __init__(self, title: str, icon_name: str, badge_text: str, color_hex: str = "#1A1A1A",
                 is_collapsed: bool = False, folder_id=None, is_drop_target: bool = False,
                 show_folder_actions: bool = False, parent=None):
        super().__init__(parent)
        self.is_collapsed = is_collapsed
        self.color_hex = color_hex
        self.folder_id = folder_id
        self.is_drop_target = is_drop_target
        self._normal_style = """
            CollapsibleVersionGroup {
                background: #FFFFFF;
                border: none;
                border-bottom: 1px solid #EFEFEF;
            }
        """
        self._dragover_style = """
            CollapsibleVersionGroup {
                background: #F4F8FF;
                border: 1.5px dashed #0071E3;
            }
        """
        self.setStyleSheet(self._normal_style)
        if is_drop_target:
            self.setAcceptDrops(True)

        self.main_lay = QVBoxLayout(self)
        self.main_lay.setContentsMargins(20, 14, 20, 14)
        self.main_lay.setSpacing(8)

        # Header Button / Frame
        self.header = QFrame()
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.setStyleSheet("background: transparent; border: none;")
        hdr_lay = QHBoxLayout(self.header)
        hdr_lay.setContentsMargins(0, 0, 0, 0)
        hdr_lay.setSpacing(14)

        # Icon
        icon_lbl = QLabel()
        actual_icon = "folder_outline" if folder_id is not None else ("history" if icon_name in ("history", "archive") else icon_name)
        icon_lbl.setPixmap(make_dashboard_icon(actual_icon, "#1A1A1A", 18))
        icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        hdr_lay.addWidget(icon_lbl)

        # Title & Subtitle block
        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(3)
        text_vbox.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(f"<b>{title}</b>")
        title_lbl.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
        title_lbl.setStyleSheet("color: #111111; background: transparent; border: none;")
        title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        text_vbox.addWidget(title_lbl)

        if badge_text:
            sub_lbl = QLabel(badge_text)
            sub_lbl.setFont(QFont(FONT_FAMILY, 8.5))
            sub_lbl.setStyleSheet("color: #888888; background: transparent; border: none;")
            sub_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            text_vbox.addWidget(sub_lbl)

        hdr_lay.addLayout(text_vbox, 1)

        if show_folder_actions:
            btn_dots = QPushButton()
            btn_dots.setIcon(QIcon(make_dashboard_icon("three_dots", "#888888", 16)))
            btn_dots.setFixedSize(28, 28)
            btn_dots.setCursor(Qt.PointingHandCursor)
            btn_dots.setToolTip("Klasör Seçenekleri")
            btn_dots.setStyleSheet("""
                QPushButton { background: transparent; border: none; border-radius: 6px; }
                QPushButton:hover { background: #F0F0F0; }
            """)
            btn_dots.clicked.connect(self._show_folder_menu)
            hdr_lay.addWidget(btn_dots)
        else:
            # Chevron icon
            self.chevron_lbl = QLabel()
            self.chevron_lbl.setPixmap(make_dashboard_icon("chevron_right" if is_collapsed else "chevron_down", "#888888", 14))
            self.chevron_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            hdr_lay.addWidget(self.chevron_lbl)

        self.main_lay.addWidget(self.header)

        # Inner content container
        self.content_widget = QWidget()
        self.content_lay = QVBoxLayout(self.content_widget)
        self.content_lay.setContentsMargins(0, 4, 0, 2)
        self.content_lay.setSpacing(5)

        self.main_lay.addWidget(self.content_widget)
        self.content_widget.setVisible(not is_collapsed)

        self.header.mousePressEvent = self._toggle_collapse

        if is_drop_target:
            self.header.setAcceptDrops(True)
            self.header.installEventFilter(self)
            self.content_widget.setAcceptDrops(True)
            self.content_widget.installEventFilter(self)

    def _show_folder_menu(self):
        btn = self.sender()
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: #FFFFFF; border: 1px solid #E0E0E0;
                border-radius: 8px; padding: 4px; font-size: 12px; font-family: {FONT_FAMILY};
            }}
            QMenu::item {{ padding: 6px 18px; border-radius: 4px; color: #111111; }}
            QMenu::item:selected {{ background: #F4F4F6; }}
        """)
        act_rename = menu.addAction("✏️  Yeniden Adlandır")
        act_del = menu.addAction("🗑️  Klasörü Sil")
        pos = btn.mapToGlobal(QPoint(0, btn.height() + 2)) if btn else QCursor.pos()
        action = menu.exec_(pos)
        if action == act_rename:
            self.rename_requested.emit()
        elif action == act_del:
            self.delete_requested.emit()

    def eventFilter(self, obj, event):
        if self.is_drop_target:
            t = event.type()
            if t == QEvent.DragEnter:
                self.dragEnterEvent(event)
                return event.isAccepted()
            elif t == QEvent.DragMove:
                self.dragMoveEvent(event)
                return event.isAccepted()
            elif t == QEvent.DragLeave:
                self.dragLeaveEvent(event)
                return True
            elif t == QEvent.Drop:
                self.dropEvent(event)
                return event.isAccepted()
        return super().eventFilter(obj, event)

    def _set_collapsed(self, collapsed: bool):
        self.is_collapsed = collapsed
        self.content_widget.setVisible(not collapsed)
        if hasattr(self, "chevron_lbl") and self.chevron_lbl is not None:
            self.chevron_lbl.setPixmap(
                make_dashboard_icon("chevron_right" if collapsed else "chevron_down", "#888888", 14)
            )

    def _toggle_collapse(self, event):
        self._set_collapsed(not self.is_collapsed)

    def _accepts(self, event) -> bool:
        return bool(self.is_drop_target and event.mimeData().hasFormat(VERSION_DRAG_MIME))

    def dragEnterEvent(self, event):
        if self._accepts(event):
            event.setDropAction(Qt.MoveAction)
            event.accept()
            self.setStyleSheet(self._dragover_style)
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Without this the drop never lands.

        QWidget's default dragMoveEvent ignores the event, and Qt only delivers
        dropEvent if the most recent drag-move was accepted — so accepting in
        dragEnterEvent alone leaves the cursor showing "forbidden" and silently
        drops the gesture on the floor. That is why dragging a version onto a folder
        appeared to do nothing at all.
        """
        if self._accepts(event):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self._normal_style)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.setStyleSheet(self._normal_style)
        if not self._accepts(event):
            event.ignore()
            return
        raw = bytes(event.mimeData().data(VERSION_DRAG_MIME)).decode("utf-8")
        slug, _, filename = raw.partition("\n")
        if not (slug and filename):
            event.ignore()
            return
        event.setDropAction(Qt.MoveAction)
        event.accept()
        # Expanding on drop gives immediate confirmation that the version landed
        # where the user aimed it — folders render collapsed by default, so without
        # this a successful drop looks identical to a failed one.
        if self.is_collapsed:
            self._set_collapsed(False)
        self.version_dropped.emit(slug, filename)

# ── Apple Clean Version Row (Compact & Modern) ───────────────────────

class AppleVersionRow(QFrame):
    double_clicked = Signal(str, str)  # slug, filename
    selected = Signal(str)  # filename
    action_requested = Signal(str, str, str)  # action ('open', 'set_active', 'delete'), slug, filename
    
    def __init__(self, slug, version_info, is_active=False, parent=None):
        super().__init__(parent)
        self.slug = slug
        self.version_info = version_info
        self.filename = version_info["filename"]
        self._is_active = is_active
        self._is_selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(46)
        self._update_style()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 4, 14, 4)
        layout.setSpacing(12)
        
        # Version title. Uses the collision-resolved label from list_versions, so two
        # schedules that both ended up numbered 82 (independent saves on two devices)
        # read as "Versiyon 82" and "Versiyon 82-B" rather than as the same thing
        # listed twice.
        num = version_info.get("number", 0)
        v_title = QLabel(version_info.get("label") or f"Versiyon {num}")
        v_title.setFont(QFont("Segoe UI", 9.5, QFont.Bold))
        v_title.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        v_title.setFixedWidth(95)
        v_title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        if version_info.get("has_number_collision"):
            v_title.setToolTip(
                "Bu numara başka bir cihazda da kullanılmış. İçerikleri farklı olduğu "
                "için ikisi de korunuyor."
            )
        layout.addWidget(v_title)
        
        # Date & Time (Clean single block)
        d_str = version_info.get("date_str", "")
        t_str = version_info.get("time_str", "")
        dt_lbl = QLabel(f"{d_str}  {t_str}")
        dt_lbl.setFont(QFont("Segoe UI", 8.5))
        dt_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
        dt_lbl.setFixedWidth(145)
        dt_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(dt_lbl)
        
        # Details: Stats badge + Note
        tot = version_info.get("total_hours", 0)
        plc = version_info.get("placed_hours", 0)
        unp = version_info.get("unplaced_hours", 0)
        
        if tot > 0:
            if unp == 0:
                stats_badge = QLabel(f"{tot} Saat • Tam Yerleşim")
                stats_badge.setFont(QFont("Segoe UI", 8, QFont.Bold))
                stats_badge.setStyleSheet("background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; padding: 2px 8px; border-radius: 5px;")
            else:
                stats_badge = QLabel(f"{plc}/{tot} Saat • {unp} Boşta")
                stats_badge.setFont(QFont("Segoe UI", 8, QFont.Bold))
                stats_badge.setStyleSheet("background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A; padding: 2px 8px; border-radius: 5px;")
        else:
            stats_badge = QLabel("Boş Çizelge")
            stats_badge.setFont(QFont("Segoe UI", 8))
            stats_badge.setStyleSheet("background: #F1F5F9; color: #64748B; border: 1px solid #E2E8F0; padding: 2px 8px; border-radius: 5px;")
            
        stats_badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(stats_badge)
        
        note_text = version_info.get("note", "")
        if note_text:
            from PySide6.QtGui import QFontMetrics
            fm = QFontMetrics(QFont("Segoe UI", 8))
            elided_note = fm.elidedText(note_text, Qt.ElideRight, 200)
            note_lbl = QLabel(elided_note)
            note_lbl.setToolTip(note_text)
            note_lbl.setFont(QFont("Segoe UI", 8))
            note_lbl.setStyleSheet("color: #94A3B8; background: transparent; border: none;")
            note_lbl.setMaximumWidth(200)
            note_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            layout.addWidget(note_lbl)
        layout.addStretch(1)
            
        # File Size
        size_lbl = QLabel(f"{version_info.get('size_kb', 0)} KB")
        size_lbl.setFont(QFont("Segoe UI", 8))
        size_lbl.setStyleSheet("color: #94A3B8; background: transparent; border: none;")
        size_lbl.setFixedWidth(55)
        size_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        size_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(size_lbl)
        
        # Active Status Indicator / Action
        if is_active:
            act_badge = QLabel("✓ Yayında")
            act_badge.setFont(QFont("Segoe UI", 8, QFont.Bold))
            act_badge.setStyleSheet("background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; padding: 3px 9px; border-radius: 6px;")
            layout.addWidget(act_badge)
        else:
            btn_make_act = QPushButton("Yayına Al")
            btn_make_act.setFont(QFont("Segoe UI", 8))
            btn_make_act.setCursor(Qt.PointingHandCursor)
            btn_make_act.setStyleSheet("""
                QPushButton {
                    background: #F8FAFC; color: #475569; border: 1px solid #E2E8F0;
                    border-radius: 6px; padding: 4px 10px;
                }
                QPushButton:hover { background: #F1F5F9; color: #0F172A; border-color: #CBD5E1; }
            """)
            btn_make_act.clicked.connect(lambda: self.action_requested.emit("set_active", self.slug, self.filename))
            layout.addWidget(btn_make_act)
            
        # Open Button
        btn_open = QPushButton("Aç")
        btn_open.setFont(QFont("Segoe UI", 8.5, QFont.Bold))
        btn_open.setCursor(Qt.PointingHandCursor)
        btn_open.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 4px 14px; min-height: 26px;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        btn_open.clicked.connect(lambda: self.action_requested.emit("open", self.slug, self.filename))
        layout.addWidget(btn_open)
        
        # Delete / Remove Button
        btn_del = QPushButton("Sil")
        btn_del.setFont(QFont("Segoe UI", 8, QFont.Bold))
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setToolTip("Versiyonu Sil")
        btn_del.setStyleSheet("""
            QPushButton {
                background: #FFF5F5; color: #DC2626; border: 1px solid #FECACA;
                border-radius: 6px; padding: 4px 10px; min-height: 26px;
            }
            QPushButton:hover { background: #FEE2E2; color: #B91C1C; border-color: #FCA5A5; }
        """)
        btn_del.clicked.connect(lambda: self.action_requested.emit("delete", self.slug, self.filename))
        layout.addWidget(btn_del)
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        
    def _context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: #FFFFFF; border: 1px solid {BORDER_HAIRLINE};
                border-radius: 8px; padding: 4px; font-size: 12px; font-family: {FONT_FAMILY};
            }}
            QMenu::item {{ padding: 6px 18px; border-radius: 4px; }}
            QMenu::item:selected {{ background: #EBF5FF; color: {APPLE_BLUE}; }}
        """)
        act_open = menu.addAction("Çizelgeyi Aç")
        act_active = None
        if not self._is_active:
            act_active = menu.addAction("Aktif Çizelge Yap")
        menu.addSeparator()

        move_menu = menu.addMenu("Klasöre Taşı")
        move_menu.setStyleSheet(menu.styleSheet())
        current_folder_id = self.version_info.get("folder_id")
        act_move_general = move_menu.addAction("Klasörsüz (Genel)")
        act_move_general.setCheckable(True)
        act_move_general.setChecked(not current_folder_id)
        move_actions = {}
        folders = version_store.list_folders(self.slug)
        if folders:
            move_menu.addSeparator()
        for folder in folders:
            act = move_menu.addAction(folder.get("name", ""))
            act.setCheckable(True)
            act.setChecked(folder.get("id") == current_folder_id)
            move_actions[act] = folder.get("id")

        menu.addSeparator()
        act_del = menu.addAction("Versiyonu Sil")

        action = menu.exec_(self.mapToGlobal(pos))
        if action == act_open:
            self.action_requested.emit("open", self.slug, self.filename)
        elif act_active and action == act_active:
            self.action_requested.emit("set_active", self.slug, self.filename)
        elif action == act_del:
            self.action_requested.emit("delete", self.slug, self.filename)
        elif action == act_move_general:
            version_store.assign_version_folder(self.slug, self.filename, None)
            self._notify_parent_refresh_versions()
        elif action in move_actions:
            version_store.assign_version_folder(self.slug, self.filename, move_actions[action])
            self._notify_parent_refresh_versions()

    def _notify_parent_refresh_versions(self):
        p = self.parent()
        while p:
            if hasattr(p, "_refresh_versions"):
                p._refresh_versions()
                break
            p = p.parent() if hasattr(p, "parent") and callable(p.parent) else None
        
    def _update_style(self):
        if self._is_selected:
            self.setStyleSheet("""
                AppleVersionRow {
                    background: #F1F5F9; border: 1px solid #94A3B8; border-radius: 8px;
                }
                AppleVersionRow:hover { background: #E2E8F0; }
            """)
        else:
            self.setStyleSheet("""
                AppleVersionRow {
                    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
                }
                AppleVersionRow:hover { background: #F8FAFC; border: 1px solid #CBD5E1; }
            """)
            
    def set_selected(self, sel):
        """No-op when the state is unchanged.

        _update_style() calls setStyleSheet(), which forces Qt to re-parse the sheet
        and re-polish the widget and all its children. Selecting a version used to
        run this over EVERY row in the list, so a single click cost a full restyle of
        the whole panel — the more versions an institution had, the slower every
        click on it became.
        """
        if bool(sel) == bool(self._is_selected):
            return
        self._is_selected = bool(sel)
        self._update_style()


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.filename)
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Opens the schedule.

        This handler did not exist. The stray `super().mouseDoubleClickEvent(event)`
        that used to sit at the end of mousePressEvent forwarded a *press* event to
        the base class and emitted nothing, so `double_clicked` never fired and
        double-clicking a version — the most natural way to open one — did nothing.
        """
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = None  # a double-click must not also start a drag
            self.double_clicked.emit(self.slug, self.filename)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _make_drag_pixmap(self) -> QPixmap:
        """A small card that follows the cursor.

        The drag previously carried no pixmap at all, so nothing moved on screen
        while dragging and the gesture read as "this control isn't draggable".
        """
        ratio = self.devicePixelRatioF() if hasattr(self, "devicePixelRatioF") else 1.0
        width, height = _DRAG_PIXMAP_W, _DRAG_PIXMAP_H
        pm = QPixmap(int(width * ratio), int(height * ratio))
        pm.setDevicePixelRatio(ratio)
        pm.fill(Qt.transparent)

        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(255, 255, 255, 242)))
        p.setPen(QPen(QColor(APPLE_BLUE), 1.4))
        p.drawRoundedRect(QRectF(1, 1, width - 2, height - 2), 9, 9)

        p.setPen(QPen(QColor(TEXT_PRIMARY)))
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        label = self.version_info.get("label") or f"Versiyon {self.version_info.get('number', 0)}"
        p.drawText(QRectF(12, 4, width - 24, 17), Qt.AlignVCenter | Qt.AlignLeft, label)

        p.setPen(QPen(QColor(TEXT_SECONDARY)))
        p.setFont(QFont("Segoe UI", 8))
        sub = f"{self.version_info.get('date_str', '')} {self.version_info.get('time_str', '')}".strip()
        p.drawText(QRectF(12, 19, width - 24, 16), Qt.AlignVCenter | Qt.AlignLeft, sub or "Klasöre taşı")
        p.end()
        return pm

    def mouseMoveEvent(self, event):
        start = getattr(self, "_drag_start_pos", None)
        if not (event.buttons() & Qt.LeftButton) or start is None:
            super().mouseMoveEvent(event)
            return
        if (event.pos() - start).manhattanLength() < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        # Clear this first: the drag below runs a nested event loop, and re-entering
        # this handler while it is running would start a second, overlapping drag.
        self._drag_start_pos = None

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(VERSION_DRAG_MIME, f"{self.slug}\n{self.filename}".encode("utf-8"))
        # Plain text too, so dropping onto anything else is harmless and legible
        # rather than an unrecognised binary blob.
        mime.setText(f"Versiyon {self.version_info.get('number', 0)} — {self.filename}")
        drag.setMimeData(mime)
        pm = self._make_drag_pixmap()
        drag.setPixmap(pm)
        # Hot spot is in the pixmap's logical coordinates, not its device pixels —
        # using pm.width() directly would offset the ghost by the DPI scale factor
        # on a HiDPI screen.
        drag.setHotSpot(QPoint(_DRAG_PIXMAP_W // 2, _DRAG_PIXMAP_H // 2))
        drag.exec(Qt.MoveAction, Qt.MoveAction)


# ── Main Home Dashboard ──────────────────────────────────────────────

class HomeDashboard(QWidget):
    open_timetable = Signal(str, str)  # slug, filename
    new_empty_timetable = Signal(str)  # slug
    logout_requested = Signal()        # Trigger logout & return to login screen
    # Carries a background sync's outcome back onto the GUI thread:
    # (pull_ok, pull_msg, push_ok, push_msg)
    sync_finished = Signal(bool, str, bool, str)

    def __init__(self, auth_data=None, parent=None):
        super().__init__(parent)
        self.auth_data = auth_data or {}
        self._selected_slug = None
        self._selected_version = None
        self._search_query = ""
        self._unlocked_slugs = set()
        self._sync_in_flight = False
        # Coalesces the refresh bursts that arrive when several cloud events land
        # together; see _on_cloud_synced.
        self._refresh_debounce = None
        
        user_email = self.auth_data.get("email", "").lower()
        user_role = self.auth_data.get("role", "").lower()
        is_guest = bool(self.auth_data.get("is_guest") or self.auth_data.get("is_shared") or user_role in ["guest", "shared", "viewer"])
        # Master admin can delete institutions and change/remove passwords; viewer/guest accounts cannot
        from api_client import api_client
        self.is_master_admin = api_client.is_admin() and not is_guest
        self.display_name = get_user_display_name(user_email, self, self.auth_data)
        
        version_store.migrate_existing_data()
        # Move any single-machine teacher reservations into the institutions'
        # meta.json, which syncs — so they become editable from every computer.
        try:
            import constraint_sync
            constraint_sync.migrate_local_reservations()
        except Exception as e:
            print(f"[HomeDashboard] reservation migration note: {e}")
        self._build_ui()
        self._refresh_institutions()
        
        # Cross-PC Realtime Database Sync on startup
        if self.auth_data and not self.auth_data.get("is_offline"):
            self._start_initial_cloud_sync()
        try:
            from cloud_sync import CloudSyncWorker
            self.cloud_worker = CloudSyncWorker(self)
            if self.auth_data:
                self.cloud_worker.set_auth(self.auth_data)
            self.cloud_worker.institutions_list_changed.connect(self._on_cloud_synced)
            self.cloud_worker.remote_data_updated.connect(lambda slug, fn: self._on_cloud_synced())
            self.cloud_worker.start()
        except Exception as cwe:
            print(f"[HomeDashboard] Cloud worker init note: {cwe}")

        # Real-time push notifications: when another device changes the institution
        # currently open here, refresh almost instantly instead of waiting for the
        # CloudSyncWorker's ~15s poll. Purely additive — if the server or connection
        # doesn't support it, this just stays quiet and the poll loop still covers it.
        try:
            from cloud_sync import RealtimeSyncClient
            self._realtime = RealtimeSyncClient(self)
            # The socket only carries a nudge, never data: it tells the worker to
            # run a delta sync now instead of waiting for its next poll. That keeps
            # the socket cheap and means a dropped message costs a little latency
            # rather than losing a change.
            self._realtime.sync_notified.connect(self._on_realtime_nudge)
            if self._selected_slug:
                self._realtime.watch(self._selected_slug)
        except Exception as rte:
            print(f"[HomeDashboard] Realtime sync init note: {rte}")

    def _on_realtime_nudge(self, slug):
        worker = getattr(self, "cloud_worker", None)
        if worker is not None:
            worker.request_pull()
            
    def _start_initial_cloud_sync(self):
        import threading
        from cloud_sync import pull_all_from_rtdb
        from PySide6.QtCore import QTimer
        
        def _worker():
            try:
                # Pull all remote institutions and versions from VDS as source of truth
                ok, _, _ = pull_all_from_rtdb(self.auth_data)
                if ok:
                    QTimer.singleShot(0, self._on_cloud_synced)
            except Exception as e:
                print(f"[HomeDashboard] Cloud sync note: {e}")
                
        threading.Thread(target=_worker, daemon=True).start()
        
    def _on_cloud_synced(self):
        """Rebuilds the panels after a sync, coalescing bursts.

        A single sync fires institutions_list_changed AND remote_data_updated, and a
        realtime nudge can land on top of both. Each one used to rebuild every card
        and every version row immediately, so one remote change could rebuild the
        whole screen three times in a row — visible as a stutter, and it discards the
        user's scroll position and selection each time. Collapsing them into one
        rebuild a short moment later is both smoother and cheaper.
        """
        from PySide6.QtCore import QTimer

        if self._refresh_debounce is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self._do_refresh_all)
            self._refresh_debounce = timer
        self._refresh_debounce.start(140)

    def _do_refresh_all(self):
        # Dragging while the panel is rebuilt under the cursor destroys the widget
        # mid-gesture; let the drop finish and pick the refresh up afterwards.
        if QApplication.mouseButtons() & Qt.LeftButton:
            self._refresh_debounce.start(300)
            return
        self._refresh_institutions()
        if self._selected_slug:
            self._refresh_versions()


    def _build_ui(self):
        self.setStyleSheet(f"""
            HomeDashboard {{ background: {BG_CANVAS}; font-family: {FONT_FAMILY}; }}
            QToolTip {{
                background-color: #1D1D1F;
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                padding: 5px 9px;
                font-size: 11px;
                font-family: {FONT_FAMILY};
            }}
        """)
        
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        # ── 1. Top Bar ───────────────────────────────────────────────
        top_bar = QFrame()
        top_bar.setFixedHeight(52)
        top_bar.setStyleSheet(f"background: {BG_CARD}; border-bottom: 1px solid {BORDER_HAIRLINE};")
        
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 0, 16, 0)
        top_layout.setSpacing(10)
        
        # Building icon
        brand_icon = QLabel()
        brand_icon.setPixmap(make_3d_institution_icon("", "#1A1A1A", 22))
        brand_icon.setFixedSize(22, 22)
        top_layout.addWidget(brand_icon)
        
        brand_lbl = QLabel("Anasayfa")
        brand_lbl.setFont(QFont(FONT_FAMILY, 13, QFont.DemiBold))
        brand_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        top_layout.addWidget(brand_lbl)
        
        top_layout.addSpacing(16)
        
        # Search Box with ⌘K hint
        search_container = QFrame()
        search_container.setFixedWidth(220)
        search_container.setFixedHeight(30)
        search_container.setStyleSheet(f"""
            QFrame {{
                background: {HOVER_BG}; border: 1px solid {BORDER_HAIRLINE};
                border-radius: 6px;
            }}
        """)
        sc_lay = QHBoxLayout(search_container)
        sc_lay.setContentsMargins(8, 0, 8, 0)
        sc_lay.setSpacing(6)
        
        search_icon = QLabel()
        search_icon.setPixmap(make_dashboard_icon("search", "#999999", 14))
        search_icon.setFixedSize(14, 14)
        sc_lay.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ara...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent; border: none;
                font-size: 12px; color: {TEXT_PRIMARY};
                padding: 0;
            }}
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        sc_lay.addWidget(self.search_input, 1)
        
        shortcut_lbl = QLabel("⌘K")
        shortcut_lbl.setFont(QFont(FONT_FAMILY, 9))
        shortcut_lbl.setStyleSheet("color: #BBBBBB; background: #EEEEEE; padding: 1px 5px; border-radius: 3px; border: 1px solid #DDDDDD;")
        sc_lay.addWidget(shortcut_lbl)
        
        top_layout.addWidget(search_container)
        
        top_layout.addStretch(1)
        
        # ── 1. Top Bar ───────────────────────────────────────────────
        top_bar = QFrame()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet("background: #FFFFFF; border-bottom: 1px solid #EFEFEF;")
        
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(18, 0, 18, 0)
        top_layout.setSpacing(10)
        
        # Classical Building icon
        brand_icon = QLabel()
        brand_icon.setPixmap(make_3d_institution_icon("", "#1A1A1A", 20))
        brand_icon.setFixedSize(20, 20)
        top_layout.addWidget(brand_icon)
        
        brand_lbl = QLabel("Anasayfa")
        brand_lbl.setFont(QFont(FONT_FAMILY, 11.5, QFont.Bold))
        brand_lbl.setStyleSheet("color: #111111;")
        top_layout.addWidget(brand_lbl)
        
        top_layout.addSpacing(16)
        
        # Search Box with ⌘K hint
        search_container = QFrame()
        search_container.setFixedWidth(210)
        search_container.setFixedHeight(30)
        search_container.setStyleSheet("""
            QFrame {
                background: #F4F4F6;
                border: 1px solid #ECECEC;
                border-radius: 6px;
            }
        """)
        sc_lay = QHBoxLayout(search_container)
        sc_lay.setContentsMargins(8, 0, 6, 0)
        sc_lay.setSpacing(6)
        
        search_icon = QLabel()
        search_icon.setPixmap(make_dashboard_icon("search", "#888888", 13))
        search_icon.setFixedSize(13, 13)
        sc_lay.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ara...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: transparent; border: none;
                font-size: 11.5px; color: #111111;
                padding: 0;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        sc_lay.addWidget(self.search_input, 1)
        
        shortcut_lbl = QLabel("⌘K")
        shortcut_lbl.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        shortcut_lbl.setStyleSheet("color: #999999; background: #E8E8EC; padding: 1px 4px; border-radius: 3px; border: none;")
        sc_lay.addWidget(shortcut_lbl)
        
        top_layout.addWidget(search_container)
        
        top_layout.addStretch(1)
        
        # Right side: User greeting
        user_lbl = QLabel(f"Hoşgeldiniz, <b>{self.display_name}</b>")
        user_lbl.setFont(QFont(FONT_FAMILY, 9.5))
        user_lbl.setStyleSheet("color: #111111;")
        top_layout.addWidget(user_lbl)
        
        top_layout.addSpacing(6)
        
        # Utility icons (?, 🔔, $S)
        def _make_icon_btn(icon_name, tooltip, color="#555555", sz=16):
            btn = QPushButton()
            btn.setIcon(QIcon(make_dashboard_icon(icon_name, color, sz)))
            btn.setIconSize(QSize(sz, sz))
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; border-radius: 6px; }
                QPushButton:hover { background: #F0F0F2; }
            """)
            return btn
        
        btn_help = _make_icon_btn("help", "Yardım & Bilgi")
        top_layout.addWidget(btn_help)
        
        btn_bell = _make_icon_btn("bell", "Bildirimler")
        top_layout.addWidget(btn_bell)
        
        top_layout.addSpacing(2)
        
        # Avatar pill button ($S)
        self.btn_avatar = QPushButton("$S")
        self.btn_avatar.setFont(QFont(FONT_FAMILY, 8.5, QFont.Bold))
        self.btn_avatar.setCursor(Qt.PointingHandCursor)
        self.btn_avatar.setToolTip(f"{self.display_name} (Profil & Ayarlar)")
        self.btn_avatar.setFixedSize(28, 28)
        self.btn_avatar.setStyleSheet("""
            QPushButton {
                background: #F4F4F6; color: #222222;
                border: 1px solid #E0E0E5; border-radius: 14px;
            }
            QPushButton:hover { background: #E8E8ED; }
        """)
        self.btn_avatar.clicked.connect(self._show_avatar_menu)
        top_layout.addWidget(self.btn_avatar)
        
        root.addWidget(top_bar)
        
        # ── 2. Main Body ─────────────────────────────────────────
        main_hbox = QHBoxLayout()
        main_hbox.setContentsMargins(0, 0, 0, 0)
        main_hbox.setSpacing(0)
        
        # Left Sidebar (Institutions)
        left_panel = QFrame()
        left_panel.setFixedWidth(235)
        left_panel.setStyleSheet("background: #FFFFFF; border-right: 1px solid #EFEFEF;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 16, 12, 12)
        left_layout.setSpacing(6)
        
        left_hdr = QHBoxLayout()
        left_title = QLabel("KURUMLAR")
        left_title.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        left_title.setStyleSheet("color: #999999; letter-spacing: 0.8px;")
        left_hdr.addWidget(left_title)
        left_hdr.addStretch(1)
        left_layout.addLayout(left_hdr)
        
        scroll_inst = QScrollArea()
        scroll_inst.setWidgetResizable(True)
        scroll_inst.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_inst.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.inst_list_widget = QWidget()
        self.inst_list_widget.setStyleSheet("background: transparent;")
        self.inst_list_layout = QVBoxLayout(self.inst_list_widget)
        self.inst_list_layout.setContentsMargins(0, 0, 0, 0)
        self.inst_list_layout.setSpacing(4)
        self.inst_list_layout.addStretch(1)
        
        scroll_inst.setWidget(self.inst_list_widget)
        left_layout.addWidget(scroll_inst, 1)
        
        # Bottom of Sidebar: Gear "Ayarlar" button
        btn_settings = QPushButton("Ayarlar")
        btn_settings.setIcon(QIcon(make_dashboard_icon("gear", "#555555", 16)))
        btn_settings.setIconSize(QSize(16, 16))
        btn_settings.setFont(QFont(FONT_FAMILY, 9.5))
        btn_settings.setCursor(Qt.PointingHandCursor)
        btn_settings.setStyleSheet("""
            QPushButton {
                background: transparent; color: #444444; border: none;
                border-radius: 6px; padding: 7px 10px; text-align: left;
            }
            QPushButton:hover { background: #F4F4F6; color: #111111; }
        """)
        btn_settings.clicked.connect(self._show_avatar_menu)
        left_layout.addWidget(btn_settings)
        
        main_hbox.addWidget(left_panel)
        
        # Right Area
        right_panel = QFrame()
        right_panel.setStyleSheet("background: #FFFFFF;")
        self.right_panel_layout = QVBoxLayout(right_panel)
        self.right_panel_layout.setContentsMargins(32, 28, 32, 16)
        self.right_panel_layout.setSpacing(16)
        
        # Header of Selected Institution
        right_hdr = QHBoxLayout()
        right_hdr.setSpacing(12)
        
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(4)
        title_vbox.setContentsMargins(0, 0, 0, 0)
        
        self.right_title = QLabel("Seçili Kurum")
        self.right_title.setFont(QFont(FONT_FAMILY, 16, QFont.Bold))
        self.right_title.setStyleSheet("color: #111111;")
        title_vbox.addWidget(self.right_title)
        
        sub_info_hbox = QHBoxLayout()
        sub_info_hbox.setSpacing(8)
        sub_info_hbox.setContentsMargins(0, 0, 0, 0)
        
        self.ver_count_lbl = QLabel("0 versiyon")
        self.ver_count_lbl.setFont(QFont(FONT_FAMILY, 9.5))
        self.ver_count_lbl.setStyleSheet("color: #777777;")
        sub_info_hbox.addWidget(self.ver_count_lbl)
        
        self.last_update_badge = QLabel("")
        self.last_update_badge.setFont(QFont(FONT_FAMILY, 9.5))
        self.last_update_badge.setStyleSheet("color: #777777;")
        sub_info_hbox.addWidget(self.last_update_badge)
        sub_info_hbox.addStretch(1)
        title_vbox.addLayout(sub_info_hbox)
        
        right_hdr.addLayout(title_vbox, 1)
        
        # Hidden legacy helper badges
        self.primary_inst_badge = QLabel()
        self.primary_inst_badge.hide()
        self.btn_set_primary = QPushButton()
        self.btn_set_primary.hide()
        
        # Action Buttons on Right Header:
        # 1. "Yeni Boş Çizelge   +" (Solid Black)
        self.btn_new_empty = QPushButton("Yeni Boş Çizelge    +")
        self.btn_new_empty.setFont(QFont(FONT_FAMILY, 9.5, QFont.Bold))
        self.btn_new_empty.setCursor(Qt.PointingHandCursor)
        self.btn_new_empty.setStyleSheet("""
            QPushButton {
                background: #111111; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 8px 18px; font-weight: 600;
            }
            QPushButton:hover { background: #2A2A2A; }
        """)
        self.btn_new_empty.clicked.connect(self._on_new_empty_clicked)
        right_hdr.addWidget(self.btn_new_empty)

        # 2. "Yeni Klasör   📁" (White Outline)
        self.btn_new_folder = QPushButton("Yeni Klasör  ")
        self.btn_new_folder.setIcon(QIcon(make_dashboard_icon("folder_outline", "#111111", 16)))
        self.btn_new_folder.setLayoutDirection(Qt.RightToLeft)
        self.btn_new_folder.setIconSize(QSize(16, 16))
        self.btn_new_folder.setFont(QFont(FONT_FAMILY, 9.5, QFont.DemiBold))
        self.btn_new_folder.setCursor(Qt.PointingHandCursor)
        self.btn_new_folder.setStyleSheet("""
            QPushButton {
                background: #FFFFFF; color: #111111; border: 1px solid #E0E0E5;
                border-radius: 8px; padding: 8px 16px;
            }
            QPushButton:hover { background: #F8F8FA; border-color: #D0D0D5; }
        """)
        self.btn_new_folder.clicked.connect(self._on_new_folder_clicked)
        right_hdr.addWidget(self.btn_new_folder)

        self.right_panel_layout.addLayout(right_hdr)
        
        # Versions container
        self.right_panel_body = QVBoxLayout()
        self.right_panel_layout.addLayout(self.right_panel_body, 1)
        
        # Normal Versions List View
        self.right_content_widget = QWidget()
        self.right_content_layout = QVBoxLayout(self.right_content_widget)
        self.right_content_layout.setContentsMargins(0, 0, 0, 0)
        self.right_content_layout.setSpacing(10)
        
        # Inline confirmation strip
        self.status_flash_lbl = QLabel("")
        self.status_flash_lbl.setFont(QFont(FONT_FAMILY, 9))
        self.status_flash_lbl.setStyleSheet(
            "background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0;"
            "border-radius: 8px; padding: 7px 12px;"
        )
        self.status_flash_lbl.hide()
        self.right_content_layout.addWidget(self.status_flash_lbl)

        scroll_ver = QScrollArea()
        scroll_ver.setWidgetResizable(True)
        scroll_ver.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: transparent; width: 8px; margin: 2px 2px 2px 0;
            }
            QScrollBar::handle:vertical {
                background: #D5D5DB; border-radius: 4px; min-height: 34px;
            }
            QScrollBar::handle:vertical:hover { background: #A0A0AA; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        scroll_ver.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_ver.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_ver.verticalScrollBar().setSingleStep(14)
        self.scroll_ver = scroll_ver

        self.ver_list_widget = QWidget()
        self.ver_list_widget.setStyleSheet("background: transparent;")
        self.ver_list_layout = QVBoxLayout(self.ver_list_widget)
        self.ver_list_layout.setContentsMargins(0, 0, 4, 0)
        self.ver_list_layout.setSpacing(10)
        self.ver_list_layout.addStretch(1)

        scroll_ver.setWidget(self.ver_list_widget)
        self.right_content_layout.addWidget(scroll_ver, 1)
        self.right_panel_body.addWidget(self.right_content_widget)
        
        # Password Protection Overlay Widget
        self.password_overlay_widget = PasswordOverlayContainer(self)
        overlay_layout = QVBoxLayout(self.password_overlay_widget)
        overlay_layout.setAlignment(Qt.AlignCenter)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        
        self.pwd_card = PasswordCardWidget(self.password_overlay_widget)
        self.pwd_card.setObjectName("pwdCard")
        self.pwd_card.setFixedSize(480, 350)
        
        c_layout = QVBoxLayout(self.pwd_card)
        c_layout.setContentsMargins(40, 30, 40, 30)
        c_layout.setSpacing(16)
        c_layout.setAlignment(Qt.AlignCenter)
        
        lock_lbl = QLabel()
        lock_lbl.setPixmap(make_apple_lock_badge(44))
        lock_lbl.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(lock_lbl)
        
        self.pwd_card_title = QLabel("Kurum Şifresi Korumalı")
        self.pwd_card_title.setFont(QFont(FONT_FAMILY, 13, QFont.Bold))
        self.pwd_card_title.setStyleSheet("color: #0F172A; font-weight: bold;")
        self.pwd_card_title.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(self.pwd_card_title)
        
        desc_lbl = QLabel("Bu kurumun ders çizelgelerine erişmek için\nlütfen kurum şifresini girin.")
        desc_lbl.setFont(QFont(FONT_FAMILY, 9))
        desc_lbl.setStyleSheet("color: #64748B;")
        desc_lbl.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(desc_lbl)
        
        self.pwd_card_input = QLineEdit()
        self.pwd_card_input.setEchoMode(QLineEdit.Password)
        self.pwd_card_input.setPlaceholderText("Kurum şifresini girin...")
        self.pwd_card_input.setFixedHeight(38)
        self.pwd_card_input.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 13px;
                background: #F8FAFC;
                color: #0F172A;
            }
            QLineEdit:focus {
                border: 1.5px solid #0071E3;
                background: #FFFFFF;
            }
        """)
        c_layout.addWidget(self.pwd_card_input)
        
        self.pwd_err_lbl = QLabel("")
        self.pwd_err_lbl.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self.pwd_err_lbl.setStyleSheet("color: #EF4444;")
        self.pwd_err_lbl.setAlignment(Qt.AlignCenter)
        self.pwd_err_lbl.hide()
        c_layout.addWidget(self.pwd_err_lbl)
        
        btn_unlock = QPushButton("Kilidi Aç ve Giriş Yap")
        btn_unlock.setFont(QFont(FONT_FAMILY, 9.5, QFont.Bold))
        btn_unlock.setFixedHeight(36)
        btn_unlock.setCursor(Qt.PointingHandCursor)
        btn_unlock.setStyleSheet("""
            QPushButton {
                background: #111111; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 4px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #333333; }
        """)
        btn_unlock.clicked.connect(self._on_submit_password_overlay)
        self.pwd_card_input.returnPressed.connect(self._on_submit_password_overlay)
        c_layout.addWidget(btn_unlock)
        
        overlay_layout.addWidget(self.pwd_card)
        self.right_panel_body.addWidget(self.password_overlay_widget)
        self.password_overlay_widget.hide()
        
        # Bottom Footer Label
        self.footer_lbl = QLabel(f"© {datetime.now().year} Boğaziçi Eğitim Kurumları")
        self.footer_lbl.setFont(QFont(FONT_FAMILY, 8.5))
        self.footer_lbl.setStyleSheet("color: #999999; padding-top: 8px;")
        self.footer_lbl.setAlignment(Qt.AlignCenter)
        self.right_panel_layout.addWidget(self.footer_lbl)
        
        main_hbox.addWidget(right_panel, 1)
        root.addLayout(main_hbox, 1)

    def _show_avatar_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: #FFFFFF; border: 1px solid #E0E0E0;
                border-radius: 8px; padding: 6px; font-size: 12px; font-family: {FONT_FAMILY};
            }}
            QMenu::item {{ padding: 6px 18px; border-radius: 4px; color: #111111; }}
            QMenu::item:selected {{ background: #F4F4F6; }}
            QMenu::separator {{ height: 1px; background: #EEEEEE; margin: 4px 0; }}
        """)
        
        act_cloud = menu.addAction("☁️  Bulut Eşitle")
        act_import = menu.addAction("🔄  Veri Aktar")
        act_new_inst = menu.addAction("➕  Yeni Kurum Ekle")
        menu.addSeparator()
        act_logout = menu.addAction("🚪  Oturumu Kapat (Çıkış)")
        
        pos = self.sender().mapToGlobal(QPoint(0, self.sender().height() + 4))
        action = menu.exec_(pos)
        if action == act_cloud:
            self._manual_cloud_sync()
        elif action == act_import:
            self._on_cross_import_clicked()
        elif action == act_new_inst:
            self._on_new_institution_clicked()
        elif action == act_logout:
            self._on_logout_clicked()

    def _on_logout_clicked(self):
        dlg = AppleConfirmDialog("Çıkış Yap", "Oturumunuzu kapatmak istediğinize emin misiniz?", confirm_text="Çıkış Yap", cancel_text="Vazgeç", is_destructive=True, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.logout_requested.emit()
        
    def _on_submit_password_overlay(self):
        pwd = self.pwd_card_input.text()
        if not self._selected_slug:
            return
        if version_store.verify_institution_password(self._selected_slug, pwd):
            self._unlocked_slugs.add(self._selected_slug)
            # Cache password for this device so it won't be asked again
            version_store.save_device_password_cache(self._selected_slug, pwd)
            self.pwd_err_lbl.hide()
            self.pwd_card_input.clear()
            self.right_content_widget.show()
            self.btn_new_empty.setEnabled(True)
            self._refresh_versions()
        else:
            self.pwd_err_lbl.setText("Hatalı kurum şifresi. Lütfen tekrar deneyin.")
            self.pwd_err_lbl.show()
            self.pwd_card_input.setStyleSheet("""
                QLineEdit {
                    border: 1.5px solid #EF4444;
                    border-radius: 8px;
                    padding: 4px 12px;
                    font-size: 13px;
                    background: #FEF2F2;
                    color: #0F172A;
                }
            """)
            self.pwd_card_input.selectAll()
            self.pwd_card_input.setFocus()
        
    def _on_search_changed(self, text):
        query = text.strip().lower()
        self._search_query = query
        
        first_visible = None
        for i in range(self.inst_list_layout.count() - 1):
            w = self.inst_list_layout.itemAt(i).widget()
            if isinstance(w, AppleInstitutionCard):
                matches = (not query) or (query in w.inst_name.lower())
                w.setVisible(matches)
                if matches and not first_visible:
                    first_visible = w.slug
                    
        # Filter current version rows if loaded
        for row in self.findChildren(AppleVersionRow):
            if query:
                num_str = str(row.version_info.get("number", ""))
                note_str = row.version_info.get("note", "").lower()
                fn_str = row.filename.lower()
                row.setVisible(query in num_str or query in note_str or query in fn_str)
            else:
                row.setVisible(True)
        
    def _refresh_institutions(self):
        while self.inst_list_layout.count() > 1:
            item = self.inst_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        institutions = version_store.list_institutions()
        
        filtered = []
        for inst in institutions:
            if self._search_query and self._search_query not in inst["name"].lower():
                continue
            filtered.append(inst)
            
        for inst in filtered:
            is_sel = (inst["slug"] == self._selected_slug)
            card = AppleInstitutionCard(inst, is_selected=is_sel, is_master_admin=self.is_master_admin)
            card.clicked.connect(self._on_institution_selected)
            self.inst_list_layout.insertWidget(self.inst_list_layout.count() - 1, card)
            
        if not self._selected_slug and filtered:
            self._on_institution_selected(filtered[0]["slug"])
        elif self._selected_slug:
            self._refresh_versions()
            
    def _on_institution_selected(self, slug):
        self._selected_slug = slug
        version_store.set_last_active_institution_slug(slug)
        self._selected_version = None
        # Auto-unlock if this device has previously authenticated for this institution
        if version_store.check_device_password_cache(slug):
            self._unlocked_slugs.add(slug)
        
        for i in range(self.inst_list_layout.count() - 1):
            w = self.inst_list_layout.itemAt(i).widget()
            if isinstance(w, AppleInstitutionCard):
                w.set_selected(w.slug == slug)

        if hasattr(self, "_realtime"):
            self._realtime.watch(slug)

        self._refresh_versions()
        
    def _on_make_selected_primary_clicked(self):
        if not self._selected_slug:
            return
        meta = version_store.get_institution_meta(self._selected_slug)
        inst_name = meta.get("name", self._selected_slug)
        version_store.set_primary_institution(self._selected_slug)
        show_apple_info(self, "Ana Kurum Güncellendi", f"'{inst_name}' başarıyla varsayılan ana kurum olarak ayarlandı.", is_success=True)
        self._refresh_institutions()
        self._refresh_versions()

    def _on_new_folder_clicked(self):
        if not self._selected_slug:
            return
        dlg = AppleInputDialog("Yeni Klasör", "Klasör adı (Örn: Yaz Çizelgesi):", parent=self)
        if dlg.exec() == QDialog.Accepted and dlg.text_value().strip():
            name = dlg.text_value().strip()
            folder, created = version_store.create_folder(self._selected_slug, name)
            if not created:
                show_apple_info(
                    self, "Klasör Zaten Var",
                    f"\"{name}\" isimli bir klasör zaten mevcut. Aynı isimle ikinci bir klasör oluşturulmadı — mevcut klasör seçili kaldı.",
                    is_success=False
                )
            self._refresh_versions()

    def _on_folder_rename(self, folder_id, current_name):
        if not self._selected_slug or not folder_id:
            return
        dlg = AppleInputDialog("Klasörü Yeniden Adlandır", "Yeni klasör adı:", default_text=current_name, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        new_name = dlg.text_value().strip()
        if not new_name or new_name == current_name:
            return
        ok = version_store.rename_folder(self._selected_slug, folder_id, new_name)
        if not ok:
            show_apple_info(
                self, "Klasör Zaten Var",
                f"\"{new_name}\" isimli başka bir klasör zaten var. İsim değiştirilmedi.",
                is_success=False
            )
        self._refresh_versions()

    def _on_folder_delete(self, folder_id, folder_name):
        if not self._selected_slug or not folder_id:
            return
        count = sum(
            1 for v in version_store.list_versions(self._selected_slug)
            if v.get("folder_id") == folder_id
        )
        if count:
            message = (
                f"\"{folder_name}\" klasörü ve içindeki {count} çizelge kalıcı olarak "
                "silinecek ve buluttan da kaldırılacaktır. Bu işlem geri alınamaz."
            )
        else:
            message = f"\"{folder_name}\" klasörü silinecek. Bu işlem geri alınamaz."
        dlg = AppleConfirmDialog(
            title="Klasörü Sil",
            message=message,
            confirm_text="Klasörü Sil",
            cancel_text="Vazgeç",
            is_destructive=True,
            parent=self
        )
        if dlg.exec() != QDialog.Accepted:
            return
        from save_dialog import run_apple_save_sequence
        run_apple_save_sequence(self, duration_seconds=0.25, title="Klasör Siliniyor", message=f"\"{folder_name}\" ve içeriği siliniyor...")
        version_store.delete_folder(self._selected_slug, folder_id)
        self._refresh_versions()
        self._refresh_institutions()

    def _on_version_dropped_on_folder(self, slug, filename, folder_id):
        """Files a dragged version into a folder (folder_id=None means Klasörsüz)."""
        if slug != self._selected_slug:
            return

        current = None
        for v in version_store.list_versions(slug):
            if v["filename"] == filename:
                current = v.get("folder_id")
                break
        if current == folder_id:
            return  # dropped back where it already was — nothing to do, no flicker

        if not version_store.assign_version_folder(slug, filename, folder_id):
            show_apple_info(
                self, "Taşınamadı",
                "Bu versiyon klasöre taşınamadı. Dosya başka bir cihaz tarafından "
                "değiştirilmiş olabilir; sayfayı yenileyip tekrar deneyin.",
                is_success=False,
            )
            return

        # Keep the moved version selected across the rebuild so the user does not
        # lose their place in a long list.
        self._selected_version = filename
        self._refresh_versions()

        folder_name = next(
            (f.get("name", "") for f in version_store.list_folders(slug) if f.get("id") == folder_id),
            "",
        )
        self._flash_status(
            f"Versiyon '{folder_name}' klasörüne taşındı."
            if folder_name else "Versiyon klasörden çıkarıldı."
        )

    def _flash_status(self, text: str, msec: int = 2600):
        """Brief inline confirmation in the right-hand panel.

        Deliberately not a modal: filing a version is a low-stakes, repeatable
        action, and a dialog that has to be dismissed after every drag would be
        worse than no feedback at all.
        """
        label = getattr(self, "status_flash_lbl", None)
        if label is None:
            return
        label.setText(text)
        label.show()
        timer = getattr(self, "_flash_timer", None)
        if timer is None:
            from PySide6.QtCore import QTimer
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(label.hide)
            self._flash_timer = timer
        timer.start(msec)

    def _create_version_group_card(self, title: str, icon_name: str, badge_text: str, color_hex: str = "#1A1A1A"):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #EAEAEA;
                border-radius: 10px;
            }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(6)
        
        # Header
        hdr = QHBoxLayout()
        hdr.setContentsMargins(2, 2, 2, 4)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_dashboard_icon(icon_name, "#1A1A1A", 18))
        hdr.addWidget(icon_lbl)
        
        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(2)
        text_vbox.setContentsMargins(0, 0, 0, 0)
        
        title_lbl = QLabel(f"<b>{title}</b>")
        title_lbl.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
        title_lbl.setStyleSheet("color: #111111; background: transparent; border: none;")
        text_vbox.addWidget(title_lbl)
        
        if badge_text:
            sub_lbl = QLabel(badge_text)
            sub_lbl.setFont(QFont(FONT_FAMILY, 8.5))
            sub_lbl.setStyleSheet("color: #888888; background: transparent; border: none;")
            text_vbox.addWidget(sub_lbl)
            
        hdr.addLayout(text_vbox, 1)
        lay.addLayout(hdr)
        
        content_lay = QVBoxLayout()
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(5)
        lay.addLayout(content_lay)
        
        return card, content_lay

    def _refresh_versions(self):
        if not self._selected_slug:
            return

        inst_dir = version_store._institution_dir(self._selected_slug)
        if not os.path.isdir(inst_dir):
            self._selected_slug = None
            return

        # The whole list is rebuilt below, which resets the viewport to the top and
        # collapses every folder. That is jarring on its own and actively disruptive
        # when the rebuild was triggered by a background cloud sync the user did not
        # ask for, so scroll offset and which folders were open are restored after.
        scroll_bar = self.scroll_ver.verticalScrollBar() if hasattr(self, "scroll_ver") else None
        prev_scroll = scroll_bar.value() if scroll_bar is not None else 0
        prev_open_folders = {
            g.folder_id for g in self.findChildren(CollapsibleVersionGroup)
            if not g.is_collapsed
        }
        # Repainting each intermediate state of a teardown-and-rebuild is pure waste;
        # draw once at the end instead.
        self.ver_list_widget.setUpdatesEnabled(False)
        try:
            self._rebuild_version_list(inst_dir, prev_open_folders)
        finally:
            self.ver_list_widget.setUpdatesEnabled(True)

        if scroll_bar is not None and prev_scroll:
            from PySide6.QtCore import QTimer
            # After the layout has settled, or the maximum is still 0 and the value
            # would be clamped away.
            QTimer.singleShot(0, lambda: scroll_bar.setValue(min(prev_scroll, scroll_bar.maximum())))

    def _rebuild_version_list(self, inst_dir, prev_open_folders):
        meta = version_store.get_institution_meta(self._selected_slug)
        inst_name = meta.get("name", self._selected_slug)
        is_prim = bool(meta.get("is_primary", False))
        
        self.right_title.setText(f"{inst_name}")
        self.pwd_card_title.setText(f"{inst_name}")
        
        if is_prim:
            self.primary_inst_badge.show()
            self.btn_set_primary.hide()
        else:
            self.primary_inst_badge.hide()
            if self.is_master_admin:
                self.btn_set_primary.show()
            else:
                self.btn_set_primary.hide()
        
        # Completely and cleanly clear all existing items from layout without creating floating windows
        while self.ver_list_layout.count() > 0:
            item = self.ver_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.hide()
        versions = version_store.list_versions(self._selected_slug, source_filter="all")
        active_ver = version_store.get_active_version(self._selected_slug)
        
        self.ver_count_lbl.setText(f"{len(versions)} versiyon")
        
        last_upd = meta.get("last_updated_str")
        if not last_upd and versions:
            last_upd = f"{versions[0]['date_str']} {versions[0]['time_str']}"
        if last_upd:
            self.last_update_badge.setText(f"•   Son güncelleme: {last_upd}")
            self.last_update_badge.show()
        else:
            self.last_update_badge.hide()
            
        if hasattr(self, "footer_lbl"):
            self.footer_lbl.setText(f"© {datetime.now().year} {inst_name}")
        
        folders = version_store.list_folders(self._selected_slug)
        folder_order = [f["id"] for f in folders]
        folder_names = {f["id"]: f.get("name", "") for f in folders}

        if not versions and not folders:
            empty_box = QFrame()
            empty_box.setStyleSheet(f"background: #FFFFFF; border: 1px dashed {BORDER_HAIRLINE}; border-radius: 12px; padding: 40px;")
            el = QVBoxLayout(empty_box)
            el.setAlignment(Qt.AlignCenter)
            el.setSpacing(8)

            el_txt = QLabel("Bu kurumda henüz versiyon bulunmuyor.\n'Yeni Boş Çizelge' butonuna basarak başlayabilirsiniz.")
            el_txt.setFont(QFont("Segoe UI", 11))
            el_txt.setStyleSheet(f"color: {TEXT_SECONDARY};")
            el_txt.setAlignment(Qt.AlignCenter)
            el.addWidget(el_txt)

            self.ver_list_layout.addWidget(empty_box)
        else:
            table_card = QFrame()
            table_card.setStyleSheet("""
                QFrame {
                    background: #FFFFFF;
                    border: 1px solid #EBEBEB;
                    border-radius: 12px;
                }
            """)
            table_lay = QVBoxLayout(table_card)
            table_lay.setContentsMargins(0, 0, 0, 0)
            table_lay.setSpacing(0)

            def _wire(row):
                row.selected.connect(self._on_version_selected)
                row.double_clicked.connect(self._on_version_double_clicked)
                row.action_requested.connect(self._on_version_action)
                if row.filename == self._selected_version:
                    row.set_selected(True)
                return row

            def _add_group(title, icon, color, items, folder_id=None, show_folder_actions=False):
                keep_open = folder_id in prev_open_folders or any(
                    v["filename"] == self._selected_version for v in items
                )
                group = CollapsibleVersionGroup(
                    title, icon, f"{len(items)} versiyon", color, is_collapsed=not keep_open,
                    folder_id=folder_id, is_drop_target=True, show_folder_actions=show_folder_actions,
                )
                for v in items:
                    is_act = (v["filename"] == active_ver)
                    group.content_lay.addWidget(
                        _wire(AppleVersionRow(self._selected_slug, v, is_active=is_act))
                    )
                group.version_dropped.connect(
                    lambda slug, filename, fid=folder_id: self._on_version_dropped_on_folder(slug, filename, fid)
                )
                if show_folder_actions:
                    group.rename_requested.connect(lambda fid=folder_id, name=title: self._on_folder_rename(fid, name))
                    group.delete_requested.connect(lambda fid=folder_id, name=title: self._on_folder_delete(fid, name))
                table_lay.addWidget(group)

            if not folder_order:
                # 1. No folders created yet: Show Active at top and History below
                active_list = [v for v in versions if v["filename"] == active_ver]
                older_list = [v for v in versions if v["filename"] != active_ver]
                if active_list:
                    _add_group("Aktif Çizelge", "active", "#1A1A1A", active_list, folder_id="active", show_folder_actions=False)
                if older_list:
                    _add_group("Geçmiş Versiyonlar", "history", "#1A1A1A", older_list, folder_id=None, show_folder_actions=False)
            else:
                # 2. Folders exist: Group EVERY version (including active ones) into their folders or Klasörsüz!
                by_folder = {fid: [] for fid in folder_order}
                unfoldered = []
                for v in versions:
                    fid = v.get("folder_id")
                    if fid and fid in folder_names:
                        by_folder.setdefault(fid, []).append(v)
                    else:
                        unfoldered.append(v)

                for fid in folder_order:
                    _add_group(folder_names[fid], "folder", "#1A1A1A", by_folder.get(fid, []), folder_id=fid, show_folder_actions=True)

                _add_group("Klasörsüz (Eski Sürümler)", "history", "#1A1A1A", unfoldered, folder_id=None)

            self.ver_list_layout.addWidget(table_card)

        self.ver_list_layout.addStretch(1)
                
        # Password Protection with Full Coverage Modal in Stack
        is_locked = version_store.has_institution_password(self._selected_slug) and (self._selected_slug not in self._unlocked_slugs)
        if is_locked:
            self.pwd_card_title.setText(f"{inst_name}")
            self.pwd_err_lbl.hide()
            self.pwd_card_input.clear()
            self.pwd_card_input.setStyleSheet("""
                QLineEdit {
                    border: 1.5px solid #CBD5E1;
                    border-radius: 8px;
                    padding: 4px 12px;
                    font-size: 13px;
                    background: #F8FAFC;
                    color: #0F172A;
                }
                QLineEdit:focus {
                    border: 1.5px solid #0071E3;
                    background: #FFFFFF;
                }
            """)
            self.btn_new_empty.setEnabled(False)
            self.right_content_widget.hide()
            self.password_overlay_widget.show()
            # Retain focus if search input is being used
            if not self.search_input.hasFocus():
                self.pwd_card_input.setFocus()
        else:
            self.btn_new_empty.setEnabled(True)
            self.password_overlay_widget.hide()
            self.right_content_widget.show()
            
    def _on_version_selected(self, filename):
        if self._selected_version == filename:
            return
        self._selected_version = filename
        # set_selected is a no-op unless the state actually changes, so this only
        # restyles the row losing selection and the row gaining it — not all of them.
        for row in self.findChildren(AppleVersionRow):
            row.set_selected(row.filename == filename)
                
    def _on_version_double_clicked(self, slug, filename):
        self.open_timetable.emit(slug, filename)
        
    def _on_version_action(self, action, slug, filename):
        if action == "open":
            self.open_timetable.emit(slug, filename)
        elif action == "set_active":
            from save_dialog import run_apple_save_sequence
            run_apple_save_sequence(self, duration_seconds=1.0, title="Aktif Çizelge Güncelleniyor", message="Seçilen versiyon yayına alınıyor...")
            version_store.set_active_version(slug, filename)
            self._refresh_versions()
            self._refresh_institutions()
        elif action == "delete":
            import re
            m = re.match(r"v(\d+)_", filename)
            v_label = f"Versiyon {int(m.group(1))}" if m else filename
            dlg = AppleConfirmDialog(
                title="Versiyonu Sil",
                message=f"'{v_label}' kalıcı olarak silinecek ve bulut veritabanından kaldırılacaktır. Devam etmek istiyor musunuz?",
                confirm_text="Versiyonu Sil",
                cancel_text="Vazgeç",
                is_destructive=True,
                parent=self
            )
            if dlg.exec() == QDialog.Accepted:
                version_store.delete_version(slug, filename)
                self._refresh_versions()
                self._refresh_institutions()
                
    def _on_new_institution_clicked(self):
        dlg = AppleNewInstitutionDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            name = data["name"]
            color = data["color"]
            pwd = data["password"]
            
            from save_dialog import run_apple_save_sequence
            run_apple_save_sequence(self, duration_seconds=0.25, title="Kurum Oluşturuluyor", message=f"'{name}' sisteme ve buluta kaydediliyor...")
            
            inst = version_store.create_institution(name, color=color, password=pwd)
            self._selected_slug = inst["slug"]
            
            if self.auth_data and not self.auth_data.get("is_offline"):
                from cloud_sync import push_institution_to_rtdb
                push_institution_to_rtdb(inst["slug"], self.auth_data)
                
            self._refresh_institutions()
            
    def _on_new_empty_clicked(self):
        if not self._selected_slug:
            return
        from save_dialog import run_apple_save_sequence
        run_apple_save_sequence(self, duration_seconds=0.25, title="Yeni Çizelge Hazırlanıyor", message="Boş çalışma alanı oluşturuluyor...")
        self.new_empty_timetable.emit(self._selected_slug)
        
    def _on_cross_import_clicked(self):
        if not self._selected_slug:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce hedef bir kurum seçin.")
            return
            
        dlg = CrossImportDialog(self._selected_slug, parent=self)
        if dlg.exec() == QDialog.Accepted:
            sel = dlg.get_selection()
            src_slug = sel["source_slug"]
            if not src_slug:
                return
                
            from save_dialog import run_apple_save_sequence
            run_apple_save_sequence(self, duration_seconds=1.2, title="Veriler Aktarılıyor", message="Tanımlar kopyalanıyor ve buluta eşitleniyor...")
            
            ok, msg, _ = version_store.import_master_data_from_institution(
                target_slug=self._selected_slug,
                source_slug=src_slug,
                include_subjects=sel["subjects"],
                include_classes=sel["classes"],
                include_rooms=sel["rooms"],
                include_teachers=sel["teachers"],
                include_assignments=sel["assignments"]
            )
            
            if ok:
                show_apple_info(self, "Aktarım Başarılı", msg, is_success=True)
                self._refresh_versions()
                self._refresh_institutions()
            else:
                show_apple_info(self, "Hata", msg, is_success=False)

    def _manual_cloud_sync(self):
        """Sync now, without freezing the window while the network works.

        The previous version spun `processEvents(); time.sleep(0.03)` on the GUI
        thread until the worker finished, then padded any run shorter than 1.2s with
        a flat `time.sleep` so the progress card would "look busy". The window was
        unresponsive for the whole time and, on a fast connection, most of that time
        was the padding.

        The worker still runs off-thread; results now come back through a signal and
        the card closes as soon as the work is genuinely done.
        """
        if getattr(self, "_sync_in_flight", False):
            return  # already syncing — don't stack a second worker on top
        self._sync_in_flight = True

        from save_dialog import AppleSaveDialog
        from cloud_sync import push_all_to_rtdb, pull_all_from_rtdb
        import threading

        dlg = AppleSaveDialog(
            title="Bulut Senkronizasyonu",
            message="Merkezi veritabanı ile eşitleniyor...",
            parent=self,
        )
        dlg.show()

        def _finish(pull_ok, pull_msg, push_ok, push_msg):
            self._sync_in_flight = False
            try:
                dlg.close()
                dlg.deleteLater()
            except Exception:
                pass

            self._refresh_institutions()
            if self._selected_slug:
                self._refresh_versions()

            if pull_ok or push_ok:
                show_apple_info(
                    self, "Bulut Senkronizasyonu",
                    f"{push_msg}\n{pull_msg}\nTüm cihazlar ve geçmiş versiyonlar başarıyla eşitlendi.",
                    is_success=True,
                )
            else:
                show_apple_info(
                    self, "Bulut Uyarısı",
                    f"{pull_msg or 'Bağlantı kurulamadı.'}\nLütfen internet bağlantınızı kontrol edin.",
                    is_success=False,
                )

        def _sync_worker():
            try:
                pull_ok, pull_msg, _ = pull_all_from_rtdb(self.auth_data)
                push_ok, push_msg, _ = push_all_to_rtdb(self.auth_data)
            except Exception as exc:
                pull_ok, push_ok = False, False
                pull_msg, push_msg = f"Bağlantı hatası: {exc}", ""
            # Hop back to the GUI thread — touching widgets from a worker thread is
            # undefined behaviour in Qt and a real source of random crashes.
            self.sync_finished.emit(bool(pull_ok), pull_msg or "", bool(push_ok), push_msg or "")

        try:
            self.sync_finished.disconnect()
        except Exception:
            pass
        self.sync_finished.connect(_finish)

        threading.Thread(target=_sync_worker, daemon=True).start()
