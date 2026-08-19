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
    QLineEdit, QDialog, QCheckBox, QGraphicsDropShadowEffect, QGraphicsBlurEffect,
    QStackedLayout, QMenu, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize, QRectF
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QIcon, QPixmap,
    QPainterPath, QLinearGradient, QRadialGradient
)

import version_store

# ── Apple Design Tokens ──────────────────────────────────────────────
BG_CANVAS        = "#F5F5F7"  # Apple Canvas Gray
BG_CARD          = "#FFFFFF"  # Apple Card Pure White
BG_SIDEBAR       = "#FFFFFF"  # Sidebar White
BORDER_HAIRLINE  = "#E5E5EA"  # Apple Hairline Border
BORDER_SUBTLE    = "rgba(0, 0, 0, 0.08)"
TEXT_PRIMARY     = "#1D1D1F"  # Apple Charcoal Dark
TEXT_SECONDARY   = "#86868B"  # Apple Slate Gray
TEXT_MUTED       = "#AEAEB2"  # Apple Light Muted
APPLE_BLUE       = "#0071E3"  # Apple Signature Blue
APPLE_GREEN      = "#34C759"  # Apple Green
APPLE_AMBER      = "#FF9500"  # Apple Amber
APPLE_RED        = "#FF3B30"  # Apple Red
APPLE_PURPLE     = "#AF52DE"  # Apple Purple

FONT_FAMILY = '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", sans-serif'

# ── 3D Institution Icon Painter ──────────────────────────────────────

