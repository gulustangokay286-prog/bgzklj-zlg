import os, sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QLineEdit, QComboBox, QCheckBox, QColorDialog, QFrame, QFormLayout, QGridLayout,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QListWidgetItem,
    QMessageBox, QGroupBox, QSpinBox, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QBrush
from database import trigger_save_db
from auto_scheduler import matches_class

def get_asset_path(rel_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, rel_path).replace("\\", "/")
    return os.path.abspath(rel_path).replace("\\", "/")

PASTEL_DISTINCT_COLORS = [
    "#1E88E5", "#43A047", "#FB8C00", "#8E24AA", "#E53935",
    "#00ACC1", "#7CB342", "#FFB300", "#6D4C41", "#546E7A",
    "#3949AB", "#00897B", "#F4511E", "#D81B60", "#00838F",
    "#5E35B1", "#A1887F", "#0097A7", "#C2185B", "#F57C00"
]

def format_tr_name(name_str: str) -> str:
    """Capitalizes Turkish names properly (e.g. 'hüseyin arman' -> 'Hüseyin Arman', 'ali ihsan' -> 'Ali İhsan')."""
    if not name_str:
        return name_str
    words = name_str.strip().split()
    formatted = []
    tr_upper_map = {'i': 'İ', 'ı': 'I', 'ç': 'Ç', 'ğ': 'Ğ', 'ö': 'Ö', 'ş': 'Ş', 'ü': 'Ü'}
    tr_lower_map = {'İ': 'i', 'I': 'ı', 'Ç': 'ç', 'Ğ': 'ğ', 'Ö': 'ö', 'Ş': 'ş', 'Ü': 'ü'}
    
    for w in words:
        if not w:
            continue
        first = w[0]
        rest = w[1:]
        first_cap = tr_upper_map.get(first, first.upper())
        rest_lower = "".join(tr_lower_map.get(c, c.lower()) for c in rest)
        formatted.append(first_cap + rest_lower)
        
    return " ".join(formatted)

def normalize_tr(text: str) -> str:
    """Normalizes Turkish characters and accents for seamless search (e.g. 'i'/'ing' matches 'İngilizce', 'turk' matches 'Türkçe')."""
    if not text:
        return ""
    tr_map = {
        'İ': 'i', 'I': 'i', 'ı': 'i', 'i': 'i',
        'Ç': 'c', 'ç': 'c',
        'Ğ': 'g', 'ğ': 'g',
        'Ö': 'o', 'ö': 'o',
        'Ş': 's', 'ş': 's',
        'Ü': 'u', 'ü': 'u',
    }
    return "".join(tr_map.get(c, c.lower()) for c in str(text))

def parse_distribution_parts(type_str: str, total_duration: int = 0) -> list:
    """
    Parses aSc distribution strings into list of block durations (cards).
    Rules:
    - '2+3' -> [2, 1, 1, 1] (1 çiftli, 3 tekli)
    - '3+2' -> [1, 1, 1, 2]
    - '2+2' -> [2, 2]
    - '2+1' -> [2, 1]
    - '2+2+1' -> [2, 2, 1]
    - '1+1' -> [1, 1]
    - '3' (single number) -> [2, 1]
    """
    type_str = str(type_str or "").strip()
    parts = []
    
    if "+" in type_str:
        raw_parts = [p.strip() for p in type_str.split("+") if p.strip().isdigit()]
        for p in raw_parts:
            val = int(p)
            if val == 3:
                # 3 in composite distribution (e.g. 2+3, 1+3) represents 3 single hours (3 tekli saat)
                parts.extend([1, 1, 1])
            elif val > 0:
                parts.append(val)
    elif type_str.isdigit() and int(type_str) > 0:
        val = int(type_str)
        rem = val
        while rem > 0:
            b = 2 if rem >= 2 else 1
            parts.append(b)
            rem -= b
            
    if not parts and total_duration > 0:
        rem = total_duration
        while rem > 0:
            b = 2 if rem >= 2 else 1
            parts.append(b)
            rem -= b
            
    return parts or ([total_duration] if total_duration > 0 else [2])

def get_subject_color(subject_name: str) -> str:
    """Returns a deterministic, vibrant, distinct color for any subject name."""
    if not subject_name:
        return "#1E88E5"
    hash_val = sum(ord(c) * (i + 1) for i, c in enumerate(subject_name.strip()))
    return PASTEL_DISTINCT_COLORS[hash_val % len(PASTEL_DISTINCT_COLORS)]


