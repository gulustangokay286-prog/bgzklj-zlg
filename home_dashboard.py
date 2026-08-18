"""
home_dashboard.py — Apple Human Interface Guidelines (Apple HIG) Minimalist Tasarımlı Kurum & Versiyon Paneli
Sade, modern, ferah, nötr renk paleti, 3D kurum ikonları ve kristal netliğinde tipografi.
Tek bir emoji barındırmaz, tamamı modern vektörel arayüz öğeleridir.
"""
import os, sys, json
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSplitter, QInputDialog, QMessageBox,
    QLineEdit, QDialog, QCheckBox, QGraphicsDropShadowEffect, QGraphicsBlurEffect,
    QStackedLayout, QMenu
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

def make_3d_institution_icon(inst_name: str, color_hex: str = "#0071E3", size: int = 44) -> QPixmap:
    """Draws a premium 3D isometric academy / campus building icon with depth, gradients and soft bevels."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    
    # 1. Base 3D Tile with gradient and bottom shadow
    grad_bg = QLinearGradient(0, 0, size, size)
    c_base = QColor(color_hex)
    grad_bg.setColorAt(0.0, c_base.lighter(135))
    grad_bg.setColorAt(0.7, c_base)
    grad_bg.setColorAt(1.0, c_base.darker(120))
    
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(grad_bg))
    p.drawRoundedRect(QRectF(2, 2, size - 4, size - 4), 11, 11)
    
    # Top highlight bevel (glass edge)
    p.setPen(QPen(QColor(255, 255, 255, 110), 1.2))
    p.drawRoundedRect(QRectF(3, 3, size - 6, size - 6), 10, 10)
    
    # 2. Isometric Pediment & Roof
    mid_x = size / 2.0
    
    # Roof Gable
    roof_path = QPainterPath()
    roof_path.moveTo(mid_x, 10.5)
    roof_path.lineTo(size - 10, 16.5)
    roof_path.lineTo(10, 16.5)
    roof_path.closeSubpath()
    
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 250))
    p.drawPath(roof_path)
    
    # Architrave / Cornice
    p.setBrush(QColor(255, 255, 255, 210))
    p.drawRoundedRect(QRectF(9, 17, size - 18, 2.5), 1, 1)
    
    # 3. Classical 3D Columns (3 Pillars)
    col_w = 3.2
    col_h = 10.5
    col_y = 20.0
    
    # Left pillar
    p.setBrush(QColor(255, 255, 255, 240))
    p.drawRoundedRect(QRectF(11.5, col_y, col_w, col_h), 1, 1)
    # Center pillar
    p.drawRoundedRect(QRectF(mid_x - col_w / 2.0, col_y, col_w, col_h), 1, 1)
    # Right pillar
    p.drawRoundedRect(QRectF(size - 11.5 - col_w, col_y, col_w, col_h), 1, 1)
    
    # 4. Base Steps / Foundation
    p.setBrush(QColor(255, 255, 255, 220))
    p.drawRoundedRect(QRectF(9.5, 31, size - 19, 2.2), 1, 1)
    p.setBrush(QColor(255, 255, 255, 250))
    p.drawRoundedRect(QRectF(8, 33.5, size - 16, 2.5), 1, 1)
    
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
        self.setFixedSize(400, 220)
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
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)
        
        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setPixmap(make_dashboard_icon("check" if is_success else "info", color_hex="#10B981" if is_success else "#0071E3", size=40))
        layout.addWidget(icon_lbl)
        
        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        t_lbl.setStyleSheet("color: #0F172A; font-weight: bold;")
        t_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(t_lbl)
        
        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont("Segoe UI", 9.5))
        msg_lbl.setStyleSheet("color: #475569;")
        msg_lbl.setAlignment(Qt.AlignCenter)
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)
        
        btn_ok = QPushButton("Tamam")
        btn_ok.setFixedSize(130, 34)
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #0056B3;
            }
        """)
        btn_ok.clicked.connect(self.accept)
        
        h_lay = QHBoxLayout()
        h_lay.addStretch(1)
        h_lay.addWidget(btn_ok)
        h_lay.addStretch(1)
        layout.addLayout(h_lay)

def show_apple_info(parent, title: str, message: str, is_success: bool = True):
    dlg = AppleInfoDialog(title, message, is_success=is_success, parent=parent)
    dlg.exec()


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


# ── Apple Institution List Item ──────────────────────────────────────

