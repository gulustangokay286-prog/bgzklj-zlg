"""
timetable_grid.py  –  Haftalık ders programı tablosu (drag-drop + sağ tık menüsü destekli)
"""
import json
from PySide6.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QAbstractItemView, QFrame, QScrollArea, QMenu, QInputDialog,
    QMessageBox, QStyledItemDelegate, QStyle
)
from PySide6.QtCore import Qt, QMimeData, Signal, QByteArray, QRect
from PySide6.QtGui import QFont, QColor, QBrush, QDrag, QPainter, QPixmap, QAction, QPen, QLinearGradient, QIcon, QPainterPath

def make_context_icon(symbol: str, color1: str, color2: str) -> QIcon:
    pix = QPixmap(24, 24)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 0, 24)
    grad.setColorAt(0, QColor(color1))
    grad.setColorAt(1, QColor(color2))
    p.setBrush(QBrush(grad))
    p.setPen(QPen(QColor(0,0,0,50), 1))
    p.drawRoundedRect(2, 2, 20, 20, 4, 4)
    p.setPen(QPen(Qt.white, 1))
    p.setFont(QFont("Segoe UI", 10, QFont.Bold))
    p.drawText(2, 2, 20, 20, Qt.AlignCenter, symbol)
    p.end()
    return QIcon(pix)


DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

