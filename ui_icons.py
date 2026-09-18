"""ui_icons.py — uygulamanın tek ikon kaynağı.

Neden var
---------
Arayüzde durumlar ve eylemler emoji ile anlatılıyordu (🔒, ⚠️, ✅, 💾, 🎨…).
Emoji üç sorun çıkarır: işletim sistemine göre başka görünür (Windows'ta
Segoe, macOS'ta Apple renkli setiyle çizilir), renkleri arayüzün paletine
uymaz, ve boyutu yazı tipine bağlı olduğu için düğme içinde hizalanmaz.
Burada her işaret vektör olarak, tek renkle ve istenen boyutta çizilir:
retina ekranda keskin, koyu/açık zeminde okunur, paletle uyumlu.

Kullanım
--------
    from ui_icons import icon, pixmap
    btn.setIcon(icon("lock", 16, "#DC2626"))
    lbl.setPixmap(pixmap("warning", 18, "#B45309"))

Ad bulunamazsa boş bir ikon döner (arayüz çökmez). Aynı (ad, boyut, renk)
üçlüsü önbelleklenir; tablo hücrelerinde yüzlerce kez çağrılabilir.
"""
import math

from PySide6.QtCore import Qt, QRectF, QPointF, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath, QPolygonF

_CACHE = {}
DEFAULT_COLOR = "#0F172A"


# ── çizim yardımcıları ─────────────────────────────────────────────────────
def _stroke(p, color, w=1.8):
    pen = QPen(QColor(color), w)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    return pen


def _fill(p, color):
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))


def _poly(*pts):
    return QPolygonF([QPointF(x, y) for x, y in pts])


# ── ikonlar: her biri 100×100 birim kutuda çizer ───────────────────────────
def _lock(p, c, closed=True):
    _stroke(p, c, 8)
    p.drawRoundedRect(QRectF(22, 44, 56, 42), 8, 8)
    path = QPainterPath()
    if closed:
        path.moveTo(35, 44)
        path.lineTo(35, 32)
        path.arcTo(QRectF(35, 14, 30, 36), 180, -180)
        path.lineTo(65, 44)
    else:
        path.moveTo(35, 44)
        path.lineTo(35, 32)
        path.arcTo(QRectF(35, 14, 30, 36), 180, -120)
    p.drawPath(path)
    _fill(p, c)
    p.drawEllipse(QPointF(50, 65), 5.5, 5.5)


def _warning(p, c):
    path = QPainterPath()
    path.moveTo(50, 12)
    path.lineTo(92, 84)
    path.lineTo(8, 84)
    path.closeSubpath()
    _stroke(p, c, 8)
    p.drawPath(path)
    p.drawLine(QPointF(50, 38), QPointF(50, 62))
    _fill(p, c)
    p.drawEllipse(QPointF(50, 72), 4.5, 4.5)


def _info(p, c):
    _stroke(p, c, 8)
    p.drawEllipse(QRectF(10, 10, 80, 80))
    p.drawLine(QPointF(50, 46), QPointF(50, 72))
    _fill(p, c)
    p.drawEllipse(QPointF(50, 32), 5, 5)


def _error(p, c):
    _stroke(p, c, 8)
    p.drawEllipse(QRectF(10, 10, 80, 80))
    p.drawLine(QPointF(34, 34), QPointF(66, 66))
    p.drawLine(QPointF(66, 34), QPointF(34, 66))


def _forbidden(p, c):
    _stroke(p, c, 8)
    p.drawEllipse(QRectF(10, 10, 80, 80))
    p.drawLine(QPointF(28, 72), QPointF(72, 28))


def _check(p, c):
    _stroke(p, c, 10)
    p.drawPolyline(_poly((18, 54), (40, 74), (84, 26)))


def _check_circle(p, c):
    _stroke(p, c, 8)
    p.drawEllipse(QRectF(10, 10, 80, 80))
    _stroke(p, c, 8)
    p.drawPolyline(_poly((31, 52), (44, 65), (70, 36)))


