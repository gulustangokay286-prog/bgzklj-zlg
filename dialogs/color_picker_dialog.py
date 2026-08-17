"""
dialogs/color_picker_dialog.py - Modern, Kusursuz ve Kalıcı Renk Seçim Paneli
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QWidget, QColorDialog
)
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PySide6.QtCore import Qt, QSize, Signal

CURATED_PALETTE = [
    "#4F75C2", "#388FB8", "#2E9AA6", "#2D9488", "#2E9970", "#43A066", "#73A034",
    "#B8831B", "#C27419", "#C9612A", "#C24242", "#C73859", "#C23E80", "#AD3EBA",
    "#8B4BC7", "#764FC2", "#5E56BF", "#5284D4", "#34A0B8", "#38AA80", "#7DBA2A",
    "#CFA123", "#D9762E", "#D45050", "#D64964", "#9B5CCF", "#64748B", "#475569"
]

class ColorSwatchButton(QPushButton):
    def __init__(self, hex_color: str, parent=None):
        super().__init__(parent)
        self.hex_color = hex_color
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)
        self.is_selected = False
        self.update_style()

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_style()

    def update_style(self):
        border = "3px solid #0F172A" if self.is_selected else "1px solid rgba(0,0,0,0.15)"
        scale_shadow = "box-shadow: 0 2px 4px rgba(0,0,0,0.2);" if self.is_selected else ""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.hex_color};
                border: {border};
                border-radius: 6px;
                {scale_shadow}
            }}
            QPushButton:hover {{
                border: 2px solid #2563EB;
            }}
        """)


def normalize_subject_name(s: str) -> str:
    if not s:
        return ""
    s_str = str(s).strip().upper().replace("🔒", "").strip()
    if " - " in s_str:
        parts = s_str.split(" - ")
        s_str = parts[-1].strip()
    tr_map = str.maketrans({
        'i': 'İ', 'ı': 'I', 'ş': 'Ş', 'ğ': 'Ğ', 'ü': 'Ü', 'ö': 'Ö', 'ç': 'Ç'
    })
    cleaned = s_str.translate(tr_map)
    return "".join(c for c in cleaned if c.isalnum())


def normalize_subject_match(s1, s2):
    if not s1 or not s2:
        return False
    n1 = normalize_subject_name(s1)
    n2 = normalize_subject_name(s2)
    if not n1 or not n2:
        return False
    if n1 == n2:
        return True
    if len(n1) >= 2 and len(n2) >= 2 and (n1.startswith(n2) or n2.startswith(n1)):
        return True
    return False


def resolve_subject_color(subject_name: str, data_store: dict = None) -> str:
    """Returns the persistent color for a subject by inspecting data_store."""
    if not subject_name:
        return "#2563EB"
    if data_store and isinstance(data_store, dict):
        # 1. Check dersler
        for d in data_store.get("dersler", []):
            if normalize_subject_match(d.get("ad"), subject_name) or normalize_subject_match(d.get("kisa"), subject_name):
                c = d.get("color") or d.get("renk")
                if c and QColor(c).isValid() and str(c).upper() not in ("#FFFFFF", "#000000", "#C0C0C0", "#B4B4B8", "#D0D0D0"):
                    return c
        # 2. Check atamalar
        for a in data_store.get("atamalar", []):
            if normalize_subject_match(a.get("subject"), subject_name):
                c = a.get("color")
                if c and QColor(c).isValid() and str(c).upper() not in ("#FFFFFF", "#000000", "#C0C0C0", "#B4B4B8", "#D0D0D0"):
                    return c
        # 3. Check grid_placements
        for p in data_store.get("grid_placements", []):
            if normalize_subject_match(p.get("subject_name") or p.get("subject"), subject_name):
                c = p.get("color")
                if c and QColor(c).isValid() and str(c).upper() not in ("#FFFFFF", "#000000", "#C0C0C0", "#B4B4B8", "#D0D0D0"):
                    return c
                    
    # Fallback to deterministic curated color
    hash_val = sum(ord(ch) * (i + 1) for i, ch in enumerate(subject_name.strip()))
    return CURATED_PALETTE[hash_val % len(CURATED_PALETTE)]


