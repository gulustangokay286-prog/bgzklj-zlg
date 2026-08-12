"""
ribbon_widget.py  –  Pixel-perfect Ribbon toolbar
Birebir aSc k12 Bilişim Ders Planlama 2020 görünümü
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QSizePolicy, QFrame, QCheckBox, QToolButton
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QPen, QFont, QBrush, QPolygon, QLinearGradient, QRadialGradient
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
    # blank document with folded corner
    p.setPen(QPen(QColor("#555"), 1.5))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    pts = [QPoint(8,2), QPoint(s-10,2), QPoint(s-4,10), QPoint(s-4,s-4), QPoint(8,s-4)]
    p.drawPolygon(QPolygon(pts))
    p.setPen(QPen(QColor("#555"), 1.0))
    p.drawLine(s-10, 2, s-10, 10)
    p.drawLine(s-10, 10, s-4,  10)
    # green plus
    p.setPen(QPen(QColor("#2E7D32"), 2))
    cx, cy = 13, s-12
    p.drawLine(cx-4, cy, cx+4, cy)
    p.drawLine(cx, cy-4, cx, cy+4)

def icon_open(p, s):
    # folder
    p.setPen(QPen(QColor("#555"), 1.5))
    p.setBrush(QBrush(QColor("#FFD54F")))
    p.drawRect(5, 9, s-10, s-14)
    p.setBrush(QBrush(QColor("#FFF176")))
    p.drawRect(5, 6, 12, 6)

def icon_save(p, s):
    p.setPen(QPen(QColor("#555"), 1.5))
    p.setBrush(QBrush(QColor("#42A5F5")))
    p.drawRect(4, 4, s-8, s-8)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRect(8, 4, s-16, 8)
    p.setBrush(QBrush(QColor("#E0E0E0")))
    p.drawRect(8, 16, s-16, s-20)

def icon_print(p, s):
    p.setPen(QPen(QColor("#555"), 1.5))
    p.setBrush(QBrush(QColor("#78909C")))
    p.drawRect(4, 10, s-8, s-18)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRect(7, 4, s-14, 10)
    p.drawRect(7, s-12, s-14, 8)

def icon_preview(p, s):
    p.setPen(QPen(QColor("#555"), 1.5))
    p.setBrush(QBrush(QColor("#FFF")))
    p.drawRect(6, 4, s-12, s-8)
    # magnifier
    p.setPen(QPen(QColor("#1E6DB5"), 2))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(s//2-3, s//2-3, 8, 8)
    p.drawLine(s//2+4, s//2+4, s-6, s-6)

def icon_back(p, s):
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    arr = QPolygon([QPoint(s//2, 4), QPoint(4, s//2), QPoint(s//2, s-4), QPoint(s//2, s//2+4), QPoint(s-6, s//2+4), QPoint(s-6, s//2-4), QPoint(s//2, s//2-4)])
    p.drawPolygon(arr)

def icon_teachers(p, s):
    # person silhouette with 3D gradient
    grad = QLinearGradient(0, 0, 0, s)
    grad.setColorAt(0, QColor("#64B5F6"))
    grad.setColorAt(1, QColor("#1565C0"))
    p.setPen(QPen(QColor("#0D47A1"), 1.5))
    p.setBrush(QBrush(grad))
    p.drawEllipse(s//2-6, 2, 12, 12)
    p.drawRoundedRect(s//2-8, 16, 16, s-20, 4, 4)

def icon_classes(p, s):
    grad = QLinearGradient(0, 0, 0, s)
    grad.setColorAt(0, QColor("#81C784"))
    grad.setColorAt(1, QColor("#2E7D32"))
    p.setPen(QPen(QColor("#1B5E20"), 1.5))
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(4, 8, s-8, s-12, 3, 3)
    p.setPen(QPen(QColor("#FFF"), 1.5))
    for y in [14, 20, 26]:
        p.drawLine(8, y, s-8, y)

def icon_rooms(p, s):
    grad = QLinearGradient(0, 0, 0, s)
    grad.setColorAt(0, QColor("#FFCC80"))
    grad.setColorAt(1, QColor("#E65100"))
    p.setPen(QPen(QColor("#BF360C"), 1.5))
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(4, 8, s-8, s-12, 3, 3)
    p.setBrush(QBrush(QColor("#5D4037")))
    p.drawRoundedRect(s//2-3, s-12, 6, 8, 1, 1)

def icon_subjects(p, s):
    grad = QLinearGradient(0, 0, 0, s)
    grad.setColorAt(0, QColor("#CE93D8"))
    grad.setColorAt(1, QColor("#6A1B9A"))
    p.setPen(QPen(QColor("#4A148C"), 1.5))
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(7, 2, s-12, s-6, 3, 3)
    p.setPen(QPen(QColor("#FFF"), 2))
    p.drawLine(10, 9, s-8, 9)
    p.drawLine(10, 16, s-8, 16)
    p.drawLine(10, 23, s-8-6, 23)

def icon_schedule(p, s):
    # calendar with 3D gradient
    grad = QLinearGradient(0, 0, 0, s)
    grad.setColorAt(0, QColor("#FFCDD2"))
    grad.setColorAt(1, QColor("#EF9A9A"))
    p.setPen(QPen(QColor("#B71C1C"), 1.5))
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(4, 6, s-8, s-10, 3, 3)
    top_grad = QLinearGradient(0, 6, 0, 13)
    top_grad.setColorAt(0, QColor("#E53935"))
    top_grad.setColorAt(1, QColor("#B71C1C"))
    p.setBrush(QBrush(top_grad))
    p.drawRoundedRect(4, 6, s-8, 7, 3, 3)
    p.setPen(QPen(QColor("#FFF"), 1))
    for x in [8, 14, 20]:
        for y in [18, 24, 28]:
            p.drawRect(x, y, 3, 3)

def icon_auto(p, s):
    # lightning bolt with gradient
    p.setPen(Qt.NoPen)
    grad = QLinearGradient(0, 0, 0, s)
    grad.setColorAt(0, QColor("#FFEE58"))
    grad.setColorAt(1, QColor("#F57F17"))
    p.setBrush(QBrush(grad))
    pts = [QPoint(s//2+2,2), QPoint(6, s//2), QPoint(s//2, s//2), QPoint(s//2-2,s-2), QPoint(s-6, s//2), QPoint(s//2, s//2)]
    p.drawPolygon(QPolygon(pts))
    # Shadow
    p.setPen(QPen(QColor(0,0,0,40), 1))
    p.setBrush(Qt.NoBrush)
    p.drawPolygon(QPolygon(pts))

def icon_cloud(p, s):
    # Cloud with gradient
    grad = QRadialGradient(QPointF(s//2, s//2), s//2)
    grad.setColorAt(0, QColor("#E1F5FE"))
    grad.setColorAt(1, QColor("#0288D1"))
    p.setPen(QPen(QColor("#01579B"), 1.5))
    p.setBrush(QBrush(grad))
    p.drawEllipse(4, 12, 16, 14)
    p.drawEllipse(10, 6, 14, 14)
    p.drawEllipse(18, 10, 14, 14)
    p.drawRect(4, 18, s-8, 8)

def icon_check(p, s):
    # Green checkmark with shadow
    p.setPen(QPen(QColor(0,0,0,60), 4))
    p.drawLine(5, s//2+1, s//2+1, s-3)
    p.drawLine(s//2+1, s-3, s-3, 5)
    p.setPen(QPen(QColor("#2E7D32"), 3))
    p.setBrush(Qt.NoBrush)
    p.drawLine(4, s//2, s//2, s-4)
    p.drawLine(s//2, s-4, s-4, 4)

def icon_wizard(p, s):
    # magic wand
    p.setPen(QPen(QColor("#7B1FA2"), 2))
    p.drawLine(4, s-4, s-4, 4)
    p.setPen(QPen(QColor("#FFD600"), 2))
    cx, cy = s-8, 6
    for dx, dy in [(0,-4),(3,-3),(4,0),(3,3),(0,4),(-3,3),(-4,0),(-3,-3)]:
        p.drawPoint(cx+dx, cy+dy)

def icon_info(p, s):
    p.setPen(QPen(QColor("#1E6DB5"), 2))
    p.setBrush(QBrush(QColor("#E3F2FD")))
    p.drawEllipse(3, 3, s-6, s-6)
    p.setPen(QPen(QColor("#1E6DB5"), 2.5))
    p.drawText(QPoint(s//2-3, s//2+5), "i")

def icon_help(p, s):
    p.setPen(QPen(QColor("#555"), 2))
    p.setBrush(QBrush(QColor("#E8F5E9")))
    p.drawEllipse(3, 3, s-6, s-6)
    p.setPen(QPen(QColor("#2E7D32"), 2.5))
    f = QFont(); f.setBold(True); f.setPointSize(10)
    p.setFont(f)
    p.drawText(QPoint(s//2-4, s//2+5), "?")

def icon_internet(p, s):
    p.setPen(QPen(QColor("#1E6DB5"), 1.5))
    p.setBrush(QBrush(QColor("#E3F2FD")))
    p.drawEllipse(3, 3, s-6, s-6)
    p.drawLine(s//2, 3, s//2, s-3)
    p.drawLine(3, s//2, s-3, s//2)
    p.drawEllipse(s//2-4, 3, 8, s-6)

def icon_color(p, s):
    colors = ["#F44336","#4CAF50","#2196F3","#FF9800"]
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
    f = QFont(); f.setBold(True); f.setPointSize(14)
    p.setFont(f)
    p.drawText(QPoint(4, s-4), "A")

def icon_lang(p, s):
    p.setPen(QPen(QColor("#555"), 1.5))
    flags = [("#C62828","#FFFFFF","#C62828"), ("#1565C0","#FFFFFF","#C62828")]
    p.setBrush(QBrush(QColor("#C62828")))
    p.drawRect(4, 6, s-8, s-12)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRect(4, 6+(s-12)//3, s-8, (s-12)//3)

def icon_stat(p, s):
    p.setPen(QPen(QColor("#1E6DB5"), 2))
    p.setBrush(QBrush(QColor("#90CAF9")))
    for i, h in enumerate([8, 14, 10, 16, 12]):
        p.drawRect(4+i*5, s-4-h, 4, h)

def icon_params(p, s):
    p.setPen(QPen(QColor("#555"), 1.5))
    for y in [6, 14, 22]:
        p.setBrush(QBrush(QColor("#90A4AE")))
        p.drawRect(4, y, s-8, 4)
        p.setBrush(QBrush(QColor("#1E6DB5")))
        cx = 6 + (y//8)*6
        p.drawEllipse(cx, y-1, 6, 6)

def icon_delete(p, s):
    p.setPen(QPen(QColor("#C62828"), 2))
    p.drawLine(4, 4, s-4, s-4)
    p.drawLine(s-4, 4, 4, s-4)

def icon_key_lock(p, s):
    p.setPen(QPen(QColor("#555"), 1.5))
    p.setBrush(QBrush(QColor("#FFD54F")))
    p.drawEllipse(4, 4, s-12, s-12)
    p.setBrush(QBrush(QColor("#78909C")))
    p.drawRect(s//2, s//2, s//2-2, s//2-2)

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
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {TAB_ACTIVE_BG};
                        color: {TAB_ACTIVE_TEXT};
                        border: none;
                        border-bottom: 3px solid {TAB_ACTIVE_LINE};
                        padding: 0 12px;
                        font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {TAB_INACTIVE_BG};
                        color: {TAB_TEXT};
                        border: none;
                        border-bottom: 3px solid transparent;
                        padding: 0 12px;
                    }}
                    QPushButton:hover {{
                        background: #E8E8E8;
                    }}
                """)
