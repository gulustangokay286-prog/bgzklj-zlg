"""
ribbon_widget.py  –  Pixel-perfect Ribbon toolbar
Birebir aSc k12 Bilişim Ders Planlama 2020 görünümü
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QSizePolicy, QFrame, QCheckBox, QToolButton
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QPen, QFont, QBrush, QPolygon, QLinearGradient, QRadialGradient, QPainterPath, QPainterPath
from PySide6.QtCore import QPoint, QPointF


# ── Colours from screenshots ──────────────────────────────────────────────────
RIBBON_BG        = "#FFFFFF"
RIBBON_BORDER    = "#D0D0D0"
TAB_ACTIVE_BG    = "#FFFFFF"
TAB_INACTIVE_BG  = "#F0F0F0"
TAB_ACTIVE_LINE  = "#1E6DB5"   # blue underline on active tab
TAB_TEXT         = "#333333"
TAB_ACTIVE_TEXT  = "#1E6DB5"
BTN_HOVER_BG     = "#DAE8FC"
BTN_PRESSED_BG   = "#B8D4F0"
GROUP_DIVIDER    = "#CCCCCC"
BACK_BTN_BG      = "#1E6DB5"


# ── Icon painter helpers ──────────────────────────────────────────────────────
def _make_pixmap(size: int, draw_fn) -> QPixmap:
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    draw_fn(p, size)
    p.end()
    return px


def icon_new(p, s):
    p.setBrush(QBrush(QColor("#0EA5E9")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(4, 3, s-8, s-6, 4, 4)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(6, 5, s-12, s-10, 3, 3)
    p.setBrush(QBrush(QColor("#10B981")))
    p.drawEllipse(s-14, s-14, 12, 12)
    p.setPen(QPen(Qt.white, 2))
    p.drawLine(s-8, s-12, s-8, s-4)
    p.drawLine(s-12, s-8, s-4, s-8)

def icon_open(p, s):
    p.setBrush(QBrush(QColor("#D97706")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(3, 7, 13, 6, 2, 2)
    p.setBrush(QBrush(QColor("#F59E0B")))
    path = QPainterPath()
    path.moveTo(3, 11)
    path.lineTo(s-3, 11)
    path.lineTo(s-6, s-5)
    path.lineTo(6, s-5)
    path.closeSubpath()
    p.drawPath(path)

def icon_save(p, s):
    p.setBrush(QBrush(QColor("#0284C7")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(3, 3, s-6, s-6, 4, 4)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(7, 3, s-14, 9, 1, 1)
    p.setBrush(QBrush(QColor("#E2E8F0")))
    p.drawRoundedRect(7, 16, s-14, 11, 2, 2)

def icon_print(p, s):
    p.setBrush(QBrush(QColor("#64748B")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(3, 11, s-6, 12, 3, 3)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(7, 3, s-14, 9, 2, 2)
    p.drawRoundedRect(7, 18, s-14, 9, 2, 2)
    p.setBrush(QBrush(QColor("#38BDF8")))
    p.drawEllipse(s-9, 14, 4, 4)

def icon_preview(p, s):
    p.setBrush(QBrush(QColor("#0EA5E9")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(5, 3, 16, 24, 3, 3)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(7, 5, 12, 20, 2, 2)
    p.setPen(QPen(QColor("#0284C7"), 2.5))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(15, 12, 10, 10)
    p.drawLine(22, 19, 28, 25)

def icon_back(p, s):
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    arr = QPolygon([QPoint(s//2, 4), QPoint(4, s//2), QPoint(s//2, s-4), QPoint(s//2, s//2+4), QPoint(s-6, s//2+4), QPoint(s-6, s//2-4), QPoint(s//2, s//2-4)])
    p.drawPolygon(arr)

def icon_teachers(p, s):
    p.setBrush(QBrush(QColor("#10B981")))
    p.setPen(Qt.NoPen)
    p.drawEllipse(s//2-5, 3, 10, 10)
    path = QPainterPath()
    path.moveTo(3, s-5)
    path.cubicTo(3, 16, s-3, 16, s-3, s-5)
    path.lineTo(s-3, s-4)
    path.lineTo(3, s-4)
    path.closeSubpath()
    p.drawPath(path)

def icon_classes(p, s):
    p.setBrush(QBrush(QColor("#0284C7")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(3, 3, 11, 11, 3, 3)
    p.drawRoundedRect(17, 3, 11, 11, 3, 3)
    p.drawRoundedRect(3, 17, 11, 11, 3, 3)
    p.drawRoundedRect(17, 17, 11, 11, 3, 3)

def icon_rooms(p, s):
    p.setBrush(QBrush(QColor("#8B5CF6")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(3, 4, 26, 18, 3, 3)
    p.setPen(QPen(QColor("#7C3AED"), 2.5))
    p.drawLine(7, 22, 4, 29)
    p.drawLine(24, 22, 27, 29)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#F3E8FF")))
    p.drawRoundedRect(5, 6, 22, 14, 1, 1)

def icon_subjects(p, s):
    p.setBrush(QBrush(QColor("#F59E0B")))
    p.setPen(Qt.NoPen)
    cap = QPainterPath()
    cap.moveTo(16, 4)
    cap.lineTo(30, 11)
    cap.lineTo(16, 18)
    cap.lineTo(2, 11)
    cap.closeSubpath()
    p.drawPath(cap)
    base = QPainterPath()
    base.moveTo(7, 15)
    base.lineTo(7, 22)
    base.cubicTo(7, 28, 25, 28, 25, 22)
    base.lineTo(25, 15)
    p.drawPath(base)

def icon_schedule(p, s):
    p.setBrush(QBrush(QColor("#EF4444")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(3, 4, s-6, s-7, 4, 4)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(3, 11, s-6, s-14, 0, 0)
    p.setBrush(QBrush(QColor("#94A3B8")))
    for x in [7, 14, 21]:
        for y in [15, 21]:
            p.drawRoundedRect(x, y, 4, 4, 1, 1)

def icon_auto(p, s):
    p.setBrush(QBrush(QColor("#F59E0B")))
    p.setPen(Qt.NoPen)
    pts = [QPoint(18, 2), QPoint(6, 17), QPoint(15, 17), QPoint(13, 29), QPoint(26, 13), QPoint(17, 13)]
    p.drawPolygon(QPolygon(pts))

def icon_cloud(p, s):
    p.setBrush(QBrush(QColor("#0284C7")))
    p.setPen(Qt.NoPen)
    path = QPainterPath()
    path.addEllipse(4, 13, 14, 14)
    path.addEllipse(11, 7, 15, 15)
    path.addEllipse(19, 12, 11, 11)
    path.addRect(8, 17, 18, 10)
    p.drawPath(path)

def icon_check(p, s):
    p.setPen(QPen(QColor("#10B981"), 3.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawLine(5, 16, 12, 24)
    p.drawLine(12, 24, 27, 7)

def icon_wizard(p, s):
    p.setPen(QPen(QColor("#8B5CF6"), 2))
    p.drawLine(4, s-4, s-4, 4)

def icon_info(p, s):
    p.setBrush(QBrush(QColor("#3B82F6")))
    p.setPen(Qt.NoPen)
    p.drawEllipse(3, 3, s-6, s-6)
    p.setPen(QPen(Qt.white, 2.5))
    p.setFont(QFont("Segoe UI", 12, QFont.Bold))
    p.drawText(3, 3, s-6, s-6, Qt.AlignCenter, "i")

def icon_help(p, s):
    p.setBrush(QBrush(QColor("#8B5CF6")))
    p.setPen(Qt.NoPen)
    p.drawEllipse(3, 3, s-6, s-6)
    p.setPen(QPen(Qt.white, 2.5))
    p.setFont(QFont("Segoe UI", 12, QFont.Bold))
    p.drawText(3, 3, s-6, s-6, Qt.AlignCenter, "?")

def icon_internet(p, s):
    p.setPen(QPen(QColor("#6366F1"), 2))
    p.setBrush(QBrush(QColor("#EEF2FF")))
    p.drawEllipse(3, 3, s-6, s-6)
    p.drawLine(s//2, 3, s//2, s-3)
    p.drawLine(3, s//2, s-3, s//2)
    p.drawEllipse(s//2-5, 3, 10, s-6)

def icon_color(p, s):
    colors = ["#EF4444","#10B981","#0284C7","#F59E0B"]
    r = (s-8)//2
    for i, c in enumerate(colors):
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(c)))
        x = (i % 2) * (r+2) + 4
        y = (i // 2) * (r+2) + 4
        p.drawEllipse(x, y, r, r)

def icon_font(p, s):
    p.setPen(QPen(QColor("#333"), 2))
    p.setBrush(Qt.NoBrush)
    f = QFont("Segoe UI", 14, QFont.Bold)
    p.setFont(f)
    p.drawText(QPoint(4, s-4), "A")

def icon_lang(p, s):
    p.setPen(QPen(QColor("#555"), 1.5))
    p.setBrush(QBrush(QColor("#C62828")))
    p.drawRect(4, 6, s-8, s-12)

def icon_stat(p, s):
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#0284C7")))
    for i, h in enumerate([8, 14, 10, 16, 12]):
        p.drawRoundedRect(4+i*5, s-4-h, 4, h, 1, 1)

def icon_params(p, s):
    p.setPen(QPen(QColor("#64748B"), 1.5))
    for y in [6, 14, 22]:
        p.setBrush(QBrush(QColor("#94A3B8")))
        p.drawRect(4, y, s-8, 4)
        p.setBrush(QBrush(QColor("#0284C7")))
        cx = 6 + (y//8)*6
        p.drawEllipse(cx, y-1, 6, 6)

def icon_delete(p, s):
    p.setPen(QPen(QColor("#EF4444"), 3.5, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawLine(7, 7, s-7, s-7)
    p.drawLine(s-7, 7, 7, s-7)

def icon_key_lock(p, s):
    p.setBrush(QBrush(QColor("#F59E0B")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(6, 13, 20, 15, 3, 3)
    p.setPen(QPen(QColor("#D97706"), 2.5))
    p.drawArc(10, 4, 12, 16, 0, 180 * 16)

ICON_MAP = {
    "yeni":       icon_new,
    "ac":         icon_open,
    "kaydet":     icon_save,
    "yazdir":     icon_print,
    "on_izleme":  icon_preview,
    "geri":       icon_back,
    "ogretmen":   icon_teachers,
    "sinif":      icon_classes,
    "derslik":    icon_rooms,
    "ders":       icon_subjects,
    "plan":       icon_schedule,
    "otomatik":   icon_auto,
    "bulut":      icon_cloud,
    "kontrol":    icon_check,
    "sihirbaz":   icon_wizard,
    "bilgi":      icon_info,
    "yardim":     icon_help,
    "internet":   icon_internet,
    "renk":       icon_color,
    "yazi":       icon_font,
    "dil":        icon_lang,
    "istatistik": icon_stat,
    "param":      icon_params,
    "temizle":    icon_delete,
    "kilit":      icon_key_lock,
}


def make_icon(key: str, size: int = 32) -> QIcon:
    fn = ICON_MAP.get(key, icon_info)
    return QIcon(_make_pixmap(size, fn))


# ── Ribbon Button ─────────────────────────────────────────────────────────────
class RibbonButton(QToolButton):
    """Vertical icon+label button matching aSc ribbon style"""
    def __init__(self, label: str, icon_key: str, callback=None, parent=None):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIcon(make_icon(icon_key, 32))
        self.setIconSize(QSize(32, 32))
        self.setText(label)
        self.setFixedSize(64, 68)
        self.setCheckable(False)
        font = QFont("Segoe UI", 7)
        self.setFont(font)
        self.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                padding: 2px;
                color: #333333;
                font-size: 7pt;
            }
            QToolButton:hover {
                background: #DAE8FC;
                border: 1px solid #B8CCE4;
                border-radius: 3px;
            }
            QToolButton:pressed {
                background: #B8D4F0;
            }
        """)
        if callback:
            self.clicked.connect(callback)


