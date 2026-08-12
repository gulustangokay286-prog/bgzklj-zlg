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
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(BASE_DIR, "data", "bgz_database.json")
        self.data_store = {"dersler": [], "siniflar": [], "derslikler": [], "ogretmenler": []}
        self.load_db()

        self._build_ui()
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
            except Exception as e:
                print("DB Load Error:", e)

    def save_db(self, path=None):
        import json
        save_path = path or self.db_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self.data_store, f, ensure_ascii=False, indent=4)
            self.statusBar().showMessage(f"Veritabanı başarıyla kaydedildi: {save_path}")
        except Exception as e:
            self.statusBar().showMessage(f"Kaydetme hatası: {e}")

    def _refresh_tree(self):
        self._tree.clear()
        
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
        colors = ["#E53935", "#1E88E5", "#43A047", "#8E24AA", "#FFB300", "#00ACC1", "#D81B60", "#3949AB"]
        for idx, ders in enumerate(self.data_store.get("dersler", [])):
            unplaced.append({
                "id": idx,
                "subject_name": ders.get("kisa", ders.get("ad", f"Ders {idx}")),
                "color": colors[idx % len(colors)],
                "teacher": "Öğretmen",
                "duration": 2 # default test duration
            })
        self._grid.unplaced_dock.load_unplaced(unplaced)

    def _on_lesson_dropped(self, row, col, lesson_id, duration):
        dersler = self.data_store.get("dersler", [])
        if 0 <= lesson_id < len(dersler):
            ders = dersler[lesson_id]
            colors = ["#E53935", "#1E88E5", "#43A047", "#8E24AA", "#FFB300", "#00ACC1", "#D81B60", "#3949AB"]
            self._grid.set_cell(row, col, ders.get("kisa", "Ders"), colors[lesson_id % len(colors)], "Öğretmen", duration)
            self.statusBar().showMessage(f"Ders '{ders.get('kisa')}' {row+1}. periyot, gün {col+1} konumuna yerleştirildi.")

    # ── Actions ───────────────────────────────────────────────────────────────
    def _go_main_tab(self):
        self._ribbon._select(0)

    def _act_new(self):
        d = SchoolInfoDialog(self)
        d.exec()

    def _act_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Dosya Aç", "", "BGZ Planlama Dosyaları (*.roz);;Tüm Dosyalar (*)")
        if path:
            self.load_db(path)
            self._grid.clear_grid()
            # Also load placed lessons back into the grid if they exist
            # Here we need to implement hydration of the grid later
            self.statusBar().showMessage(f"Açıldı: {path}")

    def _act_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Farklı Kaydet", "program.roz", "BGZ Planlama Dosyaları (*.roz)")
        if path:
            # Save placed lessons into data_store
            placed = self._grid.get_placed_lessons()
            self.data_store["yerlesim"] = {f"{r},{c}": data for (r, c), data in placed.items()}
            self.save_db(path)

    def _act_print(self):
        from PySide6.QtPrintSupport import QPrinter, QPrintDialog
        printer = QPrinter()
        dlg = QPrintDialog(printer, self)
        if dlg.exec():
            self.statusBar().showMessage("Yazdırılıyor...")

    def _act_preview(self):
        # Use placed lessons from the grid
        placed = self._grid.get_placed_lessons()
        # Convert (row, col) -> lesson data for print
        print_data = {}
        for (row, col), data in placed.items():
            print_data[(row, col)] = data
        
        # Get selected class name from the entity combo
        class_name = self._grid.entity_combo.currentText() or "12/B"
        dlg = TimetablePrintPreview(print_data, class_name, self)
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

    def _open_classes(self):
        d = MasterDataDialog(1, self)
        d.exec()
        self.save_db()

    def _open_rooms(self):
        d = MasterDataDialog(2, self)
        d.exec()
        self.save_db()

    def _open_teachers(self):
        d = MasterDataDialog(3, self)
        d.exec()
        self.save_db()

    def _open_wizard(self):
        # Fallback or main entry
        d = MasterDataDialog(0, self)
        d.exec()
        self.save_db()

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