class BaseEditForm(QDialog):
    def __init__(self, title, parent=None, existing_data=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(540, 680)
        self.setMinimumSize(520, 560)
        self.existing_data = existing_data or {}
        
        self.setStyleSheet("""
            QDialog { background-color: #F4F6F9; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; }
            QGroupBox { font-weight: bold; margin-top: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px 0 3px; }
            QLabel { border: none; background: transparent; color: #333; font-size: 13px; }
            QLineEdit { min-height: 28px; padding: 3px 8px; border: 1px solid #CCCCCC; border-radius: 4px; background: #FFFFFF; font-size: 13px; color: #333; }
            QLineEdit:focus { border: 1px solid #0078D7; }
            QComboBox { min-height: 28px; padding: 3px 8px; border: 1px solid #CCCCCC; border-radius: 4px; background: #FFFFFF; font-size: 13px; color: #333; }
            QPushButton { min-height: 28px; padding: 4px 12px; border: 1px solid #CCCCCC; border-radius: 4px; background: #F8F9FA; font-size: 13px; color: #333; }
            QPushButton:hover { background: #EAEAEA; }
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 12)
        self.main_layout.setSpacing(12)

    def _add_bottom_buttons(self):
        self.main_layout.addStretch(1)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        btn_tamam = QPushButton("Tamam")
        btn_tamam.setFixedSize(80, 28)
        btn_tamam.setStyleSheet("border: 1px solid #1E6DB5; color: #1E6DB5; background: #FFFFFF;")
        btn_tamam.clicked.connect(self.accept)
        
        btn_iptal = QPushButton("İptal")
        btn_iptal.setFixedSize(80, 28)
        btn_iptal.clicked.connect(self.reject)
        
        bottom.addWidget(btn_tamam)
        bottom.addWidget(btn_iptal)
        self.main_layout.addLayout(bottom)


class CustomFieldsDialog(QDialog):
    """aSc Standartlarında Özel Alanlar (Custom Fields) Yönetim Penceresi"""
    def __init__(self, entity_name, entity_type="Öğretmen", custom_fields=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Özel Alanlar - {entity_name}")
        self.setFixedSize(520, 440)
        self.custom_fields = dict(custom_fields or {})
        
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; }
            QLabel { color: #1E293B; font-size: 13px; }
            QTableWidget { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; }
            QLineEdit { min-height: 28px; padding: 2px 8px; border: 1px solid #CBD5E1; border-radius: 4px; }
            QLineEdit:focus { border: 1px solid #0078D7; }
            QPushButton { min-height: 28px; padding: 4px 12px; border: 1px solid #CBD5E1; border-radius: 4px; background: #FFFFFF; font-weight: 500; }
            QPushButton:hover { background: #F1F5F9; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        # Header Info Card
        header_card = QFrame()
        header_card.setStyleSheet("background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 8px;")
        h_lay = QVBoxLayout(header_card)
        lbl_info = QLabel(f"<b>{entity_type}:</b> {entity_name} için özel alan ve meta verileri tanımlayın.")
        lbl_info.setStyleSheet("color: #1D4ED8; font-size: 13px;")
        h_lay.addWidget(lbl_info)
        lbl_sub = QLabel("Bu alanlar aSc standartlarında raporlarda, özel filtrelerde ve veri aktarımlarında kullanılır.")
        lbl_sub.setStyleSheet("color: #3B82F6; font-size: 11px;")
        h_lay.addWidget(lbl_sub)
        layout.addWidget(header_card)
        
        # Presets Buttons
        presets_lay = QHBoxLayout()
        presets_lay.addWidget(QLabel("<b>Hızlı Şablon:</b>"))
        
        presets = ["Telefon", "E-Posta", "Sicil / TC", "Branş", "Notlar"]
        for p_name in presets:
            btn = QPushButton(p_name)
            btn.setStyleSheet("font-size: 11px; padding: 3px 8px; background: #F1F5F9;")
            btn.clicked.connect(lambda _, n=p_name: self._add_field(n, ""))
            presets_lay.addWidget(btn)
            
        presets_lay.addStretch(1)
        layout.addLayout(presets_lay)
        
        # Table of Custom Fields
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Alan Adı (Örn: Telefon)", "Değer (Örn: 0555 123 4567)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # Action Buttons below table
        btn_bar = QHBoxLayout()
        btn_add = QPushButton("+ Yeni Alan Ekle")
        btn_add.setStyleSheet("background: #E0F2FE; color: #0284C7; font-weight: bold;")
        btn_add.clicked.connect(lambda: self._add_field("", ""))
        
        btn_del = QPushButton("Seçiliyi Sil")
        btn_del.setStyleSheet("background: #FEE2E2; color: #DC2626;")
        btn_del.clicked.connect(self._delete_selected_row)
        
        btn_bar.addWidget(btn_add)
        btn_bar.addWidget(btn_del)
        btn_bar.addStretch(1)
        layout.addLayout(btn_bar)
        
        # Bottom Save/Cancel
        bot = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedSize(90, 32)
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Kaydet")
        btn_save.setFixedSize(110, 32)
        btn_save.setStyleSheet("background: #0078D7; color: white; font-weight: bold; border-radius: 4px;")
        btn_save.clicked.connect(self._save_and_accept)
        
        bot.addStretch(1)
        bot.addWidget(btn_cancel)
        bot.addWidget(btn_save)
        layout.addLayout(bot)
        
        self._populate_fields()
        
    def _populate_fields(self):
        self.table.setRowCount(0)
        for k, v in self.custom_fields.items():
            self._add_field(k, v)
            
    def _add_field(self, key="", val=""):
        r = self.table.rowCount()
        self.table.insertRow(r)
        
        item_k = QLineEdit(key)
        item_k.setPlaceholderText("Alan Adı")
        self.table.setCellWidget(r, 0, item_k)
        
        item_v = QLineEdit(str(val))
        item_v.setPlaceholderText("Değer")
        self.table.setCellWidget(r, 1, item_v)
        
    def _delete_selected_row(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)
            
    def _save_and_accept(self):
        res = {}
        for r in range(self.table.rowCount()):
            w_k = self.table.cellWidget(r, 0)
            w_v = self.table.cellWidget(r, 1)
            k = w_k.text().strip() if w_k else ""
            v = w_v.text().strip() if w_v else ""
            if k:
                res[k] = v
        self.custom_fields = res
        self.accept()
        
    def get_data(self):
        return self.custom_fields


class NoScrollComboBox(QComboBox):
    """Mouse wheel scrolling over combobox is ignored unless dropdown popup is actively open, preventing accidental changes."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        
    def wheelEvent(self, event):
        if self.view() and self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()


from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import Signal, QPoint, QEvent

class SearchableComboBox(QWidget):
    """
    Searchable ComboBox with complete Turkish & English character insensitive filtering.
    Avoids Qt C++ QCompleter ASCII bugs by using custom Python-level Turkish normalization and floating popup.
    """
    currentTextChanged = Signal(str)
    
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self._all_items = list(items or [])
        
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        
        lay.setAlignment(Qt.AlignVCenter)
        
        self.edit = QLineEdit(self)
        self.edit.setFixedHeight(28)
        self.edit.setPlaceholderText("Ders Ara veya Seç...")
        self.edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #CBD5E1;
                border-right: none;
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
                padding: 2px 8px;
                background: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
                color: #0F172A;
            }
            QLineEdit:focus {
                border-color: #2563EB;
            }
        """)
        lay.addWidget(self.edit, 1)
        
        self.btn_drop = QPushButton("▼", self)
        self.btn_drop.setFixedSize(28, 28)
        self.btn_drop.setCursor(Qt.PointingHandCursor)
        self.btn_drop.setStyleSheet("""
            QPushButton {
                border: 1px solid #CBD5E1;
                border-left: none;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background: #F8FAFC;
                color: #64748B;
                font-size: 10px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                background: #E2E8F0;
                color: #1E293B;
            }
        """)
        lay.addWidget(self.btn_drop)
        
        # Floating Popup List
        self.popup = QListWidget()
        self.popup.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.popup.setFocusPolicy(Qt.NoFocus)
        self.popup.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.popup.setStyleSheet("""
            QListWidget {
                border: 1px solid #94A3B8;
                border-radius: 4px;
                background: #FFFFFF;
                font-size: 13px;
                font-weight: 500;
                color: #0F172A;
                padding: 2px;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-radius: 3px;
            }
            QListWidget::item:hover {
                background: #EFF6FF;
                color: #1D4ED8;
            }
            QListWidget::item:selected {
                background: #2563EB;
                color: #FFFFFF;
            }
        """)
        
        # Signals
        self.edit.textEdited.connect(self._on_text_edited)
        self.edit.returnPressed.connect(self._on_return_pressed)
        self.btn_drop.clicked.connect(self._toggle_popup)
        self.popup.itemClicked.connect(self._on_item_clicked)
        
        self.edit.installEventFilter(self)
        
    def addItems(self, items):
        self._all_items = list(items)
        
    def setItems(self, items):
        self._all_items = list(items)
        
    def currentText(self):
        return self.edit.text().strip()
        
    def setCurrentText(self, text):
        self.edit.setText(text)
        self.currentTextChanged.emit(text)
        
    def setCurrentIndex(self, idx):
        if 0 <= idx < len(self._all_items):
            self.setCurrentText(self._all_items[idx])
        elif idx == -1:
            self.edit.clear()
            
    def findText(self, text, flags=None):
        t_norm = normalize_tr(text.strip())
        for i, item in enumerate(self._all_items):
            if normalize_tr(item) == t_norm:
                return i
        return -1
        
    def count(self):
        return len(self._all_items)
        
    def itemText(self, idx):
        return self._all_items[idx] if 0 <= idx < len(self._all_items) else ""
        
    def lineEdit(self):
        return self.edit
        
    def setMinimumWidth(self, w):
        super().setMinimumWidth(w)
        self.edit.setMinimumWidth(max(0, w - 30))
        
    def _filter_items(self, query):
        q_norm = normalize_tr(query.strip())
        if not q_norm:
            return list(self._all_items)
        prefix = [s for s in self._all_items if normalize_tr(s).startswith(q_norm)]
        substr = [s for s in self._all_items if q_norm in normalize_tr(s) and s not in prefix]
        return prefix + substr
        
    def _on_text_edited(self, text):
        matches = self._filter_items(text)
        self._show_popup_with_items(matches)
        
    def _show_popup_with_items(self, items):
        self.popup.clear()
        if not items:
            self.popup.hide()
            return
        for s in items:
            self.popup.addItem(QListWidgetItem(s))
        self.popup.setCurrentRow(0)
        
        # Position popup under lineEdit
        if self.isVisible():
            pos = self.edit.mapToGlobal(QPoint(0, self.edit.height()))
            self.popup.setFixedWidth(max(self.width(), 260))
            item_h = 28
            h = min(240, max(40, len(items) * item_h + 8))
            self.popup.setFixedHeight(h)
            self.popup.move(pos)
            self.popup.show()
        
    def _toggle_popup(self):
        if self.popup.isVisible():
            self.popup.hide()
        else:
            self._show_popup_with_items(self._filter_items(self.edit.text()))
            
    def _on_item_clicked(self, item):
        self.setCurrentText(item.text())
        self.popup.hide()
        self.edit.setFocus()
        
    def _on_return_pressed(self):
        if self.popup.isVisible() and self.popup.count() > 0:
            cur = self.popup.currentItem() or self.popup.item(0)
            if cur:
                self.setCurrentText(cur.text())
            self.popup.hide()
        else:
            matches = self._filter_items(self.edit.text())
            if matches:
                self.setCurrentText(matches[0])
            
    def eventFilter(self, obj, event):
        from PySide6.QtCore import QTimer
        if obj == self.edit and event.type() == QEvent.FocusOut:
            QTimer.singleShot(150, self.popup.hide)
            
        if obj == self.edit and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Down:
                if self.popup.isVisible():
                    row = min(self.popup.count() - 1, self.popup.currentRow() + 1)
                    self.popup.setCurrentRow(row)
                    return True
                else:
                    self._toggle_popup()
                    return True
            elif event.key() == Qt.Key_Up:
                if self.popup.isVisible():
                    row = max(0, self.popup.currentRow() - 1)
                    self.popup.setCurrentRow(row)
                    return True
            elif event.key() == Qt.Key_Escape:
                if self.popup.isVisible():
                    self.popup.hide()
                    return True
        return super().eventFilter(obj, event)


class SubjectClassMultiSelectDialog(QDialog):
    """Her ders için bağımsız sınıf seçimi ve sınıf bazlı saat/format belirleme modal penceresi"""
    def __init__(self, subject_name, all_classes, selected_classes=None, default_distribution="2", class_configs=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Sınıf(lar) Ata — {subject_name}")
        self.resize(520, 560)
        self.setMinimumSize(480, 480)
        self.selected_classes = list(selected_classes or [])
        self.default_distribution = str(default_distribution or "2")
        self.class_configs = dict(class_configs or {})
        
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; }
            QLabel { color: #1E293B; font-size: 13px; }
            QCheckBox { font-size: 13px; font-weight: 600; padding: 4px; color: #0F172A; }
            QComboBox { min-height: 26px; padding: 2px 6px; border: 1px solid #CBD5E1; border-radius: 4px; background: #FFFFFF; font-size: 12px; font-weight: bold; color: #1E293B; }
            QPushButton { min-height: 30px; padding: 4px 12px; border: 1px solid #CBD5E1; border-radius: 4px; background: #FFFFFF; font-weight: 500; font-size: 13px; }
            QPushButton:hover { background: #F1F5F9; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        card = QFrame()
        card.setStyleSheet("background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 8px;")
        c_lay = QVBoxLayout(card)
        lbl_h = QLabel(f"<b>{subject_name}</b> Dersi İçin Sınıfları ve Saat Formatını Seçin")
        lbl_h.setStyleSheet("color: #166534; font-size: 13px;")
        c_lay.addWidget(lbl_h)
        lbl_s = QLabel("Her sınıf için bağımsız saat formatı (Örn: 11A = 3 saat 2+1, 9A = 4 saat 2+2) belirleyebilirsiniz.")
        lbl_s.setStyleSheet("color: #15803D; font-size: 11px;")
        c_lay.addWidget(lbl_s)
        layout.addWidget(card)
        
        # Search Filter
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Sınıf Ara...")
        self.txt_filter.textChanged.connect(self._filter_list)
        layout.addWidget(self.txt_filter)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; }")
        w = QWidget()
        w.setStyleSheet("background: #FFFFFF;")
        self.v_lay = QVBoxLayout(w)
        self.v_lay.setContentsMargins(10, 10, 10, 10)
        self.v_lay.setSpacing(6)
        
        self.row_items = []
        DISTRIBUTIONS = ["1", "2", "3", "4", "5", "6", "1+1", "2+1", "2+2", "3+1", "3+2", "4+2", "3+3", "2+2+1", "2+2+2", "3+2+1"]
        
        for c in sorted(all_classes):
            row_w = QWidget()
            r_lay = QHBoxLayout(row_w)
            r_lay.setContentsMargins(4, 2, 4, 2)
            
            chk = QCheckBox(c)
            is_checked = (c in self.selected_classes)
            chk.setChecked(is_checked)
            
            cb_tip = NoScrollComboBox()
            cb_tip.setEditable(True)
            cb_tip.addItems(DISTRIBUTIONS)
            
            cur_cfg = self.class_configs.get(c, {})
            typ = cur_cfg.get("type", self.default_distribution)
            idx_t = cb_tip.findText(typ)
            if idx_t >= 0:
                cb_tip.setCurrentIndex(idx_t)
            else:
                cb_tip.setCurrentText(typ)
                
            cb_tip.setEnabled(is_checked)
            cb_tip.setFixedWidth(110)
            
            chk.toggled.connect(cb_tip.setEnabled)
            
            lbl_hour_badge = QLabel("Saat/Format:")
            lbl_hour_badge.setStyleSheet("color: #64748B; font-size: 11px;")
            
            r_lay.addWidget(chk, 1)
            r_lay.addStretch(1)
            r_lay.addWidget(lbl_hour_badge)
            r_lay.addWidget(cb_tip)
            
            self.v_lay.addWidget(row_w)
            self.row_items.append({"widget": row_w, "chk": chk, "cb_tip": cb_tip, "class_name": c})
            
        self.v_lay.addStretch(1)
        scroll.setWidget(w)
        layout.addWidget(scroll)
        
        bot = QHBoxLayout()
        btn_sel_all = QPushButton("Tümünü Seç / Kaldır")
        btn_sel_all.clicked.connect(self._toggle_all)
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("Seçimi Onayla")
        btn_ok.setStyleSheet("background: #0078D7; color: white; font-weight: bold;")
        btn_ok.clicked.connect(self._accept_selection)
        
        bot.addWidget(btn_sel_all)
        bot.addStretch(1)
        bot.addWidget(btn_cancel)
        bot.addWidget(btn_ok)
        layout.addLayout(bot)
        
    def _filter_list(self, text):
        q = text.strip().lower()
        for item in self.row_items:
            visible = (q in item["class_name"].lower() if q else True)
            item["widget"].setVisible(visible)
            
    def _toggle_all(self):
        visible_items = [i for i in self.row_items if i["widget"].isVisible()]
        all_checked = all(i["chk"].isChecked() for i in visible_items)
        for i in visible_items:
            i["chk"].setChecked(not all_checked)
            
    def _accept_selection(self):
        self.selected_classes = []
        self.class_configs = {}
        for item in self.row_items:
            if item["chk"].isChecked():
                c = item["class_name"]
                t_val = item["cb_tip"].currentText().strip() or "2"
                if "+" in t_val:
                    parts = [int(p.strip()) for p in t_val.split("+") if p.strip().isdigit()]
                    dur = sum(parts) if parts else 1
                else:
                    dur = int(t_val) if t_val.isdigit() else 1
                self.selected_classes.append(c)
                self.class_configs[c] = {"type": t_val, "duration": dur}
        self.accept()
        
    def get_selected(self):
        return self.selected_classes
        
    def get_configs(self):
        return self.class_configs


class CombinedClassesDialog(QDialog):
    """Birleşik / Ortak Ders Oluşturma ve Sınıf Eşleştirme Penceresi (aSc Tarzı)"""
    def __init__(self, data_store=None, selected_classes=None, parent=None, subject_name="", duration="2", teacher_name=""):
        super().__init__(parent)
        self.setWindowTitle("Birleşik / Ortak Ders Oluştur")
        self.setFixedSize(540, 620)
        self.data_store = data_store or {}
        self.selected_classes = list(selected_classes or [])
        self.init_subject = subject_name or ""
        self.init_duration = str(duration or "2")
        self.init_teacher = teacher_name or ""
        self.bypass_conflict = False
        
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; }
            QLabel { color: #1E293B; font-size: 13px; }
            QComboBox { min-height: 28px; padding: 2px 6px; border: 1px solid #CBD5E1; border-radius: 4px; background: #FFFFFF; font-size: 13px; }
            QComboBox:focus { border: 1px solid #0078D7; }
            QPushButton { min-height: 30px; padding: 4px 12px; border: 1px solid #CBD5E1; border-radius: 4px; background: #FFFFFF; font-weight: 500; }
            QPushButton:hover { background: #F1F5F9; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        # Info Header
        info_card = QFrame()
        info_card.setStyleSheet("background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px; padding: 8px;")
        info_lay = QVBoxLayout(info_card)
        lbl_h = QLabel("🔗 <b>Birleşik / Ortak Ders Tanımlama</b> (En az 2 sınıf gereklidir)")
        lbl_h.setStyleSheet("color: #92400E; font-size: 13px;")
        info_lay.addWidget(lbl_h)
        lbl_sub = QLabel("Farklı sınıflar veya gruplar aynı saatte, aynı öğretmenle ortak ders işleyecek şekilde eşleştirilir.")
        lbl_sub.setStyleSheet("color: #B45309; font-size: 11px;")
        info_lay.addWidget(lbl_sub)
        layout.addWidget(info_card)
        
        # 1. Ders ve Saat Seçim Kartı
        meta_frame = QFrame()
        meta_frame.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px;")
        meta_lay = QGridLayout(meta_frame)
        meta_lay.setContentsMargins(12, 10, 12, 10)
        meta_lay.setHorizontalSpacing(10)
        meta_lay.setVerticalSpacing(8)
        
        meta_lay.addWidget(QLabel("<b>Ders Seçimi:</b>"), 0, 0)
        self.cb_subject = SearchableComboBox()
        all_subjs = sorted(list({d.get("ad", "").strip() for d in self.data_store.get("dersler", []) if d.get("ad", "").strip()}))
        self.cb_subject.addItems(all_subjs)
        if self.init_subject:
            self.cb_subject.setCurrentText(self.init_subject)
        meta_lay.addWidget(self.cb_subject, 0, 1)
        
        meta_lay.addWidget(QLabel("<b>Haftalık Saat / Dağılım:</b>"), 0, 2)
        self.cb_tip = NoScrollComboBox()
        self.cb_tip.setEditable(True)
        self.cb_tip.addItems(["1", "2", "3", "4", "5", "6", "1+1", "2+1", "2+2", "3+1", "3+2", "4+2", "3+3", "2+2+1", "2+2+2"])
        if self.init_duration:
            idx_t = self.cb_tip.findText(self.init_duration)
            if idx_t >= 0: self.cb_tip.setCurrentIndex(idx_t)
            else: self.cb_tip.setCurrentText(self.init_duration)
        meta_lay.addWidget(self.cb_tip, 0, 3)
        
        meta_lay.addWidget(QLabel("<b>Öğretmen:</b>"), 1, 0)
        self.cb_teacher = NoScrollComboBox()
        self.cb_teacher.setEditable(True)
        all_t = sorted([t.get("ad", "") for t in self.data_store.get("ogretmenler", []) if t.get("ad")])
        self.cb_teacher.addItems(all_t)
        if self.init_teacher:
            idx_tea = self.cb_teacher.findText(self.init_teacher)
            if idx_tea >= 0: self.cb_teacher.setCurrentIndex(idx_tea)
            else: self.cb_teacher.setCurrentText(self.init_teacher)
        meta_lay.addWidget(self.cb_teacher, 1, 1, 1, 3)
        
        layout.addWidget(meta_frame)
        
        # 2. Birleştirilecek Sınıflar Kartı
        rows_frame = QFrame()
        rows_frame.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px;")
        rows_lay = QVBoxLayout(rows_frame)
        rows_lay.setContentsMargins(12, 10, 12, 10)
        rows_lay.setSpacing(6)
        
        header_lay = QHBoxLayout()
        lbl_c = QLabel("<b>Birleştirilecek Sınıf</b>")
        lbl_g = QLabel("<b>Grup / Alt Kısım</b>")
        header_lay.addWidget(lbl_c, 1)
        header_lay.addWidget(lbl_g, 1)
        rows_lay.addLayout(header_lay)
        
        classes = [""] + sorted([c.get("ad", "") for c in self.data_store.get("siniflar", []) if c.get("ad")])
        groups = ["Bütün Sınıf", "Grup 1", "Grup 2", "Erkekler", "Kızlar", "Seçmeli Ders"]
        
        self.rows = []
        for i in range(8):
            row_lay = QHBoxLayout()
            cb_class = NoScrollComboBox()
            cb_class.addItems(classes)
            cb_group = NoScrollComboBox()
            cb_group.addItems(groups)
            
            row_lay.addWidget(cb_class, 1)
            row_lay.addWidget(cb_group, 1)
            rows_lay.addLayout(row_lay)
            self.rows.append((cb_class, cb_group))
            
        layout.addWidget(rows_frame)
        
        # Load existing
        self._load_existing()
        
        # Conflict Warning Label
        self.lbl_conflict = QLabel("")
        self.lbl_conflict.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: bold; padding: 4px;")
        self.lbl_conflict.setWordWrap(True)
        self.lbl_conflict.setVisible(False)
        layout.addWidget(self.lbl_conflict)
        
        # Bottom Buttons
        bot = QHBoxLayout()
        self.btn_clear = QPushButton("🗑️ Birleşik Sınıfı Kaldır")
        self.btn_clear.setStyleSheet("background: #FEE2E2; color: #DC2626; font-weight: bold; border: 1px solid #FECACA; border-radius: 4px; padding: 6px 12px;")
        self.btn_clear.clicked.connect(self._do_clear)
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedSize(80, 32)
        btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QPushButton("✅ Birleşik Dersi Onayla")
        self.btn_ok.setFixedSize(170, 32)
        self.btn_ok.setStyleSheet("background: #0078D7; color: white; font-weight: bold; border-radius: 4px;")
        self.btn_ok.clicked.connect(self._do_accept)
        
        bot.addWidget(self.btn_clear)
        bot.addStretch(1)
        bot.addWidget(btn_cancel)
        bot.addWidget(self.btn_ok)
        layout.addLayout(bot)
        
    def _load_existing(self):
        import re
        raw_list = []
        if isinstance(self.selected_classes, str):
            raw_list = [p.strip() for p in self.selected_classes.replace("&", "+").replace(",", "+").split("+") if p.strip()]
        elif isinstance(self.selected_classes, (list, tuple, set)):
            for item in self.selected_classes:
                if isinstance(item, str):
                    for sub in item.replace("&", "+").replace(",", "+").split("+"):
                        if sub.strip():
                            raw_list.append(sub.strip())
                            
        for i, item in enumerate(raw_list):
            if i >= 8: break
            m = re.match(r"^(.*?)\s*\((.*?)\)$", item.strip())
            if m:
                c_name = m.group(1).strip()
                g_name = m.group(2).strip()
            else:
                c_name = item.strip()
                g_name = "Bütün Sınıf"
                
            idx_c = self.rows[i][0].findText(c_name)
            if idx_c < 0:
                for idx in range(self.rows[i][0].count()):
                    if self.rows[i][0].itemText(idx).strip().upper() == c_name.upper():
                        idx_c = idx
                        break
            if idx_c >= 0: self.rows[i][0].setCurrentIndex(idx_c)
            
            idx_g = self.rows[i][1].findText(g_name)
            if idx_g < 0:
                for idx in range(self.rows[i][1].count()):
                    if g_name.upper() in self.rows[i][1].itemText(idx).upper():
                        idx_g = idx
                        break
            if idx_g >= 0: self.rows[i][1].setCurrentIndex(idx_g)

    def _do_clear(self):
        for cb_c, cb_g in self.rows:
            cb_c.setCurrentIndex(0)
            cb_g.setCurrentIndex(0)
        self.selected_classes = []
        self.accept()
        
    def get_selected_classes(self):
        sel = []
        for cb_c, cb_g in self.rows:
            c_name = cb_c.currentText().strip()
            g_name = cb_g.currentText().strip()
            if c_name:
                if g_name == "Bütün Sınıf":
                    sel.append(c_name)
                else:
                    sel.append(f"{c_name} ({g_name})")
        return sel

    def get_combined_string(self):
        sel = self.get_selected_classes()
        return " + ".join(sel)

    def get_subject(self):
        return self.cb_subject.currentText().strip()

    def get_teacher(self):
        return self.cb_teacher.currentText().strip()

    def get_type(self):
        return self.cb_tip.currentText().strip() or "2"

    def get_duration(self):
        t_val = self.get_type()
        if "+" in t_val:
            parts = [int(p.strip()) for p in t_val.split("+") if p.strip().isdigit()]
            return sum(parts) if parts else 2
        return int(t_val) if t_val.isdigit() else 2

    def _do_accept(self):
        subj = self.get_subject()
        if not subj:
            QMessageBox.warning(self, "Ders Seçimi Gerekli", "Lütfen birleşik ders için atanacak Dersi seçiniz veya yazınız!")
            self.cb_subject.setFocus()
            return
            
        sel = self.get_selected_classes()
        if len(sel) == 0:
            self.selected_classes = []
            self.accept()
            return
        if len(sel) < 2:
            QMessageBox.warning(self, "Yetersiz Sınıf Seçimi", "Birleşik sınıf oluşturabilmek için en az 2 sınıf seçiniz veya seçimi temizlemek için 'Birleşik Sınıfı Kaldır' butonuna basınız.")
            return
            
        self.selected_classes = sel
        self.accept()


class LessonAssignmentDialog(QDialog):
    """
    Gelişmiş Çoklu Ders, Sınıf ve Birleşik Ders Atama Paneli
    """
    def __init__(self, *args, **kwargs):
        data_store = kwargs.get("data_store")
        parent = kwargs.get("parent")
        existing_data = kwargs.get("existing_data")
        
        for arg in args:
            if isinstance(arg, dict) and data_store is None:
                data_store = arg
            elif isinstance(arg, QWidget) and parent is None:
                parent = arg
                
        super().__init__(parent)
        self.setWindowTitle("Öğretmene Ders ve Sınıf Atama Paneli")
        self.resize(800, 720)
        self.setMinimumSize(720, 640)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; }
            QLabel { border: none; background: transparent; color: #1E293B; font-size: 13px; }
            QLineEdit, QComboBox { min-height: 30px; padding: 3px 8px; border: 1px solid #CBD5E1; border-radius: 4px; background: #FFFFFF; font-size: 13px; color: #1E293B; }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #0078D7; }
            QPushButton { min-height: 30px; padding: 4px 12px; border: 1px solid #CBD5E1; border-radius: 4px; background: #FFFFFF; font-size: 13px; color: #1E293B; font-weight: 500; }
            QPushButton:hover { background: #F1F5F9; }
        """)
        self.existing_data = existing_data or {}
        self.data_store = data_store or {}
        self.selected_teacher = kwargs.get("selected_teacher") or kwargs.get("target_teacher")
        self.subject_rows = []
        
        self._build_ui()
        self._load_teacher_initial_data()
        
    def _create_row_frame(self):
        f = QFrame()
        f.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }")
        return f

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; } QWidget#scrollContent { background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(12)
        
        # 1. Öğretmen Seçim Kartı
        row1 = self._create_row_frame()
        l1 = QHBoxLayout(row1)
        l1.setContentsMargins(14, 12, 14, 12)
        
        v1 = QVBoxLayout()
        lbl_ogr = QLabel("<b>Atanacak Öğretmen</b>")
        lbl_ogr.setStyleSheet("color: #0F172A; font-size: 13px;")
        v1.addWidget(lbl_ogr)
        self.cb_ogretmen = NoScrollComboBox()
        self.cb_ogretmen.setMinimumWidth(280)
        self.cb_ogretmen.currentTextChanged.connect(self._on_teacher_changed)
        v1.addWidget(self.cb_ogretmen)
        l1.addLayout(v1)
        l1.addStretch(1)
        self.scroll_layout.addWidget(row1)
        
        # 2. Atanacak Dersler Kartı
        row2 = self._create_row_frame()
        self.l2_main = QVBoxLayout(row2)
        self.l2_main.setContentsMargins(14, 12, 14, 12)
        self.l2_main.setSpacing(10)
        
        # Header (Clean Title Only - Row level combined buttons exist per input)
        h_ders_head = QHBoxLayout()
        lbl_dersler_title = QLabel("<b>Atanacak Dersler</b> (Bireysel veya Birleşik Sınıf Eşleme)")
        lbl_dersler_title.setStyleSheet("color: #0F172A; font-size: 13px;")
        h_ders_head.addWidget(lbl_dersler_title)
        h_ders_head.addStretch(1)
        
        self.l2_main.addLayout(h_ders_head)
        
        # Container for dynamic subject rows
        self.subjects_container = QVBoxLayout()
        self.subjects_container.setSpacing(8)
        self.l2_main.addLayout(self.subjects_container)
        
        self.scroll_layout.addWidget(row2)
        
        # 3. Sınıf / Sınıflarım Özet Kartı
        row3 = self._create_row_frame()
        l3 = QHBoxLayout(row3)
        l3.setContentsMargins(14, 12, 14, 12)
        
        v3 = QVBoxLayout()
        lbl_sinif = QLabel("<b>Tüm Atanan Sınıflar (Genel Özet)</b>")
        lbl_sinif.setStyleSheet("color: #0F172A; font-size: 13px;")
        v3.addWidget(lbl_sinif)
        
        self.txt_classes_summary = QLineEdit()
        self.txt_classes_summary.setReadOnly(True)
        self.txt_classes_summary.setPlaceholderText("Derslere atanan sınıflar burada otomatik listelenir (Örn: 9A, 10B, 11A + 10B)")
        self.txt_classes_summary.setStyleSheet("background: #F1F5F9; color: #0F172A; font-weight: bold;")
        v3.addWidget(self.txt_classes_summary)
        l3.addLayout(v3)
        self.scroll_layout.addWidget(row3)
        
        # 4. Canlı Özet Çubuğu
        self.lbl_ozet = QLabel("Otomatik Eşleşme: -")
        self.lbl_ozet.setStyleSheet("background: #EFF6FF; color: #1D4ED8; font-weight: bold; border-radius: 6px; padding: 10px; border: 1px solid #BFDBFE;")
        self.scroll_layout.addWidget(self.lbl_ozet)
        
        self.scroll_layout.addStretch(1)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # Bottom Buttons
        bot_lay = QHBoxLayout()
        btn_iptal = QPushButton("İptal")
        btn_iptal.setFixedSize(100, 36)
        btn_iptal.clicked.connect(self.reject)
        
        btn_tamam = QPushButton("Tamam ve Kaydet")
        btn_tamam.setFixedSize(170, 36)
        btn_tamam.setStyleSheet("background: #0078D7; color: white; font-weight: bold; border-radius: 4px;")
        btn_tamam.clicked.connect(self.accept)
        
        bot_lay.addWidget(btn_iptal)
        bot_lay.addStretch(1)
        bot_lay.addWidget(btn_tamam)
        main_layout.addLayout(bot_lay)

    def _get_all_subjects(self):
        return sorted(list({d.get("ad", "").strip() for d in self.data_store.get("dersler", []) if d.get("ad", "").strip()}))

    def _get_all_classes(self):
        if self.data_store:
            return sorted([c.get("ad", "") for c in self.data_store.get("siniflar", []) if c.get("ad")])
        return []

    def _add_subject_row(self, subject_name="", hours="2", distribution="2", assigned_classes=None, class_configs=None, is_combined=False, combined_classes=None):
        row_widget = QWidget()
        row_widget.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 4px;")
        row_layout = QVBoxLayout(row_widget)
        row_layout.setContentsMargins(8, 8, 8, 8)
        row_layout.setSpacing(6)
        
        top_h = QHBoxLayout()
        
        # Subject Combo (Searchable with Turkish-aware real-time search)
        cb_subject = SearchableComboBox()
        cb_subject.setMinimumWidth(220)
        all_subjs = self._get_all_subjects()
        cb_subject.addItems(all_subjs)
        
        if cb_subject.lineEdit():
            cb_subject.lineEdit().setPlaceholderText("Ders Ara veya Seç...")
            
        if subject_name:
            cb_subject.setCurrentText(subject_name)
        else:
            cb_subject.setCurrentIndex(-1)
            if cb_subject.lineEdit():
                cb_subject.lineEdit().clear()
                cb_subject.lineEdit().setPlaceholderText("Ders Ara veya Seç...")
            
        top_h.addWidget(cb_subject, 2)
        
        # Hours / Tip Combo
        cb_tip = NoScrollComboBox()
        cb_tip.setMinimumWidth(90)
        cb_tip.setEditable(True)
        cb_tip.addItems(["1", "2", "3", "4", "5", "6", "1+1", "2+1", "2+2", "3+1", "3+2", "4+2", "3+3", "2+2+1", "2+2+2", "3+2+1"])
        if distribution:
            idx_t = cb_tip.findText(distribution)
            if idx_t >= 0: cb_tip.setCurrentIndex(idx_t)
            else: cb_tip.setCurrentText(distribution)
        top_h.addWidget(cb_tip, 1)
        
        # Sınıfları Seç Butonu
        btn_classes = QPushButton("🏫 Sınıf(lar) Ata...")
        btn_classes.setStyleSheet("background: #F0FDF4; color: #166534; font-weight: bold; border: 1px solid #BBF7D0;")
        top_h.addWidget(btn_classes, 1)
        
        # Birleşik Sınıf Butonu
        btn_comb = QPushButton("🔗 Birleşik Sınıf...")
        btn_comb.setStyleSheet("background: #FFFBEB; color: #B45309; font-weight: bold; border: 1px solid #FDE68A;")
        top_h.addWidget(btn_comb, 1)
        
        # Sil Butonu
        btn_del = QPushButton("X")
        btn_del.setFixedSize(30, 30)
        btn_del.setStyleSheet("background: #FEE2E2; color: #DC2626; font-weight: bold; border: 1px solid #FECACA;")
        top_h.addWidget(btn_del)
        
        row_layout.addLayout(top_h)
        
        # Badge showing assigned classes for this row with their individual hours
        lbl_classes_badge = QLabel("Atanan Sınıflar: Belirtilmedi")
        lbl_classes_badge.setStyleSheet("color: #0369A1; font-size: 11px; font-weight: bold; padding: 3px 6px; border-radius: 4px;")
        row_layout.addWidget(lbl_classes_badge)
        
        comb_cls_list = list(combined_classes or [])
        if not comb_cls_list and is_combined and assigned_classes:
            for item in assigned_classes:
                for p in str(item).replace("&", "+").replace(",", "+").split("+"):
                    if p.strip() and p.strip() not in comb_cls_list:
                        comb_cls_list.append(p.strip())
                        
        row_data = {
            "widget": row_widget,
            "cb_subject": cb_subject,
            "cb_tip": cb_tip,
            "lbl_badge": lbl_classes_badge,
            "classes": list(assigned_classes or []),
            "class_configs": dict(class_configs or {}),
            "is_combined": bool(is_combined),
            "combined_classes": comb_cls_list
        }
        self.subject_rows.append(row_data)
        self.subjects_container.addWidget(row_widget)
        
        # Connect signals
        btn_classes.clicked.connect(lambda: self._edit_classes_for_row(row_data))
        btn_comb.clicked.connect(lambda: self._edit_combined_for_row(row_data))
        btn_del.clicked.connect(lambda: self._remove_subject_row(row_data))
        
        cb_subject.currentTextChanged.connect(lambda t: self._on_subject_changed(row_data, t))
        cb_tip.currentTextChanged.connect(lambda t: self._on_tip_changed(row_data))
        
        self._update_row_badge(row_data)
        self._update_ozet()

    def _update_row_badge(self, row_data):
        is_comb = bool(row_data.get("is_combined"))
        assigned_classes = row_data["classes"]
        configs = row_data.get("class_configs", {})
        default_dist = row_data["cb_tip"].currentText().strip() or "2"
        
        if is_comb:
            comb_classes = row_data.get("combined_classes") or assigned_classes
            comb_str = " + ".join(comb_classes) if comb_classes else (assigned_classes[0] if assigned_classes else "-")
            row_data["lbl_badge"].setText(f"BİRLEŞİK / ORTAK DERS: {comb_str} ({default_dist} Saat)")
            row_data["lbl_badge"].setStyleSheet("background: #FEF3C7; color: #92400E; font-size: 11px; font-weight: bold; padding: 4px 8px; border-radius: 4px; border: 1px solid #FDE68A;")
            return
            
        row_data["lbl_badge"].setStyleSheet("background: #F0F9FF; color: #0369A1; font-size: 11px; font-weight: bold; padding: 3px 6px; border-radius: 4px; border: 1px solid #BAE6FD;")
        if not assigned_classes:
            row_data["lbl_badge"].setText("Atanan Sınıflar: Henüz Seçilmedi")
            return
            
        badge_parts = []
        for c in assigned_classes:
            cfg = configs.get(c, {})
            c_type = cfg.get("type", default_dist)
            if "+" in c_type:
                dur = sum(int(x) for x in c_type.split("+") if x.strip().isdigit())
            elif c_type.isdigit():
                dur = int(c_type)
            else:
                dur = cfg.get("duration", 2)
            
            clean_c = c.replace(",", "+").replace(" ", "") if ("," in c or "+" in c or "&" in c) else c
            badge_parts.append(f"{clean_c} ({dur}s: {c_type})")
            
        row_data["lbl_badge"].setText("Atanan Sınıflar: " + ", ".join(badge_parts))

    def _on_tip_changed(self, row_data):
        self._update_row_badge(row_data)
        self._update_ozet()

    def _on_subject_changed(self, row_data, text):
        clean = text.strip()
        all_s = self._get_all_subjects()
        # Only automatically spawn next blank row if the subject is recognized in the database
        if clean and clean in all_s:
            if self.subject_rows and self.subject_rows[-1] == row_data:
                self._add_subject_row("", "2", "2", [], {})
        self._update_classes_summary()
        self._update_ozet()

    def _edit_classes_for_row(self, row_data):
        subj = row_data["cb_subject"].currentText().strip() or "Ders"
        all_cls = self._get_all_classes()
        default_dist = row_data["cb_tip"].currentText().strip() or "2"
        dlg = SubjectClassMultiSelectDialog(
            subject_name=subj,
            all_classes=all_cls,
            selected_classes=row_data["classes"] if not row_data.get("is_combined") else [],
            default_distribution=default_dist,
            class_configs=row_data.get("class_configs", {}),
            parent=self
        )
        if dlg.exec() == QDialog.Accepted:
            # If the user clicked '🔗 Birleşik Dersler Ayarla' inside the dialog,
            # they may have forced a combined class assignment directly to 'atamalar'.
            # We must preserve this state so final save doesn't overwrite it as separate assignments.
            forced_combined = getattr(dlg, "_is_combined_forced", False)
            row_data["is_combined"] = dlg.get_is_combined() or forced_combined
            row_data["classes"] = dlg.get_selected()
            if row_data["is_combined"]:
                row_data["combined_classes"] = list(row_data["classes"])
            else:
                row_data["combined_classes"] = []
                
            row_data["class_configs"] = dlg.get_configs()
            self._update_row_badge(row_data)
            self._update_classes_summary()
            self._update_ozet()

    def _edit_combined_for_row(self, row_data):
        current_subj = row_data["cb_subject"].currentText().strip()
        current_tip = row_data["cb_tip"].currentText().strip() or "2"
        current_t = self.cb_ogretmen.currentText().strip()
        current_classes = row_data.get("combined_classes") or row_data.get("classes", [])
        dlg = CombinedClassesDialog(
            data_store=self.data_store,
            selected_classes=current_classes,
            parent=self,
            subject_name=current_subj,
            duration=current_tip,
            teacher_name=current_t
        )
        if dlg.exec() == QDialog.Accepted:
            sel_classes = dlg.get_selected_classes()
            if sel_classes:
                row_data["is_combined"] = True
                row_data["combined_classes"] = sel_classes
                row_data["classes"] = [dlg.get_combined_string()]
                
                # Update subject and hours if changed in dialog
                s = dlg.get_subject()
                if s:
                    idx = row_data["cb_subject"].findText(s)
                    if idx >= 0: row_data["cb_subject"].setCurrentIndex(idx)
                    else: row_data["cb_subject"].setCurrentText(s)
                row_data["cb_tip"].setCurrentText(dlg.get_type())
                
                self._update_row_badge(row_data)
                self._update_classes_summary()
                self._update_ozet()
                
                if self.subject_rows and self.subject_rows[-1] == row_data:
                    self._add_subject_row("", "2", "2", [], {})
            else:
                row_data["is_combined"] = False
                row_data["combined_classes"] = []
                self._update_row_badge(row_data)
                self._update_classes_summary()
                self._update_ozet()

    def _remove_subject_row(self, row_data):
        if len(self.subject_rows) <= 1:
            row_data["cb_subject"].setCurrentIndex(-1)
            if row_data["cb_subject"].lineEdit():
                row_data["cb_subject"].lineEdit().clear()
                row_data["cb_subject"].lineEdit().setPlaceholderText("Ders Ara veya Seç...")
            row_data["classes"] = []
            row_data["class_configs"] = {}
            row_data["is_combined"] = False
            row_data["combined_classes"] = []
            self._update_row_badge(row_data)
        else:
            self.subject_rows.remove(row_data)
            self.subjects_container.removeWidget(row_data["widget"])
            row_data["widget"].deleteLater()
            
        self._update_classes_summary()
        self._update_ozet()

    def _open_combined_classes_modal(self):
        cur_t = self.cb_ogretmen.currentText().strip()
        dlg = CombinedClassesDialog(
            data_store=self.data_store,
            parent=self,
            teacher_name=cur_t
        )
        if dlg.exec() == QDialog.Accepted:
            sel_classes = dlg.get_selected_classes()
            subj = dlg.get_subject()
            tip = dlg.get_type()
            if sel_classes and subj:
                # Find an empty subject row, or create a new row
                target_row = None
                for r in self.subject_rows:
                    if not r["cb_subject"].currentText().strip():
                        target_row = r
                        break
                if not target_row:
                    self._add_subject_row(subj, tip, tip, [dlg.get_combined_string()], {}, is_combined=True, combined_classes=sel_classes)
                    target_row = self.subject_rows[-1]
                else:
                    idx = target_row["cb_subject"].findText(subj, Qt.MatchFixedString | Qt.MatchCaseSensitive)
                    if idx < 0:
                        idx = target_row["cb_subject"].findText(subj, Qt.MatchContains | Qt.MatchCaseSensitive)
                    if idx < 0:
                        for i in range(target_row["cb_subject"].count()):
                            if target_row["cb_subject"].itemText(i).strip().lower() == subj.strip().lower():
                                idx = i
                                break
                    if idx >= 0: target_row["cb_subject"].setCurrentIndex(idx)
                    else: target_row["cb_subject"].setCurrentText(subj)
                    target_row["cb_tip"].setCurrentText(tip)
                    target_row["classes"] = [dlg.get_combined_string()]
                    target_row["is_combined"] = True
                    target_row["combined_classes"] = sel_classes
                
                self._update_row_badge(target_row)
                self._update_classes_summary()
                self._update_ozet()
                
                if self.subject_rows and self.subject_rows[-1]["cb_subject"].currentText().strip():
                    self._add_subject_row("", "2", "2", [], {})

    def _update_classes_summary(self):
        all_assigned = []
        for r in self.subject_rows:
            if not r["cb_subject"].currentText().strip():
                continue
            if r.get("is_combined"):
                comb_cls = r.get("combined_classes") or r.get("classes") or []
                c_str = " + ".join(comb_cls)
                if c_str and f"BİRLEŞİK: {c_str}" not in all_assigned:
                    all_assigned.append(f"BİRLEŞİK: {c_str}")
            else:
                for c in r["classes"]:
                    clean_c = c.replace(",", "+").replace(" ", "") if ("," in c or "+" in c or "&" in c) else c
                    if clean_c and clean_c not in all_assigned:
                        all_assigned.append(clean_c)
                    
        if all_assigned:
            self.txt_classes_summary.setText(", ".join(all_assigned))
        else:
            self.txt_classes_summary.setText("")

    def _update_ozet(self, *_):
        t = self.cb_ogretmen.currentText() or "-"
        
        valid_rows = [r for r in self.subject_rows if r["cb_subject"].currentText().strip()]
        ders_count = len(valid_rows)
        
        all_cls = set()
        total_hours = 0
        for r in valid_rows:
            def_dist = r["cb_tip"].currentText().strip() or "2"
            if r.get("is_combined"):
                comb_cls = r.get("combined_classes") or r.get("classes") or []
                for c in comb_cls:
                    all_cls.add(c)
                if "+" in def_dist:
                    parts = [int(p.strip()) for p in def_dist.split("+") if p.strip().isdigit()]
                    total_hours += sum(parts) if parts else 2
                elif def_dist.isdigit():
                    total_hours += int(def_dist)
                else:
                    total_hours += 2
            else:
                cfg_map = r.get("class_configs", {})
                assigned_c = r["classes"] or []
                for c in assigned_c:
                    all_cls.add(c)
                    cfg = cfg_map.get(c, {})
                    c_type = cfg.get("type", def_dist)
                    if "+" in c_type:
                        parts = [int(p.strip()) for p in c_type.split("+") if p.strip().isdigit()]
                        total_hours += sum(parts) if parts else 2
                    elif c_type.isdigit():
                        total_hours += int(c_type)
                    else:
                        total_hours += int(cfg.get("duration", 2))
                    
        cls_count = len(all_cls)
        
        self.lbl_ozet.setText(
            f"<b>Öğretmen:</b> {t} | "
            f"<b>Toplam Ders Sayısı:</b> {ders_count} | "
            f"<b>Atanan Sınıf Sayısı:</b> {cls_count} | "
            f"<b>Toplam Haftalık Saat:</b> {total_hours} Saat"
        )

    def _load_teacher_initial_data(self):
        if not self.data_store:
            return
            
        teacher_names = sorted([t.get("ad", "") for t in self.data_store.get("ogretmenler", []) if t.get("ad")])
        self.cb_ogretmen.blockSignals(True)
        self.cb_ogretmen.clear()
        for t_name in teacher_names:
            self.cb_ogretmen.addItem(t_name)
            
        if self.selected_teacher:
            idx = self.cb_ogretmen.findText(self.selected_teacher)
            if idx >= 0:
                self.cb_ogretmen.setCurrentIndex(idx)
        elif teacher_names:
            self.cb_ogretmen.setCurrentIndex(0)
        self.cb_ogretmen.blockSignals(False)
        
        self._populate_from_teacher()

    def _on_teacher_changed(self, teacher_name):
        self._populate_from_teacher()

    def _populate_from_teacher(self):
        teacher_name = self.cb_ogretmen.currentText().strip()
        if not teacher_name or not self.data_store:
            return
            
        atamalar = self.data_store.get("atamalar", [])
        my_atamalar = [a for a in atamalar if format_tr_name(a.get("teacher", "")) == format_tr_name(teacher_name)]
        
        # Clear existing dynamic rows
        for r in list(self.subject_rows):
            self.subjects_container.removeWidget(r["widget"])
            r["widget"].deleteLater()
        self.subject_rows.clear()
        
        normal_subj_map = {}
        combined_list = []
        
        for a in my_atamalar:
            s_name = a.get("subject", "").strip()
            if not s_name: continue
            c_name = a.get("class", "").strip()
            dur = a.get("duration", 2)
            typ = a.get("type", str(dur))
            is_comb = bool(a.get("is_combined") or ("+" in c_name or "&" in c_name))
            
            if is_comb:
                comb_cls = a.get("combined_classes") or [p.strip() for p in c_name.replace("&", "+").replace(",", "+").split("+") if p.strip()]
                combined_list.append({
                    "subject": s_name,
                    "duration": dur,
                    "type": typ,
                    "class_str": c_name,
                    "combined_classes": comb_cls
                })
            else:
                if s_name not in normal_subj_map:
                    normal_subj_map[s_name] = {
                        "classes": [],
                        "duration": dur,
                        "type": typ,
                        "class_configs": {}
                    }
                if c_name and c_name not in normal_subj_map[s_name]["classes"]:
                    normal_subj_map[s_name]["classes"].append(c_name)
                normal_subj_map[s_name]["class_configs"][c_name] = {"type": typ, "duration": dur}
                
        # Add normal rows
        for s_name, s_data in normal_subj_map.items():
            self._add_subject_row(
                s_name, str(s_data.get("duration", 2)), s_data.get("type", "2"),
                s_data.get("classes", []), class_configs=s_data.get("class_configs", {}),
                is_combined=False
            )
            
        # Add combined rows
        for c_item in combined_list:
            self._add_subject_row(
                c_item["subject"], str(c_item["duration"]), c_item["type"],
                [c_item["class_str"]], class_configs={},
                is_combined=True, combined_classes=c_item["combined_classes"]
            )
            
        # Add trailing empty row
        if not self.subject_rows or self.subject_rows[-1]["cb_subject"].currentText().strip():
            self._add_subject_row("", "2", "2", [], {})
            
        self._update_classes_summary()
        self._update_ozet()

    def get_data(self):
        teacher_name = format_tr_name(self.cb_ogretmen.currentText().strip())
        if not teacher_name:
            QMessageBox.warning(self, "Öğretmen Seçilmedi", "Lütfen bir öğretmen seçiniz.")
            return None
            
        assignments = []
        valid_rows = [r for r in self.subject_rows if r["cb_subject"].currentText().strip()]
        
        for r in valid_rows:
            subj = r["cb_subject"].currentText().strip()
            default_type_val = r["cb_tip"].currentText().strip() or "2"
            is_comb = bool(r.get("is_combined"))
            
            if is_comb:
                comb_classes = r.get("combined_classes") or r.get("classes") or []
                if not comb_classes or len(comb_classes) < 2:
                    QMessageBox.warning(self, "Eksik Sınıf", f"'{subj}' birleşik dersi için en az 2 sınıf seçilmelidir!")
                    return None
                comb_str = " + ".join(comb_classes)
                cfg = r.get("class_configs", {}).get(comb_str, {})
                type_val = cfg.get("type", default_type_val)
                if "+" in type_val:
                    parts = [int(p.strip()) for p in type_val.split("+") if p.strip().isdigit()]
                    duration = sum(parts) if parts else 2
                else:
                    duration = int(type_val) if type_val.isdigit() else 2
                    
                assignments.append({
                    "teacher": teacher_name,
                    "subject": subj,
                    "class": comb_str,
                    "duration": duration,
                    "type": type_val,
                    "color": get_subject_color(subj),
                    "is_combined": True,
                    "combined_classes": list(comb_classes)
                })
            else:
                assigned_classes = r["classes"]
                if not assigned_classes:
                    QMessageBox.warning(self, "Eksik Sınıf Seçimi", f"Lütfen '{subj}' dersi için en az bir sınıf seçiniz!")
                    return None
                for c_name in assigned_classes:
                    cfg = r.get("class_configs", {}).get(c_name, {})
                    type_val = cfg.get("type", default_type_val)
                    if "+" in type_val:
                        parts = [int(p.strip()) for p in type_val.split("+") if p.strip().isdigit()]
                        duration = sum(parts) if parts else 2
                    else:
                        duration = int(type_val) if type_val.isdigit() else 2
                        
                    assignments.append({
                        "teacher": teacher_name,
                        "subject": subj,
                        "class": c_name,
                        "duration": duration,
                        "type": type_val,
                        "color": get_subject_color(subj),
                        "is_combined": False,
                        "combined_classes": []
                    })
                    
        return assignments

    def accept(self):
        teacher_name = format_tr_name(self.cb_ogretmen.currentText().strip())
        if not teacher_name:
            QMessageBox.warning(self, "Öğretmen Seçilmedi", "Lütfen bir öğretmen seçiniz.")
            return
            
        new_data = self.get_data()
        if new_data is None:
            return # Validation failed
            
        if not new_data:
            # Check if user had any rows typed
            any_typed = any(r["cb_subject"].currentText().strip() for r in self.subject_rows)
            if not any_typed:
                QMessageBox.warning(self, "Ders Seçilmedi", "Kaydedilecek geçerli bir ders veya sınıf seçimi bulunamadı.\nLütfen atanacak dersi seçtiğinizden emin olunuz.")
                return
                
        if self.data_store is not None:
            if "atamalar" not in self.data_store:
                self.data_store["atamalar"] = []
                
            # Remove old assignments for this teacher
            self.data_store["atamalar"] = [
                a for a in self.data_store["atamalar"]
                if format_tr_name(a.get("teacher", "")) != teacher_name
            ]
            
            # Add new assignments
            self.data_store["atamalar"].extend(new_data)
            
            # Clean up grid placements, auto_schedule_results, and yerlesim for removed assignments
            active_tuples = {
                (format_tr_name(a.get("subject", "")), format_tr_name(a.get("class", "")), teacher_name)
                for a in new_data
            }
            
            grid_data = self.data_store.get("grid_placements", [])
            if isinstance(grid_data, list):
                self.data_store["grid_placements"] = [
                    p for p in grid_data
                    if not (
                        format_tr_name(p.get("teacher_name", p.get("teacher", ""))) == teacher_name and
                        (format_tr_name(p.get("subject_name", p.get("subject", ""))), format_tr_name(p.get("class_name", p.get("class", ""))), teacher_name) not in active_tuples
                    )
                ]
                
            auto_data = self.data_store.get("auto_schedule_results", [])
            if isinstance(auto_data, list):
                self.data_store["auto_schedule_results"] = [
                    p for p in auto_data
                    if not (
                        format_tr_name(p.get("teacher_name", p.get("teacher", ""))) == teacher_name and
                        (format_tr_name(p.get("subject_name", p.get("subject", ""))), format_tr_name(p.get("class_name", p.get("class", ""))), teacher_name) not in active_tuples
                    )
                ]
                
            yerlesim = self.data_store.get("yerlesim", {})
            if isinstance(yerlesim, dict):
                for k in list(yerlesim.keys()):
                    info = yerlesim[k]
                    if isinstance(info, dict):
                        p_sub = format_tr_name(info.get("subject_name", info.get("subject", "")))
                        p_cls = format_tr_name(info.get("class_name", info.get("class", "")))
                        p_tea = format_tr_name(info.get("teacher_name", info.get("teacher", "")))
                        if p_tea == teacher_name and (p_sub, p_cls, p_tea) not in active_tuples:
                            yerlesim.pop(k, None)

            trigger_save_db(self, self.data_store)
            
            # Refresh MainWindow and bottom dock if accessible
            win = self.window()
            if not win or (not hasattr(win, "_grid") and not hasattr(win, "_refresh_unplaced_lessons")):
                p = self.parent()
                while p:
                    if hasattr(p, "_grid") or hasattr(p, "_refresh_unplaced_lessons"):
                        win = p
                        break
                    p = p.parent()
                    
            if not win or (not hasattr(win, "_grid") and not hasattr(win, "_refresh_unplaced_lessons")):
                from PySide6.QtWidgets import QApplication
                for top in QApplication.topLevelWidgets():
                    if hasattr(top, "_grid") or hasattr(top, "_refresh_unplaced_lessons"):
                        win = top
                        break
                        
            if win:
                if hasattr(win, "save_db"): win.save_db(sync_from_grid=False)
                if hasattr(win, "_refresh_grid"): win._refresh_grid()
                if hasattr(win, "_refresh_tree"): win._refresh_tree()
                if hasattr(win, "_load_unplaced_lessons"): win._load_unplaced_lessons()
                if hasattr(win, "_refresh_unplaced_lessons"): win._refresh_unplaced_lessons()
                
        super().accept()


