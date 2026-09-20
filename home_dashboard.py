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
    QLineEdit, QDialog, QCheckBox, QProgressBar,
    QMenu, QSizePolicy, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QAbstractButton
)
from PySide6.QtCore import (
    Qt, Signal, QSize, QRectF, QPoint, QPointF, QMimeData, QEvent, QTimer,
    QRect, QPropertyAnimation, QEasingCurve, Property,
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QIcon, QPixmap, QShortcut, QKeySequence,
    QPainterPath, QLinearGradient, QRadialGradient, QDrag, QCursor, QPolygonF
)

# Üst çubuğun yüksekliği tek yerde: çubuk da, altındaki renkli bandın üst
# kenarı da bunu okur (ikisi ayrı sayılarla yazılınca aralarında şerit kalıyordu).
TOPBAR_H = 52

import version_store
import bk_branding
import ui_icons
from version import APP_VERSION
import update_notifications
from dialogs.faq_dialog import FAQDialog
from dialogs.notifications_dialog import AppleNotificationsDialog
from dialogs.profile_dialog import (
    AppleProfileDialog, get_user_profile, make_circular_avatar_pixmap
)

# ── Design tokens ────────────────────────────────────────────────────
# Aliases, not values. The palette lives in bk_ui, which the sign-in
# window also reads, so the two halves of the program cannot drift apart:
# this file used to define its own "Apple blue" while the login screen
# used the institution's real navy.
import bk_ui

BG_CANVAS        = bk_ui.CANVAS
BG_CARD          = bk_ui.SURFACE
BG_SIDEBAR       = bk_ui.SURFACE
BORDER_HAIRLINE  = bk_ui.HAIRLINE
BORDER_SUBTLE    = "rgba(0, 0, 0, 0.05)"
TEXT_PRIMARY     = bk_ui.INK
TEXT_SECONDARY   = bk_ui.INK_SOFT
TEXT_MUTED       = bk_ui.INK_FAINT
APPLE_BLUE       = bk_ui.BRAND
APPLE_GREEN      = bk_ui.OK
APPLE_AMBER      = bk_ui.WARN
APPLE_RED        = bk_ui.DANGER
APPLE_PURPLE     = "#6B4FBB"
APPLE_INDIGO     = bk_ui.BRAND_DARK

SELECTED_BG      = bk_ui.BRAND_TINT
SELECTED_TEXT    = bk_ui.BRAND
HOVER_BG         = bk_ui.HOVER

FONT_FAMILY = 'Segoe UI, SF Pro Text, .AppleSystemUIFont, Helvetica Neue, Arial, sans-serif'

# ── Monochrome Institution Icon ──────────────────────────────────────

