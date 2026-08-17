"""dialogs/master_data_dialog.py - Gerçek Zamanlı Ana Veri Yönetim Penceresi"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSizePolicy, QSpacerItem, QMessageBox
)
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QBrush, QPolygon, QIcon

from dialogs.edit_forms import DersEditDialog, SinifEditDialog, OgretmenEditDialog, DerslikEditDialog
from database import trigger_save_db
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QAbstractItemView

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
    pix = QPixmap(48, 48)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    
    selected = name.endswith("_selected")
    base_name = name.replace("_selected", "")
    
    if base_name == "book":
        # Mavi Kitap
        p.setBrush(QColor("#5C99D6"))
        p.setPen(QColor("#3A78B4"))
        p.drawRect(8, 6, 32, 36)
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(Qt.NoPen)
        p.drawRect(12, 12, 20, 4)
        p.drawRect(12, 20, 24, 2)
        
    elif base_name == "teachers":
        # İki Kişi (Kahve ve Yeşil)
        # Kişi 1 (Kahve/Turuncu)
        p.setBrush(QColor("#E2A065"))
        p.setPen(QColor("#C07C41"))
        p.drawEllipse(6, 12, 14, 14)
        p.setBrush(QColor("#D66A55"))
        p.setPen(QColor("#B54D3D"))
        _create_shoulder_path(p, 13, 30, 20, 16)
        
        # Kişi 2 (Yeşil)
        p.setBrush(QColor("#F4D08F"))
        p.setPen(QColor("#CF9F53"))
        p.drawEllipse(18, 16, 16, 16)
        p.setBrush(QColor("#9BD08F"))
        p.setPen(QColor("#6A9E5F"))
        _create_shoulder_path(p, 26, 36, 24, 18)
        
    elif base_name == "door":
        # Kahverengi Kapı
        p.setBrush(QColor("#E8C9A8"))
        p.setPen(QColor("#9E7655"))
        p.drawRect(10, 8, 28, 32)
        # Açık kapı detayı
        p.setBrush(QColor("#5A3E26"))
        p.drawRect(14, 12, 20, 28)
        p.setBrush(QColor("#E8C9A8"))
        poly = QPolygon([QPoint(14, 12), QPoint(34, 4), QPoint(34, 44), QPoint(14, 40)])
        p.drawPolygon(poly)
        
    elif base_name == "grad_hat":
        # Mezuniyet Şapkası
        p.setBrush(QColor("#333333"))
        p.setPen(QColor("#111111"))
        poly = QPolygon([QPoint(24, 8), QPoint(42, 16), QPoint(24, 24), QPoint(6, 16)])
        p.drawPolygon(poly)
        p.drawRect(16, 20, 16, 12)
        # Püskül
        p.setPen(QPen(QColor("#F4A030"), 2))
        p.drawLine(24, 16, 38, 26)
        p.drawLine(38, 26, 38, 34)
        
    if selected:
        # Yeşil Ok
        p.setBrush(QColor("#4CAF50"))
        p.setPen(QColor("#2E7D32"))
        poly = QPolygon([
            QPoint(12, 22), QPoint(32, 22), QPoint(32, 14),
            QPoint(48, 26), QPoint(32, 38), QPoint(32, 30), QPoint(12, 30)
        ])
        p.drawPolygon(poly)
        
    p.end()
    return pix

def _create_shoulder_path(painter, cx, cy, w, h):
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.moveTo(cx - w/2, cy + h/2)
    path.quadTo(cx - w/2, cy - h/2, cx, cy - h/2)
    path.quadTo(cx + w/2, cy - h/2, cx + w/2, cy + h/2)
    path.closeSubpath()
    painter.drawPath(path)

class LeftMenuButton(QPushButton):
    def __init__(self, icon_name, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.setFixedSize(64, 64)
        self.setIcon(create_wizard_icon(self.icon_name))
        self.setIconSize(QSize(48, 48))
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton { border: none; background: transparent; border-radius: 4px; }
            QPushButton:hover { background: rgba(0, 120, 215, 0.1); }
            QPushButton:checked { background: rgba(0, 120, 215, 0.2); border: 1px solid rgba(0, 120, 215, 0.5); }
        """)

    def setChecked(self, checked):
        super().setChecked(checked)
        if checked:
            self.setIcon(create_wizard_icon(self.icon_name + "_selected"))
        else:
            self.setIcon(create_wizard_icon(self.icon_name))

