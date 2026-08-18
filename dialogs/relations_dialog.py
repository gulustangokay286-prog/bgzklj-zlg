"""
relations_dialog.py – Planlama İlişkileri ve Gelişmiş Ders Bağıntıları Yönetimi
aSc Timetables birebir kopyası – gerçek zamanlı kaydetme ve A* entegrasyonu.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFrame, QCheckBox, QGroupBox, QSpinBox, QListWidget, QAbstractItemView,
    QWidget, QListWidgetItem, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QBrush
from database import trigger_save_db


# ─── Gelişmiş Arama & Çoklu Seçim Popup ──────────────────────────
class MultiSelectDialog(QDialog):
    def __init__(self, items, selected_items, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(360, 480)
        self.setStyleSheet("""
            QDialog { background: #F8FAFC; font-family: 'Segoe UI', sans-serif; }
            QLineEdit { background: white; border: 1px solid #CBD5E1; border-radius: 6px; padding: 6px 10px; font-size: 13px; }
            QLineEdit:focus { border-color: #3B82F6; }
            QListWidget { background: white; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #F1F5F9; }
            QListWidget::item:selected { background: #DBEAFE; color: #1E40AF; font-weight: bold; }
            QPushButton { padding: 6px 14px; border: 1px solid #CBD5E1; border-radius: 6px; background: white; font-weight: bold; font-size: 12px; }
            QPushButton:hover { background: #EFF6FF; border-color: #3B82F6; }
        """)
        self.all_items = list(items)
        self.selected = set(selected_items)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        lbl = QLabel(f"<b>{title}</b>")
        lbl.setStyleSheet("color: #1E293B; font-size: 14px;")
        layout.addWidget(lbl)

        # Hızlı arama filtresi
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Listede ara...")
        self.search_input.textChanged.connect(self._filter_list)
        layout.addWidget(self.search_input)

        # Hızlı seçim butonları
        btn_quick_lay = QHBoxLayout()
        btn_sel_all = QPushButton("✓ Tümünü Seç")
        btn_sel_none = QPushButton("✗ Temizle")
        btn_sel_all.clicked.connect(self._select_all)
        btn_sel_none.clicked.connect(self._select_none)
        btn_quick_lay.addWidget(btn_sel_all)
        btn_quick_lay.addWidget(btn_sel_none)
        layout.addLayout(btn_quick_lay)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.list_widget, 1)

        self._populate_list()

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("✓ Tamam")
        btn_ok.setStyleSheet("background: #2563EB; color: white; border: none; padding: 8px 18px;")
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("padding: 8px 18px;")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _populate_list(self, filter_text=""):
        # Save current selections
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.isSelected():
                self.selected.add(item.text())
            else:
                self.selected.discard(item.text())

        self.list_widget.clear()
        filter_lower = filter_text.strip().lower()

        for item_text in sorted(self.all_items):
            if not filter_lower or filter_lower in item_text.lower():
                list_item = QListWidgetItem(item_text)
                self.list_widget.addItem(list_item)
                if item_text in self.selected:
                    list_item.setSelected(True)

    def _filter_list(self, text):
        self._populate_list(text)

    def _select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setSelected(True)
            self.selected.add(self.list_widget.item(i).text())

    def _select_none(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setSelected(False)
            self.selected.discard(self.list_widget.item(i).text())

    def get_selected(self):
        # Update final selections from list widget
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.isSelected():
                self.selected.add(item.text())
            else:
                self.selected.discard(item.text())
        return sorted(list(self.selected))


# ─── Tek Kural Düzenleme Popup ────────────────────────────────────
class EditRelationDialog(QDialog):
    def __init__(self, data_store, relation_data=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        self.relation_data = relation_data or {}

        self.setWindowTitle("Planlama Kuralı Düzenle")
        self.resize(620, 540)

        self.setStyleSheet("""
            QDialog { background: #F8FAFC; font-family: 'Segoe UI', sans-serif; font-size: 12px; }
            QGroupBox { border: 1px solid #CBD5E1; border-radius: 8px; margin-top: 14px; font-weight: bold; background: white; padding: 12px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 2px 8px; color: #1E293B; font-size: 12px; }
            QPushButton { padding: 6px 14px; border: 1px solid #CBD5E1; background: white; border-radius: 6px; font-weight: bold; font-size: 12px; }
            QPushButton:hover { background: #EFF6FF; border-color: #3B82F6; }
            QComboBox, QSpinBox { border: 1px solid #CBD5E1; padding: 5px 10px; background: white; border-radius: 6px; font-size: 12px; }
            QLabel { color: #334155; font-size: 12px; }
        """)

        self.selected_subjects = []
        self.selected_teachers = []
        self.selected_classes = []

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Kural Seçimi
        grp_rule = QGroupBox("Kural Seçimi")
        rule_lay = QVBoxLayout(grp_rule)

        self.cb_rule = QComboBox()
        self.rules = [
            "Günde maksimum ders sayısı",
            "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun",
            "Aynı ders aynı gün tekrar etmesin",
            "Dersler haftanın günlerine eşit dağıtılsın",
            "Seçilen dersler aynı gün peş peşe gelsin",
            "İki ders aynı güne gelmesin",
            "Öğretmenin dersleri öğleden önce toplansın",
            "Öğretmenin dersleri öğleden sonra toplansın",
            "Son ders saatine zor ders konulmasın",
            "X dersi belirli saatlerde kalmalı",
            "İki zor ders art arda gelmesin",
        ]
        self.cb_rule.addItems(self.rules)
        self.cb_rule.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E40AF;")
        self.cb_rule.currentIndexChanged.connect(self._rule_changed)
        rule_lay.addWidget(self.cb_rule)
        main_layout.addWidget(grp_rule)

        # Filtreler
        grp_filters = QGroupBox("Uygulanacak Filtreler")
        filter_layout = QVBoxLayout(grp_filters)
        filter_layout.setSpacing(10)

        # Dersler
        lay_subj = QHBoxLayout()
        lbl_s = QLabel("Dersler:")
        lbl_s.setFixedWidth(80)
        lay_subj.addWidget(lbl_s)
        self.cb_subj = QComboBox()
        self.cb_subj.setSizePolicy(self.cb_subj.sizePolicy().Policy.Expanding, self.cb_subj.sizePolicy().Policy.Fixed)
        self.cb_subj.currentIndexChanged.connect(self._on_subj_combo_changed)
        self.btn_subj = QPushButton("Seç")
        self.btn_subj.setFixedWidth(70)
        self.btn_subj.clicked.connect(self._change_subjects)
        lay_subj.addWidget(self.cb_subj)
        lay_subj.addWidget(self.btn_subj)
        filter_layout.addLayout(lay_subj)

        # Öğretmenler
        lay_teach = QHBoxLayout()
        lbl_t = QLabel("Öğretmenler:")
        lbl_t.setFixedWidth(80)
        lay_teach.addWidget(lbl_t)
        self.cb_teach = QComboBox()
        self.cb_teach.setSizePolicy(self.cb_teach.sizePolicy().Policy.Expanding, self.cb_teach.sizePolicy().Policy.Fixed)
        self.cb_teach.currentIndexChanged.connect(self._on_teach_combo_changed)
        self.btn_teach = QPushButton("Seç")
        self.btn_teach.setFixedWidth(70)
        self.btn_teach.clicked.connect(self._change_teachers)
        lay_teach.addWidget(self.cb_teach)
        lay_teach.addWidget(self.btn_teach)
        filter_layout.addLayout(lay_teach)

        # Sınıflar
        lay_class = QHBoxLayout()
        lbl_c = QLabel("Sınıflar:")
        lbl_c.setFixedWidth(80)
        lay_class.addWidget(lbl_c)
        self.cb_class = QComboBox()
        self.cb_class.setSizePolicy(self.cb_class.sizePolicy().Policy.Expanding, self.cb_class.sizePolicy().Policy.Fixed)
        self.cb_class.currentIndexChanged.connect(self._on_class_combo_changed)
        self.btn_class = QPushButton("Seç")
        self.btn_class.setFixedWidth(70)
        self.btn_class.clicked.connect(self._change_classes)
        lay_class.addWidget(self.cb_class)
        lay_class.addWidget(self.btn_class)
        filter_layout.addLayout(lay_class)
        main_layout.addWidget(grp_filters)

        # Parametreler
        grp_param = QGroupBox("Parametre Ayarları")
        param_lay = QHBoxLayout(grp_param)
        self.lbl_param = QLabel("Maksimum günlük ders saati:")
        self.spin_param = QSpinBox()
        self.spin_param.setRange(1, 15)
        self.spin_param.setValue(2)
        param_lay.addWidget(self.lbl_param)
        param_lay.addWidget(self.spin_param)

        self.lbl_period = QLabel("Saat aralığı (örn: 1-4):")
        self.cb_period_start = QSpinBox()
        self.cb_period_start.setRange(1, 12)
        self.cb_period_start.setValue(1)
        self.cb_period_end = QSpinBox()
        self.cb_period_end.setRange(1, 12)
        self.cb_period_end.setValue(4)
        param_lay.addWidget(self.lbl_period)
        param_lay.addWidget(self.cb_period_start)
        param_lay.addWidget(QLabel("-"))
        param_lay.addWidget(self.cb_period_end)

        param_lay.addStretch()
        self.param_group = grp_param
        main_layout.addWidget(grp_param)

        # Önem
        grp_imp = QGroupBox("Önem Derecesi")
        imp_lay = QHBoxLayout(grp_imp)
        self.cb_imp = QComboBox()
        self.cb_imp.addItems(["Sıkı (Kesinlikle uygulanmalı)", "Yüksek", "Normal", "Düşük (Mümkünse)"])
        self.cb_imp.setCurrentIndex(0)
        imp_lay.addWidget(self.cb_imp)
        main_layout.addWidget(grp_imp)

        main_layout.addStretch(1)

        # Alt butonlar
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("✓ Kaydet")
        self.btn_ok.setStyleSheet("background: #2563EB; color: white; border: none; padding: 8px 22px; font-size: 13px; font-weight: bold; border-radius: 6px;")
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setStyleSheet("padding: 8px 22px; font-size: 13px; font-weight: bold;")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

        self._refresh_combos_ui()

    def _refresh_combos_ui(self):
        # 1. Dersler
        self.cb_subj.blockSignals(True)
        self.cb_subj.clear()
        self.cb_subj.addItem("Tüm dersler")
        if self.selected_subjects:
            txt = f"Seçili ({len(self.selected_subjects)} ders): {', '.join(self.selected_subjects[:3])}{'...' if len(self.selected_subjects) > 3 else ''}"
            self.cb_subj.addItem(txt)
            self.cb_subj.setCurrentIndex(1)
        else:
            self.cb_subj.addItem("Seçili dersler...")
            self.cb_subj.setCurrentIndex(0)
        self.cb_subj.blockSignals(False)

        # 2. Öğretmenler
        self.cb_teach.blockSignals(True)
        self.cb_teach.clear()
        self.cb_teach.addItem("Tüm öğretmenler")
        if self.selected_teachers:
            txt = f"Seçili ({len(self.selected_teachers)} öğretmen): {', '.join(self.selected_teachers[:3])}{'...' if len(self.selected_teachers) > 3 else ''}"
            self.cb_teach.addItem(txt)
            self.cb_teach.setCurrentIndex(1)
        else:
            self.cb_teach.addItem("Seçili öğretmenler...")
            self.cb_teach.setCurrentIndex(0)
        self.cb_teach.blockSignals(False)

        # 3. Sınıflar
        self.cb_class.blockSignals(True)
        self.cb_class.clear()
        self.cb_class.addItem("Tüm sınıflar")
        if self.selected_classes:
            txt = f"Seçili ({len(self.selected_classes)} sınıf): {', '.join(self.selected_classes[:3])}{'...' if len(self.selected_classes) > 3 else ''}"
            self.cb_class.addItem(txt)
            self.cb_class.setCurrentIndex(1)
        else:
            self.cb_class.addItem("Seçili sınıflar...")
            self.cb_class.setCurrentIndex(0)
        self.cb_class.blockSignals(False)

    def _on_subj_combo_changed(self, idx):
        if idx == 1 and not self.selected_subjects:
            self._change_subjects()

    def _on_teach_combo_changed(self, idx):
        if idx == 1 and not self.selected_teachers:
            self._change_teachers()

    def _on_class_combo_changed(self, idx):
        if idx == 1 and not self.selected_classes:
            self._change_classes()

    def _rule_changed(self):
        rule = self.cb_rule.currentText()
        show_max = rule in ["Günde maksimum ders sayısı", "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun"]
        show_period = rule == "X dersi belirli saatlerde kalmalı"

        if rule == "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun":
            self.lbl_param.setText("Maksimum günlük ders saati:")
            self.spin_param.setValue(2)
            if not self.selected_subjects:
                def is_practical(name):
                    norm = str(name).replace("i", "İ").replace("ı", "I").upper()
                    return any(k in norm for k in ["BEDEN", "MÜZ", "MUZ", "GÖR", "GOR", "RES", "SANAT", "SPOR", "UYGULAMA", "ATÖLYE", "ATOLYE"])
                practical = []
                for d in self.data_store.get("dersler", []):
                    if is_practical(d.get("ad", "")):
                        practical.append(d.get("ad", ""))
                for a in self.data_store.get("atamalar", []):
                    if is_practical(a.get("subject", "")) and a.get("subject") not in practical:
                        practical.append(a.get("subject"))
                if practical:
                    self.selected_subjects = practical
                    self._refresh_combos_ui()
        elif rule == "Günde maksimum ders sayısı":
            self.lbl_param.setText("Maksimum günlük ders saati:")
            if self.spin_param.value() > 4:
                self.spin_param.setValue(2)

        self.lbl_param.setVisible(show_max)
        self.spin_param.setVisible(show_max)
        self.lbl_period.setVisible(show_period)
        self.cb_period_start.setVisible(show_period)
        self.cb_period_end.setVisible(show_period)

        for i in range(self.param_group.layout().count()):
            w = self.param_group.layout().itemAt(i).widget()
            if isinstance(w, QLabel) and w.text() == "-":
                w.setVisible(show_period)

        self.param_group.setVisible(show_max or show_period)

    def _change_subjects(self):
        items_set = set()
        for d in self.data_store.get("dersler", []):
            if d.get("ad"): items_set.add(d.get("ad"))
        for a in self.data_store.get("atamalar", []):
            if a.get("subject"): items_set.add(a.get("subject"))
        items = sorted(list(items_set))
        if not items:
            items = ["Matematik", "Türkçe", "Fizik", "Kimya", "Biyoloji", "Beden Eğitimi", "İngilizce", "Görsel Sanatlar", "Müzik"]

        d = MultiSelectDialog(items, self.selected_subjects, "Dersleri Seç", self)
        if d.exec():
            self.selected_subjects = d.get_selected()
            self._refresh_combos_ui()

    def _change_teachers(self):
        items_set = set()
        for t in self.data_store.get("ogretmenler", []):
            if t.get("ad"): items_set.add(t.get("ad"))
        for a in self.data_store.get("atamalar", []):
            if a.get("teacher") and a.get("teacher") not in ["—", "Atanmadı"]: items_set.add(a.get("teacher"))
        items = sorted(list(items_set))

        d = MultiSelectDialog(items, self.selected_teachers, "Öğretmenleri Seç", self)
        if d.exec():
            self.selected_teachers = d.get_selected()
            self._refresh_combos_ui()

    def _change_classes(self):
        items_set = set()
        for s in self.data_store.get("siniflar", []):
            if s.get("ad"): items_set.add(s.get("ad"))
        for a in self.data_store.get("atamalar", []):
            if a.get("class"): items_set.add(a.get("class"))
        items = sorted(list(items_set))

        d = MultiSelectDialog(items, self.selected_classes, "Sınıfları Seç", self)
        if d.exec():
            self.selected_classes = d.get_selected()
            self._refresh_combos_ui()

    def _load_data(self):
        if self.relation_data:
            rule_text = self.relation_data.get("kural", "")
            idx = self.cb_rule.findText(rule_text)
            if idx >= 0:
                self.cb_rule.setCurrentIndex(idx)

            self.selected_subjects = list(self.relation_data.get("dersler", []))
            self.selected_teachers = list(self.relation_data.get("ogretmenler", []))
            self.selected_classes = list(self.relation_data.get("siniflar", []))

            self.spin_param.setValue(self.relation_data.get("parametre") or 2)
            self.cb_period_start.setValue(self.relation_data.get("period_start") or 1)
            self.cb_period_end.setValue(self.relation_data.get("period_end") or 4)

            imp = self.relation_data.get("onem", "Sıkı (Kesinlikle uygulanmalı)")
            idx_imp = self.cb_imp.findText(imp)
            if idx_imp >= 0:
                self.cb_imp.setCurrentIndex(idx_imp)

        self._refresh_combos_ui()
        self._rule_changed()

    def get_data(self):
        rule = self.cb_rule.currentText()
        has_param = rule in ["Günde maksimum ders sayısı", "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun"]
        has_period = rule == "X dersi belirli saatlerde kalmalı"
        return {
            "aktif": self.relation_data.get("aktif", True),
            "kural": rule,
            "dersler": self.selected_subjects if self.cb_subj.currentIndex() == 1 else [],
            "ogretmenler": self.selected_teachers if self.cb_teach.currentIndex() == 1 else [],
            "siniflar": self.selected_classes if self.cb_class.currentIndex() == 1 else [],
            "parametre": self.spin_param.value() if has_param else None,
            "period_start": self.cb_period_start.value() if has_period else None,
            "period_end": self.cb_period_end.value() if has_period else None,
            "onem": self.cb_imp.currentText()
        }


# ─── Ana Planlama İlişkileri Yöneticisi ──────────────────────────
class PlanningRelationsDialog(QDialog):
    def __init__(self, data_store=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        if "planlama_iliskileri" not in self.data_store:
            self.data_store["planlama_iliskileri"] = []

        self.setWindowTitle("Planlama İlişkileri — Ders Kısıtlamaları ve Kurallar")
        self.resize(920, 580)
        self.setStyleSheet("""
            QDialog { background: #F8FAFC; font-family: 'Segoe UI', sans-serif; }
            QTableWidget { background: white; border: 1px solid #CBD5E1; border-radius: 8px; gridline-color: #F1F5F9; font-size: 12px; }
            QHeaderView::section { background: #F1F5F9; border: none; border-bottom: 2px solid #CBD5E1; padding: 8px; font-weight: bold; font-size: 12px; color: #334155; }
            QPushButton { padding: 7px 16px; border: 1px solid #CBD5E1; background: white; border-radius: 6px; font-weight: bold; font-size: 12px; }
            QPushButton:hover { background: #EFF6FF; border-color: #3B82F6; }
        """)
        self._build_ui()
        self._load_table()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Başlık
        lbl_title = QLabel("📋 Planlama İlişkileri ve Gelişmiş Bağıntılar")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E293B;")
        main_layout.addWidget(lbl_title)

        lbl_desc = QLabel("Otomatik ve manuel planlama sırasında uygulanacak kuralları buradan yönetebilirsiniz. Aktif kurallar anında veritabanına kaydedilir ve A* algoritmasında öncelikli olarak uygulanır.")
        lbl_desc.setStyleSheet("color: #64748B; font-size: 12px;")
        lbl_desc.setWordWrap(True)
        main_layout.addWidget(lbl_desc)

        # Tablo
        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(["Aktif", "Kural", "Dersler", "Sınıflar", "Öğretmenler", "Önem"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 140)
        self.table.setColumnWidth(5, 110)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.itemDoubleClicked.connect(self._edit_relation)
        self.table.itemChanged.connect(self._on_checkbox_changed)
        main_layout.addWidget(self.table, 1)

        # Özet
        self.lbl_summary = QLabel()
        self.lbl_summary.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500;")
        main_layout.addWidget(self.lbl_summary)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_add = QPushButton("+ Kural Ekle")
        btn_add.setStyleSheet("background: #2563EB; color: white; border: none; padding: 8px 18px;")
        btn_add.clicked.connect(self._add_relation)

        btn_edit = QPushButton("✏️ Düzenle")
        btn_edit.clicked.connect(self._edit_relation_btn)

        btn_del = QPushButton("🗑️ Sil")
        btn_del.setStyleSheet("color: #DC2626; border-color: #FECACA;")
        btn_del.clicked.connect(self._del_relation)

        btn_toggle = QPushButton("Tümünü Aktifleştir / Kapat")
        btn_toggle.clicked.connect(self._toggle_all)

        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_del)
        btn_row.addWidget(btn_toggle)
        btn_row.addStretch(1)

        btn_close = QPushButton("Kapat ve Kaydet")
        btn_close.setStyleSheet("background: #16A34A; color: white; border: none; padding: 8px 20px;")
        btn_close.clicked.connect(self._close_and_save)
        btn_row.addWidget(btn_close)

        main_layout.addLayout(btn_row)

    def _load_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        items = self.data_store.get("planlama_iliskileri", [])

        active_count = 0
        for idx, item in enumerate(items):
            self.table.insertRow(idx)

            # Checkbox using widget for perfect centering and avoiding the extra square bug
            chk_widget = QWidget()
            chk_lay = QHBoxLayout(chk_widget)
            chk_lay.setContentsMargins(0, 0, 0, 0)
            chk_lay.setAlignment(Qt.AlignCenter)
            chk_box = QCheckBox()
            is_active = item.get("aktif", True)
            chk_box.setChecked(is_active)
            chk_box.stateChanged.connect(lambda state, r=idx: self._on_widget_checkbox_changed(r, state))
            chk_lay.addWidget(chk_box)
            self.table.setCellWidget(idx, 0, chk_widget)
            
            # Keep a dummy item for sorting/selection
            dummy_item = QTableWidgetItem()
            dummy_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(idx, 0, dummy_item)
            if is_active:
                active_count += 1

            # Kural metni
            kural_text = item.get("kural", "")
            if item.get("parametre"):
                kural_text += f" (maks: {item['parametre']} saat)"
            if item.get("period_start") and item.get("period_end"):
                kural_text += f" ({item['period_start']}.–{item['period_end']}. saat)"
            kural_item = QTableWidgetItem(kural_text)
            if not is_active:
                kural_item.setForeground(QBrush(QColor("#94A3B8")))
            else:
                kural_item.setForeground(QBrush(QColor("#1E293B")))
                kural_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(idx, 1, kural_item)

            # Dersler
            subj = item.get("dersler", [])
            subj_item = QTableWidgetItem(", ".join(subj) if subj else "Tüm dersler")
            if not subj:
                subj_item.setForeground(QBrush(QColor("#94A3B8")))
            self.table.setItem(idx, 2, subj_item)

            # Sınıflar
            cls = item.get("siniflar", [])
            cls_item = QTableWidgetItem(", ".join(cls) if cls else "Tüm sınıflar")
            if not cls:
                cls_item.setForeground(QBrush(QColor("#94A3B8")))
            self.table.setItem(idx, 3, cls_item)

            # Öğretmenler
            teach = item.get("ogretmenler", [])
            teach_item = QTableWidgetItem(", ".join(teach) if teach else "Tüm öğretmenler")
            if not teach:
                teach_item.setForeground(QBrush(QColor("#94A3B8")))
            self.table.setItem(idx, 4, teach_item)

            # Önem
            onem = item.get("onem", "Sıkı")
            color_map = {"Sıkı": "#DC2626", "Yüksek": "#D97706", "Normal": "#2563EB", "Düşük": "#64748B"}
            onem_short = onem.split("(")[0].strip() if "(" in onem else onem
            onem_item = QTableWidgetItem(onem_short)
            onem_item.setForeground(QBrush(QColor(color_map.get(onem_short, "#334155"))))
            onem_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(idx, 5, onem_item)

        self.table.blockSignals(False)
        total = len(items)
        self.lbl_summary.setText(f"Toplam {total} kural tanımlı, {active_count} aktif")

    def _on_widget_checkbox_changed(self, row, state):
        relations = self.data_store.get("planlama_iliskileri", [])
        if 0 <= row < len(relations):
            is_active = (state == Qt.Checked)
            relations[row]["aktif"] = is_active

            kural_item = self.table.item(row, 1)
            if kural_item:
                if is_active:
                    kural_item.setForeground(QBrush(QColor("#1E293B")))
                    kural_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                else:
                    kural_item.setForeground(QBrush(QColor("#94A3B8")))
                    kural_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal))

            active_count = sum(1 for r in relations if r.get("aktif", True))
            self.lbl_summary.setText(f"Toplam {len(relations)} kural tanımlı, {active_count} aktif")
            self._save()

    def _on_checkbox_changed(self, item):
        pass

    def _add_relation(self):
        d = EditRelationDialog(self.data_store, parent=self)
        if d.exec():
            new_data = d.get_data()
            if "planlama_iliskileri" not in self.data_store:
                self.data_store["planlama_iliskileri"] = []
            self.data_store["planlama_iliskileri"].append(new_data)
            self._save()
            self._load_table()

    def _edit_relation_btn(self):
        r = self.table.currentRow()
        if r >= 0:
            self._edit_relation(self.table.item(r, 1))

    def _edit_relation(self, item):
        if not item:
            return
        r = item.row()
        relations = self.data_store.get("planlama_iliskileri", [])
        if r >= len(relations):
            return
        rel_data = relations[r]
        d = EditRelationDialog(self.data_store, relation_data=rel_data, parent=self)
        if d.exec():
            updated_data = d.get_data()
            self.data_store["planlama_iliskileri"][r] = updated_data
            self._save()
            self._load_table()

    def _del_relation(self):
        r = self.table.currentRow()
        if r >= 0:
            resp = QMessageBox.question(self, "Kuralı Sil", "Bu kuralı silmek istediğinize emin misiniz?",
                                         QMessageBox.Yes | QMessageBox.No)
            if resp == QMessageBox.Yes:
                self.data_store["planlama_iliskileri"].pop(r)
                self._save()
                self._load_table()

    def _toggle_all(self):
        relations = self.data_store.get("planlama_iliskileri", [])
        all_active = all(r.get("aktif", True) for r in relations)
        new_state = not all_active
        for r in relations:
            r["aktif"] = new_state

        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked if new_state else Qt.Unchecked)
            kural_item = self.table.item(row, 1)
            if kural_item:
                if new_state:
                    kural_item.setForeground(QBrush(QColor("#1E293B")))
                    kural_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                else:
                    kural_item.setForeground(QBrush(QColor("#94A3B8")))
                    kural_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal))
        self.table.blockSignals(False)

        active_count = len(relations) if new_state else 0
        self.lbl_summary.setText(f"Toplam {len(relations)} kural tanımlı, {active_count} aktif")
        self._save()

    def _close_and_save(self):
        self._save()
        self.accept()

    def _save(self):
        # Gerçek zamanlı veritabanına kaydet
        trigger_save_db(self, self.data_store)

        # Ana pencereye bildir
        p = self.parent()
        while p:
            if hasattr(p, "save_db"):
                p.save_db()
                break
            p = p.parent()