def make_3d_institution_icon(inst_name: str, color_hex: str = None, size: int = 36) -> QPixmap:
    """Kept under its old name because a dozen call sites use it. The
    drawing lives in bk_ui.institution_3d now — an isometric block on a
    plinth with banded glazing, supersampled for hi-DPI, whose colour
    lives in the glass rather than the walls so a sidebar of five stays
    calm. Its docstring records the three drawings that were tried and
    thrown away before it."""
    return bk_ui.institution_3d(inst_name, color_hex, size)

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
                border-radius: 18px;
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
        t_lbl.setFont(QFont(FONT_FAMILY, 12, QFont.Bold))
        t_lbl.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none;")
        t_lbl.setAlignment(Qt.AlignCenter)
        c_lay.addWidget(t_lbl)
        
        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont(FONT_FAMILY, 9.5))
        msg_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
        msg_lbl.setAlignment(Qt.AlignCenter)
        msg_lbl.setWordWrap(True)
        c_lay.addWidget(msg_lbl)
        
        btn_ok = QPushButton("Tamam")
        btn_ok.setFixedSize(140, 34)
        btn_ok.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 17px;
                font-weight: 600;
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
                border-radius: 18px;
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
        t_lbl.setFont(QFont(FONT_FAMILY, 12.5, QFont.Bold))
        t_lbl.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none;")
        t_lbl.setAlignment(Qt.AlignCenter)
        c_lay.addWidget(t_lbl)
        
        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont(FONT_FAMILY, 9.5))
        msg_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
        msg_lbl.setAlignment(Qt.AlignCenter)
        msg_lbl.setWordWrap(True)
        msg_lbl.setMinimumHeight(44)
        c_lay.addWidget(msg_lbl)
        
        c_lay.addSpacing(4)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        
        btn_cancel = QPushButton(cancel_text)
        btn_cancel.setFixedHeight(34)
        btn_cancel.setFont(QFont(FONT_FAMILY, 9, QFont.DemiBold))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F1F5F9; color: #1E293B; border: 1px solid #CBD5E1;
                border-radius: 17px; padding: 0 20px; font-weight: 500;
            }
            QPushButton:hover { background: #E2E8F0; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        btn_ok = QPushButton(confirm_text)
        btn_ok.setFixedHeight(34)
        btn_ok.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        btn_ok.setCursor(Qt.PointingHandCursor)
        bg_col = "#FF3B30" if is_destructive else "#0071E3"
        hover_col = "#DC2626" if is_destructive else "#0062C4"
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background: {bg_col}; color: #FFFFFF; border: none;
                border-radius: 17px; padding: 0 22px; font-weight: 600;
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
                border-radius: 18px;
            }
        """)
        
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(24, 20, 24, 20)
        c_lay.setSpacing(14)
        
        t_lbl = QLabel("Kurum Rengi Seç")
        t_lbl.setFont(QFont(FONT_FAMILY, 12, QFont.Bold))
        t_lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")
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
        btn_cancel.setFont(QFont(FONT_FAMILY, 9, QFont.DemiBold))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F1F5F9; color: #1E293B; border: 1px solid #CBD5E1;
                border-radius: 17px; padding: 0 18px; font-weight: 500;
            }
            QPushButton:hover { background: #E2E8F0; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        btn_ok = QPushButton("Kaydet")
        btn_ok.setFixedHeight(34)
        btn_ok.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 17px; padding: 0 22px; font-weight: 600;
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
        t_lbl.setFont(QFont(FONT_FAMILY, 13, QFont.Bold))
        t_lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        title_box.addWidget(t_lbl)
        
        sub_lbl = QLabel("Bağımsız ders çizelgeleri ve versiyon alanı tanımlayın.")
        sub_lbl.setFont(QFont(FONT_FAMILY, 9))
        sub_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
        title_box.addWidget(sub_lbl)
        
        hdr_row.addLayout(title_box, 1)
        c_lay.addLayout(hdr_row)
        
        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: #E2E8F0; border: none;")
        c_lay.addWidget(div)
        
        # Field 1: Name
        name_title = QLabel("KURUM ADI *")
        name_title.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        name_title.setStyleSheet("color: #64748B; letter-spacing: 0.5px; background: transparent; border: none;")
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
        color_title.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        color_title.setStyleSheet("color: #64748B; letter-spacing: 0.5px; background: transparent; border: none;")
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
        pwd_title.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        pwd_title.setStyleSheet("color: #64748B; letter-spacing: 0.5px; background: transparent; border: none;")
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
        btn_cancel.setFixedHeight(36)
        btn_cancel.setFont(QFont(FONT_FAMILY, 9, QFont.DemiBold))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F1F5F9; color: #1E293B; border: 1px solid #CBD5E1;
                border-radius: 18px; padding: 0 20px; font-weight: 500;
            }
            QPushButton:hover { background: #E2E8F0; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        self.btn_create = QPushButton("+ Kurumu Oluştur")
        self.btn_create.setFixedHeight(36)
        self.btn_create.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self.btn_create.setCursor(Qt.PointingHandCursor)
        self.btn_create.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 18px; padding: 0 24px; font-weight: 600;
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
        t_lbl.setFont(QFont(FONT_FAMILY, 12, QFont.Bold))
        t_lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        c_lay.addWidget(t_lbl)
        
        msg_lbl = QLabel(label)
        msg_lbl.setFont(QFont(FONT_FAMILY, 9.5))
        msg_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
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
        btn_cancel.setFont(QFont(FONT_FAMILY, 9, QFont.DemiBold))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F1F5F9; color: #1E293B; border: 1px solid #CBD5E1;
                border-radius: 17px; padding: 0 18px; font-weight: 500;
            }
            QPushButton:hover { background: #E2E8F0; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        btn_ok = QPushButton("Tamam")
        btn_ok.setFixedHeight(34)
        btn_ok.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 17px; padding: 0 22px; font-weight: 600;
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

        self.cb_invert_timeoff = QCheckBox("Zaman Kısıtlamalarını / Diğer Kurum Saatlerini Tam Tersi Olarak Aktar")
        self.cb_invert_timeoff.setToolTip("Kaynak kurumda öğretmenin derste olduğu saatler bu kurum için kapalı saat yapılır; çakışmalar otomatik engellenir.")
        self.cb_invert_timeoff.setChecked(True)
        self.cb_invert_timeoff.setStyleSheet(f"color: {APPLE_BLUE}; font-weight: 600;")
        cb_box.addWidget(self.cb_invert_timeoff)
        
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
            "invert_timeoff": self.cb_invert_timeoff.isChecked(),
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
        self.inst_color = inst_data.get("color", "#0071E3")
        self.has_password = inst_data.get("has_password", False)
        self.is_primary = bool(inst_data.get("is_primary", False))
        self._selected = is_selected
        self.is_master_admin = is_master_admin
        
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(50)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)
        
        # Institution 3D Building Avatar
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(34, 34)
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("border: none; background: transparent;")
        self.icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.icon_lbl)
        
        # Text Info
        t_layout = QVBoxLayout()
        t_layout.setSpacing(1)
        t_layout.setContentsMargins(0, 0, 0, 0)
        
        self.name_lbl = ElidedLabel(self.inst_name)
        self.name_lbl.setFont(bk_ui.font(9.3, QFont.DemiBold))
        self.name_lbl.setStyleSheet("border: none; background: transparent;")
        self.name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        t_layout.addWidget(self.name_lbl)
        
        v_count = inst_data.get("version_count", 0)
        upd = version_store.tr_month_text(inst_data.get("last_updated_str", ""))
        sub_text = f"{v_count} versiyon" + (f" · {upd}" if upd else "")
        self.sub_lbl = QLabel(sub_text)
        self.sub_lbl.setFont(bk_ui.font(7.8))
        self.sub_lbl.setStyleSheet("border: none; background: transparent;")
        self.sub_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        t_layout.addWidget(self.sub_lbl)
        
        layout.addLayout(t_layout, 1)

        # Hover Actions Button (•••)
        self.btn_more = AppleThreeDotsButton(color="#8E8E93", size=22, tooltip="Seçenekler", parent=self)
        self.btn_more.clicked.connect(lambda: self._context_menu(self.btn_more.mapToGlobal(QPoint(0, self.btn_more.height() + 2))))
        self.btn_more.hide()
        layout.addWidget(self.btn_more, 0, Qt.AlignVCenter)
        
        self._update_style()
    
    def _update_style(self):
        self.setStyleSheet("""
            AppleInstitutionCard {
                background: transparent;
                border: none;
                border-radius: 10px;
            }
            AppleInstitutionCard:hover {
                background: rgba(0, 0, 0, 0.04);
            }
        """)
        if self._selected:
            self.name_lbl.setStyleSheet("color: #0F172A; font-weight: 600; background: transparent; border: none;")
            self.sub_lbl.setStyleSheet("color: #334155; background: transparent; border: none;")
        else:
            self.name_lbl.setStyleSheet("color: #334155; font-weight: 500; background: transparent; border: none;")
            self.sub_lbl.setStyleSheet("color: #8E8E93; background: transparent; border: none;")
        self.icon_lbl.setPixmap(make_3d_institution_icon(self.inst_name, self.inst_color, 34))

    def enterEvent(self, event):
        self.btn_more.show()
        if not self._selected:
            self.name_lbl.setStyleSheet("color: #0F172A; font-weight: 600; background: transparent; border: none;")
            self.sub_lbl.setStyleSheet("color: #475569; background: transparent; border: none;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.btn_more.hide()
        if not self._selected:
            self.name_lbl.setStyleSheet("color: #334155; font-weight: 500; background: transparent; border: none;")
            self.sub_lbl.setStyleSheet("color: #8E8E93; background: transparent; border: none;")
        super().leaveEvent(event)
            
    def set_selected(self, selected):
        self._selected = selected
        self._update_style()

    def update_data(self, inst_data, is_selected=False):
        self.inst_data = inst_data
        self.inst_name = inst_data["name"]
        self.inst_color = inst_data.get("color", "#0071E3")
        self.has_password = inst_data.get("has_password", False)
        self.is_primary = bool(inst_data.get("is_primary", False))
        self._selected = is_selected
        self.name_lbl.setText(self.inst_name)
        v_count = inst_data.get("version_count", 0)
        upd = version_store.tr_month_text(inst_data.get("last_updated_str", ""))
        self.sub_lbl.setText(f"{v_count} versiyon" + (f" · {upd}" if upd else ""))
        self._update_style()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.slug)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._context_menu(event.pos())
        super().mouseDoubleClickEvent(event)
        
    def _context_menu(self, pos):
        menu = bk_ui.HeroPopoverMenu(self)

        def _do_set_primary():
            version_store.set_primary_institution(self.slug)
            show_apple_info(self, "Ana Kurum Güncellendi", f"'{self.inst_name}' varsayılan ana kurum olarak ayarlandı.", is_success=True)
            self._notify_parent_refresh()

        def _do_rename():
            dlg = AppleInputDialog("Kurum Adı", "Yeni kurum adı:", default_text=self.inst_name, parent=self)
            if dlg.exec() == QDialog.Accepted and dlg.text_value():
                new_name = dlg.text_value()
                from save_dialog import run_apple_save_sequence
                run_apple_save_sequence(self, duration_seconds=0.25, title="Güncelleniyor", message=f"Kurum adı '{new_name}' olarak kaydediliyor...")
                version_store.rename_institution(self.slug, new_name)
                self._notify_parent_refresh()

        def _do_change_color():
            dlg = AppleColorPickerDialog(current_color=self.inst_color, parent=self)
            if dlg.exec() == QDialog.Accepted:
                new_color = dlg.get_color()
                if new_color:
                    self.inst_color = new_color
                    version_store.set_institution_color(self.slug, new_color)
                    self._update_style()
                    self._notify_parent_refresh()

        def _do_set_pwd():
            dlg = SetPasswordDialog(self.inst_name, has_current=self.has_password, parent=self)
            if dlg.exec() == QDialog.Accepted:
                pwd = dlg.get_password()
                version_store.set_institution_password(self.slug, pwd)
                p = self.parent()
                while p:
                    if hasattr(p, "user_email") and p.user_email:
                        version_store.add_trusted_user(self.slug, p.user_email)
                        break
                    p = p.parent()
                show_apple_info(self, "Bilgi", "Kurum şifresi başarıyla güncellendi.", is_success=True)
                self._notify_parent_refresh()

        def _do_rm_pwd():
            version_store.remove_institution_password(self.slug)
            show_apple_info(self, "Bilgi", "Kurum şifresi kaldırıldı.", is_success=True)
            self._notify_parent_refresh()

        def _do_delete():
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

        if not self.is_primary:
            menu.add_action("Ana Kurum Olarak Ayarla", bk_ui.star_glyph(bk_ui.BRAND, 16), on_click=_do_set_primary)
            menu.add_separator()

        menu.add_action("Yeniden Adlandır", bk_ui.pencil_glyph(bk_ui.BRAND, 16), on_click=_do_rename)

        if self.has_password:
            menu.add_action("Şifreyi Değiştir", bk_ui.key_glyph(bk_ui.BRAND, 16), on_click=_do_set_pwd)
            menu.add_action("Şifreyi Kaldır", bk_ui.trash_glyph(bk_ui.INK_SOFT, 16), on_click=_do_rm_pwd)
        else:
            menu.add_action("Şifre Belirle (Yönetici)", bk_ui.key_glyph(bk_ui.BRAND, 16), on_click=_do_set_pwd)

        menu.add_action("Renk Değiştir", bk_ui.palette_glyph(bk_ui.BRAND, 16), on_click=_do_change_color)

        menu.add_separator()
        menu.add_action("Kurumu Sil", bk_ui.trash_glyph(bk_ui.DANGER, 16), is_danger=True, on_click=_do_delete)

        if not isinstance(pos, QPoint):
            from PySide6.QtGui import QCursor
            global_pos = QCursor.pos()
        elif 0 <= pos.x() <= self.width() and 0 <= pos.y() <= self.height():
            global_pos = self.mapToGlobal(pos)
        else:
            global_pos = pos

        menu.popup_at(global_pos)

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
    """Draws crisp, minimalist Apple-style vector iconography with 2x Retina supersampling."""
    scale = 2
    actual_sz = size * scale
    pix = QPixmap(actual_sz, actual_sz)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(scale, scale)
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
        return bk_ui.folder_3d_glyph(size=size)
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
        for dx in [0.28, 0.50, 0.72]:
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
        # Apple SF Symbols Question mark circle
        p.setPen(QPen(c, max(1.3, size * 0.08)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(2, 2, size - 4, size - 4))
        # Draw question curve
        qpath = QPainterPath()
        qpath.moveTo(size * 0.38, size * 0.40)
        qpath.quadTo(size * 0.38, size * 0.28, size * 0.50, size * 0.28)
        qpath.quadTo(size * 0.62, size * 0.28, size * 0.62, size * 0.40)
        qpath.quadTo(size * 0.62, size * 0.49, size * 0.50, size * 0.55)
        qpath.lineTo(size * 0.50, size * 0.62)
        p.drawPath(qpath)
        # Dot
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c))
        p.drawEllipse(QRectF(size * 0.50 - 1.0, size * 0.72 - 1.0, 2.0, 2.0))
    elif name == "check":
        p.setPen(QPen(c, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(size * 0.22, size * 0.52)
        path.lineTo(size * 0.42, size * 0.72)
        path.lineTo(size * 0.78, size * 0.28)
        p.drawPath(path)
    elif name == "refresh":
        # Dairesel yenileme oku
        p.setPen(QPen(c, 1.7, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        rect = QRectF(size * 0.18, size * 0.18, size * 0.64, size * 0.64)
        p.drawArc(rect, 45 * 16, 280 * 16)
        head = QPainterPath()
        head.moveTo(size * 0.80, size * 0.16)
        head.lineTo(size * 0.82, size * 0.42)
        head.lineTo(size * 0.56, size * 0.34)
        head.closeSubpath()
        p.setBrush(QBrush(c))
        p.setPen(Qt.NoPen)
        p.drawPath(head)
    elif name == "import":
        # Kutuya inen ok: veri aktarımı
        p.setPen(QPen(c, 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawLine(QPointF(size * 0.5, size * 0.16), QPointF(size * 0.5, size * 0.58))
        arrow = QPainterPath()
        arrow.moveTo(size * 0.32, size * 0.44)
        arrow.lineTo(size * 0.5, size * 0.63)
        arrow.lineTo(size * 0.68, size * 0.44)
        p.drawPath(arrow)
        p.drawLine(QPointF(size * 0.2, size * 0.78), QPointF(size * 0.8, size * 0.78))
    elif name == "info":
        p.setPen(QPen(c, max(1.3, size * 0.08)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(2, 2, size - 4, size - 4))
        p.drawLine(int(size / 2), int(size * 0.42), int(size / 2), int(size * 0.75))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c))
        p.drawEllipse(QRectF(size / 2 - 1.2, size * 0.25 - 1.2, 2.4, 2.4))
    else:
        p.setBrush(QBrush(c))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(3, 3, size - 6, size - 6))
        
    p.end()
    pix.setDevicePixelRatio(scale)
    return pix


class AppleThreeDotsButton(QPushButton):
    """Ultra-crisp Retina-ready vector 3-dots button with transparent background (no box artifacts)."""
    def __init__(self, color="#64748B", size=24, tooltip="Diğer Seçenekler", parent=None):
        super().__init__(parent)
        self.dot_color = QColor(color)
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Soft hover circle
        if self.underMouse():
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 18))
            p.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), (self.height() - 2) / 2.0, (self.height() - 2) / 2.0)
            
        # Draw 3 crisp dots
        p.setPen(Qt.NoPen)
        p.setBrush(self.dot_color)
        
        w = float(self.width())
        h = float(self.height())
        dot_r = 1.6
        cy = h / 2.0
        
        for dx in [w * 0.28, w * 0.50, w * 0.72]:
            p.drawEllipse(QRectF(dx - dot_r, cy - dot_r, dot_r * 2.0, dot_r * 2.0))
        p.end()


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


# A folder's colour comes from its own name, not from where it sits in
# the list. Indexing by row order would re-colour everything each time a
# folder was created above another, which makes the colour useless for
# recognising a folder — the whole point of giving it one.
#
_FOLDER_PALETTE = (
    "#0F4AAB",  # brand navy
    "#2E9E5B",  # green
    "#C9821A",  # amber
    "#6B4FBB",  # violet
    "#C2456A",  # rose
    "#1F8FA6",  # teal
    "#4A5BC4",  # indigo
    "#7A8F2E",  # olive
)


def _folder_colour(name, fallback=None):
    if not name:
        return QColor(fallback or bk_ui.BRAND)
    # CRC32, not a sum of character codes: a plain sum ignores order, so
    # unrelated names collide constantly — six real folder names landed on
    # three colours in testing. And unlike Python's hash(), CRC32 gives the
    # same answer in every process, which matters because this colour has
    # to still be the same one tomorrow.
    import zlib

    key = str(name).strip().lower().encode("utf-8")
    return QColor(_FOLDER_PALETTE[zlib.crc32(key) % len(_FOLDER_PALETTE)])


class CollapsibleVersionGroup(QFrame):
    """A collapsible section of version rows with macOS HIG card styling."""

    # Başlık metninin sol kenarı: kenar boşluğu + ikon + aradaki boşluk.
    # Versiyon satırları da buradan başlar, ikisi tek çizgide dursun.
    PAD_X, ICON_W, GAP_X = 16, 30, 12
    TEXT_X = PAD_X + ICON_W + GAP_X

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

        self._normal_style = f"""
            CollapsibleVersionGroup {{
                background: transparent;
                border: none;
                border-bottom: 1px solid {bk_ui.HAIRLINE};
            }}
        """
        self._dragover_style = f"""
            CollapsibleVersionGroup {{
                background: {bk_ui.BRAND_TINT};
                border: 1.5px dashed {bk_ui.BRAND};
            }}
        """
        self.setStyleSheet(self._normal_style)
        if is_drop_target:
            self.setAcceptDrops(True)

        self.main_lay = QVBoxLayout(self)
        self.main_lay.setContentsMargins(0, 0, 0, 0)
        self.main_lay.setSpacing(0)

        # Header Frame
        self.header = QFrame()
        self.header.setFixedHeight(48)
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.setStyleSheet(f"""
            QFrame {{
                background: #FFFFFF;
                border: none;
            }}
            QFrame:hover {{
                background: {bk_ui.HOVER};
            }}
        """)
        hdr_lay = QHBoxLayout(self.header)
        hdr_lay.setContentsMargins(self.PAD_X, 8, 16, 8)
        hdr_lay.setSpacing(self.GAP_X)

        # One colour for every folder you made; grey for the pile of
        # everything you did not file.
        is_history = icon_name in ("history", "archive")
        if is_history:
            accent = QColor(bk_ui.INK_FAINT)
            glyph = bk_ui.folder_3d_glyph(accent.name(), 28)
        else:
            accent = _folder_colour(None, color_hex)
            glyph = bk_ui.folder_3d_glyph(accent.name(), 28)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(self.ICON_W, 30)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setPixmap(glyph)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        hdr_lay.addWidget(icon_lbl)

        # Title & Subtitle block
        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(1)
        text_vbox.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(title)
        title_lbl.setFont(bk_ui.font(9.8, QFont.DemiBold))
        title_lbl.setStyleSheet(f"color: {bk_ui.INK}; background: transparent; border: none;")
        title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        text_vbox.addWidget(title_lbl)

        hdr_lay.addLayout(text_vbox, 1)

        if badge_text:
            badge = bk_ui.Chip(badge_text, "neutral")
            badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            hdr_lay.addWidget(badge, 0, Qt.AlignVCenter)

        if show_folder_actions:
            btn_dots = AppleThreeDotsButton(color="#64748B", size=24, tooltip="Klasör Seçenekleri", parent=self.header)
            btn_dots.clicked.connect(self._show_folder_menu)
            hdr_lay.addWidget(btn_dots)

        # Chevron icon
        self.chevron_lbl = QLabel()
        self.chevron_lbl.setFixedSize(14, 14)
        self.chevron_lbl.setStyleSheet("background: transparent; border: none;")
        self.chevron_lbl.setPixmap(
            bk_ui.chevron_glyph(bk_ui.INK_FAINT, 14,
                                "right" if is_collapsed else "down"))
        self.chevron_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        hdr_lay.addWidget(self.chevron_lbl, 0, Qt.AlignVCenter)

        self.main_lay.addWidget(self.header)

        # Inner content container
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent; border: none;")
        self.content_lay = QVBoxLayout(self.content_widget)
        self.content_lay.setContentsMargins(0, 0, 0, 0)
        self.content_lay.setSpacing(0)

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
        menu = bk_ui.HeroPopoverMenu(self)
        if self.folder_id is not None and str(self.folder_id).lower() != "active":
            menu.add_action("Yeniden Adlandır", bk_ui.pencil_glyph(bk_ui.BRAND, 16), on_click=lambda: self.rename_requested.emit())
            menu.add_action("Klasörü Sil", bk_ui.trash_glyph(bk_ui.DANGER, 16), is_danger=True, on_click=lambda: self.delete_requested.emit())
        else:
            menu.add_action("Klasörsüz Çizelgeleri Sil", bk_ui.trash_glyph(bk_ui.DANGER, 16), is_danger=True, on_click=lambda: self.delete_requested.emit())
        menu.popup_below(btn, align="right")

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

    def set_row_factory(self, factory):
        self._row_factory = factory
        self._rows_built = False

    def _ensure_rows(self):
        factory = getattr(self, "_row_factory", None)
        if factory is None or getattr(self, "_rows_built", False):
            return
        self._rows_built = True
        for w in factory():
            self.content_lay.addWidget(w)

    def _set_collapsed(self, collapsed: bool):
        self.is_collapsed = collapsed
        if not collapsed:
            self._ensure_rows()
        self.content_widget.setVisible(not collapsed)
        if hasattr(self, "chevron_lbl") and self.chevron_lbl is not None:
            self.chevron_lbl.setPixmap(
                bk_ui.chevron_glyph(bk_ui.INK_FAINT, 14, "right" if collapsed else "down")
            )

    def _toggle_collapse(self, event):
        if hasattr(event, "pos"):
            child = self.header.childAt(event.pos())
            if child and isinstance(child, QAbstractButton):
                return
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
        self.version_dropped.emit(slug, filename)


# ── Apple Clean Version Row (macOS Card Layout) ──────────────────────

_CHIP_PAD_X = 8     # künye zemininin yazısından taşan yanal payı


class AppleVersionRow(QFrame):
    double_clicked = Signal(str, str)  # slug, filename
    selected = Signal(str)  # filename
    action_requested = Signal(str, str, str)  # action ('open', 'set_active', 'delete'), slug, filename
    move_to_folder_requested = Signal(str, str, object)  # slug, filename, folder_id
    
    def __init__(self, slug, version_info, is_active=False, is_last=False, parent=None):
        super().__init__(parent)
        self.slug = slug
        self.version_info = version_info
        self.filename = version_info["filename"]
        self._is_active = is_active
        self._is_selected = False
        self._is_last = is_last
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(46)
        self.setAcceptDrops(True)
        
        layout = QHBoxLayout(self)
        # Künye, üstündeki klasör İKONUYLA aynı dikey çizgide başlar.
        # 44 piksel ne ikonla (16) ne klasör adıyla (58) hizalıydı;
        # ikisinin arasında, hiçbir şeye ait olmayan bir girintideydi.
        # Hizalanan iki nesne de bir kutu — ikon kutusu ve künye kutusu —
        # o yüzden hizayı kenarları tutuyor.
        layout.setContentsMargins(CollapsibleVersionGroup.PAD_X, 4, 16, 4)
        layout.setSpacing(12)
        
        # Version Title Badge (e.g. v121 or v121  oturan program)
        num = version_info.get("number", 0)
        cname = (version_info.get("custom_name") or "").strip()
        v_label_str = version_info.get("label") or (f"v{num}  {cname}" if cname else f"Versiyon {num}")
        v_title = QLabel(v_label_str)
        v_title.setFont(bk_ui.font(8.8, QFont.DemiBold))
        v_title.setAlignment(Qt.AlignCenter)
        v_title.setFixedHeight(22)
        v_title.setStyleSheet(f"""
            background: #F1F3F5;
            color: #1E293B;
            border-radius: 5px;
            padding: 0 {_CHIP_PAD_X}px;
        """)
        v_title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        if cname:
            v_title.setToolTip(f"Çizelge: {v_label_str}")
        elif version_info.get("has_number_collision"):
            v_title.setToolTip("Bu numara başka bir cihazda da kullanılmış.")
        layout.addWidget(v_title)

        # BİR SATIRDA BİR KUTU YETER.
        #
        # Satırda dört kutu vardı: versiyon künyesi, "● Yayında", "✓ Tam
        # Yerleşim" ve mavi "Aç" düğmesi. Dördü de aynı yüksekliğe, aynı
        # yuvarlaklığa, kendi kenarlığına ve kendi arka planına sahipti —
        # yani hiçbiri diğerinden önemli görünmüyordu ve göz her satırda
        # dört kere duruyordu. Üstelik "✓ Tam Yerleşim" listenin neredeyse
        # tamamında aynı yazıyordu: herkeste olan bir şey ayırt etmez.
        #
        # Kutu artık yalnızca künyede (ona dokunulmadı). Geri kalan her şey
        # çıplak yazı: durum solda, yerleşim ile tarih sağda, ikisi de sağa
        # hizalı sabit sütunlarda — künye adları farklı uzunlukta olduğu
        # için soldan hizalanan her şey basamak basamak kayıyordu.
        if is_active:
            act_lbl = QLabel("Yayında")
            act_lbl.setFont(bk_ui.font(9.0, QFont.DemiBold))
            act_lbl.setStyleSheet("color: #15803D; background: transparent; border: none;")
            act_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            act_lbl.setToolTip("Kurumun yayındaki çizelgesi")
            layout.addWidget(act_lbl)
        
        # Note snippet: Only display real custom notes from user, hide generic system messages
        note_text = (version_info.get("note") or "").strip()
        _generic_notes = {
            "kullanıcı kaydı", "değişiklikler kaydedildi", "kapanırken kaydedildi",
            "kapanış kaydı", "güncelleme öncesi kayıt", "başlangıç çizelgesi", "manual", "auto"
        }
        if note_text and note_text.lower() not in _generic_notes:
            from PySide6.QtGui import QFontMetrics
            fm = QFontMetrics(bk_ui.font(8.2))
            elided_note = fm.elidedText(note_text, Qt.ElideRight, 260)
            note_lbl = QLabel(f"{elided_note}")
            note_lbl.setToolTip(f"Not: {note_text}")
            note_lbl.setFont(bk_ui.font(8.2))
            note_lbl.setStyleSheet("color: #475569; background: transparent; border: none;")
            note_lbl.setMaximumWidth(260)
            note_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            layout.addWidget(note_lbl)
            
        layout.addStretch(1)

        # Yerleşim durumu — çıplak yazı, sağa hizalı sabit sütun.
        tot = version_info.get("total_hours", 0)
        unp = version_info.get("unplaced_hours", 0)
        if tot <= 0:
            fill_txt, fill_col, fill_tip = "Boş çizelge", bk_ui.INK_SOFT, "Bu versiyonda ders yok."
        elif unp == 0:
            fill_txt, fill_col, fill_tip = "Tam yerleşim", bk_ui.INK_SOFT, f"{tot} saatin tamamı yerleşti."
        else:
            fill_txt, fill_col = f"{unp} saat boşta", "#B45309"
            fill_tip = f"{tot} saatin {unp} saati yerleşemedi."
        fill_lbl = QLabel(fill_txt)
        fill_lbl.setFont(bk_ui.font(9.0, QFont.Medium if unp else QFont.Normal))
        fill_lbl.setStyleSheet(f"color: {fill_col}; background: transparent; border: none;")
        # Bu üç yazı — durum, yerleşim, tarih — 8.2 puntoda ve INK_FAINT
        # tonundaydı: ikisi birden, hem küçük hem soluk. O ton ve o boyut
        # etiketler ve devre dışı metinler içindir; bunlar ise satırın
        # okunmak üzere orada duran bilgileri. Künyenin bir tık altında,
        # 9 puntoda ve INK_SOFT'ta.
        fill_lbl.setFixedWidth(108)
        fill_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fill_lbl.setToolTip(fill_tip)
        fill_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(fill_lbl)

        # Tarih — satırdaki EN SAĞDAKİ yazı.
        #
        # "20 Sep 2026  01:06:20" üç sorun taşıyordu: ayı İngilizce yazıyor,
        # saniyeyi söylüyor (bir çizelgenin 20. saniyede kaydedildiğini
        # bilmenin kimseye faydası yok) ve bu listede satırların çoğu aynı
        # güne ait olduğu için tarihin kendisi de tekrar oluyordu. Bugün ve
        # dün adıyla anılıyor, yıl yalnızca başka bir yılsa yazılıyor.
        dt_lbl = QLabel(self._when())
        dt_lbl.setFont(bk_ui.font(9.0))
        dt_lbl.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent; border: none;")
        dt_lbl.setFixedWidth(116)
        dt_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        dt_lbl.setToolTip("{}  {}  •  {} KB".format(
            version_info.get("date_str", ""), version_info.get("time_str", ""),
            version_info.get("size_kb", 0)))
        dt_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(dt_lbl)

        # "Aç" — üst çubuktaki klasör düğmesinin dili: beyaz gövde, ince
        # kenar, imleç altında kurumun rengi. Dolu mavi düğme yüz satırda
        # yüz kere tekrarlanınca listenin en gürültülü nesnesi oluyordu ve
        # hepsi aynı ağırlıkta olduğu için hiçbiri "asıl eylem" demiyordu.
        btn_open = QPushButton("Aç")
        btn_open.setFont(bk_ui.font(8.4, QFont.DemiBold))
        btn_open.setCursor(Qt.PointingHandCursor)
        btn_open.setFixedHeight(26)
        btn_open.setStyleSheet(f"""
            QPushButton {{
                background: #FFFFFF; color: {bk_ui.INK_BODY};
                border: 1px solid rgba(15, 23, 42, 0.12);
                border-radius: 13px; padding: 0 14px;
            }}
            QPushButton:hover {{
                background: {bk_ui.BRAND}; color: #FFFFFF;
                border-color: {bk_ui.BRAND};
            }}
            QPushButton:pressed {{
                background: {bk_ui.BRAND_DARK}; border-color: {bk_ui.BRAND_DARK};
            }}
        """)
        btn_open.clicked.connect(lambda: self.action_requested.emit("open", self.slug, self.filename))
        layout.addWidget(btn_open)
        
        # Options Button (•••)
        btn_menu = AppleThreeDotsButton(color="#8E8E93", size=24, tooltip="Seçenekler", parent=self)
        btn_menu.clicked.connect(lambda: self._context_menu(btn_menu.mapToGlobal(QPoint(0, btn_menu.height() + 2))))
        layout.addWidget(btn_menu)
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self._update_style()
        
    def _when(self) -> str:
        """Bugün 01:06 / Dün 20:32 / 20 Eyl 01:06 / 20 Eyl 2025."""
        dt = self.version_info.get("datetime")
        d_str = self.version_info.get("date_str", "")
        t_str = (self.version_info.get("time_str") or "")[:5]
        if dt is None:
            return f"{d_str} {t_str}".strip()
        today = datetime.now().date()
        days = (today - dt.date()).days
        if days == 0:
            return f"Bugün {t_str}"
        if days == 1:
            return f"Dün {t_str}"
        if dt.year == today.year:
            return f"{' '.join(d_str.split()[:2])} {t_str}"     # "20 Eyl 01:06"
        return d_str                                            # "20 Eyl 2025"

    def _context_menu(self, pos):
        menu = bk_ui.HeroPopoverMenu(self)
        menu.add_action("Çizelgeyi Aç", bk_ui.folder_glyph(bk_ui.BRAND, 16), on_click=lambda: self.action_requested.emit("open", self.slug, self.filename))
        if not self._is_active:
            menu.add_action("Aktif Çizelge Yap", bk_ui.star_glyph(bk_ui.BRAND, 16), on_click=lambda: self.action_requested.emit("set_active", self.slug, self.filename))
        menu.add_separator()

        current_folder_id = self.version_info.get("folder_id")
        menu.add_action("Klasörsüz (Genel) Yap", None, checkable=True, checked=(not current_folder_id),
                        on_click=lambda: self.move_to_folder_requested.emit(self.slug, self.filename, None))

        folders = version_store.list_folders(self.slug)
        for folder in folders:
            fid = folder.get("id")
            fname = folder.get("name", "")
            menu.add_action(fname, bk_ui.folder_line_glyph(bk_ui.INK_SOFT, 16), checkable=True, checked=(fid == current_folder_id),
                            on_click=lambda f=fid: self.move_to_folder_requested.emit(self.slug, self.filename, f))

        menu.add_separator()
        menu.add_action("Çizelge İsmi Tanımla...", None, on_click=self._edit_custom_name)
        menu.add_action("Not Düzenle...", None, on_click=self._edit_note)
        menu.add_separator()
        menu.add_action("Versiyonu Sil", bk_ui.trash_glyph(bk_ui.DANGER, 16), is_danger=True,
                        on_click=lambda: self.action_requested.emit("delete", self.slug, self.filename))

        if not isinstance(pos, QPoint):
            global_pos = QCursor.pos()
        elif 0 <= pos.x() <= self.width() and 0 <= pos.y() <= self.height():
            global_pos = self.mapToGlobal(pos)
        else:
            global_pos = pos

        menu.popup_at(global_pos)

    def _edit_custom_name(self):
        from PySide6.QtWidgets import QInputDialog
        curr = (self.version_info.get("custom_name") or "").strip()
        num = self.version_info.get("number", 0)
        new_name, ok = QInputDialog.getText(
            self, f"v{num} Çizelge İsmi",
            f"<b>v{num}</b> için özel çizelge ismi tanımlayın:<br><small style='color: #64748B;'>Örn: Oturan Program, Oturmaya Yakın, Taslak 2</small>",
            text=curr
        )
        if ok:
            import version_store
            version_store.assign_version_custom_name(self.slug, self.filename, new_name.strip())
            self._notify_parent_refresh_versions()

    def _edit_note(self):
        from PySide6.QtWidgets import QInputDialog
        curr = (self.version_info.get("note") or "").strip()
        _generic = {"kullanıcı kaydı", "değişiklikler kaydedildi", "kapanırken kaydedildi", "kapanış kaydı", "güncelleme öncesi kayıt", "başlangıç çizelgesi", "manual", "auto"}
        if curr.lower() in _generic:
            curr = ""
        num = self.version_info.get("number", 0)
        new_note, ok = QInputDialog.getText(
            self, f"v{num} Versiyon Notu",
            f"<b>v{num}</b> için özel not girin:<br><small style='color: #64748B;'>Örn: Cuma öğleden sonra boşaltıldı</small>",
            text=curr
        )
        if ok:
            import version_store
            version_store.assign_version_note(self.slug, self.filename, new_note.strip())
            self._notify_parent_refresh_versions()

    def _notify_parent_refresh_versions(self):
        p = self.parent()
        while p:
            if hasattr(p, "_refresh_versions"):
                p._refresh_versions()
                break
            p = p.parent() if hasattr(p, "parent") and callable(p.parent) else None
        
    def _update_style(self):
        divider = "border-bottom: 1px solid #F1F5F9;" if not self._is_last else "border-bottom: none;"
        if self._is_selected:
            self.setStyleSheet(f"""
                AppleVersionRow {{
                    background: {bk_ui.BRAND_TINT};
                    border: none;
                    {divider}
                }}
            """)
        else:
            self.setStyleSheet(f"""
                AppleVersionRow {{
                    background: #FFFFFF;
                    border: none;
                    {divider}
                }}
                AppleVersionRow:hover {{
                    background: {bk_ui.HOVER};
                }}
            """)
            
    def set_selected(self, sel):
        if bool(sel) == bool(self._is_selected):
            return
        self._is_selected = bool(sel)
        self._update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.pos())
            if child and isinstance(child, QAbstractButton):
                super().mousePressEvent(event)
                return
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

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(VERSION_DRAG_MIME):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(VERSION_DRAG_MIME):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat(VERSION_DRAG_MIME):
            raw = bytes(event.mimeData().data(VERSION_DRAG_MIME)).decode("utf-8")
            slug, _, filename = raw.partition("\n")
            if slug and filename:
                event.setDropAction(Qt.MoveAction)
                event.accept()
                p = self.parent()
                while p:
                    if hasattr(p, "folder_id"):
                        version_store.assign_version_folder(slug, filename, p.folder_id)
                        self._notify_parent_refresh_versions()
                        return
                    p = p.parent() if hasattr(p, "parent") and callable(p.parent) else None
                return
        event.ignore()


# ── Main Home Dashboard ──────────────────────────────────────────────

class InstitutionHeader(QWidget):
    """The selected institution: 3D avatar, title, state metadata, and action buttons."""

    CONTENT_H = 110
    filter_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._colour = None
        self._inst_name = "Seçili Kurum"
        self.setFixedHeight(self.CONTENT_H)
        self.setAttribute(Qt.WA_TranslucentBackground)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(32, 0, 32, 0)
        main_lay.setSpacing(0)

        # Top Row: Avatar + Title + Actions
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(14)

        # No institution mark here. The sidebar shows it a few centimetres
        # to the left, on the row that is highlighted, and the band already
        # carries the school's colour. A third copy said nothing new and
        # pushed the name off the 32px column everything below it lines up
        # on. Kept as a hidden widget only because set_institution writes
        # a pixmap into it.
        self.icon_lbl = QLabel(self)
        self.icon_lbl.hide()

        # Text Column
        #
        # İki etiket de dikeyde genişleyebildiği için artan yüksekliği
        # aralarında paylaşıyorlardı: isim tepeye yapışıyor, alt satır
        # dibe düşüyor, ortada kimseye ait olmayan bir boşluk kalıyordu.
        # Boşluk artık bloğun ALTINDA ve ÜSTÜNDE; isim ile alt satır
        # birbirine 2 piksel uzakta, tek bir künye gibi duruyor.
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.addStretch(1)

        self.title = QLabel("Seçili Kurum")
        self.title.setFont(bk_ui.font(18, QFont.DemiBold, spacing=-0.3))
        self.title.setStyleSheet(f"color: {bk_ui.INK}; background: transparent;")
        self.title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        text_col.addWidget(self.title)

        self.meta = QLabel("")
        self.meta.setFont(bk_ui.font(9.0))
        self.meta.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent;")
        self.meta.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        text_col.addWidget(self.meta)

        text_col.addStretch(1)

        top_row.addLayout(text_col, 1)

        # Action Buttons
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(0)
        actions.setAlignment(Qt.AlignVCenter)

        # Two buttons, one shape, one weight of icon.
        #
        # The secondary carried a full 3-D amber folder — a miniature
        # illustration inside a 36px control, in a colour the list below
        # it no longer uses for folders. An icon in a button is a label,
        # not a picture: it should be a line glyph at the weight of the
        # text beside it, in the same ink. The 3-D folder stays where it
        # earns its detail, on the rows.
        #
        # Both buttons now share a height, a radius, a font and an icon
        # size, so the pair reads as one control with two settings rather
        # than as two controls that happen to sit together.
        # HİYERARŞİ, SİMETRİ DEĞİL.
        #
        # Bu ikisi eşit değil: bu ekran çizelge açmak için var, klasör ise
        # biriken çizelgeleri toplamak için ara sıra kullanılan bir düzen
        # işi. Önce ayrı ama eşit ağırlıkta iki düğmeydiler, sonra bitişik
        # tek bir kontrol — ikisi de aynı hatayı yapıyordu: iki eylemi eşit
        # gösteriyordu. Birleşik hâlde beyaz yarı, mavi yarının yanında
        # sönük bir ek gibi duruyordu.
        #
        # Şimdi tek bir dolu düğme var — asıl eylem — ve onun solunda
        # çerçevesiz, ikonlu bir metin: klasör. Zemin yalnızca imleç
        # üstündeyken beliriyor. Mavi düğme yumuşak bir gölgeyle bandın bir
        # tık üstünde duruyor; bakışın ilk gittiği yer orası.
        # AYNI GÖVDE, FARKLI AĞIRLIK.
        #
        # Klasör düğmesi çerçevesizdi: zemini yalnızca imleç üstündeyken
        # beliriyordu, yani düğme olduğunu ancak dokununca söylüyordu. Bir
        # eylem, tıklanabilir olduğunu duyurmak için imleci beklememeli.
        # Zemin artık DURAĞAN hâlin kendisi; imleç geldiğinde bambaşka bir
        # şey oluyor — kenar kurumun rengine dönüyor, yazı ve ikon da
        # onunla birlikte renkleniyor, altına yumuşak bir gölge giriyor.
        # Yani hover artık "biraz daha beyaz" değil, ayrı bir durum.
        #
        # İkisi de aynı yükseklikte, aynı yuvarlaklıkta ve _sync_widths ile
        # aynı genişlikte: iki eşit gövde. Hiyerarşiyi boyut değil DOLGU
        # taşıyor — biri kurumun rengiyle dolu, diğeri beyaz.
        _BTN_H, _BTN_R, _ICON = 36, 18, 15
        _PAD = 18
        _btn_font = bk_ui.font(9.4, QFont.DemiBold)

        self.btn_new_folder = QPushButton("Yeni Klasör")
        self.btn_new_folder.setCursor(Qt.PointingHandCursor)
        self.btn_new_folder.setFixedHeight(_BTN_H)
        self.btn_new_folder.setFont(bk_ui.font(9.2, QFont.Medium))
        self.btn_new_folder.setIconSize(QSize(_ICON, _ICON))
        self._folder_icon_size = _ICON
        self._folder_shadow = QGraphicsDropShadowEffect(self.btn_new_folder)
        self._folder_shadow.setBlurRadius(14)
        self._folder_shadow.setOffset(0, 3)
        self._folder_shadow.setColor(QColor(15, 23, 42, 0))   # durağanken görünmez
        self.btn_new_folder.setGraphicsEffect(self._folder_shadow)
        self.btn_new_folder.installEventFilter(self)
        actions.addWidget(self.btn_new_folder)
        actions.addSpacing(8)

        self.btn_primary = QPushButton("Yeni Çizelge")
        self.btn_primary.setCursor(Qt.PointingHandCursor)
        self.btn_primary.setFixedHeight(_BTN_H)
        self.btn_primary.setFont(_btn_font)
        self.btn_primary.setIcon(QIcon(bk_ui.plus_glyph("#FFFFFF", _ICON)))
        self.btn_primary.setIconSize(QSize(_ICON, _ICON))
        _sh = QGraphicsDropShadowEffect(self.btn_primary)
        _sh.setBlurRadius(12)
        _sh.setOffset(0, 2)
        _sh.setColor(QColor(15, 74, 171, 55))
        self.btn_primary.setGraphicsEffect(_sh)
        self._primary_shadow = _sh
        actions.addWidget(self.btn_primary)

        self._btn_metrics = (_BTN_H, _BTN_R, _PAD)
        self._folder_hover = False
        self._restyle_primary()     # ikisini birden giydirir ve eşit genişliğe çeker

        top_row.addLayout(actions)
        main_lay.addLayout(top_row)

        # No filter bar. Four segments — Tümü / Aktifler / Klasörler /
        # Arşiv — put a permanent control above a list that, for most
        # institutions, holds a handful of rows: three of the four filters
        # would have shown the same thing as the fourth. Search already
        # narrows across every institution, and the list itself is grouped
        # by folder, so the segments were sorting something that was not
        # unsorted. The widget stays, hidden, because _rebuild_version_list
        # still reads the current filter.
        self.segmented_filter = bk_ui.AppleSegmentedControl(
            ["Tümü", "Aktifler", "Klasörler", "Arşiv"])
        self.segmented_filter.hide()
        self.segmented_filter.segment_changed.connect(
            lambda _, txt: self.filter_changed.emit(txt))

    def _accent(self):
        c = QColor(self._colour) if self._colour else QColor(bk_ui.BRAND)
        return c if c.isValid() else QColor(bk_ui.BRAND)

    def _wash(self):
        """Three stops, all the same colour — the band is flat. Callers
        still ask for a triple, so they get a constant one rather than a
        signature change rippling through five call sites for no gain."""
        flat = bk_ui.flat_tint(self._accent(), 0.16)
        return (flat, flat, flat)

    def _style_folder(self):
        """Klasör düğmesi: durağanken beyaz, imleç altındayken kurumun rengi.

        Durağan hâl artık hover'ın eski hâli — beyaz kapsül, ince kenar.
        Hover ise yeni bir şey: kenar ve yazı kurumun rengine döner, gölge
        açılır. İki durum birbirinin biraz koyusu değil, iki ayrı görüntü.
        """
        h, r, pad = self._btn_metrics
        c = self._accent()
        edge = QColor(c)
        edge.setAlpha(110)
        ink = QColor(c).darker(112).name() if self._folder_hover else bk_ui.INK_BODY
        self.btn_new_folder.setStyleSheet(f"""
            QPushButton {{
                background: #FFFFFF; color: {ink};
                border: 1px solid {'rgba(%d, %d, %d, 0.45)' % (c.red(), c.green(), c.blue())
                                   if self._folder_hover else 'rgba(15, 23, 42, 0.10)'};
                border-radius: {r}px; padding: 0px {pad}px;
            }}
            QPushButton:pressed {{ background: {bk_ui.flat_tint(c, 0.10).name()}; }}
            QPushButton:disabled {{
                background: rgba(255, 255, 255, 0.55); color: {bk_ui.INK_FAINT};
                border: 1px solid rgba(15, 23, 42, 0.06);
            }}
        """)
        glyph = c.darker(112).name() if self._folder_hover else bk_ui.INK_SOFT
        self.btn_new_folder.setIcon(
            QIcon(bk_ui.folder_line_glyph(glyph, self._folder_icon_size)))
        self._folder_shadow.setColor(
            QColor(c.red(), c.green(), c.blue(), 60) if self._folder_hover
            else QColor(15, 23, 42, 0))

    def eventFilter(self, obj, ev):
        if obj is getattr(self, "btn_new_folder", None):
            if ev.type() in (QEvent.Enter, QEvent.Leave):
                self._folder_hover = (ev.type() == QEvent.Enter)
                self._style_folder()
        return super().eventFilter(obj, ev)

    def _sync_widths(self):
        """İki düğme tek genişlikte. Metinler ("Yeni Klasör" / "Yeni Çizelge")
        birkaç piksel farkla yazıldığı için, eşitlemezsek gövdeler eşit
        görünmüyor — fark, yanlışlık gibi okunacak kadar küçük."""
        for b in (self.btn_new_folder, self.btn_primary):
            b.setMinimumWidth(0)
            b.updateGeometry()
        w = max(self.btn_new_folder.sizeHint().width(),
                self.btn_primary.sizeHint().width())
        self.btn_new_folder.setFixedWidth(w)
        self.btn_primary.setFixedWidth(w)

    def _restyle_primary(self):
        """The one filled control on the page takes the institution's own
        colour, like the band behind it and the folders below it. A fixed
        navy button on a green page was the last thing still insisting on
        a palette the rest of the screen had stopped using."""
        h, r, pad = self._btn_metrics
        c = self._accent()
        hover = QColor(c).darker(115)
        press = QColor(c).darker(132)
        self.btn_primary.setStyleSheet(f"""
            QPushButton {{
                background: {c.name()}; color: #FFFFFF;
                border: 1px solid {c.name()};
                border-radius: {r}px; padding: 0px {pad}px;
            }}
            QPushButton:hover {{ background: {hover.name()}; border-color: {hover.name()}; }}
            QPushButton:pressed {{ background: {press.name()}; border-color: {press.name()}; }}
            QPushButton:disabled {{
                background: #E2E8F0; color: #94A3B8; border: 1px solid #CBD5E1;
            }}
        """)
        self._primary_shadow.setColor(QColor(c.red(), c.green(), c.blue(), 70))
        self._style_folder()
        self._sync_widths()

    def set_institution(self, name, meta_text, colour=None):
        self._colour = colour
        self._inst_name = name
        self.title.setText(name)
        self.meta.setText(meta_text)
        self._restyle_primary()
        self.icon_lbl.setPixmap(make_3d_institution_icon(name, colour or bk_ui.BRAND, 44))
        w = self.window()
        if w:
            w.update()


# The old name, so nothing else has to change.
InstitutionHero = InstitutionHeader


class SlidingSelection(QWidget):
    """The selected institution, as one card that slides between rows.

    Every row used to paint its own selected state, so changing schools
    was a hard cut: one rectangle off, another on, nothing connecting
    them. A single card that travels says *the same object moved*.

    The institution's colour is a wash across the card, not a bar down its
    edge. A solid bar is a second object stuck to the side of the card:
    it has its own corners, fights the card's radius, and ends in two hard
    right angles no amount of clipping makes look intentional.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._from = QColor(bk_ui.BRAND)
        self._to = QColor(bk_ui.BRAND)
        self._mix_t = 1.0
        self._geo_anim = None
        self._tint_anim = None
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.hide()

    def _get_mix(self):
        return self._mix_t

    def _set_mix(self, value):
        self._mix_t = float(value)
        self.update()

    mix = Property(float, _get_mix, _set_mix)

    def _current(self):
        t = max(0.0, min(1.0, self._mix_t))
        return QColor(int(self._from.red() * (1 - t) + self._to.red() * t),
                      int(self._from.green() * (1 - t) + self._to.green() * t),
                      int(self._from.blue() * (1 - t) + self._to.blue() * t))

    def move_to(self, rect, colour=None, animated=True):
        target = QColor(colour) if colour else QColor(bk_ui.BRAND)
        if not target.isValid():
            target = QColor(bk_ui.BRAND)

        if self._geo_anim is not None:
            try:
                self._geo_anim.stop()
            except RuntimeError:
                pass
            self._geo_anim = None

        if self._tint_anim is not None:
            try:
                self._tint_anim.stop()
            except RuntimeError:
                pass
            self._tint_anim = None

        if not self.isVisible() or not animated:
            self._from = self._to = target
            self._mix_t = 1.0
            self.setGeometry(rect)
            self.show()
            self.lower()
            self.update()
            return

        self.lower()
        if target.name() != self._to.name():
            self._from = self._current()
            self._to = target
            self._mix_t = 0.0
            tint = QPropertyAnimation(self, b"mix", self)
            tint.setDuration(bk_ui.DUR_BASE)
            tint.setStartValue(0.0)
            tint.setEndValue(1.0)
            tint.setEasingCurve(bk_ui.EASE_OUT)
            tint.start()
            self._tint_anim = tint

        if self.geometry() == rect:
            return

        anim = QPropertyAnimation(self, b"geometry", self)
        anim.setDuration(bk_ui.DUR_BASE)
        anim.setStartValue(self.geometry())
        anim.setEndValue(rect)
        anim.setEasingCurve(bk_ui.EASE_OUT)
        anim.start()
        self._geo_anim = anim

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Inset slightly so antialiasing does not clip at the widget boundaries
        r = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        radius = 10.0

        path = QPainterPath()
        path.addRoundedRect(r, radius, radius)

        # 1. Clean solid white base
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawPath(path)

        # 2. Institution brand tint wash
        c = self._current()
        fill = QColor(c)
        fill.setAlpha(26)
        p.setBrush(fill)
        p.drawPath(path)

        # 3. Crisp, smooth border stroke
        edge = QColor(c)
        edge.setAlpha(80)
        p.setPen(QPen(edge, 1.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, radius, radius)
        p.end()


class SearchResultRow(QFrame):
    """One hit. Carries the thing it found AND where it lives, because the
    same version number legitimately exists in more than one institution
    and a list that shows only "Versiyon 82" twice is useless."""

    activated = Signal(object)

    def __init__(self, payload, title, subtitle, glyph, tone, parent=None):
        super().__init__(parent)
        self.payload = payload
        self._selected = False
        self.setFixedHeight(54)
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(12)

        mark = QLabel()
        mark.setFixedSize(34, 34)
        mark.setAlignment(Qt.AlignCenter)
        mark.setPixmap(glyph)
        mark.setStyleSheet(f"background: {tone}; border: none; border-radius: 10px;")
        mark.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(mark)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)

        self.title_lbl = QLabel(title)
        self.title_lbl.setFont(bk_ui.font(10.2, QFont.DemiBold))
        self.title_lbl.setStyleSheet(f"color: {bk_ui.INK}; background: transparent;")
        self.title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.title_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        col.addWidget(self.title_lbl)

        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setFont(bk_ui.font(8.8))
        self.sub_lbl.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent;")
        self.sub_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.sub_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        col.addWidget(self.sub_lbl)

        lay.addLayout(col, 1)

        chev = QLabel()
        chev.setPixmap(bk_ui.chevron_glyph(bk_ui.INK_FAINT, 14))
        chev.setFixedSize(14, 14)
        chev.setStyleSheet("background: transparent; border: none;")
        chev.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(chev, 0, Qt.AlignVCenter)

        self._restyle()

    def _restyle(self):
        bg = bk_ui.BRAND_TINT if self._selected else "transparent"
        hover = bk_ui.BRAND_TINT if self._selected else bk_ui.HOVER
        self.setStyleSheet(f"""
            SearchResultRow {{ background: {bg}; border: none; border-radius: 10px; }}
            SearchResultRow:hover {{ background: {hover}; }}
        """)

    def set_selected(self, on):
        if on != self._selected:
            self._selected = on
            self._restyle()

    def mousePressEvent(self, event):
        self.activated.emit(self.payload)


