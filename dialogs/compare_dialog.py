import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush

class CompareDialog(QDialog):
    def __init__(self, current_data_store, parent=None):
        super().__init__(parent)
        self.current_data_store = current_data_store
        self.old_data_store = None
        self.setWindowTitle("Ders Programı Karşılaştırma (Diff)")
        self.resize(750, 500)
        
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QLabel { color: #1E293B; font-size: 13px; font-weight: bold; }
            QTableWidget { background-color: white; border: 1px solid #E2E8F0; }
            QHeaderView::section { background-color: #F1F5F9; font-weight: bold; border: 1px solid #E2E8F0; }
            QPushButton { background-color: #3B82F6; color: white; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #2563EB; }
            QPushButton#btn_load { background-color: #F59E0B; }
            QPushButton#btn_load:hover { background-color: #D97706; }
        """)
        
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Üst Kısım
        top_layout = QHBoxLayout()
        self.lbl_info = QLabel("Lütfen karşılaştırmak istediğiniz eski yedek dosyasını (.json) seçin.")
        top_layout.addWidget(self.lbl_info)
        
        btn_load = QPushButton("Eski Dosyayı Seç")
        btn_load.setObjectName("btn_load")
        btn_load.clicked.connect(self._load_old_file)
        top_layout.addWidget(btn_load)
        
        layout.addLayout(top_layout)
        
        # Sonuç Tablosu
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Sınıf", "Öğretmen", "Ders", "Değişim Durumu"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        
        # Alt Kısım
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        
    def _load_old_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Eski Programı Aç", "", "JSON Dosyaları (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.old_data_store = json.load(f)
                self.lbl_info.setText(f"Seçilen Dosya: {path.split('/')[-1]}")
                self._compare_data()
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya okunurken hata oluştu:\n{str(e)}")
                
    def _compare_data(self):
        self.table.setRowCount(0)
        
        old_assignments = self.old_data_store.get("atamalar", [])
        new_assignments = self.current_data_store.get("atamalar", [])
        
        def make_sig(a):
            return f"{a.get('sinif')}_{a.get('ogretmen')}_{a.get('ders')}_{a.get('saat')}"
            
        old_sigs = set(make_sig(a) for a in old_assignments)
        new_sigs = set(make_sig(a) for a in new_assignments)
        
        added = new_sigs - old_sigs
        removed = old_sigs - new_sigs
        
        row = 0
        
        # Eklenenler (Yeşil)
        for a in new_assignments:
            sig = make_sig(a)
            if sig in added:
                self.table.insertRow(row)
                self._add_row_items(row, a, "YENİ EKLENDİ", "#15803D", "#DCFCE7")
                row += 1
                
        # Silinenler (Kırmızı)
        for a in old_assignments:
            sig = make_sig(a)
            if sig in removed:
                self.table.insertRow(row)
                self._add_row_items(row, a, "SİLİNMİŞ", "#B91C1C", "#FEE2E2")
                row += 1
                
        if row == 0:
            QMessageBox.information(self, "Sonuç", "Mevcut program ile seçilen eski program tamamen aynı. Hiçbir fark bulunamadı.")
            
    def _add_row_items(self, row, a_dict, status_text, fg_color, bg_color):
        item_c = QTableWidgetItem(a_dict.get('sinif', ''))
        item_t = QTableWidgetItem(a_dict.get('ogretmen', ''))
        item_s = QTableWidgetItem(a_dict.get('ders', ''))
        item_st = QTableWidgetItem(status_text)
        
        for item in (item_c, item_t, item_s, item_st):
            item.setForeground(QBrush(QColor(fg_color)))
            item.setBackground(QBrush(QColor(bg_color)))
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, self.table.column(item), item)
