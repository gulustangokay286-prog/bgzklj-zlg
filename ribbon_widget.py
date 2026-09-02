"""
ribbon_widget.py  –  Pixel-perfect Ribbon toolbar
Birebir aSc Ders Dağıtım / aSc Timetables ikon seti ve ribbon görünümü.
Retina 2x Vektörel Çizim Motoru ile kristal netliğinde 3D ikonlar.
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QSizePolicy, QFrame, QCheckBox, QToolButton, QScrollArea
)
from PySide6.QtCore import Qt, QSize, Signal, QPoint, QPointF, QRectF
from PySide6.QtGui import (
    QIcon, QPixmap, QColor, QPainter, QPen, QFont, QBrush,
    QPolygon, QPolygonF, QLinearGradient, QRadialGradient, QPainterPath
)


# ── Colours from screenshots ──────────────────────────────────────────────────
RIBBON_BG        = "#FFFFFF"
RIBBON_BORDER    = "#D0D0D0"
TAB_ACTIVE_BG    = "#FFFFFF"
TAB_INACTIVE_BG  = "#F0F0F0"
TAB_ACTIVE_LINE  = "#1E6DB5"
TAB_TEXT         = "#333333"
TAB_ACTIVE_TEXT  = "#1E6DB5"
BTN_HOVER_BG     = "#DAE8FC"
BTN_PRESSED_BG   = "#B8D4F0"
GROUP_DIVIDER    = "#CCCCCC"
BACK_BTN_BG      = "#1E6DB5"

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"


# ── Retina 2x Icon Painter Helper ──────────────────────────────────────────────
def _make_pixmap(size: int, draw_fn) -> QPixmap:
    scale = 2
    px = QPixmap(size * scale, size * scale)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(scale, scale)
    draw_fn(p, size)
    p.end()
    px.setDevicePixelRatio(scale)
    return px


# ── aSc Timetables Vector Icons ────────────────────────────────────────────────

def icon_new(p: QPainter, s: int):
    """1. Yeni Dosya: Beyaz kıvrımlı sayfa ve sağ altta yeşil dairesel '+' rozeti"""
    # White page base
    p.setPen(QPen(QColor("#94A3B8"), 1.2))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    
    # Page with folded corner
    path = QPainterPath()
    path.moveTo(5, 3)
    path.lineTo(19, 3)
    path.lineTo(25, 9)
    path.lineTo(25, 27)
    path.lineTo(5, 27)
    path.closeSubpath()
    p.drawPath(path)
    
    # Fold corner
    fold = QPainterPath()
    fold.moveTo(19, 3)
    fold.lineTo(19, 9)
    fold.lineTo(25, 9)
    fold.closeSubpath()
    p.setBrush(QBrush(QColor("#E2E8F0")))
    p.drawPath(fold)
    
    # Content lines on page
    p.setPen(QPen(QColor("#CBD5E1"), 1.5))
    p.drawLine(8, 12, 17, 12)
    p.drawLine(8, 16, 17, 16)
    p.drawLine(8, 20, 14, 20)
    
    # Green Plus Circle Badge at bottom right
    p.setPen(QPen(QColor("#FFFFFF"), 1.5))
    grad = QLinearGradient(16, 16, 28, 28)
    grad.setColorAt(0, QColor("#34D399"))
    grad.setColorAt(1, QColor("#059669"))
    p.setBrush(QBrush(grad))
    p.drawEllipse(15, 15, 13, 13)
    
    # Plus sign
    p.setPen(QPen(QColor("#FFFFFF"), 2, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(21.5, 18.5, 21.5, 24.5)
    p.drawLine(18.5, 21.5, 24.5, 21.5)


def icon_open(p: QPainter, s: int):
    """2. Aç: 3D Altın Sarısı Açık Klasör"""
    # Back folder body
    p.setPen(QPen(QColor("#B45309"), 1))
    grad_back = QLinearGradient(3, 4, 3, 26)
    grad_back.setColorAt(0, QColor("#FBBF24"))
    grad_back.setColorAt(1, QColor("#D97706"))
    p.setBrush(QBrush(grad_back))
    
    back_path = QPainterPath()
    back_path.moveTo(3, 8)
    back_path.lineTo(3, 5)
    back_path.lineTo(12, 5)
    back_path.lineTo(15, 8)
    back_path.lineTo(28, 8)
    back_path.lineTo(28, 24)
    back_path.lineTo(3, 24)
    back_path.closeSubpath()
    p.drawPath(back_path)
    
    # Inner white paper sheet sticking out
    p.setPen(QPen(QColor("#CBD5E1"), 1))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(6, 8, 19, 13, 1.5, 1.5)
    p.setPen(QPen(QColor("#94A3B8"), 1))
    p.drawLine(9, 12, 21, 12)
    p.drawLine(9, 15, 18, 15)
    
    # Front open flap (angled 3D perspective)
    grad_front = QLinearGradient(2, 13, 28, 27)
    grad_front.setColorAt(0, QColor("#FDE047"))
    grad_front.setColorAt(1, QColor("#F59E0B"))
    p.setBrush(QBrush(grad_front))
    p.setPen(QPen(QColor("#B45309"), 1))
    
    front_poly = QPolygonF([
        QPointF(2, 14),
        QPointF(26, 14),
        QPointF(23, 27),
        QPointF(4, 27)
    ])
    p.drawPolygon(front_poly)


def icon_save(p: QPainter, s: int):
    """3. Kaydet: Klasik Mor/Lavanta 3.5 inç Disket"""
    # Floppy disk main body (purple/lavender)
    p.setPen(QPen(QColor("#6D28D9"), 1))
    grad = QLinearGradient(3, 3, 29, 29)
    grad.setColorAt(0, QColor("#C4B5FD"))
    grad.setColorAt(1, QColor("#8B5CF6"))
    p.setBrush(QBrush(grad))
    
    disk_path = QPainterPath()
    disk_path.moveTo(3, 3)
    disk_path.lineTo(25, 3)
    disk_path.lineTo(29, 7)
    disk_path.lineTo(29, 29)
    disk_path.lineTo(3, 29)
    disk_path.closeSubpath()
    p.drawPath(disk_path)
    
    # Top metal shutter
    p.setPen(QPen(QColor("#94A3B8"), 1))
    shutter_grad = QLinearGradient(7, 3, 23, 13)
    shutter_grad.setColorAt(0, QColor("#F8FAFC"))
    shutter_grad.setColorAt(1, QColor("#CBD5E1"))
    p.setBrush(QBrush(shutter_grad))
    p.drawRoundedRect(7, 3, 16, 10, 1.5, 1.5)
    
    # Metal slider notch
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#475569")))
    p.drawRect(18, 5, 3, 6)
    
    # Bottom white paper label
    p.setPen(QPen(QColor("#94A3B8"), 0.8))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(6, 15, 20, 14, 1.5, 1.5)
    
    # Blue stripe on label
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#0284C7")))
    p.drawRect(8, 17, 16, 2.5)
    
    # Pencil lines on label
    p.setPen(QPen(QColor("#94A3B8"), 1))
    p.drawLine(8, 22, 22, 22)
    p.drawLine(8, 25, 18, 25)


def icon_print(p: QPainter, s: int):
    """4. Yazdır: Açık Mavi & Beyaz Masaüstü Yazıcı"""
    # Top feed paper
    p.setPen(QPen(QColor("#94A3B8"), 1))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(8, 3, 16, 9, 1, 1)
    p.setPen(QPen(QColor("#CBD5E1"), 1))
    p.drawLine(10, 6, 22, 6)
    p.drawLine(10, 8, 19, 8)
    
    # Printer main housing
    p.setPen(QPen(QColor("#2563EB"), 1))
    grad = QLinearGradient(3, 10, 29, 23)
    grad.setColorAt(0, QColor("#93C5FD"))
    grad.setColorAt(1, QColor("#3B82F6"))
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(3, 10, 26, 13, 3, 3)
    
    # Output tray slot
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#1E3A8A")))
    p.drawRoundedRect(6, 16, 20, 4, 1, 1)
    
    # Emerging output paper
    p.setPen(QPen(QColor("#94A3B8"), 1))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(7, 18, 18, 9, 1, 1)
    p.setPen(QPen(QColor("#0284C7"), 1))
    p.drawLine(9, 21, 23, 21)
    p.drawLine(9, 23, 20, 23)
    
    # Power LED button
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#34D399")))
    p.drawEllipse(24, 12, 3, 3)


def icon_preview(p: QPainter, s: int):
    """5. Baskı Önizleme: Büyüteçli Doküman"""
    # Background document
    p.setPen(QPen(QColor("#94A3B8"), 1))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(4, 3, 17, 25, 2, 2)
    
    # Document content lines
    p.setPen(QPen(QColor("#CBD5E1"), 1.2))
    p.drawLine(7, 7, 17, 7)
    p.drawLine(7, 10, 16, 10)
    p.drawLine(7, 13, 18, 13)
    p.drawLine(7, 16, 15, 16)
    p.drawLine(7, 19, 14, 19)
    p.drawLine(7, 22, 17, 22)
    
    # Magnifying glass handle
    p.setPen(QPen(QColor("#0369A1"), 3.5, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(21, 21, 28, 28)
    
    # Magnifying glass lens rim
    p.setPen(QPen(QColor("#0284C7"), 2.2))
    p.setBrush(QBrush(QColor(56, 189, 248, 100)))
    p.drawEllipse(12, 8, 13, 13)
    
    # Lens reflection glint
    p.setPen(QPen(QColor("#FFFFFF"), 1.2, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(14, 10, 9, 9, 45 * 16, 90 * 16)


def icon_undo(p: QPainter, s: int):
    """Geri Al (Ctrl+Z): Mavi kıvrımlı geri oku"""
    p.setPen(QPen(QColor("#0284C7"), 2.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.moveTo(24, 23)
    path.cubicTo(24, 11, 14, 9, 8, 13)
    p.drawPath(path)
    # Arrow head
    p.drawLine(8, 13, 13, 9)
    p.drawLine(8, 13, 12, 18)


def icon_redo(p: QPainter, s: int):
    """Yinele (Ctrl+Y): Mavi kıvrımlı ileri oku"""
    p.setPen(QPen(QColor("#0284C7"), 2.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.moveTo(8, 23)
    path.cubicTo(8, 11, 18, 9, 24, 13)
    p.drawPath(path)
    # Arrow head
    p.drawLine(24, 13, 19, 9)
    p.drawLine(24, 13, 20, 18)


def icon_subjects(p: QPainter, s: int):
    """7. Dersler: Yüksek Çözünürlüklü 3D Mavi Ciltli Ders Kitabı"""
    p.setRenderHint(QPainter.Antialiasing, True)
    
    # White page block on right & top
    p.setPen(QPen(QColor("#CBD5E1"), 0.8))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRect(9, 4, 18, 24)
    
    # Page edge lines
    p.setPen(QPen(QColor("#E2E8F0"), 0.8))
    p.drawLine(25, 6, 25, 27)
    p.drawLine(23, 6, 23, 27)
    
    # Front Blue Hardcover
    grad = QLinearGradient(6, 3, 24, 29)
    grad.setColorAt(0, QColor("#60A5FA"))
    grad.setColorAt(0.5, QColor("#2563EB"))
    grad.setColorAt(1, QColor("#1D4ED8"))
    p.setPen(QPen(QColor("#1E40AF"), 1.2))
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(6, 3, 19, 26, 2.5, 2.5)
    
    # Dark blue spine trim on the left
    p.setPen(QPen(QColor("#1E3A8A"), 1))
    p.setBrush(QBrush(QColor("#1E40AF")))
    p.drawRoundedRect(6, 3, 4.5, 26, 2, 2)
    
    # White label badge on front cover
    p.setPen(QPen(QColor("#93C5FD"), 0.8))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(12, 8, 10, 14, 1.5, 1.5)
    
    # Ruled lines on label
    p.setPen(QPen(QColor("#3B82F6"), 1))
    p.drawLine(14, 11, 20, 11)
    p.drawLine(14, 14, 20, 14)
    p.drawLine(14, 17, 18, 17)


def icon_classes(p: QPainter, s: int):
    """8. Sınıflar: Modern 3D Öğrenci Grubu / Sınıf Kohortu (Pembe, Zümrüt Yeşili ve Gök Mavisi Öğrenciler)"""
    p.setRenderHint(QPainter.Antialiasing, True)
    
    # ── 1. Left Student (Girl in Coral/Pink) ──
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#92400E")))
    p.drawEllipse(2, 6, 11, 11)  # Hair
    p.setBrush(QBrush(QColor("#FDE68A")))
    p.drawEllipse(3, 8, 9, 9)    # Face
    
    grad_l = QLinearGradient(1, 17, 13, 27)
    grad_l.setColorAt(0, QColor("#FB7185"))
    grad_l.setColorAt(1, QColor("#E11D48"))
    p.setBrush(QBrush(grad_l))
    path_l = QPainterPath()
    path_l.moveTo(1, 27)
    path_l.lineTo(1, 19)
    path_l.cubicTo(1, 15, 13, 15, 13, 19)
    path_l.lineTo(13, 27)
    path_l.closeSubpath()
    p.drawPath(path_l)
    
    # ── 2. Right Student (Sky Blue Polo) ──
    p.setBrush(QBrush(QColor("#334155")))
    p.drawEllipse(19, 6, 11, 11)  # Hair
    p.setBrush(QBrush(QColor("#FDE68A")))
    p.drawEllipse(20, 8, 9, 9)    # Face
    
    grad_r = QLinearGradient(19, 17, 31, 27)
    grad_r.setColorAt(0, QColor("#38BDF8"))
    grad_r.setColorAt(1, QColor("#0284C7"))
    p.setBrush(QBrush(grad_r))
    path_r = QPainterPath()
    path_r.moveTo(19, 27)
    path_r.lineTo(19, 19)
    path_r.cubicTo(19, 15, 31, 15, 31, 19)
    path_r.lineTo(31, 27)
    path_r.closeSubpath()
    p.drawPath(path_r)
    
    # ── 3. Center Front Student (Emerald Green - Main Focus) ──
    grad_c = QLinearGradient(8, 15, 24, 29)
    grad_c.setColorAt(0, QColor("#34D399"))
    grad_c.setColorAt(1, QColor("#059669"))
    p.setBrush(QBrush(grad_c))
    path_c = QPainterPath()
    path_c.moveTo(7, 29)
    path_c.lineTo(7, 18)
    path_c.cubicTo(7, 13, 25, 13, 25, 18)
    path_c.lineTo(25, 29)
    path_c.closeSubpath()
    p.drawPath(path_c)
    
    # White V-collar
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.setPen(QPen(QColor("#047857"), 0.8))
    p.drawPolygon([QPoint(13, 17), QPoint(16, 22), QPoint(19, 17), QPoint(16, 18)])
    
    # Face
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#FEF08A")))
    p.drawEllipse(10, 5, 12, 12)
    
    # Cheek blush
    p.setBrush(QBrush(QColor(244, 63, 94, 60)))
    p.drawEllipse(11, 11, 2.5, 1.8)
    p.drawEllipse(18, 11, 2.5, 1.8)
    
    # Golden styled hair
    p.setBrush(QBrush(QColor("#F59E0B")))
    path_ch = QPainterPath()
    path_ch.moveTo(9, 9)
    path_ch.cubicTo(9, 2, 23, 2, 23, 9)
    path_ch.cubicTo(20, 5, 13, 5, 9, 9)
    path_ch.closeSubpath()
    p.drawPath(path_ch)
    
    # Hair highlight
    p.setBrush(QBrush(QColor("#FDE047")))
    p.drawEllipse(13, 3.5, 6, 2.5)


def icon_rooms(p: QPainter, s: int):
    """9. Derslikler: 3D Açık Sınıf Kapısı (Ahşap Açık Kapı & Kasa)"""
    p.setRenderHint(QPainter.Antialiasing, True)
    
    # Outer Door Frame (Light Sand Wood)
    p.setPen(QPen(QColor("#92400E"), 1.2))
    p.setBrush(QBrush(QColor("#FDE68A")))
    p.drawRect(5, 4, 22, 25)
    
    # Dark Open Room Interior (Void)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#1E293B")))
    p.drawRect(8, 7, 16, 22)
    
    # Open Wooden Door Leaf (Swung open into room in 3D perspective)
    grad_door = QLinearGradient(8, 7, 26, 29)
    grad_door.setColorAt(0, QColor("#FBBF24"))
    grad_door.setColorAt(1, QColor("#D97706"))
    p.setBrush(QBrush(grad_door))
    p.setPen(QPen(QColor("#92400E"), 1.2))
    
    door_poly = QPolygon([
        QPoint(8, 7),
        QPoint(26, 3),
        QPoint(26, 29),
        QPoint(8, 27)
    ])
    p.drawPolygon(door_poly)
    
    # Door panel bevels
    p.setPen(QPen(QColor("#92400E"), 0.8))
    p.drawLine(12, 8, 22, 6)
    p.drawLine(22, 6, 22, 26)
    p.drawLine(22, 26, 12, 26)
    p.drawLine(12, 26, 12, 8)
    
    # Gold Door Handle / Knob
    p.setPen(QPen(QColor("#78350F"), 0.8))
    p.setBrush(QBrush(QColor("#FEF08A")))
    p.drawEllipse(22, 16, 3, 3)


def icon_teachers(p: QPainter, s: int):
    """10. Öğretmenler: 3D Akademik Mezuniyet Kepi (Büyük ve Net)"""
    p.setRenderHint(QPainter.Antialiasing, True)
    p.save()
    p.translate(0, 1.5)
    
    # Cap skull base underneath (large)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#0F172A")))
    p.drawRoundedRect(QRectF(8, 13, 16, 12), 2, 2)
    
    # Inner skull volume shadow
    p.setBrush(QBrush(QColor("#1E293B")))
    p.drawRect(QRectF(10, 15, 12, 9))
    
    # Diamond Cap Top (Mortarboard) - Full width
    hat_poly = QPolygonF([
        QPointF(16, 2),
        QPointF(30, 9),
        QPointF(16, 16),
        QPointF(2, 9)
    ])
    grad_hat = QLinearGradient(2, 2, 30, 16)
    grad_hat.setColorAt(0, QColor("#475569"))
    grad_hat.setColorAt(1, QColor("#0F172A"))
    p.setPen(QPen(QColor("#64748B"), 1.2))
    p.setBrush(QBrush(grad_hat))
    p.drawPolygon(hat_poly)
    
    # Golden Button at center of mortarboard
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#F59E0B")))
    p.drawEllipse(QRectF(14, 7.5, 4, 4))
    
    # Golden Tassel Ribbon hanging left
    p.setPen(QPen(QColor("#F59E0B"), 1.8, Qt.SolidLine, Qt.RoundCap))
    tassel_path = QPainterPath()
    tassel_path.moveTo(16, 9)
    tassel_path.cubicTo(9, 10, 5, 14, 4, 19)
    p.drawPath(tassel_path)
    
    # Golden Tassel Brush
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#F59E0B")))
    p.drawRoundedRect(QRectF(2, 19, 3.5, 7), 1, 1)
    p.restore()


def icon_electives(p: QPainter, s: int):
    """11. Seçmeli Dersler / Öğrenciler: Öğrenci ve Mavi Onay Rozeti"""
    # Student Bust (Head)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#92400E")))
    p.drawEllipse(7, 4, 12, 12)  # Hair
    p.setBrush(QBrush(QColor("#FDE68A")))
    p.drawEllipse(8, 7, 10, 10)  # Face
    
    # Shirt (Green / Teal)
    p.setBrush(QBrush(QColor("#10B981")))
    body = QPainterPath()
    body.moveTo(3, 27)
    body.lineTo(3, 21)
    body.cubicTo(3, 17, 18, 17, 18, 21)
    body.lineTo(18, 27)
    body.closeSubpath()
    p.drawPath(body)
    
    # Blue Checkmark Badge at bottom right
    p.setPen(QPen(QColor("#FFFFFF"), 1.2))
    grad_b = QLinearGradient(16, 15, 29, 28)
    grad_b.setColorAt(0, QColor("#60A5FA"))
    grad_b.setColorAt(1, QColor("#2563EB"))
    p.setBrush(QBrush(grad_b))
    p.drawRoundedRect(16, 15, 13, 13, 3, 3)
    
    # White checkmark in badge
    p.setPen(QPen(QColor("#FFFFFF"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawLine(19, 21.5, 21.5, 24.5)
    p.drawLine(21.5, 24.5, 26, 18.5)


def icon_relations(p: QPainter, s: int):
    """12. İlişkiler: Bağlantılı Molekül Grafı (Renkli Düğümler & Çubuklar)"""
    # Connecting silver rods
    p.setPen(QPen(QColor("#94A3B8"), 2.2, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(8, 8, 24, 8)
    p.drawLine(8, 8, 16, 16)
    p.drawLine(24, 8, 16, 16)
    p.drawLine(16, 16, 8, 24)
    p.drawLine(16, 16, 24, 24)
    p.drawLine(8, 24, 24, 24)
    
    # Helper to draw a 3D sphere node
    def _draw_node(cx, cy, r, c1, c2):
        grad = QRadialGradient(cx - r*0.3, cy - r*0.3, r * 1.3)
        grad.setColorAt(0, QColor(c1))
        grad.setColorAt(1, QColor(c2))
        p.setPen(QPen(QColor(0, 0, 0, 40), 0.8))
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), r, r)
        
    _draw_node(8, 8, 4.5, "#93C5FD", "#2563EB")     # Top Left (Blue)
    _draw_node(24, 8, 4.5, "#FDA4AF", "#E11D48")    # Top Right (Pink)
    _draw_node(16, 16, 5.5, "#6EE7B7", "#059669")   # Center (Green)
    _draw_node(8, 24, 4.5, "#67E8F9", "#0891B2")    # Bottom Left (Cyan)
    _draw_node(24, 24, 4.5, "#FDE047", "#D97706")   # Bottom Right (Amber)


def icon_check_badge(p: QPainter, s: int):
    """13. Doğrula / Kontrol: Yeşil Daire Rozet ve Beyaz Onay İşareti"""
    p.setPen(QPen(QColor("#059669"), 1.2))
    grad = QLinearGradient(3, 3, 29, 29)
    grad.setColorAt(0, QColor("#6EE7B7"))
    grad.setColorAt(1, QColor("#059669"))
    p.setBrush(QBrush(grad))
    p.drawEllipse(QRectF(3, 3, 26, 26))
    
    # Inner white circle border
    p.setPen(QPen(QColor(255, 255, 255, 140), 1))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(5, 5, 22, 22))
    
    # Crisp white checkmark
    p.setPen(QPen(QColor("#FFFFFF"), 2.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawLine(QPointF(9, 16), QPointF(14, 21))
    p.drawLine(QPointF(14, 21), QPointF(23, 11))


def icon_auto(p: QPainter, s: int):
    """14. Otomatik Planla: Kırmızı Parlayan Tepe Sireni / Feneri"""
    # Metal base
    p.setPen(QPen(QColor("#64748B"), 1))
    grad_base = QLinearGradient(5, 22, 27, 28)
    grad_base.setColorAt(0, QColor("#F1F5F9"))
    grad_base.setColorAt(1, QColor("#94A3B8"))
    p.setBrush(QBrush(grad_base))
    p.drawRoundedRect(5, 22, 22, 6, 2, 2)
    
    # Translucent Red Beacon Glass Dome
    grad_dome = QLinearGradient(7, 5, 25, 22)
    grad_dome.setColorAt(0, QColor("#F87171"))
    grad_dome.setColorAt(1, QColor("#DC2626"))
    p.setPen(QPen(QColor("#991B1B"), 1))
    p.setBrush(QBrush(grad_dome))
    
    dome = QPainterPath()
    dome.moveTo(7, 22)
    dome.lineTo(9, 9)
    dome.cubicTo(10, 5, 22, 5, 23, 9)
    dome.lineTo(25, 22)
    dome.closeSubpath()
    p.drawPath(dome)
    
    # Glowing central bulb
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#FEF08A")))
    p.drawEllipse(13, 12, 6, 6)
    
    # Specular glass reflection line
    p.setPen(QPen(QColor(255, 255, 255, 180), 1.5, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(10, 9, 9, 19)


def icon_cloud_auto(p: QPainter, s: int):
    """15. Bulutta Oluştur: Kırmızı Siren ve Bulut Rozeti"""
    # Red Siren (Slightly left)
    p.setPen(QPen(QColor("#64748B"), 1))
    p.setBrush(QBrush(QColor("#CBD5E1")))
    p.drawRoundedRect(3, 22, 18, 5, 2, 2)
    
    # Red Dome
    grad_dome = QLinearGradient(5, 5, 20, 22)
    grad_dome.setColorAt(0, QColor("#F87171"))
    grad_dome.setColorAt(1, QColor("#DC2626"))
    p.setPen(QPen(QColor("#991B1B"), 1))
    p.setBrush(QBrush(grad_dome))
    dome = QPainterPath()
    dome.moveTo(5, 22)
    dome.lineTo(7, 9)
    dome.cubicTo(8, 5, 17, 5, 18, 9)
    dome.lineTo(19, 22)
    dome.closeSubpath()
    p.drawPath(dome)
    
    # Cloud at bottom right
    p.setPen(QPen(QColor("#0284C7"), 1.2))
    p.setBrush(QBrush(QColor("#F0F9FF")))
    c_path = QPainterPath()
    c_path.addEllipse(15, 16, 7, 7)
    c_path.addEllipse(19, 13, 8, 8)
    c_path.addEllipse(24, 16, 6, 6)
    c_path.addRect(17, 18, 11, 6)
    p.drawPath(c_path)


def icon_gavel(p: QPainter, s: int):
    """16. Gelişmiş Kısıtlamalar: Ahşap Adalet / Şart Tokmağı (Gavel)"""
    # Sound block at bottom
    p.setPen(QPen(QColor("#78350F"), 1))
    grad_b = QLinearGradient(6, 23, 26, 28)
    grad_b.setColorAt(0, QColor("#D97706"))
    grad_b.setColorAt(1, QColor("#92400E"))
    p.setBrush(QBrush(grad_b))
    p.drawRoundedRect(6, 23, 20, 5, 2, 2)
    
    # Gavel Handle (Diagonal)
    p.setPen(QPen(QColor("#B45309"), 3, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(14, 14, 27, 25)
    
    # Gavel Mallet Head (Angled Cylinder)
    p.save()
    p.translate(12, 12)
    p.rotate(-35)
    p.setPen(QPen(QColor("#78350F"), 1))
    grad_m = QLinearGradient(-8, -5, 8, 5)
    grad_m.setColorAt(0, QColor("#F59E0B"))
    grad_m.setColorAt(1, QColor("#B45309"))
    p.setBrush(QBrush(grad_m))
    p.drawRoundedRect(-9, -5, 18, 10, 2.5, 2.5)
    
    # Gold decorative rings
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#FDE047")))
    p.drawRect(-3, -5, 2, 10)
    p.drawRect(1, -5, 2, 10)
    p.restore()


def icon_school_info(p: QPainter, s: int):
    """17. Okul Bilgileri: Klasik Akademik Kurum / Tapınak Binası (Pantheon)"""
    # Roof (Triangular Pediment)
    p.setPen(QPen(QColor("#0284C7"), 1))
    grad_roof = QLinearGradient(3, 4, 29, 12)
    grad_roof.setColorAt(0, QColor("#93C5FD"))
    grad_roof.setColorAt(1, QColor("#2563EB"))
    p.setBrush(QBrush(grad_roof))
    
    roof = QPolygonF([
        QPointF(16, 4),
        QPointF(29, 11),
        QPointF(3, 11)
    ])
    p.drawPolygon(roof)
    
    # Roof Base Beam
    p.setPen(QPen(QColor("#1D4ED8"), 0.8))
    p.setBrush(QBrush(QColor("#DBEAFE")))
    p.drawRect(4, 11, 24, 2.5)
    
    # 4 Classical Columns
    p.setPen(QPen(QColor("#0284C7"), 1))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    for x in [5.5, 11.5, 17.5, 23.5]:
        p.drawRect(x, 13.5, 3, 10.5)
        # Column capital & base
        p.drawLine(x - 0.5, 13.5, x + 3.5, 13.5)
        p.drawLine(x - 0.5, 24, x + 3.5, 24)
        
    # Steps at bottom (Base steps)
    p.setPen(QPen(QColor("#1D4ED8"), 0.8))
    p.setBrush(QBrush(QColor("#BFDBFE")))
    p.drawRect(3, 24, 26, 2.5)
    p.drawRect(1.5, 26.5, 29, 2.5)


def icon_cloud(p: QPainter, s: int):
    """18. İnternet Hesabı / Bulut: Gökyüzü Mavisi Bulut"""
    p.setPen(QPen(QColor("#0284C7"), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    grad = QLinearGradient(4, 8, 28, 26)
    grad.setColorAt(0, QColor("#E0F2FE"))
    grad.setColorAt(1, QColor("#BAE6FD"))
    p.setBrush(QBrush(grad))
    
    path = QPainterPath()
    path.addEllipse(4, 14, 11, 11)
    path.addEllipse(10, 7, 13, 13)
    path.addEllipse(19, 12, 9, 9)
    path.addRect(8, 17, 17, 8)
    p.drawPath(path)


def icon_help(p: QPainter, s: int):
    """19. Sorular & Yardım: Mavi Daire Soru İşareti"""
    p.setPen(QPen(QColor("#0284C7"), 1))
    grad = QLinearGradient(3, 3, 29, 29)
    grad.setColorAt(0, QColor("#60A5FA"))
    grad.setColorAt(1, QColor("#2563EB"))
    p.setBrush(QBrush(grad))
    p.drawEllipse(3, 3, 26, 26)
    
    # White question mark vector path
    p.setPen(QPen(QColor("#FFFFFF"), 2.6, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    q_path = QPainterPath()
    q_path.moveTo(11.5, 11.5)
    q_path.cubicTo(11.5, 8, 20.5, 8, 20.5, 12.5)
    q_path.cubicTo(20.5, 15.5, 16, 16, 16, 19.5)
    p.drawPath(q_path)
    
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawEllipse(14.7, 22.5, 2.6, 2.6)


def icon_home(p: QPainter, s: int):
    """Ana Sayfa: Şık Mor Ev İkonu"""
    p.setPen(QPen(QColor("#4C1D95"), 1))
    grad = QLinearGradient(3, 4, 29, 28)
    grad.setColorAt(0, QColor("#A78BFA"))
    grad.setColorAt(1, QColor("#7C3AED"))
    p.setBrush(QBrush(grad))
    
    roof = QPolygonF([
        QPointF(16, 3),
        QPointF(29, 13),
        QPointF(3, 13)
    ])
    p.drawPolygon(roof)
    
    p.drawRoundedRect(6, 13, 20, 14, 2, 2)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(13, 18, 6, 9, 1, 1)


def icon_clear(p: QPainter, s: int):
    """Çizelgeyi Sıfırla: Kırmızı Silme / Sıfırlama Rozeti"""
    p.setPen(QPen(QColor("#DC2626"), 1.2))
    grad = QLinearGradient(3, 3, 29, 29)
    grad.setColorAt(0, QColor("#F87171"))
    grad.setColorAt(1, QColor("#EF4444"))
    p.setBrush(QBrush(grad))
    p.drawEllipse(QRectF(3, 3, 26, 26))
    
    p.setPen(QPen(QColor("#FFFFFF"), 2.8, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(9, 9), QPointF(23, 23))
    p.drawLine(QPointF(23, 9), QPointF(9, 23))


def icon_wizard(p: QPainter, s: int):
    """Sihirbaz: Sihirli Değnek ve Yıldızlar"""
    p.setPen(QPen(QColor("#8B5CF6"), 3, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(6, 26, 22, 10)
    
    p.setPen(QPen(QColor("#FBBF24"), 1))
    p.setBrush(QBrush(QColor("#FDE047")))
    # Small stars around wand
    p.drawEllipse(23, 6, 4, 4)
    p.drawEllipse(13, 5, 3, 3)
    p.drawEllipse(25, 15, 3, 3)


def icon_back(p: QPainter, s: int):
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    arr = QPolygon([
        QPoint(s//2, 4), QPoint(4, s//2), QPoint(s//2, s-4),
        QPoint(s//2, s//2+4), QPoint(s-6, s//2+4),
        QPoint(s-6, s//2-4), QPoint(s//2, s//2-4)
    ])
    p.drawPolygon(arr)


# ── ICON MAP ──────────────────────────────────────────────────────────────────

ICON_MAP = {
    "anasayfa":       icon_home,
    "yeni":           icon_new,
    "ac":             icon_open,
    "kaydet":         icon_save,
    "yazdir":         icon_print,
    "on_izleme":      icon_preview,
    "geri_al":        icon_undo,
    "yinele":         icon_redo,
    "ders":           icon_subjects,
    "sinif":          icon_classes,
    "derslik":        icon_rooms,
    "ogretmen":       icon_teachers,
    "secim":          icon_electives,
    "iliskiler":      icon_relations,
    "plan":           icon_relations,
    "kontrol":        icon_check_badge,
    "otomatik":       icon_auto,
    "bulut_olustur":  icon_cloud_auto,
    "bulut":          icon_cloud,
    "sartlar":        icon_gavel,
    "okul":           icon_school_info,
    "bilgi":          icon_school_info,
    "internet":       icon_cloud,
    "yardim":         icon_help,
    "temizle":        icon_clear,
    "sihirbaz":       icon_wizard,
    "geri":           icon_back,
}


def make_icon(key: str, size: int = 32) -> QIcon:
    fn = ICON_MAP.get(key, icon_school_info)
    return QIcon(_make_pixmap(size, fn))


# ── Ribbon Scroll Area ────────────────────────────────────────────────────────
class RibbonScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("""
            QScrollArea {
                background: #FFFFFF;
                border: none;
            }
            QScrollBar:horizontal {
                height: 3px;
                background: #F8FAFC;
                border: none;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #CBD5E1;
                min-width: 20px;
                border-radius: 1.5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #94A3B8;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

    def wheelEvent(self, event):
        # Enable smooth horizontal scrolling with normal mouse wheel
        if event.angleDelta().y() != 0:
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - event.angleDelta().y()
            )
            event.accept()
        elif event.angleDelta().x() != 0:
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - event.angleDelta().x()
            )
            event.accept()
        else:
            super().wheelEvent(event)


