"""dialogs/bell_times_dialog.py — Zil ve Teneffüs Saatleri Gelişmiş Yönetim Penceresi"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QTimeEdit, QSpinBox, QHeaderView, QGroupBox,
    QGridLayout, QFrame, QComboBox, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, QTime
from PySide6.QtGui import QFont, QColor, QBrush, QIcon

class BellAndBreakTimesDialog(QDialog):
    """Gelişmiş Zil, Ders ve Teneffüs Saatleri Yönetim Penceresi (1-16 Saat Destekli)"""
    def __init__(self, data_store=None, periods=8, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        self.periods = max(1, min(16, int(periods)))
        
        self.setWindowTitle("🔔 Zil ve Teneffüs Saatleri Ayarları (Saat Saat Özelleştirme)")
        self.resize(820, 640)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; }
            QGroupBox { font-weight: bold; border: 1px solid #CBD5E1; border-radius: 8px; margin-top: 10px; padding-top: 12px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #1E40AF; }
            QTableWidget { border: 1px solid #CBD5E1; border-radius: 6px; background: white; gridline-color: #E2E8F0; }
            QHeaderView::section { background-color: #F1F5F9; color: #334155; font-weight: bold; padding: 6px; border: 1px solid #E2E8F0; }
            QTimeEdit, QSpinBox, QComboBox { border: 1px solid #CBD5E1; border-radius: 4px; padding: 3px 6px; min-height: 24px; }
            QPushButton { border-radius: 5px; font-weight: bold; min-height: 32px; padding: 4px 14px; }
        """)
        
        self._build_ui()
        self._load_data()
        
    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(16, 16, 16, 16)
        main_lay.setSpacing(12)
        
        # 1. Info Banner
        info_lbl = QLabel(
            "💡 <b>Zil & Teneffüs Saatleri:</b> Günlük ders saatinize (" + str(self.periods) + " Saat) göre her bir dersin başlangıç, "
            "bitiş ve teneffüs sürelerini saat saat elle özelleştirebilir veya sihirbaz ile tek tıkla otomatik hesaplatabilirsiniz."
        )
        info_lbl.setStyleSheet("background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 8px 12px; color: #1E3A8A; font-size: 11px;")
        info_lbl.setWordWrap(True)
        main_lay.addWidget(info_lbl)
        
        # 2. Hızlı Otomatik Hesaplama Sihirbazı
        grp_wiz = QGroupBox("⚡ Hızlı Otomatik Doldurma ve Hesaplama")
        lay_wiz = QGridLayout(grp_wiz)
        lay_wiz.setContentsMargins(12, 12, 12, 12)
        lay_wiz.setSpacing(10)
        
        lay_wiz.addWidget(QLabel("1. Ders Başlangıcı:"), 0, 0)
        self.tm_start = QTimeEdit(QTime(8, 30))
        self.tm_start.setDisplayFormat("HH:mm")
        lay_wiz.addWidget(self.tm_start, 0, 1)
        
        lay_wiz.addWidget(QLabel("Ders Süresi (dk):"), 0, 2)
        self.sp_lesson_dur = QSpinBox()
        self.sp_lesson_dur.setRange(20, 90)
        self.sp_lesson_dur.setValue(40)
        lay_wiz.addWidget(self.sp_lesson_dur, 0, 3)
        
        lay_wiz.addWidget(QLabel("Standart Teneffüs (dk):"), 0, 4)
        self.sp_break_dur = QSpinBox()
        self.sp_break_dur.setRange(0, 60)
        self.sp_break_dur.setValue(10)
        lay_wiz.addWidget(self.sp_break_dur, 0, 5)
        
        lay_wiz.addWidget(QLabel("Öğle Arası Saati:"), 1, 0)
        self.cb_lunch_period = QComboBox()
        self.cb_lunch_period.addItem("Öğle Arası Yok", 0)
        for i in range(1, self.periods):
            self.cb_lunch_period.addItem(f"{i}. Ders Sonrası", i)
        if self.periods >= 4:
            self.cb_lunch_period.setCurrentIndex(4) # 4. ders sonrası default
        lay_wiz.addWidget(self.cb_lunch_period, 1, 1)
        
        lay_wiz.addWidget(QLabel("Öğle Arası Süresi (dk):"), 1, 2)
        self.sp_lunch_dur = QSpinBox()
        self.sp_lunch_dur.setRange(15, 120)
        self.sp_lunch_dur.setValue(45)
        lay_wiz.addWidget(self.sp_lunch_dur, 1, 3)
        
        btn_calc = QPushButton("⚡ Tüm Saatleri Otomatik Hesapla")
        btn_calc.setStyleSheet("background: #2563EB; color: white; border: none; padding: 6px 16px;")
        btn_calc.clicked.connect(self._auto_calculate_times)
        lay_wiz.addWidget(btn_calc, 1, 4, 1, 2)
        
        main_lay.addWidget(grp_wiz)
        
        # 3. Manuel Düzenleme Tablosu
        self.table = QTableWidget(self.periods, 5)
        self.table.setHorizontalHeaderLabels([
            "Ders No", "Başlangıç Saati", "Bitiş Saati", "Ders Süresi", "Sonraki Teneffüs (dk)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.setAlternatingRowColors(True)
        
        self.rows_data = []
        for i in range(self.periods):
            # 1. Ders No
            it_no = QTableWidgetItem(f"📚 {i+1}. Ders")
            it_no.setFlags(Qt.ItemIsEnabled)
            it_no.setTextAlignment(Qt.AlignCenter)
            it_no.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table.setItem(i, 0, it_no)
            
            # 2. Start Time
            tm_s = QTimeEdit()
            tm_s.setDisplayFormat("HH:mm")
            self.table.setCellWidget(i, 1, tm_s)
            
            # 3. End Time
            tm_e = QTimeEdit()
            tm_e.setDisplayFormat("HH:mm")
            self.table.setCellWidget(i, 2, tm_e)
            
            # 4. Duration Display
            it_dur = QTableWidgetItem("40 dk")
            it_dur.setTextAlignment(Qt.AlignCenter)
            it_dur.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(i, 3, it_dur)
            
            # 5. Break Duration
            sp_b = QSpinBox()
            sp_b.setRange(0, 120)
            sp_b.setValue(10 if i < self.periods - 1 else 0)
            sp_b.setSuffix(" dk")
            self.table.setCellWidget(i, 4, sp_b)
            
            self.rows_data.append({
                "start": tm_s, "end": tm_e, "dur_item": it_dur, "break": sp_b
            })
            
            # Connect live duration updates
            tm_s.timeChanged.connect(lambda _, row=i: self._on_time_modified(row))
            tm_e.timeChanged.connect(lambda _, row=i: self._on_time_modified(row))
            
        main_lay.addWidget(self.table)
        
        # 4. Bottom Buttons
        bot = QHBoxLayout()
        btn_preset_meb = QPushButton("🇹🇷 Standart MEB Şablonu")
        btn_preset_meb.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; color: #334155;")
        btn_preset_meb.clicked.connect(self._apply_meb_preset)
        bot.addWidget(btn_preset_meb)
        
        btn_preset_kurs = QPushButton("🏫 Kurs / Özel Öğretim Şablonu")
        btn_preset_kurs.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; color: #334155;")
        btn_preset_kurs.clicked.connect(self._apply_kurs_preset)
        bot.addWidget(btn_preset_kurs)
        
        bot.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background: white; border: 1px solid #CBD5E1; color: #475569;")
        btn_cancel.clicked.connect(self.reject)
        bot.addWidget(btn_cancel)
        
        btn_save = QPushButton("💾 Zil ve Teneffüsleri Kaydet")
        btn_save.setStyleSheet("background: #16A34A; color: white; border: none; padding: 6px 20px;")
        btn_save.clicked.connect(self._save_and_accept)
        bot.addWidget(btn_save)
        
        main_lay.addLayout(bot)
        
    def _on_time_modified(self, row):
        if row < len(self.rows_data):
            s = self.rows_data[row]["start"].time()
            e = self.rows_data[row]["end"].time()
            diff_mins = (e.hour() * 60 + e.minute()) - (s.hour() * 60 + s.minute())
            if diff_mins > 0:
                self.rows_data[row]["dur_item"].setText(f"{diff_mins} dk")
            else:
                self.rows_data[row]["dur_item"].setText("Geçersiz")
                
    def _auto_calculate_times(self):
        curr = self.tm_start.time()
        l_dur = self.sp_lesson_dur.value()
        b_dur = self.sp_break_dur.value()
        lunch_after = self.cb_lunch_period.currentData()
        lunch_mins = self.sp_lunch_dur.value()
        
        for i, row in enumerate(self.rows_data):
            row["start"].setTime(curr)
            end_t = curr.addSecs(l_dur * 60)
            row["end"].setTime(end_t)
            row["dur_item"].setText(f"{l_dur} dk")
            
            # Determine break
            if i == self.periods - 1:
                row["break"].setValue(0)
            elif lunch_after > 0 and (i + 1) == lunch_after:
                row["break"].setValue(lunch_mins)
                curr = end_t.addSecs(lunch_mins * 60)
            else:
                row["break"].setValue(b_dur)
                curr = end_t.addSecs(b_dur * 60)
                
    def _apply_meb_preset(self):
        self.tm_start.setTime(QTime(8, 30))
        self.sp_lesson_dur.setValue(40)
        self.sp_break_dur.setValue(10)
        if self.periods >= 4:
            self.cb_lunch_period.setCurrentIndex(4) # 4. ders sonrası
        self.sp_lunch_dur.setValue(45)
        self._auto_calculate_times()
        
    def _apply_kurs_preset(self):
        self.tm_start.setTime(QTime(9, 0))
        self.sp_lesson_dur.setValue(45)
        self.sp_break_dur.setValue(15)
        if self.periods >= 4:
            self.cb_lunch_period.setCurrentIndex(4)
        self.sp_lunch_dur.setValue(45)
        self._auto_calculate_times()
        
    def _load_data(self):
        saved = self.data_store.get("settings", {}).get("bell_times", [])
        if saved and len(saved) >= self.periods:
            for i in range(self.periods):
                item = saved[i]
                s_str = item.get("start", "08:30")
                e_str = item.get("end", "09:10")
                b_val = item.get("break_mins", 10)
                
                s_time = QTime.fromString(s_str, "HH:mm") if ":" in s_str else QTime(8, 30)
                e_time = QTime.fromString(e_str, "HH:mm") if ":" in e_str else QTime(9, 10)
                
                if not s_time.isValid(): s_time = QTime(8, 30)
                if not e_time.isValid(): e_time = QTime(9, 10)
                
                self.rows_data[i]["start"].setTime(s_time)
                self.rows_data[i]["end"].setTime(e_time)
                self.rows_data[i]["break"].setValue(int(b_val))
                self._on_time_modified(i)
        else:
            self._apply_meb_preset()
            
    def _save_and_accept(self):
        bell_times = []
        schedule_strs = []
        for i, row in enumerate(self.rows_data):
            s_str = row["start"].time().toString("HH:mm")
            e_str = row["end"].time().toString("HH:mm")
            b_val = row["break"].value()
            bell_times.append({
                "period": i + 1,
                "start": s_str,
                "end": e_str,
                "break_mins": b_val
            })
            schedule_strs.append(f"{s_str}-{e_str}")
            
        settings = self.data_store.setdefault("settings", {})
        settings["bell_times"] = bell_times
        settings["bell_schedule"] = ", ".join(schedule_strs)
        self.data_store["bell_times"] = bell_times
        self.accept()
