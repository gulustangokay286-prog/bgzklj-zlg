import os
import sys
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QListWidget, QScrollArea, QWidget, QFrame, QMessageBox
)
from PySide6.QtCore import Qt

# Resolve absolute paths properly whether running from script or PyInstaller EXE
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
DIALOGS_DATA = {}
STRINGS_DATA = []
STRING_MAP = {}

try:
    with open(os.path.join(DATA_DIR, "dialogs.json"), "r", encoding="utf-8") as f:
        DIALOGS_DATA = json.load(f)
    with open(os.path.join(DATA_DIR, "strings.json"), "r", encoding="utf-8") as f:
        STRINGS_DATA = json.load(f)
    STRING_MAP = {1000 + idx: s for idx, s in enumerate(STRINGS_DATA)}
except Exception as e:
    print(f"Error loading 2025 data: {e}")


def resolve_text(text_val):
    if not text_val:
        return ""
    text_str = str(text_val).strip()
    if text_str.startswith("#"):
        try:
            s_id = int(text_str[1:])
            if s_id in STRING_MAP:
                return STRING_MAP[s_id]
        except ValueError:
            pass
    return text_str


class ExtractedDialog(QDialog):
    """Dynamically builds native Qt windows from aSc 2025 Decompiled JSON data."""
    def __init__(self, dlg_id, dlg_info, parent=None):
        super().__init__(parent)
        self.dlg_id = dlg_id
        
        raw_title = dlg_info.get("title", "")
        title = resolve_text(raw_title) or f"Pencere #{dlg_id}"
        self.setWindowTitle(f"{title}")
        
        rect = dlg_info.get("rect", {})
        raw_w = rect.get("w", 300)
        raw_y = rect.get("y", 0)
        
        w = raw_w * 2 if raw_w > 50 else 550
        h = raw_y * 2 if raw_y > 50 else 400
        self.resize(max(w, 450), max(h, 350))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header banner (Modern)
        header = QFrame(self)
        header.setStyleSheet("background: #0078D7; color: white;")
        header.setFixedHeight(40)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(15, 0, 15, 0)
        h_label = QLabel(f"<b>{title}</b>", header)
        h_label.setStyleSheet("font-size: 14px; color: white;")
        h_layout.addWidget(h_label)
        layout.addWidget(header)
        
        # Content scroll area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        scroll_content.setMinimumSize(w - 40, h - 100)
        
        controls = dlg_info.get("controls", [])
        for ctrl in controls:
            c_class = str(ctrl.get("class", ""))
            raw_text = ctrl.get("text", "")
            text = resolve_text(raw_text)
            
            r = ctrl.get("rect", {})
            cx, cy = r.get("x", 0)*2, r.get("y", 0)*2
            cw, ch = r.get("w", 50)*2, r.get("h", 14)*2
            
            if cw <= 0: cw = 100
            if ch <= 0: ch = 25
            
            if "128" in c_class or "BUTTON" in c_class.upper():
                btn = QPushButton(text or "Tamam", scroll_content)
                btn.setGeometry(cx, cy, max(cw, 80), max(ch, 28))
                if "Tamam" in text or "OK" in text.upper():
                    btn.clicked.connect(self.accept)
            elif "129" in c_class or "EDIT" in c_class.upper():
                edit = QLineEdit(scroll_content)
                edit.setGeometry(cx, cy, max(cw, 120), max(ch, 26))
            elif "133" in c_class or "COMBOBOX" in c_class.upper():
                cb = QComboBox(scroll_content)
                if text: cb.addItem(text)
                cb.setGeometry(cx, cy, max(cw, 120), max(ch, 26))
            elif "131" in c_class or "LISTBOX" in c_class.upper():
                lw = QListWidget(scroll_content)
                if text: lw.addItem(text)
                lw.setGeometry(cx, cy, max(cw, 150), max(ch, 80))
            else:
                if text:
                    lbl = QLabel(text, scroll_content)
                    lbl.setWordWrap(True)
                    lbl.setGeometry(cx, cy, max(cw, 120), max(ch, 20))
                    
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Bottom Button Bar
        btn_box = QHBoxLayout()
        btn_box.setContentsMargins(15, 10, 15, 10)
        btn_box.addStretch()
        ok_btn = QPushButton("Tamam", self)
        ok_btn.setStyleSheet("background: #0078D7; color: white; padding: 6px 20px; font-weight: bold; border-radius: 4px;")
        ok_btn.clicked.connect(self.accept)
        close_btn = QPushButton("İptal", self)
        close_btn.setStyleSheet("padding: 6px 20px; border-radius: 4px; border: 1px solid #CCC;")
        close_btn.clicked.connect(self.reject)
        btn_box.addWidget(ok_btn)
        btn_box.addWidget(close_btn)
        layout.addLayout(btn_box)

def open_extracted_dialog(dlg_id, parent):
    if not DIALOGS_DATA:
        QMessageBox.warning(parent, "Veri Hatası", "2025 Decompile verileri yüklenemedi (dialogs.json eksik).")
        return
        
    dlg_info = DIALOGS_DATA.get(str(dlg_id))
    if dlg_info:
        dlg = ExtractedDialog(dlg_id, dlg_info, parent)
        dlg.exec()
    else:
        QMessageBox.warning(parent, "Uyarı", f"Orijinal {dlg_id} ID'li pencere decompile datasında bulunamadı!")
