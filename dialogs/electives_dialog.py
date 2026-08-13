"""
electives_dialog.py – Seçmeli Dersler ve Havuz Grupları (Seminerler) Yönetimi
aSc Timetables "Seminerler" arayüzü kopyası.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSplitter,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFrame, QInputDialog, QListWidget, QListWidgetItem, QAbstractItemView, QWidget, QGroupBox, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

class EditSeminarDialog(QDialog):
    def __init__(self, data_store, seminar_data=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store
        self.seminar_data = seminar_data or {}
        
        self.setWindowTitle("Seminer / Seçmeli Ders")
        self.resize(400, 250)
        
        self.setStyleSheet("""
            QDialog { background-color: #F0F0F0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 12px; }
            QPushButton { padding: 4px 12px; border: 1px solid #ADADAD; background: #E1E1E1; border-radius: 3px; min-width: 60px; }
            QPushButton:hover { background: #E5F1FB; border: 1px solid #0078D7; }
            QComboBox, QSpinBox, QLineEdit { border: 1px solid #ADADAD; padding: 3px; background: white; }
        """)
        
        self._build_ui()
        self._load_data()
        
    def _build_ui(self):
        from PySide6.QtWidgets import QLineEdit, QFormLayout
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.txt_name = QLineEdit()
        form.addRow("Seminer / Seçmeli Adı:", self.txt_name)
        
        self.cb_teacher = QComboBox()
        teachers = ["Atanmadı"] + [t.get("ad", "") for t in self.data_store.get("ogretmenler", []) if t.get("ad")]
        self.cb_teacher.addItems(teachers)
        form.addRow("Öğretmen:", self.cb_teacher)
        
        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(1, 10)
        self.spin_duration.setValue(2)
        form.addRow("Haftalık Ders Saati:", self.spin_duration)
        
        layout.addLayout(form)
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Tamam")
        self.btn_cancel = QPushButton("İptal")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
    def _load_data(self):
        if self.seminar_data:
            self.txt_name.setText(self.seminar_data.get("ad", ""))
            t = self.seminar_data.get("ogretmen", "Atanmadı")
            idx = self.cb_teacher.findText(t)
            if idx >= 0:
                self.cb_teacher.setCurrentIndex(idx)
            self.spin_duration.setValue(self.seminar_data.get("saat", 2))
            
    def get_data(self):
        return {
            "ad": self.txt_name.text().strip(),
            "ogretmen": self.cb_teacher.currentText(),
            "saat": self.spin_duration.value(),
            "siniflar": self.seminar_data.get("siniflar", [])
        }


class AddClassToSeminarDialog(QDialog):
    def __init__(self, data_store, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sınıf Seçimi")
        self.resize(300, 400)
        
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        
        classes = [s.get("ad", "") for s in data_store.get("siniflar", []) if s.get("ad")]
        for c in classes:
            item = QListWidgetItem(c)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)
            
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
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected


class ElectivesDialog(QDialog):
    def __init__(self, data_store=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        if "secmeli_dersler" not in self.data_store:
            self.data_store["secmeli_dersler"] = []
            
        self.setWindowTitle("Seminerler")
        self.resize(850, 500)
        
        self.setStyleSheet("""
            QDialog { background-color: #F0F0F0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 12px; }
            QTableWidget { background: white; border: 1px solid #A0A0A0; gridline-color: #D0D0D0; }
            QHeaderView::section { background: #E0E0E0; border: 1px solid #A0A0A0; padding: 4px; }
            QPushButton { padding: 4px 12px; border: 1px solid #ADADAD; background: #E1E1E1; border-radius: 3px; min-width: 60px; }
            QPushButton:hover { background: #E5F1FB; border: 1px solid #0078D7; }
            QGroupBox { border: 1px solid #B0B0B0; margin-top: 2ex; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; }
        """)
        
        self.current_seminar_idx = -1
        self._build_ui()
        self._load_seminars()
        
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel (Seminars)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        
        lbl_sem = QLabel("<b>Seminerler / Seçmeli Dersler</b>")
        left_layout.addWidget(lbl_sem)
        
        self.table_sem = QTableWidget(0, 3)
        self.table_sem.setHorizontalHeaderLabels(["Seminer", "Saat", "Öğretmen"])
        self.table_sem.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_sem.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_sem.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_sem.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_sem.itemSelectionChanged.connect(self._on_seminar_selected)
        left_layout.addWidget(self.table_sem)
        
        sem_btn_layout = QHBoxLayout()
        btn_sem_add = QPushButton("Ekle")
        btn_sem_add.clicked.connect(self._add_seminar)
        btn_sem_edit = QPushButton("Düzenle")
        btn_sem_edit.clicked.connect(self._edit_seminar)
        btn_sem_del = QPushButton("Sil")
        btn_sem_del.clicked.connect(self._del_seminar)
        
        sem_btn_layout.addWidget(btn_sem_add)
        sem_btn_layout.addWidget(btn_sem_edit)
        sem_btn_layout.addWidget(btn_sem_del)
        left_layout.addLayout(sem_btn_layout)
        
        # Right Panel (Classes assigned to selected seminar)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0,0,0,0)
        
        self.lbl_class = QLabel("<b>Seçili Seminere Atanan Sınıflar</b>")
        right_layout.addWidget(self.lbl_class)
        
        self.table_class = QTableWidget(0, 1)
        self.table_class.setHorizontalHeaderLabels(["Sınıf / Grup"])
        self.table_class.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_class.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_class.setEditTriggers(QTableWidget.NoEditTriggers)
        right_layout.addWidget(self.table_class)
        
        cls_btn_layout = QHBoxLayout()
        self.btn_cls_add = QPushButton("Sınıf Ekle")
        self.btn_cls_add.clicked.connect(self._add_class_to_seminar)
        self.btn_cls_del = QPushButton("Sınıfı Çıkar")
        self.btn_cls_del.clicked.connect(self._del_class_from_seminar)
        
        self.btn_cls_add.setEnabled(False)
        self.btn_cls_del.setEnabled(False)
        
        cls_btn_layout.addWidget(self.btn_cls_add)
        cls_btn_layout.addWidget(self.btn_cls_del)
        cls_btn_layout.addStretch()
        right_layout.addLayout(cls_btn_layout)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([450, 350])
        main_layout.addWidget(splitter, 1)
        
        # Bottom
        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(self.accept)
        bot_layout = QHBoxLayout()
        bot_layout.addStretch()
        bot_layout.addWidget(btn_close)
        main_layout.addLayout(bot_layout)
        
    def _load_seminars(self):
        self.table_sem.setRowCount(0)
        items = self.data_store.get("secmeli_dersler", [])
        for idx, item in enumerate(items):
            self.table_sem.insertRow(idx)
            self.table_sem.setItem(idx, 0, QTableWidgetItem(item.get("ad", "")))
            self.table_sem.setItem(idx, 1, QTableWidgetItem(str(item.get("saat", 2))))
            self.table_sem.setItem(idx, 2, QTableWidgetItem(item.get("ogretmen", "Atanmadı")))
            
        self._on_seminar_selected()
        
    def _on_seminar_selected(self):
        sel = self.table_sem.selectedItems()
        if sel:
            self.current_seminar_idx = sel[0].row()
            self.btn_cls_add.setEnabled(True)
            self.btn_cls_del.setEnabled(True)
            self._load_classes_for_seminar()
        else:
            self.current_seminar_idx = -1
            self.table_class.setRowCount(0)
            self.btn_cls_add.setEnabled(False)
            self.btn_cls_del.setEnabled(False)
            
    def _load_classes_for_seminar(self):
        if self.current_seminar_idx < 0: return
        self.table_class.setRowCount(0)
        seminar = self.data_store["secmeli_dersler"][self.current_seminar_idx]
        classes = seminar.get("siniflar", [])
        for idx, c in enumerate(classes):
            self.table_class.insertRow(idx)
            self.table_class.setItem(idx, 0, QTableWidgetItem(c))
            
    def _add_seminar(self):
        d = EditSeminarDialog(self.data_store, parent=self)
        if d.exec():
            new_data = d.get_data()
            if not new_data.get("ad"):
                QMessageBox.warning(self, "Hata", "Seminer adı boş olamaz!")
                return
            self.data_store["secmeli_dersler"].append(new_data)
            self._save()
            self._load_seminars()
            
    def _edit_seminar(self):
        if self.current_seminar_idx < 0: return
        data = self.data_store["secmeli_dersler"][self.current_seminar_idx]
        d = EditSeminarDialog(self.data_store, seminar_data=data, parent=self)
        if d.exec():
            updated_data = d.get_data()
            if not updated_data.get("ad"):
                QMessageBox.warning(self, "Hata", "Seminer adı boş olamaz!")
                return
            self.data_store["secmeli_dersler"][self.current_seminar_idx] = updated_data
            self._save()
            self._load_seminars()
            
    def _del_seminar(self):
        if self.current_seminar_idx < 0: return
        resp = QMessageBox.question(self, "Sil", "Bu semineri silmek istediğinize emin misiniz?", QMessageBox.Yes | QMessageBox.No)
        if resp == QMessageBox.Yes:
            self.data_store["secmeli_dersler"].pop(self.current_seminar_idx)
            self._save()
            self._load_seminars()
            
    def _add_class_to_seminar(self):
        if self.current_seminar_idx < 0: return
        d = AddClassToSeminarDialog(self.data_store, parent=self)
        if d.exec():
            sel_classes = d.get_selected()
            seminar = self.data_store["secmeli_dersler"][self.current_seminar_idx]
            existing = seminar.get("siniflar", [])
            for c in sel_classes:
                if c not in existing:
                    existing.append(c)
            seminar["siniflar"] = existing
            self._save()
            self._load_classes_for_seminar()
            
    def _del_class_from_seminar(self):
        r = self.table_class.currentRow()
        if r >= 0 and self.current_seminar_idx >= 0:
            c_name = self.table_class.item(r, 0).text()
            seminar = self.data_store["secmeli_dersler"][self.current_seminar_idx]
            if c_name in seminar.get("siniflar", []):
                seminar["siniflar"].remove(c_name)
                self._save()
                self._load_classes_for_seminar()

    def _save(self):
        p = self.parent()
        if p and hasattr(p, "save_db"):
            p.save_db()
