"""
print_preview.py – Gelişmiş Baskı, Yazdırma ve PDF Dışa Aktarma Penceresi
Sınıf Haftalık Programı, Öğretmen Programı ve Fotoğraftaki Sınıf Dersleri / Atama Listesi Formatı Desteği
"""
import os
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QFileDialog, QMessageBox,
    QStyledItemDelegate, QStyleOptionViewItem, QFrame, QStyle, QScrollArea, QWidget
)
from PySide6.QtPrintSupport import QPrintPreviewWidget, QPrinter
from PySide6.QtGui import QPainter, QPen, QFont, QColor, QPageLayout, QBrush, QPageSize, QPainterPath, QPixmap, QIcon
from PySide6.QtCore import Qt, QRectF, QPointF, QSize, Signal
from auto_scheduler import matches_class
import lesson_hours
import bk_ui

SUBJECT_COLORS = [
    "#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#E91E63",
    "#00BCD4", "#8BC34A", "#FFC107", "#795548", "#607D8B",
    "#3F51B5", "#009688", "#E67E22", "#D32F2F", "#16A085"
]


def make_preview_icon(name: str, size: int = 14, color_hex: str = "#475569") -> QIcon:
    scale = 2
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(scale, scale)
    c = QColor(color_hex)
    
    if name == 'html':
        p.setPen(QPen(c, 1.3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(size * 0.34, size * 0.28)
        path.lineTo(size * 0.14, size * 0.5)
        path.lineTo(size * 0.34, size * 0.72)
        p.drawPath(path)
        p.drawLine(QPointF(size * 0.42, size * 0.74), QPointF(size * 0.58, size * 0.26))
        path2 = QPainterPath()
        path2.moveTo(size * 0.66, size * 0.28)
        path2.lineTo(size * 0.86, size * 0.5)
        path2.lineTo(size * 0.66, size * 0.72)
        p.drawPath(path2)
    elif name == 'pdf':
        p.setPen(QPen(c, 1.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(size * 0.22, size * 0.14)
        path.lineTo(size * 0.58, size * 0.14)
        path.lineTo(size * 0.78, size * 0.34)
        path.lineTo(size * 0.78, size * 0.86)
        path.lineTo(size * 0.22, size * 0.86)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(size * 0.58, size * 0.14), QPointF(size * 0.58, size * 0.34))
        p.drawLine(QPointF(size * 0.58, size * 0.34), QPointF(size * 0.78, size * 0.34))
        p.drawLine(QPointF(size * 0.36, size * 0.52), QPointF(size * 0.64, size * 0.52))
        p.drawLine(QPointF(size * 0.36, size * 0.68), QPointF(size * 0.54, size * 0.68))
    elif name == 'print':
        p.setPen(QPen(c, 1.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(size * 0.16, size * 0.34, size * 0.68, size * 0.36), 1.2, 1.2)
        p.drawLine(QPointF(size * 0.3, size * 0.34), QPointF(size * 0.3, size * 0.16))
        p.drawLine(QPointF(size * 0.3, size * 0.16), QPointF(size * 0.7, size * 0.16))
        p.drawLine(QPointF(size * 0.7, size * 0.16), QPointF(size * 0.7, size * 0.34))
        p.drawLine(QPointF(size * 0.3, size * 0.58), QPointF(size * 0.3, size * 0.84))
        p.drawLine(QPointF(size * 0.3, size * 0.84), QPointF(size * 0.7, size * 0.84))
        p.drawLine(QPointF(size * 0.7, size * 0.84), QPointF(size * 0.7, size * 0.58))
    p.end()
    return QIcon(pix)


class AppleComboBox(QPushButton):
    """
    Apple native single-click popover dropdown with curved corners and zero Cocoa glitching.
    Fully compatible with QComboBox API.
    """
    currentIndexChanged = Signal(int)
    currentTextChanged = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self._items = []
        self._current_index = -1
        self._menu = None
        
        self.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 0px 28px 0px 10px;
                text-align: left;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
                font-size: 11.5px;
                font-weight: 500;
                color: #0F172A;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                border-color: #94A3B8;
                background-color: #F8FAFC;
            }
            QPushButton:focus {
                border: 1.2px solid #0071E3;
                background-color: #FFFFFF;
            }
            QPushButton:disabled {
                background-color: #F1F5F9;
                border-color: #E2E8F0;
                color: #94A3B8;
            }
        """)
        self.clicked.connect(self.showPopup)

    def addItems(self, items):
        for item in items:
            self.addItem(item)

    def addItem(self, text, data=None):
        self._items.append({"text": str(text), "data": data})
        if self._current_index < 0:
            self.setCurrentIndex(0)
            
    def clear(self):
        self._items.clear()
        self._current_index = -1
        self.setText("")

    def count(self):
        return len(self._items)

    def currentText(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index]["text"]
        return ""

    def currentIndex(self):
        return self._current_index

    def setCurrentIndex(self, index):
        if 0 <= index < len(self._items):
            old_idx = self._current_index
            self._current_index = index
            text = self._items[index]["text"]
            self.setText(text.replace("&", "&&"))
            self.update()
            if old_idx != index:
                self.currentIndexChanged.emit(index)
                self.currentTextChanged.emit(text)
        elif index == -1:
            self._current_index = -1
            self.setText("")

    def setCurrentText(self, text):
        idx = self.findText(text)
        if idx >= 0:
            self.setCurrentIndex(idx)

    def findText(self, text):
        for i, item in enumerate(self._items):
            if item["text"] == text:
                return i
        return -1

    def itemText(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]["text"]
        return ""

    def itemData(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]["data"]
        return None

    def showPopup(self):
        if not self.isEnabled() or not self._items:
            return
        menu = bk_ui.HeroPopoverMenu(self)
        menu.card.setMinimumWidth(max(self.width(), 260))
        menu.card.setMaximumHeight(380)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 5px; margin: 0; }
            QScrollBar::handle:vertical { background: #CBD5E1; border-radius: 2.5px; min-height: 24px; }
            QScrollBar::handle:vertical:hover { background: #94A3B8; }
        """)
        
        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)
        
        for idx, item in enumerate(self._items):
            t = item["text"]
            is_selected = (idx == self._current_index)
            
            btn = QPushButton(t.replace("&", "&&"))
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            
            if is_selected:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #0071E3;
                        color: #FFFFFF;
                        border: none;
                        border-radius: 6px;
                        padding: 0 10px;
                        text-align: left;
                        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
                        font-size: 11.5px;
                        font-weight: 600;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        color: #0F172A;
                        border: none;
                        border-radius: 6px;
                        padding: 0 10px;
                        text-align: left;
                        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
                        font-size: 11.5px;
                        font-weight: 500;
                    }
                    QPushButton:hover {
                        background: #F1F5F9;
                    }
                """)
            btn.clicked.connect(lambda _, i=idx: (self.setCurrentIndex(i), menu.close()))
            lay.addWidget(btn)
            
        scroll.setWidget(container)
        menu.card_lay.addWidget(scroll)
        menu.popup_below(self, align="left", offset_y=4)
        self._menu = menu

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        cx = w - 12
        cy = h / 2.0
        
        is_open = bool(self._menu and self._menu.isVisible())
        color = QColor("#0071E3" if (self.hasFocus() or is_open) else "#64748B")
        pen = QPen(color, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        path = QPainterPath()
        if is_open:
            path.moveTo(cx - 3.2, cy + 1.6)
            path.lineTo(cx, cy - 1.8)
            path.lineTo(cx + 3.2, cy + 1.6)
        else:
            path.moveTo(cx - 3.2, cy - 1.8)
            path.lineTo(cx, cy + 1.6)
            path.lineTo(cx + 3.2, cy - 1.8)
            
        painter.drawPath(path)

def get_bell_times(data_store: dict, periods: int = 8, separator: str = "-") -> list:
    """
    Returns a list of formatted time strings (e.g. ['08:50-09:30', '09:40-10:20', ...])
    for periods 0..periods-1 by inspecting bell_schedule and all time configurations in data_store.
    """
    if not data_store or not isinstance(data_store, dict):
        data_store = {}
    settings = data_store.get("settings", {}) if isinstance(data_store.get("settings"), dict) else {}

    # 1. Check bell_schedule list
    schedule = (
        settings.get("bell_schedule")
        or data_store.get("bell_schedule")
        or data_store.get("bell_times")
        or settings.get("bell_times")
        or settings.get("zil_saatleri")
        or data_store.get("zil_saatleri")
    )
    
    out = [None] * periods
    if schedule and isinstance(schedule, list):
        for p_idx in range(min(periods, len(schedule))):
            item = schedule[p_idx]
            if isinstance(item, dict):
                s = str(item.get("start") or item.get("baslangic") or "").strip()
                e = str(item.get("end") or item.get("bitis") or "").strip()
                if s and e:
                    out[p_idx] = f"{s}{separator}{e}"
            elif isinstance(item, str) and "-" in item:
                out[p_idx] = item.replace(" - ", separator).replace(" ", "")

    # 2. Check dict representations (e.g. zil_programi)
    if any(x is None for x in out):
        bells = data_store.get("zil_programi") or settings.get("zil_saatleri")
        if isinstance(bells, dict):
            for p_idx in range(periods):
                if out[p_idx] is not None:
                    continue
                entry = bells.get(str(p_idx)) or bells.get(p_idx) or bells.get(str(p_idx + 1)) or bells.get(p_idx + 1)
                if isinstance(entry, dict):
                    s = str(entry.get("start") or entry.get("baslangic") or "").strip()
                    e = str(entry.get("end") or entry.get("bitis") or "").strip()
                    if s and e:
                        out[p_idx] = f"{s}{separator}{e}"

    # 3. Fill missing slots sequentially
    curr_h, curr_m = 8, 30
    first_valid = next((x for x in out if x is not None), None)
    if first_valid:
        try:
            start_part = first_valid.split(separator)[0].strip()
            if ":" in start_part:
                curr_h, curr_m = map(int, start_part.split(":")[:2])
        except Exception:
            curr_h, curr_m = 8, 30

    result = []
    for p_idx in range(periods):
        if out[p_idx]:
            result.append(out[p_idx])
            try:
                end_part = out[p_idx].split(separator)[1].strip()
                eh, em = map(int, end_part.split(":")[:2])
                tot_m = eh * 60 + em + 10  # 10 min break
                curr_h, curr_m = (tot_m // 60) % 24, tot_m % 60
            except Exception:
                pass
        else:
            s_str = f"{curr_h:02d}:{curr_m:02d}"
            tot_end = curr_h * 60 + curr_m + 40
            e_str = f"{(tot_end // 60) % 24:02d}:{tot_end % 60:02d}"
            result.append(f"{s_str}{separator}{e_str}")
            tot_next = tot_end + 10
            curr_h, curr_m = (tot_next // 60) % 24, tot_next % 60

    return result


def get_bell_times(data_store: dict, periods: int = 8, separator: str = "-") -> list:
    """
    Returns a list of formatted time strings (e.g. ['08:50-09:30', '09:40-10:20', ...])
    for periods 0..periods-1 by inspecting bell_schedule and all time configurations in data_store.
    """
    if not data_store or not isinstance(data_store, dict):
        data_store = {}
    settings = data_store.get("settings", {}) if isinstance(data_store.get("settings"), dict) else {}

    # 1. Check bell_schedule list
    schedule = (
        settings.get("bell_schedule")
        or data_store.get("bell_schedule")
        or data_store.get("bell_times")
        or settings.get("bell_times")
        or settings.get("zil_saatleri")
        or data_store.get("zil_saatleri")
    )
    
    out = [None] * periods
    if schedule and isinstance(schedule, list):
        for p_idx in range(min(periods, len(schedule))):
            item = schedule[p_idx]
            if isinstance(item, dict):
                s = str(item.get("start") or item.get("baslangic") or "").strip()
                e = str(item.get("end") or item.get("bitis") or "").strip()
                if s and e:
                    out[p_idx] = f"{s}{separator}{e}"
            elif isinstance(item, str) and "-" in item:
                out[p_idx] = item.replace(" - ", separator).replace(" ", "")

    # 2. Check dict representations (e.g. zil_programi)
    if any(x is None for x in out):
        bells = data_store.get("zil_programi") or settings.get("zil_saatleri")
        if isinstance(bells, dict):
            for p_idx in range(periods):
                if out[p_idx] is not None:
                    continue
                entry = bells.get(str(p_idx)) or bells.get(p_idx) or bells.get(str(p_idx + 1)) or bells.get(p_idx + 1)
                if isinstance(entry, dict):
                    s = str(entry.get("start") or entry.get("baslangic") or "").strip()
                    e = str(entry.get("end") or entry.get("bitis") or "").strip()
                    if s and e:
                        out[p_idx] = f"{s}{separator}{e}"

    # 3. Fill missing slots sequentially
    curr_h, curr_m = 8, 30
    first_valid = next((x for x in out if x is not None), None)
    if first_valid:
        try:
            start_part = first_valid.split(separator)[0].strip()
            if ":" in start_part:
                curr_h, curr_m = map(int, start_part.split(":")[:2])
        except Exception:
            curr_h, curr_m = 8, 30

    result = []
    for p_idx in range(periods):
        if out[p_idx]:
            result.append(out[p_idx])
            try:
                end_part = out[p_idx].split(separator)[1].strip()
                eh, em = map(int, end_part.split(":")[:2])
                tot_m = eh * 60 + em + 10  # 10 min break
                curr_h, curr_m = (tot_m // 60) % 24, tot_m % 60
            except Exception:
                pass
        else:
            s_str = f"{curr_h:02d}:{curr_m:02d}"
            tot_end = curr_h * 60 + curr_m + 40
            e_str = f"{(tot_end // 60) % 24:02d}:{tot_end % 60:02d}"
            result.append(f"{s_str}{separator}{e_str}")
            tot_next = tot_end + 10
            curr_h, curr_m = (tot_next // 60) % 24, tot_next % 60

    return result


def get_subject_color(subject_name: str, custom_color: str = None) -> str:
    if custom_color and custom_color not in ["#FFFFFF", "#C4C4F0", ""]:
        return custom_color
    if not subject_name:
        return "#2196F3"
    hash_val = sum(ord(c) for c in subject_name)
    return SUBJECT_COLORS[hash_val % len(SUBJECT_COLORS)]

def format_tr_name(val):
    if not val:
        return ""
    val = str(val).strip()
    return val.replace("i", "İ").replace("ı", "I").upper()

def make_font(size, bold=False):
    f = QFont("Segoe UI, Arial")
    f.setPixelSize(size)
    f.setBold(bold)
    return f

def get_subject_badge(subj_name, data_store=None):
    if not subj_name:
        return ""
        
    s_clean = str(subj_name).strip()
    
    # 1. If manual short code exists in data_store and is short (<= 5 chars), return it
    if data_store and "dersler" in data_store:
        for d in data_store["dersler"]:
            if d.get("ad", "").strip().lower() == s_clean.lower():
                kisa = (d.get("kisa") or "").strip().upper()
                if kisa and len(kisa) <= 5 and kisa.lower() != d.get("ad", "").strip().lower():
                    return kisa

    import re
    # Extract trailing number if exists (e.g. "Matematik 1" -> "MAT 1")
    m = re.match(r'^(.*?)\s*(\d+)$', s_clean)
    base_name = m.group(1).strip() if m else s_clean
    num_str = f" {m.group(2)}" if m else ""
    
    tr_map = str.maketrans({'i': 'İ', 'ı': 'I', 'ç': 'Ç', 'ğ': 'Ğ', 'ö': 'Ö', 'ş': 'Ş', 'ü': 'Ü'})
    base_up = base_name.translate(tr_map).upper()
    
    STANDARDS = [
        ("MATEMATİK", "MAT"), ("MATEMATIK", "MAT"), ("MATE", "MAT"), ("MAT", "MAT"),
        ("GEOMETRİ", "GEOMETRİ"), ("GEOMETRI", "GEOMETRİ"), ("GEOM", "GEOMETRİ"), ("GEO", "GEOMETRİ"),
        ("COĞRAFYA", "COĞRAFYA"), ("COGRAFYA", "COĞRAFYA"), ("COĞRAF", "COĞRAFYA"), ("COĞ", "COĞRAFYA"), ("COG", "COĞRAFYA"),
        ("BEDEN EĞİTİMİ VE SPOR", "BEDEN"), ("BEDEN EĞİTİMİ", "BEDEN"), ("BEDEN", "BEDEN"), ("BED", "BEDEN"),
        ("FİZİK", "FİZİK"), ("FIZIK", "FİZİK"), ("FİZ", "FİZİK"), ("FIZ", "FİZİK"),
        ("KİMYA", "KİMYA"), ("KIMYA", "KİMYA"), ("KİM", "KİMYA"), ("KIM", "KİMYA"),
        ("BİYOLOJİ", "BİYO"), ("BIYOLOJI", "BİYO"), ("BİYO", "BİYO"), ("BIYO", "BİYO"), ("BİY", "BİYO"), ("BIY", "BİYO"),
        ("TÜRK DİLİ VE EDEBİYATI", "EDEBİYAT"), ("EDEBİYAT", "EDEBİYAT"), ("EDEBIYAT", "EDEBİYAT"), ("TÜRKÇE", "TÜRKÇE"), ("TURKCE", "TÜRKÇE"), ("TRK", "TÜRKÇE"),
        ("TARİH", "TARİH"), ("TARIH", "TARİH"), ("TAR", "TARİH"),
        ("DİN KÜLTÜRÜ VE AHLAK BİLGİSİ", "DİN"), ("DİN KÜLTÜRÜ", "DİN"), ("DİN", "DİN"), ("DIN", "DİN"),
        ("FELSEFE", "FELSEFE"), ("FELS", "FELSEFE"), ("FEL", "FELSEFE"),
        ("İNGİLİZCE", "İNGİLİZCE"), ("INGILIZCE", "İNGİLİZCE"), ("İNG", "İNGİLİZCE"), ("ING", "İNGİLİZCE"),
        ("ALMANCA", "ALMANCA"), ("ALM", "ALMANCA"),
        ("GÖRSEL SANATLAR", "GÖRSEL"), ("GÖRSEL", "GÖRSEL"), ("RESİM", "GÖRSEL"), ("GÖR", "GÖRSEL"), ("GOR", "GÖRSEL"),
        ("MÜZİK", "MÜZİK"), ("MUZIK", "MÜZİK"), ("MÜZ", "MÜZİK"), ("MUZ", "MÜZİK"),
        ("REHBERLİK", "REHBERLİK"), ("REHBERLIK", "REHBERLİK"), ("REH", "REHBERLİK"),
        ("PARAGRAF", "PARAGRAF"), ("PRG", "PARAGRAF"), ("PAR", "PARAGRAF")
    ]
    
    for k, v in STANDARDS:
        if base_up == k or base_up.startswith(k):
            return f"{v}{num_str}".strip()
            
    # Fallback to alphanumeric prefix
    clean_alpha = "".join(c for c in base_up if c.isalnum())
    return f"{clean_alpha[:5]}{num_str}".strip()

def format_teacher_display_name(t_name, data_store=None):
    if not t_name or t_name in ["—", "Atanmadı", "❌ Atama Yok"]:
        return "—"
    
    t_clean = str(t_name).strip()
    
    # Check if data_store has teacher with this name
    if data_store and "ogretmenler" in data_store:
        for t in data_store["ogretmenler"]:
            ad = t.get("ad", "").strip()
            kisa = t.get("kisa", "").strip()
            if ad.lower() == t_clean.lower() or kisa.lower() == t_clean.lower() or ad.lower().startswith(t_clean.lower()):
                if kisa and "." in kisa and len(kisa.split(".")[0]) <= 3:
                    return kisa.upper()
                parts = ad.split()
                if len(parts) >= 2:
                    first_initial = parts[0][0].upper()
                    last_name = " ".join(parts[1:]).upper()
                    return f"{first_initial}. {last_name}"
                elif len(parts) == 1:
                    return f"{parts[0][0].upper()}. {parts[0].upper()}"

    # If t_clean already has format "X. SOYAD" (e.g. "S. ÖZKAN")
    if "." in t_clean and len(t_clean.split(".")) == 2:
        p1, p2 = t_clean.split(".")
        if len(p1.strip()) <= 3:
            return f"{p1.strip().upper()}. {p2.strip().upper()}"
            
    # Generic format: split into words
    parts = t_clean.split()
    if len(parts) >= 2:
        first_initial = parts[0][0].upper()
        last_name = " ".join(parts[1:]).upper()
        return f"{first_initial}. {last_name}"
    elif len(parts) == 1:
        w = parts[0].upper()
        trunc_map = {
            "MESU": "M. MESUT", "MESUT": "M. MESUT",
            "CEYL": "C. CEYLAN", "CEYLAN": "C. CEYLAN",
            "RASI": "R. RASİM", "RASİM": "R. RASİM", "RASİ": "R. RASİM",
            "ÖZGE": "Ö. ÖZGE", "OZGE": "Ö. ÖZGE",
            "HAKAN": "H. BİLİR"
        }
        if w in trunc_map:
            return trunc_map[w]
        return f"{w[0]}. {w}"
        
    return t_clean.upper()

def draw_class_avatar_icon(painter, x, y):
    painter.save()
    painter.setPen(Qt.NoPen)
    # Background silhouette
    painter.setBrush(QBrush(QColor("#94A3B8")))
    painter.drawEllipse(QRectF(x + 14, y + 2, 13, 13))
    painter.drawRoundedRect(QRectF(x + 10, y + 15, 20, 11), 4, 4)
    # Foreground silhouette
    painter.setBrush(QBrush(QColor("#64748B")))
    painter.drawEllipse(QRectF(x + 4, y + 6, 14, 14))
    painter.drawRoundedRect(QRectF(x, y + 20, 22, 12), 4, 4)
    painter.restore()

def _chunk_classes(classes_list, max_len=36, max_count=4):
    chunks = []
    current_chunk = []
    current_len = 0
    for c in classes_list:
        c_str = str(c).strip()
        add_len = len(c_str) + (2 if current_chunk else 0)
        if current_chunk and (current_len + add_len > max_len or len(current_chunk) >= max_count):
            chunks.append(current_chunk)
            current_chunk = [c_str]
            current_len = len(c_str)
        else:
            current_chunk.append(c_str)
            current_len += add_len
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def _group_teacher_atamalar_by_subject(atamalar):
    grouped = {}
    for a in atamalar:
        subj = str(a.get("ders") or a.get("subject", "")).strip()
        if not subj:
            continue
        if subj not in grouped:
            grouped[subj] = {
                "subject": subj,
                "classes": [],
                "duration": 0,
                "types": [],
                "color": a.get("renk") or a.get("color"),
                "is_combined": False
            }
        cls_str = str(a.get("sinif") or a.get("class", "")).strip()
        if a.get("is_combined") or "+" in cls_str or "," in cls_str or "&" in cls_str:
            grouped[subj]["is_combined"] = True
            combs = a.get("combined_classes") or [c.strip() for c in cls_str.replace("&", "+").replace(",", "+").split("+") if c.strip()]
            for cc in combs:
                if cc and cc not in grouped[subj]["classes"]:
                    grouped[subj]["classes"].append(cc)
        else:
            if cls_str and cls_str not in grouped[subj]["classes"]:
                grouped[subj]["classes"].append(cls_str)
                
        # Saat, ekranlarla ayni kaynaktan (lesson_hours): eski ders_sayisi alani
        # sinif ekranindan yapilan bir degisiklikten sonra bayat kalabiliyor ve
        # basilan ogretmen raporu sinif raporundan az saat gosteriyordu.
        grouped[subj]["duration"] += lesson_hours.hours(a) or 1
        typ = lesson_hours.type_str(a)
        if typ and typ not in grouped[subj]["types"]:
            grouped[subj]["types"].append(typ)
            
    res = []
    for subj, g in grouped.items():
        cls_chunks = _chunk_classes(g["classes"])
        if not cls_chunks:
            cls_chunks = [[]]
            
        for chunk_idx, c_chunk in enumerate(cls_chunks):
            if chunk_idx == 0:
                res.append({
                    "subject": subj,
                    "class": ", ".join(c_chunk) if c_chunk else "—",
                    "duration": g["duration"],
                    "type": ", ".join(g["types"]) if g["types"] else str(g["duration"]),
                    "color": g["color"],
                    "is_combined": g["is_combined"],
                    "is_continuation": False
                })
            else:
                res.append({
                    "subject": f"{subj} (Devam)",
                    "class": ", ".join(c_chunk),
                    "duration": "—",
                    "type": "—",
                    "color": g["color"],
                    "is_combined": g["is_combined"],
                    "is_continuation": True
                })
    return res


class TimetablePrintPreview(QDialog):
    def __init__(self, data_store=None, placed_lessons=None, filters=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Baskı Ön İzleme ve PDF Raporu")
        self.resize(1050, 780)
        
        self.data_store = data_store or {}
        self.placed_lessons = placed_lessons or {}
        self.filters = filters or {}

        self.filtered_classes = self.data_store.get("siniflar", [])
        self.filtered_teachers = self.data_store.get("ogretmenler", [])
        
        if self.filters.get("classes"):
            self.filtered_classes = [c for c in self.filtered_classes if c.get("ad") in self.filters.get("classes")]
        if self.filters.get("teachers"):
            self.filtered_teachers = [t for t in self.filtered_teachers if t.get("ad") in self.filters.get("teachers")]
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)
        
        # ── Controls Header Bar Card
        header_card = QFrame(self)
        header_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        top_bar = QHBoxLayout(header_card)
        top_bar.setContentsMargins(10, 5, 10, 5)
        top_bar.setSpacing(10)
        
        self.ALL_REPORT_MODES = [
            "Toplu Çarşaf Liste : Sınıflar",
            "Toplu Çarşaf Liste : Öğretmenler",
            "Tablo Olarak : Dersler",
            "[BİREBİR] Tüm Sınıflar (Yatay Sayfada 6'lı Çizelge)",
            "[BİREBİR] Tüm Öğretmenler (Yatay Sayfada 6'lı Çizelge)",
            "Sınıf Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)",
            "Öğretmen Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)",
            "Sınıf Dersleri & Atama Listesi (Liste Formatı)",
            "Tüm Öğretmenlerin Ders Yükü Listesi"
        ]
        
        lbl_mode = QLabel("RAPOR TÜRÜ", self)
        lbl_mode.setStyleSheet("color: #64748B; font-size: 10px; font-weight: 700; border: none; background: transparent; letter-spacing: 0.5px;")
        top_bar.addWidget(lbl_mode)
        
        self.mode_combo = AppleComboBox(self)
        self.mode_combo.setMinimumWidth(350)
        self.mode_combo.addItems(self.ALL_REPORT_MODES)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        top_bar.addWidget(self.mode_combo)
        
        lbl_target = QLabel("SEÇİM", self)
        lbl_target.setStyleSheet("color: #64748B; font-size: 10px; font-weight: 700; border: none; background: transparent; letter-spacing: 0.5px;")
        top_bar.addWidget(lbl_target)
        
        self.target_combo = AppleComboBox(self)
        self.target_combo.setMinimumWidth(215)
        self.target_combo.currentIndexChanged.connect(self._repaint)
        top_bar.addWidget(self.target_combo)
        
        top_bar.addStretch(1)
        
        btn_style = """
            QPushButton {
                background-color: #FFFFFF;
                color: #334155;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-weight: 500;
                font-size: 11.5px;
                padding: 0 10px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #F8FAFC;
                border-color: #94A3B8;
                color: #0F172A;
            }
            QPushButton:pressed {
                background-color: #F1F5F9;
            }
        """
        
        btn_html = QPushButton("HTML Çıktısı")
        btn_html.setIcon(make_preview_icon("html", 14, "#334155"))
        btn_html.setCursor(Qt.PointingHandCursor)
        btn_html.setStyleSheet(btn_style)
        btn_html.clicked.connect(self._export_html)
        top_bar.addWidget(btn_html)
        
        btn_pdf = QPushButton("PDF Kaydet")
        btn_pdf.setIcon(make_preview_icon("pdf", 14, "#334155"))
        btn_pdf.setCursor(Qt.PointingHandCursor)
        btn_pdf.setStyleSheet(btn_style)
        btn_pdf.clicked.connect(self._export_pdf)
        top_bar.addWidget(btn_pdf)
        
        btn_print = QPushButton("Yazdır")
        btn_print.setIcon(make_preview_icon("print", 14, "#FFFFFF"))
        btn_print.setCursor(Qt.PointingHandCursor)
        btn_print.setStyleSheet("""
            QPushButton {
                background-color: #0071E3;
                color: #FFFFFF;
                border: 1px solid #0062C4;
                border-radius: 6px;
                font-weight: 500;
                font-size: 11.5px;
                padding: 0 14px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #0077ED;
            }
            QPushButton:pressed {
                background-color: #005BB5;
            }
        """)
        btn_print.clicked.connect(self._do_print)
        top_bar.addWidget(btn_print)
        
        main_layout.addWidget(header_card)
        
        # ── Print Preview Widget
        self.preview = QPrintPreviewWidget(self)
        self.preview.paintRequested.connect(self._paint)
        main_layout.addWidget(self.preview, 1)
        
        # Filter mode preselection
        lock_mode = self.filters.get("lock_mode")
        entity_type = self.filters.get("entity_type")
        
        target_mode_idx = 0
        if lock_mode:
            for idx, m_text in enumerate(self.ALL_REPORT_MODES):
                if lock_mode in m_text or m_text in lock_mode:
                    target_mode_idx = idx
                    break
        elif entity_type == "teacher":
            target_mode_idx = 2  # Öğretmen Haftalık Ders Programı (Tekil Çizelge)
        elif entity_type in ["class", "sinif"]:
            target_mode_idx = 3  # Sınıf Haftalık Ders Programı (Tekil Çizelge)
            
        self.mode_combo.setCurrentIndex(target_mode_idx)
        self._populate_targets()
        
        mode = self.mode_combo.currentText()
        is_portrait = ("Sınıf Dersleri" in mode)
        self.preview.setOrientation(QPageLayout.Orientation.Portrait if is_portrait else QPageLayout.Orientation.Landscape)

    def _on_mode_changed(self):
        mode = self.mode_combo.currentText()
        is_portrait = ("Sınıf Dersleri" in mode)
        self.preview.setOrientation(QPageLayout.Orientation.Portrait if is_portrait else QPageLayout.Orientation.Landscape)
        self._populate_targets()
        self._repaint()

    def _populate_targets(self):
        mode = self.mode_combo.currentText()
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.setEnabled(True)
        
        is_teacher_mode = bool(
            self.filters.get("teachers") or 
            self.filters.get("entity_type") in ["teacher", "teachers_all"] or 
            "Öğretmen" in mode
        )
        
        teachers_list = [t.get("ad", "").strip() for t in (self.filtered_teachers or self.data_store.get("ogretmenler", [])) if t.get("ad")]
        teachers_list = sorted(list(set(teachers_list)))
        
        import re
        def natural_sort_key(s):
            m = re.match(r"(\d+)(.*)", str(s).strip())
            return (int(m.group(1)), m.group(2)) if m else (999, str(s))
            
        raw_classes = [c.get("ad", "").strip() for c in (self.filtered_classes or self.data_store.get("siniflar", [])) if c.get("ad")]
        classes_list = sorted(list(set(raw_classes)), key=natural_sort_key)
        
        if is_teacher_mode:
            self.target_combo.addItem("Tüm Öğretmenler (Çoklu Sayfa)")
            for t in teachers_list:
                self.target_combo.addItem(t)
        else:
            self.target_combo.addItem("Tüm Sınıflar (Çoklu Sayfa)")
            for c in classes_list:
                self.target_combo.addItem(c)
                
        # If filters specified selected_items or default_selection, select it
        sel = self.filters.get("selected_items") or ([self.filters.get("default_selection")] if self.filters.get("default_selection") else [])
        if sel and len(sel) > 0 and sel[0]:
            idx = self.target_combo.findText(sel[0])
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
        else:
            idx = self.target_combo.findText("Tüm Öğretmenler (Çoklu Sayfa)" if is_teacher_mode else "Tüm Sınıflar (Çoklu Sayfa)")
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
                
        self.target_combo.blockSignals(False)

    def _repaint(self):
        self.preview.updatePreview()

    def _export_html(self):
        path, _ = QFileDialog.getSaveFileName(self, "HTML Olarak Kaydet", "Ders_Programi.html", "HTML Files (*.html)")
        if not path:
            return
        try:
            mode = self.mode_combo.currentText()
            target = self.target_combo.currentText()
            html = f"<html><head><meta charset='utf-8'><title>{target} - Program</title></head><body>"
            html += f"<h1>{target} - {mode}</h1><p>Chenkron Ders Planlama 2026 - 2027</p></body></html>"
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            QMessageBox.information(self, "Başarılı", "HTML çıktısı kaydedildi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"HTML kaydedilemedi:\n{e}")

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "PDF Olarak Kaydet", "Ders_Programi.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            from PySide6.QtGui import QPageSize, QPageLayout
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            
            mode = self.mode_combo.currentText()
            is_portrait = ("Sınıf Dersleri" in mode)
            printer.setPageOrientation(QPageLayout.Orientation.Portrait if is_portrait else QPageLayout.Orientation.Landscape)
            printer.setPageSize(QPageSize(QPageSize.A4))
            printer.setFullPage(True)
            
            self._paint(printer)
            QMessageBox.information(self, "Başarılı", "PDF başarıyla kaydedildi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"PDF oluşturulamadı:\n{e}")

    def _do_print(self):
        try:
            from PySide6.QtPrintSupport import QPrintDialog
            printer = QPrinter(QPrinter.HighResolution)
            mode = self.mode_combo.currentText()
            is_portrait = ("Sınıf Dersleri" in mode)
            printer.setPageOrientation(QPageLayout.Orientation.Portrait if is_portrait else QPageLayout.Orientation.Landscape)
            printer.setPageSize(QPageSize(QPageSize.A4))
            printer.setFullPage(True)
            
            dlg = QPrintDialog(printer, self)
            dlg.setWindowTitle("Yazdır")
            if dlg.exec() == QPrintDialog.Accepted:
                self._paint(printer)
                QMessageBox.information(self, "Yazdırıldı", "Yazdırma işlemi yazıcıya başarıyla iletildi.")
        except Exception as e:
            reply = QMessageBox.question(
                self, "Yazıcı Uyarısı",
                f"Sistem yazıcısına ulaşılamadı:\n{e}\n\nDoğrudan PDF olarak kaydetmek ister misiniz?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._export_pdf()

    def direct_print(self):
        try:
            from PySide6.QtPrintSupport import QPrintDialog
            printer = QPrinter(QPrinter.HighResolution)
            mode = self.mode_combo.currentText()
            is_portrait = ("Sınıf Dersleri" in mode)
            printer.setPageOrientation(QPageLayout.Orientation.Portrait if is_portrait else QPageLayout.Orientation.Landscape)
            printer.setPageSize(QPageSize(QPageSize.A4))
            printer.setFullPage(True)
            
            dlg = QPrintDialog(printer, self.parent() or self)
            dlg.setWindowTitle("Yazdır")
            if dlg.exec() == QPrintDialog.Accepted:
                self._paint(printer)
                QMessageBox.information(self.parent() or self, "Yazdırıldı", "Yazdırma işlemi yazıcıya başarıyla iletildi.")
                return True
            return False
        except Exception as e:
            reply = QMessageBox.question(
                self.parent() or self, "Yazıcı Uyarısı",
                f"Sistem yazıcısına ulaşılamadı:\n{e}\n\nDoğrudan PDF olarak kaydetmek ister misiniz?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._export_pdf()
            return False

    def _paint(self, printer):
        painter = QPainter(printer)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        VW, VH = 1120, 792
        mode = self.mode_combo.currentText()
        if "Sınıf Dersleri" in mode:
            VW, VH = 800, 1120
            
        painter.setViewport(0, 0, printer.width(), printer.height())
        painter.setWindow(0, 0, VW, VH)
        
        if mode == "Toplu Çarşaf Liste : Sınıflar":
            self._render_carsaf_liste(painter, printer, VW, VH, is_teacher=False)
        elif mode == "Toplu Çarşaf Liste : Öğretmenler":
            self._render_carsaf_liste(painter, printer, VW, VH, is_teacher=True)
        elif mode == "Tablo Olarak : Dersler":
            self._render_tablo_dersler(painter, printer, VW, VH)
        elif mode == "[BİREBİR] Tüm Sınıflar (Yatay Sayfada 6'lı Çizelge)":
            self._render_asc_multi_grid(painter, printer, VW, VH, is_teacher=False)
        elif mode == "[BİREBİR] Tüm Öğretmenler (Yatay Sayfada 6'lı Çizelge)":
            self._render_asc_multi_grid(painter, printer, VW, VH, is_teacher=True)
        elif mode == "Sınıf Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)":
            self._render_weekly_grid(painter, printer, VW, VH, is_teacher=False)
        elif mode == "Öğretmen Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)":
            self._render_weekly_grid(painter, printer, VW, VH, is_teacher=True)
        elif mode == "Sınıf Dersleri & Atama Listesi (Liste Formatı)":
            self._render_class_lessons_list(painter, printer, VW, VH)
        elif mode == "Tüm Öğretmenlerin Ders Yükü Listesi":
            self._render_teacher_summary_list(painter, VW, VH)
        else:
            self._render_weekly_grid(painter, printer, VW, VH, is_teacher=False)
            
        painter.end()

    def _get_pseudo_placements(self, target_name, is_teacher=False):
        if not hasattr(self, "_placements_cache"):
            self._placements_cache = {}
            
        cache_key = f"{target_name}_{is_teacher}"
        if cache_key in self._placements_cache:
            return self._placements_cache[cache_key]
            
        res = {}
        tr_map = str.maketrans({'İ': 'i', 'I': 'ı', 'ı': 'i', 'Ş': 's', 'ş': 's', 'Ğ': 'g', 'ğ': 'g', 'Ü': 'u', 'ü': 'u', 'Ö': 'o', 'ö': 'o', 'Ç': 'c', 'ç': 'c'})
        
        def normalize_clean(s):
            if not s: return ""
            raw = str(s).strip()
            import re
            raw = re.sub(r'\s*\((?:ea|say|söz|soz|dil)\)\s*$', '', raw, flags=re.IGNORECASE)
            return "".join(c for c in raw.translate(tr_map).lower() if c.isalnum())
            
        target_norm = normalize_clean(target_name)
        periods_per_day = int(self.data_store.get("settings", {}).get("periods", 8))
        
        # Source 1: data_store["grid_placements"] (Only fallback to auto_schedule_results if empty)
        grid_data = list(self.data_store.get("grid_placements", []))
        if not grid_data and self.data_store.get("auto_schedule_results"):
            grid_data = list(self.data_store.get("auto_schedule_results", []))
            
        for item in grid_data:
            if not isinstance(item, dict): continue
            raw_col = int(item.get("col", 0))
            raw_day = item.get("day")
            raw_period = item.get("period")
            
            if raw_day is not None and raw_period is not None:
                d_idx = int(raw_day)
                p_idx = int(raw_period)
            else:
                d_idx = raw_col // periods_per_day if periods_per_day > 0 else 0
                p_idx = raw_col % periods_per_day if periods_per_day > 0 else 0
                
            dur = int(item.get("duration", 1))
            t_name = item.get("teacher_name") or item.get("teacher") or ""
            c_name = item.get("class_name") or item.get("class") or ""
            s_name = item.get("subject_name") or item.get("subject") or ""
            scolor = item.get("color") or get_subject_color(s_name)
            
            match = False
            if is_teacher:
                if t_name and (normalize_clean(t_name) == target_norm or format_tr_name(t_name) == format_tr_name(target_name)):
                    match = True
                    other_name = c_name
            else:
                if c_name and (normalize_clean(c_name) == target_norm or matches_class(c_name, target_name)):
                    match = True
                    other_name = t_name
                    
            if match:
                is_comb = bool(item.get("is_combined") or (item.get("combined_classes") and len(item.get("combined_classes")) > 1))
                for off in range(dur):
                    slot = (d_idx, p_idx + off)
                    if is_teacher and slot in res:
                        old_entry = res[slot]
                        old_c = old_entry.get("class_name", "")
                        # Only merge class names if this was an explicit combined lesson
                        if is_comb and c_name and c_name not in old_c:
                            merged_c = f"{old_c} + {c_name}"
                            old_entry["class_name"] = merged_c
                            old_entry["is_combined"] = True
                        elif not is_comb:
                            # Not a combined lesson: overwrite with active placement
                            res[slot] = {
                                "subject_name": s_name,
                                "teacher_name": t_name or other_name,
                                "class_name": c_name or other_name,
                                "color": scolor,
                                "is_start": (off == 0),
                                "duration": dur,
                                "is_combined": False
                            }
                    else:
                        res[slot] = {
                            "subject_name": s_name,
                            "teacher_name": t_name or other_name,
                            "class_name": c_name or other_name,
                            "color": scolor,
                            "is_start": (off == 0),
                            "duration": dur,
                            "is_combined": is_comb
                        }
        self._placements_cache[cache_key] = res
        return res

    def _render_asc_multi_grid(self, painter, printer, VW, VH, is_teacher=False):
        import re
        def natural_sort_key(s):
            m = re.match(r"(\d+)(.*)", str(s).strip())
            return (int(m.group(1)), m.group(2)) if m else (999, str(s))
            
        sel_target = self.target_combo.currentText().strip()
        
        if sel_target and "Çoklu Sayfa" not in sel_target and sel_target != "Tümü":
            items = [sel_target]
        else:
            if is_teacher:
                items = sorted([t.get("ad", "Öğretmen") for t in (self.filtered_teachers if self.filtered_teachers else self.data_store.get("ogretmenler", []))])
            else:
                items = sorted([c.get("ad", "Sınıf") for c in (self.filtered_classes if self.filtered_classes else self.data_store.get("siniflar", []))], key=natural_sort_key)
            
        if not items:
            items = ["Örnek 1"]
            
        school_name = self.data_store.get("okul_adi") or self.data_store.get("settings", {}).get("school_name", "Özel Öğretim Kurumu")
        
        # Single entity selected (e.g. 9A or single teacher) -> Center full page with high scale!
        if len(items) == 1:
            margin_x = 35
            margin_y = 25
            cell_w = VW - (2 * margin_x)
            cell_h = VH - (2 * margin_y)
            x = margin_x
            y = margin_y
            placements = self._get_pseudo_placements(items[0], is_teacher)
            self._draw_mini_grid(painter, x, y, cell_w, cell_h, items[0], school_name, placements, is_teacher=is_teacher, is_single_page=True)
            return

        # Grid layout math: 2 columns x 3 rows (6 boxes per page on A4 Landscape)
        cols, rows = 2, 3
        per_page = cols * rows
        
        margin_x, margin_y = 25, 20
        spacing_x, spacing_y = 30, 25
        
        cell_w = (VW - (2 * margin_x) - (cols - 1) * spacing_x) / cols
        cell_h = (VH - (2 * margin_y) - (rows - 1) * spacing_y) / rows
        
        for i, item_name in enumerate(items):
            if i > 0 and i % per_page == 0:
                printer.newPage()
                painter.fillRect(0, 0, VW, VH, Qt.white)
                
            page_idx = i % per_page
            col_idx = page_idx % cols
            row_idx = page_idx // cols
            
            x = margin_x + col_idx * (cell_w + spacing_x)
            y = margin_y + row_idx * (cell_h + spacing_y)
            
            placements = self._get_pseudo_placements(item_name, is_teacher)
            self._draw_mini_grid(painter, x, y, cell_w, cell_h, item_name, school_name, placements, is_teacher=is_teacher, is_single_page=False)

    def _draw_mini_grid(self, painter, x, y, w, h, target_name, school_name, placements, is_teacher=False, is_single_page=False):
        """Draws exact timetable grid matching photo: Pa..Cu on left, 1..8 on top, Bold Subject + Teacher/Class"""
        import datetime
        date_str = datetime.datetime.now().strftime("%d/%m/%Y")
        acad_year = self.data_store.get("settings", {}).get("academic_year") or "2026 - 2027"
        if not acad_year or any(y in str(acad_year) for y in ("2023", "2024", "2025")):
            acad_year = "2026 - 2027"
        
        # 1. Header Row
        header_h = 36 if is_single_page else 18
        
        # Top Left: Date (e.g. 12/09/2026)
        painter.setFont(make_font(14 if is_single_page else 8, False))
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawText(QRectF(x, y, w * 0.35, header_h), Qt.AlignLeft | Qt.AlignVCenter, date_str)
        
        # Top Center: Class / Teacher Name (e.g. 9A, 11A, Hüseyin Arman)
        painter.setFont(make_font(32 if is_single_page else 16, True))
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawText(QRectF(x, y - (2 if is_single_page else 0), w, header_h + (12 if is_single_page else 4)), Qt.AlignCenter, str(target_name).upper())
        
        # Top Right: Ders Planı : 2026 - 2027
        painter.setFont(make_font(14 if is_single_page else 8, False))
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawText(QRectF(x + w * 0.65, y, w * 0.35, header_h), Qt.AlignRight | Qt.AlignVCenter, f"Ders Planı : {acad_year}")
        
        # 2. Table Grid
        top_gap = 48 if is_single_page else 22
        grid_x = x
        grid_y = y + top_gap
        grid_w = w
        grid_h = h - top_gap
        
        all_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        short_days = ["Pa", "Sa", "Ça", "Pe", "Cu", "Cts", "Paz"]
        settings = self.data_store.get("settings", {})
        cnt = int(settings.get("day_count") or settings.get("days_count") or self.data_store.get("gun_sayisi", 5))
        saved_days = settings.get("days") or settings.get("days_list") or all_days[:cnt]
        days = [short_days[all_days.index(d)] if d in all_days else d[:3] for d in saved_days]
        periods = int(settings.get("periods", 8))
        
        hour_col_w = max(55 if is_single_page else 40, grid_w * (0.08 if is_single_page else 0.08))
        col_header_h = max(32 if is_single_page else 24, grid_h * (0.10 if is_single_page else 0.14))
        
        col_w = (grid_w - hour_col_w) / periods
        row_h = (grid_h - col_header_h) / len(days)
        
        painter.setPen(QPen(QColor("#000000"), 1.4 if is_single_page else 1.0))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        
        # Top-Left Corner Box
        painter.drawRect(QRectF(grid_x, grid_y, hour_col_w, col_header_h))
        
        times = get_bell_times(self.data_store, periods, separator="-")
        
        # Top Period Column Headers (1..periods with times underneath)
        for p_idx in range(periods):
            cx = grid_x + hour_col_w + p_idx * col_w
            painter.setPen(QPen(QColor("#000000"), 1.4 if is_single_page else 1.0))
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.drawRect(QRectF(cx, grid_y, col_w, col_header_h))
            
            painter.setPen(QPen(QColor("#000000"), 1))
            painter.setFont(make_font(18 if is_single_page else 10, True))
            painter.drawText(QRectF(cx, grid_y + 1, col_w, col_header_h * 0.52), Qt.AlignCenter | Qt.AlignBottom, str(p_idx + 1))
            
            t_str = times[p_idx]
            painter.setFont(make_font(11 if is_single_page else 6.5, False))
            painter.drawText(QRectF(cx, grid_y + col_header_h * 0.54, col_w, col_header_h * 0.44), Qt.AlignCenter | Qt.AlignTop, t_str)
            
        # Left Day Column Headers & Content Cells
        for d_idx, day_name in enumerate(days):
            ry = grid_y + col_header_h + d_idx * row_h
            painter.setPen(QPen(QColor("#000000"), 1.4 if is_single_page else 1.0))
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.drawRect(QRectF(grid_x, ry, hour_col_w, row_h))
            
            painter.setFont(make_font(24 if is_single_page else 12, True))
            painter.setPen(QPen(QColor("#000000"), 1))
            painter.drawText(QRectF(grid_x, ry, hour_col_w, row_h), Qt.AlignCenter, day_name)
            
            p_idx = 0
            while p_idx < periods:
                lesson = placements.get((d_idx, p_idx))
                cx = grid_x + hour_col_w + p_idx * col_w
                
                if lesson:
                    sname = lesson.get("subject_name", "")
                    if is_teacher:
                        other_name = lesson.get("class_name", "")
                    else:
                        other_name = lesson.get("teacher_name", "")

                    # Check contiguous span of same lesson on this day
                    dur = 1
                    while p_idx + dur < periods:
                        next_l = placements.get((d_idx, p_idx + dur))
                        if not next_l: break
                        next_s = next_l.get("subject_name", "")
                        next_o = next_l.get("class_name" if is_teacher else "teacher_name", "")
                        if next_s == sname and next_o == other_name:
                            dur += 1
                        else:
                            break
                            
                    block_w = col_w * dur
                    painter.setPen(QPen(QColor("#000000"), 1.4 if is_single_page else 1.0))
                    painter.setBrush(QBrush(QColor("#FFFFFF")))
                    painter.drawRect(QRectF(cx, ry, block_w, row_h))
                    
                    # Line 1: Subject Short Code in Bold (e.g. BİYO 1, BED, GÖR, MAT)
                    short_subj = get_subject_badge(sname, self.data_store)
                    
                    # Dynamically shrink font if it's a single hour block and subject name is long
                    subj_font_sz = 20 if is_single_page else 10
                    if dur == 1 and len(short_subj) >= 6:
                        subj_font_sz = 15 if is_single_page else 8
                        
                    painter.setFont(make_font(subj_font_sz, True))
                    painter.setPen(QPen(QColor("#000000"), 1))
                    painter.drawText(QRectF(cx + 1, ry + 2, block_w - 2, row_h * 0.52), Qt.AlignCenter | Qt.AlignVCenter, short_subj)
                    
                    # Line 2: Teacher / Class Name
                    if other_name:
                        if not is_teacher:
                            display_other = format_teacher_display_name(other_name, self.data_store)
                        else:
                            if "," in other_name or "&" in other_name or "+" in other_name:
                                parts = [c.split("(")[0].strip() for c in other_name.replace("&", ",").replace("+", ",").split(",") if c.strip()]
                                if len(parts) <= 2:
                                    display_other = "+".join(parts)
                                else:
                                    display_other = f"{parts[0]}+{parts[1]}"
                            else:
                                display_other = other_name.strip()
                        
                        # Dynamically shrink font if it's a single hour block (so 11C+11D fits)
                        other_font_sz = 15 if is_single_page else 7
                        if dur == 1 and len(display_other) > 6:
                            other_font_sz = 12 if is_single_page else 6
                            
                        painter.setFont(make_font(other_font_sz, False))
                        painter.setPen(QPen(QColor("#111111"), 1))
                        painter.drawText(QRectF(cx + 1, ry + row_h * 0.5, block_w - 2, row_h * 0.46), Qt.AlignCenter | Qt.AlignVCenter, display_other)
                        
                    is_comb_lesson = bool(lesson.get("is_combined") or ("+" in str(lesson.get("class_name", ""))) or ("," in str(lesson.get("class_name", ""))))
                    if is_comb_lesson:
                        painter.save()
                        badge_sz = 22 if is_single_page else 14
                        comb_rect = QRectF(cx + block_w - badge_sz - 3, ry + 3, badge_sz, badge_sz)
                        painter.setBrush(QBrush(QColor("#DBEAFE")))
                        painter.setPen(QPen(QColor("#2563EB"), 1))
                        painter.drawRoundedRect(comb_rect, 2.5, 2.5)
                        painter.setFont(make_font(14 if is_single_page else 8.5, True))
                        painter.setPen(QPen(QColor("#1E40AF"), 1))
                        painter.drawText(comb_rect, Qt.AlignCenter, "📎")
                        painter.restore()
                    
                    p_idx += dur
                else:
                    is_closed = False
                    if is_teacher:
                        for t in self.data_store.get("ogretmenler", []) or []:
                            if (t.get("ad") or t.get("name") or "").strip() == target_name:
                                toff = t.get("timeoff", [])
                                if toff and d_idx < len(toff) and p_idx < len(toff[d_idx]):
                                    is_closed = (toff[d_idx][p_idx] == 0)
                                break
                        if not is_closed:
                            kisit = self.data_store.get("kisitlamalar", {}).get(target_name, {})
                            if f"{d_idx},{p_idx}" in kisit:
                                is_closed = (kisit[f"{d_idx},{p_idx}"] in (0, False))
                    else:
                        for c in self.data_store.get("siniflar", []) or []:
                            if (c.get("ad") or c.get("name") or "").strip() == target_name:
                                toff = c.get("timeoff", [])
                                if toff and d_idx < len(toff) and p_idx < len(toff[d_idx]):
                                    is_closed = (toff[d_idx][p_idx] == 0)
                                break
                        if not is_closed:
                            kisit = self.data_store.get("kisitlamalar", {}).get(target_name, {})
                            if f"{d_idx},{p_idx}" in kisit:
                                is_closed = (kisit[f"{d_idx},{p_idx}"] in (0, False))

                    painter.setBrush(QBrush(QColor("#E2E8F0" if is_closed else "#FFFFFF")))
                    painter.setPen(QPen(QColor("#000000"), 1.4 if is_single_page else 1.0))
                    painter.drawRect(QRectF(cx, ry, col_w, row_h))
                    if is_closed:
                        painter.setFont(make_font(14 if is_single_page else 8, True))
                        painter.setPen(QPen(QColor("#94A3B8"), 1))
                        painter.drawText(QRectF(cx, ry, col_w, row_h), Qt.AlignCenter, "✕")
                    p_idx += 1

    def _render_class_lessons_list(self, painter, printer, VW, VH):
        """Sınıfın Dersleri / Öğretmen Atama Listesi Formatı (Fotoğraftaki Birebir aSc Dikey Formu)"""
        target_name = self.target_combo.currentText().strip()
        all_teachers = [t.get("ad", "").strip() for t in self.data_store.get("ogretmenler", []) if t.get("ad")]
        all_classes = [c.get("ad", "").strip() for c in (self.filtered_classes or self.data_store.get("siniflar", [])) if c.get("ad")]
        
        # Determine whether this is a teacher report
        if target_name in all_teachers or target_name == "Tüm Öğretmenler (Çoklu Sayfa)":
            is_teacher_report = True
        elif target_name in all_classes or target_name == "Tüm Sınıflar (Çoklu Sayfa)":
            is_teacher_report = False
        else:
            is_teacher_report = bool(self.filters.get("teachers") or self.filters.get("entity_type") in ["teacher", "teachers_all"])
        
        if is_teacher_report:
            if target_name and target_name not in ["Tümü (Çoklu Sayfa)", "Tüm Öğretmenler (Çoklu Sayfa)", "Tüm Öğretmenler", ""]:
                entities = [target_name]
            elif self.filters.get("teachers"):
                entities = self.filters["teachers"]
            else:
                entities = all_teachers
        else:
            if target_name and target_name not in ["Tümü (Çoklu Sayfa)", "Tüm Sınıflar (Çoklu Sayfa)", "Tüm Sınıflar", ""]:
                entities = [target_name]
            elif self.filters.get("classes"):
                entities = self.filters["classes"]
            else:
                entities = all_classes
                
        if not entities:
            entities = ["Öğretmen"] if is_teacher_report else ["9A"]
            
        if len(entities) == 1:
            self._draw_single_class_lessons_table(painter, entities[0], is_teacher_report, VW, VH)
        else:
            self._draw_continuous_master_lessons_list(painter, printer, entities, is_teacher_report, VW, VH)

    def _draw_continuous_master_lessons_list(self, painter, printer, entities, is_teacher_report, VW, VH):
        tbl_x = 25
        tbl_w = VW - 50
        raw_atamalar = self.data_store.get("atamalar", [])
        school_name = self.data_store.get("okul_adi") or self.data_store.get("settings", {}).get("school_name", "Özel Öğretim Kurumu")
        
        page_num = 1
        
        def draw_page_header():
            # Top Banner Header
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.setBrush(QBrush(QColor("#0F172A")))
            painter.drawRoundedRect(QRectF(tbl_x, 18, tbl_w, 32), 4, 4)
            
            painter.setFont(make_font(10.5, True))
            painter.setPen(QPen(QColor("#FFFFFF"), 1))
            title_txt = "TOPLU ÖĞRETMEN DERS & BRANŞ ATAMA LİSTESİ" if is_teacher_report else "TOPLU SINIF DERS & ÖĞRETMEN ATAMA LİSTESİ"
            painter.drawText(QRectF(tbl_x + 14, 18, 500, 32), Qt.AlignLeft | Qt.AlignVCenter, title_txt)
            
            painter.setFont(make_font(8.5, False))
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.drawText(QRectF(tbl_x + tbl_w - 260, 18, 248, 32), Qt.AlignRight | Qt.AlignVCenter, f"{school_name.upper()} | Sayfa {page_num}")
            
        def draw_page_footer():
            painter.setFont(make_font(8, False))
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.drawText(QRectF(tbl_x, VH - 30, tbl_w / 2, 20), Qt.AlignLeft, "Chenkron Ders Planlama Sistemi 2026 - 2027")
            painter.drawText(QRectF(tbl_x + tbl_w / 2, VH - 30, tbl_w / 2, 20), Qt.AlignRight, f"Sayfa {page_num}")

        draw_page_header()
        cur_y = 58
        
        cols = [
            ("Ders", 180),
            ("Sınıf" if is_teacher_report else "Öğretmen", 230),
            ("Branş / Not" if is_teacher_report else "Sınıf", 75),
            ("Toplam Saat", 65),
            ("Dağılım / Tip", 70),
            ("Derslik", 60),
            ("Dönem", 50)
        ]
        
        grand_total_lessons = 0
        grand_total_hours = 0
        
        for ent_name in entities:
            if is_teacher_report:
                raw_teacher_atamalar = [a for a in raw_atamalar if (a.get("ogretmen") or a.get("teacher")) == ent_name or format_tr_name(a.get("ogretmen") or a.get("teacher", "")) == format_tr_name(ent_name)]
                t_obj = next((t for t in self.data_store.get("ogretmenler", []) if t.get("ad") == ent_name or format_tr_name(t.get("ad", "")) == format_tr_name(ent_name)), {})
                t_brans = t_obj.get("brans") or t_obj.get("branch") or "Öğretmen"
                ent_sub = f"{t_brans.upper()} ÖĞRETMENİ"
                atamalar = _group_teacher_atamalar_by_subject(raw_teacher_atamalar)
                tot_h = sum(lesson_hours.hours(a) for a in atamalar)
            else:
                atamalar = [a for a in raw_atamalar if matches_class(a.get("sinif") or a.get("class", ""), ent_name) or (a.get("is_combined") and any(matches_class(cc, ent_name) for cc in a.get("combined_classes", [])))]
                ent_sub = f"{ent_name.upper()} SINIF PROGRAMI"
                t_brans = "Öğretmen"
                tot_h = sum(lesson_hours.hours(a) for a in atamalar)

            grand_total_lessons += len(atamalar)
            grand_total_hours += tot_h
            
            needed_h = 32 + 22 + max(1, len(atamalar)) * 22 + 10
            if cur_y + min(needed_h, 76) > VH - 45:
                draw_page_footer()
                if printer:
                    printer.newPage()
                    painter.fillRect(QRectF(0, 0, VW, VH), Qt.white)
                page_num += 1
                draw_page_header()
                cur_y = 58
                
            # 1. Teacher / Class Header Strip
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.setBrush(QBrush(QColor("#F1F5F9")))
            painter.drawRoundedRect(QRectF(tbl_x, cur_y, tbl_w, 26), 3, 3)
            
            # Name
            painter.setFont(make_font(10, True))
            painter.setPen(QPen(QColor("#0F172A"), 1))
            painter.drawText(QRectF(tbl_x + 10, cur_y, 250, 26), Qt.AlignLeft | Qt.AlignVCenter, ent_name.upper())
            
            # Subtitle / Branch
            painter.setFont(make_font(8.5, False))
            painter.setPen(QPen(QColor("#475569"), 1))
            painter.drawText(QRectF(tbl_x + 265, cur_y, 230, 26), Qt.AlignLeft | Qt.AlignVCenter, ent_sub)
            
            # Total Hours Badge
            painter.setFont(make_font(9, True))
            painter.setPen(QPen(QColor("#1D4ED8"), 1))
            painter.drawText(QRectF(tbl_x + tbl_w - 210, cur_y, 200, 26), Qt.AlignRight | Qt.AlignVCenter, f"Ders: {len(atamalar)} | Toplam: {tot_h} Saat")
            
            cur_y += 27
            
            # 2. Table Column Headers
            header_h = 20
            painter.setBrush(QBrush(QColor("#E2E8F0")))
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.drawRect(QRectF(tbl_x, cur_y, tbl_w, header_h))
            
            painter.setFont(make_font(8, True))
            painter.setPen(QPen(QColor("#1E293B"), 1))
            c_x = tbl_x
            for col_idx, (col_name, col_width) in enumerate(cols):
                align = Qt.AlignLeft | Qt.AlignVCenter if col_idx < 2 else Qt.AlignCenter
                pad = 8 if col_idx < 2 else 0
                painter.drawText(QRectF(c_x + pad, cur_y, col_width - pad, header_h), align, col_name)
                c_x += col_width
                if col_idx < len(cols) - 1:
                    painter.drawLine(c_x, cur_y, c_x, cur_y + header_h)
            cur_y += header_h
            
            # 3. Lesson Rows
            row_h = 22
            if not atamalar:
                painter.setBrush(QBrush(QColor("#FFFFFF")))
                painter.setPen(QPen(QColor("#CBD5E1"), 1))
                painter.drawRect(QRectF(tbl_x, cur_y, tbl_w, row_h))
                painter.setFont(make_font(8, False))
                painter.setPen(QPen(QColor("#94A3B8"), 1))
                painter.drawText(QRectF(tbl_x + 8, cur_y, tbl_w - 16, row_h), Qt.AlignLeft | Qt.AlignVCenter, "— Atanmış ders bulunmuyor —")
                cur_y += row_h
            else:
                for idx, item in enumerate(atamalar):
                    if cur_y + row_h > VH - 45:
                        draw_page_footer()
                        if printer:
                            printer.newPage()
                            painter.fillRect(QRectF(0, 0, VW, VH), Qt.white)
                        page_num += 1
                        draw_page_header()
                        cur_y = 58
                        
                    bg_color = QColor("#F8FAFC") if idx % 2 == 1 else QColor("#FFFFFF")
                    painter.setBrush(QBrush(bg_color))
                    painter.setPen(QPen(QColor("#CBD5E1"), 1))
                    painter.drawRect(QRectF(tbl_x, cur_y, tbl_w, row_h))
                    
                    c_x = tbl_x
                    subj_name = item.get("subject", "")
                    teacher_name = item.get("teacher", "—")
                    cls_name = item.get("class", "—")
                    dur = str(item.get("duration", 1))
                    typ = str(item.get("type", dur)).strip()
                    is_comb_item = bool(item.get("is_combined") or ("+" in str(cls_name)) or (item.get("combined_classes") and len(item.get("combined_classes")) > 1))
                    
                    # Col 0: Subject (Clean subtle badge + Name)
                    col_w0 = cols[0][1]
                    badge_text = get_subject_badge(subj_name, self.data_store)
                    badge_w = 44
                    badge_rect = QRectF(c_x + 6, cur_y + 3, badge_w, row_h - 6)
                    
                    painter.setBrush(QBrush(QColor("#F1F5F9")))
                    painter.setPen(QPen(QColor("#94A3B8"), 0.8))
                    painter.drawRoundedRect(badge_rect, 2, 2)
                    
                    painter.setFont(make_font(7, True))
                    painter.setPen(QPen(QColor("#334155"), 1))
                    painter.drawText(badge_rect, Qt.AlignCenter, badge_text)
                    
                    painter.setFont(make_font(8, True))
                    painter.setPen(QPen(QColor("#0F172A"), 1))
                    painter.drawText(QRectF(c_x + 54, cur_y, col_w0 - 56, row_h), Qt.AlignLeft | Qt.AlignVCenter, subj_name.upper())
                    c_x += col_w0
                    painter.setPen(QPen(QColor("#CBD5E1"), 1))
                    painter.drawLine(c_x, cur_y, c_x, cur_y + row_h)
                    
                    # Col 1: Class / Teacher
                    col_w1 = cols[1][1]
                    painter.setFont(make_font(8, False))
                    if is_teacher_report:
                        if is_comb_item:
                            painter.setPen(QPen(QColor("#16A34A"), 1))
                            comb_lbl = f"{cls_name.upper()} (Birleşik)" if "Birleşik" not in cls_name else cls_name.upper()
                            painter.drawText(QRectF(c_x + 6, cur_y, col_w1 - 10, row_h), Qt.AlignLeft | Qt.AlignVCenter, comb_lbl)
                        else:
                            painter.setPen(QPen(QColor("#1E293B"), 1))
                            painter.drawText(QRectF(c_x + 6, cur_y, col_w1 - 10, row_h), Qt.AlignLeft | Qt.AlignVCenter, cls_name.upper())
                    else:
                        painter.setPen(QPen(QColor("#1E293B"), 1))
                        painter.drawText(QRectF(c_x + 6, cur_y, col_w1 - 10, row_h), Qt.AlignLeft | Qt.AlignVCenter, teacher_name.upper())
                    c_x += col_w1
                    painter.setPen(QPen(QColor("#CBD5E1"), 1))
                    painter.drawLine(c_x, cur_y, c_x, cur_y + row_h)
                    
                    # Col 2: Branch
                    col_w2 = cols[2][1]
                    painter.setFont(make_font(8, False))
                    painter.setPen(QPen(QColor("#64748B"), 1))
                    painter.drawText(QRectF(c_x, cur_y, col_w2, row_h), Qt.AlignCenter, t_brans if is_teacher_report else cls_name.upper())
                    c_x += col_w2
                    painter.setPen(QPen(QColor("#CBD5E1"), 1))
                    painter.drawLine(c_x, cur_y, c_x, cur_y + row_h)
                    
                    # Col 3: Total Hours
                    col_w3 = cols[3][1]
                    painter.setFont(make_font(8.5, True))
                    painter.setPen(QPen(QColor("#0F172A"), 1))
                    painter.drawText(QRectF(c_x, cur_y, col_w3, row_h), Qt.AlignCenter, dur)
                    c_x += col_w3
                    painter.setPen(QPen(QColor("#CBD5E1"), 1))
                    painter.drawLine(c_x, cur_y, c_x, cur_y + row_h)
                    
                    # Col 4: Distribution / Type
                    col_w4 = cols[4][1]
                    painter.setFont(make_font(8, False))
                    painter.setPen(QPen(QColor("#64748B"), 1))
                    painter.drawText(QRectF(c_x, cur_y, col_w4, row_h), Qt.AlignCenter, typ if typ else dur)
                    c_x += col_w4
                    painter.setPen(QPen(QColor("#CBD5E1"), 1))
                    painter.drawLine(c_x, cur_y, c_x, cur_y + row_h)
                    
                    # Col 5: Room
                    col_w5 = cols[5][1]
                    painter.drawText(QRectF(c_x, cur_y, col_w5, row_h), Qt.AlignCenter, "Tümü")
                    c_x += col_w5
                    painter.setPen(QPen(QColor("#CBD5E1"), 1))
                    painter.drawLine(c_x, cur_y, c_x, cur_y + row_h)
                    
                    # Col 6: Term
                    col_w6 = cols[6][1]
                    painter.drawText(QRectF(c_x, cur_y, col_w6, row_h), Qt.AlignCenter, "Her iki...")
                    
                    cur_y += row_h
                    
            cur_y += 8
            
        draw_page_footer()

    def _draw_single_class_lessons_table(self, painter, target_entity, is_teacher_report, VW, VH):
        raw_atamalar = self.data_store.get("atamalar", [])
        
        if is_teacher_report:
            selected_teacher = target_entity
            raw_t_atamalar = [a for a in raw_atamalar if (a.get("ogretmen") or a.get("teacher")) == selected_teacher or format_tr_name(a.get("ogretmen") or a.get("teacher", "")) == format_tr_name(selected_teacher)]
            atamalar = _group_teacher_atamalar_by_subject(raw_t_atamalar)
            title_name = selected_teacher.upper()
            t_obj = next((t for t in self.data_store.get("ogretmenler", []) if t.get("ad") == selected_teacher or format_tr_name(t.get("ad", "")) == format_tr_name(selected_teacher)), {})
            t_brans = t_obj.get("brans") or t_obj.get("branch") or "Öğretmen"
            clean_sub = f"{t_brans.upper()} ÖĞRETMENİ" if t_brans else "BRANŞ ÖĞRETMENİ"
            panel_title = "Öğretmenin Girdiği Sınıflar & Dersler"
        else:
            selected_class = target_entity
            atamalar = [a for a in raw_atamalar if matches_class(a.get("sinif") or a.get("class", ""), selected_class) or (a.get("is_combined") and any(matches_class(cc, selected_class) for cc in a.get("combined_classes", [])))]
            title_name = selected_class.upper()
            clean_sub = f"{selected_class.upper()} SINIF DERS PROGRAMI"
            panel_title = "Sınıfın Dersleri & Atamaları"
            
        if not atamalar and self.data_store.get("dersler"):
            atamalar = []
            for d in self.data_store.get("dersler", []):
                atamalar.append({
                    "subject": d.get("ad", "Ders"),
                    "teacher": target_entity if is_teacher_report else "Atanmadı",
                    "class": "—" if is_teacher_report else target_entity,
                    "duration": d.get("saat", 2),
                    "length": 1,
                    "color": d.get("renk")
                })

        tbl_x = 25
        tbl_w = VW - 50 
        
        # 1. Top Window Frame Header
        painter.setPen(QPen(QColor("#94A3B8"), 1))
        painter.setBrush(QBrush(QColor("#E2E8F0")))
        painter.drawRect(QRectF(tbl_x, 20, tbl_w, 24))
        
        painter.setPen(QPen(QColor("#0F172A"), 1))
        painter.setFont(make_font(10, True))
        painter.drawText(QRectF(tbl_x + 8, 20, 20, 24), Qt.AlignCenter, "👨‍🏫" if is_teacher_report else "🗂️")
        painter.drawText(QRectF(tbl_x + 30, 20, 300, 24), Qt.AlignLeft | Qt.AlignVCenter, panel_title)
        
        # Top right "TÜM ÖĞRETMENLER" / "TÜM SINIFLAR" header indicator
        painter.setFont(make_font(9, True))
        painter.setPen(QPen(QColor("#475569"), 1))
        painter.drawText(QRectF(tbl_x + tbl_w - 220, 20, 210, 24), Qt.AlignRight | Qt.AlignVCenter, "TÜM ÖĞRETMENLER" if is_teacher_report else "TÜM SINIFLAR")
        
        # Header Panel
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawRect(QRectF(tbl_x, 44, tbl_w, 48))
        
        # Avatar Icon
        draw_class_avatar_icon(painter, tbl_x + 14, 50)
        
        # Name (Large Bold) & Subtitle
        painter.setFont(make_font(15, True))
        painter.setPen(QPen(QColor("#0F172A"), 1))
        painter.drawText(QRectF(tbl_x + 56, 48, 400, 22), Qt.AlignLeft | Qt.AlignVCenter, title_name)
        
        painter.setFont(make_font(9, False))
        painter.setPen(QPen(QColor("#64748B"), 1))
        painter.drawText(QRectF(tbl_x + 56, 70, 400, 16), Qt.AlignLeft | Qt.AlignVCenter, clean_sub)
        
        # 2. Table Headers
        start_y = 96
        header_h = 24
        
        cols = [
            ("Ders", 200),
            ("Sınıf" if is_teacher_report else "Öğretmen", 190),
            ("Branş / Not" if is_teacher_report else "Sınıf", 75),
            ("Toplam", 75),
            ("Uzunluk", 70),
            ("Derslikler", 70),
            ("Hafta", 35),
            ("Dönem", 35)
        ]
        
        painter.setBrush(QBrush(QColor("#E2E8F0")))
        painter.setPen(QPen(QColor("#94A3B8"), 1))
        painter.drawRect(QRectF(tbl_x, start_y, tbl_w, header_h))
        
        painter.setFont(make_font(9, True))
        painter.setPen(QPen(QColor("#1E293B"), 1))
        cur_x = tbl_x
        for col_idx, (col_name, col_width) in enumerate(cols):
            align = Qt.AlignLeft | Qt.AlignVCenter if col_idx < 2 else Qt.AlignCenter
            pad = 8 if col_idx < 2 else 0
            painter.drawText(QRectF(cur_x + pad, start_y, col_width - pad, header_h), align, col_name)
            cur_x += col_width
            if col_idx < len(cols) - 1:
                painter.drawLine(cur_x, start_y, cur_x, start_y + header_h)

        # 3. Table Rows
        row_h = 26
        cur_y = start_y + header_h
        
        for idx, item in enumerate(atamalar):
            if cur_y + row_h > VH - 40:
                break
                
            # Alternating clean zebra striping
            bg_color = QColor("#F8FAFC") if idx % 2 == 1 else QColor("#FFFFFF")
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawRect(QRectF(tbl_x, cur_y, tbl_w, row_h))
            
            cur_x = tbl_x
            subj_name = item.get("subject", "")
            teacher_name = item.get("teacher", "—")
            cls_name = item.get("class", "—")
            dur = str(item.get("duration", 1))
            is_comb_item = bool(item.get("is_combined") or ("+" in str(cls_name)) or (item.get("combined_classes") and len(item.get("combined_classes")) > 1))
            
            # --- Col 0: Ders ---
            col_w0 = cols[0][1]
            badge_text = get_subject_badge(subj_name, self.data_store)
            badge_w = 56
            badge_rect = QRectF(cur_x + 6, cur_y + 3, badge_w, row_h - 6)
            
            from dialogs.color_picker_dialog import resolve_subject_color
            scolor_hex = item.get("color") or resolve_subject_color(subj_name, self.data_store)
            fill_c = scolor_hex if isinstance(scolor_hex, QColor) else QColor(str(scolor_hex or "#E2E8F0"))
            if not fill_c.isValid(): fill_c = QColor("#E2E8F0")
            
            painter.setBrush(QBrush(fill_c))
            painter.setPen(QPen(QColor("#64748B"), 0.8))
            painter.drawRoundedRect(badge_rect, 3, 3)
            
            painter.setFont(make_font(8.5, True))
            painter.setPen(QPen(QColor("#0F172A"), 1))
            painter.drawText(badge_rect, Qt.AlignCenter, badge_text)
            
            # Subject Full Name
            painter.setFont(make_font(8.5, True))
            painter.setPen(QPen(QColor("#0F172A"), 1))
            painter.drawText(QRectF(cur_x + 68, cur_y, col_w0 - 72, row_h), Qt.AlignLeft | Qt.AlignVCenter, subj_name.upper())
            
            cur_x += col_w0
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 1: Sınıf (Öğretmen Raporu) / Öğretmen (Sınıf Raporu) ---
            col_w1 = cols[1][1]
            painter.setFont(make_font(9, False))
            if is_teacher_report:
                if is_comb_item:
                    painter.setPen(QPen(QColor("#16A34A"), 1)) # Green for combined
                    comb_lbl = f"{cls_name.upper()} (🔗 Birleşik)" if "Birleşik" not in cls_name else cls_name.upper()
                    painter.drawText(QRectF(cur_x + 8, cur_y, col_w1 - 12, row_h), Qt.AlignLeft | Qt.AlignVCenter, comb_lbl)
                else:
                    painter.setPen(QPen(QColor("#1E293B"), 1))
                    painter.drawText(QRectF(cur_x + 8, cur_y, col_w1 - 12, row_h), Qt.AlignLeft | Qt.AlignVCenter, cls_name.upper())
            else:
                painter.setPen(QPen(QColor("#1E293B"), 1))
                t_display = format_teacher_display_name(teacher_name, self.data_store)
                painter.drawText(QRectF(cur_x + 8, cur_y, col_w1 - 12, row_h), Qt.AlignLeft | Qt.AlignVCenter, t_display)
            cur_x += col_w1
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 2: Branş / Not (Öğretmen Raporu) / Sınıf (Sınıf Raporu) ---
            col_w2 = cols[2][1]
            painter.setFont(make_font(9, False))
            painter.setPen(QPen(QColor("#64748B"), 1))
            if is_teacher_report:
                painter.drawText(QRectF(cur_x, cur_y, col_w2, row_h), Qt.AlignCenter, t_brans if t_brans else "Öğretmen")
            else:
                painter.drawText(QRectF(cur_x, cur_y, col_w2, row_h), Qt.AlignCenter, cls_name.upper())
            cur_x += col_w2
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 3: Toplam Saat ---
            col_w3 = cols[3][1]
            painter.setFont(make_font(9, True))
            painter.setPen(QPen(QColor("#0F172A"), 1))
            painter.drawText(QRectF(cur_x, cur_y, col_w3, row_h), Qt.AlignCenter, dur)
            cur_x += col_w3
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 4: Uzunluk ---
            col_w4 = cols[4][1]
            painter.setFont(make_font(9, False))
            painter.setPen(QPen(QColor("#64748B"), 1))
            painter.drawText(QRectF(cur_x, cur_y, col_w4, row_h), Qt.AlignCenter, "1")
            cur_x += col_w4
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 5: Derslikler ---
            col_w5 = cols[5][1]
            painter.drawText(QRectF(cur_x, cur_y, col_w5, row_h), Qt.AlignCenter, "Tümü")
            cur_x += col_w5
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 6: Hafta ---
            col_w6 = cols[6][1]
            painter.drawText(QRectF(cur_x, cur_y, col_w6, row_h), Qt.AlignCenter, "Tümü")
            cur_x += col_w6
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 7: Dönem ---
            col_w7 = cols[7][1]
            painter.drawText(QRectF(cur_x, cur_y, col_w7, row_h), Qt.AlignCenter, "Her iki...")
            
            cur_y += row_h
            
        # Summary footer
        total_hours = sum(lesson_hours.hours(a) for a in atamalar)
        painter.setFont(make_font(8.5, False))
        painter.setPen(QPen(QColor("#64748B"), 1))
        painter.drawText(QRectF(tbl_x, VH - 35, 450, 20), Qt.AlignLeft, f"Toplam Atanan Ders Sayısı: {len(atamalar)} | Toplam Ders Saati: {total_hours} Saat")
        painter.drawText(QRectF(VW - tbl_x - 300, VH - 35, 300, 20), Qt.AlignRight, "Chenkron Ders Planlama Sistemi 2026 - 2027")

    def _render_weekly_grid(self, painter, printer, VW, VH, is_teacher=False):
        """Single class or single teacher timetable on one page (Same exact layout as photo)"""
        import re
        def natural_sort_key(s):
            m = re.match(r"(\d+)(.*)", str(s).strip())
            return (int(m.group(1)), m.group(2)) if m else (999, str(s))
            
        sel_target = self.target_combo.currentText().strip()
        school_name = self.data_store.get("okul_adi") or self.data_store.get("settings", {}).get("school_name", "Özel Öğretim Kurumu")
        
        if is_teacher:
            all_items = sorted([t.get("ad", "Öğretmen") for t in (self.filtered_teachers if self.filtered_teachers else self.data_store.get("ogretmenler", [])) if t.get("ad")])
        else:
            all_items = sorted([c.get("ad", "Sınıf") for c in (self.filtered_classes if self.filtered_classes else self.data_store.get("siniflar", [])) if c.get("ad")], key=natural_sort_key)
            
        if sel_target and "Çoklu Sayfa" not in sel_target and sel_target != "Tümü" and not sel_target.startswith("Tüm "):
            items = [sel_target]
        else:
            items = all_items
            
        if not items:
            items = ["Örnek 1"]
            
        margin_x = 35
        margin_y = 25
        grid_w = VW - (2 * margin_x)
        grid_h = VH - (2 * margin_y)
        
        for i, item_name in enumerate(items):
            if i > 0:
                printer.newPage()
                painter.fillRect(0, 0, VW, VH, Qt.white)
            placements = self._get_pseudo_placements(item_name, is_teacher)
            self._draw_mini_grid(painter, margin_x, margin_y, grid_w, grid_h, item_name, school_name, placements, is_teacher=is_teacher, is_single_page=True)

    def _render_teacher_summary_list(self, painter, VW, VH):
        teachers = sorted(self.data_store.get("ogretmenler", []), key=lambda t: t.get("ad", ""))
        atamalar = self.data_store.get("atamalar", [])
        
        # Header banner box with clean border
        painter.setPen(QPen(QColor("#64748B"), 1.2))
        painter.setBrush(QBrush(QColor("#F8FAFC")))
        painter.drawRoundedRect(30, 20, VW - 60, 50, 6, 6)
        
        painter.setPen(QPen(QColor("#0F172A"), 1))
        painter.setFont(make_font(17, True))
        painter.drawText(QRectF(50, 25, 600, 40), Qt.AlignLeft | Qt.AlignVCenter, "Tüm Öğretmenlerin Ders Yükü Raporu")
        
        start_y = 85
        tbl_w = VW - 60
        cols = [("Öğretmen Adı", 280), ("Kısa Kodu", 140), ("Atanan Dersler", 460), ("Toplam Saat", 180)]
        
        cur_x = 30
        header_h = 34
        painter.setBrush(QBrush(QColor("#E2E8F0")))
        painter.setPen(QPen(QColor("#64748B"), 1.2))
        painter.drawRect(QRectF(30, start_y, tbl_w, header_h))
        
        # Draw bold high-contrast column headers
        painter.setPen(QPen(QColor("#0F172A"), 1))
        painter.setFont(make_font(12, True))
        for col_name, col_w in cols:
            painter.drawText(QRectF(cur_x, start_y, col_w, header_h), Qt.AlignCenter, col_name)
            cur_x += col_w
            
        cur_y = start_y + header_h
        row_h = 32
        
        for idx, t in enumerate(teachers):
            if cur_y + row_h > VH - 40:
                break
            bg_color = QColor("#F8FAFC") if idx % 2 == 1 else QColor("#FFFFFF")
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.drawRect(QRectF(30, cur_y, tbl_w, row_h))
            
            tname = t.get("ad", "")
            tkisa = t.get("kisa", "")
            t_atamalar = [a for a in atamalar if format_tr_name(a.get("ogretmen") or a.get("teacher", "")) == format_tr_name(tname)]
            subs_str = ", ".join(list({(a.get("ders") or a.get("subject", "")) for a in t_atamalar if (a.get("ders") or a.get("subject"))})) or "—"
            tot_hours = sum(lesson_hours.hours(a) for a in t_atamalar)
            
            # Text pen MUST be high-contrast crisp black / dark slate
            painter.setPen(QPen(QColor("#0F172A"), 1))
            painter.setFont(make_font(11, True))
            
            cur_x = 30
            painter.drawText(QRectF(cur_x + 12, cur_y, cols[0][1] - 14, row_h), Qt.AlignLeft | Qt.AlignVCenter, tname)
            cur_x += cols[0][1]
            
            painter.setFont(make_font(11, False))
            painter.setPen(QPen(QColor("#334155"), 1))
            painter.drawText(QRectF(cur_x, cur_y, cols[1][1], row_h), Qt.AlignCenter, tkisa)
            cur_x += cols[1][1]
            
            painter.drawText(QRectF(cur_x + 10, cur_y, cols[2][1] - 14, row_h), Qt.AlignLeft | Qt.AlignVCenter, subs_str)
            cur_x += cols[2][1]
            
            painter.setFont(make_font(12, True))
            painter.setPen(QPen(QColor("#0284C7") if tot_hours > 0 else QColor("#94A3B8"), 1))
            painter.drawText(QRectF(cur_x, cur_y, cols[3][1], row_h), Qt.AlignCenter, f"{tot_hours} Saat")
            cur_y += row_h

    def _render_carsaf_liste(self, painter, printer, VW, VH, is_teacher=False):
        """Toplu Çarşaf Liste: Sınıflar/Öğretmenler. 8 saatlik birebir aSc formatı."""
        import datetime
        import re
        
        date_str = datetime.datetime.now().strftime("%d.%m.%Y")
        school_name = self.data_store.get("okul_adi") or self.data_store.get("settings", {}).get("school_name", "Okul Adı")
        
        def smart_abbr(subject_name):
            if not subject_name: return ""
            s = str(subject_name).strip()
            tr_map = str.maketrans({'i': 'İ', 'ı': 'I', 'ç': 'Ç', 'ğ': 'Ğ', 'ö': 'Ö', 'ş': 'Ş', 'ü': 'Ü'})
            s_up = s.translate(tr_map).upper()
            
            mapping = {
                "MATEMATİK": "MAT",
                "MATEMATIK": "MAT",
                "GEOMETRİ": "GEO",
                "GEOMETRI": "GEO",
                "COĞRAFYA": "COĞ",
                "COGRAFYA": "COĞ",
                "BEDEN EĞİTİMİ VE SPOR": "BED",
                "BEDEN EGITIMI VE SPOR": "BED",
                "BEDEN EĞİTİMİ": "BED",
                "BEDEN EGITIMI": "BED",
                "BEDEN": "BED",
                "TÜRK DİLİ VE EDEBİYATI": "TDE",
                "TURK DILI VE EDEBIYATI": "TDE",
                "TÜRKÇE": "TRK",
                "TURKCE": "TRK",
                "EDEBİYAT": "EDE",
                "EDEBIYAT": "EDE",
                "GÖRSEL SANATLAR": "GÖR",
                "GORSEL SANATLAR": "GÖR",
                "GÖRSEL": "GÖR",
                "GORSEL": "GÖR",
                "RESİM": "GÖR",
                "İNGİLİZCE": "İNG",
                "INGILIZCE": "İNG",
                "ALMANCA": "ALM",
                "DİN KÜLTÜRÜ VE AHLAK BİLGİSİ": "DİN",
                "DIN KULTURU VE AHLAK BILGISI": "DİN",
                "DİN KÜLTÜRÜ": "DİN",
                "DIN KULTURU": "DİN",
                "FELSEFE": "FEL",
                "REHBERLİK": "REH",
                "REHBERLIK": "REH",
                "BİYOLOJİ": "BİY",
                "BIYOLOJI": "BİY",
                "KİMYA": "KİM",
                "KIMYA": "KİM",
                "FİZİK": "FİZ",
                "FIZIK": "FİZ",
                "TARİH": "TAR",
                "TARIH": "TAR",
                "MÜZİK": "MÜZ",
                "MUZIK": "MÜZ",
                "BİLİŞİM": "BİL",
                "KODLAMA": "KOD",
                "SEÇMELİ": "SEÇ",
                "SECMELI": "SEÇ",
                "PARAGRAF": "PRG",
                "PROBLEM": "PRB"
            }
            for k, v in mapping.items():
                if s_up == k or s_up.startswith(k):
                    import re
                    m = re.search(r'\s*(\d+)$', s_up)
                    num_s = f"{m.group(1)}" if m else ""
                    return f"{v}{num_s}"[:5]
                    
            import re
            m = re.search(r'^(.+?)\s*(\d+)$', s_up)
            if m:
                base = m.group(1).strip()
                suf = m.group(2)
                return f"{base[:3]}{suf}"[:5]
            return s_up[:4]
            
        import re
        def natural_sort_key(s):
            name = s.get("ad", "") if isinstance(s, dict) else str(s)
            m = re.match(r"(\d+)(.*)", name.strip())
            return (int(m.group(1)), m.group(2)) if m else (999, name)
            
        if is_teacher:
            items = sorted(self.filtered_teachers if self.filtered_teachers else self.data_store.get("ogretmenler", []), key=lambda t: t.get("ad", ""))
        else:
            items = sorted(self.filtered_classes if self.filtered_classes else self.data_store.get("siniflar", []), key=natural_sort_key)
            
        # Filter by combo box selection if not "Tümü"
        current_sel = self.target_combo.currentText().strip()
        if current_sel and "Tümü" not in current_sel and "Tüm " not in current_sel:
            items = [item for item in items if item.get("ad", "") == current_sel]
            
        if not items:
            items = [{"ad": "Örnek 1"}]
            
        base_title = "Toplu Çarşaf Liste : Öğretmenler" if is_teacher else "Toplu Çarşaf Liste : Sınıflar"
        
        # Grid parameters
        all_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        settings = self.data_store.get("settings", {})
        cnt = int(settings.get("day_count") or settings.get("days_count") or self.data_store.get("gun_sayisi", 5))
        days = settings.get("days") or settings.get("days_list") or all_days[:cnt]
        periods_per_day = int(settings.get("periods", 8))
        
        margin_x = 18
        margin_y = 16
        w = VW - (2 * margin_x)
        
        name_col_w = 80
        day_w = (w - name_col_w) / len(days)
        period_w = day_w / periods_per_day
        
        header_h = 24
        row_h = 16.5
        rows_per_page = 26
        
        total_pages = (len(items) + rows_per_page - 1) // rows_per_page
        if total_pages == 0: total_pages = 1
        
        for p_idx in range(total_pages):
            if p_idx > 0 and printer:
                printer.newPage()
                painter.fillRect(0, 0, VW, VH, Qt.white)
                
            cur_y = margin_y
            
            # --- Top Title & Date Bar ---
            painter.setFont(make_font(13, True))
            painter.setPen(QPen(QColor("#0F172A"), 1))
            painter.drawText(QRectF(margin_x, cur_y, w, 20), Qt.AlignLeft, f"{school_name} - {base_title}")
            
            painter.setFont(make_font(9.5, False))
            painter.setPen(QPen(QColor("#64748B"), 1))
            painter.drawText(QRectF(margin_x, cur_y, w, 20), Qt.AlignRight, f"Tarih: {date_str}  |  Sayfa: {p_idx+1}/{total_pages}")
            
            cur_y += 24
            
            # --- Table Header: Days & Periods ---
            painter.setPen(QPen(QColor("#0F172A"), 1.5))
            painter.setBrush(QBrush(QColor("#E2E8F0")))
            painter.drawRect(QRectF(margin_x, cur_y, name_col_w, header_h))
            painter.setFont(make_font(10, True))
            painter.setPen(QPen(QColor("#0F172A"), 1))
            painter.drawText(QRectF(margin_x, cur_y, name_col_w, header_h), Qt.AlignCenter, "Öğretmen" if is_teacher else "Sınıf")
            
            for d_idx, day_name in enumerate(days):
                dx = margin_x + name_col_w + d_idx * day_w
                painter.setPen(QPen(QColor("#0F172A"), 1.5))
                painter.setBrush(QBrush(QColor("#E2E8F0")))
                painter.drawRect(QRectF(dx, cur_y, day_w, header_h / 2))
                painter.setFont(make_font(10, True))
                painter.setPen(QPen(QColor("#0F172A"), 1))
                painter.drawText(QRectF(dx, cur_y, day_w, header_h / 2), Qt.AlignCenter, day_name)
                
                for p_offset in range(periods_per_day):
                    p = p_offset
                    px = dx + p_offset * period_w
                    painter.setPen(QPen(QColor("#0F172A"), 0.8))
                    painter.setBrush(QBrush(QColor("#F8FAFC")))
                    painter.drawRect(QRectF(px, cur_y + header_h / 2, period_w, header_h / 2))
                    painter.setFont(make_font(9.5, True))
                    painter.setPen(QPen(QColor("#334155"), 1))
                    painter.drawText(QRectF(px, cur_y + header_h / 2, period_w, header_h / 2), Qt.AlignCenter, str(p + 1))
            
            cur_y += header_h
            
            page_items = items[p_idx * rows_per_page : (p_idx + 1) * rows_per_page]
            used_subjects = {} # {abbr: full_name}
            
            for item in page_items:
                target_name = (item.get("ad") or item.get("name") or "").strip()
                
                painter.setPen(QPen(QColor("#0F172A"), 1.5))
                painter.setBrush(QBrush(QColor("#F8FAFC")))
                painter.drawRect(QRectF(margin_x, cur_y, name_col_w, row_h))
                painter.setPen(QPen(QColor("#0F172A"), 1))
                
                if is_teacher and item.get("kisa"):
                    display_name = item.get("kisa")
                elif not is_teacher:
                    import re
                    display_name = re.sub(r'\s*\([^)]*\)\s*$', '', target_name).strip()
                else:
                    display_name = target_name
                    
                # Dynamically fit font size so name never overflows
                font_sz = 11.0
                painter.setFont(make_font(font_sz, True))
                while painter.fontMetrics().horizontalAdvance(display_name) > (name_col_w - 6) and font_sz > 7.0:
                    font_sz -= 0.5
                    painter.setFont(make_font(font_sz, True))
                    
                painter.drawText(QRectF(margin_x + 2, cur_y, name_col_w - 4, row_h), Qt.AlignCenter, display_name)
                
                placements = self._get_pseudo_placements(target_name, is_teacher)
                
                for d_idx in range(len(days)):
                    dx = margin_x + name_col_w + d_idx * day_w
                    
                    p_offset = 0
                    while p_offset < periods_per_day:
                        p = p_offset
                        px = dx + p_offset * period_w
                        lesson = placements.get((d_idx, p))
                        if not lesson or str(lesson.get("subject_name", "")).strip().lower() in ["boş", "bos", "-", "—", ""]:
                            is_closed = False
                            if is_teacher:
                                for t in self.data_store.get("ogretmenler", []) or []:
                                    if (t.get("ad") or t.get("name") or "").strip() == target_name:
                                        toff = t.get("timeoff", [])
                                        if toff and d_idx < len(toff) and p < len(toff[d_idx]):
                                            is_closed = (toff[d_idx][p] == 0)
                                        break
                                if not is_closed:
                                    kisit = self.data_store.get("kisitlamalar", {}).get(target_name, {})
                                    if f"{d_idx},{p}" in kisit:
                                        is_closed = (kisit[f"{d_idx},{p}"] in (0, False))
                            else:
                                for c in self.data_store.get("siniflar", []) or []:
                                    if (c.get("ad") or c.get("name") or "").strip() == target_name:
                                        toff = c.get("timeoff", [])
                                        if toff and d_idx < len(toff) and p < len(toff[d_idx]):
                                            is_closed = (toff[d_idx][p] == 0)
                                        break
                                if not is_closed:
                                    kisit = self.data_store.get("kisitlamalar", {}).get(target_name, {})
                                    if f"{d_idx},{p}" in kisit:
                                        is_closed = (kisit[f"{d_idx},{p}"] in (0, False))

                            painter.setBrush(QBrush(QColor("#E2E8F0" if is_closed else "#FFFFFF")))
                            painter.setPen(QPen(QColor("#0F172A"), 0.8))
                            painter.drawRect(QRectF(px, cur_y, period_w, row_h))
                            if is_closed:
                                painter.setFont(make_font(8.5, True))
                                painter.setPen(QPen(QColor("#94A3B8"), 1))
                                painter.drawText(QRectF(px, cur_y, period_w, row_h), Qt.AlignCenter, "✕")
                            p_offset += 1
                            continue
                            
                        sname = lesson.get("subject_name", "")
                        if is_teacher:
                            raw_c = str(lesson.get("class_name") or lesson.get("teacher_name") or "")
                            if lesson.get("is_combined") and ("," in raw_c or "&" in raw_c or "+" in raw_c):
                                parts = [c.split("(")[0].strip().replace(" ", "").upper() for c in raw_c.replace("&", ",").replace("+", ",").split(",") if c.strip()]
                                if len(parts) == 1:
                                    cell_text = parts[0]
                                elif len(parts) >= 2:
                                    cell_text = f"{parts[0]}+{parts[1]}"
                            else:
                                cell_text = raw_c.split("(")[0].strip().replace(" ", "").upper()
                            if not cell_text:
                                cell_text = smart_abbr(sname)
                        else:
                            cell_text = smart_abbr(sname)
                            used_subjects[cell_text] = sname
                            
                        # Detect horizontal contiguous span on this day
                        span = 1
                        s1 = smart_abbr(sname)
                        c1 = str(lesson.get("class_name") or lesson.get("teacher_name") or "").strip().upper()
                        
                        while p_offset + span < periods_per_day:
                            next_p = p_offset + span
                            next_l = placements.get((d_idx, next_p))
                            if not next_l:
                                break
                            next_s = next_l.get("subject_name", "")
                            next_c = str(next_l.get("class_name") or next_l.get("teacher_name") or "").strip().upper()
                            c2 = next_c
                            s2 = smart_abbr(next_s)
                            
                            if is_teacher:
                                # In teacher sheet, if same class (or multi-hour continuous assignment)
                                if c1 and c1 == c2:
                                    span += 1
                                else:
                                    break
                            else:
                                # In class sheet, if same subject abbreviation
                                if s1 and s1 == s2:
                                    span += 1
                                else:
                                    break
                                
                        block_w = period_w * span
                        painter.setBrush(QBrush(QColor("#FFFFFF")))
                        painter.setPen(QPen(QColor("#0F172A"), 0.8))
                        painter.drawRect(QRectF(px, cur_y, block_w, row_h))
                        
                        if cell_text:
                            if span >= 2 and is_teacher and lesson.get("is_combined") and ("," in raw_c or "&" in raw_c):
                                parts = [c.split("(")[0].strip().replace(" ", "").upper() for c in raw_c.replace("&", ",").replace("+", ",").split(",") if c.strip()]
                                if len(parts) <= 3:
                                    full_text = "+".join(parts)
                                else:
                                    full_text = f"{parts[0]}+{parts[1]}+{len(parts)-2}"
                                if painter.fontMetrics().horizontalAdvance(full_text) < (block_w - 4):
                                    cell_text = full_text

                            font_sz = 10.0
                            painter.setFont(make_font(font_sz, True))
                            # Add newlines instead of + if it's too long
                            if "+" in cell_text and painter.fontMetrics().horizontalAdvance(cell_text) > (block_w - 2):
                                cell_text = cell_text.replace("+", "\n")
                            
                            while painter.fontMetrics().horizontalAdvance(cell_text) > (block_w - 2) and font_sz > 4.5:
                                font_sz -= 0.5
                                painter.setFont(make_font(font_sz, True))
                            painter.setPen(QPen(QColor("#0F172A"), 1))
                            
                            painter.save()
                            painter.setClipRect(QRectF(px + 1, cur_y + 1, block_w - 2, row_h - 2))
                            painter.drawText(QRectF(px + 1, cur_y + 1, block_w - 2, row_h - 2), Qt.AlignCenter | Qt.TextWordWrap, cell_text)
                            painter.restore()
                            
                        p_offset += span
                        
                cur_y += row_h
                
            # --- Draw Thick Day Divider Strokes across table height ---
            table_top_y = margin_y + 24
            table_bottom_y = cur_y
            for d_idx in range(len(days) + 1):
                dx = margin_x + name_col_w + d_idx * day_w
                painter.setPen(QPen(QColor("#0F172A"), 2.2))
                painter.drawLine(QPointF(dx, table_top_y), QPointF(dx, table_bottom_y))
                
            # --- Structured Legend Section Immediately Under Table ---
            leg_start_y = cur_y + 8
            if not is_teacher:
                if not used_subjects:
                    for d_item in self.data_store.get("dersler", []):
                        d_name = d_item.get("ad", "").strip()
                        if d_name:
                            used_subjects[smart_abbr(d_name)] = d_name

                legend_items = sorted([(k, v) for k, v in used_subjects.items() if k and v], key=lambda x: x[0])
                if legend_items:
                    num_cols = 5
                    col_w = (w - 20) / num_cols
                    item_h = 16
                    num_rows = (len(legend_items) + num_cols - 1) // num_cols
                    box_h = 24 + num_rows * item_h + 8
                    
                    # Boundary safety
                    if leg_start_y + box_h > VH - margin_y - 25:
                        box_h = max(30, VH - margin_y - 25 - leg_start_y)
                        
                    painter.setPen(QPen(QColor("#CBD5E1"), 1.2))
                    painter.setBrush(QBrush(QColor("#F8FAFC")))
                    painter.drawRoundedRect(QRectF(margin_x, leg_start_y, w, box_h), 5, 5)
                    
                    # Legend Header
                    painter.setFont(make_font(9.5, True))
                    painter.setPen(QPen(QColor("#1E293B"), 1))
                    painter.drawText(QRectF(margin_x + 10, leg_start_y + 4, w - 20, 16), Qt.AlignLeft | Qt.AlignVCenter, "Ders Kısaltmaları ve Açıklamaları:")
                    
                    # Legend Items Grid
                    for idx, (abbr, full_name) in enumerate(legend_items):
                        c_idx = idx % num_cols
                        r_idx = idx // num_cols
                        
                        item_x = margin_x + 12 + c_idx * col_w
                        item_y = leg_start_y + 22 + r_idx * item_h
                        
                        if item_y + item_h <= leg_start_y + box_h:
                            painter.setFont(make_font(8.5, True))
                            painter.setPen(QPen(QColor("#0F172A"), 1))
                            prefix = f"• {abbr}: "
                            p_w = painter.fontMetrics().horizontalAdvance(prefix)
                            painter.drawText(QRectF(item_x, item_y, p_w + 4, item_h), Qt.AlignLeft | Qt.AlignVCenter, prefix)
                            
                            painter.setFont(make_font(8.5, False))
                            painter.setPen(QPen(QColor("#334155"), 1))
                            val_rect = QRectF(item_x + p_w, item_y, col_w - p_w - 6, item_h)
                            painter.drawText(val_rect, Qt.AlignLeft | Qt.AlignVCenter, full_name)
                            
                    leg_bottom = leg_start_y + box_h + 8
                else:
                    leg_bottom = leg_start_y + 8

                # Footer
                painter.setFont(make_font(8.5, False))
                painter.setPen(QPen(QColor("#64748B"), 1))
                painter.drawText(QRectF(margin_x, min(leg_bottom, VH - margin_y + 14), w / 2, 18), Qt.AlignLeft, f"Ders Planı Oluşturuldu: {date_str}")
                painter.drawText(QRectF(margin_x + w / 2, min(leg_bottom, VH - margin_y + 14), w / 2, 18), Qt.AlignRight, "Chenkron Ders Planlama")


    def _render_tablo_dersler(self, painter, printer, VW, VH):
        """Tablo Olarak: Dersler. Her ders ayrı bir sayfada."""
        import datetime
        date_str = datetime.datetime.now().strftime("%d.%m.%Y")
        school_name = self.data_store.get("okul_adi") or self.data_store.get("settings", {}).get("school_name", "Okul Adı")
        
        dersler = self.data_store.get("dersler", [])
        if not dersler:
            dersler = [{"ad": "MATEMATİK", "kisa": "MAT"}]
            
        margin_x, margin_y = 60, 60
        w = VW - (2 * margin_x)
        h = VH - (2 * margin_y)
        
        all_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        short_days = ["Pa", "Sa", "Ça", "Pe", "Cu", "Cts", "Paz"]
        settings = self.data_store.get("settings", {})
        cnt = int(settings.get("day_count") or settings.get("days_count") or self.data_store.get("gun_sayisi", 5))
        saved_days = settings.get("days") or settings.get("days_list") or all_days[:cnt]
        days = [short_days[all_days.index(d)] if d in all_days else d[:3] for d in saved_days]
        periods = int(settings.get("periods", 8))
        times = get_bell_times(self.data_store, periods, separator=" - ")
        
        day_col_w = 80
        grid_w = w - day_col_w
        period_w = grid_w / periods
        
        header_h = 60
        row_h = (h - header_h - 80) / len(days) # 80 is for title space
        
        for i, ders in enumerate(dersler):
            if i > 0:
                printer.newPage()
                painter.fillRect(0, 0, VW, VH, Qt.white)
                
            sname = ders.get("ad", "")
            short_name = ders.get("kisa") or get_subject_badge(sname, self.data_store)
            
            # Title
            painter.setFont(make_font(36, False))
            painter.setPen(QPen(QColor("#000000"), 1))
            painter.drawText(QRectF(margin_x, margin_y, w, 50), Qt.AlignCenter, short_name)
            
            # School Name
            painter.setFont(make_font(10, False))
            painter.drawText(QRectF(margin_x, margin_y + 45, w, 20), Qt.AlignLeft | Qt.AlignBottom, school_name)
            
            table_y = margin_y + 70
            
            # Grid
            painter.setPen(QPen(QColor("#000000"), 1.5))
            painter.setBrush(Qt.NoBrush)
            
            # Empty top-left
            painter.drawRect(QRectF(margin_x, table_y, day_col_w, header_h))
            
            # Column headers (Periods & Times)
            for p in range(periods):
                px = margin_x + day_col_w + p * period_w
                painter.drawRect(QRectF(px, table_y, period_w, header_h))
                
                painter.setFont(make_font(16, False))
                painter.drawText(QRectF(px, table_y + 5, period_w, header_h / 2), Qt.AlignCenter | Qt.AlignBottom, str(p + 1))
                
                painter.setFont(make_font(8.5, False))
                t_str = times[p]
                painter.drawText(QRectF(px, table_y + header_h / 2, period_w, header_h / 2), Qt.AlignCenter | Qt.AlignTop, t_str)
                
            cur_y = table_y + header_h
            
            # Gather all placements for this subject across all classes
            subj_placements = {} # (day, period) -> list of (class, teacher)
            
            # Ensure we are reading live grid data or saved grid_placements
            grid_data = self.data_store.get("grid_placements", [])
            for item in grid_data:
                if item.get("subject_name") == sname or item.get("subject") == sname:
                    r = int(item.get("period", item.get("row", 0)))
                    c = int(item.get("day", item.get("col", 0)))
                    dur = int(item.get("duration", 1))
                    cls = item.get("class_name") or item.get("class") or ""
                    tchr = item.get("teacher_name") or item.get("teacher") or ""
                    
                    for off in range(dur):
                        if (c, r + off) not in subj_placements:
                            subj_placements[(c, r + off)] = []
                        subj_placements[(c, r + off)].append((cls, tchr))
            
            # Rows (Days)
            for d_idx, day_name in enumerate(days):
                ry = cur_y + d_idx * row_h
                painter.drawRect(QRectF(margin_x, ry, day_col_w, row_h))
                painter.setFont(make_font(24, False))
                painter.drawText(QRectF(margin_x, ry, day_col_w, row_h), Qt.AlignCenter, day_name)
                
                for p in range(periods):
                    px = margin_x + day_col_w + p * period_w
                    painter.drawRect(QRectF(px, ry, period_w, row_h))
                    
                    placements = subj_placements.get((d_idx, p), [])
                    if placements:
                        # Draw first placement (typically there's only 1 or 2 classes doing this subject at this time)
                        cls, tchr = placements[0]
                        if "," in cls or "&" in cls or "+" in cls:
                            parts = [c.split("(")[0].strip().replace(" ", "").upper() for c in cls.replace("&", ",").replace("+", ",").split(",") if c.strip()]
                            cls_str = "+".join(parts) if parts else ""
                        else:
                            cls_str = cls.split("(")[0].strip().replace(" ", "").upper()
                        
                        font_sz = 12
                        painter.setFont(make_font(font_sz, True))
                        while painter.fontMetrics().horizontalAdvance(cls_str) > (period_w - 4) and font_sz > 5.0:
                            font_sz -= 0.5
                            painter.setFont(make_font(font_sz, True))
                            
                        painter.drawText(QRectF(px, ry, period_w, row_h / 2), Qt.AlignCenter | Qt.AlignBottom, cls_str)
                        
                        painter.setFont(make_font(10, False))
                        if tchr:
                            # Short teacher name (e.g. H. ARMAN)
                            parts = tchr.split()
                            if len(parts) >= 2:
                                t_str = f"{parts[0][0].upper()}. {parts[1].upper()}"
                            else:
                                t_str = tchr.upper()
                            painter.drawText(QRectF(px, ry + row_h / 2, period_w, row_h / 2), Qt.AlignCenter | Qt.AlignTop, t_str)
            
            # Footer
            painter.setFont(make_font(8, False))
            painter.drawText(QRectF(margin_x, cur_y + len(days) * row_h + 10, w / 2, 20), Qt.AlignLeft, f"Ders Planı Oluşturuldu:{date_str}")
            painter.drawText(QRectF(margin_x + w / 2, cur_y + len(days) * row_h + 10, w / 2, 20), Qt.AlignRight, "Chenkron Ders Planlama")
