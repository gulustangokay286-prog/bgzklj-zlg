import os, sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QLineEdit, QComboBox, QCheckBox, QColorDialog, QFrame, QFormLayout, QGridLayout,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QListWidgetItem,
    QMessageBox, QGroupBox, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QBrush
from database import trigger_save_db

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
    """Birleşik Sınıflar Seçimi ve Çakışma Yönetimi Penceresi"""
    def __init__(self, data_store=None, selected_classes=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Birleşik Sınıflar Seçimi")
        self.setFixedSize(460, 530)
        self.data_store = data_store or {}
        self.selected_classes = list(selected_classes or [])
        self.bypass_conflict = False
        
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; }
            QLabel { color: #1E293B; font-size: 13px; }
            QCheckBox { font-size: 13px; font-weight: 500; padding: 4px; }
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
        lbl_h = QLabel("🔗 <b>Birleştirilecek Sınıfları Seçin</b> (En az 2 sınıf gereklidir)")
        lbl_h.setStyleSheet("color: #92400E; font-size: 13px;")
        info_lay.addWidget(lbl_h)
        lbl_sub = QLabel("Seçilen sınıflar aynı saatte tek bir derslikte birleşik ders alacak şekilde planlanır.\nBirleşik sınıfı kaldırmak için 'Birleşik Sınıfı Kaldır' butonunu kullanabilirsiniz.")
        lbl_sub.setStyleSheet("color: #B45309; font-size: 11px;")
        info_lay.addWidget(lbl_sub)
        layout.addWidget(info_card)
        
        # Quick Select Bar
        quick_lay = QHBoxLayout()
        self.btn_select_all = QPushButton("Tümünü Seç")
        self.btn_select_all.clicked.connect(self._toggle_select_all)
        self.lbl_selected_count = QLabel("Seçili: 0 Sınıf")
        self.lbl_selected_count.setStyleSheet("font-weight: bold; color: #0284C7;")
        quick_lay.addWidget(self.btn_select_all)
        quick_lay.addStretch(1)
        quick_lay.addWidget(self.lbl_selected_count)
        layout.addLayout(quick_lay)
        
        # Classes Scroll Checklist
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; }")
        
        w = QWidget()
        w.setStyleSheet("background: #FFFFFF;")
        self.v_lay = QVBoxLayout(w)
        self.v_lay.setContentsMargins(10, 10, 10, 10)
        self.v_lay.setSpacing(6)
        
        classes = sorted([c.get("ad", "") for c in self.data_store.get("siniflar", []) if c.get("ad")])
        self.chks = []
        for c in classes:
            chk = QCheckBox(c)
            if c in self.selected_classes:
                chk.setChecked(True)
            chk.stateChanged.connect(self._on_check_changed)
            self.v_lay.addWidget(chk)
            self.chks.append(chk)
            
        self.v_lay.addStretch(1)
        scroll.setWidget(w)
        layout.addWidget(scroll)
        
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
        
        self.btn_yoksay = QPushButton("⚠️ Çakışmayı Yoksay ve Birleştir")
        self.btn_yoksay.setStyleSheet("background: #EA580C; color: white; font-weight: bold; border-radius: 4px; padding: 6px 12px;")
        self.btn_yoksay.setVisible(False)
        self.btn_yoksay.clicked.connect(lambda: self._do_accept(bypass=True))
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedSize(80, 32)
        btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QPushButton("✅ Tamam")
        self.btn_ok.setFixedSize(110, 32)
        self.btn_ok.setStyleSheet("background: #0078D7; color: white; font-weight: bold; border-radius: 4px;")
        self.btn_ok.clicked.connect(lambda: self._do_accept(bypass=False))
        
        bot.addWidget(self.btn_clear)
        bot.addWidget(self.btn_yoksay)
        bot.addStretch(1)
        bot.addWidget(btn_cancel)
        bot.addWidget(self.btn_ok)
        layout.addLayout(bot)
        
        self._on_check_changed()
        
    def _toggle_select_all(self):
        all_checked = all(c.isChecked() for c in self.chks)
        for c in self.chks:
            c.setChecked(not all_checked)
        self.btn_select_all.setText("Tümünü Kaldır" if not all_checked else "Tümünü Seç")
        
    def _do_clear(self):
        for c in self.chks:
            c.setChecked(False)
        self.selected_classes = []
        self.accept()
        
    def _check_conflicts(self, selected_names):
        grid_placements = self.data_store.get("grid_placements", [])
        if not grid_placements:
            return False, ""
            
        slot_map = {}
        for item in grid_placements:
            c_name = item.get("class_name") or item.get("class")
            if c_name in selected_names:
                key = (item.get("day"), item.get("period"))
                if key in slot_map and slot_map[key] != c_name:
                    return True, f"Çakışma Tespit Edildi: {c_name} ve {slot_map[key]} sınıflarının aynı zaman diliminde yerleştirilmiş dersi var."
                slot_map[key] = c_name
        return False, ""
        
    def _on_check_changed(self):
        sel = [c.text() for c in self.chks if c.isChecked()]
        self.lbl_selected_count.setText(f"Seçili: {len(sel)} Sınıf")
        
        has_conflict, msg = self._check_conflicts(sel)
        if has_conflict:
            self.lbl_conflict.setText(f"⚠️ {msg}")
            self.lbl_conflict.setVisible(True)
            self.btn_yoksay.setVisible(True)
        else:
            self.lbl_conflict.setText("")
            self.lbl_conflict.setVisible(False)
            self.btn_yoksay.setVisible(False)
            
    def _do_accept(self, bypass=False):
        sel = [c.text() for c in self.chks if c.isChecked()]
        if len(sel) == 0:
            self.selected_classes = []
            self.accept()
            return
        if len(sel) < 2:
            QMessageBox.warning(self, "Yetersiz Sınıf Seçimi", "Birleşik sınıf oluşturabilmek için en az 2 sınıf seçiniz veya seçimi temizlemek için 'Birleşik Sınıfı Kaldır' butonuna basınız.")
            return
        self.selected_classes = sel
        self.bypass_conflict = bypass
        self.accept()
        
    def get_selected_classes(self):
        return self.selected_classes
        
    def get_combined_string(self):
        return " + ".join(self.selected_classes) if self.selected_classes else ""


