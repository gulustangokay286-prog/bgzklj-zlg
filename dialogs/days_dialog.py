"""dialogs/days_dialog.py — Çalışma Günleri ve Tatil Günleri Özelleştirme Penceresi"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QGroupBox, QGridLayout, QComboBox, QFrame, QMessageBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

DAYS_ALL = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

class DaysAndHolidaysDialog(QDialog):
    """Haftalık Çalışma Günleri ve Tatil Günleri Gelişmiş Seçim Penceresi"""
    def __init__(self, data_store=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        
        self.setWindowTitle("📅 Çalışma Günleri ve Tatil Günleri Ayarları")
        self.resize(540, 520)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; }
            QGroupBox { font-weight: bold; border: 1px solid #CBD5E1; border-radius: 8px; margin-top: 10px; padding-top: 12px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #1E40AF; }
            QCheckBox { font-size: 13px; font-weight: 500; color: #1E293B; padding: 4px; }
            QComboBox { border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 8px; min-height: 28px; background: white; }
            QPushButton { border-radius: 5px; font-weight: bold; min-height: 32px; padding: 4px 16px; }
        """)
        
        self._build_ui()
        self._load_data()
        
    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(14)
        
        # 1. Info Banner
        info_lbl = QLabel(
            "💡 <b>Haftalık Çalışma Günleri:</b> Okulunuzun veya kurumunuzun haftalık ders yaptığı günleri "
            "işaretleyiniz. Cumartesi veya Pazar günleri işaretlendiğinde ana çizelge ve yazdırma tabloları "
            "otomatik olarak bu günleri kapsayacak şekilde genişleyecektir."
        )
        info_lbl.setStyleSheet("background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 10px; color: #1E3A8A; font-size: 11px;")
        info_lbl.setWordWrap(True)
        lay.addWidget(info_lbl)
        
        # 2. Gün Seçim Kutusu
        grp_days = QGroupBox("1. Haftalık Ders Yapılan Günleri Seçin")
        lay_days = QVBoxLayout(grp_days)
        lay_days.setContentsMargins(14, 12, 14, 12)
        lay_days.setSpacing(8)
        
        self.day_checks = []
        for i, day_name in enumerate(DAYS_ALL):
            f_row = QFrame()
            f_row.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 4px 10px;")
            l_row = QHBoxLayout(f_row)
            l_row.setContentsMargins(4, 2, 4, 2)
            
            chk = QCheckBox(f"📌 {day_name}")
            is_weekend = (i >= 5)
            if is_weekend:
                chk.setStyleSheet("color: #B45309; font-weight: bold;")
                tag_lbl = QLabel("Hafta Sonu / Kurs")
                tag_lbl.setStyleSheet("background: #FEF3C7; color: #92400E; font-size: 10px; padding: 2px 6px; border-radius: 3px;")
            else:
                tag_lbl = QLabel("Hafta İçi")
                tag_lbl.setStyleSheet("background: #DCFCE7; color: #166534; font-size: 10px; padding: 2px 6px; border-radius: 3px;")
                
            l_row.addWidget(chk)
            l_row.addStretch()
            l_row.addWidget(tag_lbl)
            
            lay_days.addWidget(f_row)
            self.day_checks.append((day_name, chk))
            chk.stateChanged.connect(self._on_days_changed)
            
        lay.addWidget(grp_days)
        
        # 3. Özet ve Şablonlar
        grp_summary = QGroupBox("2. Hızlı Şablonlar & Özet")
        lay_sum = QHBoxLayout(grp_summary)
        lay_sum.setContentsMargins(12, 10, 12, 10)
        
        btn_5d = QPushButton("5 Gün (Pzt - Cuma)")
        btn_5d.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; color: #334155;")
        btn_5d.clicked.connect(lambda: self._apply_template(5))
        lay_sum.addWidget(btn_5d)
        
        btn_6d = QPushButton("6 Gün (+Cumartesi)")
        btn_6d.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; color: #334155;")
        btn_6d.clicked.connect(lambda: self._apply_template(6))
        lay_sum.addWidget(btn_6d)
        
        btn_7d = QPushButton("7 Gün (Tüm Hafta)")
        btn_7d.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; color: #334155;")
        btn_7d.clicked.connect(lambda: self._apply_template(7))
        lay_sum.addWidget(btn_7d)
        
        lay.addWidget(grp_summary)
        
        self.lbl_count = QLabel("Seçilen Toplam Gün: 5 Gün")
        self.lbl_count.setStyleSheet("font-weight: bold; font-size: 12px; color: #1E40AF; padding-left: 4px;")
        lay.addWidget(self.lbl_count)
        
        # 4. Buttons
        bot = QHBoxLayout()
        bot.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background: white; border: 1px solid #CBD5E1; color: #475569;")
        btn_cancel.clicked.connect(self.reject)
        bot.addWidget(btn_cancel)
        
        btn_save = QPushButton("💾 Gün Ayarlarını Kaydet")
        btn_save.setStyleSheet("background: #2563EB; color: white; border: none; padding: 6px 20px;")
        btn_save.clicked.connect(self._save_and_accept)
        bot.addWidget(btn_save)
        
        lay.addLayout(bot)
        
    def _apply_template(self, count):
        for i, (name, chk) in enumerate(self.day_checks):
            chk.setChecked(i < count)
        self._on_days_changed()
        
    def _on_days_changed(self):
        selected = [name for name, chk in self.day_checks if chk.isChecked()]
        self.lbl_count.setText(f"Seçilen Toplam Gün: {len(selected)} Gün ({', '.join(selected) if selected else 'Yok'})")
        
    def _load_data(self):
        settings = self.data_store.get("settings", {})
        saved_days = settings.get("days", [])
        if not saved_days:
            cnt = int(settings.get("day_count", self.data_store.get("gun_sayisi", 5)))
            saved_days = DAYS_ALL[:cnt]
            
        for name, chk in self.day_checks:
            chk.setChecked(name in saved_days)
        self._on_days_changed()
        
    def _save_and_accept(self):
        selected_days = [name for name, chk in self.day_checks if chk.isChecked()]
        if not selected_days:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az 1 çalışma günü seçiniz!")
            return
            
        settings = self.data_store.setdefault("settings", {})
        settings["days"] = selected_days
        settings["days_list"] = selected_days
        settings["days_count"] = len(selected_days)
        settings["day_count"] = len(selected_days)
        self.data_store["gun_sayisi"] = len(selected_days)
        
        # Determine weekend string
        unselected = [name for name in DAYS_ALL if name not in selected_days]
        if "Cumartesi" in unselected and "Pazar" in unselected:
            settings["weekend"] = "Cumartesi - Pazar"
        elif "Pazar" in unselected:
            settings["weekend"] = "Yalnız Pazar"
        elif not unselected:
            settings["weekend"] = "Hafta Sonu Tatili Yok"
        else:
            settings["weekend"] = " - ".join(unselected)
            
        win = self.window()
        if not win or not hasattr(win, "_grid"):
            p = self.parent()
            while p:
                if hasattr(p, "_grid"): win = p; break
                p = p.parent()
        if win:
            if hasattr(win, "save_db"): win.save_db(sync_from_grid=False)
            if hasattr(win, "_refresh_grid"): win._refresh_grid()
            if hasattr(win, "_refresh_tree"): win._refresh_tree()
            
        self.accept()
        
    def get_selected_days(self):
        return [name for name, chk in self.day_checks if chk.isChecked()]