def _cross(p, c):
    _stroke(p, c, 10)
    p.drawLine(QPointF(24, 24), QPointF(76, 76))
    p.drawLine(QPointF(76, 24), QPointF(24, 76))


def _save(p, c):
    _stroke(p, c, 8)
    path = QPainterPath()
    path.moveTo(18, 14)
    path.lineTo(70, 14)
    path.lineTo(86, 30)
    path.lineTo(86, 86)
    path.lineTo(18, 86)
    path.closeSubpath()
    p.drawPath(path)
    p.drawRect(QRectF(36, 14, 32, 22))
    p.drawRect(QRectF(32, 56, 40, 30))


def _folder(p, c):
    _stroke(p, c, 8)
    path = QPainterPath()
    path.moveTo(12, 78)
    path.lineTo(12, 26)
    path.lineTo(42, 26)
    path.lineTo(52, 38)
    path.lineTo(88, 38)
    path.lineTo(88, 78)
    path.closeSubpath()
    p.drawPath(path)


def _note(p, c):
    _stroke(p, c, 8)
    p.drawRoundedRect(QRectF(20, 12, 60, 76), 8, 8)
    for y in (36, 52, 68):
        p.drawLine(QPointF(34, y), QPointF(66, y))


def _book(p, c):
    _stroke(p, c, 8)
    p.drawLine(QPointF(50, 26), QPointF(50, 84))
    path = QPainterPath()
    path.moveTo(50, 26)
    path.cubicTo(38, 14, 22, 16, 14, 20)
    path.lineTo(14, 76)
    path.cubicTo(24, 72, 40, 74, 50, 84)
    p.drawPath(path)
    path2 = QPainterPath()
    path2.moveTo(50, 26)
    path2.cubicTo(62, 14, 78, 16, 86, 20)
    path2.lineTo(86, 76)
    path2.cubicTo(76, 72, 60, 74, 50, 84)
    p.drawPath(path2)


def _clipboard(p, c):
    _stroke(p, c, 8)
    p.drawRoundedRect(QRectF(22, 20, 56, 70), 8, 8)
    p.drawRoundedRect(QRectF(38, 10, 24, 18), 5, 5)
    for y in (48, 64):
        p.drawLine(QPointF(36, y), QPointF(64, y))


def _pencil(p, c):
    _stroke(p, c, 8)
    path = QPainterPath()
    path.moveTo(22, 78)
    path.lineTo(28, 60)
    path.lineTo(68, 20)
    path.lineTo(82, 34)
    path.lineTo(42, 74)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(60, 28), QPointF(74, 42))


def _scissors(p, c):
    _stroke(p, c, 7)
    p.drawLine(QPointF(26, 20), QPointF(72, 66))
    p.drawLine(QPointF(74, 20), QPointF(28, 66))
    p.drawEllipse(QRectF(16, 64, 22, 22))
    p.drawEllipse(QRectF(62, 64, 22, 22))


def _paperclip(p, c):
    _stroke(p, c, 8)
    path = QPainterPath()
    path.moveTo(66, 30)
    path.lineTo(36, 60)
    path.arcTo(QRectF(22, 46, 28, 28), 90, 180)
    path.lineTo(70, 46)
    path.arcTo(QRectF(56, 18, 28, 28), 270, 180)
    path.lineTo(40, 76)
    p.drawPath(path)


def _gear(p, c):
    _fill(p, c)
    path = QPainterPath()
    n, r1, r2, w = 8, 46.0, 33.0, 0.16
    for i in range(n):
        a0 = (i / n) * 2 * math.pi
        a1 = a0 + w
        a2 = a0 + (1.0 / n) * 2 * math.pi - w
        for (rad, ang) in ((r2, a0 - w), (r1, a1), (r1, a2), (r2, a2 + w)):
            x, y = 50 + rad * math.cos(ang), 50 + rad * math.sin(ang)
            if i == 0 and rad == r2 and ang == a0 - w:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
    path.closeSubpath()
    inner = QPainterPath()
    inner.addEllipse(QRectF(36, 36, 28, 28))
    p.drawPath(path.subtracted(inner))