def make_3d_institution_icon(inst_name: str, color_hex: str = "#0071E3", size: int = 40) -> QPixmap:
    """Draws a mathematically centered, scalable 3D isometric academy icon."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    
    # 1. Base rounded rectangle tile
    grad_bg = QLinearGradient(0, 0, size, size)
    c_base = QColor(color_hex)
    grad_bg.setColorAt(0.0, c_base.lighter(130))
    grad_bg.setColorAt(0.7, c_base)
    grad_bg.setColorAt(1.0, c_base.darker(115))
    
    pad = max(1.5, size * 0.04)
    tile_rect = QRectF(pad, pad, size - 2 * pad, size - 2 * pad)
    radius = size * 0.26
    
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(grad_bg))
    p.drawRoundedRect(tile_rect, radius, radius)
    
    # Highlight bevel (subtle top glass edge)
    p.setPen(QPen(QColor(255, 255, 255, 100), max(1.0, size * 0.025)))
    p.drawRoundedRect(QRectF(pad + 0.5, pad + 0.5, size - 2 * pad - 1, size - 2 * pad - 1), radius - 1, radius - 1)
    
    # 2. Centered Classical Building (normalized scale)
    cx = size / 2.0
    cy = size / 2.0
    
    w = size * 0.54  # building total width
    h = size * 0.54  # building total height
    top_y = cy - h * 0.48
    
    # A. Roof Triangle (Gable)
    roof = QPainterPath()
    roof.moveTo(cx, top_y)
    roof.lineTo(cx + w * 0.5, top_y + h * 0.26)
    roof.lineTo(cx - w * 0.5, top_y + h * 0.26)
    roof.closeSubpath()
    
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 255))
    p.drawPath(roof)
    
    # B. Architrave / Cornice Beam
    beam_y = top_y + h * 0.28
    beam_h = max(2.0, h * 0.08)
    p.setBrush(QColor(255, 255, 255, 220))
    p.drawRoundedRect(QRectF(cx - w * 0.46, beam_y, w * 0.92, beam_h), 1, 1)
    
    # C. Columns (3 pillars evenly centered)
    col_y = beam_y + beam_h + h * 0.04
    col_h = h * 0.36
    col_w = max(2.5, w * 0.16)
    
    left_x = cx - w * 0.38
    center_x = cx - col_w / 2.0
    right_x = cx + w * 0.38 - col_w
    
    p.setBrush(QColor(255, 255, 255, 245))
    p.drawRoundedRect(QRectF(left_x, col_y, col_w, col_h), 1, 1)
    p.drawRoundedRect(QRectF(center_x, col_y, col_w, col_h), 1, 1)
    p.drawRoundedRect(QRectF(right_x, col_y, col_w, col_h), 1, 1)
    
    # D. Steps / Foundation
    step1_y = col_y + col_h + h * 0.02
    step1_h = max(2.0, h * 0.08)
    p.setBrush(QColor(255, 255, 255, 225))
    p.drawRoundedRect(QRectF(cx - w * 0.44, step1_y, w * 0.88, step1_h), 1, 1)
    
    step2_y = step1_y + step1_h + 1
    step2_h = max(2.0, h * 0.08)
    p.setBrush(QColor(255, 255, 255, 250))
    p.drawRoundedRect(QRectF(cx - w * 0.50, step2_y, w, step2_h), 1, 1)
    
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

class AppleInfoDialog(QDialog):
    def __init__(self, title: str, message: str, is_success: bool = True, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(400, 230)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        container = QWidget(self)
        container.setObjectName("infoCard")
        container.setStyleSheet("""
            #infoCard {
                background: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)
        
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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        container = QWidget(self)
        container.setObjectName("confirmCard")
        container.setStyleSheet("""
            #confirmCard {
                background: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 18px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)
        
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
        btn_box.setSpacing(12)
        
        btn_cancel = QPushButton(cancel_text)
        btn_cancel.setFixedHeight(34)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F2F2F7; color: #1D1D1F; border: 1px solid #E5E5EA;
                border-radius: 8px; padding: 6px 18px; font-weight: 500;
            }
            QPushButton:hover { background: #E5E5EA; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        btn_ok = QPushButton(confirm_text)
        btn_ok.setFixedHeight(34)
        bg_col = "#FF3B30" if is_destructive else "#0071E3"
        hover_col = "#DC2626" if is_destructive else "#0062C4"
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background: {bg_col}; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 6px 20px; font-weight: 600;
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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.selected_color = current_color
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        container = QWidget(self)
        container.setObjectName("colorCard")
        container.setStyleSheet("""
            #colorCard {
                background: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)
        
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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.selected_color = "#0071E3"
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        container = QWidget(self)
        container.setObjectName("modalCard")
        container.setStyleSheet("""
            #modalCard {
                background: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 20px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 10)
        container.setGraphicsEffect(shadow)
        
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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        container = QWidget(self)
        container.setObjectName("inputCard")
        container.setStyleSheet("""
            #inputCard {
                background: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)
        
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
        self.inst_color = inst_data.get("color", APPLE_BLUE)
        self.has_password = inst_data.get("has_password", False)
        self._selected = is_selected
        self.is_master_admin = is_master_admin
        
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(58)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self._update_style()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)
        
        # 3D Institution Icon
        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_3d_institution_icon(self.inst_name, self.inst_color, 36))
        icon_lbl.setFixedSize(36, 36)
        layout.addWidget(icon_lbl)
        
        # Text Info
        t_layout = QVBoxLayout()
        t_layout.setSpacing(1)
        t_layout.setContentsMargins(0, 1, 0, 1)
        
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        
        name_lbl = ElidedLabel(self.inst_name)
        name_lbl.setFont(QFont("Segoe UI", 9.5, QFont.Bold))
        name_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; border: none;")
        name_row.addWidget(name_lbl, 1)
        
        if self.has_password:
            lock_badge = QLabel("Kilitli")
            lock_badge.setFont(QFont("Segoe UI", 7, QFont.Bold))
            lock_badge.setStyleSheet("background: #F2F2F7; color: #8E8E93; padding: 1px 5px; border-radius: 4px; border: none;")
            name_row.addWidget(lock_badge)
            
        t_layout.addLayout(name_row)
        
        v_count = inst_data.get("version_count", 0)
        upd = inst_data.get("last_updated_str", "")
        if upd:
            sub_lbl = QLabel(f"{v_count} versiyon • {upd}")
        else:
            sub_lbl = QLabel(f"{v_count} versiyon")
        sub_lbl.setFont(QFont("Segoe UI", 8))
        sub_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")
        t_layout.addWidget(sub_lbl)
        
        layout.addLayout(t_layout, 1)
    
    def _update_style(self):
        if self._selected:
            self.setStyleSheet(f"""
                AppleInstitutionCard {{
                    background: #F0F6FF;
                    border: 1.5px solid {APPLE_BLUE};
                    border-radius: 10px;
                }}
                AppleInstitutionCard:hover {{ background: #E6F0FE; }}
            """)
        else:
            self.setStyleSheet(f"""
                AppleInstitutionCard {{
                    background: #FFFFFF;
                    border: 1px solid {BORDER_HAIRLINE};
                    border-radius: 10px;
                }}
                AppleInstitutionCard:hover {{
                    background: #F8FAFC;
                    border: 1px solid #CBD5E1;
                }}
            """)
            
    def set_selected(self, selected):
        self._selected = selected
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
        act_rename = menu.addAction("Yeniden Adlandır")
        act_color = menu.addAction("Renk Değiştir")
        
        menu.addSeparator()
        if self.is_master_admin:
            if self.has_password:
                act_pwd = menu.addAction("Şifreyi Değiştir")
                act_rm_pwd = menu.addAction("Şifreyi Kaldır")
            else:
                act_pwd = menu.addAction("Şifre Belirle (Yönetici)")
                act_rm_pwd = None
        else:
            act_pwd = None
            act_rm_pwd = None
            
        act_delete = None
        if self.is_master_admin:
            menu.addSeparator()
            act_delete = menu.addAction("Kurumu Sil")
        
        action = menu.exec_(self.mapToGlobal(pos))
        if action == act_rename:
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
    else:
        p.setBrush(QBrush(c))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(3, 3, size - 6, size - 6))
        
    p.end()
    return pix

