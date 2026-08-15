"""
timetable_grid.py  –  Haftalık ders programı tablosu (drag-drop + sağ tık menüsü destekli)
"""
import json
from PySide6.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QAbstractItemView, QFrame, QScrollArea, QMenu, QInputDialog,
    QMessageBox
)
from PySide6.QtCore import Qt, QMimeData, Signal, QByteArray
from PySide6.QtGui import QFont, QColor, QBrush, QDrag, QPainter, QPixmap, QAction, QPen, QLinearGradient, QIcon

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

def get_subject_abbr(subject_name: str) -> str:
    if not subject_name: return ""
    s = subject_name.strip()
    
    mapping = {
        "MATEMATİK": "MAT", "FİZİK": "FİZ", "BİYOLOJİ": "BİY", "KİMYA": "KİM",
        "GEOMETRİ": "GEO", "TARİH": "TAR", "COĞRAFYA": "COĞ", "TÜRKÇE": "TÜR",
        "EDEBİYAT": "EDB", "TÜRK DİLİ VE EDEBİYATI": "TDE", "GÖRSEL SANATLAR": "GÖR",
        "İNGİLİZCE": "İNG", "ALMANCA": "ALM", "FRANSIZCA": "FRA", "DİN": "DİN",
        "DİN KÜLTÜRÜ": "DİN", "FELSEFE": "FEL", "BEDEN": "BDN", "BEDEN EĞİTİMİ": "BDN",
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


class DraggableLessonCard(QLabel):
    def __init__(self, lesson_id: int, subject_name: str, color: str, duration: int = 1, teacher: str = "", class_name: str = "", parent=None):
        super().__init__(parent)
        self.lesson_id = lesson_id
        self.subject_name = subject_name
        self.color = color
        self.duration = duration
        self.teacher = teacher
        self.class_name = class_name
        
        abbr = get_subject_abbr(subject_name)
        t_short = ""
        if teacher and teacher != "Öğretmen":
            parts = teacher.strip().split()
            if len(parts) >= 2:
                t_short = f"{parts[0]} {parts[-1][0]}."
            else:
                t_short = parts[0]
                
        display_text = f"<b>{abbr}</b>"
        if t_short:
            display_text += f"<br><span style='font-weight:normal; font-size:10px; opacity:0.9;'>{t_short}</span>"
        if duration > 1:
            display_text += f" <span style='background:rgba(255,255,255,0.35); border-radius:3px; padding:1px 4px; font-size:9px; font-weight:bold;'>{duration}h</span>"
            
        self.setText(display_text)
        self.setAlignment(Qt.AlignCenter)
        card_width = max(85, 75 + (duration - 1)*30)
        self.setFixedSize(card_width, 54)
        
        c = QColor(color)
        luminance = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
        text_color = "#FFFFFF" if luminance < 160 else "#111111"
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: {text_color};
                font-family: system-ui, -apple-system, sans-serif;
                font-size: 11px;
                border: 1px solid rgba(0, 0, 0, 0.18);
                border-radius: 8px;
                padding: 4px;
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
            from dialogs.color_picker_dialog import ModernColorPickerDialog
            new_color = ModernColorPickerDialog.pick_color(
                initial_color=self.color,
                parent=win or self,
                title=f"🎨 {self.subject_name} — Renk Seçimi",
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
                        font-size: 11px;
                        border: 1px solid rgba(0, 0, 0, 0.18);
                        border-radius: 8px;
                        padding: 4px;
                    }}
                    QLabel:hover {{
                        border: 2px solid #0078D7;
                    }}
                """)
                if win:
                    if hasattr(win, "save_db"): win.save_db(sync_from_grid=False)
                    if hasattr(win, "_refresh_tree"): win._refresh_tree()
                    if hasattr(win, "_on_tree_selection_changed"): win._on_tree_selection_changed()
                    elif hasattr(win, "_load_unplaced_lessons"): win._load_unplaced_lessons()
            return

        selected_type = None
        if action == act_2_2: selected_type = "2+2"
        elif action == act_2_1: selected_type = "2+1"
        elif action == act_2_2_1: selected_type = "2+2+1"
        elif action == act_3_2: selected_type = "3+2"
        elif action == act_1_1_1: selected_type = "1+1+1"
        elif action == act_custom:
            val, ok = QInputDialog.getText(self, "Özel Ders Dağılımı", "Dağılım biçimi (Örn: 2+3, 1+2+2, 2+2+2):", text=str(self.duration))
            if ok and val.strip():
                selected_type = val.strip()
        elif action == act_del:
            if data_store and "atamalar" in data_store:
                data_store["atamalar"] = [
                    a for a in data_store["atamalar"]
                    if not (a.get("teacher") == self.teacher and a.get("subject") == self.subject_name and a.get("class") == self.class_name)
                ]
                
                if "grid_placements" in data_store:
                    data_store["grid_placements"] = [
                        p for p in data_store["grid_placements"]
                        if not (p.get("teacher_name") == self.teacher and p.get("subject_name") == self.subject_name and p.get("class_name") == self.class_name)
                    ]
                    
                if hasattr(win, "save_db"): win.save_db()
                if hasattr(win, "_refresh_tree"): win._refresh_tree()
                if hasattr(win, "_on_tree_selection_changed"): win._on_tree_selection_changed()
            return
            
        if selected_type and data_store:
            if "atamalar" not in data_store:
                data_store["atamalar"] = []
                
            updated = False
            for a in data_store["atamalar"]:
                if (a.get("teacher") == self.teacher or not self.teacher or self.teacher == "Öğretmen") and a.get("subject") == self.subject_name:
                    a["type"] = selected_type
                    parts = [int(p.strip()) for p in selected_type.split("+") if p.strip().isdigit()]
                    a["duration"] = sum(parts) if parts else (int(selected_type) if selected_type.isdigit() else 1)
                    updated = True
                    break
                    
            if not updated:
                parts = [int(p.strip()) for p in selected_type.split("+") if p.strip().isdigit()]
                tot_dur = sum(parts) if parts else (int(selected_type) if selected_type.isdigit() else 1)
                data_store["atamalar"].append({
                    "teacher": self.teacher or "Öğretmen",
                    "subject": self.subject_name,
                    "class": self.class_name,
                    "duration": tot_dur,
                    "type": selected_type,
                    "color": self.color
                })
                
            if hasattr(win, "save_db"): win.save_db()
            if hasattr(win, "_refresh_tree"): win._refresh_tree()


class UnplacedLessonsDock(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(85)
        self.setAcceptDrops(True)
        self.setStyleSheet("QFrame { background: #F8FAFC; border-top: 2px solid #E2E8F0; }")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 6, 12, 6)
        self.layout.setSpacing(10)
        
        # Scroll area for unplaced lessons
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:horizontal {
                height: 6px;
                background: #E2E8F0;
                border-radius: 3px;
            }
            QScrollBar::handle:horizontal {
                background: #94A3B8;
                border-radius: 3px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #64748B;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            QScrollBar:vertical {
                width: 0px;
            }
        """)
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
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
                    orig_dur = data.get("duration", 1)
                    win = self.window()
                    grid = getattr(win, "_grid", None)
                    if grid and orig_r >= 0 and orig_c >= 0:
                        grid.table._delete_lesson_at(orig_r, orig_c)
            except Exception as e:
                print("Dock drop error:", e)
            event.accept()

    def load_unplaced(self, lessons_data, has_assignments=True):
        # clear existing
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not lessons_data:
            if not has_assignments:
                hint = QLabel("⚠️ Bu sınıfa / öğretmene henüz hiç ders atanmadı! Lütfen 'Ders Atama' bölümünden ders ve öğretmen tanımlayın.")
                hint.setStyleSheet("color: #D32F2F; font-weight: bold; font-size: 12px; padding: 10px; background: #FFEBEE; border: 1px solid #FFCDD2; border-radius: 6px;")
            else:
                hint = QLabel("✅ Bu sınıfın / öğretmenin tüm dersleri başarıyla programa yerleştirildi.")
                hint.setStyleSheet("color: #2E7D32; font-weight: bold; font-size: 12px; padding: 10px; background: #E8F5E9; border: 1px solid #C8E6C9; border-radius: 6px;")
            self.container_layout.addWidget(hint)
            return

        for l in lessons_data:
            dur = l.get("duration", 1)
            teacher = l.get("teacher", "")
            cls_name = l.get("class_name", "")
            card = DraggableLessonCard(l["id"], l["subject_name"], l["color"], duration=dur, teacher=teacher, class_name=cls_name)
            self.container_layout.addWidget(card)