class RibbonWideButton(QToolButton):
    """Wide back-arrow button (Geri)"""
    def __init__(self, callback=None, parent=None):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIcon(make_icon("geri", 32))
        self.setIconSize(QSize(32, 32))
        self.setText("Geri")
        self.setFixedSize(52, 68)
        font = QFont("Segoe UI", 7, QFont.Bold)
        self.setFont(font)
        self.setStyleSheet("""
            QToolButton {
                background: #1E6DB5;
                border: none;
                border-radius: 4px;
                padding: 2px;
                color: #FFFFFF;
                font-size: 7pt;
                font-weight: bold;
            }
            QToolButton:hover { background: #1557A0; }
            QToolButton:pressed { background: #0F4280; }
        """)
        if callback:
            self.clicked.connect(callback)


class RibbonCheckItem(QWidget):
    """Checkbox item for Arayüz Ayarları panel"""
    def __init__(self, label, checked=True, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 1, 4, 1)
        self.cb = QCheckBox(label, self)
        self.cb.setChecked(checked)
        font = QFont("Segoe UI", 8)
        self.cb.setFont(font)
        layout.addWidget(self.cb)


def _divider(parent=None):
    f = QFrame(parent)
    f.setFrameShape(QFrame.VLine)
    f.setFrameShadow(QFrame.Sunken)
    f.setStyleSheet("color: #CCCCCC;")
    f.setFixedWidth(2)
    return f