def get_user_display_name(email: str, parent=None) -> str:
    clean_email = (email or "").strip().lower()
    if not clean_email or clean_email in ("admin@bgz.local", "admin", "yonetici", "admin@chenki.net"):
        return "Seher Şanlı"
    
    profiles_path = "bgz_user_profiles.json"
    profiles = {}
    if os.path.exists(profiles_path):
        try:
            with open(profiles_path, "r", encoding="utf-8") as f:
                profiles = json.load(f)
        except Exception:
            profiles = {}
            
    if clean_email in profiles and profiles[clean_email].get("name"):
        return profiles[clean_email]["name"]
        
    if parent:
        from PySide6.QtWidgets import QInputDialog
        dlg = QInputDialog(parent)
        dlg.setWindowTitle("Kullanıcı Profili")
        dlg.setLabelText(f"Hoşgeldiniz!\nSayın {clean_email}, lütfen adınızı ve soyadınızı giriniz:")
        dlg.setTextValue(clean_email.split("@")[0].capitalize())
        if dlg.exec() == QDialog.Accepted and dlg.textValue().strip():
            name = dlg.textValue().strip()
        else:
            name = clean_email.split("@")[0].capitalize()
    else:
        name = clean_email.split("@")[0].capitalize()
        
    profiles[clean_email] = {"name": name, "email": clean_email}
    try:
        with open(profiles_path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return name

# ── Collapsible Version Group with Chevron ───────────────────────────

class CollapsibleVersionGroup(QFrame):
    def __init__(self, title: str, icon_name: str, badge_text: str, color_hex: str = "#0071E3", is_collapsed: bool = False, parent=None):
        super().__init__(parent)
        self.is_collapsed = is_collapsed
        self.color_hex = color_hex
        self.setStyleSheet(f"""
            CollapsibleVersionGroup {{
                background: #FFFFFF;
                border: 1px solid {BORDER_HAIRLINE};
                border-radius: 10px;
            }}
        """)
        
        self.main_lay = QVBoxLayout(self)
        self.main_lay.setContentsMargins(12, 10, 12, 10)
        self.main_lay.setSpacing(6)
        
        # Header Button / Frame
        self.header = QFrame()
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.setStyleSheet("background: transparent; border: none;")
        hdr_lay = QHBoxLayout(self.header)
        hdr_lay.setContentsMargins(2, 2, 2, 2)
        hdr_lay.setSpacing(10)
        
        # Icon
        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_dashboard_icon(icon_name, color_hex, 18))
        hdr_lay.addWidget(icon_lbl)
        
        # Title
        title_lbl = QLabel(f"<b>{title}</b>")
        title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        hdr_lay.addWidget(title_lbl)
        
        # Badge
        if badge_text:
            badge = QLabel(badge_text)
            badge.setFont(QFont("Segoe UI", 8, QFont.Bold))
            badge.setStyleSheet("background: #F2F2F7; color: #636366; padding: 2px 8px; border-radius: 5px;")
            hdr_lay.addWidget(badge)
            
        hdr_lay.addStretch(1)
        
        # Chevron icon
        self.chevron_lbl = QLabel()
        self.chevron_lbl.setPixmap(make_dashboard_icon("chevron_right" if is_collapsed else "chevron_down", "#86868B", 14))
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
        
    def _toggle_collapse(self, event):
        self.is_collapsed = not self.is_collapsed
        self.content_widget.setVisible(not self.is_collapsed)
        self.chevron_lbl.setPixmap(make_dashboard_icon("chevron_right" if self.is_collapsed else "chevron_down", "#64748B", 14))

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
        self.setFixedHeight(44)
        self._update_style()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 4, 14, 4)
        layout.setSpacing(12)
        
        # Version Title: "Versiyon 10"
        num = version_info.get("number", 0)
        v_title = QLabel(f"Versiyon {num}")
        v_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        v_title.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; border: none;")
        v_title.setFixedWidth(90)
        layout.addWidget(v_title)
        
        # Date & Time (Clean single block)
        d_str = version_info.get("date_str", "")
        t_str = version_info.get("time_str", "")
        dt_lbl = QLabel(f"{d_str}  {t_str}")
        dt_lbl.setFont(QFont("Segoe UI", 8.5))
        dt_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")
        dt_lbl.setFixedWidth(145)
        layout.addWidget(dt_lbl)
        
        # Details: Unplaced stats badge + Note
        tot = version_info.get("total_hours", 0)
        plc = version_info.get("placed_hours", 0)
        unp = version_info.get("unplaced_hours", 0)
        
        if tot > 0:
            if unp == 0:
                stats_badge = QLabel(f"{tot} Saat • Tamamı Yerleşti")
                stats_badge.setFont(QFont("Segoe UI", 8, QFont.Bold))
                stats_badge.setStyleSheet("background: #E8F8EE; color: #1E7E34; padding: 2px 7px; border-radius: 5px;")
            else:
                stats_badge = QLabel(f"{plc}/{tot} Saat • {unp} Artan")
                stats_badge.setFont(QFont("Segoe UI", 8, QFont.Bold))
                stats_badge.setStyleSheet("background: #FFF7ED; color: #C2410C; padding: 2px 7px; border-radius: 5px;")
        else:
            stats_badge = QLabel("Boş Çizelge")
            stats_badge.setFont(QFont("Segoe UI", 7.5))
            stats_badge.setStyleSheet("background: #F1F5F9; color: #64748B; padding: 2px 7px; border-radius: 5px;")
            
        layout.addWidget(stats_badge)
        
        note_text = version_info.get("note", "")
        if note_text:
            from PySide6.QtGui import QFontMetrics
            fm = QFontMetrics(QFont("Segoe UI", 8))
            elided_note = fm.elidedText(note_text, Qt.ElideRight, 200)
            note_lbl = QLabel(elided_note)
            note_lbl.setToolTip(note_text)
            note_lbl.setFont(QFont("Segoe UI", 8))
            note_lbl.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent; border: none;")
            note_lbl.setMaximumWidth(200)
            layout.addWidget(note_lbl)
        layout.addStretch(1)
            
        # File Size
        size_lbl = QLabel(f"{version_info.get('size_kb', 0)} KB")
        size_lbl.setFont(QFont("Segoe UI", 8))
        size_lbl.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent; border: none;")
        size_lbl.setFixedWidth(50)
        size_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(size_lbl)
        
        # Active Status Indicator
        if is_active:
            act_badge = QLabel("● Aktif")
            act_badge.setFont(QFont("Segoe UI", 8, QFont.Bold))
            act_badge.setStyleSheet(f"background: #E8F8EE; color: #1E7E34; padding: 3px 8px; border-radius: 5px; border: none;")
            layout.addWidget(act_badge)
        else:
            btn_make_act = QPushButton("Aktif Yap")
            btn_make_act.setFont(QFont("Segoe UI", 8))
            btn_make_act.setCursor(Qt.PointingHandCursor)
            btn_make_act.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {TEXT_SECONDARY}; border: 1px solid {BORDER_HAIRLINE};
                    border-radius: 5px; padding: 3px 8px;
                }}
                QPushButton:hover {{ background: #E5E5EA; color: {TEXT_PRIMARY}; }}
            """)
            btn_make_act.clicked.connect(lambda: self.action_requested.emit("set_active", self.slug, self.filename))
            layout.addWidget(btn_make_act)
            
        # Open Button
        btn_open = QPushButton("Aç")
        btn_open.setFont(QFont("Segoe UI", 8.5, QFont.Bold))
        btn_open.setCursor(Qt.PointingHandCursor)
        btn_open.setStyleSheet(f"""
            QPushButton {{
                background: {APPLE_BLUE}; color: #FFFFFF; border: none;
                border-radius: 5px; padding: 4px 14px;
            }}
            QPushButton:hover {{ background: #0062C4; }}
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
                background: transparent; color: #EF4444; border: 1px solid #FECACA;
                border-radius: 5px; padding: 4px 8px;
            }
            QPushButton:hover { background: #FEF2F2; color: #DC2626; border-color: #EF4444; }
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
        act_del = menu.addAction("Versiyonu Sil")
        
        action = menu.exec_(self.mapToGlobal(pos))
        if action == act_open:
            self.action_requested.emit("open", self.slug, self.filename)
        elif act_active and action == act_active:
            self.action_requested.emit("set_active", self.slug, self.filename)
        elif action == act_del:
            self.action_requested.emit("delete", self.slug, self.filename)
        
    def _update_style(self):
        if self._is_active:
            self.setStyleSheet(f"""
                AppleVersionRow {{
                    background: #F0F6FF; border: 1.5px solid {APPLE_BLUE}; border-radius: 8px;
                }}
                AppleVersionRow:hover {{ background: #E6F0FE; }}
            """)
        elif self._is_selected:
            self.setStyleSheet(f"""
                AppleVersionRow {{
                    background: #F2F2F7; border: 1px solid #D1D1D6; border-radius: 8px;
                }}
                AppleVersionRow:hover {{ background: #E5E5EA; }}
            """)
        else:
            self.setStyleSheet(f"""
                AppleVersionRow {{
                    background: #FFFFFF; border: 1px solid {BORDER_HAIRLINE}; border-radius: 8px;
                }}
                AppleVersionRow:hover {{ background: #F8FAFC; border: 1px solid #D1D5DB; }}
            """)
            
    def set_selected(self, sel):
        self._is_selected = sel
        self._update_style()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.filename)
        super().mousePressEvent(event)
        
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.slug, self.filename)
        super().mouseDoubleClickEvent(event)


# ── Main Home Dashboard ──────────────────────────────────────────────

class HomeDashboard(QWidget):
    open_timetable = Signal(str, str)  # slug, filename
    new_empty_timetable = Signal(str)  # slug
    logout_requested = Signal()        # Trigger logout & return to login screen
    
    def __init__(self, auth_data=None, parent=None):
        super().__init__(parent)
        self.auth_data = auth_data or {}
        self._selected_slug = None
        self._selected_version = None
        self._search_query = ""
        self._unlocked_slugs = set()
        
        user_email = self.auth_data.get("email", "").lower()
        user_role = self.auth_data.get("role", "").lower()
        is_guest = bool(self.auth_data.get("is_guest") or self.auth_data.get("is_shared") or user_role in ["guest", "shared"])
        # Master admin can delete institutions and change/remove passwords; shared/guest accounts cannot
        self.is_master_admin = True if ("admin" in user_email or not user_email or not is_guest) else False
        self.display_name = get_user_display_name(user_email, self)
        
        version_store.migrate_existing_data()
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
            
    def _start_initial_cloud_sync(self):
        import threading
        from cloud_sync import push_all_to_rtdb, pull_all_from_rtdb
        from PySide6.QtCore import QTimer
        
        def _worker():
            try:
                # 1. Push any local versions to VDS
                push_all_to_rtdb(self.auth_data)
                # 2. Pull all remote institutions and versions from VDS
                ok, _, _ = pull_all_from_rtdb(self.auth_data)
                if ok:
                    QTimer.singleShot(0, self._on_cloud_synced)
            except Exception as e:
                print(f"[HomeDashboard] Cloud sync note: {e}")
                
        threading.Thread(target=_worker, daemon=True).start()
        
    def _on_cloud_synced(self):
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
        top_bar.setFixedHeight(56)
        top_bar.setStyleSheet(f"background: {BG_CARD}; border-bottom: 1px solid {BORDER_HAIRLINE};")
        
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 20, 0)
        top_layout.setSpacing(14)
        
        brand_lbl = QLabel("Anasayfa")
        brand_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        brand_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        top_layout.addWidget(brand_lbl)
        
        top_layout.addSpacing(20)
        
        # Search Box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Kurum veya versiyon ara...")
        self.search_input.setFixedWidth(280)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: #E8E8ED; border: 1px solid transparent;
                border-radius: 8px; padding: 6px 12px; font-size: 12px; color: {TEXT_PRIMARY};
            }}
            QLineEdit:focus {{ background: #FFFFFF; border: 1.5px solid {APPLE_BLUE}; }}
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        top_layout.addWidget(self.search_input)
        
        top_layout.addStretch(1)
        
        # Profile Greeting
        user_lbl = QLabel(f"Hoşgeldiniz, <b>{self.display_name}</b>")
        user_lbl.setFont(QFont("Segoe UI", 9.5))
        user_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        top_layout.addWidget(user_lbl)
        
        if self.is_master_admin:
            admin_badge = QLabel("Ana Yönetici")
            admin_badge.setFixedHeight(22)
            admin_badge.setFont(QFont("Segoe UI", 8, QFont.Bold))
            admin_badge.setStyleSheet("background: #F2F2F7; color: #1D1D1F; padding: 2px 8px; border-radius: 5px; border: 1px solid #E5E5EA;")
            top_layout.addWidget(admin_badge)
            
        btn_cloud_sync = QPushButton("Bulut Eşitle")
        btn_cloud_sync.setFont(QFont("Segoe UI", 9, QFont.Bold))
        btn_cloud_sync.setCursor(Qt.PointingHandCursor)
        btn_cloud_sync.setStyleSheet(f"""
            QPushButton {{
                background: #F2F2F7; color: {APPLE_BLUE}; border: 1px solid {BORDER_HAIRLINE};
                border-radius: 8px; padding: 6px 14px;
            }}
            QPushButton:hover {{ background: #E5E5EA; }}
        """)
        btn_cloud_sync.clicked.connect(self._manual_cloud_sync)
        top_layout.addWidget(btn_cloud_sync)
        
        btn_import = QPushButton("Veri Aktar")
        btn_import.setFont(QFont("Segoe UI", 9, QFont.Bold))
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.setStyleSheet(f"""
            QPushButton {{
                background: #F2F2F7; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_HAIRLINE};
                border-radius: 8px; padding: 6px 14px;
            }}
            QPushButton:hover {{ background: #E5E5EA; }}
        """)
        btn_import.clicked.connect(self._on_cross_import_clicked)
        top_layout.addWidget(btn_import)
        
        btn_new_inst = QPushButton("+ Yeni Kurum")
        btn_new_inst.setFont(QFont("Segoe UI", 9, QFont.Bold))
        btn_new_inst.setCursor(Qt.PointingHandCursor)
        btn_new_inst.setStyleSheet(f"""
            QPushButton {{
                background: {APPLE_BLUE}; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 6px 16px;
            }}
            QPushButton:hover {{ background: #0062C4; }}
        """)
        btn_new_inst.clicked.connect(self._on_new_institution_clicked)
        top_layout.addWidget(btn_new_inst)
        
        # Logout Button
        btn_logout = QPushButton("Çıkış Yap")
        btn_logout.setFont(QFont("Segoe UI", 8.5, QFont.Bold))
        btn_logout.setFixedHeight(30)
        btn_logout.setCursor(Qt.PointingHandCursor)
        btn_logout.setStyleSheet("""
            QPushButton {
                background: #F2F2F7; color: #FF3B30; border: 1px solid #E5E5EA;
                border-radius: 6px; padding: 4px 12px;
            }
            QPushButton:hover { background: #FEE2E2; }
        """)
        btn_logout.clicked.connect(self._on_logout_clicked)
        top_layout.addWidget(btn_logout)
        
        root.addWidget(top_bar)
        
        # ── 2. Main Body ─────────────────────────────────────────
        main_hbox = QHBoxLayout()
        main_hbox.setContentsMargins(0, 0, 0, 0)
        main_hbox.setSpacing(0)
        
        # Left Sidebar (Institutions)
        left_panel = QFrame()
        left_panel.setFixedWidth(270)
        left_panel.setStyleSheet(f"background: {BG_SIDEBAR}; border-right: 1px solid {BORDER_HAIRLINE};")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 14, 12, 14)
        left_layout.setSpacing(8)
        
        left_hdr = QHBoxLayout()
        left_title = QLabel("KURUMLAR")
        left_title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        left_title.setStyleSheet(f"color: {TEXT_MUTED}; letter-spacing: 0.5px;")
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
        self.inst_list_layout.setSpacing(6)
        self.inst_list_layout.addStretch(1)
        
        scroll_inst.setWidget(self.inst_list_widget)
        left_layout.addWidget(scroll_inst, 1)
        
        main_hbox.addWidget(left_panel)
        
        # Right Area
        right_panel = QFrame()
        right_panel.setStyleSheet(f"background: {BG_CANVAS};")
        self.right_panel_layout = QVBoxLayout(right_panel)
        self.right_panel_layout.setContentsMargins(24, 20, 24, 20)
        self.right_panel_layout.setSpacing(14)
        
        # Header of Selected Institution
        right_hdr = QHBoxLayout()
        self.right_title = QLabel("Seçili Kurum")
        self.right_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.right_title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        right_hdr.addWidget(self.right_title)
        
        self.ver_count_lbl = QLabel("")
        self.ver_count_lbl.setFont(QFont("Segoe UI", 10))
        self.ver_count_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        right_hdr.addWidget(self.ver_count_lbl)
        
        self.last_update_badge = QLabel("")
        self.last_update_badge.setFont(QFont("Segoe UI", 8.5))
        self.last_update_badge.setStyleSheet("background: #F2F2F7; color: #636366; padding: 3px 10px; border-radius: 6px; font-weight: 500; border: 1px solid #E5E5EA;")
        right_hdr.addWidget(self.last_update_badge)
        right_hdr.addStretch(1)
        
        self.btn_new_empty = QPushButton("+ Yeni Boş Çizelge")
        self.btn_new_empty.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.btn_new_empty.setCursor(Qt.PointingHandCursor)
        self.btn_new_empty.setStyleSheet(f"""
            QPushButton {{
                background: #FFFFFF; color: {APPLE_BLUE}; border: 1px solid {BORDER_HAIRLINE};
                border-radius: 8px; padding: 6px 14px;
            }}
            QPushButton:hover {{ background: #F5F5F7; border: 1.5px solid {APPLE_BLUE}; }}
        """)
        self.btn_new_empty.clicked.connect(self._on_new_empty_clicked)
        right_hdr.addWidget(self.btn_new_empty)
        
        self.right_panel_layout.addLayout(right_hdr)
        
        # Versions Stack Container
        self.right_panel_stack = QStackedLayout()
        self.right_panel_layout.addLayout(self.right_panel_stack, 1)
        
        # Normal Versions List View
        self.right_content_widget = QWidget()
        self.right_content_layout = QVBoxLayout(self.right_content_widget)
        self.right_content_layout.setContentsMargins(0, 0, 0, 0)
        self.right_content_layout.setSpacing(10)
        
        scroll_ver = QScrollArea()
        scroll_ver.setWidgetResizable(True)
        scroll_ver.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.ver_list_widget = QWidget()
        self.ver_list_widget.setStyleSheet("background: transparent;")
        self.ver_list_layout = QVBoxLayout(self.ver_list_widget)
        self.ver_list_layout.setContentsMargins(0, 0, 0, 0)
        self.ver_list_layout.setSpacing(12)
        self.ver_list_layout.addStretch(1)
        
        scroll_ver.setWidget(self.ver_list_widget)
        self.right_content_layout.addWidget(scroll_ver, 1)
        self.right_panel_stack.addWidget(self.right_content_widget)
        
        # Password Protection Overlay Widget (Ultra-clean modern card)
        self.password_overlay_widget = QWidget()
        self.password_overlay_widget.setStyleSheet("background: transparent;")
        overlay_layout = QVBoxLayout(self.password_overlay_widget)
        overlay_layout.setAlignment(Qt.AlignCenter)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        
        # Modal Floating Card (Centered)
        self.pwd_card = QFrame()
        self.pwd_card.setObjectName("pwdCard")
        self.pwd_card.setFixedSize(480, 360)
        self.pwd_card.setStyleSheet("""
            QFrame#pwdCard {
                background: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 20px;
            }
        """)
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(40)
        card_shadow.setColor(QColor(0, 0, 0, 40))
        card_shadow.setOffset(0, 10)
        self.pwd_card.setGraphicsEffect(card_shadow)
        
        c_layout = QVBoxLayout(self.pwd_card)
        c_layout.setContentsMargins(40, 30, 40, 30)
        c_layout.setSpacing(16)
        c_layout.setAlignment(Qt.AlignCenter)
        
        lock_lbl = QLabel()
        lock_lbl.setPixmap(make_apple_lock_badge(44))
        lock_lbl.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(lock_lbl)
        
        self.pwd_card_title = QLabel("Kurum Şifresi Korumalı")
        self.pwd_card_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.pwd_card_title.setStyleSheet("color: #0F172A; font-weight: bold;")
        self.pwd_card_title.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(self.pwd_card_title)
        
        desc_lbl = QLabel("Bu kurumun ders çizelgelerine erişmek için\nlütfen kurum şifresini girin.")
        desc_lbl.setFont(QFont("Segoe UI", 9))
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
        self.pwd_err_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.pwd_err_lbl.setStyleSheet("color: #EF4444;")
        self.pwd_err_lbl.setAlignment(Qt.AlignCenter)
        self.pwd_err_lbl.hide()
        c_layout.addWidget(self.pwd_err_lbl)
        
        btn_unlock = QPushButton("Kilidi Aç ve Giriş Yap")
        btn_unlock.setFont(QFont("Segoe UI", 9.5, QFont.Bold))
        btn_unlock.setFixedHeight(36)
        btn_unlock.setCursor(Qt.PointingHandCursor)
        btn_unlock.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 4px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #0056B3; }
        """)
        btn_unlock.clicked.connect(self._on_submit_password_overlay)
        self.pwd_card_input.returnPressed.connect(self._on_submit_password_overlay)
        c_layout.addWidget(btn_unlock)
        
        overlay_layout.addWidget(self.pwd_card)
        self.password_overlay_widget.hide()
        self.right_panel_stack.addWidget(self.password_overlay_widget)
        
        main_hbox.addWidget(right_panel, 1) # right panel gets stretch
        root.addLayout(main_hbox, 1)

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
            self.pwd_err_lbl.hide()
            self.pwd_card_input.clear()
            self.right_panel_stack.setCurrentWidget(self.right_content_widget)
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
        self._unlocked_slugs.discard(slug)
        
        for i in range(self.inst_list_layout.count() - 1):
            w = self.inst_list_layout.itemAt(i).widget()
            if isinstance(w, AppleInstitutionCard):
                w.set_selected(w.slug == slug)
                
        self._refresh_versions()
        
    def _create_version_group_card(self, title: str, icon_name: str, badge_text: str, color_hex: str = "#0071E3"):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: #FFFFFF;
                border: 1px solid {BORDER_HAIRLINE};
                border-radius: 10px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)
        
        # Header
        hdr = QHBoxLayout()
        hdr.setContentsMargins(2, 2, 2, 4)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_dashboard_icon(icon_name, color_hex, 18))
        hdr.addWidget(icon_lbl)
        
        title_lbl = QLabel(f"<b>{title}</b>")
        title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; border: none;")
        hdr.addWidget(title_lbl)
        hdr.addStretch(1)
        
        if badge_text:
            badge = QLabel(badge_text)
            badge.setFont(QFont("Segoe UI", 8, QFont.Bold))
            badge.setStyleSheet("background: #EBF5FF; color: #0071E3; padding: 2px 8px; border-radius: 5px;")
            hdr.addWidget(badge)
            
        lay.addLayout(hdr)
        
        content_lay = QVBoxLayout()
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(5)
        lay.addLayout(content_lay)
        
        return card, content_lay

    def _refresh_versions(self):
        if not self._selected_slug:
            return
            
        meta = version_store.get_institution_meta(self._selected_slug)
        inst_name = meta.get("name", self._selected_slug)
        self.right_title.setText(f"{inst_name}")
        self.pwd_card_title.setText(f"{inst_name}")
        
        # Completely and cleanly clear all existing items from layout without creating floating windows
        while self.ver_list_layout.count() > 0:
            item = self.ver_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.deleteLater()
                
        versions = version_store.list_versions(self._selected_slug, source_filter="all")
        active_ver = version_store.get_active_version(self._selected_slug)
        
        self.ver_count_lbl.setText(f"•  {len(versions)} versiyon")
        
        last_upd = meta.get("last_updated_str")
        if not last_upd and versions:
            last_upd = f"{versions[0]['date_str']} {versions[0]['time_str']}"
        if last_upd:
            self.last_update_badge.setText(f"Son Güncelleme: {last_upd}")
            self.last_update_badge.show()
        else:
            self.last_update_badge.hide()
        
        if not versions:
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
            # 1. Separate Active and Older Versions
            active_list = []
            older_list = []
            
            for v in versions:
                if v["filename"] == active_ver:
                    active_list.append(v)
                else:
                    older_list.append(v)
                    
            # 1. Active Timetable Card at top
            if active_list:
                card, lay = self._create_version_group_card("Aktif Çizelge", "active", "Yayında", APPLE_BLUE)
                for v in active_list:
                    row = AppleVersionRow(self._selected_slug, v, is_active=True)
                    row.selected.connect(self._on_version_selected)
                    row.double_clicked.connect(self._on_version_double_clicked)
                    row.action_requested.connect(self._on_version_action)
                    lay.addWidget(row)
                self.ver_list_layout.addWidget(card)
                
            # 2. Collapsible Older Versions Group with Chevron
            if older_list:
                hist_group = CollapsibleVersionGroup("Eski Sürümler", "history", f"{len(older_list)} Versiyon", "#86868B", is_collapsed=True)
                for v in older_list:
                    row = AppleVersionRow(self._selected_slug, v, is_active=False)
                    row.selected.connect(self._on_version_selected)
                    row.double_clicked.connect(self._on_version_double_clicked)
                    row.action_requested.connect(self._on_version_action)
                    hist_group.content_lay.addWidget(row)
                self.ver_list_layout.addWidget(hist_group)
                
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
            self.right_panel_stack.setCurrentWidget(self.password_overlay_widget)
            self.password_overlay_widget.show()
            # Retain focus if search input is being used
            if not self.search_input.hasFocus():
                self.pwd_card_input.setFocus()
        else:
            self.btn_new_empty.setEnabled(True)
            self.right_panel_stack.setCurrentWidget(self.right_content_widget)
            self.password_overlay_widget.hide()
            
    def _on_version_selected(self, filename):
        self._selected_version = filename
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
                from save_dialog import run_apple_save_sequence
                run_apple_save_sequence(self, duration_seconds=0.25, title="Versiyon Siliniyor", message=f"'{v_label}' yerel sistemden ve buluttan siliniyor...")
                version_store.delete_version(slug, filename)
                from cloud_sync import delete_version_from_rtdb
                delete_version_from_rtdb(slug, filename, self.auth_data)
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
                from cloud_sync import push_all_to_rtdb
                push_all_to_rtdb(self.auth_data)
                
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
        from save_dialog import AppleSaveDialog
        from cloud_sync import push_all_to_rtdb, pull_all_from_rtdb
        import threading
        import time
        
        dlg = AppleSaveDialog(
            title="Bulut Senkronizasyonu",
            message="Merkezi veritabanı ile eşitleniyor...",
            parent=self
        )
        dlg.show()
        QApplication.processEvents()
        
        results = {}
        
        def _sync_worker():
            try:
                push_ok, push_msg, _ = push_all_to_rtdb(self.auth_data)
                pull_ok, pull_msg, count = pull_all_from_rtdb(self.auth_data)
                results["push_ok"] = push_ok
                results["push_msg"] = push_msg
                results["pull_ok"] = pull_ok
                results["pull_msg"] = pull_msg
            except Exception as e:
                results["push_ok"] = False
                results["pull_ok"] = False
                results["pull_msg"] = f"Bağlantı hatası: {e}"
            finally:
                results["done"] = True
            
        t = threading.Thread(target=_sync_worker, daemon=True)
        t.start()
        
        t_start = time.time()
        while not results.get("done"):
            QApplication.processEvents()
            time.sleep(0.03)
            if time.time() - t_start > 15:
                break
                
        elapsed = time.time() - t_start
        if elapsed < 1.2:
            time.sleep(1.2 - elapsed)
            QApplication.processEvents()
            
        dlg.close()
        dlg.deleteLater()
        QApplication.processEvents()
        
        self._refresh_institutions()
        if self._selected_slug:
            self._refresh_versions()
            
        push_ok = results.get("push_ok", False)
        pull_ok = results.get("pull_ok", False)
        push_msg = results.get("push_msg", "")
        pull_msg = results.get("pull_msg", "")
        
        if pull_ok or push_ok:
            show_apple_info(self, "Bulut Senkronizasyonu", f"{push_msg}\n{pull_msg}\nTüm cihazlar ve geçmiş versiyonlar başarıyla eşitlendi.", is_success=True)
        else:
            show_apple_info(self, "Bulut Uyarısı", f"{pull_msg or 'Bağlantı kurulamadı.'}\nLütfen internet bağlantınızı kontrol edin.", is_success=False)
