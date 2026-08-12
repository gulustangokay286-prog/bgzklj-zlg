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


DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]

class DraggableLessonCard(QLabel):
    def __init__(self, lesson_id: int, subject_name: str, color: str, duration: int = 1, teacher: str = "", parent=None):
        super().__init__(parent)
        self.lesson_id = lesson_id
        self.subject_name = subject_name
        self.color = color
        self.duration = duration
        self.teacher = teacher
        
        self.setText(f"{subject_name} ({duration})")
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(50 + (duration - 1)*30, 40)
        self.setStyleSheet(f"background: {color}; color: white; font-weight: bold; border: 1px solid #333; border-radius: 4px; font-size: 10px;")
        self.setCursor(Qt.OpenHandCursor)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            
            data = {"lesson_id": self.lesson_id, "subject_name": self.subject_name, "color": self.color, "duration": self.duration, "teacher": self.teacher}
            mime.setData("application/x-lesson", QByteArray(json.dumps(data).encode()))
            drag.setMimeData(mime)
            
            pix = self.grab()
            drag.setPixmap(pix)
            drag.setHotSpot(event.pos())
            
            drag.exec_(Qt.MoveAction)


class UnplacedLessonsDock(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setStyleSheet("background: #555555; border-top: 2px solid #F39C12;")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)
        
        # Scroll area for many unplaced lessons
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setAlignment(Qt.AlignLeft)
        
        scroll.setWidget(self.container)
        self.layout.addWidget(scroll)

    def load_unplaced(self, lessons_data):
        # clear existing
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        for l in lessons_data:
            dur = l.get("duration", 1)
            teacher = l.get("teacher", "")
            card = DraggableLessonCard(l["id"], l["subject_name"], l["color"], duration=dur, teacher=teacher)
            self.container_layout.addWidget(card)


