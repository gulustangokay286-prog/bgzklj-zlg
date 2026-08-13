"""
relations_dialog.py – Planlama İlişkileri ve Gelişmiş Ders Bağıntıları Yönetimi
aSc Timetables birebir kopyası.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFrame, QCheckBox, QGroupBox, QSpinBox, QListWidget, QAbstractItemView, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

class MultiSelectDialog(QDialog):
    def __init__(self, items, selected_items, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(300, 400)
        self.items = items
        self.selected = list(selected_items)
        
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
        
        for item in self.items:
            list_item = QListWidget()
            # We just add items and set selected
            self.list_widget.addItem(item)
            
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.text() in self.selected:
                item.setSelected(True)
                
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Tamam")
        btn_cancel = QPushButton("İptal")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
    def get_selected(self):
        return [item.text() for item in self.list_widget.selectedItems()]


class EditRelationDialog(QDialog):
    def __init__(self, data_store, relation_data=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store
        self.relation_data = relation_data or {}
        
        self.setWindowTitle("Dersler arasındaki gelişmiş planlama ilişkileri")
        self.resize(600, 500)
        
        self.setStyleSheet("""
            QDialog { background-color: #F0F0F0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 12px; }
            QGroupBox { border: 1px solid #B0B0B0; margin-top: 2ex; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; }
            QPushButton { padding: 4px 12px; border: 1px solid #ADADAD; background: #E1E1E1; border-radius: 3px; }
            QPushButton:hover { background: #E5F1FB; border: 1px solid #0078D7; }
            QComboBox, QSpinBox { border: 1px solid #ADADAD; padding: 2px; background: white; }
        """)
        
        self._build_ui()
        self._load_data()
        
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Top Rule Selection
        lbl_rule = QLabel("Aşağıdaki kuralı uygula:")
        self.cb_rule = QComboBox()
        self.rules = [
            "Günde maksimum ders sayısı",
            "Dersler haftanın günlerine eşit dağıtılsın",
            "Seçilen dersler aynı gün peş peşe gelsin",
            "İki ders aynı güne gelmesin",
            "Öğretmenin dersleri öğleden önce toplansın",
            "Öğretmenin dersleri öğleden sonra toplansın",
            "Son ders saatine zor ders konulmasın"
        ]
        self.cb_rule.addItems(self.rules)
        self.cb_rule.currentIndexChanged.connect(self._rule_changed)
        
        main_layout.addWidget(lbl_rule)
        main_layout.addWidget(self.cb_rule)
        
        # Filters Group
        group_filters = QGroupBox("Aşağıdaki filtreleri uygula:")
        filter_layout = QVBoxLayout(group_filters)
        
        # Subjects Filter
        lay_subj = QHBoxLayout()
        lay_subj.addWidget(QLabel("Dersler:"))
        self.cb_subj = QComboBox()
        self.cb_subj.addItems(["Tüm dersler", "Seçili dersler..."])
        self.cb_subj.setSizePolicy(self.cb_subj.sizePolicy().Policy.Expanding, self.cb_subj.sizePolicy().Policy.Fixed)
        self.btn_subj = QPushButton("Değiştir")
        self.btn_subj.clicked.connect(self._change_subjects)
        lay_subj.addWidget(self.cb_subj)
        lay_subj.addWidget(self.btn_subj)
        filter_layout.addLayout(lay_subj)
        
        # Teachers Filter
        lay_teach = QHBoxLayout()
        lay_teach.addWidget(QLabel("Öğretmenler:"))
        self.cb_teach = QComboBox()
        self.cb_teach.addItems(["Tüm öğretmenler", "Seçili öğretmenler..."])
        self.cb_teach.setSizePolicy(self.cb_teach.sizePolicy().Policy.Expanding, self.cb_teach.sizePolicy().Policy.Fixed)
        self.btn_teach = QPushButton("Değiştir")
        self.btn_teach.clicked.connect(self._change_teachers)
        lay_teach.addWidget(self.cb_teach)
        lay_teach.addWidget(self.btn_teach)
        filter_layout.addLayout(lay_teach)
        
        # Classes Filter
        lay_class = QHBoxLayout()
        lay_class.addWidget(QLabel("Sınıflar:"))
        self.cb_class = QComboBox()
        self.cb_class.addItems(["Tüm sınıflar", "Seçili sınıflar..."])
        self.cb_class.setSizePolicy(self.cb_class.sizePolicy().Policy.Expanding, self.cb_class.sizePolicy().Policy.Fixed)
        self.btn_class = QPushButton("Değiştir")
        self.btn_class.clicked.connect(self._change_classes)
        lay_class.addWidget(self.cb_class)
        lay_class.addWidget(self.btn_class)
        filter_layout.addLayout(lay_class)
        
        main_layout.addWidget(group_filters)
        
        # Dynamic Parameters
        self.param_widget = QWidget()
        self.param_layout = QHBoxLayout(self.param_widget)
        self.param_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_param = QLabel("Maksimum sayı:")
        self.spin_param = QSpinBox()
        self.spin_param.setRange(1, 15)
        self.param_layout.addWidget(self.lbl_param)
        self.param_layout.addWidget(self.spin_param)
        self.param_layout.addStretch()
        main_layout.addWidget(self.param_widget)
        
        # Importance
        lay_imp = QHBoxLayout()
        lay_imp.addWidget(QLabel("Önem derecesi:"))
        self.cb_imp = QComboBox()
        self.cb_imp.addItems(["Sıkı", "Yüksek", "Normal", "Düşük"])
        lay_imp.addWidget(self.cb_imp)
        lay_imp.addStretch()
        main_layout.addLayout(lay_imp)
        
        main_layout.addStretch(1)
        
        # Bottom Buttons
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Tamam")
        self.btn_cancel = QPushButton("İptal")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)
        
        self.selected_subjects = []
        self.selected_teachers = []
        self.selected_classes = []
        
    def _rule_changed(self):
        rule = self.cb_rule.currentText()
        if rule == "Günde maksimum ders sayısı":
            self.param_widget.show()
            self.lbl_param.setText("Maksimum sayı:")
        else:
            self.param_widget.hide()
            
    def _change_subjects(self):
        items = [d.get("ad", "") for d in self.data_store.get("dersler", []) if d.get("ad")]
        d = MultiSelectDialog(items, self.selected_subjects, "Dersleri Seç", self)
        if d.exec():
            self.selected_subjects = d.get_selected()
            if self.selected_subjects:
                self.cb_subj.setCurrentIndex(1)
            else:
                self.cb_subj.setCurrentIndex(0)
                
    def _change_teachers(self):
        items = [t.get("ad", "") for t in self.data_store.get("ogretmenler", []) if t.get("ad")]
        d = MultiSelectDialog(items, self.selected_teachers, "Öğretmenleri Seç", self)
        if d.exec():
            self.selected_teachers = d.get_selected()
            if self.selected_teachers:
                self.cb_teach.setCurrentIndex(1)
            else:
                self.cb_teach.setCurrentIndex(0)
                
    def _change_classes(self):
        items = [s.get("ad", "") for s in self.data_store.get("siniflar", []) if s.get("ad")]
        d = MultiSelectDialog(items, self.selected_classes, "Sınıfları Seç", self)
        if d.exec():
            self.selected_classes = d.get_selected()
            if self.selected_classes:
                self.cb_class.setCurrentIndex(1)
            else:
                self.cb_class.setCurrentIndex(0)
                
    def _load_data(self):
        if self.relation_data:
            rule_text = self.relation_data.get("kural", "")
            idx = self.cb_rule.findText(rule_text)
            if idx >= 0: self.cb_rule.setCurrentIndex(idx)
            
            subj = self.relation_data.get("dersler", [])
            if subj:
                self.selected_subjects = subj
                self.cb_subj.setCurrentIndex(1)
                
            teach = self.relation_data.get("ogretmenler", [])
            if teach:
                self.selected_teachers = teach
                self.cb_teach.setCurrentIndex(1)
                
            cls = self.relation_data.get("siniflar", [])
            if cls:
                self.selected_classes = cls
                self.cb_class.setCurrentIndex(1)
                
            self.spin_param.setValue(self.relation_data.get("parametre", 1))
            
            imp = self.relation_data.get("onem", "Sıkı")
            idx_imp = self.cb_imp.findText(imp)
            if idx_imp >= 0: self.cb_imp.setCurrentIndex(idx_imp)
            
        self._rule_changed()
        
    def get_data(self):
        return {
            "aktif": self.relation_data.get("aktif", True),
            "kural": self.cb_rule.currentText(),
            "dersler": self.selected_subjects if self.cb_subj.currentIndex() == 1 else [],
            "ogretmenler": self.selected_teachers if self.cb_teach.currentIndex() == 1 else [],
            "siniflar": self.selected_classes if self.cb_class.currentIndex() == 1 else [],
            "parametre": self.spin_param.value() if not self.param_widget.isHidden() else None,
            "onem": self.cb_imp.currentText()
        }


class PlanningRelationsDialog(QDialog):
    def __init__(self, data_store=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        if "planlama_iliskileri" not in self.data_store:
            self.data_store["planlama_iliskileri"] = []
            
        self.setWindowTitle("Dersler arasındaki gelişmiş planlama ilişkileri")
        self.resize(800, 600)
        self.setStyleSheet("""
            QDialog { background-color: #F0F0F0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 12px; }
            QTableWidget { background: white; border: 1px solid #A0A0A0; gridline-color: #D0D0D0; }
            QHeaderView::section { background: #E0E0E0; border: 1px solid #A0A0A0; padding: 4px; }
            QPushButton { padding: 4px 12px; border: 1px solid #ADADAD; background: #E1E1E1; border-radius: 3px; min-width: 60px; }
            QPushButton:hover { background: #E5F1FB; border: 1px solid #0078D7; }
        """)
        self._build_ui()
        self._load_table()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Table
        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(["", "İlişki", "Uygulanacak Dersler", "Sınıflar", "Öğretmenler", "Önem"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 30)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self._edit_relation)
        main_layout.addWidget(self.table, 1)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_add = QPushButton("Ekle")
        btn_add.clicked.connect(self._add_relation)
        
        btn_edit = QPushButton("Düzenle")
        btn_edit.clicked.connect(self._edit_relation_btn)
        
        btn_del = QPushButton("Sil")
        btn_del.clicked.connect(self._del_relation)
        
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_del)
        btn_row.addStretch(1)
        
        btn_ok = QPushButton("Kapat")
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_ok)
        
        main_layout.addLayout(btn_row)

    def _load_table(self):
        self.table.setRowCount(0)
        items = self.data_store.get("planlama_iliskileri", [])
        for idx, item in enumerate(items):
            self.table.insertRow(idx)
            
            # Checkbox item
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Checked if item.get("aktif", True) else Qt.Unchecked)
            self.table.setItem(idx, 0, chk_item)
            
            # Rule text
            kural_text = item.get("kural", "")
            if item.get("parametre"):
                kural_text += f" ({item['parametre']})"
            self.table.setItem(idx, 1, QTableWidgetItem(kural_text))
            
            # Subj
            subj = item.get("dersler", [])
            self.table.setItem(idx, 2, QTableWidgetItem(", ".join(subj) if subj else "Tümü"))
            
            # Class
            cls = item.get("siniflar", [])
            self.table.setItem(idx, 3, QTableWidgetItem(", ".join(cls) if cls else "Tümü"))
            
            # Teach
            teach = item.get("ogretmenler", [])
            self.table.setItem(idx, 4, QTableWidgetItem(", ".join(teach) if teach else "Tümü"))
            
            # Importance
            self.table.setItem(idx, 5, QTableWidgetItem(item.get("onem", "Sıkı")))

    def _add_relation(self):
        d = EditRelationDialog(self.data_store, parent=self)
        if d.exec():
            new_data = d.get_data()
            self.data_store["planlama_iliskileri"].append(new_data)
            self._save()
            self._load_table()

    def _edit_relation_btn(self):
        r = self.table.currentRow()
        if r >= 0:
            self._edit_relation(self.table.item(r, 1))

    def _edit_relation(self, item):
        if not item: return
        r = item.row()
        rel_data = self.data_store["planlama_iliskileri"][r]
        d = EditRelationDialog(self.data_store, relation_data=rel_data, parent=self)
        if d.exec():
            updated_data = d.get_data()
            self.data_store["planlama_iliskileri"][r] = updated_data
            self._save()
            self._load_table()

    def _del_relation(self):
        r = self.table.currentRow()
        if r >= 0:
            resp = QMessageBox.question(self, "Sil", "Bu kuralı silmek istediğinize emin misiniz?", QMessageBox.Yes | QMessageBox.No)
            if resp == QMessageBox.Yes:
                self.data_store["planlama_iliskileri"].pop(r)
                self._save()
                self._load_table()

    def _save(self):
        # Update check states before saving to main db
        for r in range(self.table.rowCount()):
            chk = self.table.item(r, 0)
            if chk:
                self.data_store["planlama_iliskileri"][r]["aktif"] = (chk.checkState() == Qt.Checked)
                
        p = self.parent()
        if p and hasattr(p, "save_db"):
            p.save_db()
