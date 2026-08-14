"""
constraints_dialog.py – Öğretmen ve Sınıf Gün/Saat Kısıtlama Diyaloğu
Öğretmenlerin çalışamayacağı gün ve saatleri (Örn: Salı tüm gün veya Perşembe öğleden sonra) işaretlemelerini sağlar.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QBrush

DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
PERIODS = 8

class ConstraintsDialog(QDialog):
    def __init__(self, data_store=None, target_type="ogretmen", parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        self.target_type = target_type  # "ogretmen" veya "sinif"
        
        title_str = "Öğretmen Zaman Kısıtlamaları" if target_type == "ogretmen" else "Sınıf Zaman Kısıtlamaları"
        self.setWindowTitle(title_str)
        self.resize(750, 520)
        
        # Structure in data_store: data_store["kisitlamalar"][entity_name] = {"(day, period)": False}
        if "kisitlamalar" not in self.data_store:
            self.data_store["kisitlamalar"] = {}
            
        settings = self.data_store.get("settings", {})
        self.periods = int(settings.get("periods", 8))
        days_count = int(settings.get("days_count", 5))
        
        from timetable_grid import DAYS
        self.days = DAYS[:days_count]
            
        self._build_ui()
        self._populate_combo()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header Info
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Seçilen Kişi/Birim:", self))
        
        self.combo_target = QComboBox(self)
        self.combo_target.setMinimumWidth(200)
        self.combo_target.currentTextChanged.connect(self._on_target_changed)
        header_layout.addWidget(self.combo_target)
        
        header_layout.addStretch(1)
        
        btn_clear_all = QPushButton("Tümünü Uygun Yap (✓)")
        btn_clear_all.setStyleSheet("background: #E8F5E9; color: #2E7D32; font-weight: bold; border: 1px solid #A5D6A7; padding: 4px 10px; border-radius: 4px;")
        btn_clear_all.clicked.connect(self._make_all_available)
        header_layout.addWidget(btn_clear_all)
        layout.addLayout(header_layout)
        
        info_lbl = QLabel(
            "<b>Bilgi:</b> Çizelgede kırmızı olan saatler, öğretmenin (veya sınıfın) o saatte "
            "<i>çalışamayacağını (kapalı olduğunu)</i> ifade eder.<br>"
            "Yeşil alanlar müsaittir. Değiştirmek için hücrelere tıklayın."
        )
        info_lbl.setStyleSheet("color: #444444; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(info_lbl)
        
        # Table Grid
        self.table = QTableWidget(self.periods, len(self.days), self)
        self.table.setHorizontalHeaderLabels(self.days)
        self.table.setVerticalHeaderLabels([f"{i+1}. Ders" for i in range(self.periods)])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellClicked.connect(self._on_cell_clicked)
        
        layout.addWidget(self.table, 1)
        
        # Quick Day Buttons Bar (Salı Kapat, Perşembe Kapat vb.)
        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("Hızlı Gün Kapat:", self))
        
        for d_idx, d_name in enumerate(DAYS):
            btn_day = QPushButton(f"{d_name} Kapat")
            btn_day.setStyleSheet("background: #FFEBEE; color: #C62828; border: 1px solid #FFCDD2; border-radius: 4px; padding: 3px 6px; font-size: 11px;")
            btn_day.clicked.connect(lambda ch, idx=d_idx: self._toggle_entire_day(idx, False))
            quick_layout.addWidget(btn_day)
            
        quick_layout.addStretch(1)
        layout.addLayout(quick_layout)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Kaydet ve Kapat")
        btn_save.setStyleSheet("background: #0078D7; color: white; font-weight: bold; padding: 6px 20px; border-radius: 4px;")
        btn_save.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC; padding: 6px 20px; border-radius: 4px;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch(1)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _populate_combo(self):
        self.combo_target.blockSignals(True)
        self.combo_target.clear()
        
        key = "ogretmenler" if self.target_type == "ogretmen" else "siniflar"
        items = self.data_store.get(key, [])
        for item in items:
            self.combo_target.addItem(item.get("ad", ""))
            
        self.combo_target.blockSignals(False)
        self._load_matrix_for_current()

    def _on_target_changed(self):
        self._load_matrix_for_current()

    def _get_current_name(self):
        return self.combo_target.currentText()

    def _load_matrix_for_current(self):
        name = self._get_current_name()
        if not name: return
        
        entity_constraints = self.data_store["kisitlamalar"].get(name, {})
        
        for p in range(self.periods):
            for d in range(len(self.days)):
                cell_key = f"{d},{p}"
                is_available = entity_constraints.get(cell_key, True)
                self._set_cell_state(p, d, is_available)

    def _set_cell_state(self, row, col, is_available):
        item = QTableWidgetItem()
        item.setTextAlignment(Qt.AlignCenter)
        font = QFont("Arial", 11, QFont.Bold)
        item.setFont(font)
        
        if is_available:
            item.setText("✓ Müsait")
            item.setBackground(QBrush(QColor("#E8F5E9")))
            item.setForeground(QBrush(QColor("#2E7D32")))
        else:
            item.setText("✗ KAPALI")
            item.setBackground(QBrush(QColor("#FFEBEE")))
            item.setForeground(QBrush(QColor("#C62828")))
            
        self.table.setItem(row, col, item)
        
        # Save into data_store dict
        name = self._get_current_name()
        if name:
            if name not in self.data_store["kisitlamalar"]:
                self.data_store["kisitlamalar"][name] = {}
            self.data_store["kisitlamalar"][name][f"{col},{row}"] = is_available

    def _on_cell_clicked(self, row, col):
        item = self.table.item(row, col)
        current_available = True
        if item and "KAPALI" in item.text():
            current_available = False
            
        self._set_cell_state(row, col, not current_available)

    def _toggle_entire_day(self, day_idx, target_state):
        for p in range(PERIODS):
            self._set_cell_state(p, day_idx, target_state)

    def _make_all_available(self):
        for p in range(PERIODS):
            for d in range(len(DAYS)):
                self._set_cell_state(p, d, True)
