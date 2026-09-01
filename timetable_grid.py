"""
timetable_grid.py  –  Haftalık ders programı tablosu (drag-drop + sağ tık menüsü destekli)
"""
import json
import uuid
import time
from PySide6.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QAbstractItemView, QFrame, QScrollArea, QMenu, QInputDialog,
    QMessageBox, QStyledItemDelegate, QStyle, QApplication
)
from PySide6.QtCore import Qt, QMimeData, Signal, QByteArray, QRect, QRectF, QTimer, QPoint, QPointF, QEvent
from PySide6.QtGui import QFont, QColor, QBrush, QDrag, QPainter, QPixmap, QAction, QPen, QLinearGradient, QIcon, QPainterPath, QCursor
from auto_scheduler import matches_class, format_tr_name

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"

_CELL_FONT = QFont("Segoe UI", 8, QFont.Bold)
_CELL_BRUSH_CACHE = {}
_CELL_TEXT_BRUSH_CACHE = {}
_CLASS_FMT_CACHE = {}

def _fast_cell_brush(color_str: str) -> QBrush:
    b = _CELL_BRUSH_CACHE.get(color_str)
    if b is None:
        b = QBrush(QColor(color_str))
        _CELL_BRUSH_CACHE[color_str] = b
    return b

def _fast_text_brush(color_str: str) -> QBrush:
    tb = _CELL_TEXT_BRUSH_CACHE.get(color_str)
    if tb is None:
        c = QColor(color_str)
        luminance = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
        tb = QBrush(Qt.white if luminance < 160 else Qt.black)
        _CELL_TEXT_BRUSH_CACHE[color_str] = tb
    return tb

