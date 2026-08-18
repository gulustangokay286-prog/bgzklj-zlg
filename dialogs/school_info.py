"""dialogs/school_info.py — Temel Okul Bilgileri (Ayarlar Sihirbazı)"""
import os, re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, 
    QPushButton, QTabWidget, QWidget, QCheckBox, QRadioButton, QFrame, QButtonGroup,
    QMessageBox
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
            
    elif icon_type == "globe":
        grad = QLinearGradient(10, 10, 54, 54)
        grad.setColorAt(0, QColor("#DDD6FE"))
        grad.setColorAt(1, QColor("#8B5CF6"))
        p.setBrush(grad)
        p.setPen(QColor("#6D28D9"))
        p.drawRoundedRect(10, 10, 44, 44, 10, 10)
        
        p.setPen(QPen(QColor("#FFFFFF"), 2))
        p.drawEllipse(18, 18, 28, 28)
        p.drawLine(18, 32, 46, 32)
        p.drawEllipse(25, 18, 14, 28)
            
    p.end()
    return pix

class SchoolInfoDialog(QDialog):
    def __init__(self, parent=None, data_store=None):
        super().__init__(parent)
        self.data_store = data_store if data_store is not None else {}
        self.setWindowTitle("Ayarlar")
        self.resize(740, 540)
        self.setStyleSheet("""
            QDialog { background-color: #F0F0F0; font-family: 'Segoe UI', sans-serif; font-size: 12px; }
            QTabWidget::pane { border: 1px solid #CCC; background: #FFFFFF; }
            QTabBar::tab { background: #E5E5E5; border: 1px solid #CCC; padding: 6px 18px; margin-right: 2px; font-weight: 500; }
            QTabBar::tab:selected { background: #FFFFFF; border-bottom-color: #FFFFFF; font-weight: bold; }
            QLineEdit, QComboBox { border: 1px solid #B0B0B0; padding: 5px; background: white; border-radius: 3px; }
            QLineEdit:focus, QComboBox:focus { border: 1.5px solid #0284C7; }
            QPushButton { padding: 5px 14px; border: 1px solid #ADADAD; background: #E1E1E1; border-radius: 3px; font-weight: 500; }
            QPushButton:hover { background: #E5F1FB; border: 1px solid #0078D7; }
            QPushButton#btn_primary { border: 1px solid #005499; background: #0284C7; color: white; font-weight: bold; }
            QPushButton#btn_primary:hover { background: #0369A1; }
            QFrame#h_line { background: #E0E0E0; max-height: 1px; }
            QLabel#status_lbl { background: #EFF6FF; border: 1px solid #93C5FD; color: #1E40AF; font-weight: bold; padding: 8px; border-radius: 6px; font-size: 12px; }
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
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        
        self.tabs = QTabWidget()
        self.tab_genel = QWidget()
        self.tab_ulke = QWidget()
        self.tab_program = QWidget()
        
        self.tabs.addTab(self.tab_genel, "Genel Bilgiler")
        self.tabs.addTab(self.tab_ulke, "Ülke")
        self.tabs.addTab(self.tab_program, "Program Türü")
        
        self._build_genel_tab()
        self._build_ulke_tab()
        self._build_program_tab()
        
        main_layout.addWidget(self.tabs)
        
        self.lbl_status = QLabel("🏫 BGZ Eğitim Kurumları : Üyelik Durumu Aktif (Kalan Süre: 365 Gün / 1 Yıl — Lisanslı Kurum)")
        self.lbl_status.setObjectName("status_lbl")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.lbl_status)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_ok = QPushButton("Tamam")
        self.btn_ok.setObjectName("btn_primary")
        self.btn_ok.setFixedSize(95, 32)
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.clicked.connect(self._save_and_accept)
        
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setFixedSize(95, 32)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)
        
    def _build_genel_tab(self):
        layout = QVBoxLayout(self.tab_genel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        # Section 1: Basic Info
        sec1 = QHBoxLayout()
        icon1 = QLabel()
        icon1.setPixmap(draw_placeholder_icon("bank"))
        icon1.setFixedSize(70, 70)
        sec1.addWidget(icon1)
        
        grid1 = QGridLayout()
        grid1.setSpacing(8)
        
        grid1.addWidget(QLabel("Okul / Kurum Adı:"), 0, 0)
        self.txt_kurum_adi = QLineEdit("BGZ Eğitim Kurumları")
        grid1.addWidget(self.txt_kurum_adi, 0, 1, 1, 2)
        
        grid1.addWidget(QLabel("Başlangıç Tarihi:"), 1, 0)
        self.txt_baslangic = QLineEdit("12/09/2026")
        grid1.addWidget(self.txt_baslangic, 1, 1, 1, 2)
        
        grid1.addWidget(QLabel("Öğretim Yılı / Tebliğ Sayısı:"), 2, 0)
        self.txt_yil = QLineEdit("2026 - 2027")
        self.txt_teblig = QLineEdit()
        self.txt_teblig.setPlaceholderText("Tebliğ No (Opsiyonel)")
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
        grid2.setSpacing(8)
        
        grid2.addWidget(QLabel("Çizelge Zamanı / Günlük Ders Saati:"), 0, 0)
        self.cb_ders_saati = QComboBox()
        self.cb_ders_saati.addItems([str(i) for i in range(1, 17)])
        self.cb_ders_saati.setCurrentText("8")
        self.cb_ders_saati.setFixedWidth(70)
        grid2.addWidget(self.cb_ders_saati, 0, 1)
        
        btn_zil = QPushButton("🔔 Zil / Teneffüs Saatlerini Ayarla")
        btn_zil.setCursor(Qt.PointingHandCursor)
        btn_zil.clicked.connect(self._open_zil_dialog)
        grid2.addWidget(btn_zil, 0, 2)
        
        grid2.addWidget(QLabel("Haftalık Çalışma Gün Sayısı:"), 1, 0)
        self.cb_gun_sayisi = QComboBox()
        self.cb_gun_sayisi.addItems([str(i) for i in range(1, 8)])
        self.cb_gun_sayisi.setCurrentText("5")
        self.cb_gun_sayisi.setFixedWidth(70)
        grid2.addWidget(self.cb_gun_sayisi, 1, 1)
        
        btn_gunler = QPushButton("📅 Günler ve Tatil Günlerini Seç")
        btn_gunler.setCursor(Qt.PointingHandCursor)
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
        sec4.setContentsMargins(85, 0, 0, 0)
        layout.addLayout(sec4)
        
        layout.addStretch()

    def _build_ulke_tab(self):
        layout = QVBoxLayout(self.tab_ulke)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        sec = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(draw_placeholder_icon("globe"))
        icon.setFixedSize(70, 70)
        sec.addWidget(icon)
        
        grid = QGridLayout()
        grid.setSpacing(10)
        
        grid.addWidget(QLabel("Ülke Seçimi:"), 0, 0)
        self.cb_ulke = QComboBox()
        self.cb_ulke.addItems(["Türkiye (TR)", "Kuzey Kıbrıs Türk Cumhuriyeti (KKTC)", "Almanya (DE)", "İngiltere (UK)", "Azerbaycan (AZ)"])
        grid.addWidget(self.cb_ulke, 0, 1)
        
        grid.addWidget(QLabel("Arayüz Dili:"), 1, 0)
        self.cb_dil = QComboBox()
        self.cb_dil.addItems(["Türkçe (Varsayılan)", "English", "Deutsch"])
        grid.addWidget(self.cb_dil, 1, 1)
        
        grid.addWidget(QLabel("Saat Dilimi / Zaman:"), 2, 0)
        self.cb_saat_dilimi = QComboBox()
        self.cb_saat_dilimi.addItems(["GMT+3 (İstanbul, Ankara)", "GMT+2 (Berlin, Paris)", "GMT+0 (Londra)", "GMT+4 (Bakü)"])
        grid.addWidget(self.cb_saat_dilimi, 2, 1)
        
        sec.addLayout(grid)
        sec.addStretch()
        layout.addLayout(sec)
        layout.addStretch()

    def _build_program_tab(self):
        layout = QVBoxLayout(self.tab_program)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        lbl_info = QLabel("<b>Çizelge Programlama Modeli</b><br>Kurumunuz için geçerli olan haftalık dağılım türünü belirleyin.")
        lbl_info.setStyleSheet("color: #334155; font-size: 13px;")
        layout.addWidget(lbl_info)
        
        self.radio_prog_standart = QRadioButton("Standart Tek Haftalık Çizelge (Haftalık Ders Dağılımı - Önerilen)")
        self.radio_prog_ab = QRadioButton("2 Haftalık Dönüşümlü Çizelge (A Haftası / B Haftası Çift Sistem)")
        self.radio_prog_donem = QRadioButton("Dönemlik Modüler Çizelge (Güz Dönemi / Bahar Dönemi Ayrımı)")
        self.radio_prog_standart.setChecked(True)
        
        prog_grp = QButtonGroup(self)
        prog_grp.addButton(self.radio_prog_standart)
        prog_grp.addButton(self.radio_prog_ab)
        prog_grp.addButton(self.radio_prog_donem)
        
        layout.addWidget(self.radio_prog_standart)
        layout.addWidget(self.radio_prog_ab)
        layout.addWidget(self.radio_prog_donem)
        layout.addStretch()

    def _open_zil_dialog(self):
        from dialogs.bell_times_dialog import BellAndBreakTimesDialog
        cur_periods = int(self.cb_ders_saati.currentText())
        dlg = BellAndBreakTimesDialog(self.data_store, periods=cur_periods, parent=self)
        if dlg.exec():
            win = self.window()
            if hasattr(win, "save_db"):
                win.save_db(sync_from_grid=False)

    def _open_gunler_dialog(self):
        from dialogs.days_dialog import DaysAndHolidaysDialog
        dlg = DaysAndHolidaysDialog(self.data_store, parent=self)
        if dlg.exec():
            sel_days = dlg.get_selected_days()
            day_cnt = str(len(sel_days))
            idx_d = self.cb_gun_sayisi.findText(day_cnt)
            if idx_d >= 0:
                self.cb_gun_sayisi.setCurrentIndex(idx_d)
            weekend = self.data_store.get("settings", {}).get("weekend", "Cumartesi - Pazar")
            idx_w = self.cb_hafta_sonu.findText(weekend)
            if idx_w >= 0:
                self.cb_hafta_sonu.setCurrentIndex(idx_w)

    def _load_data(self):
        if not self.data_store: return
        settings = self.data_store.get("settings", {})
        kurum = self.data_store.get("kurum", {})
        
        # 1. Okul / Kurum Adı
        school_name = settings.get("school_name") or kurum.get("isim") or self.data_store.get("okul_adi", "") or self.data_store.get("kurum_adi", "")
        if school_name:
            self.txt_kurum_adi.setText(str(school_name))
            
        # 2. Başlangıç Tarihi
        start_date = settings.get("start_date") or settings.get("baslangic") or kurum.get("baslangic") or "12/09/2026"
        self.txt_baslangic.setText(str(start_date))
        
        # 3. Öğretim Yılı & Tebliğ
        acad_year = settings.get("academic_year") or settings.get("ogretim_yili") or kurum.get("yil") or "2026 - 2027"
        self.txt_yil.setText(str(acad_year))
        
        teblig = settings.get("bulletin_no") or settings.get("teblig") or kurum.get("teblig") or ""
        self.txt_teblig.setText(str(teblig))
        
        # 4. Yetkili Ad & Unvan
        principal = settings.get("principal") or kurum.get("yetkili", "") or "Ali ÇEKEN"
        self.txt_yetkili_ad.setText(str(principal))
        
        principal_title = settings.get("principal_title") or kurum.get("yetkili_unvan", "") or "Okul Müdürü"
        self.txt_yetkili_unvan.setText(str(principal_title))
        
        # 5. Ders Saati
        periods = str(settings.get("periods") or self.data_store.get("ders_saati", 8))
        idx_p = self.cb_ders_saati.findText(periods)
        if idx_p >= 0:
            self.cb_ders_saati.setCurrentIndex(idx_p)
            
        # 6. Gün Sayısı
        day_count = str(settings.get("day_count") or settings.get("days_count") or self.data_store.get("gun_sayisi", 5))
        idx_d = self.cb_gun_sayisi.findText(day_count)
        if idx_d >= 0:
            self.cb_gun_sayisi.setCurrentIndex(idx_d)
            
        # 7. Hafta Sonu
        weekend = settings.get("weekend") or self.data_store.get("hafta_sonu", "Cumartesi - Pazar")
        idx_w = self.cb_hafta_sonu.findText(weekend)
        if idx_w >= 0:
            self.cb_hafta_sonu.setCurrentIndex(idx_w)
            
        # 8. Çok Dönemli
        multi_term = bool(settings.get("multi_term") or settings.get("cok_donem", False))
        self.chk_cok_donem.setChecked(multi_term)
        
        # 9. Okul / Fakülte Türü
        s_type = settings.get("school_type") or self.data_store.get("kurum_turu", "okul")
        if s_type == "fakulte":
            self.radio_fakulte.setChecked(True)
        else:
            self.radio_okul.setChecked(True)

    def _save_and_accept(self):
        if self.data_store is not None:
            settings = self.data_store.setdefault("settings", {})
            kurum = self.data_store.setdefault("kurum", {})
            
            sch_name = self.txt_kurum_adi.text().strip() or "BGZ Eğitim Kurumları"
            start_date = self.txt_baslangic.text().strip() or "12/09/2026"
            acad_year = self.txt_yil.text().strip() or "2026 - 2027"
            teblig = self.txt_teblig.text().strip()
            princ = self.txt_yetkili_ad.text().strip() or "Ali ÇEKEN"
            princ_title = self.txt_yetkili_unvan.text().strip() or "Okul Müdürü"
            
            try:
                periods = int(self.cb_ders_saati.currentText())
            except Exception:
                periods = 8
                
            try:
                day_cnt = int(self.cb_gun_sayisi.currentText())
            except Exception:
                day_cnt = 5
                
            weekend = self.cb_hafta_sonu.currentText()
            multi_term = self.chk_cok_donem.isChecked()
            school_type = "fakulte" if self.radio_fakulte.isChecked() else "okul"
            
            # Root keys update
            self.data_store["okul_adi"] = sch_name
            self.data_store["kurum_adi"] = sch_name
            self.data_store["ders_saati"] = periods
            self.data_store["gun_sayisi"] = day_cnt
            self.data_store["hafta_sonu"] = weekend
            self.data_store["kurum_turu"] = school_type
            
            # Kurum dict update
            kurum["isim"] = sch_name
            kurum["yetkili"] = princ
            kurum["yetkili_unvan"] = princ_title
            kurum["baslangic"] = start_date
            kurum["yil"] = acad_year
            kurum["teblig"] = teblig
            
            # Settings dict update
            settings["school_name"] = sch_name
            settings["start_date"] = start_date
            settings["academic_year"] = acad_year
            settings["bulletin_no"] = teblig
            settings["principal"] = princ
            settings["principal_title"] = princ_title
            settings["periods"] = periods
            settings["day_count"] = day_cnt
            settings["days_count"] = day_cnt
            settings["weekend"] = weekend
            settings["multi_term"] = multi_term
            settings["school_type"] = school_type
            
            all_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            active_days = all_days[:day_cnt]
            settings["days"] = active_days
            settings["days_list"] = active_days
            
            # Locate MainWindow
            win = self.window()
            if not win or not hasattr(win, "_grid"):
                p = self.parent()
                while p:
                    if hasattr(p, "_grid"):
                        win = p
                        break
                    p = p.parent()
                    
            if win:
                if hasattr(win, "_grid"):
                    win._grid.set_periods(periods)
                    
                slug = getattr(win, "institution_slug", None)
                ver_fn = getattr(win, "version_filename", None)
                if slug:
                    try:
                        import version_store
                        version_store.rename_institution(slug, sch_name)
                        if ver_fn:
                            version_store.update_version_in_place(slug, ver_fn, self.data_store)
                    except Exception as e:
                        print("Error updating version_store from school_info:", e)
                        
                try:
                    v_num = ""
                    if ver_fn:
                        m = re.match(r"v(\d+)_", ver_fn)
                        if m: v_num = f"v{int(m.group(1))}"
                    title_suffix = f" — {v_num}" if v_num else ""
                    win.setWindowTitle(f"BGZ Ders Planlama — {sch_name}{title_suffix}")
                except Exception:
                    pass
                    
                if hasattr(win, "save_db"):
                    win.save_db(sync_from_grid=False)
                    
                if hasattr(win, "_refresh_grid"): win._refresh_grid()
                if hasattr(win, "_refresh_tree"): win._refresh_tree()
                if hasattr(win, "_refresh_unplaced_lessons"): win._refresh_unplaced_lessons()
                
        self.accept()

    def get_data(self):
        return {
            "okul_adi": self.txt_kurum_adi.text().strip(),
            "yil": self.txt_yil.text().strip() or "2026 - 2027",
            "gun_sayisi": int(self.cb_gun_sayisi.currentText()),
            "ders_saati": int(self.cb_ders_saati.currentText()),
            "baslangic": self.txt_baslangic.text().strip(),
            "yetkili": self.txt_yetkili_ad.text().strip(),
            "yetkili_unvan": self.txt_yetkili_unvan.text().strip()
        }
