"""
groups_dialog.py – Sınıf ve Öğrenci Grupları (Seçmeli Ders / Şube Grupları) Yönetimi
Sınıfların şube gruplarına (Örn: 10-A Almanca/Fransızca, 12-B Sayısal/Sözel) ayrılmasını sağlar.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

class GroupsDialog(QDialog):
    def __init__(self, data_store=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        if "gruplar" not in self.data_store:
            self.data_store["gruplar"] = []
            
        self.setWindowTitle("Sınıf Ders Grupları ve Şube Bölünmeleri")
        self.resize(650, 480)
        self.setStyleSheet("""
            QDialog { background-color: #F4F6F9; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; }
            QLabel { color: #333; font-weight: bold; }
            QTableWidget { background: white; border: 1px solid #D0D7DE; border-radius: 6px; gridline-color: #E0E0E0; }
            QHeaderView::section { background: #EBF3FB; font-weight: bold; padding: 6px; border: 1px solid #D0D7DE; }
            QPushButton { min-height: 28px; padding: 4px 12px; border: 1px solid #CCCCCC; border-radius: 4px; background: #FFFFFF; }
            QPushButton:hover { background: #EBF3FB; }
        """)
        self._build_ui()
        self._load_table()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Info
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Sınıf Seçin:"))
        
        self.combo_sinif = QComboBox(self)
        self.combo_sinif.setMinimumWidth(200)
        siniflar = self.data_store.get("siniflar", [])
        for s in siniflar:
            self.combo_sinif.addItem(s.get("ad", ""), s)
        self.combo_sinif.currentIndexChanged.connect(self._load_table)
        header_layout.addWidget(self.combo_sinif)
        
        header_layout.addStretch(1)
        main_layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["Grup Adı", "Kısa Adı", "Öğrenci / Ders Detayı"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        main_layout.addWidget(self.table, 1)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_add = QPushButton(" Yeni Grup Ekle")
        btn_add.setStyleSheet("background: #E8F5E9; color: #2E7D32; font-weight: bold; border: 1px solid #A5D6A7;")
        btn_add.clicked.connect(self._add_group)
        
        btn_del = QPushButton(" Grubu Sil")
        btn_del.setStyleSheet("background: #FFEBEE; color: #C62828; font-weight: bold; border: 1px solid #FFCDD2;")
        btn_del.clicked.connect(self._del_group)
        
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addStretch(1)
        main_layout.addLayout(btn_row)

        # Bottom Controls
        bottom = QHBoxLayout()
        btn_save = QPushButton("Kaydet ve Kapat")
        btn_save.setStyleSheet("background: #0078D7; color: white; font-weight: bold; padding: 6px 20px; border-radius: 4px;")
        btn_save.clicked.connect(self._save_and_accept)
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        
        bottom.addStretch(1)
        bottom.addWidget(btn_cancel)
        bottom.addWidget(btn_save)
        main_layout.addLayout(bottom)

    def _load_table(self):
        self.table.setRowCount(0)
        sinif_name = self.combo_sinif.currentText()
        if not sinif_name: return
        
        gruplar = [g for g in self.data_store.get("gruplar", []) if g.get("sinif") == sinif_name]
        
        for g in gruplar:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(g.get("ad", "")))
            self.table.setItem(r, 1, QTableWidgetItem(g.get("kisa", "")))
            self.table.setItem(r, 2, QTableWidgetItem(g.get("detay", "")))

    def _add_group(self):
        sinif_name = self.combo_sinif.currentText()
        if not sinif_name: return
        
        name, ok = QInputDialog.getText(self, "Yeni Grup", "Grup Adı (Örn: Seçmeli İngilizce):")
        if ok and name:
            new_g = {"sinif": sinif_name, "ad": name, "kisa": name[:4].upper(), "detay": "Tüm Sınıf / Şube"}
            self.data_store["gruplar"].append(new_g)
            self._load_table()

    def _del_group(self):
        r = self.table.currentRow()
        if r >= 0:
            name_item = self.table.item(r, 0)
            if name_item:
                g_name = name_item.text()
                sinif_name = self.combo_sinif.currentText()
                self.data_store["gruplar"] = [g for g in self.data_store.get("gruplar", []) if not (g.get("sinif") == sinif_name and g.get("ad") == g_name)]
                self.table.removeRow(r)

    def _save_and_accept(self):
        p = self.parent()
        if p and hasattr(p, "save_db"):
            p.save_db()
        self.accept()
