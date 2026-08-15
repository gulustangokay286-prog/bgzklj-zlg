from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QCheckBox, QTabWidget, QWidget
)
from PySide6.QtCore import Qt
import database

class PrintWizardDialog(QDialog):
    def __init__(self, data_store=None, default_entity=None, default_view=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        self.default_entity = default_entity
        self.default_view = default_view or ""
        self.setWindowTitle("Gelişmiş Yazdırma Sihirbazı")
        self.resize(500, 500)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QLabel { font-weight: bold; font-size: 14px; color: #1E293B; }
            QListWidget { border: 1px solid #CBD5E1; border-radius: 4px; padding: 5px; }
            QListWidget::item { padding: 4px; }
            QTabBar::tab { padding: 8px 16px; font-weight: bold; }
            QPushButton { padding: 8px 16px; font-weight: bold; border-radius: 4px; }
            QPushButton#printBtn { background-color: #059669; color: white; border: none; }
            QPushButton#printBtn:hover { background-color: #047857; }
        """)
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Classes Tab
        self.tab_classes = QWidget()
        l_classes = QVBoxLayout(self.tab_classes)
        self.list_classes = QListWidget()
        l_classes.addWidget(self.list_classes)
        
        # Teachers Tab
        self.tab_teachers = QWidget()
        l_teachers = QVBoxLayout(self.tab_teachers)
        self.list_teachers = QListWidget()
        l_teachers.addWidget(self.list_teachers)
        
        self.tabs.addTab(self.tab_classes, "Sınıflar (Öğrenci Görünümü)")
        self.tabs.addTab(self.tab_teachers, "Öğretmenler")
        
        # Load data
        self._load_data()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_all = QPushButton("Tümünü Seç")
        btn_all.clicked.connect(self._select_all)
        btn_none = QPushButton("Hiçbirini Seçme")
        btn_none.clicked.connect(self._select_none)
        
        self.btn_print = QPushButton("Seçilenleri Yazdır")
        self.btn_print.setObjectName("printBtn")
        self.btn_print.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_print)
        
        layout.addLayout(btn_layout)
        
    def _load_data(self):
        classes = self.data_store.get("siniflar", [])
        is_class_view = "Sınıf" in self.default_view or (self.default_entity and any(c.get("ad") == self.default_entity for c in classes))
        
        for c in classes:
            c_name = c.get("ad", "")
            item = QListWidgetItem(c_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if self.default_entity:
                item.setCheckState(Qt.Checked if c_name == self.default_entity else Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)
            self.list_classes.addItem(item)
            
        teachers = self.data_store.get("ogretmenler", [])
        is_teacher_view = "Öğretmen" in self.default_view or (self.default_entity and any(t.get("ad") == self.default_entity for t in teachers))
        
        for t in teachers:
            t_name = t.get("ad", "")
            item = QListWidgetItem(t_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if self.default_entity and is_teacher_view:
                item.setCheckState(Qt.Checked if t_name == self.default_entity else Qt.Unchecked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.list_teachers.addItem(item)
            
        if is_teacher_view:
            self.tabs.setCurrentIndex(1)
        else:
            self.tabs.setCurrentIndex(0)
            
    def _select_all(self):
        current_list = self.list_classes if self.tabs.currentIndex() == 0 else self.list_teachers
        for i in range(current_list.count()):
            current_list.item(i).setCheckState(Qt.Checked)
            
    def _select_none(self):
        current_list = self.list_classes if self.tabs.currentIndex() == 0 else self.list_teachers
        for i in range(current_list.count()):
            current_list.item(i).setCheckState(Qt.Unchecked)
            
    def get_selected_filters(self):
        selected_classes = []
        for i in range(self.list_classes.count()):
            if self.list_classes.item(i).checkState() == Qt.Checked:
                selected_classes.append(self.list_classes.item(i).text())
                
        selected_teachers = []
        for i in range(self.list_teachers.count()):
            if self.list_teachers.item(i).checkState() == Qt.Checked:
                selected_teachers.append(self.list_teachers.item(i).text())
                
        return {
            "classes": selected_classes,
            "teachers": selected_teachers
        }