def _auto_short_code(text: str) -> str:
    if not text:
        return ""
    clean = text.strip()
    import re
    
    # Extract numbers and letters separately
    nums = "".join(re.findall(r'\d+', clean))
    letters_str = re.sub(r'\d+', '', clean).strip()
    
    # Turkish uppercase helper
    def tr_upper(s):
        return s.replace("i", "İ").replace("ı", "I").upper()
        
    upper_letters = tr_upper(letters_str)
    
    # Special Overrides with Full Turkish Subject Names
    overrides = {
        "BEDEN": "BEDEN",
        "BEDEN EĞİTİMİ": "BEDEN",
        "BEDEN EĞİTİMİ VE SPOR": "BEDEN",
        "BED": "BEDEN",
        "TARİH": "TARİH",
        "TAR": "TARİH",
        "İNKILAP": "İNKILAP TARİHİ",
        "İNKILAP TARİHİ": "İNKILAP TARİHİ",
        "T.C. İNKILAP TARİHİ": "İNKILAP TARİHİ",
        "REHBERLİK": "REHBERLİK",
        "REHBERLİK VE YÖNLENDİRME": "REHBERLİK",
        "REH": "REHBERLİK",
        "TÜRKÇE": "TÜRKÇE",
        "TÜRK": "TÜRKÇE",
        "MÜZİK": "MÜZİK",
        "MÜZ": "MÜZİK",
        "FELSEFE": "FELSEFE",
        "FEL": "FELSEFE",
        "DİN": "DİN",
        "DİN KÜLTÜRÜ": "DİN",
        "DİN KÜLTÜRÜ VE AHLAK BİLGİSİ": "DİN",
        "EDİN KÜLTÜRÜ": "DİN",
        "GÖRSEL SANATLAR": "GÖRSEL",
        "GÖRSEL": "GÖRSEL",
        "GÖRS": "GÖRSEL",
        "RESİM": "GÖRSEL",
        
        # Diğer dersler kısa koda dönüştürülmeli
        "BİYOLOJİ": "BİYO",
        "BİYO": "BİYO",
        "FİZİK": "FİZİK",
        "FİZ": "FİZİK",
        "KİMYA": "KİMYA",
        "KİM": "KİMYA",
        "COĞRAFYA": "COĞRAF",
        "COĞ": "COĞRAF",
        "GEOMETRİ": "GEOM",
        "GEOMETRI": "GEOM",
        "GEO": "GEOM",
        "EDEBİYAT": "EDEB",
        "EDB": "EDEB",
        "TÜRK DİLİ VE EDEBİYATI": "TDE",
        "TDE": "TDE",
        "MATEMATİK": "MATE",
        "MATEMATIK": "MATE",
        "MAT": "MATE",
        "MATE": "MATE",
        "İNGİLİZCE": "İNG",
        "İNG": "İNG",
        "ALMANCA": "ALM",
        "ALM": "ALM",
        "FRANSIZCA": "FRA",
        "FRA": "FRA",
        "PARAGRAF": "PARAG",
        "PARAG": "PARAG",
        "PAR": "PARAG",
        "PROBLEM": "PROB",
        "PROB": "PROB",
        
        # Kısa kodu olmayan diğer dersler
        "BİLİŞİM": "BİLİŞ",
        "KODLAMA": "KODLAM",
        "YAZILIM": "YAZILIM",
        "ROBOTİK": "ROBOTİK",
        "SAĞLIK": "SAĞLIK BİLGİSİ",
        "SAĞLIK BİLGİSİ": "SAĞLIK BİLGİSİ",
        "TRAFİK": "TRAFİK",
        "ASTRONOMİ": "ASTRONOMİ",
        "MANTIK": "MANTIK",
        "SOSYOLOJİ": "SOSYOLOJİ",
        "PSİKOLOJİ": "PSİKOLOJİ",
    }
    
    if upper_letters in overrides:
        base = overrides[upper_letters]
    elif len(upper_letters) <= 20:
        base = upper_letters[:4] if len(upper_letters) > 4 else upper_letters
    else:
        base = upper_letters[:4]
    
    # Numbers must ALWAYS stand separate by a space
    sc = f"{base} {nums}" if nums else base
    return sc.strip()