def _tag(p, c):
    _stroke(p, c, 8)
    path = QPainterPath()
    path.moveTo(52, 12)
    path.lineTo(88, 48)
    path.lineTo(52, 84)
    path.lineTo(16, 48)
    path.lineTo(16, 12)
    path.closeSubpath()
    p.drawPath(path)
    _fill(p, c)
    p.drawEllipse(QPointF(32, 30), 5.5, 5.5)


def _flag(p, c):
    _stroke(p, c, 8)
    p.drawLine(QPointF(26, 12), QPointF(26, 88))
    path = QPainterPath()
    path.moveTo(26, 18)
    path.lineTo(80, 30)
    path.lineTo(26, 54)
    path.closeSubpath()
    p.setBrush(QColor(c))
    p.drawPath(path)


def _bulb(p, c):
    _stroke(p, c, 8)
    path = QPainterPath()
    path.addEllipse(QRectF(26, 12, 48, 48))
    p.drawPath(path)
    p.drawLine(QPointF(40, 62), QPointF(40, 74))
    p.drawLine(QPointF(60, 62), QPointF(60, 74))
    p.drawLine(QPointF(40, 80), QPointF(60, 80))
    p.drawLine(QPointF(44, 88), QPointF(56, 88))


def _pin(p, c):
    _stroke(p, c, 8)
    path = QPainterPath()
    path.moveTo(50, 88)
    path.lineTo(50, 56)
    p.drawPath(path)
    p.setBrush(QColor(c))
    path2 = QPainterPath()
    path2.addEllipse(QRectF(30, 16, 40, 40))
    p.drawPath(path2)


def _cloud(p, c):
    _stroke(p, c, 8)
    path = QPainterPath()
    path.moveTo(26, 72)
    path.arcTo(QRectF(10, 48, 32, 32), 180, -180)
    path.arcTo(QRectF(26, 26, 40, 40), 200, -150)
    path.arcTo(QRectF(58, 44, 34, 34), 90, -180)
    path.closeSubpath()
    p.drawPath(path)


def _broom(p, c):
    _stroke(p, c, 8)
    p.drawLine(QPointF(70, 14), QPointF(44, 48))
    path = QPainterPath()
    path.moveTo(30, 46)
    path.lineTo(58, 62)
    path.lineTo(44, 88)
    path.lineTo(16, 72)
    path.closeSubpath()
    p.drawPath(path)


def _chat(p, c):
    _stroke(p, c, 8)
    path = QPainterPath()
    path.addRoundedRect(QRectF(12, 18, 76, 54), 12, 12)
    p.drawPath(path)
    p.drawPolyline(_poly((34, 72), (34, 88), (52, 72)))


def _palette(p, c):
    _stroke(p, c, 8)
    path = QPainterPath()
    path.moveTo(50, 12)
    path.arcTo(QRectF(8, 12, 84, 76), 90, 300)
    path.lineTo(62, 72)
    path.arcTo(QRectF(56, 60, 24, 24), 270, 180)
    path.closeSubpath()
    p.drawPath(path)
    _fill(p, c)
    for x, y in ((34, 34), (52, 28), (66, 42)):
        p.drawEllipse(QPointF(x, y), 5, 5)


def _link(p, c):
    _stroke(p, c, 8)
    p.drawLine(QPointF(38, 62), QPointF(62, 38))
    path = QPainterPath()
    path.moveTo(44, 26)
    path.lineTo(56, 14)
    path.arcTo(QRectF(56, 2, 36, 36), 135, -180)
    path.lineTo(62, 50)
    p.drawPath(path)
    path2 = QPainterPath()
    path2.moveTo(56, 74)
    path2.lineTo(44, 86)
    path2.arcTo(QRectF(8, 62, 36, 36), 315, -180)
    path2.lineTo(38, 50)
    p.drawPath(path2)