# ── Ribbon Button ─────────────────────────────────────────────────────────────
class RibbonButton(QToolButton):
    """Vertical icon+label button matching aSc ribbon style"""
    def __init__(self, label: str, icon_key: str, callback=None, parent=None):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIcon(make_icon(icon_key, 32))
        self.setIconSize(QSize(32, 32))
        self.setText(label)
        self.setMinimumWidth(56)
        self.setMaximumWidth(76)
        self.setFixedHeight(62)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setCheckable(False)
        self.setCursor(Qt.PointingHandCursor)
        font = QFont(FONT_FAMILY, 7)
        self.setFont(font)
        self.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 0px 2px;
                color: #0F172A;
                font-size: 7pt;
                font-weight: 500;
                text-align: center;
            }
            QToolButton:hover {
                background: #DAE8FC;
                border: 1px solid #B8CCE4;
            }
            QToolButton:pressed {
                background: #B8D4F0;
            }
            QToolButton:disabled {
                background: transparent;
                border: 1px solid transparent;
                color: #A0AEC0;
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
        self.setFixedSize(50, 62)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        font = QFont(FONT_FAMILY, 7.5, QFont.Bold)
        self.setFont(font)
        self.setStyleSheet("""
            QToolButton {
                background: #1E6DB5;
                border: none;
                border-radius: 6px;
                padding: 0px 2px;
                color: #FFFFFF;
                font-size: 7.5pt;
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
        font = QFont(FONT_FAMILY, 8)
        self.cb.setFont(font)
        layout.addWidget(self.cb)


def _divider(parent=None):
    f = QFrame(parent)
    f.setFrameShape(QFrame.VLine)
    f.setFrameShadow(QFrame.Sunken)
    f.setStyleSheet("color: #E2E8F0;")
    f.setFixedWidth(2)
    return f


# ── Ribbon Tab Page ───────────────────────────────────────────────────────────
class RibbonPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(74)
        
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        self.scroll_area = RibbonScrollArea(self)
        self.content_widget = QWidget(self.scroll_area)
        self.content_widget.setFixedHeight(72)
        self.content_widget.setStyleSheet(f"background: {RIBBON_BG};")
        
        self.main_layout = QHBoxLayout(self.content_widget)
        self.main_layout.setContentsMargins(6, 1, 6, 1)
        self.main_layout.setSpacing(3)
        self.main_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        self.scroll_area.setWidget(self.content_widget)
        outer_layout.addWidget(self.scroll_area)
        self.setStyleSheet(f"background: {RIBBON_BG};")

    def add_button(self, label, icon_key, callback=None):
        btn = RibbonButton(label, icon_key, callback, self.content_widget)
        self.main_layout.addWidget(btn)
        return btn

    def add_back(self, callback=None):
        btn = RibbonWideButton(callback, self.content_widget)
        self.main_layout.addWidget(btn)
        self.main_layout.addWidget(_divider(self.content_widget))
        return btn

    def add_divider(self):
        self.main_layout.addWidget(_divider(self.content_widget))

    def add_stretch(self):
        self.main_layout.addStretch(1)

    def add_checkbox(self, label, checked=True):
        item = RibbonCheckItem(label, checked, self.content_widget)
        self.main_layout.addWidget(item)
        return item


def make_menu_icon(symbol: str, color1: str, color2: str) -> QIcon:
    pix = QPixmap(28, 28)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 0, 28)
    grad.setColorAt(0, QColor(color1))
    grad.setColorAt(1, QColor(color2))
    p.setBrush(QBrush(grad))
    p.setPen(QPen(QColor(0,0,0,30), 1))
    p.drawRoundedRect(2, 2, 24, 24, 5, 5)
    p.setPen(QPen(Qt.white, 2))
    p.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
    p.drawText(2, 2, 24, 24, Qt.AlignCenter, symbol)
    p.end()
    return QIcon(pix)


# ── Main Ribbon Widget ────────────────────────────────────────────────────────
class RibbonWidget(QWidget):
    tab_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(116)
        self._pages = []
        self._tab_buttons = []
        self._active = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Tab bar ──
        self._tab_bar = QWidget(self)
        self._tab_bar.setFixedHeight(34)
        self._tab_bar.setStyleSheet(f"background: #FFFFFF; border-bottom: 1px solid {RIBBON_BORDER};")
        self._tab_layout = QHBoxLayout(self._tab_bar)
        self._tab_layout.setContentsMargins(8, 3, 8, 0)
        self._tab_layout.setSpacing(4)

        outer.addWidget(self._tab_bar)

        # ── Page area ──
        self._page_area = QWidget(self)
        self._page_area.setFixedHeight(84)
        self._page_area.setStyleSheet(f"background: {RIBBON_BG}; border-bottom: 1px solid {RIBBON_BORDER};")
        self._page_layout = QVBoxLayout(self._page_area)
        self._page_layout.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._page_area)

    def set_collapsed(self, collapsed: bool):
        """Hides the button area, leaving only the tab strip.

        The widget has a fixed height, so hiding the page area alone would leave an
        82 px empty band; the height has to shrink with it.
        """
        self._collapsed = bool(collapsed)
        self._page_area.setVisible(not self._collapsed)
        self.setFixedHeight(34 if self._collapsed else 116)

    def is_collapsed(self) -> bool:
        return bool(getattr(self, "_collapsed", False))

    def add_tab(self, name: str) -> RibbonPage:
        idx = len(self._pages)
        page = RibbonPage(self._page_area)

        btn = QPushButton(name, self._tab_bar)
        btn.setFlat(True)
        btn.setFixedHeight(30)
        btn.setFont(QFont(FONT_FAMILY, 9))
        btn.setCheckable(True)
        btn.setChecked(idx == 0)
        btn.setCursor(Qt.PointingHandCursor)
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
                        background: #FFFFFF;
                        color: #0284C7;
                        border: none;
                        border-bottom: 2.5px solid #0284C7;
                        padding: 2px 14px;
                        font-weight: 700;
                        font-family: {FONT_FAMILY};
                        font-size: 12.5px;
                        border-top-left-radius: 6px;
                        border-top-right-radius: 6px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: #64748B;
                        border: none;
                        border-bottom: 2.5px solid transparent;
                        padding: 2px 14px;
                        font-weight: 600;
                        font-family: {FONT_FAMILY};
                        font-size: 12.5px;
                        border-top-left-radius: 6px;
                        border-top-right-radius: 6px;
                    }}
                    QPushButton:hover {{
                        background: #F1F5F9;
                        color: #0F172A;
                    }}
                """)
