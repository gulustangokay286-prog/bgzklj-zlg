from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QLabel, QMessageBox, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QIcon

class TimeoffDialog(QDialog):
    """
    Öğretmen, Sınıf veya Derslik için Zaman-Kilit Matrisi (Time-off Matrix).
    Durumlar:
      2 = Yeşil Tik (Uygundur)
      0 = Kırmızı Çarpı (Çalışamaz)
      1 = Sarı Soru İşareti (Zorunlu olmadıkça atanmasın)
    """
    def __init__(self, entity_dict, entity_type, data_store, parent=None):
        super().__init__(parent)
        self.entity_dict = entity_dict
        self.entity_type = entity_type
        self.data_store = data_store
        
        name = self.entity_dict.get("ad", "İsimsiz")
        self.setWindowTitle(f"Zaman Tablosu (Kısıtlamalar) - {name} ({self.entity_type})")
        self.resize(700, 450)
        
        # Tema ve CSS
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: 'Segoe UI', Tahoma, sans-serif; }
            QLabel { color: #1E293B; font-size: 13px; }
            QTableWidget { background-color: white; gridline-color: #E2E8F0; border: 1px solid #CBD5E1; border-radius: 4px; }
            QHeaderView::section { background-color: #F1F5F9; font-weight: bold; padding: 4px; border: 1px solid #E2E8F0; color: #334155; }
            QPushButton { background-color: #3B82F6; color: white; border-radius: 4px; padding: 8px 16px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background-color: #2563EB; }
            QPushButton#btn_cancel { background-color: #64748B; }
            QPushButton#btn_cancel:hover { background-color: #475569; }
        """)
        
        self.settings = self.data_store.get("settings", {})
        self.days = self.settings.get("days", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
        self.periods = int(self.settings.get("periods", 8))
        
        # `timeoff` verisini yükle veya oluştur
        if "timeoff" not in self.entity_dict:
            # Varsayılan: Her şey yeşil (2)
            self.entity_dict["timeoff"] = [[2 for _ in range(self.periods)] for _ in range(len(self.days))]
            
        self.timeoff_data = self.entity_dict["timeoff"]
        
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Üst Bilgi
        info_lbl = QLabel("Hücrelere tıklayarak durumu değiştirin (Yeşil -> Kırmızı -> Sarı -> Yeşil).")
        info_lbl.setStyleSheet("font-style: italic; color: #64748B;")
        layout.addWidget(info_lbl)
        
        # Grid
        self.table = QTableWidget(len(self.days), self.periods)
        self.table.setHorizontalHeaderLabels([f"{i+1}. Ders" for i in range(self.periods)])
        self.table.setVerticalHeaderLabels(self.days)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # Satır ve Sütun boyutları
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Hücreleri Doldur
        for d_idx in range(len(self.days)):
            for p_idx in range(self.periods):
                state = self.timeoff_data[d_idx][p_idx]
                item = QTableWidgetItem()
                self._update_item_visuals(item, state)
                self.table.setItem(d_idx, p_idx, item)
                
        self.table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self.table)
        
        # Lejand (Legend)
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(self._create_legend_item("✔ Uygun (2)", "#22C55E"))
        legend_layout.addWidget(self._create_legend_item("✖ Kapalı (0)", "#EF4444"))
        legend_layout.addWidget(self._create_legend_item("? Tercih Edilmez (1)", "#EAB308"))
        legend_layout.addStretch()
        layout.addLayout(legend_layout)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setObjectName("btn_cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_save = QPushButton("Kaydet")
        btn_save.clicked.connect(self._save_data)
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)
        
    def _create_legend_item(self, text, color):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {color}; font-weight: bold; margin-right: 15px;")
        return lbl
        
    def _update_item_visuals(self, item, state):
        item.setTextAlignment(Qt.AlignCenter)
        if state == 2:
            item.setText("✔")
            item.setForeground(QBrush(QColor("#15803D"))) # Koyu Yeşil
            item.setBackground(QBrush(QColor("#DCFCE7"))) # Açık Yeşil
        elif state == 0:
            item.setText("✖")
            item.setForeground(QBrush(QColor("#B91C1C"))) # Koyu Kırmızı
            item.setBackground(QBrush(QColor("#FEE2E2"))) # Açık Kırmızı
        elif state == 1:
            item.setText("?")
            item.setForeground(QBrush(QColor("#A16207"))) # Koyu Sarı
            item.setBackground(QBrush(QColor("#FEF9C3"))) # Açık Sarı
            
    def _on_cell_clicked(self, row, col):
        current_state = self.timeoff_data[row][col]
        # Cycle: 2 -> 0 -> 1 -> 2
        if current_state == 2:
            new_state = 0
        elif current_state == 0:
            new_state = 1
        else:
            new_state = 2
            
        self.timeoff_data[row][col] = new_state
        item = self.table.item(row, col)
        self._update_item_visuals(item, new_state)
        
    def _save_data(self):
        # Kaydet: dict zaten referans tipli olduğu için self.entity_dict["timeoff"] güncellendi bile.
        self.accept()