def update_subject_color_globally(widget_or_parent, data_store: dict, subject_name: str, new_hex: str):
    """
    Globally updates and immediately persists subject color across:
    1. data_store["dersler"]
    2. data_store["atamalar"]
    3. data_store["grid_placements"]
    4. data_store["yerlesim"]
    5. active grid _placed_lessons and table cells
    6. active unplaced dock cards
    7. writes to disk database file
    """
    if not subject_name or not new_hex:
        return
        
    win = None
    if hasattr(widget_or_parent, "window") and callable(widget_or_parent.window):
        candidate = widget_or_parent.window()
        if hasattr(candidate, "data_store"):
            win = candidate
            
    if not win:
        cur = widget_or_parent
        while cur is not None:
            if hasattr(cur, "data_store") and cur.data_store:
                win = cur
                break
            if hasattr(cur, "parent") and callable(cur.parent):
                cur = cur.parent()
            else:
                break

    if win and hasattr(win, "data_store") and win.data_store:
        data_store = win.data_store

    if not data_store:
        try:
            import json, os
            if os.path.exists("bgz_database.json"):
                with open("bgz_database.json", "r", encoding="utf-8") as f:
                    data_store = json.load(f)
        except Exception:
            data_store = {}

    if data_store:
        # 1. Update dersler
        found_in_dersler = False
        if "dersler" not in data_store:
            data_store["dersler"] = []
            
        for d in data_store.get("dersler", []):
            if normalize_subject_match(d.get("ad"), subject_name) or normalize_subject_match(d.get("kisa"), subject_name):
                d["renk"] = new_hex
                d["color"] = new_hex
                found_in_dersler = True
                
        if not found_in_dersler:
            data_store["dersler"].append({
                "ad": subject_name.strip(),
                "kisa": subject_name.strip()[:3].upper(),
                "renk": new_hex,
                "color": new_hex
            })
                
        # 2. Update atamalar
        for a in data_store.get("atamalar", []):
            if normalize_subject_match(a.get("subject"), subject_name):
                a["color"] = new_hex
                
        # 3. Update grid_placements
        for gp in data_store.get("grid_placements", []):
            if normalize_subject_match(gp.get("subject_name") or gp.get("subject"), subject_name):
                gp["color"] = new_hex
                
        # 4. Update yerlesim dict
        if isinstance(data_store.get("yerlesim"), dict):
            for k, v in data_store["yerlesim"].items():
                if isinstance(v, dict) and normalize_subject_match(v.get("subject_name") or v.get("subject"), subject_name):
                    v["color"] = new_hex

    # 5. Live UI update on main window grid
    if win and hasattr(win, "_grid"):
        grid = win._grid
        if hasattr(grid, "_placed_lessons"):
            for (r, c), info in list(grid._placed_lessons.items()):
                if normalize_subject_match(info.get("subject_name"), subject_name):
                    info["color"] = new_hex
                    item = grid.table.item(r, c)
                    if item:
                        item.setBackground(QBrush(QColor(new_hex)))
                        lum = (0.299 * QColor(new_hex).red() + 0.587 * QColor(new_hex).green() + 0.114 * QColor(new_hex).blue())
                        item.setForeground(QBrush(Qt.white if lum < 160 else Qt.black))
                        
        if hasattr(grid, "table"):
            for r in range(grid.table.rowCount()):
                for c in range(grid.table.columnCount()):
                    it = grid.table.item(r, c)
                    if it and it.text().strip():
                        clean_text = it.text().replace("🔒", "").strip()
                        if normalize_subject_match(clean_text, subject_name):
                            it.setBackground(QBrush(QColor(new_hex)))
            grid.table.viewport().update()
            grid.table.update()
            
        if hasattr(grid, "info_color_box"):
            grid.info_color_box.setStyleSheet(f"background: {new_hex}; border: 2px solid #334155; border-radius: 4px;")
            
        if hasattr(grid, "unplaced_dock") and hasattr(grid.unplaced_dock, "update_list"):
            grid.unplaced_dock.update_list(data_store)
            
        if hasattr(win, "save_db"):
            win.save_db(sync_from_grid=False)
        if hasattr(win, "_refresh_tree"):
            win._refresh_tree()
        if hasattr(win, "_refresh_grid"):
            win._refresh_grid()
    else:
        from database import trigger_save_db
        trigger_save_db(widget_or_parent, data_store or {})