class ActionButton(QPushButton):
    def __init__(self, text, icon_name=None, is_primary=False, parent=None):
        super().__init__(text, parent)
        self.icon_name = icon_name
        self.setFixedHeight(28)
        self.setFont(QFont("Segoe UI", 9))
        self.setStyleSheet("text-align: left; padding-left: 32px;")

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.icon_name: return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.icon_name == "plus":
            p.setBrush(QColor("#4CAF50"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(8, 6, 16, 16)
            p.setPen(QPen(Qt.white, 2))
            p.drawLine(16, 10, 16, 18)
            p.drawLine(12, 14, 20, 14)
        elif self.icon_name == "edit":
            p.setBrush(QColor("#B0B0B0"))
            p.setPen(Qt.NoPen)
            p.drawRect(8, 8, 16, 12)
            p.drawPolygon([QPoint(8, 8), QPoint(16, 4), QPoint(24, 8)])
        elif self.icon_name == "minus":
            p.setBrush(QColor("#B0B0B0"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(8, 6, 16, 16)
            p.setPen(QPen(Qt.white, 2))
            p.drawLine(12, 14, 20, 14)
        elif self.icon_name == "doc":
            p.setBrush(QColor("#B0B0B0"))
            p.setPen(Qt.NoPen)
            p.drawRect(10, 6, 12, 16)
            p.drawRect(18, 4, 6, 6)
        elif self.icon_name == "clock":
            p.setPen(QPen(QColor("#B0B0B0"), 2))
            p.drawEllipse(8, 6, 16, 16)
            p.drawLine(16, 14, 16, 8)
            p.drawLine(16, 14, 20, 14)
        elif self.icon_name == "hash":
            p.setPen(QPen(QColor("#B0B0B0"), 2))
            p.drawLine(12, 6, 12, 22)
            p.drawLine(20, 6, 20, 22)
            p.drawLine(8, 10, 24, 10)
            p.drawLine(8, 18, 24, 18)
        elif self.icon_name == "branch":
            p.setPen(QPen(QColor("#B0B0B0"), 2))
            p.drawLine(16, 20, 16, 14)
            p.drawLine(16, 14, 10, 8)
            p.drawLine(16, 14, 22, 8)
        p.end()


class MasterDataDialog(QDialog):
    def __init__(self, start_idx=0, parent=None, data_store=None):
        super().__init__(parent)
        self.setWindowTitle("Sınıflar") # Will be updated in select_tab
        self.resize(900, 650)
        self.setFont(QFont("Segoe UI", 9))
        
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
        
        self._build_ui()
        self._load_existing_data()
        self._select_tab(start_idx)

    def _load_data(self):
        self._load_existing_data()

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

        for data in self.data_store.get("dersler", []):
            toplam = str(totals["dersler"].get(data.get("ad", ""), 0))
            self._add_row(self.table_ders, [data.get("ad",""), data.get("kisa",""), toplam, "Mevcut", "İdeal", "8"])
        settings = self.data_store.get("settings", {})
        days = settings.get("days", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
        periods = int(settings.get("periods", 8))
        total_default = len(days) * periods
        
        for data in self.data_store.get("siniflar", []):
            toplam = str(totals["siniflar"].get(data.get("ad", ""), 0))
            timeoff = data.get("timeoff", [])
            if not timeoff:
                zaman_str = f"{total_default} Ders"
            else:
                open_cells = sum(1 for r in timeoff for c in r if c > 0)
                zaman_str = f"{open_cells} Ders"
                
            self._add_row(self.table_sinif, [data.get("ad",""), data.get("kisa",""), toplam, zaman_str, data.get("ders_bitimi","15:30"), data.get("sinif_ogretmeni",""), data.get("kapasite","30")])
        for data in self.data_store.get("derslikler", []):
            self._add_row(self.table_derslik, [data.get("ad",""), data.get("kisa",""), "0", "Mevcut", data.get("kapasite",""), "Merkez"])
        # Build Class Teacher mapping (e.g. 11A, 9B)
        class_teacher_map = {}
        for s in self.data_store.get("siniflar", []):
            so = s.get("sinif_ogretmeni")
            if so:
                class_teacher_map[so] = s.get("ad")

        for data in self.data_store.get("ogretmenler", []):
            t_name = data.get("ad", "")
            toplam = str(totals["ogretmenler"].get(t_name, 0))
            
            # Class teacher of which class (e.g. 11A)
            so_class = class_teacher_map.get(t_name) or data.get("sinif_ogretmeni", "")
            
            # Branch
            brans = data.get("brans", "")
            
            # Assigned subjects & classes
            from dialogs.edit_forms import format_tr_name
            teacher_atamalar = [a for a in self.data_store.get("atamalar", []) if format_tr_name(a.get("teacher", "")) == format_tr_name(t_name)]
            assignments_summary_list = []
            for a in teacher_atamalar:
                subj = a.get("subject", "")
                cls = a.get("class", "")
                if subj and cls:
                    assignments_summary_list.append(f"{subj} ({cls})")
                elif subj:
                    assignments_summary_list.append(subj)
            atanan_dersler_str = ", ".join(assignments_summary_list) if assignments_summary_list else "Atama Yok"
            
            zaman_str = "📅 Çizelge Göster / Yazdır"
            
            self._add_row(self.table_ogretmen, [
                t_name, data.get("kisa",""), toplam, zaman_str, so_class, brans, atanan_dersler_str
            ])

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
        btn_help.setIcon(QIcon.fromTheme("help-browser")) # System icon if available
        btn_help.setFixedSize(90, 30)
        btn_help.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC; border-radius: 4px;")
        
        btn_undo = QPushButton("↺ Geri Al")
        btn_undo.setFixedSize(90, 32)
        btn_undo.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; color: #334155; font-weight: bold; border-radius: 4px;")
        btn_undo.clicked.connect(self._act_undo)

        btn_redo = QPushButton("↻ Yinele")
        btn_redo.setFixedSize(90, 32)
        btn_redo.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; color: #334155; font-weight: bold; border-radius: 4px;")
        btn_redo.clicked.connect(self._act_redo)

        btn_save = QPushButton("Kaydet")
        btn_save.setFixedSize(110, 32)
        btn_save.setStyleSheet("background: #0078D7; color: white; font-weight: bold; border-radius: 4px; font-size: 13px;")
        btn_save.clicked.connect(self.accept)
        
        btn_reset_classes = QPushButton("🧹 Tüm Sınıf Atamalarını Sıfırla")
        btn_reset_classes.setFixedSize(200, 32)
        btn_reset_classes.setStyleSheet("background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; font-weight: bold; border-radius: 4px; font-size: 12px;")
        btn_reset_classes.clicked.connect(self._reset_all_class_assignments)
        
        btn_info = QPushButton("Bilgi Al")
        btn_info.setFixedSize(90, 30)
        btn_info.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC; border-radius: 4px;")
        
        btn_close = QPushButton("Kapat")
        btn_close.setFixedSize(90, 30)
        btn_close.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC; border-radius: 4px;")
        btn_close.clicked.connect(self.reject)
        
        bottom_layout.addWidget(btn_help)
        bottom_layout.addWidget(btn_undo)
        bottom_layout.addWidget(btn_redo)
        bottom_layout.addWidget(btn_save)
        bottom_layout.addWidget(btn_reset_classes)
        bottom_layout.addWidget(btn_info)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(btn_close)
        
        main_layout.addLayout(bottom_layout)

        # Keyboard shortcuts
        from PySide6.QtGui import QKeySequence, QShortcut
        QShortcut(QKeySequence("Ctrl+Z"), self, self._act_undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self._act_redo)

    def _push_undo_state(self):
        import copy
        if not hasattr(self, "_history_stack"): self._history_stack = []
        if not hasattr(self, "_redo_stack"): self._redo_stack = []
        if len(self._history_stack) > 50:
            self._history_stack.pop(0)
        self._history_stack.append(copy.deepcopy(self.data_store))
        self._redo_stack.clear()

    def _act_undo(self):
        import copy
        if hasattr(self, "_history_stack") and self._history_stack:
            if not hasattr(self, "_redo_stack"): self._redo_stack = []
            self._redo_stack.append(copy.deepcopy(self.data_store))
            prev_state = self._history_stack.pop()
            self.data_store.clear()
            self.data_store.update(prev_state)
            trigger_save_db(self, self.data_store)
            if hasattr(self, "_load_data"):
                self._load_data()
            win = self.window() or self.parent()
            if win and hasattr(win, "_refresh_tree"):
                win._refresh_tree()
            if win and hasattr(win, "_refresh_grid"):
                win._refresh_grid()
            if win and hasattr(win, "statusBar"):
                win.statusBar().showMessage("↺ Yapılan son işlem başarıyla geri alındı.")
        else:
            win = self.window() or self.parent()
            if win and hasattr(win, "statusBar"):
                win.statusBar().showMessage("⚠️ Geri alınacak başka işlem yok.")

    def _act_redo(self):
        import copy
        if hasattr(self, "_redo_stack") and self._redo_stack:
            if not hasattr(self, "_history_stack"): self._history_stack = []
            self._history_stack.append(copy.deepcopy(self.data_store))
            next_state = self._redo_stack.pop()
            self.data_store.clear()
            self.data_store.update(next_state)
            trigger_save_db(self, self.data_store)
            if hasattr(self, "_load_data"):
                self._load_data()
            win = self.window() or self.parent()
            if win and hasattr(win, "_refresh_tree"):
                win._refresh_tree()
            if win and hasattr(win, "_refresh_grid"):
                win._refresh_grid()
            if win and hasattr(win, "statusBar"):
                win.statusBar().showMessage("↻ İşlem başarıyla tekrar uygulandı.")
        else:
            win = self.window() or self.parent()
            if win and hasattr(win, "statusBar"):
                win.statusBar().showMessage("⚠️ Yinelenecek başka işlem yok.")

    def _reset_all_class_assignments(self):
        r = QMessageBox.question(
            self,
            "Tüm Sınıf Atamalarını Sıfırla",
            "TÜM sınıflara ait ders ve öğretmen görevlendirmeleri tamamen silinecektir.\n\nEmin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if r == QMessageBox.Yes:
            self.data_store["atamalar"] = []
            self.data_store["grid_placements"] = []
            self.data_store["yerlesim"] = {}
            trigger_save_db(self, self.data_store)
            
            # Find main window to refresh grid and tree
            win = self.window()
            if not win or not hasattr(win, "_grid"):
                p = self.parent()
                while p:
                    if hasattr(p, "_grid"):
                        win = p
                        break
                    p = p.parent()
            if win:
                if hasattr(win, "save_db"):
                    win.save_db(sync_from_grid=False)
                if hasattr(win, "_refresh_tree"):
                    win._refresh_tree()
                if hasattr(win, "_load_unplaced_lessons"):
                    win._load_unplaced_lessons()
                if hasattr(win, "_grid") and hasattr(win._grid, "load_lessons"):
                    win._grid.load_lessons({})
                    
            if hasattr(self, "_load_data"):
                self._load_data()
            QMessageBox.information(self, "Başarılı", "Tüm sınıf atamaları başarıyla sıfırlandı.")

    def _create_table(self, headers):
        t = DragDropTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.verticalHeader().setDefaultSectionSize(40)
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
                padding: 8px 12px;
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
            
            # Pop and insert manually in memory
            item = data_list.pop(start)
            data_list.insert(dest, item)
            
            # Re-render UI table to match memory
            self._load_existing_data()
            
            # Highlight newly moved row
            tables = [self.table_ders, self.table_sinif, self.table_derslik, self.table_ogretmen]
            t = tables[idx]
            t.selectRow(dest)
            
            p = self.parent() or getattr(self, "main_window", None)
            if p and hasattr(p, "save_db"): p.save_db()

    def _on_table_clicked(self, row, col):
        idx = self.stack.currentIndex()
        if idx == 3 and col == 3: # Zaman Tablosu & Çizelge column
            item = self.table_ogretmen.item(row, 0)
            if item:
                t_name = item.text().strip()
                d = TeacherIndividualTimetableDialog(t_name, self.data_store, self)
                d.exec()

    def _on_table_double_clicked(self, row, col):
        idx = self.stack.currentIndex()
        if idx == 3 and col == 3: # Zaman Tablosu & Çizelge column
            item = self.table_ogretmen.item(row, 0)
            if item:
                t_name = item.text().strip()
                d = TeacherIndividualTimetableDialog(t_name, self.data_store, self)
                d.exec()
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
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl.setStyleSheet("padding: 4px;")
        top_bar.addWidget(lbl)
        top_bar.addStretch(1)
        
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
                
            data_list.sort(key=smart_sort)
            self._load_existing_data()
            p = self.parent() or getattr(self, "main_window", None)
            if p and hasattr(p, "save_db"): p.save_db()
            
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
                    trigger_save_db(self, self.data_store)
                    p = self.parent()
                    if p and hasattr(p, "_refresh_tree"): p._refresh_tree()
            return

        from dialogs.edit_forms import LessonAssignmentDialog
        if not teacher_name and hasattr(self, "table_ogretmen"):
            r = self.table_ogretmen.currentRow()
            if r >= 0:
                item = self.table_ogretmen.item(r, 0)
                if item: teacher_name = item.text()
                
        d = LessonAssignmentDialog(data_store=self.data_store, parent=self, selected_teacher=teacher_name)
        if d.exec():
            data = d.get_data()
            if "atamalar" not in self.data_store:
                self.data_store["atamalar"] = []
            
            # Remove old assignments for this teacher (they are being re-saved from the dialog)
            current_teacher = d.cb_ogretmen.currentText()
            self.data_store["atamalar"] = [
                a for a in self.data_store["atamalar"] 
                if a.get("teacher") != current_teacher
            ]
                
            if isinstance(data, list):
                self.data_store["atamalar"].extend(data)
            else:
                self.data_store["atamalar"].append(data)
                
            trigger_save_db(self, self.data_store)
            p = self.parent()
            if p and hasattr(p, "_refresh_tree"): p._refresh_tree()

    def _act_new(self):
        idx = self.stack.currentIndex()
        if idx == 0:  # Dersler
            d = DersEditDialog(self)
            if d.exec():
                data = d.get_data()
                self.data_store["dersler"].append(data)
                self._add_row(self.table_ders, [data.get("ad",""), data.get("kisa",""), "0", "Mevcut", "İdeal", "8"])
        elif idx == 1:  # Sınıflar
            d = SinifEditDialog(self)
            if d.exec():
                data = d.get_data()
                self.data_store["siniflar"].append(data)
                
                settings = self.data_store.get("settings", {})
                total_default = len(settings.get("days", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])) * int(settings.get("periods", 8))
                
                timeoff = data.get("timeoff", [])
                if not timeoff:
                    zaman_str = f"{total_default} Ders"
                else:
                    open_cells = sum(1 for r in timeoff for c in r if c > 0)
                    zaman_str = f"{open_cells} Ders"
                    
                self._add_row(self.table_sinif, [data.get("ad",""), data.get("kisa",""), "0", zaman_str, data.get("ders_bitimi","15:30"), data.get("sinif_ogretmeni",""), data.get("kapasite","30")])
        elif idx == 2:  # Derslikler
            d = DerslikEditDialog(self)
            if d.exec():
                data = d.get_data()
                self.data_store["derslikler"].append(data)
                self._add_row(self.table_derslik, [data.get("ad",""), data.get("kisa",""), "0", "Mevcut", data.get("kapasite",""), "Merkez"])
        elif idx == 3:  # Öğretmenler
            d = OgretmenEditDialog(self)
            if d.exec():
                data = d.get_data()
                self.data_store["ogretmenler"].append(data)
                self._add_row(self.table_ogretmen, [data.get("ad",""), data.get("kisa",""), "0", "Mevcut", data.get("sinif_ogretmeni",""), data.get("brans",""), ""])
                self._act_assign(teacher_name=data.get("ad"))

        trigger_save_db(self, self.data_store)
        p = self.parent()
        if p and hasattr(p, "_refresh_tree"): p._refresh_tree()

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
            d = dialogs[idx](parent=self, existing_data=old_data)
            if d.exec():
                new_data = d.get_data()
                old_name = old_data.get("ad")
                new_name = new_data.get("ad")
                if old_name and new_name and old_name != new_name:
                    key_map = {0: "subject", 1: "class", 3: "teacher"}
                    if idx in key_map:
                        attr = key_map[idx]
                        for a in self.data_store.get("atamalar", []):
                            if a.get(attr) == old_name:
                                a[attr] = new_name
                        for p in self.data_store.get("grid_placements", []):
                            if idx == 0:
                                if p.get("subject_name") == old_name or p.get("subject") == old_name:
                                    p["subject_name"] = new_name
                                    p["subject"] = new_name
                            elif idx == 1:
                                if p.get("class_name") == old_name or p.get("class") == old_name:
                                    p["class_name"] = new_name
                                    p["class"] = new_name
                            elif idx == 3:
                                if p.get("teacher_name") == old_name or p.get("teacher") == old_name:
                                    p["teacher_name"] = new_name
                                    p["teacher"] = new_name

                data_list[matched_idx] = new_data
                
                # Refresh entire table to be safe
                table.setRowCount(0)
                
                totals = {"dersler": {}, "siniflar": {}, "ogretmenler": {}}
                for a in self.data_store.get("atamalar", []):
                    dur = a.get("duration", 1)
                    t = a.get("teacher", "")
                    s = a.get("subject", "")
                    c = a.get("class", "")
                    if t: totals["ogretmenler"][t] = totals["ogretmenler"].get(t, 0) + dur
                    if s: totals["dersler"][s] = totals["dersler"].get(s, 0) + dur
                    if c: totals["siniflar"][c] = totals["siniflar"].get(c, 0) + dur

                if idx == 0:
                    for data in self.data_store.get("dersler", []):
                        toplam = str(totals["dersler"].get(data.get("ad", ""), 0))
                        self._add_row(self.table_ders, [data.get("ad",""), data.get("kisa",""), toplam, "Mevcut", "İdeal", "8"])
                elif idx == 1:
                    settings = self.data_store.get("settings", {})
                    total_default = len(settings.get("days", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])) * int(settings.get("periods", 8))
                    for data in self.data_store.get("siniflar", []):
                        toplam = str(totals["siniflar"].get(data.get("ad", ""), 0))
                        
                        timeoff = data.get("timeoff", [])
                        if not timeoff:
                            zaman_str = f"{total_default} Ders"
                        else:
                            open_cells = sum(1 for r in timeoff for c in r if c > 0)
                            zaman_str = f"{open_cells} Ders"
                            
                        self._add_row(self.table_sinif, [data.get("ad",""), data.get("kisa",""), toplam, zaman_str, data.get("ders_bitimi","15:30"), data.get("sinif_ogretmeni",""), data.get("kapasite","30")])
                elif idx == 2:
                    for data in self.data_store.get("derslikler", []):
                        self._add_row(self.table_derslik, [data.get("ad",""), data.get("kisa",""), "0", "Mevcut", data.get("kapasite",""), "Merkez"])
                elif idx == 3:
                    for data in self.data_store.get("ogretmenler", []):
                        toplam = str(totals["ogretmenler"].get(data.get("ad", ""), 0))
                        self._add_row(self.table_ogretmen, [data.get("ad",""), data.get("kisa",""), toplam, "Mevcut", data.get("sinif_ogretmeni",""), ""])
                
                trigger_save_db(self, self.data_store)
                p = self.parent()
                if p and hasattr(p, "_refresh_tree"): p._refresh_tree()
                if p and hasattr(p, "_restore_grid_placements"): p._restore_grid_placements()

    def _act_delete(self):
        from PySide6.QtWidgets import QMessageBox
        idx = self.stack.currentIndex()
        tables = [self.table_ders, self.table_sinif, self.table_derslik, self.table_ogretmen]
        stores = ["dersler", "siniflar", "derslikler", "ogretmenler"]
        
        table = tables[idx]
        row = table.currentRow()
        if row >= 0:
            item = table.item(row, 0)
            if not item: return
            del_name = item.text().strip()
            r = QMessageBox.question(self, "Silme Onayı", f"{del_name} silmek istediğinize emin misiniz?", QMessageBox.Yes | QMessageBox.No)
            if r == QMessageBox.Yes:
                table.removeRow(row)
                data_list = self.data_store[stores[idx]]
                self.data_store[stores[idx]] = [d for d in data_list if d.get("ad") != del_name and d.get("kisa") != del_name]
                if idx == 3: # Teacher
                    self.data_store["atamalar"] = [a for a in self.data_store.get("atamalar", []) if a.get("teacher") != del_name]
                elif idx == 0: # Subject
                    self.data_store["atamalar"] = [a for a in self.data_store.get("atamalar", []) if a.get("subject") != del_name]
                elif idx == 1: # Class
                    self.data_store["atamalar"] = [a for a in self.data_store.get("atamalar", []) if a.get("class") != del_name]
                p = self.parent() or getattr(self, "main_window", None)
                if p and hasattr(p, "save_db"): p.save_db()
                if p and hasattr(p, "_refresh_tree"): p._refresh_tree()

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
            from dialogs.timeoff_dialog import TimeoffDialog
            dlg = TimeoffDialog(entity, names[idx], self.data_store, self)
            if dlg.exec() == QDialog.Accepted:
                trigger_save_db(self, self.data_store)
                
                # Anlık UI yenileme
                self.table_ders.setRowCount(0)
                self.table_sinif.setRowCount(0)
                self.table_derslik.setRowCount(0)
                self.table_ogretmen.setRowCount(0)
                self._load_existing_data()

    def _act_constraints(self):
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
            trigger_save_db(self, self.data_store)

    def _act_delete_all(self):
        from PySide6.QtWidgets import QMessageBox
        idx = self.stack.currentIndex()
        tables = [self.table_ders, self.table_sinif, self.table_derslik, self.table_ogretmen]
        stores = ["dersler", "siniflar", "derslikler", "ogretmenler"]
        names = ["derslerin", "sınıfların", "dersliklerin", "öğretmenlerin"]
        
        r = QMessageBox.question(
            self, "Tümünü Sil Onayı",
            f"Tanımlı tüm {names[idx]} listesini silmek istediğinize emin misiniz?\nBu işlem geri alınamaz!",
            QMessageBox.Yes | QMessageBox.No
        )
        if r == QMessageBox.Yes:
            tables[idx].setRowCount(0)
            self.data_store[stores[idx]] = []
            if idx in (0, 1, 3):
                self.data_store["atamalar"] = []
            trigger_save_db(self, self.data_store)
            if p and hasattr(p, "_refresh_tree"): p._refresh_tree()

    def _act_groups(self):
        from dialogs.groups_dialog import GroupsDialog
        dlg = GroupsDialog(self.data_store, self)
        dlg.exec()

    def _act_auto_schedule(self):
        from dialogs.auto_schedule_dialog import AutoScheduleDialog
        dlg = AutoScheduleDialog(self.data_store, self)
        if dlg.exec():
            self._load_existing_data()
            p = self.parent() or getattr(self, "main_window", None)
            if p and hasattr(p, "save_db"): p.save_db()
            if p and hasattr(p, "_refresh_tree"): p._refresh_tree()
            if p and hasattr(p, "_restore_grid_placements"): p._restore_grid_placements()

    def _open_2025_dialog(self, dlg_id):
        from dialogs.extracted_dialog import open_extracted_dialog
        open_extracted_dialog(dlg_id, self)

    def accept(self):
        try:
            p = self.parent() or getattr(self, "main_window", None)
            if p and hasattr(p, "save_db"):
                p.save_db()
            if p and hasattr(p, "_refresh_tree"):
                p._refresh_tree()
        except Exception as e:
            print("accept Exception Handled:", e)
        super().accept()

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
            data_list[row], data_list[target_row] = data_list[target_row], data_list[row]
            self._load_existing_data()
            table.setCurrentCell(target_row, 0)
            p = self.parent() or getattr(self, "main_window", None)
            if p and hasattr(p, "save_db"): p.save_db()

    def _add_row(self, table, texts):
        r = table.rowCount()
        table.insertRow(r)
        for c, txt in enumerate(texts):
            item = QTableWidgetItem(str(txt))
            if c == 3 and table == self.table_ogretmen:
                item.setForeground(QBrush(QColor("#0078D7")))
                item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
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
                item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                
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

        teacher_atamalar = [a for a in self.data_store.get("atamalar", []) if is_teacher_match(a.get("teacher", ""), self.teacher_name, teacher_objs)]
        total_assigned_hours = sum(int(a.get("duration", 1)) for a in teacher_atamalar)

        # Summary footer bar
        info_banner = QLabel(f"Toplam Tanımlı Ders: {total_assigned_hours} Saat  |  Haftalık Çizelgede Yerleşen: {placed_hours} Saat")
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
