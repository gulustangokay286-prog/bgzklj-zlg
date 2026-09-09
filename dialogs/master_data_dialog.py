"""dialogs/master_data_dialog.py - Gerçek Zamanlı Ana Veri Yönetim Penceresi"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSizePolicy, QSpacerItem, QMessageBox
)
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QBrush, QPolygon, QIcon, QLinearGradient, QPainterPath
from PySide6.QtCore import Signal, QEvent

from dialogs.edit_forms import DersEditDialog, SinifEditDialog, OgretmenEditDialog, DerslikEditDialog, make_edit_svg_icon
from auto_scheduler import format_tr_name, matches_class
import lesson_hours
from database import trigger_save_db
from PySide6.QtWidgets import QAbstractItemView

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"

def check_undo_removes_assigned_entity(widget, current_store, prev_store, out_removed_entities=None) -> bool:
    """
    Checks if restoring prev_store would delete/remove any lesson, teacher, or class
    that currently has active assignments (atamalar).
    If so, prompts the user:
    "Geri alma işlemi sonucunda '{entity_name}' {entity_type} kaldırılacaktır.
     Bu kayda ait {count} adet ders ataması bulunmaktadır.
     Kaydı geri alıp bağlı tüm atamalarını da kaldırmak istiyor musunuz?"
    
    Returns:
        True: User confirmed or no assigned entity is being deleted -> proceed with undo.
        False: User declined (No) -> cancel undo.
    """
    from auto_scheduler import format_tr_name, matches_class
    from version_store import _matches_teacher
    from PySide6.QtWidgets import QMessageBox

    test_mode = getattr(widget, "_test_mode", False) or getattr(getattr(widget, "main_window", None), "_test_mode", False)
    test_confirm = getattr(widget, "_test_confirm_undo", True)

    to_remove = []

    # 1. Check Dersler (Lessons)
    curr_lessons = [d.get("ad", "").strip() for d in current_store.get("dersler", []) if d.get("ad")]
    prev_lessons_fmt = {format_tr_name(d.get("ad", "")) for d in prev_store.get("dersler", []) if d.get("ad")}
    
    for l_name in curr_lessons:
        l_fmt = format_tr_name(l_name)
        if l_fmt not in prev_lessons_fmt:
            matching_atama = [
                a for a in current_store.get("atamalar", [])
                if format_tr_name(a.get("subject", "")) == l_fmt
            ]
            if matching_atama:
                count = len(matching_atama)
                if test_mode:
                    if not test_confirm:
                        return False
                    to_remove.append(("lesson", l_name))
                    continue
                r = QMessageBox.question(
                    widget,
                    "Geri Alma Onayı — Atanmış Ders",
                    f"Geri alma işlemi sonucunda '{l_name}' dersi kaldırılacaktır.\n\n"
                    f"Bu derse ait {count} adet ders ataması bulunmaktadır.\n\n"
                    f"Dersi geri alıp bağlı tüm atamalarını da kaldırmak istiyor musunuz?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if r != QMessageBox.Yes:
                    return False
                to_remove.append(("lesson", l_name))

    # 2. Check Öğretmenler (Teachers)
    curr_teachers = [t.get("ad", "").strip() for t in current_store.get("ogretmenler", []) if t.get("ad")]
    prev_teachers_fmt = {format_tr_name(t.get("ad", "")) for t in prev_store.get("ogretmenler", []) if t.get("ad")}
    
    for t_name in curr_teachers:
        t_fmt = format_tr_name(t_name)
        if t_fmt not in prev_teachers_fmt:
            matching_atama = [
                a for a in current_store.get("atamalar", [])
                if _matches_teacher(a.get("teacher", ""), t_name) or format_tr_name(a.get("teacher", "")) == t_fmt
            ]
            if matching_atama:
                count = len(matching_atama)
                if test_mode:
                    if not test_confirm:
                        return False
                    to_remove.append(("teacher", t_name))
                    continue
                r = QMessageBox.question(
                    widget,
                    "Geri Alma Onayı — Görevlendirilmiş Öğretmen",
                    f"Geri alma işlemi sonucunda '{t_name}' öğretmeni kaldırılacaktır.\n\n"
                    f"Bu öğretmene ait {count} adet ders ataması bulunmaktadır.\n\n"
                    f"Öğretmeni geri alıp bağlı tüm atamalarını da kaldırmak istiyor musunuz?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if r != QMessageBox.Yes:
                    return False
                to_remove.append(("teacher", t_name))

    # 3. Check Sınıflar (Classes)
    curr_classes = [c.get("ad", "").strip() for c in current_store.get("siniflar", []) if c.get("ad")]
    prev_classes_fmt = {format_tr_name(c.get("ad", "")) for c in prev_store.get("siniflar", []) if c.get("ad")}
    
    for c_name in curr_classes:
        c_fmt = format_tr_name(c_name)
        if c_fmt not in prev_classes_fmt:
            matching_atama = [
                a for a in current_store.get("atamalar", [])
                if matches_class(a.get("class", ""), c_name) or format_tr_name(a.get("class", "")) == c_fmt or (isinstance(a.get("combined_classes"), list) and any(matches_class(x, c_name) for x in a["combined_classes"]))
            ]
            if matching_atama:
                count = len(matching_atama)
                if test_mode:
                    if not test_confirm:
                        return False
                    to_remove.append(("class", c_name))
                    continue
                r = QMessageBox.question(
                    widget,
                    "Geri Alma Onayı — Atanmış Sınıf",
                    f"Geri alma işlemi sonucunda '{c_name}' sınıfı kaldırılacaktır.\n\n"
                    f"Bu sınıfa ait {count} adet ders ataması bulunmaktadır.\n\n"
                    f"Sınıfı geri alıp bağlı tüm atamalarını da kaldırmak istiyor musunuz?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if r != QMessageBox.Yes:
                    return False
                to_remove.append(("class", c_name))

    if out_removed_entities is not None:
        out_removed_entities.extend(to_remove)

    return True


def purge_entity_references(data_store, entity_type, entity_name):
    """
    Purges assignments, grid placements, and yerlesim only for the specific entity
    that was confirmed to be removed during undo.
    """
    from auto_scheduler import format_tr_name, matches_class
    from version_store import _matches_teacher

    del_fmt = format_tr_name(entity_name)

    if entity_type == "lesson":
        data_store["atamalar"] = [
            a for a in data_store.get("atamalar", [])
            if format_tr_name(a.get("subject", "")) != del_fmt
        ]
        data_store["grid_placements"] = [
            p for p in data_store.get("grid_placements", [])
            if format_tr_name(p.get("subject_name") or p.get("subject", "")) != del_fmt
        ]
        yerlesim = data_store.get("yerlesim", {})
        if isinstance(yerlesim, dict):
            for k in list(yerlesim.keys()):
                info = yerlesim[k]
                if isinstance(info, dict) and format_tr_name(info.get("subject_name") or info.get("subject", "")) == del_fmt:
                    yerlesim.pop(k, None)
        if "auto_schedule_results" in data_store:
            data_store["auto_schedule_results"] = [
                p for p in data_store.get("auto_schedule_results", [])
                if format_tr_name(p.get("subject_name") or p.get("subject", "")) != del_fmt
            ]

    elif entity_type == "teacher":
        data_store["atamalar"] = [
            a for a in data_store.get("atamalar", [])
            if not _matches_teacher(a.get("teacher", ""), entity_name) and format_tr_name(a.get("teacher", "")) != del_fmt
        ]
        data_store["grid_placements"] = [
            p for p in data_store.get("grid_placements", [])
            if not _matches_teacher(p.get("teacher_name") or p.get("teacher", ""), entity_name) and format_tr_name(p.get("teacher_name") or p.get("teacher", "")) != del_fmt
        ]
        yerlesim = data_store.get("yerlesim", {})
        if isinstance(yerlesim, dict):
            for k in list(yerlesim.keys()):
                info = yerlesim[k]
                if isinstance(info, dict) and (_matches_teacher(info.get("teacher_name") or info.get("teacher", ""), entity_name) or format_tr_name(info.get("teacher_name") or info.get("teacher", "")) == del_fmt):
                    yerlesim.pop(k, None)
        if "auto_schedule_results" in data_store:
            data_store["auto_schedule_results"] = [
                p for p in data_store.get("auto_schedule_results", [])
                if not _matches_teacher(p.get("teacher_name") or p.get("teacher", ""), entity_name) and format_tr_name(p.get("teacher_name") or p.get("teacher", "")) != del_fmt
            ]

    elif entity_type == "class":
        data_store["atamalar"] = [
            a for a in data_store.get("atamalar", [])
            if not (matches_class(a.get("class", ""), entity_name) or a.get("class") == entity_name or
                    (isinstance(a.get("combined_classes"), list) and any(matches_class(x, entity_name) for x in a["combined_classes"])))
        ]
        data_store["grid_placements"] = [
            p for p in data_store.get("grid_placements", [])
            if not (matches_class(p.get("class_name") or p.get("class", ""), entity_name) or
                    (isinstance(p.get("combined_classes"), list) and any(matches_class(x, entity_name) for x in p["combined_classes"])))
        ]
        yerlesim = data_store.get("yerlesim", {})
        if isinstance(yerlesim, dict):
            for k in list(yerlesim.keys()):
                info = yerlesim[k]
                if isinstance(info, dict) and (matches_class(info.get("class_name") or info.get("class", ""), entity_name) or
                                               (isinstance(info.get("combined_classes"), list) and any(matches_class(x, entity_name) for x in info["combined_classes"]))):
                    yerlesim.pop(k, None)
        if "auto_schedule_results" in data_store:
            data_store["auto_schedule_results"] = [
                p for p in data_store.get("auto_schedule_results", [])
                if not (matches_class(p.get("class_name") or p.get("class", ""), entity_name) or
                        (isinstance(p.get("combined_classes"), list) and any(matches_class(x, entity_name) for x in p["combined_classes"])))
            ]


class DragDropTableWidget(QTableWidget):
    row_dropped = Signal(int, int) # start_row, dest_row

    def __init__(self, rows, cols, parent=None):
        super().__init__(rows, cols, parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        
    def dropEvent(self, event):
        if not event.isAccepted() and event.source() == self:
            drop_row = self.rowAt(event.position().toPoint().y())
            if drop_row == -1:
                drop_row = self.rowCount()
            
            selected_rows = sorted(list(set(item.row() for item in self.selectedItems())))
            if selected_rows:
                start_row = selected_rows[0]
                self.row_dropped.emit(start_row, drop_row)
                event.setDropAction(Qt.IgnoreAction)
                event.accept()
                return
        super().dropEvent(event)
def create_wizard_icon(name: str) -> QPixmap:
    """Authentic aSc Timetables left navigation icons (Retina 2x vector supersampling)."""
    sz = 48
    pix = QPixmap(sz * 2, sz * 2)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    p.scale(2, 2)
    
    selected = name.endswith("_selected")
    base_name = name.replace("_selected", "")
    
    if base_name == "book":
        # 1. DERSLER: 3D Mavi Ciltli Ders Kitabı
        # Page Block on right & top
        p.setPen(QPen(QColor("#CBD5E1"), 0.8))
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawRect(14, 6, 26, 35)
        
        # Page lines
        p.setPen(QPen(QColor("#E2E8F0"), 0.8))
        p.drawLine(37, 8, 37, 40)
        p.drawLine(35, 8, 35, 40)
        
        # Front Blue Hardcover
        grad_cover = QLinearGradient(9, 5, 34, 43)
        grad_cover.setColorAt(0, QColor("#60A5FA"))
        grad_cover.setColorAt(0.5, QColor("#2563EB"))
        grad_cover.setColorAt(1, QColor("#1D4ED8"))
        p.setPen(QPen(QColor("#1E40AF"), 1.2))
        p.setBrush(QBrush(grad_cover))
        p.drawRoundedRect(9, 5, 27, 38, 3, 3)
        
        # Dark blue spine on left
        p.setPen(QPen(QColor("#1E3A8A"), 1))
        p.setBrush(QBrush(QColor("#1E40AF")))
        p.drawRoundedRect(9, 5, 6, 38, 2, 2)
        
        # White label on front cover
        p.setPen(QPen(QColor("#93C5FD"), 0.8))
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawRoundedRect(18, 12, 14, 20, 2, 2)
        
        # Label lines
        p.setPen(QPen(QColor("#3B82F6"), 1))
        p.drawLine(21, 17, 29, 17)
        p.drawLine(21, 22, 29, 22)
        p.drawLine(21, 27, 26, 27)
        
    elif base_name in ["teachers", "siniflar"]:
        # 2. SINIFLAR: 3D Öğrenci Grubu / Sınıf Kohortu (Pembe, Zümrüt Yeşili ve Gök Mavisi)
        # ── 1. Left Student (Coral/Pink) ──
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#92400E")))
        p.drawEllipse(3, 10, 16, 16)
        p.setBrush(QBrush(QColor("#FDE68A")))
        p.drawEllipse(5, 13, 13, 13)
        
        grad_l = QLinearGradient(2, 26, 20, 42)
        grad_l.setColorAt(0, QColor("#FB7185"))
        grad_l.setColorAt(1, QColor("#E11D48"))
        p.setBrush(QBrush(grad_l))
        path_l = QPainterPath()
        path_l.moveTo(2, 42)
        path_l.lineTo(2, 29)
        path_l.cubicTo(2, 23, 20, 23, 20, 29)
        path_l.lineTo(20, 42)
        path_l.closeSubpath()
        p.drawPath(path_l)
        
        # ── 2. Right Student (Sky Blue) ──
        p.setBrush(QBrush(QColor("#334155")))
        p.drawEllipse(29, 10, 16, 16)
        p.setBrush(QBrush(QColor("#FDE68A")))
        p.drawEllipse(30, 13, 13, 13)
        
        grad_r = QLinearGradient(28, 26, 46, 42)
        grad_r.setColorAt(0, QColor("#38BDF8"))
        grad_r.setColorAt(1, QColor("#0284C7"))
        p.setBrush(QBrush(grad_r))
        path_r = QPainterPath()
        path_r.moveTo(28, 42)
        path_r.lineTo(28, 29)
        path_r.cubicTo(28, 23, 46, 23, 46, 29)
        path_r.lineTo(46, 42)
        path_r.closeSubpath()
        p.drawPath(path_r)
        
        # ── 3. Center Front Student (Emerald Green) ──
        grad_c = QLinearGradient(12, 23, 36, 45)
        grad_c.setColorAt(0, QColor("#34D399"))
        grad_c.setColorAt(1, QColor("#059669"))
        p.setBrush(QBrush(grad_c))
        path_c = QPainterPath()
        path_c.moveTo(11, 45)
        path_c.lineTo(11, 28)
        path_c.cubicTo(11, 20, 37, 20, 37, 28)
        path_c.lineTo(37, 45)
        path_c.closeSubpath()
        p.drawPath(path_c)
        
        # White V-collar
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.setPen(QPen(QColor("#047857"), 0.8))
        p.drawPolygon([QPoint(20, 26), QPoint(24, 34), QPoint(28, 26), QPoint(24, 28)])
        
        # Face
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#FEF08A")))
        p.drawEllipse(15, 8, 18, 18)
        
        # Cheek blush
        p.setBrush(QBrush(QColor(244, 63, 94, 60)))
        p.drawEllipse(17, 18, 3.5, 2.5)
        p.drawEllipse(27, 18, 3.5, 2.5)
        
        # Golden styled hair
        p.setBrush(QBrush(QColor("#F59E0B")))
        path_ch = QPainterPath()
        path_ch.moveTo(14, 14)
        path_ch.cubicTo(14, 4, 34, 4, 34, 14)
        path_ch.cubicTo(30, 8, 20, 8, 14, 14)
        path_ch.closeSubpath()
        p.drawPath(path_ch)
        
        # Hair highlight
        p.setBrush(QBrush(QColor("#FDE047")))
        p.drawEllipse(19, 6, 9, 3.5)
        
    elif base_name in ["door", "derslikler"]:
        # 3. DERSLİKLER: 3D Açık Sınıf Kapısı
        p.setPen(QPen(QColor("#92400E"), 1.2))
        p.setBrush(QBrush(QColor("#FDE68A")))
        p.drawRect(7, 5, 33, 38)
        
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#1E293B")))
        p.drawRect(11, 9, 25, 34)
        
        grad_door = QLinearGradient(11, 9, 39, 43)
        grad_door.setColorAt(0, QColor("#FBBF24"))
        grad_door.setColorAt(1, QColor("#D97706"))
        p.setPen(QPen(QColor("#92400E"), 1.2))
        p.setBrush(QBrush(grad_door))
        
        door_poly = QPolygon([
            QPoint(11, 9),
            QPoint(39, 3),
            QPoint(39, 44),
            QPoint(11, 42)
        ])
        p.drawPolygon(door_poly)
        
        p.setPen(QPen(QColor("#92400E"), 0.9))
        p.drawLine(18, 12, 33, 8)
        p.drawLine(33, 8, 33, 40)
        p.drawLine(33, 40, 18, 40)
        p.drawLine(18, 40, 18, 12)
        
        p.setPen(QPen(QColor("#78350F"), 0.8))
        p.setBrush(QBrush(QColor("#FEF08A")))
        p.drawEllipse(34, 24, 4, 4)
        
    elif base_name in ["grad_hat", "teacher", "ogretmenler", "ogretmen"]:
        # 4. ÖĞRETMENLER: 3D Mezuniyet Kepi
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#0F172A")))
        p.drawRect(15, 23, 18, 12)
        p.drawRoundedRect(13, 21, 22, 14, 3, 3)
        
        hat_poly = QPolygon([
            QPoint(24, 7),
            QPoint(45, 17),
            QPoint(24, 27),
            QPoint(3, 17)
        ])
        grad_hat = QLinearGradient(3, 7, 45, 27)
        grad_hat.setColorAt(0, QColor("#334155"))
        grad_hat.setColorAt(1, QColor("#0F172A"))
        p.setPen(QPen(QColor("#475569"), 1.2))
        p.setBrush(QBrush(grad_hat))
        p.drawPolygon(hat_poly)
        
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#F59E0B")))
        p.drawEllipse(22.5, 15.5, 3.5, 3.5)
        
        p.setPen(QPen(QColor("#F59E0B"), 1.8, Qt.SolidLine, Qt.RoundCap))
        tassel = QPainterPath()
        tassel.moveTo(24, 17)
        tassel.cubicTo(16, 18, 9, 23, 8, 29)
        p.drawPath(tassel)
        
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#F59E0B")))
        p.drawRoundedRect(6, 29, 4, 8, 1, 1)
        
    # ── 3D Green Arrow Highlight on Selected / Active Item ──────────────────
    if selected:
        arrow = QPolygon([
            QPoint(2, 20),
            QPoint(20, 20),
            QPoint(20, 12),
            QPoint(36, 24),
            QPoint(20, 36),
            QPoint(20, 28),
            QPoint(2, 28)
        ])
        grad_arrow = QLinearGradient(2, 12, 36, 36)
        grad_arrow.setColorAt(0, QColor("#4ADE80"))
        grad_arrow.setColorAt(1, QColor("#15803D"))
        
        # Arrow Shadow
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 70)))
        arrow_shadow = QPolygon([
            QPoint(3, 22),
            QPoint(21, 22),
            QPoint(21, 14),
            QPoint(38, 26),
            QPoint(21, 38),
            QPoint(21, 30),
            QPoint(3, 30)
        ])
        p.drawPolygon(arrow_shadow)
        
        # Arrow Body
        p.setPen(QPen(QColor("#14532D"), 1.5))
        p.setBrush(QBrush(grad_arrow))
        p.drawPolygon(arrow)
        
        # Arrow Inner 3D Highlight
        p.setPen(QPen(QColor(255, 255, 255, 140), 1))
        p.drawLine(3, 21, 20, 21)
        p.drawLine(20, 14, 33, 24)
        
    p.end()
    pix.setDevicePixelRatio(2.0)
    return pix


class LeftMenuButton(QPushButton):
    def __init__(self, icon_name, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.setFixedSize(68, 68)
        self.setIcon(create_wizard_icon(self.icon_name))
        self.setIconSize(QSize(52, 52))
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                border: 1.5px solid transparent;
                background: transparent;
                border-radius: 8px;
                margin: 2px;
            }
            QPushButton:hover {
                background: #F1F5F9;
                border-color: #E2E8F0;
            }
            QPushButton:checked {
                background: #E0F2FE;
                border-color: #0284C7;
            }
        """)

    def setChecked(self, checked):
        super().setChecked(checked)
        if checked:
            self.setIcon(create_wizard_icon(self.icon_name + "_selected"))
        else:
            self.setIcon(create_wizard_icon(self.icon_name))