class ModernColorPickerDialog(QDialog):
    """Modern, Sade ve Şık Renk Seçim Penceresi"""
    def __init__(self, current_color="#2563EB", title="Renk Seç", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(380, 420)
        
        # Parse initial color
        if isinstance(current_color, QColor):
            self.selected_hex = current_color.name().upper()
        elif isinstance(current_color, str) and current_color.startswith("#"):
            self.selected_hex = current_color.upper()
        else:
            self.selected_hex = "#2563EB"
            
        self.swatch_buttons = []
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #FFFFFF; font-family: system-ui, -apple-system, sans-serif; }
            QLabel { color: #1E293B; font-size: 13px; font-weight: bold; }
            QLineEdit { border: 1px solid #CBD5E1; border-radius: 6px; padding: 6px 10px; font-size: 13px; font-weight: bold; color: #0F172A; }
            QLineEdit:focus { border: 2px solid #2563EB; }
            QPushButton { min-height: 32px; border-radius: 6px; font-size: 13px; font-weight: bold; }
        """)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(14)
        
        # Header
        lbl_title = QLabel("🎨 Canlı Renk Paleti")
        lbl_title.setStyleSheet("font-size: 15px; color: #0F172A; font-weight: bold;")
        lay.addWidget(lbl_title)
        
        # Swatch Palette Grid (4 rows x 7 cols)
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        
        cols = 7
        for idx, hex_code in enumerate(CURATED_PALETTE):
            r = idx // cols
            c = idx % cols
            btn = ColorSwatchButton(hex_code, self)
            if hex_code.upper() == self.selected_hex:
                btn.set_selected(True)
            btn.clicked.connect(lambda _, h=hex_code, b=btn: self._select_color(h, b))
            grid.addWidget(btn, r, c)
            self.swatch_buttons.append(btn)
            
        lay.addWidget(grid_widget)
        
        # Live Preview & Custom Input Row
        preview_frame = QFrame()
        preview_frame.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 6px;")
        prev_lay = QHBoxLayout(preview_frame)
        prev_lay.setContentsMargins(10, 8, 10, 8)
        prev_lay.setSpacing(10)
        
        self.preview_box = QLabel()
        self.preview_box.setFixedSize(36, 36)
        self._update_preview_box()
        prev_lay.addWidget(self.preview_box)
        
        v_hex = QVBoxLayout()
        lbl_hex = QLabel("Renk Kodu (HEX):")
        lbl_hex.setStyleSheet("font-size: 11px; color: #64748B; font-weight: normal;")
        v_hex.addWidget(lbl_hex)
        
        self.txt_hex = QLineEdit(self.selected_hex)
        self.txt_hex.setFixedWidth(100)
        self.txt_hex.textChanged.connect(self._on_hex_text_changed)
        v_hex.addWidget(self.txt_hex)
        prev_lay.addLayout(v_hex)
        
        prev_lay.addStretch(1)
        
        btn_custom = QPushButton("Özel Renk...")
        btn_custom.setStyleSheet("background: #FFFFFF; color: #475569; border: 1px solid #CBD5E1; padding: 6px 12px;")
        btn_custom.clicked.connect(self._open_native_picker)
        prev_lay.addWidget(btn_custom)
        
        lay.addWidget(preview_frame)
        lay.addStretch(1)
        
        # Bottom Buttons
        bot_lay = QHBoxLayout()
        bot_lay.setSpacing(10)
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; padding: 6px 16px;")
        btn_cancel.clicked.connect(self.reject)
        bot_lay.addWidget(btn_cancel)
        
        btn_apply = QPushButton("Seçilen Rengi Uygula")
        btn_apply.setStyleSheet("background: #2563EB; color: #FFFFFF; border: none; padding: 6px 20px; font-weight: bold; border-radius: 6px;")
        btn_apply.clicked.connect(self.accept)
        bot_lay.addWidget(btn_apply)
        
        lay.addLayout(bot_lay)

    def _select_color(self, hex_code: str, active_btn=None):
        self.selected_hex = hex_code.upper()
        self.txt_hex.setText(self.selected_hex)
        for b in self.swatch_buttons:
            b.set_selected(b == active_btn or b.hex_color.upper() == self.selected_hex)
        self._update_preview_box()

    def _on_hex_text_changed(self, text: str):
        cleaned = text.strip().upper()
        if not cleaned.startswith("#"):
            cleaned = "#" + cleaned
        if len(cleaned) == 7 and QColor(cleaned).isValid():
            self.selected_hex = cleaned
            for b in self.swatch_buttons:
                b.set_selected(b.hex_color.upper() == self.selected_hex)
            self._update_preview_box()

    def _update_preview_box(self):
        c = QColor(self.selected_hex)
        lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
        border_col = "#000000" if lum > 200 else "rgba(0,0,0,0.15)"
        self.preview_box.setStyleSheet(f"""
            background-color: {self.selected_hex};
            border: 2px solid {border_col};
            border-radius: 6px;
        """)

    def _open_native_picker(self):
        dlg = QColorDialog(QColor(self.selected_hex), self)
        dlg.setWindowTitle("Özel Renk Seçimi")
        dlg.setStyleSheet("background: #FFFFFF; color: #000000;")
        if dlg.exec():
            c = dlg.selectedColor()
            if c.isValid():
                self._select_color(c.name())

    def get_color(self) -> QColor:
        return QColor(self.selected_hex)

    def get_hex(self) -> str:
        return self.selected_hex

    @staticmethod
    def pick_color(initial_color="#2563EB", parent=None, title="Renk Seç", data_store=None, subject_name=None):
        """Helper that opens dialog and optionally saves to data_store automatically."""
        dlg = ModernColorPickerDialog(current_color=initial_color, title=title, parent=parent)
        if dlg.exec() == QDialog.Accepted:
            chosen_hex = dlg.get_hex()
            if subject_name:
                update_subject_color_globally(parent or dlg, data_store, subject_name, chosen_hex)
            return dlg.get_color()
        return None
