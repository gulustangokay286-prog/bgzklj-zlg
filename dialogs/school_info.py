"""dialogs/school_info.py — Temel Okul Bilgileri (Ayarlar Sihirbazı)"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, 
    QPushButton, QTabWidget, QWidget, QCheckBox, QRadioButton, QFrame, QButtonGroup
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen
from PySide6.QtGui import QLinearGradient

def draw_placeholder_icon(icon_type):
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    
    # Common shadow
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 50))
    p.drawRoundedRect(6, 6, 52, 52, 12, 12)
    
    if icon_type == "bank":
        grad = QLinearGradient(10, 10, 54, 54)
        grad.setColorAt(0, QColor("#E2E8F0"))
        grad.setColorAt(1, QColor("#94A3B8"))
        p.setBrush(grad)
        p.setPen(QColor("#475569"))
        p.drawRoundedRect(10, 10, 44, 44, 10, 10)
        
        # Draw a classic bank/school icon
        p.setBrush(QColor("#FFFFFF"))
        p.drawPolygon([QPoint(32, 16), QPoint(18, 28), QPoint(46, 28)])
        p.drawRect(20, 28, 24, 4)
        for i in range(3):
            p.drawRect(22 + i*8, 32, 4, 14)
        p.drawRect(20, 46, 24, 4)
        
    elif icon_type == "grid":
        grad = QLinearGradient(10, 10, 54, 54)
        grad.setColorAt(0, QColor("#BAE6FD"))
        grad.setColorAt(1, QColor("#38BDF8"))
        p.setBrush(grad)
        p.setPen(QColor("#0284C7"))
        p.drawRoundedRect(10, 10, 44, 44, 10, 10)
        
        # Grid lines
        p.setPen(QPen(QColor("#FFFFFF"), 2))
        p.drawLine(10, 25, 54, 25)
        p.drawLine(10, 40, 54, 40)
        p.drawLine(25, 10, 25, 54)
        p.drawLine(40, 10, 40, 54)
        
        # Highlight cell
        p.setBrush(QColor("#FDE047"))
        p.setPen(Qt.NoPen)
        p.drawRect(27, 27, 11, 11)
        
    elif icon_type == "list":
        grad = QLinearGradient(10, 10, 54, 54)
        grad.setColorAt(0, QColor("#A7F3D0"))
        grad.setColorAt(1, QColor("#34D399"))
        p.setBrush(grad)
        p.setPen(QColor("#059669"))
        p.drawRoundedRect(10, 10, 44, 44, 10, 10)
        
        p.setPen(QPen(QColor("#FFFFFF"), 3))
        p.setBrush(QColor("#FFFFFF"))
        for i in range(3):
            p.drawEllipse(16, 18 + i*12, 4, 4)
            p.drawLine(26, 20 + i*12, 46, 20 + i*12)
            
    p.end()
    return pix

class SchoolInfoDialog(QDialog):
    def __init__(self, parent=None, data_store=None):
        super().__init__(parent)
        self.data_store = data_store if data_store is not None else {}
        self.setWindowTitle("Ayarlar")
        self.resize(720, 520)
        self.setStyleSheet("""
            QDialog { background-color: #F0F0F0; font-family: 'Segoe UI', sans-serif; font-size: 12px; }
            QTabWidget::pane { border: 1px solid #CCC; background: #FFFFFF; }
            QTabBar::tab { background: #E5E5E5; border: 1px solid #CCC; padding: 6px 16px; margin-right: 2px; }
            QTabBar::tab:selected { background: #FFFFFF; border-bottom-color: #FFFFFF; }
            QLineEdit, QComboBox { border: 1px solid #B0B0B0; padding: 4px; background: white; }
            QPushButton { padding: 4px 12px; border: 1px solid #ADADAD; background: #E1E1E1; border-radius: 2px; }
            QPushButton:hover { background: #E5F1FB; border: 1px solid #0078D7; }
            QPushButton#btn_primary { border: 1px solid #005499; background: #FFFFFF; font-weight: bold; }
            QPushButton#btn_primary:hover { background: #E5F1FB; }
            QFrame#h_line { background: #E0E0E0; max-height: 1px; }
            QLabel#status_lbl { background: #E0E0E0; border: 1px solid #B0B0B0; padding: 4px; color: #333; }
        """)
        self._build_ui()
        self._load_data()
        
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabs = QTabWidget()
        self.tab_genel = QWidget()
        self.tab_ulke = QWidget()
        self.tab_program = QWidget()
        
        self.tabs.addTab(self.tab_genel, "Genel Bilgiler")
        self.tabs.addTab(self.tab_ulke, "Ülke")
        self.tabs.addTab(self.tab_program, "Program Türü")
        
        self._build_genel_tab()
        
        main_layout.addWidget(self.tabs)
        
        # Status Bar Fake
        self.lbl_status = QLabel("k12kbs.com Üyelik Durumu : Pasif")
        self.lbl_status.setObjectName("status_lbl")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.lbl_status)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_ok = QPushButton("Tamam")
        self.btn_ok.setObjectName("btn_primary")
        self.btn_ok.setFixedSize(90, 30)
        self.btn_ok.clicked.connect(self._save_and_accept)
        
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setFixedSize(90, 30)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)
        
    def _build_genel_tab(self):
        layout = QVBoxLayout(self.tab_genel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # --- Section 1: Basic Info ---
        sec1 = QHBoxLayout()
        icon1 = QLabel()
        icon1.setPixmap(draw_placeholder_icon("bank"))
        icon1.setFixedSize(70, 70)
        sec1.addWidget(icon1)
        
        grid1 = QGridLayout()
        grid1.setSpacing(10)
        
        grid1.addWidget(QLabel("Okul / Kurum Adı:"), 0, 0)
        self.txt_kurum_adi = QLineEdit("Pivot Akademi")
        grid1.addWidget(self.txt_kurum_adi, 0, 1, 1, 2)
        
        grid1.addWidget(QLabel("Başlangıç Tarihi:"), 1, 0)
        self.txt_baslangic = QLineEdit("12/09/2026")
        grid1.addWidget(self.txt_baslangic, 1, 1, 1, 2)
        
        grid1.addWidget(QLabel("Öğretim Yılı / Tebliğ Sayısı:"), 2, 0)
        self.txt_yil = QLineEdit("2026/2027")
        self.txt_teblig = QLineEdit()
        grid1.addWidget(self.txt_yil, 2, 1)
        grid1.addWidget(self.txt_teblig, 2, 2)
        
        grid1.addWidget(QLabel("Kurum Yetkilisi Ad/Unvan:"), 3, 0)
        self.txt_yetkili_ad = QLineEdit("Ali ÇEKEN")
        self.txt_yetkili_unvan = QLineEdit("Okul Müdürü")
        grid1.addWidget(self.txt_yetkili_ad, 3, 1)
        grid1.addWidget(self.txt_yetkili_unvan, 3, 2)
        
        sec1.addLayout(grid1)
        sec1.addStretch()
        layout.addLayout(sec1)

    def _load_data(self):
        if not self.data_store: return
        kurum = self.data_store.get("kurum", {})
        if kurum.get("isim"):
            self.txt_kurum_adi.setText(kurum.get("isim"))
        line1 = QFrame(); line1.setObjectName("h_line"); layout.addWidget(line1)
        
        # --- Section 2: Time Settings ---
        sec2 = QHBoxLayout()
        icon2 = QLabel()
        icon2.setPixmap(draw_placeholder_icon("grid"))
        icon2.setFixedSize(70, 70)
        sec2.addWidget(icon2)
        
        grid2 = QGridLayout()
        grid2.setSpacing(10)
        
        grid2.addWidget(QLabel("Günlük Ders Saati:"), 0, 0)
        self.cb_ders_saati = QComboBox()
        self.cb_ders_saati.addItems([str(i) for i in range(1, 21)])
        self.cb_ders_saati.setCurrentText("7")
        self.cb_ders_saati.setFixedWidth(60)
        grid2.addWidget(self.cb_ders_saati, 0, 1)
        
        btn_zil = QPushButton("Zil / Zamanları Yeniden Adlandır")
        grid2.addWidget(btn_zil, 0, 2)
        
        grid2.addWidget(QLabel("Gün Sayısı:"), 1, 0)
        self.cb_gun_sayisi = QComboBox()
        self.cb_gun_sayisi.addItems([str(i) for i in range(1, 15)])
        self.cb_gun_sayisi.setCurrentText("5")
        self.cb_gun_sayisi.setFixedWidth(60)
        grid2.addWidget(self.cb_gun_sayisi, 1, 1)
        
        btn_gunler = QPushButton("Haftanın Günlerini Güncelle")
        grid2.addWidget(btn_gunler, 1, 2)
        
        grid2.addWidget(QLabel("Hafta Sonu:"), 2, 0, 1, 2, Qt.AlignRight)
        self.cb_hafta_sonu = QComboBox()
        self.cb_hafta_sonu.addItems(["Cumartesi - Pazar", "Pazar - Pazartesi", "Cuma - Cumartesi"])
        grid2.addWidget(self.cb_hafta_sonu, 2, 2)
        
        sec2.addLayout(grid2)
        sec2.addStretch()
        layout.addLayout(sec2)
        
        line2 = QFrame(); line2.setObjectName("h_line"); layout.addWidget(line2)
        
        # --- Section 3: Multi-week ---
        sec3 = QHBoxLayout()
        icon3 = QLabel()
        icon3.setPixmap(draw_placeholder_icon("calendar"))
        icon3.setFixedSize(70, 70)
        sec3.addWidget(icon3)
        
        vbox3 = QVBoxLayout()
        self.chk_cok_donem = QCheckBox("Çok Dönemli veya Çok Haftalı Program")
        font_bold = QFont()
        font_bold.setBold(True)
        self.chk_cok_donem.setFont(font_bold)
        vbox3.addWidget(self.chk_cok_donem)
        
        sec3.addLayout(vbox3)
        sec3.addStretch()
        layout.addLayout(sec3)
        
        line3 = QFrame(); line3.setObjectName("h_line"); layout.addWidget(line3)
        
        # --- Section 4: School Type ---
        sec4 = QVBoxLayout()
        self.radio_okul = QRadioButton("Okul / Kolej / Diğer")
        self.radio_fakulte = QRadioButton("Fakülte / Yüksek Okul")
        self.radio_okul.setChecked(True)
        
        btn_grp = QButtonGroup(self)
        btn_grp.addButton(self.radio_okul)
        btn_grp.addButton(self.radio_fakulte)
        
        sec4.addWidget(self.radio_okul)
        sec4.addWidget(self.radio_fakulte)
        sec4.setContentsMargins(90, 0, 0, 0)
        layout.addLayout(sec4)
        
        layout.addStretch()

    def _load_data(self):
        if not self.data_store: return
        kurum = self.data_store.get("kurum", {})
        if kurum.get("isim"):
            self.txt_kurum_adi.setText(kurum.get("isim"))
        if kurum.get("yetkili"):
            self.txt_yetkili_ad.setText(kurum.get("yetkili"))
            
        settings = self.data_store.get("settings", {})
        if settings.get("periods"):
            self.cb_ders_saati.setCurrentText(str(settings.get("periods")))
        if settings.get("days_count"):
            self.cb_gun_sayisi.setCurrentText(str(settings.get("days_count")))
        if settings.get("weekend"):
            idx = self.cb_hafta_sonu.findText(settings.get("weekend"))
            if idx >= 0: self.cb_hafta_sonu.setCurrentIndex(idx)
        if settings.get("multi_week"):
            self.chk_cok_donem.setChecked(settings.get("multi_week"))
        if settings.get("school_type") == "fakulte":
            self.radio_fakulte.setChecked(True)
        else:
            self.radio_okul.setChecked(True)
            
    def _save_and_accept(self):
        if self.data_store is not None:
            if "kurum" not in self.data_store:
                self.data_store["kurum"] = {}
            self.data_store["kurum"]["isim"] = self.txt_kurum_adi.text().strip()
            self.data_store["kurum"]["yetkili"] = self.txt_yetkili_ad.text().strip()
            
            if "settings" not in self.data_store:
                self.data_store["settings"] = {}
            
            self.data_store["settings"]["periods"] = int(self.cb_ders_saati.currentText())
            self.data_store["settings"]["days_count"] = int(self.cb_gun_sayisi.currentText())
            self.data_store["settings"]["weekend"] = self.cb_hafta_sonu.currentText()
            self.data_store["settings"]["multi_week"] = self.chk_cok_donem.isChecked()
            self.data_store["settings"]["school_type"] = "okul" if self.radio_okul.isChecked() else "fakulte"
            
        self.accept()

    def get_data(self):
        return {
            "okul_adi": self.txt_yetkili_ad.text(), # For backwards compatibility if needed
            "yil": 2026 - 2027,
            "gun_sayisi": int(self.cb_gun_sayisi.currentText()),
            "ders_saati": int(self.cb_ders_saati.currentText()),
        }