def make_grid_action_icon(name: str, size: int = 24) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    
    if name == 'siniflar':
        # Modern 3D School / Classroom building
        grad = QLinearGradient(0, 0, 0, size)
        grad.setColorAt(0, QColor('#3B82F6'))
        grad.setColorAt(1, QColor('#1D4ED8'))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(3, 8, size - 6, size - 11, 3, 3)
        path = QPainterPath()
        path.moveTo(size/2, 2)
        path.lineTo(size - 2, 8)
        path.lineTo(2, 8)
        path.closeSubpath()
        grad_roof = QLinearGradient(0, 0, 0, 8)
        grad_roof.setColorAt(0, QColor('#60A5FA'))
        grad_roof.setColorAt(1, QColor('#2563EB'))
        p.setBrush(QBrush(grad_roof))
        p.drawPath(path)
        p.setBrush(QBrush(QColor('#FFFFFF')))
        p.drawRoundedRect(size/2 - 2.5, size - 9, 5, 6, 1.5, 1.5)
    elif name == 'ogretmenler':
        # Modern Teacher / User icon
        grad_head = QLinearGradient(0, 2, 0, 12)
        grad_head.setColorAt(0, QColor('#F59E0B'))
        grad_head.setColorAt(1, QColor('#D97706'))
        p.setBrush(QBrush(grad_head))
        p.setPen(Qt.NoPen)
        p.drawEllipse(size/2 - 4.5, 2, 9, 9)
        path = QPainterPath()
        path.moveTo(size/2 - 7, size - 3)
        path.quadTo(size/2 - 7, 13, size/2, 13)
        path.quadTo(size/2 + 7, 13, size/2 + 7, size - 3)
        path.closeSubpath()
        grad_body = QLinearGradient(0, 13, 0, size)
        grad_body.setColorAt(0, QColor('#10B981'))
        grad_body.setColorAt(1, QColor('#059669'))
        p.setBrush(QBrush(grad_body))
        p.drawPath(path)
    elif name == 'lock_open':
        p.setPen(QPen(QColor('#DC2626'), 2))
        p.setBrush(Qt.NoBrush)
        p.drawArc(size/2 - 4, 3, 8, 8, 0, 180 * 16)
        grad = QLinearGradient(0, 9, 0, size - 3)
        grad.setColorAt(0, QColor('#F87171'))
        grad.setColorAt(1, QColor('#DC2626'))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(4, 9, size - 8, size - 12, 3, 3)
        p.setBrush(QBrush(QColor('#FFFFFF')))
        p.drawEllipse(size/2 - 1.5, 12, 3, 3)
        p.drawRect(size/2 - 1, 14, 2, 3)
    elif name == 'lock_closed':
        p.setPen(QPen(QColor('#7C3AED'), 2))
        p.setBrush(Qt.NoBrush)
        p.drawArc(size/2 - 4, 3, 8, 8, 0, 180 * 16)
        p.drawLine(size/2 - 4, 7, size/2 - 4, 10)
        p.drawLine(size/2 + 4, 7, size/2 + 4, 10)
        grad = QLinearGradient(0, 9, 0, size - 3)
        grad.setColorAt(0, QColor('#A78BFA'))
        grad.setColorAt(1, QColor('#7C3AED'))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(4, 9, size - 8, size - 12, 3, 3)
        p.setBrush(QBrush(QColor('#FFFFFF')))
        p.drawEllipse(size/2 - 1.5, 12, 3, 3)
        p.drawRect(size/2 - 1, 14, 2, 3)
    elif name == 'check_circle':
        grad = QLinearGradient(0, 0, 0, size)
        grad.setColorAt(0, QColor('#22C55E'))
        grad.setColorAt(1, QColor('#16A34A'))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, size - 4, size - 4)
        p.setPen(QPen(QColor('#FFFFFF'), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(6, size/2 + 1, size/2 - 1, size - 7)
        p.drawLine(size/2 - 1, size - 7, size - 6, 7)
    elif name == 'alert_triangle':
        path = QPainterPath()
        path.moveTo(size/2, 2)
        path.lineTo(size - 2, size - 3)
        path.lineTo(2, size - 3)
        path.closeSubpath()
        grad = QLinearGradient(0, 2, 0, size)
        grad.setColorAt(0, QColor('#FBBF24'))
        grad.setColorAt(1, QColor('#D97706'))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawPath(path)
        p.setPen(QPen(QColor('#FFFFFF'), 2, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(size/2, 7, size/2, size - 9)
        p.drawPoint(size/2, size - 6)
    elif name == 'download':
        grad = QLinearGradient(0, 0, 0, size)
        grad.setColorAt(0, QColor('#38BDF8'))
        grad.setColorAt(1, QColor('#0284C7'))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(4, 8, 8, 8)
        p.drawEllipse(10, 4, 10, 10)
        p.drawEllipse(size - 12, 8, 8, 8)
        p.drawRect(8, 10, size - 16, 6)
        p.setPen(QPen(QColor('#FFFFFF'), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(size/2, 10, size/2, size - 4)
        p.drawLine(size/2 - 3, size - 7, size/2, size - 4)
        p.drawLine(size/2 + 3, size - 7, size/2, size - 4)
    elif name == 'toggle_panel':
        p.setPen(QPen(QColor('#64748B'), 1.5))
        p.setBrush(QBrush(QColor('#F1F5F9')))
        p.drawRoundedRect(3, 3, size - 6, size - 6, 3, 3)
        p.setBrush(QBrush(QColor('#3B82F6')))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(3, 3, 6, size - 6, 2, 2)
    elif name == 'edit':
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor('#10B981')))
        path = QPainterPath()
        path.moveTo(size - 4, 4)
        path.lineTo(size - 7, 1)
        path.lineTo(4, size - 10)
        path.lineTo(1, size - 1)
        path.lineTo(10, size - 4)
        path.closeSubpath()
        p.drawPath(path)
    elif name == 'palette':
        p.setPen(Qt.NoPen)
        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0, QColor('#EC4899'))
        grad.setColorAt(0.5, QColor('#8B5CF6'))
        grad.setColorAt(1, QColor('#3B82F6'))
        p.setBrush(QBrush(grad))
        p.drawEllipse(2, 2, size - 4, size - 4)
        p.setBrush(QBrush(QColor('#FFFFFF')))
        p.drawEllipse(6, 6, 3, 3)
        p.drawEllipse(12, 5, 3, 3)
        p.drawEllipse(16, 9, 3, 3)
    p.end()
    return QIcon(pix)

def get_subject_abbr(subject_name: str) -> str:
    if not subject_name: return ""
    s = subject_name.strip()
    
    mapping = {
        "MATEMATİK": "MAT", "FİZİK": "F", "FİZ": "F", "BİYOLOJİ": "BİY", "KİMYA": "KİM",
        "GEOMETRİ": "GEO", "TARİH": "TAR", "COĞRAFYA": "COĞ", "TÜRKÇE": "TÜR",
        "EDEBİYAT": "EDB", "TÜRK DİLİ VE EDEBİYATI": "TDE", "GÖRSEL SANATLAR": "GÖR",
        "İNGİLİZCE": "İNG", "ALMANCA": "ALM", "FRANSIZCA": "FRA", "DİN": "DİN",
        "DİN KÜLTÜRÜ": "DİN", "DİN KÜLTÜRÜ VE AHLAK BİLGİSİ": "DİN", "FELSEFE": "FEL",
        "BEDEN": "BDN", "BEDEN EĞİTİMİ": "BDN", "BEDEN EĞİTİMİ VE SPOR": "BDN",
        "MÜZİK": "MÜZ", "REHBERLİK": "REH", "SAĞLIK": "SAĞ", "ASTRONOMİ": "AST"
    }
    
    import re
    m = re.search(r'^(.*?)\s*(\d+)$', s)
    num_suffix = ""
    if m:
        base_title = m.group(1).strip().upper()
        num_suffix = m.group(2)
    else:
        base_title = s.upper()
        
    if base_title in mapping:
        return f"{mapping[base_title]}{num_suffix}"
        
    for k, v in mapping.items():
        if base_title.startswith(k):
            return f"{v}{num_suffix}"
            
    if len(base_title) >= 3:
        return f"{base_title[:3]}{num_suffix}"
    return f"{base_title}{num_suffix}"


from PySide6.QtCore import QRect

class AsCTimetableHeader(QHeaderView):
    """aSc Timetables style two-level header: Days on top spanning periods, Period numbers below."""
    def __init__(self, periods: int = 8, days_list: list = None, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.periods = max(1, int(periods))
        self.days_list = days_list or DAYS[:5]
        self.setFixedHeight(36)
        self.setSectionResizeMode(QHeaderView.Fixed)
        self.setDefaultSectionSize(44)
        self.setMinimumSectionSize(20)
        self.sectionResized.connect(lambda *args: self.viewport().update())
        self.geometriesChanged.connect(lambda *args: self.viewport().update())

    def set_config(self, periods: int, days_list: list):
        self.periods = max(1, int(periods))
        self.days_list = days_list
        self.viewport().update()

    def paintSection(self, painter, rect, logicalIndex):
        pass  # Suppress default section painting to prevent overlapping/glitched text

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setClipping(False)  # Completely disable painter clipping so the entire header area is cleanly repainted
        
        vw = self.viewport().width()
        vh = self.viewport().height()
        
        # Fill header background
        painter.fillRect(self.viewport().rect(), QColor("#CBD5E1"))
        
        total_sections = self.count()
        if total_sections == 0:
            painter.end()
            return
            
        periods = self.periods
        days_list = self.days_list
        
        # ── SINGLE ENTITY VIEW (1 column per day)
        if total_sections == len(days_list):
            for col_idx, day_name in enumerate(days_list):
                x = self.sectionViewportPosition(col_idx)
                w = self.sectionSize(col_idx)
                if x + w <= 0 or x >= vw:
                    continue
                rect = QRect(x, 0, w, vh)
                painter.setPen(QPen(QColor("#94A3B8"), 1))
                painter.setBrush(QBrush(QColor("#E2E8F0")))
                painter.drawRect(rect)
                
                painter.setPen(QPen(QColor("#0F172A")))
                painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
                painter.drawText(rect, Qt.AlignCenter, day_name)
            painter.end()
            return
            
        # ── MULTI-SHEET VIEW (Days on top row y=0..18, Period numbers on bottom row y=18..36)
        # 1. Day headers (Top row)
        for d_idx, day_name in enumerate(days_list):
            start_col = d_idx * periods
            end_col = start_col + periods - 1
            if start_col >= total_sections:
                break
            actual_end_col = min(end_col, total_sections - 1)
            x_start = self.sectionViewportPosition(start_col)
            x_end = self.sectionViewportPosition(actual_end_col) + self.sectionSize(actual_end_col)
            day_w = x_end - x_start
            
            if x_end <= 0 or x_start >= vw:
                continue
                
            day_rect = QRect(x_start, 0, day_w, 18)
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.setBrush(QBrush(QColor("#E2E8F0")))
            painter.drawRect(day_rect)
            
            painter.setPen(QPen(QColor("#0F172A")))
            font_day = QFont("Segoe UI", 8, QFont.Bold)
            painter.setFont(font_day)
            
            # Keep day label visible and centered in the viewport portion of that day
            vis_left = max(x_start, 0)
            vis_right = min(x_end, vw)
            if vis_right > vis_left:
                vis_rect = QRect(vis_left, 0, vis_right - vis_left, 18)
                if vis_rect.width() >= 25:
                    painter.drawText(vis_rect, Qt.AlignCenter, day_name)
                elif not day_rect.isEmpty():
                    painter.drawText(day_rect, Qt.AlignCenter, day_name)
            
        # 2. Period headers (Bottom row)
        for col_idx in range(total_sections):
            x = self.sectionViewportPosition(col_idx)
            w = self.sectionSize(col_idx)
            if x + w <= 0 or x >= vw:
                continue
            period_num = (col_idx % periods) + 1
            
            period_rect = QRect(x, 18, w, 18)
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.setBrush(QBrush(QColor("#F8FAFC")))
            painter.drawRect(period_rect)
            
            painter.setPen(QPen(QColor("#334155")))
            font_p = QFont("Segoe UI", 7, QFont.Bold)
            painter.setFont(font_p)
            painter.drawText(period_rect, Qt.AlignCenter, str(period_num))
            
        painter.end()


class DraggableLessonCard(QLabel):
    def __init__(self, lesson_id: int, subject_name: str, color: str, duration: int = 1, teacher: str = "", class_name: str = "", display_mode: str = "classes", parent=None):
        super().__init__(parent)
        self.lesson_id = lesson_id
        self.subject_name = subject_name
        self.color = color
        self.duration = duration
        self.teacher = teacher
        self.class_name = class_name
        self.display_mode = display_mode
        
        abbr = get_subject_abbr(subject_name)
        t_short = ""
        if teacher and teacher != "Öğretmen":
            parts = teacher.strip().split()
            if len(parts) >= 2:
                t_short = f"{parts[0]} {parts[-1][0]}."
            else:
                t_short = parts[0]
                
        is_comb = ("," in class_name or "&" in class_name or "+" in class_name)
        if is_comb:
            c_clean = "+".join([c.strip().split("(")[0] for c in class_name.replace("&", ",").replace("+", ",").split(",") if c.strip()])
            if display_mode == "teachers":
                display_text = f"<b>🔗 {c_clean}</b>"
            else:
                display_text = f"<b>🔗 {abbr}</b> <span style='font-size:8px;'>({c_clean})</span>"
        elif display_mode == "teachers":
            # For teacher view, highlight class name in bold and subject name as subtitle
            c_clean = class_name.replace(" ", "").upper()
            display_text = f"<b>{c_clean}</b>"
            if abbr:
                display_text += f" <span style='font-weight:normal; font-size:8.5px; opacity:0.95;'>{abbr}</span>"
        else:
            display_text = f"<b>{abbr}</b>"
            if t_short:
                display_text += f" <span style='font-weight:normal; font-size:8.5px; opacity:0.95;'>{t_short}</span>"
                
        if duration > 1:
            display_text += f" <span style='background:rgba(255,255,255,0.35); border-radius:2px; padding:0 3px; font-size:8px; font-weight:bold;'>{duration}h</span>"
            
        self.setText(display_text)
        self.setAlignment(Qt.AlignCenter)
        card_width = max(64, 52 + (duration - 1)*18)
        self.setFixedSize(card_width, 32)
        
        c = QColor(color)
        luminance = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
        text_color = "#FFFFFF" if luminance < 160 else "#111111"
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: {text_color};
                font-family: system-ui, -apple-system, sans-serif;
                font-size: 10px;
                border: 1px solid rgba(0, 0, 0, 0.22);
                border-radius: 4px;
                padding: 1px 4px;
            }}
            QLabel:hover {{
                border: 2px solid #0078D7;
            }}
        """)
        self.setCursor(Qt.OpenHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_card_context_menu)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            
            data = {
                "lesson_id": self.lesson_id,
                "subject_name": self.subject_name,
                "color": self.color,
                "duration": self.duration,
                "teacher": self.teacher,
                "class_name": self.class_name
            }
            mime.setData("application/x-lesson", QByteArray(json.dumps(data).encode()))
            drag.setMimeData(mime)
            
            pix = self.grab()
            drag.setPixmap(pix)
            drag.setHotSpot(event.pos())
            
            drag.exec_(Qt.MoveAction)

    def _show_card_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #FFFFFF; border: 1px solid #CCC; font-family: 'Segoe UI'; font-size: 12px; }
            QMenu::item { padding: 6px 22px; }
            QMenu::item:selected { background: #0078D7; color: white; }
            QMenu::separator { height: 1px; background: #DDD; margin: 3px 10px; }
        """)
        
        act_palette = menu.addAction(make_context_icon("🎨", "#E91E63", "#C2185B"), f"🎨 {self.subject_name} Rengini Ayarla (Renk Paleti)...")
        menu.addSeparator()
        act_2_2 = menu.addAction(make_context_icon("2+2", "#AB47BC", "#7B1FA2"), "2+2 Saat (2 İkili Blok)")
        act_2_1 = menu.addAction(make_context_icon("2+1", "#AB47BC", "#7B1FA2"), "2+1 Saat (1 İkili + 1 Tekli)")
        act_2_2_1 = menu.addAction(make_context_icon("2+2+1", "#AB47BC", "#7B1FA2"), "2+2+1 Saat (5 Saat)")
        act_3_2 = menu.addAction(make_context_icon("3+2", "#AB47BC", "#7B1FA2"), "3+2 Saat (5 Saat)")
        act_1_1_1 = menu.addAction(make_context_icon("1+1+1", "#AB47BC", "#7B1FA2"), "1+1+1 Saat (3 Tekli)")
        act_custom = menu.addAction(make_context_icon("✏️", "#4CAF50", "#2E7D32"), "Özel Dağılım Yapısı Gir...")
        menu.addSeparator()
        act_del = menu.addAction(make_context_icon("X", "#EF5350", "#C62828"), "Atamayı Sil (Kaldır)")
        
        action = menu.exec_(self.mapToGlobal(pos))
        
        if not action:
            return
            
        win = self.window()
        data_store = getattr(win, "data_store", None)
        
        if action == act_palette:
            from dialogs.color_picker_dialog import ModernColorPickerDialog, update_subject_color_globally
            new_color = ModernColorPickerDialog.pick_color(
                initial_color=self.color,
                parent=win or self,
                title=f"{self.subject_name} — Renk Seçimi",
                data_store=data_store,
                subject_name=self.subject_name
            )
            if new_color and new_color.isValid():
                new_hex = new_color.name()
                self.color = new_hex
                lum = (0.299 * new_color.red() + 0.587 * new_color.green() + 0.114 * new_color.blue())
                text_color = "#FFFFFF" if lum < 160 else "#111111"
                self.setStyleSheet(f"""
                    QLabel {{
                        background-color: {new_hex};
                        color: {text_color};
                        font-family: system-ui, -apple-system, sans-serif;
                        font-size: 10px;
                        border: 1px solid rgba(0, 0, 0, 0.22);
                        border-radius: 4px;
                        padding: 1px 4px;
                    }}
                    QLabel:hover {{
                        border: 2px solid #0078D7;
                    }}
                """)
                update_subject_color_globally(self, data_store, self.subject_name, new_hex)
            return

        parts = None
        if action == act_2_2:
            parts = [2, 2]
        elif action == act_2_1:
            parts = [2, 1]
        elif action == act_2_2_1:
            parts = [2, 2, 1]
        elif action == act_3_2:
            parts = [3, 2]
        elif action == act_1_1_1:
            parts = [1, 1, 1]
        elif action == act_custom:
            val, ok = QInputDialog.getText(self, "Özel Dağılım", "Saat Dağılımı (Örn: 2+2 veya 1+1+1):", text=f"{self.duration}")
            if ok and val.strip():
                try:
                    parts = [int(p.strip()) for p in val.replace(",", "+").split("+") if p.strip()]
                except Exception:
                    pass
        elif action == act_del:
            if data_store and "atamalar" in data_store:
                data_store["atamalar"] = [
                    a for a in data_store["atamalar"] 
                    if not (a.get("subject", "").strip().upper() == self.subject_name.strip().upper() and 
                            a.get("class", "").strip().upper() == self.class_name.strip().upper() and
                            a.get("teacher", "").strip().upper() == self.teacher.strip().upper())
                ]
                if win:
                    if hasattr(win, "save_db"): win.save_db()
                    if hasattr(win, "_refresh_tree"): win._refresh_tree()
                    if hasattr(win, "_refresh_grid"): win._refresh_grid()
            return
            
        if parts and data_store:
            if "atamalar" in data_store:
                for a in data_store["atamalar"]:
                    if (a.get("subject", "").strip().upper() == self.subject_name.strip().upper() and 
                        a.get("class", "").strip().upper() == self.class_name.strip().upper() and
                        a.get("teacher", "").strip().upper() == self.teacher.strip().upper()):
                        a["type"] = "+".join(map(str, parts))
                        a["distribution"] = parts
                        a["duration"] = sum(parts)
                        break
            if win:
                if hasattr(win, "save_db"): win.save_db()
                if hasattr(win, "_refresh_tree"): win._refresh_tree()
                if hasattr(win, "_refresh_grid"): win._refresh_grid()


class UnplacedLessonsDock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(54)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:horizontal { height: 5px; background: transparent; margin: 0; }
            QScrollBar::handle:horizontal { background: #CBD5E1; border-radius: 2px; }
            QScrollBar::handle:horizontal:hover { background: #94A3B8; }
        """)
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(8, 0, 8, 0)
        self.container_layout.setSpacing(8)
        self.container_layout.setAlignment(Qt.AlignLeft)
        
        scroll.setWidget(self.container)
        self.layout.addWidget(scroll)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-lesson"):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-lesson"):
            try:
                data = json.loads(event.mimeData().data("application/x-lesson").data().decode())
                if data.get("is_move"):
                    orig_r = data.get("origin_row", -1)
                    orig_c = data.get("origin_col", -1)
                    win = self.window()
                    grid = getattr(win, "_grid", None)
                    if grid and orig_r >= 0 and orig_c >= 0:
                        grid.table._delete_lesson_at(orig_r, orig_c)
            except Exception as e:
                print("Dock drop error:", e)
            event.accept()

    def load_unplaced(self, lessons_data, has_assignments=True, display_mode="classes"):
        self.container.setUpdatesEnabled(False)
        try:
            # clear existing
            while self.container_layout.count():
                item = self.container_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                    
            if not lessons_data:
                self.container_layout.setAlignment(Qt.AlignCenter)
                msg_widget = QWidget()
                msg_widget.setStyleSheet("background: transparent;")
                msg_layout = QHBoxLayout(msg_widget)
                msg_layout.setContentsMargins(0, 0, 0, 0)
                msg_layout.setSpacing(8)
                msg_layout.setAlignment(Qt.AlignCenter)
                
                icon_lbl = QLabel()
                icon_lbl.setStyleSheet("background: transparent; border: none;")
                text_lbl = QLabel()
                text_lbl.setStyleSheet("background: transparent; border: none;")
                
                if not has_assignments:
                    icon_lbl.setPixmap(make_grid_action_icon("alert_triangle", 20).pixmap(20, 20))
                    text_lbl.setText("Bu sınıfa / öğretmene henüz hiç ders atanmadı. Lütfen 'Ders Atama' bölümünden tanımlayın.")
                    text_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    text_lbl.setStyleSheet("color: #B45309; background: transparent; border: none;")
                else:
                    icon_lbl.setPixmap(make_grid_action_icon("check_circle", 20).pixmap(20, 20))
                    text_lbl.setText("Bu sınıfın / öğretmenin tüm dersleri başarıyla programa yerleştirildi.")
                    text_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    text_lbl.setStyleSheet("color: #15803D; background: transparent; border: none;")
                    
                msg_layout.addWidget(icon_lbl)
                msg_layout.addWidget(text_lbl)
                
                self.container_layout.addWidget(msg_widget)
                return

            self.container_layout.setAlignment(Qt.AlignLeft)
            for l in lessons_data:
                dur = l.get("duration", 1)
                teacher = l.get("teacher", "")
                cls_name = l.get("class_name", "")
                card = DraggableLessonCard(l["id"], l["subject_name"], l["color"], duration=dur, teacher=teacher, class_name=cls_name, display_mode=display_mode)
                self.container_layout.addWidget(card)
        finally:
            self.container.setUpdatesEnabled(True)

    def update_list(self, data_store: dict = None, display_mode: str = None):
        if not data_store:
            return
        if display_mode is None:
            grid = self.parent()
            display_mode = getattr(grid, "current_view_mode", "classes") if grid else "classes"
            
        atamalar = data_store.get("atamalar", [])
        grid_placements = data_store.get("grid_placements", [])
        from dialogs.color_picker_dialog import resolve_subject_color
        unplaced_cards = []
        for idx, a in enumerate(atamalar):
            s_name = a.get("subject", "")
            c_name = a.get("class", "")
            t_name = a.get("teacher", "")
            dur = int(a.get("duration", 1))
            color = resolve_subject_color(s_name, data_store)
            
            placed_count = 0
            for p in grid_placements:
                p_s = p.get("subject_name") or p.get("subject", "")
                p_c = p.get("class_name") or p.get("class", "")
                p_t = p.get("teacher_name") or p.get("teacher", "")
                if p_s == s_name and (not c_name or p_c == c_name) and (not t_name or p_t == t_name):
                    placed_count += int(p.get("duration", 1))
                    
            remaining = dur - placed_count
            if remaining > 0:
                unplaced_cards.append({
                    "id": idx + 1,
                    "subject_name": s_name,
                    "color": color,
                    "duration": remaining,
                    "teacher": t_name,
                    "class_name": c_name
                })
        self.load_unplaced(unplaced_cards, has_assignments=bool(atamalar), display_mode=display_mode)


class TimetableCellDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        rect = option.rect
        table = self.parent()
        grid = table.parent() if table else None
        
        row = index.row()
        col = index.column()
        
        # Check placed lesson info
        orig_r, orig_c, orig_dur, info = table._get_lesson_origin(row, col) if hasattr(table, "_get_lesson_origin") else (row, col, 1, None)
        if not info and grid and hasattr(grid, "_placed_lessons"):
            info = grid._placed_lessons.get((row, col))
            
        bg_brush = index.data(Qt.BackgroundRole)
        text = index.data(Qt.DisplayRole)
        clean_str = str(text).replace("🔒", "").strip() if text else ""
        
        is_locked = bool(info and info.get("locked"))
        
        # Get subject and teacher from info
        subject_name = ""
        teacher_name = ""
        if info:
            subject_name = info.get("subject_name") or info.get("subject") or ""
            teacher_name = info.get("teacher_name") or info.get("teacher") or ""
            
        # 1. Determine cell background color - prefer subject_name from info
        cell_color = None
        win = table.window() if table and hasattr(table, "window") else None
        data_store = getattr(win, "data_store", None)
        
        color_key = subject_name or clean_str
        if color_key:
            from dialogs.color_picker_dialog import resolve_subject_color
            resolved_hex = resolve_subject_color(color_key, data_store)
            cell_color = QColor(resolved_hex)
        elif info and info.get("color"):
            c = QColor(info["color"])
            if c.isValid():
                cell_color = c
        elif bg_brush and isinstance(bg_brush, (QBrush, QColor)):
            c = bg_brush.color() if isinstance(bg_brush, QBrush) else bg_brush
            if c.isValid() and c.alpha() > 0 and c.name().upper() not in ("#C0C0C0", "#B4B4B8", "#D0D0D0", "#D8D8D8", "#FFFFFF"):
                cell_color = c
                
        if not cell_color or not cell_color.isValid():
            cell_color = QColor("#D1D5DB") # Neutral empty slot
                
        # 2. Fill background
        painter.fillRect(rect, cell_color)
        
        # 3. Draw clean 1px border
        painter.setPen(QPen(QColor("#9CA3AF"), 1))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        
        # 4. Selection border
        if option.state & QStyle.State_Selected:
            painter.setPen(QPen(QColor("#1D4ED8"), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -2, -2))
            
        # 5. Draw text - Subject + Teacher (two lines)
        if clean_str or subject_name:
            lum = (0.299 * cell_color.red() + 0.587 * cell_color.green() + 0.114 * cell_color.blue())
            text_color = QColor("#FFFFFF") if lum < 155 else QColor("#111827")
            painter.setPen(text_color)
            
            lock_prefix = "🔒 " if is_locked else ""
            display_subj = lock_prefix + clean_str
            
            if teacher_name:
                # Two-line display: Subject (top, bold) + Teacher (bottom, smaller)
                # Get short teacher name (first name initial + surname)
                t_parts = teacher_name.strip().split()
                if len(t_parts) >= 2:
                    short_teacher = f"{t_parts[0][0]}.{t_parts[-1]}"
                elif t_parts:
                    short_teacher = t_parts[0]
                else:
                    short_teacher = ""
                
                top_rect = QRect(rect.left(), rect.top() + 1, rect.width(), rect.height() // 2)
                bot_rect = QRect(rect.left(), rect.top() + rect.height() // 2 - 1, rect.width(), rect.height() // 2)
                
                painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
                painter.drawText(top_rect, Qt.AlignCenter | Qt.AlignBottom, display_subj)
                
                # Teacher name in slightly transparent color
                t_color = QColor(text_color)
                t_color.setAlpha(200)
                painter.setPen(t_color)
                painter.setFont(QFont("Segoe UI", 6))
                painter.drawText(bot_rect, Qt.AlignCenter | Qt.AlignTop, short_teacher)
            else:
                painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
                painter.drawText(rect, Qt.AlignCenter, display_subj)
            
        painter.restore()



class DropTableWidget(QTableWidget):
    lesson_dropped = Signal(int, int, dict) # row, col, lesson_info
    cell_right_clicked = Signal(int, int)  # row, col for context menu
    
    def __init__(self, rows, cols, parent=None):
        super().__init__(rows, cols, parent)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.asc_header = AsCTimetableHeader(8, DAYS[:5], self)
        self.setHorizontalHeader(self.asc_header)
        self.horizontalScrollBar().valueChanged.connect(lambda: self.asc_header.viewport().update())
        self.setItemDelegate(TimetableCellDelegate(self))
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-lesson"):
            event.accept()
        else:
            event.ignore()
            
    def _clear_highlight(self):
        if hasattr(self, '_drag_hl_cell') and self._drag_hl_cell:
            r, c = self._drag_hl_cell
            item = self.item(r, c)
            if item and getattr(item, "_is_temp_highlight", False):
                self.setItem(r, c, None)
            self._drag_hl_cell = None

    def dragLeaveEvent(self, event):
        self._clear_highlight()
        event.accept()
        
    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-lesson"):
            item = self.itemAt(event.pos())
            r = self.row(item) if item else self.rowAt(event.pos().y())
            c = self.column(item) if item else self.columnAt(event.pos().x())
            
            if (r, c) != getattr(self, '_drag_hl_cell', None):
                self._clear_highlight()
                if r >= 0 and c >= 0:
                    current = self.item(r, c)
                    if not current:
                        temp = QTableWidgetItem("✚ Bırak")
                        temp._is_temp_highlight = True
                        temp.setBackground(QColor("#DCFCE7")) # Subtle light green
                        temp.setForeground(QColor("#16A34A"))
                        temp.setTextAlignment(Qt.AlignCenter)
                        self.setItem(r, c, temp)
                        self._drag_hl_cell = (r, c)
            event.accept()
        else:
            event.ignore()
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not hasattr(self, 'drag_start_pos'):
            return
        if (event.pos() - self.drag_start_pos).manhattanLength() < 5:
            return
            
        item = self.itemAt(self.drag_start_pos)
        if item and item.text().strip():
            row = self.rowAt(self.drag_start_pos.y())
            col = self.columnAt(self.drag_start_pos.x())
            orig_r, orig_c, orig_dur, info = self._get_lesson_origin(row, col)
            if info:
                # Kilitli ders taşıma uyarısı
                if info.get("locked"):
                    ret = QMessageBox.warning(
                        self, "Kilitli Ders Uyarısı",
                        f"🔒 '{info.get('subject_name')}' dersi kilitlenmiştir.\n\n"
                        "Kilitli bir dersi taşımak istiyor musunuz?",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )
                    if ret != QMessageBox.Yes:
                        return
                        
                from PySide6.QtGui import QDrag
                drag = QDrag(self)
                mime = QMimeData()
                
                data = dict(info)
                data["is_move"] = True
                data["origin_row"] = orig_r
                data["origin_col"] = orig_c
                data["teacher"] = info.get("teacher_name", "")
                data["locked"] = info.get("locked", False)
                
                mime.setData("application/x-lesson", QByteArray(json.dumps(data).encode()))
                drag.setMimeData(mime)
                
                orig_item = self.item(orig_r, orig_c) or item
                rect = self.visualItemRect(orig_item)
                pixmap = self.viewport().grab(rect)
                drag.setPixmap(pixmap)
                
                hotspot = event.pos() - rect.topLeft()
                drag.setHotSpot(hotspot)
                
                drag.exec_(Qt.MoveAction)
        super().mouseMoveEvent(event)

    def dropEvent(self, event):
        self._clear_highlight()
        if event.mimeData().hasFormat("application/x-lesson"):
            data = event.mimeData().data("application/x-lesson").data().decode()
            lesson_info = json.loads(data)
            
            item = self.itemAt(event.pos())
            row = self.row(item) if item else self.rowAt(event.pos().y())
            col = self.column(item) if item else self.columnAt(event.pos().x())
            
            if row >= 0 and col >= 0:
                # Hedef slot kilitli ders kontrolü
                target_r, target_c, target_dur, target_info = self._get_lesson_origin(row, col)
                if target_info and target_info.get("locked"):
                    if not (lesson_info.get("is_move") and lesson_info.get("origin_row") == target_r and lesson_info.get("origin_col") == target_c):
                        ret = QMessageBox.warning(
                            self, "Kilitli Slot Uyarısı",
                            f"⛔ Bırakmak istediğiniz zaman diliminde kilitli bir ders ({target_info.get('subject_name')}) bulunmaktadır!\n\n"
                            "Bu slota yeni ders yerleştirmek kilit kuralını geçersiz kılabilir. Devam etmek istiyor musunuz?",
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                        )
                        if ret != QMessageBox.Yes:
                            event.ignore()
                            return
                            
                # Öğretmen timeoff kontrolü
                teacher = lesson_info.get("teacher", "")
                dur = int(lesson_info.get("duration", 1))
                win = self.window()
                if teacher and hasattr(win, "data_store"):
                    for t in win.data_store.get("ogretmenler", []):
                        t_ad = t.get("ad", "")
                        if t_ad and (t_ad == teacher or t_ad.upper() == teacher.upper()):
                            toff = t.get("timeoff", [])
                            if toff:
                                for off in range(dur):
                                    if col < len(toff) and (row + off) < len(toff[col]) and toff[col][row + off] == 0:
                                        QMessageBox.warning(self, "Kısıtlama Engeli",
                                            f"⛔ {t_ad} öğretmeni bu zaman diliminde kısıtlıdır.\n"
                                            f"Önce öğretmenin kısıtlama ayarlarını değiştirin.")
                                        event.ignore()
                                        return
                            break
                
                self.lesson_dropped.emit(row, col, lesson_info)
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()

    def _get_lesson_origin(self, row, col):
        """Finds the true starting cell (origin_row, origin_col) and info of a placed lesson at (row, col)."""
        grid = self.parent()
        if hasattr(grid, "_placed_lessons"):
            for (r, c), info in list(grid._placed_lessons.items()):
                dur = info.get("duration", 1)
                if c == col and r <= row < r + dur:
                    return r, c, dur, info
        return row, col, max(1, self.rowSpan(row, col)), None

    def _delete_lesson_at(self, row, col):
        orig_r, orig_c, orig_dur, info = self._get_lesson_origin(row, col)
        self.setSpan(orig_r, orig_c, 1, 1)
        for r_off in range(orig_dur):
            tr = orig_r + r_off
            if tr < self.rowCount():
                self.removeCellWidget(tr, orig_c)
                self.takeItem(tr, orig_c)
                self.setItem(tr, orig_c, None)
        grid = self.parent()
        if hasattr(grid, "_placed_lessons"):
            grid._placed_lessons.pop((orig_r, orig_c), None)
            
        self.viewport().update()
        self.update()
        
        win = self.window()
        if hasattr(win, "data_store"):
            yerlesim = win.data_store.get("yerlesim", {})
            if isinstance(yerlesim, dict):
                yerlesim.pop(f"{orig_r},{orig_c}", None)
                yerlesim.pop(f"{orig_c},{orig_r}", None)
                
        if hasattr(win, "save_db"):
            win.save_db(sync_from_grid=True)
        if hasattr(grid, "unplaced_dock") and hasattr(grid.unplaced_dock, "_rebuild_cards"):
            grid.unplaced_dock._rebuild_cards()
        if hasattr(win, "_refresh_tree"):
            win._refresh_tree()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            r = self.currentRow()
            c = self.currentColumn()
            if r >= 0 and c >= 0:
                orig_r, orig_c, orig_dur, info = self._get_lesson_origin(r, c)
                if info or (self.item(orig_r, orig_c) and self.item(orig_r, orig_c).text().strip()):
                    self._delete_lesson_at(orig_r, orig_c)
                    return
        super().keyPressEvent(event)

    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        row = self.rowAt(pos.y())
        col = self.columnAt(pos.x())
        
        orig_r, orig_c, orig_dur, orig_info = self._get_lesson_origin(row, col)
        orig_item = self.item(orig_r, orig_c) or item
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #FFFFFF; border: 1px solid #CCC; font-family: system-ui; font-size: 12px; }
            QMenu::item { padding: 8px 25px; }
            QMenu::item:selected { background: #0078D7; color: white; }
            QMenu::separator { height: 1px; background: #DDD; margin: 3px 10px; }
        """)
        
        if orig_item and orig_item.text().strip():
            grid = self.parent()
            info = grid._placed_lessons.get((orig_r, orig_c), {}) if hasattr(grid, "_placed_lessons") else {}
            is_currently_locked = info.get("locked", False)
            
            act_edit = menu.addAction(make_context_icon("✏️", "#2196F3", "#1976D2"), "Düzenle")
            act_move = menu.addAction(make_context_icon("✥", "#FFCA28", "#FF8F00"), "Taşı")
            if not is_currently_locked:
                act_lock = menu.addAction(make_context_icon("🔒", "#9C27B0", "#7B1FA2"), "Dersi Kilitle (Sabitle)")
                act_unlock = None
            else:
                act_lock = None
                act_unlock = menu.addAction(make_context_icon("🔓", "#E53935", "#C62828"), "Bu Dersin Kilidini Aç")
                
            act_unlock_all = menu.addAction(make_context_icon("🔓", "#E53935", "#C62828"), "Tüm Kilitleri Kaldır")
            act_color = menu.addAction(make_grid_action_icon("palette", 16), "Renk Paleti Ayarla...")
            menu.addSeparator()
            act_del = menu.addAction(make_context_icon("X", "#EF5350", "#C62828"), "Sil (Kaldır)")
            
            action = menu.exec_(self.viewport().mapToGlobal(pos))
            
            if action == act_del:
                self._delete_lesson_at(orig_r, orig_c)
            elif action == act_edit:
                self.cell_right_clicked.emit(orig_r, orig_c)
            elif action == act_lock:
                if hasattr(grid, "_placed_lessons") and (orig_r, orig_c) in grid._placed_lessons:
                    info = grid._placed_lessons[(orig_r, orig_c)]
                    info["locked"] = True
                    win = self.window()
                    if hasattr(win, "data_store") and win.data_store:
                        s_name = info.get("subject_name", "")
                        c_name = info.get("class_name", "")
                        for p in win.data_store.get("grid_placements", []):
                            if (p.get("subject_name") or p.get("subject")) == s_name and (p.get("class_name") or p.get("class")) == c_name:
                                p["locked"] = True
                    if hasattr(win, "save_db"): win.save_db(sync_from_grid=False)
                    if hasattr(win, "statusBar"): win.statusBar().showMessage("🔒 Ders kilitlendi.")
                    self.viewport().update()
                    self.update()
            elif action == act_unlock:
                if hasattr(grid, "_placed_lessons") and (orig_r, orig_c) in grid._placed_lessons:
                    info = grid._placed_lessons[(orig_r, orig_c)]
                    info["locked"] = False
                    if orig_item:
                        orig_item.setText(orig_item.text().replace("🔒", ""))
                    win = self.window()
                    if hasattr(win, "data_store") and win.data_store:
                        s_name = info.get("subject_name", "")
                        c_name = info.get("class_name", "")
                        for p in win.data_store.get("grid_placements", []):
                            if (p.get("subject_name") or p.get("subject")) == s_name and (p.get("class_name") or p.get("class")) == c_name:
                                p["locked"] = False
                    if hasattr(win, "save_db"): win.save_db(sync_from_grid=False)
                    if hasattr(win, "statusBar"): win.statusBar().showMessage("🔓 Dersin kilidi kaldırıldı.")
                    self.viewport().update()
                    self.update()
            elif action == act_unlock_all:
                if hasattr(grid, "_placed_lessons"):
                    for (r, c), p_info in grid._placed_lessons.items():
                        p_info["locked"] = False
                        it = self.item(r, c)
                        if it:
                            it.setText(it.text().replace("🔒", ""))
                    win = self.window()
                    if hasattr(win, "data_store") and win.data_store:
                        for p in win.data_store.get("grid_placements", []):
                            p["locked"] = False
                    if hasattr(win, "save_db"): win.save_db(sync_from_grid=False)
                    if hasattr(win, "statusBar"): win.statusBar().showMessage("🔓 Tüm derslerin kilitleri açıldı.")
                    self.viewport().update()
                    self.update()
            elif action == act_color:
                from dialogs.color_picker_dialog import ModernColorPickerDialog, update_subject_color_globally
                grid = self.parent()
                win = self.window()
                data_store = getattr(win, "data_store", None)
                if hasattr(grid, "_placed_lessons") and (orig_r, orig_c) in grid._placed_lessons:
                    info = grid._placed_lessons[(orig_r, orig_c)]
                    s_name = info.get("subject_name", "")
                    new_color = ModernColorPickerDialog.pick_color(
                        initial_color=info.get("color", "#1E88E5"),
                        parent=self,
                        title=f"{s_name} — Renk Seçimi",
                        data_store=data_store,
                        subject_name=s_name
                    )
                    if new_color and new_color.isValid():
                        update_subject_color_globally(self, data_store, s_name, new_color.name())
            elif action == act_move:
                # Instant move dialog
                from PySide6.QtWidgets import QInputDialog
                days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
                win = self.window()
                if hasattr(win, "data_store"):
                    settings = win.data_store.get("settings", {})
                    days = settings.get("days", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
                day_choice, ok1 = QInputDialog.getItem(self, "Dersi Taşı", "Hedef Gün:", days, 0, False)
                if ok1 and day_choice:
                    target_col = days.index(day_choice)
                    period_strs = [f"{p+1}. Ders" for p in range(self.rowCount())]
                    p_choice, ok2 = QInputDialog.getItem(self, "Dersi Taşı", "Hedef Saat:", period_strs, 0, False)
                    if ok2 and p_choice:
                        target_row = period_strs.index(p_choice)
                        if orig_item and hasattr(self.parent(), "set_cell"):
                            txt = orig_item.text()
                            bg = orig_item.background().color().name()
                            self.setSpan(orig_r, orig_c, 1, 1)
                            for r_off in range(orig_dur):
                                tr = orig_r + r_off
                                if tr < self.rowCount():
                                    self.setItem(tr, orig_c, None)
                            if hasattr(self.parent(), "_placed_lessons"):
                                self.parent()._placed_lessons.pop((orig_r, orig_c), None)
                            self.parent().set_cell(target_row, target_col, txt.split('\n')[0], bg, txt.split('\n')[1] if '\n' in txt else "", duration=orig_dur)
                            if hasattr(win, "save_db"):
                                win.save_db()
                            if hasattr(win, "_refresh_tree"):
                                win._refresh_tree()
        else:
            act_add = menu.addAction(make_context_icon("+", "#B0BEC5", "#546E7A"), "Ders Ekle (Aşağıdan Sürükle)")
            act_block = menu.addAction(make_context_icon("L", "#B0BEC5", "#546E7A"), "Bu Slotu Kilitle")
            menu.exec_(self.viewport().mapToGlobal(pos))

    def _set_span(self, row, col, span):
        """Change span of existing cell, automatically shifting any displaced lessons down!"""
        orig_r, orig_c, old_dur, info = self._get_lesson_origin(row, col)
        
        grid = self.parent()
        if not hasattr(grid, "_placed_lessons") or (orig_r, orig_c) not in grid._placed_lessons:
            return
            
        target_lesson_info = dict(grid._placed_lessons[(orig_r, orig_c)])
        
        max_possible_span = min(span, self.rowCount() - orig_r)
        if max_possible_span <= 0:
            return
            
        target_range = range(orig_r + 1, orig_r + max_possible_span)
        
        # 1. Identify all displaced lessons in target_range on column orig_c
        displaced = []
        for r_check in target_range:
            if r_check < self.rowCount():
                d_orig_r, d_orig_c, d_dur, d_info = self._get_lesson_origin(r_check, orig_c)
                if d_info and (d_orig_r, d_orig_c) != (orig_r, orig_c):
                    if (d_orig_r, d_orig_c, d_dur, d_info) not in displaced:
                        displaced.append((d_orig_r, d_orig_c, d_dur, d_info))
                        
        # 2. Clear displaced lessons from grid
        for d_orig_r, d_orig_c, d_dur, _ in displaced:
            self.setSpan(d_orig_r, d_orig_c, 1, 1)
            for r_off in range(d_dur):
                tr = d_orig_r + r_off
                if tr < self.rowCount():
                    self.setItem(tr, d_orig_c, None)
            grid._placed_lessons.pop((d_orig_r, d_orig_c), None)

        # 3. Clear old span of target lesson and apply new span
        self.setSpan(orig_r, orig_c, 1, 1)
        if max_possible_span > 1:
            self.setSpan(orig_r, orig_c, max_possible_span, 1)
            
        target_lesson_info["duration"] = max_possible_span
        grid._placed_lessons[(orig_r, orig_c)] = target_lesson_info

        # Re-set item display for target lesson
        display_text = f"{target_lesson_info.get('subject_name', '')}"
        t_name = target_lesson_info.get("teacher_name", "")
        if t_name and t_name != "Öğretmen":
            display_text += f"\n{t_name}"
        item = QTableWidgetItem(display_text)
        item.setTextAlignment(Qt.AlignCenter)
        color = target_lesson_info.get("color", "#1E88E5")
        item.setBackground(QBrush(QColor(color)))
        c = QColor(color)
        lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
        item.setForeground(QBrush(Qt.white if lum < 160 else Qt.black))
        font = QFont("Segoe UI", 9, QFont.Bold)
        item.setFont(font)
        self.setItem(orig_r, orig_c, item)

        # 4. Shift/re-place all displaced lessons further down on column orig_c
        curr_r = orig_r + max_possible_span
        for _, _, d_dur, d_info in displaced:
            placed_ok = False
            while curr_r + d_dur <= self.rowCount():
                is_free = True
                for check_r in range(curr_r, curr_r + d_dur):
                    if self.item(check_r, orig_c) is not None or (check_r, orig_c) in grid._placed_lessons:
                        is_free = False
                        break
                if is_free:
                    grid.set_cell(
                        curr_r, orig_c,
                        d_info.get("subject_name", ""),
                        d_info.get("color", "#1E88E5"),
                        d_info.get("teacher_name", ""),
                        d_dur,
                        d_info.get("class_name", "")
                    )
                    curr_r += d_dur
                    placed_ok = True
                    break
                else:
                    curr_r += 1

        win = self.window()
        if hasattr(win, "save_db"):
            win.save_db()
        if hasattr(win, "_refresh_tree"):
            win._refresh_tree()


class TimetableGrid(QWidget):
    cell_right_clicked = Signal(int, int)
    view_mode_changed = Signal(str)

    def __init__(self, periods: int = 8, parent=None):
        super().__init__(parent)
        self._periods = periods
        self._placed_lessons = {}
        self.current_view_mode = "classes"
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Toolbar row
        top = QHBoxLayout()
        top.setContentsMargins(8, 4, 8, 4)
        top.setSpacing(8)

        self.toggle_panel_btn = QPushButton(" Sol Panel", self)
        self.toggle_panel_btn.setIcon(make_grid_action_icon("toggle_panel", 16))
        self.toggle_panel_btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.toggle_panel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; color: #334155; border: 1px solid #CBD5E1;
                border-radius: 6px; padding: 4px 12px;
            }
            QPushButton:hover { background-color: #F1F5F9; border-color: #94A3B8; }
        """)
        top.addWidget(self.toggle_panel_btn)
        
        top.addSpacing(10)
        
        # Segmented view switchers (Sınıflar Çarşafı / Öğretmenler Çarşafı)
        switcher_frame = QFrame(self)
        switcher_frame.setStyleSheet("QFrame { background: #E2E8F0; border-radius: 6px; }")
        switcher_layout = QHBoxLayout(switcher_frame)
        switcher_layout.setContentsMargins(2, 2, 2, 2)
        switcher_layout.setSpacing(2)
        
        self.btn_view_classes = QPushButton(" Sınıflar Çarşafı", switcher_frame)
        self.btn_view_classes.setIcon(make_grid_action_icon("siniflar", 18))
        self.btn_view_teachers = QPushButton(" Öğretmenler Çarşafı", switcher_frame)
        self.btn_view_teachers.setIcon(make_grid_action_icon("ogretmenler", 18))
        
        for btn in (self.btn_view_classes, self.btn_view_teachers):
            btn.setCheckable(True)
            btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            switcher_layout.addWidget(btn)
            
        self.btn_view_classes.setChecked(True)
        self._update_view_btn_styles()
        
        self.btn_view_classes.clicked.connect(lambda: self._set_view_mode("classes"))
        self.btn_view_teachers.clicked.connect(lambda: self._set_view_mode("teachers"))
        
        top.addWidget(switcher_frame)
        
        top.addStretch(1)
        
        # Unlock All Button
        btn_unlock_all = QPushButton(" Tüm Kilitleri Aç", self)
        btn_unlock_all.setIcon(make_grid_action_icon("lock_open", 16))
        btn_unlock_all.setFont(QFont("Segoe UI", 9, QFont.Bold))
        btn_unlock_all.setStyleSheet("""
            QPushButton {
                background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;
                border-radius: 6px; padding: 4px 12px;
            }
            QPushButton:hover { background: #FEE2E2; }
        """)
        btn_unlock_all.setCursor(Qt.PointingHandCursor)
        btn_unlock_all.clicked.connect(self._unlock_all_lessons)
        top.addWidget(btn_unlock_all)
        
        layout.addLayout(top)

        # ── Table (aSc-style gray compact grid)
        self.table = DropTableWidget(self._periods, len(DAYS), self)
        self.table.cell_right_clicked.connect(self.cell_right_clicked)
        self.table.setVerticalHeaderLabels([f"{i+1}" for i in range(self._periods)])

        self.table.setShowGrid(True)
        self.table.setGridStyle(Qt.SolidLine)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        vh = self.table.verticalHeader()
        vh.setSectionResizeMode(QHeaderView.Fixed)
        vh.setDefaultSectionSize(26)
        vh.setDefaultAlignment(Qt.AlignCenter)
        vh.setStyleSheet("""
            QHeaderView::section {
                background: #D4D4D4; font-weight: bold; border: 1px solid #888888;
                padding: 2px 6px; font-size: 10px; color: #111111;
            }
        """)

        self.table.setStyleSheet("""
            QTableWidget {
                background: #B4B4B8;
                gridline-color: #7E7E84;
                font-size: 10px;
                selection-background-color: #FFFF00;
                selection-color: #000;
            }
            QTableWidget::item {
                padding: 0px;
                border: none;
            }
        """)

        # Connect click for info panel
        self.table.cellClicked.connect(self._on_cell_clicked)
        
        layout.addWidget(self.table, stretch=1)
        
        # ── Bottom area: info panel + unplaced dock
        bottom_frame = QFrame(self)
        bottom_frame.setStyleSheet("QFrame { background: #B0B0B8; border-top: 1px solid #888; }")
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)
        
        # Left: Lesson Info Panel (aSc-style)
        self.info_panel = QFrame(self)
        self.info_panel.setFixedHeight(75)
        self.info_panel.setMinimumWidth(280)
        self.info_panel.setMaximumWidth(400)
        self.info_panel.setStyleSheet("QFrame { background: #B8B8C0; border: 1px solid #888; }")
        info_inner = QVBoxLayout(self.info_panel)
        info_inner.setContentsMargins(8, 4, 8, 4)
        info_inner.setSpacing(2)
        
        # Color swatch + subject name
        info_top = QHBoxLayout()
        info_top.setSpacing(6)
        self.info_color_box = QLabel()
        self.info_color_box.setFixedSize(22, 22)
        self.info_color_box.setCursor(Qt.PointingHandCursor)
        self.info_color_box.setToolTip("Rengi Değiştirmek İçin Tıklayın")
        self.info_color_box.setStyleSheet("background: transparent; border: 1px solid #666; border-radius: 3px;")
        self.info_color_box.mousePressEvent = self._on_color_box_clicked
        info_top.addWidget(self.info_color_box)
        
        self.info_subject_lbl = QLabel("")
        self.info_subject_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.info_subject_lbl.setStyleSheet("color: #111; background: transparent; border: none;")
        info_top.addWidget(self.info_subject_lbl)
        info_top.addStretch(1)
        info_inner.addLayout(info_top)
        
        self.info_class_lbl = QLabel("")
        self.info_class_lbl.setFont(QFont("Segoe UI", 10))
        self.info_class_lbl.setStyleSheet("color: #D32F2F; background: transparent; border: none; font-weight: bold;")
        info_inner.addWidget(self.info_class_lbl)
        
        self.info_teacher_lbl = QLabel("")
        self.info_teacher_lbl.setFont(QFont("Segoe UI", 10))
        self.info_teacher_lbl.setStyleSheet("color: #333; background: transparent; border: none;")
        info_inner.addWidget(self.info_teacher_lbl)
        
        bottom_layout.addWidget(self.info_panel)
        
        # Right: Unplaced lessons dock
        self.unplaced_dock = UnplacedLessonsDock(self)
        bottom_layout.addWidget(self.unplaced_dock, stretch=1)
        
        layout.addWidget(bottom_frame)

    def _on_color_box_clicked(self, event):
        info = getattr(self, "_current_selected_lesson_info", None)
        if not info:
            r = self.table.currentRow()
            c = self.table.currentColumn()
            if r >= 0 and c >= 0:
                _, _, _, info = self.table._get_lesson_origin(r, c)
                
        win = self.window()
        data_store = getattr(win, "data_store", None)
        
        s_name = ""
        cur_color = "#2563EB"
        if info:
            s_name = info.get("subject_name", "")
            cur_color = info.get("color", "#2563EB")
        elif self.info_subject_lbl.text().strip():
            txt = self.info_subject_lbl.text().replace("🔒", "").strip()
            if " - " in txt:
                s_name = txt.split(" - ")[-1].strip()
            else:
                s_name = txt
                
        if not s_name and data_store and data_store.get("dersler"):
            s_name = data_store["dersler"][0].get("ad", "")
            cur_color = data_store["dersler"][0].get("color", "#2563EB")
            
        if s_name:
            from dialogs.color_picker_dialog import ModernColorPickerDialog, update_subject_color_globally, resolve_subject_color
            cur_color = resolve_subject_color(s_name, data_store)
            new_color = ModernColorPickerDialog.pick_color(
                initial_color=cur_color,
                parent=self,
                title=f"{s_name} — Renk Seçimi",
                data_store=data_store,
                subject_name=s_name
            )
            if new_color and new_color.isValid():
                new_hex = new_color.name()
                if info:
                    info["color"] = new_hex
                self.info_color_box.setStyleSheet(f"background: {new_hex}; border: 2px solid #334155; border-radius: 4px;")
                update_subject_color_globally(self, data_store, s_name, new_hex)

    def _update_view_btn_styles(self):
        active_style = "QPushButton { background-color: #2563EB; color: #FFFFFF; border: none; border-radius: 4px; padding: 4px 14px; font-weight: bold; } QPushButton:hover { background-color: #1D4ED8; }"
        inactive_style = "QPushButton { background-color: transparent; color: #475569; border: none; border-radius: 4px; padding: 4px 14px; font-weight: bold; } QPushButton:hover { background-color: #CBD5E1; color: #0F172A; }"
        self.btn_view_classes.setStyleSheet(active_style if self.current_view_mode == "classes" else inactive_style)
        self.btn_view_teachers.setStyleSheet(active_style if self.current_view_mode == "teachers" else inactive_style)

    def _set_view_mode(self, mode: str):
        self.current_view_mode = mode
        self.btn_view_classes.setChecked(mode == "classes")
        self.btn_view_teachers.setChecked(mode == "teachers")
        self._update_view_btn_styles()
        self.view_mode_changed.emit(mode)
        win = self.window()
        if hasattr(win, "_refresh_grid"):
            win._refresh_grid()

    def _unlock_all_lessons(self):
        for (r, c), p_info in self._placed_lessons.items():
            p_info["locked"] = False
            c_item = self.table.item(r, c)
            if c_item:
                c_item.setText(c_item.text().replace("🔒", ""))
        win = self.window()
        if hasattr(win, "data_store"):
            for p in win.data_store.get("grid_placements", []):
                p["locked"] = False
            if hasattr(win, "save_db"):
                win.save_db(sync_from_grid=False)
            if hasattr(win, "_refresh_grid"):
                win._refresh_grid()
        if hasattr(win, "statusBar"):
            win.statusBar().showMessage("Tüm derslerin kilitleri açıldı.")

    def _on_cell_clicked(self, row, col):
        """Show lesson info in the bottom-left panel when a cell is clicked (aSc-style)."""
        orig_r, orig_c, orig_dur, info = self.table._get_lesson_origin(row, col) if hasattr(self.table, "_get_lesson_origin") else (row, col, 1, None)
        if not info:
            info = self._placed_lessons.get((row, col))
        if not info:
            for (r, c), lesson_info in self._placed_lessons.items():
                dur = lesson_info.get("duration", 1)
                if c == col and r <= row < r + dur:
                    info = lesson_info
                    break
        
        self._current_selected_lesson_info = info
        self._current_selected_pos = (row, col)
        
        if info:
            subj = info.get("subject_name", "")
            teacher = info.get("teacher_name", "")
            cls = info.get("class_name", "")
            
            win = self.window()
            data_store = getattr(win, "data_store", None)
            from dialogs.color_picker_dialog import resolve_subject_color
            color = info.get("color") or resolve_subject_color(subj, data_store)
            info["color"] = color
            is_locked = info.get("locked", False)
            
            abbr = get_subject_abbr(subj)
            self.info_color_box.setStyleSheet(f"background: {color}; border: 2px solid #334155; border-radius: 4px;")
            lock_prefix = "🔒 " if is_locked else ""
            is_comb = bool(info.get("is_combined") or (cls and ("," in cls or "&" in cls or "+" in cls)))
            if is_comb:
                clean_cls = cls.replace("&", ", ").replace("+", ", ").strip()
                self.info_class_lbl.setText(f"🔗 Ortak Ders: {clean_cls.upper()}")
            else:
                self.info_class_lbl.setText(cls.upper() if cls else "")
            
            t_display = ""
            if teacher:
                parts = teacher.strip().split()
                if len(parts) >= 2:
                    t_display = f"{parts[0][0].upper()} – {teacher}"
                else:
                    t_display = teacher
            self.info_teacher_lbl.setText(t_display)
        else:
            self.info_color_box.setStyleSheet("background: transparent; border: 1px solid #666; border-radius: 3px;")
            self.info_subject_lbl.setText("")
            self.info_class_lbl.setText("")
            self.info_teacher_lbl.setText("")

    def set_periods(self, periods: int):
        new_periods = max(1, min(16, int(periods)))
        if self._periods != new_periods:
            self._periods = new_periods
            self.table.setRowCount(self._periods)
            self.table.setVerticalHeaderLabels([f"{i+1}" for i in range(self._periods)])

    def set_cell(self, row, col, subject_name, color, teacher_name="", duration=1, class_name="", display_mode="classes", locked=False):
        class_name = str(class_name).replace("(ea)", "(EA)").replace("(say)", "(SAY)").replace("(soz)", "(SÖZ)").replace("(dil)", "(DİL)")
        if display_mode == "teachers":
            if "," in class_name or "&" in class_name or "+" in class_name:
                display_text = "+".join([c.strip().split("(")[0].strip() for c in class_name.replace("&", ",").replace("+", ",").split(",") if c.strip()])
            else:
                display_text = class_name.strip().split("(")[0].strip()
        else:
            display_text = get_subject_abbr(subject_name)
            
        if locked:
            display_text = f"🔒 {display_text}"
            
        item = QTableWidgetItem(display_text)
            
        item.setTextAlignment(Qt.AlignCenter)
        item.setBackground(QBrush(QColor(color)))
        
        c = QColor(color)
        luminance = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
        text_color = Qt.white if luminance < 160 else Qt.black
        item.setForeground(QBrush(text_color))
        
        font = QFont("Segoe UI", 8, QFont.Bold)
        item.setFont(font)
        
        self.table.setItem(row, col, item)
        
        # Track placed lesson
        self._placed_lessons[(row, col)] = {
            "subject_name": subject_name, "color": color,
            "teacher_name": teacher_name, "class_name": class_name, "duration": duration,
            "locked": bool(locked)
        }
        
    def get_placed_lessons(self):
        """Return dict of placed lessons for printing"""
        return self._placed_lessons
        
    def clear_grid(self):
        self.table.clearContents()
        self.table.clearSpans()
        self._placed_lessons.clear()
        
    def set_mode_single_entity(self, periods: int, days_list: list):
        """Standard view: 1 entity (class/teacher), Rows=Periods, Cols=Days"""
        self._periods = periods
        self.table.setRowCount(periods)
        self.table.setColumnCount(len(days_list))
        if hasattr(self.table, "asc_header"):
            self.table.asc_header.set_config(1, days_list)
        self.table.setVerticalHeaderLabels([f"{i+1}" for i in range(periods)])
        self.clear_grid()
        
    def set_mode_all_classes(self, class_list: list, periods: int, days_list: list):
        """Whole School View (aSc Çarşaf - Sınıflar): Rows=Classes, Cols=Days*Periods"""
        self._periods = periods
        self.class_list = class_list
        self.current_view_mode = "classes"
        self.table.setRowCount(len(class_list))
        self.table.setVerticalHeaderLabels(class_list)
        total_cols = len(days_list) * periods
        self.table.setColumnCount(total_cols)
        
        # Configure AsCTimetableHeader
        if hasattr(self.table, "asc_header"):
            self.table.asc_header.set_config(periods, days_list)
        
        # Set compact column widths and row heights
        for i in range(total_cols):
            self.table.setColumnWidth(i, 44)
        for r in range(len(class_list)):
            self.table.setRowHeight(r, 26)
            
        self.clear_grid()

    def set_mode_all_teachers(self, teacher_list: list, periods: int, days_list: list):
        """Whole School View (aSc Çarşaf - Öğretmenler): Rows=Teachers, Cols=Days*Periods"""
        self._periods = periods
        self.teacher_list = teacher_list
        self.current_view_mode = "teachers"
        self.table.setRowCount(len(teacher_list))
        self.table.setVerticalHeaderLabels(teacher_list)
        total_cols = len(days_list) * periods
        self.table.setColumnCount(total_cols)
        
        # Configure AsCTimetableHeader
        if hasattr(self.table, "asc_header"):
            self.table.asc_header.set_config(periods, days_list)
        
        # Set compact column widths and row heights
        for i in range(total_cols):
            self.table.setColumnWidth(i, 44)
        for r in range(len(teacher_list)):
            self.table.setRowHeight(r, 26)
            
        self.clear_grid()