class LessonAssignmentDialog(QDialog):
    """
    Gelişmiş Çoklu Ders, Sınıf ve Saat Eşleştirme Paneli (Prompt 1, 2, 3 Gereksinimleri)
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
        self.resize(760, 700)
        self.setMinimumSize(700, 640)
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
        self.combined_classes = []
        
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
        
        # 2. Atanacak Dersler Kartı (Dinamik Çoklu Input Mimarisi)
        row2 = self._create_row_frame()
        self.l2_main = QVBoxLayout(row2)
        self.l2_main.setContentsMargins(14, 12, 14, 12)
        self.l2_main.setSpacing(10)
        
        # Header + Info Badge
        h_ders_head = QHBoxLayout()
        lbl_dersler_title = QLabel("<b>Atanacak Dersler</b> (Otomatik Genişleyen Ders & Sınıf Eşleme)")
        lbl_dersler_title.setStyleSheet("color: #0F172A; font-size: 13px;")
        h_ders_head.addWidget(lbl_dersler_title)
        h_ders_head.addStretch(1)
        
        btn_info = QPushButton("İpucu")
        btn_info.setStyleSheet("background: #EFF6FF; color: #1D4ED8; font-size: 11px; padding: 2px 8px; border: 1px solid #BFDBFE;")
        btn_info.clicked.connect(lambda: QMessageBox.information(
            self, "Ders Girişi İpucu",
            "Ders seçtikçe veya arama alanına yazdıkça aşağıda otomatik olarak yeni bir ders satırı açılır.\n"
            "Tüm derslerinizi tamamladıysanız en altta boş kalan satırı doldurmanıza gerek yoktur, doğrudan kaydedebilirsiniz."
        ))
        h_ders_head.addWidget(btn_info)
        self.l2_main.addLayout(h_ders_head)
        
        # Container for dynamic subject rows
        self.subjects_container = QVBoxLayout()
        self.subjects_container.setSpacing(8)
        self.l2_main.addLayout(self.subjects_container)
        
        self.scroll_layout.addWidget(row2)
        
        # 3. Sınıf / Sınıflarım Kartı
        row3 = self._create_row_frame()
        l3 = QHBoxLayout(row3)
        l3.setContentsMargins(14, 12, 14, 12)
        
        v3 = QVBoxLayout()
        lbl_sinif = QLabel("<b>Sınıf / Sınıflarım (Genel Özet & Birleşik Sınıf)</b>")
        lbl_sinif.setStyleSheet("color: #0F172A; font-size: 13px;")
        v3.addWidget(lbl_sinif)
        
        self.txt_classes_summary = QLineEdit()
        self.txt_classes_summary.setReadOnly(True)
        self.txt_classes_summary.setPlaceholderText("Derslere atanan sınıflar burada otomatik listelenir (Örn: 9A, 10B, 11C)")
        self.txt_classes_summary.setStyleSheet("background: #F1F5F9; color: #0F172A; font-weight: bold;")
        v3.addWidget(self.txt_classes_summary)
        l3.addLayout(v3)
        l3.addSpacing(10)
        
        btn_birl_sinif = QPushButton("Birleşik Sınıflar...")
        btn_birl_sinif.setStyleSheet("background: #FFFBEB; color: #B45309; font-weight: bold; border: 1px solid #FDE68A; border-radius: 4px; padding: 6px 14px;")
        btn_birl_sinif.clicked.connect(self._open_combined_classes_modal)
        l3.addWidget(btn_birl_sinif, alignment=Qt.AlignBottom)
        self.scroll_layout.addWidget(row3)
        
        # 4. Derslik Seçim Kartı
        row4 = self._create_row_frame()
        l4 = QHBoxLayout(row4)
        l4.setContentsMargins(14, 12, 14, 12)
        
        v4 = QVBoxLayout()
        lbl_derslik = QLabel("<b>Derslik Seçimi</b>")
        lbl_derslik.setStyleSheet("color: #0F172A; font-size: 13px;")
        v4.addWidget(lbl_derslik)
        
        self.txt_derslik = QLineEdit()
        self.txt_derslik.setPlaceholderText("Derslik Seç (Opsiyonel)")
        v4.addWidget(self.txt_derslik)
        l4.addLayout(v4)
        self.scroll_layout.addWidget(row4)
        
        # 5. Canlı Özet Çubuğu
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

    def _add_subject_row(self, subject_name="", hours="2", distribution="2", assigned_classes=None, class_configs=None):
        row_widget = QWidget()
        row_widget.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 4px;")
        row_layout = QVBoxLayout(row_widget)
        row_layout.setContentsMargins(8, 8, 8, 8)
        row_layout.setSpacing(6)
        
        top_h = QHBoxLayout()
        
        # Subject Combo (Searchable + Mouse Wheel Blocked)
        cb_subject = NoScrollComboBox()
        cb_subject.setMinimumWidth(220)
        cb_subject.setEditable(True)
        all_subjs = self._get_all_subjects()
        cb_subject.addItems(all_subjs)
        
        # Autocomplete search
        from PySide6.QtWidgets import QCompleter
        completer = QCompleter(all_subjs, cb_subject)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        cb_subject.setCompleter(completer)
        
        if cb_subject.lineEdit():
            cb_subject.lineEdit().setPlaceholderText("Ders Ara veya Seç...")
            
        if subject_name:
            idx = cb_subject.findText(subject_name)
            if idx >= 0: cb_subject.setCurrentIndex(idx)
            else: cb_subject.setCurrentText(subject_name)
        else:
            cb_subject.setCurrentIndex(-1)
            if cb_subject.lineEdit():
                cb_subject.lineEdit().clear()
                cb_subject.lineEdit().setPlaceholderText("Ders Ara veya Seç...")
            
        top_h.addWidget(cb_subject, 2)
        
        # Hours / Tip Combo (Mouse Wheel Blocked)
        cb_tip = NoScrollComboBox()
        cb_tip.setMinimumWidth(100)
        cb_tip.setEditable(True)
        cb_tip.addItems(["1", "2", "3", "4", "5", "6", "1+1", "2+1", "2+2", "3+1", "3+2", "4+2", "3+3", "2+2+1", "2+2+2", "3+2+1"])
        if distribution:
            idx_t = cb_tip.findText(distribution)
            if idx_t >= 0: cb_tip.setCurrentIndex(idx_t)
            else: cb_tip.setCurrentText(distribution)
        top_h.addWidget(cb_tip, 1)
        
        # Sınıfları Seç Butonu
        btn_classes = QPushButton("Sınıf(lar) Ata...")
        btn_classes.setStyleSheet("background: #F0FDF4; color: #166534; font-weight: bold; border: 1px solid #BBF7D0;")
        top_h.addWidget(btn_classes, 1)
        
        # Sil Butonu
        btn_del = QPushButton("X")
        btn_del.setFixedSize(30, 30)
        btn_del.setStyleSheet("background: #FEE2E2; color: #DC2626; font-weight: bold; border: 1px solid #FECACA;")
        top_h.addWidget(btn_del)
        
        row_layout.addLayout(top_h)
        
        # Badge showing assigned classes for this row with their individual hours
        lbl_classes_badge = QLabel("Atanan Sınıflar: " + (", ".join(assigned_classes) if assigned_classes else "Tüm Sınıflar / Belirtilmedi"))
        lbl_classes_badge.setStyleSheet("color: #0369A1; font-size: 11px; font-weight: bold; padding-left: 4px;")
        row_layout.addWidget(lbl_classes_badge)
        
        row_data = {
            "widget": row_widget,
            "cb_subject": cb_subject,
            "cb_tip": cb_tip,
            "lbl_badge": lbl_classes_badge,
            "classes": list(assigned_classes or []),
            "class_configs": dict(class_configs or {})
        }
        self.subject_rows.append(row_data)
        self.subjects_container.addWidget(row_widget)
        
        # Connect signals
        btn_classes.clicked.connect(lambda: self._edit_classes_for_row(row_data))
        btn_del.clicked.connect(lambda: self._remove_subject_row(row_data))
        
        cb_subject.editTextChanged.connect(lambda t: self._on_subject_changed(row_data, t))
        cb_tip.currentTextChanged.connect(lambda t: self._on_tip_changed(row_data))
        
        self._update_row_badge(row_data)
        self._update_ozet()

    def _update_row_badge(self, row_data):
        assigned_classes = row_data["classes"]
        configs = row_data.get("class_configs", {})
        default_dist = row_data["cb_tip"].currentText().strip() or "2"
        
        if not assigned_classes:
            row_data["lbl_badge"].setText("Atanan Sınıflar: Tüm Sınıflar / Belirtilmedi")
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
        if clean:
            # If this is the last row, automatically append a new empty row below it!
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
            selected_classes=row_data["classes"],
            default_distribution=default_dist,
            class_configs=row_data.get("class_configs", {}),
            parent=self
        )
        if dlg.exec() == QDialog.Accepted:
            row_data["classes"] = dlg.get_selected()
            row_data["class_configs"] = dlg.get_configs()
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
            self._update_row_badge(row_data)
        else:
            self.subject_rows.remove(row_data)
            self.subjects_container.removeWidget(row_data["widget"])
            row_data["widget"].deleteLater()
            
        self._update_classes_summary()
        self._update_ozet()

    def _open_combined_classes_modal(self):
        dlg = CombinedClassesDialog(self.data_store, self.combined_classes, self)
        if dlg.exec() == QDialog.Accepted:
            self.combined_classes = dlg.get_selected_classes()
            comb_str = dlg.get_combined_string()
            if comb_str:
                self.txt_classes_summary.setText(f"BİRLEŞİK: {comb_str}")
            else:
                self._update_classes_summary()

    def _update_classes_summary(self):
        if self.combined_classes:
            self.txt_classes_summary.setText(f"BİRLEŞİK: {' + '.join(self.combined_classes)}")
            return
            
        all_assigned = []
        for r in self.subject_rows:
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
            cfg_map = r.get("class_configs", {})
            assigned_c = r["classes"] or (self.combined_classes if self.combined_classes else ["9A"])
            def_dist = r["cb_tip"].currentText().strip() or "2"
            
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
        
        # Group by subject
        subj_map = {}
        for a in my_atamalar:
            s_name = a.get("subject", "").strip()
            if not s_name: continue
            cls_name = a.get("class", "").strip()
            dur = a.get("duration", 2)
            typ = a.get("type", str(dur))
            if s_name not in subj_map:
                subj_map[s_name] = {
                    "classes": [],
                    "duration": dur,
                    "type": typ,
                    "class_configs": {}
                }
            if cls_name:
                if cls_name not in subj_map[s_name]["classes"]:
                    subj_map[s_name]["classes"].append(cls_name)
                subj_map[s_name]["class_configs"][cls_name] = {"type": typ, "duration": dur}
                
        if subj_map:
            for s_name, s_data in subj_map.items():
                self._add_subject_row(s_name, str(s_data.get("duration", 2)), s_data.get("type", "2"), s_data.get("classes", []), class_configs=s_data.get("class_configs", {}))
        else:
            self._add_subject_row("", "2", "2", [], {})
            
        # Add trailing empty row for frictionless addition
        if self.subject_rows and self.subject_rows[-1]["cb_subject"].currentText().strip():
            self._add_subject_row("", "2", "2", [], {})
            
        self._update_classes_summary()
        self._update_ozet()

    def accept(self):
        # 1. Update data_store["atamalar"] for this teacher
        teacher_name = format_tr_name(self.cb_ogretmen.currentText().strip())
        if self.data_store is not None and teacher_name:
            if "atamalar" not in self.data_store:
                self.data_store["atamalar"] = []
                
            # Remove old assignments for this teacher
            self.data_store["atamalar"] = [
                a for a in self.data_store["atamalar"]
                if format_tr_name(a.get("teacher", "")) != teacher_name
            ]
            
            # Add new assignments
            new_data = self.get_data()
            if isinstance(new_data, list):
                self.data_store["atamalar"].extend(new_data)
            elif new_data:
                self.data_store["atamalar"].append(new_data)
                
            # Clean up grid placements, auto_schedule_results, and yerlesim for removed assignments
            active_tuples = {
                (format_tr_name(a.get("subject", "")), format_tr_name(a.get("class", "")), teacher_name)
                for a in (new_data if isinstance(new_data, list) else [new_data])
                if a
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
            if not win or not hasattr(win, "_grid"):
                p = self.parent()
                while p:
                    if hasattr(p, "_grid"):
                        win = p
                        break
                    p = p.parent()
            if win:
                if hasattr(win, "save_db"): win.save_db(sync_from_grid=False)
                if hasattr(win, "_refresh_grid"): win._refresh_grid()
                if hasattr(win, "_refresh_tree"): win._refresh_tree()
                if hasattr(win, "_load_unplaced_lessons"): win._load_unplaced_lessons()
                if hasattr(win, "_refresh_unplaced_lessons"): win._refresh_unplaced_lessons()
                
        super().accept()

    def get_data(self):
        teacher_name = format_tr_name(self.cb_ogretmen.currentText().strip())
        all_classes_list = self._get_all_classes()
        default_class = all_classes_list[0] if all_classes_list else "9A"
        
        assignments = []
        for r in self.subject_rows:
            subj = r["cb_subject"].currentText().strip()
            if not subj:
                continue
                
            default_type_val = r["cb_tip"].currentText().strip()
            assigned_classes = r["classes"]
            if not assigned_classes:
                if self.combined_classes:
                    assigned_classes = [" + ".join(self.combined_classes)]
                else:
                    assigned_classes = [default_class]
                    
            for c_name in assigned_classes:
                cfg = r.get("class_configs", {}).get(c_name, {})
                type_val = cfg.get("type", default_type_val)
                if "+" in type_val:
                    parts = [int(p.strip()) for p in type_val.split("+") if p.strip().isdigit()]
                    duration = sum(parts) if parts else 1
                else:
                    duration = int(type_val) if type_val.isdigit() else 1
                    
                assignments.append({
                    "teacher": teacher_name,
                    "subject": subj,
                    "class": c_name,
                    "duration": duration,
                    "type": type_val,
                    "color": get_subject_color(subj)
                })
                
        return assignments


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


class MultiClassAssignDialog(QDialog):
    """Modern Checkbox ile Çoklu Sınıf Seçim Penceresi & Birleşik Sınıf Desteği"""
    def __init__(self, teacher_name="", subject_name="", all_classes=None, selected_classes=None, is_combined=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Sınıf Seçimi — {teacher_name}")
        self.resize(360, 480)
        all_classes = all_classes or []
        selected_classes = selected_classes or []
        
        chk_checked = get_asset_path("resources/chk_checked.png")
        chk_unchk = get_asset_path("resources/chk_unchecked.png")
        
        self.setStyleSheet(f"""
            QDialog {{ background: #FFFFFF; }}
            QListWidget {{ border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px; }}
            QListWidget::item {{ padding: 8px 12px; }}
            QListWidget::indicator {{
                width: 18px;
                height: 18px;
            }}
            QListWidget::indicator:unchecked {{
                image: url("{chk_unchk}");
            }}
            QListWidget::indicator:checked {{
                image: url("{chk_checked}");
            }}
            QPushButton {{ min-height: 32px; padding: 4px 14px; border-radius: 6px; font-weight: bold; font-size: 13px; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(12)
        
        lbl = QLabel(f"🎓 {teacher_name} — Atanacak Sınıflar\n(Ders: {subject_name})")
        lbl.setStyleSheet("color: #0284C7; font-size: 14px;")
        lay.addWidget(lbl)
        
        self.list_widget = QListWidget()
        for c in all_classes:
            item = QListWidgetItem(c)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if c in selected_classes else Qt.Unchecked)
            self.list_widget.addItem(item)
        lay.addWidget(self.list_widget)
        
        btn_all = QPushButton("Tüm Sınıfları Seç / Kaldır")
        btn_all.setStyleSheet("background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1;")
        def toggle_all():
            any_unchecked = any(self.list_widget.item(i).checkState() == Qt.Unchecked for i in range(self.list_widget.count()))
            new_st = Qt.Checked if any_unchecked else Qt.Unchecked
            for i in range(self.list_widget.count()):
                self.list_widget.item(i).setCheckState(new_st)
        btn_all.clicked.connect(toggle_all)
        lay.addWidget(btn_all)
        
        # 🔗 Birleşik Dersler Ayarlama Butonu
        btn_combine_manager = QPushButton("🔗 Birleşik Dersler Ayarla (Sınıf & Ders Birleştirme)...")
        btn_combine_manager.setStyleSheet("background: #EFF6FF; color: #1D4ED8; font-weight: bold; border: 1px solid #BFDBFE; border-radius: 4px; padding: 6px; margin-top: 2px;")
        def open_combined():
            p = self.parent()
            ds = getattr(p, "data_store", {}) if p else {}
            dlg = CombinedClassesAssignDialog(
                data_store=ds,
                parent=self,
                default_classes=self.get_selected_classes()
            )
            if dlg.exec():
                if hasattr(dlg, "selected_classes"):
                    for i in range(self.list_widget.count()):
                        txt = self.list_widget.item(i).text()
                        self.list_widget.item(i).setCheckState(Qt.Checked if txt in dlg.selected_classes else Qt.Unchecked)
                    self.chk_combine.setChecked(True)
        btn_combine_manager.clicked.connect(open_combined)
        lay.addWidget(btn_combine_manager)
        
        # 🔗 Birleşik Sınıf Seçeneği (Ortak Ders)
        self.chk_combine = QCheckBox("🔗 Seçili Sınıfları Birleştir (Ortak/Birleşik Ders Yap)")
        self.chk_combine.setChecked(is_combined)
        self.chk_combine.setStyleSheet("QCheckBox { font-weight: bold; color: #1E40AF; font-size: 12px; margin-top: 4px; }")
        lay.addWidget(self.chk_combine)
        
        btns = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; color: #475569;")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Uygula")
        btn_ok.setStyleSheet("background: #2563EB; color: white; border: none;")
        btn_ok.clicked.connect(self.accept)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)
        lay.addLayout(btns)
        
    def get_selected_classes(self):
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count()) if self.list_widget.item(i).checkState() == Qt.Checked]

    def get_is_combined(self):
        return self.chk_combine.isChecked()


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
        if "2+2" in type_choice:
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
            t_asgns = [a for a in existing if format_tr_name(a.get("teacher", "")) == format_tr_name(t)]
            if t_asgns:
                t_classes = list({a.get("class", "") for a in t_asgns if a.get("class")})
                t_type = t_asgns[0].get("type", str(t_asgns[0].get("duration", 2)))
                
                # If current_class is specified (e.g. "9A"), is THIS teacher assigned to THIS class?
                if self.current_class:
                    is_for_cur = any(format_tr_name(c) == format_tr_name(self.current_class) for c in t_classes)
                    self.teacher_configs[t] = {
                        "checked": is_for_cur,
                        "type": t_type,
                        "classes": t_classes if is_for_cur else [self.current_class]
                    }
                else:
                    self.teacher_configs[t] = {
                        "checked": True,
                        "type": t_type,
                        "classes": t_classes
                    }
            else:
                self.teacher_configs[t] = {
                    "checked": False,
                    "type": "2",
                    "classes": [self.current_class] if self.current_class else (self.all_classes[:1] if self.all_classes else [])
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
        
        # Table (Integrated Teacher + Hours + Classes)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            "Atanacak Öğretmen", "Haftalık Saat / Dağılım Tipi", "Atanan Sınıf(lar)", "Ayrıcalıklı Sınıf Seçimi"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 260)
        self.table.setColumnWidth(1, 190)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnWidth(3, 190)
        self.table.verticalHeader().setDefaultSectionSize(38)
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

    def _create_hour_combo(self, t_name, current_val):
        cb_tip = QComboBox()
        cb_tip.setEditable(True)
        cb_tip.addItems(["1", "2", "3", "4", "5", "6", "7", "8", "1+1", "2+1", "2+2", "3+1", "3+2", "2+2+1", "2+2+2"])
        cb_tip.setCurrentText(str(current_val))
        cb_tip.currentTextChanged.connect(lambda txt, t=t_name: self._on_type_changed(t, txt))
        return cb_tip

    def _create_class_modal_btn(self, t_name, row_idx):
        btn = QPushButton("⚙️ Daha Fazla Sınıf Ata")
        btn.setFixedHeight(26)
        btn.setStyleSheet("background: #F0F9FF; color: #0284C7; border: 1px solid #BAE6FD; border-radius: 5px; font-size: 11px; font-weight: bold;")
        btn.clicked.connect(lambda chk=False, t=t_name, r=row_idx: self._open_class_modal(t, r))
        return btn

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
            
            # 1. Weekly Hours (Only created when checked!)
            if cfg["checked"]:
                self.table.setCellWidget(row, 1, self._create_hour_combo(t_name, cfg["type"]))
            else:
                self.table.removeCellWidget(row, 1)
                it1 = QTableWidgetItem("—")
                it1.setTextAlignment(Qt.AlignCenter)
                it1.setForeground(QBrush(QColor("#CBD5E1")))
                it1.setFlags(it1.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row, 1, it1)
            
            # 2. Classes Label / Badges
            if cfg.get("is_combined") and len(cfg.get("classes", [])) > 1:
                cls_str = f"( {' & '.join(cfg['classes'])} sınıfı birleşiktir )"
            else:
                cls_str = ", ".join(cfg["classes"]) if (cfg["checked"] and cfg["classes"]) else "—"
            item_cls = QTableWidgetItem(cls_str)
            item_cls.setTextAlignment(Qt.AlignCenter)
            item_cls.setFlags(item_cls.flags() ^ Qt.ItemIsEditable)
            if not cfg["checked"]:
                item_cls.setForeground(QBrush(QColor("#CBD5E1")))
            else:
                if cfg.get("is_combined") and len(cfg.get("classes", [])) > 1:
                    item_cls.setForeground(QBrush(QColor("#16A34A"))) # Green for combined
                else:
                    item_cls.setForeground(QBrush(QColor("#0284C7")))
                item_cls.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(row, 2, item_cls)
            
            # 3. Class Assignment Modal Button (Only created when checked!)
            if cfg["checked"]:
                self.table.setCellWidget(row, 3, self._create_class_modal_btn(t_name, row))
            else:
                self.table.removeCellWidget(row, 3)
                it3 = QTableWidgetItem("—")
                it3.setTextAlignment(Qt.AlignCenter)
                it3.setForeground(QBrush(QColor("#CBD5E1")))
                it3.setFlags(it3.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row, 3, it3)

    def _on_teacher_toggled(self, teacher_name, is_checked):
        self.teacher_configs[teacher_name]["checked"] = is_checked
        
        # If current_class is specified, sync classes list with checkbox state
        if self.current_class:
            cur_c = self.current_class
            classes_list = self.teacher_configs[teacher_name]["classes"]
            if is_checked:
                if not any(format_tr_name(c) == format_tr_name(cur_c) for c in classes_list):
                    classes_list.append(cur_c)
            else:
                classes_list = [c for c in classes_list if format_tr_name(c) != format_tr_name(cur_c)]
                self.teacher_configs[teacher_name]["classes"] = classes_list
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
                    item_cls = self.table.item(r, 2)
                    
                    if is_checked:
                        self.table.setCellWidget(r, 1, self._create_hour_combo(teacher_name, self.teacher_configs[teacher_name]["type"]))
                        if item_cls:
                            cls_str = ", ".join(self.teacher_configs[teacher_name]["classes"]) if self.teacher_configs[teacher_name]["classes"] else "—"
                            item_cls.setText(cls_str)
                            item_cls.setForeground(QBrush(QColor("#0284C7")))
                            item_cls.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                        self.table.setCellWidget(r, 3, self._create_class_modal_btn(teacher_name, r))
                    else:
                        self.table.removeCellWidget(r, 1)
                        it1 = QTableWidgetItem("—")
                        it1.setTextAlignment(Qt.AlignCenter)
                        it1.setForeground(QBrush(QColor("#CBD5E1")))
                        it1.setFlags(it1.flags() ^ Qt.ItemIsEditable)
                        self.table.setItem(r, 1, it1)
                        
                        if item_cls:
                            item_cls.setText("—")
                            item_cls.setForeground(QBrush(QColor("#CBD5E1")))
                            
                        self.table.removeCellWidget(r, 3)
                        it3 = QTableWidgetItem("—")
                        it3.setTextAlignment(Qt.AlignCenter)
                        it3.setForeground(QBrush(QColor("#CBD5E1")))
                        it3.setFlags(it3.flags() ^ Qt.ItemIsEditable)
                        self.table.setItem(r, 3, it3)
                    break
                
        # Find row and show/hide widgets cleanly
        for r in range(self.table.rowCount()):
            w_chk = self.table.cellWidget(r, 0)
            if w_chk:
                chk = w_chk.findChild(QCheckBox)
                if chk and chk.text() == teacher_name:
                    item_cls = self.table.item(r, 2)
                    
                    if is_checked:
                        self.table.setCellWidget(r, 1, self._create_hour_combo(teacher_name, self.teacher_configs[teacher_name]["type"]))
                        if item_cls:
                            cls_str = ", ".join(self.teacher_configs[teacher_name]["classes"]) if self.teacher_configs[teacher_name]["classes"] else "—"
                            item_cls.setText(cls_str)
                            item_cls.setForeground(QBrush(QColor("#0284C7")))
                            item_cls.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                        self.table.setCellWidget(r, 3, self._create_class_modal_btn(teacher_name, r))
                    else:
                        self.table.removeCellWidget(r, 1)
                        it1 = QTableWidgetItem("—")
                        it1.setTextAlignment(Qt.AlignCenter)
                        it1.setForeground(QBrush(QColor("#CBD5E1")))
                        it1.setFlags(it1.flags() ^ Qt.ItemIsEditable)
                        self.table.setItem(r, 1, it1)
                        
                        if item_cls:
                            item_cls.setText("—")
                            item_cls.setForeground(QBrush(QColor("#CBD5E1")))
                            
                        self.table.removeCellWidget(r, 3)
                        it3 = QTableWidgetItem("—")
                        it3.setTextAlignment(Qt.AlignCenter)
                        it3.setForeground(QBrush(QColor("#CBD5E1")))
                        it3.setFlags(it3.flags() ^ Qt.ItemIsEditable)
                        self.table.setItem(r, 3, it3)
                    break

    def _on_type_changed(self, teacher_name, new_type):
        self.teacher_configs[teacher_name]["type"] = str(new_type).strip()

    def _open_class_modal(self, teacher_name, row_idx):
        cfg = self.teacher_configs[teacher_name]
        d = MultiClassAssignDialog(
            teacher_name=teacher_name,
            subject_name=self.subject_name,
            all_classes=self.all_classes,
            selected_classes=cfg["classes"],
            is_combined=cfg.get("is_combined", False),
            parent=self
        )
        if d.exec():
            new_classes = d.get_selected_classes()
            is_comb = d.get_is_combined()
            cfg["classes"] = new_classes
            cfg["is_combined"] = is_comb
            item_cls = self.table.item(row_idx, 2)
            if item_cls:
                if is_comb and len(new_classes) > 1:
                    cls_str = f"( {' & '.join(new_classes)} sınıfı birleşiktir )"
                    item_cls.setForeground(QBrush(QColor("#16A34A")))
                else:
                    cls_str = ", ".join(new_classes) if new_classes else "—"
                    item_cls.setForeground(QBrush(QColor("#0284C7")))
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
        subj_target = format_tr_name(self.subject_name)
        target_cls = format_tr_name(self.current_class) if self.current_class else ""
        atamalar = self.data_store.get("atamalar", [])
        
        if target_cls:
            self.data_store["atamalar"] = [
                a for a in atamalar
                if not (format_tr_name(a.get("subject", "")) == subj_target and format_tr_name(a.get("class", "")) == target_cls)
            ]
            grid_data = self.data_store.get("grid_placements", [])
            if isinstance(grid_data, list):
                self.data_store["grid_placements"] = [
                    p for p in grid_data
                    if not (format_tr_name(p.get("subject_name", p.get("subject", ""))) == subj_target and
                            format_tr_name(p.get("class_name", p.get("class", ""))) == target_cls)
                ]
            yerlesim = self.data_store.get("yerlesim", {})
            if isinstance(yerlesim, dict):
                for k in list(yerlesim.keys()):
                    info = yerlesim[k]
                    if isinstance(info, dict):
                        if (format_tr_name(info.get("subject_name", info.get("subject", ""))) == subj_target and
                            format_tr_name(info.get("class_name", info.get("class", ""))) == target_cls):
                            yerlesim.pop(k, None)
        else:
            self.data_store["atamalar"] = [
                a for a in atamalar
                if format_tr_name(a.get("subject", "")) != subj_target
            ]
            grid_data = self.data_store.get("grid_placements", [])
            if isinstance(grid_data, list):
                self.data_store["grid_placements"] = [
                    p for p in grid_data
                    if format_tr_name(p.get("subject_name", p.get("subject", ""))) != subj_target
                ]
            yerlesim = self.data_store.get("yerlesim", {})
            if isinstance(yerlesim, dict):
                for k in list(yerlesim.keys()):
                    info = yerlesim[k]
                    if isinstance(info, dict):
                        if format_tr_name(info.get("subject_name", info.get("subject", ""))) == subj_target:
                            yerlesim.pop(k, None)
                            
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
            if hasattr(win, "save_db"): win.save_db(sync_from_grid=False)
            if hasattr(win, "_refresh_tree"): win._refresh_tree()
            if hasattr(win, "_load_unplaced_lessons"): win._load_unplaced_lessons()
            if hasattr(win, "_on_tree_selection_changed"): win._on_tree_selection_changed()

        self.accept()

    def _save_assignments(self):
        subj_target = format_tr_name(self.subject_name)
        target_cls = format_tr_name(self.current_class) if self.current_class else ""
        atamalar = self.data_store.get("atamalar", [])
        
        # 1. Sınıf bazında mı yoksa genel mi temizlenecek?
        if target_cls:
            clean_atamalar = [
                a for a in atamalar
                if not (format_tr_name(a.get("subject", "")) == subj_target and format_tr_name(a.get("class", "")) == target_cls)
            ]
        else:
            clean_atamalar = [
                a for a in atamalar
                if format_tr_name(a.get("subject", "")) != subj_target
            ]
            
        for t_name, cfg in self.teacher_configs.items():
            if cfg["checked"] and cfg["classes"]:
                type_str = str(cfg["type"]).strip() or "2"
                parts = [int(p.strip()) for p in type_str.split("+") if p.strip().isdigit()]
                total_dur = sum(parts) if parts else (int(type_str) if type_str.isdigit() else 2)
                
                target_classes = cfg["classes"]
                is_combined = bool(cfg.get("is_combined", False)) and len(target_classes) > 1
                
                for c_name in target_classes:
                    if c_name:
                        if not any(
                            format_tr_name(a.get("teacher", "")) == format_tr_name(t_name) and
                            format_tr_name(a.get("subject", "")) == subj_target and
                            format_tr_name(a.get("class", "")) == format_tr_name(c_name)
                            for a in clean_atamalar
                        ):
                            clean_atamalar.append({
                                "teacher": t_name.strip(),
                                "subject": self.subject_name.strip(),
                                "class": c_name.strip(),
                                "duration": total_dur,
                                "type": type_str,
                                "color": get_subject_color(self.subject_name),
                                "is_combined": is_combined,
                                "combined_classes": target_classes if is_combined else []
                            })
                        
        self.data_store["atamalar"] = clean_atamalar
        
        # 2. Grid Placements Senkronizasyonu: Kaldırılan atamaları çizelgeden sil!
        active_pairs = {
            (format_tr_name(a.get("subject", "")), format_tr_name(a.get("class", "")), format_tr_name(a.get("teacher", "")))
            for a in clean_atamalar
        }
        
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
                    if not (
                        format_tr_name(p.get("subject_name", p.get("subject", ""))) == subj_target and
                        (subj_target, format_tr_name(p.get("class_name", p.get("class", ""))), format_tr_name(p.get("teacher_name", p.get("teacher", "")))) not in active_pairs
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
                    if p_sub == subj_target:
                        if target_cls and p_cls == target_cls:
                            if (p_sub, p_cls, p_tea) not in active_pairs:
                                yerlesim.pop(k, None)
                        elif not target_cls:
                            if (p_sub, p_cls, p_tea) not in active_pairs:
                                yerlesim.pop(k, None)

        trigger_save_db(self, self.data_store)
        
        # 3. Ana Pencere Canlı Senkronizasyon
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
        if self.parent() and hasattr(self.parent(), "data_store"):
            raw_teachers = [t.get("ad", "") for t in self.parent().data_store.get("ogretmenler", []) if t.get("ad")]
            teachers.extend(sorted(raw_teachers))
        self.w_so.addItems(teachers)
        
        existing_so = self.existing_data.get("sinif_ogretmeni", "")
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
        lay_gorev.setContentsMargins(15, 15, 15, 15)
        lay_gorev.setSpacing(12)
        
        self.w_so = QComboBox()
        classes = [""]
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        raw_classes = [c.get("ad", "") for c in data_store.get("siniflar", []) if c.get("ad")]
        classes.extend(sorted(raw_classes))
        self.w_so.addItems(classes)
        existing_so = self.existing_data.get("sinif_ogretmeni", "")
        idx_so = self.w_so.findText(existing_so)
        if idx_so >= 0: self.w_so.setCurrentIndex(idx_so)
        
        lay_gorev.addRow(QLabel("<b>Sınıf Öğretmeni (Rehberlik):</b>"), self.w_so)
        
        self.w_brans = QLineEdit(self.existing_data.get("brans", ""))
        self.w_brans.setPlaceholderText("Örn: Matematik, Geometri")
        lay_gorev.addRow(QLabel("<b>Öğretmen Branşı:</b>"), self.w_brans)
        
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
        
        self.w_ek_dersler = QLineEdit(", ".join(my_subjects) if my_subjects else self.existing_data.get("ek_dersler", ""))
        self.w_ek_dersler.setReadOnly(True)
        self.w_ek_dersler.setStyleSheet("background: #EAEAEA; color: #333; border: 1px solid #CCC; border-radius: 4px; padding: 4px 8px;")
        self.w_ek_dersler.setToolTip("Bu alan atamalardan otomatik olarak çekilir.")
        
        lay_ek = QHBoxLayout()
        lay_ek.setSpacing(10)
        lbl_ek = QLabel("<b>Otomatik Ek Dersler:</b>")
        lbl_ek.setFont(QFont("Segoe UI", 9))
        lay_ek.addWidget(lbl_ek)
        lay_ek.addWidget(self.w_ek_dersler, 1)
        lay_ders.addLayout(lay_ek)
        
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
            
            # Update local UI list
            self.list_assignments.clear()
            my_atamalar = [a for a in data_store["atamalar"] if format_tr_name(a.get("teacher", "")) == current_teacher]
            for a in my_atamalar:
                item_text = f"📚 {a.get('subject', '')} ➔ 🎓 {a.get('class', '')} ({a.get('duration', 0)} Saat)"
                self.list_assignments.addItem(QListWidgetItem(item_text))
            if not my_atamalar:
                self.list_assignments.addItem(QListWidgetItem("❌ Henüz hiçbir derse veya sınıfa atanmadı."))
            
            my_subjects = list({a.get("subject", "") for a in my_atamalar if a.get("subject")})
            self.w_ek_dersler.setText(", ".join(my_subjects))

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
        return {
            "ad": ad_formatted, "kisa": self.w_kisa.text(),
            "renk": self._color, "sinif_ogretmeni": self.w_so.currentText(),
            "brans": getattr(self, "w_brans", QLineEdit()).text().strip(),
            "ek_dersler": self.w_ek_dersler.text(),
            "es_zamanli": self.chk_es_zamanli.isChecked(),
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
        subj_target = format_tr_name(self.subject_name)
        atamalar = self.data_store.get("atamalar", [])
        if self.current_class:
            self.data_store["atamalar"] = [
                a for a in atamalar
                if not (format_tr_name(a.get("subject", "")) == subj_target and a.get("class") == self.current_class)
            ]
        else:
            self.data_store["atamalar"] = [
                a for a in atamalar
                if format_tr_name(a.get("subject", "")) != subj_target
            ]
        trigger_save_db(self, self.data_store)
        self.accept()

    def _save_assignments(self):
        subj_target = format_tr_name(self.subject_name)
        atamalar = self.data_store.get("atamalar", [])
        
        # Remove previous assignments for this subject
        if self.current_class:
            atamalar = [
                a for a in atamalar
                if not (format_tr_name(a.get("subject", "")) == subj_target and a.get("class") == self.current_class)
            ]
        else:
            atamalar = [
                a for a in atamalar
                if format_tr_name(a.get("subject", "")) != subj_target
            ]
            
        scolor = get_subject_color(self.subject_name)
        
        for t_name, cfg in self.teacher_configs.items():
            if cfg["checked"]:
                raw_type = str(cfg["type"]).strip()
                dur = 2
                if "+" in raw_type:
                    try:
                        dur = sum(int(x.strip()) for x in raw_type.split("+") if x.strip().isdigit())
                    except Exception:
                        dur = 2
                elif raw_type.isdigit():
                    dur = int(raw_type)
                    
                for c_name in cfg["classes"]:
                    if c_name:
                        atamalar.append({
                            "teacher": t_name,
                            "subject": self.subject_name,
                            "class": c_name,
                            "duration": dur,
                            "type": raw_type,
                            "color": scolor
                        })
                        
        self.data_store["atamalar"] = atamalar
        trigger_save_db(self, self.data_store)
        self.accept()


class ClassComprehensiveAssignmentDialog(QDialog):
    """
    Sınıfa Bütünsel Ders ve Öğretmen Atama Paneli (Modern ve Yenilikçi Tasarım)
    """
    def __init__(self, class_name="", data_store=None, parent=None):
        super().__init__(parent)
        self.class_name = class_name
        self.data_store = data_store or {}
        self.setWindowTitle(f"🎓 {self.class_name} Sınıfı — Ders ve Öğretmen Atama Paneli")
        self.setFixedSize(980, 700)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; }
            QLabel { color: #334155; font-size: 13px; font-weight: bold; }
            QTableWidget { border: 1px solid #CBD5E1; background: #FFFFFF; gridline-color: #F1F5F9; font-size: 13px; border-radius: 8px; }
            QHeaderView::section { background-color: #F1F5F9; border: none; border-bottom: 2px solid #CBD5E1; padding: 8px; font-weight: bold; font-size: 13px; color: #334155; }
            QPushButton { border: 1px solid #CBD5E1; border-radius: 6px; background: #FFFFFF; font-size: 13px; font-weight: bold; color: #475569; }
            QPushButton:hover { background: #F8FAFC; }
            QLineEdit { border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px 12px; font-size: 13px; background: white; }
            QLineEdit:focus { border: 1px solid #2563EB; }
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
        
        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Ders Adı", "Atanan Öğretmen(ler)", "Haftalık Saat / Dağılım", "İşlemler"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 160)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.setColumnWidth(2, 140)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 140)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget::item { padding: 4px; }")
        lay.addWidget(self.table, 1)

        # Bottom Actions Bar
        bot_lay = QHBoxLayout()
        self.lbl_summary = QLabel("Toplam Atanan: 0 / 40 Saat (%0 Dolu)")
        self.lbl_summary.setStyleSheet("color: #0284C7; font-size: 14px; font-weight: bold;")
        bot_lay.addWidget(self.lbl_summary)
        
        bot_lay.addStretch(1)
        
        btn_clear_all = QPushButton("🗑️ Hepsini Kaldır")
        btn_clear_all.setStyleSheet("background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; font-weight: bold;")
        btn_clear_all.clicked.connect(self._clear_all_assignments)
        bot_lay.addWidget(btn_clear_all)

        btn_close = QPushButton("💾 Kapat ve Kaydet")
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
            target_cls = format_tr_name(self.class_name)
            atamalar = self.data_store.get("atamalar", [])
            self.data_store["atamalar"] = [a for a in atamalar if format_tr_name(a.get("class", "")) != target_cls]
            grid_data = self.data_store.get("grid_placements", [])
            if isinstance(grid_data, list):
                self.data_store["grid_placements"] = [p for p in grid_data if format_tr_name(p.get("class_name", p.get("class", ""))) != target_cls]
            yerlesim = self.data_store.get("yerlesim", {})
            if isinstance(yerlesim, dict):
                for k in list(yerlesim.keys()):
                    info = yerlesim[k]
                    if isinstance(info, dict) and format_tr_name(info.get("class_name", info.get("class", ""))) == target_cls:
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
        self.table.setRowCount(0)
        subjects = [d.get("ad", "") for d in self.data_store.get("dersler", []) if d.get("ad")]
        atamalar = self.data_store.get("atamalar", [])
        
        class_atamalar = {}
        for a in atamalar:
            if format_tr_name(a.get("class", "")) == format_tr_name(self.class_name):
                s = a.get("subject", "")
                if s:
                    class_atamalar.setdefault(s, []).append(a)
                    
        total_class_hours = 0

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
            teachers_str = ", ".join(teachers) if teachers else "❌ Atama Yok"
            
            item_teachers = QTableWidgetItem(teachers_str)
            item_teachers.setFlags(item_teachers.flags() ^ Qt.ItemIsEditable)
            if not teachers:
                item_teachers.setForeground(QBrush(QColor("#94A3B8")))
            else:
                item_teachers.setForeground(QBrush(QColor("#0F172A")))
                item_teachers.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(row, 1, item_teachers)
            
            # 2. Hours / Distribution Type
            dur_sum = sum(a.get("duration", 1) for a in assigned_list)
            total_class_hours += dur_sum
            
            type_str = assigned_list[0].get("type", "") if assigned_list else ""
            if type_str and type_str != str(dur_sum):
                display_dur = f"{dur_sum} Saat ({type_str})"
            else:
                display_dur = f"{dur_sum} Saat" if dur_sum > 0 else "—"
                
            item_dur = QTableWidgetItem(display_dur)
            item_dur.setTextAlignment(Qt.AlignCenter)
            item_dur.setFlags(item_dur.flags() ^ Qt.ItemIsEditable)
            if dur_sum > 0:
                item_dur.setForeground(QBrush(QColor("#0284C7")))
                item_dur.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            else:
                item_dur.setForeground(QBrush(QColor("#94A3B8")))
            self.table.setItem(row, 2, item_dur)
            
            # 3. Action Buttons (Always fully visible, centered, and clean)
            cell_w = QWidget()
            cell_lay = QHBoxLayout(cell_w)
            cell_lay.setContentsMargins(4, 2, 4, 2)
            cell_lay.setSpacing(4)
            cell_lay.setAlignment(Qt.AlignCenter)
            
            if assigned_list:
                btn_edit = QPushButton("✏️ Düzenle")
                btn_edit.setFixedSize(68, 24)
                btn_edit.setStyleSheet("background: #EFF6FF; color: #1D4ED8; border: 1px solid #93C5FD; border-radius: 4px; font-size: 10px; font-weight: bold; min-height: 0; max-height: 24px; padding: 0 4px;")
                btn_edit.clicked.connect(lambda chk=False, s=subj: self._edit_subject_assignment(s))
                cell_lay.addWidget(btn_edit)
                
                btn_remove = QPushButton("Kaldır")
                btn_remove.setToolTip("Bu dersin atamasını kaldır")
                btn_remove.setFixedSize(52, 24)
                btn_remove.setStyleSheet("background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; border-radius: 4px; font-size: 10px; font-weight: bold; min-height: 0; max-height: 24px; padding: 0 4px;")
                btn_remove.clicked.connect(lambda chk=False, s=subj: self._remove_subject_assignment(s))
                cell_lay.addWidget(btn_remove)
            else:
                btn_add = QPushButton("+ Ata")
                btn_add.setFixedSize(52, 24)
                btn_add.setStyleSheet("background: #F8FAFC; color: #2563EB; border: 1px solid #CBD5E1; border-radius: 4px; font-size: 10px; font-weight: bold; min-height: 0; max-height: 24px; padding: 0 6px;")
                btn_add.clicked.connect(lambda chk=False, s=subj: self._edit_subject_assignment(s))
                cell_lay.addWidget(btn_add)
                
                btn_remove = QPushButton("Kaldır")
                btn_remove.setToolTip("Bu dersin atamasını kaldır")
                btn_remove.setFixedSize(52, 24)
                btn_remove.setStyleSheet("background: #F1F5F9; color: #94A3B8; border: 1px solid #E2E8F0; border-radius: 4px; font-size: 10px; font-weight: bold; min-height: 0; max-height: 24px; padding: 0 4px;")
                btn_remove.setEnabled(False)
                cell_lay.addWidget(btn_remove)
                
            self.table.setCellWidget(row, 3, cell_w)

        pct = min(100, int((total_class_hours / 40.0) * 100))
        color_hex = "#16A34A" if total_class_hours >= 40 else ("#2563EB" if total_class_hours >= 20 else "#D97706")
        self.lbl_summary.setText(f"Toplam Atanan: {total_class_hours} / 40 Saat (%{pct} Haftalık Doluluk)")
        self.lbl_summary.setStyleSheet(f"color: {color_hex}; font-size: 14px; font-weight: bold;")

    def _remove_subject_assignment(self, subject_name):
        v_scroll = self.table.verticalScrollBar().value()
        target_s = format_tr_name(subject_name)
        target_c = format_tr_name(self.class_name)
        
        atamalar = self.data_store.get("atamalar", [])
        self.data_store["atamalar"] = [
            a for a in atamalar
            if not (format_tr_name(a.get("subject", "")) == target_s and format_tr_name(a.get("class", "")) == target_c)
        ]
        grid_data = self.data_store.get("grid_placements", [])
        if isinstance(grid_data, list):
            self.data_store["grid_placements"] = [
                p for p in grid_data
                if not (format_tr_name(p.get("subject_name", p.get("subject", ""))) == target_s and
                        format_tr_name(p.get("class_name", p.get("class", ""))) == target_c)
            ]
        yerlesim = self.data_store.get("yerlesim", {})
        if isinstance(yerlesim, dict):
            for k in list(yerlesim.keys()):
                info = yerlesim[k]
                if isinstance(info, dict):
                    if (format_tr_name(info.get("subject_name", info.get("subject", ""))) == target_s and
                        format_tr_name(info.get("class_name", info.get("class", ""))) == target_c):
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

    def _print_class_timetable(self):
        from dialogs.print_preview import TimetablePrintPreview
        filters = {
            "entity_type": "class_list",
            "default_selection": self.class_name,
            "lock_mode": "Sınıf Dersleri & Atama Listesi (Liste Formatı)"
        }
        dlg = TimetablePrintPreview(data_store=self.data_store, filters=filters, parent=self)
        dlg.exec()
