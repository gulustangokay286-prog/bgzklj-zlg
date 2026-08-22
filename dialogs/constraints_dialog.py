"""
constraints_dialog.py – Öğretmen, Sınıf ve Pedagojik Ders Kısıtlama Diyaloğu
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QTabWidget, QWidget, QCheckBox, QFrame, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QBrush

DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]

class ConstraintsDialog(QDialog):
    def __init__(self, data_store=None, target_type="ogretmen", parent=None, preselected_name=""):
        super().__init__(parent)
        self.data_store = data_store if data_store is not None else {}
        self.target_type = target_type  # "ogretmen" veya "sinif"
        self.preselected_name = preselected_name
        
        # Gün/saat boyutları Zaman Tablosu ekranıyla ORTAK kaynaktan gelir; ikisi
        # farklı hesaplarsa matrisler kayar ve ekranlar birbirini ezer.
        import constraint_sync
        self._cs = constraint_sync
        self.days = constraint_sync.day_names(self.data_store)
        self.day_count, self.periods = constraint_sync.grid_dimensions(self.data_store)

        # Düzenlenen matrisler hafızada tutulur; yalnızca "Kaydet ve Uygula" ile yazılır,
        # böylece sadece ekranı açıp gezinmek veriye dokunmaz (eski davranış yazıyordu).
        self._matrices = {}

        self.setWindowTitle("Gelişmiş Planlama ve Zaman Kısıtlamaları")
        self.resize(840, 600)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; }
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 6px; }
            QTabBar::tab { background: #E2E8F0; padding: 8px 18px; margin-right: 2px; font-weight: bold; color: #475569; }
            QTabBar::tab:selected { background: #FFFFFF; color: #2563EB; border-top: 2px solid #2563EB; }
            QLabel { color: #1E293B; font-size: 13px; }
            QTableWidget { border: 1px solid #CBD5E1; gridline-color: #E2E8F0; font-size: 12px; }
            QPushButton { min-height: 30px; padding: 4px 14px; border-radius: 6px; font-weight: bold; }
        """)
        
        if "kisitlamalar" not in self.data_store:
            self.data_store["kisitlamalar"] = {}
        if "constraints" not in self.data_store:
            self.data_store["constraints"] = {
                "no_consecutive_hard": True,
                "max_daily_same_subject": 2,
                "limit_teacher_gaps": True,
                "subject_windows": {}
            }
            
        self._build_ui()
        self._populate_combo()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        self.tabs = QTabWidget()
        
        # TAB 1: Zaman Müsaitlik Matrisi
        tab1 = QWidget()
        t1_lay = QVBoxLayout(tab1)
        t1_lay.setContentsMargins(12, 12, 12, 12)
        t1_lay.setSpacing(10)
        
        # Header Target Combo
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Seçilen Kişi / Birim:"))
        
        self.combo_target = QComboBox()
        self.combo_target.setMinimumWidth(240)
        self.combo_target.currentIndexChanged.connect(self._on_target_changed)
        header_layout.addWidget(self.combo_target)
        
        header_layout.addStretch(1)
        
        btn_clear_all = QPushButton("Tümünü Uygun Yap (✓)")
        btn_clear_all.setStyleSheet("background: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7;")
        btn_clear_all.clicked.connect(self._make_all_available)
        header_layout.addWidget(btn_clear_all)
        t1_lay.addLayout(header_layout)
        
        hint = QLabel("💡 İpucu: Hücreye tıklayarak durumu değiştirin (Yeşil ✓ Müsait → Kırmızı ✗ Kapalı → Sarı ? Tercih Edilmez).<br>"
                      "Bu ekran <b>Zaman Tablosu</b> ekranıyla tamamen aynı veriyi kullanır; birinde yaptığınız değişiklik diğerine de yansır.")
        hint.setStyleSheet("color: #64748B; font-style: italic; font-size: 11px;")
        t1_lay.addWidget(hint)
        
        # Table Grid
        self.table = QTableWidget(self.periods, len(self.days))
        self.table.setHorizontalHeaderLabels(self.days)
        self.table.setVerticalHeaderLabels([f"{i+1}. Ders" for i in range(self.periods)])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellClicked.connect(self._on_cell_clicked)
        t1_lay.addWidget(self.table, 1)
        
        # Quick Day Buttons Bar
        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("Hızlı Gün Kapat:"))
        for d_idx, d_name in enumerate(self.days):
            btn_day = QPushButton(f"{d_name} Kapat")
            btn_day.setStyleSheet("background: #FFEBEE; color: #C62828; border: 1px solid #FFCDD2; font-size: 11px;")
            btn_day.clicked.connect(lambda ch, idx=d_idx: self._toggle_entire_day(idx, False))
            quick_layout.addWidget(btn_day)
        quick_layout.addStretch(1)
        t1_lay.addLayout(quick_layout)
        
        self.tabs.addTab(tab1, "🕒 Zaman Müsaitlik Matrisi")
        
        # TAB 2: Gelişmiş Pedagojik Kurallar
        tab2 = QWidget()
        t2_lay = QVBoxLayout(tab2)
        t2_lay.setContentsMargins(16, 16, 16, 16)
        t2_lay.setSpacing(14)
        
        grp_pedagogic = QGroupBox("🧠 Pedagojik Dağılım ve Sağlık Kuralları")
        grp_pedagogic.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #CBD5E1; border-radius: 6px; margin-top: 10px; padding-top: 10px; }")
        v_ped = QVBoxLayout(grp_pedagogic)
        v_ped.setSpacing(10)
        
        cur_c = self.data_store.get("constraints", {})
        
        self.chk_no_consecutive_hard = QCheckBox("✅ İki zor ders (Matematik, Fizik, Kimya, Biyoloji, Geometri vb.) aynı gün art arda gelmesin")
        self.chk_no_consecutive_hard.setChecked(cur_c.get("no_consecutive_hard", True))
        v_ped.addWidget(self.chk_no_consecutive_hard)
        
        self.chk_limit_gaps = QCheckBox("✅ Öğretmenlerin haftalık programında boş saatler (pencere) minimize edilsin")
        self.chk_limit_gaps.setChecked(cur_c.get("limit_teacher_gaps", True))
        v_ped.addWidget(self.chk_limit_gaps)
        
        self.chk_max_daily = QCheckBox("✅ Bir günde aynı dersten en fazla 2 saat blok ders yerleştirilsin")
        self.chk_max_daily.setChecked(cur_c.get("max_daily_same_subject", 2) == 2)
        v_ped.addWidget(self.chk_max_daily)
        
        t2_lay.addWidget(grp_pedagogic)
        
        # Subject Time Window Settings
        grp_subjs = QGroupBox("🎯 Ders Bazlı Saat Tercihi (X Dersi Sabah / Öğle Saatlerine Yerleşsin)")
        grp_subjs.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #CBD5E1; border-radius: 6px; margin-top: 10px; padding-top: 10px; }")
        v_subjs = QVBoxLayout(grp_subjs)
        
        self.tbl_subj_pref = QTableWidget(0, 2)
        self.tbl_subj_pref.setHorizontalHeaderLabels(["Ders Adı", "Öncelikli Yerleşim Zamanı"])
        self.tbl_subj_pref.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_subj_pref.setColumnWidth(1, 240)
        
        all_subjs = sorted([d.get("ad", "") for d in self.data_store.get("dersler", []) if d.get("ad")])
        saved_windows = cur_c.get("subject_windows", {})
        
        for subj in all_subjs:
            row = self.tbl_subj_pref.rowCount()
            self.tbl_subj_pref.insertRow(row)
            self.tbl_subj_pref.setItem(row, 0, QTableWidgetItem(subj))
            
            cb_win = QComboBox()
            cb_win.wheelEvent = lambda event: event.ignore()
            cb_win.addItems(["Fark Etmez (Esnek)", "Sabah Saatleri (1-4. Saatler)", "Öğleden Sonra Saatleri"])
            saved_pref = saved_windows.get(subj, "any")
            if saved_pref == "morning":
                cb_win.setCurrentIndex(1)
            elif saved_pref == "afternoon":
                cb_win.setCurrentIndex(2)
            else:
                cb_win.setCurrentIndex(0)
            self.tbl_subj_pref.setCellWidget(row, 1, cb_win)
            
        v_subjs.addWidget(self.tbl_subj_pref)
        t2_lay.addWidget(grp_subjs)
        
        self.tabs.addTab(tab2, "⚙️ Gelişmiş Pedagojik Ayarlar")
        layout.addWidget(self.tabs, 1)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("💾 Kaydet ve Uygula")
        btn_save.setStyleSheet("background: #2563EB; color: white; border: none; padding: 8px 22px;")
        btn_save.clicked.connect(self._save_and_accept)
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; color: #475569; padding: 8px 20px;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch(1)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _populate_combo(self):
        self.combo_target.blockSignals(True)
        self.combo_target.clear()
        
        key = "ogretmenler" if self.target_type == "ogretmen" else "siniflar"
        items = sorted([item.get("ad", "") for item in self.data_store.get(key, []) if item.get("ad")])
        for name in items:
            self.combo_target.addItem(name)
            
        if self.preselected_name and self.preselected_name in items:
            self.combo_target.setCurrentText(self.preselected_name)
            
        self.combo_target.blockSignals(False)
        self._load_matrix_for_current()

    def _on_target_changed(self):
        self._load_matrix_for_current()

    def _get_current_name(self):
        return self.combo_target.currentText()

    def _entity_for(self, name):
        key = "ogretmenler" if self.target_type == "ogretmen" else "siniflar"
        return next((item for item in self.data_store.get(key, []) if item.get("ad") == name), None)

    def _matrix_for(self, name):
        """Bu birimin düzenlenmekte olan matrisi (ilk erişimde ortak kaynaktan yüklenir)."""
        if name not in self._matrices:
            entity = self._entity_for(name) or {}
            self._matrices[name] = self._cs.get_matrix(entity, name, self.data_store)
        return self._matrices[name]

    def _load_matrix_for_current(self):
        name = self._get_current_name()
        if not name:
            return
        matrix = self._matrix_for(name)
        for p in range(self.periods):
            for d in range(len(self.days)):
                self._set_cell_state(p, d, matrix[d][p], store=False)

    def _set_cell_state(self, row, col, state, store=True):
        """row = ders saati (period), col = gün. state: 2 açık / 1 tercih edilmez / 0 kapalı."""
        state = self._cs._coerce_state(state)

        item = QTableWidgetItem()
        item.setTextAlignment(Qt.AlignCenter)
        item.setFont(QFont("Arial", 10, QFont.Bold))

        if state == self._cs.OPEN:
            item.setText("✓ Müsait")
            item.setBackground(QBrush(QColor("#E8F5E9")))
            item.setForeground(QBrush(QColor("#2E7D32")))
        elif state == self._cs.CLOSED:
            item.setText("✗ KAPALI")
            item.setBackground(QBrush(QColor("#FFEBEE")))
            item.setForeground(QBrush(QColor("#C62828")))
        else:
            item.setText("? Tercih Edilmez")
            item.setBackground(QBrush(QColor("#FEF9C3")))
            item.setForeground(QBrush(QColor("#A16207")))

        self.table.setItem(row, col, item)

        if store:
            name = self._get_current_name()
            if name:
                self._matrix_for(name)[col][row] = state

    def _on_cell_clicked(self, row, col):
        name = self._get_current_name()
        if not name:
            return
        # Zaman Tablosu ekranıyla aynı döngü: ✓ -> ✗ -> ? -> ✓
        current = self._matrix_for(name)[col][row]
        if current == self._cs.OPEN:
            new_state = self._cs.CLOSED
        elif current == self._cs.CLOSED:
            new_state = self._cs.AVOID
        else:
            new_state = self._cs.OPEN
        self._set_cell_state(row, col, new_state)

    def _toggle_entire_day(self, day_idx, target_state):
        state = self._cs.OPEN if target_state else self._cs.CLOSED
        for p in range(self.periods):
            self._set_cell_state(p, day_idx, state)

    def _make_all_available(self):
        for p in range(self.periods):
            for d in range(len(self.days)):
                self._set_cell_state(p, d, self._cs.OPEN)

    def _save_and_accept(self):
        # Save pedagogical settings
        c = self.data_store.setdefault("constraints", {})
        c["no_consecutive_hard"] = self.chk_no_consecutive_hard.isChecked()
        c["limit_teacher_gaps"] = self.chk_limit_gaps.isChecked()
        c["max_daily_same_subject"] = 2 if self.chk_max_daily.isChecked() else 4
        
        sub_windows = {}
        for r in range(self.tbl_subj_pref.rowCount()):
            s_name = self.tbl_subj_pref.item(r, 0).text()
            cb = self.tbl_subj_pref.cellWidget(r, 1)
            if cb:
                idx = cb.currentIndex()
                if idx == 1:
                    sub_windows[s_name] = "morning"
                elif idx == 2:
                    sub_windows[s_name] = "afternoon"
        c["subject_windows"] = sub_windows

        # Yalnızca bu ekranda GERÇEKTEN düzenlenen birimler yazılır. Eskiden burası
        # kisitlamalar sözlüğündeki her birimin timeoff'unu bool'lardan yeniden
        # üretiyordu; bu, 3 durumlu "? tercih edilmez" işaretlerini sessizce "açık"a
        # çeviriyor ve dokunulmamış birimlerin verisini eziyordu.
        for name, matrix in self._matrices.items():
            entity = self._entity_for(name)
            if entity is not None:
                self._cs.set_matrix(entity, name, self.data_store, matrix)

        # Kalan birimlerin iki gösterimini de hizada tut (eski kayıtları onarır).
        self._cs.sync_all(self.data_store)

        if self.target_type == "ogretmen":
            try:
                inst_slug = self.data_store.get("settings", {}).get("institution_slug")
                if not inst_slug:
                    import version_store
                    inst_slug = version_store.get_last_active_institution_slug()
                if inst_slug:
                    self._cs.publish(inst_slug, self.data_store)
            except Exception as e:
                print(f"[CONSTRAINTS_SAVE_ERR] global publish failed: {e}")

        self.accept()