def _graduation(p, c):
    _fill(p, c)
    p.drawPolygon(_poly((50, 20), (92, 40), (50, 60), (8, 40)))
    _stroke(p, c, 7)
    p.drawPolyline(_poly((24, 48), (24, 70)))
    path = QPainterPath()
    path.moveTo(24, 70)
    path.cubicTo(36, 82, 64, 82, 76, 70)
    path.lineTo(76, 48)
    p.drawPath(path)


def _refresh(p, c):
    _stroke(p, c, 8)
    path = QPainterPath()
    path.arcMoveTo(QRectF(16, 16, 68, 68), 60)
    path.arcTo(QRectF(16, 16, 68, 68), 60, 280)
    p.drawPath(path)
    _fill(p, c)
    p.drawPolygon(_poly((78, 10), (92, 34), (64, 32)))


def _undo(p, c, flip=False):
    _stroke(p, c, 8)
    path = QPainterPath()
    path.moveTo(26, 44)
    path.cubicTo(44, 24, 72, 28, 80, 50)
    path.cubicTo(86, 68, 72, 84, 52, 84)
    p.drawPath(path)
    _fill(p, c)
    p.drawPolygon(_poly((16, 32), (40, 34), (24, 56)))
    if flip:
        pass


def _arrow_right(p, c):
    _stroke(p, c, 9)
    p.drawLine(QPointF(16, 50), QPointF(76, 50))
    p.drawPolyline(_poly((56, 30), (78, 50), (56, 70)))


def _printer(p, c):
    _stroke(p, c, 8)
    p.drawRect(QRectF(28, 12, 44, 22))
    path = QPainterPath()
    path.addRoundedRect(QRectF(12, 34, 76, 34), 7, 7)
    p.drawPath(path)
    p.drawRect(QRectF(28, 62, 44, 26))


def _mail(p, c):
    _stroke(p, c, 8)
    p.drawRoundedRect(QRectF(10, 24, 80, 52), 8, 8)
    p.drawPolyline(_poly((14, 30), (50, 56), (86, 30)))


def _search(p, c):
    _stroke(p, c, 8)
    p.drawEllipse(QRectF(16, 16, 50, 50))
    p.drawLine(QPointF(62, 62), QPointF(86, 86))


def _plus(p, c):
    _stroke(p, c, 10)
    p.drawLine(QPointF(50, 20), QPointF(50, 80))
    p.drawLine(QPointF(20, 50), QPointF(80, 50))


def _trash(p, c):
    _stroke(p, c, 8)
    p.drawLine(QPointF(14, 28), QPointF(86, 28))
    p.drawLine(QPointF(40, 16), QPointF(60, 16))
    path = QPainterPath()
    path.moveTo(24, 28)
    path.lineTo(30, 88)
    path.lineTo(70, 88)
    path.lineTo(76, 28)
    p.drawPath(path)
    p.drawLine(QPointF(42, 44), QPointF(44, 74))
    p.drawLine(QPointF(58, 44), QPointF(56, 74))


def _download(p, c, up=False):
    _stroke(p, c, 8)
    if up:
        p.drawLine(QPointF(50, 76), QPointF(50, 20))
        p.drawPolyline(_poly((30, 40), (50, 18), (70, 40)))
    else:
        p.drawLine(QPointF(50, 16), QPointF(50, 68))
        p.drawPolyline(_poly((30, 48), (50, 70), (70, 48)))
    p.drawPolyline(_poly((16, 84), (16, 90), (84, 90), (84, 84)))


def _calendar(p, c):
    _stroke(p, c, 8)
    p.drawRoundedRect(QRectF(12, 22, 76, 66), 8, 8)
    p.drawLine(QPointF(12, 42), QPointF(88, 42))
    p.drawLine(QPointF(32, 12), QPointF(32, 28))
    p.drawLine(QPointF(68, 12), QPointF(68, 28))


def _clock(p, c):
    _stroke(p, c, 8)
    p.drawEllipse(QRectF(12, 12, 76, 76))
    p.drawPolyline(_poly((50, 30), (50, 52), (68, 62)))