class SearchOverlay(bk_ui.MorphOverlay):
    """Search, as a panel that grows out of the search field.

    Searches institutions, folders, and versions across all schools,
    ranking version numbers accurately and displaying clean hierarchy.
    """

    open_institution = Signal(str)
    open_version = Signal(str, str)

    MAX_ROWS = 40

    def __init__(self, host, anchor):
        super().__init__(host, radius=16, dim=48, blur=18)
        self._anchor = anchor
        self._rows = []
        self._cursor = -1
        self._index_cache = None

        outer = QVBoxLayout(self.body)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 6px; margin: 4px 2px; }
            QScrollBar::handle:vertical { background: #D5D5DB; border-radius: 3px; min-height: 28px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        self.holder = QWidget()
        self.holder.setStyleSheet("background: transparent;")
        self.list_lay = QVBoxLayout(self.holder)
        self.list_lay.setContentsMargins(8, 8, 8, 8)
        self.list_lay.setSpacing(2)
        self.scroll.setWidget(self.holder)
        outer.addWidget(self.scroll)

        self.footer = QLabel("")
        self.footer.setFont(bk_ui.font(8.6))
        self.footer.setStyleSheet(
            f"color: {bk_ui.INK_FAINT}; background: transparent; "
            f"border-top: 1px solid {bk_ui.HAIRLINE}; padding: 7px 14px;")
        outer.addWidget(self.footer)

    def invalidate_index(self):
        self._index_cache = None

    def _get_search_index(self):
        if self._index_cache is not None:
            return self._index_cache

        index = []
        try:
            all_inst = version_store.list_institutions()
        except Exception:
            all_inst = []

        for inst in all_inst:
            name = inst.get("name", "") or ""
            slug = inst.get("slug", "") or ""
            inst_hay = f"{name} {slug}".lower()

            folders_list = []
            try:
                folders_raw = version_store.list_folders(slug)
                for f in folders_raw:
                    fname = f.get("name", "")
                    fid = f.get("id", "")
                    folders_list.append({
                        "slug": slug,
                        "folder_id": fid,
                        "name": fname,
                        "inst_name": name,
                        "haystack": f"{fname} {name} {slug}".lower()
                    })
            except Exception:
                pass

            versions_list = []
            try:
                vers_raw = version_store.list_versions(slug, source_filter="all")
                for v in vers_raw:
                    num_str = str(v.get("number", ""))
                    note_str = (v.get("note") or "").strip()
                    cname_str = (v.get("custom_name") or "").strip()
                    fname_str = (v.get("folder_name") or "").strip()
                    file_str = v.get("filename", "")
                    is_active = bool(v.get("is_active"))
                    dt_str = f"{v.get('date_str', '')} {v.get('time_str', '')[:5]}".strip()

                    v_hay = f"versiyon {num_str} {num_str} {cname_str} {name} {fname_str} {note_str} {file_str}".lower()
                    versions_list.append({
                        "slug": slug,
                        "filename": file_str,
                        "number": num_str,
                        "custom_name": cname_str,
                        "note": note_str,
                        "folder_name": fname_str,
                        "inst_name": name,
                        "date_time": dt_str,
                        "is_active": is_active,
                        "haystack": v_hay
                    })
            except Exception:
                pass

            inst_entry = {
                "slug": slug,
                "name": name,
                "color": inst.get("color"),
                "version_count": inst.get("version_count", len(versions_list)),
                "haystack": inst_hay
            }
            index.append((inst_entry, folders_list, versions_list))

        self._index_cache = index
        return index

    def _gather(self, query):
        import re
        q = query.strip().lower()
        institutions, folders, versions = [], [], []
        if not q:
            return institutions, folders, versions

        terms = q.split()
        index = self._get_search_index()

        num_match = re.search(r'\b\d+\b', q)
        target_num = num_match.group(0) if num_match else ""

        scored_versions = []

        for inst_entry, f_list, v_list in index:
            # Match institutions
            if all(t in inst_entry["haystack"] for t in terms):
                institutions.append(inst_entry)

            # Match folders
            for f in f_list:
                if all(t in f["haystack"] for t in terms):
                    folders.append(f)
                    if len(folders) >= self.MAX_ROWS:
                        break

            # Match versions with score priority
            for v in v_list:
                v_num = str(v.get("number", ""))
                matches = False
                score = 0

                if target_num and v_num == target_num:
                    matches = True
                    score += 1000
                elif target_num and v_num.startswith(target_num):
                    matches = True
                    score += 500
                elif all(t in v["haystack"] for t in terms):
                    matches = True
                    score += 100

                if matches:
                    if v.get("is_active"):
                        score += 50
                    scored_versions.append((score, v))

        scored_versions.sort(key=lambda item: item[0], reverse=True)
        versions = [item[1] for item in scored_versions[:self.MAX_ROWS]]

        return institutions, folders, versions

    def _section(self, text):
        lbl = bk_ui.section_label(text)
        lbl.setContentsMargins(8, 10, 8, 4)
        return lbl

    def refresh(self, query):
        while self.list_lay.count():
            item = self.list_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._rows = []
        self._cursor = -1

        institutions, folders, versions = self._gather(query)

        if institutions:
            self.list_lay.addWidget(self._section("Kurumlar"))
            for inst in institutions:
                row = SearchResultRow(
                    ("inst", inst.get("slug", "")),
                    inst.get("name", ""),
                    f"{inst.get('version_count', 0)} versiyon",
                    bk_ui.institution_3d(inst.get("name", ""), inst.get("color"), 26),
                    bk_ui.BRAND_TINT,
                )
                row.activated.connect(self._activate)
                self.list_lay.addWidget(row)
                self._rows.append(row)

        if folders:
            self.list_lay.addWidget(self._section("Klasörler"))
            for f in folders:
                row = SearchResultRow(
                    ("folder", f.get("slug", ""), f.get("folder_id", "")),
                    f.get("name", ""),
                    f"{f.get('inst_name', '')}  ·  Klasör",
                    bk_ui.folder_3d_glyph(size=24),
                    bk_ui.SURFACE_SUNK,
                )
                row.activated.connect(self._activate)
                self.list_lay.addWidget(row)
                self._rows.append(row)

        if versions:
            self.list_lay.addWidget(self._section("Versiyonlar"))
            for v in versions:
                num = v.get("number", "")
                note = (v.get("note") or "").strip()

                # Primary title is ALWAYS "Versiyon {number}"
                title = f"Versiyon {num}" if num else "Versiyon"

                # Subtitle: Kurum · [Klasör] · [Aktif] · Tarih · [Not]
                bits = [v.get("inst_name", "")]
                if v.get("folder_name"):
                    bits.append(f"{v['folder_name']}")
                if v.get("is_active"):
                    bits.append("● Aktif")
                if v.get("date_time"):
                    bits.append(v["date_time"])
                if note:
                    short_note = note[:55] + ("..." if len(note) > 55 else "")
                    bits.append(f"{short_note}")

                row = SearchResultRow(
                    ("ver", v.get("slug", ""), v.get("filename", "")),
                    title,
                    "  ·  ".join([b for b in bits if b]),
                    bk_ui.grid_glyph(bk_ui.INK_SOFT, 18),
                    bk_ui.SURFACE_SUNK,
                )
                row.activated.connect(self._activate)
                self.list_lay.addWidget(row)
                self._rows.append(row)

        if not self._rows:
            empty = QLabel(f'"{query}" için sonuç bulunamadı.')
            empty.setFont(bk_ui.font(10))
            empty.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent; padding: 26px 8px;")
            empty.setAlignment(Qt.AlignCenter)
            self.list_lay.addWidget(empty)

        self.list_lay.addStretch(1)
        counts = []
        if institutions:
            counts.append(f"{len(institutions)} kurum")
        if folders:
            counts.append(f"{len(folders)} klasör")
        if versions:
            counts.append(f"{len(versions)} versiyon")

        summary = " · ".join(counts)
        self.footer.setText(
            f"{summary}        ↑↓ gez · ↵ aç · esc kapat"
            if self._rows else "↵ veya esc ile kapatın")
        if self._rows:
            self._move_cursor(0)
        self._resize_panel()

    def _resize_panel(self):
        """Responsive: aligned flush with search input, wide and comfortably tall."""
        host = self._host
        tl = self._anchor.mapTo(host, QPoint(0, 0))

        # Panel width matches the search bar or expands cleanly rightwards
        available_w = host.width() - tl.x() - 24
        w = max(self._anchor.width(), min(available_w, 660))

        y = tl.y() + self._anchor.height() + 8
        room = max(260, host.height() - y - 24)

        num_rows = len(self._rows)
        if num_rows == 0:
            target_h = 160
        else:
            sections_count = 0
            if any(r.payload[0] == "inst" for r in self._rows):
                sections_count += 1
            if any(r.payload[0] == "folder" for r in self._rows):
                sections_count += 1
            if any(r.payload[0] == "ver" for r in self._rows):
                sections_count += 1
            
            target_h = 50 + (sections_count * 38) + (num_rows * 56)
            target_h = max(340, target_h)

        h = int(min(room, min(650, target_h)))

        x = tl.x()
        x = max(16, min(max(16, host.width() - w - 16), x))
        self._target = QRect(x, y, w, h)
        self.resize_panel_to(self._target)

    def open_for(self, query):
        self.refresh(query)
        if not self.isVisible() or getattr(self, "_closing", False):
            self.open_from(self._anchor, self._target)

    def _move_cursor(self, index):
        if not self._rows:
            return
        index = max(0, min(len(self._rows) - 1, index))
        for i, r in enumerate(self._rows):
            r.set_selected(i == index)
        self._cursor = index
        self.scroll.ensureWidgetVisible(self._rows[index], 0, 30)

    def move_selection(self, delta):
        if self._rows:
            self._move_cursor((self._cursor + delta) % len(self._rows))

    def activate_selection(self):
        if 0 <= self._cursor < len(self._rows):
            self._activate(self._rows[self._cursor].payload)

    def _activate(self, payload):
        self.request_close()
        if payload[0] == "inst":
            self.open_institution.emit(payload[1])
        elif payload[0] == "folder":
            self._on_search_pick_folder(payload[1], payload[2])
        else:
            self.open_version.emit(payload[1], payload[2])

    def _on_search_pick_folder(self, slug, folder_id):
        # Open institution first and select folder
        self.open_institution.emit(slug)


class ListSheet(QFrame):
    """The folder sheet — and the second half of the header's dissolve.

    The wash could not simply be painted further down the page: this sheet
    is an opaque child widget, and Qt draws children after their parent,
    so anything the page painted under it was covered. For the colour to
    run ONTO the folders, the folders' own surface has to carry it.

    So the ramp is split across the boundary rather than stopped at it.
    The page holds full tint right down to this sheet's top edge, and the
    sheet picks the same colour up at its first pixel and takes it to
    white over the next 170. The seam disappears because there is no step
    at it — both sides are the same colour on the same line.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def set_tint(self, _colour):
        """A no-op, kept so callers need not care.

        Carrying the header's colour down across the rows was built and
        then taken back out. The band's dissolve is spent on this sheet's
        top edge instead: the list starts on clean paper, which is what a
        list of files should do.
        """
        return

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        p.fillRect(r, QColor("#FFFFFF"))
        p.setPen(QPen(QColor(bk_ui.HAIRLINE), 1))
        p.drawLine(QPointF(r.left(), r.bottom() - 0.5),
                   QPointF(r.right(), r.bottom() - 0.5))
        p.end()


class SyncBadgeIcon(QWidget):
    """Apple-style 36x36 vector icon badge with 3 states: yellow (spinning), green (verified checkmark), red (alert)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self._state = "yellow"
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(25)
        self._timer.timeout.connect(self._on_tick)

    def set_state(self, state: str):
        self._state = state
        if state == "yellow":
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _on_tick(self):
        self._angle = (self._angle + 12) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        cx, cy = rect.width() / 2.0, rect.height() / 2.0
        r = min(cx, cy) - 2

        if self._state == "yellow":
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#FEF3C7"))
            p.drawEllipse(QPointF(cx, cy), r, r)
            p.save()
            p.translate(cx, cy)
            p.rotate(self._angle)
            pen = QPen(QColor("#D97706"), 2.6, Qt.SolidLine, Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            arc_r = r - 5.5
            p.drawArc(QRectF(-arc_r, -arc_r, arc_r * 2, arc_r * 2), 30 * 16, 120 * 16)
            p.drawArc(QRectF(-arc_r, -arc_r, arc_r * 2, arc_r * 2), 210 * 16, 120 * 16)
            p.restore()
        elif self._state == "green":
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#DCFCE7"))
            p.drawEllipse(QPointF(cx, cy), r, r)
            pen = QPen(QColor("#16A34A"), 2.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            path = QPainterPath()
            path.moveTo(cx - 5.5, cy + 0.2)
            path.lineTo(cx - 1.5, cy + 4.5)
            path.lineTo(cx + 6.0, cy - 4.5)
            p.drawPath(path)
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#FEE2E2"))
            p.drawEllipse(QPointF(cx, cy), r, r)
            pen = QPen(QColor("#DC2626"), 2.5, Qt.SolidLine, Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawLine(QPointF(cx, cy - 5), QPointF(cx, cy + 1))
            p.drawPoint(QPointF(cx, cy + 5))
        p.end()


class SyncCenterLoadingOverlay(QWidget):
    """
    Ekranın ortasında beliren, kırmızı-sarı-yeşil progress durumlarına ve
    'Kurumlar birbirine senkronizedir' verified onayına sahip Apple-style loading bar paneli.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)
        
        # Floating Card
        self.card = QFrame(self)
        self.card.setObjectName("syncLoadingCard")
        self.card.setFixedSize(430, 134)
        self.card.setStyleSheet("""
            QFrame#syncLoadingCard {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 16px;
            }
        """)
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)
        
        top_row = QHBoxLayout()
        top_row.setSpacing(14)
        
        self.badge = SyncBadgeIcon(self.card)
        top_row.addWidget(self.badge, 0, Qt.AlignVCenter)
        
        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        self.title_lbl = QLabel("Senkronizasyon Yapılıyor...")
        self.title_lbl.setFont(bk_ui.font(11.5, QFont.Bold, spacing=-0.2))
        self.title_lbl.setStyleSheet("color: #0F172A; background: transparent;")
        
        self.subtitle_lbl = QLabel("Lokal veriler kontrol ediliyor...")
        self.subtitle_lbl.setFont(bk_ui.font(9.5, QFont.Normal))
        self.subtitle_lbl.setStyleSheet("color: #64748B; background: transparent;")
        
        text_col.addWidget(self.title_lbl)
        text_col.addWidget(self.subtitle_lbl)
        top_row.addLayout(text_col, 1)
        
        self.percent_lbl = QLabel("0%")
        self.percent_lbl.setFont(bk_ui.font(9.5, QFont.DemiBold))
        self.percent_lbl.setStyleSheet("color: #D97706; background: transparent;")
        top_row.addWidget(self.percent_lbl, 0, Qt.AlignRight | Qt.AlignVCenter)
        
        card_layout.addLayout(top_row)
        
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(7)
        self.pbar.setTextVisible(False)
        self.pbar.setRange(0, 100)
        self.pbar.setValue(0)
        self._set_bar_color("#F59E0B")
        card_layout.addWidget(self.pbar)
        
        self.hide()

    def _set_bar_color(self, color_hex: str):
        self.pbar.setStyleSheet(f"""
            QProgressBar {{
                background: #F1F5F9;
                border: none;
                border-radius: 3.5px;
            }}
            QProgressBar::chunk {{
                background: {color_hex};
                border-radius: 3.5px;
            }}
        """)

    def _reposition(self):
        if self.parent():
            self.setGeometry(self.parent().rect())
            cx = (self.width() - self.card.width()) // 2
            cy = (self.height() - self.card.height()) // 2
            self.card.move(cx, max(40, cy))

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(15, 23, 42, 35))
        p.end()

    def show_stage(self, pct: int, detail: str):
        self._auto_hide_timer.stop()
        self._reposition()
        self.badge.set_state("yellow")
        self._set_bar_color("#F59E0B")
        self.title_lbl.setText("Senkronizasyon Yapılıyor...")
        self.title_lbl.setStyleSheet("color: #0F172A; background: transparent;")
        self.subtitle_lbl.setText(detail)
        self.pbar.setValue(pct)
        self.percent_lbl.setText(f"{pct}%")
        self.percent_lbl.setStyleSheet("color: #D97706; background: transparent;")
        self.show()
        self.raise_()

    def show_started(self, stage_msg="Lokal veriler kontrol ediliyor..."):
        self.show_stage(20, stage_msg)

    def show_progress(self, current: int, total: int, detail: str):
        self._reposition()
        self.badge.set_state("yellow")
        self._set_bar_color("#F59E0B")
        self.title_lbl.setText("Değişiklikler İndiriliyor...")
        self.subtitle_lbl.setText(detail)
        pct = 50 + int((current / max(1, total)) * 45)
        pct = min(95, pct)
        self.pbar.setValue(pct)
        self.percent_lbl.setText(f"{pct}%")
        self.percent_lbl.setStyleSheet("color: #D97706; background: transparent;")
        self.show()
        self.raise_()

    def show_completed(self, changed_count: int = 0, msg: str = "Kurumlar birbirine senkronizedir"):
        self._reposition()
        self.badge.set_state("green")
        self._set_bar_color("#10B981")
        self.pbar.setValue(100)
        self.percent_lbl.setText("100%")
        self.percent_lbl.setStyleSheet("color: #10B981; background: transparent; font-weight: bold;")
        self.title_lbl.setText("Kurumlar Birbirine Senkronizedir")
        self.title_lbl.setStyleSheet("color: #065F46; background: transparent; font-weight: bold;")
        
        if changed_count > 0:
            self.subtitle_lbl.setText(f"{changed_count} değişiklik başarıyla eşitlendi.")
        else:
            self.subtitle_lbl.setText("Tüm kurumlar ve versiyonlar güncel.")
            
        self.show()
        self.raise_()
        self._auto_hide_timer.start(1400)

    def show_failed(self, error_msg: str):
        self._reposition()
        self.badge.set_state("red")
        self._set_bar_color("#EF4444")
        self.pbar.setValue(100)
        self.percent_lbl.setText("Hata")
        self.percent_lbl.setStyleSheet("color: #EF4444; background: transparent; font-weight: bold;")
        self.title_lbl.setText("Senkronizasyon Hatası")
        self.title_lbl.setStyleSheet("color: #991B1B; background: transparent; font-weight: bold;")
        self.subtitle_lbl.setText(error_msg or "Sunucuya bağlanılamadı.")
        self.show()
        self.raise_()
        self._auto_hide_timer.start(3500)

    def hide_animated(self):
        self.hide()


class SyncStatusButton(QWidget):
    """Bulut durumu: bir rozet ve soluk bir kelime.

    Önce bütün kelime renkliydi ("Senkronize" yeşil): üst çubuktaki en
    parlak nesne, hiçbir şey olmadığında bile dikkat çekiyordu. Sonra renk
    6 piksellik bir noktaya indi — sessiz oldu ama bu sefer hiçbir şey
    söylemiyordu: yeşil nokta "iyi", turuncu nokta "bir şey oluyor" demek
    için rengin ezberlenmesini bekliyordu, üstelik renk körlüğünde ikisi
    aynı lekeydi.

    Şimdi yerinde bir ROZET var: dalgalı kenarı onu arayüzdeki noktalardan
    ayırır, içindeki işaret durumu rengi bilmeden okutur — tik (her şey
    yerinde), dönen ok (eşitleniyor), eğik çizgi (bağlantı yok). Kelime
    normalde gridir; bir sorun varsa o da renklenir.
    """
    clicked = Signal()

    BADGE = 14
    STATES = {
        "synced":  ("verified",      "#1B74D8"),   # markayla akraba, rozet gibi canlı
        "syncing": ("verified_sync", "#C9821A"),
        "offline": ("verified_off",  "#C7392F"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("syncStatusBtn")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(24)
        self._quiet = True

        lay = QHBoxLayout(self)
        lay.setContentsMargins(7, 2, 9, 2)
        lay.setSpacing(6)

        self.badge = QLabel()
        self.badge.setFixedSize(self.BADGE, self.BADGE)
        self.badge.setStyleSheet("background: transparent; border: none; padding: 0;")
        lay.addWidget(self.badge, 0, Qt.AlignVCenter)

        self.lbl = QLabel("Senkronize")
        self.lbl.setFont(bk_ui.font(8.8, QFont.Medium))
        self.lbl.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent; border: none; padding: 0;")
        lay.addWidget(self.lbl, 0, Qt.AlignVCenter)

        self.setStyleSheet("""
            QWidget#syncStatusBtn { background: transparent; border: none; border-radius: 6px; }
            QWidget#syncStatusBtn:hover { background: rgba(0, 0, 0, 0.04); }
            QLabel { background: transparent; border: none; padding: 0; }
        """)
        self.set_synced()

    def _apply(self, text, state, quiet, tip):
        name, colour = self.STATES[state]
        self.lbl.setText(text)
        self._quiet = quiet
        try:
            self.badge.setPixmap(ui_icons.pixmap(name, self.BADGE, colour))
        except Exception:
            self.badge.clear()
        self.lbl.setStyleSheet(
            f"color: {bk_ui.INK_SOFT if quiet else colour}; background: transparent; "
            f"border: none; padding: 0;")
        self.setToolTip(tip)
        self.update()

    def set_syncing(self, text="Eşitleniyor"):
        self._apply(text, "syncing", False, "Bulut veritabanı eşitleniyor…")

    def set_synced(self, text="Senkronize"):
        self._apply(text, "synced", True, "Tüm kurumlar güncel • Yenilemek için tıklayın")

    def set_offline(self, text="Çevrimdışı"):
        self._apply(text, "offline", False, "Sunucuya ulaşılamıyor (Yerel Mod)")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# Geriye dönük uyumluluk takma adları
SyncNudeIndicator = SyncStatusButton
SyncStatusPill = SyncStatusButton


class HomeDashboard(QWidget):
    open_timetable = Signal(str, str)  # slug, filename
    new_empty_timetable = Signal(str, str, str, object, object)  # slug, mode, sch_name, pool_id, pool_name
    logout_requested = Signal()        # Trigger logout & return to login screen
    # Carries a background sync's outcome back onto the GUI thread:
    # (pull_ok, pull_msg, push_ok, push_msg)
    sync_finished = Signal(bool, str, bool, str)
    manual_sync_progress = Signal(int, str)    # pct, detail
    manual_sync_done = Signal(bool, str, int)  # ok, msg, changed

    def __init__(self, auth_data=None, parent=None):
        super().__init__(parent)
        self.manual_sync_progress.connect(self._on_manual_sync_progress_gui)
        self.manual_sync_done.connect(self._on_manual_sync_done_gui)
        self.auth_data = auth_data or {}
        self._selected_slug = None
        self._selected_version = None
        self._search_query = ""
        self._search_overlay = None
        self._search_debounce = None
        self._unlocked_slugs = set()
        self._sync_in_flight = False
        self._show_center_overlay_on_sync = False
        self._initial_sync_pending = True
        # Coalesces the refresh bursts that arrive when several cloud events land
        # together; see _on_cloud_synced.
        self._refresh_debounce = None
        
        user_email = self.auth_data.get("email", "").lower()
        self.user_email = user_email
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
        self.setCursor(Qt.ArrowCursor)
        self._build_ui()
        self._refresh_institutions()
        
        # Cross-PC Realtime Database Sync on startup
        try:
            from cloud_sync import CloudSyncWorker
            self.cloud_worker = CloudSyncWorker(self)
            if self.auth_data:
                self.cloud_worker.set_auth(self.auth_data)
            self.cloud_worker.institutions_list_changed.connect(self._on_cloud_synced)
            self.cloud_worker.remote_data_updated.connect(lambda slug, fn: self._on_cloud_synced())
            self.cloud_worker.sync_started.connect(self._on_sync_started)
            self.cloud_worker.sync_progress.connect(self._on_sync_progress)
            self.cloud_worker.sync_completed.connect(self._on_sync_completed)
            self.cloud_worker.sync_failed.connect(self._on_sync_failed)
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
            self._realtime.version_notified.connect(self.cloud_worker.request_version)
            self._realtime.watch_many(i[0] for i in self._institution_signature)
        except Exception as rte:
            print(f"[HomeDashboard] Realtime sync init note: {rte}")

        QTimer.singleShot(200, self._warm_search_index)

    def _warm_search_index(self):
        try:
            ov = self._ensure_search_overlay()
            ov._get_search_index()
        except Exception:
            pass

    def _start_version_check(self):
        """Fire-and-forget: asks the release server whether a newer version
        than the one currently running exists, and updates the small status
        label next to the version number once it answers. Never blocks
        startup and never raises — see update_notifications.VersionStatusChecker."""
        self._version_checker = update_notifications.VersionStatusChecker()
        self._version_checker.result_ready.connect(self._on_version_check_result)
        self._version_checker.start()

    def _on_version_check_result(self, status: str, detail: str):
        if status == "latest":
            self.version_status_lbl.setText("Güncel")
            self.version_status_lbl.setStyleSheet("color: #16A34A; margin-left: 6px;")
        elif status == "update_available":
            self.version_status_lbl.setText(f"Güncelleme mevcut (v{detail})")
            self.version_status_lbl.setStyleSheet("color: #D97706; margin-left: 6px;")
        else:
            self.version_status_lbl.setText("")

    def _on_sync_started(self, stage_msg):
        """Arka plandan gelen indirme de ORTADA gösterilir.

        Bu sinyal yalnızca gerçekten indirilecek bir şey varken gelir (bkz.
        CloudSyncWorker: 'diff_found'). Eskiden ortadaki pencere sadece
        kullanıcı Yenile'ye bastığında açılıyordu; kendiliğinden başlayan
        senkronizasyon yalnızca sol üstteki küçük yazıda görünüyordu ve
        kullanıcı veriler değişirken ne olduğunu anlamıyordu.
        """
        if hasattr(self, "sync_pill"):
            self.sync_pill.set_syncing(stage_msg or "Güncelleniyor...")
        if hasattr(self, "sync_overlay"):
            self._show_center_overlay_on_sync = True
            self.sync_overlay.show_started(stage_msg)

    def _on_sync_progress(self, current, total, detail):
        if hasattr(self, "sync_pill"):
            self.sync_pill.set_syncing(f"İndiriliyor ({current}/{total})")
        if hasattr(self, "sync_overlay"):
            if not self.sync_overlay.isVisible():
                self._show_center_overlay_on_sync = True
                self.sync_overlay.show_started(detail or "Güncellemeler indiriliyor…")
            self.sync_overlay.show_progress(current, total, detail)

    def _on_sync_completed(self, changed_count, msg):
        self._initial_sync_pending = False
        was_overlay_active = getattr(self, "_show_center_overlay_on_sync", False) or (hasattr(self, "sync_overlay") and self.sync_overlay.isVisible())
        self._show_center_overlay_on_sync = False
        if hasattr(self, "sync_pill"):
            self.sync_pill.set_synced("Senkronize")
        if was_overlay_active and hasattr(self, "sync_overlay"):
            self.sync_overlay.show_completed(changed_count, msg or "Kurumlar birbirine senkronizedir")

    def _on_sync_failed(self, error_msg):
        was_overlay_active = getattr(self, "_show_center_overlay_on_sync", False) or (hasattr(self, "sync_overlay") and self.sync_overlay.isVisible())
        self._show_center_overlay_on_sync = False
        if hasattr(self, "sync_pill"):
            self.sync_pill.set_offline("Çevrimdışı")
        if was_overlay_active and hasattr(self, "sync_overlay"):
            self.sync_overlay.show_failed(error_msg)

    def _on_manual_sync_progress_gui(self, pct: int, detail: str):
        if hasattr(self, "sync_overlay"):
            self.sync_overlay.show_stage(pct, detail)

    def _on_manual_sync_done_gui(self, ok: bool, msg: str, changed: int):
        self._sync_in_flight = False
        if hasattr(self, "btn_refresh"):
            self.btn_refresh.setEnabled(True)
            self.btn_refresh.setToolTip("Yenile — buluttaki değişiklikleri getir")
        if ok:
            if hasattr(self, "sync_pill"):
                self.sync_pill.set_synced("Senkronize")
            if hasattr(self, "sync_overlay"):
                self.sync_overlay.show_completed(changed, "Kurumlar birbirine senkronizedir")
            self._refresh_institutions()
        else:
            if hasattr(self, "sync_pill"):
                self.sync_pill.set_offline("Çevrimdışı")
            if hasattr(self, "sync_overlay"):
                self.sync_overlay.show_failed(msg or "Sunucuya bağlanılamadı.")

    def _on_manual_refresh(self):
        """Yenile düğmesi: buluttan çek, panelleri yeniden kur."""
        if getattr(self, "_sync_in_flight", False):
            return
        self._sync_in_flight = True
        self._show_center_overlay_on_sync = True
        if hasattr(self, "sync_pill"):
            self.sync_pill.set_syncing("Eşitleniyor...")
        if hasattr(self, "sync_overlay"):
            self.sync_overlay.show_stage(20, "Lokal ve VDS verileri kontrol ediliyor...")
        if hasattr(self, "btn_refresh"):
            self.btn_refresh.setEnabled(False)
            self.btn_refresh.setToolTip("Yenileniyor...")

        import threading

        def _worker():
            ok, msg, changed = True, "", 0
            try:
                from cloud_sync import pull_all_from_rtdb
                def _on_manual_progress(stage, cur, tot, det):
                    if stage == "local_check":
                        self.manual_sync_progress.emit(25, det)
                    elif stage == "vds_check":
                        self.manual_sync_progress.emit(55, det)
                    elif stage == "diff":
                        self.manual_sync_progress.emit(85, det)
                    elif stage in ("diff_found", "downloading"):
                        pct = 85 + int((cur / max(1, tot)) * 12)
                        self.manual_sync_progress.emit(pct, det)

                ok, msg, changed = pull_all_from_rtdb(self.auth_data, progress_callback=_on_manual_progress)
            except Exception as exc:
                ok, msg = False, str(exc)
            finally:
                self.manual_sync_done.emit(ok, msg, changed)

        if not (self.auth_data or {}).get("is_offline", False):
            threading.Thread(target=_worker, daemon=True).start()
        else:
            self.manual_sync_done.emit(True, "", 0)

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
        if not self._refresh_debounce.isActive():
            self._refresh_debounce.start(0)

    def _do_refresh_all(self):
        # Dragging while the panel is rebuilt under the cursor destroys the widget
        # mid-gesture; let the drop finish and pick the refresh up afterwards.
        if QApplication.mouseButtons() & Qt.LeftButton:
            self._refresh_debounce.start(300)
            return
        self._refresh_institutions()

    def on_returned_to_dashboard(self):
        """Called when returning from timetable editor to dashboard.
        Instantly refreshes UI cards and pulls fresh updates/prunes from VDS.
        """
        self._refresh_institutions()
        if hasattr(self, "_selected_slug") and self._selected_slug:
            self._refresh_versions()
        if hasattr(self, "cloud_worker") and self.cloud_worker:
            self.cloud_worker.request_pull()
        else:
            self._start_initial_cloud_sync()


    def paintEvent(self, event):
        """The right-hand pane: one flat band, one texture, no ramp here.

        The institution's colour is a FLAT tint — no diagonal wash, no
        bloom. What fades is the handover: the band holds full strength
        down to the folder sheet's top edge and ListSheet carries the
        colour on across the first rows before letting go into white. The
        ramp spans the seam instead of stopping at it, which is why there
        is no visible event where the header ends.

        Painting it here rather than on the header widget is the only way
        that can work: a widget may only paint inside its own rectangle,
        and this band runs under a label the header does not own.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(BG_CANVAS))

        hero = getattr(self, "hero", None)
        # Bandın üst kenarı çubuğun ALT KENARIDIR. Burada 60 sabiti yazılıydı;
        # çubuk 52 piksele inince aradaki 8 piksel beyaz bir şerit olarak
        # kaldı ve renkli alan havada duruyormuş gibi göründü. Artık tek
        # kaynak TOPBAR_H.
        bar = getattr(self, "top_bar", None)
        x0 = 252
        y0 = bar.height() if bar is not None else TOPBAR_H
        w = max(1, self.width() - x0)
        if hero is None or w < 2 or self.height() < y0 + 2:
            p.end()
            return

        sheet_top = y0 + hero.CONTENT_H + 96
        scroll = getattr(self, "scroll_ver", None)
        if scroll is not None and scroll.isVisible():
            try:
                sheet_top = scroll.mapTo(self, QPoint(0, 0)).y()
            except Exception:
                pass
        sheet_top = max(y0 + hero.CONTENT_H + 24, min(sheet_top, self.height() - 8))

        accent = hero._accent()
        band = QRectF(x0, y0, w, sheet_top - y0)

        p.fillRect(band, bk_ui.flat_tint(accent, 0.16))
        p.save()
        p.setClipRect(band)
        bk_ui.paint_grid_texture(p, band, accent, line_alpha=26, block_alpha=30)
        p.restore()

        # The dissolve, landing on the folder sheet's own top edge — the
        # colour is spent exactly where the list begins, not carried over
        # it. That edge is measured from the sheet rather than guessed
        # with a constant, so it lands correctly however tall the header
        # happens to be.
        fade_h = min(band.height() * 0.62, 150.0)
        fade_top = band.bottom() - fade_h
        fade = QLinearGradient(0, fade_top, 0, band.bottom())
        for i in range(11):
            t = i / 10.0
            c = QColor(BG_CANVAS)
            # Ease-in: barely there where it starts, complete where it
            # meets the list. A straight ramp reads as a grey band laid
            # over the texture rather than as the texture running out.
            c.setAlpha(int(255 * (t ** 1.9)))
            fade.setColorAt(t, c)
        p.fillRect(QRectF(band.left(), fade_top, band.width(), fade_h), fade)

        floor_top = min(self.height() - 1.0, sheet_top + 200)
        if self.height() - floor_top > 40:
            floor = QRectF(x0, floor_top, w, self.height() - floor_top)
            p.save()
            p.setClipRect(floor)
            bk_ui.paint_grid_texture(p, floor, bk_ui.INK_FAINT, line_alpha=13,
                                     block_alpha=0, anchor="bottom", blocks=False)
            p.restore()

        p.end()

    def _build_ui(self):
        self.setStyleSheet(f"""
            HomeDashboard {{ font-family: {FONT_FAMILY}; }}
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
        
        # ── 1. Üst çubuk ─────────────────────────────────────────────
        #
        # Çıplak. Üç bilgi var ve üçü de kendi ağırlığında duruyor: nerede
        # olduğun (durum noktası + sürüm), ne aradığın (arama), kim olduğun
        # (avatar). Eskiden bu satırda altı ayrı kap vardı — yeşil bir durum
        # yazısı, dikey bir ayraç, gri bir arama kutusu, çerçeveli bir ⌘K
        # rozeti, dört ikonu saran gri bir hap ve bir kullanıcı kapsülü.
        # Hiçbiri tıklanmadan önce bir şey söylemiyordu, ama hepsi yer
        # kaplıyordu. Burada kaplar kalktı: zeminler yalnızca imleç üzerine
        # geldiğinde ya da arama odaklandığında beliriyor.
        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(TOPBAR_H)
        self.top_bar = top_bar
        top_bar.setStyleSheet(f"""
            QFrame#topBar {{
                background: {bk_ui.SURFACE};
                border: none;
                border-bottom: 1px solid #F0F0F3;
            }}
        """)

        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 0, 14, 0)
        top_layout.setSpacing(0)

        # ── Sol: durum ve sürüm ──
        title_container = QWidget()
        title_container.setMinimumWidth(236)
        title_box = QHBoxLayout(title_container)
        title_box.setSpacing(8)
        title_box.setContentsMargins(0, 0, 0, 0)

        self.sync_nude = SyncStatusButton()
        self.sync_pill = self.sync_nude
        self.sync_nude.clicked.connect(self._on_manual_refresh)
        title_box.addWidget(self.sync_nude, 0, Qt.AlignVCenter)

        # Sürüm: ayraçsız. İki soluk yazıyı ayırmak için çizgi gerekmez,
        # boşluk yeter.
        self.version_lbl = QLabel(APP_VERSION)
        self.version_lbl.setFont(bk_ui.font(8.6, QFont.Normal))
        self.version_lbl.setStyleSheet(
            f"color: #B6B6BD; background: transparent; border: none; padding: 0;")
        self.version_lbl.setToolTip(f"Chenkron {APP_VERSION}")
        title_box.addWidget(self.version_lbl, 0, Qt.AlignVCenter)

        self.version_status_lbl = QLabel("")
        self.version_status_lbl.setFont(bk_ui.font(8.6, QFont.DemiBold))
        self.version_status_lbl.setStyleSheet(
            f"color: {bk_ui.WARN}; background: transparent; border: none; padding: 0;")
        title_box.addWidget(self.version_status_lbl, 0, Qt.AlignVCenter)
        title_box.addStretch(1)
        self._start_version_check()
        top_layout.addWidget(title_container)
        top_layout.addStretch(1)

        # ── Orta: arama ──
        # Yerleşim ortalaması sol/sağ blokların genişliğine bağlıdır ve
        # kullanıcı adı uzayınca arama kayar. Bu yüzden arama çubuğun
        # ÇOCUĞU olarak mutlak ortaya konur (resizeEvent'te yeniden
        # ortalanır), yerleşimde yalnızca yeri ayrılır.
        # Kutu yok. Büyüteç ve yazı doğrudan çubuğun üstünde duruyor; zemin
        # yalnızca imleç üzerindeyken ya da yazarken beliriyor. Arama bu
        # ekranda en çok kullanılan şey, ama kullanılmadığı sürece sessiz.
        self.search_shell = QFrame()
        self.search_shell.setFixedSize(460, 34)
        self.search_shell.setObjectName("searchShell")
        self._search_css = """
            QFrame#searchShell {{
                background: {bg};
                border: 1px solid {line};
                border-radius: 9px;
            }}
        """
        # Boşta bile ince bir çizgi taşır: alan tamamen görünmez olunca
        # nereye yazılacağı belli olmuyordu. Çizgi çok soluk; imleç gelince
        # ve odaklanınca koyulaşır.
        self.search_shell.setStyleSheet(self._search_css.format(bg="transparent", line="#E7E7EC"))
        sc_lay = QHBoxLayout(self.search_shell)
        sc_lay.setContentsMargins(9, 0, 9, 0)
        sc_lay.setSpacing(8)

        search_icon = QLabel()
        search_icon.setPixmap(bk_ui.search_glyph("#A9A9B2", 14))
        search_icon.setFixedSize(14, 14)
        search_icon.setStyleSheet("background: transparent; border: none;")
        sc_lay.addWidget(search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ara")
        self.search_input.setFont(bk_ui.font(10))
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent; border: none; padding: 0px;
                color: {bk_ui.INK}; font-size: 13px;
                selection-background-color: {bk_ui.BRAND}; selection-color: #FFFFFF;
            }}
        """)
        # Açılışta odak almaz: çıplak çubuk, program açılır açılmaz beyaz bir
        # kutuyla başlamasın. Ctrl/⌘+K ve tıklama yine odaklar.
        self.search_input.setFocusPolicy(Qt.ClickFocus)
        self.search_input.setToolTip("Versiyon, klasör veya kurum ara")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.returnPressed.connect(self._activate_search_result)
        self.search_input.installEventFilter(self)
        self.search_shell.installEventFilter(self)
        sc_lay.addWidget(self.search_input, 1)

        # Kısayol ipucu: çerçevesiz, yalnızca soluk harfler. Odaklanınca
        # kaybolur — o an zaten arama kutusundasın.
        _combo = "⌘K" if sys.platform == "darwin" else "Ctrl K"
        self.kbd_hint = QLabel(_combo)
        self.kbd_hint.setFont(bk_ui.font(8.2, QFont.Medium, spacing=0.3))
        self.kbd_hint.setStyleSheet(
            "color: #C2C2C9; background: transparent; border: none; padding: 0;")
        self.kbd_hint.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        sc_lay.addWidget(self.kbd_hint, 0, Qt.AlignVCenter)

        self.search_shell.setParent(top_bar)
        self.search_shell.raise_()
        spacer = QWidget()
        spacer.setFixedWidth(1)
        top_layout.addWidget(spacer)
        top_layout.addStretch(1)
        top_layout.addSpacing(10)

        # ── Sağ: araçlar ──
        # Hap kalktı. Dört ikon kendi başına duruyor; zemin yalnızca imlecin
        # altındakinde beliriyor, o da daire biçiminde.
        def _tool(icon_name, tooltip):
            btn = QPushButton()
            # "Yenile" ikonu burada ucu olmayan bir yay olarak çiziliyordu ve
            # C harfi gibi okunuyordu; ortak ikon setindeki ok uçlu daire
            # niyeti söylüyor. Diğerleri panonun kendi setinden.
            if icon_name == "refresh":
                from ui_icons import pixmap as _uipix
                btn.setIcon(QIcon(_uipix("refresh", 17, "#5E5E67")))
            else:
                btn.setIcon(QIcon(make_dashboard_icon(icon_name, "#5E5E67", 17)))
            btn.setIconSize(QSize(17, 17))
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setToolTip(tooltip)
            btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; border-radius: 16px; }
                QPushButton:hover { background: rgba(0, 0, 0, 0.06); }
                QPushButton:pressed { background: rgba(0, 0, 0, 0.10); }
                QPushButton:disabled { background: transparent; }
            """)
            return btn

        tools = QWidget()
        cl_lay = QHBoxLayout(tools)
        cl_lay.setContentsMargins(0, 0, 0, 0)
        cl_lay.setSpacing(4)

        self.btn_refresh = _tool("refresh", "Yenile — buluttaki değişiklikleri getir")
        self.btn_refresh.clicked.connect(self._on_manual_refresh)
        cl_lay.addWidget(self.btn_refresh)

        self.btn_import = _tool("import", "Veri Aktar — başka kurumdan tanımları kopyala")
        self.btn_import.clicked.connect(self._on_cross_import_clicked)
        cl_lay.addWidget(self.btn_import)

        btn_help = _tool("help", "Yardım & SSS")
        btn_help.clicked.connect(self._on_help_clicked)
        cl_lay.addWidget(btn_help)

        btn_bell = _tool("bell", "Bildirimler")
        btn_bell.clicked.connect(self._on_notifications_clicked)
        cl_lay.addWidget(btn_bell)

        top_layout.addWidget(tools)
        top_layout.addSpacing(6)

        # ── Sağ: kimlik ──
        # Avatar zaten bir şekil; etrafına ikinci bir şekil gerekmiyor.
        self.user_capsule = QFrame()
        self.user_capsule.setObjectName("userCapsule")
        self.user_capsule.setCursor(Qt.PointingHandCursor)
        self.user_capsule.setFixedHeight(34)
        self.user_capsule.setStyleSheet("""
            QFrame#userCapsule { background: transparent; border: none; border-radius: 17px; }
            QFrame#userCapsule:hover { background: rgba(0, 0, 0, 0.05); }
        """)
        uc_lay = QHBoxLayout(self.user_capsule)
        uc_lay.setContentsMargins(4, 0, 9, 0)
        uc_lay.setSpacing(7)

        self.btn_avatar = QPushButton()
        self.btn_avatar.setCursor(Qt.PointingHandCursor)
        self.btn_avatar.setFocusPolicy(Qt.NoFocus)
        self.btn_avatar.setToolTip(f"{self.display_name} — profil ve ayarlar")
        self.btn_avatar.setFixedSize(26, 26)
        self.btn_avatar.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 13px; }")
        self._refresh_avatar_button()
        self.btn_avatar.clicked.connect(self._show_avatar_menu)
        uc_lay.addWidget(self.btn_avatar)

        self.user_lbl = QLabel(self.display_name)
        self.user_lbl.setFont(bk_ui.font(9.0, QFont.Medium))
        self.user_lbl.setStyleSheet(
            f"color: {bk_ui.INK_SOFT}; background: transparent; border: none;")
        self.user_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        uc_lay.addWidget(self.user_lbl)

        chev = QLabel()
        chev.setPixmap(bk_ui.chevron_glyph("#B6B6BD", 11, "down"))
        chev.setFixedSize(11, 11)
        chev.setStyleSheet("background: transparent; border: none;")
        chev.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        uc_lay.addWidget(chev, 0, Qt.AlignVCenter)

        self.user_capsule.mousePressEvent = lambda e: self._show_avatar_menu()
        top_layout.addWidget(self.user_capsule)

        _find = QShortcut(QKeySequence.Find, self)
        _find.activated.connect(self._focus_search)
        _find2 = QShortcut(QKeySequence("Ctrl+K"), self)
        _find2.activated.connect(self._focus_search)
        _esc = QShortcut(QKeySequence(Qt.Key_Escape), self.search_input)
        _esc.activated.connect(self.search_input.clear)
        self._paint_search(focus=False, hover=False)
        QTimer.singleShot(0, self._center_search)

        root.addWidget(top_bar)
        
        # ── 2. Main Body ─────────────────────────────────────────
        main_hbox = QHBoxLayout()
        main_hbox.setContentsMargins(0, 0, 0, 0)
        main_hbox.setSpacing(0)
        
        # Left Sidebar (Institutions)
        # The rail is sunk and the selection is raised — the inverse of
        # what was here, which was a flat tint on a flat white list. A
        # sidebar is chrome; the page is the paper. Making the chrome the
        # darker surface is what lets the content pane read as the thing
        # you are working in rather than as another panel of equal weight.
        left_panel = QFrame()
        left_panel.setObjectName("leftRail")
        left_panel.setFixedWidth(252)
        left_panel.setStyleSheet(f"""
            QFrame#leftRail {{
                background: #F5F5F7;
                border: none;
                border-right: 1px solid {bk_ui.HAIRLINE};
            }}
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 16, 12, 12)
        left_layout.setSpacing(0)

        left_hdr = QHBoxLayout()
        left_hdr.setContentsMargins(6, 0, 4, 0)
        left_hdr.setSpacing(8)

        left_title = QLabel("KURUMLAR")
        left_title.setFont(bk_ui.font(8.6, QFont.Bold, spacing=0.4))
        left_title.setStyleSheet(f"color: {bk_ui.INK_FAINT}; background: transparent;")
        left_hdr.addWidget(left_title)

        self.inst_count_lbl = QLabel("")
        self.inst_count_lbl.setFont(bk_ui.font(8.4))
        self.inst_count_lbl.setStyleSheet(f"color: {bk_ui.INK_FAINT}; background: transparent;")
        left_hdr.addWidget(self.inst_count_lbl, 0, Qt.AlignVCenter)
        left_hdr.addStretch(1)

        # Quick Add Button in sidebar header
        btn_quick_add = QPushButton()
        btn_quick_add.setIcon(QIcon(bk_ui.plus_glyph(bk_ui.INK_SOFT, 13)))
        btn_quick_add.setIconSize(QSize(13, 13))
        btn_quick_add.setFixedSize(24, 24)
        btn_quick_add.setCursor(Qt.PointingHandCursor)
        btn_quick_add.setToolTip("Yeni Kurum Ekle")
        btn_quick_add.setStyleSheet("""
            QPushButton { background: transparent; border: none; border-radius: 6px; }
            QPushButton:hover { background: rgba(0, 0, 0, 0.06); }
            QPushButton:pressed { background: rgba(0, 0, 0, 0.1); }
        """)
        btn_quick_add.clicked.connect(self._on_new_institution_clicked)
        left_hdr.addWidget(btn_quick_add)

        left_layout.addLayout(left_hdr)
        left_layout.addSpacing(10)

        scroll_inst = QScrollArea()
        scroll_inst.setWidgetResizable(True)
        scroll_inst.setFrameShape(QFrame.NoFrame)
        scroll_inst.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_inst.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 4px; background: transparent; margin: 0px; border: none; }
            QScrollBar::handle:vertical { background: rgba(0,0,0,0.14); border-radius: 2px; min-height: 24px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; border: none; background: none; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)

        self.inst_list_widget = QWidget()
        self.inst_list_widget.setStyleSheet("background: transparent; border: none;")
        self.inst_list_layout = QVBoxLayout(self.inst_list_widget)
        self.inst_list_layout.setContentsMargins(0, 0, 0, 0)
        self.inst_list_layout.setSpacing(4)
        self.inst_list_layout.addStretch(1)

        # Behind the rows, so it can slide underneath them.
        self.sel_card = SlidingSelection(self.inst_list_widget)

        scroll_inst.setWidget(self.inst_list_widget)
        left_layout.addWidget(scroll_inst, 1)

        left_layout.addSpacing(10)
        left_layout.addWidget(bk_ui.hairline())
        left_layout.addSpacing(10)

        btn_add_inst = QPushButton("Yeni Kurum Ekle")
        btn_add_inst.setFixedHeight(36)
        btn_add_inst.setCursor(Qt.PointingHandCursor)
        btn_add_inst.setFocusPolicy(Qt.NoFocus)
        btn_add_inst.setFont(bk_ui.font(9.2, QFont.DemiBold))
        btn_add_inst.setIcon(QIcon(bk_ui.plus_glyph(bk_ui.INK_BODY, 13)))
        btn_add_inst.setIconSize(QSize(13, 13))
        btn_add_inst.setToolTip("Yeni Kurum Ekle")
        btn_add_inst.setStyleSheet(f"""
            QPushButton {{
                background: #FFFFFF; color: {bk_ui.INK};
                border: 1px solid {bk_ui.HAIRLINE};
                border-radius: 9px; text-align: center;
            }}
            QPushButton:hover {{ background: #FFFFFF; border-color: {bk_ui.HAIRLINE_STRONG}; }}
            QPushButton:pressed {{ background: {bk_ui.SURFACE_SUNK}; }}
        """)
        btn_add_inst.clicked.connect(self._on_new_institution_clicked)
        self.btn_add_inst = btn_add_inst
        left_layout.addWidget(btn_add_inst)

        main_hbox.addWidget(left_panel)
        
        # Right Area
        right_panel = QFrame()
        right_panel.setObjectName("rightPane")
        right_panel.setAttribute(Qt.WA_TranslucentBackground)
        right_panel.setStyleSheet("QFrame#rightPane { background: transparent; border: none; }")
        self.right_panel_layout = QVBoxLayout(right_panel)
        self.right_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.right_panel_layout.setSpacing(0)
        
        self.hero = InstitutionHero()
        self.hero.btn_primary.clicked.connect(self._on_new_empty_clicked)
        self.hero.btn_new_folder.clicked.connect(self._on_new_folder_clicked)
        self.hero.filter_changed.connect(self._on_filter_changed)
        self.btn_new_empty = self.hero.btn_primary     # old names, same buttons
        self.btn_new_folder = self.hero.btn_new_folder
        self.right_panel_layout.addWidget(self.hero)

        _body = QWidget()
        _body.setStyleSheet("background: transparent;")
        _body_lay = QVBoxLayout(_body)
        # No side padding. The banner above runs to the window's own
        # edges; a card floating 32px inside them put two different width
        # systems on top of each other, and the composition came apart the
        # moment the fade ended. The list is now the same sheet, continued.
        _body_lay.setContentsMargins(0, 0, 0, 0)
        _body_lay.setSpacing(0)
        self.right_panel_layout.addWidget(_body, 1)
        # Everything built after this point lands inside the padded body.
        self.right_panel_layout = _body_lay

        # A chapter marker, not a caption.
        #
        # "Çizelgeler" used to be a bare label hanging off the left edge,
        # sitting between the banner's dissolve and the top of the list
        # card and belonging to neither. Centred, it holds the gap on its
        # own. No capsule: a pill would make a word look like a control it
        # is not. The trick is the ampersand — the two words are set small
        # and quiet in the interface face and the "&" between them is set
        # in a hand, italic, a size and a half up, in the institution's own
        # colour. An old typesetter's move, and it costs nothing.
        section_wrap = QWidget()
        section_wrap.setStyleSheet("background: transparent;")
        sw = QHBoxLayout(section_wrap)
        sw.setContentsMargins(0, 0, 0, 0)
        sw.setSpacing(0)

        self.lbl_section_and = QLabel("")
        self.lbl_section_and.setTextFormat(Qt.RichText)
        self.lbl_section_and.setAlignment(Qt.AlignCenter)
        self.lbl_section_and.setFixedHeight(26)
        self.lbl_section_and.setStyleSheet("background: transparent; border: none;")
        sw.addWidget(self.lbl_section_and, 1, Qt.AlignVCenter)
        self._update_section_and_color()

        self.right_panel_layout.addSpacing(16)
        self.right_panel_layout.addWidget(section_wrap)
        self.right_panel_layout.addSpacing(12)

        # Vestigial helpers. Nothing lays these out, but _refresh_versions
        # still calls show() on them, and a parentless widget that is shown
        # becomes a top-level window — that was the stray grey rectangle
        # with traffic lights that used to float above everything.
        self.primary_inst_badge = QLabel(right_panel)
        self.primary_inst_badge.hide()
        self.btn_set_primary = QPushButton(right_panel)
        self.btn_set_primary.hide()

        
        # Versions container
        self.right_panel_body = QVBoxLayout()
        self.right_panel_layout.addLayout(self.right_panel_body, 1)
        
        # Normal Versions List View
        self.right_content_widget = QWidget()
        self.right_content_widget.setStyleSheet("background: transparent;")
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
                background: transparent; width: 6px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #D5D5DB; border-radius: 3px; min-height: 34px;
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
        self.ver_list_layout.setContentsMargins(0, 0, 0, 0)
        self.ver_list_layout.setSpacing(0)
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
        # Not a copyright notice. This printed "© <year> <whichever
        # institution is selected>", which asserts that a school owns a
        # copyright in its own list of timetables and changes as you click
        # around. Kept only as a hidden widget because _refresh_versions
        # still writes to it.
        self.footer_lbl = QLabel("")
        self.footer_lbl.hide()
        
        main_hbox.addWidget(right_panel, 1)
        root.addLayout(main_hbox, 1)

        self.sync_overlay = SyncCenterLoadingOverlay(self)

    def _refresh_avatar_button(self):
        prof = get_user_profile(self.user_email)
        avatar_url = prof.get("avatar_url", "")
        parts = [p for p in self.display_name.strip().split() if p]
        initials = (parts[0][0] + parts[1][0]) if len(parts) >= 2 else (parts[0][:2] if parts else "U")
        
        pix = make_circular_avatar_pixmap(avatar_url, initials, size=28)
        self.btn_avatar.setIcon(QIcon(pix))
        self.btn_avatar.setIconSize(QSize(28, 28))

    def _show_avatar_menu(self):
        menu = bk_ui.HeroPopoverMenu(self)
        
        prof = get_user_profile(self.user_email)
        avatar_url = prof.get("avatar_url") or (self.auth_data or {}).get("avatar_url", "")
        parts = self.display_name.strip().split()
        initials = (parts[0][0] + parts[1][0]) if len(parts) >= 2 else (parts[0][:2] if parts else "U")
        av_pix = make_circular_avatar_pixmap(avatar_url, initials, size=34)
        
        user_title = prof.get("title") or ("Yönetici" if (self.auth_data and (self.auth_data.get("is_master") or self.auth_data.get("role") == "admin")) else "Kullanıcı")
        email_str = self.user_email or (self.auth_data.get("email", "") if self.auth_data else "")
        sub_text = f"{email_str} · {user_title}" if email_str else user_title
        menu.add_user_header(self.display_name, sub_text, av_pix)
        
        menu.add_action("Profili Düzenle", bk_ui.user_glyph(bk_ui.BRAND, 16), on_click=self._on_edit_profile_clicked)
        menu.add_action("Şifre Sıfırla / Değiştir", bk_ui.key_glyph(bk_ui.BRAND, 16), on_click=self._on_change_password_clicked)
        
        u_email = (self.auth_data.get("email", "") if self.auth_data else "").lower()
        if u_email in ("sehersanli@gmail.com", "sehersanli@chenki.net", "admin@chenki.net") or (self.auth_data and self.auth_data.get("is_master")):
            menu.add_action("Kurum Anahtarları", bk_ui.building_glyph(bk_ui.BRAND, 16), on_click=self._on_create_customer_account_clicked)
            
        menu.add_separator()
        menu.add_action("Oturumu Kapat", bk_ui.logout_glyph(bk_ui.DANGER, 16), is_danger=True, on_click=self._on_logout_clicked)
        
        anchor = getattr(self, "user_capsule", None) or getattr(self, "btn_avatar", None)
        menu.popup_below(anchor, align="right")
        self._active_popover = menu

    def _on_help_clicked(self):
        dlg = FAQDialog(self)
        dlg.exec()
        
    def _on_notifications_clicked(self):
        dlg = AppleNotificationsDialog(self)
        dlg.exec()
        
    def _on_edit_profile_clicked(self):
        dlg = AppleProfileDialog(current_email=self.user_email, parent=self)
        dlg.profile_updated.connect(self._on_profile_updated)
        dlg.exec()

    def _on_change_password_clicked(self):
        from dialogs.profile_dialog import AppleChangePasswordDialog
        dlg = AppleChangePasswordDialog(user_email=self.user_email, parent=self)
        dlg.exec()

    def _on_create_customer_account_clicked(self):
        from dialogs.customer_account_dialog import AppleCreateCustomerAccountDialog
        dlg = AppleCreateCustomerAccountDialog(parent=self)
        dlg.account_created.connect(lambda acc: self._refresh_institutions())
        dlg.exec()
        
    def _on_profile_updated(self, new_name: str, new_avatar_url: str, new_title: str = ""):
        self.display_name = new_name
        self.user_lbl.setText(f"Hoşgeldiniz, <b>{self.display_name}</b>")
        self._refresh_avatar_button()
    def _on_help_clicked(self):
        dlg = FAQDialog(self)
        dlg.exec()
        
    def _on_notifications_clicked(self):
        dlg = AppleNotificationsDialog(self)
        dlg.exec()
        
    def _on_edit_profile_clicked(self):
        dlg = AppleProfileDialog(current_email=self.user_email, parent=self)
        dlg.profile_updated.connect(self._on_profile_updated)
        dlg.exec()

    def _on_change_password_clicked(self):
        from dialogs.profile_dialog import AppleChangePasswordDialog
        dlg = AppleChangePasswordDialog(user_email=self.user_email, parent=self)
        dlg.exec()

    def _on_create_customer_account_clicked(self):
        from dialogs.customer_account_dialog import AppleCreateCustomerAccountDialog
        dlg = AppleCreateCustomerAccountDialog(parent=self)
        dlg.account_created.connect(lambda acc: self._refresh_institutions())
        dlg.exec()
        
    def _on_profile_updated(self, new_name: str, new_avatar_url: str, new_title: str = ""):
        self.display_name = new_name
        self.user_lbl.setText(f"Hoşgeldiniz, <b>{self.display_name}</b>")
        if isinstance(self.auth_data, dict):
            self.auth_data["full_name"] = new_name
            self.auth_data["name"] = new_name
            if new_title:
                self.auth_data["title"] = new_title
            if new_avatar_url:
                self.auth_data["avatar_url"] = new_avatar_url
        self._refresh_avatar_button()

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
            
            # Record account-level trust across devices
            if hasattr(self, "user_email") and self.user_email:
                version_store.add_trusted_user(self._selected_slug, self.user_email)
                
            # Cache password for this device so it won't be asked again
            version_store.save_device_password_cache(self._selected_slug, pwd)
            self.pwd_err_lbl.hide()
            self.pwd_card_input.clear()
            self.right_content_widget.show()
            self._update_primary_btn_state()
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
        
    def _ensure_search_overlay(self):
        if getattr(self, "_search_overlay", None) is None:
            self._search_overlay = SearchOverlay(self, self.search_shell)
            self._search_overlay.open_institution.connect(self._on_search_pick_institution)
            self._search_overlay.open_version.connect(self._on_search_pick_version)
        return self._search_overlay

    def _on_search_changed(self, text):
        """Opens the results panel; the search itself runs in the overlay."""
        query = text.strip()
        self._search_query = query.lower()

        if not query:
            if getattr(self, "_search_overlay", None) and self._search_overlay.isVisible():
                self._search_overlay.request_close()
            return

        # Debounced: fast responsive search
        if getattr(self, "_search_debounce", None) is None:
            self._search_debounce = QTimer(self)
            self._search_debounce.setSingleShot(True)
            self._search_debounce.timeout.connect(self._run_search)
        self._search_debounce.start(40)

    def _run_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        self._ensure_search_overlay().open_for(query)

    def _focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _activate_search_result(self):
        ov = getattr(self, "_search_overlay", None)
        if ov and ov.isVisible():
            ov.activate_selection()

    def eventFilter(self, obj, event):
        if obj in (getattr(self, "search_input", None), getattr(self, "search_shell", None)):
            t = event.type()
            if t == QEvent.KeyPress:
                ov = getattr(self, "_search_overlay", None)
                key = event.key()
                if key == Qt.Key_Escape:
                    if ov and ov.isVisible():
                        ov.request_close()
                    self.search_input.clear()
                    return True
                if ov and ov.isVisible():
                    if key == Qt.Key_Down:
                        ov.move_selection(1)
                        return True
                    if key == Qt.Key_Up:
                        ov.move_selection(-1)
                        return True
            elif t in (QEvent.MouseButtonPress, QEvent.FocusIn):
                if obj is getattr(self, "search_shell", None) and not self.search_input.hasFocus():
                    self.search_input.setFocus()
                self._paint_search(focus=True)
                query = self.search_input.text().strip()
                if query:
                    ov = self._ensure_search_overlay()
                    if not ov.isVisible() or getattr(ov, "_closing", False):
                        self._run_search()
            elif t == QEvent.FocusOut:
                self._paint_search(focus=False)
            elif t == QEvent.Enter:
                self._paint_search(hover=True)
            elif t == QEvent.Leave:
                self._paint_search(hover=False)
        return super().eventFilter(obj, event)

    def _paint_search(self, focus=None, hover=None):
        """Arama alanının zemini: normalde YOK, imleç ya da odak varken var.

        Çıplak bir çubukta arama kutusu görünmez olmasın diye zemin tamamen
        kaldırılmadı — yalnızca dokunulduğunda beliriyor. Odaktayken kısayol
        ipucu da gizleniyor: zaten oradasın.
        """
        if focus is not None:
            self._search_focused = bool(focus)
        if hover is not None:
            self._search_hovered = bool(hover)
        f = getattr(self, "_search_focused", False)
        h = getattr(self, "_search_hovered", False)
        shell = getattr(self, "search_shell", None)
        if shell is None:
            return
        if f:
            shell.setStyleSheet(self._search_css.format(bg="#FFFFFF", line="#CFCFD6"))
        elif h:
            shell.setStyleSheet(self._search_css.format(bg="#F7F7FA", line="#DCDCE2"))
        else:
            shell.setStyleSheet(self._search_css.format(bg="transparent", line="#E7E7EC"))
        hint = getattr(self, "kbd_hint", None)
        if hint is not None:
            hint.setVisible(not f)

    def _on_search_pick_institution(self, slug):
        self.search_input.clear()
        self._on_institution_selected(slug)

    def _on_search_pick_version(self, slug, filename):
        self.search_input.clear()
        if slug != self._selected_slug:
            self._on_institution_selected(slug)
        self.open_timetable.emit(slug, filename)

    def _center_search(self):
        """Aramayı üst çubuğun tam ortasına yerleştirir.

        Yerleşim ortalaması sol ve sağ blokların genişliğine bağlıdır;
        kullanıcı adı uzadıkça arama sola kayıyordu. Burada çubuğun kendi
        genişliği ölçülüp mutlak merkeze konuyor.
        """
        shell = getattr(self, "search_shell", None)
        bar = getattr(self, "top_bar", None)
        if shell is None or bar is None:
            return
        x = int((bar.width() - shell.width()) / 2)
        y = int((bar.height() - shell.height()) / 2)
        shell.move(max(8, x), max(0, y))
        shell.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._center_search()
        ov = getattr(self, "_search_overlay", None)
        if ov and ov.isVisible():
            ov.refresh_backdrop()
            ov._resize_panel()
        so = getattr(self, "sync_overlay", None)
        if so and so.isVisible():
            so._reposition()

    def _sync_selection_card(self, animated=True):
        """Puts the raised card on whichever row is selected."""
        card = getattr(self, "sel_card", None)
        if card is None:
            return
        for i in range(self.inst_list_layout.count() - 1):
            w = self.inst_list_layout.itemAt(i).widget()
            if isinstance(w, AppleInstitutionCard) and w.slug == self._selected_slug:
                card.move_to(w.geometry(), w.inst_color, animated=animated)
                return
        card.hide()

    def _refresh_institutions(self):
        institutions = version_store.list_institutions()
        tenant_type = (self.auth_data.get("tenant_type") if self.auth_data else None) or "internal"
        allowed_slugs = set((self.auth_data.get("allowed_institutions") if self.auth_data else None) or [])

        filtered = []
        for inst in institutions:
            slug = inst.get("slug", "")
            if slug.startswith("_system_") or slug.startswith("_auth_"):
                continue
            if tenant_type == "isolated" and slug not in allowed_slugs:
                # Isolated external customer account: DO NOT display internal group institutions
                continue
            # The sidebar no longer filters itself while you type. Search
            # results live in their own panel, and hiding the list underneath
            # meant dismissing the panel left a sidebar missing half its rows.
            filtered.append(inst)
            
        signature = [(i.get("slug"), i.get("name"), i.get("color"),
                      i.get("is_primary"), i.get("has_password"),
                      i.get("version_count"), i.get("last_updated_str")) for i in filtered]
        if getattr(self, "_institution_signature", None) == signature:
            self._refresh_versions()
            return
        self._institution_signature = signature
        if getattr(self, "_realtime", None):
            self._realtime.watch_many(i[0] for i in signature)

        existing_cards = []
        for i in range(self.inst_list_layout.count() - 1):
            w = self.inst_list_layout.itemAt(i).widget()
            if isinstance(w, AppleInstitutionCard):
                existing_cards.append(w)

        if len(existing_cards) == len(filtered) and [c.slug for c in existing_cards] == [i["slug"] for i in filtered]:
            for card, inst in zip(existing_cards, filtered):
                card.update_data(inst, is_selected=(inst["slug"] == self._selected_slug))
        else:
            while self.inst_list_layout.count() > 1:
                item = self.inst_list_layout.takeAt(0)
                if item.widget():
                    item.widget().hide()
                    item.widget().deleteLater()

            for inst in filtered:
                is_sel = (inst["slug"] == self._selected_slug)
                card = AppleInstitutionCard(inst, is_selected=is_sel, is_master_admin=self.is_master_admin)
                card.clicked.connect(self._on_institution_selected)
                self.inst_list_layout.insertWidget(self.inst_list_layout.count() - 1, card)

        if hasattr(self, "inst_count_lbl"):
            self.inst_count_lbl.setText(str(len(filtered)) if filtered else "")
        # The list was just rebuilt, so the card is placed rather than
        # flown: animating from wherever it sat before a refresh is motion
        # that describes nothing.
        QTimer.singleShot(0, lambda: self._sync_selection_card(animated=False))
            
        if not self._selected_slug and filtered:
            self._on_institution_selected(filtered[0]["slug"])
        elif filtered and self._selected_slug not in [i["slug"] for i in filtered]:
            self._on_institution_selected(filtered[0]["slug"])
        elif not filtered:
            self._selected_slug = None
            self.hero.set_institution("Kurum bulunmuyor",
                                      "Başlamak için soldan bir kurum ekleyin.")
            self._refresh_versions()
        elif self._selected_slug:
            self._refresh_versions()
            
    def _on_institution_selected(self, slug):
        if slug == self._selected_slug:
            return
        self._selected_slug = slug
        version_store.set_last_active_institution_slug(slug)
        self._selected_version = None
        
        # Auto-unlock if this user or device is trusted / has authenticated
        if (
            getattr(self, "is_master_admin", False)
            or (hasattr(self, "user_email") and self.user_email and version_store.is_trusted_user(slug, self.user_email))
            or version_store.check_device_password_cache(slug)
        ):
            self._unlocked_slugs.add(slug)
        
        for i in range(self.inst_list_layout.count() - 1):
            w = self.inst_list_layout.itemAt(i).widget()
            if isinstance(w, AppleInstitutionCard):
                w.set_selected(w.slug == slug)
        self._sync_selection_card(animated=True)

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
        target_fid = str(folder_id).strip()
        count = sum(
            1 for v in version_store.list_versions(self._selected_slug)
            if str(v.get("folder_id") or "").strip() == target_fid
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

    def _on_delete_unfoldered(self):
        if not self._selected_slug:
            return
        unfoldered = [v for v in version_store.list_versions(self._selected_slug) if not v.get("folder_id")]
        count = len(unfoldered)
        if count == 0:
            show_apple_info(self, "Klasörsüz Çizelge Yok", "Bu kurumda silinecek klasörsüz çizelge bulunmuyor.", is_success=True)
            return
        dlg = AppleConfirmDialog(
            title="Klasörsüz Çizelgeleri Sil",
            message=f"Klasörsüz (Genel) durumdaki {count} çizelge kalıcı olarak silinecek ve buluttan da kaldırılacaktır. Devam etmek istiyor musunuz?",
            confirm_text="Tümünü Sil",
            cancel_text="Vazgeç",
            is_destructive=True,
            parent=self
        )
        if dlg.exec() != QDialog.Accepted:
            return
        from save_dialog import run_apple_save_sequence
        run_apple_save_sequence(self, duration_seconds=0.3, title="Çizelgeler Siliniyor", message="Klasörsüz çizelgeler kaldırılıyor...")
        version_store.delete_unfoldered_versions(self._selected_slug)
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
        
    def _update_section_and_color(self, color_hex=None):
        """The chapter marker: two quiet words and one ampersand doing all
        the work.

        The words sit in the interface face at label size. The "&" is set
        in a swash italic, a size and a half up, in the institution's own
        colour — an old typesetter's move, and the only place on the page
        where a second face appears. It is worth the exception because it
        costs nothing else: no rule, no capsule, no second colour anywhere
        around it.
        """
        if not hasattr(self, "lbl_section_and") or not self.lbl_section_and:
            return
        if not color_hex:
            meta = version_store.get_institution_meta(self._selected_slug) if self._selected_slug else {}
            color_hex = meta.get("color") or bk_ui.BRAND
        amp = bk_ui.ampersand_family()
        ui = FONT_FAMILY.split(",")[0].strip().replace("'", "")
        self.lbl_section_and.setText(
            f'<span style="font-family:\'{ui}\'; font-size:11.5px;'
            f' color:{bk_ui.INK_SOFT};">Klasörler</span>'
            # The gaps live OUTSIDE the ampersand's span, in the interface
            # font. Inside it they are set in the swash italic, whose glyph
            # advance swallows them — which is why the "&" ended up welded
            # to the word after it.
            f'&nbsp;&nbsp;'
            f'<span style="font-family:\'{amp}\'; font-size:17px; font-style:italic;'
            f' color:{color_hex};">&amp;</span>'
            f'&nbsp;&nbsp;'
            f'<span style="font-family:\'{ui}\'; font-size:11.5px;'
            f' color:{bk_ui.INK_SOFT};">Versiyonlar</span>'
        )

    def _refresh_versions(self):
        if not self._selected_slug:
            return

        inst_dir = version_store._institution_dir(self._selected_slug)
        if not os.path.isdir(inst_dir):
            self._selected_slug = None
            return

        from sync_coordinator import file_signature
        ver_dir = os.path.join(inst_dir, "versions")
        signature = (
            self._selected_slug, file_signature(os.path.join(inst_dir, "meta.json")),
            getattr(self, "_current_filter", "Tümü"),
            self._selected_slug in self._unlocked_slugs,
            tuple((entry.name, entry.stat().st_mtime_ns, entry.stat().st_size)
                  for entry in sorted(os.scandir(ver_dir), key=lambda e: e.name)
                  if entry.name.endswith(".roz")) if os.path.isdir(ver_dir) else (),
        )
        if getattr(self, "_version_list_signature", None) == signature:
            return
        self._version_list_signature = signature

        # The whole list is rebuilt below, which resets the viewport to the top and
        # collapses every folder. That is jarring on its own and actively disruptive
        # when the rebuild was triggered by a background cloud sync the user did not
        # ask for, so scroll offset and which folders were open are restored after.
        scroll_bar = self.scroll_ver.verticalScrollBar() if hasattr(self, "scroll_ver") else None
        prev_scroll = scroll_bar.value() if scroll_bar is not None else 0
        if not hasattr(self, "_open_folders_by_slug"):
            self._open_folders_by_slug = {}
        prev_slug = getattr(self, "_rendered_slug", None)
        if prev_slug and prev_slug != self._selected_slug:
            self._open_folders_by_slug[prev_slug] = {
                g.folder_id for g in self.findChildren(CollapsibleVersionGroup)
                if not g.is_collapsed
            }
        self._rendered_slug = self._selected_slug
        prev_open_folders = self._open_folders_by_slug.get(self._selected_slug, {"active"})
        self._rebuild_version_list(inst_dir, prev_open_folders)
        
        self.ver_list_widget.show()

        if scroll_bar is not None and prev_scroll:
            from PySide6.QtCore import QTimer
            # After the layout has settled, or the maximum is still 0 and the value
            # would be clamped away.
            QTimer.singleShot(0, lambda: scroll_bar.setValue(min(prev_scroll, scroll_bar.maximum())))

    def _rebuild_version_list(self, inst_dir, prev_open_folders):
        meta = version_store.get_institution_meta(self._selected_slug)
        inst_name = meta.get("name", self._selected_slug)
        is_prim = bool(meta.get("is_primary", False))
        

        self.pwd_card_title.setText(f"{inst_name}")
        
        # Both widgets are vestigial (see _build_ui) — no layout positions them, so
        # showing either one only ever produced a stray floating rectangle. The primary
        # institution is already indicated on its card, so they simply stay hidden.
        self.primary_inst_badge.hide()
        self.btn_set_primary.hide()
        
        # Completely and cleanly clear all existing items from layout
        self.ver_list_widget.hide()
        
        while self.ver_list_layout.count() > 0:
            item = self.ver_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.deleteLater()
        versions = version_store.list_versions(self._selected_slug, source_filter="all")
        active_ver = version_store.get_active_version(self._selected_slug)
        

        
        last_upd = version_store.tr_month_text(meta.get("last_updated_str"))
        if not last_upd and versions:
            last_upd = f"{versions[0]['date_str']} {versions[0]['time_str']}"

        folders_for_meta = version_store.list_folders(self._selected_slug)
        bits = [f"{len(versions)} versiyon"]
        if folders_for_meta:
            bits.append(f"{len(folders_for_meta)} klasör")
        if last_upd:
            bits.append(f"son güncelleme {last_upd}")
        self.hero.set_institution(inst_name, "  ·  ".join(bits), meta.get("color"))
        self._update_section_and_color(meta.get("color"))
        self._update_primary_btn_state()

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
            # Full-bleed sheet, not a floating card: no side border, no
            # radius, only the hairlines where it meets what is above and
            # below it. The rows carry their own 32px indent, which lands
            # them on the same vertical line as the institution's name in
            # the banner — that shared line is what makes the two halves
            # read as one page rather than two components.
            table_card = ListSheet()
            table_card.set_tint(self.hero._wash()[2])
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

            _inst_colour = (version_store.get_institution_meta(self._selected_slug) or {}).get(
                "color") or bk_ui.BRAND

            def _add_group(title, icon, color, items, folder_id=None, show_folder_actions=False):
                keep_open = folder_id in prev_open_folders or any(
                    v["filename"] == self._selected_version for v in items
                )
                group = CollapsibleVersionGroup(
                    title, icon, f"{len(items)} versiyon", color, is_collapsed=not keep_open,
                    folder_id=folder_id, is_drop_target=True, show_folder_actions=show_folder_actions,
                )
                def _rows(items=items, slug=self._selected_slug, active=active_ver):
                    out = []
                    for idx, v in enumerate(items):
                        out.append(_wire(AppleVersionRow(
                            slug, v,
                            is_active=(v["filename"] == active),
                            is_last=(idx == len(items) - 1))))
                    return out

                group.set_row_factory(_rows)
                if keep_open:
                    # Already open on arrival, so its rows are needed now.
                    group._ensure_rows()
                group.version_dropped.connect(
                    lambda slug, filename, fid=folder_id: self._on_version_dropped_on_folder(slug, filename, fid)
                )
                if show_folder_actions:
                    if folder_id is not None and str(folder_id).lower() != "active":
                        group.rename_requested.connect(lambda fid=folder_id, name=title: self._on_folder_rename(fid, name))
                        group.delete_requested.connect(lambda fid=folder_id, name=title: self._on_folder_delete(fid, name))
                    elif folder_id is None:
                        group.delete_requested.connect(self._on_delete_unfoldered)
                table_lay.addWidget(group)

            cur_filter = getattr(self, "_current_filter", "Tümü")
            if cur_filter == "Aktifler":
                active_list = [v for v in versions if v["filename"] == active_ver]
                if active_list:
                    _add_group("Aktif Çizelge", "active", _inst_colour, active_list, folder_id="active", show_folder_actions=False)
                else:
                    empty_f = QLabel("Henüz aktif olarak belirlenmiş bir çizelge yok.")
                    empty_f.setFont(bk_ui.font(9.5))
                    empty_f.setStyleSheet(f"color: {bk_ui.INK_SOFT}; padding: 30px;")
                    empty_f.setAlignment(Qt.AlignCenter)
                    table_lay.addWidget(empty_f)
            elif cur_filter == "Klasörler":
                if folder_order:
                    by_folder = {fid: [] for fid in folder_order}
                    for v in versions:
                        fid = v.get("folder_id")
                        if fid and fid in folder_names:
                            by_folder.setdefault(fid, []).append(v)
                    for fid in folder_order:
                        _add_group(folder_names[fid], "folder", _inst_colour, by_folder.get(fid, []), folder_id=fid, show_folder_actions=True)
                else:
                    empty_f = QLabel("Bu kurumda henüz klasör oluşturulmamış.")
                    empty_f.setFont(bk_ui.font(9.5))
                    empty_f.setStyleSheet(f"color: {bk_ui.INK_SOFT}; padding: 30px;")
                    empty_f.setAlignment(Qt.AlignCenter)
                    table_lay.addWidget(empty_f)
            elif cur_filter == "Arşiv":
                older_list = [v for v in versions if v["filename"] != active_ver and not v.get("folder_id")]
                if older_list:
                    _add_group("Arşiv / Klasörsüz", "history", "#64748B", older_list, folder_id=None, show_folder_actions=True)
                else:
                    empty_f = QLabel("Arşivde çizelge bulunmuyor.")
                    empty_f.setFont(bk_ui.font(9.5))
                    empty_f.setStyleSheet(f"color: {bk_ui.INK_SOFT}; padding: 30px;")
                    empty_f.setAlignment(Qt.AlignCenter)
                    table_lay.addWidget(empty_f)
            else:  # "Tümü"
                if not folder_order:
                    active_list = [v for v in versions if v["filename"] == active_ver]
                    older_list = [v for v in versions if v["filename"] != active_ver]
                    if active_list:
                        _add_group("Aktif Çizelge", "active", _inst_colour, active_list, folder_id="active", show_folder_actions=False)
                    if older_list:
                        _add_group("Geçmiş Versiyonlar", "history", "#64748B", older_list, folder_id=None, show_folder_actions=True)
                else:
                    by_folder = {fid: [] for fid in folder_order}
                    unfoldered = []
                    for v in versions:
                        fid = v.get("folder_id")
                        if fid and fid in folder_names:
                            by_folder.setdefault(fid, []).append(v)
                        else:
                            unfoldered.append(v)

                    for fid in folder_order:
                        _add_group(folder_names[fid], "folder", _inst_colour, by_folder.get(fid, []), folder_id=fid, show_folder_actions=True)

                    if unfoldered:
                        _add_group("Klasörsüz (Genel)", "history", "#64748B", unfoldered, folder_id=None, show_folder_actions=True)

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
            self.password_overlay_widget.hide()
            self.right_content_widget.show()
            self._update_primary_btn_state()

    def _update_primary_btn_state(self):
        """Ensures the '+ Yeni Çizelge' button on the dashboard is active for the selected institution."""
        if not self._selected_slug:
            self.hero.btn_primary.setEnabled(False)
            self.hero.btn_primary.setToolTip("Bir kurum seçin.")
            return

        self.hero.btn_primary.setEnabled(True)
        self.hero.btn_primary.setToolTip("Yeni boş çalışma alanı ve çizelge oluşturun.")

    def _on_filter_changed(self, filter_text):
        self._current_filter = filter_text
        self._refresh_versions()
            
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
            
            # If current user is isolated, add this newly created slug to allowed_institutions
            if self.auth_data and self.auth_data.get("tenant_type") == "isolated":
                allowed = self.auth_data.setdefault("allowed_institutions", [])
                if inst["slug"] not in allowed:
                    allowed.append(inst["slug"])
                from api_client import api_client
                stored = api_client.get_stored_auth_data() or {}
                stored["allowed_institutions"] = allowed
                api_client.save_token(stored)
                
                # Update registered accounts map
                em = self.auth_data.get("email", "").lower()
                if em:
                    accs = api_client.load_registered_accounts()
                    if em in accs:
                        accs[em]["allowed_institutions"] = allowed
                        api_client.save_registered_accounts_locally(accs)
            
            if self.auth_data and not self.auth_data.get("is_offline"):
                from cloud_sync import push_institution_to_rtdb
                push_institution_to_rtdb(inst["slug"], self.auth_data)
                
            self._refresh_institutions()
            
    def _on_version_dropped_on_folder(self, slug, filename, folder_id):
        if not slug or not filename:
            return
        version_store.assign_version_folder(slug, filename, folder_id)
        self._refresh_versions()

    def _on_new_empty_clicked(self):
        if not self._selected_slug:
            return
        from dialogs.new_schedule_dialog import AppleNewScheduleDialog
        dlg = AppleNewScheduleDialog(slug=self._selected_slug, parent=self)
        if dlg.exec() == QDialog.Accepted:
            mode, sch_name, pool_id, pool_name = dlg.get_selection()
            if not mode:
                return
            from save_dialog import run_apple_save_sequence
            title_msg = "Mevcut Veriler Aktarılıyor" if mode == "current_data" else "Yeni Veri Havuzu Hazırlanıyor"
            display_name = pool_name or sch_name or "Yeni Çizelge"
            sub_msg = f"'{display_name}' çalışma alanı oluşturuluyor..."
            run_apple_save_sequence(self, duration_seconds=0.35, title=title_msg, message=sub_msg)
            self.new_empty_timetable.emit(self._selected_slug, mode, sch_name, pool_id, pool_name)
        
    def _on_cross_import_clicked(self):
        # Hedef kurum seçili değilse, kullanıcıyı boş bir uyarıyla geri çevirmek
        # yerine makul olanı seç: tek kurum varsa o, yoksa son açılan kurum.
        target = self._selected_slug
        if not target:
            try:
                insts = version_store.list_institutions() or []
            except Exception:
                insts = []
            if len(insts) == 1:
                target = insts[0].get("slug")
            else:
                target = version_store.get_last_active_institution_slug()
        if not target:
            QMessageBox.warning(
                self, "Kurum Seçilmedi",
                "Verilerin aktarılacağı kurumu soldaki listeden seçin, "
                "sonra tekrar deneyin.")
            return
        self._selected_slug = target

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
                include_assignments=sel["assignments"],
                invert_timeoff=sel.get("invert_timeoff", True)
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
