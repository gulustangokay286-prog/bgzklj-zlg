from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QCheckBox, QTabWidget, QWidget
)
from PySide6.QtCore import Qt
import database

class PrintWizardDialog(QDialog):
    def __init__(self, data_store=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
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
        
        # Load from SQLite
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
        for c in classes:
            item = QListWidgetItem(c.get("ad", ""))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.list_classes.addItem(item)
            
        teachers = self.data_store.get("ogretmenler", [])
        for t in teachers:
            item = QListWidgetItem(t.get("ad", ""))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked) # Varsayılan olarak sınıf yazdırıldığı için öğretmenleri kapalı tut
            self.list_teachers.addItem(item)
            
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