def _user(p, c, many=False):
    _fill(p, c)
    if many:
        p.drawEllipse(QPointF(36, 34), 16, 16)
        path = QPainterPath()
        path.moveTo(8, 84)
        path.cubicTo(8, 56, 64, 56, 64, 84)
        p.drawPath(path)
        _stroke(p, c, 7)
        path2 = QPainterPath()
        path2.arcMoveTo(QRectF(52, 20, 28, 28), 300)
        path2.arcTo(QRectF(52, 20, 28, 28), 300, 130)
        p.drawPath(path2)
        path3 = QPainterPath()
        path3.moveTo(72, 84)
        path3.cubicTo(72, 62, 94, 62, 94, 84)
        p.drawPath(path3)
    else:
        p.drawEllipse(QPointF(50, 32), 18, 18)
        path = QPainterPath()
        path.moveTo(16, 88)
        path.cubicTo(16, 56, 84, 56, 84, 88)
        p.drawPath(path)


def _grid(p, c):
    _fill(p, c)
    for x in (16, 54):
        for y in (16, 54):
            p.drawRoundedRect(QRectF(x, y, 30, 30), 5, 5)


def _rules(p, c):
    _stroke(p, c, 8)
    p.drawRoundedRect(QRectF(14, 14, 72, 72), 10, 10)
    p.drawLine(QPointF(30, 38), QPointF(70, 38))
    p.drawLine(QPointF(30, 54), QPointF(70, 54))
    p.drawLine(QPointF(30, 70), QPointF(54, 70))


def _sparkle(p, c):
    _fill(p, c)
    def star(cx, cy, r, k):
        path = QPainterPath(QPointF(cx, cy - r))
        path.quadTo(cx + k, cy - k, cx + r, cy)
        path.quadTo(cx + k, cy + k, cx, cy + r)
        path.quadTo(cx - k, cy + k, cx - r, cy)
        path.quadTo(cx - k, cy - k, cx, cy - r)
        p.drawPath(path)
    star(44, 56, 34, 6)
    star(76, 24, 16, 3)


def _sun(p, c):
    _stroke(p, c, 8)
    p.drawEllipse(QRectF(32, 32, 36, 36))
    for i in range(8):
        a = i * math.pi / 4
        p.drawLine(QPointF(50 + 26 * math.cos(a), 50 + 26 * math.sin(a)),
                   QPointF(50 + 40 * math.cos(a), 50 + 40 * math.sin(a)))


def _moon(p, c):
    _fill(p, c)
    outer = QPainterPath()
    outer.addEllipse(QRectF(16, 16, 68, 68))
    inner = QPainterPath()
    inner.addEllipse(QRectF(36, 6, 64, 64))
    p.drawPath(outer.subtracted(inner))


def _building(p, c):
    _stroke(p, c, 8)
    p.drawRect(QRectF(16, 24, 44, 64))
    p.drawRect(QRectF(60, 44, 26, 44))
    _fill(p, c)
    for y in (38, 54, 70):
        for x in (26, 42):
            p.drawRect(QRectF(x, y, 8, 8))


def _party(p, c):
    _stroke(p, c, 8)
    path = QPainterPath()
    path.moveTo(16, 88)
    path.lineTo(52, 30)
    path.lineTo(84, 62)
    path.closeSubpath()
    p.drawPath(path)
    _fill(p, c)
    for x, y in ((74, 22), (86, 40), (60, 14)):
        p.drawEllipse(QPointF(x, y), 4.5, 4.5)