class StickyGhostWidget(QLabel):
    _active_instance = None
    _hovered_table = None
    last_drop_time = 0

    def __init__(self, pixmap, drag_data, parent_window=None, grab_offset=None):
        if StickyGhostWidget._active_instance:
            StickyGhostWidget._active_instance.cancel()

        super().__init__(None)
        StickyGhostWidget._active_instance = self
        # NoDropShadowWindowHint: on macOS a frameless + translucent window still gets a
        # native Cocoa shadow layer, and that layer is what paints as an opaque black
        # rectangle when the compositor cannot resolve the window's alpha. The in-app
        # QGraphicsDropShadowEffects were removed for this same symptom; this is the
        # remaining shadow source. The cards draw their own border, so nothing is lost.
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.BypassWindowManagerHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.setPixmap(pixmap)
        self.setFixedSize(pixmap.size())
        # Low opacity so the ghost reads as "in flight" rather than a fully solid card
        self.setWindowOpacity(0.62)
        self.drag_data = drag_data
        self.parent_window = parent_window
        self._tick_count = 0
        self._last_cursor_pos = None
        # Where inside the card the user grabbed it. The ghost keeps that exact offset
        # under the cursor, and the target cell is read from the ghost's own top-left
        # corner — so a block always lands where it is drawn. Previously the ghost was
        # CENTERED on the cursor while the drop cell was read from the cursor itself,
        # which for a 2-hour block put the cursor over the block's second half: the
        # lesson landed one period to the right of where it appeared, and putting a
        # lesson back where it came from was nearly impossible.
        if grab_offset is None:
            grab_offset = QPoint(pixmap.width() // 2, pixmap.height() // 2)
        # Keep the grab point inside the pixmap so the anchor can never fall outside it.
        gx = max(0, min(int(grab_offset.x()), max(0, pixmap.width() - 1)))
        gy = max(0, min(int(grab_offset.y()), max(0, pixmap.height() - 1)))
        self._grab_offset = QPoint(gx, gy)

        # Follow cursor with fast timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_pos)
        self._timer.start(12)

        self._update_pos()
        self.show()

        # Install application-level event filter
        QTimer.singleShot(20, self._install_filter)

    def _install_filter(self):
        if StickyGhostWidget._active_instance == self:
            QApplication.instance().installEventFilter(self)

    def _anchor_global(self, cursor_global):
        """Global point used for hit-testing: a little way inside the ghost's FIRST cell.

        Reading the cell from the ghost's exact corner is fragile — that pixel sits on
        the grid line, so rounding decides whether the row/column comes back as the
        intended one or its neighbour. Nudging a few pixels inward makes the answer the
        cell the user actually sees the ghost covering.
        """
        top_left = cursor_global - self._grab_offset
        return top_left + QPoint(4, 4)

    def _update_pos(self):
        cur = QCursor.pos()
        # Always move the ghost itself every tick so it tracks the cursor smoothly.
        top_left = cur - self._grab_offset
        self.move(top_left.x(), top_left.y())

        # The hit-testing + preview computation below (QApplication.widgetAt is a global
        # window hit-test) is the expensive part. Running it on every 12ms tick was the
        # main cause of the freeze/lag feeling while dragging. Skip it when the cursor
        # hasn't actually moved, and otherwise only run it every 3rd tick (~36ms, still
        # well under human perception for a hover highlight) instead of every tick.
        self._tick_count += 1
        if cur == self._last_cursor_pos:
            return
        self._last_cursor_pos = cur
        if self._tick_count % 3 != 0:
            return

        # Live preview on table under cursor
        target_widget = QApplication.widgetAt(cur)
        table = None
        p = target_widget
        while p:
            if hasattr(p, "lesson_dropped") and hasattr(p, "set_drag_preview"):
                table = p
                break
            p = p.parent() if hasattr(p, "parent") else None

        if StickyGhostWidget._hovered_table and StickyGhostWidget._hovered_table != table:
            try:
                StickyGhostWidget._hovered_table.clear_drag_preview()
            except Exception:
                pass
            StickyGhostWidget._hovered_table = None

        if table:
            StickyGhostWidget._hovered_table = table
            local_pos = table.viewport().mapFromGlobal(self._anchor_global(cur))
            r = table.rowAt(local_pos.y())
            c = table.columnAt(local_pos.x())
            if r >= 0 and c >= 0:
                table.set_drag_preview(r, c, self.drag_data)
            else:
                table.clear_drag_preview()

    def cancel(self):
        try:
            QApplication.instance().removeEventFilter(self)
        except Exception:
            pass
        if StickyGhostWidget._hovered_table:
            try:
                StickyGhostWidget._hovered_table.clear_drag_preview()
            except Exception:
                pass
            StickyGhostWidget._hovered_table = None
        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.stop()
        self.hide()
        self.deleteLater()
        if StickyGhostWidget._active_instance == self:
            StickyGhostWidget._active_instance = None

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.RightButton:
                self.cancel()
                StickyGhostWidget.last_drop_time = time.time()
                return True
                
            if event.button() == Qt.LeftButton:
                click_pos = QCursor.pos()
                # Resolve the drop anchor while the ghost is still alive; cancel()
                # schedules this widget for deletion.
                anchor_pos = self._anchor_global(click_pos)
                data = dict(self.drag_data)
                self.cancel()
                StickyGhostWidget.last_drop_time = time.time()

                target_widget = QApplication.widgetAt(click_pos)
                candidates = [obj, target_widget]
                
                # 1. Check if dropped on grid table
                table = None
                for cand in candidates:
                    p = cand
                    while p:
                        if hasattr(p, "lesson_dropped"):
                            table = p
                            break
                        p = p.parent() if hasattr(p, "parent") else None
                    if table:
                        break
                        
                if table:
                    # Same anchor the live preview used, so the lesson lands exactly on
                    # the cells the preview highlighted.
                    local_pos = table.viewport().mapFromGlobal(anchor_pos)
                    row = table.rowAt(local_pos.y())
                    col = table.columnAt(local_pos.x())
                    if row >= 0 and col >= 0:
                        table.lesson_dropped.emit(row, col, data)
                        return True
                        
                # 2. Check if dropped on dock (drag alanı)
                dock = None
                for cand in candidates:
                    p = cand
                    while p:
                        if hasattr(p, "load_unplaced") or isinstance(p, UnplacedLessonsDock):
                            dock = p
                            break
                        p = p.parent() if hasattr(p, "parent") else None
                    if dock:
                        break
                        
                if dock or (target_widget and ("dock" in str(type(target_widget)).lower() or "unplaced" in str(type(target_widget)).lower())):
                    if data.get("is_move"):
                        orig_r = data.get("origin_row", -1)
                        orig_c = data.get("origin_col", -1)
                        table = None
                        win = self.parent_window
                        if win:
                            if hasattr(win, "_editor") and getattr(win, "_editor"):
                                win = win._editor
                            if hasattr(win, "_grid") and hasattr(win._grid, "table"):
                                table = win._grid.table
                        if not table and dock:
                            p = dock.parent()
                            while p:
                                if hasattr(p, "table") and hasattr(p.table, "_delete_lesson_at"):
                                    table = p.table
                                    break
                                p = p.parent()
                        if table and orig_r >= 0 and orig_c >= 0:
                            table._delete_lesson_at(orig_r, orig_c)
                    return True
                    
                return True
                
        elif event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            self.cancel()
            StickyGhostWidget.last_drop_time = time.time()
            return True
            
        return super().eventFilter(obj, event)

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

def make_grid_action_icon(name: str, size: int = 18, color_override: str = None) -> QIcon:
    def _draw(color_hex):
        scale = 2
        pix = QPixmap(size * scale, size * scale)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.scale(scale, scale)
        color = QColor(color_hex)
        
        if name == 'siniflar':
            # Minimalist Apple SF 4-tile grid
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            gap = 2.0
            pad = 2.0
            cw = (size - 2 * pad - gap) / 2.0
            ch = (size - 2 * pad - gap) / 2.0
            p.drawRoundedRect(QRectF(pad, pad, cw, ch), 1.8, 1.8)
            p.drawRoundedRect(QRectF(pad + cw + gap, pad, cw, ch), 1.8, 1.8)
            p.drawRoundedRect(QRectF(pad, pad + ch + gap, cw, ch), 1.8, 1.8)
            p.drawRoundedRect(QRectF(pad + cw + gap, pad + ch + gap, cw, ch), 1.8, 1.8)
            
        elif name == 'ogretmenler':
            # Minimalist Apple SF Person
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            hr = size * 0.22
            p.drawEllipse(QPointF(size / 2.0, size * 0.32), hr, hr)
            path = QPainterPath()
            path.moveTo(size * 0.16, size * 0.88)
            path.quadTo(size * 0.16, size * 0.58, size / 2.0, size * 0.58)
            path.quadTo(size * 0.84, size * 0.58, size * 0.84, size * 0.88)
            path.quadTo(size / 2.0, size * 0.96, size * 0.16, size * 0.88)
            p.drawPath(path)
            
        elif name in ('add_plus', 'add_lesson'):
            p.setPen(QPen(color, 2.0, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(size / 2.0, 3.0), QPointF(size / 2.0, size - 3.0))
            p.drawLine(QPointF(3.0, size / 2.0), QPointF(size - 3.0, size / 2.0))
            
        elif name == 'lock_open':
            p.setPen(QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(size / 2.0 - 3.5, 2, 7, 7), 0, 180 * 16)
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(3.5, 7.5, size - 7, size - 9.5), 2, 2)
            p.setBrush(QColor('#FFFFFF'))
            p.drawEllipse(QPointF(size / 2.0, 11), 1.2, 1.2)
            
        elif name == 'lock_closed':
            p.setPen(QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(size / 2.0 - 3.5, 2, 7, 7), 0, 180 * 16)
            p.drawLine(QPointF(size / 2.0 - 3.5, 5.5), QPointF(size / 2.0 - 3.5, 8.5))
            p.drawLine(QPointF(size / 2.0 + 3.5, 5.5), QPointF(size / 2.0 + 3.5, 8.5))
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(3.5, 7.5, size - 7, size - 9.5), 2, 2)
            p.setBrush(QColor('#FFFFFF'))
            p.drawEllipse(QPointF(size / 2.0, 11), 1.2, 1.2)
            
        elif name == 'check_circle':
            p.setPen(Qt.NoPen)
            p.setBrush(QColor('#10B981'))
            p.drawEllipse(QRectF(1, 1, size - 2, size - 2))
            p.setPen(QPen(QColor('#FFFFFF'), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(QPointF(size * 0.28, size * 0.52), QPointF(size * 0.45, size * 0.70))
            p.drawLine(QPointF(size * 0.45, size * 0.70), QPointF(size * 0.72, size * 0.34))
            
        elif name == 'alert_triangle':
            path = QPainterPath()
            path.moveTo(size / 2.0, 1.5)
            path.lineTo(size - 1.5, size - 2)
            path.lineTo(1.5, size - 2)
            path.closeSubpath()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor('#F59E0B'))
            p.drawPath(path)
            p.setPen(QPen(QColor('#FFFFFF'), 1.5, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(size / 2.0, 5), QPointF(size / 2.0, size - 6))
            p.drawPoint(QPointF(size / 2.0, size - 3.5))
            
        elif name == 'download':
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawEllipse(4, 8, 8, 8)
            p.drawEllipse(10, 4, 10, 10)
            p.drawEllipse(size - 12, 8, 8, 8)
            p.drawRect(8, 10, size - 16, 6)
            p.setPen(QPen(QColor('#FFFFFF'), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(QPointF(size / 2.0, 10), QPointF(size / 2.0, size - 4))
            p.drawLine(QPointF(size / 2.0 - 3, size - 7), QPointF(size / 2.0, size - 4))
            p.drawLine(QPointF(size / 2.0 + 3, size - 7), QPointF(size / 2.0, size - 4))
            
        elif name == 'toggle_panel':
            p.setPen(QPen(QColor('#64748B'), 1.3))
            p.setBrush(QBrush(QColor('#F1F5F9')))
            p.drawRoundedRect(QRectF(3, 3, size - 6, size - 6), 3, 3)
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(3, 3, 5.5, size - 6), 2, 2)
            
        elif name == 'edit':
            p.setPen(Qt.NoPen)
            p.setBrush(color)
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
            p.setBrush(color)
            p.drawEllipse(QRectF(2, 2, size - 4, size - 4))
            p.setBrush(QBrush(QColor('#FFFFFF')))
            p.drawEllipse(QRectF(5, 5, 2.5, 2.5))
            p.drawEllipse(QRectF(10, 4, 2.5, 2.5))
            p.drawEllipse(QRectF(13, 8, 2.5, 2.5))
            
        p.end()
        pix.setDevicePixelRatio(scale)
        return pix

    if color_override:
        return QIcon(_draw(color_override))

    icon = QIcon()
    # Inactive (Off): Slate
    icon.addPixmap(_draw('#64748B'), QIcon.Normal, QIcon.Off)
    # Active / Checked (On): Crisp White
    icon.addPixmap(_draw('#FFFFFF'), QIcon.Normal, QIcon.On)
    # Hover / Active (On): Crisp White
    icon.addPixmap(_draw('#FFFFFF'), QIcon.Active, QIcon.On)
    # Hover / Inactive (Off): Darker Slate #1E293B
    icon.addPixmap(_draw('#1E293B'), QIcon.Active, QIcon.Off)
    return icon

def get_subject_abbr(subject_name: str, max_len: int = 6) -> str:
    """Grid cell abbreviation: strictly max 6 chars for clean layout."""
    if not subject_name: return ""
    s = str(subject_name).strip()
    tr_map = str.maketrans({'i': 'İ', 'ı': 'I', 'ç': 'Ç', 'ğ': 'Ğ', 'ö': 'Ö', 'ş': 'Ş', 'ü': 'Ü'})
    s_up = s.translate(tr_map).upper()
    
    # Pre-process specific terms
    s_up = s_up.replace("BEDEN EĞİTİMİ VE SPOR", "BEDEN")
    s_up = s_up.replace("BEDEN EGITIMI VE SPOR", "BEDEN")
    s_up = s_up.replace("BEDEN EĞİTİMİ", "BEDEN")
    s_up = s_up.replace("BEDEN EGITIMI", "BEDEN")
    s_up = s_up.replace("MATEMATİK", "MAT")
    s_up = s_up.replace("MATEMATIK", "MAT")
    s_up = s_up.replace("GEOMETRİ", "GEOM")
    s_up = s_up.replace("GEOMETRI", "GEOM")
    s_up = s_up.replace("COĞRAFYA", "COĞRAF")
    s_up = s_up.replace("COGRAFYA", "COĞRAF")
    
    mapping = {
        "TÜRK DİLİ VE EDEBİYATI": "TDE",
        "TURK DILI VE EDEBIYATI": "TDE",
        "TÜRKÇE": "TÜR",
        "TURKCE": "TÜR",
        "EDEBİYAT": "EDEB",
        "EDEBIYAT": "EDEB",
        "GÖRSEL SANATLAR": "GÖRSEL",
        "GORSEL SANATLAR": "GÖRSEL",
        "GÖRSEL": "GÖRSEL",
        "GORSEL": "GÖRSEL",
        "İNGİLİZCE": "İNG",
        "INGILIZCE": "İNG",
        "ALMANCA": "ALM",
        "DİN KÜLTÜRÜ VE AHLAK BİLGİSİ": "DİN",
        "DIN KULTURU VE AHLAK BILGISI": "DİN",
        "DİN KÜLTÜRÜ": "DİN",
        "DIN KULTURU": "DİN",
        "FELSEFE": "FELS",
        "REHBERLİK": "REHBER",
        "REHBERLIK": "REHBER",
        "BİYOLOJİ": "BİYO",
        "BIYOLOJI": "BİYO",
        "KİMYA": "KİMYA",
        "KIMYA": "KİMYA",
        "FİZİK": "FİZİK",
        "FIZIK": "FİZİK",
        "TARİH": "TARİH",
        "TARIH": "TARİH",
        "SEÇMELİ": "SEÇ",
        "SECMELI": "SEÇ",
    }
    
    for k, v in mapping.items():
        if s_up == k or s_up.startswith(k):
            s_up = s_up.replace(k, v)
            break
            
    import re
    m = re.search(r'^(.+?)\s*(\d+)$', s_up)
    if m:
        base_title = m.group(1).strip()
        num_suffix = f" {m.group(2)}"
    else:
        base_title = s_up
        num_suffix = ""
        
    if len(base_title) + len(num_suffix) <= max_len:
        return f"{base_title}{num_suffix}"
        
    allowed_base_len = max_len - len(num_suffix)
    if allowed_base_len > 0:
        return f"{base_title[:allowed_base_len]}{num_suffix}".strip()[:max_len]
    return s_up[:max_len]


from PySide6.QtCore import QRect

# Başlık şeridi renkleri: yerleşim durumunun görsel karşılığı (bkz.
# placement_engine). Tek eşleme noktası burasıdır, bileşenlere dağılmaz.
_HEADER_STATE_COLORS = {
    "GREEN": QColor(34, 197, 94),
    "BLUE": QColor(59, 130, 246),
    "RED": QColor(239, 68, 68),
    "GREY": QColor(148, 163, 184),
    "SELECTED": QColor(250, 204, 21),
}


class AsCTimetableHeader(QHeaderView):
    """aSc Timetables style two-level header: Days on top spanning periods, Period numbers below (Scaled down 25%)."""
    def __init__(self, periods: int = 8, days_list: list = None, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.periods = max(1, int(periods))
        self.days_list = days_list or DAYS[:5]
        self.setFixedHeight(38)
        self.setSectionResizeMode(QHeaderView.Stretch)
        self.setMinimumSectionSize(0)
        self.sectionResized.connect(lambda *args: self.viewport().update())
        self.geometriesChanged.connect(lambda *args: self.viewport().update())

    def set_config(self, periods: int, days_list: list):
        self.periods = max(1, int(periods))
        self.days_list = days_list
        self.viewport().update()

    def set_placement_states(self, states: dict):
        """Sürükleme sırasında sütun başlıklarının durumu: {sütun: görsel}.

        Başlık "bu saat dolu mu"yu değil, "SÜRÜKLENEN ders buradan başlayabilir
        mi"yi gösterir; renk yalnızca elde kart varken görünür.
        """
        self._placement_states = states or {}
        self.viewport().update()

    def paintSection(self, painter, rect, logicalIndex):
        pass  # Suppress default section painting to prevent overlapping/glitched text

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setClipping(False)  # Completely disable painter clipping so the entire header area is cleanly repainted
        
        vw = self.viewport().width()
        vh = self.viewport().height()
        
        # Fill header background with flat clean tone
        painter.fillRect(self.viewport().rect(), QColor("#E2E8F0"))
        
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
                state = (getattr(self, "_placement_states", None) or {}).get(col_idx)
                painter.fillRect(rect, _HEADER_STATE_COLORS.get(state, QColor("#E2E8F0")))
                painter.setPen(QPen(QColor("#CBD5E1"), 1))
                painter.drawLine(x, vh - 1, x + w, vh - 1)
                painter.drawLine(x + w - 1, 0, x + w - 1, vh)
                
                painter.setPen(QPen(QColor("#0F172A")))
                painter.setFont(QFont(FONT_FAMILY, 8.5, QFont.Bold))
                painter.drawText(rect, Qt.AlignCenter, day_name)
                
                # Day separator line on right edge
                painter.setPen(QPen(QColor("#64748B"), 1.5))
                painter.drawLine(x + w - 1, 0, x + w - 1, vh)
            painter.end()
            return
            
        # ── MULTI-SHEET VIEW (Days on top row y=0..19, Period numbers on bottom row y=19..38)
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
                
            day_rect = QRect(x_start, 0, day_w, 19)
            painter.fillRect(day_rect, QColor("#E2E8F0"))
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(x_start, 18, x_end, 18)
            painter.drawLine(x_end - 1, 0, x_end - 1, 18)
            
            painter.setPen(QPen(QColor("#0F172A")))
            font_day = QFont(FONT_FAMILY, 8, QFont.Bold)
            painter.setFont(font_day)
            
            # Keep day label visible and centered in the viewport portion of that day
            vis_left = max(x_start, 0)
            vis_right = min(x_end, vw)
            if vis_right > vis_left:
                vis_rect = QRect(vis_left, 0, vis_right - vis_left, 19)
                if vis_rect.width() >= 20:
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
            
            period_rect = QRect(x, 19, w, 19)
            state = (getattr(self, "_placement_states", None) or {}).get(col_idx)
            painter.fillRect(period_rect, _HEADER_STATE_COLORS.get(state, QColor("#F8FAFC")))
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(x, 37, x + w, 37)
            painter.drawLine(x + w - 1, 19, x + w - 1, 37)
            
            painter.setPen(QPen(QColor("#334155")))
            font_p = QFont(FONT_FAMILY, 7.5, QFont.Bold)
            painter.setFont(font_p)
            painter.drawText(period_rect, Qt.AlignCenter, str(period_num))
            
            # Draw prominent dividing stroke at each day boundary
            if (col_idx + 1) % periods == 0:
                painter.setPen(QPen(QColor("#64748B"), 1.5))
                painter.drawLine(x + w - 1, 0, x + w - 1, vh)
            
        painter.end()


class AsCVerticalHeader(QHeaderView):
    """Modern header for rows with support for unplaced hours badges."""
    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)
        self.setSectionResizeMode(QHeaderView.Stretch)
        self.setDefaultAlignment(Qt.AlignCenter)
        self.setDefaultSectionSize(36)
        self.setMinimumSectionSize(0)
        self.setMinimumWidth(82)

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        # 1. Fill background & borders
        painter.fillRect(rect, QColor("#F8FAFC"))
        painter.setPen(QPen(QColor("#E2E8F0"), 1))
        painter.drawLine(rect.right(), rect.top(), rect.right(), rect.bottom())
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        # 2. Unplaced hours indicator badge (Artan dersler - sağ alt köşe)
        table = self.parent()
        grid = table.parent() if table else None
        
        # Robustly locate data_store
        data_store = None
        curr = self
        while curr:
            if hasattr(curr, "data_store") and isinstance(getattr(curr, "data_store"), dict):
                data_store = curr.data_store
                break
            curr = curr.parent()
        if not data_store:
            app = QApplication.instance()
            if app:
                for w in app.topLevelWidgets():
                    if hasattr(w, "data_store") and isinstance(getattr(w, "data_store"), dict):
                        data_store = w.data_store
                        break

        unplaced_hrs = 0
        if grid and data_store:
            display_mode = getattr(grid, "current_view_mode", "classes")
            target_name = ""
            if display_mode == "classes":
                class_list = getattr(grid, "class_list", []) or []
                if 0 <= logicalIndex < len(class_list):
                    target_name = class_list[logicalIndex]
            elif display_mode == "teachers":
                teacher_list = getattr(grid, "teacher_list", []) or []
                if 0 <= logicalIndex < len(teacher_list):
                    target_name = teacher_list[logicalIndex]

            if target_name:
                norm_tgt = target_name.replace(" ", "").upper()
                # 1. Total assigned hours
                total_assigned = 0
                for a in data_store.get("atamalar", []) or []:
                    if isinstance(a, dict):
                        if display_mode == "classes":
                            c_raw = str(a.get("class") or a.get("sinif") or a.get("class_name") or "")
                            if norm_tgt == c_raw.replace(" ", "").upper() or target_name in c_raw or c_raw in target_name:
                                total_assigned += int(a.get("duration", 1) or 1)
                        else:
                            t_raw = str(a.get("teacher") or a.get("ogretmen") or a.get("teacher_name") or "")
                            if norm_tgt == t_raw.replace(" ", "").upper() or target_name in t_raw or t_raw in target_name:
                                total_assigned += int(a.get("duration", 1) or 1)

                # 2. Total placed hours on the active grid
                total_placed = 0
                if hasattr(grid, "_placed_lessons") and grid._placed_lessons:
                    seen_blocks = set()
                    for (r, c), info in grid._placed_lessons.items():
                        if not isinstance(info, dict):
                            continue
                        orig_r = info.get("origin_row", r)
                        orig_c = info.get("origin_col", c)
                        block_key = (orig_r, orig_c, info.get("block_id") or id(info))
                        if block_key in seen_blocks:
                            continue
                        seen_blocks.add(block_key)
                        
                        if display_mode == "classes":
                            c_raw = str(info.get("class_name") or info.get("class") or "")
                            if norm_tgt == c_raw.replace(" ", "").upper() or target_name in c_raw or c_raw in target_name:
                                total_placed += int(info.get("duration", 1) or 1)
                        else:
                            t_raw = str(info.get("teacher_name") or info.get("teacher") or "")
                            if norm_tgt == t_raw.replace(" ", "").upper() or target_name in t_raw or t_raw in target_name:
                                total_placed += int(info.get("duration", 1) or 1)
                else:
                    for p in data_store.get("grid_placements", []) or []:
                        if isinstance(p, dict):
                            if display_mode == "classes":
                                c_raw = str(p.get("class_name") or p.get("class") or "")
                                if norm_tgt == c_raw.replace(" ", "").upper() or target_name in c_raw or c_raw in target_name:
                                    total_placed += int(p.get("duration", 1) or 1)
                            else:
                                t_raw = str(p.get("teacher_name") or p.get("teacher") or "")
                                if norm_tgt == t_raw.replace(" ", "").upper() or target_name in t_raw or t_raw in target_name:
                                    total_placed += int(p.get("duration", 1) or 1)

                unplaced_hrs = max(0, total_assigned - total_placed)

        # Draw section text
        model = self.model()
        text = str(model.headerData(logicalIndex, Qt.Vertical, Qt.DisplayRole) or "")
        painter.setFont(QFont(FONT_FAMILY, 8.5, QFont.Bold))
        painter.setPen(QColor("#0F172A"))
        if unplaced_hrs > 0:
            painter.drawText(rect.adjusted(6, 0, -28, 0), Qt.AlignLeft | Qt.AlignVCenter, text)
            badge_text = f"{unplaced_hrs}s"
            badge_w = 26 if len(badge_text) <= 3 else 32
            badge_h = 13
            badge_rect = QRectF(rect.right() - badge_w - 2, rect.bottom() - badge_h - 2, badge_w, badge_h)
            painter.setBrush(QBrush(QColor("#FEE2E2")))
            painter.setPen(QPen(QColor("#EF4444"), 1))
            painter.drawRoundedRect(badge_rect, 3, 3)
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.setPen(QColor("#DC2626"))
            painter.drawText(badge_rect, Qt.AlignCenter, badge_text)
        else:
            painter.drawText(rect.adjusted(2, 0, -2, 0), Qt.AlignCenter, text)

        painter.restore()


def _compute_free_slot_capacity(data_store, class_name, teacher_name, is_comb, combined_classes, exclude_subject_fmt):
    """Best-effort estimate of how many empty slots across the whole week are actually
    available for a lesson, so a distribution edit (e.g. picking "2+2+1" = 5 hours) can be
    checked against reality before it's applied. Returns None if there's nothing to check
    against (no class and no teacher), otherwise the slot count as an int.

    "Available" = total weekly slots, minus slots closed off by timeoff/restrictions, minus
    slots already occupied by OTHER subjects. Hours this SAME subject/class/teacher already
    occupies are not subtracted — those aren't "used up" by redefining the structure, they're
    part of the lesson itself. For a combined lesson (multiple classes at once) and/or when a
    teacher is set, the binding constraint is whichever entity has the least room.
    """
    from auto_scheduler import format_tr_name as fmt, matches_class as mcls

    settings = data_store.get("settings", {})
    periods = int(settings.get("periods", data_store.get("ders_saati", 8)) or 8)
    days_list = settings.get("days")
    if not days_list:
        days_count = int(settings.get("days_count", settings.get("day_count", data_store.get("gun_sayisi", 5))))
        days_list = DAYS[:days_count]
    total_slots = periods * max(1, len(days_list))

    target_classes = list(combined_classes) if (is_comb and combined_classes) else ([class_name] if class_name else [])
    if not target_classes and not teacher_name:
        return None

    def _occupied_by_others(matches_entity_fn, timeoff_rows):
        unusable = set()
        for d_idx, day_offs in enumerate(timeoff_rows or []):
            for p_idx, val in enumerate(day_offs):
                if val == 0:
                    unusable.add((d_idx, p_idx))
        for p in data_store.get("grid_placements", []):
            if not matches_entity_fn(p):
                continue
            p_s = fmt(p.get("subject_name") or p.get("subject") or "")
            if p_s == exclude_subject_fmt:
                continue
            d = int(p.get("day") if "day" in p else p.get("col", 0))
            per = int(p.get("period") if "period" in p else p.get("row", 0))
            dur = int(p.get("duration", 1))
            for off in range(dur):
                unusable.add((d, per + off))
        return unusable

    capacities = []
    for cn in target_classes:
        timeoff = []
        for c in data_store.get("siniflar", []):
            if mcls(c.get("ad", ""), cn) or mcls(cn, c.get("ad", "")):
                timeoff = c.get("timeoff", [])
                break

        def _class_match(p, cn=cn):
            p_c = (p.get("class_name") or p.get("class") or "").strip()
            return bool(mcls(p_c, cn) or mcls(cn, p_c))

        unusable = _occupied_by_others(_class_match, timeoff)
        capacities.append(total_slots - len(unusable))

    if teacher_name:
        t_fmt = fmt(teacher_name)
        timeoff = []
        for t in data_store.get("ogretmenler", []):
            if fmt(t.get("ad", "")) == t_fmt:
                timeoff = t.get("timeoff", [])
                break

        def _teacher_match(p):
            return fmt(p.get("teacher_name") or p.get("teacher") or "") == t_fmt

        unusable = _occupied_by_others(_teacher_match, timeoff)
        capacities.append(total_slots - len(unusable))

    return min(capacities) if capacities else None


class DraggableLessonCard(QWidget):
    def __init__(self, lesson_id: str, subject_name: str, color: str, duration: int = 1, count: int = 1, teacher: str = "", class_name: str = "", display_mode: str = "classes", blocked_reason: str = "", parent=None):
        super().__init__(parent)
        self.lesson_id = str(lesson_id)
        self.subject_name = subject_name
        self.color = color or "#94A3B8"
        self.duration = max(1, int(duration or 1))
        self.count = max(1, int(count or 1))
        self.teacher = teacher
        self.class_name = class_name
        self.display_mode = display_mode
        self.blocked_reason = blocked_reason
        self._is_hovered = False
        self._is_pressed = False
        
        self.abbr = get_subject_abbr(subject_name)
        self.is_comb = bool("," in class_name or "&" in class_name or "+" in class_name)
        if self.is_comb:
            comb_parts = [c.split("(")[0].strip() for c in class_name.replace("&", "+").replace(",", "+").split("+") if c.strip()]
            self.clean_cls_display = "+".join(comb_parts) if comb_parts else class_name.replace(" ", "")
        else:
            self.clean_cls_display = class_name.split("(")[0].strip() if class_name else ""
            
        # Ultra-compact modern proportions (Shortened on X axis)
        if self.duration == 1:
            base_w = max(46, min(65, 7.5 * len(self.clean_cls_display) + 10)) if (self.is_comb and display_mode == "teachers") else 46
        elif self.duration == 2:
            base_w = max(72, min(95, 7.5 * len(self.clean_cls_display) + 16)) if (self.is_comb and display_mode == "teachers") else 72
        else:
            base_w = max(98, min(125, 7.5 * len(self.clean_cls_display) + 20)) if (self.is_comb and display_mode == "teachers") else 98
            
        self.card_w = base_w
        self.card_h = 26
        
        stack_depth = min(self.count, 3)
        extra_w = 2.5 * (stack_depth - 1) if stack_depth > 1 else 0
        extra_h = 2.5 * (stack_depth - 1) if stack_depth > 1 else 0
        
        self.total_w = int(base_w + extra_w + 4)
        self.total_h = int(self.card_h + extra_h + 4)
        
        self.setFixedSize(self.total_w, self.total_h)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_card_context_menu)
        
        # Tooltip
        dur_str = f"{self.duration} Saatlik Blok" if self.duration > 1 else "1 Saatlik Ders"
        cnt_str = f"\nDestedeki Kart Sayısı: {self.count} Adet" if self.count > 1 else ""
        comb_str = "\n(Birleşik / Ortak Ders)" if self.is_comb else ""
        tch_str = f"\nÖğretmen: {self.teacher}" if self.teacher else ""
        cls_str = f"\nSınıf: {self.class_name}" if self.class_name else ""
        blk_str = f"\n⚠️ Kısıtlama: {self.blocked_reason}" if self.blocked_reason else ""
        self.setToolTip(f"<b>{self.subject_name}</b> ({dur_str}){cnt_str}{cls_str}{tch_str}{comb_str}{blk_str}")

    def set_color(self, new_hex: str):
        if new_hex:
            self.color = str(new_hex).upper()
            self.update()
            if hasattr(self, "repaint"):
                self.repaint()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        
        base_color = QColor(self.color)
        if not base_color.isValid() or str(self.color).upper() in ("#FFFFFF", "#000000", "#94A3B8", ""):
            try:
                from dialogs.color_picker_dialog import resolve_subject_color
                win = self.window()
                ds = getattr(win, "data_store", None)
                if not ds and hasattr(win, "parent") and callable(win.parent):
                    ds = getattr(win.parent(), "data_store", None)
                cur = resolve_subject_color(self.subject_name, ds)
                if cur:
                    self.color = cur
                    base_color = QColor(cur)
            except Exception:
                pass
        if not base_color.isValid():
            base_color = QColor("#64748B")
            
        lum = (0.299 * base_color.red() + 0.587 * base_color.green() + 0.114 * base_color.blue())
        text_color = QColor("#FFFFFF") if lum < 165 else QColor("#0F172A")
        
        stack_depth = min(self.count, 3)
        w = self.card_w
        h = self.card_h
        
        # 1. Draw Underneath Card Layers (for stacks > 1)
        for layer in range(stack_depth - 1, 0, -1):
            ox = 1.5 + layer * 2.5
            oy = 1.5 + layer * 2.5
            r = QRectF(ox, oy, w, h)
            
            # Ambient soft shadow
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 18))
            p.drawRoundedRect(r.translated(0.5, 0.5), 4, 4)
            
            # Layer body
            layer_color = base_color.darker(110 + layer * 10)
            p.setPen(QPen(QColor(0, 0, 0, 45), 1))
            p.setBrush(layer_color)
            p.drawRoundedRect(r, 4, 4)
            
            # Top highlight edge on stack
            p.setPen(QPen(QColor(255, 255, 255, 55), 1))
            p.drawLine(QPointF(ox + 3, oy + 1), QPointF(ox + w - 3, oy + 1))
            
        # 2. Top Card
        top_ox = 2 if self._is_pressed else 1.5
        top_oy = 2 if self._is_pressed else 1.5
        top_r = QRectF(top_ox, top_oy, w, h)
        
        # Top card ambient shadow
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 28 if not self._is_hovered else 40))
        p.drawRoundedRect(top_r.translated(0.5, 1), 4, 4)
        
        # Top card gradient
        grad = QLinearGradient(top_ox, top_oy, top_ox, top_oy + h)
        if self._is_hovered:
            grad.setColorAt(0.0, base_color.lighter(116))
            grad.setColorAt(0.5, base_color.lighter(104))
            grad.setColorAt(1.0, base_color)
        else:
            grad.setColorAt(0.0, base_color.lighter(108))
            grad.setColorAt(0.5, base_color)
            grad.setColorAt(1.0, base_color.darker(106))
            
        # Top card crisp border stroke
        border_color = QColor("#2563EB") if self._is_hovered else QColor(0, 0, 0, 70)
        border_w = 1.3 if self._is_hovered else 1.0
        p.setPen(QPen(border_color, border_w))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(top_r, 4, 4)
        
        # Top inner subtle shine
        p.setPen(QPen(QColor(255, 255, 255, 85), 1))
        p.drawLine(QPointF(top_ox + 3, top_oy + 1), QPointF(top_ox + w - 3, top_oy + 1))
        
        # 3. Truly Centered Subject Text
        if self.display_mode == "teachers" and self.clean_cls_display:
            p.setFont(QFont("Segoe UI", 7, QFont.Bold))
            p.setPen(text_color)
            p.drawText(QRectF(top_ox + 1, top_oy, w - 2, h * 0.5), Qt.AlignCenter, self.clean_cls_display)
            p.setFont(QFont("Segoe UI", 6.5, QFont.Normal))
            p.drawText(QRectF(top_ox + 1, top_oy + h * 0.45, w - 2, h * 0.5), Qt.AlignCenter, self.abbr[:4])
        else:
            p.setFont(QFont("Segoe UI", 7, QFont.Bold))
            p.setPen(text_color)
            display_txt = self.abbr if len(self.abbr) <= 6 else self.abbr[:5] + "."
            p.drawText(top_r, Qt.AlignCenter, display_txt)
            
        # 4. Combined lesson '+' badge in top-left
        if self.is_comb:
            badge_r = QRectF(top_ox + 2, top_oy + 2, 9, 9)
            p.setPen(QPen(QColor("#1D4ED8"), 0.8))
            p.setBrush(QBrush(QColor("#EFF6FF")))
            p.drawRoundedRect(badge_r, 2, 2)
            p.setFont(QFont("Segoe UI", 6, QFont.Bold))
            p.setPen(QColor("#1D4ED8"))
            p.drawText(badge_r, Qt.AlignCenter, "+")
            
        # 5. Count badge in top-right: sleek modern dark capsule pill (+2, +3, +4)
        if self.count > 1:
            cnt_str = f"+{self.count}"
            badge_w = 15 if len(cnt_str) <= 2 else 19
            badge_h = 10
            badge_r = QRectF(top_ox + w - badge_w - 2, top_oy + 2, badge_w, badge_h)
            
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(15, 23, 42, 225))
            p.drawRoundedRect(badge_r, 3, 3)
            
            p.setFont(QFont("Segoe UI", 5.5, QFont.Bold))
            p.setPen(QColor("#FFFFFF"))
            p.drawText(badge_r, Qt.AlignCenter, cnt_str)
            
        p.end()

    def render_single_card_pixmap(self):
        pm = QPixmap(self.card_w + 4, self.card_h + 4)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        
        base_color = QColor(self.color)
        if not base_color.isValid():
            base_color = QColor("#64748B")
        lum = (0.299 * base_color.red() + 0.587 * base_color.green() + 0.114 * base_color.blue())
        text_color = QColor("#FFFFFF") if lum < 165 else QColor("#0F172A")
        
        r = QRectF(1, 1, self.card_w, self.card_h)
        
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 30))
        p.drawRoundedRect(r.translated(1, 1), 6, 6)
        
        grad = QLinearGradient(1, 1, 1, 1 + self.card_h)
        grad.setColorAt(0.0, base_color.lighter(108))
        grad.setColorAt(0.5, base_color)
        grad.setColorAt(1.0, base_color.darker(106))
        
        p.setPen(QPen(QColor(0, 0, 0, 75), 1))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(r, 6, 6)
        
        p.setPen(QPen(QColor(255, 255, 255, 90), 1))
        p.drawLine(QPointF(3, 2), QPointF(self.card_w - 1, 2))
        
        p.setFont(QFont("Segoe UI", 8.5, QFont.Bold))
        p.setPen(text_color)
        if self.display_mode == "teachers" and self.clean_cls_display:
            p.setFont(QFont("Segoe UI", 8, QFont.Bold))
            p.drawText(QRectF(4, 2, self.card_w - 8, self.card_h * 0.48), Qt.AlignCenter, self.clean_cls_display)
            p.setFont(QFont("Segoe UI", 7.5, QFont.Normal))
            p.drawText(QRectF(4, self.card_h * 0.46, self.card_w - 8, self.card_h * 0.48), Qt.AlignCenter, self.abbr[:5])
        else:
            display_txt = self.abbr if len(self.abbr) <= 7 else self.abbr[:6] + "."
            p.drawText(r, Qt.AlignCenter, display_txt)
            
        p.end()
        return pm

    def enterEvent(self, event):
        super().enterEvent(event)
        self._is_hovered = True
        self.update()
        w = self
        while w:
            if hasattr(w, "update_info_panel"):
                w.update_info_panel({
                    "subject_name": self.subject_name,
                    "color": self.color,
                    "duration": self.duration,
                    "teacher": self.teacher,
                    "class_name": self.class_name,
                    "is_combined": self.is_comb,
                    "combined_classes": getattr(self, "combined_classes", [])
                })
                break
            w = w.parent()
        win = self.window()
        if win and hasattr(win, "statusBar") and win.statusBar():
            cls_txt = self.class_name if self.class_name else "-"
            tch_txt = self.teacher if self.teacher else "-"
            cnt_txt = f"  |  Deste: {self.count} adet" if self.count > 1 else ""
            dur_txt = f"{self.duration} Saatlik Blok" if self.duration > 1 else "1 Saatlik Ders"
            win.statusBar().showMessage(f"{self.subject_name}  •  {cls_txt}  •  {tch_txt}  ({dur_txt}){cnt_txt}")

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._is_hovered = False
        self.update()
        w = self
        while w:
            if hasattr(w, "update_info_panel"):
                w.update_info_panel(getattr(w, "_current_selected_lesson_info", None))
                break
            w = w.parent()
        
    def _get_card_data(self):
        return {
            "lesson_id": self.lesson_id,
            "subject_name": self.subject_name,
            "color": self.color,
            "duration": self.duration,
            "teacher": self.teacher,
            "class_name": self.class_name,
            "is_combined": bool(getattr(self, "is_combined", False) or ("+" in self.class_name or "&" in self.class_name)),
            "combined_classes": getattr(self, "combined_classes", [])
        }

    def _start_standard_drag(self, pos):
        drag = QDrag(self)
        mime = QMimeData()
        data = self._get_card_data()

        pix = self.render_single_card_pixmap()
        # Tutma noktasi kartin ILK saatinin ortasi: imlecin altindaki hucre dersin
        # birinci saati olur, kart imlecin sagina dogru uzar.
        dur = max(1, int(data.get("duration", 1) or 1))
        hotspot = QPoint(max(1, pix.width() // (2 * dur)), pix.height() // 2)
        data["grab_dx"] = 0
        data["grab_dy"] = 0

        mime.setData("application/x-lesson", QByteArray(json.dumps(data).encode()))
        drag.setMimeData(mime)
        drag.setPixmap(pix)
        drag.setHotSpot(hotspot)
        drag.exec_(Qt.MoveAction)

    def _start_sticky_drag(self):
        data = self._get_card_data()
        pix = self.render_single_card_pixmap()
        dur = max(1, int(data.get("duration", 1) or 1))
        grab = QPoint(max(1, pix.width() // (2 * dur)), pix.height() // 2)
        data["grab_dx"] = 0
        data["grab_dy"] = 0
        win = self.window()
        StickyGhostWidget(pix, data, win, grab_offset=grab)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self._is_pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and hasattr(self, '_drag_start_pos'):
            if (event.pos() - self._drag_start_pos).manhattanLength() >= 5:
                self._is_pressed = False
                self.update()
                self._start_standard_drag(event.pos())
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_pressed:
            self._is_pressed = False
            self.update()
        if event.button() == Qt.LeftButton and hasattr(self, '_drag_start_pos'):
            if (event.pos() - self._drag_start_pos).manhattanLength() < 5:
                self._start_sticky_drag()
                return
        super().mouseReleaseEvent(event)

    def _show_card_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #FFFFFF; border: 1px solid #CBD5E1; font-family: 'Segoe UI'; font-size: 12px; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 22px; border-radius: 4px; }
            QMenu::item:selected { background: #EEF2FF; color: #4338CA; font-weight: bold; }
            QMenu::separator { height: 1px; background: #E2E8F0; margin: 3px 8px; }
        """)
        
        act_palette = menu.addAction(make_context_icon("🎨", "#E91E63", "#C2185B"), f"🎨 {self.subject_name} Rengini Ayarla...")
        menu.addSeparator()
        
        # Split / Combine options
        act_split = None
        act_merge = None
        if self.duration == 2:
            act_split = menu.addAction(make_context_icon("✂️", "#0284C7", "#0369A1"), "✂️ İkiye Böl (1+1 Saat Yap)")
        elif self.duration == 1 and self.count >= 2:
            act_merge = menu.addAction(make_context_icon("🔗", "#0284C7", "#0369A1"), "🔗 2 Kartı Birleştir (2 Saatlik Blok Yap)")
            
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
        if not hasattr(win, "data_store") and hasattr(win, "parent") and hasattr(win.parent(), "data_store"):
            win = win.parent()
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
                self.update()
                update_subject_color_globally(self, data_store, self.subject_name, new_hex)
            return

        def _row_matches(a, s_fmt, c_fmt, t_fmt):
            from auto_scheduler import format_tr_name as _fmt2, normalize_clean as _nc2
            a_s = _fmt2(a.get("subject") or a.get("ders") or "")
            a_c = _fmt2(a.get("class") or a.get("sinif") or "")
            a_t_raw = a.get("teacher") or a.get("ogretmen") or ""
            a_t = _fmt2(a_t_raw)
            return (a_s == s_fmt and (not c_fmt or a_c == c_fmt) and
                    (not t_fmt or a_t == t_fmt or _nc2(a_t_raw) == _nc2(self.teacher)))

        parts = None
        if action == act_split and data_store and "atamalar" in data_store:
            from auto_scheduler import format_tr_name as _fmt
            s_fmt = _fmt(self.subject_name)
            c_fmt = _fmt(self.class_name)
            t_fmt = _fmt(self.teacher)
            for idx, a in enumerate(data_store["atamalar"]):
                if _row_matches(a, s_fmt, c_fmt, t_fmt):
                    dist = a.get("distribution")
                    if dist and 2 in dist:
                        new_dist = []
                        split_done = False
                        for p in dist:
                            if p == 2 and not split_done:
                                new_dist.extend([1, 1])
                                split_done = True
                            else:
                                new_dist.append(p)
                        parts = new_dist
                        break
            if not parts:
                parts = [1, 1]
        elif action == act_merge and data_store and "atamalar" in data_store:
            from auto_scheduler import format_tr_name as _fmt
            s_fmt = _fmt(self.subject_name)
            c_fmt = _fmt(self.class_name)
            t_fmt = _fmt(self.teacher)
            for idx, a in enumerate(data_store["atamalar"]):
                if _row_matches(a, s_fmt, c_fmt, t_fmt):
                    dist = a.get("distribution")
                    if dist and dist.count(1) >= 2:
                        new_dist = []
                        ones_count = 0
                        for p in dist:
                            if p == 1 and ones_count < 2:
                                ones_count += 1
                                if ones_count == 2:
                                    new_dist.append(2)
                            else:
                                new_dist.append(p)
                        parts = new_dist
                        break
            if not parts:
                parts = [2]
        elif action == act_2_2:
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
                from auto_scheduler import format_tr_name as _fmt
                s_fmt = _fmt(self.subject_name)
                c_fmt = _fmt(self.class_name)
                t_fmt = _fmt(self.teacher)
                data_store["atamalar"] = [a for a in data_store["atamalar"] if not _row_matches(a, s_fmt, c_fmt, t_fmt)]
                if win:
                    if hasattr(win, "save_db"): win.save_db()
                    if hasattr(win, "_refresh_tree"): win._refresh_tree()
                    if hasattr(win, "_refresh_grid"): win._refresh_grid()
                    if hasattr(win, "_refresh_unplaced_lessons"): win._refresh_unplaced_lessons()
            return

        if parts and data_store:
            from auto_scheduler import format_tr_name as _fmt
            if "atamalar" in data_store:
                s_fmt = _fmt(self.subject_name)
                c_fmt = _fmt(self.class_name)
                t_fmt = _fmt(self.teacher)

                capacity = _compute_free_slot_capacity(
                    data_store, self.class_name, self.teacher,
                    getattr(self, "is_comb", False), getattr(self, "combined_classes", []), s_fmt
                )
                if capacity is not None and sum(parts) > capacity:
                    QMessageBox.warning(
                        self, "Yeterli Boş Saat Yok",
                        f"⚠️ '{self.subject_name}' dersi için seçilen <b>{'+'.join(map(str, parts))}</b> dağılımı "
                        f"toplam <b>{sum(parts)} saat</b> gerektiriyor.<br><br>"
                        f"Ancak <b>{self.class_name}</b>{' / ' + self.teacher if self.teacher else ''} için çizelgede "
                        f"sadece <b>{capacity} saat</b> boş yer var.<br><br>"
                        "Lütfen daha küçük bir dağılım seçin ya da önce çizelgede yer açın."
                    )
                    return

                matching_indices = [i for i, a in enumerate(data_store["atamalar"]) if _row_matches(a, s_fmt, c_fmt, t_fmt)]
                if not matching_indices:
                    matching_indices = [
                        i for i, a in enumerate(data_store["atamalar"])
                        if _fmt(a.get("subject") or a.get("ders") or "") == s_fmt
                    ]

                if matching_indices:
                    old_rows = data_store["atamalar"]
                    template = dict(old_rows[matching_indices[0]])
                    matching_set = set(matching_indices)
                    insert_pos = matching_indices[0]

                    # Dağılım TEK satırda tutulur.
                    #
                    # Eskiden her parça için ayrı bir atama satırı yazılıyordu
                    # (2+2+1 -> hours=2, hours=2, hours=1). Kayıt sırasında
                    # sanitize_atamalar aynı (ders, öğretmen, sınıf) satırlarını
                    # teke indirdiği için geriye SON parça kalıyor, duration ise
                    # type'tan yeniden hesaplanıyordu: ortaya duration=5 ama
                    # hours=1 taşıyan bir satır çıkıyordu. Hangi ekranın hangi
                    # alanı okuduğuna göre aynı ders 5 saat de 1 saat de
                    # görünebiliyordu — sınıf ve öğretmen toplamlarının
                    # tutmamasının sebeplerinden biri buydu.
                    import uuid as _uuid
                    import lesson_hours
                    new_row = dict(template)
                    new_row["type"] = "+".join(map(str, parts))
                    new_row["distribution"] = list(parts)
                    new_row["duration"] = sum(parts)
                    new_row["id"] = str(_uuid.uuid4())
                    lesson_hours.sync_keys(new_row)
                    new_rows = [new_row]

                    tail = [a for idx, a in enumerate(old_rows) if idx >= insert_pos and idx not in matching_set]
                    data_store["atamalar"] = old_rows[:insert_pos] + new_rows + tail

                    # Clean any loose/manual unplaced cards matching this subject+class so they regenerate cleanly with new distribution
                    from auto_scheduler import format_tr_name as _fmt
                    s_clean = _fmt(self.subject_name)
                    c_clean = _fmt(self.class_name)
                    if "loose_unplaced_cards" in data_store:
                        data_store["loose_unplaced_cards"] = [
                            lc for lc in data_store["loose_unplaced_cards"]
                            if not (_fmt(lc.get("subject_name", "")) == s_clean and (not c_clean or _fmt(lc.get("class_name", "")) == c_clean))
                        ]
                    if "manual_unplaced_cards" in data_store:
                        data_store["manual_unplaced_cards"] = [
                            mc for mc in data_store["manual_unplaced_cards"]
                            if not (_fmt(mc.get("subject_name", "")) == s_clean and (not c_clean or _fmt(mc.get("class_name", "")) == c_clean))
                        ]

            if win:
                if hasattr(win, "save_db"): win.save_db()
                if hasattr(win, "_refresh_tree"): win._refresh_tree()
                if hasattr(win, "_refresh_unplaced_lessons"):
                    win._refresh_unplaced_lessons()
                if hasattr(win, "statusBar") and win.statusBar():
                    win.statusBar().showMessage(f"ℹ️ '{self.subject_name}' dersi {'+'.join(map(str, parts))} yapısına dönüştürüldü ({sum(parts)} saat).", 4000)


class UnplacedLessonsDock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(64)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(6, 0, 6, 0)
        self.layout.setSpacing(8)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAcceptDrops(True)
        self.scroll.viewport().setAcceptDrops(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:horizontal { height: 4px; background: transparent; margin: 0; }
            QScrollBar::handle:horizontal { background: #CBD5E1; border-radius: 2px; }
            QScrollBar::handle:horizontal:hover { background: #94A3B8; }
        """)
        
        self.container = QWidget()
        self.container.setAcceptDrops(True)
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(6, 6, 6, 6)
        self.container_layout.setSpacing(10)
        self.container_layout.setAlignment(Qt.AlignLeft)
        
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll, 1)
        
        self.scroll.installEventFilter(self)
        self.scroll.viewport().installEventFilter(self)
        self.container.installEventFilter(self)

    def _on_add_more_clicked(self):
        win = self.window()
        if not hasattr(win, "data_store") and hasattr(win, "parent") and hasattr(win.parent(), "data_store"):
            win = win.parent()
        if not win or not hasattr(win, "data_store"):
            return
            
        grid = getattr(win, "_grid", None)
        if not grid:
            p = self.parent()
            while p:
                if hasattr(p, "current_view_mode") and hasattr(p, "table"):
                    grid = p
                    break
                p = p.parent()
                
        display_mode = getattr(grid, "current_view_mode", "classes") if grid else "classes"
        
        target_entity = None
        if grid and hasattr(grid, "table"):
            cur_r = grid.table.currentRow()
            if cur_r < 0 and hasattr(grid, "_current_selected_pos") and grid._current_selected_pos:
                cur_r = grid._current_selected_pos[0]
            if cur_r >= 0:
                if display_mode == "classes" and hasattr(grid, "class_list") and cur_r < len(grid.class_list):
                    target_entity = grid.class_list[cur_r]
                elif display_mode == "teachers" and hasattr(grid, "teacher_list") and cur_r < len(grid.teacher_list):
                    target_entity = grid.teacher_list[cur_r]
                    
        if not target_entity and hasattr(win, "_tree"):
            cur_item = win._tree.currentItem()
            if cur_item and cur_item.parent():
                target_entity = cur_item.data(0, Qt.UserRole)
                
        if not target_entity and grid:
            if display_mode == "classes" and hasattr(grid, "class_list") and grid.class_list:
                target_entity = grid.class_list[0]
            elif display_mode == "teachers" and hasattr(grid, "teacher_list") and grid.teacher_list:
                target_entity = grid.teacher_list[0]
                
        atamalar = win.data_store.get("atamalar", [])
        from auto_scheduler import matches_class, format_tr_name
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 4px; font-family: 'Segoe UI', system-ui; font-size: 12px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #EEF2FF; color: #4338CA; font-weight: bold; }
            QMenu::separator { height: 1px; background: #E2E8F0; margin: 4px 8px; }
        """)
        
        relevant_assignments = []
        if target_entity:
            if display_mode == "classes":
                relevant_assignments = [
                    a for a in atamalar
                    if matches_class(a.get("class", ""), target_entity) or
                       (a.get("is_combined") and any(matches_class(cc, target_entity) for cc in a.get("combined_classes", []))) or
                       ("+" in str(a.get("class", "")) and any(matches_class(p, target_entity) for p in str(a.get("class", "")).replace("&", "+").replace(",", "+").split("+") if p.strip()))
                ]
            else:
                relevant_assignments = [
                    a for a in atamalar
                    if format_tr_name(a.get("teacher", "")) == format_tr_name(target_entity)
                ]
                
        if not relevant_assignments:
            for d in win.data_store.get("dersler", []):
                s_name = d.get("ad", "").strip()
                if s_name:
                    relevant_assignments.append({"subject": s_name, "class": target_entity or "", "teacher": "", "duration": 2})
                    
        title_text = f"📚 {target_entity} — Eklenecek Dersi Seçin:" if target_entity else "📚 Eklenecek Dersi Seçin:"
        title_act = menu.addAction(title_text)
        title_act.setEnabled(False)
        menu.addSeparator()
        
        seen = set()
        for idx, a in enumerate(relevant_assignments):
            s_name = (a.get("subject") or a.get("ders") or "Ders").strip()
            t_name = format_tr_name(a.get("teacher") or a.get("ogretmen") or "")
            c_name = (a.get("class") or a.get("sinif") or target_entity or "").strip()
            key = (s_name, t_name, c_name)
            if key in seen:
                continue
            seen.add(key)
            
            tch_label = f" ({t_name})" if t_name else ""
            sub_menu = menu.addMenu(f"📖 {s_name}{tch_label}")
            sub_menu.setStyleSheet(menu.styleSheet())
            
            act_1 = sub_menu.addAction("1 Saat Ekle (Tekli Kart)")
            act_2 = sub_menu.addAction("2 Saat Ekle (2 Saatlik Blok Kart)")
            act_2_2 = sub_menu.addAction("2+2 Saat Ekle (2x Çiftli Deste)")
            
            def make_handler(sn, tn, cn, dur_choice):
                return lambda: self._add_custom_card(sn, tn, cn, dur_choice)
                
            act_1.triggered.connect(make_handler(s_name, t_name, c_name, 1))
            act_2.triggered.connect(make_handler(s_name, t_name, c_name, 2))
            act_2_2.triggered.connect(make_handler(s_name, t_name, c_name, 4))
            
        from PySide6.QtGui import QCursor
        menu.exec_(QCursor.pos())

    def _add_custom_card(self, s_name, t_name, c_name, duration):
        win = self.window()
        if not hasattr(win, "data_store") and hasattr(win, "parent") and hasattr(win.parent(), "data_store"):
            win = win.parent()
        data_store = getattr(win, "data_store", {})
        from dialogs.color_picker_dialog import resolve_subject_color
        color = resolve_subject_color(s_name, data_store)
        
        card_durs = [2, 2] if duration == 4 else [duration]
        manual_list = data_store.setdefault("manual_unplaced_cards", [])
        
        for cd in card_durs:
            cid = f"manual_{s_name}_{c_name}_{uuid.uuid4().hex[:6]}"
            manual_list.append({
                "id": cid,
                "subject_name": s_name,
                "color": color,
                "duration": cd,
                "teacher": t_name,
                "class_name": c_name
            })
            
        if win and hasattr(win, "_refresh_unplaced_lessons"):
            win._refresh_unplaced_lessons(target_entity=c_name)
        elif win and hasattr(win, "update_list"):
            self.load_unplaced([])
            
        if win and hasattr(win, "statusBar") and win.statusBar():
            win.statusBar().showMessage(f"'{s_name}' ders kartı yerleştirilmek üzere alt panele eklendi.", 4000)

    def eventFilter(self, watched, event):
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.DragEnter, QEvent.DragMove):
            if hasattr(event, "mimeData") and event.mimeData() and event.mimeData().hasFormat("application/x-lesson"):
                event.acceptProposedAction()
                return True
        elif event.type() == QEvent.Drop:
            if hasattr(event, "mimeData") and event.mimeData() and event.mimeData().hasFormat("application/x-lesson"):
                self.dropEvent(event)
                return True
        return super().eventFilter(watched, event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-lesson"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-lesson"):
            event.acceptProposedAction()
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
                    if hasattr(win, "_editor") and getattr(win, "_editor"):
                        win = win._editor
                    grid = getattr(win, "_grid", None)
                    if not grid:
                        p = self.parent()
                        while p:
                            if hasattr(p, "table") and hasattr(p.table, "_delete_lesson_at"):
                                grid = p
                                break
                            p = p.parent()
                    if grid and orig_r >= 0 and orig_c >= 0:
                        grid.table._delete_lesson_at(orig_r, orig_c)
                        event.acceptProposedAction()
                        return
            except Exception as e:
                print("Dock drop error:", e)
            event.acceptProposedAction()

    def load_unplaced(self, lessons_data, has_assignments=True, display_mode="classes", target_entity="", empty_slot_count=0):
        self.container.setUpdatesEnabled(False)
        try:
            # clear existing
            while self.container_layout.count():
                item = self.container_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.hide()
                    w.setParent(None)
                    w.deleteLater()
                    
            if not lessons_data:
                self.container_layout.setAlignment(Qt.AlignCenter)
                msg_widget = QWidget()
                msg_widget.setStyleSheet("background: transparent;")
                msg_widget.setAcceptDrops(True)
                msg_widget.installEventFilter(self)
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
                    if target_entity:
                        ent_desc = "sınıfına" if display_mode == "classes" else "öğretmenine"
                        text_lbl.setText(f"{target_entity} {ent_desc} henüz hiç ders atanmadı. Lütfen 'Ders Atama' bölümünden tanımlayın.")
                    else:
                        text_lbl.setText("Henüz hiç ders ataması yapılmadı. Lütfen 'Ders Atama' bölümünden ders tanımlayın.")
                    text_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    text_lbl.setStyleSheet("color: #B45309; background: transparent; border: none;")
                else:
                    icon_lbl.setPixmap(make_grid_action_icon("check_circle", 20).pixmap(20, 20))
                    if target_entity:
                        ent_desc = "sınıfının" if display_mode == "classes" else "öğretmeninin"
                        text_lbl.setText(f"{target_entity} {ent_desc} çizelgesi dolu — yerleştirilecek ders kalmadı.")
                    else:
                        text_lbl.setText("Çizelge dolu — yerleştirilecek ders kalmadı.")
                    text_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    text_lbl.setStyleSheet("color: #15803D; background: transparent; border: none;")
                    
                msg_layout.addWidget(icon_lbl)
                msg_layout.addWidget(text_lbl)
                
                btn_empty_add = QPushButton("  Daha Fazla Ders Ekle...")
                btn_empty_add.setIcon(make_grid_action_icon("add_plus", 14, "#0071E3"))
                btn_empty_add.setCursor(Qt.PointingHandCursor)
                btn_empty_add.setFixedHeight(28)
                btn_empty_add.setStyleSheet(f"""
                    QPushButton {{
                        background: #FFFFFF;
                        color: #0F172A;
                        font-family: {FONT_FAMILY};
                        font-size: 11px;
                        font-weight: 600;
                        padding: 0 14px;
                        border-radius: 6px;
                        border: 1px solid #CBD5E1;
                    }}
                    QPushButton:hover {{
                        background: #F1F5F9;
                        border-color: #0071E3;
                        color: #0071E3;
                    }}
                    QPushButton:pressed {{
                        background: #E2E8F0;
                    }}
                """)
                btn_empty_add.clicked.connect(self._on_add_more_clicked)
                msg_layout.addWidget(btn_empty_add)
                
                self.container_layout.addWidget(msg_widget)
                return

            self.container_layout.setAlignment(Qt.AlignLeft)
            
            from dialogs.color_picker_dialog import resolve_subject_color
            ds_context = getattr(self, "data_store", None)
            if not ds_context:
                win = self.window()
                ds_context = getattr(win, "data_store", None)
                if not ds_context and hasattr(win, "parent") and callable(win.parent):
                    ds_context = getattr(win.parent(), "data_store", None)

            for l in lessons_data:
                dur = l.get("duration", 1)
                count = l.get("count", 1)
                teacher = l.get("teacher", "")
                cls_name = l.get("class_name", "")
                s_name = l.get("subject_name", "")
                card_col = resolve_subject_color(s_name, ds_context) or l.get("color") or "#94A3B8"
                card = DraggableLessonCard(
                    l["id"], s_name, card_col,
                    duration=dur, count=count, teacher=teacher,
                    class_name=cls_name, display_mode=display_mode,
                    blocked_reason=l.get("blocked_reason", "")
                )
                if l.get("is_combined"): card.is_comb = True
                card.is_combined = l.get("is_combined", False)
                card.combined_classes = l.get("combined_classes", [])
                card.setAcceptDrops(True)
                card.installEventFilter(self)
                self.container_layout.addWidget(card)
                
            btn_inline_add = QPushButton("  Daha Fazla Ders Ekle...")
            btn_inline_add.setIcon(make_grid_action_icon("add_plus", 13, "#0071E3"))
            btn_inline_add.setCursor(Qt.PointingHandCursor)
            btn_inline_add.setFixedHeight(26)
            btn_inline_add.setStyleSheet(f"""
                QPushButton {{
                    background: #FFFFFF;
                    color: #475569;
                    font-family: {FONT_FAMILY};
                    font-size: 10.5px;
                    font-weight: 600;
                    padding: 0 10px;
                    border-radius: 5px;
                    border: 1px dashed #94A3B8;
                }}
                QPushButton:hover {{
                    background: #F8FAFC;
                    border-color: #0071E3;
                    color: #0071E3;
                }}
                QPushButton:pressed {{
                    background: #F1F5F9;
                }}
            """)
            btn_inline_add.clicked.connect(self._on_add_more_clicked)
            self.container_layout.addWidget(btn_inline_add)
        finally:
            self.container.setUpdatesEnabled(True)

    def update_list(self, data_store: dict = None, display_mode: str = None):
        if not data_store:
            return
            
        grid = self.parent()
        if hasattr(grid, "window") and hasattr(grid.window(), "_refresh_unplaced_lessons"):
            grid.window()._refresh_unplaced_lessons()
            return

        if display_mode is None:
            display_mode = getattr(grid, "current_view_mode", "classes") if grid else "classes"
            
        atamalar = data_store.get("atamalar", [])
        grid_placements = data_store.get("grid_placements", [])
        from auto_scheduler import matches_class, format_tr_name
        from dialogs.color_picker_dialog import resolve_subject_color
        
        placed_pool = []
        for p in grid_placements:
            dur = int(p.get("duration", 1))
            if dur > 0:
                placed_pool.append({
                    "subject": (p.get("subject_name") or p.get("subject") or "").strip(),
                    "class": (p.get("class_name") or p.get("class") or "").strip(),
                    "teacher": (p.get("teacher_name") or p.get("teacher") or "").strip(),
                    "remaining": dur
                })
                
        unplaced_cards = []
        for idx, a in enumerate(atamalar):
            s_name = (a.get("subject") or a.get("ders") or "Ders").strip()
            c_name = (a.get("class") or a.get("sinif") or "").strip()
            t_name = (a.get("teacher") or a.get("ogretmen") or "").strip()
            dur = int(a.get("duration", 1))
            type_str = str(a.get("type", "")).strip()
            color = resolve_subject_color(s_name, data_store)
            
            from auto_scheduler import parse_distribution_parts
            parts = parse_distribution_parts(type_str, dur)
                    
            s_fmt = format_tr_name(s_name)
            t_fmt = format_tr_name(t_name)
            
            for p_idx, block_dur in enumerate(parts):
                needed = block_dur
                for p_item in placed_pool:
                    if p_item["remaining"] <= 0:
                        continue
                    if format_tr_name(p_item["subject"]) != s_fmt:
                        continue
                    if t_name and p_item["teacher"] and format_tr_name(p_item["teacher"]) != t_fmt:
                        continue
                    p_c = p_item["class"]
                    if c_name and p_c:
                        if not (p_c == c_name or matches_class(p_c, c_name) or matches_class(c_name, p_c)):
                            continue
                            
                    deduct = min(needed, p_item["remaining"])
                    needed -= deduct
                    p_item["remaining"] -= deduct
                    if needed <= 0:
                        break
                        
                if needed > 0:
                    unplaced_cards.append({
                        "id": f"{idx}_{p_idx}",
                        "subject_name": s_name,
                        "color": color,
                        "duration": needed,
                        "teacher": t_name,
                        "class_name": c_name
                    })
        self.load_unplaced(unplaced_cards, has_assignments=bool(atamalar), display_mode=display_mode)


_CELL_COLOR_CACHE = {}

def clear_cell_color_cache():
    global _CELL_COLOR_CACHE
    _CELL_COLOR_CACHE.clear()

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
            
        # 1. Determine cell background color directly from data_store
        win = table.window() if table and hasattr(table, "window") else None
        data_store = getattr(win, "data_store", None)
        
        cell_color = None
        color_key = subject_name or clean_str
        if color_key:
            if color_key in _CELL_COLOR_CACHE:
                cell_color = _CELL_COLOR_CACHE[color_key]
            else:
                from dialogs.color_picker_dialog import resolve_subject_color
                resolved_hex = resolve_subject_color(color_key, data_store)
                c = QColor(resolved_hex)
                if not c.isValid():
                    c = QColor("#2563EB")
                _CELL_COLOR_CACHE[color_key] = c
                cell_color = c
        elif info and info.get("color"):
            c = QColor(info["color"])
            if c.isValid():
                cell_color = c
        elif bg_brush and isinstance(bg_brush, (QBrush, QColor)):
            c = bg_brush.color() if isinstance(bg_brush, QBrush) else bg_brush
            if c.isValid() and c.alpha() > 0 and c.name().upper() not in ("#C0C0C0", "#B4B4B8", "#D0D0D0", "#D8D8D8", "#FFFFFF"):
                cell_color = c
                
        is_filled = bool(clean_str or (info and info.get("subject_name")))
        is_closed_slot = False
        if not is_filled and grid:
            pos = grid.resolve_cell(row, col)
            day_idx = pos.get("day", -1)
            period_idx = pos.get("period", -1)
            c_name = pos.get("class_name", "")
            t_name = pos.get("teacher_name", "")
            display_mode = getattr(grid, "current_view_mode", "classes")
            if day_idx >= 0 and period_idx >= 0 and data_store:
                if display_mode == "teachers" and t_name:
                    for t in data_store.get("ogretmenler", []) or []:
                        if (t.get("ad") or t.get("name") or "").strip() == t_name:
                            toff = t.get("timeoff", [])
                            if toff and day_idx < len(toff) and period_idx < len(toff[day_idx]):
                                is_closed_slot = (toff[day_idx][period_idx] == 0)
                            break
                    if not is_closed_slot:
                        kisit = data_store.get("kisitlamalar", {}).get(t_name, {})
                        if f"{day_idx},{period_idx}" in kisit:
                            is_closed_slot = (kisit[f"{day_idx},{period_idx}"] in (0, False))
                elif c_name:
                    for c in data_store.get("siniflar", []) or []:
                        if (c.get("ad") or c.get("name") or "").strip() == c_name:
                            toff = c.get("timeoff", [])
                            if toff and day_idx < len(toff) and period_idx < len(toff[day_idx]):
                                is_closed_slot = (toff[day_idx][period_idx] == 0)
                            break
                    if not is_closed_slot:
                        kisit = data_store.get("kisitlamalar", {}).get(c_name, {})
                        if f"{day_idx},{period_idx}" in kisit:
                            is_closed_slot = (kisit[f"{day_idx},{period_idx}"] in (0, False))

        if not cell_color or not cell_color.isValid():
            cell_color = QColor("#E2E8F0") if is_closed_slot else (QColor("#F8FAFC") if not is_filled else QColor("#FFFFFF"))
                
        # 2. Fill background (Exact crisp color)
        painter.fillRect(rect, cell_color)
        
        # 3. Flat hairline grid borders (right and bottom lines only for flat 1px grid)
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.drawLine(rect.right(), rect.top(), rect.right(), rect.bottom())
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        
        # 3.1 Prominent day separator line (flat, crisp)
        periods = grid._periods if (grid and hasattr(grid, "_periods")) else 8
        if periods > 0 and (col + 1) % periods == 0:
            painter.setPen(QPen(QColor("#64748B"), 1.5))
            painter.drawLine(rect.right(), rect.top(), rect.right(), rect.bottom())

        # 3.2 Closed slot X icon
        if is_closed_slot and not is_filled:
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(rect, Qt.AlignCenter, "✕")
        
        # 4. Selection border
        if option.state & QStyle.State_Selected:
            painter.setPen(QPen(QColor("#0071E3"), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -2, -2))
            
        # 5. Draw text - High-contrast readable centered text
        if clean_str or (info and info.get("subject_name")):
            lum = (0.299 * cell_color.red() + 0.587 * cell_color.green() + 0.114 * cell_color.blue())
            text_color = QColor("#FFFFFF") if lum < 140 else QColor("#0F172A")
            painter.setPen(text_color)
            
            s_name = info.get("subject_name", "") if info else ""
            if not s_name:
                s_name = clean_str
                
            display_mode = getattr(grid, "current_view_mode", "classes")
            
            if display_mode == "teachers":
                # In teacher view, display ONLY the CLASS NAME (e.g. 9A, 10B, 11A)
                c_name = (info.get("class_name") or "") if info else ""
                if not c_name and clean_str and clean_str != s_name:
                    c_name = clean_str
                if "," in c_name or "&" in c_name or "+" in c_name:
                    main_text = "+".join([c.strip().split("(")[0].strip() for c in c_name.replace("&", ",").replace("+", ",").split(",") if c.strip()])
                else:
                    main_text = c_name.strip().split("(")[0].strip() if c_name else clean_str
                
                if rect.width() < 35 and len(main_text) > 4:
                    main_text = main_text[:4]
            else:
                # In class view, display ONLY the SUBJECT (e.g. MATE 9, FİZ 9, MAT 10)
                limit = 6
                if rect.width() < 45: limit = 4
                if rect.width() < 32: limit = 3
                main_text = get_subject_abbr(s_name, max_len=limit) if s_name else clean_str
                
            # Dynamic font sizing for crystal clear readability (Scaled down 25%)
            font_size = 8 if len(main_text) <= 6 else (7.5 if len(main_text) <= 10 else 6.5)
            if rect.width() < 35: font_size = max(6, font_size - 1)
            painter.setFont(QFont("Segoe UI", int(font_size), QFont.Bold))
            painter.drawText(rect, Qt.AlignCenter, main_text)
                
            # Lock icon: prominent top-left corner badge
            if is_locked:
                lock_bg = QRectF(rect.left() + 0.5, rect.top() + 0.5, 12, 12)
                painter.setBrush(QBrush(QColor("#FEF3C7")))  # Soft amber background
                painter.setPen(QPen(QColor("#D97706"), 1))   # Amber border
                painter.drawRoundedRect(lock_bg, 2.5, 2.5)
                
                painter.setFont(QFont("Segoe UI", 6.5, QFont.Bold))
                painter.setPen(QColor("#78350F"))
                painter.drawText(lock_bg, Qt.AlignCenter, "🔒")
                
            # Combined lesson paperclip badge: prominent top-right corner badge (📎 ataç)
            c_name_check = str((info.get("class_name") or info.get("class") or "")) if info else ""
            is_comb = bool(info and (info.get("is_combined") or ("+" in c_name_check) or ("," in c_name_check) or ("&" in c_name_check)))
            if not is_comb and info and data_store:
                s_chk = info.get("subject_name") or info.get("subject") or clean_str
                c_chk = c_name_check
                if s_chk:
                    for a in data_store.get("atamalar", []):
                        if (a.get("is_combined") or ("+" in str(a.get("class", "")))) and a.get("subject") == s_chk:
                            if not c_chk or any(matches_class(cc, c_chk) for cc in a.get("combined_classes", [])) or matches_class(a.get("class", ""), c_chk):
                                is_comb = True
                                break
                                
            if is_comb:
                comb_bg = QRectF(rect.right() - 17, rect.top() + 1, 16, 16)
                painter.setBrush(QBrush(QColor("#DBEAFE")))  # Soft light blue background
                painter.setPen(QPen(QColor("#2563EB"), 1.2)) # Crisp blue border
                painter.drawRoundedRect(comb_bg, 3, 3)
                
                painter.setFont(QFont("Segoe UI Emoji", 9, QFont.Bold))
                painter.setPen(QColor("#1E40AF"))
                painter.drawText(comb_bg, Qt.AlignCenter, "📎")
            
        painter.restore()



# Başlık şeridinde bir sütuna birden çok satırın durumu düşerse, EN GÜÇLÜ olan
# gösterilir: bir yerde kapalıysa "kapalı", çakışıyorsa "çakışma" görünür.
_PLACEMENT_RANK = {"NONE": 0, "SELECTED": 1, "GREEN": 2, "BLUE": 3, "RED": 4, "GREY": 5}


def _placement_rank(visual):
    return _PLACEMENT_RANK.get(visual, 0)


class DropTableWidget(QTableWidget):
    lesson_dropped = Signal(int, int, dict) # row, col, lesson_info
    cell_right_clicked = Signal(int, int)  # row, col for context menu
    
    def __init__(self, rows, cols, parent=None):
        super().__init__(rows, cols, parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.asc_header = AsCTimetableHeader(8, DAYS[:5], self)
        self.setHorizontalHeader(self.asc_header)
        self.horizontalScrollBar().valueChanged.connect(lambda: self.asc_header.viewport().update())
        self.setItemDelegate(TimetableCellDelegate(self))
        self._drag_preview_info = None
        # Sürükleme sırasındaki yerleşim analizi (bkz. begin_placement_analysis)
        self._placement_map = {}        # (satır, sütun) -> PlacementAnalysisResult
        self._placement_session = 0     # eski analizin yeniyi ezmemesi için
        self._placement_lesson = None

    # ── Sürükleme sırasında canlı yerleşim analizi ─────────────────────────
    #
    # Kart havadayken her hedef hücre için "bu ders buraya konabilir mi?" sorusu
    # placement_engine'e sorulur ve cevap renge çevrilir:
    #     yeşil  konabilir      mavi  konur ama tercih edilmez
    #     kırmızı çakışma var   gri   kapalı, asla konamaz
    # Analiz saftır: çizelgeye dokunmaz, kayıt yapmaz, senkron tetiklemez.
    PLACEMENT_COLORS = {
        "GREEN": (QColor(34, 197, 94, 90), QColor(21, 128, 61)),
        "BLUE": (QColor(59, 130, 246, 85), QColor(29, 78, 216)),
        "RED": (QColor(239, 68, 68, 95), QColor(185, 28, 28)),
        "GREY": (QColor(100, 116, 139, 70), QColor(71, 85, 105)),
        "SELECTED": (QColor(250, 204, 21, 80), QColor(161, 98, 7)),
    }

    def _analysis_host(self):
        """data_store'u taşıyan en yakın nesne (pencere ya da üst widget).

        Gerçek uygulamada bu MainWindow'dur; ızgara tek başına (test/önizleme)
        kullanıldığında pencere olmayabilir, o yüzden ebeveyn zinciri de taranır.
        """
        candidates = [self.window()]
        node = self.parent()
        while node is not None and len(candidates) < 8:
            candidates.append(node)
            node = node.parent() if hasattr(node, "parent") else None
        for obj in candidates:
            if obj is not None and getattr(obj, "data_store", None) is not None:
                return obj
        return None

    def begin_placement_analysis(self, lesson_info: dict):
        """Kart kaldırıldı: bütün aday konumları BİR KEZ değerlendir.

        İndeksler burada kurulur; fare hareket ettikçe yeniden hesap yapılmaz,
        hazır sonuç okunur. Bu yüzden sürükleme büyük çizelgede de akıcı kalır.
        """
        self._placement_session += 1
        session = self._placement_session
        self._placement_map = {}
        self._placement_lesson = lesson_info or {}
        grid = self.parent()
        if not grid or not lesson_info:
            return

        win = self._analysis_host()
        data_store = getattr(win, "data_store", None)
        if data_store is None:
            return
        try:
            import placement_engine as pe
            snapshot = pe.TimetableSnapshot(
                data_store,
                institution_slug=getattr(win, "institution_slug", None),
                exclude_block_id=lesson_info.get("block_id"))
        except Exception as exc:
            print(f"[Grid] yerleşim analizi kurulamadı: {exc}")
            return

        duration = max(1, int(lesson_info.get("duration", 1) or 1))
        rows = grid.rows_for_lesson(lesson_info)
        cache = {}
        result_map = {}
        for row in rows:
            for col in range(self.columnCount()):
                pos = grid.resolve_cell(row, col)
                if pos["day"] < 0 or pos["period"] < 0:
                    continue
                lesson = dict(lesson_info)
                # Satır hangi sınıfa aitse aday o sınıfa kurulur: aynı ders
                # farklı satırda farklı sonuç verebilir (renk hücrenin değil,
                # ders+konum çiftinin özelliğidir).
                if pos["class_name"]:
                    lesson.setdefault("class_name", pos["class_name"])
                cand = pe.CandidatePlacement(lesson, pos["day"], pos["period"], duration)
                key = cand.key()
                res = cache.get(key)
                if res is None:
                    res = pe.analyze(snapshot, lesson, cand)
                    cache[key] = res
                result_map[(row, col)] = res

        # Fare bu arada başka bir karta geçtiyse eski sonucu yazma.
        if session != self._placement_session:
            return
        self._placement_map = result_map
        self.viewport().update()
        if hasattr(self, "asc_header"):
            self.asc_header.set_placement_states(self.header_placement_states())
            self.asc_header.viewport().update()

    def header_placement_states(self) -> dict:
        """Sütun başlığı şeridi için: {sütun: görsel durum}.

        Başlık "hücre dolu mu"yu değil, "SÜRÜKLENEN ders buradan başlayabilir mi"yi
        gösterir — aSc'deki davranış budur. Çok saatlik derslerde (ör. 2 saat)
        yerleşebilen bloğun kapsadığı tüm saatler yeşil gösterilir.
        """
        by_col = {}
        dur = max(1, int(self._placement_lesson.get("duration", 1) or 1)) if self._placement_lesson else 1
        grid = self.parent()
        periods = grid._periods if (grid and hasattr(grid, "_periods")) else 8
        if periods <= 0: periods = 8

        for (row, col), res in self._placement_map.items():
            if res.outside_class_hours:
                continue
            cur = by_col.get(col)
            if cur is None or _placement_rank(res.visual) > _placement_rank(cur):
                by_col[col] = res.visual

        # Çok saatlik kart sürüklendiğinde / üzerine gelindiğinde kapsanan tüm saatleri başlıkta yeşil yap
        if self._drag_preview_info:
            p_row = self._drag_preview_info.get("row", -1)
            p_col = self._drag_preview_info.get("col", -1)
            p_dur = max(1, int(self._drag_preview_info.get("duration", dur) or dur))
            if p_row >= 0 and p_col >= 0:
                res = self._placement_map.get((p_row, p_col))
                state = res.visual if res else "RED"
                day_start = (p_col // periods) * periods
                day_end = day_start + periods - 1
                for off in range(p_dur):
                    tgt_c = p_col + off
                    if tgt_c <= day_end and tgt_c < self.columnCount():
                        by_col[tgt_c] = state

        return by_col

    def end_placement_analysis(self):
        self._placement_session += 1
        if self._placement_map:
            self._placement_map = {}
            self._placement_lesson = None
            self.viewport().update()
            if hasattr(self, "asc_header"):
                self.asc_header.set_placement_states({})
                self.asc_header.viewport().update()

    def placement_at(self, row: int, col: int):
        return self._placement_map.get((row, col))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "asc_header"):
            self.asc_header.viewport().update()
        grid = self.parent()
        if grid and hasattr(grid, "adjust_columns_to_fit"):
            grid.adjust_columns_to_fit()

    def _preview_rect(self, preview):
        """Union rect covering a preview's full duration span, or None if off-grid."""
        if not preview:
            return None
        r = preview.get("row", -1)
        c = preview.get("col", -1)
        dur = max(1, int(preview.get("duration", 1)))
        if not (0 <= r < self.rowCount() and 0 <= c < self.columnCount()):
            return None
        grid = self.parent()
        periods = grid._periods if (grid and hasattr(grid, "_periods")) else 8
        if periods <= 0: periods = 8
        day_start_col = (c // periods) * periods
        day_end_col = day_start_col + periods - 1
        effective_end_col = min(c + dur - 1, day_end_col, self.columnCount() - 1)
        start_rect = self.visualRect(self.model().index(r, c))
        end_rect = self.visualRect(self.model().index(r, effective_end_col))
        return start_rect.united(end_rect)

    def _clear_preview_targeted(self):
        """Drop the preview and repaint only the (small) rect it occupied, instead of the
        whole viewport — called constantly while dragging, so this keeps drag-move handling
        cheap and the UI responsive instead of freezing/lagging."""
        if self._drag_preview_info is not None:
            old_rect = self._preview_rect(self._drag_preview_info)
            self._drag_preview_info = None
            if old_rect:
                self.viewport().update(old_rect.adjusted(-2, -2, 2, 2))
            else:
                self.viewport().update()

    def set_drag_preview(self, row: int, col: int, lesson_info: dict):
        if not lesson_info or row < 0 or col < 0 or row >= self.rowCount() or col >= self.columnCount():
            self._clear_preview_targeted()
            return

        dur = int(lesson_info.get("duration", 1))
        if dur <= 0: dur = 1

        grid = self.parent()
        periods = grid._periods if (grid and hasattr(grid, "_periods")) else 8
        if periods <= 0: periods = 8

        # Check day boundary: preview must not cross days
        day_start_col = (col // periods) * periods
        day_end_col = day_start_col + periods - 1
        if col + dur - 1 > day_end_col or col + dur > self.columnCount():
            self._clear_preview_targeted()
            return

        is_move = bool(lesson_info.get("is_move", False))
        orig_r = lesson_info.get("origin_row", -1)
        orig_c = lesson_info.get("origin_col", -1)

        # Is the target occupied? This used to bail out and hide the preview entirely,
        # back when dropping onto a taken slot was refused. Dropping there now swaps the
        # two lessons, so hiding the preview removed the feedback exactly where the user
        # needs it most — they could not see which cell they were about to land on.
        # The preview is still drawn; it is just flagged so it can be rendered as a swap.
        occupied = False
        for off in range(dur):
            chk_c = col + off
            if is_move and row == orig_r and (orig_c <= chk_c < orig_c + dur):
                continue  # moving from itself is allowed

            cell_item = self.item(row, chk_c)
            if cell_item and cell_item.text().strip():
                occupied = True
                break

            if grid and hasattr(grid, "_placed_lessons") and (row, chk_c) in grid._placed_lessons:
                pl = grid._placed_lessons[(row, chk_c)]
                if pl and (pl.get("subject_name") or pl.get("subject")):
                    occupied = True
                    break

        subj = lesson_info.get("subject_name") or lesson_info.get("subject") or ""

        # Cheap identity check FIRST — skip the (relatively) expensive color resolution
        # below entirely on every drag-move tick when the preview hasn't actually moved
        # to a new cell/subject. This is what used to make dragging feel laggy: a full
        # color lookup + dict rebuild on every single mouse-move event, dozens of times
        # a second, even while hovering the exact same cell.
        prev = self._drag_preview_info
        if (prev and prev.get("row") == row and prev.get("col") == col
                and prev.get("duration") == dur and prev.get("subject_name") == subj
                and prev.get("is_swap") == occupied):
            return

        teacher = lesson_info.get("teacher_name") or lesson_info.get("teacher") or ""
        cls = lesson_info.get("class_name") or lesson_info.get("class") or ""

        win = self.window()
        if not hasattr(win, "data_store") and hasattr(win, "parent") and hasattr(win.parent(), "data_store"):
            win = win.parent()
        data_store = getattr(win, "data_store", None)
        from dialogs.color_picker_dialog import resolve_subject_color
        color = resolve_subject_color(subj, data_store) if subj else (lesson_info.get("color") or "#2563EB")

        new_preview = {
            "row": row,
            "col": col,
            "duration": dur,
            "subject_name": subj,
            "teacher_name": teacher,
            "class_name": cls,
            "color": color,
            "is_combined": bool(lesson_info.get("is_combined") or ("+" in cls or "," in cls or "&" in cls)),
            "combined_classes": lesson_info.get("combined_classes", []),
            # Target already holds a lesson: the drop will exchange the two, so the
            # preview is drawn differently to say so before the user lets go.
            "is_swap": occupied,
        }

        old_rect = self._preview_rect(prev)
        self._drag_preview_info = new_preview
        new_rect = self._preview_rect(new_preview)
        repaint_rect = old_rect.united(new_rect) if (old_rect and new_rect) else (new_rect or old_rect)
        if repaint_rect:
            self.viewport().update(repaint_rect.adjusted(-2, -2, 2, 2))
        else:
            self.viewport().update()

        if hasattr(self, "asc_header"):
            self.asc_header.set_placement_states(self.header_placement_states())

    def clear_drag_preview(self):
        self._clear_preview_targeted()
        if hasattr(self, "asc_header"):
            self.asc_header.set_placement_states(self.header_placement_states())

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-lesson"):
            # Kart ızgaraya girdi: bütün aday konumlar BİR KEZ değerlendirilir,
            # fare hareket ettikçe yeniden hesap yapılmaz.
            try:
                payload = event.mimeData().data("application/x-lesson").data().decode()
                self.begin_placement_analysis(json.loads(payload))
            except Exception as exc:
                print(f"[Grid] yerleşim analizi başlatılamadı: {exc}")
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.clear_drag_preview()
        self.end_placement_analysis()
        event.accept()

    def _drop_anchor(self, pos, lesson_info=None):
        """İmlecin üzerinde durduğu hücre, dersin BİRİNCİ saatidir.

        Kural tek cümle: fareyi hangi saatin üzerine getirdiyseniz ders ORADAN
        başlar. 2 saatlik bir dersi 1. saatin üzerine getirirseniz 1-2. saatleri,
        2. saatin üzerine getirirseniz 2-3. saatleri kapsar. Önizleme de bırakma da
        aynı hücreyi kullanır.

        Eskiden kartın neresinden tutulduğu (grab_dx/dy) imleçten çıkarılıyordu:
        kartı ortasından tutmak 2 saatlik bir derste tam bir saatlik kayma demekti
        ve kullanıcı 2. saatin üzerindeyken ders 1. saate yapışıyordu. Tutma noktası
        artık kartın İLK hücresinin ortasına ayarlandığı için hayalet görüntü de
        imlecin sağına doğru uzuyor; görünen ile olan aynı.

        Sonuç viewport içine KIRPILIR: dışarı taşan bir noktada rowAt()/columnAt()
        -1 döner, dragMoveEvent bunu "burada hücre yok" diye okur ve imleçte yasak
        işareti çıkardı.
        """
        bounds = self.viewport().rect()
        x = min(max(pos.x(), bounds.left() + 2), bounds.right() - 2)
        y = min(max(pos.y(), bounds.top() + 2), bounds.bottom() - 2)
        return QPoint(x, y)

    def _cell_at(self, point):
        """(row, col) under a viewport point, or (-1, -1).

        itemAt() returns None for a cell with no QTableWidgetItem, and for the
        non-anchor half of a merged (spanned) block, so rowAt/columnAt are the
        reliable fallback.
        """
        item = self.itemAt(point)
        if item is not None:
            return item.row(), item.column()
        return self.rowAt(point.y()), self.columnAt(point.x())

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-lesson"):
            try:
                data = event.mimeData().data("application/x-lesson").data().decode()
                lesson_info = json.loads(data)
            except Exception:
                lesson_info = {}

            r, c = self._cell_at(self._drop_anchor(event.pos(), lesson_info))
            if r < 0 or c < 0:
                # Last resort: the raw cursor position always sits inside the grid
                # while dragging over it, so this keeps the drop enabled instead of
                # showing a forbidden cursor.
                r, c = self._cell_at(event.pos())

            if r >= 0 and c >= 0:
                self.set_drag_preview(r, c, lesson_info)
                event.setDropAction(Qt.MoveAction)
                event.accept()
            else:
                self.clear_drag_preview()
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        self.clear_drag_preview()
        self.end_placement_analysis()
        if event.mimeData().hasFormat("application/x-lesson"):
            try:
                data = event.mimeData().data("application/x-lesson").data().decode()
                lesson_info = json.loads(data)
            except Exception:
                lesson_info = {}
                
            row, col = self._cell_at(self._drop_anchor(event.pos(), lesson_info))
            if row < 0 or col < 0:
                row, col = self._cell_at(event.pos())

            if row >= 0 and col >= 0 and lesson_info:
                teacher = lesson_info.get("teacher", "")
                dur = int(lesson_info.get("duration", 1))
                win = self.window()
                periods = getattr(self.parent(), "_periods", 8)
                if periods <= 0: periods = 8
                day_idx = col // periods
                period_idx = col % periods
                
                if teacher and hasattr(win, "data_store"):
                    for t in win.data_store.get("ogretmenler", []):
                        t_ad = t.get("ad", "")
                        if t_ad and (t_ad == teacher or t_ad.upper() == teacher.upper()):
                            toff = t.get("timeoff", [])
                            if toff and hasattr(win, "statusBar") and win.statusBar():
                                for off in range(dur):
                                    chk_p = period_idx + off
                                    if day_idx < len(toff) and chk_p < len(toff[day_idx]) and toff[day_idx][chk_p] == 0:
                                        win.statusBar().showMessage(f"ℹ️ {t_ad} öğretmeninin bu saatte kısıtlaması bulunuyor.", 3000)
                                        break
                            break
                
                self.lesson_dropped.emit(row, col, lesson_info)
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def _paint_placement_states(self):
        """Aday konumları boya: yeşil / mavi / kırmızı / gri.

        Renk burada HESAPLANMAZ; placement_engine'in verdiği duruma karşılık gelen
        görsel jetona bakılır. Arayüzde iş kuralı yoktur.
        """
        if not self._placement_map:
            return
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing, False)
        view = self.viewport().rect()
        drawn = 0
        for (row, col), res in self._placement_map.items():
            # Sınıfın ders saati dışındaki hücreler boyanmaz: zaten okul günü
            # değiller ve boyandıklarında ekranın yarısı griye dönüp asıl bilgiyi
            # bastırıyorlardı.
            if res.outside_class_hours:
                continue
            visual = res.visual
            colors = self.PLACEMENT_COLORS.get(visual)
            if not colors:
                continue
            rect = self.visualRect(self.model().index(row, col))
            if not rect.isValid() or not view.intersects(rect):
                continue
            fill, edge = colors
            painter.fillRect(rect.adjusted(1, 1, -1, -1), fill)
            painter.setPen(QPen(edge, 1))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            drawn += 1
            if drawn > 4000:      # emniyet: aşırı büyük ızgarada boyamayı sınırla
                break

        # Aktif önizleme bloğunun (ör. 2 saat) tüm hücrelerini aynı durumla boya
        preview = self._drag_preview_info
        if preview and isinstance(preview, dict):
            p_r = preview.get("row", -1)
            p_c = preview.get("col", -1)
            p_d = max(1, int(preview.get("duration", 1)))
            if p_r >= 0 and p_c >= 0:
                res = self._placement_map.get((p_r, p_c))
                if res and not res.outside_class_hours:
                    colors = self.PLACEMENT_COLORS.get(res.visual)
                    if colors:
                        fill, edge = colors
                        grid = self.parent()
                        periods = grid._periods if (grid and hasattr(grid, "_periods")) else 8
                        if periods <= 0: periods = 8
                        day_end = (p_c // periods) * periods + periods - 1
                        for off in range(p_d):
                            cur_c = p_c + off
                            if cur_c <= day_end and cur_c < self.columnCount():
                                r_cell = self.visualRect(self.model().index(p_r, cur_c))
                                if r_cell.isValid() and view.intersects(r_cell):
                                    painter.fillRect(r_cell.adjusted(1, 1, -1, -1), fill)
                                    painter.setPen(QPen(edge, 1.5))
                                    painter.drawRect(r_cell.adjusted(0, 0, -1, -1))
        painter.end()

    def paintEvent(self, event):
        super().paintEvent(event)

        # Sürükleme sırasında yerleşim analizi katmanı (hayaletin ALTINDA durur)
        try:
            self._paint_placement_states()
        except Exception as exc:
            print(f"[Grid] yerleşim boyama notu: {exc}")

        # Draw drag preview ghost overlay if active
        preview = self._drag_preview_info
        if preview and isinstance(preview, dict):
            dur = max(1, int(preview.get("duration", 1)))
            union_rect = self._preview_rect(preview)
            grid = self.parent()

            if union_rect is not None:
                if not union_rect.isEmpty():
                    painter = QPainter(self.viewport())
                    painter.setRenderHint(QPainter.Antialiasing, True)
                    
                    is_swap = bool(preview.get("is_swap"))
                    base_color = QColor(preview.get("color") or "#3B82F6")
                    res = self._placement_map.get((preview.get("row", -1), preview.get("col", -1)))
                    visual = res.visual if res else ("RED" if is_swap else "GREEN")
                    if visual == "RED":
                        fill_color = QColor(239, 68, 68, 150)
                        pen = QPen(QColor(185, 28, 28), 2.5, Qt.SolidLine)
                    elif visual == "GREY":
                        fill_color = QColor(100, 116, 139, 140)
                        pen = QPen(QColor(71, 85, 105), 2.5, Qt.SolidLine)
                    elif is_swap:
                        fill_color = QColor(245, 158, 11, 150)
                        pen = QPen(QColor("#B45309"), 2.5, Qt.SolidLine)
                    elif visual == "GREEN":
                        fill_color = QColor(34, 197, 94, 150)
                        pen = QPen(QColor(21, 128, 61), 2.5, Qt.SolidLine)
                    else:
                        fill_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 145)
                        pen = QPen(QColor(base_color.darker(130)), 2, Qt.DashLine)
                    painter.setBrush(QBrush(fill_color))
                    painter.setPen(pen)
                    painter.drawRoundedRect(union_rect.adjusted(1, 1, -1, -1), 4, 4)

                    display_mode = getattr(grid, "current_view_mode", "classes") if grid else "classes"
                    s_name = preview.get("subject_name", "")
                    c_name = preview.get("class_name", "")
                    if display_mode == "teachers":
                        main_txt = c_name or s_name
                    else:
                        main_txt = get_subject_abbr(s_name) if s_name else c_name

                    if dur > 1:
                        main_txt += f" ({dur}h)"
                    if is_swap:
                        main_txt = f"⇄ {main_txt}"


                    painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    painter.setPen(QColor("#000000"))
                    painter.drawText(union_rect, Qt.AlignCenter, main_txt)
                    
                    painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def _lookup_placement_fallback(self, row, col):
        """Fallback used ONLY when the _placed_lessons cache has no entry for (row, col).

        This used to match a stored placement by day/period ALONE, with no check that it
        actually belongs to the class/teacher of the ROW that was clicked. Since every row
        (class or teacher) shares the exact same day/period columns, that meant clicking a
        cell that was genuinely empty FOR THIS ROW could still "find" a completely unrelated
        lesson belonging to some OTHER class/teacher that simply happened to be scheduled at
        the same time slot — picking it up as a phantom card that could then be dropped
        somewhere else, effectively duplicating a lesson out of thin air. Now it requires the
        placement's class (or teacher, in teacher view) to actually match this row.
        """
        grid = self.parent()
        win = self.window()
        if hasattr(win, "_editor") and getattr(win, "_editor"):
            win = win._editor
        elif not hasattr(win, "data_store") and hasattr(win, "parent") and hasattr(win.parent(), "data_store"):
            win = win.parent()
        if not hasattr(win, "data_store"):
            return None, row, col, 1

        periods = int(getattr(grid, "_periods", 8))
        if periods <= 0: periods = 8
        d_day = col // periods
        d_per = col % periods
        view_mode = getattr(grid, "current_view_mode", "classes")
        v_item = self.verticalHeaderItem(row)
        row_header_name = v_item.text().strip() if v_item else ""

        from auto_scheduler import matches_class, format_tr_name
        for p in win.data_store.get("grid_placements", []):
            p_d = int(p.get("day") if "day" in p else p.get("col", 0))
            p_p = int(p.get("period") if "period" in p else p.get("row", 0))
            p_dur = int(p.get("duration", 1))
            if p_d != d_day or not (p_p <= d_per < p_p + p_dur):
                continue
            p_cls = (p.get("class_name") or p.get("class") or "").strip()
            p_t = (p.get("teacher_name") or p.get("teacher") or "").strip()
            if row_header_name:
                if view_mode == "classes":
                    if not (matches_class(p_cls, row_header_name) or matches_class(row_header_name, p_cls)):
                        continue
                else:
                    if format_tr_name(p_t) != format_tr_name(row_header_name):
                        continue
            info = {
                "subject_name": p.get("subject_name") or p.get("subject", ""),
                "teacher_name": p.get("teacher_name") or p.get("teacher", ""),
                "class_name": p.get("class_name") or p.get("class", ""),
                "duration": p_dur,
                "color": p.get("color", "#2563EB"),
                "locked": bool(p.get("locked")),
                "is_combined": bool(p.get("is_combined")),
                "combined_classes": p.get("combined_classes", []),
                "origin_row": row,
                "origin_col": d_day * periods + p_p,
                "block_id": p.get("block_id")
            }
            return info, row, d_day * periods + p_p, p_dur
        return None, row, col, 1

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton and hasattr(self, 'drag_start_pos'):
            if (event.pos() - self.drag_start_pos).manhattanLength() < 5:
                row = self.rowAt(self.drag_start_pos.y())
                col = self.columnAt(self.drag_start_pos.x())
                if row >= 0 and col >= 0:
                    orig_r, orig_c, orig_dur, info = self._get_lesson_origin(row, col)
                    if not info:
                        info, orig_r, orig_c, orig_dur = self._lookup_placement_fallback(row, col)
                    if info:
                        s_name = info.get("subject_name", "")
                        c_name = info.get("class_name", "")
                        is_comb = bool(info.get("is_combined") or ("+" in c_name or "," in c_name or "&" in c_name))
                        combined_classes = list(info.get("combined_classes", []))
                        if is_comb and not combined_classes:
                            combined_classes = [c.strip().split("(")[0].strip() for c in c_name.replace("&", "+").replace(",", "+").split("+") if c.strip()]
                        
                        data = dict(info)
                        data["is_move"] = True
                        data["origin_row"] = orig_r
                        data["origin_col"] = orig_c
                        data["teacher"] = info.get("teacher_name", "")
                        # Preserve the lesson's ACTUAL lock state instead of forcing it to
                        # True — this used to silently lock every lesson ever picked up this
                        # way, even ones that were never locked, causing an unwanted "locked
                        # lesson" confirmation dialog the next time anyone tried to remove it.
                        data["locked"] = bool(info.get("locked", False))
                        data["is_combined"] = is_comb
                        data["combined_classes"] = combined_classes
                        if is_comb and combined_classes:
                            data["class_name"] = " + ".join(combined_classes)

                        # Always size the grabbed ghost pixmap to the lesson's FULL duration
                        # span (not just the single cell that was clicked/found), so a 2-hour
                        # block always drags as a 2-wide rectangle, never a 1-cell square.
                        rect = self._preview_rect({"row": orig_r, "col": orig_c, "duration": orig_dur})
                        if rect is None:
                            rect = self.visualRect(self.model().index(orig_r, orig_c))
                        pixmap = self.viewport().grab(rect)

                        win = self.window()
                        # Hand over where inside the block it was grabbed, so the ghost
                        # sits exactly over the cells it came from and can be dropped
                        # straight back onto them.
                        StickyGhostWidget(pixmap, data, win,
                                          grab_offset=self.drag_start_pos - rect.topLeft())

    def mouseMoveEvent(self, event):
        # 1. Drag & Drop start when Left button is pressed
        if (event.buttons() & Qt.LeftButton) and hasattr(self, 'drag_start_pos'):
            if (event.pos() - self.drag_start_pos).manhattanLength() >= 5:
                row = self.rowAt(self.drag_start_pos.y())
                col = self.columnAt(self.drag_start_pos.x())
                if row >= 0 and col >= 0:
                    orig_r, orig_c, orig_dur, info = self._get_lesson_origin(row, col)
                    if not info:
                        info, orig_r, orig_c, orig_dur = self._lookup_placement_fallback(row, col)
                    if info:
                        s_name = info.get("subject_name", "")
                        c_name = info.get("class_name", "")
                        is_comb = bool(info.get("is_combined") or ("+" in c_name or "," in c_name or "&" in c_name))
                        combined_classes = list(info.get("combined_classes", [])) if is_comb else []
                        if is_comb and not combined_classes:
                            combined_classes = [c.strip().split("(")[0].strip() for c in c_name.replace("&", "+").replace(",", "+").split("+") if c.strip()]

                        # Kilitli ders taşıma uyarısı
                        was_locked = bool(info.get("locked"))
                        if was_locked:
                            from auto_scheduler import matches_class
                            ret = QMessageBox.warning(
                                self, "Kilitli Ders Uyarısı",
                                f"🔒 '{s_name}' ({c_name}) dersi kilitlenmiştir.\n\n"
                                "Kilitli bir dersi taşımak istiyor musunuz?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                            )
                            if ret != QMessageBox.Yes:
                                return
                            
                            info["locked"] = False
                            grid = self.parent()
                            # NOTE: both scans below must check the ROW (class/teacher) too, not
                            # just subject+column proximity — otherwise unlocking this lesson
                            # could silently unlock an unrelated lesson belonging to a DIFFERENT
                            # class/teacher that just happened to share the same subject name and
                            # sit in a nearby/same-day column. Same for the `not is_comb or ...`
                            # shortcut below: for a non-combined lesson that unconditionally
                            # matched ANY class at that day/period, not just this one.
                            if hasattr(grid, "_placed_lessons"):
                                for (r_k, c_k), pl in list(grid._placed_lessons.items()):
                                    if r_k == orig_r and abs(c_k - orig_c) < orig_dur and (pl.get("subject_name") == s_name):
                                        if (is_comb and any(matches_class(pl.get("class_name", ""), tc) for tc in combined_classes)) or pl.get("class_name") == c_name:
                                            pl["locked"] = False
                            win = self.window()
                            if hasattr(win, "data_store"):
                                periods = int(getattr(grid, "_periods", 8))
                                if periods <= 0: periods = 8
                                d_day = orig_c // periods
                                d_per = orig_c % periods
                                for p in win.data_store.get("grid_placements", []):
                                    p_d = int(p.get("day") if "day" in p else p.get("col", 0))
                                    p_p = int(p.get("period") if "period" in p else p.get("row", 0))
                                    p_c = (p.get("class_name") or p.get("class") or "").strip()
                                    if p_d == d_day and (d_per <= p_p < d_per + orig_dur):
                                        if (is_comb and any(matches_class(p_c, tc) for tc in combined_classes)) or p_c == c_name:
                                            p["locked"] = False
                            self.viewport().update()

                        from PySide6.QtGui import QDrag
                        drag = QDrag(self)
                        mime = QMimeData()
                        
                        data = dict(info)
                        data["is_move"] = True
                        data["origin_row"] = orig_r
                        data["origin_col"] = orig_c
                        data["teacher"] = info.get("teacher_name", "")
                        # info["locked"] was just explicitly cleared above (after confirming
                        # the unlock) if this lesson was locked — forcing True back here
                        # undid that confirmation and silently re-locked (or, for a never-
                        # locked lesson, newly locked) it at the destination every single
                        # time anything was moved, which is why removing a lesson later kept
                        # popping an unexpected "locked lesson" confirmation dialog.
                        data["locked"] = bool(info.get("locked", False))
                        data["is_combined"] = is_comb
                        data["combined_classes"] = combined_classes
                        if is_comb and combined_classes:
                            data["class_name"] = " + ".join(combined_classes)

                        # Always size the dragged pixmap to the lesson's FULL duration span.
                        rect = self._preview_rect({"row": orig_r, "col": orig_c, "duration": orig_dur})
                        if rect is None:
                            rect = self.visualRect(self.model().index(orig_r, orig_c))
                        pixmap = self.viewport().grab(rect)

                        # Tutma noktasi, blogun ILK hucresinin ortasi. Boylece hayalet
                        # goruntu imlecin sagina dogru uzar ve "imlecin altindaki hucre
                        # dersin 1. saatidir" kurali gorunusle birebir ortusur. Kartin
                        # neresinden tuttugunuz artik bir sey degistirmiyor: eskiden
                        # kartin sag yarisindan tutmak 2 saatlik dersi bir saat ileri
                        # kaydiriyordu.
                        cell_w = max(1, rect.width() // max(1, int(orig_dur or 1)))
                        hotspot = QPoint(cell_w // 2, rect.height() // 2)
                        data["grab_dx"] = 0
                        data["grab_dy"] = 0

                        mime.setData("application/x-lesson", QByteArray(json.dumps(data).encode()))
                        drag.setMimeData(mime)
                        drag.setPixmap(pixmap)
                        drag.setHotSpot(hotspot)

                        drag.exec_(Qt.MoveAction)
                        return

        # 2. Pure Hover
        super().mouseMoveEvent(event)
        item = self.itemAt(event.pos())
        grid = self.parent() if self.parent() else None
        
        info = None
        if item:
            r = item.row()
            c = item.column()
            orig_r, orig_c, orig_dur, info = self._get_lesson_origin(r, c) if hasattr(self, "_get_lesson_origin") else (r, c, 1, None)
            if not info and grid and hasattr(grid, "_placed_lessons"):
                info = grid._placed_lessons.get((r, c))
                
        if info and (info.get("subject_name") or info.get("subject")):
            self.viewport().setCursor(Qt.PointingHandCursor)
            if grid and hasattr(grid, "update_info_panel"):
                grid.update_info_panel(info)
        else:
            self.viewport().setCursor(Qt.ArrowCursor)

    def _get_lesson_origin(self, row, col):
        """Finds the true starting cell (origin_row, origin_col) and info of a placed lesson at (row, col)."""
        grid = self.parent()
        if hasattr(grid, "_placed_lessons") and (row, col) in grid._placed_lessons:
            info = grid._placed_lessons[(row, col)]
            orig_r = info.get("origin_row", row)
            orig_c = info.get("origin_col", col)
            dur = info.get("duration", 1)
            return orig_r, orig_c, dur, info
            
        c_span = self.columnSpan(row, col)
        r_span = self.rowSpan(row, col)
        return row, col, max(c_span, r_span, 1), None

    def _delete_lesson_at(self, row, col):
        orig_r, orig_c, orig_dur, info = self._get_lesson_origin(row, col)
        grid = self.parent()
        periods = int(getattr(grid, "_periods", 8))
        if periods <= 0: periods = 8
        del_day = int(orig_c) // periods
        del_period = int(orig_c) % periods
        
        view_mode = getattr(grid, "current_view_mode", "classes")
        v_item = self.verticalHeaderItem(orig_r)
        row_header_name = v_item.text().strip() if v_item else ""
        
        win = self.window()
        if hasattr(win, "_editor") and getattr(win, "_editor"):
            win = win._editor
        elif not hasattr(win, "data_store") and hasattr(win, "parent") and hasattr(win.parent(), "data_store"):
            win = win.parent()
            
        # 1. Accurately find ALL placements in data_store for this cell's lesson block
        from auto_scheduler import matches_class, format_tr_name, normalize_clean
        matching_block_placements = []
        
        if hasattr(win, "data_store") and "grid_placements" in win.data_store:
            # Find primary placement matching slot
            primary_p = None
            for p in win.data_store.get("grid_placements", []):
                p_day = int(p.get("day") if "day" in p else p.get("col", 0))
                p_period = int(p.get("period") if "period" in p else p.get("row", 0))
                p_dur = int(p.get("duration", 1))
                if p_day == del_day and (p_period <= del_period < p_period + p_dur):
                    p_cls = (p.get("class_name") or p.get("class") or "").strip()
                    p_t = (p.get("teacher_name") or p.get("teacher") or "").strip()
                    if view_mode == "classes" and (matches_class(p_cls, row_header_name) or row_header_name in p_cls or not row_header_name):
                        primary_p = p
                        break
                    elif view_mode == "teachers" and (format_tr_name(p_t) == format_tr_name(row_header_name) or p_t == row_header_name or not row_header_name):
                        primary_p = p
                        break
                        
            if primary_p:
                p_bid = primary_p.get("block_id")
                p_sub = primary_p.get("subject_name") or primary_p.get("subject") or ""
                p_cls = primary_p.get("class_name") or primary_p.get("class") or ""
                p_tea = primary_p.get("teacher_name") or primary_p.get("teacher") or ""
                p_per = int(primary_p.get("period") if "period" in primary_p else primary_p.get("row", del_period))
                
                if p_bid:
                    matching_block_placements = [
                        p for p in win.data_store.get("grid_placements", [])
                        if p.get("block_id") == p_bid
                    ]
                else:
                    matching_block_placements = [
                        p for p in win.data_store.get("grid_placements", [])
                        if (int(p.get("day") if "day" in p else p.get("col", 0)) == del_day and
                            abs(int(p.get("period") if "period" in p else p.get("row", 0)) - p_per) <= 2 and
                            (p.get("subject_name") or p.get("subject")) == p_sub and
                            (matches_class(p.get("class_name") or p.get("class", ""), p_cls) or
                             format_tr_name(p.get("teacher_name") or p.get("teacher", "")) == format_tr_name(p_tea)))
                    ]
                    
        # Extract metadata from primary placement or info
        if matching_block_placements:
            ref_p = matching_block_placements[0]
            c_name = ref_p.get("class_name") or ref_p.get("class") or row_header_name
            t_name = ref_p.get("teacher_name") or ref_p.get("teacher") or ""
            s_name = ref_p.get("subject_name") or ref_p.get("subject") or ""
            is_locked = bool(ref_p.get("locked"))
            is_comb = bool(ref_p.get("is_combined") or ("+" in c_name or "," in c_name or "&" in c_name))
            is_filler = bool(ref_p.get("is_filler"))
            removed_color = ref_p.get("color") or ""
            removed_combined_classes = ref_p.get("combined_classes") or []
        else:
            c_name = (info.get("class_name") or info.get("class") or row_header_name) if info else row_header_name
            t_name = (info.get("teacher_name") or info.get("teacher") or "") if info else ""
            s_name = (info.get("subject_name") or info.get("subject") or "") if info else ""
            is_locked = bool(info and info.get("locked"))
            is_comb = bool(info and (info.get("is_combined") or ("+" in c_name or "," in c_name or "&" in c_name)))
            is_filler = bool(info and info.get("is_filler"))
            removed_color = (info.get("color") if info else "") or ""
            removed_combined_classes = (info.get("combined_classes") if info else []) or []

        # Lock Check
        if is_locked and not getattr(self, "_test_mode", False) and not getattr(self.window(), "_test_mode", False):
            ret = QMessageBox.warning(
                self, "Kilitli Ders Uyarısı",
                f"🔒 '{s_name}' ({c_name}) dersi kilitlenmiştir.\n\n"
                "Kilitli dersin kilidini kaldırıp programa/tepsiye geri almak istiyor musunuz?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if ret != QMessageBox.Yes:
                return

        if hasattr(win, "_push_undo_state"):
            win._push_undo_state()

        target_entity = c_name if view_mode == "classes" else (t_name or row_header_name)
        
        # 2. Identify all target slots to remove
        block_ids = {p.get("block_id") for p in matching_block_placements if p.get("block_id")}
        target_slots = set()
        for p in matching_block_placements:
            sd = int(p.get("day") if "day" in p else p.get("col", del_day))
            sp = int(p.get("period") if "period" in p else p.get("row", del_period))
            # CRITICAL: expand across this row's OWN duration, not just its starting period.
            # Manually-placed lessons are stored as one row per hour (duration always 1), so
            # this never mattered there — but the auto-scheduler stores a whole 1-2 hour block
            # as a SINGLE row with duration=span. Only ever adding the start left the block's
            # trailing hour(s) out of target_slots entirely: grid_placements still happened to
            # get cleaned (the one row's own start matched), but the in-memory _placed_lessons
            # cache for that trailing hour was never popped, so it kept "remembering" a lesson
            # that no longer existed there — which is exactly why clicking a now visually-empty
            # cell could still make an already-removed lesson pop back up.
            p_dur = int(p.get("duration", 1))
            for off in range(max(1, p_dur)):
                target_slots.add((sd, sp + off))

        if not target_slots:
            for off in range(max(1, orig_dur)):
                target_slots.add((del_day, del_period + off))

        # Belt-and-suspenders: also sweep _placed_lessons for any cell that still points back
        # to this SAME lesson instance (same origin_row/origin_col) but wasn't captured above,
        # e.g. because matching_block_placements/block_id lookup missed a sibling row. Without
        # this, such a cell would look empty (its QTableWidgetItem/span gets reset below) while
        # still "containing" a lesson as far as click/hover lookups are concerned.
        if hasattr(grid, "_placed_lessons"):
            for (pr, pc), pl in list(grid._placed_lessons.items()):
                if pr == orig_r and pl.get("origin_row", pr) == orig_r and pl.get("origin_col", pc) == orig_c:
                    target_slots.add((pc // periods, pc % periods))

        # 3. Clear cells visually & from placed_lessons
        for (sd, sp) in target_slots:
            sc = sd * periods + sp
            if self.rowSpan(orig_r, sc) > 1 or self.columnSpan(orig_r, sc) > 1:
                self.setSpan(orig_r, sc, 1, 1)
            self.removeCellWidget(orig_r, sc)
            self.takeItem(orig_r, sc)
            self.setItem(orig_r, sc, None)
            if hasattr(grid, "_placed_lessons"):
                grid._placed_lessons.pop((orig_r, sc), None)

        self.viewport().update()

        # 4. Remove from data_store["grid_placements"] & auto_schedule_results
        if hasattr(win, "data_store"):
            def should_remove(p):
                if block_ids and p.get("block_id") in block_ids:
                    return True
                p_d = int(p.get("day") if "day" in p else p.get("col", 0))
                p_p = int(p.get("period") if "period" in p else p.get("row", 0))
                if (p_d, p_p) in target_slots:
                    p_s = (p.get("subject_name") or p.get("subject") or "").strip()
                    p_c = (p.get("class_name") or p.get("class") or "").strip()
                    if not s_name or (p_s == s_name or format_tr_name(p_s) == format_tr_name(s_name)):
                        if view_mode == "classes":
                            if is_comb or not c_name or (matches_class(p_c, c_name) or p_c == c_name):
                                return True
                        else:
                            return True
                return False

            if "grid_placements" in win.data_store:
                win.data_store["grid_placements"] = [p for p in win.data_store.get("grid_placements", []) if not should_remove(p)]
            if "auto_schedule_results" in win.data_store:
                win.data_store["auto_schedule_results"] = [p for p in win.data_store.get("auto_schedule_results", []) if not should_remove(p)]

            # Whatever was just removed from the grid goes STRAIGHT into the dock as its own
            # card — unconditionally, no recomputing "assigned vs. placed" hours to decide
            # whether it's allowed to show up. This is on top of (not instead of) the
            # atamalar-based reconciliation below, which still covers hours that were never
            # placed on the grid in the first place; _refresh_unplaced_lessons treats any
            # hours already represented by one of these loose cards as accounted for, so nothing
            # is ever shown twice.
            if s_name:
                win.data_store.setdefault("loose_unplaced_cards", []).append({
                    "id": f"loose_{uuid.uuid4().hex[:8]}",
                    "subject_name": s_name,
                    "teacher": t_name,
                    "class_name": c_name,
                    "duration": orig_dur,
                    "color": removed_color or "#94A3B8",
                    "is_combined": is_comb,
                    "combined_classes": removed_combined_classes,
                    "is_filler": is_filler,
                })

            if hasattr(win, "mark_dirty"):
                win.mark_dirty()

            if hasattr(win, "save_db"):
                win.save_db(sync_from_grid=False)

            # 5. Refresh grid and unplaced dock (skip_unplaced=True: we do the dock refresh
            # ourselves right below with the correct target_entity, so _refresh_grid must not
            # also do its own untargeted one — that duplicate call was doubling the rebuild
            # cost on every single drag, and its untargeted result could race with/clobber
            # this one, which is why a second consecutive removal sometimes failed to show up)
            if hasattr(win, "_refresh_grid"):
                win._refresh_grid(skip_unplaced=True)
            if hasattr(win, "_refresh_unplaced_lessons"):
                win._refresh_unplaced_lessons(target_entity=target_entity)

    def keyPressEvent(self, event):
        win = self.window()
        if not hasattr(win, "_act_undo") and hasattr(win, "parent") and hasattr(win.parent(), "_act_undo"):
            win = win.parent()
            
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_Z:
                if hasattr(win, "_act_undo"):
                    win._act_undo()
                    return
            elif event.key() == Qt.Key_Y:
                if hasattr(win, "_act_redo"):
                    win._act_redo()
                    return
        elif event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            if event.key() == Qt.Key_Z:
                if hasattr(win, "_act_redo"):
                    win._act_redo()
                    return
                    
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
            is_currently_locked = bool(info.get("locked") in [True, "true", "True", 1, "1"])
            
            act_edit = menu.addAction(make_context_icon("✏️", "#2196F3", "#1976D2"), "Düzenle")
            act_move = menu.addAction(make_context_icon("✥", "#FFCA28", "#FF8F00"), "Taşı")
            if not is_currently_locked:
                act_lock = menu.addAction(make_context_icon("🔒", "#9C27B0", "#7B1FA2"), "Dersi Kilitle (Sabitle)")
                act_unlock = None
            else:
                act_lock = None
                act_unlock = menu.addAction(make_context_icon("🔓", "#E53935", "#C62828"), "Bu Dersin Kilidini Kaldır")
                
            act_unlock_all = None
            act_color = menu.addAction(make_grid_action_icon("palette", 16), "Renk Paleti Ayarla...")
            menu.addSeparator()
            act_del = menu.addAction(make_context_icon("X", "#EF5350", "#C62828"), "Sil (Kaldır)")
            
            action = menu.exec_(self.viewport().mapToGlobal(pos))
            
            if action == act_del:
                self._delete_lesson_at(orig_r, orig_c)
            elif action == act_edit:
                self.cell_right_clicked.emit(orig_r, orig_c)
            elif action in (act_lock, act_unlock):
                new_lock_state = (action == act_lock)
                win = self.window()
                if not hasattr(win, "data_store") and hasattr(win, "parent") and hasattr(win.parent(), "data_store"):
                    win = win.parent()
                if hasattr(win, "_push_undo_state"):
                    win._push_undo_state()
                if hasattr(grid, "_placed_lessons") and (orig_r, orig_c) in grid._placed_lessons:
                    info = grid._placed_lessons[(orig_r, orig_c)]
                    s_name = info.get("subject_name", "")
                    c_name = info.get("class_name", "")
                    
                    from auto_scheduler import matches_class, format_tr_name
                    
                    # Parse all combined partner classes
                    if info.get("is_combined") and info.get("combined_classes"):
                        target_classes = [str(c).strip().split("(")[0].strip() for c in info["combined_classes"] if str(c).strip()]
                    elif "," in c_name or "&" in c_name or "+" in c_name:
                        target_classes = [c.strip().split("(")[0].strip() for c in c_name.replace("&", "+").replace(",", "+").split("+") if c.strip()]
                    else:
                        target_classes = [c_name]
                        
                    periods = getattr(grid, "_periods", 8)
                    if periods <= 0: periods = 8
                    day_idx = orig_c // periods
                    day_start_col = day_idx * periods
                    day_end_col = day_start_col + periods
                    
                    cols_affected = [orig_c]
                    # Scan left
                    c_scan = orig_c - 1
                    while c_scan >= day_start_col:
                        nb = grid._placed_lessons.get((orig_r, c_scan))
                        if nb and (nb.get("subject_name") == s_name or format_tr_name(nb.get("subject_name", "")) == format_tr_name(s_name)):
                            cols_affected.append(c_scan)
                            c_scan -= 1
                        else:
                            break
                    # Scan right
                    c_scan = orig_c + 1
                    while c_scan < day_end_col:
                        nb = grid._placed_lessons.get((orig_r, c_scan))
                        if nb and (nb.get("subject_name") == s_name or format_tr_name(nb.get("subject_name", "")) == format_tr_name(s_name)):
                            cols_affected.append(c_scan)
                            c_scan += 1
                        else:
                            break
                            
                    # 1. Update memory placements in data_store for all combined classes
                    win = self.window()
                    if hasattr(win, "data_store") and win.data_store:
                        for cl in cols_affected:
                            p_per = cl % periods
                            for p in win.data_store.get("grid_placements", []):
                                p_day = int(p.get("day", p.get("col", -1)))
                                p_p = int(p.get("period", p.get("row", -1)))
                                p_subj = p.get("subject_name") or p.get("subject") or ""
                                p_cls = (p.get("class_name") or p.get("class") or "").strip()
                                if (p_subj == s_name or format_tr_name(p_subj) == format_tr_name(s_name)) and p_day == day_idx and p_p == p_per:
                                    if any(matches_class(p_cls, tc) or matches_class(tc, p_cls) or p_cls == tc for tc in target_classes) or p_cls == c_name:
                                        p["locked"] = new_lock_state
                                        
                    # 2. Update all matching placed lesson cells across all rows in grid
                    for (r_k, c_k), pl in list(grid._placed_lessons.items()):
                        if c_k in cols_affected and (pl.get("subject_name") == s_name or format_tr_name(pl.get("subject_name", "")) == format_tr_name(s_name)):
                            pl_cls = (pl.get("class_name") or "").strip()
                            if any(matches_class(pl_cls, tc) or matches_class(tc, pl_cls) or pl_cls == tc for tc in target_classes) or pl_cls == c_name:
                                pl["locked"] = new_lock_state
                                it = self.item(r_k, c_k)
                                if it:
                                    if new_lock_state:
                                        if "🔒" not in it.text():
                                            it.setText(f"🔒 {it.text()}")
                                    else:
                                        it.setText(it.text().replace("🔒", "").strip())
                                        
                    if hasattr(win, "save_db"): win.save_db(sync_from_grid=False)
                    if hasattr(win, "_refresh_grid"): win._refresh_grid()
                    lock_msg = "kilitlendi" if new_lock_state else "kilidi kaldırıldı"
                    lock_icon = "🔒" if new_lock_state else "🔓"
                    if hasattr(win, "statusBar") and win.statusBar():
                        win.statusBar().showMessage(f"{lock_icon} '{s_name}' ({c_name}) dersi {lock_msg}.")
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
                            if self.rowSpan(orig_r, orig_c) > 1 or self.columnSpan(orig_r, orig_c) > 1:
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
            if self.rowSpan(d_orig_r, d_orig_c) > 1 or self.columnSpan(d_orig_r, d_orig_c) > 1:
                self.setSpan(d_orig_r, d_orig_c, 1, 1)
            for r_off in range(d_dur):
                tr = d_orig_r + r_off
                if tr < self.rowCount():
                    self.setItem(tr, d_orig_c, None)
            grid._placed_lessons.pop((d_orig_r, d_orig_c), None)

        # 3. Clear old span of target lesson and apply new span
        if self.rowSpan(orig_r, orig_c) > 1 or self.columnSpan(orig_r, orig_c) > 1:
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
        self.toggle_panel_btn.setIcon(make_grid_action_icon("toggle_panel", 15))
        self.toggle_panel_btn.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self.toggle_panel_btn.setFixedHeight(30)
        self.toggle_panel_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_panel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1;
                border-radius: 15px; padding: 0 14px; font-weight: 600;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{ background-color: #F8FAFC; border-color: #0284C7; color: #0284C7; }}
        """)
        top.addWidget(self.toggle_panel_btn)
        
        top.addSpacing(8)
        
        # Segmented view switchers (Sınıflar Çarşafı / Öğretmenler Çarşafı)
        switcher_frame = QFrame(self)
        switcher_frame.setStyleSheet("QFrame { background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 16px; }")
        switcher_layout = QHBoxLayout(switcher_frame)
        switcher_layout.setContentsMargins(2, 2, 2, 2)
        switcher_layout.setSpacing(2)
        
        self.btn_view_classes = QPushButton(" Sınıflar Çarşafı", switcher_frame)
        self.btn_view_classes.setIcon(make_grid_action_icon("siniflar", 16))
        self.btn_view_teachers = QPushButton(" Öğretmenler Çarşafı", switcher_frame)
        self.btn_view_teachers.setIcon(make_grid_action_icon("ogretmenler", 16))
        
        for btn in (self.btn_view_classes, self.btn_view_teachers):
            btn.setCheckable(True)
            btn.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
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
        btn_unlock_all.setIcon(make_grid_action_icon("lock_open", 15))
        btn_unlock_all.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        btn_unlock_all.setFixedHeight(30)
        btn_unlock_all.setCursor(Qt.PointingHandCursor)
        btn_unlock_all.setStyleSheet(f"""
            QPushButton {{
                background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;
                border-radius: 15px; padding: 0 14px; font-weight: 600;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{ background: #FEE2E2; }}
        """)
        btn_unlock_all.clicked.connect(self._unlock_all_lessons)
        top.addWidget(btn_unlock_all)
        
        layout.addLayout(top)

        # ── Table (aSc-style gray compact grid)
        self.table = DropTableWidget(self._periods, len(DAYS), self)
        self.table.cell_right_clicked.connect(self.cell_right_clicked)
        self.table.setVerticalHeaderLabels([f"{i+1}" for i in range(self._periods)])

        self.table.setShowGrid(False)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.table.setVerticalHeader(AsCVerticalHeader(self.table))
        vh = self.table.verticalHeader()
        vh.setSectionResizeMode(QHeaderView.Stretch)
        vh.setMinimumSectionSize(0)
        vh.setDefaultSectionSize(36)
        vh.setDefaultAlignment(Qt.AlignCenter)
        vh.setStyleSheet(f"""
            QHeaderView::section {{
                background: #F8FAFC;
                font-weight: 600;
                border: none;
                border-right: 1px solid #E2E8F0;
                border-bottom: 1px solid #E2E8F0;
                padding: 1px 6px;
                font-size: 11px;
                font-family: {FONT_FAMILY};
                color: #0F172A;
            }}
        """)

        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                font-size: 11px;
                font-family: {FONT_FAMILY};
                selection-background-color: #EFF6FF;
                selection-color: #0071E3;
            }}
            QTableWidget::item {{
                padding: 0px;
                border: none;
            }}
            QScrollBar:vertical {{
                background: #F8FAFC;
                width: 8px;
                margin: 0;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: #CBD5E1;
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #94A3B8;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: #F8FAFC;
                height: 8px;
                margin: 0;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: #CBD5E1;
                min-width: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: #94A3B8;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)

        # Connect explicit click, keyboard navigation, and header click for info panel & unplaced dock update
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.currentCellChanged.connect(lambda r, c, pr, pc: self._on_cell_clicked(r, c) if r >= 0 and c >= 0 else None)
        self.table.cellPressed.connect(self._on_cell_clicked)
        self.table.verticalHeader().sectionClicked.connect(self._on_vertical_header_clicked)
        
        layout.addWidget(self.table, stretch=1)
        
        # ── Bottom area: info panel + unplaced dock
        bottom_frame = QFrame(self)
        bottom_frame.setFixedHeight(72)
        bottom_frame.setStyleSheet("QFrame { background: #FFFFFF; border-top: 1px solid #E2E8F0; }")
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(6, 4, 6, 4)
        bottom_layout.setSpacing(8)
        
        # Left: Lesson Info Panel (Apple Minimalist Card Style)
        self.info_panel = QFrame(self)
        self.info_panel.setFixedHeight(54)
        self.info_panel.setMinimumWidth(260)
        self.info_panel.setMaximumWidth(380)
        self.info_panel.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 9px; }")
        info_lay = QHBoxLayout(self.info_panel)
        info_lay.setContentsMargins(10, 5, 12, 5)
        info_lay.setSpacing(9)
        
        # Color swatch
        self.info_color_box = QLabel()
        self.info_color_box.setFixedSize(20, 20)
        self.info_color_box.setCursor(Qt.PointingHandCursor)
        self.info_color_box.setToolTip("Ders Rengini Değiştirmek İçin Tıklayın")
        self.info_color_box.setStyleSheet("background: transparent; border: 1px dashed #94A3B8; border-radius: 5px;")
        self.info_color_box.mousePressEvent = self._on_color_box_clicked
        info_lay.addWidget(self.info_color_box, 0, Qt.AlignVCenter)
        
        # Text details
        info_inner = QVBoxLayout()
        info_inner.setContentsMargins(0, 0, 0, 0)
        info_inner.setSpacing(2)
        
        # Top line: Subject Name + Duration (Apple minimal text format)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)
        
        self.info_subject_lbl = QLabel("Ders Seçilmedi")
        self.info_subject_lbl.setFont(QFont(FONT_FAMILY, 9.5, QFont.Bold))
        self.info_subject_lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        top_row.addWidget(self.info_subject_lbl)
        
        self.info_duration_lbl = QLabel("")
        self.info_duration_lbl.setFont(QFont(FONT_FAMILY, 8.5))
        self.info_duration_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
        top_row.addWidget(self.info_duration_lbl)
        top_row.addStretch()
        
        # Backwards compatibility
        self.info_duration_badge = self.info_duration_lbl
        self.info_weekly_badge = QLabel("")
        self.info_lock_badge = QLabel("")
        
        info_inner.addLayout(top_row)
        
        # Bottom line: Class + Teacher
        bot_row = QHBoxLayout()
        bot_row.setContentsMargins(0, 0, 0, 0)
        bot_row.setSpacing(5)
        
        self.info_class_lbl = QLabel("")
        self.info_class_lbl.setFont(QFont(FONT_FAMILY, 8.5, QFont.Bold))
        self.info_class_lbl.setStyleSheet("color: #2563EB; background: transparent; border: none;")
        self.info_class_badge = self.info_class_lbl
        bot_row.addWidget(self.info_class_lbl)
        
        self.info_dot_lbl = QLabel("•")
        self.info_dot_lbl.setStyleSheet("color: #CBD5E1; background: transparent; border: none;")
        self.info_dot_lbl.hide()
        bot_row.addWidget(self.info_dot_lbl)
        
        self.info_teacher_lbl = QLabel("Detaylar için bir derse tıklayın")
        self.info_teacher_lbl.setFont(QFont(FONT_FAMILY, 8.5))
        self.info_teacher_lbl.setStyleSheet("color: #94A3B8; font-style: italic; background: transparent; border: none;")
        bot_row.addWidget(self.info_teacher_lbl)
        bot_row.addStretch()
        info_inner.addLayout(bot_row)
        
        info_lay.addLayout(info_inner, 1)
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
        active_style = f"QPushButton {{ background-color: #0071E3; color: #FFFFFF; border: none; border-radius: 14px; padding: 0 16px; font-weight: 700; font-family: {FONT_FAMILY}; font-size: 12px; }} QPushButton:hover {{ background-color: #0062C4; }}"
        inactive_style = f"QPushButton {{ background-color: transparent; color: #64748B; border: none; border-radius: 14px; padding: 0 16px; font-weight: 600; font-family: {FONT_FAMILY}; font-size: 12px; }} QPushButton:hover {{ background-color: #E2E8F0; color: #0F172A; }}"
        self.btn_view_classes.setStyleSheet(active_style if self.current_view_mode == "classes" else inactive_style)
        self.btn_view_teachers.setStyleSheet(active_style if self.current_view_mode == "teachers" else inactive_style)

    def _set_view_mode(self, mode: str):
        if getattr(self, "current_view_mode", None) == mode:
            return
        self.current_view_mode = mode
        self.btn_view_classes.setChecked(mode == "classes")
        self.btn_view_teachers.setChecked(mode == "teachers")
        self._update_view_btn_styles()
        self.view_mode_changed.emit(mode)

    def _unlock_all_lessons(self):
        for (r, c), p_info in self._placed_lessons.items():
            p_info["locked"] = False
            p_info["is_manual"] = False
            c_item = self.table.item(r, c)
            if c_item:
                c_item.setText(c_item.text().replace("🔒", ""))
        win = self.window()
        if hasattr(win, "data_store"):
            for p in win.data_store.get("grid_placements", []):
                p["locked"] = False
                p["is_manual"] = False
            for p in win.data_store.get("auto_schedule_results", []):
                p["locked"] = False
                p["is_manual"] = False
            for k, v in win.data_store.get("yerlesim", {}).items():
                if isinstance(v, dict):
                    v["locked"] = False
                    v["is_manual"] = False
            if hasattr(win, "save_db"):
                win.save_db(sync_from_grid=False)
            if hasattr(win, "_refresh_grid"):
                win._refresh_grid()
        self.table.viewport().update()
        self.table.update()
        if hasattr(win, "statusBar") and win.statusBar():
            win.statusBar().showMessage("🔓 Tüm derslerin kilitleri başarıyla açıldı.", 3000)

    def _on_vertical_header_clicked(self, logicalIndex):
        if logicalIndex < 0:
            return
        self.table.selectRow(logicalIndex)
        self._on_cell_clicked(logicalIndex, 0)

    def _on_cell_clicked(self, row, col):
        """Show lesson info in the bottom-left panel when a cell is clicked (aSc-style) and filter unplaced dock."""
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
        
        self.update_info_panel(info)
        
        # Filter unplaced dock by the selected class or teacher row
        entity_name = ""
        if self.current_view_mode == "classes":
            if hasattr(self, "class_list") and 0 <= row < len(self.class_list):
                entity_name = self.class_list[row]
        else:
            if hasattr(self, "teacher_list") and 0 <= row < len(self.teacher_list):
                entity_name = self.teacher_list[row]
                
        win = self.window()
        if hasattr(win, "_refresh_unplaced_lessons"):
            win._refresh_unplaced_lessons(target_entity=entity_name)

    def update_info_panel(self, info):
        if not info:
            self.info_color_box.setStyleSheet("background: transparent; border: 1px dashed #94A3B8; border-radius: 5px;")
            self.info_subject_lbl.setText("Ders Seçilmedi")
            self.info_duration_lbl.setText("")
            self.info_class_lbl.setText("")
            self.info_dot_lbl.hide()
            self.info_teacher_lbl.setText("Detaylar için bir derse tıklayın")
            self.info_teacher_lbl.setStyleSheet("color: #94A3B8; font-style: italic; background: transparent; border: none;")
            return
            
        subj = info.get("subject_name", "") or info.get("subject", "")
        teacher = info.get("teacher_name", "") or info.get("teacher", "")
        cls = info.get("class_name", "") or info.get("class", "")
        dur = int(info.get("duration", 1) or 1)
        is_locked = bool(info.get("locked"))
        
        win = self.window()
        data_store = getattr(win, "data_store", None)
        from dialogs.color_picker_dialog import resolve_subject_color
        color_key = subj or ""
        color = resolve_subject_color(color_key, data_store) if color_key else info.get("color", "#2563EB")
        info["color"] = color
        
        # Color Box
        self.info_color_box.setStyleSheet(f"background: {color}; border: 1px solid rgba(0,0,0,0.15); border-radius: 5px;")
        
        # Subject Label
        lock_prefix = "🔒 " if is_locked else ""
        self.info_subject_lbl.setText(f"{lock_prefix}{subj}")
        
        # Weekly Distribution & Curly Format Calculation (e.g. {2+1}, {2+2})
        weekly_dist = []
        total_weekly_hours = 0
        if data_store and subj:
            for a in data_store.get("atamalar", []):
                a_subj = a.get("subject", "")
                a_cls = a.get("class", "")
                a_tch = a.get("teacher", "")
                
                subj_match = format_tr_name(a_subj) == format_tr_name(subj)
                cls_match = (not cls) or matches_class(a_cls, cls) or (a.get("is_combined") and any(matches_class(cc, cls) for cc in a.get("combined_classes", [])))
                tch_match = (not teacher) or (format_tr_name(a_tch) == format_tr_name(teacher))
                
                if subj_match and cls_match and tch_match:
                    a_dur = int(a.get("duration", 1) or 1)
                    if a_dur == 3:
                        weekly_dist.extend([2, 1])
                    elif a_dur == 4:
                        weekly_dist.extend([2, 2])
                    elif a_dur == 5:
                        weekly_dist.extend([2, 2, 1])
                    elif a_dur == 6:
                        weekly_dist.extend([2, 2, 2])
                    elif a_dur > 0:
                        weekly_dist.append(a_dur)
                    total_weekly_hours += a_dur
                    
        if weekly_dist:
            weekly_dist.sort(reverse=True)
            dist_str = "{" + "+".join(str(x) for x in weekly_dist) + "}"
        else:
            if dur == 3:
                dist_str = "{2+1}"
            elif dur == 4:
                dist_str = "{2+2}"
            else:
                dist_str = f"{{{dur}}}"
                
        self.info_duration_lbl.setText(f"•  {dur} Saat  {dist_str}")
            
        # Class Label
        is_comb = bool(info.get("is_combined") or (cls and ("," in cls or "&" in cls or "+" in cls)))
        full_comb_cls = cls
        if not is_comb and data_store and subj:
            for a in data_store.get("atamalar", []):
                if (a.get("is_combined") or ("+" in str(a.get("class", "")))) and a.get("subject") == subj:
                    if not cls or any(matches_class(cc, cls) for cc in a.get("combined_classes", [])) or matches_class(a.get("class", ""), cls):
                        is_comb = True
                        full_comb_cls = a.get("class", "") or " + ".join(a.get("combined_classes", []))
                        break
                        
        if is_comb:
            clean_cls = full_comb_cls.replace("&", ", ").replace("+", ", ").strip()
            self.info_class_lbl.setText(f"Ortak: {clean_cls.upper()}")
        else:
            self.info_class_lbl.setText(cls.upper() if cls else "")
            
        if cls and teacher:
            self.info_dot_lbl.show()
        else:
            self.info_dot_lbl.hide()
            
        # Teacher Label
        self.info_teacher_lbl.setText(teacher if teacher else "Öğretmen Belirtilmedi")
        self.info_teacher_lbl.setStyleSheet("color: #475569; font-style: normal; background: transparent; border: none;")
        
        if win and hasattr(win, "statusBar") and win.statusBar():
            lock_text = " [Kilitli]" if is_locked else ""
            win.statusBar().showMessage(f"{subj}  •  {cls}  •  {teacher}  ({dur} Saat){lock_text}")

    def set_periods(self, periods: int):
        new_periods = max(1, min(16, int(periods)))
        if self._periods != new_periods:
            self._periods = new_periods
            self.table.setRowCount(self._periods)
            self.table.setVerticalHeaderLabels([f"{i+1}" for i in range(self._periods)])

    def set_cell(self, row, col, subject_name, color, teacher_name="", duration=1, class_name="", display_mode="classes", locked=False, is_manual=False, is_combined=False, combined_classes=None):
        if display_mode == "teachers":
            fmt_c = _CLASS_FMT_CACHE.get(class_name)
            if fmt_c is None:
                c_clean = str(class_name).replace("(ea)", "(EA)").replace("(say)", "(SAY)").replace("(soz)", "(SÖZ)").replace("(dil)", "(DİL)")
                if "," in c_clean or "&" in c_clean or "+" in c_clean:
                    fmt_c = "+".join([c.strip().split("(")[0].strip() for c in c_clean.replace("&", ",").replace("+", ",").split(",") if c.strip()])
                else:
                    fmt_c = c_clean.strip().split("(")[0].strip()
                _CLASS_FMT_CACHE[class_name] = fmt_c
            display_text = fmt_c
        else:
            display_text = get_subject_abbr(subject_name)
            
        item = QTableWidgetItem(display_text)
        item.setTextAlignment(Qt.AlignCenter)
        item.setBackground(_fast_cell_brush(color))
        item.setForeground(_fast_text_brush(color))
        item.setFont(_CELL_FONT)
        
        self.table.setItem(row, col, item)
        
        if duration > 1:
            self.table.setSpan(row, col, 1, duration)
        elif self.table.rowSpan(row, col) > 1 or self.table.columnSpan(row, col) > 1:
            self.table.setSpan(row, col, 1, 1)
        
        periods = self._periods
        day_idx = col // periods if periods > 0 else 0
        period_idx = col % periods if periods > 0 else 0
        info_dict = {
            "subject_name": subject_name,
            "teacher_name": teacher_name,
            "class_name": class_name,
            "duration": duration,
            "color": color,
            "locked": bool(locked),
            "is_manual": bool(is_manual),
            "is_combined": bool(is_combined),
            "combined_classes": combined_classes or [],
            "day_idx": day_idx, "period": period_idx,
            "origin_row": row, "origin_col": col
        }
        for off in range(duration):
            self._placed_lessons[(row, col + off)] = info_dict
            
    def get_placed_lessons(self):
        """Return dict of placed lessons for printing"""
        return self._placed_lessons
        
    def clear_grid(self):
        self.table.clearContents()
        self.table.clearSpans()
        self._placed_lessons.clear()

    def adjust_columns_to_fit(self):
        """Dynamically scales all columns so the timetable always perfectly fits the available viewport width without right-side overflow."""
        total_cols = self.table.columnCount()
        if total_cols <= 0:
            return
            
        vw = self.table.viewport().width()
        vh = self.table.verticalHeader()
        vh_w = vh.width() if (vh and vh.isVisible()) else 0
        if vw <= 50:
            vw = self.table.width() - vh_w - 4
            
        if vw <= 50:
            return
            
        base_w = vw // total_cols
        remainder = vw % total_cols
        
        # Responsive column width: fit 100% of viewport width
        min_w = 4
        col_w = max(min_w, base_w)
        
        for c in range(total_cols):
            w = col_w + (1 if c < remainder else 0)
            self.table.setColumnWidth(c, w)
            
        if hasattr(self.table, "asc_header"):
            self.table.asc_header.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_columns_to_fit()
        
    # ── YERLEŞİM ANALİZİ: ızgara koordinatı -> takvim koordinatı ────────────
    #
    # Piksel eşiği ve "col // periods" hesabı arayüzün içine dağılmış olmasın diye
    # tek yer: hangi hücre hangi güne, saate ve hangi sınıf/öğretmen satırına
    # denk geliyor? Sürükleme analizi de bırakma da buradan okur.
    def resolve_cell(self, row: int, col: int) -> dict:
        periods = max(1, int(getattr(self, "_periods", 8) or 8))
        mode = getattr(self, "current_view_mode", "classes")
        out = {"row": row, "col": col, "day": -1, "period": -1,
               "class_name": "", "teacher_name": "", "mode": mode}
        if row < 0 or col < 0:
            return out

        if mode == "classes":
            out["day"], out["period"] = col // periods, col % periods
            names = getattr(self, "class_list", []) or []
            if row < len(names):
                out["class_name"] = names[row]
        elif mode == "teachers":
            out["day"], out["period"] = col // periods, col % periods
            names = getattr(self, "teacher_list", []) or []
            if row < len(names):
                out["teacher_name"] = names[row]
        else:
            # Tek birim görünümü: satır = ders saati, sütun = gün.
            out["day"], out["period"] = col, row
            kind, name = getattr(self, "_single_entity", ("class", ""))
            if kind == "teacher":
                out["teacher_name"] = name
            else:
                out["class_name"] = name
        return out

    def set_single_entity(self, kind: str, name: str):
        """Tek birim görünümünde ekranda kimin çizelgesi var (analiz için)."""
        self._single_entity = (kind or "class", name or "")

    def rows_for_lesson(self, lesson: dict) -> list:
        """Bu ders hangi satırlara konabilir? (analiz yalnız o satırlarda döner)

        Bir ders yalnız KENDİ sınıfının satırına konabilir; öğretmen görünümünde
        de kendi öğretmeninin satırına. Bütün ızgarayı taramak hem yanlış (başka
        sınıfın satırı bu ders için bir aday değildir) hem de gereksiz.
        """
        import placement_engine as pe
        mode = getattr(self, "current_view_mode", "classes")
        if mode == "classes":
            wanted = {pe.class_key(c) for c in pe.lesson_classes(lesson)}
            return [i for i, name in enumerate(getattr(self, "class_list", []) or [])
                    if pe.class_key(name) in wanted]
        if mode == "teachers":
            wanted = {pe.teacher_key(t) for t in pe.lesson_teachers(lesson)}
            return [i for i, name in enumerate(getattr(self, "teacher_list", []) or [])
                    if pe.teacher_key(name) in wanted]
        return list(range(self.table.rowCount()))

    def set_mode_single_entity(self, periods: int, days_list: list):
        """Standard view: 1 entity (class/teacher), Rows=Periods, Cols=Days"""
        self._periods = periods
        self._active_table_layout_sig = ("single", periods, tuple(days_list))
        self.table.setRowCount(periods)
        self.table.setColumnCount(len(days_list))
        if hasattr(self.table, "asc_header"):
            self.table.asc_header.set_config(1, days_list)
        self.table.setVerticalHeaderLabels([f"{i+1}" for i in range(periods)])
        self.adjust_columns_to_fit()
        self.clear_grid()
        
    def set_mode_all_classes(self, class_list: list, periods: int, days_list: list):
        """Whole School View (aSc Çarşaf - Sınıflar): Rows=Classes, Cols=Days*Periods"""
        self._periods = periods
        self.class_list = class_list
        self.current_view_mode = "classes"
        total_cols = len(days_list) * periods

        sig = ("classes", tuple(class_list), periods, tuple(days_list))
        if getattr(self, "_active_table_layout_sig", None) != sig:
            self._active_table_layout_sig = sig
            self.table.setRowCount(len(class_list))
            self.table.setVerticalHeaderLabels(class_list)
            self.table.setColumnCount(total_cols)

            if hasattr(self.table, "asc_header"):
                self.table.asc_header.set_config(periods, days_list)

            self.adjust_columns_to_fit()
            for r in range(len(class_list)):
                self.table.setRowHeight(r, 28)
        else:
            self.adjust_columns_to_fit()

        self.clear_grid()

    def set_mode_all_teachers(self, teacher_list: list, periods: int, days_list: list):
        """Whole School View (aSc Çarşaf - Öğretmenler): Rows=Teachers, Cols=Days*Periods"""
        self._periods = periods
        self.teacher_list = teacher_list
        self.current_view_mode = "teachers"
        total_cols = len(days_list) * periods

        sig = ("teachers", tuple(teacher_list), periods, tuple(days_list))
        if getattr(self, "_active_table_layout_sig", None) != sig:
            self._active_table_layout_sig = sig
            self.table.setRowCount(len(teacher_list))
            self.table.setVerticalHeaderLabels(teacher_list)
            self.table.setColumnCount(total_cols)

            if hasattr(self.table, "asc_header"):
                self.table.asc_header.set_config(periods, days_list)

            self.adjust_columns_to_fit()
            for r in range(len(teacher_list)):
                self.table.setRowHeight(r, 28)
        else:
            self.adjust_columns_to_fit()

        self.clear_grid()

