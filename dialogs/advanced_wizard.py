"""dialogs/advanced_wizard.py - Birleşik Sihirbaz ve Tanımlama Arayüzü"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QBrush, QPolygon

from dialogs.edit_forms import DersEditDialog, SinifEditDialog, OgretmenEditDialog, DerslikEditDialog


def create_wizard_icon(name: str) -> QPixmap:
    pix = QPixmap(48, 48)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    
    selected = name.endswith("_selected")
    base_name = name.replace("_selected", "")
    
    if base_name == "book":
        # 1. DERSLER: 3D Mavi Ciltli Ders Kitabı
        p.setPen(QPen(QColor("#CBD5E1"), 0.8))
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawRect(14, 6, 26, 35)
        
        grad_cover = QLinearGradient(9, 5, 34, 43)
        grad_cover.setColorAt(0, QColor("#60A5FA"))
        grad_cover.setColorAt(0.5, QColor("#2563EB"))
        grad_cover.setColorAt(1, QColor("#1D4ED8"))
        p.setPen(QPen(QColor("#1E40AF"), 1.2))
        p.setBrush(QBrush(grad_cover))
        p.drawRoundedRect(9, 5, 27, 38, 3, 3)
        
        p.setPen(QPen(QColor("#1E3A8A"), 1))
        p.setBrush(QBrush(QColor("#1E40AF")))
        p.drawRoundedRect(9, 5, 6, 38, 2, 2)
        
        p.setPen(QPen(QColor("#93C5FD"), 0.8))
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawRoundedRect(18, 12, 14, 20, 2, 2)
        
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
        
    elif base_name in ["grad_hat", "teacher", "ogretmenler", "ogretmen"]:
        # 4. ÖĞRETMENLER: 3D Mezuniyet Kepi
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#0F172A")))
        p.drawRect(15, 23, 18, 12)
        
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
        
        p.setPen(QPen(QColor("#14532D"), 1.5))
        p.setBrush(QBrush(grad_arrow))
        p.drawPolygon(arrow)
        
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


class AdvancedWizard(QDialog):
    def __init__(self, start_idx=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sihirbaz")
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
        for data in self.data_store["dersler"]:
            self._add_row(self.table_ders, [data.get("ad",""), data.get("kisa",""), "0", "", "Ideal", "", ""])
        for data in self.data_store["siniflar"]:
            self._add_row(self.table_sinif, [data.get("ad",""), data.get("kisa",""), "0", "", "30", "", "", ""])
        for data in self.data_store["derslikler"]:
            self._add_row(self.table_derslik, [data.get("ad",""), data.get("kisa",""), "0", "", "Standart", "Merkez"])
        for data in self.data_store["ogretmenler"]:
            self._add_row(self.table_ogretmen, [data.get("ad",""), data.get("kisa",""), "0", "", "", ""])

    def closeEvent(self, event):
        if hasattr(self.main_window, "_refresh_tree"):
            self.main_window._refresh_tree()
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
        
        self.table_ders = self._create_table(["Adı", "Kısa Kodu", "Toplam", "Zaman Tablosu", "Dağılım", "Evde Hazırlık", "Max."])
        self.table_sinif = self._create_table(["Adı", "Kısa Kodu", "Toplam", "Zaman Tablosu", "2. Ders", "Hazırlık", "Öğretmen", "Öğrenci"])
        self.table_derslik = self._create_table(["Adı", "Kısa Kodu", "Toplam", "Zaman Tablosu", "Tipi", "Bina"])
        self.table_ogretmen = self._create_table(["Adı", "Kısa Kodu", "Toplam", "Zaman Tablosu", "Sınıf Öğretmeni", "Branşı"])
        
        self.stack.addWidget(self._wrap_table("Tanımlı Dersler", self.table_ders))
        self.stack.addWidget(self._wrap_table("Tanımlı Sınıflar", self.table_sinif))
        self.stack.addWidget(self._wrap_table("Tanımlı Derslikler", self.table_derslik))
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
        
        right_panel.addSpacing(20)
        
        # Orijinal 2025 Dialoglarına yönlendiren butonlar
        btn_ders_atama = ActionButton("Ders Atama", icon_name="doc")
        btn_ders_atama.clicked.connect(lambda: self._open_2025_dialog("130"))
        right_panel.addWidget(btn_ders_atama)
        
        btn_zaman = ActionButton("Zaman Tablosu", icon_name="clock")
        btn_zaman.clicked.connect(lambda: self._open_2025_dialog("135"))
        right_panel.addWidget(btn_zaman)
        
        btn_kisit = ActionButton("Kısıtlamalar", icon_name="hash")
        btn_kisit.clicked.connect(lambda: self._open_2025_dialog("124"))
        right_panel.addWidget(btn_kisit)
        
        self.btn_gruplar = ActionButton("Gruplar", icon_name="branch")
        self.btn_gruplar.clicked.connect(lambda: self._open_2025_dialog("136"))
        right_panel.addWidget(self.btn_gruplar)
        
        self.btn_tumunu_sil = ActionButton("Tümünü Sil", icon_name="minus")
        self.btn_oto_olustur = ActionButton("Otomatik Oluştur", icon_name="plus", is_primary=True)
        
        right_panel.addStretch(1)
        right_panel.addWidget(self.btn_tumunu_sil)
        right_panel.addWidget(self.btn_oto_olustur)
        
        center_layout.addLayout(right_panel)
        main_layout.addLayout(center_layout, 1)

        # --- Bottom Bar ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 8, 0, 0)
        
        btn_yardim = QPushButton("Yardım")
        btn_yardim.setFixedHeight(28)
        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setFixedHeight(28)
        btn_bilgi = QPushButton("Bilgi Al")
        btn_bilgi.setFixedHeight(28)
        
        btn_kapat = QPushButton("Kapat")
        btn_kapat.setFixedHeight(28)
        btn_kapat.clicked.connect(self.accept)
        
        for b in (btn_yardim, btn_kaydet, btn_bilgi, btn_kapat):
            b.setFont(QFont("Segoe UI", 9))
            b.setFixedWidth(80)
        
        bottom_layout.addWidget(btn_yardim)
        bottom_layout.addWidget(btn_kaydet)
        bottom_layout.addWidget(btn_bilgi)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(btn_kapat)
        
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
        return t

    def _wrap_table(self, title, table):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)
        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet("padding: 4px; border-bottom: 1px solid #D0D0D0;")
        l.addWidget(lbl)
        l.addWidget(table, 1)
        return w

    def _select_tab(self, idx):
        titles = ["Dersler", "Sınıflar", "Derslikler", "Öğretmenler"]
        self.setWindowTitle(titles[idx] if idx < len(titles) else "Sihirbaz")
        
        # Sağ menü buton görünürlükleri
        self.btn_gruplar.setVisible(idx == 1)  # Sadece sınıflarda (idx 1) göster
        
        show_derslik_btns = (idx == 2) # Sadece dersliklerde (idx 2) göster
        self.btn_tumunu_sil.setVisible(show_derslik_btns)
        self.btn_oto_olustur.setVisible(show_derslik_btns)
        
        for i, b in enumerate(self.left_btns):
            b.setChecked(i == idx)
        self.stack.setCurrentIndex(idx)

    def _act_new(self):
        idx = self.stack.currentIndex()
        if idx == 0:  # Dersler
            d = DersEditDialog(self)
            if d.exec():
                data = d.get_data()
                self.data_store["dersler"].append(data)
                self._add_row(self.table_ders, [data.get("ad",""), data.get("kisa",""), "0", "", "Ideal", "", ""])
        elif idx == 1:  # Sınıflar
            d = SinifEditDialog(self)
            if d.exec():
                data = d.get_data()
                self.data_store["siniflar"].append(data)
                self._add_row(self.table_sinif, [data.get("ad",""), data.get("kisa",""), "0", "", "30", "", "", ""])
        elif idx == 2:  # Derslikler
            d = DerslikEditDialog(self)
            if d.exec():
                data = d.get_data()
                self.data_store["derslikler"].append(data)
                self._add_row(self.table_derslik, [data.get("ad",""), data.get("kisa",""), "0", "", "Standart", "Merkez"])
        elif idx == 3:  # Öğretmenler
            d = OgretmenEditDialog(self)
            if d.exec():
                data = d.get_data()
                self.data_store["ogretmenler"].append(data)
                self._add_row(self.table_ogretmen, [data.get("ad",""), data.get("kisa",""), "0", "", "", ""])

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
                data_list[row] = new_data
                table.item(row, 0).setText(new_data.get("ad", ""))
                table.item(row, 1).setText(new_data.get("kisa", ""))

    def _act_delete(self):
        idx = self.stack.currentIndex()
        tables = [self.table_ders, self.table_sinif, self.table_derslik, self.table_ogretmen]
        stores = ["dersler", "siniflar", "derslikler", "ogretmenler"]
        
        table = tables[idx]
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)
            if row < len(self.data_store[stores[idx]]):
                self.data_store[stores[idx]].pop(row)

    def _open_2025_dialog(self, dlg_id):
        from dialogs.extracted_dialog import open_extracted_dialog
        open_extracted_dialog(dlg_id, self.parent())

    def _add_row(self, table, texts):
        r = table.rowCount()
        table.insertRow(r)
        for c, txt in enumerate(texts):
            table.setItem(r, c, QTableWidgetItem(str(txt)))