DRAW = {
    "lock": lambda p, c: _lock(p, c, True),
    "unlock": lambda p, c: _lock(p, c, False),
    "warning": _warning,
    "info": _info,
    "error": _error,
    "forbidden": _forbidden,
    "check": _check,
    "check_circle": _check_circle,
    "cross": _cross,
    "save": _save,
    "folder": _folder,
    "note": _note,
    "book": _book,
    "clipboard": _clipboard,
    "pencil": _pencil,
    "scissors": _scissors,
    "paperclip": _paperclip,
    "gear": _gear,
    "tag": _tag,
    "flag": _flag,
    "bulb": _bulb,
    "pin": _pin,
    "cloud": _cloud,
    "broom": _broom,
    "chat": _chat,
    "palette": _palette,
    "link": _link,
    "graduation": _graduation,
    "refresh": _refresh,
    "undo": _undo,
    "arrow_right": _arrow_right,
    "printer": _printer,
    "mail": _mail,
    "search": _search,
    "plus": _plus,
    "trash": _trash,
    "download": _download,
    "upload": lambda p, c: _download(p, c, up=True),
    "calendar": _calendar,
    "clock": _clock,
    "user": _user,
    "users": lambda p, c: _user(p, c, many=True),
    "grid": _grid,
    "rules": _rules,
    "sparkle": _sparkle,
    "sun": _sun,
    "moon": _moon,
    "building": _building,
    "party": _party,
}


def pixmap(name: str, size: int = 16, color: str = DEFAULT_COLOR, dpr: float = 2.0) -> QPixmap:
    """Tek renkli, retina keskinliğinde ikon haritası."""
    key = (name, int(size), str(color), float(dpr))
    hit = _CACHE.get(key)
    if hit is not None:
        return hit
    px = QPixmap(int(size * dpr), int(size * dpr))
    px.setDevicePixelRatio(dpr)
    px.fill(Qt.transparent)
    fn = DRAW.get(name)
    if fn is not None:
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        # QPainter pixmap'in devicePixelRatio'sunu kendisi uygular; ölçek
        # MANTIKSAL boyuta göre verilir. dpr ile çarpmak çift ölçekleme
        # yapıyor ve ikonun yalnızca sol üst çeyreği görünüyordu.
        p.scale(size / 100.0, size / 100.0)
        try:
            fn(p, color)
        finally:
            p.end()
    _CACHE[key] = px
    return px


def icon(name: str, size: int = 16, color: str = DEFAULT_COLOR) -> QIcon:
    return QIcon(pixmap(name, size, color))


def names():
    return sorted(DRAW)


# Emoji → ikon adı. Metinden emoji silinirken yerine hangi ikonun konacağını
# tek yerden okumak için; dönüşüm betiği ve arayüz kodu aynı eşlemeyi kullanır.
EMOJI_MAP = {
    "🔒": "lock", "🔓": "unlock", "⚠": "warning", "⚠️": "warning",
    "ℹ": "info", "ℹ️": "info", "⛔": "forbidden", "❌": "error", "✖": "cross",
    "✅": "check_circle", "✔": "check", "✔️": "check", "✓": "check", "✕": "cross", "✗": "cross",
    "💾": "save", "📁": "folder", "📂": "folder", "📝": "note", "📚": "book",
    "📋": "clipboard", "✏": "pencil", "✏️": "pencil", "✂": "scissors", "✂️": "scissors",
    "📎": "paperclip", "⚙": "gear", "⚙️": "gear", "🏷": "tag", "🏷️": "tag",
    "⚑": "flag", "🚩": "flag", "💡": "bulb", "📌": "pin", "☁": "cloud", "☁️": "cloud",
    "🧹": "broom", "💬": "chat", "🎨": "palette", "🔗": "link", "🎓": "graduation",
    "🔄": "refresh", "↺": "undo", "↻": "refresh", "🖨": "printer", "🖨️": "printer",
    "📧": "mail", "✉": "mail", "✉️": "mail", "🔍": "search", "🔎": "search",
    "➕": "plus", "🗑": "trash", "🗑️": "trash", "⬇": "download", "⬆": "upload",
    "📅": "calendar", "🕐": "clock", "⏰": "clock", "👤": "user", "👥": "users",
    "🏢": "building", "🎉": "party", "🌅": "sun", "🌇": "moon", "✨": "sparkle",
    "🤖": "sparkle", "📊": "grid", "📈": "grid", "🔔": "info", "🚀": "sparkle",
}
