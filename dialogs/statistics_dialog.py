from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QPushButton, QHeaderView, QGroupBox
)
from PySide6.QtCore import Qt
from collections import defaultdict

class StatisticsDialog(QDialog):
    def __init__(self, data_store, parent=None):
        super().__init__(parent)
        self.data_store = data_store
        self.setWindowTitle("İstatistikler ve Analiz")
        self.resize(600, 500)
        
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid #CBD5E1; border-radius: 4px; margin-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; color: #334155; }
            QLabel { font-size: 13px; color: #475569; }
            QTableWidget { background-color: white; border: 1px solid #E2E8F0; }
            QHeaderView::section { background-color: #F1F5F9; font-weight: bold; border: 1px solid #E2E8F0; }
            QPushButton { background-color: #3B82F6; color: white; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #2563EB; }
        """)
        
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. Genel Özet
        grp_summary = QGroupBox("Genel Okul Özeti")
        sum_layout = QVBoxLayout(grp_summary)
        
        num_classes = len(self.data_store.get("siniflar", []))
        num_teachers = len(self.data_store.get("ogretmenler", []))
        
        assignments = self.data_store.get("atamalar", [])
        total_hours = sum(int(a.get("saat", 1)) for a in assignments)
        
        sum_layout.addWidget(QLabel(f"Toplam Sınıf Sayısı: {num_classes}"))
        sum_layout.addWidget(QLabel(f"Toplam Öğretmen Sayısı: {num_teachers}"))
        sum_layout.addWidget(QLabel(f"Atanan Toplam Ders Saati: {total_hours} Saat"))
        
        layout.addWidget(grp_summary)
        
        # 2. Öğretmen Yükleri Tablosu
        grp_teachers = QGroupBox("Öğretmen Ders Yükü Dağılımı")
        t_layout = QVBoxLayout(grp_teachers)
        
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Öğretmen", "Haftalık Toplam Saat"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Compute teacher loads
        loads = defaultdict(int)
        for a in assignments:
            t = a.get("ogretmen", "")
            if t:
                loads[t] += int(a.get("saat", 1))
                
        self.table.setRowCount(len(loads))
        for row, (t_name, hours) in enumerate(sorted(loads.items(), key=lambda x: -x[1])):
            self.table.setItem(row, 0, QTableWidgetItem(t_name))
            
            h_item = QTableWidgetItem(f"{hours} Saat")
            h_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, h_item)
            
        t_layout.addWidget(self.table)
        layout.addWidget(grp_teachers)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton("Kapat")
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)
        
        layout.addLayout(btn_layout)
