"""dialogs/school_info.py — Temel Okul Bilgileri (Ayarlar Sihirbazı)"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, 
    QPushButton, QTabWidget, QWidget, QCheckBox, QRadioButton, QFrame, QButtonGroup
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QLinearGradient

def draw_placeholder_icon(icon_type):
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    
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
        
        p.setPen(QPen(QColor("#FFFFFF"), 2))
        p.drawLine(10, 25, 54, 25)
        p.drawLine(10, 40, 54, 40)
        p.drawLine(25, 10, 25, 54)
        p.drawLine(40, 10, 40, 54)
        
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
        
        self.lbl_status = QLabel("k12kbs.com Üyelik Durumu : Pasif")
        self.lbl_status.setObjectName("status_lbl")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.lbl_status)
        
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
        
        # Section 1: Basic Info
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
        
        line1 = QFrame(); line1.setObjectName("h_line"); layout.addWidget(line1)
        
        # Section 2: Time Settings
        sec2 = QHBoxLayout()
        icon2 = QLabel()
        icon2.setPixmap(draw_placeholder_icon("grid"))
        icon2.setFixedSize(70, 70)
        sec2.addWidget(icon2)
        
        grid2 = QGridLayout()
        grid2.setSpacing(10)
        
        grid2.addWidget(QLabel("Çizelge Zamanı / Günlük Ders Saati:"), 0, 0)
        self.cb_ders_saati = QComboBox()
        self.cb_ders_saati.addItems([str(i) for i in range(1, 17)])
        self.cb_ders_saati.setCurrentText("8")
        self.cb_ders_saati.setFixedWidth(70)
        grid2.addWidget(self.cb_ders_saati, 0, 1)
        
        btn_zil = QPushButton("🔔 Zil / Teneffüs Saatlerini Ayarla")
        btn_zil.clicked.connect(self._open_zil_dialog)
        grid2.addWidget(btn_zil, 0, 2)
        
        grid2.addWidget(QLabel("Haftalık Çalışma Gün Sayısı:"), 1, 0)
        self.cb_gun_sayisi = QComboBox()
        self.cb_gun_sayisi.addItems([str(i) for i in range(1, 8)])
        self.cb_gun_sayisi.setCurrentText("5")
        self.cb_gun_sayisi.setFixedWidth(70)
        grid2.addWidget(self.cb_gun_sayisi, 1, 1)
        
        btn_gunler = QPushButton("📅 Günler ve Tatil Günlerini Seç")
        btn_gunler.clicked.connect(self._open_gunler_dialog)
        grid2.addWidget(btn_gunler, 1, 2)
        
        grid2.addWidget(QLabel("Hafta Sonu:"), 2, 0, 1, 2, Qt.AlignRight)
        self.cb_hafta_sonu = QComboBox()
        self.cb_hafta_sonu.addItems(["Cumartesi - Pazar", "Pazar - Pazartesi", "Cuma - Cumartesi", "Yalnız Pazar", "Hafta Sonu Tatili Yok"])
        grid2.addWidget(self.cb_hafta_sonu, 2, 2)
        
        sec2.addLayout(grid2)
        sec2.addStretch()
        layout.addLayout(sec2)
        
        line2 = QFrame(); line2.setObjectName("h_line"); layout.addWidget(line2)
        
        # Section 3: Multi-week
        sec3 = QHBoxLayout()
        icon3 = QLabel()
        icon3.setPixmap(draw_placeholder_icon("list"))
        icon3.setFixedSize(70, 70)
        sec3.addWidget(icon3)
        
        vbox3 = QVBoxLayout()
        self.chk_cok_donem = QCheckBox("Çok Dönemli veya Çok Haftalı Program (Güz / Bahar)")
        font_bold = QFont()
        font_bold.setBold(True)
        self.chk_cok_donem.setFont(font_bold)
        vbox3.addWidget(self.chk_cok_donem)
        
        sec3.addLayout(vbox3)
        sec3.addStretch()
        layout.addLayout(sec3)
        
        line3 = QFrame(); line3.setObjectName("h_line"); layout.addWidget(line3)
        
        # Section 4: School Type
        sec4 = QVBoxLayout()
        self.radio_okul = QRadioButton("Okul / Kolej / Kurs / Özel Öğretim")
        self.radio_fakulte = QRadioButton("Fakülte / Yüksek Okul / Üniversite")
        self.radio_okul.setChecked(True)
        
        btn_grp = QButtonGroup(self)
        btn_grp.addButton(self.radio_okul)
        btn_grp.addButton(self.radio_fakulte)
        
        sec4.addWidget(self.radio_okul)
        sec4.addWidget(self.radio_fakulte)
        sec4.setContentsMargins(90, 0, 0, 0)
        layout.addLayout(sec4)
        
        layout.addStretch()

    def _open_zil_dialog(self):
        from PySide6.QtWidgets import QInputDialog
        cur_periods = int(self.cb_ders_saati.currentText())
        settings = self.data_store.setdefault("settings", {})
        default_bell = settings.get("bell_schedule", "08:30-09:10, 09:20-10:00, 10:10-10:50, 11:00-11:40, 11:50-12:30, 13:30-14:10, 14:20-15:00, 15:10-15:50")
        text, ok = QInputDialog.getMultiLineText(
            self, "Zil / Teneffüs Saatleri Ayarı",
            f"Günlük {cur_periods} saatlik dersler için zil ve teneffüs saatlerini virgülle ayırarak giriniz:",
            default_bell
        )
        if ok and text.strip():
            settings["bell_schedule"] = text.strip()

    def _open_gunler_dialog(self):
        from PySide6.QtWidgets import QMessageBox
        cnt = self.cb_gun_sayisi.currentText()
        ws = self.cb_hafta_sonu.currentText()
        QMessageBox.information(
            self, "Çalışma Günleri",
            f"Haftalık Çalışma Gün Sayısı: {cnt} Gün\nHafta Sonu Tatili: {ws}\n\nProgram çizelgesi bu gün ayarlarına göre otomatik güncellenecektir."
        )

    def _load_data(self):
        if not self.data_store: return
        settings = self.data_store.get("settings", {})
        kurum = self.data_store.get("kurum", {})
        
        school_name = settings.get("school_name") or kurum.get("isim") or self.data_store.get("okul_adi", "")
        if school_name:
            self.txt_kurum_adi.setText(school_name)
            
        principal = settings.get("principal") or kurum.get("yetkili", "")
        if principal:
            self.txt_yetkili_ad.setText(principal)
            
        principal_title = settings.get("principal_title", "Okul Müdürü")
        self.txt_yetkili_unvan.setText(principal_title)
        
        acad_year = settings.get("academic_year", "2026 - 2027")
        self.txt_yil.setText(acad_year)
        
        periods = str(settings.get("periods") or self.data_store.get("ders_saati", 8))
        idx_p = self.cb_ders_saati.findText(periods)
        if idx_p >= 0:
            self.cb_ders_saati.setCurrentIndex(idx_p)
            
        day_count = str(settings.get("day_count") or self.data_store.get("gun_sayisi", 5))
        idx_d = self.cb_gun_sayisi.findText(day_count)
        if idx_d >= 0:
            self.cb_gun_sayisi.setCurrentIndex(idx_d)
            
        weekend = settings.get("weekend", "Cumartesi - Pazar")
        idx_w = self.cb_hafta_sonu.findText(weekend)
        if idx_w >= 0:
            self.cb_hafta_sonu.setCurrentIndex(idx_w)
            
    def _save_and_accept(self):
        if self.data_store is not None:
            settings = self.data_store.setdefault("settings", {})
            kurum = self.data_store.setdefault("kurum", {})
            
            sch_name = self.txt_kurum_adi.text().strip()
            princ = self.txt_yetkili_ad.text().strip()
            princ_title = self.txt_yetkili_unvan.text().strip()
            acad_year = self.txt_yil.text().strip() or "2026 - 2027"
            periods = int(self.cb_ders_saati.currentText())
            day_cnt = int(self.cb_gun_sayisi.currentText())
            weekend = self.cb_hafta_sonu.currentText()
            
            kurum["isim"] = sch_name
            kurum["yetkili"] = princ
            self.data_store["okul_adi"] = sch_name
            self.data_store["ders_saati"] = periods
            self.data_store["gun_sayisi"] = day_cnt
            
            settings["school_name"] = sch_name
            settings["principal"] = princ
            settings["principal_title"] = princ_title
            settings["academic_year"] = acad_year
            settings["periods"] = periods
            settings["day_count"] = day_cnt
            settings["weekend"] = weekend
            
            all_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            settings["days"] = all_days[:day_cnt]
            
        self.accept()

    def get_data(self):
        return {
            "okul_adi": self.txt_kurum_adi.text().strip(),
            "yil": "2026 - 2027",
            "gun_sayisi": int(self.cb_gun_sayisi.currentText()),
            "ders_saati": int(self.cb_ders_saati.currentText()),
        }
