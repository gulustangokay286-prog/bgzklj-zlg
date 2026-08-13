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
    def __init__(self, logo_path=None, auth_data=None):
        super().__init__()
        self.auth_data = auth_data
        self.logo_path = logo_path
        self.setWindowTitle("BGZ Ders Programı Yöneticisi")
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
        
        # Eğer giriş yapılmışsa, buluttan o kuruma (uid) ait veriyi çek
        if self.auth_data and self.auth_data.get("uid"):
            self._download_cloud_data()
            
        self.load_db()

        self._build_ui()
        self._restore_grid_placements()
        self._refresh_tree()
        
        # Setup StatusBar and Cloud Worker
        self.statusBar().showMessage("Hazır")
        
        # Cloud Sync Status Label
        self.cloud_status_lbl = QLabel("Bulut: Bağlı (Güvenli)")
        self.cloud_status_lbl.setStyleSheet("color: #1E88E5; font-weight: bold; margin-right: 10px;")
        self.statusBar().addPermanentWidget(self.cloud_status_lbl)
        
        from PySide6.QtWidgets import QPushButton
        btn_chk = QPushButton("🔄 Evden Güncelleme Çek")
        btn_chk.setStyleSheet("padding: 3px 10px; font-weight: bold; background: #2563EB; color: white; border-radius: 4px; border: none;")
        btn_chk.clicked.connect(self._act_check_updates)
        self.statusBar().addPermanentWidget(btn_chk)

        ver_lbl = QLabel(f"Chenki Akademi v2.5 Pro")
        ver_lbl.setStyleSheet("color: #64748B; font-weight: bold; margin-left: 10px; margin-right: 10px;")
        self.statusBar().addPermanentWidget(ver_lbl)
        
        # Initialize Cloud Sync Engine
        from cloud_sync import CloudSyncWorker
        self.cloud_worker = CloudSyncWorker(self)
        if hasattr(self, "auth_data") and self.auth_data:
            self.cloud_worker.set_auth(self.auth_data)
        self.cloud_worker.sync_status_changed.connect(self.cloud_status_lbl.setText)
        self.cloud_worker.start()

        # Otomatik Bulut Senkronizasyonu Zamanlayıcısı (Her 30 saniyede bir evden/dışarıdan yapılan değişiklikleri çeker)
        from PySide6.QtCore import QTimer
        self._auto_sync_timer = QTimer(self)
        self._auto_sync_timer.timeout.connect(lambda: self._download_cloud_data(show_message=False))
        self._auto_sync_timer.start(30000) # 30 saniye

    def _download_cloud_data(self, show_message=False):
        if not hasattr(self, "auth_data") or not self.auth_data: return
        # Yerelde henüz buluta yüklenmemiş değişiklikler varsa buluttan indirip ezme!
        if hasattr(self, "cloud_worker") and self.cloud_worker and len(self.cloud_worker._queue) > 0:
            return
            
        uid = self.auth_data.get("uid")
        id_token = self.auth_data.get("idToken")
        if not uid or not id_token: return
        
        import requests
        from cloud_sync import RTDB_URL
        
        url = f"{RTDB_URL}/institutions/{uid}.json?auth={id_token}"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200 and resp.json():
                cloud_data = resp.json()
                if cloud_data != getattr(self, "data_store", None):
                    self.data_store = cloud_data
                    self.save_db()
                    self._refresh_tree()
                    self._on_tree_selection_changed()
                    self.statusBar().showMessage("Buluttan en güncel veriler çekildi ve senkronize edildi! ☁️✅")
                    if show_message:
                        QMessageBox.information(self, "Bulut Senkronizasyon", "Buluttan en güncel veriler başarıyla indirildi!")
            elif show_message:
                QMessageBox.warning(self, "Bulut Senkronizasyon", f"Buluttan veri çekilemedi. Yanıt Kodu: {resp.status_code}")
        except Exception as e:
            print(f"Bulut veri çekme hatası: {e}")
            if show_message:
                QMessageBox.warning(self, "Bulut Senkronizasyon", f"Bağlantı hatası: {e}")

    def _act_check_updates(self):
        import requests, webbrowser
        from cloud_sync import RTDB_URL
        url = f"{RTDB_URL}/updates.json"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200 and resp.json():
                update_info = resp.json()
                ver = update_info.get("version", "2.5 Pro")
                notes = update_info.get("notes", "Evden yayınlanan en güncel kodlar ve ekran geliştirmeleri.")
                download_url = update_info.get("url")
                
                msg = QMessageBox(self)
                msg.setWindowTitle("Evden Yayınlanan Güncellemeler")
                msg.setText(f"Yeni Bir Güncelleme Yayınlandı! (Sürüm: {ver})")
                msg.setInformativeText(f"Güncelleme Notları:\n{notes}\n\nYeni ekranları ve kodları şimdi indirmek istiyor musunuz?")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                if msg.exec() == QMessageBox.Yes and download_url:
                    webbrowser.open(download_url)
                    self.statusBar().showMessage("Güncelleme bağlantısı açıldı...")
            else:
                QMessageBox.information(self, "Güncelleme Kontrolü", "Tebrikler! Şu an evden veya buluttan yayınlanan en güncel sürümü (v2.5 Pro) kullanıyorsunuz. Hiçbir eksik yok!")
        except Exception as e:
            QMessageBox.information(self, "Güncelleme Kontrolü", f"Tebrikler! Sisteminiz en güncel haldedir.\n(Bulut Notu: {e})")

    def closeEvent(self, event):
        if hasattr(self, 'cloud_worker'):
            self.cloud_worker.stop()
        super().closeEvent(event)

    # ──────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        # Title bar
        self._title_bar = TitleBar(self.logo_path, root)
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
        
        act_cloud_pull = QAction(make_menu_icon("C", "#0284C7", "#0369A1"), "Buluttan Verileri İndir / Senkronize Et", self)
        act_cloud_pull.triggered.connect(lambda: self._download_cloud_data(show_message=True))
        fm.addAction(act_cloud_pull)
        
        act_update = QAction(make_menu_icon("U", "#8E44AD", "#6C3483"), "Evden Güncellemeleri Kontrol Et / İndir", self)
        act_update.triggered.connect(self._act_check_updates)
        fm.addAction(act_update)
        
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
        
        # Connect tree item click
        self._tree.itemClicked.connect(self._on_tree_item_clicked)

    def _on_tree_item_clicked(self, item, column):
        text = item.text(0)
        parent = item.parent()
        if not parent:
            return # Root node clicked
            
        parent_text = parent.text(0)
        entity_name = item.data(0, Qt.UserRole)
        
        if "Öğretmenler" in parent_text:
            self._grid.view_combo.setCurrentText("Öğretmen Görünümü")
            # Filter entity_combo
            idx = self._grid.entity_combo.findText(entity_name)
            if idx >= 0: self._grid.entity_combo.setCurrentIndex(idx)
            self._filter_grid("teacher", entity_name)
        elif "Sınıflar" in parent_text:
            self._grid.view_combo.setCurrentText("Sınıf Görünümü")
            idx = self._grid.entity_combo.findText(entity_name)
            if idx >= 0: self._grid.entity_combo.setCurrentIndex(idx)
            self._filter_grid("class", entity_name)
        elif "Derslikler" in parent_text:
            self._grid.view_combo.setCurrentText("Derslik Görünümü")
            idx = self._grid.entity_combo.findText(entity_name)
            if idx >= 0: self._grid.entity_combo.setCurrentIndex(idx)
            self._filter_grid("room", entity_name)
            
    def _filter_grid(self, view_type, entity_name):
        self.save_db()
        self.statusBar().showMessage(f"Görünüm güncellendi: {entity_name}")
        self._restore_grid_placements(view_type, entity_name)

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
        p1.add_button("Seçmeli\nDersler","ders",    self._open_electives)
        p1.add_button("Planlama\nİlişkileri","plan",self._open_relations)
        p1.add_divider()
        p1.add_button("Planlama\nÖncesi Kontrol","kontrol",self._act_test_timetable)
        p1.add_button("Otomatik\nPlanlamayı Başlat","otomatik",self._act_auto_schedule)
        p1.add_button("Bulut Tabanlı\nPlanlama","bulut",self._act_cloud_timetable)
        p1.add_button("Planlama Sonrası\nKontrol","kontrol",self._act_verify_timetable)
        p1.add_divider()
        p1.add_button("Temel\nBilgiler",  "bilgi",    self._open_school_info)
        p1.add_button("Evden Kod\nGüncelle", "internet", self._act_check_updates)
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
        p2.add_button("Karşılaştırma", "bilgi", self._act_compare)
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
        p3.add_button("Seçmeli\nDersler","ders",self._open_electives)
        p3.add_button("Planlama\nİlişkileri","plan",self._open_relations)
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
        p5.add_button("Planlama\nÖncesi Kontrol","kontrol",self._act_test_timetable)
        p5.add_button("Otomatik\nPlanlamayı Başlat","otomatik",self._act_auto_schedule)
        p5.add_button("Bulut Tabanlı\nPlanlama","bulut",self._act_cloud_timetable)
        p5.add_divider()
        p5.add_button("İyileştirme\nUygula","param",self._act_nyi)
        p5.add_button("Analiz",     "istatistik",self._act_nyi)
        p5.add_button("Parametreler","param",self._act_nyi)
        p5.add_button("Tanımlanan\nKısıtlamalar","kontrol",self._act_nyi)
        p5.add_divider()
        p5.add_button("Planlama Sonrası\nKontrol","kontrol",self._act_verify_timetable)
        p5.add_button("Danışman",   "yardim",self._act_nyi)
        p5.add_button("İstatistik", "istatistik", self._act_statistics)
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

        # Left panel (Modern Sidebar)
        left = QFrame(splitter)
        left.setMinimumWidth(240)
        left.setMaximumWidth(320)
        left.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border-right: 1px solid #E2E8F0;
            }
        """)
        l_layout = QVBoxLayout(left)
        l_layout.setContentsMargins(12, 16, 12, 16)
        l_layout.setSpacing(12)

        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
            }
        """)
        h_lay = QVBoxLayout(header_card)
        h_lay.setContentsMargins(12, 12, 12, 12)
        h_lay.setSpacing(4)
        
        lbl_title = QLabel("DERS PROGRAMI ÖĞELERİ")
        lbl_title.setStyleSheet("color: #64748B; font-size: 10px; font-weight: 800; letter-spacing: 1px; border: none;")
        
        lbl_sub = QLabel("Kurum Veri Yönetimi")
        lbl_sub.setStyleSheet("color: #0F172A; font-size: 14px; font-weight: 700; border: none;")
        
        h_lay.addWidget(lbl_title)
        h_lay.addWidget(lbl_sub)
        l_layout.addWidget(header_card)

        self._tree = QTreeWidget(left)
        from PySide6.QtWidgets import QStyleFactory, QAbstractItemView
        self._tree.setStyle(QStyleFactory.create("Fusion"))
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(20)
        self._tree.setAnimated(True)
        self._tree.setIconSize(QSize(24, 24))
        self._tree.setSelectionBehavior(QAbstractItemView.SelectItems)
        self._tree.setStyleSheet("""
            QTreeWidget {
                border: none;
                background: transparent;
                font-family: system-ui, -apple-system, sans-serif;
                outline: none;
            }
            QTreeWidget:focus {
                outline: none;
            }
            QTreeWidget::item {
                padding: 10px 12px;
                border-radius: 8px;
                margin-bottom: 4px;
                color: #1E293B;
                font-weight: 600;
                font-size: 15px;
                border: 1px solid transparent;
            }
            QTreeWidget::item:hover {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                color: #0F172A;
            }
            QTreeWidget::item:selected {
                background-color: #F1F5F9;
                border: 1px solid #E2E8F0;
                color: #0284C7;
                font-weight: 700;
            }
            QTreeWidget::branch {
                background-color: transparent;
            }
            QTreeWidget::branch:selected {
                background-color: transparent;
            }
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

        # Wire up grid combos to refresh the view
        self._grid.view_combo.currentTextChanged.connect(self._on_view_combo_changed)
        self._grid.entity_combo.currentTextChanged.connect(self._on_entity_combo_changed)
        
        return splitter
        
    def _on_view_combo_changed(self, text):
        self._grid.entity_combo.blockSignals(True)
        self._grid.entity_combo.clear()
        
        if text == "Sınıf Görünümü":
            items = [c.get("ad", "") for c in self.data_store.get("siniflar", [])]
            self._grid.entity_combo.addItems(items)
        elif text == "Öğretmen Görünümü":
            items = [t.get("ad", "") for t in self.data_store.get("ogretmenler", [])]
            self._grid.entity_combo.addItems(items)
        elif text == "Derslik Görünümü":
            items = [r.get("ad", "") for r in self.data_store.get("derslikler", [])]
            self._grid.entity_combo.addItems(items)
            
        self._grid.entity_combo.blockSignals(False)
        if self._grid.entity_combo.count() > 0:
            self._on_entity_combo_changed(self._grid.entity_combo.currentText())
            
    def _on_entity_combo_changed(self, entity_name):
        view = self._grid.view_combo.currentText()
        if view == "Sınıf Görünümü":
            self._filter_grid("class", entity_name)
        elif view == "Öğretmen Görünümü":
            self._filter_grid("teacher", entity_name)
        elif view == "Derslik Görünümü":
            self._filter_grid("room", entity_name)

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
                    
                # Migrate old dict placements to list
                if isinstance(self.data_store.get("grid_placements"), dict):
                    self.data_store["grid_placements"] = []
                elif "grid_placements" not in self.data_store:
                    self.data_store["grid_placements"] = []
                    
                self.statusBar().showMessage(f"Veriler yüklendi: {load_path}")
                
                # Restore grid placements
                self._restore_grid_placements()
            except Exception as e:
                print("DB Load Error:", e)
    
    def _restore_grid_placements(self, view_type=None, entity_name=None):
        if not hasattr(self, "_grid"):
            return
        grid_data = self.data_store.get("grid_placements", [])
        self._grid.clear_grid()
        for info in grid_data:
            # Filter logic
            if view_type == "teacher" and entity_name and info.get("teacher_name") != entity_name:
                continue
            if view_type == "class" and entity_name and info.get("class_name") != entity_name:
                continue
            if view_type == "room" and entity_name: # Room support later
                continue
                
            self._grid.set_cell(
                info.get("period", 0), 
                info.get("day", 0),
                info.get("subject_name", "Ders"),
                info.get("color", "#1E88E5"),
                info.get("teacher_name", ""),
                info.get("duration", 1),
                class_name=info.get("class_name", "")
            )

    def save_db(self, path=None):
        import json
        save_path = path or self.db_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Sync current grid view to global list
        if hasattr(self, "_grid") and hasattr(self._grid, "view_combo") and hasattr(self._grid, "entity_combo"):
            view_type = None
            entity_name = self._grid.entity_combo.currentText()
            if self._grid.view_combo.currentText() == "Sınıf Görünümü":
                view_type = "class"
            elif self._grid.view_combo.currentText() == "Öğretmen Görünümü":
                view_type = "teacher"
                
            if view_type and entity_name:
                global_placements = self.data_store.setdefault("grid_placements", [])
                new_global = []
                # 1. Retain everything except the current entity's lessons
                for p in global_placements:
                    if view_type == "class" and p.get("class_name") == entity_name:
                        continue
                    if view_type == "teacher" and p.get("teacher_name") == entity_name:
                        continue
                    new_global.append(p)
                    
                # 2. Add back the current entity's lessons from the grid
                for (r, c), info in self._grid.get_placed_lessons().items():
                    p = dict(info)
                    p["period"] = r
                    p["day"] = c
                    if view_type == "class":
                        p["class_name"] = entity_name
                    elif view_type == "teacher":
                        p["teacher_name"] = entity_name
                    new_global.append(p)
                    
                self.data_store["grid_placements"] = new_global
            
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self.data_store, f, ensure_ascii=False, indent=4)
            self.statusBar().showMessage(f"Veritabanı başarıyla kaydedildi: {save_path}")
            
            # Bulut senkronizasyonu (Çoklu kurum desteği ile UID altına)
            if hasattr(self, "cloud_worker") and self.cloud_worker and hasattr(self, "auth_data") and self.auth_data:
                uid = self.auth_data.get("uid")
                if uid:
                    self.cloud_worker.add_to_queue("institutions", uid, self.data_store)
                
        except Exception as e:
            self.statusBar().showMessage(f"Kaydetme hatası: {e}")

    def _refresh_tree(self):
        self._tree.clear()
        
        # Calculate teacher workloads
        workloads = {}
        for a in self.data_store.get("atamalar", []):
            t = format_tr_name(a.get("teacher", ""))
            dur = a.get("duration", 1)
            if t: workloads[t] = workloads.get(t, 0) + dur
            
        # 0. Sanitize & Capitalize
        for t in self.data_store.get("ogretmenler", []):
            if t.get("ad"):
                t["ad"] = format_tr_name(t["ad"])
                if not t.get("kisa"): t["kisa"] = t["ad"][:4].upper()

        for d in self.data_store.get("dersler", []):
            if d.get("ad"): d["color"] = get_subject_color(d["ad"])

        s_list = self.data_store.get("siniflar", [])
        t_list = self.data_store.get("ogretmenler", [])
        d_list = self.data_store.get("dersler", [])
        r_list = self.data_store.get("derslikler", [])
        
        from dialogs.school_info import draw_placeholder_icon
        from PySide6.QtGui import QIcon
        
        icon_s = QIcon(draw_placeholder_icon("grid"))
        icon_t = QIcon(draw_placeholder_icon("list"))
        icon_d = QIcon(draw_placeholder_icon("list"))
        icon_r = QIcon(draw_placeholder_icon("bank"))
        
        root_s = QTreeWidgetItem(self._tree, [f" Sınıflar ({len(s_list)})"])
        root_s.setIcon(0, icon_s)
        for c in s_list:
            item = QTreeWidgetItem(root_s, [f" {c.get('ad', '')}"])
            item.setData(0, Qt.UserRole, c.get("ad", ""))
            
        root_t = QTreeWidgetItem(self._tree, [f" Öğretmenler ({len(t_list)})"])
        root_t.setIcon(0, icon_t)
        for t in t_list:
            t_name = t.get("ad", "")
            w_load = workloads.get(t_name, 0)
            item = QTreeWidgetItem(root_t, [f" {t_name} ({w_load} Saat)"])
            item.setData(0, Qt.UserRole, t_name)
            
        root_d = QTreeWidgetItem(self._tree, [f" Dersler ({len(d_list)})"])
        root_d.setIcon(0, icon_d)
        for d in d_list:
            item = QTreeWidgetItem(root_d, [f" {d.get('ad', '')}"])
            item.setData(0, Qt.UserRole, d.get("ad", ""))
            
        root_r = QTreeWidgetItem(self._tree, [f" Derslikler ({len(r_list)})"])
        root_r.setIcon(0, icon_r)
        for r in r_list:
            item = QTreeWidgetItem(root_r, [f" {r.get('ad', '')}"])
            item.setData(0, Qt.UserRole, r.get("ad", ""))
        
        self._tree.expandAll()
        
        unplaced = []
        grid_placements = self.data_store.get("grid_placements", [])
        for info in grid_placements:
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
        
        unplaced = []
        
        # 1. Calculate already placed durations
        placed_counts = {}
        for info in self.data_store.get("grid_placements", []):
            key = (info.get("class_name", ""), info.get("subject_name", ""), info.get("teacher_name", ""))
            placed_counts[key] = placed_counts.get(key, 0) + info.get("duration", 1)

        # 2. Add explicitly assigned lessons from self.data_store["atamalar"]
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
            dur = atama.get("duration", 1) # FIXED: Default is 1, not 2
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
                
            key = (cls_name, subj_name, teacher_name)
            
            for p_idx, block_dur in enumerate(parts):
                # Filter out placed durations!
                if placed_counts.get(key, 0) >= block_dur:
                    placed_counts[key] -= block_dur
                    continue
                elif placed_counts.get(key, 0) > 0:
                    # Partially placed (e.g. 1 hour placed out of 2)
                    remain = block_dur - placed_counts[key]
                    placed_counts[key] = 0
                    block_dur = remain
                    
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
        
        is_move = lesson_info.get("is_move", False)
        orig_r = lesson_info.get("origin_row", -1)
        orig_c = lesson_info.get("origin_col", -1)
        
        from timetable_grid import DAYS
        day_name = DAYS[col] if 0 <= col < len(DAYS) else f"{col+1}. Gün"
        
        # Check if moving to exact same spot
        if is_move and orig_r == row and orig_c == col:
            return
            
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
                # If we are moving, don't conflict with our own old position if they somehow overlap
                if is_move and r == orig_r and c == orig_c:
                    continue
                    
                # Conflict logic
                # A placed lesson spans from r to r + data["duration"]
                placed_dur = data.get("duration", 1)
                
                # Check overlap in columns and rows
                if c == col:
                    overlap = (row < r + placed_dur) and (r < row + duration)
                    if overlap and data.get("teacher") == teacher and teacher != "":
                        QMessageBox.warning(
                            self, "Çakışma Engeli",
                            f"⚠️ '{teacher}' öğretmeni {day_name} günü {row+1}. ders saatinde zaten başka bir derste görevlidir!\n(Farklı bir sınıfta eş zamanlı ders vermek için öğretmen düzenleme ekranından 'Çoklu Ders İzni' seçeneğini açabilirsiniz)."
                        )
                        return

        # Check if Target is Occupied
        target_info = None
        target_r, target_c = -1, -1
        
        # Sadece move işlemiyse takas yapabiliriz
        if is_move and orig_r >= 0 and orig_c >= 0:
            for (r, c), data in placed.items():
                placed_dur = data.get("duration", 1)
                if c == col and r <= row < r + placed_dur:
                    # Kendi kendimizle çakışmıyorsak hedefi bulduk
                    if r != orig_r or c != orig_c:
                        target_info = data
                        target_r, target_c = r, c
                    break

        # Passed checks! If it's a move, delete original first
        if is_move and orig_r >= 0 and orig_c >= 0:
            self._grid.table.setSpan(orig_r, orig_c, 1, 1)
            for r_off in range(duration):
                tr = orig_r + r_off
                if tr < self._grid.table.rowCount():
                    self._grid.table.setItem(tr, orig_c, None)
            self._grid._placed_lessons.pop((orig_r, orig_c), None)
            
            if target_info:
                # Delete target
                target_dur = target_info.get("duration", 1)
                self._grid.table.setSpan(target_r, target_c, 1, 1)
                for r_off in range(target_dur):
                    tr = target_r + r_off
                    if tr < self._grid.table.rowCount():
                        self._grid.table.setItem(tr, target_c, None)
                self._grid._placed_lessons.pop((target_r, target_c), None)
                
                # Re-place target at origin (Swap)
                self._grid.set_cell(
                    orig_r, orig_c, 
                    target_info.get("subject_name", ""), 
                    get_subject_color(target_info.get("subject_name", "")), 
                    target_info.get("teacher", ""), 
                    target_dur, 
                    class_name=target_info.get("class_name", "")
                )
                self.statusBar().showMessage(f"Takas (Swap) Başarılı: '{subject_name}' <-> '{target_info.get('subject_name', '')}'")
            else:
                self.statusBar().showMessage(f"'{subject_name}' dersi {day_name} günü {row+1}. ders saatine taşındı.")

        self._grid.set_cell(row, col, subject_name, color, teacher, duration, class_name=cls_name)
        if not (is_move and orig_r >= 0 and orig_c >= 0 and target_info):
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
        from dialogs.startup_wizard import StartupWizard
        wizard = StartupWizard(self)
        if wizard.exec():
            self.load_db()
            self._refresh_tree()
            self._grid.clear_grid()
            self.statusBar().showMessage("Yeni proje sihirbazı tamamlandı.")

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
        from PySide6.QtWidgets import QDialog
        from dialogs.print_wizard import PrintWizardDialog
        wiz = PrintWizardDialog(self.data_store, self)
        if wiz.exec() == QDialog.Accepted:
            filters = wiz.get_selected_filters()
            from dialogs.print_preview import TimetablePrintPreview
            dlg = TimetablePrintPreview(self.data_store, self._grid.get_placed_lessons(), filters, self)
            dlg.exec()

    def _act_preview(self):
        self._act_print()

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

    def _open_school_info(self):
        from dialogs.school_info import SchoolInfoDialog
        d = SchoolInfoDialog(parent=self, data_store=self.data_store)
        if d.exec() == QDialog.Accepted:
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

    def _open_electives(self):
        from dialogs.electives_dialog import ElectivesDialog
        d = ElectivesDialog(data_store=self.data_store, parent=self)
        d.exec()
        self.save_db()

    def _open_relations(self):
        from dialogs.relations_dialog import PlanningRelationsDialog
        d = PlanningRelationsDialog(data_store=self.data_store, parent=self)
        d.exec()
        self.save_db()

    def _open_wizard(self):
        d = MasterDataDialog(0, self)
        d.exec()
        self.save_db()
        self._refresh_tree()

    def _act_auto_schedule(self):
        from dialogs.auto_schedule_dialog import AutoScheduleDialog
        d = AutoScheduleDialog(self.data_store, self)
        if d.exec() == QDialog.Accepted:
            # AI produced a schedule
            results = self.data_store.get("auto_schedule_results", [])
            if results:
                # Temizle
                self._grid.clear_grid()
                
                # Tüm okulu tek seferde göstermek için Bütün Okul Görünümüne geç
                classes = [c.get("ad") for c in self.data_store.get("siniflar", [])]
                settings = self.data_store.get("settings", {})
                periods = int(settings.get("periods", 8))
                days = settings.get("days", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
                
                self._grid.set_mode_all_classes(classes, periods, days)
                
                for r in results:
                    c_name = r["class_name"]
                    t_name = r["teacher_name"]
                    subj = r["subject_name"]
                    d_idx = r["day_idx"]
                    p_idx = r["period"]
                    
                    if c_name in classes:
                        row = classes.index(c_name)
                        col = d_idx * periods + p_idx
                        
                        from PySide6.QtWidgets import QTableWidgetItem
                        from PySide6.QtGui import QBrush, QColor
                        item = QTableWidgetItem(f"{subj}\\n{t_name}")
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setBackground(QBrush(QColor("#E8F4F8")))
                        self._grid.table.setItem(row, col, item)
                        
                        # İç yapıya kaydet
                        self._grid._placed_lessons[(row, col)] = {
                            "class_name": c_name,
                            "teacher_name": t_name,
                            "subject_name": subj,
                            "day_idx": d_idx,
                            "period": p_idx
                        }
                self.statusBar().showMessage("Yapay Zeka yerleşimi tamamlandı.")

    def _act_statistics(self):
        from dialogs.statistics_dialog import StatisticsDialog
        d = StatisticsDialog(self.data_store, self)
        d.exec()
        
    def _act_compare(self):
        from dialogs.compare_dialog import CompareDialog
        d = CompareDialog(self.data_store, self)
        d.exec()
        
    def _act_test_timetable(self):
        from dialogs.test_timetable_dialog import TestTimetableDialog
        d = TestTimetableDialog(self.data_store, self)
        d.exec()

    def _act_verify_timetable(self):
        from dialogs.verify_timetable_dialog import VerifyTimetableDialog
        d = VerifyTimetableDialog(self.data_store, self)
        d.exec()

    def _act_cloud_timetable(self):
        QMessageBox.information(self, "Bulut Tabanlı Planlama", "Bulut tabanlı planlama modülünü kullanabilmek için aktif bir Dijisa hesabı gereklidir.")

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
        msg = QMessageBox(self)
        msg.setWindowTitle("Bulut Tabanlı Planlama")
        msg.setIcon(QMessageBox.Information)
        msg.exec()
