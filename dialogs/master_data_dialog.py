"""dialogs/master_data_dialog.py - Gerçek Zamanlı Ana Veri Yönetim Penceresi"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QBrush, QPolygon, QIcon

from dialogs.edit_forms import DersEditDialog, SinifEditDialog, OgretmenEditDialog, DerslikEditDialog


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
    def __init__(self, start_idx=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sınıflar") # Will be updated in select_tab
        self.resize(900, 650)
        self.setFont(QFont("Segoe UI", 9))
        
        self.main_window = parent
        if hasattr(self.main_window, "data_store"):
            self.data_store = self.main_window.data_store
            # Ensure keys exist
            for k in ["siniflar", "ogretmenler", "derslikler", "dersler"]:
                if k not in self.data_store:
                    self.data_store[k] = []
        else:
            self.data_store = {
                "siniflar": [], "ogretmenler": [], "derslikler": [], "dersler": []
            }
        
        self._build_ui()
        self._load_existing_data()
        self._select_tab(start_idx)

    def _load_existing_data(self):
        # Reset row counts to avoid duplicate row stacking
        self.table_ders.setRowCount(0)
        self.table_sinif.setRowCount(0)
        self.table_derslik.setRowCount(0)
        self.table_ogretmen.setRowCount(0)
        
        # Sort master data alphabetically
        tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
        def tr_sort(item):
            n = item.get("ad", "") if isinstance(item, dict) else ""
            return n.translate(tr_map).lower()

        for k in ["dersler", "siniflar", "derslikler", "ogretmenler"]:
            if k in self.data_store and isinstance(self.data_store[k], list):
                self.data_store[k].sort(key=tr_sort)

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
        for data in self.data_store.get("ogretmenler", []):
            toplam = str(totals["ogretmenler"].get(data.get("ad", ""), 0))
            self._add_row(self.table_ogretmen, [data.get("ad",""), data.get("kisa",""), toplam, "Mevcut", data.get("sinif_ogretmeni",""), ""])

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

        self.table_ogretmen = self._create_table(["Öğretmen Adı", "Kısa Kodu", "Toplam", "Zaman Tablosu", "Sınıf Öğretmeni", "Branşı"])
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
        
        btn_yukari = ActionButton("▲ Yukarı Taşı", icon_name="edit")
        btn_yukari.clicked.connect(lambda: self._act_move_row(-1))
        right_panel.addWidget(btn_yukari)
        
        btn_asagi = ActionButton("▼ Aşağı Taşı", icon_name="edit")
        btn_asagi.clicked.connect(lambda: self._act_move_row(1))
        right_panel.addWidget(btn_asagi)
        
        right_panel.addSpacing(15)
        
        # Orijinal 2025 Dialoglarına yönlendiren butonlar
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
        
        btn_save = QPushButton("Kaydet")
        btn_save.setFixedSize(110, 32)
        btn_save.setStyleSheet("background: #0078D7; color: white; font-weight: bold; border-radius: 4px; font-size: 13px;")
        btn_save.clicked.connect(self.accept)
        
        btn_info = QPushButton("Bilgi Al")
        btn_info.setFixedSize(90, 30)
        btn_info.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC; border-radius: 4px;")
        
        btn_close = QPushButton("Kapat")
        btn_close.setFixedSize(90, 30)
        btn_close.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC; border-radius: 4px;")
        btn_close.clicked.connect(self.reject)
        
        bottom_layout.addWidget(btn_help)
        bottom_layout.addWidget(btn_save)
        bottom_layout.addWidget(btn_info)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(btn_close)
        
        main_layout.addLayout(bottom_layout)

    def _create_table(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.setSelectionBehavior(QTableWidget.SelectRows)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.setStyleSheet("""
            QTableWidget { border: 1px solid #D0D0D0; font-size: 9pt; gridline-color: #E0E0E0; }
            QHeaderView::section {
                background-color: #F0F0F0;
                border: 1px solid #D0D0D0;
                padding: 4px; font-weight: bold; font-size: 9pt;
            }
        """)
        t.doubleClicked.connect(self._act_update)
        return t

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
        txt_search.setPlaceholderText("🔍 Gerçek Zamanlı Ara...")
        txt_search.setFixedWidth(220)
        txt_search.setStyleSheet("padding: 4px 8px; border: 1px solid #CCCCCC; border-radius: 4px; font-size: 9pt; background: #FFFFFF;")
        
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
                
            p = self.parent()
            if p and hasattr(p, "save_db"): p.save_db()
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
                self._add_row(self.table_ogretmen, [data.get("ad",""), data.get("kisa",""), "0", "Mevcut", data.get("sinif_ogretmeni",""), ""])
                self._act_assign(teacher_name=data.get("ad"))

        p = self.parent()
        if p and hasattr(p, "save_db"): p.save_db()
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
            
        data_list = self.data_store[stores[idx]]
        if row < len(data_list):
            old_data = data_list[row]
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

                data_list[row] = new_data
                
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
                
                p = self.parent()
                if p and hasattr(p, "save_db"): p.save_db()
                if p and hasattr(p, "_refresh_tree"): p._refresh_tree()

    def _act_delete(self):
        from PySide6.QtWidgets import QMessageBox
        idx = self.stack.currentIndex()
        tables = [self.table_ders, self.table_sinif, self.table_derslik, self.table_ogretmen]
        stores = ["dersler", "siniflar", "derslikler", "ogretmenler"]
        
        table = tables[idx]
        row = table.currentRow()
        if row >= 0:
            item = table.item(row, 0)
            name = item.text() if item else "Bu öğeyi"
            r = QMessageBox.question(self, "Silme Onayı", f"{name} silmek istediğinize emin misiniz?", QMessageBox.Yes | QMessageBox.No)
            if r == QMessageBox.Yes:
                table.removeRow(row)
                if row < len(self.data_store[stores[idx]]):
                    removed_item = self.data_store[stores[idx]].pop(row)
                    del_name = removed_item.get("ad")
                    if del_name:
                        if idx == 3: # Teacher
                            self.data_store["atamalar"] = [a for a in self.data_store.get("atamalar", []) if a.get("teacher") != del_name]
                        elif idx == 0: # Subject
                            self.data_store["atamalar"] = [a for a in self.data_store.get("atamalar", []) if a.get("subject") != del_name]
                        elif idx == 1: # Class
                            self.data_store["atamalar"] = [a for a in self.data_store.get("atamalar", []) if a.get("class") != del_name]
                p = self.parent()
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
                p = self.parent()
                if p and hasattr(p, "save_db"): p.save_db()
                
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
        dlg = ConstraintsDialog(self.data_store, target_type=target_type, parent=self)
        dlg.exec()

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
            p = self.parent()
            if p and hasattr(p, "save_db"): p.save_db()
            if p and hasattr(p, "_refresh_tree"): p._refresh_tree()

    def _act_groups(self):
        from dialogs.groups_dialog import GroupsDialog
        dlg = GroupsDialog(self.data_store, self)
        dlg.exec()

    def _act_auto_schedule(self):
        from dialogs.auto_schedule_dialog import AutoScheduleDialog
        dlg = AutoScheduleDialog(self.data_store, self)
        dlg.exec()

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
            table.setItem(r, c, QTableWidgetItem(str(txt)))
