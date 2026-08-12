"""
main_window.py  –  Ana pencere
Pixel-perfect aSc k12 Bilişim Ders Planlama 2020 ribbon + workspace
"""
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QSplitter, QTreeWidget, QTreeWidgetItem, QStatusBar,
    QMessageBox, QTabWidget, QFrame, QSizePolicy, QMenu, QToolButton, QFileDialog
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPen, QLinearGradient, QBrush, QAction

from ribbon_widget import RibbonWidget, make_icon
from timetable_grid import TimetableGrid
from dialogs.master_data_dialog import MasterDataDialog
from dialogs.school_info import SchoolInfoDialog
from dialogs.auto_schedule_dialog import AutoScheduleDialog
from dialogs.print_preview import TimetablePrintPreview
from core.timetable_data import TimetableData

APP_TITLE = "BGZ Ders Planlama"
VERSION   = "2025"

PASTEL_DISTINCT_COLORS = [
    "#1E88E5", "#43A047", "#FB8C00", "#8E24AA", "#E53935",
    "#00ACC1", "#7CB342", "#FFB300", "#6D4C41", "#546E7A",
    "#3949AB", "#00897B", "#F4511E", "#D81B60", "#00838F",
    "#5E35B1", "#A1887F", "#0097A7", "#C2185B", "#F57C00"
]

def format_tr_name(name_str: str) -> str:
    """Capitalizes Turkish names properly (e.g. 'hüseyin arman' -> 'Hüseyin Arman', 'ali ihsan' -> 'Ali İhsan')."""
    if not name_str:
        return name_str
    words = name_str.strip().split()
    formatted = []
    tr_upper_map = {'i': 'İ', 'ı': 'I', 'ç': 'Ç', 'ğ': 'Ğ', 'ö': 'Ö', 'ş': 'Ş', 'ü': 'Ü'}
    tr_lower_map = {'İ': 'i', 'I': 'ı', 'Ç': 'ç', 'Ğ': 'ğ', 'Ö': 'ö', 'Ş': 'ş', 'Ü': 'ü'}
    
    for w in words:
        if not w:
            continue
        first = w[0]
        rest = w[1:]
        first_cap = tr_upper_map.get(first, first.upper())
        rest_lower = "".join(tr_lower_map.get(c, c.lower()) for c in rest)
        formatted.append(first_cap + rest_lower)
        
    return " ".join(formatted)

def get_subject_color(subject_name: str) -> str:
    """Returns a deterministic, vibrant, distinct color for any subject name."""
    if not subject_name:
        return "#1E88E5"
    hash_val = sum(ord(c) * (i + 1) for i, c in enumerate(subject_name.strip()))
    return PASTEL_DISTINCT_COLORS[hash_val % len(PASTEL_DISTINCT_COLORS)]

def make_menu_icon(symbol: str, color1: str, color2: str) -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 0, 32)
    grad.setColorAt(0, QColor(color1))
    grad.setColorAt(1, QColor(color2))
    p.setBrush(QBrush(grad))
    p.setPen(QPen(QColor(0,0,0,50), 1))
    p.drawRoundedRect(4, 4, 24, 24, 6, 6)
    p.setPen(QPen(Qt.white, 2))
    p.setFont(QFont("Segoe UI", 12, QFont.Bold))
    p.drawText(4, 4, 24, 24, Qt.AlignCenter, symbol)
    p.end()
    return QIcon(pix)