class AppleInstitutionCard(QFrame):
    clicked = Signal(str)  # slug
    
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
        self.setFixedHeight(68)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self._update_style()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # 3D Institution Icon
        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_3d_institution_icon(self.inst_name, self.inst_color, 44))
        icon_lbl.setFixedSize(44, 44)
        layout.addWidget(icon_lbl)
        
        # Text Info
        t_layout = QVBoxLayout()
        t_layout.setSpacing(2)
        t_layout.setContentsMargins(0, 2, 0, 2)
        
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        
        name_lbl = QLabel(self.inst_name)
        name_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        name_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; border: none;")
        name_lbl.setMaximumWidth(160)
        name_lbl.setToolTip(self.inst_name)
        name_row.addWidget(name_lbl)
        
        if self.has_password:
            lock_badge = QLabel("Korumalı")
            lock_badge.setFont(QFont("Segoe UI", 7, QFont.Bold))
            lock_badge.setStyleSheet(f"background: #FEE2E2; color: {APPLE_RED}; padding: 1px 5px; border-radius: 4px; border: none;")
            name_row.addWidget(lock_badge)
            
        name_row.addStretch(1)
        t_layout.addLayout(name_row)
        
        v_count = inst_data.get("version_count", 0)
        sub_lbl = QLabel(f"{v_count} versiyon")
        sub_lbl.setFont(QFont("Segoe UI", 8))
        sub_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")
        t_layout.addWidget(sub_lbl)
        
        layout.addLayout(t_layout, 1)
        
        # Selection Indicator
        if self._selected:
            dot = QLabel("●")
            dot.setFont(QFont("Segoe UI", 10))
            dot.setStyleSheet(f"color: {APPLE_BLUE}; background: transparent; border: none;")
            layout.addWidget(dot)
    
    def _update_style(self):
        if self._selected:
            self.setStyleSheet(f"""
                AppleInstitutionCard {{
                    background: #EBF5FF;
                    border: 1.5px solid {APPLE_BLUE};
                    border-radius: 12px;
                }}
                AppleInstitutionCard:hover {{ background: #E1F0FF; }}
            """)
        else:
            self.setStyleSheet(f"""
                AppleInstitutionCard {{
                    background: #FFFFFF;
                    border: 1px solid {BORDER_HAIRLINE};
                    border-radius: 12px;
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
            
        menu.addSeparator()
        act_delete = menu.addAction("Kurumu Sil")
        
        action = menu.exec_(self.mapToGlobal(pos))
        if action == act_rename:
            new_name, ok = QInputDialog.getText(self, "Kurum Adı", "Yeni kurum adı:", text=self.inst_name)
            if ok and new_name.strip():
                version_store.rename_institution(self.slug, new_name.strip())
                self._notify_parent_refresh()
        elif action == act_color:
            new_color, ok = QInputDialog.getItem(
                self, "Renk Seç", "Kurum rengi:",
                version_store.INSTITUTION_COLORS, 0, False
            )
            if ok and new_color:
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
            ret = QMessageBox.warning(
                self, "Kurumu Sil",
                f"'{self.inst_name}' kurumunu ve tüm versiyonlarını silmek istediğinize emin misiniz?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if ret == QMessageBox.Yes:
                version_store.delete_institution(self.slug)
                self._notify_parent_refresh()
                
    def _notify_parent_refresh(self):
        p = self.parent()
        while p:
            if hasattr(p, "_refresh_institutions"):
                p._refresh_institutions()
                if p._selected_slug == self.slug:
                    p._unlocked_slugs.discard(self.slug)
                    p._refresh_versions()
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
            badge.setStyleSheet(f"background: {color_hex}15; color: {color_hex}; padding: 2px 7px; border-radius: 5px;")
            hdr_lay.addWidget(badge)
            
        hdr_lay.addStretch(1)
        
        # Chevron icon
        self.chevron_lbl = QLabel()
        self.chevron_lbl.setPixmap(make_dashboard_icon("chevron_right" if is_collapsed else "chevron_down", "#64748B", 14))
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
        
    def _update_style(self):
        if self._is_active:
            self.setStyleSheet(f"""
                AppleVersionRow {{
                    background: #FAFDFA; border: 1px solid #B7E4C7; border-radius: 8px;
                }}
                AppleVersionRow:hover {{ background: #F0FBF4; }}
            """)
        elif self._is_selected:
            self.setStyleSheet(f"""
                AppleVersionRow {{
                    background: #EBF5FF; border: 1px solid #B8DCFF; border-radius: 8px;
                }}
                AppleVersionRow:hover {{ background: #E1F0FF; }}
            """)
        else:
            self.setStyleSheet(f"""
                AppleVersionRow {{
                    background: #FFFFFF; border: 1px solid {BORDER_HAIRLINE}; border-radius: 8px;
                }}
                AppleVersionRow:hover {{ background: #F8FAFC; border: 1px solid #CBD5E1; }}
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
        self.is_master_admin = bool(user_email or self.auth_data.get("uid"))
        self.display_name = get_user_display_name(user_email, self)
        
        version_store.migrate_existing_data()
        self._build_ui()
        self._refresh_institutions()
        
        # Cross-PC Realtime Database Sync on startup
        if self.auth_data and not self.auth_data.get("is_offline"):
            self._start_initial_cloud_sync()
            
    def _start_initial_cloud_sync(self):
        import threading
        from cloud_sync import pull_all_from_rtdb
        from PySide6.QtCore import QTimer
        
        def _worker():
            try:
                ok, _, _ = pull_all_from_rtdb(self.auth_data)
                if ok:
                    QTimer.singleShot(0, self._on_cloud_synced)
            except Exception as e:
                print(f"[HomeDashboard] Cloud pull note: {e}")
                
        threading.Thread(target=_worker, daemon=True).start()
        
    def _on_cloud_synced(self):
        self._refresh_institutions()
        if self._selected_slug:
            self._refresh_versions()
        
    def _build_ui(self):
        self.setStyleSheet(f"""
            HomeDashboard {{ background: {BG_CANVAS}; font-family: {FONT_FAMILY}; }}
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
        
        brand_lbl = QLabel("Chenki  <span style='color: #86868B; font-weight: normal;'>Planlama Hub</span>")
        brand_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
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
            admin_badge.setStyleSheet(f"background: #FDF4FF; color: {APPLE_PURPLE}; padding: 2px 8px; border-radius: 5px; border: 1px solid #F0ABFC;")
            top_layout.addWidget(admin_badge)
            
        btn_cloud_sync = QPushButton("Bulut Eşitle")
        btn_cloud_sync.setFont(QFont("Segoe UI", 9, QFont.Bold))
        btn_cloud_sync.setCursor(Qt.PointingHandCursor)
        btn_cloud_sync.setStyleSheet(f"""
            QPushButton {{
                background: #E8E8ED; color: {APPLE_BLUE}; border: none;
                border-radius: 8px; padding: 6px 14px;
            }}
            QPushButton:hover {{ background: #D8D8DC; }}
        """)
        btn_cloud_sync.clicked.connect(self._manual_cloud_sync)
        top_layout.addWidget(btn_cloud_sync)
        
        btn_import = QPushButton("Veri Aktar")
        btn_import.setFont(QFont("Segoe UI", 9, QFont.Bold))
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.setStyleSheet(f"""
            QPushButton {{
                background: #E8E8ED; color: {TEXT_PRIMARY}; border: none;
                border-radius: 8px; padding: 6px 14px;
            }}
            QPushButton:hover {{ background: #D8D8DC; }}
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
        btn_logout.setStyleSheet(f"""
            QPushButton {{
                background: #FEE2E2; color: #DC2626; border: 1px solid #FECACA;
                border-radius: 6px; padding: 4px 12px;
            }}
            QPushButton:hover {{ background: #FCA5A5; color: #991B1B; }}
        """)
        btn_logout.clicked.connect(self._on_logout_clicked)
        top_layout.addWidget(btn_logout)
        
        root.addWidget(top_bar)
        
        # ── 2. Splitter Body ─────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{ background: {BORDER_HAIRLINE}; width: 1px; }}
        """)
        
        # Left Sidebar (Institutions)
        left_panel = QFrame()
        left_panel.setFixedWidth(280)
        left_panel.setStyleSheet(f"background: {BG_SIDEBAR}; border-right: 1px solid {BORDER_HAIRLINE};")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 16, 14, 16)
        left_layout.setSpacing(10)
        
        left_hdr = QHBoxLayout()
        left_title = QLabel("KURUMLAR")
        left_title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        left_title.setStyleSheet(f"color: {TEXT_MUTED}; letter-spacing: 0.5px;")
        left_hdr.addWidget(left_title)
        left_hdr.addStretch(1)
        left_layout.addLayout(left_hdr)
        
        scroll_inst = QScrollArea()
        scroll_inst.setWidgetResizable(True)
        scroll_inst.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.inst_list_widget = QWidget()
        self.inst_list_widget.setStyleSheet("background: transparent;")
        self.inst_list_layout = QVBoxLayout(self.inst_list_widget)
        self.inst_list_layout.setContentsMargins(0, 0, 0, 0)
        self.inst_list_layout.setSpacing(6)
        self.inst_list_layout.addStretch(1)
        
        scroll_inst.setWidget(self.inst_list_widget)
        left_layout.addWidget(scroll_inst, 1)
        splitter.addWidget(left_panel)
        
        # Right Main Panel (Versions)
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
        self.password_overlay_widget.setStyleSheet("background: #F8FAFC;")
        overlay_layout = QVBoxLayout(self.password_overlay_widget)
        overlay_layout.setAlignment(Qt.AlignCenter)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        
        # Modal Floating Card (Centered)
        self.pwd_card = QFrame()
        self.pwd_card.setFixedSize(400, 300)
        self.pwd_card.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 16px;
            }
        """)
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(30)
        card_shadow.setColor(QColor(0, 0, 0, 40))
        card_shadow.setOffset(0, 8)
        self.pwd_card.setGraphicsEffect(card_shadow)
        
        c_layout = QVBoxLayout(self.pwd_card)
        c_layout.setContentsMargins(28, 26, 28, 26)
        c_layout.setSpacing(12)
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
        
        splitter.addWidget(right_panel)
        splitter.setSizes([280, 820])
        root.addWidget(splitter, 1)

    def _on_logout_clicked(self):
        r = QMessageBox.question(self, "Çıkış Onayı", "Oturumunuzu kapatmak istediğinize emin misiniz?", QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
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
        self._search_query = text.strip().lower()
        self._refresh_institutions()
        
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
            card = AppleInstitutionCard(inst, is_selected=is_sel)
            card.clicked.connect(self._on_institution_selected)
            self.inst_list_layout.insertWidget(self.inst_list_layout.count() - 1, card)
            
        if not self._selected_slug and filtered:
            self._on_institution_selected(filtered[0]["slug"])
        elif self._selected_slug:
            self._refresh_versions()
            
    def _on_institution_selected(self, slug):
        self._selected_slug = slug
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
            badge.setStyleSheet(f"background: {color_hex}15; color: {color_hex}; padding: 2px 7px; border-radius: 5px;")
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
        
        while self.ver_list_layout.count() > 1:
            item = self.ver_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        versions = version_store.list_versions(self._selected_slug, source_filter="all")
        active_ver = version_store.get_active_version(self._selected_slug)
        
        self.ver_count_lbl.setText(f"•  {len(versions)} versiyon")
        
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
            
            self.ver_list_layout.insertWidget(0, empty_box)
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
                card, lay = self._create_version_group_card("Aktif ve Yayındaki Çizelge", "active", "Yayında", APPLE_GREEN)
                for v in active_list:
                    row = AppleVersionRow(self._selected_slug, v, is_active=True)
                    row.selected.connect(self._on_version_selected)
                    row.double_clicked.connect(self._on_version_double_clicked)
                    row.action_requested.connect(self._on_version_action)
                    lay.addWidget(row)
                self.ver_list_layout.insertWidget(self.ver_list_layout.count() - 1, card)
                
            # 2. Collapsible Older Versions Group with Chevron
            if older_list:
                hist_group = CollapsibleVersionGroup("Eski Sürümler & Geçmiş Kayıtlar", "history", f"{len(older_list)} Versiyon", APPLE_PURPLE, is_collapsed=False)
                for v in older_list:
                    row = AppleVersionRow(self._selected_slug, v, is_active=False)
                    row.selected.connect(self._on_version_selected)
                    row.double_clicked.connect(self._on_version_double_clicked)
                    row.action_requested.connect(self._on_version_action)
                    hist_group.content_lay.addWidget(row)
                self.ver_list_layout.insertWidget(self.ver_list_layout.count() - 1, hist_group)
                
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
            version_store.set_active_version(slug, filename)
            self._refresh_versions()
            self._refresh_institutions()
        elif action == "delete":
            ret = QMessageBox.warning(
                self, "Versiyonu Sil",
                f"'{filename}' versiyonunu silmek istediğinize emin misiniz?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if ret == QMessageBox.Yes:
                version_store.delete_version(slug, filename)
                self._refresh_versions()
                self._refresh_institutions()
                
    def _on_new_institution_clicked(self):
        name, ok = QInputDialog.getText(self, "Yeni Kurum", "Kurum adını girin:")
        if ok and name.strip():
            inst = version_store.create_institution(name.strip())
            self._selected_slug = inst["slug"]
            self._refresh_institutions()
            
    def _on_new_empty_clicked(self):
        if not self._selected_slug:
            return
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
                QMessageBox.information(self, "Aktarım Başarılı", msg)
                self._refresh_versions()
                self._refresh_institutions()
            else:
                QMessageBox.critical(self, "Hata", msg)

    def _manual_cloud_sync(self):
        from cloud_sync import push_all_to_rtdb, pull_all_from_rtdb
        push_ok, push_msg, _ = push_all_to_rtdb(self.auth_data)
        pull_ok, pull_msg, count = pull_all_from_rtdb(self.auth_data)
        self._refresh_institutions()
        if self._selected_slug:
            self._refresh_versions()
        if pull_ok:
            QMessageBox.information(self, "Bulut Senkronizasyonu", f"{pull_msg}\n{push_msg}\nTüm cihazlar başarıyla eşitlendi.")
        else:
            QMessageBox.warning(self, "Bulut Uyarısı", f"{pull_msg}\nLütfen internet bağlantınızı kontrol edin.")