class MiniTimeoffGridWidget(QWidget):
    """Authentic aSc Timetables Compact Timeoff Matrix.
    X-Axis = Days (Cols, e.g. Pazartesi..Cuma)
    Y-Axis = Periods (Rows, e.g. 1.Ders..8.Ders - stacked vertically)
    """
    def __init__(self, timeoff_data=None, days=5, periods=8, parent=None):
        super().__init__(parent)
        self.timeoff_data = timeoff_data or []
        self.days = max(1, int(days))
        self.periods = max(1, int(periods))
        self.setToolTip("Çift Tıklayarak Zaman Tablosu / Kısıtlama Ayarlarını Açın")
        
        # ÖLÇÜ: hücre boyutu ÖNCE seçilir, kutu ondan türetilir.
        #
        # Eskiden tersiydi: sabit bir kutu boyutu alınıp hücre sınırları
        # int(p*(h-1)/rows) ile hesaplanıyordu. Bölme tam bölünmediğinde
        # satırların kimi 2 kimi 3 piksel çıkıyor, ızgara çizgileri de hücrenin
        # ÜSTÜNE çizildiği için ince satırların rengi yeniyordu: en alttaki
        # neredeyse görünmüyor, aradaki bazı siyah çizgiler kalın duruyordu.
        #
        # Artık her hücre birebir aynı boyutta ve çizgiler hücrelerin ARASINDA
        # duruyor (kutu önce siyaha boyanıp hücreler 1 piksel içeriden
        # dolduruluyor), yani hiçbir satır bir diğerinden ince olamaz.
        self.cell_w, self.cell_h = self._pick_cell_size()
        w = self.days * (self.cell_w + 1) + 1
        h = self.periods * (self.cell_h + 1) + 1
        self.setFixedSize(w, h)

    # Kutuya GERÇEKTE kalan yer: satır 44 piksel, QTableWidget::item dikey iç
    # boşluğu 4+4 = 8 piksel alıyor -> 36. Bu tavan aşılırsa widget alttan
    # kırpılır ve son ders saatleri hiç görünmez (yaşanan hata buydu).
    # Satır artık kutuya göre büyüdüğü için (bkz. _add_row) tavan yalnızca
    # kutunun makul kalmasını sağlıyor; kırpılmayı önleyen şey tavan değil,
    # satırın kutuya uydurulması.
    MAX_H = 40
    MAX_W = 76

    def _pick_cell_size(self):
        """(hücre_genişliği, hücre_yüksekliği) — sığan en büyük boy.

        Ayraç çizgileri HER ZAMAN kalır; sığdırmak için hücre küçültülür.
        Ayraçları kaldırıp hücreyi büyütmeyi denemek yanlıştı: aynı renkteki
        komşu saatler tek bir bloğa yapışıyor, kullanıcı kaç saat olduğunu
        ayırt edemiyordu. 1 piksellik hücre bile ayraçla birlikte sayılabilir
        kalıyor.
        """
        cw = 2
        for cand in range(13, 1, -1):
            if self.days * (cand + 1) + 1 <= self.MAX_W:
                cw = cand
                break

        ch = 1
        for cand in (4, 3, 2, 1):
            if self.periods * (cand + 1) + 1 <= self.MAX_H:
                ch = cand
                break
        return cw, ch
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        cols = self.days     # X ekseni: günler
        rows = self.periods  # Y ekseni: ders saatleri (yukarıdan aşağı)
        cw, ch = self.cell_w, self.cell_h

        # Izgara, hücrelerin ÜSTÜNE çizilmiyor: önce bütün kutu siyaha boyanıp
        # hücreler 1 piksel içeriden dolduruluyor. Böylece çizgiler tam olarak
        # hücrelerin arasında kalıyor, her çizgi tam 1 piksel ve her hücre
        # birebir aynı boyutta oluyor.
        painter.fillRect(self.rect(), QColor("#000000"))

        for p in range(rows):
            y = 1 + p * (ch + 1)
            for d in range(cols):
                x = 1 + d * (cw + 1)

                # timeoff_data, constraint_sync.get_matrix'ten gelen HAZIR matris:
                # boyutu her zaman gün x saat, kişisel kısıtlar işlenmiş, durumlar
                # normalleştirilmiş. Eskiden burası entity["timeoff"]'u HAM okuyup
                # dizinin kısa kaldığı saatleri "açık" sayıyordu; diyalog ise
                # get_matrix kullandığı için ikisi ayrışıyor, kapatılan son saat
                # önizlemede yeşil kalıyordu.
                val = 2
                if d < len(self.timeoff_data or []) and p < len(self.timeoff_data[d]):
                    val = self.timeoff_data[d][p]

                painter.fillRect(x, y, cw, ch,
                                 QColor("#00C800") if val == 2 else QColor("#DC2626"))