class TitleBar(QWidget):
    """Working file menu button + Title bar"""
    def __init__(self, logo_path, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setStyleSheet("background: #F0F0F0; border-bottom: 1px solid #D0D0D0;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 8, 0)

        # File menu button (top-left circle)
        self.file_btn = QToolButton(self)
        # Use a nice 3D icon instead of text
        self.file_btn.setIcon(make_menu_icon("M", "#0078D7", "#005A9E"))
        self.file_btn.setIconSize(QSize(28, 28))
        self.file_btn.setFixedSize(32, 32)
        self.file_btn.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 4px;
            }
            QToolButton:hover { background: #E5F1FB; }
            QToolButton::menu-indicator { image: none; }
        """)
        self.file_menu = QMenu(self.file_btn)
        self.file_menu.setStyleSheet("""
            QMenu { background: #FFFFFF; border: 1px solid #CCC; font-family: 'Segoe UI'; font-size: 10pt; }
            QMenu::item { padding: 8px 30px; }
            QMenu::item:selected { background: #0078D7; color: white; }
            QMenu::separator { height: 1px; background: #DDD; margin: 3px 10px; }
        """)
        self.file_btn.setMenu(self.file_menu)
        self.file_btn.setPopupMode(QToolButton.InstantPopup)
        layout.addWidget(self.file_btn)

        layout.addStretch(1)

        title = QLabel(f"{APP_TITLE} {VERSION}", self)
        title.setFont(QFont("Segoe UI", 9))
        title.setStyleSheet("color: #333333;")
        layout.addWidget(title)


class MainWindow(QMainWindow):
    def __init__(self, logo_path=None):
        super().__init__()
        self._logo = logo_path
        self.setWindowTitle(f"{APP_TITLE} {VERSION}")
        self.resize(1280, 780)
        self.setMinimumSize(900, 600)

        if logo_path and os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        # Core Data Engine Initialization
        self.tt_data = TimetableData()
        user_dir = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
        os.makedirs(user_dir, exist_ok=True)
        self.db_path = os.path.join(user_dir, "bgz_database.json")
        
        # Seed from workspace data if user database does not exist yet
        base_dir = os.path.dirname(os.path.abspath(__file__))
        init_db = os.path.join(base_dir, "data", "bgz_database.json")
        if not os.path.exists(self.db_path) and os.path.exists(init_db):
            import shutil
            try:
                shutil.copy(init_db, self.db_path)
            except Exception:
                pass
                
        self.data_store = {"dersler": [], "siniflar": [], "derslikler": [], "ogretmenler": [], "atamalar": []}
        self.load_db()

        self._build_ui()
        self._restore_grid_placements()
        self._refresh_tree()

    # ──────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        # Title bar
        self._title_bar = TitleBar(self._logo, root)
        root_layout.addWidget(self._title_bar)
        
        # Wire the file menu
        fm = self._title_bar.file_menu
        
        act_new = QAction(make_menu_icon("N", "#4CAF50", "#2E7D32"), "Yeni", self)
        act_new.triggered.connect(self._act_new)
        fm.addAction(act_new)
        
        act_open = QAction(make_menu_icon("O", "#FFCA28", "#FF8F00"), "Aç", self)
        act_open.triggered.connect(self._act_open)
        fm.addAction(act_open)
        
        act_save = QAction(make_menu_icon("S", "#29B6F6", "#0277BD"), "Kaydet", self)
        act_save.triggered.connect(self._act_save)
        fm.addAction(act_save)
        
        fm.addSeparator()
        
        act_print = QAction(make_menu_icon("P", "#AB47BC", "#6A1B9A"), "Yazdır", self)
        act_print.triggered.connect(self._act_print)
        fm.addAction(act_print)
        
        act_prev = QAction(make_menu_icon("V", "#26C6DA", "#00838F"), "Ön İzleme", self)
        act_prev.triggered.connect(self._act_preview)
        fm.addAction(act_prev)
        
        fm.addSeparator()
        
        act_about = QAction(make_menu_icon("?", "#B0BEC5", "#546E7A"), "Hakkında", self)
        act_about.triggered.connect(lambda: QMessageBox.about(self, "Hakkında", f"{APP_TITLE} {VERSION}\n\nBGZ Ders Planlama Yazılımı"))
        fm.addAction(act_about)
        
        fm.addSeparator()
        
        act_exit = QAction(make_menu_icon("X", "#EF5350", "#C62828"), "Çıkış", self)
        act_exit.triggered.connect(self.close)
        fm.addAction(act_exit)

        # Ribbon
        self._ribbon = RibbonWidget(root)
        self._build_ribbon()
        root_layout.addWidget(self._ribbon)

        # Workspace
        workspace = self._build_workspace(root)
        root_layout.addWidget(workspace, 1)

        # Status bar
        sb = QStatusBar(self)
        sb.setFont(QFont("Segoe UI", 8))
        sb.showMessage(f"{APP_TITLE} {VERSION}  |  Hazır")
        self.setStatusBar(sb)

    # ── Ribbon ────────────────────────────────────────────────────────────────
    def _build_ribbon(self):
        r = self._ribbon

        # ── 1. Ana Menü ──────────────────────────────────────────────────────
        p1 = r.add_tab("Ana Menü")
        p1.add_button("Yeni",           "yeni",     self._act_new)
        p1.add_button("Aç",             "ac",       self._act_open)
        p1.add_button("Kaydet",         "kaydet",   self._act_save)
        p1.add_button("Yazdır",         "yazdir",   self._act_print)
        p1.add_button("Ön İzleme",      "on_izleme",self._act_preview)
        p1.add_divider()
        p1.add_button("Dersler",        "ders",     self._open_subjects)
        p1.add_button("Sınıflar",       "sinif",    self._open_classes)
        p1.add_button("Derslikler",     "derslik",  self._open_rooms)
        p1.add_button("Öğretmenler",    "ogretmen", self._open_teachers)
        p1.add_button("Seçmeli\nDersler","ders",    lambda: self._open_extracted(118))
        p1.add_button("Planlama\nİlişkileri","plan",lambda: self._open_extracted(123))
        p1.add_divider()
        p1.add_button("Planlama\nÖncesi Kontrol","kontrol",lambda: self._open_extracted(130))
        p1.add_button("Otomatik\nPlanlamayı Başlat","otomatik",self._act_auto_schedule)
        p1.add_button("Bulut Tabanlı\nPlanlama","bulut",lambda: self._open_extracted(132))
        p1.add_button("Planlama Sonrası\nKontrol","kontrol",lambda: self._open_extracted(133))
        p1.add_divider()
        p1.add_button("Temel\nBilgiler",  "bilgi",    lambda: self._open_extracted(100))
        p1.add_button("İnternet\nHesabı","internet", lambda: self._open_extracted(140))
        p1.add_button("Sorular?\nYorumlar?","yardim",lambda: self._open_extracted(141))
        p1.add_stretch()

        # ── 2. Dosya İşlemleri ───────────────────────────────────────────────
        p2 = r.add_tab("Dosya İşlemleri")
        p2.add_back(self._go_main_tab)
        p2.add_button("Yeni",       "yeni",   self._act_new)
        p2.add_button("Aç",         "ac",     self._act_open)
        p2.add_button("Kapat",      "temizle",self._act_close)
        p2.add_button("Demo\nDosyaları","bilgi",self._act_nyi)
        p2.add_divider()
        p2.add_button("Kaydet",     "kaydet", self._act_save)
        p2.add_button("Yazdır",     "yazdir", self._act_print)
        p2.add_button("Ön İzleme",  "on_izleme",self._act_preview)
        p2.add_button("Bilgi Al",   "bilgi",  self._act_nyi)
        p2.add_button("Aktar",      "internet",self._act_nyi)
        p2.add_button("Karşılaştırma","bilgi",self._act_nyi)
        p2.add_button("E-Mail\nGönder","internet",self._act_nyi)
        p2.add_button("İnternet\nHesabı","internet",self._act_nyi)
        p2.add_stretch()

        # ── 3. Tanımlama İşlemleri ───────────────────────────────────────────
        p3 = r.add_tab("Tanımlama İşlemleri")
        p3.add_back(self._go_main_tab)
        p3.add_button("Sihirbaz",   "sihirbaz",self._open_wizard)
        p3.add_button("Temel\nBilgiler","bilgi",self._act_nyi)
        p3.add_divider()
        p3.add_button("Dersler",    "ders",   self._open_subjects)
        p3.add_button("Sınıflar",   "sinif",  self._open_classes)
        p3.add_button("Derslikler", "derslik",self._open_rooms)
        p3.add_button("Öğretmenler","ogretmen",self._open_teachers)
        p3.add_button("Seçmeli\nDersler","ders",lambda: self._open_extracted(118))
        p3.add_button("Planlama\nİlişkileri","plan",lambda: self._open_extracted(123))
        p3.add_button("Tanımlanan\nKısıtlamalar","kontrol",lambda: self._open_extracted(126))
        p3.add_divider()
        p3.add_button("Değiştir",   "param",  lambda: self._open_extracted(135))
        p3.add_stretch()

        # ── 4. Görünüm ───────────────────────────────────────────────────────
        p4 = r.add_tab("Görünüm")
        p4.add_back(self._go_main_tab)
        p4.add_button("Geri Al\nCtrl+Z","bilgi",self._act_undo)
        p4.add_button("Tekrarla\nCtrl+Y","bilgi",self._act_redo)
        p4.add_divider()
        p4.add_button("Görünüm",    "plan",   self._act_nyi)
        p4.add_button("Yakınlaştır","istatistik",self._act_nyi)
        p4.add_button("Hafta",      "plan",   self._act_nyi)
        p4.add_button("Sekmeleri\nGöster","bilgi",self._act_nyi)
        p4.add_button("Ders Programı\nİle İlgili","plan",self._act_nyi)
        p4.add_stretch()

        # ── 5. Planlama / Yerleştirme ────────────────────────────────────────
        p5 = r.add_tab("Planlama / Yerleştirme")
        p5.add_back(self._go_main_tab)
        p5.add_button("Planlama\nÖncesi Kontrol","kontrol",self._act_nyi)
        p5.add_button("Otomatik\nPlanlamayı Başlat","otomatik",self._act_auto_schedule)
        p5.add_button("Bulut Tabanlı\nPlanlama","bulut",self._act_nyi)
        p5.add_divider()
        p5.add_button("İyileştirme\nUygula","param",self._act_nyi)
        p5.add_button("Analiz",     "istatistik",self._act_nyi)
        p5.add_button("Parametreler","param",self._act_nyi)
        p5.add_button("Tanımlanan\nKısıtlamalar","kontrol",self._act_nyi)
        p5.add_divider()
        p5.add_button("Planlama Sonrası\nKontrol","kontrol",self._act_nyi)
        p5.add_button("Danışman",   "yardim",self._act_nyi)
        p5.add_button("İstatistik", "istatistik",self._act_nyi)
        p5.add_divider()
        p5.add_button("Dersliklere\nAtama","derslik",self._act_nyi)
        p5.add_button("Kart\nKilitle","kilit",self._act_nyi)
        p5.add_button("Kilit Aç",   "kilit",  self._act_nyi)
        p5.add_button("Tabloyu\nTemizle","temizle",self._act_clear_schedule)
        p5.add_stretch()

        # ── 6. Arayüz Ayarları ───────────────────────────────────────────────
        p6 = r.add_tab("Arayüz Ayarları")
        p6.add_back(self._go_main_tab)
        p6.add_button("Temel\nBilgiler","bilgi",  lambda: self._open_extracted(100))
        p6.add_button("Yazılımı\nÖzelleştir","param",self._act_nyi)
        p6.add_button("Gelişmiş",   "param",  lambda: self._open_extracted(135))
        p6.add_divider()
        p6.add_button("Uygulama\nRenk Teması","renk",lambda: self._open_extracted(136))
        p6.add_button("Yazı",       "yazi",   lambda: self._open_extracted(137))
        p6.add_button("Menü Dil\nGüncelle","dil",lambda: self._open_extracted(138))
        p6.add_divider()
        p6.add_checkbox("Durum Çubukları Göster/Gizle", True)
        p6.add_checkbox("Ana Menü Tuşlarını Göster/Gizle", True)
        p6.add_checkbox("Hızlı Başlat Tuşlarını Göster/Gizle", False)
        p6.add_stretch()

        # ── 7. Yardım ────────────────────────────────────────────────────────
        p7 = r.add_tab("Yardım")
        p7.add_back(self._go_main_tab)
        p7.add_button("Tanıtım Ve\nÖğrenme","bilgi",self._act_nyi)
        p7.add_button("Günlük\nİpucu","bilgi",self._act_nyi)
        p7.add_button("Demo Dosyaları\nGöster","bilgi",self._act_nyi)
        p7.add_divider()
        p7.add_button("Program Dilini\nDeğiştir","dil",self._act_nyi)
        p7.add_button("Lisans\nBilgi Kartı","kilit",self._act_nyi)
        p7.add_button("Teknik\nDestek","yardim",self._act_nyi)
        p7.add_button("Yeni Versiyon\nKontrolü","internet",self._act_nyi)
        p7.add_button("Hizmet Yenilemek\nİçin Tıklayınız","internet",self._act_nyi)
        p7.add_divider()
        p7.add_button("Online\nYardım","yardim",self._act_nyi)
        p7.add_button("Sorular?\nYorumlar?","yardim",self._act_nyi)
        p7.add_stretch()

    # ── Workspace ─────────────────────────────────────────────────────────────
    def _build_workspace(self, parent):
        splitter = QSplitter(Qt.Horizontal, parent)
        splitter.setHandleWidth(3)

        # Left panel
        left = QWidget(splitter)
        left.setMinimumWidth(200)
        left.setMaximumWidth(300)
        left.setStyleSheet("background: #F5F7FA;")
        l_layout = QVBoxLayout(left)
        l_layout.setContentsMargins(4, 4, 4, 4)

        lbl = QLabel("Ders Programı Öğeleri", left)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        lbl.setStyleSheet("color: #1E6DB5; padding: 4px;")
        l_layout.addWidget(lbl)

        self._tree = QTreeWidget(left)
        self._tree.setHeaderLabels(["Ad", "Detay"])
        self._tree.setFont(QFont("Segoe UI", 8))
        self._tree.setStyleSheet("""
            QTreeWidget { border: 1px solid #DDD; background: #FFFFFF; }
            QTreeWidget::item:hover { background: #EAF2FF; }
            QTreeWidget::item:selected { background: #BCD8F8; color: #0D47A1; }
        """)
        l_layout.addWidget(self._tree)

        # Right panel  
        right = QWidget(splitter)
        r_layout = QVBoxLayout(right)
        r_layout.setContentsMargins(4, 4, 4, 4)
        r_layout.setSpacing(4)

        # Tab widget for multiple views
        self._tab_widget = QTabWidget(right)
        self._tab_widget.setFont(QFont("Segoe UI", 9))
        self._tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #BCC8D8; }
            QTabBar::tab { padding: 5px 14px; font-size: 9pt; }
            QTabBar::tab:selected { background: #FFFFFF; border-bottom: 3px solid #1E6DB5; color: #1E6DB5; }
            QTabBar::tab:!selected { background: #F0F0F0; color: #555; }
        """)

        # Main timetable grid
        self._grid = TimetableGrid(8, right)
        self._tab_widget.addTab(self._grid, "Haftalık Program")
        
        # Connect drop signal
        self._grid.table.lesson_dropped.connect(self._on_lesson_dropped)
        self._grid.cell_right_clicked.connect(self._on_cell_edit)

        r_layout.addWidget(self._tab_widget)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([220, 1060])

        return splitter

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Kaydet",
            "Çıkmadan önce değişiklikleri kaydetmek ister misiniz?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self._act_save()
            event.accept()
        elif reply == QMessageBox.No:
            event.accept()
        else:
            event.ignore()

    def load_db(self, path=None):
        import json
        load_path = path or self.db_path
        if os.path.exists(load_path):
            try:
                with open(load_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data_store.update(loaded)
                self.statusBar().showMessage(f"Veriler yüklendi: {load_path}")
                
                # Restore grid placements
                self._restore_grid_placements()
            except Exception as e:
                print("DB Load Error:", e)
    
    def _restore_grid_placements(self):
        if not hasattr(self, "_grid"):
            return
        grid_data = self.data_store.get("grid_placements", {})
        if grid_data:
            self._grid.clear_grid()
            for key, info in grid_data.items():
                parts = key.split(",")
                if len(parts) == 2:
                    r, c = int(parts[0]), int(parts[1])
                    self._grid.set_cell(
                        r, c,
                        info.get("subject_name", "Ders"),
                        info.get("color", "#1E88E5"),
                        info.get("teacher_name", ""),
                        info.get("duration", 1)
                    )

    def save_db(self, path=None):
        import json
        save_path = path or self.db_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Save grid placements into data_store before writing
        grid_data = {}
        for (r, c), info in self._grid.get_placed_lessons().items():
            grid_data[f"{r},{c}"] = info
        self.data_store["grid_placements"] = grid_data
        
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self.data_store, f, ensure_ascii=False, indent=4)
            self.statusBar().showMessage(f"Veritabanı başarıyla kaydedildi: {save_path}")
        except Exception as e:
            self.statusBar().showMessage(f"Kaydetme hatası: {e}")

        try:
            with open("bgz_database.json", "w", encoding="utf-8") as f2:
                json.dump(self.data_store, f2, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def _refresh_tree(self):
        self._tree.clear()
        
        # 0. Sanitize & Capitalize Teacher Names and Assign Distinct Subject Colors across data_store
        for t in self.data_store.get("ogretmenler", []):
            if t.get("ad"):
                t["ad"] = format_tr_name(t["ad"])
                if not t.get("kisa"):
                    t["kisa"] = t["ad"][:4].upper()

        for d in self.data_store.get("dersler", []):
            if d.get("ad"):
                d["color"] = get_subject_color(d["ad"])
                d["renk"] = d["color"]

        for a in self.data_store.get("atamalar", []):
            if a.get("teacher"):
                a["teacher"] = format_tr_name(a["teacher"])
            if a.get("subject"):
                a["color"] = get_subject_color(a["subject"])

        grid_placements = self.data_store.get("grid_placements", {})
        for key, info in grid_placements.items():
            if info.get("teacher_name"):
                info["teacher_name"] = format_tr_name(info["teacher_name"])
            if info.get("subject_name"):
                info["color"] = get_subject_color(info["subject_name"])

        if hasattr(self, "_grid") and hasattr(self._grid, "_placed_lessons"):
            for key, info in self._grid._placed_lessons.items():
                if info.get("teacher_name"):
                    info["teacher_name"] = format_tr_name(info["teacher_name"])
                if info.get("subject_name"):
                    info["color"] = get_subject_color(info["subject_name"])
        
        s_count = len(self.data_store.get("siniflar", []))
        t_count = len(self.data_store.get("ogretmenler", []))
        d_count = len(self.data_store.get("dersler", []))
        r_count = len(self.data_store.get("derslikler", []))
        
        QTreeWidgetItem(self._tree, ["Sınıflar", f"{s_count} Sınıf"])
        QTreeWidgetItem(self._tree, ["Öğretmenler", f"{t_count} Öğretmen"])
        QTreeWidgetItem(self._tree, ["Dersler", f"{d_count} Ders"])
        QTreeWidgetItem(self._tree, ["Derslikler", f"{r_count} Derslik"])
        
        self._tree.expandAll()
        
        unplaced = []
        
        # 1. Add explicitly assigned lessons from self.data_store["atamalar"]
        atamalar = self.data_store.get("atamalar", [])
        existing_teachers = [t.get("ad") for t in self.data_store.get("ogretmenler", []) if t.get("ad")]
        existing_subjects = [d.get("ad") for d in self.data_store.get("dersler", []) if d.get("ad")]
        
        # Auto-register subjects/teachers that were assigned but not yet in master data
        for a in atamalar:
            t_name = format_tr_name(a.get("teacher"))
            s_name = a.get("subject")
            if t_name and t_name not in existing_teachers:
                self.data_store.setdefault("ogretmenler", []).append({"ad": t_name, "kisa": t_name[:4].upper()})
                existing_teachers.append(t_name)
            if s_name and s_name not in existing_subjects:
                self.data_store.setdefault("dersler", []).append({"ad": s_name, "kisa": s_name[:3].upper(), "color": get_subject_color(s_name)})
                existing_subjects.append(s_name)

        for idx, atama in enumerate(atamalar):
            subj_name = atama.get("subject", "Ders")
            teacher_name = format_tr_name(atama.get("teacher", ""))
            cls_name = atama.get("class", "")
            dur = atama.get("duration", 2)
            type_str = str(atama.get("type", ""))
            
            # Parse custom breakdown like "2+3", "3+1", "2+1", "1+1+1"
            parts = []
            if "+" in type_str:
                for p in type_str.split("+"):
                    p_clean = p.strip()
                    if p_clean.isdigit():
                        parts.append(int(p_clean))
            
            if not parts:
                parts = [dur]
                
            for p_idx, block_dur in enumerate(parts):
                unplaced.append({
                    "id": f"{idx}_{p_idx}",
                    "subject_name": subj_name,
                    "color": get_subject_color(subj_name),
                    "teacher": teacher_name,
                    "class_name": cls_name,
                    "duration": block_dur
                })
            
        # 2. Add defined subjects from self.data_store["dersler"] if not already in atamalar
        defined_subjects = self.data_store.get("dersler", [])
        assigned_subj_names = {a.get("subject") for a in atamalar}
        
        for idx, ders in enumerate(defined_subjects):
            sname = ders.get("kisa") or ders.get("ad")
            if sname and (sname not in assigned_subj_names and ders.get("ad") not in assigned_subj_names):
                unplaced.append({
                    "id": len(unplaced),
                    "subject_name": sname,
                    "color": get_subject_color(sname),
                    "teacher": "Öğretmen",
                    "class_name": "",
                    "duration": 2
                })
                
        self._grid.unplaced_dock.load_unplaced(unplaced)

    def _on_lesson_dropped(self, row, col, lesson_info):
        subject_name = lesson_info.get("subject_name", "Ders")
        color = get_subject_color(subject_name)
        teacher = format_tr_name(lesson_info.get("teacher", ""))
        cls_name = lesson_info.get("class_name", "")
        duration = lesson_info.get("duration", 1)
        
        from timetable_grid import DAYS
        day_name = DAYS[col] if 0 <= col < len(DAYS) else f"{col+1}. Gün"
        
        # 1. Check Teacher Constraints (Time-off / Kapalı gün/saat)
        kisitlamalar = self.data_store.get("kisitlamalar", {})
        if teacher and teacher in kisitlamalar:
            cell_key = f"{col},{row}"
            is_available = kisitlamalar[teacher].get(cell_key, True)
            if not is_available:
                QMessageBox.warning(
                    self, "Kısıtlama Engeli",
                    f"⚠️ '{teacher}' öğretmeninin {day_name} günü {row+1}. ders saatinde 'ÇALIŞAMAZ / KAPALI' kısıtlaması bulunmaktadır!\nDers yerleştirilemez."
                )
                self.statusBar().showMessage(f"Kısıtlama engeli: {teacher} - {day_name} {row+1}. saat kapalı!")
                return
                
        # 2. Check Teacher Conflict (Is teacher already placed elsewhere at this slot?)
        teacher_info = next((t for t in self.data_store.get("ogretmenler", []) if t.get("ad") == teacher), {})
        allows_parallel = teacher_info.get("es_zamanli", False)
        
        if not allows_parallel:
            placed = self._grid.get_placed_lessons()
            for (r, c), data in placed.items():
                if (r, c) == (row, col) and data.get("teacher") == teacher and teacher != "":
                    QMessageBox.warning(
                        self, "Çakışma Engeli",
                        f"⚠️ '{teacher}' öğretmeni {day_name} günü {row+1}. ders saatinde zaten başka bir derste görevlidir!\n(Farklı bir sınıfta eş zamanlı ders vermek için öğretmen düzenleme ekranından 'Çoklu Ders İzni' seçeneğini açabilirsiniz)."
                    )
                    return

        self._grid.set_cell(row, col, subject_name, color, teacher, duration, class_name=cls_name)
        self.statusBar().showMessage(f"'{subject_name}' dersi {day_name} günü {row+1}. ders saatine yerleştirildi.")
        self.save_db()

    # ── Actions ───────────────────────────────────────────────────────────────
    def _go_main_tab(self):
        self._ribbon._select(0)

    def _on_cell_edit(self, row, col):
        from dialogs.edit_forms import LessonAssignmentDialog
        dlg = LessonAssignmentDialog(data_store=self.data_store, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            if isinstance(data, list):
                self.data_store.setdefault("atamalar", []).extend(data)
            else:
                self.data_store.setdefault("atamalar", []).append(data)
            self.save_db()
            self._refresh_tree()

    def _act_new(self):
        from PySide6.QtWidgets import QInputDialog
        opts = [
            "🏫 Kurum / Sınıf Haftalık Ders Programı Oluştur",
            "🎓 Öğrenci Bireysel Ders Programı Oluştur"
        ]
        choice, ok = QInputDialog.getItem(self, "Yeni Program Yapılandır", "Oluşturmak istediğiniz program türünü seçin:", opts, 0, False)
        if ok and choice:
            if "Öğrenci" in choice:
                self.statusBar().showMessage("Öğrenci Bireysel Ders Programı Modu Aktif.")
                self._grid.view_combo.setCurrentText("Öğrenci Görünümü")
            else:
                d = SchoolInfoDialog(self)
                d.exec()

    def _act_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Dosya Aç", "", "BGZ Planlama Dosyaları (*.roz);;Tüm Dosyalar (*)")
        if path:
            self.load_db(path)
            self._grid.clear_grid()
            self._refresh_tree()
            self.statusBar().showMessage(f"Açıldı: {path}")

    def _act_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Farklı Kaydet", "program.roz", "BGZ Planlama Dosyaları (*.roz)")
        if path:
            placed = self._grid.get_placed_lessons()
            self.data_store["yerlesim"] = {f"{r},{c}": data for (r, c), data in placed.items()}
            self.save_db(path)

    def _act_print(self):
        dlg = TimetablePrintPreview(self.data_store, self._grid.get_placed_lessons(), self)
        dlg.exec()

    def _act_preview(self):
        dlg = TimetablePrintPreview(self.data_store, self._grid.get_placed_lessons(), self)
        dlg.exec()

    def _act_close(self):
        self.statusBar().showMessage("Dosya kapatıldı.")

    def _act_undo(self):
        self.statusBar().showMessage("Geri alındı.")

    def _act_redo(self):
        self.statusBar().showMessage("Tekrarlandı.")

    def _open_subjects(self):
        d = MasterDataDialog(0, self)
        d.exec()
        self.save_db()
        self._refresh_tree()

    def _open_classes(self):
        d = MasterDataDialog(1, self)
        d.exec()
        self.save_db()
        self._refresh_tree()

    def _open_rooms(self):
        d = MasterDataDialog(2, self)
        d.exec()
        self.save_db()
        self._refresh_tree()

    def _open_teachers(self):
        d = MasterDataDialog(3, self)
        d.exec()
        self.save_db()
        self._refresh_tree()

    def _open_wizard(self):
        d = MasterDataDialog(0, self)
        d.exec()
        self.save_db()
        self._refresh_tree()

    def _act_auto_schedule(self):
        d = AutoScheduleDialog(self)
        d.exec()

    def _act_clear_schedule(self):
        r = QMessageBox.question(self, "Tabloyu Temizle",
            "Tüm ders yerleştirmeleri silinecek. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            self._grid.clear_grid()
            self.statusBar().showMessage("Tablo temizlendi.")

    def _open_extracted(self, dialog_id):
        from dialogs.extracted_dialog import open_extracted_dialog
        open_extracted_dialog(dialog_id, self)

    def _act_nyi(self):
        self.statusBar().showMessage("Bu özellik yakında eklenecek.")
