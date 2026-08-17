from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QPushButton, QLabel, QHBoxLayout, QWidget, QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

class ClassAssignmentsPreviewDialog(QDialog):
    def __init__(self, data_store, parent=None):
        super().__init__(parent)
        self.data_store = data_store
        self.setWindowTitle("Sınıf Dersleri & Atama Listesi")
        self.resize(1000, 700)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QTableWidget { background: white; border: 1px solid #CBD5E1; border-radius: 4px; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #E2E8F0; }
            QHeaderView::section { background-color: #F1F5F9; font-weight: bold; border: none; padding: 10px; border-bottom: 2px solid #CBD5E1; }
            QPushButton { background: #0078D7; color: white; padding: 6px 12px; border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #005A9E; }
            QLineEdit { border: 1px solid #CBD5E1; border-radius: 4px; padding: 6px; }
        """)
        self._build_ui()
        self._load_data()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        top_bar = QHBoxLayout()
        lbl = QLabel("📚 <b>Sınıf Dersleri & Atama Listesi</b>")
        lbl.setFont(QFont("Segoe UI", 14))
        top_bar.addWidget(lbl)
        
        top_bar.addStretch()
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Sınıf, Ders veya Öğretmen Ara...")
        self.txt_search.setFixedWidth(250)
        self.txt_search.textChanged.connect(self._filter_table)
        top_bar.addWidget(self.txt_search)
        
        btn_print = QPushButton("🖨️ Yazdır / PDF Önizle")
        btn_print.clicked.connect(self._open_print_preview)
        top_bar.addWidget(btn_print)
        
        layout.addLayout(top_bar)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Sınıf", "Ders", "Öğretmen", "Haftalık Saat"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("alternate-background-color: #F8FAFC;")
        
        layout.addWidget(self.table)
        
        btn_close = QPushButton("Kapat")
        btn_close.setStyleSheet("background: #64748B;")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)
        
    def _open_print_preview(self):
        from dialogs.print_preview import TimetablePrintPreview
        filters = {
            "lock_mode": "Sınıf Dersleri & Atama Listesi (Liste Formatı)",
            "default_selection": ""
        }
        dlg = TimetablePrintPreview(self.data_store, {}, filters, self)
        dlg.exec()
        
    def _load_data(self):
        atamalar = self.data_store.get("atamalar", [])
        
        flattened = []
        for a in atamalar:
            c_raw = a.get("class", "").strip()
            s_name = a.get("subject", "").strip()
            t_name = a.get("teacher", "").strip()
            dur = a.get("duration", 0)
            
            if "," in c_raw or "&" in c_raw:
                parts = [c.strip() for c in c_raw.replace("&", ",").split(",") if c.strip()]
                for p in parts:
                    flattened.append({
                        "class": p,
                        "subject": f"{s_name} (Ortak)",
                        "teacher": t_name,
                        "duration": dur
                    })
            else:
                flattened.append({
                    "class": c_raw,
                    "subject": s_name,
                    "teacher": t_name,
                    "duration": dur
                })
        
        import re
        def cls_sort_key(a):
            c = a.get("class", "").strip()
            m = re.match(r"(\d+)(.*)", c)
            return (int(m.group(1)), m.group(2)) if m else (999, c)
            
        sorted_atamalar = sorted(flattened, key=cls_sort_key)
        self.table.setRowCount(len(sorted_atamalar))
        
        for i, a in enumerate(sorted_atamalar):
            c_name = a.get("class", "")
            s_name = a.get("subject", "")
            t_name = a.get("teacher", "")
            dur = str(a.get("duration", 0))
            
            self.table.setItem(i, 0, QTableWidgetItem(c_name))
            self.table.setItem(i, 1, QTableWidgetItem(s_name))
            self.table.setItem(i, 2, QTableWidgetItem(t_name))
            
            item_dur = QTableWidgetItem(dur)
            item_dur.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 3, item_dur)
            
    def _filter_table(self, text):
        query = text.strip().lower()
        for r in range(self.table.rowCount()):
            match = False
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item and query in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(r, not match)