class DropTableWidget(QTableWidget):
    lesson_dropped = Signal(int, int, int, int) # row, col, lesson_id, duration
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
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-lesson"):
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-lesson"):
            data = event.mimeData().data("application/x-lesson").data().decode()
            lesson_info = json.loads(data)
            
            item = self.itemAt(event.pos())
            row = self.row(item) if item else self.rowAt(event.pos().y())
            col = self.column(item) if item else self.columnAt(event.pos().x())
            
            if row >= 0 and col >= 0:
                self.lesson_dropped.emit(row, col, lesson_info["lesson_id"], lesson_info.get("duration", 1))
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()

    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        row = self.rowAt(pos.y())
        col = self.columnAt(pos.x())
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #FFFFFF; border: 1px solid #CCC; font-family: 'Segoe UI'; font-size: 11px; }
            QMenu::item { padding: 8px 30px 8px 30px; }
            QMenu::item:selected { background: #0078D7; color: white; }
            QMenu::separator { height: 1px; background: #DDD; margin: 3px 10px; }
        """)
        
        if item and item.text().strip():
            act_edit = menu.addAction(make_context_icon("E", "#4CAF50", "#2E7D32"), "Düzenle")
            act_move = menu.addAction(make_context_icon("M", "#FFCA28", "#FF8F00"), "Taşı")
            menu.addSeparator()
            act_single = menu.addAction(make_context_icon("1", "#29B6F6", "#0277BD"), "Tekli Yap")
            act_double = menu.addAction(make_context_icon("2", "#29B6F6", "#0277BD"), "İkili Blok Yap")
            act_triple = menu.addAction(make_context_icon("3", "#29B6F6", "#0277BD"), "Üçlü Blok Yap")
            act_quad   = menu.addAction(make_context_icon("4", "#29B6F6", "#0277BD"), "Dörtlü Blok Yap")
            menu.addSeparator()
            act_del = menu.addAction(make_context_icon("X", "#EF5350", "#C62828"), "Sil (Kaldır)")
            
            action = menu.exec_(self.viewport().mapToGlobal(pos))
            
            if action == act_del:
                self.setSpan(row, col, 1, 1) # Clear span
                self.setItem(row, col, None)
            elif action == act_single:
                self._set_span(row, col, 1)
            elif action == act_double:
                self._set_span(row, col, 2)
            elif action == act_triple:
                self._set_span(row, col, 3)
            elif action == act_quad:
                self._set_span(row, col, 4)
            elif action == act_edit:
                self.cell_right_clicked.emit(row, col)
            elif action == act_move:
                self.parent().parent().statusBar().showMessage("Taşımak için hücreyi basılı tutup başka bir boşluğa sürükleyebilirsiniz.")
        else:
            act_add = menu.addAction(make_context_icon("+", "#B0BEC5", "#546E7A"), "Ders Ekle (Aşağıdan Sürükle)")
            act_block = menu.addAction(make_context_icon("L", "#B0BEC5", "#546E7A"), "Bu Slotu Kilitle")
            menu.exec_(self.viewport().mapToGlobal(pos))

    def _set_span(self, row, col, span):
        """Change span of existing cell"""
        item = self.item(row, col)
        if item:
            # We don't call clearSpans() because it ruins ALL spans!
            # Instead, reset current cell span to 1x1 first, then apply new span
            self.setSpan(row, col, 1, 1)
            max_span = min(span, self.rowCount() - row)
            if max_span > 1:
                self.setSpan(row, col, max_span, 1)


class TimetableGrid(QWidget):
    def __init__(self, periods: int = 8, parent=None):
        super().__init__(parent)
        self._periods = periods
        self._placed_lessons = {}  # (row, col) -> lesson_data
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ── Toolbar row
        top = QHBoxLayout()
        top.setSpacing(8)

        view_lbl = QLabel("Görünüm:", self)
        view_lbl.setFont(QFont("Segoe UI", 9))
        top.addWidget(view_lbl)

        self.view_combo = QComboBox(self)
        self.view_combo.addItems(["Sınıf Görünümü", "Öğretmen Görünümü", "Derslik Görünümü"])
        self.view_combo.setFixedWidth(180)
        top.addWidget(self.view_combo)

        self.entity_combo = QComboBox(self)
        self.entity_combo.setFixedWidth(160)
        top.addWidget(self.entity_combo)

        top.addStretch(1)
        layout.addLayout(top)

        # ── Table
        self.table = DropTableWidget(self._periods, len(DAYS), self)
        self.table.setHorizontalHeaderLabels(DAYS)
        self.table.setVerticalHeaderLabels([f"{i+1}" for i in range(self._periods)])

        self.table.setShowGrid(True)
        self.table.setGridStyle(Qt.SolidLine)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)
        hh.setDefaultAlignment(Qt.AlignCenter)
        hh.setStyleSheet("QHeaderView::section { background: #D0D8E4; font-weight: bold; padding: 4px; border: 1px solid #BCC8D8; }")

        vh = self.table.verticalHeader()
        vh.setSectionResizeMode(QHeaderView.Fixed)
        vh.setDefaultSectionSize(60)
        vh.setStyleSheet("QHeaderView::section { background: #F5F7FA; font-weight: bold; border: 1px solid #DDD; padding: 4px; }")

        self.table.setStyleSheet("QTableWidget { background: #E0E0E0; gridline-color: #BCC8D8; }")
        
        layout.addWidget(self.table)
        
        # Bottom Dock for unplaced lessons
        self.unplaced_dock = UnplacedLessonsDock(self)
        layout.addWidget(self.unplaced_dock)
        
    def set_cell(self, row, col, subject_name, color, teacher_name="", duration=1):
        item = QTableWidgetItem(f"{subject_name}\n{teacher_name}")
        item.setTextAlignment(Qt.AlignCenter)
        item.setBackground(QBrush(QColor(color)))
        # White text for dark colors
        is_dark = color.upper() in ["#E53935", "#FF0000", "#A30F37", "#1E88E5", "#8E24AA", "#C62828", "#1565C0"]
        item.setForeground(QBrush(Qt.white if is_dark else Qt.black))
        font = QFont("Segoe UI", 9)
        font.setBold(True)
        item.setFont(font)
        
        # Set span
        max_span = min(duration, self.table.rowCount() - row)
        self.table.setSpan(row, col, max_span, 1)
        self.table.setItem(row, col, item)
        
        # Track placed lesson
        self._placed_lessons[(row, col)] = {
            "subject_name": subject_name, "color": color,
            "teacher_name": teacher_name, "duration": duration
        }
        
    def get_placed_lessons(self):
        """Return dict of placed lessons for printing"""
        return self._placed_lessons
        
    def clear_grid(self):
        self.table.clearContents()
        self.table.clearSpans()
        self._placed_lessons.clear()