# ── Ribbon Tab Page ───────────────────────────────────────────────────────────
class RibbonPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(6, 4, 6, 4)
        self.main_layout.setSpacing(2)
        self.main_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setStyleSheet(f"background: {RIBBON_BG};")

    def add_button(self, label, icon_key, callback=None):
        btn = RibbonButton(label, icon_key, callback, self)
        self.main_layout.addWidget(btn)
        return btn

    def add_back(self, callback=None):
        btn = RibbonWideButton(callback, self)
        self.main_layout.addWidget(btn)
        self.main_layout.addWidget(_divider(self))
        return btn

    def add_divider(self):
        self.main_layout.addWidget(_divider(self))

    def add_stretch(self):
        self.main_layout.addStretch(1)

    def add_checkbox(self, label, checked=True):
        item = RibbonCheckItem(label, checked, self)
        self.main_layout.addWidget(item)
        return item


# ── Main Ribbon Widget ────────────────────────────────────────────────────────
class RibbonWidget(QWidget):
    tab_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(110)
        self._pages = []
        self._tab_buttons = []
        self._active = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Tab bar ──
        self._tab_bar = QWidget(self)
        self._tab_bar.setFixedHeight(28)
        self._tab_bar.setStyleSheet(f"background: {TAB_INACTIVE_BG}; border-bottom: 1px solid {RIBBON_BORDER};")
        self._tab_layout = QHBoxLayout(self._tab_bar)
        self._tab_layout.setContentsMargins(52, 0, 0, 0)
        self._tab_layout.setSpacing(0)
        outer.addWidget(self._tab_bar)

        # ── Page area ──
        self._page_area = QWidget(self)
        self._page_area.setFixedHeight(82)
        self._page_area.setStyleSheet(f"background: {RIBBON_BG}; border-bottom: 1px solid {RIBBON_BORDER};")
        self._page_layout = QVBoxLayout(self._page_area)
        self._page_layout.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._page_area)

    def add_tab(self, name: str) -> RibbonPage:
        idx = len(self._pages)
        page = RibbonPage(self._page_area)

        # Tab button
        btn = QPushButton(name, self._tab_bar)
        btn.setFlat(True)
        btn.setFixedHeight(28)
        btn.setFont(QFont("Segoe UI", 9))
        btn.setCheckable(True)
        btn.setChecked(idx == 0)
        btn.clicked.connect(lambda _, i=idx: self._select(i))
        self._tab_layout.addWidget(btn)
        self._tab_buttons.append(btn)
        self._pages.append(page)

        if idx == 0:
            self._page_layout.addWidget(page)
        else:
            page.setVisible(False)
            self._page_layout.addWidget(page)

        self._update_tab_styles()
        return page

    def _select(self, idx: int):
        if self._active == idx:
            return
        old_page = self._pages[self._active]
        old_page.setVisible(False)
        self._active = idx
        self._pages[idx].setVisible(True)
        self._update_tab_styles()
        self.tab_changed.emit(idx)

    def _update_tab_styles(self):
        for i, btn in enumerate(self._tab_buttons):
            if i == self._active:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #FFFFFF;
                        color: #0284C7;
                        border: none;
                        border-bottom: 2.5px solid #0284C7;
                        padding: 2px 14px;
                        font-weight: 700;
                        font-size: 13px;
                        border-top-left-radius: 6px;
                        border-top-right-radius: 6px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        color: #475569;
                        border: none;
                        border-bottom: 2.5px solid transparent;
                        padding: 2px 14px;
                        font-weight: 600;
                        font-size: 13px;
                        border-top-left-radius: 6px;
                        border-top-right-radius: 6px;
                    }
                    QPushButton:hover {
                        background: #F1F5F9;
                        color: #0F172A;
                    }
                """)
