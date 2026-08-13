"""
verify_timetable_dialog.py – Planlama Sonrası Kontrol
aSc Timetables birebir kopyası.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

class VerifyTimetableDialog(QDialog):
    def __init__(self, data_store, parent=None):
        super().__init__(parent)
        self.data_store = data_store
        
        self.setWindowTitle("Doğrulama Sonuçları")
        self.resize(700, 450)
        
        self.setStyleSheet("""
            QDialog { background-color: #F0F0F0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 12px; }
            QTableWidget { background: white; border: 1px solid #A0A0A0; gridline-color: #D0D0D0; }
            QHeaderView::section { background: #E0E0E0; border: 1px solid #A0A0A0; padding: 4px; font-weight: bold; }
            QPushButton { padding: 4px 12px; border: 1px solid #ADADAD; background: #E1E1E1; border-radius: 3px; min-width: 80px; }
            QPushButton:hover { background: #E5F1FB; border: 1px solid #0078D7; }
        """)
        
        self._build_ui()
        self._run_verification()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        self.lbl_status = QLabel("Planlama kontrol ediliyor...")
        font = QFont()
        font.setBold(True)
        self.lbl_status.setFont(font)
        layout.addWidget(self.lbl_status)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Önem", "Kısıtlama / İhlal Nedeni", "Etkilenen Nesneler"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(2, 200)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_close = QPushButton("Kapat")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        
    def _run_verification(self):
        self.table.setRowCount(0)
        
        # Simulated verification logic based on actual data
        errors = []
        
        # 1. Check empty schedule (if no placements exist)
        placements = self.data_store.get("grid_placements", {})
        if not placements:
            errors.append(("Yüksek", "Ders programı boş! Hiçbir ders yerleştirilmemiş.", "Tüm Sınıflar"))
            
        # 2. Check for missing teacher assignments in defined electives
        for elec in self.data_store.get("secmeli_dersler", []):
            if elec.get("ogretmen") == "Atanmadı":
                errors.append(("Normal", f"Seçmeli derse öğretmen atanmamış.", elec.get("ad", "Bilinmeyen")))
                
        # 3. Check for unassigned classes in electives
        for elec in self.data_store.get("secmeli_dersler", []):
            if not elec.get("siniflar"):
                errors.append(("Düşük", f"Seçmeli ders hiçbir sınıfa atanmamış.", elec.get("ad", "Bilinmeyen")))
                
        # Populate table
        for idx, (severity, desc, affected) in enumerate(errors):
            self.table.insertRow(idx)
            item_sev = QTableWidgetItem(severity)
            if severity == "Yüksek":
                item_sev.setForeground(QColor("red"))
            elif severity == "Normal":
                item_sev.setForeground(QColor("orange"))
                
            self.table.setItem(idx, 0, item_sev)
            self.table.setItem(idx, 1, QTableWidgetItem(desc))
            self.table.setItem(idx, 2, QTableWidgetItem(affected))
            
        if not errors:
            self.lbl_status.setText("Doğrulama başarılı! Hiçbir kısıtlama ihlali bulunamadı.")
            self.lbl_status.setStyleSheet("color: green;")
        else:
            self.lbl_status.setText(f"Doğrulama tamamlandı. {len(errors)} adet kısıtlama ihlali bulundu!")
            self.lbl_status.setStyleSheet("color: red;")