class DropTableWidget(QTableWidget):
    lesson_dropped = Signal(int, int, dict) # row, col, lesson_info
    cell_right_clicked = Signal(int, int)  # row, col for context menu
    
    def __init__(self, rows, cols, parent=None):
        super().__init__(rows, cols, parent)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
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
        super().dragLeaveEvent(event)
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-lesson"):
            row = self.rowAt(event.pos().y())
            col = self.columnAt(event.pos().x())
            
            if row >= 0 and col >= 0:
                if getattr(self, '_drag_hl_cell', None) != (row, col):
                    self._clear_highlight()
                    self._drag_hl_cell = (row, col)
                    
                    item = self.item(row, col)
                    if not item: # Sadece boş hücreleri boya
                        data = json.loads(event.mimeData().data("application/x-lesson").data().decode())
                        teacher = data.get("teacher", "")
                        
                        # Basit çakışma kontrolü (İleride GlobalState'den kontrol edilecek)
                        # Şimdilik öğretmenin o saatte dersi var mı simulasyonu:
                        # Eğer teacher doluysa ve rastgele bir conflict mantığı (Gerçek veritabanına bağlanacak)
                        grid = self.parent()
                        is_conflict = False
                        if hasattr(grid, "_placed_lessons"):
                            for (r, c_idx), info in grid._placed_lessons.items():
                                if c_idx == col and r == row and info.get("teacher_name") == teacher:
                                    is_conflict = True
                                    break
                                    
                        hl_item = QTableWidgetItem("")
                        hl_item._is_temp_highlight = True
                        color = QColor(255, 0, 0, 80) if is_conflict else QColor(76, 175, 80, 80) # Kırmızı veya Yeşil
                        hl_item.setBackground(QBrush(color))
                        self.setItem(row, col, hl_item)
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
                from PySide6.QtGui import QDrag
                drag = QDrag(self)
                mime = QMimeData()
                
                data = dict(info)
                data["is_move"] = True
                data["origin_row"] = orig_r
                data["origin_col"] = orig_c
                data["teacher"] = info.get("teacher_name", "")
                
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
            act_edit = menu.addAction(make_context_icon("E", "#4CAF50", "#2E7D32"), "Düzenle")
            act_move = menu.addAction(make_context_icon("M", "#FFCA28", "#FF8F00"), "Taşı")
            act_lock = menu.addAction(make_context_icon("K", "#9C27B0", "#6A1B9A"), "Kilitle (Sabitle)")
            act_change_teacher = menu.addAction(make_context_icon("Ö", "#00BCD4", "#00838F"), "Öğretmeni Değiştir")
            act_color = menu.addAction(make_context_icon("🎨", "#EC407A", "#C2185B"), "🎨 Renk Paleti Ayarla...")
            menu.addSeparator()
            act_del = menu.addAction(make_context_icon("X", "#EF5350", "#C62828"), "Sil (Kaldır)")
            
            action = menu.exec_(self.viewport().mapToGlobal(pos))
            
            if action == act_del:
                self._delete_lesson_at(orig_r, orig_c)
            elif action == act_edit:
                self.cell_right_clicked.emit(orig_r, orig_c)
            elif action == act_lock:
                grid = self.parent()
                if hasattr(grid, "_placed_lessons") and (orig_r, orig_c) in grid._placed_lessons:
                    info = grid._placed_lessons[(orig_r, orig_c)]
                    info["locked"] = not info.get("locked", False)
                    if info["locked"]:
                        orig_item.setBackground(QBrush(QColor("#E0E0E0"))) # Grayed out / locked
                    else:
                        orig_item.setBackground(QBrush(QColor("#E8F4F8")))
                    win = self.window()
                    if hasattr(win, "save_db"): win.save_db()
            elif action == act_color:
                from dialogs.color_picker_dialog import ModernColorPickerDialog
                grid = self.parent()
                win = self.window()
                data_store = getattr(win, "data_store", None)
                if hasattr(grid, "_placed_lessons") and (orig_r, orig_c) in grid._placed_lessons:
                    info = grid._placed_lessons[(orig_r, orig_c)]
                    s_name = info.get("subject_name", "")
                    new_color = ModernColorPickerDialog.pick_color(
                        initial_color=info.get("color", "#1E88E5"),
                        parent=self,
                        title=f"🎨 {s_name} — Renk Seçimi",
                        data_store=data_store,
                        subject_name=s_name
                    )
                    if new_color and new_color.isValid():
                        hex_color = new_color.name()
                        info["color"] = hex_color
                        orig_item.setBackground(QBrush(new_color))
                        lum = (0.299 * new_color.red() + 0.587 * new_color.green() + 0.114 * new_color.blue())
                        orig_item.setForeground(QBrush(Qt.white if lum < 160 else Qt.black))
                        
                        # Update subject globally in data_store
                        if data_store and "dersler" in data_store:
                            for d in data_store["dersler"]:
                                if d.get("ad", "").strip().upper() == s_name.strip().upper():
                                    d["color"] = hex_color
                                    d["renk"] = hex_color
                                    
                        # Update all placements of this subject on current grid
                        if hasattr(grid, "_placed_lessons"):
                            for (r, c), p_info in grid._placed_lessons.items():
                                if p_info.get("subject_name", "").strip().upper() == s_name.strip().upper():
                                    p_info["color"] = hex_color
                                    cell_item = self.item(r, c)
                                    if cell_item:
                                        cell_item.setBackground(QBrush(new_color))
                                        cell_item.setForeground(QBrush(Qt.white if lum < 160 else Qt.black))
                                        
                        if hasattr(win, "save_db"): win.save_db()
                        if hasattr(win, "_refresh_tree"): win._refresh_tree()
            elif action == act_change_teacher:
                from PySide6.QtWidgets import QInputDialog
                win = self.window()
                if hasattr(win, "data_store"):
                    teachers = [t.get("ad") for t in win.data_store.get("ogretmenler", [])]
                    t_choice, ok = QInputDialog.getItem(self, "Öğretmen Değiştir", "Yeni Öğretmen Seçin:", teachers, 0, False)
                    if ok and t_choice:
                        grid = self.parent()
                        if hasattr(grid, "_placed_lessons") and (orig_r, orig_c) in grid._placed_lessons:
                            info = grid._placed_lessons[(orig_r, orig_c)]
                            info["teacher"] = t_choice
                            subj = info.get("subject_name", "")
                            orig_item.setText(f"{subj}\n{t_choice}")
                            win.save_db()
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

    def __init__(self, periods: int = 8, parent=None):
        super().__init__(parent)
        self._periods = periods
        self._placed_lessons = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Toolbar row
        top = QHBoxLayout()
        top.setContentsMargins(8, 4, 8, 4)
        top.setSpacing(8)

        self.toggle_panel_btn = QPushButton("Sol Paneli Aç/Kapat", self)
        self.toggle_panel_btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.toggle_panel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6; color: white; border-radius: 4px; padding: 4px 12px;
            }
            QPushButton:hover { background-color: #2563EB; }
        """)
        top.addWidget(self.toggle_panel_btn)
        
        top.addStretch(1)
        layout.addLayout(top)

        # ── Table (aSc-style gray compact grid)
        self.table = DropTableWidget(self._periods, len(DAYS), self)
        self.table.cell_right_clicked.connect(self.cell_right_clicked)
        self.table.setHorizontalHeaderLabels(DAYS)
        self.table.setVerticalHeaderLabels([f"{i+1}" for i in range(self._periods)])

        self.table.setShowGrid(True)
        self.table.setGridStyle(Qt.SolidLine)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)
        hh.setDefaultAlignment(Qt.AlignCenter)
        hh.setMinimumSectionSize(22)
        hh.setStyleSheet("""
            QHeaderView::section {
                background: #D0D0D0; font-weight: bold; padding: 2px;
                border: 1px solid #999; font-size: 10px; color: #111;
            }
        """)

        vh = self.table.verticalHeader()
        vh.setSectionResizeMode(QHeaderView.Stretch)
        vh.setMinimumSectionSize(22)
        vh.setStyleSheet("""
            QHeaderView::section {
                background: #D8D8D8; font-weight: bold; border: 1px solid #999;
                padding: 2px; font-size: 10px; color: #111;
            }
        """)

        self.table.setStyleSheet("""
            QTableWidget {
                background: #C0C0C0;
                gridline-color: #999999;
                font-size: 10px;
                selection-background-color: #FFFF00;
                selection-color: #000;
            }
            QTableWidget::item {
                padding: 1px;
                background: #C0C0C0;
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
        self.info_color_box.setStyleSheet("background: transparent; border: 1px solid #666;")
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

    def _on_cell_clicked(self, row, col):
        """Show lesson info in the bottom-left panel when a cell is clicked (aSc-style)."""
        info = self._placed_lessons.get((row, col))
        if not info:
            for (r, c), lesson_info in self._placed_lessons.items():
                dur = lesson_info.get("duration", 1)
                if c == col and r <= row < r + dur:
                    info = lesson_info
                    break
        
        if info:
            subj = info.get("subject_name", "")
            teacher = info.get("teacher_name", "")
            cls = info.get("class_name", "")
            color = info.get("color", "#C0C0C0")
            
            abbr = get_subject_abbr(subj)
            self.info_color_box.setStyleSheet(f"background: {color}; border: 1px solid #666;")
            self.info_subject_lbl.setText(f"{abbr} - {subj.upper()}")
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
            self.info_color_box.setStyleSheet("background: transparent; border: 1px solid #666;")
            self.info_subject_lbl.setText("")
            self.info_class_lbl.setText("")
            self.info_teacher_lbl.setText("")

    def set_periods(self, periods: int):
        new_periods = max(1, min(16, int(periods)))
        if self._periods != new_periods:
            self._periods = new_periods
            self.table.setRowCount(self._periods)
            self.table.setVerticalHeaderLabels([f"{i+1}" for i in range(self._periods)])

    def set_cell(self, row, col, subject_name, color, teacher_name="", duration=1, class_name=""):
        abbr = get_subject_abbr(subject_name)
        display_text = abbr
            
        item = QTableWidgetItem(display_text)
        item.setTextAlignment(Qt.AlignCenter)
        item.setBackground(QBrush(QColor(color)))
        
        c = QColor(color)
        luminance = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
        text_color = Qt.white if luminance < 160 else Qt.black
        item.setForeground(QBrush(text_color))
        
        font = QFont("Segoe UI", 9)
        font.setBold(True)
        item.setFont(font)
        
        # Set span
        max_span = min(duration, self.table.rowCount() - row)
        if max_span > 1:
            self.table.setSpan(row, col, max_span, 1)
        self.table.setItem(row, col, item)
        
        # Track placed lesson
        self._placed_lessons[(row, col)] = {
            "subject_name": subject_name, "color": color,
            "teacher_name": teacher_name, "class_name": class_name, "duration": max_span
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
        self.table.setHorizontalHeaderLabels(days_list)
        self.table.setVerticalHeaderLabels([f"{i+1}" for i in range(periods)])
        self.clear_grid()
        
    def set_mode_all_classes(self, class_list: list, periods: int, days_list: list):
        """Whole School View (aSc Çarşaf): Rows=Classes, Cols=Days*Periods"""
        self._periods = periods
        self.table.setRowCount(len(class_list))
        total_cols = len(days_list) * periods
        self.table.setColumnCount(total_cols)
        
        # Build headers
        self.table.setVerticalHeaderLabels(class_list)
        
        col_headers = []
        for d in days_list:
            for p in range(periods):
                col_headers.append(str(p + 1))
        self.table.setHorizontalHeaderLabels(col_headers)
        
        # Set compact column widths
        hh = self.table.horizontalHeader()
        hh.setMinimumSectionSize(18)
        for i in range(total_cols):
            self.table.setColumnWidth(i, 24)
            
        self.clear_grid()

