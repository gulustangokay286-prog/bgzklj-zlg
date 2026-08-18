from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QLabel, QMessageBox, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QIcon, QFont

class TimeoffDialog(QDialog):
    """
    Öğretmen, Sınıf veya Derslik için Zaman-Kilit Matrisi (Time-off Matrix).
    Y Ekseni (Satırlar): 1. Ders ... 16. Ders (Temel Bilgiler ayarına göre dinamik)
    X Ekseni (Sütunlar): Pazartesi ... Cuma / Pazar
    Durumlar:
      2 = Yeşil Tik (Uygundur)
      0 = Kırmızı Çarpı (Çalışamaz / Kapalı)
      1 = Sarı Soru İşareti (Zorunlu olmadıkça atanmasın)
    """
    def __init__(self, entity_dict, entity_type, data_store, parent=None):
        super().__init__(parent)
        self.entity_dict = entity_dict
        self.entity_type = entity_type
        self.data_store = data_store if data_store is not None else {}
        
        name = self.entity_dict.get("ad", "İsimsiz")
        self.setWindowTitle(f"Zaman Tablosu (Kısıtlamalar) - {name} ({self.entity_type})")
        self.resize(740, 520)
        
        # Tema ve CSS
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: 'Segoe UI', Tahoma, sans-serif; }
            QLabel { color: #1E293B; font-size: 13px; }
            QTableWidget { background-color: white; gridline-color: #CBD5E1; border: 1px solid #CBD5E1; border-radius: 6px; }
            QHeaderView::section { background-color: #F1F5F9; font-weight: bold; padding: 6px; border: 1px solid #E2E8F0; color: #1E293B; font-size: 12px; }
            QPushButton { background-color: #2563EB; color: white; border-radius: 4px; padding: 8px 18px; font-weight: bold; font-size: 13px; border: none; }
            QPushButton:hover { background-color: #1D4ED8; }
            QPushButton#btn_cancel { background-color: #FFFFFF; color: #475569; border: 1px solid #CBD5E1; }
            QPushButton#btn_cancel:hover { background-color: #F1F5F9; }
        """)
        
        self.settings = self.data_store.get("settings", {})
        
        # Günleri oku
        self.days = self.settings.get("days")
        if not self.days:
            days_count = int(self.settings.get("days_count", self.settings.get("day_count", self.data_store.get("gun_sayisi", 5))))
            from timetable_grid import DAYS
            self.days = DAYS[:days_count]
            
        # Periyot / Günlük ders saatini Temel Bilgiler'den dinamik oku (Örn: 8, 10, 12, 16)
        self.periods = int(self.settings.get("periods", self.data_store.get("ders_saati", 8)))
        if self.periods <= 0:
            self.periods = 8
            
        # `timeoff` verisini dinamik periyot ve gün sayısına göre boyutlandır ve senkronize et
        current_toff = self.entity_dict.get("timeoff", [])
        new_toff = []
        for d_idx in range(len(self.days)):
            row = []
            for p_idx in range(self.periods):
                if d_idx < len(current_toff) and p_idx < len(current_toff[d_idx]):
                    row.append(current_toff[d_idx][p_idx])
                else:
                    row.append(2)  # Varsayılan: Açık / Uygun
            new_toff.append(row)
            
        self.entity_dict["timeoff"] = new_toff
        self.timeoff_data = self.entity_dict["timeoff"]
        
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Üst Bilgi
        info_lbl = QLabel("💡 <b>Kısıtlama Ayarı:</b> Y ekseninde ders saatleri (1-" + str(self.periods) + "), X ekseninde günler yer alır.<br>Hücreye tıklayarak durumu değiştirin (Yeşil ✔ -> Kırmızı ✖ -> Sarı ? -> Yeşil ✔).")
        info_lbl.setStyleSheet("color: #475569; font-size: 12px;")
        layout.addWidget(info_lbl)
        
        # Grid: Y-Ekseni = Periyotlar (1..periods), X-Ekseni = Günler (Pzt..Cuma)
        self.table = QTableWidget(self.periods, len(self.days))
        self.table.setVerticalHeaderLabels([f"{i+1}. Ders" for i in range(self.periods)])
        self.table.setHorizontalHeaderLabels(self.days)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # Satır ve Sütun boyutları
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Hücreleri Doldur
        for p_idx in range(self.periods):
            for d_idx in range(len(self.days)):
                state = self.timeoff_data[d_idx][p_idx]
                item = QTableWidgetItem()
                self._update_item_visuals(item, state)
                self.table.setItem(p_idx, d_idx, item)
                
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.horizontalHeader().sectionClicked.connect(self._toggle_column)
        self.table.verticalHeader().sectionClicked.connect(self._toggle_row)
        layout.addWidget(self.table, 1)
        
        # Hızlı Butonlar (Tümünü Kapat / Tümünü Aç)
        quick_bar = QHBoxLayout()
        btn_all_open = QPushButton("Tümünü Müsait Yap (✔)")
        btn_all_open.setStyleSheet("background: #DCFCE7; color: #15803D; border: 1px solid #86EFAC; font-size: 11px;")
        btn_all_open.clicked.connect(self._make_all_open)
        
        btn_all_close = QPushButton("Tümünü Kapat / Kısıtla (✖)")
        btn_all_close.setStyleSheet("background: #FEE2E2; color: #B91C1C; border: 1px solid #FCA5A5; font-size: 11px;")
        btn_all_close.clicked.connect(self._make_all_close)
        
        quick_bar.addWidget(btn_all_open)
        quick_bar.addWidget(btn_all_close)
        quick_bar.addStretch(1)
        layout.addLayout(quick_bar)
        
        # Lejand (Legend)
        legend_layout = QHBoxLayout()
        self.lbl_musait = self._create_legend_item("✔ Müsait (0)", "#15803D")
        self.lbl_kapali = self._create_legend_item("✖ Kapalı / Kısıtlı (0)", "#B91C1C")
        self.lbl_tercih = self._create_legend_item("? Tercih Edilmez (0)", "#A16207")
        legend_layout.addWidget(self.lbl_musait)
        legend_layout.addWidget(self.lbl_kapali)
        legend_layout.addWidget(self.lbl_tercih)
        legend_layout.addStretch()
        layout.addLayout(legend_layout)
        
        self._update_counters()
        
        # Alt Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setObjectName("btn_cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_save = QPushButton("Kaydet ve Uygula")
        btn_save.clicked.connect(self._save_data)
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)
        
    def _create_legend_item(self, text, color):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {color}; font-weight: bold; margin-right: 15px;")
        return lbl
        
    def _update_counters(self):
        c_musait = 0
        c_kapali = 0
        c_tercih = 0
        for d in range(len(self.days)):
            for p in range(self.periods):
                state = self.timeoff_data[d][p]
                if state == 2: c_musait += 1
                elif state == 0: c_kapali += 1
                elif state == 1: c_tercih += 1
                
        self.lbl_musait.setText(f"✔ Müsait ({c_musait})")
        self.lbl_kapali.setText(f"✖ Kapalı / Kısıtlı ({c_kapali})")
        self.lbl_tercih.setText(f"? Tercih Edilmez ({c_tercih})")


    def _update_item_visuals(self, item, state):
        item.setTextAlignment(Qt.AlignCenter)
        font = QFont("Segoe UI", 11, QFont.Bold)
        item.setFont(font)
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
        # row = p_idx (period), col = d_idx (day)
        current_state = self.timeoff_data[col][row]
        # Cycle: 2 -> 0 -> 1 -> 2
        if current_state == 2:
            new_state = 0
        elif current_state == 0:
            new_state = 1
        else:
            new_state = 2
            
        self.timeoff_data[col][row] = new_state
        item = self.table.item(row, col)
        self._update_item_visuals(item, new_state)
        self._update_counters()

    def _toggle_column(self, col):
        # col = d_idx (toggle entire day)
        any_open = any(self.timeoff_data[col][p] > 0 for p in range(self.periods))
        new_st = 0 if any_open else 2
        for p in range(self.periods):
            self.timeoff_data[col][p] = new_st
            item = self.table.item(p, col)
            if item: self._update_item_visuals(item, new_st)
        self._update_counters()

    def _toggle_row(self, row):
        # row = p_idx (toggle entire period)
        any_open = any(self.timeoff_data[d][row] > 0 for d in range(len(self.days)))
        new_st = 0 if any_open else 2
        for d in range(len(self.days)):
            self.timeoff_data[d][row] = new_st
            item = self.table.item(row, d)
            if item: self._update_item_visuals(item, new_st)
        self._update_counters()

    def _make_all_open(self):
        for d in range(len(self.days)):
            for p in range(self.periods):
                self.timeoff_data[d][p] = 2
                item = self.table.item(p, d)
                if item: self._update_item_visuals(item, 2)
        self._update_counters()

    def _make_all_close(self):
        for d in range(len(self.days)):
            for p in range(self.periods):
                self.timeoff_data[d][p] = 0
                item = self.table.item(p, d)
                if item: self._update_item_visuals(item, 0)
        self._update_counters()

    def _save_data(self):
        self.accept()