class ActionButton(QPushButton):
    def __init__(self, text, icon_name=None, is_primary=False, parent=None):
        super().__init__(text, parent)
        self.icon_name = icon_name
        self.setFixedHeight(30)
        self.setFont(QFont("SF Pro Text", 9, QFont.Bold))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 32px;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background-color: #FFFFFF;
                color: #0F172A;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F8FAFC;
                border-color: #94A3B8;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.icon_name:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.icon_name == "plus":
            p.setBrush(QColor("#16A34A"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(8, 7, 16, 16)
            p.setPen(QPen(Qt.white, 2))
            p.drawLine(16, 11, 16, 19)
            p.drawLine(12, 15, 20, 15)
        elif self.icon_name == "edit":
            p.setBrush(QColor("#64748B"))
            p.setPen(Qt.NoPen)
            p.drawRect(8, 9, 16, 12)
            p.drawPolygon([QPoint(8, 9), QPoint(16, 5), QPoint(24, 9)])
        elif self.icon_name == "minus":
            p.setBrush(QColor("#64748B"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(8, 7, 16, 16)
            p.setPen(QPen(Qt.white, 2))
            p.drawLine(12, 15, 20, 15)
        elif self.icon_name == "doc":
            p.setBrush(QColor("#64748B"))
            p.setPen(Qt.NoPen)
            p.drawRect(10, 7, 12, 16)
            p.drawRect(18, 5, 6, 6)
        elif self.icon_name == "clock":
            p.setPen(QPen(QColor("#64748B"), 2))
            p.drawEllipse(8, 7, 16, 16)
            p.drawLine(16, 15, 16, 9)
            p.drawLine(16, 15, 20, 15)
        elif self.icon_name == "hash":
            p.setPen(QPen(QColor("#64748B"), 2))
            p.drawLine(12, 7, 12, 23)
            p.drawLine(20, 7, 20, 23)
            p.drawLine(8, 11, 24, 11)
            p.drawLine(8, 19, 24, 19)
        elif self.icon_name == "branch":
            p.setPen(QPen(QColor("#64748B"), 2))
            p.drawLine(16, 21, 16, 15)
            p.drawLine(16, 15, 10, 9)
            p.drawLine(16, 15, 22, 9)
        p.end()


class MasterDataDialog(QDialog):
    def __init__(self, start_idx=0, parent=None, data_store=None):
        super().__init__(parent)
        if isinstance(start_idx, dict):
            data_store = start_idx
            start_idx = 0
        self.setWindowTitle("Sınıflar") # Will be updated in select_tab
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        self.setSizeGripEnabled(True)
        self.mag_buttons = []
        self.resize(950, 680)
        self.setFont(QFont(FONT_FAMILY, 9))
        
        self.main_window = parent
        if data_store is not None:
            self.data_store = data_store
        elif hasattr(self.main_window, "data_store"):
            self.data_store = self.main_window.data_store
        else:
            self.data_store = {
                "siniflar": [], "ogretmenler": [], "derslikler": [], "dersler": []
            }
        for k in ["siniflar", "ogretmenler", "derslikler", "dersler", "atamalar", "grid_placements"]:
            if k not in self.data_store:
                self.data_store[k] = []
        
        if parent and hasattr(parent, "_history_stack"):
            self._history_stack = parent._history_stack
            self._redo_stack = parent._redo_stack
        else:
            self._history_stack = []
            self._redo_stack = []
        
        self._build_ui()
        self._load_existing_data()
        self._select_tab(start_idx)
        self._update_undo_redo_ui()

    def _load_data(self):
        self._load_existing_data()

    def _update_count_labels(self):
        """Sekmelerin sağ üstündeki sade özeti tazeler: kaç kayıt, kaç saat.

        Saat, atamalardaki haftalık ders saatlerinin toplamı. Ders sekmesinde
        o dersin, sınıf sekmesinde o sınıfın, öğretmen sekmesinde o öğretmenin
        saatleri toplanıyor; derslikte saat kavramı olmadığı için yalnız sayı
        gösteriliyor.
        """
        labels = getattr(self, "count_labels", None)
        if not labels:
            return

        atamalar = self.data_store.get("atamalar", []) or []

        def _hours(field):
            tot = 0
            for a in atamalar:
                if not isinstance(a, dict):
                    continue
                if not str(a.get(field) or "").strip():
                    continue
                try:
                    tot += int(a.get("duration") or a.get("hours") or 1)
                except (TypeError, ValueError):
                    tot += 1
            return tot

        # Sekme sırası: Dersler, Sınıflar, Derslikler, Öğretmenler.
        specs = [
            ("dersler", "ders", "subject", "Tanımlı ders sayısı ve bu derslere atanmış toplam haftalık ders saati."),
            ("siniflar", "sınıf", "class", "Tanımlı sınıf sayısı ve sınıflara atanmış toplam haftalık ders saati."),
            ("derslikler", "derslik", None, "Tanımlı derslik sayısı."),
            ("ogretmenler", "öğretmen", "teacher", "Tanımlı öğretmen sayısı ve öğretmenlere atanmış toplam haftalık ders saati."),
        ]
        icons = getattr(self, "count_icons", []) or []

        for i, (key, word, field, tip) in enumerate(specs):
            if i >= len(labels):
                break
            n = len([x for x in (self.data_store.get(key) or [])
                     if isinstance(x, dict) and str(x.get("ad") or "").strip()])
            if field:
                h = _hours(field)
                labels[i].setText(f"{n} {word}  ·  {h} saat")
                full_tip = f"{tip}\n\n{n} {word}, toplam {h} saat."
            else:
                labels[i].setText(f"{n} {word}")
                full_tip = f"{tip}\n\n{n} {word}."
            labels[i].setToolTip(full_tip)
            if i < len(icons):
                icons[i].setToolTip(full_tip)

    def _load_existing_data(self):
        # Reset row counts to avoid duplicate row stacking
        self.table_ders.setRowCount(0)
        self.table_sinif.setRowCount(0)
        self.table_derslik.setRowCount(0)
        self.table_ogretmen.setRowCount(0)
        
        # Clean & Format all subject and teacher names to Turkish title case
        from dialogs.edit_forms import format_tr_name
        for d in self.data_store.get("dersler", []):
            if d.get("ad"): d["ad"] = format_tr_name(d["ad"])
        for a in self.data_store.get("atamalar", []):
            if a.get("subject"): a["subject"] = format_tr_name(a["subject"])
        for t in self.data_store.get("ogretmenler", []):
            if t.get("ad"): t["ad"] = format_tr_name(t["ad"])

        # Sort logic removed here to preserve manual drag-and-drop order.
        # A dedicated sort button will be provided in the UI instead.

        # Calculate totals from atamalar
        totals = {"dersler": {}, "siniflar": {}, "ogretmenler": {}}
        for a in self.data_store.get("atamalar", []):
            dur = a.get("duration", 1)
            t = a.get("teacher", "")
            s = a.get("subject", "")
            c = a.get("class", "")
            if t: totals["ogretmenler"][t] = totals["ogretmenler"].get(t, 0) + dur
            if s: totals["dersler"][s] = totals["dersler"].get(s, 0) + dur
            if c: totals["siniflar"][c] = totals["siniflar"].get(c, 0) + dur

        settings = self.data_store.get("settings", {})
        days = settings.get("days", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
        periods = int(settings.get("periods", self.data_store.get("ders_saati", 8)))
        total_default = len(days) * periods

        for data in self.data_store.get("dersler", []):
            toplam = str(totals["dersler"].get(data.get("ad", ""), 0))
            self._add_row(self.table_ders, [data.get("ad",""), data.get("kisa",""), toplam, "Mevcut", "İdeal", str(data.get("max_gunluk", periods))], timeoff=self._timeoff_matrix(data), days_cnt=len(days), periods_cnt=periods)
        
        for data in self.data_store.get("siniflar", []):
            toplam = str(totals["siniflar"].get(data.get("ad", ""), 0))
            timeoff = data.get("timeoff", [])
            if not timeoff:
                zaman_str = f"{total_default} Ders"
            else:
                open_cells = sum(1 for r in timeoff for c in r if c > 0)
                zaman_str = f"{open_cells} Ders"
                
            self._add_row(self.table_sinif, [data.get("ad",""), data.get("kisa",""), toplam, zaman_str, data.get("ders_bitimi","15:30"), data.get("sinif_ogretmeni",""), data.get("kapasite","30")], timeoff=self._timeoff_matrix(data), days_cnt=len(days), periods_cnt=periods)
        for data in self.data_store.get("derslikler", []):
            self._add_row(self.table_derslik, [data.get("ad",""), data.get("kisa",""), "0", "Mevcut", data.get("kapasite",""), "Merkez"], timeoff=self._timeoff_matrix(data), days_cnt=len(days), periods_cnt=periods)
        # Build Class Teacher mapping strictly from siniflar
        class_teacher_map = {}
        for s in self.data_store.get("siniflar", []):
            so = s.get("sinif_ogretmeni")
            if so and str(so).strip():
                class_teacher_map[format_tr_name(str(so))] = s.get("ad", "")

        totals = {"dersler": {}, "siniflar": {}, "ogretmenler": {}}
        for a in self.data_store.get("atamalar", []):
            dur = int(a.get("duration", 1))
            t = format_tr_name(a.get("teacher", ""))
            s = format_tr_name(a.get("subject", ""))
            c = (a.get("class") or "").strip()
            if t: totals["ogretmenler"][t] = totals["ogretmenler"].get(t, 0) + dur
            if s: totals["dersler"][s] = totals["dersler"].get(s, 0) + dur
            if c: totals["siniflar"][c] = totals["siniflar"].get(c, 0) + dur

        for data in self.data_store.get("ogretmenler", []):
            t_name = data.get("ad", "")
            t_fmt = format_tr_name(t_name)
            toplam = str(totals["ogretmenler"].get(t_fmt, totals["ogretmenler"].get(t_name, 0)))
            
            # Class teacher of which class (e.g. 11A) - only if actually registered in siniflar
            so_class = class_teacher_map.get(t_fmt, "")
            
            # Branch
            brans = data.get("brans", "")
            
            # Assigned subjects & classes computed in real time from atamalar
            teacher_atamalar = [a for a in self.data_store.get("atamalar", []) if format_tr_name(a.get("teacher", "")) == t_fmt]
            assignments_summary_list = []
            for a in teacher_atamalar:
                subj = a.get("subject", "")
                cls = a.get("class", "")
                dur = a.get("duration", "")
                if subj and cls:
                    assignments_summary_list.append(f"{subj} ({cls})")
                elif subj:
                    assignments_summary_list.append(subj)
            atanan_dersler_str = ", ".join(assignments_summary_list) if assignments_summary_list else "Atama Yok"
            
            zaman_str = "📅 Çizelge Göster / Yazdır"
            
            self._add_row(self.table_ogretmen, [
                t_name, data.get("kisa",""), toplam, zaman_str, so_class, brans, atanan_dersler_str
            ], timeoff=self._timeoff_matrix(data), days_cnt=len(days), periods_cnt=periods)

        # Tablolar yeniden dolduğuna göre sağ üstteki sayılar da tazelenmeli.
        self._update_count_labels()

    def _toggle_maximize_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._update_magnifier_buttons()

    def _update_magnifier_buttons(self):
        is_max = self.isMaximized()
        for b in getattr(self, "mag_buttons", []):
            if b.text():
                b.setText("  Normal Boyut (Küçült)" if is_max else "  Tam Ekran (Büyüt)")
            b.setToolTip("Normal Boyuta Döndür (Küçült)" if is_max else "Tam Ekran Yap (Büyüt)")

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            self._update_magnifier_buttons()
        super().changeEvent(event)

    def closeEvent(self, event):
        try:
            p = self.parent() or getattr(self, "main_window", None)
            if p and hasattr(p, "save_db"):
                p.save_db()
            if p and hasattr(p, "_refresh_tree"):
                p._refresh_tree()
        except Exception as e:
            print("closeEvent Exception Handled:", e)
        event.accept()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # --- Top / Center Area ---
        center_layout = QHBoxLayout()
        center_layout.setSpacing(12)
        
        # 1. Left Icons
        left_panel = QVBoxLayout()
        left_panel.setSpacing(16)
        
        self.left_btns = [
            LeftMenuButton("book"),      # idx 0 -> Dersler
            LeftMenuButton("teachers"),  # idx 1 -> Sınıflar
            LeftMenuButton("door"),      # idx 2 -> Derslikler
            LeftMenuButton("grad_hat")   # idx 3 -> Öğretmenler
        ]
        
        for i, btn in enumerate(self.left_btns):
            left_panel.addWidget(btn)
            btn.clicked.connect(lambda checked, idx=i: self._select_tab(idx))
            
        left_panel.addStretch(1)
        center_layout.addLayout(left_panel)
        
        # 2. Main Content (Stacked Widget)
        self.stack = QStackedWidget(self)
        self.stack.setStyleSheet("background: #FFFFFF; border: 1px solid #D0D0D0;")
        
        # Tables
        self.table_ders = self._create_table(["Ders Adı", "Kısa Kodu", "Toplam", "Zaman Tablosu", "Dağılım", "Max. Günlük"])
        self.stack.addWidget(self._wrap_table("Tanımlı Dersler", self.table_ders))

        self.table_sinif = self._create_table(["Sınıf Adı", "Kısa Kodu", "Toplam", "Zaman Tablosu", "Ders Bitim Saati", "Sınıf Öğretmeni", "Öğrenci"])
        self.stack.addWidget(self._wrap_table("Tanımlı Sınıflar", self.table_sinif))

        self.table_derslik = self._create_table(["Derslik Adı", "Kısa Kodu", "Toplam", "Zaman Tablosu", "Kapasite", "Bina"])
        self.stack.addWidget(self._wrap_table("Tanımlı Derslikler", self.table_derslik))

        self.table_ogretmen = self._create_table(["Öğretmen Adı", "Kısa Kodu", "Toplam", "Zaman Tablosu & Çizelge", "Sınıf Öğretmeni", "Branşı", "Atanan Dersler ve Sınıflar"])
        self.stack.addWidget(self._wrap_table("Tanımlı Öğretmenler ve Dersleri", self.table_ogretmen))
        
        center_layout.addWidget(self.stack, 1)
        
        # 3. Right Action Menu
        right_panel = QVBoxLayout()
        right_panel.setSpacing(6)
        right_panel.setContentsMargins(0, 24, 0, 0)
        
        self.btn_yeni = ActionButton("Yeni", icon_name="plus", is_primary=True)
        self.btn_yeni.clicked.connect(self._act_new)
        right_panel.addWidget(self.btn_yeni)
        self.btn_guncelle = ActionButton("Güncelle", icon_name="edit")
        self.btn_guncelle.clicked.connect(self._act_update)
        right_panel.addWidget(self.btn_guncelle)
        
        self.btn_sil = ActionButton("Sil", icon_name="minus")
        self.btn_sil.clicked.connect(self._act_delete)
        right_panel.addWidget(self.btn_sil)
        
        btn_yukari = ActionButton("Yukarı Taşı", icon_name="edit")
        btn_yukari.clicked.connect(lambda: self._act_move_row(-1))
        right_panel.addWidget(btn_yukari)
        
        btn_asagi = ActionButton("Aşağı Taşı", icon_name="edit")
        btn_asagi.clicked.connect(lambda: self._act_move_row(1))
        right_panel.addWidget(btn_asagi)
        
        right_panel.addSpacing(15)
        
        # Orijinal 2026 - 2027 Dialoglarına yönlendiren butonlar
        btn_ders_atama = ActionButton("Ders Atama", icon_name="doc")
        btn_ders_atama.clicked.connect(self._act_assign)
        right_panel.addWidget(btn_ders_atama)
        
        btn_zaman = ActionButton("Zaman Tablosu", icon_name="clock")
        btn_zaman.clicked.connect(self._act_timeoff)
        right_panel.addWidget(btn_zaman)
        
        btn_kisit = ActionButton("Kısıtlamalar", icon_name="hash")
        btn_kisit.clicked.connect(self._act_constraints)
        right_panel.addWidget(btn_kisit)
        
        self.btn_gruplar = ActionButton("Gruplar", icon_name="branch")
        self.btn_gruplar.clicked.connect(self._act_groups)
        right_panel.addWidget(self.btn_gruplar)
        
        self.btn_tumunu_sil = ActionButton("Tümünü Sil", icon_name="minus")
        self.btn_tumunu_sil.clicked.connect(self._act_delete_all)
        
        self.btn_oto_olustur = ActionButton("Otomatik Oluştur", icon_name="plus", is_primary=True)
        self.btn_oto_olustur.clicked.connect(self._act_auto_schedule)
        
        right_panel.addStretch(1)
        right_panel.addWidget(self.btn_tumunu_sil)
        right_panel.addWidget(self.btn_oto_olustur)
        
        center_layout.addLayout(right_panel)
        main_layout.addLayout(center_layout, 1)

        # --- Bottom Area ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 12, 0, 0)
        
        btn_help = QPushButton("Yardım")
        btn_help.setFixedSize(90, 32)
        btn_help.setFont(QFont("SF Pro Text", 9, QFont.Bold))
        btn_help.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; color: #334155; font-weight: 600; border-radius: 6px;")
        
        btn_undo = QPushButton("Geri Al")
        btn_undo.setFixedSize(90, 32)
        btn_undo.setFont(QFont("SF Pro Text", 9, QFont.Bold))
        btn_undo.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; color: #334155; font-weight: 600; border-radius: 6px;")
        btn_undo.clicked.connect(self._act_undo)

        btn_redo = QPushButton("Yinele")
        btn_redo.setFixedSize(90, 32)
        btn_redo.setFont(QFont("SF Pro Text", 9, QFont.Bold))
        btn_redo.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; color: #334155; font-weight: 600; border-radius: 6px;")
        btn_redo.clicked.connect(self._act_redo)

        btn_save = QPushButton("Kaydet")
        btn_save.setFixedSize(110, 32)
        btn_save.setFont(QFont("SF Pro Text", 9.5, QFont.Bold))
        btn_save.setStyleSheet("background: #0071E3; color: white; font-weight: 700; border-radius: 6px; border: none;")
        btn_save.clicked.connect(self.accept)
        
        btn_reset_classes = QPushButton("Tüm Sınıf Atamalarını Sıfırla")
        btn_reset_classes.setFixedSize(210, 32)
        btn_reset_classes.setFont(QFont("SF Pro Text", 9, QFont.Bold))
        btn_reset_classes.setStyleSheet("background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; font-weight: 600; border-radius: 6px;")
        btn_reset_classes.clicked.connect(self._reset_all_class_assignments)
        
        btn_info = QPushButton("Bilgi Al")
        btn_info.setFixedSize(90, 32)
        btn_info.setFont(QFont("SF Pro Text", 9, QFont.Bold))
        btn_info.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; color: #334155; font-weight: 600; border-radius: 6px;")
        
        btn_close = QPushButton("Kapat")
        btn_close.setFixedSize(90, 32)
        btn_close.setFont(QFont("SF Pro Text", 9, QFont.Bold))
        btn_close.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; color: #334155; font-weight: 600; border-radius: 6px;")
        btn_close.clicked.connect(self.reject)
        
        btn_mag_bottom = QPushButton("  Tam Ekran (Büyüt)")
        btn_mag_bottom.setIcon(make_edit_svg_icon("search", 15, "#334155"))
        btn_mag_bottom.setFixedHeight(32)
        btn_mag_bottom.setCursor(Qt.PointingHandCursor)
        btn_mag_bottom.setFont(QFont("SF Pro Text", 9, QFont.Bold))
        btn_mag_bottom.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; color: #334155; font-weight: 600; border-radius: 6px; padding: 0 12px;")
        btn_mag_bottom.setToolTip("Tam Ekran Yap / Normal Boyuta Dön (Büyüteç)")
        btn_mag_bottom.clicked.connect(self._toggle_maximize_restore)
        self.mag_buttons.append(btn_mag_bottom)
        
        self.btn_help = btn_help
        self.btn_undo = btn_undo
        self.btn_redo = btn_redo
        self.btn_save = btn_save
        self.btn_reset_classes = btn_reset_classes
        self.btn_info = btn_info
        
        bottom_layout.addWidget(btn_help)
        bottom_layout.addWidget(btn_undo)
        bottom_layout.addWidget(btn_redo)
        bottom_layout.addWidget(btn_save)
        bottom_layout.addWidget(btn_reset_classes)
        bottom_layout.addWidget(btn_info)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(btn_mag_bottom)
        bottom_layout.addWidget(btn_close)
        
        main_layout.addLayout(bottom_layout)

        # Keyboard shortcuts
        from PySide6.QtGui import QKeySequence, QShortcut
        QShortcut(QKeySequence("Ctrl+Z"), self, self._act_undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self._act_redo)
        
        self._update_undo_redo_ui()

    def _update_undo_redo_ui(self):
        can_undo = bool(hasattr(self, "_history_stack") and self._history_stack)
        can_redo = bool(hasattr(self, "_redo_stack") and self._redo_stack)
        if hasattr(self, "btn_undo"):
            self.btn_undo.setEnabled(can_undo)
            if can_undo:
                self.btn_undo.setStyleSheet("background: #0078D7; border: 1px solid #005A9E; color: #FFFFFF; font-weight: bold; border-radius: 4px;")
            else:
                self.btn_undo.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; color: #94A3B8; font-weight: bold; border-radius: 4px;")
        if hasattr(self, "btn_redo"):
            self.btn_redo.setEnabled(can_redo)
            if can_redo:
                self.btn_redo.setStyleSheet("background: #0078D7; border: 1px solid #005A9E; color: #FFFFFF; font-weight: bold; border-radius: 4px;")
            else:
                self.btn_redo.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; color: #94A3B8; font-weight: bold; border-radius: 4px;")
        # Yığın ana pencereyle PAYLAŞILIYOR (bkz. __init__: self._history_stack
        # = parent._history_stack). Sheet içinde yapılan her itme şeritteki
        # Geri Al düğmesini de canlandırmalı; yoksa sheet kapandığında şerit
        # dolu bir yığınla soluk kalıyor.
        mw = getattr(self, "main_window", None)
        if mw is not None and hasattr(mw, "_update_undo_redo_ui"):
            try:
                mw._update_undo_redo_ui()
            except Exception:
                pass

    def _sync_class_teacher_two_way(self):
        """
        Ensure 100% two-way consistency between siniflar and ogretmenler:
        If class C has sinif_ogretmeni = T, teacher T must have sinif_ogretmeni = C.
        If teacher T has sinif_ogretmeni = C, class C must have sinif_ogretmeni = T.
        """
        from auto_scheduler import format_tr_name
        siniflar = self.data_store.get("siniflar", [])
        ogretmenler = self.data_store.get("ogretmenler", [])
        
        # 1. Map from siniflar: teacher_fmt -> class_name
        teacher_to_class = {}
        for s in siniflar:
            so = s.get("sinif_ogretmeni")
            if so and str(so).strip():
                teacher_to_class[format_tr_name(str(so))] = s.get("ad", "")
                
        # 2. Map from ogretmenler: class_name -> teacher_name
        class_to_teacher = {}
        for t in ogretmenler:
            soc = t.get("sinif_ogretmeni")
            if soc and str(soc).strip():
                class_to_teacher[str(soc).strip()] = t.get("ad", "")
                
        # Reconcile: If teacher has class assignment, set in siniflar
        for c_name, t_name in class_to_teacher.items():
            for s in siniflar:
                if s.get("ad", "").strip() == c_name:
                    s["sinif_ogretmeni"] = t_name
                    teacher_to_class[format_tr_name(t_name)] = c_name
                    break
                    
        # Update all teachers based on teacher_to_class
        for t in ogretmenler:
            t_fmt = format_tr_name(t.get("ad", ""))
            assigned_cls = teacher_to_class.get(t_fmt, "")
            t["sinif_ogretmeni"] = assigned_cls

    def _notify_main_window_refresh(self):
        win = getattr(self, "main_window", None) or self.parent() or self.window()
        if not win or not hasattr(win, "_grid"):
            p = self.parent()
            while p:
                if hasattr(p, "_grid"):
                    win = p
                    break
                p = p.parent()
        if win:
            if hasattr(win, "data_store") and win.data_store is not self.data_store:
                win.data_store.clear()
                win.data_store.update(self.data_store)
            if hasattr(win, "save_db") and callable(getattr(win, "save_db")):
                try:
                    win.save_db(sync_from_grid=False)
                except Exception as e:
                    print("save_db error:", e)
            if hasattr(win, "_refresh_tree") and callable(getattr(win, "_refresh_tree")):
                try:
                    win._refresh_tree()
                except Exception as e:
                    print("_refresh_tree error:", e)
            if hasattr(win, "_load_unplaced_lessons") and callable(getattr(win, "_load_unplaced_lessons")):
                try:
                    win._load_unplaced_lessons()
                except Exception as e:
                    print("_load_unplaced_lessons error:", e)
            if hasattr(win, "_restore_grid_placements") and callable(getattr(win, "_restore_grid_placements")):
                try:
                    win._restore_grid_placements()
                except Exception as e:
                    print("_restore_grid_placements error:", e)
            if hasattr(win, "_refresh_unplaced_lessons") and callable(getattr(win, "_refresh_unplaced_lessons")):
                try:
                    win._refresh_unplaced_lessons()
                except Exception as e:
                    print("_refresh_unplaced_lessons error:", e)
            if hasattr(win, "_refresh_grid") and callable(getattr(win, "_refresh_grid")):
                try:
                    win._refresh_grid()
                except Exception as e:
                    print("_refresh_grid error:", e)

    def _push_undo_state(self):
        import copy
        if not hasattr(self, "_history_stack"): self._history_stack = []
        if not hasattr(self, "_redo_stack"): self._redo_stack = []
        if self._history_stack and self._history_stack[-1] == self.data_store:
            return
        if len(self._history_stack) > 50:
            self._history_stack.pop(0)
        self._history_stack.append(copy.deepcopy(self.data_store))
        self._redo_stack.clear()
        self._update_undo_redo_ui()

    def _push_undo_snapshot(self, snapshot):
        import copy
        if snapshot is None:
            return
        if not hasattr(self, "_history_stack"): self._history_stack = []
        if not hasattr(self, "_redo_stack"): self._redo_stack = []
        if self._history_stack and self._history_stack[-1] == snapshot:
            return
        if len(self._history_stack) > 50:
            self._history_stack.pop(0)
        self._history_stack.append(copy.deepcopy(snapshot))
        self._redo_stack.clear()
        self._update_undo_redo_ui()

    def _act_undo(self):
        import copy
        if hasattr(self, "_history_stack") and self._history_stack:
            prev_state = self._history_stack.pop()

            removed_entities = []
            if not check_undo_removes_assigned_entity(self, self.data_store, prev_state, out_removed_entities=removed_entities):
                self._history_stack.append(prev_state)
                self._update_undo_redo_ui()
                return

            if not hasattr(self, "_redo_stack"): self._redo_stack = []
            self._redo_stack.append(copy.deepcopy(self.data_store))

            self.data_store.clear()
            self.data_store.update(prev_state)
            for etype, ename in removed_entities:
                purge_entity_references(self.data_store, etype, ename)
            self._sync_class_teacher_two_way()
            if hasattr(self, "_load_existing_data"):
                self._load_existing_data()
            self._notify_main_window_refresh()
            self._update_undo_redo_ui()
            win = self.window() or self.parent()
            if win and hasattr(win, "statusBar") and callable(getattr(win, "statusBar")):
                sb = win.statusBar()
                if sb: sb.showMessage("↺ Yapılan son işlem başarıyla geri alındı.")
        else:
            self._update_undo_redo_ui()
            win = self.window() or self.parent()
            if win and hasattr(win, "statusBar") and callable(getattr(win, "statusBar")):
                sb = win.statusBar()
                if sb: sb.showMessage("⚠️ Geri alınacak başka işlem yok.")

    def _act_redo(self):
        import copy
        if hasattr(self, "_redo_stack") and self._redo_stack:
            next_state = self._redo_stack.pop()

            if not hasattr(self, "_history_stack"): self._history_stack = []
            self._history_stack.append(copy.deepcopy(self.data_store))

            self.data_store.clear()
            self.data_store.update(next_state)
            self._sync_class_teacher_two_way()
            if hasattr(self, "_load_existing_data"):
                self._load_existing_data()
            self._notify_main_window_refresh()
            self._update_undo_redo_ui()
            win = self.window() or self.parent()
            if win and hasattr(win, "statusBar") and callable(getattr(win, "statusBar")):
                sb = win.statusBar()
                if sb: sb.showMessage("↻ İşlem başarıyla tekrar uygulandı.")
        else:
            self._update_undo_redo_ui()
            win = self.window() or self.parent()
            if win and hasattr(win, "statusBar") and callable(getattr(win, "statusBar")):
                sb = win.statusBar()
                if sb: sb.showMessage("⚠️ Yinelenecek başka işlem yok.")

    def _reset_all_class_assignments(self):
        test_mode = getattr(self, "_test_mode", False) or getattr(getattr(self, "main_window", None), "_test_mode", False)
        if not test_mode:
            r = QMessageBox.question(
                self,
                "Tüm Sınıf Atamalarını Sıfırla",
                "TÜM sınıflara ait ders ve öğretmen görevlendirmeleri tamamen silinecektir.\n\nEmin misiniz?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
        else:
            r = QMessageBox.Yes
        if r == QMessageBox.Yes:
            self._push_undo_state()
            self.data_store["atamalar"] = []
            self.data_store["grid_placements"] = []
            self.data_store["yerlesim"] = {}
            if hasattr(self, "_load_existing_data"):
                self._load_existing_data()
            self._notify_main_window_refresh()
            if not test_mode:
                QMessageBox.information(self, "Başarılı", "Tüm sınıf atamaları başarıyla sıfırlandı.")

    def _create_table(self, headers):
        t = DragDropTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.verticalHeader().setDefaultSectionSize(44)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E2E8F0;
                background-color: #FFFFFF;
                alternate-background-color: #F8FAFC;
                gridline-color: #E2E8F0;
                font-size: 10pt;
                font-weight: 500;
                color: #0F172A;
                selection-background-color: #E0F2FE;
                selection-color: #0369A1;
            }
            QTableWidget::item {
                /* Dikey iç boşluk 8'di: 40 piksellik satırdan 16 piksel yiyor,
                   Zaman Tablosu önizlemesine 24 piksel kalıyor ve kutunun altı
                   (son 2-3 ders saati) kırpılıyordu. */
                padding: 4px 12px;
                border-bottom: 1px solid #E2E8F0;
            }
            QHeaderView::section {
                background-color: #F1F5F9;
                color: #334155;
                border: none;
                border-bottom: 2px solid #CBD5E1;
                padding: 10px 12px;
                font-weight: 700;
                font-size: 10pt;
            }
        """)
        t.cellDoubleClicked.connect(self._on_table_double_clicked)
        t.cellClicked.connect(self._on_table_clicked)
        t.row_dropped.connect(self._on_row_dropped)
        return t

    def _on_row_dropped(self, start, dest):
        idx = self.stack.currentIndex()
        stores = ["dersler", "siniflar", "derslikler", "ogretmenler"]
        data_list = self.data_store.get(stores[idx], [])
        if 0 <= start < len(data_list):
            dest = max(0, min(dest, len(data_list) - 1))
            if start != dest:
                self._push_undo_state()
                # Pop and insert manually in memory
                item = data_list.pop(start)
                data_list.insert(dest, item)
                
                # Re-render UI table to match memory
                self._load_existing_data()
                
                # Highlight newly moved row
                tables = [self.table_ders, self.table_sinif, self.table_derslik, self.table_ogretmen]
                t = tables[idx]
                t.selectRow(dest)
                
                self._notify_main_window_refresh()

    def _on_table_clicked(self, row, col):
        pass # Let row selection happen naturally

    def _on_table_double_clicked(self, row, col):
        idx = self.stack.currentIndex()
        if col == 3: # Zaman Tablosu column (for any entity)
            self._act_timeoff()
            return
        self._act_update()
        return

    def _wrap_table(self, title, table):
        from PySide6.QtWidgets import QLineEdit
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(4, 4, 4, 4)
        l.setSpacing(4)
        
        top_bar = QHBoxLayout()
        lbl = QLabel(title)
        lbl.setFont(QFont(FONT_FAMILY, 9, QFont.Weight.Bold))
        lbl.setStyleSheet("padding: 4px;")
        top_bar.addWidget(lbl)
        top_bar.addStretch(1)

        # Sağ üstte özet: "16 öğretmen · 128 saat". Çıplak (nude) — kutu, çerçeve,
        # dolgu yok; yalnız gri ince yazı. Solunda tooltip taşıyan bir bilgi
        # simgesi var, sayının neyi saydığı oradan okunuyor. Sekme sırasıyla
        # saklanıyor (Dersler, Sınıflar, Derslikler, Öğretmenler);
        # _load_existing_data her veri değişiminde tazeliyor.
        info_icon = QLabel("ⓘ")
        info_icon.setFont(QFont(FONT_FAMILY, 10))
        info_icon.setStyleSheet("color: #94A3B8; background: transparent; border: none;")
        info_icon.setCursor(Qt.WhatsThisCursor)

        count_lbl = QLabel("")
        count_lbl.setFont(QFont(FONT_FAMILY, 9))
        count_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")

        if not hasattr(self, "count_labels"):
            self.count_labels = []
            self.count_icons = []
        self.count_labels.append(count_lbl)
        self.count_icons.append(info_icon)

        top_bar.addWidget(info_icon)
        top_bar.addSpacing(5)
        top_bar.addWidget(count_lbl)
        top_bar.addSpacing(12)

        txt_search = QLineEdit()
        txt_search.setPlaceholderText("Gerçek Zamanlı Ara...")
        txt_search.setFixedWidth(220)
        txt_search.setStyleSheet("padding: 4px 8px; border: 1px solid #CCCCCC; border-radius: 4px; font-size: 9pt; background: #FFFFFF;")
        
        btn_sort = QPushButton("A-Z Sırala")
        btn_sort.setFixedHeight(28)
        btn_sort.setStyleSheet("background: #E0E0E0; border: 1px solid #CCC; border-radius: 4px; padding: 0 10px; font-weight: bold;")
        
        def do_sort():
            idx = self.stack.currentIndex()
            stores = ["dersler", "siniflar", "derslikler", "ogretmenler"]
            data_list = self.data_store.get(stores[idx], [])
            
            import re
            def smart_sort(item):
                name = item.get("ad", "") if isinstance(item, dict) else ""
                parts = re.split(r'(\d+)', name)
                return [int(p) if p.isdigit() else p.lower() for p in parts]
                
            self._push_undo_state()
            data_list.sort(key=smart_sort)
            self._load_existing_data()
            self._notify_main_window_refresh()
            
        btn_sort.clicked.connect(do_sort)
        
        top_bar.addWidget(btn_sort)
        
        def do_filter(text):
            query = text.strip().lower()
            for r in range(table.rowCount()):
                match = False
                for c in range(table.columnCount()):
                    item = table.item(r, c)
                    if item and query in item.text().lower():
                        match = True
                        break
                table.setRowHidden(r, not match)
                
        txt_search.textChanged.connect(do_filter)
        top_bar.addWidget(txt_search)
        
        btn_mag = QPushButton()
        btn_mag.setFixedSize(28, 28)
        btn_mag.setCursor(Qt.PointingHandCursor)
        btn_mag.setIcon(make_edit_svg_icon("search", 15, "#1E293B"))
        btn_mag.setToolTip("Tam Ekran Yap / Normal Boyuta Dön (Büyüteç)")
        btn_mag.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #F1F5F9;
                border-color: #94A3B8;
            }
        """)
        btn_mag.clicked.connect(self._toggle_maximize_restore)
        self.mag_buttons.append(btn_mag)
        top_bar.addWidget(btn_mag)
        
        l.addLayout(top_bar)
        l.addWidget(table, 1)
        return w

    def _select_tab(self, idx):
        # Update left buttons
        for i, btn in enumerate(self.left_btns):
            btn.setChecked(i == idx)
            
        self.stack.setCurrentIndex(idx)
        
        titles = ["Dersler", "Sınıflar", "Derslikler", "Öğretmenler"]
        self.setWindowTitle(titles[idx])
        
        # Enable/Disable right panel buttons based on context if necessary
        # All actions are kept enabled for now as they are universally valid in this design

    def _act_assign(self, teacher_name=None):
        import copy
        snapshot = copy.deepcopy(self.data_store)
        idx = self.stack.currentIndex()
        if idx == 1:  # Sınıflar tab
            r = self.table_sinif.currentRow()
            c_name = ""
            if r >= 0:
                item = self.table_sinif.item(r, 0)
                if item: c_name = item.text().strip()
            if not c_name:
                from PySide6.QtWidgets import QInputDialog
                classes = [c.get("ad", "") for c in self.data_store.get("siniflar", []) if c.get("ad")]
                if classes:
                    c_choice, ok = QInputDialog.getItem(self, "Sınıfın Dersleri", "Derslerini Düzenleyeceğiniz Sınıfı Seçin:", sorted(classes), 0, False)
                    if ok and c_choice: c_name = c_choice
            if c_name:
                from dialogs.edit_forms import ClassComprehensiveAssignmentDialog
                d = ClassComprehensiveAssignmentDialog(class_name=c_name, data_store=self.data_store, parent=self)
                if d.exec():
                    if self.data_store != snapshot:
                        self._push_undo_snapshot(snapshot)
                    self._load_existing_data()
                    self._notify_main_window_refresh()
                return

        from dialogs.edit_forms import LessonAssignmentDialog
        if not teacher_name and hasattr(self, "table_ogretmen"):
            r = self.table_ogretmen.currentRow()
            if r >= 0:
                item = self.table_ogretmen.item(r, 0)
                if item: teacher_name = item.text()
                
        d = LessonAssignmentDialog(data_store=self.data_store, parent=self, selected_teacher=teacher_name)
        if d.exec():
            if self.data_store != snapshot:
                self._push_undo_snapshot(snapshot)
            self._load_existing_data()
            self._notify_main_window_refresh()

    def _act_new(self):
        import copy
        snapshot = copy.deepcopy(self.data_store)
        idx = self.stack.currentIndex()
        saved = False
        if idx == 0:  # Dersler
            d = DersEditDialog(self)
            if d.exec():
                data = d.get_data()
                self.data_store["dersler"].append(data)
                saved = True
        elif idx == 1:  # Sınıflar
            d = SinifEditDialog(self)
            if d.exec():
                data = d.get_data()
                self.data_store["siniflar"].append(data)
                c_name = data.get("ad", "").strip()
                new_so = data.get("sinif_ogretmeni", "").strip()
                if new_so:
                    for s in self.data_store.get("siniflar", [])[:-1]:
                        if format_tr_name(s.get("sinif_ogretmeni", "")) == format_tr_name(new_so):
                            s["sinif_ogretmeni"] = ""
                    for t in self.data_store.get("ogretmenler", []):
                        if format_tr_name(t.get("ad", "")) == format_tr_name(new_so):
                            t["sinif_ogretmeni"] = c_name
                        elif t.get("sinif_ogretmeni", "").strip().upper() == c_name.upper():
                            t["sinif_ogretmeni"] = ""
                saved = True
        elif idx == 2:  # Derslikler
            d = DerslikEditDialog(self)
            if d.exec():
                data = d.get_data()
                self.data_store["derslikler"].append(data)
                saved = True
        elif idx == 3:  # Öğretmenler
            d = OgretmenEditDialog(self)
            if d.exec():
                data = d.get_data()
                self.data_store["ogretmenler"].append(data)
                t_name = data.get("ad", "").strip()
                new_class = data.get("sinif_ogretmeni", "").strip()
                if new_class:
                    for t in self.data_store.get("ogretmenler", [])[:-1]:
                        if t.get("sinif_ogretmeni", "").strip().upper() == new_class.upper():
                            t["sinif_ogretmeni"] = ""
                    for s in self.data_store.get("siniflar", []):
                        if s.get("ad", "").strip().upper() == new_class.upper():
                            s["sinif_ogretmeni"] = t_name
                        elif format_tr_name(s.get("sinif_ogretmeni", "")) == format_tr_name(t_name):
                            s["sinif_ogretmeni"] = ""
                # Push snapshot for teacher creation first so teacher creation and its assignments are separate undo steps
                self._push_undo_snapshot(snapshot)
                self._load_existing_data()
                self._notify_main_window_refresh()
                self._act_assign(teacher_name=data.get("ad"))
                return

        if saved:
            self._push_undo_snapshot(snapshot)
            self._load_existing_data()
            self._notify_main_window_refresh()

    def _act_update(self):
        idx = self.stack.currentIndex()
        tables = [self.table_ders, self.table_sinif, self.table_derslik, self.table_ogretmen]
        stores = ["dersler", "siniflar", "derslikler", "ogretmenler"]
        dialogs = [DersEditDialog, SinifEditDialog, DerslikEditDialog, OgretmenEditDialog]
        
        table = tables[idx]
        row = table.currentRow()
        if row < 0:
            return
            
        item = table.item(row, 0)
        if not item:
            return
        selected_name = item.text().strip()
        
        data_list = self.data_store[stores[idx]]
        matched_idx = -1
        old_data = None
        for i, d in enumerate(data_list):
            if d.get("ad") == selected_name or d.get("kisa") == selected_name:
                matched_idx = i
                old_data = d
                break
                
        if matched_idx >= 0 and old_data:
            import copy
            snapshot = copy.deepcopy(self.data_store)
            d = dialogs[idx](parent=self, existing_data=old_data)
            if d.exec():
                new_data = d.get_data()
                old_name = old_data.get("ad")
                new_name = new_data.get("ad")
                old_color = old_data.get("renk")
                new_color = new_data.get("renk")

                if old_name and new_name and old_name != new_name:
                    key_map = {0: "subject", 1: "class", 3: "teacher"}
                    if idx == 3:
                        from version_store import rename_teacher_in_data_store
                        rename_teacher_in_data_store(self.data_store, old_name, new_name)
                    elif idx in key_map:
                        attr = key_map[idx]
                        for a in self.data_store.get("atamalar", []):
                            if a.get(attr) == old_name:
                                a[attr] = new_name
                            if idx == 1 and isinstance(a.get("combined_classes"), list):
                                a["combined_classes"] = [new_name if c == old_name else c for c in a["combined_classes"]]
                        for p in self.data_store.get("grid_placements", []):
                            if idx == 0:
                                if p.get("subject_name") == old_name or p.get("subject") == old_name:
                                    p["subject_name"] = new_name
                                    p["subject"] = new_name
                            elif idx == 1:
                                if p.get("class_name") == old_name or p.get("class") == old_name:
                                    p["class_name"] = new_name
                                    p["class"] = new_name
                        for p in self.data_store.get("auto_schedule_results", []):
                            if idx == 0:
                                if p.get("subject_name") == old_name or p.get("subject") == old_name:
                                    p["subject_name"] = new_name
                                    p["subject"] = new_name
                            elif idx == 1:
                                if p.get("class_name") == old_name or p.get("class") == old_name:
                                    p["class_name"] = new_name
                                    p["class"] = new_name

                if idx == 0:
                    target_subj = new_name or old_name
                    target_col = new_color or old_color
                    if target_subj and target_col:
                        from dialogs.color_picker_dialog import update_subject_color_globally
                        update_subject_color_globally(self, self.data_store, target_subj, target_col)

                # Specific Two-Way Sync for Classes
                if idx == 1:
                    c_name = new_data.get("ad", "").strip()
                    new_so = new_data.get("sinif_ogretmeni", "").strip()
                    if new_so:
                        for s in self.data_store.get("siniflar", []):
                            if s is not data_list[matched_idx] and format_tr_name(s.get("sinif_ogretmeni", "")) == format_tr_name(new_so):
                                s["sinif_ogretmeni"] = ""
                        for t in self.data_store.get("ogretmenler", []):
                            if format_tr_name(t.get("ad", "")) == format_tr_name(new_so):
                                t["sinif_ogretmeni"] = c_name
                            elif t.get("sinif_ogretmeni", "").strip().upper() == c_name.upper():
                                t["sinif_ogretmeni"] = ""
                    else:
                        for t in self.data_store.get("ogretmenler", []):
                            if t.get("sinif_ogretmeni", "").strip().upper() == c_name.upper():
                                t["sinif_ogretmeni"] = ""

                # Specific Two-Way Sync for Teachers
                elif idx == 3:
                    t_name = new_data.get("ad", "").strip()
                    new_class = new_data.get("sinif_ogretmeni", "").strip()
                    if new_class:
                        for t in self.data_store.get("ogretmenler", []):
                            if t is not data_list[matched_idx] and t.get("sinif_ogretmeni", "").strip().upper() == new_class.upper():
                                t["sinif_ogretmeni"] = ""
                        for s in self.data_store.get("siniflar", []):
                            if s.get("ad", "").strip().upper() == new_class.upper():
                                s["sinif_ogretmeni"] = t_name
                            elif format_tr_name(s.get("sinif_ogretmeni", "")) == format_tr_name(t_name):
                                s["sinif_ogretmeni"] = ""
                    else:
                        for s in self.data_store.get("siniflar", []):
                            if format_tr_name(s.get("sinif_ogretmeni", "")) == format_tr_name(t_name):
                                s["sinif_ogretmeni"] = ""

                data_list[matched_idx] = new_data
                if self.data_store != snapshot:
                    self._push_undo_snapshot(snapshot)
                self._load_existing_data()
                self._notify_main_window_refresh()

    def _act_delete(self):
        from PySide6.QtWidgets import QMessageBox
        from auto_scheduler import matches_class, format_tr_name
        idx = self.stack.currentIndex()
        tables = [self.table_ders, self.table_sinif, self.table_derslik, self.table_ogretmen]
        stores = ["dersler", "siniflar", "derslikler", "ogretmenler"]
        
        table = tables[idx]
        row = table.currentRow()
        if row >= 0:
            item = table.item(row, 0)
            if not item: return
            del_name = item.text().strip()
            del_fmt = format_tr_name(del_name)
            if not getattr(self, "_test_mode", False) and not getattr(getattr(self, "main_window", None), "_test_mode", False):
                r = QMessageBox.question(self, "Silme Onayı", f"'{del_name}' kaydını ve bağlı tüm atama/program verilerini silmek istediğinize emin misiniz?", QMessageBox.Yes | QMessageBox.No)
            else:
                r = QMessageBox.Yes
            if r == QMessageBox.Yes:
                self._push_undo_state()
                data_list = self.data_store[stores[idx]]
                self.data_store[stores[idx]] = [d for d in data_list if format_tr_name(d.get("ad", "")) != del_fmt and d.get("kisa") != del_name]
                
                if idx == 3: # Teacher
                    from version_store import _matches_teacher
                    self.data_store["atamalar"] = [
                        a for a in self.data_store.get("atamalar", [])
                        if not _matches_teacher(a.get("teacher", ""), del_name) and format_tr_name(a.get("teacher", "")) != del_fmt
                    ]
                    self.data_store["grid_placements"] = [
                        p for p in self.data_store.get("grid_placements", [])
                        if not _matches_teacher(p.get("teacher_name") or p.get("teacher", ""), del_name) and format_tr_name(p.get("teacher_name") or p.get("teacher", "")) != del_fmt
                    ]
                    # Clean yerlesim dict
                    yerlesim = self.data_store.get("yerlesim", {})
                    if isinstance(yerlesim, dict):
                        for k in list(yerlesim.keys()):
                            info = yerlesim[k]
                            if isinstance(info, dict) and (_matches_teacher(info.get("teacher_name") or info.get("teacher", ""), del_name) or format_tr_name(info.get("teacher_name") or info.get("teacher", "")) == del_fmt):
                                yerlesim.pop(k, None)
                    if "auto_schedule_results" in self.data_store:
                        self.data_store["auto_schedule_results"] = [
                            p for p in self.data_store.get("auto_schedule_results", [])
                            if not _matches_teacher(p.get("teacher_name") or p.get("teacher", ""), del_name) and format_tr_name(p.get("teacher_name") or p.get("teacher", "")) != del_fmt
                        ]
                    # Clear class teacher references in siniflar
                    for s in self.data_store.get("siniflar", []):
                        if format_tr_name(str(s.get("sinif_ogretmeni", ""))) == del_fmt or _matches_teacher(str(s.get("sinif_ogretmeni", "")), del_name):
                            s["sinif_ogretmeni"] = ""
                    # Remove teacher constraints
                    if "kisitlamalar" in self.data_store:
                        self.data_store["kisitlamalar"].pop(del_name, None)
                        self.data_store["kisitlamalar"].pop(del_fmt, None)
                        
                elif idx == 0: # Subject
                    self.data_store["atamalar"] = [
                        a for a in self.data_store.get("atamalar", [])
                        if format_tr_name(a.get("subject", "")) != del_fmt
                    ]
                    self.data_store["grid_placements"] = [
                        p for p in self.data_store.get("grid_placements", [])
                        if format_tr_name(p.get("subject_name") or p.get("subject", "")) != del_fmt
                    ]
                    yerlesim = self.data_store.get("yerlesim", {})
                    if isinstance(yerlesim, dict):
                        for k in list(yerlesim.keys()):
                            info = yerlesim[k]
                            if isinstance(info, dict) and format_tr_name(info.get("subject_name") or info.get("subject", "")) == del_fmt:
                                yerlesim.pop(k, None)
                    if "auto_schedule_results" in self.data_store:
                        self.data_store["auto_schedule_results"] = [
                            p for p in self.data_store.get("auto_schedule_results", [])
                            if format_tr_name(p.get("subject_name") or p.get("subject", "")) != del_fmt
                        ]
                        
                elif idx == 1: # Class
                    self.data_store["atamalar"] = [
                        a for a in self.data_store.get("atamalar", [])
                        if not (matches_class(a.get("class", ""), del_name) or a.get("class") == del_name or
                                (isinstance(a.get("combined_classes"), list) and del_name in a["combined_classes"]))
                    ]
                    self.data_store["grid_placements"] = [
                        p for p in self.data_store.get("grid_placements", [])
                        if not (matches_class(p.get("class_name") or p.get("class", ""), del_name) or
                                (isinstance(p.get("combined_classes"), list) and del_name in p["combined_classes"]))
                    ]
                    yerlesim = self.data_store.get("yerlesim", {})
                    if isinstance(yerlesim, dict):
                        for k in list(yerlesim.keys()):
                            info = yerlesim[k]
                            if isinstance(info, dict) and (matches_class(info.get("class_name") or info.get("class", ""), del_name) or
                                                           (isinstance(info.get("combined_classes"), list) and del_name in info["combined_classes"])):
                                yerlesim.pop(k, None)
                    if "auto_schedule_results" in self.data_store:
                        self.data_store["auto_schedule_results"] = [
                            p for p in self.data_store.get("auto_schedule_results", [])
                            if not (matches_class(p.get("class_name") or p.get("class", ""), del_name) or
                                    (isinstance(p.get("combined_classes"), list) and del_name in p["combined_classes"]))
                        ]
                    # Clear class teacher on teachers if this class is deleted
                    for t in self.data_store.get("ogretmenler", []):
                        if t.get("sinif_ogretmeni", "").strip().upper() == del_name.upper():
                            t["sinif_ogretmeni"] = ""
                
                self._load_existing_data()
                self._notify_main_window_refresh()

    def _refresh_unplaced_lessons(self, *args, **kwargs):
        p = self.parent() or getattr(self, "main_window", None)
        if p and hasattr(p, "_refresh_unplaced_lessons"):
            p._refresh_unplaced_lessons(*args, **kwargs)

    def _refresh_grid(self, *args, **kwargs):
        p = self.parent() or getattr(self, "main_window", None)
        if p and hasattr(p, "_refresh_grid"):
            p._refresh_grid(*args, **kwargs)

    def _refresh_tree(self, *args, **kwargs):
        p = self.parent() or getattr(self, "main_window", None)
        if p and hasattr(p, "_refresh_tree"):
            p._refresh_tree(*args, **kwargs)

    def _restore_grid_placements(self, *args, **kwargs):
        p = self.parent() or getattr(self, "main_window", None)
        if p and hasattr(p, "_restore_grid_placements"):
            p._restore_grid_placements(*args, **kwargs)

    def _act_timeoff(self):
        idx = self.stack.currentIndex()
        tables = [self.table_ders, self.table_sinif, self.table_derslik, self.table_ogretmen]
        stores = ["dersler", "siniflar", "derslikler", "ogretmenler"]
        names = ["Ders", "Sınıf", "Derslik", "Öğretmen"]
        
        table = tables[idx]
        if idx == 0:
            QMessageBox.warning(self, "Hata", "Dersler için zaman tablosu ayarlanamaz.")
            return
            
        r = table.currentRow()
        if r < 0:
            QMessageBox.warning(self, "Hata", "Lütfen listeden bir kayıt seçin.")
            return
            
        raw_text = table.item(r, 0).text()
        entity = None
        for e in self.data_store.get(stores[idx], []):
            if str(e.get("id")) == raw_text or e.get("ad") == raw_text or e.get("name") == raw_text:
                entity = e
                break
                
        if not entity and self.data_store.get(stores[idx]):
            if r < len(self.data_store[stores[idx]]):
                entity = self.data_store[stores[idx]][r]
        
        if entity:
            import copy
            snapshot = copy.deepcopy(self.data_store)
            from dialogs.timeoff_dialog import TimeoffDialog
            dlg = TimeoffDialog(entity, names[idx], self.data_store, self)
            if dlg.exec() == QDialog.Accepted:
                if self.data_store != snapshot:
                    self._push_undo_snapshot(snapshot)
                
                # Anlık UI yenileme
                self.table_ders.setRowCount(0)
                self.table_sinif.setRowCount(0)
                self.table_derslik.setRowCount(0)
                self.table_ogretmen.setRowCount(0)
                self._load_existing_data()
                self._notify_main_window_refresh()

    def _act_constraints(self):
        import copy
        snapshot = copy.deepcopy(self.data_store)
        from dialogs.constraints_dialog import ConstraintsDialog
        idx = self.stack.currentIndex()
        target_type = "ogretmen" if idx == 3 else "sinif"
        table = self.table_ogretmen if idx == 3 else self.table_sinif
        r = table.currentRow()
        preselected_name = ""
        if r >= 0 and table.item(r, 0):
            preselected_name = table.item(r, 0).text().strip()
            
        dlg = ConstraintsDialog(self.data_store, target_type=target_type, parent=self, preselected_name=preselected_name)
        if dlg.exec():
            if self.data_store != snapshot:
                self._push_undo_snapshot(snapshot)
            self._load_existing_data()
            self._notify_main_window_refresh()

    def _act_delete_all(self):
        from PySide6.QtWidgets import QMessageBox
        idx = self.stack.currentIndex()
        tables = [self.table_ders, self.table_sinif, self.table_derslik, self.table_ogretmen]
        stores = ["dersler", "siniflar", "derslikler", "ogretmenler"]
        names = ["derslerin", "sınıfların", "dersliklerin", "öğretmenlerin"]
        
        test_mode = getattr(self, "_test_mode", False) or getattr(getattr(self, "main_window", None), "_test_mode", False)
        if not test_mode:
            r = QMessageBox.question(
                self, "Tümünü Sil Onayı",
                f"Tanımlı tüm {names[idx]} listesini silmek istediğinize emin misiniz?",
                QMessageBox.Yes | QMessageBox.No
            )
        else:
            r = QMessageBox.Yes
        if r == QMessageBox.Yes:
            self._push_undo_state()
            tables[idx].setRowCount(0)
            self.data_store[stores[idx]] = []
            if stores[idx] in ("dersler", "siniflar", "ogretmenler"):
                self.data_store["atamalar"] = []
                self.data_store["grid_placements"] = []
                self.data_store["yerlesim"] = {}
                if "auto_schedule_results" in self.data_store:
                    self.data_store["auto_schedule_results"] = []
            elif stores[idx] == "derslikler":
                for a in self.data_store.get("atamalar", []):
                    a["room"] = ""
                for p in self.data_store.get("grid_placements", []):
                    p["room_name"] = ""
                yerlesim = self.data_store.get("yerlesim", {})
                if isinstance(yerlesim, dict):
                    for info in yerlesim.values():
                        if isinstance(info, dict):
                            info["room"] = ""
            self._load_existing_data()
            self._notify_main_window_refresh()

    def _act_groups(self):
        from dialogs.groups_dialog import GroupsDialog
        dlg = GroupsDialog(self.data_store, self)
        dlg.exec()

    def _act_auto_schedule(self):
        import copy
        snapshot = copy.deepcopy(self.data_store)
        from dialogs.auto_schedule_dialog import AutoScheduleDialog
        dlg = AutoScheduleDialog(self.data_store, self)
        if dlg.exec():
            if self.data_store != snapshot:
                self._push_undo_snapshot(snapshot)
            self._load_existing_data()
            self._notify_main_window_refresh()

    def _open_2025_dialog(self, dlg_id):
        from dialogs.extracted_dialog import open_extracted_dialog
        open_extracted_dialog(dlg_id, self)

    def accept(self):
        try:
            self._notify_main_window_refresh()
        except Exception as e:
            print("accept Exception Handled:", e)
        super().accept()

    def reject(self):
        try:
            self._notify_main_window_refresh()
        except Exception as e:
            print("reject Exception Handled:", e)
        super().reject()

    def closeEvent(self, event):
        try:
            self._notify_main_window_refresh()
        except Exception as e:
            print("closeEvent Exception Handled:", e)
        super().closeEvent(event)

    def _act_move_row(self, direction):
        idx = self.stack.currentIndex()
        tables = [self.table_ders, self.table_sinif, self.table_derslik, self.table_ogretmen]
        stores = ["dersler", "siniflar", "derslikler", "ogretmenler"]
        table = tables[idx]
        row = table.currentRow()
        if row < 0:
            return
        target_row = row + direction
        data_list = self.data_store.get(stores[idx], [])
        if 0 <= target_row < len(data_list) and 0 <= row < len(data_list):
            self._push_undo_state()
            data_list[row], data_list[target_row] = data_list[target_row], data_list[row]
            self._load_existing_data()
            table.setCurrentCell(target_row, 0)
            self._notify_main_window_refresh()

    def _timeoff_matrix(self, entity):
        """Mini önizlemenin çizeceği matris — Zaman Tablosu diyalogunun okuduğunun AYNISI.

        Önizleme eskiden entity["timeoff"] listesini ham okuyordu; diyalog ise
        constraint_sync.get_matrix() kullanıyordu. İki okuyucu üç noktada ayrılıyordu:
        kayıtlı dizi ekrandaki saat sayısından kısaysa önizleme eksik saatleri
        "açık" sayıyor, kişisel kısıtları hiç görmüyor, "timeoff" yokken
        kisitlamalar'a düşmüyordu. Sonuç: kapatılan son saat önizlemede yeşil
        kalıyordu. Artık tek kaynak var.
        """
        try:
            import constraint_sync
            name = (entity.get("ad") or entity.get("name") or "").strip()
            return constraint_sync.get_matrix(entity, name, self.data_store)
        except Exception as exc:
            print(f"[MINI_TIMEOFF] matris okunamadi: {exc}")
            return entity.get("timeoff") or []

    # Zaman Tablosu hücresinde kutunun etrafına bırakılan pay: QTableWidget::item
    # dikey iç boşluğu (4+4) + alt kenar çizgisi + emniyet payı.
    TIMEOFF_CELL_PAD = 12

    def _add_row(self, table, texts, timeoff=None, days_cnt=5, periods_cnt=8):
        r = table.rowCount()
        table.insertRow(r)
        for c, txt in enumerate(texts):
            item = QTableWidgetItem(str(txt))
            
            # If this is the "Zaman Tablosu" column (index 3) and it's a known table
            if c == 3 and table in [self.table_ogretmen, self.table_sinif, self.table_ders, self.table_derslik]:
                # Instead of text, add the MiniTimeoffGridWidget
                item.setText("") # Clear text
                table.setItem(r, c, item)
                
                mini_grid = MiniTimeoffGridWidget(timeoff_data=timeoff, days=days_cnt, periods=periods_cnt)
                
                # Center the widget in the cell without any outer box border
                container = QWidget()
                container.setStyleSheet("background: transparent; border: none;")
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setAlignment(Qt.AlignCenter)
                container_layout.addWidget(mini_grid)

                # SATIR KUTUYA GÖRE BÜYÜR — tersi değil.
                #
                # Kutu sabit bir tavana sığdırılmaya çalışılıyordu ama hücreye
                # gerçekte kalan yer satır yüksekliğinden AZ: QTableWidget::item
                # dikey iç boşluğu ve resizeRowsToContents birlikte 44 piksellik
                # satırda widget'a 29 piksel bırakıyordu. Kutu 33 piksel olduğu
                # için alttan kırpılıyor, son 1-2 ders saati hiç görünmüyordu —
                # ölçtüm: 8 saatin 7'si çiziliyordu.
                #
                # Artık satır, kutunun gerçek yüksekliğine göre açılıyor; kırpılma
                # kaynağı ne olursa olsun (iç boşluk, kenar çizgisi, tema) kutunun
                # tamamı her zaman sığıyor.
                container.setMinimumHeight(mini_grid.height())
                table.setRowHeight(r, max(table.rowHeight(r),
                                          mini_grid.height() + self.TIMEOFF_CELL_PAD))

                table.setCellWidget(r, c, container)
            else:
                table.setItem(r, c, item)


def normalize_tr_str(s: str) -> str:
    if not s:
        return ""
    tr_map = str.maketrans({
        'İ': 'i', 'I': 'ı', 'ı': 'i', 'Ş': 's', 'ş': 's',
        'Ğ': 'g', 'ğ': 'g', 'Ü': 'u', 'ü': 'u', 'Ö': 'o', 'ö': 'o',
        'Ç': 'c', 'ç': 'c'
    })
    cleaned = str(s).translate(tr_map).lower().strip()
    return "".join(c for c in cleaned if c.isalnum())

def is_teacher_match(t1: str, t2: str, teacher_objs=None) -> bool:
    if not t1 or not t2:
        return False
    n1 = normalize_tr_str(t1)
    n2 = normalize_tr_str(t2)
    if n1 == n2:
        return True
    if len(n1) >= 4 and len(n2) >= 4 and (n1 in n2 or n2 in n1):
        return True
    if teacher_objs:
        for t in teacher_objs:
            ad_norm = normalize_tr_str(t.get("ad", ""))
            kisa_norm = normalize_tr_str(t.get("kisa", ""))
            if (n1 == ad_norm or n1 == kisa_norm or (len(n1) >= 3 and n1 in ad_norm)) and \
               (n2 == ad_norm or n2 == kisa_norm or (len(n2) >= 3 and n2 in ad_norm)):
                return True
    return False


class TeacherIndividualTimetableDialog(QDialog):
    """Öğretmenin Özel Zaman Çizelgesi ve Önizleme/Yazdırma Ekranı"""
    def __init__(self, teacher_name, data_store=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Öğretmen Çizelgesi - {teacher_name}")
        self.setMinimumSize(880, 620)
        self.resize(880, 620)
        self.teacher_name = teacher_name
        self.data_store = data_store if data_store is not None else {}
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; }
            QLabel { color: #334155; font-size: 13px; font-weight: bold; }
            QPushButton { min-height: 32px; padding: 6px 14px; border: 1px solid #CBD5E1; border-radius: 6px; background: #FFFFFF; font-size: 13px; font-weight: bold; color: #475569; }
            QPushButton:hover { background: #F1F5F9; }
            QTableWidget { border: 1px solid #CBD5E1; background: #FFFFFF; gridline-color: #E2E8F0; font-size: 12px; border-radius: 8px; }
            QHeaderView::section { background-color: #F1F5F9; border: none; border-bottom: 2px solid #CBD5E1; padding: 8px; font-weight: bold; font-size: 13px; color: #334155; }
        """)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)
        
        top_bar = QHBoxLayout()
        lbl = QLabel(f"{self.teacher_name} — Haftalık Ders Çizelgesi")
        lbl.setStyleSheet("font-size: 16px; color: #2563EB; font-weight: bold;")
        top_bar.addWidget(lbl)
        top_bar.addStretch(1)
        
        btn_yazdir = QPushButton("Bu Öğretmenin Çizelgesini Yazdır")
        btn_yazdir.setStyleSheet("background: #2563EB; color: white; font-weight: bold; padding: 6px 16px; border-radius: 6px; border: none;")
        btn_yazdir.clicked.connect(self._print_teacher_timetable)
        top_bar.addWidget(btn_yazdir)
        lay.addLayout(top_bar)
        
        settings = self.data_store.get("settings", {})
        periods = int(settings.get("periods", 8))
        days_count = int(settings.get("days_count", 5))
        
        from timetable_grid import DAYS
        days = DAYS[:days_count]
        
        table = QTableWidget(periods, len(days))
        table.setHorizontalHeaderLabels(days)
        table.setVerticalHeaderLabels([f"{p+1}. Ders" for p in range(periods)])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setDefaultSectionSize(48)
        
        from dialogs.edit_forms import format_tr_name, get_subject_color
        from PySide6.QtGui import QBrush, QColor
        
        teacher_objs = self.data_store.get("ogretmenler", [])
        placed_cells = {}
        placed_hours = 0

        # Helper to set cell item
        def fill_cell(r, c, subj, cls, col_hex):
            nonlocal placed_hours
            if 0 <= r < periods and 0 <= c < len(days):
                if (r, c) not in placed_cells:
                    placed_hours += 1
                placed_cells[(r, c)] = True
                
                item = QTableWidgetItem(f"{subj}\n({cls})" if cls else f"{subj}")
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(QFont(FONT_FAMILY, 10, QFont.Weight.Bold))
                
                bg_color = QColor(col_hex or get_subject_color(subj))
                item.setBackground(QBrush(bg_color))
                lum = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue())
                item.setForeground(QBrush(Qt.white if lum < 160 else Qt.black))
                table.setItem(r, c, item)

        # 1. Scan data_store["grid_placements"] (Global list for all classes)
        placements_list = self.data_store.get("grid_placements", [])
        for p in placements_list:
            if not isinstance(p, dict):
                continue
            t_name = p.get("teacher_name") or p.get("teacher") or p.get("ogretmen") or ""
            if is_teacher_match(t_name, self.teacher_name, teacher_objs):
                s_name = p.get("subject_name") or p.get("subject") or p.get("ders") or ""
                c_name = p.get("class_name") or p.get("class") or p.get("sinif") or ""
                dur = int(p.get("duration") or 1)
                col_hex = p.get("color") or get_subject_color(s_name)
                
                day_val = p.get("day") if "day" in p else (p.get("day_idx") if "day_idx" in p else p.get("col", 0))
                period_val = p.get("period") if "period" in p else p.get("row", 0)
                try:
                    d = int(day_val)
                    r = int(period_val)
                except (ValueError, TypeError):
                    continue
                    
                for off in range(dur):
                    fill_cell(r + off, d, s_name, c_name, col_hex)

        # 2. Scan data_store["yerlesim"] (Dict mapping)
        raw_yerlesim = self.data_store.get("yerlesim", {})
        if isinstance(raw_yerlesim, dict):
            for key_str, p in raw_yerlesim.items():
                if not isinstance(p, dict):
                    continue
                t_name = p.get("teacher_name") or p.get("teacher") or p.get("ogretmen") or ""
                if is_teacher_match(t_name, self.teacher_name, teacher_objs):
                    s_name = p.get("subject_name") or p.get("subject") or p.get("ders") or ""
                    c_name = p.get("class_name") or p.get("class") or p.get("sinif") or ""
                    dur = int(p.get("duration") or 1)
                    col_hex = p.get("color") or get_subject_color(s_name)
                    
                    if "," in str(key_str):
                        try:
                            parts = str(key_str).split(",")
                            r, d = int(parts[0]), int(parts[1])
                            for off in range(dur):
                                fill_cell(r + off, d, s_name, c_name, col_hex)
                        except Exception:
                            pass

        # 3. Scan active grid if parent main window is present
        parent_mw = self.parent()
        while parent_mw and not hasattr(parent_mw, "_grid"):
            parent_mw = parent_mw.parent()
            
        if parent_mw and hasattr(parent_mw, "_grid") and hasattr(parent_mw._grid, "get_placed_lessons"):
            grid_placed = parent_mw._grid.get_placed_lessons()
            for (r, d), info in grid_placed.items():
                if isinstance(info, dict):
                    t_name = info.get("teacher_name") or info.get("teacher") or info.get("ogretmen") or ""
                    if is_teacher_match(t_name, self.teacher_name, teacher_objs):
                        s_name = info.get("subject_name") or info.get("subject") or info.get("ders") or ""
                        c_name = info.get("class_name") or info.get("class") or info.get("sinif") or ""
                        dur = int(info.get("duration") or 1)
                        col_hex = info.get("color") or get_subject_color(s_name)
                        for off in range(dur):
                            fill_cell(r + off, d, s_name, c_name, col_hex)

        # 4. Cross-Institution Busy Slots (Çapraz Kurum Dersleri)
        cross_hours = 0
        try:
            import version_store
            current_slug = self.data_store.get("settings", {}).get("institution_slug", None)
            cross_busy = version_store.get_cross_institution_teacher_busy_slots(exclude_slug=current_slug)
            for (t_norm, d, p_slot), conflict_info in cross_busy.items():
                t_raw = conflict_info.get("teacher_name", "")
                if is_teacher_match(t_raw or t_norm, self.teacher_name, teacher_objs):
                    if (p_slot, d) not in placed_cells and 0 <= p_slot < periods and 0 <= d < len(days):
                        cross_hours += 1
                        c_inst = conflict_info.get("institution_name", "Diğer Kurum")
                        c_cls = conflict_info.get("class", "")
                        c_subj = conflict_info.get("subject", "Ders")
                        
                        item = QTableWidgetItem(f"{c_subj}\n({c_cls})\n[{c_inst}]")
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setFont(QFont(FONT_FAMILY, 9, QFont.Weight.Bold))
                        item.setBackground(QBrush(QColor("#D97706"))) # Amber warning
                        item.setForeground(QBrush(Qt.white))
                        item.setToolTip(f"Bu öğretmen {c_inst} kurumunda {c_cls} ({c_subj}) dersindedir.")
                        table.setItem(p_slot, d, item)
        except Exception as e:
            print(f"[MasterDataDialog] Cross-institution scan notice: {e}")

        teacher_atamalar = [a for a in self.data_store.get("atamalar", []) if is_teacher_match(a.get("ogretmen") or a.get("teacher", ""), self.teacher_name, teacher_objs)]
        total_assigned_hours = sum(lesson_hours.hours(a) for a in teacher_atamalar)

        # Summary footer bar
        banner_txt = f"Toplam Tanımlı Ders: {total_assigned_hours} Saat  |  Bu Kurumda Yerleşen: {placed_hours} Saat"
        if cross_hours > 0:
            banner_txt += f"  |  🏢 Diğer Kurumlarda: {cross_hours} Saat"
        info_banner = QLabel(banner_txt)
        info_banner.setStyleSheet("color: #1E293B; background: #E2E8F0; padding: 6px 12px; border-radius: 6px; font-weight: 600;")
        lay.addWidget(info_banner)
        lay.addWidget(table, 1)
        
        bot = QHBoxLayout()
        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(self.accept)
        bot.addStretch(1)
        bot.addWidget(btn_close)
        lay.addLayout(bot)

    def _print_teacher_timetable(self):
        from dialogs.print_preview import TimetablePrintPreview
        filters = {"entity_type": "teacher", "selected_items": [self.teacher_name]}
        dlg = TimetablePrintPreview(self.data_store, {}, filters, self)
        dlg.exec()
