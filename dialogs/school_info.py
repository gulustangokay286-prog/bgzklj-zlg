"""dialogs/school_info.py — Temel Okul Bilgileri ve Genel Ayarlar (Apple Studio Minimalist UI)"""
import os, re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, 
    QPushButton, QTabWidget, QWidget, QCheckBox, QRadioButton, QFrame, QButtonGroup,
    QMessageBox, QScrollArea, QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, QSize
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath, QIcon

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"


def make_school_vector_badge(name: str, size: int = 38) -> QPixmap:
    """Renders pure nude vector icons without enclosing background square/frame boxes."""
    scale = 2
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(scale, scale)
    
    if name == "institution":
        color = QColor("#0284C7")
        p.setPen(QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        
        # Triangular Pediment Roof
        roof = QPainterPath()
        roof.moveTo(size / 2.0, 5)
        roof.lineTo(size - 5, 13)
        roof.lineTo(5, 13)
        roof.closeSubpath()
        p.drawPath(roof)
        
        # Entablature Beam
        p.drawLine(QPointF(4, 15), QPointF(size - 4, 15))
        
        # 4 Classical Columns
        col_tops = [8, 14, size - 14, size - 8]
        for x in col_tops:
            p.drawLine(QPointF(x, 17), QPointF(x, size - 9))
            
        # Stepped Base (2 steps)
        p.drawLine(QPointF(4, size - 8), QPointF(size - 4, size - 8))
        p.drawLine(QPointF(2, size - 5), QPointF(size - 2, size - 5))
        
    elif name == "clock":
        color = QColor("#7C3AED")
        p.setPen(QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(4, 4, size - 8, size - 8))
        p.drawLine(QPointF(size / 2.0, size / 2.0), QPointF(size / 2.0, 9))
        p.drawLine(QPointF(size / 2.0, size / 2.0), QPointF(size / 2.0 + 6, size / 2.0 + 3))
        
    elif name == "globe":
        color = QColor("#059669")
        p.setPen(QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(4, 4, size - 8, size - 8))
        p.drawEllipse(QRectF(size / 2.0 - (size - 8) / 4.0, 4, (size - 8) / 2.0, size - 8))
        p.drawLine(QPointF(4, size / 2.0), QPointF(size - 4, size / 2.0))
        
    elif name == "document":
        color = QColor("#D97706")
        p.setPen(QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(6, 4, size - 12, size - 8), 3, 3)
        p.drawLine(QPointF(11, 11), QPointF(size - 11, 11))
        p.drawLine(QPointF(11, 17), QPointF(size - 11, 17))
        p.drawLine(QPointF(11, 23), QPointF(size - 15, 23))
        
    p.end()
    pix.setDevicePixelRatio(scale)
    return pix


def make_school_vector_icon(name: str, size: int = 16, color_hex: str = "#0071E3") -> QIcon:
    scale = 2
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(scale, scale)
    color = QColor(color_hex)
    
    if name == "clock":
        p.setPen(QPen(color, 1.4, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(2, 2, size - 4, size - 4))
        p.drawLine(QPointF(size / 2.0, size / 2.0), QPointF(size / 2.0, 5))
        p.drawLine(QPointF(size / 2.0, size / 2.0), QPointF(size / 2.0 + 3.5, size / 2.0 + 2))
        
    elif name == "calendar":
        p.setPen(QPen(color, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(2.5, 3.5, size - 5, size - 6), 2, 2)
        p.drawLine(QPointF(2.5, 7.5), QPointF(size - 2.5, 7.5))
        p.drawLine(QPointF(5.5, 2), QPointF(5.5, 4.5))
        p.drawLine(QPointF(size - 5.5, 2), QPointF(size - 5.5, 4.5))
        
    elif name == "key":
        p.setPen(QPen(color, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(1.5, 3.5, 6, 6))
        p.drawLine(QPointF(7.5, 6.5), QPointF(size - 1.5, 6.5))
        p.drawLine(QPointF(size - 4, 6.5), QPointF(size - 4, 9.5))
        p.drawLine(QPointF(size - 1.5, 6.5), QPointF(size - 1.5, 9))
        
    elif name == "cloud_check":
        p.setPen(QPen(color, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(4, size - 5)
        path.quadTo(2, size - 5, 2, size - 8)
        path.quadTo(2, size - 11, 5, size - 11)
        path.quadTo(6, 3, 11, 4)
        path.quadTo(size - 2, 4, size - 3, size - 8)
        path.quadTo(size - 2, size - 5, size - 5, size - 5)
        path.closeSubpath()
        p.drawPath(path)
        
    p.end()
    pix.setDevicePixelRatio(scale)
    return QIcon(pix)


class SchoolInfoDialog(QDialog):
    def __init__(self, parent=None, data_store=None):
        super().__init__(parent)
        self.data_store = data_store if data_store is not None else {}
        self.setWindowTitle("Temel Okul Bilgileri ve Genel Ayarlar")
        self.resize(800, 580)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #F8FAFC;
                font-family: {FONT_FAMILY};
                font-size: 13px;
                color: #0F172A;
            }}
            QTabWidget::pane {{
                border: 1px solid #E2E8F0;
                background: #FFFFFF;
                border-radius: 12px;
                top: -1px;
            }}
            QTabBar::tab {{
                background: #F1F5F9;
                color: #64748B;
                border: 1px solid #E2E8F0;
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                padding: 8px 22px;
                margin-right: 4px;
                font-weight: 600;
                font-size: 12px;
            }}
            QTabBar::tab:hover {{
                background: #E2E8F0;
                color: #0F172A;
            }}
            QTabBar::tab:selected {{
                background: #FFFFFF;
                color: #0071E3;
                border-color: #E2E8F0;
                border-bottom: 2px solid #FFFFFF;
                font-weight: 700;
            }}
            QFrame.card_frame {{
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }}
            QLineEdit, QComboBox {{
                border: 1px solid #CBD5E1;
                padding: 6px 10px;
                background: #FFFFFF;
                border-radius: 7px;
                font-size: 12.5px;
                color: #0F172A;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: #0071E3;
            }}
            QRadioButton, QCheckBox {{
                font-size: 12.5px;
                color: #334155;
                font-weight: 500;
                spacing: 8px;
            }}
            QRadioButton::indicator, QCheckBox::indicator {{
                width: 16px;
                height: 16px;
            }}
        """)
        self._build_ui()
        self.cb_gun_sayisi.currentIndexChanged.connect(self._on_gun_sayisi_changed)
        self.cb_hafta_sonu.currentIndexChanged.connect(self._on_hafta_sonu_changed)
        self._load_data()
        
    def _on_gun_sayisi_changed(self):
        try:
            cnt = int(self.cb_gun_sayisi.currentText())
        except Exception:
            cnt = 5
        self.cb_hafta_sonu.blockSignals(True)
        if cnt >= 7:
            self.cb_hafta_sonu.setCurrentText("Hafta Sonu Tatili Yok")
        elif cnt == 6:
            self.cb_hafta_sonu.setCurrentText("Yalnız Pazar")
        elif cnt == 5:
            self.cb_hafta_sonu.setCurrentText("Cumartesi - Pazar")
        self.cb_hafta_sonu.blockSignals(False)

    def _on_hafta_sonu_changed(self):
        w = self.cb_hafta_sonu.currentText().strip()
        self.cb_gun_sayisi.blockSignals(True)
        if w == "Hafta Sonu Tatili Yok":
            self.cb_gun_sayisi.setCurrentText("7")
        elif w == "Yalnız Pazar":
            self.cb_gun_sayisi.setCurrentText("6")
        elif w in ("Cumartesi - Pazar", "Pazar - Pazartesi", "Cuma - Cumartesi"):
            self.cb_gun_sayisi.setCurrentText("5")
        self.cb_gun_sayisi.blockSignals(False)
        
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(12)
        
        # Clean Unboxed Header Area (No Icon, No Box)
        header_lay = QVBoxLayout()
        header_lay.setContentsMargins(2, 0, 2, 2)
        header_lay.setSpacing(3)

        title_lbl = QLabel("Temel Okul Bilgileri ve Planlama Parametreleri")
        title_lbl.setFont(QFont(FONT_FAMILY, 14, QFont.Bold))
        title_lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        header_lay.addWidget(title_lbl)

        sub_lbl = QLabel("Ders çizelgesi zaman yapısı, kurum kimliği ve bulut senkronizasyon ayarları.")
        sub_lbl.setFont(QFont(FONT_FAMILY, 9.5))
        sub_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
        header_lay.addWidget(sub_lbl)

        main_layout.addLayout(header_lay)
        
        self.tabs = QTabWidget()
        self.tab_genel = QWidget()
        self.tab_ulke = QWidget()
        self.tab_program = QWidget()
        
        self.tabs.addTab(self.tab_genel, "Genel Bilgiler ve Zaman")
        self.tabs.addTab(self.tab_ulke, "Ülke ve Yerelleştirme")
        self.tabs.addTab(self.tab_program, "Program ve Dönem Türü")
        
        self._build_genel_tab()
        self._build_ulke_tab()
        self._build_program_tab()
        
        main_layout.addWidget(self.tabs, 1)
        
        # Centered License Status Strip (Nude Minimalist)
        status_bar_layout = QHBoxLayout()
        status_bar_layout.setContentsMargins(0, 4, 0, 4)
        status_bar_layout.setSpacing(6)
        status_bar_layout.addStretch()
        
        key_icon = QLabel()
        key_icon.setPixmap(make_school_vector_icon("key", 14, "#16A34A").pixmap(14, 14))
        key_icon.setStyleSheet("background: transparent; border: none;")
        status_bar_layout.addWidget(key_icon)
        
        self.lbl_status = QLabel("Lisans Türü: Sınırsız")
        self.lbl_status.setFont(QFont(FONT_FAMILY, 9.5, QFont.Bold))
        self.lbl_status.setStyleSheet("color: #166534; background: transparent; border: none;")
        status_bar_layout.addWidget(self.lbl_status)
        
        status_bar_layout.addStretch()
        main_layout.addLayout(status_bar_layout)
        
        # Bottom Buttons (Silindirik / Pill)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Vazgeç")
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 17px;
                font-size: 12px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover { background: #F8FAFC; color: #0F172A; }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QPushButton(" Kaydet ve Uygula")
        self.btn_ok.setIcon(make_school_vector_icon("cloud_check", 14, "#FFFFFF"))
        self.btn_ok.setFixedHeight(34)
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.setStyleSheet("""
            QPushButton {
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 17px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 24px;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        self.btn_ok.clicked.connect(self._on_save)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        main_layout.addLayout(btn_layout)

    def _build_genel_tab(self):
        layout = QVBoxLayout(self.tab_genel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        
        # Card 1: Kurum Kimlik Bilgileri
        card1 = QFrame()
        card1.setProperty("class", "card_frame")
        card1_layout = QHBoxLayout(card1)
        card1_layout.setContentsMargins(14, 14, 14, 14)
        card1_layout.setSpacing(14)
        
        icon1 = QLabel()
        icon1.setPixmap(make_school_vector_badge("institution", 38))
        icon1.setStyleSheet("background: transparent; border: none;")
        card1_layout.addWidget(icon1, 0, Qt.AlignTop)
        
        grid1 = QGridLayout()
        grid1.setSpacing(10)
        
        lbl_name = QLabel("Okul / Kurum Adı:")
        lbl_name.setStyleSheet("font-weight: 600; color: #334155;")
        grid1.addWidget(lbl_name, 0, 0)
        self.txt_okul_adi = QLineEdit()
        self.txt_okul_adi.setPlaceholderText("Örn: Çeken Akademi / Anadolu Lisesi")
        grid1.addWidget(self.txt_okul_adi, 0, 1, 1, 2)
        
        lbl_year = QLabel("Akademik Eğitim Yılı:")
        lbl_year.setStyleSheet("font-weight: 600; color: #334155;")
        grid1.addWidget(lbl_year, 1, 0)
        self.cb_egitim_yili = QComboBox()
        self.cb_egitim_yili.addItems(["2025-2026", "2026-2027", "2024-2025", "2027-2028"])
        grid1.addWidget(self.cb_egitim_yili, 1, 1, 1, 2)
        
        lbl_reg = QLabel("Mevzuat / Tebliğ:")
        lbl_reg.setStyleSheet("font-weight: 600; color: #334155;")
        grid1.addWidget(lbl_reg, 2, 0)
        self.cb_mevzuat = QComboBox()
        self.cb_mevzuat.addItems(["MEB Standart Haftalık Çizelgesi", "Özel Öğretim Kurumları Yönetmeliği", "YÖK / Üniversite Standart"])
        grid1.addWidget(self.cb_mevzuat, 2, 1)
        self.txt_teblig = QLineEdit()
        self.txt_teblig.setPlaceholderText("Örn: 2025/14 Tebliğler Dergisi")
        grid1.addWidget(self.txt_teblig, 2, 2)
        
        lbl_princ = QLabel("Kurum Yetkilisi / Unvan:")
        lbl_princ.setStyleSheet("font-weight: 600; color: #334155;")
        grid1.addWidget(lbl_princ, 3, 0)
        self.txt_yetkili_ad = QLineEdit()
        self.txt_yetkili_ad.setPlaceholderText("Örn: Ad Soyad")
        self.txt_yetkili_unvan = QLineEdit()
        self.txt_yetkili_unvan.setPlaceholderText("Örn: Okul Müdürü")
        grid1.addWidget(self.txt_yetkili_ad, 3, 1)
        grid1.addWidget(self.txt_yetkili_unvan, 3, 2)
        
        card1_layout.addLayout(grid1, 1)
        layout.addWidget(card1)
        
        # Card 2: Zaman ve Çizelge Parametreleri
        card2 = QFrame()
        card2.setProperty("class", "card_frame")
        card2_layout = QHBoxLayout(card2)
        card2_layout.setContentsMargins(14, 14, 14, 14)
        card2_layout.setSpacing(14)
        
        icon2 = QLabel()
        icon2.setPixmap(make_school_vector_badge("clock", 38))
        icon2.setStyleSheet("background: transparent; border: none;")
        card2_layout.addWidget(icon2, 0, Qt.AlignTop)
        
        grid2 = QGridLayout()
        grid2.setSpacing(8)
        
        lbl_period = QLabel("Günlük Ders Saati:")
        lbl_period.setStyleSheet("font-weight: 600; color: #334155;")
        grid2.addWidget(lbl_period, 0, 0)
        self.cb_ders_saati = QComboBox()
        self.cb_ders_saati.addItems([str(i) for i in range(1, 17)])
        self.cb_ders_saati.setCurrentText("8")
        self.cb_ders_saati.setFixedWidth(80)
        grid2.addWidget(self.cb_ders_saati, 0, 1)
        
        btn_zil = QPushButton("  Zil ve Teneffüs Saatleri...")
        btn_zil.setIcon(make_school_vector_icon("clock", 13, "#0071E3"))
        btn_zil.setFixedHeight(28)
        btn_zil.setCursor(Qt.PointingHandCursor)
        btn_zil.setStyleSheet("""
            QPushButton {
                background: #EFF6FF;
                border: 1px solid #BFDBFE;
                color: #0071E3;
                border-radius: 14px;
                font-weight: 600;
                font-size: 11.5px;
                padding: 0 14px;
            }
            QPushButton:hover { background: #DBEAFE; }
        """)
        btn_zil.clicked.connect(self._open_zil_dialog)
        grid2.addWidget(btn_zil, 0, 2)
        
        lbl_days = QLabel("Haftalık Çalışma Gün Sayısı:")
        lbl_days.setStyleSheet("font-weight: 600; color: #334155;")
        grid2.addWidget(lbl_days, 1, 0)
        self.cb_gun_sayisi = QComboBox()
        self.cb_gun_sayisi.addItems([str(i) for i in range(1, 8)])
        self.cb_gun_sayisi.setCurrentText("5")
        self.cb_gun_sayisi.setFixedWidth(80)
        grid2.addWidget(self.cb_gun_sayisi, 1, 1)
        
        btn_gunler = QPushButton("  Günler ve Tatil Seçimi...")
        btn_gunler.setIcon(make_school_vector_icon("calendar", 13, "#0071E3"))
        btn_gunler.setFixedHeight(28)
        btn_gunler.setCursor(Qt.PointingHandCursor)
        btn_gunler.setStyleSheet("""
            QPushButton {
                background: #EFF6FF;
                border: 1px solid #BFDBFE;
                color: #0071E3;
                border-radius: 14px;
                font-weight: 600;
                font-size: 11.5px;
                padding: 0 14px;
            }
            QPushButton:hover { background: #DBEAFE; }
        """)
        btn_gunler.clicked.connect(self._open_gunler_dialog)
        grid2.addWidget(btn_gunler, 1, 2)
        
        lbl_weekend = QLabel("Hafta Sonu Tatili:")
        lbl_weekend.setStyleSheet("font-weight: 600; color: #334155;")
        grid2.addWidget(lbl_weekend, 2, 0)
        self.cb_hafta_sonu = QComboBox()
        self.cb_hafta_sonu.addItems(["Cumartesi - Pazar", "Yalnız Pazar", "Hafta Sonu Tatili Yok", "Pazar - Pazartesi", "Cuma - Cumartesi"])
        grid2.addWidget(self.cb_hafta_sonu, 2, 1, 1, 2)
        
        card2_layout.addLayout(grid2, 1)
        layout.addWidget(card2)
        
        # Card 3: Kurum Tipi
        card3 = QFrame()
        card3.setProperty("class", "card_frame")
        card3_layout = QVBoxLayout(card3)
        card3_layout.setContentsMargins(14, 12, 14, 12)
        card3_layout.setSpacing(8)
        
        self.radio_okul = QRadioButton("Okul / Kolej / Kurs / Özel Öğretim")
        self.radio_fakulte = QRadioButton("Fakülte / Yüksek Okul / Üniversite")
        self.radio_okul.setChecked(True)
        
        btn_grp = QButtonGroup(self)
        btn_grp.addButton(self.radio_okul)
        btn_grp.addButton(self.radio_fakulte)
        
        card3_layout.addWidget(self.radio_okul)
        card3_layout.addWidget(self.radio_fakulte)
        
        self.chk_cok_donem = QCheckBox("Çok Dönemli veya Çok Haftalı Program (Güz / Bahar)")
        self.chk_cok_donem.setStyleSheet("font-weight: 600; color: #1E293B;")
        card3_layout.addWidget(self.chk_cok_donem)
        card3_layout.addStretch()
        
        layout.addWidget(card3)
        layout.addStretch()

    def _build_ulke_tab(self):
        layout = QVBoxLayout(self.tab_ulke)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        
        card = QFrame()
        card.setProperty("class", "card_frame")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(16)
        
        icon = QLabel()
        icon.setPixmap(make_school_vector_badge("globe", 38))
        icon.setStyleSheet("background: transparent; border: none;")
        card_layout.addWidget(icon, 0, Qt.AlignTop)
        
        grid = QGridLayout()
        grid.setSpacing(12)
        
        lbl_country = QLabel("Ülke Seçimi:")
        lbl_country.setStyleSheet("font-weight: 600; color: #334155;")
        grid.addWidget(lbl_country, 0, 0)
        self.cb_ulke = QComboBox()
        self.cb_ulke.addItems(["Türkiye (TR)", "Kuzey Kıbrıs Türk Cumhuriyeti (KKTC)", "Almanya (DE)", "İngiltere (UK)", "Azerbaycan (AZ)"])
        grid.addWidget(self.cb_ulke, 0, 1)
        
        lbl_lang = QLabel("Arayüz Dili:")
        lbl_lang.setStyleSheet("font-weight: 600; color: #334155;")
        grid.addWidget(lbl_lang, 1, 0)
        self.cb_dil = QComboBox()
        self.cb_dil.addItems(["Türkçe (Varsayılan)", "English", "Deutsch"])
        grid.addWidget(self.cb_dil, 1, 1)
        
        lbl_tz = QLabel("Saat Dilimi / Zaman:")
        lbl_tz.setStyleSheet("font-weight: 600; color: #334155;")
        grid.addWidget(lbl_tz, 2, 0)
        self.cb_saat_dilimi = QComboBox()
        self.cb_saat_dilimi.addItems(["GMT+3 (İstanbul, Ankara)", "GMT+2 (Berlin, Paris)", "GMT+0 (Londra)", "GMT+4 (Bakü)"])
        grid.addWidget(self.cb_saat_dilimi, 2, 1)
        
        card_layout.addLayout(grid, 1)
        layout.addWidget(card)
        layout.addStretch()

    def _build_program_tab(self):
        layout = QVBoxLayout(self.tab_program)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        
        card = QFrame()
        card.setProperty("class", "card_frame")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(16)
        
        icon = QLabel()
        icon.setPixmap(make_school_vector_badge("document", 38))
        icon.setStyleSheet("background: transparent; border: none;")
        card_layout.addWidget(icon, 0, Qt.AlignTop)
        
        vbox = QVBoxLayout()
        vbox.setSpacing(10)
        
        lbl_info = QLabel("<b>Çizelge Programlama Modeli</b><br>Kurumunuz için geçerli olan haftalık ders dağılım sistemini belirleyin.")
        lbl_info.setStyleSheet("color: #334155; font-size: 13px;")
        vbox.addWidget(lbl_info)
        
        self.radio_prog_standart = QRadioButton("Standart Tek Haftalık Çizelge (Haftalık Ders Dağılımı - Önerilen)")
        self.radio_prog_ab = QRadioButton("2 Haftalık Dönüşümlü Çizelge (A Haftası / B Haftası Çift Sistem)")
        self.radio_prog_donem = QRadioButton("Dönemlik Modüler Çizelge (Güz Dönemi / Bahar Dönemi Ayrımı)")
        self.radio_prog_standart.setChecked(True)
        
        prog_grp = QButtonGroup(self)
        prog_grp.addButton(self.radio_prog_standart)
        prog_grp.addButton(self.radio_prog_ab)
        prog_grp.addButton(self.radio_prog_donem)
        
        vbox.addWidget(self.radio_prog_standart)
        vbox.addWidget(self.radio_prog_ab)
        vbox.addWidget(self.radio_prog_donem)
        
        card_layout.addLayout(vbox, 1)
        layout.addWidget(card)
        layout.addStretch()
        
    def _open_zil_dialog(self):
        try:
            cnt = int(self.cb_ders_saati.currentText())
        except Exception:
            cnt = 8
        from dialogs.bell_times_dialog import BellAndBreakTimesDialog
        dlg = BellAndBreakTimesDialog(data_store=self.data_store, periods=cnt, parent=self)
        dlg.exec()
        
    def _open_gunler_dialog(self):
        try:
            cnt = int(self.cb_gun_sayisi.currentText())
        except Exception:
            cnt = 5
        from dialogs.days_dialog import DaysAndHolidaysDialog
        dlg = DaysAndHolidaysDialog(data_store=self.data_store, days_count=cnt, parent=self)
        if dlg.exec():
            # Update days count combo if modified in days dialog
            settings = self.data_store.get("settings", {})
            d_list = settings.get("active_days_list", [])
            if d_list:
                active_c = len([d for d in d_list if d.get("active", True)])
                if 1 <= active_c <= 7:
                    self.cb_gun_sayisi.blockSignals(True)
                    self.cb_gun_sayisi.setCurrentText(str(active_c))
                    self.cb_gun_sayisi.blockSignals(False)

    def _load_data(self):
        settings = self.data_store.get("settings", {})
        
        name = self.data_store.get("okul_adi") or settings.get("school_name", "")
        if name:
            self.txt_okul_adi.setText(name)
        elif self.data_store.get("school_name"):
            self.txt_okul_adi.setText(self.data_store["school_name"])
            
        y = settings.get("academic_year", "2025-2026")
        idx = self.cb_egitim_yili.findText(y)
        if idx >= 0: self.cb_egitim_yili.setCurrentIndex(idx)
        
        ds = str(self.data_store.get("ders_saati") or settings.get("periods_per_day", 8))
        idx_ds = self.cb_ders_saati.findText(ds)
        if idx_ds >= 0: self.cb_ders_saati.setCurrentIndex(idx_ds)
        
        gs = str(self.data_store.get("gun_sayisi") or settings.get("days_count", 5))
        idx_gs = self.cb_gun_sayisi.findText(gs)
        if idx_gs >= 0: self.cb_gun_sayisi.setCurrentIndex(idx_gs)
        
        hs = settings.get("weekend_option", "Cumartesi - Pazar")
        idx_hs = self.cb_hafta_sonu.findText(hs)
        if idx_hs >= 0: self.cb_hafta_sonu.setCurrentIndex(idx_hs)
        
        m = settings.get("mevzuat_tipi", "")
        if m:
            idx_m = self.cb_mevzuat.findText(m)
            if idx_m >= 0: self.cb_mevzuat.setCurrentIndex(idx_m)
            
        t = settings.get("teblig_bilgisi", "")
        if t: self.txt_teblig.setText(t)
        
        ya = settings.get("yetkili_ad", "")
        if ya: self.txt_yetkili_ad.setText(ya)
        
        yu = settings.get("yetkili_unvan", "")
        if yu: self.txt_yetkili_unvan.setText(yu)
        
        kt = settings.get("kurum_tipi", "okul")
        if kt == "fakulte":
            self.radio_fakulte.setChecked(True)
        else:
            self.radio_okul.setChecked(True)
            
        self.chk_cok_donem.setChecked(settings.get("multi_term", False))
        
        pm = settings.get("program_modeli", "standart")
        if pm == "ab_haftalik":
            self.radio_prog_ab.setChecked(True)
        elif pm == "donemlik":
            self.radio_prog_donem.setChecked(True)
        else:
            self.radio_prog_standart.setChecked(True)

    def _on_save(self):
        name = self.txt_okul_adi.text().strip()
        if not name:
            QMessageBox.warning(self, "Uyarı", "Lütfen okul veya kurum adını boş bırakmayınız.")
            return
            
        try:
            p_count = int(self.cb_ders_saati.currentText())
        except Exception:
            p_count = 8
            
        try:
            d_count = int(self.cb_gun_sayisi.currentText())
        except Exception:
            d_count = 5
            
        self.data_store["okul_adi"] = name
        self.data_store["ders_saati"] = p_count
        self.data_store["gun_sayisi"] = d_count
        
        settings = self.data_store.setdefault("settings", {})
        settings["school_name"] = name
        settings["academic_year"] = self.cb_egitim_yili.currentText()
        settings["periods"] = p_count
        settings["periods_per_day"] = p_count
        settings["days_count"] = d_count
        settings["day_count"] = d_count
        settings["weekend_option"] = self.cb_hafta_sonu.currentText()
        settings["mevzuat_tipi"] = self.cb_mevzuat.currentText()
        settings["teblig_bilgisi"] = self.txt_teblig.text().strip()
        settings["yetkili_ad"] = self.txt_yetkili_ad.text().strip()
        settings["yetkili_unvan"] = self.txt_yetkili_unvan.text().strip()
        settings["kurum_tipi"] = "fakulte" if self.radio_fakulte.isChecked() else "okul"
        settings["multi_term"] = self.chk_cok_donem.isChecked()
        
        from timetable_grid import DAYS
        # Sync active_days_list and days
        active_list = settings.get("active_days_list", [])
        if active_list and len(active_list) == 7 and sum(1 for d in active_list if d.get("active", True)) == d_count:
            days_names = [d["name"] for d in active_list if d.get("active", True)]
        else:
            days_names = DAYS[:d_count]
            settings["active_days_list"] = [{"day_index": i, "name": d, "active": (i < d_count)} for i, d in enumerate(DAYS)]
        settings["days"] = days_names
        
        if self.radio_prog_ab.isChecked():
            settings["program_modeli"] = "ab_haftalik"
        elif self.radio_prog_donem.isChecked():
            settings["program_modeli"] = "donemlik"
        else:
            settings["program_modeli"] = "standart"
            
        # Direct and Reliable Real-Time Persistence (SQLite + JSON Version + VDS Cloud + UI Grid)
        win = self.window()
        main_win = None
        curr = self
        while curr:
            if hasattr(curr, "save_db") and hasattr(curr, "_refresh_grid"):
                main_win = curr
                break
            curr = curr.parent() if hasattr(curr, "parent") else None
            
        if main_win:
            main_win.save_db(sync_from_grid=False)
            main_win._refresh_grid()
            main_win._refresh_tree()
        else:
            from database import sync_data_store_to_vds
            sync_data_store_to_vds(self.data_store)
            
        self.accept()
