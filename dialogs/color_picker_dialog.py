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
        self.setFixedSize(40, 40)
        self.setCursor(Qt.PointingHandCursor)
        self.is_selected = False
        self.update_style()

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_style()

    def update_style(self):
        border = "2.5px solid #0071E3" if self.is_selected else "1px solid rgba(0,0,0,0.14)"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.hex_color};
                border: {border};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                border: 2px solid #0071E3;
            }}
        """)


def normalize_tr(s: str) -> str:
    if not s:
        return ""
    s_str = str(s).strip().replace("🔒", "").strip()
    if " - " in s_str:
        s_str = s_str.split(" - ")[-1].strip()
    tr_map = str.maketrans({
        'i': 'İ', 'ı': 'I', 'ç': 'Ç', 'ğ': 'Ğ', 'ö': 'Ö', 'ş': 'Ş', 'ü': 'Ü'
    })
    return s_str.translate(tr_map).upper()


def extract_stem_and_digits(s: str):
    import re
    s_norm = normalize_tr(s)
    alphanumeric = "".join(c for c in s_norm if c.isalnum())
    m = re.search(r'(\d+)$', alphanumeric)
    if m:
        digits = m.group(1)
        stem = alphanumeric[:m.start()]
    else:
        digits = ""
        stem = alphanumeric
    return stem, digits


def normalize_subject_name(s: str) -> str:
    stem, digits = extract_stem_and_digits(s)
    return stem + digits


ACRONYM_MAP = {
    "TÜRK DİLİ VE EDEBİYATI": "TDE",
    "TURK DILI VE EDEBIYATI": "TDE",
    "TÜRKÇE": "TÜR",
    "TURKCE": "TÜR",
    "EDEBİYAT": "EDEB",
    "EDEBIYAT": "EDEB",
    "GÖRSEL SANATLAR": "GÖRSEL",
    "GORSEL SANATLAR": "GÖRSEL",
    "DİN KÜLTÜRÜ VE AHLAK BİLGİSİ": "DİN",
    "DIN KULTURU VE AHLAK BILGISI": "DİN",
    "DİN KÜLTÜRÜ": "DİN",
    "DIN KULTURU": "DİN",
    "BEDEN EĞİTİMİ VE SPOR": "BEDEN",
    "BEDEN EGITIMI VE SPOR": "BEDEN",
    "BEDEN EĞİTİMİ": "BEDEN",
    "BEDEN EGITIMI": "BEDEN",
    "REHBERLİK VE YÖNLENDİRME": "REHBER",
    "REHBERLIK VE YONLENDIRME": "REHBER",
    "REHBERLİK": "REHBER",
    "REHBERLIK": "REHBER",
    "FELSEFE": "FELS",
    "MATEMATİK": "MAT",
    "MATEMATIK": "MAT",
    "GEOMETRİ": "GEOM",
    "GEOMETRI": "GEOM",
    "COĞRAFYA": "COĞRAF",
    "COGRAFYA": "COĞRAF",
    "BİYOLOJİ": "BİYO",
    "BIYOLOJI": "BİYO",
    "KİMYA": "KİM",
    "KIMYA": "KİM",
    "FİZİK": "FİZ",
    "FIZIK": "FİZ",
    "İNGİLİZCE": "İNG",
    "INGILIZCE": "İNG",
    "ALMANCA": "ALM",
    "FRANSIZCA": "FRAN",
    "TARİH": "TAR",
    "TARIH": "TAR",
}


def normalize_subject_match(s1, s2) -> bool:
    if not s1 or not s2:
        return False
    str1 = str(s1).strip().replace("🔒", "").strip()
    str2 = str(s2).strip().replace("🔒", "").strip()
    if str1.upper() == str2.upper():
        return True

    from auto_scheduler import normalize_clean
    n1 = normalize_clean(str1)
    n2 = normalize_clean(str2)
    if n1 == n2 and n1:
        return True

    # Check known acronyms & reverse lookup
    for full_name, abbr in ACRONYM_MAP.items():
        fn_norm = normalize_clean(full_name)
        ab_norm = normalize_clean(abbr)
        if (n1 == fn_norm or fn_norm in n1 or n1.startswith(fn_norm)) and (n2 == ab_norm or ab_norm in n2 or n2.startswith(ab_norm)):
            return True
        if (n2 == fn_norm or fn_norm in n2 or n2.startswith(fn_norm)) and (n1 == ab_norm or ab_norm in n1 or n1.startswith(ab_norm)):
            return True

    # Substring containment (e.g. "biyoloji" in "biyoloji9", "mat" in "matematik")
    if n1 in n2 or n2 in n1:
        return True

    # Exact stem / letter-only match
    s1_letters = "".join(c for c in n1 if c.isalpha())
    s2_letters = "".join(c for c in n2 if c.isalpha())
    if s1_letters and s2_letters:
        if s1_letters == s2_letters:
            return True
        if len(s1_letters) >= 3 and len(s2_letters) >= 3:
            if s1_letters[:3] == s2_letters[:3]:
                return True
            if s1_letters.startswith(s2_letters) or s2_letters.startswith(s1_letters):
                return True

    return False


def resolve_subject_color(subject_name: str, data_store: dict = None) -> str:
    """Returns the persistent color for a subject by inspecting data_store."""
    if not subject_name:
        return "#2563EB"
        
    s_clean = str(subject_name).replace("🔒", "").strip()
    if data_store and isinstance(data_store, dict):
        # 1. Check dersler (highest priority for user configured subject colors)
        for d in data_store.get("dersler", []):
            if normalize_subject_match(d.get("ad"), s_clean) or normalize_subject_match(d.get("kisa"), s_clean):
                c = d.get("color") or d.get("renk")
                if c and QColor(c).isValid() and str(c).upper() not in ("#FFFFFF", "#000000", "#C0C0C0", "#B4B4B8", "#D0D0D0", ""):
                    return str(c).upper()
                    
        # 2. Check atamalar
        for a in data_store.get("atamalar", []):
            if normalize_subject_match(a.get("subject"), s_clean) or normalize_subject_match(a.get("ders"), s_clean):
                c = a.get("color") or a.get("renk")
                if c and QColor(c).isValid() and str(c).upper() not in ("#FFFFFF", "#000000", "#C0C0C0", "#B4B4B8", "#D0D0D0", ""):
                    return str(c).upper()
                    
        # 3. Check grid_placements
        for p in data_store.get("grid_placements", []):
            if normalize_subject_match(p.get("subject_name") or p.get("subject"), s_clean):
                c = p.get("color")
                if c and QColor(c).isValid() and str(c).upper() not in ("#FFFFFF", "#000000", "#C0C0C0", "#B4B4B8", "#D0D0D0", ""):
                    return str(c).upper()

        # 4. Check yerlesim
        if isinstance(data_store.get("yerlesim"), dict):
            for k, v in data_store["yerlesim"].items():
                if isinstance(v, dict) and normalize_subject_match(v.get("subject_name") or v.get("subject"), s_clean):
                    c = v.get("color")
                    if c and QColor(c).isValid() and str(c).upper() not in ("#FFFFFF", "#000000", "#C0C0C0", "#B4B4B8", "#D0D0D0", ""):
                        return str(c).upper()

    # Deterministic curated fallback based on root stem
    from auto_scheduler import normalize_clean
    key = normalize_clean(s_clean) or s_clean
    hash_val = sum(ord(ch) * (i + 1) for i, ch in enumerate(key))
    return CURATED_PALETTE[hash_val % len(CURATED_PALETTE)]


def update_subject_color_globally(widget_or_parent, data_store: dict, subject_name: str, new_hex: str):
    """
    Globally updates and immediately persists subject color across data_store and UI.
    """
    if not subject_name or not new_hex:
        return
        
    new_hex = str(new_hex).upper().strip()
    
    # Invalidate cell color caches
    try:
        from timetable_grid import clear_cell_color_cache
        clear_cell_color_cache()
    except Exception:
        pass

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

    if not win:
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for top in app.topLevelWidgets():
                    if hasattr(top, "data_store") and top.data_store:
                        win = top
                        break
        except Exception:
            pass

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
            if normalize_subject_match(a.get("subject"), subject_name) or normalize_subject_match(a.get("ders"), subject_name):
                a["color"] = new_hex
                a["renk"] = new_hex
                
        # 3. Update grid_placements
        for gp in data_store.get("grid_placements", []):
            if normalize_subject_match(gp.get("subject_name") or gp.get("subject"), subject_name):
                gp["color"] = new_hex
                
        # 4. Update yerlesim dict
        if isinstance(data_store.get("yerlesim"), dict):
            for k, v in data_store["yerlesim"].items():
                if isinstance(v, dict) and normalize_subject_match(v.get("subject_name") or v.get("subject"), subject_name):
                    v["color"] = new_hex

        # 5. Update manual_unplaced_cards
        for mc in data_store.get("manual_unplaced_cards", []):
            if normalize_subject_match(mc.get("subject_name"), subject_name):
                mc["color"] = new_hex

        # 6. Update loose_unplaced_cards
        for lc in data_store.get("loose_unplaced_cards", []):
            if normalize_subject_match(lc.get("subject_name"), subject_name):
                lc["color"] = new_hex

    # 6. Locate grid widget
    grid = None
    if win and hasattr(win, "_grid"):
        grid = win._grid
    elif hasattr(widget_or_parent, "_grid"):
        grid = widget_or_parent._grid
    elif hasattr(widget_or_parent, "table") and hasattr(widget_or_parent, "_placed_lessons"):
        grid = widget_or_parent
    else:
        cur = widget_or_parent
        while cur is not None:
            if hasattr(cur, "table") and hasattr(cur, "_placed_lessons"):
                grid = cur
                break
            if hasattr(cur, "parent") and callable(cur.parent):
                cur = cur.parent()
            else:
                break

    # 7. Real-time UI update on grid
    if grid:
        if hasattr(grid, "_placed_lessons"):
            for (r, c), info in list(grid._placed_lessons.items()):
                if normalize_subject_match(info.get("subject_name"), subject_name):
                    info["color"] = new_hex
                    
        if hasattr(grid, "table"):
            for r in range(grid.table.rowCount()):
                for c in range(grid.table.columnCount()):
                    it = grid.table.item(r, c)
                    if it and it.text().strip():
                        clean_text = it.text().replace("🔒", "").strip()
                        if normalize_subject_match(clean_text, subject_name):
                            it.setBackground(QBrush(QColor(new_hex)))
                            lum = (0.299 * QColor(new_hex).red() + 0.587 * QColor(new_hex).green() + 0.114 * QColor(new_hex).blue())
                            it.setForeground(QBrush(Qt.white if lum < 140 else Qt.black))
                            
            grid.table.viewport().update()
            grid.table.update()
            
        if hasattr(grid, "info_color_box"):
            grid.info_color_box.setStyleSheet(f"background: {new_hex}; border: 1px solid rgba(0,0,0,0.15); border-radius: 5px;")
            
    # 8. Instantly update all DraggableLessonCard instances across ALL open widgets/docks in memory
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            for w in app.allWidgets():
                cls_name = w.__class__.__name__
                if cls_name == "DraggableLessonCard" or (hasattr(w, "subject_name") and hasattr(w, "color")):
                    s_card = getattr(w, "subject_name", "")
                    if s_card and normalize_subject_match(s_card, subject_name):
                        w.color = new_hex
                        if hasattr(w, "set_color"):
                            w.set_color(new_hex)
                        else:
                            w.update()
                            if hasattr(w, "repaint"):
                                w.repaint()
    except Exception:
        pass

    if win:
        if hasattr(win, "save_db"):
            win.save_db(sync_from_grid=False)
        if hasattr(win, "_refresh_tree"):
            win._refresh_tree()
        if hasattr(win, "_refresh_grid"):
            win._refresh_grid()
        if hasattr(win, "_refresh_unplaced_lessons"):
            win._refresh_unplaced_lessons()
    else:
        from database import trigger_save_db
        trigger_save_db(widget_or_parent, data_store or {})


class ModernColorPickerDialog(QDialog):
    """Modern, Sade ve Şık Renk Seçim Penceresi"""
    def __init__(self, current_color="#2563EB", title="Renk Seçimi", parent=None):
        super().__init__(parent)
        clean_title = str(title).replace("🎨", "").strip()
        self.setWindowTitle(clean_title)
        self.setFixedSize(400, 460)
        
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
            QDialog { background-color: #FFFFFF; font-family: .AppleSystemUIFont, SF Pro Text, -apple-system, Helvetica Neue, Segoe UI, sans-serif; }
            QLabel { color: #1E293B; font-size: 13px; font-weight: 600; }
            QLineEdit { border: 1px solid #CBD5E1; border-radius: 8px; padding: 6px 10px; font-size: 13px; font-weight: 600; color: #0F172A; }
            QLineEdit:focus { border: 1.5px solid #0071E3; }
        """)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)
        
        # Header
        lbl_title = QLabel("Canlı Renk Paleti")
        lbl_title.setStyleSheet("font-size: 15px; color: #0F172A; font-weight: 700;")
        lay.addWidget(lbl_title)
        
        # Swatch Palette Grid (4 rows x 7 cols) with generous X and Y spacing
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(12)
        
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
        preview_frame.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 6px;")
        prev_lay = QHBoxLayout(preview_frame)
        prev_lay.setContentsMargins(12, 10, 12, 10)
        prev_lay.setSpacing(12)
        
        self.preview_box = QLabel()
        self.preview_box.setFixedSize(38, 38)
        self._update_preview_box()
        prev_lay.addWidget(self.preview_box)
        
        v_hex = QVBoxLayout()
        v_hex.setSpacing(2)
        lbl_hex = QLabel("Renk Kodu (HEX):")
        lbl_hex.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 500;")
        v_hex.addWidget(lbl_hex)
        
        self.txt_hex = QLineEdit(self.selected_hex)
        self.txt_hex.setFixedWidth(110)
        self.txt_hex.textChanged.connect(self._on_hex_text_changed)
        v_hex.addWidget(self.txt_hex)
        prev_lay.addLayout(v_hex)
        
        prev_lay.addStretch(1)
        
        btn_custom = QPushButton("Özel Renk...")
        btn_custom.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #334155;
                border: 1px solid #CBD5E1;
                border-radius: 17px;
                padding: 0 16px;
                min-height: 34px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background: #F1F5F9; }
        """)
        btn_custom.clicked.connect(self._open_native_picker)
        prev_lay.addWidget(btn_custom)
        
        lay.addWidget(preview_frame)
        lay.addStretch(1)
        
        # Bottom Buttons (Capsule pills)
        bot_lay = QHBoxLayout()
        bot_lay.setSpacing(12)
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 19px;
                padding: 0 22px;
                min-height: 38px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { background: #F8FAFC; color: #0F172A; }
        """)
        btn_cancel.clicked.connect(self.reject)
        bot_lay.addWidget(btn_cancel)
        
        btn_apply = QPushButton("Seçilen Rengi Uygula")
        btn_apply.setStyleSheet("""
            QPushButton {
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 19px;
                padding: 0 26px;
                min-height: 38px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover { background: #0062C4; }
        """)
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
            border-radius: 8px;
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
    def pick_color(initial_color="#2563EB", parent=None, title="Renk Seçimi", data_store=None, subject_name=None):
        """Helper that opens dialog and optionally saves to data_store automatically."""
        clean_title = str(title).replace("🎨", "").strip()
        dlg = ModernColorPickerDialog(current_color=initial_color, title=clean_title, parent=parent)
        if dlg.exec() == QDialog.Accepted:
            chosen_hex = dlg.get_hex()
            if subject_name:
                update_subject_color_globally(parent or dlg, data_store, subject_name, chosen_hex)
            return dlg.get_color()
        return None