class DersEditDialog(QDialog):
    """
    Sade Ders (Subject) Tanımlama Ekranı
    """
    def __init__(self, parent=None, existing_data=None):
        super().__init__(parent)
        self.setWindowTitle("Ders")
        self.resize(540, 680)
        self.setMinimumSize(520, 640)
        self.setStyleSheet("""
            QDialog { background-color: #F4F6F9; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; }
            QLabel { border: none; background: transparent; color: #333; font-size: 13px; }
            QLineEdit { min-height: 28px; padding: 3px 8px; border: 1px solid #CCCCCC; border-radius: 4px; background: #FFFFFF; font-size: 13px; color: #333; }
            QLineEdit:focus { border: 1px solid #0078D7; }
            QComboBox { min-height: 28px; padding: 3px 8px; border: 1px solid #CCCCCC; border-radius: 4px; background: #FFFFFF; font-size: 13px; }
            QPushButton { min-height: 28px; padding: 4px 12px; border: 1px solid #CCCCCC; border-radius: 4px; background: #F8F9FA; font-size: 13px; color: #333; }
            QPushButton:hover { background: #EAEAEA; }
        """)
        self.existing_data = existing_data or {}
        self.current_color = self.existing_data.get("renk", "#C4C4F0")
        self._build_ui()
        
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # 1. Dersin Adı / Kısa Kodu
        f1 = QFrame()
        f1.setObjectName("card1")
        f1.setStyleSheet("#card1 { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
        l1 = QFormLayout(f1)
        l1.setContentsMargins(12, 12, 12, 12)
        l1.setSpacing(10)
        
        self.txt_ad = QLineEdit()
        if "ad" in self.existing_data: self.txt_ad.setText(self.existing_data["ad"])
        self.txt_ad.textChanged.connect(self._auto_short_code)
        
        self.txt_kisa = QLineEdit()
        if "kisa" in self.existing_data: self.txt_kisa.setText(self.existing_data["kisa"])
        
        l1.addRow(QLabel("Dersin Adı"), self.txt_ad)
        l1.addRow(QLabel("Kısa Kodu"), self.txt_kisa)
        
        btn_ozel = QPushButton("🏷️ Özel Alanlar...")
        btn_ozel.setStyleSheet("background: #F1F5F9; color: #1E293B; font-weight: 500;")
        btn_ozel.clicked.connect(self._open_custom_fields)
        l1.addRow("", btn_ozel)
        
        main_layout.addWidget(f1)

        # 2. Renk Kodu
        f2 = QFrame()
        f2.setObjectName("card2")
        f2.setStyleSheet("#card2 { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
        l2 = QVBoxLayout(f2)
        l2.setContentsMargins(12, 12, 12, 12)
        l2.setSpacing(8)
        
        lbl_renk_title = QLabel("Renk Kodu / Küçük Resim Seç")
        lbl_renk_title.setStyleSheet("font-weight: bold;")
        l2.addWidget(lbl_renk_title)
        
        h2 = QHBoxLayout()
        self.color_lbl = QLabel()
        self.color_lbl.setFixedSize(140, 36)
        self.color_lbl.setStyleSheet(f"background-color: {self.current_color}; border: 1px solid #AAA; border-radius: 4px;")
        h2.addWidget(self.color_lbl)
        
        btn_renk = QPushButton("Değiştir")
        btn_renk.setFixedSize(90, 32)
        btn_renk.clicked.connect(self._pick_color)
        h2.addStretch(1)
        h2.addWidget(btn_renk)
        h2.addStretch(1)
        l2.addLayout(h2)
        
        main_layout.addWidget(f2)
        
        # 3. Derslikler
        f3 = QFrame()
        f3.setObjectName("card3")
        f3.setStyleSheet("#card3 { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
        l3 = QVBoxLayout(f3)
        l3.setContentsMargins(12, 12, 12, 12)
        l3.setSpacing(8)
        
        lbl_derslik_title = QLabel("Derslikler")
        lbl_derslik_title.setStyleSheet("font-weight: bold;")
        l3.addWidget(lbl_derslik_title)
        
        btn_derslik = QPushButton("Derslikler")
        btn_derslik.clicked.connect(self._open_derslikler)
        btn_uygula = QPushButton("Dersin Tanımlanmış Kartlarına Uygula")
        btn_uygula.clicked.connect(self._apply_to_cards)
        btn_hoca_ata = QPushButton("Dersin Öğretmenlerini ve Sınıflarını Ata")
        btn_hoca_ata.setStyleSheet("background: #0078D7; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        btn_hoca_ata.clicked.connect(self._assign_teachers_for_subject)
        
        l3.addWidget(btn_derslik)
        l3.addWidget(btn_uygula)
        l3.addWidget(btn_hoca_ata)
        
        l3.addWidget(QLabel("Atandığı Sınıflar ve Öğretmenler (Gerçek Zamanlı):"))
        self.list_assignments = QListWidget()
        self.list_assignments.setMinimumHeight(85)
        self.list_assignments.setMaximumHeight(130)
        self.list_assignments.setStyleSheet("QListWidget { background: #F8F9FA; border: 1px solid #D0D7DE; border-radius: 6px; color: #333333; font-size: 12px; } QListWidget::item { padding: 4px 8px; }")
        l3.addWidget(self.list_assignments)
        
        main_layout.addWidget(f3)

        # 4. Bottom Controls (Kaydet / İptal)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        
        btn_iptal = QPushButton("İptal")
        btn_iptal.setFixedSize(90, 34)
        btn_iptal.setStyleSheet("QPushButton { background: #F0F0F0; border: 1px solid #CCC; border-radius: 4px; } QPushButton:hover { background: #E5E5E5; }")
        btn_iptal.clicked.connect(self.reject)
        
        btn_tamam = QPushButton("Kaydet")
        btn_tamam.setFixedSize(110, 34)
        btn_tamam.setStyleSheet("QPushButton { background: #0078D7; color: white; font-weight: bold; border-radius: 4px; font-size: 13px; } QPushButton:hover { background: #005A9E; }")
        btn_tamam.clicked.connect(self.accept)
        
        bottom.addWidget(btn_iptal)
        bottom.addWidget(btn_tamam)
        main_layout.addLayout(bottom)

        self.txt_ad.textChanged.connect(self._refresh_assignments_list)
        self._refresh_assignments_list()

    def _get_data_store(self):
        curr = self.parent()
        while curr is not None:
            if hasattr(curr, "data_store") and curr.data_store is not None:
                return curr.data_store
            curr = getattr(curr, "parent", lambda: None)()
        return {}

    def _refresh_assignments_list(self):
        self.list_assignments.clear()
        data_store = self._get_data_store()
        atamalar = data_store.get("atamalar", [])
        my_ad = self.txt_ad.text().strip() or self.existing_data.get("ad", "")
        
        if not my_ad:
            self.list_assignments.addItem(QListWidgetItem("Ders adı girildiğinde atamalar burada listelenir."))
            return
            
        my_atamalar = [a for a in atamalar if format_tr_name(a.get("subject", "")) == format_tr_name(my_ad)]
        for a in my_atamalar:
            item_text = f"• {a.get('teacher', 'Atanmadı')}  →  {a.get('class', '')} ({a.get('duration', 0)} Saat, Tip: {a.get('type', '-')})"
            item = QListWidgetItem(item_text)
            self.list_assignments.addItem(item)
        if not my_atamalar:
            self.list_assignments.addItem(QListWidgetItem("Henüz hiçbir sınıfa / öğretmene atanmadı."))

    def _assign_teachers_for_subject(self):
        data_store = self._get_data_store()
        subj_name = format_tr_name(self.txt_ad.text().strip())
        if not subj_name:
            return
        d = SubjectTeacherAssignmentDialog(subject_name=subj_name, data_store=data_store, parent=self.parent() or self)
        if d.exec():
            trigger_save_db(self, data_store)
            self._refresh_assignments_list()

    def _open_derslikler(self):
        from dialogs.master_data_dialog import MasterDataDialog
        d = MasterDataDialog(start_idx=2, parent=self)
        d.exec()

    def _apply_to_cards(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Derslik Ayarı", "Derslik seçimleri bu dersin tüm tanımlı kartlarına uygulandı.")

    def _auto_short_code(self, text):
        if text:
            self.txt_kisa.setText(_auto_short_code(text))

    def _open_custom_fields(self):
        d_name = self.txt_ad.text().strip() or "Ders"
        dlg = CustomFieldsDialog(d_name, "Ders", self.existing_data.get("ozel_alanlar", {}), self)
        if dlg.exec() == QDialog.Accepted:
            self.existing_data["ozel_alanlar"] = dlg.get_data()

    def _pick_color(self):
        from dialogs.color_picker_dialog import ModernColorPickerDialog
        s_name = self.txt_ad.text().strip() or "Ders"
        data_store = self._get_data_store()
        c = ModernColorPickerDialog.pick_color(
            initial_color=self.current_color,
            parent=self,
            title=f"🎨 {s_name} — Renk Seçimi",
            data_store=data_store,
            subject_name=s_name
        )
        if c and c.isValid():
            self.current_color = c.name()
            self.color_lbl.setStyleSheet(f"background-color: {self.current_color}; border: 1px solid #AAA; border-radius: 4px;")

    def get_data(self):
        raw_ad = self.txt_ad.text().strip()
        formatted_ad = format_tr_name(raw_ad)
        return {
            "ad": formatted_ad,
            "kisa": self.txt_kisa.text().strip(),
            "renk": self.current_color,
            "ozel_alanlar": self.existing_data.get("ozel_alanlar", {})
        }


def _matches_teacher(t1, t2):
    if not t1 or not t2: return False
    from version_store import normalize_teacher_name
    n1 = normalize_teacher_name(str(t1))
    n2 = normalize_teacher_name(str(t2))
    if n1 == n2 or format_tr_name(t1) == format_tr_name(t2):
        return True
    p1 = set(n1.split())
    p2 = set(n2.split())
    if p1 and p2 and (p1.issubset(p2) or p2.issubset(p1)):
        return True
    return False


class BranchMultiSelectDialog(QDialog):
    """Modern Checkbox ile Çoklu Branş Seçim Penceresi"""
    def __init__(self, teacher_name="", all_branches=None, selected_branches=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Branş(lar) Ata — {teacher_name}")
        self.resize(360, 460)
        all_branches = all_branches or []
        selected_branches = [b.strip() for b in (selected_branches or []) if b.strip()]
        
        chk_checked = get_asset_path("resources/chk_checked.png")
        chk_unchk = get_asset_path("resources/chk_unchecked.png")
        
        self.setStyleSheet(f"""
            QDialog {{ background: #FFFFFF; font-family: system-ui, -apple-system, sans-serif; }}
            QListWidget {{ border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px; }}
            QListWidget::item {{ padding: 8px 12px; }}
            QListWidget::indicator {{ width: 18px; height: 18px; }}
            QListWidget::indicator:unchecked {{ image: url("{chk_unchk}"); }}
            QListWidget::indicator:checked {{ image: url("{chk_checked}"); }}
            QPushButton {{ min-height: 32px; padding: 4px 14px; border-radius: 6px; font-weight: bold; font-size: 13px; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(12)
        
        lbl = QLabel(f"🎓 <b>{teacher_name}</b> — Atanacak Branş(lar)")
        lbl.setStyleSheet("color: #0284C7; font-size: 13px;")
        lay.addWidget(lbl)
        
        self.list_widget = QListWidget()
        for b in all_branches:
            item = QListWidgetItem(b)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            is_chk = any(b.upper() == s.upper() for s in selected_branches)
            item.setCheckState(Qt.Checked if is_chk else Qt.Unchecked)
            self.list_widget.addItem(item)
        lay.addWidget(self.list_widget)
        
        btns = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; color: #475569;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("Kaydet ve Ata")
        btn_ok.setStyleSheet("background: #0284C7; color: white; border: none;")
        btn_ok.clicked.connect(self.accept)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)
        lay.addLayout(btns)
        
    def get_selected_branches(self):
        return [self.list_widget.item(i).text().strip() for i in range(self.list_widget.count()) if self.list_widget.item(i).checkState() == Qt.Checked]


class MultiClassAssignDialog(QDialog):
    """Tek Tablolu Net ve Modern Sınıf Seçim & Birleştirme Penceresi"""
    def __init__(self, teacher_name="", subject_name="", all_classes=None, selected_classes=None, combined_classes=None, is_combined=False, parent=None):
        super().__init__(parent)
        self.teacher_name = teacher_name
        self.subject_name = subject_name
        self.all_classes = list(all_classes or [])
        self._initial_selected = set(selected_classes or [])
        self._initial_combined = set(combined_classes or [])
        self._initial_is_combined = bool(is_combined and combined_classes and len(combined_classes) > 1)
        
        self.setWindowTitle(f"Sınıf Seçimi ve Birleştirme — {teacher_name}")
        self.resize(580, 560)
        self.setMinimumSize(520, 480)
        
        chk_checked = get_asset_path("resources/chk_checked.png")
        chk_unchk = get_asset_path("resources/chk_unchecked.png")
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; }}
            QLabel {{ color: #1E293B; font-size: 13px; }}
            QTableWidget {{
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                gridline-color: #F1F5F9;
                font-size: 13px;
            }}
            QHeaderView::section {{
                background-color: #F1F5F9;
                color: #334155;
                font-weight: bold;
                font-size: 12px;
                padding: 6px 10px;
                border: none;
                border-bottom: 2px solid #CBD5E1;
            }}
            QPushButton {{
                min-height: 30px;
                padding: 4px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }}
            QLineEdit {{
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                background: white;
            }}
            QLineEdit:focus {{ border-color: #2563EB; }}
        """)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)
        
        # Header Info Card
        top_card = QFrame()
        top_card.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; }")
        top_lay = QVBoxLayout(top_card)
        top_lay.setContentsMargins(10, 8, 10, 8)
        top_lay.setSpacing(4)
        
        lbl_h = QLabel(f"🎓 <b>{teacher_name}</b> — Atanacak Sınıflar ve Birleştirme")
        lbl_h.setStyleSheet("font-size: 15px; color: #2563EB; font-weight: bold;")
        top_lay.addWidget(lbl_h)
        
        lbl_sub = QLabel(f"📚 Ders: <b>{subject_name}</b> | Bu öğretmene atanacak sınıfları seçin. Birlikte (ortak) işlenecek sınıflar için <b>🔗 Birleşik</b> kutucuğunu işaretleyin.")
        lbl_sub.setStyleSheet("color: #64748B; font-size: 12px; font-weight: normal;")
        lbl_sub.setWordWrap(True)
        top_lay.addWidget(lbl_sub)
        lay.addWidget(top_card)
        
        # Search & Quick Actions Bar
        h_tools = QHBoxLayout()
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍 Sınıf Ara...")
        self.txt_filter.textChanged.connect(self._filter_table)
        h_tools.addWidget(self.txt_filter, 1)
        
        btn_sel_all = QPushButton("Tümünü Seç")
        btn_sel_all.setStyleSheet("background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1;")
        btn_sel_all.clicked.connect(self._select_all)
        h_tools.addWidget(btn_sel_all)
        
        btn_comb_all = QPushButton("🔗 Seçilileri Birleştir")
        btn_comb_all.setStyleSheet("background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE;")
        btn_comb_all.clicked.connect(self._combine_all_selected)
        h_tools.addWidget(btn_comb_all)
        
        btn_comb_clear = QPushButton("Birleştirmeyi Sıfırla")
        btn_comb_clear.setStyleSheet("background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;")
        btn_comb_clear.clicked.connect(self._clear_combines)
        h_tools.addWidget(btn_comb_clear)
        lay.addLayout(h_tools)
        
        # Single Unified Table (Col 0: Sınıf Ata, Col 1: Birleşik Yap)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["1. Bu Sınıfa Ders Ata", "2. 🔗 Ortak / Birleşik İşlensin"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.setColumnWidth(1, 210)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        lay.addWidget(self.table, 1)
        
        # Live Preview Banner
        self.lbl_preview = QLabel()
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setStyleSheet("background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 10px; color: #166534; font-size: 12px; font-weight: bold;")
        lay.addWidget(self.lbl_preview)
        
        # Bottom Dialog Buttons
        btns = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; color: #475569;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("Uygula")
        btn_ok.setStyleSheet("background: #2563EB; color: white; border: none; min-width: 100px;")
        btn_ok.clicked.connect(self.accept)
        
        btns.addStretch(1)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)
        lay.addLayout(btns)
        
        self._populate_table()
        self._update_preview()

    def _populate_table(self):
        self.table.setRowCount(0)
        for c in self.all_classes:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Check states
            is_sel = any(matches_class(c, sc) or matches_class(sc, c) or str(c).strip() == str(sc).strip() for sc in self._initial_selected)
            is_comb = False
            if self._initial_is_combined and self._initial_combined:
                is_comb = any(matches_class(c, sc) or matches_class(sc, c) or str(c).strip() == str(sc).strip() for sc in self._initial_combined)
                
            # Col 0: Assign Checkbox + Class Name
            w0 = QWidget()
            l0 = QHBoxLayout(w0)
            l0.setContentsMargins(12, 0, 4, 0)
            l0.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            chk0 = QCheckBox(c)
            chk0.setChecked(is_sel)
            chk0.setStyleSheet("QCheckBox { font-weight: bold; color: #0F172A; font-size: 13px; spacing: 8px; } QCheckBox::indicator { width: 18px; height: 18px; }")
            l0.addWidget(chk0)
            self.table.setCellWidget(row, 0, w0)
            
            # Col 1: Combined Checkbox
            w1 = QWidget()
            l1 = QHBoxLayout(w1)
            l1.setContentsMargins(12, 0, 4, 0)
            l1.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            chk1 = QCheckBox("Birleşik (Ortak)")
            chk1.setChecked(is_comb and is_sel)
            chk1.setStyleSheet("QCheckBox { font-weight: bold; color: #1D4ED8; font-size: 12px; spacing: 6px; } QCheckBox::indicator { width: 16px; height: 16px; }")
            l1.addWidget(chk1)
            self.table.setCellWidget(row, 1, w1)
            
            # Wire listeners with closure
            chk0.toggled.connect(lambda state, r=row: self._on_assign_toggled(r, state))
            chk1.toggled.connect(lambda state, r=row: self._on_combine_toggled(r, state))

    def _on_assign_toggled(self, row, is_checked):
        w1 = self.table.cellWidget(row, 1)
        if w1:
            chk1 = w1.findChild(QCheckBox)
            if chk1 and not is_checked and chk1.isChecked():
                chk1.blockSignals(True)
                chk1.setChecked(False)
                chk1.blockSignals(False)
        self._update_preview()

    def _on_combine_toggled(self, row, is_checked):
        w0 = self.table.cellWidget(row, 0)
        if w0:
            chk0 = w0.findChild(QCheckBox)
            if chk0 and is_checked and not chk0.isChecked():
                chk0.blockSignals(True)
                chk0.setChecked(True)
                chk0.blockSignals(False)
        self._update_preview()

    def _select_all(self):
        for r in range(self.table.rowCount()):
            if not self.table.isRowHidden(r):
                w0 = self.table.cellWidget(r, 0)
                if w0:
                    chk0 = w0.findChild(QCheckBox)
                    if chk0: chk0.setChecked(True)
        self._update_preview()

    def _combine_all_selected(self):
        for r in range(self.table.rowCount()):
            w0 = self.table.cellWidget(r, 0)
            w1 = self.table.cellWidget(r, 1)
            if w0 and w1:
                chk0 = w0.findChild(QCheckBox)
                chk1 = w1.findChild(QCheckBox)
                if chk0 and chk1 and chk0.isChecked():
                    chk1.setChecked(True)
        self._update_preview()

    def _clear_combines(self):
        for r in range(self.table.rowCount()):
            w1 = self.table.cellWidget(r, 1)
            if w1:
                chk1 = w1.findChild(QCheckBox)
                if chk1: chk1.setChecked(False)
        self._update_preview()

    def _filter_table(self, text):
        q = text.strip().lower()
        for r in range(self.table.rowCount()):
            w0 = self.table.cellWidget(r, 0)
            c_name = ""
            if w0:
                chk0 = w0.findChild(QCheckBox)
                if chk0: c_name = chk0.text().lower()
            self.table.setRowHidden(r, bool(q and q not in c_name))

    def _update_preview(self):
        sel = self.get_selected_classes()
        comb = self.get_combined_classes()
        
        if not sel:
            self.lbl_preview.setText("ℹ️ Henüz hiçbir sınıf seçilmedi.")
            self.lbl_preview.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; color: #64748B; font-size: 12px;")
            return
            
        if comb and len(comb) > 1:
            separate = [c for c in sel if c not in comb]
            comb_text = "+".join(comb)
            if separate:
                sep_text = ", ".join(separate)
                self.lbl_preview.setText(f"🔗 <b>Birleşik (Ortak) Sınıflar:</b> {comb_text} (Ortak İşlenir)<br>📌 <b>Ayrı Sınıflar:</b> {sep_text} (Bağımsız İşlenir)")
            else:
                self.lbl_preview.setText(f"🔗 <b>Birleşik (Ortak) Sınıflar:</b> {comb_text} (Tümü Ortak İşlenir)")
            self.lbl_preview.setStyleSheet("background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 10px; color: #166534; font-size: 12px;")
        else:
            self.lbl_preview.setText(f"📌 <b>Ayrı Sınıflar:</b> {', '.join(sel)} (Her sınıf bağımsız olarak işlenecektir)")
            self.lbl_preview.setStyleSheet("background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 10px; color: #1E40AF; font-size: 12px;")

    def get_selected_classes(self):
        res = []
        for r in range(self.table.rowCount()):
            w0 = self.table.cellWidget(r, 0)
            if w0:
                chk0 = w0.findChild(QCheckBox)
                if chk0 and chk0.isChecked():
                    res.append(chk0.text().strip())
        return res

    def get_combined_classes(self):
        comb = []
        for r in range(self.table.rowCount()):
            w0 = self.table.cellWidget(r, 0)
            w1 = self.table.cellWidget(r, 1)
            if w0 and w1:
                chk0 = w0.findChild(QCheckBox)
                chk1 = w1.findChild(QCheckBox)
                if chk0 and chk1 and chk0.isChecked() and chk1.isChecked():
                    comb.append(chk0.text().strip())
        return comb if len(comb) > 1 else []

    def get_is_combined(self):
        return bool(len(self.get_combined_classes()) > 1)


class CombinedClassesAssignDialog(QDialog):
    """Birleşik Dersler ve Sınıf Birleştirme Ayarlama Penceresi"""
    def __init__(self, data_store=None, parent=None, default_subject="", default_teacher="", default_classes=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        self.default_subject = default_subject
        self.default_teacher = default_teacher
        self.default_classes = default_classes or []
        
        self.setWindowTitle("🔗 Birleşik Dersler Ayarla — Sınıf ve Ders Birleştirme")
        self.resize(520, 520)
        chk_checked = get_asset_path("resources/chk_checked.png")
        chk_unchk = get_asset_path("resources/chk_unchecked.png")
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; }}
            QLabel {{ color: #1E293B; font-size: 12px; font-weight: bold; }}
            QGroupBox {{ font-weight: bold; border: 1px solid #CBD5E1; border-radius: 6px; margin-top: 10px; padding-top: 10px; background: white; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #1E40AF; }}
            QComboBox, QSpinBox {{ min-height: 28px; border: 1px solid #CBD5E1; border-radius: 4px; padding: 2px 8px; background: white; }}
            QListWidget::indicator {{ width: 18px; height: 18px; }}
            QListWidget::indicator:unchecked {{ image: url("{chk_unchk}"); }}
            QListWidget::indicator:checked {{ image: url("{chk_checked}"); }}
            QPushButton {{ min-height: 32px; border-radius: 5px; font-weight: bold; padding: 6px 16px; }}
        """)
        
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(16, 16, 16, 16)
        
        # Info Box
        info_lbl = QLabel(
            "💡 <b>Birleşik Ders Nedir?</b><br>"
            "Farklı sınıflar (Örn: <b>10A ve 10B</b>) aynı derste (Örn: <b>Beden Eğitimi / Müzik</b>) "
            "birleştirildiğinde, haftalık çizelgede ve otomatik planlamada <b>aynı gün ve saatte tek bir öğretmen</b> "
            "ile ortak derse katılırlar."
        )
        info_lbl.setStyleSheet("background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 10px; color: #1E3A8A; font-size: 11px;")
        info_lbl.setWordWrap(True)
        lay.addWidget(info_lbl)
        
        # Sınıflar Grubu
        grp_cls = QGroupBox("1. Birleştirilecek Sınıfları Seçin")
        lay_cls = QVBoxLayout(grp_cls)
        self.cls_list = QListWidget()
        self.cls_list.setStyleSheet("border: 1px solid #E2E8F0; border-radius: 4px;")
        
        all_cls = [c.get("ad", "") for c in self.data_store.get("siniflar", []) if c.get("ad")]
        from auto_scheduler import matches_class
        for c in all_cls:
            clean_c = c.split("(")[0].strip()
            item = QListWidgetItem(clean_c)
            item.setData(Qt.UserRole, c)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            is_chk = any(matches_class(clean_c, d) or matches_class(c, d) for d in self.default_classes)
            item.setCheckState(Qt.Checked if is_chk else Qt.Unchecked)
            self.cls_list.addItem(item)
        lay_cls.addWidget(self.cls_list)
        lay.addWidget(grp_cls)
        
        # Ders & Öğretmen Grubu
        grp_subj = QGroupBox("2. Ortak Ders ve Öğretmen Bilgileri")
        form_subj = QFormLayout(grp_subj)
        form_subj.setSpacing(8)
        
        self.cb_subj = QComboBox()
        all_subjs = [d.get("ad", "") for d in self.data_store.get("dersler", []) if d.get("ad")]
        for s in all_subjs:
            self.cb_subj.addItem(s)
        if self.default_subject and self.default_subject in all_subjs:
            self.cb_subj.setCurrentText(self.default_subject)
        form_subj.addRow("Ortak Ders:", self.cb_subj)
        
        self.cb_teacher = QComboBox()
        all_teachers = [t.get("ad", "") for t in self.data_store.get("ogretmenler", []) if t.get("ad")]
        for t in all_teachers:
            self.cb_teacher.addItem(t)
        if self.default_teacher and self.default_teacher in all_teachers:
            self.cb_teacher.setCurrentText(self.default_teacher)
        form_subj.addRow("Ortak Öğretmen:", self.cb_teacher)
        
        self.cb_type = QComboBox()
        self.cb_type.addItems(["2 Saat (2'li Blok)", "2+2 Saat (4 Saat)", "1 Saat (Tekli)", "1+1 Saat (2 Tekli)", "3 Saat", "Özel"])
        form_subj.addRow("Ders Dağılımı:", self.cb_type)
        
        self.txt_custom_type = QLineEdit()
        self.txt_custom_type.setPlaceholderText("Örn: 2+2+1 veya 1+1+1+1")
        self.txt_custom_type.setText("2+2+1")
        self.txt_custom_type.hide()
        self.lbl_custom_type = QLabel("Özel Dağılım (Format):")
        self.lbl_custom_type.hide()
        form_subj.addRow(self.lbl_custom_type, self.txt_custom_type)
        
        self.cb_type.currentTextChanged.connect(self._on_type_changed)
        
        lay.addWidget(grp_subj)
        
        # Buttons
        btns = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background: white; border: 1px solid #CBD5E1; color: #475569;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("✅ Birleşik Dersi Ata ve Kaydet")
        btn_save.setStyleSheet("background: #2563EB; color: white; border: none;")
        btn_save.clicked.connect(self._save_combined)
        
        btns.addStretch()
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        lay.addLayout(btns)
        
    def _on_type_changed(self, text):
        is_custom = (text == "Özel")
        self.lbl_custom_type.setVisible(is_custom)
        self.txt_custom_type.setVisible(is_custom)
        if is_custom:
            self.txt_custom_type.setFocus()
        
    def _save_combined(self):
        selected_classes = [self.cls_list.item(i).text() for i in range(self.cls_list.count()) if self.cls_list.item(i).checkState() == Qt.Checked]
        if len(selected_classes) < 2:
            QMessageBox.warning(self, "Yetersiz Sınıf Seçimi", "Lütfen birleştirmek için en az 2 sınıf seçiniz (Örn: 10A ve 10B).")
            return
            
        subj = self.cb_subj.currentText()
        teacher = self.cb_teacher.currentText()
        type_choice = self.cb_type.currentText()
        
        type_str = "2"
        tot_dur = 2
        if type_choice == "Özel":
            custom_val = self.txt_custom_type.text().strip()
            if not custom_val:
                QMessageBox.warning(self, "Eksik Bilgi", "Lütfen özel ders dağılımını girin (Örn: 2+2+1).")
                return
            try:
                parts = [int(p.strip()) for p in custom_val.split("+") if p.strip()]
                if not parts or any(p <= 0 for p in parts):
                    raise ValueError()
                type_str = "+".join(map(str, parts))
                tot_dur = sum(parts)
            except:
                QMessageBox.warning(self, "Geçersiz Format", "Özel dağılım formatı geçersiz! Örnek format: 2+2+1 veya 1+1+1+1")
                return
        elif "2+2" in type_choice:
            type_str = "2+2"; tot_dur = 4
        elif "1+1" in type_choice:
            type_str = "1+1"; tot_dur = 2
        elif "1 Saat" in type_choice:
            type_str = "1"; tot_dur = 1
        elif "3 Saat" in type_choice:
            type_str = "3"; tot_dur = 3
            
        combined_class_name = ", ".join(selected_classes)
        
        if "atamalar" not in self.data_store:
            self.data_store["atamalar"] = []
            
        # Check if identical combined assignment exists
        found = False
        for a in self.data_store["atamalar"]:
            if a.get("subject") == subj and (a.get("is_combined") or "," in str(a.get("class", ""))):
                a["class"] = combined_class_name
                a["teacher"] = teacher
                a["duration"] = tot_dur
                a["type"] = type_str
                a["is_combined"] = True
                a["combined_classes"] = list(selected_classes)
                found = True
                break
                
        if not found:
            from dialogs.edit_forms import get_subject_color
            self.data_store["atamalar"].append({
                "subject": subj,
                "teacher": teacher,
                "class": combined_class_name,
                "duration": tot_dur,
                "type": type_str,
                "is_combined": True,
                "combined_classes": list(selected_classes),
                "color": get_subject_color(subj)
            })
            
        self.selected_classes = selected_classes
        self.accept()


class SubjectTeacherAssignmentDialog(QDialog):
    """Modernize Edilmiş Öğretmen Seç, Saat ve Sınıf Eşleştirme Sheet Ekranı"""
    def __init__(self, subject_name="", data_store=None, parent=None, current_class="", preselect_class="", preselect_teacher="", is_cell_edit=False, cell_r=-1, cell_c=-1, **kwargs):
        super().__init__(parent)
        self.subject_name = subject_name
        self.data_store = data_store or {}
        self.current_class = current_class or preselect_class or ""
        self.preselect_teacher = preselect_teacher or ""
        self.is_cell_edit = is_cell_edit
        self.cell_r = cell_r
        self.cell_c = cell_c
        self.new_teacher = None
        self.resize(920, 580)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; }
            QLabel { color: #334155; font-size: 13px; font-weight: bold; }
            QTableWidget { border: 1px solid #CBD5E1; background: #FFFFFF; gridline-color: #F1F5F9; font-size: 13px; border-radius: 8px; }
            QHeaderView::section { background-color: #F1F5F9; border: none; border-bottom: 2px solid #CBD5E1; padding: 8px; font-weight: bold; font-size: 13px; color: #334155; }
            QPushButton { min-height: 32px; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: bold; }
            QLineEdit { border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px 12px; font-size: 13px; background: white; }
            QLineEdit:focus { border: 1px solid #2563EB; }
            QComboBox { min-height: 30px; border: 1px solid #CBD5E1; border-radius: 6px; padding: 3px 8px; background: white; }
            QCheckBox {
                font-weight: 600;
                color: #0F172A;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border: 2px solid #64748B;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:hover {
                border-color: #2563EB;
                background-color: #EFF6FF;
            }
            QCheckBox::indicator:checked {
                border-color: #2563EB;
                background-color: #2563EB;
            }
        """)
        
        self.teacher_configs = {}
        self.all_classes = [c.get("ad", "") for c in self.data_store.get("siniflar", []) if c.get("ad")]
        
        if self.is_cell_edit:
            self.setWindowTitle(f"Öğretmen Değiştir (Günlük) — {self.subject_name}")
            self.resize(600, 250)
            self._build_cell_edit_ui()
        else:
            self.setWindowTitle(f"Öğretmen Seç & Saat Ata — {self.subject_name}")
            self._init_data()
            self._build_ui()
            self._populate_table()

    def _build_cell_edit_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)
        
        lbl = QLabel(f"📚 <b>{self.subject_name}</b> dersine şu an <b>{self.preselect_teacher or 'Kimse'}</b> atanmış.<br>Sadece bu gün için öğretmeni değiştirmek için yeni öğretmeni seçiniz:")
        lbl.setStyleSheet("font-size: 13px; color: #334155;")
        lay.addWidget(lbl)
        
        f_row = QFrame()
        f_row.setStyleSheet("background: white; border: 1px solid #CBD5E1; border-radius: 8px; padding: 10px;")
        l_row = QHBoxLayout(f_row)
        
        l_row.addWidget(QLabel("Hedef Sınıf: <b>" + str(self.current_class) + "</b>"))
        l_row.addSpacing(20)
        l_row.addWidget(QLabel("Yeni Öğretmen:"))
        
        self.cb_teacher = QComboBox()
        self.cb_teacher.setMinimumWidth(220)
        self.cb_teacher.setEditable(True)
        teachers = sorted([t.get("ad") for t in self.data_store.get("ogretmenler", []) if t.get("ad")])
        self.cb_teacher.addItems(teachers)
        if self.preselect_teacher in teachers:
            self.cb_teacher.setCurrentText(self.preselect_teacher)
            
        l_row.addWidget(self.cb_teacher)
        lay.addWidget(f_row)
        
        bot = QHBoxLayout()
        bot.addStretch()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; color: #475569;")
        btn_cancel.clicked.connect(self.reject)
        bot.addWidget(btn_cancel)
        
        btn_save = QPushButton("💾 Kaydet (Sadece Bu Gün)")
        btn_save.setStyleSheet("background: #2563EB; color: white; border: none; padding: 6px 18px;")
        
        def save_action():
            self.new_teacher = self.cb_teacher.currentText().strip()
            self.accept()
            
        btn_save.clicked.connect(save_action)
        bot.addWidget(btn_save)
        lay.addLayout(bot)

    def _init_data(self):
        subj_target = format_tr_name(self.subject_name)
        existing = [a for a in self.data_store.get("atamalar", []) if format_tr_name(a.get("subject", "")) == subj_target]
        
        all_teachers = [t.get("ad", "") for t in self.data_store.get("ogretmenler", []) if t.get("ad")]
        for t in all_teachers:
            t_asgns = [a for a in existing if _matches_teacher(a.get("teacher", ""), t)]
            
            # Determine existing classes, combined classes, and combined state
            t_classes = []
            t_combined_classes = []
            cur_cls_type = ""
            comb_cls_type = ""
            sep_hours = {}
            
            for a in t_asgns:
                typ = str(a.get("type", "")).strip()
                if not typ or typ in ("0", "None"):
                    dur = int(a.get("duration", 0))
                    typ = str(dur) if dur > 0 else "2"
                    
                c_raw = str(a.get("class", "")).strip()
                
                if a.get("is_combined") and a.get("combined_classes"):
                    comb_cls_type = typ
                    for c in a["combined_classes"]:
                        clean_c = str(c).strip()
                        if clean_c and clean_c not in t_classes:
                            t_classes.append(clean_c)
                        if clean_c and clean_c not in t_combined_classes:
                            t_combined_classes.append(clean_c)
                elif "+" in c_raw or ("," in c_raw and a.get("is_combined")):
                    comb_cls_type = typ
                    for c in c_raw.replace("&", "+").replace(",", "+").split("+"):
                        c_clean = c.strip()
                        if c_clean and c_clean not in t_classes:
                            t_classes.append(c_clean)
                        if c_clean and c_clean not in t_combined_classes:
                            t_combined_classes.append(c_clean)
                elif c_raw:
                    if c_raw not in t_classes:
                        t_classes.append(c_raw)
                    sep_hours[format_tr_name(c_raw)] = typ
                    if self.current_class and (format_tr_name(c_raw) == format_tr_name(self.current_class) or matches_class(c_raw, self.current_class)):
                        cur_cls_type = typ

            if not cur_cls_type:
                cur_cls_type = ""
            if not comb_cls_type:
                comb_cls_type = ""
                
            if self.current_class:
                cur_c = format_tr_name(self.current_class)
                is_checked = any(format_tr_name(c) == cur_c or matches_class(c, cur_c) or matches_class(cur_c, c) for c in t_classes)
            else:
                is_checked = bool(t_asgns)
                
            self.teacher_configs[t] = {
                "checked": is_checked,
                "current_class_type": cur_cls_type,
                "combined_type": comb_cls_type,
                "classes": t_classes,
                "combined_classes": t_combined_classes,
                "is_combined": bool(t_combined_classes) or bool(comb_cls_type) or any(a.get("is_combined") for a in t_asgns),
                "separate_hours": sep_hours
            }

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)
        
        # Header Info Card
        top_card = QFrame()
        top_card.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; }")
        top_lay = QHBoxLayout(top_card)
        top_lay.setContentsMargins(12, 8, 12, 8)
        
        v_title = QVBoxLayout()
        lbl_h = QLabel(f"📚 {self.subject_name} Dersi — Öğretmen ve Saat Atama Paneli")
        lbl_h.setStyleSheet("font-size: 16px; color: #2563EB; font-weight: bold;")
        v_title.addWidget(lbl_h)
        
        cls_info = f"Hedef Sınıf: <b>{self.current_class}</b>" if self.current_class else "Tüm Sınıflar"
        lbl_sub = QLabel(f"{cls_info} | Seçilen öğretmene ders saati ve dağılım tipi otomatik eşleştirilir.")
        lbl_sub.setStyleSheet("color: #64748B; font-size: 12px; font-weight: normal;")
        v_title.addWidget(lbl_sub)
        top_lay.addLayout(v_title)
        top_lay.addStretch(1)
        lay.addWidget(top_card)
        
        # Minimalist Real-Time Search Bar
        search_lay = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Öğretmen Ara (Gerçek Zamanlı)...")
        self.txt_search.textChanged.connect(self._filter_table)
        search_lay.addWidget(self.txt_search)
        lay.addLayout(search_lay)
        
        # Table (Integrated Teacher + Target Class Hours + Combined Hours + Classes)
        self.table = QTableWidget(0, 5)
        cls_col_label = f"{self.current_class} Saati" if self.current_class else "Ders Saati"
        self.table.setHorizontalHeaderLabels([
            "Atanacak Öğretmen", cls_col_label, "🔗 Birleşik Ders Saati", "Atanan Sınıf(lar)", "Ayrıcalıklı Sınıf Seçimi"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(2, 160)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setColumnWidth(4, 180)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.setWordWrap(True)
        self.table.setAlternatingRowColors(True)
        lay.addWidget(self.table, 1)
        
        # Bottom Actions
        bot = QHBoxLayout()
        btn_clear = QPushButton("🗑️ Bu Dersi Kaldır")
        btn_clear.setStyleSheet("background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;")
        btn_clear.clicked.connect(self._clear_assignments)
        bot.addWidget(btn_clear)
        
        bot.addStretch(1)
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background: #FFFFFF; color: #475569; border: 1px solid #CBD5E1;")
        btn_cancel.clicked.connect(self.reject)
        bot.addWidget(btn_cancel)
        
        btn_save = QPushButton("💾 Kaydet ve Eşleştir")
        btn_save.setStyleSheet("background: #2563EB; color: white; border: none;")
        btn_save.clicked.connect(self._save_assignments)
        bot.addWidget(btn_save)
        
        lay.addLayout(bot)

    def _create_hour_combo(self, t_name, current_val, is_combined=False):
        cb_tip = QComboBox()
        cb_tip.wheelEvent = lambda event: event.ignore()  # Prevent accidental scroll adjustments
        cb_tip.setEditable(True)
        cb_tip.addItems(["", "1", "2", "3", "4", "5", "6", "7", "8", "1+1", "2+1", "2+2", "3+1", "3+2", "2+2+1", "2+2+2", "2+2+3"])
        if cb_tip.lineEdit():
            cb_tip.lineEdit().setPlaceholderText("Saat Yaz")
            if is_combined:
                cb_tip.lineEdit().editingFinished.connect(lambda t=t_name, cb=cb_tip: self._on_combined_type_changed(t, cb.currentText()))
            else:
                cb_tip.lineEdit().editingFinished.connect(lambda t=t_name, cb=cb_tip: self._on_current_type_changed(t, cb.currentText()))
            
        cur_str = str(current_val).strip()
        cb_tip.setCurrentText(cur_str if cur_str and cur_str != "0" else "")
        if is_combined:
            cb_tip.activated.connect(lambda idx, t=t_name, cb=cb_tip: self._on_combined_type_changed(t, cb.currentText()))
        else:
            cb_tip.activated.connect(lambda idx, t=t_name, cb=cb_tip: self._on_current_type_changed(t, cb.currentText()))
        
        return cb_tip

    def _create_class_modal_btn(self, t_name, row_idx):
        btn = QPushButton("⚙️ Daha Fazla Sınıf Ata")
        btn.setFixedHeight(28)
        btn.setStyleSheet("background: #F0F9FF; color: #0284C7; border: 1px solid #BAE6FD; border-radius: 5px; font-size: 11px; font-weight: bold;")
        btn.clicked.connect(lambda chk=False, t=t_name, r=row_idx: self._open_class_modal(t, r))
        return btn

    def _format_class_display_text(self, cfg):
        classes = cfg.get("classes", [])
        comb_classes = cfg.get("combined_classes", [])
        is_comb = bool(cfg.get("is_combined") and comb_classes and len(comb_classes) > 1)
        
        if not (cfg.get("checked") and classes):
            return "—", False
            
        if is_comb:
            separate = [c for c in classes if c not in comb_classes]
            comb_str = "+".join(comb_classes)
            if separate:
                main_str = f"{', '.join(separate)}, {comb_str} (🔗 Birleşik)"
            else:
                main_str = f"{comb_str} (🔗 Birleşik)"
            return main_str, True
        else:
            return ", ".join(classes), False

    def _populate_table(self):
        self.table.setRowCount(0)
        all_teachers = sorted(list(self.teacher_configs.keys()))
        
        for t_name in all_teachers:
            cfg = self.teacher_configs[t_name]
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # 0. Container with Clean Visible CheckBox
            w_chk = QWidget()
            l_chk = QHBoxLayout(w_chk)
            l_chk.setContentsMargins(12, 0, 4, 0)
            l_chk.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            chk = QCheckBox(t_name)
            chk.setChecked(cfg["checked"])
            chk.setStyleSheet("QCheckBox { font-weight: bold; color: #0F172A; font-size: 13px; spacing: 8px; } QCheckBox::indicator { width: 16px; height: 16px; }")
            chk.toggled.connect(lambda state, t=t_name: self._on_teacher_toggled(t, state))
            l_chk.addWidget(chk)
            self.table.setCellWidget(row, 0, w_chk)
            
            # 1. Target / Current Class Hours (Only created when checked!)
            if cfg["checked"]:
                self.table.setCellWidget(row, 1, self._create_hour_combo(t_name, cfg.get("current_class_type", "2"), is_combined=False))
            else:
                self.table.removeCellWidget(row, 1)
                it1 = QTableWidgetItem("—")
                it1.setTextAlignment(Qt.AlignCenter)
                it1.setForeground(QBrush(QColor("#CBD5E1")))
                it1.setFlags(it1.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row, 1, it1)
                
            # 2. Combined Class Hours (Always created when checked to allow immediate entry, empty if not combined)
            if cfg["checked"]:
                combined_val = cfg.get("combined_type", "2+2") if cfg.get("is_combined") else ""
                self.table.setCellWidget(row, 2, self._create_hour_combo(t_name, combined_val, is_combined=True))
            else:
                self.table.removeCellWidget(row, 2)
                it2 = QTableWidgetItem("—")
                it2.setTextAlignment(Qt.AlignCenter)
                it2.setForeground(QBrush(QColor("#CBD5E1")))
                it2.setFlags(it2.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row, 2, it2)
            
            # 3. Classes Label / Badges
            cls_str, is_comb = self._format_class_display_text(cfg)
            item_cls = QTableWidgetItem(cls_str)
            item_cls.setTextAlignment(Qt.AlignCenter)
            item_cls.setFlags(item_cls.flags() ^ Qt.ItemIsEditable)
            if not cfg["checked"]:
                item_cls.setForeground(QBrush(QColor("#CBD5E1")))
            else:
                if is_comb:
                    item_cls.setForeground(QBrush(QColor("#16A34A")))  # Green for combined
                else:
                    item_cls.setForeground(QBrush(QColor("#0284C7")))
                item_cls.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(row, 3, item_cls)
            
            # 4. Class Assignment Modal Button (Only created when checked!)
            if cfg["checked"]:
                self.table.setCellWidget(row, 4, self._create_class_modal_btn(t_name, row))
            else:
                self.table.removeCellWidget(row, 4)
                it4 = QTableWidgetItem("—")
                it4.setTextAlignment(Qt.AlignCenter)
                it4.setForeground(QBrush(QColor("#CBD5E1")))
                it4.setFlags(it4.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row, 4, it4)

    def _on_teacher_toggled(self, teacher_name, is_checked):
        self.teacher_configs[teacher_name]["checked"] = is_checked
        
        # If current_class is specified, sync classes list with checkbox state
        if self.current_class:
            cur_c = self.current_class
            classes_list = self.teacher_configs[teacher_name]["classes"]
            if is_checked:
                if not any(format_tr_name(c) == format_tr_name(cur_c) or matches_class(c, cur_c) for c in classes_list):
                    classes_list.append(cur_c)
            else:
                classes_list = [c for c in classes_list if format_tr_name(c) != format_tr_name(cur_c) and not matches_class(c, cur_c)]
                self.teacher_configs[teacher_name]["classes"] = classes_list
                comb_list = [c for c in self.teacher_configs[teacher_name].get("combined_classes", []) if format_tr_name(c) != format_tr_name(cur_c) and not matches_class(c, cur_c)]
                if len(comb_list) <= 1:
                    comb_list = []
                self.teacher_configs[teacher_name]["combined_classes"] = comb_list
                self.teacher_configs[teacher_name]["is_combined"] = bool(comb_list)
        else:
            if is_checked and not self.teacher_configs[teacher_name]["classes"]:
                if self.all_classes:
                    self.teacher_configs[teacher_name]["classes"] = [self.all_classes[0]]
                
        # Find row and show/hide widgets cleanly
        for r in range(self.table.rowCount()):
            w_chk = self.table.cellWidget(r, 0)
            if w_chk:
                chk = w_chk.findChild(QCheckBox)
                if chk and chk.text() == teacher_name:
                    item_cls = self.table.item(r, 3)
                    cfg = self.teacher_configs[teacher_name]
                    
                    if is_checked:
                        self.table.setCellWidget(r, 1, self._create_hour_combo(teacher_name, cfg.get("current_class_type", "2"), is_combined=False))
                        if cfg.get("is_combined"):
                            self.table.setCellWidget(r, 2, self._create_hour_combo(teacher_name, cfg.get("combined_type", "2+2"), is_combined=True))
                        else:
                            self.table.setCellWidget(r, 2, self._create_hour_combo(teacher_name, "", is_combined=True))
                            
                        if item_cls:
                            cls_str, is_comb = self._format_class_display_text(cfg)
                            item_cls.setText(cls_str)
                            item_cls.setForeground(QBrush(QColor("#16A34A") if is_comb else QColor("#0284C7")))
                            item_cls.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                        self.table.setCellWidget(r, 4, self._create_class_modal_btn(teacher_name, r))
                    else:
                        self.table.removeCellWidget(r, 1)
                        it1 = QTableWidgetItem("—")
                        it1.setTextAlignment(Qt.AlignCenter)
                        it1.setForeground(QBrush(QColor("#CBD5E1")))
                        it1.setFlags(it1.flags() ^ Qt.ItemIsEditable)
                        self.table.setItem(r, 1, it1)
                        
                        self.table.removeCellWidget(r, 2)
                        it2 = QTableWidgetItem("—")
                        it2.setTextAlignment(Qt.AlignCenter)
                        it2.setForeground(QBrush(QColor("#CBD5E1")))
                        it2.setFlags(it2.flags() ^ Qt.ItemIsEditable)
                        self.table.setItem(r, 2, it2)
                        
                        if item_cls:
                            item_cls.setText("—")
                            item_cls.setForeground(QBrush(QColor("#CBD5E1")))
                            
                        self.table.removeCellWidget(r, 4)
                        it4 = QTableWidgetItem("—")
                        it4.setTextAlignment(Qt.AlignCenter)
                        it4.setForeground(QBrush(QColor("#CBD5E1")))
                        it4.setFlags(it4.flags() ^ Qt.ItemIsEditable)
                        self.table.setItem(r, 4, it4)
                    break

    def _on_current_type_changed(self, teacher_name, new_type):
        self.teacher_configs[teacher_name]["current_class_type"] = str(new_type).strip()

    def _on_combined_type_changed(self, teacher_name, new_type):
        self.teacher_configs[teacher_name]["combined_type"] = str(new_type).strip()

    def _open_class_modal(self, teacher_name, row_idx):
        cfg = self.teacher_configs[teacher_name]
        d = MultiClassAssignDialog(
            teacher_name=teacher_name,
            subject_name=self.subject_name,
            all_classes=self.all_classes,
            selected_classes=cfg.get("classes", []),
            combined_classes=cfg.get("combined_classes", []),
            is_combined=cfg.get("is_combined", False),
            parent=self
        )
        if d.exec():
            new_classes = d.get_selected_classes()
            new_combined = d.get_combined_classes()
            is_comb = d.get_is_combined()
            cfg["classes"] = new_classes
            cfg["combined_classes"] = new_combined
            cfg["is_combined"] = is_comb
            
            # Automatically check the row if classes are selected
            if new_classes and not cfg.get("checked"):
                cfg["checked"] = True
                w_chk = self.table.cellWidget(row_idx, 0)
                if w_chk:
                    chk = w_chk.findChild(QCheckBox)
                    if chk:
                        chk.setChecked(True)
                        
            # Update Current Class Hour Combo
            self.table.setCellWidget(row_idx, 1, self._create_hour_combo(teacher_name, cfg.get("current_class_type", "2"), is_combined=False))
            
            # Update Combined Class Hour Combo
            if is_comb:
                self.table.setCellWidget(row_idx, 2, self._create_hour_combo(teacher_name, cfg.get("combined_type", "2+2"), is_combined=True))
            else:
                self.table.removeCellWidget(row_idx, 2)
                it2 = QTableWidgetItem("—")
                it2.setTextAlignment(Qt.AlignCenter)
                it2.setForeground(QBrush(QColor("#CBD5E1")))
                it2.setFlags(it2.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row_idx, 2, it2)
                
            item_cls = self.table.item(row_idx, 3)
            if item_cls:
                cls_str, is_comb_flag = self._format_class_display_text(cfg)
                item_cls.setForeground(QBrush(QColor("#16A34A") if is_comb_flag else QColor("#0284C7")))
                item_cls.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                item_cls.setText(cls_str)

    def _filter_table(self, text):
        query = text.strip().lower()
        for r in range(self.table.rowCount()):
            w_chk = self.table.cellWidget(r, 0)
            t_name = ""
            if w_chk:
                chk = w_chk.findChild(QCheckBox)
                if chk:
                    t_name = chk.text().lower()
            if query in t_name:
                self.table.setRowHidden(r, False)
            else:
                self.table.setRowHidden(r, True)

    def _clear_assignments(self):
        # Uncheck all teachers and clear their classes if in target_cls mode
        for t_name in self.teacher_configs:
            self.teacher_configs[t_name]["checked"] = False
            if self.current_class:
                cur_c = format_tr_name(self.current_class)
                self.teacher_configs[t_name]["classes"] = [c for c in self.teacher_configs[t_name]["classes"] if format_tr_name(c) != cur_c and not matches_class(c, cur_c)]
                comb_list = [c for c in self.teacher_configs[t_name].get("combined_classes", []) if format_tr_name(c) != cur_c and not matches_class(c, cur_c)]
                if len(comb_list) <= 1:
                    comb_list = []
                self.teacher_configs[t_name]["combined_classes"] = comb_list
                self.teacher_configs[t_name]["is_combined"] = bool(comb_list)
            else:
                self.teacher_configs[t_name]["classes"] = []
                self.teacher_configs[t_name]["combined_classes"] = []
                self.teacher_configs[t_name]["is_combined"] = False
                
        # This will automatically clean atamalar, grid_placements, and yerlesim based on our robust logic
        self._save_assignments()

    def _save_assignments(self):
        # UI'daki güncel ComboBox değerlerini zorla kaydet (editingFinished tetiklenmemiş olabilir)
        for r in range(self.table.rowCount()):
            w_chk = self.table.cellWidget(r, 0)
            if w_chk:
                from PySide6.QtWidgets import QCheckBox, QComboBox
                chk = w_chk.findChild(QCheckBox)
                if chk and chk.isChecked():
                    t_name = chk.text()
                    if t_name in self.teacher_configs:
                        w_cur = self.table.cellWidget(r, 1)
                        if w_cur and isinstance(w_cur, QComboBox):
                            self.teacher_configs[t_name]["current_class_type"] = w_cur.currentText().strip()
                        w_comb = self.table.cellWidget(r, 2)
                        if w_comb and isinstance(w_comb, QComboBox):
                            self.teacher_configs[t_name]["combined_type"] = w_comb.currentText().strip()

        win = self.window()
        if not win or not hasattr(win, "_push_undo_state"):
            p = self.parent()
            while p:
                if hasattr(p, "_push_undo_state"):
                    win = p
                    break
                p = p.parent()
        if win and hasattr(win, "_push_undo_state"):
            win._push_undo_state()

        subj_target = format_tr_name(self.subject_name)
        target_cls = format_tr_name(self.current_class) if self.current_class else ""
        atamalar = self.data_store.get("atamalar", [])
        
        clean_atamalar = []
        
        # 1. Keep assignments that are completely unrelated to this subject
        for a in atamalar:
            if format_tr_name(a.get("subject", "")) != subj_target:
                clean_atamalar.append(a)
                
        # 2. Keep assignments for teachers we are NOT managing in this dialog
        managed_teachers = [format_tr_name(t) for t in self.teacher_configs.keys()]
        for a in atamalar:
            if format_tr_name(a.get("subject", "")) == subj_target:
                t_name = format_tr_name(a.get("teacher", ""))
                if not any(_matches_teacher(t_name, mt) for mt in managed_teachers):
                    clean_atamalar.append(a)
                    
        # 3. Recreate assignments for managed teachers based on their configuration
        for t_name, cfg in self.teacher_configs.items():
            is_checked = cfg.get("checked", False)
            classes = cfg.get("classes", [])
            classes = [c for c in classes if str(c).strip()]
            
            # If the teacher is not checked for this class, remove this class from their list.
            if not is_checked:
                if self.current_class:
                    cur_c = format_tr_name(self.current_class)
                    classes = [c for c in classes if format_tr_name(c) != cur_c and not matches_class(c, cur_c)]
                    comb_classes = [c for c in cfg.get("combined_classes", []) if format_tr_name(c) != cur_c and not matches_class(c, cur_c)]
                    if len(comb_classes) <= 1:
                        comb_classes = []
                    cfg["combined_classes"] = comb_classes
                    cfg["is_combined"] = bool(comb_classes)
                else:
                    classes = []
                    cfg["combined_classes"] = []
                    cfg["is_combined"] = False
            
            if not classes:
                continue
                
            comb_classes = list(cfg.get("combined_classes", []))
            comb_type_str = str(cfg.get("combined_type", "")).strip()
            
            if not comb_classes and comb_type_str:
                comb_classes = list(classes)
                cfg["combined_classes"] = comb_classes
                cfg["is_combined"] = True
                
            is_combined = bool(cfg.get("is_combined", False)) or bool(comb_type_str)
            
            # 1. Save Combined Classes with combined_type!
            if is_combined and comb_classes:
                if not comb_type_str:
                    comb_type_str = "2"
                parts = [int(p.strip()) for p in comb_type_str.split("+") if p.strip().isdigit()]
                comb_dur = sum(parts) if parts else (int(comb_type_str) if comb_type_str.isdigit() else 2)
                
                comb_name = " + ".join(comb_classes)
                clean_atamalar.append({
                    "teacher": t_name.strip(),
                    "subject": self.subject_name.strip(),
                    "class": comb_name,
                    "duration": comb_dur,
                    "type": comb_type_str,
                    "color": get_subject_color(self.subject_name),
                    "is_combined": True,
                    "combined_classes": list(comb_classes)
                })
                
            # 2. Save Separate Classes (Target class gets current_class_type, others preserve their own separate hours)
            separate_classes = [c for c in classes if c not in comb_classes] if is_combined else classes
            for c in separate_classes:
                if self.current_class and (format_tr_name(c) == format_tr_name(self.current_class) or matches_class(c, self.current_class)):
                    cur_type_str = str(cfg.get("current_class_type", "")).strip()
                    parts = [int(p.strip()) for p in cur_type_str.split("+") if p.strip().isdigit()]
                    dur = sum(parts) if parts else (int(cur_type_str) if cur_type_str.isdigit() else 0)
                    typ = cur_type_str if dur > 0 else ""
                else:
                    old_typ = cfg.get("separate_hours", {}).get(format_tr_name(c))
                    if not old_typ:
                        old_a = next((a for a in atamalar if format_tr_name(a.get("subject", "")) == subj_target and _matches_teacher(a.get("teacher", ""), t_name) and format_tr_name(a.get("class", "")) == format_tr_name(c)), None)
                        if old_a and str(old_a.get("type", "")).strip():
                            old_typ = str(old_a.get("type", "")).strip()
                        elif old_a and int(old_a.get("duration", 0)) > 0:
                            old_typ = str(old_a.get("duration", 0))
                        else:
                            old_typ = ""
                            
                    parts = [int(p.strip()) for p in old_typ.split("+") if p.strip().isdigit()]
                    dur = sum(parts) if parts else (int(old_typ) if old_typ.isdigit() else 0)
                    typ = old_typ if dur > 0 else ""
                    
                clean_atamalar.append({
                    "teacher": t_name.strip(),
                    "subject": self.subject_name.strip(),
                    "class": c.strip(),
                    "duration": dur,
                    "type": typ,
                    "color": get_subject_color(self.subject_name),
                    "is_combined": False,
                    "combined_classes": []
                })
                    
        from version_store import sanitize_atamalar
        self.data_store["atamalar"] = sanitize_atamalar(clean_atamalar)
        trigger_save_db(self, self.data_store)
        
        # Grid Placements Synchronization
        active_pairs = set()
        for a in self.data_store["atamalar"]:
            s = format_tr_name(a.get("subject", ""))
            t = format_tr_name(a.get("teacher", ""))
            c_raw = str(a.get("class", ""))
            active_pairs.add((s, format_tr_name(c_raw), t))
            if a.get("is_combined") and a.get("combined_classes"):
                for c in a["combined_classes"]:
                    active_pairs.add((s, format_tr_name(c), t))
            if "+" in c_raw or "," in c_raw or "&" in c_raw:
                for part in c_raw.replace("&", "+").replace(",", "+").split("+"):
                    if part.strip():
                        active_pairs.add((s, format_tr_name(part.strip()), t))
        
        grid_data = self.data_store.get("grid_placements", [])
        if isinstance(grid_data, list):
            if target_cls:
                self.data_store["grid_placements"] = [
                    p for p in grid_data
                    if not (
                        format_tr_name(p.get("subject_name", p.get("subject", ""))) == subj_target and
                        format_tr_name(p.get("class_name", p.get("class", ""))) == target_cls and
                        (subj_target, target_cls, format_tr_name(p.get("teacher_name", p.get("teacher", "")))) not in active_pairs
                    )
                ]
            else:
                self.data_store["grid_placements"] = [
                    p for p in grid_data
                    if (format_tr_name(p.get("subject_name", p.get("subject", ""))),
                        format_tr_name(p.get("class_name", p.get("class", ""))),
                        format_tr_name(p.get("teacher_name", p.get("teacher", "")))) in active_pairs
                ]
                
        yerlesim = self.data_store.get("yerlesim", {})
        if isinstance(yerlesim, dict):
            for k in list(yerlesim.keys()):
                info = yerlesim[k]
                if isinstance(info, dict):
                    t_subj = format_tr_name(info.get("subject_name", info.get("subject", "")))
                    t_cls = format_tr_name(info.get("class_name", info.get("class", "")))
                    t_tea = format_tr_name(info.get("teacher_name", info.get("teacher", "")))
                    
                    if target_cls:
                        if t_subj == subj_target and t_cls == target_cls and (t_subj, t_cls, t_tea) not in active_pairs:
                            yerlesim.pop(k, None)
                    else:
                        if (t_subj, t_cls, t_tea) not in active_pairs:
                            yerlesim.pop(k, None)
                            
        win = self.window()
        if not win or not hasattr(win, "_grid"):
            p = self.parent()
            while p:
                if hasattr(p, "_grid"):
                    win = p
                    break
                p = p.parent()
        if win:
            if hasattr(win, "save_db"): win.save_db(sync_from_grid=False)
            if hasattr(win, "_refresh_tree"): win._refresh_tree()
            if hasattr(win, "_grid") and hasattr(win._grid, "load_data"):
                win._grid.load_data(win.data_store)

        self.accept()


class SinifEditDialog(BaseEditForm):
    def __init__(self, parent=None, existing_data=None):
        super().__init__("Sınıf", parent, existing_data)
        self._color = self.existing_data.get("renk", "#A30F37")
        self._build_ui()
        
    def _build_ui(self):
        form = QFormLayout()
        form.setSpacing(12)
        
        self.w_ad = QLineEdit(self.existing_data.get("ad", ""))
        self.w_ad.textChanged.connect(self._auto_short_code_class)
        self.w_kisa = QLineEdit(self.existing_data.get("kisa", ""))
        form.addRow("Sınıf Adı", self.w_ad)
        form.addRow("Kısa Kodu", self.w_kisa)
        self.main_layout.addLayout(form)
        
        btn_ozel = QPushButton("Özel Alanlar...")
        btn_ozel.setFixedWidth(200)
        btn_ozel.setStyleSheet("background: #F1F5F9; color: #1E293B; font-weight: 500;")
        btn_ozel.clicked.connect(self._open_custom_fields)
        btn_ozel_lay = QHBoxLayout()
        btn_ozel_lay.addStretch(1); btn_ozel_lay.addWidget(btn_ozel); btn_ozel_lay.addStretch(1)
        self.main_layout.addLayout(btn_ozel_lay)
        
        cb_lay = QHBoxLayout()
        cb_lay.addStretch(1)
        self.cb_foto = QCheckBox("Fotoğrafları yazdırın")
        self.cb_foto.setChecked(self.existing_data.get("foto", True))
        cb_lay.addWidget(self.cb_foto)
        cb_lay.addStretch(1)
        self.main_layout.addLayout(cb_lay)
        
        lbl_renk = QLabel("Renk Kodu")
        self.main_layout.addWidget(lbl_renk)
        
        renk_frame = QFrame()
        renk_frame.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
        r_lay = QHBoxLayout(renk_frame)
        self.color_box = QLabel()
        self.color_box.setFixedSize(180, 50)
        self.color_box.setStyleSheet(f"background: {self._color};")
        btn_degistir = QPushButton("Değiştir")
        btn_degistir.setFixedSize(80, 28)
        btn_degistir.clicked.connect(self._pick_color)
        r_lay.addWidget(self.color_box)
        r_lay.addStretch(1)
        r_lay.addWidget(btn_degistir)
        r_lay.addStretch(1)
        self.main_layout.addWidget(renk_frame)
        
        so_lay = QHBoxLayout()
        so_lay.addWidget(QLabel("Sınıf Öğretmeni:"))
        
        self.w_so = QComboBox()
        teachers = [""]
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        if not data_store and hasattr(p, "main_window"):
            data_store = getattr(p.main_window, "data_store", {})
        raw_teachers = [t.get("ad", "") for t in data_store.get("ogretmenler", []) if t.get("ad")]
        teachers.extend(sorted(raw_teachers))
        self.w_so.addItems(teachers)
        
        c_name = self.existing_data.get("ad", "").strip()
        existing_so = self.existing_data.get("sinif_ogretmeni", "").strip()
        if not existing_so and data_store and c_name:
            for t in data_store.get("ogretmenler", []):
                if (t.get("sinif_ogretmeni") or "").strip().upper() == c_name.upper():
                    existing_so = t.get("ad", "").strip()
                    break
        idx_so = self.w_so.findText(existing_so)
        if idx_so >= 0:
            self.w_so.setCurrentIndex(idx_so)
            
        so_lay.addWidget(self.w_so)
        self.main_layout.addLayout(so_lay)
        
        form2 = QFormLayout()
        self.w_sinif = QComboBox()
        self.w_sinif.addItems(["Hepsi", "Sabah", "Öğle"])
        idx = self.w_sinif.findText(self.existing_data.get("sinif_tipi", "Hepsi"))
        if idx >= 0: self.w_sinif.setCurrentIndex(idx)
        form2.addRow("Sınıf:", self.w_sinif)
        
        self.w_num = QLineEdit(str(self.existing_data.get("kapasite", "30")))
        form2.addRow("Öğrenci Sayısı (Kapasite):", self.w_num)
        
        self.w_max_gunluk = QLineEdit(str(self.existing_data.get("ders_bitimi", "15:30")))
        form2.addRow("Ders Bitim Saati:", self.w_max_gunluk)
        h_btn_lay = QHBoxLayout()
        btn_hoca_ata = QPushButton("🎓 Ders & Öğretmen Ata")
        btn_hoca_ata.setStyleSheet("background: #0078D7; color: white; font-weight: bold; min-height: 32px; border-radius: 4px;")
        btn_hoca_ata.clicked.connect(self._assign_lessons_for_this_class)
        
        btn_cizelge = QPushButton("🖨️ Çizelge Göster / Yazdır")
        btn_cizelge.setStyleSheet("background: #27AE60; color: white; font-weight: bold; min-height: 32px; border-radius: 4px;")
        btn_cizelge.clicked.connect(self._show_class_timetable)
        
        h_btn_lay.addWidget(btn_hoca_ata)
        h_btn_lay.addWidget(btn_cizelge)
        self.main_layout.addLayout(h_btn_lay)

        self._add_bottom_buttons()

    def _show_class_timetable(self):
        c_name = self.w_ad.text().strip()
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        from dialogs.print_preview import TimetablePrintPreview
        filters = {"entity_type": "class_list", "default_selection": c_name, "lock_mode": "Sınıf Dersleri & Atama Listesi (Liste Formatı)"}
        dlg = TimetablePrintPreview(data_store=data_store, filters=filters, parent=self)
        dlg.exec()

    def _assign_lessons_for_this_class(self):
        c_name = self.w_ad.text().strip()
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        d = ClassComprehensiveAssignmentDialog(class_name=c_name, data_store=data_store, parent=p or self)
        if d.exec():
            trigger_save_db(self, data_store)

    def _pick_color(self):
        from dialogs.color_picker_dialog import ModernColorPickerDialog
        c_name = self.w_ad.text().strip() or "Sınıf"
        c = ModernColorPickerDialog.pick_color(
            initial_color=self._color,
            parent=self,
            title=f"🎨 {c_name} — Renk Seçimi"
        )
        if c and c.isValid():
            self._color = c.name()
            self.color_box.setStyleSheet(f"background: {self._color}; border: 1px solid #CCC; border-radius: 4px;")
            
    def _auto_short_code_class(self, text):
        if text:
            self.w_kisa.setText(text.strip().replace(" ", "").upper())

    def _open_custom_fields(self):
        c_name = self.w_ad.text().strip() or "Sınıf"
        dlg = CustomFieldsDialog(c_name, "Sınıf", self.existing_data.get("ozel_alanlar", {}), self)
        if dlg.exec() == QDialog.Accepted:
            self.existing_data["ozel_alanlar"] = dlg.get_data()

    def get_data(self):
        return {
            "ad": self.w_ad.text(), "kisa": self.w_kisa.text(), 
            "renk": self._color, "foto": self.cb_foto.isChecked(),
            "sinif_ogretmeni": self.w_so.currentText(), "sinif_tipi": self.w_sinif.currentText(),
            "kapasite": self.w_num.text(), "ders_bitimi": self.w_max_gunluk.text(),
            "ozel_alanlar": self.existing_data.get("ozel_alanlar", {})
        }


class OgretmenEditDialog(BaseEditForm):
    def __init__(self, parent=None, existing_data=None):
        super().__init__("Öğretmen Düzenle", parent, existing_data)
        self.resize(600, 680)
        self.setMinimumSize(550, 650)
        self._color = self.existing_data.get("renk", "#27AE60")
        self._build_ui()
        
    def _build_ui(self):
        # 1. Temel Bilgiler Frame
        frame_temel = QFrame()
        frame_temel.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 6px; }")
        lay_temel = QFormLayout(frame_temel)
        lay_temel.setContentsMargins(15, 15, 15, 15)
        lay_temel.setSpacing(12)
        
        self.w_ad = QLineEdit(self.existing_data.get("ad", ""))
        self.w_ad.setPlaceholderText("Öğretmen Adı Soyadı")
        self.w_ad.textChanged.connect(self._auto_short_code_teacher)
        self.w_kisa = QLineEdit(self.existing_data.get("kisa", ""))
        self.w_kisa.setPlaceholderText("Kısa Kod (Örn: A. YILMAZ)")
        
        lay_temel.addRow(QLabel("<b>Öğretmen Adı:</b>"), self.w_ad)
        lay_temel.addRow(QLabel("<b>Kısa Kodu:</b>"), self.w_kisa)
        
        btn_ozel = QPushButton("Özel Alanlar...")
        btn_ozel.setStyleSheet("background: #F1F5F9; color: #1E293B; font-weight: 500;")
        btn_ozel.clicked.connect(self._open_custom_fields)
        lay_temel.addRow("", btn_ozel)
        
        self.main_layout.addWidget(frame_temel)
        
        # 2. Görev ve Sınıf Frame
        frame_gorev = QFrame()
        frame_gorev.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 6px; }")
        lay_gorev = QFormLayout(frame_gorev)
        self.w_so = QComboBox()
        classes = [""]
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        if not data_store and hasattr(p, "main_window"):
            data_store = getattr(p.main_window, "data_store", {})
        raw_classes = [c.get("ad", "") for c in data_store.get("siniflar", []) if c.get("ad")]
        classes.extend(sorted(raw_classes))
        self.w_so.addItems(classes)
        
        t_name = self.existing_data.get("ad", "").strip()
        existing_so = self.existing_data.get("sinif_ogretmeni", "").strip()
        if not existing_so and data_store and t_name:
            for s in data_store.get("siniflar", []):
                if format_tr_name(s.get("sinif_ogretmeni", "").strip()) == format_tr_name(t_name):
                    existing_so = s.get("ad", "").strip()
                    break
        idx_so = self.w_so.findText(existing_so)
        if idx_so >= 0:
            self.w_so.setCurrentIndex(idx_so)
        
        lay_gorev.addRow(QLabel("<b>Sınıf Öğretmeni (Rehberlik):</b>"), self.w_so)
        
        # Branch is now a multi-branch field with "Branş(lar) Ata..." popup dialog
        h_brans_lay = QHBoxLayout()
        existing_brans = self.existing_data.get("brans", "").strip()
        self.w_brans = QLineEdit(existing_brans)
        self.w_brans.setReadOnly(True)
        self.w_brans.setPlaceholderText("Branş atanmadı...")
        self.w_brans.setStyleSheet("background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 8px; font-weight: bold; color: #0369A1;")
        
        btn_brans_ata = QPushButton("Branş(lar) Ata...")
        btn_brans_ata.setFixedSize(125, 30)
        btn_brans_ata.setStyleSheet("background: #F0F9FF; color: #0284C7; border: 1px solid #BAE6FD; border-radius: 4px; font-size: 11px; font-weight: bold;")
        
        def open_branch_dialog():
            raw_subjects = [d.get("ad", "").strip() for d in data_store.get("dersler", []) if d.get("ad")]
            current_b_list = [b.strip() for b in self.w_brans.text().split(",") if b.strip()]
            for b in current_b_list:
                if b not in raw_subjects:
                    raw_subjects.append(b)
            dlg = BranchMultiSelectDialog(
                teacher_name=self.w_ad.text().strip() or "Öğretmen",
                all_branches=sorted(list(set(raw_subjects))),
                selected_branches=current_b_list,
                parent=self
            )
            if dlg.exec():
                sel = dlg.get_selected_branches()
                self.w_brans.setText(", ".join(sel))
                
        btn_brans_ata.clicked.connect(open_branch_dialog)
        h_brans_lay.addWidget(self.w_brans, 1)
        h_brans_lay.addWidget(btn_brans_ata)
        lay_gorev.addRow(QLabel("<b>Öğretmen Branş(lar)ı:</b>"), h_brans_lay)
        
        self.chk_es_zamanli = QCheckBox("Aynı saatte çoklu/paralel ders girebilir (Çoklu Ders İzni)")
        self.chk_es_zamanli.setChecked(self.existing_data.get("es_zamanli", False))
        lay_gorev.addRow("", self.chk_es_zamanli)
        
        self.main_layout.addWidget(frame_gorev)
        
        # 3. Dersler ve Planlama Frame
        frame_ders = QFrame()
        frame_ders.setStyleSheet(".QFrame { background: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 6px; }")
        lay_ders = QVBoxLayout(frame_ders)
        lay_ders.setContentsMargins(15, 12, 15, 12)
        lay_ders.setSpacing(10)
        
        lbl_dersler = QLabel("<b>Atandığı Sınıflar ve Dersler (Gerçek Zamanlı):</b>")
        lbl_dersler.setFont(QFont("Segoe UI", 9))
        lay_ders.addWidget(lbl_dersler)
        
        self.list_assignments = QListWidget()
        self.list_assignments.setFixedHeight(80)
        self.list_assignments.setStyleSheet("QListWidget { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 4px; font-size: 11px; padding: 4px; }")
        
        atamalar = data_store.get("atamalar", [])
        my_name = self.existing_data.get("ad", "")
        my_atamalar = [a for a in atamalar if format_tr_name(a.get("teacher", "")) == format_tr_name(my_name)]
        my_subjects = list({a.get("subject", "") for a in my_atamalar if a.get("subject")})
        
        for a in my_atamalar:
            item_text = f"• {a.get('subject', '')}  →  {a.get('class', '')} ({a.get('duration', 0)} Saat)"
            item = QListWidgetItem(item_text)
            self.list_assignments.addItem(item)
        if not my_atamalar:
            self.list_assignments.addItem(QListWidgetItem("Henüz hiçbir derse veya sınıfa atanmadı."))
            
        lay_ders.addWidget(self.list_assignments)
        

        
        # Action Buttons (Clean text, no emojis)
        h_btn_lay = QHBoxLayout()
        h_btn_lay.setSpacing(8)
        
        btn_ata = QPushButton("Ders Ata")
        btn_ata.setStyleSheet("background: #0078D7; color: white; font-weight: bold; min-height: 32px; border-radius: 4px;")
        btn_ata.clicked.connect(self._assign_lessons_for_this_teacher)
        
        btn_cizelge = QPushButton("Çizelge / Yazdır")
        btn_cizelge.setStyleSheet("background: #27AE60; color: white; font-weight: bold; min-height: 32px; border-radius: 4px;")
        btn_cizelge.clicked.connect(self._show_teacher_timetable)
        
        btn_zaman = QPushButton("Zaman / Kısıtlama")
        btn_zaman.setStyleSheet("background: #E67E22; color: white; font-weight: bold; min-height: 32px; border-radius: 4px;")
        btn_zaman.clicked.connect(self._open_constraints)
        
        btn_oto = QPushButton("Otomatik Oluştur")
        btn_oto.setStyleSheet("background: #8E44AD; color: white; font-weight: bold; min-height: 32px; border-radius: 4px;")
        btn_oto.clicked.connect(self._auto_plan_teacher)
        
        h_btn_lay.addWidget(btn_ata)
        h_btn_lay.addWidget(btn_cizelge)
        h_btn_lay.addWidget(btn_zaman)
        h_btn_lay.addWidget(btn_oto)
        lay_ders.addLayout(h_btn_lay)
        
        self.main_layout.addWidget(frame_ders)
        
        # 4. Renk Frame
        frame_renk = QFrame()
        frame_renk.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 6px; }")
        lay_renk = QHBoxLayout(frame_renk)
        lay_renk.setContentsMargins(15, 10, 15, 10)
        lay_renk.addWidget(QLabel("<b>Renk Kodu:</b>"))
        self.color_box = QLabel()
        self.color_box.setFixedSize(120, 30)
        self.color_box.setStyleSheet(f"background: {self._color}; border: 1px solid #CCC; border-radius: 4px;")
        btn_degistir = QPushButton("Değiştir")
        btn_degistir.setFixedSize(80, 28)
        btn_degistir.clicked.connect(self._pick_color)
        lay_renk.addWidget(self.color_box)
        lay_renk.addWidget(btn_degistir)
        lay_renk.addStretch(1)
        self.main_layout.addWidget(frame_renk)
        
        self._add_bottom_buttons()

    def _open_constraints(self):
        t_name = self.w_ad.text().strip()
        if not t_name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Uyarı", "Lütfen önce öğretmenin adını girin.")
            return
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        from dialogs.constraints_dialog import ConstraintsDialog
        d = ConstraintsDialog(data_store=data_store, target_type="ogretmen", parent=self)
        idx = d.combo_target.findText(t_name)
        if idx >= 0:
            d.combo_target.setCurrentIndex(idx)
        d.exec()

    def _auto_plan_teacher(self):
        from dialogs.auto_schedule_dialog import AutoScheduleDialog
        from PySide6.QtWidgets import QMessageBox
        p = self.parent()
        if not p: return
        data_store = getattr(p, "data_store", {})
        d = AutoScheduleDialog(data_store, p)
        if d.exec():
            results = data_store.get("auto_schedule_results", [])
            if results:
                grid_placements = data_store.get("grid_placements", [])
                manuals = [g for g in grid_placements if g.get("is_manual", False) or g.get("locked", False)]
                new_placements = list(manuals)
                
                from main_window import get_subject_color
                for r in results:
                    if r.get("is_manual", False):
                        continue
                    new_placements.append({
                        "period": r["period"],
                        "day": r["day_idx"],
                        "subject_name": r["subject_name"],
                        "color": get_subject_color(r["subject_name"]),
                        "teacher_name": r["teacher_name"],
                        "duration": r.get("duration", 1),
                        "class_name": r["class_name"]
                    })
                    
                data_store["grid_placements"] = new_placements
                if hasattr(p, "save_db"): p.save_db()
                if hasattr(p, "_refresh_tree"): p._refresh_tree()
                if hasattr(p, "_restore_grid_placements"): p._restore_grid_placements()
                QMessageBox.information(self, "Başarılı", "Otomatik planlama tamamlandı!")

    def _assign_lessons_for_this_teacher(self):
        t_name = self.w_ad.text().strip()
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        d = LessonAssignmentDialog(data_store=data_store, parent=p or self, selected_teacher=t_name)
        if d.exec():
            data = d.get_data()
            if "atamalar" not in data_store:
                data_store["atamalar"] = []
            
            # Remove old assignments for this teacher
            current_teacher = format_tr_name(d.cb_ogretmen.currentText())
            data_store["atamalar"] = [
                a for a in data_store["atamalar"] 
                if format_tr_name(a.get("teacher", "")) != current_teacher
            ]
            
            # Add new ones
            if isinstance(data, list):
                data_store["atamalar"].extend(data)
            else:
                data_store["atamalar"].append(data)
                
            trigger_save_db(self, data_store)
            if hasattr(p, "save_db"): p.save_db()
            if hasattr(p, "_refresh_tree"): p._refresh_tree()
            if hasattr(p, "_refresh_unplaced_lessons"): p._refresh_unplaced_lessons()
            if hasattr(p, "_restore_grid_placements"): p._restore_grid_placements()
            if hasattr(p, "_refresh_grid"): p._refresh_grid()
            
            # Update local UI list
            self.list_assignments.clear()
            my_atamalar = [a for a in data_store["atamalar"] if format_tr_name(a.get("teacher", "")) == current_teacher]
            for a in my_atamalar:
                item_text = f"📚 {a.get('subject', '')} ➔ 🎓 {a.get('class', '')} ({a.get('duration', 0)} Saat)"
                self.list_assignments.addItem(QListWidgetItem(item_text))
            if not my_atamalar:
                self.list_assignments.addItem(QListWidgetItem("❌ Henüz hiçbir derse veya sınıfa atanmadı."))

    def _open_custom_fields(self):
        t_name = self.w_ad.text().strip() or "Öğretmen"
        dlg = CustomFieldsDialog(t_name, "Öğretmen", self.existing_data.get("ozel_alanlar", {}), self)
        if dlg.exec() == QDialog.Accepted:
            self.existing_data["ozel_alanlar"] = dlg.get_data()

    def _show_teacher_timetable(self):
        t_name = format_tr_name(self.w_ad.text().strip())
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        from dialogs.print_preview import TimetablePrintPreview
        filters = {
            "entity_type": "teacher",
            "teachers": [t_name],
            "default_selection": t_name,
            "lock_mode": "Öğretmen Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)"
        }
        dlg = TimetablePrintPreview(data_store=data_store, filters=filters, parent=self)
        dlg.exec()

    def _auto_short_code_teacher(self, text):
        if text:
            clean = text.strip()
            parts = clean.split()
            if len(parts) >= 2:
                sc = f"{parts[0][0].upper()}. {' '.join(parts[1:]).upper()}"
            elif len(parts) == 1 and len(parts[0]) > 0:
                sc = f"{parts[0][0].upper()}. {parts[0].upper()}"
            else:
                sc = clean.upper()
            self.w_kisa.setText(sc)

    def _pick_color(self):
        from dialogs.color_picker_dialog import ModernColorPickerDialog
        t_name = self.w_ad.text().strip() or "Öğretmen"
        c = ModernColorPickerDialog.pick_color(
            initial_color=self._color,
            parent=self,
            title=f"🎨 {t_name} — Renk Seçimi"
        )
        if c and c.isValid():
            self._color = c.name()
            self.color_box.setStyleSheet(f"background: {self._color}; border: 1px solid #CCC; border-radius: 4px;")

    def get_data(self):
        raw_ad = self.w_ad.text().strip()
        ad_formatted = format_tr_name(raw_ad)
        brans_val = ""
        if hasattr(self, "w_brans"):
            if isinstance(self.w_brans, QComboBox):
                brans_val = self.w_brans.currentText().strip()
            else:
                brans_val = self.w_brans.text().strip()
        return {
            "ad": ad_formatted, "kisa": self.w_kisa.text().strip(),
            "renk": self._color, "sinif_ogretmeni": self.w_so.currentText().strip(),
            "brans": brans_val,
            "ozel_alanlar": self.existing_data.get("ozel_alanlar", {})
        }


class DerslikEditDialog(BaseEditForm):
    def __init__(self, parent=None, existing_data=None):
        super().__init__("Derslik", parent, existing_data)
        self._color = self.existing_data.get("renk", "#F39C12")
        self._build_ui()
        
    def _build_ui(self):
        form = QFormLayout()
        form.setSpacing(12)
        
        self.w_ad = QLineEdit(self.existing_data.get("ad", ""))
        self.w_kisa = QLineEdit(self.existing_data.get("kisa", ""))
        self.w_ad.textChanged.connect(lambda t: self.w_kisa.setText(t.strip().upper()))
        form.addRow("Derslik Adı", self.w_ad)
        form.addRow("Kısa Kodu", self.w_kisa)
        self.main_layout.addLayout(form)
        
        btn_ozel = QPushButton("Özel Alanlar...")
        btn_ozel.setFixedWidth(200)
        btn_ozel.setStyleSheet("background: #F1F5F9; color: #1E293B; font-weight: 500;")
        btn_ozel.clicked.connect(self._open_custom_fields)
        btn_ozel_lay = QHBoxLayout()
        btn_ozel_lay.addStretch(1); btn_ozel_lay.addWidget(btn_ozel); btn_ozel_lay.addStretch(1)
        self.main_layout.addLayout(btn_ozel_lay)
        
        lbl_renk = QLabel("Renk Kodu")
        self.main_layout.addWidget(lbl_renk)
        
        renk_frame = QFrame()
        renk_frame.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
        r_lay = QHBoxLayout(renk_frame)
        self.color_box = QLabel()
        self.color_box.setFixedSize(180, 50)
        self.color_box.setStyleSheet(f"background: {self._color};")
        btn_degistir = QPushButton("Değiştir")
        btn_degistir.setFixedSize(80, 28)
        btn_degistir.clicked.connect(self._pick_color)
        r_lay.addWidget(self.color_box)
        r_lay.addStretch(1)
        r_lay.addWidget(btn_degistir)
        r_lay.addStretch(1)
        self.main_layout.addWidget(renk_frame)
        
        d_frame = QFrame()
        d_frame.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
        d_lay = QHBoxLayout(d_frame)
        d_lay.addWidget(QLabel("Derslik Kapasitesi:"))
        self.w_cap = QLineEdit(self.existing_data.get("kapasite", ""))
        d_lay.addWidget(self.w_cap)
        self.main_layout.addWidget(d_frame)
        
        self._add_bottom_buttons()

    def _open_custom_fields(self):
        d_name = self.w_ad.text().strip() or "Derslik"
        dlg = CustomFieldsDialog(d_name, "Derslik", self.existing_data.get("ozel_alanlar", {}), self)
        if dlg.exec() == QDialog.Accepted:
            self.existing_data["ozel_alanlar"] = dlg.get_data()

    def _pick_color(self):
        from dialogs.color_picker_dialog import ModernColorPickerDialog
        d_name = self.w_ad.text().strip() or "Derslik"
        c = ModernColorPickerDialog.pick_color(
            initial_color=self._color,
            parent=self,
            title=f"🎨 {d_name} — Renk Seçimi"
        )
        if c and c.isValid():
            self._color = c.name()
            self.color_box.setStyleSheet(f"background: {self._color}; border: 1px solid #CCC; border-radius: 4px;")

    def get_data(self):
        return {
            "ad": self.w_ad.text().strip(),
            "kisa": self.w_kisa.text().strip(),
            "renk": self._color,
            "kapasite": self.w_cap.text().strip(),
            "ozel_alanlar": self.existing_data.get("ozel_alanlar", {})
        }


class FastComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        
    def wheelEvent(self, event):
        # Ignore wheel event on combobox to let the parent table scroll smoothly at 60 FPS
        event.ignore()


class ClassComprehensiveAssignmentDialog(QDialog):
    """
    Sınıfa Bütünsel Ders ve Öğretmen Atama Paneli (Modern, Hızlı ve İkili Saat Girişli Tasarım)
    """
    def __init__(self, class_name="", data_store=None, parent=None):
        super().__init__(parent)
        self.class_name = class_name
        self.data_store = data_store or {}
        self.setWindowTitle(f"🎓 {self.class_name} Sınıfı — Ders ve Öğretmen Atama Paneli")
        self.setFixedSize(1040, 700)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; }
            QLabel { color: #334155; font-size: 13px; font-weight: bold; }
            QTableWidget { border: 1px solid #CBD5E1; background: #FFFFFF; gridline-color: #F1F5F9; font-size: 13px; border-radius: 8px; }
            QHeaderView::section { background-color: #F1F5F9; border: none; border-bottom: 2px solid #CBD5E1; padding: 8px; font-weight: bold; font-size: 12px; color: #334155; }
            QPushButton { border: 1px solid #CBD5E1; border-radius: 6px; background: #FFFFFF; font-size: 13px; font-weight: bold; color: #475569; }
            QPushButton:hover { background: #F8FAFC; }
            QLineEdit { border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px 12px; font-size: 13px; background: white; }
            QLineEdit:focus { border: 1px solid #2563EB; }
            QTableWidget QComboBox {
                background: #F0F9FF; color: #0284C7; border: 1px solid #BAE6FD;
                border-radius: 4px; padding: 2px 6px; font-weight: bold; font-size: 11px;
                min-height: 22px; max-height: 24px;
            }
            QTableWidget QComboBox:hover { border-color: #0284C7; background: #E0F2FE; }
            QTableWidget QComboBox QLineEdit { color: #0284C7; font-weight: bold; }
        """)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)
        
        # Header Banner Card
        top_frame = QFrame()
        top_frame.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; }")
        top_lay = QHBoxLayout(top_frame)
        top_lay.setContentsMargins(14, 10, 14, 10)
        
        v_title = QVBoxLayout()
        lbl_title = QLabel(f"🎓 {self.class_name} Sınıfı — Ders ve Öğretmen Atama Paneli")
        lbl_title.setStyleSheet("font-size: 17px; color: #2563EB; font-weight: bold;")
        v_title.addWidget(lbl_title)
        
        lbl_sub = QLabel("Bu sınıfa ait tüm derslerin öğretmen görevlendirmelerini, haftalık ders saatlerini ve dağılım tiplerini yönetin.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #64748B; font-weight: normal;")
        v_title.addWidget(lbl_sub)
        top_lay.addLayout(v_title)
        top_lay.addStretch(1)
        
        btn_print = QPushButton("🖨️ Bu Sınıfın Çizelgesini ve Öğretmenlerini Yazdır")
        btn_print.setStyleSheet("background: #F0FDF4; color: #16A34A; border: 1px solid #BBF7D0; font-size: 13px; padding: 8px 16px;")
        btn_print.clicked.connect(self._print_class_timetable)
        top_lay.addWidget(btn_print)
        lay.addWidget(top_frame)
        
        # Minimalist Search Bar
        search_lay = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Ders veya Öğretmen Ara (Gerçek Zamanlı)...")
        self.txt_search.textChanged.connect(self._filter_table)
        search_lay.addWidget(self.txt_search)
        lay.addLayout(search_lay)
        
        # Table with Dual Hour Columns (Target Class Hours & Combined Hours)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Ders Adı", "Atanan Öğretmen(ler)", f"{self.class_name} Saati", "🔗 Birleşik Ders Saati", "İşlemler"
        ])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 160)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.setColumnWidth(2, 130)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.setColumnWidth(3, 155)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 140)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget::item { padding: 3px; }")
        lay.addWidget(self.table, 1)

        # Bottom Actions Bar
        bot_lay = QHBoxLayout()
        self.lbl_summary = QLabel("Toplam Atanan: 0 / 40 Saat (%0 Doluluk)")
        self.lbl_summary.setStyleSheet("color: #0284C7; font-size: 14px; font-weight: bold;")
        bot_lay.addWidget(self.lbl_summary)
        
        bot_lay.addStretch(1)
        
        btn_clear_all = QPushButton("Hepsini Kaldır")
        btn_clear_all.setStyleSheet("background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; font-weight: bold;")
        btn_clear_all.clicked.connect(self._clear_all_assignments)
        bot_lay.addWidget(btn_clear_all)

        btn_close = QPushButton("Kapat ve Kaydet")
        btn_close.setStyleSheet("background: #2563EB; color: white; border: none; font-weight: bold;")
        btn_close.clicked.connect(self.accept)
        bot_lay.addWidget(btn_close)
        
        lay.addLayout(bot_lay)

    def _filter_table(self, text):
        search_term = format_tr_name(text).lower()
        for i in range(self.table.rowCount()):
            subj_item = self.table.item(i, 0)
            teacher_item = self.table.item(i, 1)
            if subj_item and teacher_item:
                subj_text = format_tr_name(subj_item.text()).lower()
                teacher_text = format_tr_name(teacher_item.text()).lower()
                if search_term in subj_text or search_term in teacher_text:
                    self.table.setRowHidden(i, False)
                else:
                    self.table.setRowHidden(i, True)

    def _clear_all_assignments(self):
        reply = QMessageBox.question(
            self,
            "Hepsini Kaldır Onayı",
            f"<b>{self.class_name}</b> sınıfına atanmış olan <b>TÜM ders ve öğretmen görevlendirmelerini</b> silmek istediğinize emin misiniz?\n\nBu işlem geri alınamaz.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            target_cls = self.class_name
            atamalar = self.data_store.get("atamalar", [])
            self.data_store["atamalar"] = [a for a in atamalar if not matches_class(a.get("class", ""), target_cls)]
            grid_data = self.data_store.get("grid_placements", [])
            if isinstance(grid_data, list):
                self.data_store["grid_placements"] = [p for p in grid_data if not matches_class(p.get("class_name", p.get("class", "")), target_cls)]
            yerlesim = self.data_store.get("yerlesim", {})
            if isinstance(yerlesim, dict):
                for k in list(yerlesim.keys()):
                    info = yerlesim[k]
                    if isinstance(info, dict) and matches_class(info.get("class_name", info.get("class", "")), target_cls):
                        yerlesim.pop(k, None)
            trigger_save_db(self, self.data_store)
            
            # Live sync with main window
            win = self.window()
            if not win or not hasattr(win, "_grid"):
                p = self.parent()
                while p:
                    if hasattr(p, "_grid"):
                        win = p
                        break
                    p = p.parent()
            if win:
                if hasattr(win, "save_db"): win.save_db(sync_from_grid=False)
                if hasattr(win, "_refresh_tree"): win._refresh_tree()
                if hasattr(win, "_load_unplaced_lessons"): win._load_unplaced_lessons()
                if hasattr(win, "_on_tree_selection_changed"): win._on_tree_selection_changed()

            self._load_data()
            QMessageBox.information(self, "Başarılı", f"{self.class_name} sınıfının tüm ders atamaları başarıyla temizlendi.")

    def _load_data(self):
        self._is_loading = True
        self.table.setRowCount(0)
        subjects = [d.get("ad", "") for d in self.data_store.get("dersler", []) if d.get("ad")]
        atamalar = self.data_store.get("atamalar", [])
        
        class_atamalar = {}
        for a in atamalar:
            c_str = a.get("class", "")
            is_match = False
            if matches_class(c_str, self.class_name):
                is_match = True
            elif a.get("is_combined") and a.get("combined_classes"):
                if any(matches_class(cc, self.class_name) for cc in a.get("combined_classes")):
                    is_match = True
            elif "+" in c_str or "," in c_str or "&" in c_str:
                parts = [p.strip() for p in c_str.replace("&", "+").replace(",", "+").split("+") if p.strip()]
                if any(matches_class(p, self.class_name) for p in parts):
                    is_match = True
                    
            if is_match:
                s = a.get("subject", "")
                if s:
                    class_atamalar.setdefault(s, []).append(a)

        for subj in sorted(subjects):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # 0. Subject Name with color pill indicator
            scolor = get_subject_color(subj)
            item_subj = QTableWidgetItem(f"  ●  {subj}")
            item_subj.setForeground(QBrush(QColor(scolor)))
            item_subj.setFlags(item_subj.flags() ^ Qt.ItemIsEditable)
            item_subj.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(row, 0, item_subj)
            
            # 1. Teachers
            assigned_list = class_atamalar.get(subj, [])
            teachers = [a.get("teacher", "") for a in assigned_list if a.get("teacher")]
            
            sep_list = [a for a in assigned_list if not a.get("is_combined") and "+" not in str(a.get("class", "")) and "," not in str(a.get("class", ""))]
            comb_list = [a for a in assigned_list if a.get("is_combined") or "+" in str(a.get("class", "")) or "," in str(a.get("class", ""))]
            
            comb_classes_info = []
            for a in comb_list:
                if a.get("combined_classes"):
                    for c in a["combined_classes"]:
                        if str(c).strip() and str(c).strip() not in comb_classes_info:
                            comb_classes_info.append(str(c).strip())
                elif "+" in str(a.get("class", "")):
                    for c in str(a.get("class", "")).replace("&", "+").replace(",", "+").split("+"):
                        if c.strip() and c.strip() not in comb_classes_info:
                            comb_classes_info.append(c.strip())
                            
            # 1. Sütun 1: Atanan Öğretmen(ler) (Rich Widget)
            w_teachers = QWidget()
            lt = QHBoxLayout(w_teachers)
            lt.setContentsMargins(6, 2, 6, 2)
            lt.setSpacing(8)
            lt.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            
            if not teachers:
                lbl_t = QLabel("Atama Yok")
                lbl_t.setStyleSheet("color: #94A3B8; font-style: italic; font-size: 13px;")
                lt.addWidget(lbl_t)
            else:
                base_t = ", ".join(dict.fromkeys(teachers))
                lbl_t = QLabel(base_t)
                lbl_t.setStyleSheet("font-weight: bold; font-size: 13px; color: #1E293B;")
                lt.addWidget(lbl_t)
                
                if comb_list:
                    comb_str = " + ".join(comb_classes_info)
                    lbl_badge = QLabel(f"Birleşik: {comb_str}")
                    # Use subject color for the badge
                    c_obj = QColor(scolor)
                    bg_rgba = f"rgba({c_obj.red()}, {c_obj.green()}, {c_obj.blue()}, 0.15)"
                    border_rgba = f"rgba({c_obj.red()}, {c_obj.green()}, {c_obj.blue()}, 0.4)"
                    lbl_badge.setStyleSheet(f"""
                        background-color: {bg_rgba};
                        color: {scolor};
                        font-weight: bold;
                        font-size: 12px;
                        padding: 3px 8px;
                        border-radius: 6px;
                        border: 1px solid {border_rgba};
                    """)
                    lt.addWidget(lbl_badge)
                    
            self.table.setCellWidget(row, 1, w_teachers)
            
            # Placeholder text item to maintain row integrity and sorting if needed
            it_placeholder = QTableWidgetItem()
            it_placeholder.setFlags(it_placeholder.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 1, it_placeholder)
            
            is_cur_class_in_comb = any(
                matches_class(a.get("class", ""), self.class_name) or
                (a.get("is_combined") and any(matches_class(cc, self.class_name) for cc in a.get("combined_classes", []))) or
                ("+" in str(a.get("class", "")) and any(matches_class(part, self.class_name) for part in str(a.get("class", "")).replace("&", "+").replace(",", "+").split("+") if part.strip()))
                for a in comb_list
            )
            
            def _calc_hours_subtext(typ_str):
                typ_str = str(typ_str or "").strip()
                if not typ_str or typ_str in ("0", "—", "None"):
                    return ""
                if "+" in typ_str:
                    parts = [int(p.strip()) for p in typ_str.split("+") if p.strip().isdigit()]
                    tot = sum(parts)
                    return f"({tot} Saat)" if tot > 0 else ""
                elif typ_str.isdigit() and int(typ_str) > 0:
                    return f"({typ_str} Saat)"
                return ""

            def _make_hour_cell(cb, subtext, is_active=True):
                w = QWidget()
                lay = QVBoxLayout(w)
                lay.setContentsMargins(4, 2, 4, 2)
                lay.setSpacing(2)
                lay.setAlignment(Qt.AlignCenter)
                lay.addWidget(cb)
                
                lbl = QLabel(subtext if subtext else "")
                lbl.setAlignment(Qt.AlignCenter)
                if is_active:
                    lbl.setStyleSheet("color: #2563EB; font-weight: bold; font-size: 11px;")
                    # Dynamically update the label instantly when typing or selecting!
                    def _update_lbl(txt):
                        lbl.setText(_calc_hours_subtext(txt))
                    if isinstance(cb, QComboBox):
                        cb.currentTextChanged.connect(_update_lbl)
                else:
                    lbl.setStyleSheet("color: #94A3B8; font-style: italic; font-size: 10.5px;")
                
                lay.addWidget(lbl)
                return w

            # 2. Sütun 2: {self.class_name} Saati (Separate Hour)
            if is_cur_class_in_comb:
                # If this class is combined, separate hour is DISABLED and GREY!
                cb_sep = FastComboBox()
                cb_sep.setEnabled(False)
                cb_sep.setEditable(False)
                cb_sep.setStyleSheet("background: #F1F5F9; color: #94A3B8; border: 1px solid #E2E8F0; font-weight: normal;")
                cb_sep.addItem("— (Birleşik)")
                cb_sep.setCurrentText("— (Birleşik)")
                w_cell2 = _make_hour_cell(cb_sep, "(Devre Dışı)", is_active=False)
                self.table.setCellWidget(row, 2, w_cell2)
            elif sep_list or teachers:
                # If this class is separate, separate hour is ACTIVE!
                cb_sep = FastComboBox()
                cb_sep.setEditable(True)
                cb_sep.setEnabled(True)
                cb_sep.setStyleSheet("background: #FFFFFF; color: #1E293B; font-weight: bold; border: 1px solid #CBD5E1;")
                cb_sep.addItems(["", "1", "2", "3", "4", "5", "6", "7", "8", "1+1", "2+1", "2+2", "3+1", "3+2", "2+2+1", "2+2+2", "2+2+3", "2+2+2+1"])
                cur_sep_type = str(sep_list[0].get("type", "")).strip() if sep_list else ""
                if cur_sep_type in ("0", "None"): cur_sep_type = ""
                cb_sep.setCurrentText(cur_sep_type if cur_sep_type else (str(sep_list[0].get("duration", "")) if sep_list and int(sep_list[0].get("duration", 0)) > 0 else ""))
                if cb_sep.lineEdit():
                    cb_sep.lineEdit().setPlaceholderText("Saat Girin")
                    cb_sep.lineEdit().setAlignment(Qt.AlignCenter)
                    cb_sep.lineEdit().editingFinished.connect(lambda s=subj, cb=cb_sep: self._on_inline_sep_hour_committed(s, cb.currentText()))
                cb_sep.activated.connect(lambda idx, s=subj, cb=cb_sep: self._on_inline_sep_hour_committed(s, cb.currentText()))
                sub_txt = _calc_hours_subtext(cb_sep.currentText())
                w_cell2 = _make_hour_cell(cb_sep, sub_txt, is_active=True)
                self.table.setCellWidget(row, 2, w_cell2)
            else:
                self.table.removeCellWidget(row, 2)
                item_sep = QTableWidgetItem("—")
                item_sep.setTextAlignment(Qt.AlignCenter)
                item_sep.setFlags(item_sep.flags() ^ Qt.ItemIsEditable)
                item_sep.setForeground(QBrush(QColor("#CBD5E1")))
                self.table.setItem(row, 2, item_sep)
                
            # 3. Sütun 3: 🔗 Birleşik Ders Saati (Combined Hour)
            if is_cur_class_in_comb:
                # If this class is combined, combined hour is ACTIVE and EDITABLE!
                cb_comb = FastComboBox()
                cb_comb.setEditable(True)
                cb_comb.setEnabled(True)
                cb_comb.setStyleSheet("background: #FFFFFF; color: #0284C7; font-weight: bold; border: 1px solid #BAE6FD;")
                cb_comb.addItems(["", "1", "2", "3", "4", "5", "6", "7", "8", "1+1", "2+1", "2+2", "3+1", "3+2", "2+2+1", "2+2+2", "2+2+3", "2+2+2+1"])
                cur_comb_type = str(comb_list[0].get("type", "")).strip() if comb_list else ""
                if cur_comb_type in ("0", "None"): cur_comb_type = ""
                cb_comb.setCurrentText(cur_comb_type if cur_comb_type else (str(comb_list[0].get("duration", "")) if comb_list and int(comb_list[0].get("duration", 0)) > 0 else ""))
                if cb_comb.lineEdit():
                    cb_comb.lineEdit().setPlaceholderText("Birleşik Saat")
                    cb_comb.lineEdit().setAlignment(Qt.AlignCenter)
                    cb_comb.lineEdit().editingFinished.connect(lambda s=subj, cb=cb_comb: self._on_inline_comb_hour_committed(s, cb.currentText()))
                cb_comb.activated.connect(lambda idx, s=subj, cb=cb_comb: self._on_inline_comb_hour_committed(s, cb.currentText()))
                sub_txt = _calc_hours_subtext(cb_comb.currentText())
                w_cell3 = _make_hour_cell(cb_comb, sub_txt, is_active=True)
                self.table.setCellWidget(row, 3, w_cell3)
            elif comb_list or teachers:
                # If this class is NOT in the combination, combined hour is DISABLED and GREY!
                cb_comb = FastComboBox()
                cb_comb.setEnabled(False)
                cb_comb.setEditable(False)
                cb_comb.setStyleSheet("background: #F1F5F9; color: #94A3B8; border: 1px solid #E2E8F0; font-weight: normal;")
                cur_comb_type = str(comb_list[0].get("type", "")).strip() if comb_list else ""
                comb_hint = cur_comb_type if cur_comb_type else "—"
                cb_comb.addItem(comb_hint)
                cb_comb.setCurrentText(comb_hint)
                w_cell3 = _make_hour_cell(cb_comb, "(Devre Dışı)", is_active=False)
                self.table.setCellWidget(row, 3, w_cell3)
            else:
                self.table.removeCellWidget(row, 3)
                item_comb = QTableWidgetItem("—")
                item_comb.setTextAlignment(Qt.AlignCenter)
                item_comb.setFlags(item_comb.flags() ^ Qt.ItemIsEditable)
                item_comb.setForeground(QBrush(QColor("#CBD5E1")))
                self.table.setItem(row, 3, item_comb)
            
            # 4. Action Buttons (Always fully visible, centered, and clean)
            cell_w = QWidget()
            cell_lay = QHBoxLayout(cell_w)
            cell_lay.setContentsMargins(4, 2, 4, 2)
            cell_lay.setSpacing(4)
            cell_lay.setAlignment(Qt.AlignCenter)
            
            if assigned_list:
                btn_edit = QPushButton("Düzenle")
                btn_edit.setAutoDefault(False)
                btn_edit.setFixedSize(68, 24)
                btn_edit.setStyleSheet("background: #EFF6FF; color: #1D4ED8; border: 1px solid #93C5FD; border-radius: 4px; font-size: 10px; font-weight: bold; min-height: 0; max-height: 24px; padding: 0 4px;")
                btn_edit.clicked.connect(lambda chk=False, s=subj: self._edit_subject_assignment(s))
                cell_lay.addWidget(btn_edit)
                
                btn_remove = QPushButton("Kaldır")
                btn_remove.setAutoDefault(False)
                btn_remove.setToolTip("Bu dersin atamasını kaldır")
                btn_remove.setFixedSize(52, 24)
                btn_remove.setStyleSheet("background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; border-radius: 4px; font-size: 10px; font-weight: bold; min-height: 0; max-height: 24px; padding: 0 4px;")
                btn_remove.clicked.connect(lambda chk=False, s=subj: self._remove_subject_assignment(s))
                cell_lay.addWidget(btn_remove)
            else:
                btn_add = QPushButton("+ Ata")
                btn_add.setAutoDefault(False)
                btn_add.setFixedSize(52, 24)
                btn_add.setStyleSheet("background: #F8FAFC; color: #2563EB; border: 1px solid #CBD5E1; border-radius: 4px; font-size: 10px; font-weight: bold; min-height: 0; max-height: 24px; padding: 0 6px;")
                btn_add.clicked.connect(lambda chk=False, s=subj: self._edit_subject_assignment(s))
                cell_lay.addWidget(btn_add)
                
                btn_remove = QPushButton("Kaldır")
                btn_remove.setAutoDefault(False)
                btn_remove.setToolTip("Bu dersin atamasını kaldır")
                btn_remove.setFixedSize(52, 24)
                btn_remove.setStyleSheet("background: #F1F5F9; color: #94A3B8; border: 1px solid #E2E8F0; border-radius: 4px; font-size: 10px; font-weight: bold; min-height: 0; max-height: 24px; padding: 0 4px;")
                btn_remove.setEnabled(False)
                cell_lay.addWidget(btn_remove)
                
            self.table.setCellWidget(row, 4, cell_w)

        self._is_loading = False
        self._update_summary_label()

    def _update_summary_label(self):
        # Calculate clean, deduplicated total hours for this class
        cur_class_atamalar = []
        seen_keys = set()
        for a in self.data_store.get("atamalar", []):
            c_str = a.get("class", "")
            is_match = False
            if matches_class(c_str, self.class_name):
                is_match = True
            elif a.get("is_combined") and a.get("combined_classes"):
                if any(matches_class(cc, self.class_name) for cc in a.get("combined_classes")):
                    is_match = True
            elif "+" in c_str or "," in c_str or "&" in c_str:
                parts = [p.strip() for p in c_str.replace("&", "+").replace(",", "+").split("+") if p.strip()]
                if any(matches_class(p, self.class_name) for p in parts):
                    is_match = True
                    
            if is_match:
                s = format_tr_name(a.get("subject", ""))
                t = format_tr_name(a.get("teacher", ""))
                c = format_tr_name(a.get("class", ""))
                k = (s, t, c)
                if k not in seen_keys:
                    seen_keys.add(k)
                    cur_class_atamalar.append(a)
                    
        tot_hrs = sum(int(a.get("duration", 0)) for a in cur_class_atamalar)
        
        settings = self.data_store.get("settings", {})
        periods = int(settings.get("periods", self.data_store.get("ders_saati", 8)))
        days_count = int(settings.get("days_count", settings.get("day_count", self.data_store.get("gun_sayisi", 5))))
        max_weekly_hours = periods * days_count
        if max_weekly_hours <= 0: max_weekly_hours = 40
        
        pct = min(100, int((tot_hrs / float(max_weekly_hours)) * 100))
        color_hex = "#16A34A" if tot_hrs >= max_weekly_hours else ("#2563EB" if tot_hrs >= (max_weekly_hours // 2) else "#D97706")
        self.lbl_summary.setText(f"Toplam Atanan: {tot_hrs} / {max_weekly_hours} Saat (%{pct} Haftalık Doluluk)")
        self.lbl_summary.setStyleSheet(f"color: {color_hex}; font-size: 14px; font-weight: bold;")

    def _on_inline_sep_hour_committed(self, subject_name, new_type_str):
        if getattr(self, "_is_loading", False):
            return
        raw_type = str(new_type_str).strip()
        parts = [int(p.strip()) for p in raw_type.split("+") if p.strip().isdigit()]
        dur = sum(parts) if parts else (int(raw_type) if raw_type.isdigit() else 0)
        canonical_type = "+".join(str(p) for p in parts) if len(parts) > 1 else str(dur)
        if dur <= 0:
            canonical_type = ""
            dur = 0
            
        subj_target = format_tr_name(subject_name)
        cur_c = format_tr_name(self.class_name)
        
        found = False
        for a in self.data_store.get("atamalar", []):
            if format_tr_name(a.get("subject", "")) == subj_target:
                if not a.get("is_combined") and "+" not in str(a.get("class", "")) and format_tr_name(a.get("class", "")) == cur_c:
                    a["type"] = canonical_type
                    a["duration"] = dur
                    found = True
                    
        # If no separate entry existed yet, create one using assigned teacher
        if not found and dur > 0:
            existing_teacher = ""
            for a in self.data_store.get("atamalar", []):
                if format_tr_name(a.get("subject", "")) == subj_target and a.get("teacher"):
                    existing_teacher = a.get("teacher").split(",")[0].strip()
                    break
            if not existing_teacher and self.data_store.get("ogretmenler"):
                existing_teacher = self.data_store["ogretmenler"][0].get("ad", "")
                
            self.data_store.setdefault("atamalar", []).append({
                "teacher": existing_teacher,
                "subject": subject_name,
                "class": self.class_name,
                "duration": dur,
                "type": canonical_type,
                "color": get_subject_color(subject_name),
                "is_combined": False,
                "combined_classes": []
            })
            
        from version_store import sanitize_atamalar
        self.data_store["atamalar"] = sanitize_atamalar(self.data_store.get("atamalar", []))
        trigger_save_db(self, self.data_store)
        self._update_summary_label()

    def _on_inline_comb_hour_committed(self, subject_name, new_type_str):
        if getattr(self, "_is_loading", False):
            return
        raw_type = str(new_type_str).strip()
        parts = [int(p.strip()) for p in raw_type.split("+") if p.strip().isdigit()]
        dur = sum(parts) if parts else (int(raw_type) if raw_type.isdigit() else 0)
        canonical_type = "+".join(str(p) for p in parts) if len(parts) > 1 else str(dur)
        if dur <= 0:
            canonical_type = ""
            dur = 0
            
        subj_target = format_tr_name(subject_name)
        cur_c = format_tr_name(self.class_name)
        
        found = False
        # 1. Update any existing combined assignment that contains this class
        for a in self.data_store.get("atamalar", []):
            if format_tr_name(a.get("subject", "")) == subj_target:
                if (a.get("is_combined") and any(matches_class(c, self.class_name) for c in a.get("combined_classes", []))) or (not a.get("is_combined") and "+" in str(a.get("class", "")) and matches_class(a.get("class", ""), self.class_name)):
                    a["type"] = canonical_type
                    a["duration"] = dur
                    a["is_combined"] = True
                    found = True
                    
        # 2. If not found, check if a combined assignment exists for this subject with OTHER classes (e.g. 11A + 11C) and attach this class
        if not found and dur > 0:
            for a in self.data_store.get("atamalar", []):
                if format_tr_name(a.get("subject", "")) == subj_target and (a.get("is_combined") or "+" in str(a.get("class", ""))):
                    comb_list = list(a.get("combined_classes", []))
                    if not comb_list and "+" in str(a.get("class", "")):
                        comb_list = [c.strip() for c in str(a.get("class", "")).replace("&", "+").replace(",", "+").split("+") if c.strip()]
                    if not any(matches_class(c, self.class_name) for c in comb_list):
                        comb_list.append(self.class_name)
                    a["combined_classes"] = comb_list
                    a["class"] = " + ".join(comb_list)
                    a["type"] = canonical_type
                    a["duration"] = dur
                    a["is_combined"] = True
                    found = True
                    # Remove old separate entry for this class
                    self.data_store["atamalar"] = [asgn for asgn in self.data_store["atamalar"] if not (format_tr_name(asgn.get("subject", "")) == subj_target and not asgn.get("is_combined") and "+" not in str(asgn.get("class", "")) and matches_class(asgn.get("class", ""), self.class_name))]
                    break
                    
        # 3. If still not found and dur > 0: convert current separate assignment or create combined assignment
        if not found and dur > 0:
            existing_teacher = ""
            for a in self.data_store.get("atamalar", []):
                if format_tr_name(a.get("subject", "")) == subj_target and a.get("teacher"):
                    existing_teacher = a.get("teacher").split(",")[0].strip()
                    break
            if not existing_teacher and self.data_store.get("ogretmenler"):
                existing_teacher = self.data_store["ogretmenler"][0].get("ad", "")
                
            self.data_store.setdefault("atamalar", []).append({
                "teacher": existing_teacher,
                "subject": subject_name,
                "class": self.class_name,
                "duration": dur,
                "type": canonical_type,
                "color": get_subject_color(subject_name),
                "is_combined": True,
                "combined_classes": [self.class_name]
            })
            
        from version_store import sanitize_atamalar
        self.data_store["atamalar"] = sanitize_atamalar(self.data_store.get("atamalar", []))
        trigger_save_db(self, self.data_store)
        self._load_data()

    def accept(self):
        try:
            trigger_save_db(self, self.data_store)
            win = self.window()
            if not win or not hasattr(win, "_grid"):
                p = self.parent()
                while p:
                    if hasattr(p, "_grid"):
                        win = p
                        break
                    p = p.parent()
            if win:
                if hasattr(win, "_refresh_tree"): win._refresh_tree()
                if hasattr(win, "_refresh_grid"): win._refresh_grid()
                if hasattr(win, "_refresh_unplaced_lessons"): win._refresh_unplaced_lessons()
        except Exception as e:
            print(f"[ACCEPT_SYNC_ERR] {e}")
        super().accept()

    def _remove_subject_assignment(self, subject_name):
        v_scroll = self.table.verticalScrollBar().value()
        subj_target = format_tr_name(subject_name)
        cur_c = format_tr_name(self.class_name)
        
        atamalar = self.data_store.get("atamalar", [])
        new_atamalar = []
        for a in atamalar:
            s_name = format_tr_name(a.get("subject", ""))
            if s_name != subj_target:
                new_atamalar.append(a)
                continue
            
            c_str = a.get("class", "")
            # Check if this assignment applies to this class
            if matches_class(c_str, self.class_name):
                # Direct single class assignment -> remove completely
                continue
            elif a.get("is_combined") or "+" in c_str or "," in c_str or "&" in c_str:
                # Combined assignment -> remove self.class_name from combined classes
                comb = list(a.get("combined_classes", []))
                if not comb and ("+" in c_str or "," in c_str or "&" in c_str):
                    comb = [c.strip() for c in c_str.replace("&", "+").replace(",", "+").split("+") if c.strip()]
                
                comb = [c for c in comb if not matches_class(c, self.class_name)]
                if len(comb) >= 2:
                    a["combined_classes"] = comb
                    a["class"] = " + ".join(comb)
                    a["is_combined"] = True
                    new_atamalar.append(a)
                elif len(comb) == 1:
                    a["combined_classes"] = []
                    a["class"] = comb[0]
                    a["is_combined"] = False
                    new_atamalar.append(a)
                else:
                    # 0 classes remain -> drop assignment
                    continue
            else:
                new_atamalar.append(a)
                
        self.data_store["atamalar"] = new_atamalar
        
        # Clean placements from grid_placements and yerlesim
        grid_data = self.data_store.get("grid_placements", [])
        if isinstance(grid_data, list):
            self.data_store["grid_placements"] = [
                p for p in grid_data
                if not (format_tr_name(p.get("subject_name", p.get("subject", ""))) == subj_target and
                        matches_class(p.get("class_name", p.get("class", "")), self.class_name))
            ]
        yerlesim = self.data_store.get("yerlesim", {})
        if isinstance(yerlesim, dict):
            for k in list(yerlesim.keys()):
                info = yerlesim[k]
                if isinstance(info, dict):
                    if (format_tr_name(info.get("subject_name", info.get("subject", ""))) == subj_target and
                        matches_class(info.get("class_name", info.get("class", "")), self.class_name)):
                        yerlesim.pop(k, None)
                        
        trigger_save_db(self, self.data_store)
        
        # Live sync with main window
        win = self.window()
        if not win or not hasattr(win, "_grid"):
            p = self.parent()
            while p:
                if hasattr(p, "_grid"):
                    win = p
                    break
                p = p.parent()
        if win:
            if hasattr(win, "save_db"): win.save_db(sync_from_grid=False)
            if hasattr(win, "_refresh_tree"): win._refresh_tree()
            if hasattr(win, "_load_unplaced_lessons"): win._load_unplaced_lessons()
            if hasattr(win, "_refresh_unplaced_lessons"): win._refresh_unplaced_lessons()
            if hasattr(win, "_restore_grid_placements"): win._restore_grid_placements()
            if hasattr(win, "_refresh_grid"): win._refresh_grid()

        self._load_data()
        self.table.verticalScrollBar().setValue(v_scroll)

    def _edit_subject_assignment(self, subject_name):
        v_scroll = self.table.verticalScrollBar().value()
        d = SubjectTeacherAssignmentDialog(
            subject_name=subject_name,
            data_store=self.data_store,
            parent=self,
            current_class=self.class_name
        )
        if d.exec():
            trigger_save_db(self, self.data_store)
            self._load_data()
            self.table.verticalScrollBar().setValue(v_scroll)
            win = self.window()
            if not win or not hasattr(win, "_grid"):
                p = self.parent()
                while p:
                    if hasattr(p, "_grid"):
                        win = p
                        break
                    p = p.parent()
            if win:
                if hasattr(win, "save_db"): win.save_db(sync_from_grid=False)
                if hasattr(win, "_refresh_tree"): win._refresh_tree()
                if hasattr(win, "_grid") and hasattr(win._grid, "load_data"):
                    win._grid.load_data(win.data_store)

    def _print_class_timetable(self):
        from dialogs.print_preview import TimetablePrintPreview
        filters = {
            "entity_type": "class_list",
            "default_selection": self.class_name,
            "lock_mode": "Sınıf Dersleri & Atama Listesi (Liste Formatı)"
        }
        dlg = TimetablePrintPreview(data_store=self.data_store, filters=filters, parent=self)
        dlg.exec()
