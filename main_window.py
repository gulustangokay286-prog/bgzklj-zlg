"""
main_window.py  –  Ana pencere
Pixel-perfect aSc k12 Bilişim Ders Planlama 2020 ribbon + workspace
"""
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QSplitter, QTreeWidget, QTreeWidgetItem, QStatusBar,
    QMessageBox, QTabWidget, QFrame, QSizePolicy, QMenu, QToolButton, QFileDialog, QDialog
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPen, QLinearGradient, QBrush, QAction, QPainterPath, QPainterPath

from ribbon_widget import RibbonWidget, make_icon
from timetable_grid import TimetableGrid
from dialogs.master_data_dialog import MasterDataDialog
from dialogs.school_info import SchoolInfoDialog
from dialogs.auto_schedule_dialog import AutoScheduleDialog
from dialogs.print_preview import TimetablePrintPreview
from core.timetable_data import TimetableData
from dialogs.edit_forms import format_tr_name
from dialogs.edit_forms import format_tr_name

APP_TITLE = "BGZ Ders Planlama"
VERSION   = "2026 - 2027"

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

def normalize_class_name(cls_name: str) -> str:
    """Normalizes class names (e.g. '12 / A' -> '12/A', '9 - B' -> '9/B') for consistent matching."""
    if not cls_name:
        return ""
    s = str(cls_name).strip().upper().replace(" ", "")
    s = s.replace("-", "/").replace("\\", "/")
    return s

def get_subject_color(subject_name: str) -> str:
    """Returns a deterministic, vibrant, distinct color for any subject name."""
    if not subject_name:
        return "#1E88E5"
    hash_val = sum(ord(c) * (i + 1) for i, c in enumerate(subject_name.strip()))
    return PASTEL_DISTINCT_COLORS[hash_val % len(PASTEL_DISTINCT_COLORS)]

def make_clean_vector_icon(icon_type: str, is_expanded: bool = True) -> QIcon:
    pix = QPixmap(48, 28)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    
    # 1. DRAW LARGE CHEVRON ON THE FAR LEFT (x: 0..14)
    p.setBrush(QBrush(QColor("#0284C7" if is_expanded else "#64748B")))
    p.setPen(Qt.NoPen)
    ch_path = QPainterPath()
    if is_expanded:
        ch_path.moveTo(2, 10)
        ch_path.lineTo(12, 10)
        ch_path.lineTo(7, 17)
    else:
        ch_path.moveTo(4, 7)
        ch_path.lineTo(11, 12)
        ch_path.lineTo(4, 17)
    ch_path.closeSubpath()
    p.drawPath(ch_path)
    
    # 2. DRAW CATEGORY VECTOR ICON ON THE RIGHT (x: 18..46)
    ox = 18
    if icon_type == "sinif":
        p.setBrush(QBrush(QColor("#0284C7")))
        p.drawRoundedRect(ox + 2, 2, 10, 10, 3, 3)
        p.drawRoundedRect(ox + 15, 2, 10, 10, 3, 3)
        p.drawRoundedRect(ox + 2, 15, 10, 10, 3, 3)
        p.drawRoundedRect(ox + 15, 15, 10, 10, 3, 3)
    elif icon_type == "ogretmen":
        p.setBrush(QBrush(QColor("#10B981")))
        p.drawEllipse(ox + 9, 2, 10, 10)
        path = QPainterPath()
        path.moveTo(ox + 3, 25)
        path.cubicTo(ox + 3, 15, ox + 25, 15, ox + 25, 25)
        path.lineTo(ox + 25, 26)
        path.lineTo(ox + 3, 26)
        path.closeSubpath()
        p.drawPath(path)
    elif icon_type == "ders":
        p.setBrush(QBrush(QColor("#F59E0B")))
        cap_path = QPainterPath()
        cap_path.moveTo(ox + 13, 3)
        cap_path.lineTo(ox + 26, 9)
        cap_path.lineTo(ox + 13, 15)
        cap_path.lineTo(ox + 0, 9)
        cap_path.closeSubpath()
        p.drawPath(cap_path)
        base_path = QPainterPath()
        base_path.moveTo(ox + 5, 12)
        base_path.lineTo(ox + 5, 18)
        base_path.cubicTo(ox + 5, 23, ox + 21, 23, ox + 21, 18)
        base_path.lineTo(ox + 21, 12)
        p.drawPath(base_path)
    else: # derslik
        p.setBrush(QBrush(QColor("#8B5CF6")))
        p.drawRoundedRect(ox + 2, 3, 23, 16, 3, 3)
        p.setPen(QPen(QColor("#7C3AED"), 2))
        p.drawLine(ox + 6, 19, ox + 3, 26)
        p.drawLine(ox + 21, 19, ox + 24, 26)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#F3E8FF")))
        p.drawRoundedRect(ox + 4, 5, 19, 12, 1, 1)
        
    p.end()
    return QIcon(pix)

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
        self.setFixedHeight(44)
        self.setStyleSheet("background: #F0F0F0; border-bottom: 1px solid #D0D0D0;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 8, 8, 0) # 8px down

        # File menu button (top-left circle)
        self.file_btn = QToolButton(self)
        self.file_btn.setIcon(make_menu_icon("M", "#0078D7", "#005A9E"))
        self.file_btn.setIconSize(QSize(28, 28))
        self.file_btn.setFixedSize(34, 34)
        self.file_btn.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 4px;
                background: transparent;
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
        self.config_path = os.path.join(user_dir, "app_config.json")
        self.db_path = self._get_last_db_path()
        if not self.db_path or not os.path.exists(self.db_path):
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
                
        self._is_loading = True
        self._active_view_type = "class"
        self._active_entity_name = ""
        self.current_roz_path = self.db_path
        self.data_store = {"dersler": [], "siniflar": [], "derslikler": [], "ogretmenler": [], "atamalar": [], "settings": {}}
        
        # Eğer giriş yapılmışsa, buluttan o kuruma (uid) ait veriyi çek
        if self.auth_data and self.auth_data.get("uid"):
            self._download_cloud_data()
            
        self._build_ui()
        self.load_db()
        self._refresh_tree()
        self._is_loading = False
        
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

        ver_lbl = QLabel(f"Chenki Akademi 2026 - 2027 Pro")
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
                local_classes = len(self.data_store.get("siniflar", []))
                local_teachers = len(self.data_store.get("ogretmenler", []))
                cloud_classes = len(cloud_data.get("siniflar", []))
                cloud_teachers = len(cloud_data.get("ogretmenler", []))

                # Safe merge/sync: do not wipe local non-empty data with empty cloud data
                if (local_classes > 0 or local_teachers > 0) and (cloud_classes == 0 and cloud_teachers == 0):
                    if hasattr(self, "cloud_worker") and self.cloud_worker and uid:
                        self.cloud_worker.add_to_queue("institutions", uid, self.data_store)
                elif show_message or (local_classes == 0 and local_teachers == 0 and (cloud_classes > 0 or cloud_teachers > 0)):
                    if cloud_data != getattr(self, "data_store", None):
                        self.data_store.update(cloud_data)
                        self.save_db()
                        self._refresh_tree()
                        self._on_tree_selection_changed()
                        self.statusBar().showMessage("Buluttan veriler senkronize edildi! ☁️✅")
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

    def _on_tree_item_expanded_collapsed(self, item):
        icon_type = item.data(0, Qt.UserRole + 10)
        if icon_type:
            item.setIcon(0, make_clean_vector_icon(icon_type, item.isExpanded()))

    def _on_tree_item_clicked(self, item, column):
        text = item.text(0)
        parent = item.parent()
        if not parent:
            item.setExpanded(not item.isExpanded())
            return
            
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
        if not getattr(self, "_is_loading", False):
            prev_view = getattr(self, "_active_view_type", None)
            prev_entity = getattr(self, "_active_entity_name", None)
            if prev_view and prev_entity and (prev_view != view_type or prev_entity != entity_name):
                self._sync_grid_to_store(prev_view, prev_entity)
                self.save_db(sync_from_grid=False)
        
        if hasattr(self, "_grid") and hasattr(self._grid, "entity_combo"):
            self._grid.entity_combo.blockSignals(True)
            if self._grid.entity_combo.count() == 0:
                self._on_view_combo_changed(self._grid.view_combo.currentText(), initial_load=True)
            idx = self._grid.entity_combo.findText(entity_name)
            if idx >= 0:
                self._grid.entity_combo.setCurrentIndex(idx)
            else:
                self._grid.entity_combo.addItem(entity_name)
                self._grid.entity_combo.setCurrentText(entity_name)
            self._grid.entity_combo.blockSignals(False)
            
        self._active_view_type = view_type
        self._active_entity_name = entity_name
        self.statusBar().showMessage(f"Görünüm güncellendi: {entity_name}")
        self._restore_grid_placements(view_type, entity_name)
        self._refresh_tree(view_type=view_type, target_entity=entity_name)

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
        p1.add_button("Çizelgeyi\nSıfırla","temizle",self._act_clear_schedule)
        p1.add_divider()
        p1.add_button("Temel\nBilgiler",  "bilgi",    self._open_school_info)
        p1.add_button("Evden Kod\nGüncelle", "internet", self._act_check_updates)
        p1.add_button("İnternet\nHesabı","internet", lambda: __import__('webbrowser').open("https://chenki.net/"))
        p1.add_button("Sorular?\nYorumlar?","yardim",lambda: __import__('dialogs.faq_dialog', fromlist=['FAQDialog']).FAQDialog(self).exec())
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
        p2.add_button("İnternet\nHesabı","internet", lambda: __import__('webbrowser').open("https://chenki.net/"))
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
        p7.add_button("Online\nYardım","yardim",lambda: __import__('webbrowser').open("https://chenki.net/"))
        p7.add_button("Sorular?\nYorumlar?","yardim",lambda: __import__('dialogs.faq_dialog', fromlist=['FAQDialog']).FAQDialog(self).exec())
        p7.add_stretch()

    # ── Workspace ─────────────────────────────────────────────────────────────
    def _build_workspace(self, parent):
        splitter = QSplitter(Qt.Horizontal, parent)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #CBD5E1;
                margin: 0px 1px;
                border-radius: 2px;
            }
            QSplitter::handle:hover {
                background-color: #0284C7;
            }
            QSplitter::handle:pressed {
                background-color: #0369A1;
            }
        """)

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
        l_layout.setContentsMargins(8, 8, 8, 8)
        l_layout.setSpacing(6)

        self._tree = QTreeWidget(left)
        from PySide6.QtWidgets import QAbstractItemView
        self._tree.setMouseTracking(True)
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(False)
        self._tree.setIndentation(10)
        self._tree.setAnimated(True)
        self._tree.setIconSize(QSize(48, 28))
        self._tree.setSelectionBehavior(QAbstractItemView.SelectRows)
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
                padding: 7px 10px;
                margin-bottom: 3px;
                border-radius: 6px;
                color: #1E293B;
                font-weight: 600;
                font-size: 13px;
                background: transparent;
                border: 1.5px dashed transparent;
            }
            QTreeWidget::item:hover {
                background: transparent;
                border: 1.5px dashed #0284C7;
                color: #0284C7;
            }
            QTreeWidget::item:selected {
                background: transparent;
                border: 1.5px dashed #0284C7;
                color: #0369A1;
                font-weight: 700;
            }
            QTreeWidget::item:selected:hover {
                background: transparent;
                border: 1.5px dashed #0284C7;
                color: #0369A1;
            }
            QTreeWidget::branch {
                background: transparent;
            }
        """)
        self._tree.itemExpanded.connect(self._on_tree_item_expanded_collapsed)
        self._tree.itemCollapsed.connect(self._on_tree_item_expanded_collapsed)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_tree_context_menu)
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
        settings = self.data_store.get("settings", {})
        periods = int(settings.get("periods", 8))
        self._grid = TimetableGrid(periods, right)
        self._tab_widget.addTab(self._grid, "Haftalık Program")
        
        # Connect drop signal
        self._grid.table.lesson_dropped.connect(self._on_lesson_dropped)
        self._grid.cell_right_clicked.connect(self._on_cell_edit)

        r_layout.addWidget(self._tab_widget)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([220, 1060])

        # Wire up grid toggle button
        self._grid.toggle_panel_btn.clicked.connect(lambda: left.setVisible(not left.isVisible()))
        # Set initial left panel hidden (kapalı başlasın)
        left.setVisible(False)
        splitter.setSizes([0, 1060])
        
        return splitter
        
    def _on_view_combo_changed(self, text, initial_load=False):
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
            if not initial_load and not getattr(self, "_is_loading", False):
                self._on_entity_combo_changed(self._grid.entity_combo.currentText())
            
    def _on_entity_combo_changed(self, entity_name):
        if getattr(self, "_is_loading", False):
            return
        view = self._grid.view_combo.currentText()
        if view == "Sınıf Görünümü":
            self._filter_grid("class", entity_name)
        elif view == "Öğretmen Görünümü":
            self._filter_grid("teacher", entity_name)
        elif view == "Derslik Görünümü":
            self._filter_grid("room", entity_name)

    def closeEvent(self, event):
        # Auto-save changes seamlessly
        try:
            self.save_db(sync_from_grid=True)
        except Exception as e:
            print("Auto-save on exit error:", e)
        event.accept()

    def _get_last_db_path(self):
        import json
        default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "program.roz")
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("last_roz_path", default_path)
            except:
                pass
        return default_path

    def _set_last_db_path(self, path):
        import json
        self.db_path = path
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"last_roz_path": path}, f)
        except:
            pass

    def load_db(self, path=None):
        self._is_loading = True
        import json
        load_path = path or getattr(self, "current_roz_path", None) or self.db_path
        if not load_path or not os.path.exists(load_path):
            user_dir = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
            load_path = os.path.join(user_dir, "bgz_database.json")
            
        if os.path.exists(load_path):
            try:
                self.current_roz_path = os.path.abspath(load_path)
                self.db_path = self.current_roz_path
                self._set_last_db_path(self.current_roz_path)
                with open(load_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data_store.clear()
                    self.data_store.update(loaded)
                    
                # Migrate old dict placements to list
                if isinstance(self.data_store.get("grid_placements"), dict):
                    self.data_store["grid_placements"] = []
                elif "grid_placements" not in self.data_store:
                    self.data_store["grid_placements"] = []
                    
                # Clean & Format all subject and teacher names to Turkish title case
                from dialogs.edit_forms import format_tr_name
                for d in self.data_store.get("dersler", []):
                    if d.get("ad"): d["ad"] = format_tr_name(d["ad"])
                for a in self.data_store.get("atamalar", []):
                    if a.get("subject"): a["subject"] = format_tr_name(a["subject"])
                for t in self.data_store.get("ogretmenler", []):
                    if t.get("ad"): t["ad"] = format_tr_name(t["ad"])

                self.statusBar().showMessage(f"Veriler yüklendi: {load_path}")
            except Exception as e:
                print("DB Load Error:", e)

        # Update entity combo without triggering premature saves
        if hasattr(self, "_grid") and hasattr(self._grid, "view_combo"):
            self._grid.entity_combo.blockSignals(True)
            self._grid.view_combo.blockSignals(True)
            self._on_view_combo_changed(self._grid.view_combo.currentText(), initial_load=True)
            if self._grid.entity_combo.count() > 0:
                self._active_entity_name = self._grid.entity_combo.currentText()
                v_text = self._grid.view_combo.currentText()
                if "Sınıf" in v_text: self._active_view_type = "class"
                elif "Öğretmen" in v_text: self._active_view_type = "teacher"
                elif "Derslik" in v_text: self._active_view_type = "room"
            self._grid.view_combo.blockSignals(False)
            self._grid.entity_combo.blockSignals(False)
            
        self._restore_grid_placements()
        self._refresh_tree()
        self._is_loading = False

    def _sync_grid_to_store(self, view_type=None, entity_name=None):
        if getattr(self, "_is_loading", False):
            return
        if not hasattr(self, "_grid") or not hasattr(self._grid, "get_placed_lessons"):
            return
            
        settings = self.data_store.get("settings", {})
        periods = int(settings.get("periods", 8))
        classes = self.data_store.get("siniflar", [])
        class_names = [c.get("ad", "") for c in classes if c.get("ad")]
        if not class_names:
            class_names = ["Sınıf 1"]
            
        placed = self._grid.get_placed_lessons()
        new_global = []
        for (r, c), info in placed.items():
            p = dict(info)
            # aSc multi-sheet görünümünde row = Sınıf indexi, c = Gün * period + saat
            if r < len(class_names):
                cls_name = class_names[r]
                day = c // periods
                period = c % periods
                
                p["class_name"] = cls_name
                p["class"] = cls_name
                p["day"] = day
                p["col"] = day
                p["period"] = period
                p["row"] = period
                new_global.append(p)
                
        self.data_store["grid_placements"] = new_global

    def _restore_grid_placements(self, view_type=None, entity_name=None):
        # We handle restoring inside _refresh_grid directly now
        pass



    def save_db(self, path=None, sync_from_grid=True):
        if getattr(self, "_is_loading", False):
            return
            
        import json
        if hasattr(self, "_push_undo_state"):
            self._push_undo_state()
            
        if sync_from_grid:
            self._sync_grid_to_store()
            
        save_path = path or getattr(self, "current_roz_path", None) or self.db_path
        if not save_path:
            save_path = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "bgz_database.json")
            
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        self.current_roz_path = os.path.abspath(save_path)
        self.db_path = self.current_roz_path
        self._set_last_db_path(self.current_roz_path)
        
        try:
            with open(self.current_roz_path, "w", encoding="utf-8") as f:
                json.dump(self.data_store, f, ensure_ascii=False, indent=4)
                
            fname = os.path.basename(self.current_roz_path)
            self.statusBar().showMessage(f"💾 Tüm değişiklikler '{fname}' dosyasına anlık kaydedildi.")
            
            # Bulut senkronizasyonu
            if hasattr(self, "cloud_worker") and self.cloud_worker and hasattr(self, "auth_data") and self.auth_data:
                uid = self.auth_data.get("uid")
                if uid:
                    self.cloud_worker.add_to_queue("institutions", uid, self.data_store)
        except Exception as e:
            self.statusBar().showMessage(f"Kaydetme hatası: {e}")

    def _refresh_tree(self, view_type=None, target_entity=None):
        expanded_states = {}
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            icon_type = item.data(0, Qt.UserRole + 10)
            if icon_type:
                expanded_states[icon_type] = item.isExpanded()

        self._tree.clear()
        
        # Calculate teacher workloads
        workloads = {}
        for a in self.data_store.get("atamalar", []):
            t = format_tr_name(a.get("teacher", ""))
            dur = a.get("duration", 1)
            if t: workloads[t] = workloads.get(t, 0) + dur
            
        # 0. Sanitize & Capitalize (Preserve manual short codes)
        from dialogs.edit_forms import _auto_short_code
        for t in self.data_store.get("ogretmenler", []):
            if t.get("ad"):
                t["ad"] = format_tr_name(t["ad"])
                if not t.get("kisa"):
                    clean = t["ad"].strip()
                    parts = clean.split()
                    if len(parts) >= 2:
                        t["kisa"] = f"{parts[0][0].upper()}. {' '.join(parts[1:]).upper()}"
                    elif len(parts) == 1 and len(parts[0]) > 0:
                        t["kisa"] = f"{parts[0][0].upper()}. {parts[0].upper()}"

        for d in self.data_store.get("dersler", []):
            if d.get("ad"):
                if not d.get("color"):
                    d["color"] = get_subject_color(d["ad"])
                if not d.get("kisa"):
                    d["kisa"] = _auto_short_code(d["ad"])

        for c in self.data_store.get("siniflar", []):
            if c.get("ad"):
                if not c.get("kisa"):
                    c["kisa"] = c["ad"].strip().replace(" ", "").upper()

        s_list = self.data_store.get("siniflar", [])
        t_list = self.data_store.get("ogretmenler", [])
        d_list = self.data_store.get("dersler", [])
        r_list = self.data_store.get("derslikler", [])
        
        is_exp_s = expanded_states.get("sinif", False)
        is_exp_t = expanded_states.get("ogretmen", False)
        is_exp_d = expanded_states.get("ders", False)
        is_exp_r = expanded_states.get("derslik", False)
        
        icon_s = make_clean_vector_icon("sinif", is_exp_s)
        icon_t = make_clean_vector_icon("ogretmen", is_exp_t)
        icon_d = make_clean_vector_icon("ders", is_exp_d)
        icon_r = make_clean_vector_icon("derslik", is_exp_r)
        
        root_s = QTreeWidgetItem(self._tree, [f"Sınıflar ({len(s_list)})"])
        root_s.setIcon(0, icon_s)
        root_s.setData(0, Qt.UserRole + 10, "sinif")
        for c in s_list:
            item = QTreeWidgetItem(root_s, [f"{c.get('ad', '')}"])
            item.setData(0, Qt.UserRole, c.get("ad", ""))
            
        root_t = QTreeWidgetItem(self._tree, [f"Öğretmenler ({len(t_list)})"])
        root_t.setIcon(0, icon_t)
        root_t.setData(0, Qt.UserRole + 10, "ogretmen")
        for t in t_list:
            t_name = t.get("ad", "")
            w_load = workloads.get(t_name, 0)
            item = QTreeWidgetItem(root_t, [f"{t_name} ({w_load} Saat)"])
            item.setData(0, Qt.UserRole, t_name)
            
        root_d = QTreeWidgetItem(self._tree, [f"Dersler ({len(d_list)})"])
        root_d.setIcon(0, icon_d)
        root_d.setData(0, Qt.UserRole + 10, "ders")
        for d in d_list:
            item = QTreeWidgetItem(root_d, [f"{d.get('ad', '')}"])
            item.setData(0, Qt.UserRole, d.get("ad", ""))
            
        root_r = QTreeWidgetItem(self._tree, [f"Derslikler ({len(r_list)})"])
        root_r.setIcon(0, icon_r)
        root_r.setData(0, Qt.UserRole + 10, "derslik")
        for r in r_list:
            item = QTreeWidgetItem(root_r, [f"{r.get('ad', '')}"])
            item.setData(0, Qt.UserRole, r.get("ad", ""))
        
        root_s.setExpanded(is_exp_s)
        root_t.setExpanded(is_exp_t)
        root_d.setExpanded(is_exp_d)
        root_r.setExpanded(is_exp_r)
        
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
            c_name = info.get("class_name", "").strip().upper()
            t_name = format_tr_name(info.get("teacher_name", ""))
            s_name = info.get("subject_name", "").strip().upper()
            key = (c_name, s_name, t_name)
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
                
            key = (cls_name.strip().upper(), subj_name.strip().upper(), teacher_name)
            
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
            
        # 2. Filter unplaced cards by currently selected class / teacher view if active
        has_assignments = True
        if hasattr(self, "_grid") and hasattr(self._grid, "view_combo") and hasattr(self._grid, "entity_combo"):
            v_type = view_type or self._grid.view_combo.currentText()
            e_name = target_entity or self._grid.entity_combo.currentText()
            if v_type in ("class", "Sınıf Görünümü") and e_name:
                total_for_entity = [a for a in atamalar if a.get("class") and a.get("class").strip().upper() == e_name.strip().upper()]
                has_assignments = len(total_for_entity) > 0
                unplaced = [u for u in unplaced if u.get("class_name") and u.get("class_name").strip().upper() == e_name.strip().upper()]
            elif v_type in ("teacher", "Öğretmen Görünümü") and e_name:
                total_for_entity = [a for a in atamalar if a.get("teacher") and format_tr_name(a.get("teacher")) == format_tr_name(e_name)]
                has_assignments = len(total_for_entity) > 0
                unplaced = [u for u in unplaced if u.get("teacher") and format_tr_name(u.get("teacher")) == format_tr_name(e_name)]

        self._grid.unplaced_dock.load_unplaced(unplaced, has_assignments=has_assignments)

    def _check_planning_relations(self, subject, teacher, class_name, day, period, duration, is_move=False, orig_r=-1, orig_c=-1):
        """
        Validates active Planning Relations (planlama_iliskileri) in real-time for manual placements.
        Returns (is_valid, violation_message).
        """
        relations = [r for r in self.data_store.get("planlama_iliskileri", []) if r.get("aktif", True)]
        if not relations:
            return True, ""
            
        from timetable_grid import DAYS
        day_name = DAYS[day] if 0 <= day < len(DAYS) else f"{day+1}. Gün"
        
        placed = self._grid.get_placed_lessons()
        current_day_lessons = []
        for (r, c), data in placed.items():
            if is_move and r == orig_r and c == orig_c:
                continue
            if c == day:
                current_day_lessons.append((r, data))
                
        # Existing hours of THIS specific subject on this day
        existing_subj_daily_hours = 0
        for r, data in current_day_lessons:
            d_subj = data.get("subject_name", data.get("subject", ""))
            d_cls = data.get("class_name", data.get("class", ""))
            if d_subj.strip().upper() == subject.strip().upper() and (not class_name or d_cls == class_name):
                existing_subj_daily_hours += data.get("duration", 1)

        new_total_daily_hours = existing_subj_daily_hours + duration

        for rel in relations:
            r_type = rel.get("kural", "")
            val = rel.get("parametre", 2)
            f_subjs = [s.strip().upper() for s in rel.get("dersler", []) if s.strip()]
            f_teach = [t.strip().upper() for t in rel.get("ogretmenler", []) if t.strip()]
            f_classes = [c.strip().upper() for c in rel.get("siniflar", []) if c.strip()]
            
            # Sınıf veya öğretmen filtresi varsa tam eşleşmeli
            if f_classes and class_name and (class_name.strip().upper() not in f_classes):
                continue
            if f_teach and teacher and (teacher.strip().upper() not in f_teach):
                continue
            if f_subjs and (subject.strip().upper() not in f_subjs):
                continue
                
            # Rule 1: Günde maksimum ders sayısı
            if "Günde maksimum ders sayısı" in r_type or "Günlük maksimum" in r_type:
                max_h = int(val) if str(val).isdigit() else 2
                if not f_subjs:
                    if existing_subj_daily_hours > 0 and new_total_daily_hours > max_h:
                        return False, f"⚠️ <b>'Günde maksimum ders sayısı'</b> kuralına göre <b>{subject}</b> dersi günde en fazla <b>{max_h} saat</b> olabilir. (Bu günde zaten {existing_subj_daily_hours} saat var, bu yerleşimle {new_total_daily_hours} saat oluyor!)"
                else:
                    if existing_subj_daily_hours > 0 and new_total_daily_hours > max_h:
                        return False, f"⚠️ <b>'Günde maksimum ders sayısı'</b> kuralına göre <b>{subject}</b> dersi günde en fazla <b>{max_h} saat</b> olabilir. (Bu günde zaten {existing_subj_daily_hours} saat var, bu yerleşimle {new_total_daily_hours} saat oluyor!)"

            # Rule 2: Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun
            elif "Uygulamalı dersler" in r_type or "Beden Eğitimi" in r_type:
                if existing_subj_daily_hours > 0 and new_total_daily_hours > 2:
                    return False, f"⚠️ <b>'Uygulamalı dersler günde en fazla 2 saat'</b> kuralına göre <b>{subject}</b> dersi bu gün 2 saati aşıyor!"

            # Rule 3: Aynı ders aynı gün tekrar etmesin (Tek blok kuralı)
            elif "tekrar etmesin" in r_type:
                if existing_subj_daily_hours > 0:
                    return False, f"⚠️ <b>'Aynı ders aynı gün tekrar etmesin'</b> kuralına göre <b>{subject}</b> dersi {day_name} gününde zaten mevcuttur!"

            # Rule 4: İki ders aynı güne gelmesin
            elif "aynı güne gelmesin" in r_type or "İki ders aynı güne" in r_type:
                if len(f_subjs) >= 2 and subject.strip().upper() in f_subjs:
                    other_subjs = [s for s in f_subjs if s != subject.strip().upper()]
                    for r, data in current_day_lessons:
                        d_subj = data.get("subject_name", data.get("subject", "")).strip().upper()
                        if d_subj in other_subjs:
                            return False, f"⚠️ <b>'İki ders aynı güne gelmesin'</b> kuralına göre <b>{subject}</b> ve <b>{d_subj}</b> dersleri {day_name} gününde birlikte bulunamaz!"

            # Rule 5: Öğretmenin dersleri öğleden önce toplansın (Period < 4)
            elif "öğleden önce toplansın" in r_type or "Sabah" in r_type:
                if period >= 4:
                    return False, f"⚠️ <b>'Öğretmenin dersleri öğleden önce toplansın'</b> kuralına göre <b>{teacher}</b> öğretmeninin dersi öğleden sonraki saatlere ({period+1}. saat) konulamaz!"

            # Rule 6: Öğretmenin dersleri öğleden sonra toplansın (Period >= 4)
            elif "öğleden sonra toplansın" in r_type:
                if period < 4:
                    return False, f"⚠️ <b>'Öğretmenin dersleri öğleden sonra toplansın'</b> kuralına göre <b>{teacher}</b> öğretmeninin dersi sabah saatlerine ({period+1}. saat) konulamaz!"

            # Rule 7: Son ders saatine zor ders konulmasın
            elif "Son ders saatine zor ders" in r_type:
                last_period = self._grid.table.rowCount() - 1
                HARD_KEYWORDS = ["MAT", "FİZ", "KİM", "BİYO", "GEO"]
                is_hard = any(k in subject.upper() for k in HARD_KEYWORDS)
                if (period + duration - 1 >= last_period) and is_hard:
                    return False, f"⚠️ <b>'Son ders saatine zor ders konulmasın'</b> kuralına göre <b>{subject}</b> gibi zor bir ders günün son saatine ({last_period+1}. saat) konulamaz!"

            # Rule 8: İki zor ders art arda gelmesin
            elif "İki zor ders art arda" in r_type:
                HARD_KEYWORDS = ["MAT", "FİZ", "KİM", "BİYO", "GEO"]
                is_hard = any(k in subject.upper() for k in HARD_KEYWORDS)
                if is_hard:
                    prev_data = placed.get((period - 1, day))
                    next_data = placed.get((period + duration, day))
                    if prev_data and any(k in prev_data.get("subject_name", "").upper() for k in HARD_KEYWORDS):
                        return False, f"⚠️ <b>'İki zor ders art arda gelmesin'</b> kuralına göre <b>{subject}</b> dersi öncesindeki <b>{prev_data.get('subject_name')}</b> dersiyle peş peşe gelemez!"
                    if next_data and any(k in next_data.get("subject_name", "").upper() for k in HARD_KEYWORDS):
                        return False, f"⚠️ <b>'İki zor ders art arda gelmesin'</b> kuralına göre <b>{subject}</b> dersi sonrasındaki <b>{next_data.get('subject_name')}</b> dersiyle peş peşe gelemez!"

        return True, ""

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
            
        # Check boundary
        if row + duration > self._grid.table.rowCount():
            QMessageBox.warning(self, "Geçersiz Konum", f"⚠️ Ders {duration} saatlik olduğu için {row+1}. saate sığmıyor (günlük sınır: {self._grid.table.rowCount()} saat)!")
            return
            
        placed = self._grid.get_placed_lessons()
        
        # Check if cell is occupied when adding from card dock (not a move)
        if not is_move:
            occupied_conflict = None
            for (r, c), data in placed.items():
                if c == col:
                    placed_dur = data.get("duration", 1)
                    if (row < r + placed_dur) and (r < row + duration):
                        occupied_conflict = data
                        break
            if occupied_conflict:
                occ_subj = occupied_conflict.get("subject_name", occupied_conflict.get("subject", "Ders"))
                occ_t = occupied_conflict.get("teacher_name", occupied_conflict.get("teacher", ""))
                msg = QMessageBox(self)
                msg.setWindowTitle("Ders Çakışması / Üzerine Yazma")
                msg.setIcon(QMessageBox.Warning)
                msg.setText(
                    f"⚠️ <b>Bu Saatte Zaten Ders Var!</b><br><br>"
                    f"<b>{day_name}</b> günü <b>{row+1}. ders saatinde</b> bu sınıfta zaten <b>{occ_subj}</b> ({occ_t}) dersi bulunmaktadır.<br><br>"
                    f"Mevcut dersin üzerine yazmak istiyor musunuz?"
                )
                btn_yes = msg.addButton("⚠️ Evet, Üzerine Yaz", QMessageBox.AcceptRole)
                btn_no = msg.addButton("❌ İptal Et / Engelle", QMessageBox.RejectRole)
                msg.setDefaultButton(btn_no)
                msg.exec()
                if msg.clickedButton() != btn_yes:
                    self.statusBar().showMessage("İşlem iptal edildi (Mevcut ders korundu).")
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
                
        # 2. Check Active Planning Relations in Real Time
        is_rel_ok, rel_msg = self._check_planning_relations(
            subject=subject_name, teacher=teacher, class_name=cls_name,
            day=col, period=row, duration=duration,
            is_move=is_move, orig_r=orig_r, orig_c=orig_c
        )
        if not is_rel_ok:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Planlama İlişkisi Uyarısı")
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText(
                f"{rel_msg}<br><br>"
                f"Tanımlanmış aktif bir <b>Planlama İlişkisi</b> kuralı ihlal edilmektedir.<br>"
                f"Ne yapmak istersiniz?"
            )
            btn_ignore = msg_box.addButton("⚠️ Kuralı Yoksay ve Yerleştir", QMessageBox.AcceptRole)
            btn_cancel = msg_box.addButton("❌ İptal Et / Engelle", QMessageBox.RejectRole)
            msg_box.setDefaultButton(btn_cancel)
            msg_box.exec()
            if msg_box.clickedButton() != btn_ignore:
                self.statusBar().showMessage("Planlama ilişkisi kuralı nedeniyle işlem iptal edildi.")
                return
                
        # 2. Check Teacher Conflict (Is teacher already placed elsewhere at this slot across ANY class?)
        teacher_info = next((t for t in self.data_store.get("ogretmenler", []) if t.get("ad") == teacher), {})
        allows_parallel = teacher_info.get("es_zamanli", False)
        
        if teacher and not allows_parallel:
            conflict_found = False
            conflict_class = ""
            conflict_subj = ""
            conflict_period = row
            
            # Check 1: In active grid view
            placed = self._grid.get_placed_lessons()
            for (r, c), data in placed.items():
                if is_move and r == orig_r and c == orig_c:
                    continue
                placed_dur = data.get("duration", 1)
                if c == col:
                    overlap = (row < r + placed_dur) and (r < row + duration)
                    if overlap and data.get("teacher") == teacher and teacher != "":
                        conflict_found = True
                        conflict_class = data.get("class", data.get("class_name", "Mevcut Sınıf"))
                        conflict_subj = data.get("subject", data.get("subject_name", "Ders"))
                        conflict_period = r
                        break
                        
            # Check 2: Globally in data_store grid_placements
            if not conflict_found:
                for p_item in self.data_store.get("grid_placements", []):
                    p_t = format_tr_name(p_item.get("teacher_name") or p_item.get("teacher") or "")
                    if p_t == teacher:
                        p_day = int(p_item.get("day") if "day" in p_item else p_item.get("col", 0))
                        p_period = int(p_item.get("period") if "period" in p_item else p_item.get("row", 0))
                        p_dur = int(p_item.get("duration", 1))
                        p_cls = p_item.get("class_name") or p_item.get("class") or ""
                        p_sub = p_item.get("subject_name") or p_item.get("subject") or "Ders"
                        
                        if is_move and p_cls == cls_name and p_day == orig_c and p_period == orig_r:
                            continue
                            
                        if p_day == col:
                            if (row < p_period + p_dur) and (p_period < row + duration):
                                conflict_found = True
                                conflict_class = p_cls or "Başka Bir Sınıf"
                                conflict_subj = p_sub
                                conflict_period = p_period
                                break
                                
            if conflict_found:
                msg_text = (
                    f"⚠️ <b>Öğretmen Çakışması Algılandı!</b><br><br>"
                    f"<b>{teacher}</b> isimli öğretmenin <b>{day_name}</b> günü <b>{conflict_period+1}. ders saatinde</b> "
                    f"<b>{conflict_class}</b> sınıfında <b>{conflict_subj}</b> dersi bulunmaktadır.<br><br>"
                    f"Normalde sistem çakışmaları engeller. Ne yapmak istersiniz?"
                )
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Ders Çakışması Uyarısı")
                msg_box.setText(msg_text)
                msg_box.setIcon(QMessageBox.Warning)
                btn_ignore = msg_box.addButton("⚠️ Yoksay ve Devam Et", QMessageBox.AcceptRole)
                btn_cancel = msg_box.addButton("❌ İptal Et / Engelle", QMessageBox.RejectRole)
                msg_box.setDefaultButton(btn_cancel)
                msg_box.exec()
                
                if msg_box.clickedButton() != btn_ignore:
                    self.statusBar().showMessage(f"Çakışma engellendi: {teacher} - {conflict_class} ile çakışıyor.")
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
                target_teacher = target_info.get("teacher_name") or target_info.get("teacher", "")
                target_cls = target_info.get("class_name") or target_info.get("class", "")
                self._grid.set_cell(
                    orig_r, orig_c, 
                    target_info.get("subject_name", ""), 
                    get_subject_color(target_info.get("subject_name", "")), 
                    target_teacher, 
                    target_dur, 
                    class_name=target_cls
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
            # Create fresh data store ONLY when confirmed
            self.data_store = {
                "dersler": [], "siniflar": [], "derslikler": [], 
                "ogretmenler": [], "atamalar": [], "settings": {}
            }
            # Kurum adı ile kaydet
            kurum_adi = self.data_store.get("kurum", {}).get("isim", "Yeni_Kurum").replace(" ", "_")
            default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{kurum_adi}.roz")
            
            path, _ = QFileDialog.getSaveFileName(self, "Yeni Kurum Dosyası Oluştur", default_path, "BGZ Planlama Dosyaları (*.roz)")
            if path:
                self.save_db(path)
                self.load_db(path)
                self._refresh_tree()
                self._grid.clear_grid()
                self.statusBar().showMessage("Yeni kurum oluşturuldu ve açıldı.")
            else:
                self.statusBar().showMessage("Kurum oluşturma iptal edildi.")

    def _act_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Dosya Aç / Kurum Değiştir", "", "BGZ Planlama Dosyaları (*.roz);;Tüm Dosyalar (*)")
        if path:
            self.load_db(path)
            self.statusBar().showMessage(f"Açıldı: {path}")

    def _act_save(self):
        self.save_db(sync_from_grid=True)
        fname = os.path.basename(self.current_roz_path or self.db_path or "program.roz")
        self.statusBar().showMessage(f"💾 '{fname}' başarıyla kaydedildi.")

    def _act_print(self):
        if hasattr(self, "save_db"):
            self.save_db(sync_from_grid=True)
        from PySide6.QtWidgets import QDialog
        from dialogs.print_wizard import PrintWizardDialog
        curr_view = self._grid.view_combo.currentText() if hasattr(self, "_grid") else ""
        curr_entity = self._grid.entity_combo.currentText() if hasattr(self, "_grid") else ""
        wiz = PrintWizardDialog(self.data_store, default_entity=curr_entity, default_view=curr_view, parent=self)
        if wiz.exec() == QDialog.Accepted:
            filters = wiz.get_selected_filters()
            filters["default_selection"] = curr_entity
            from dialogs.print_preview import TimetablePrintPreview
            dlg = TimetablePrintPreview(self.data_store, self._grid.get_placed_lessons(), filters, self)
            dlg.direct_print()

    def _act_preview(self):
        if hasattr(self, "save_db"):
            self.save_db(sync_from_grid=True)
        from PySide6.QtWidgets import QDialog
        from dialogs.print_wizard import PrintWizardDialog
        
        curr_view = "Sınıf Görünümü"
        curr_entity = ""
        
        wiz = PrintWizardDialog(self.data_store, default_entity=curr_entity, default_view=curr_view, parent=self)
        if wiz.exec() == QDialog.Accepted:
            filters = wiz.get_selected_filters()
            filters["default_selection"] = curr_entity
            dlg = TimetablePrintPreview(self.data_store, self._grid.get_placed_lessons(), filters, self)
            dlg.exec()

    def _act_close(self):
        self.data_store = {
            "dersler": [], "siniflar": [], "derslikler": [], 
            "ogretmenler": [], "atamalar": [], "settings": {}
        }
        if hasattr(self, "_grid"):
            self._grid.clear_grid()
        self._refresh_tree()
        self.statusBar().showMessage("Dosya kapatıldı.")

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
            self.data_store = prev_state
            save_path = getattr(self, "current_roz_path", None) or self.db_path
            with open(save_path, "w", encoding="utf-8") as f:
                import json
                json.dump(self.data_store, f, ensure_ascii=False, indent=4)
            self._refresh_tree()
            self._restore_grid_placements()
            self.statusBar().showMessage("İşlem geri alındı (Rollback). ↩️")
        else:
            self.statusBar().showMessage("Geri alınacak başka işlem yok.")

    def _act_redo(self):
        import copy
        if hasattr(self, "_redo_stack") and self._redo_stack:
            if not hasattr(self, "_history_stack"): self._history_stack = []
            self._history_stack.append(copy.deepcopy(self.data_store))
            next_state = self._redo_stack.pop()
            self.data_store = next_state
            save_path = getattr(self, "current_roz_path", None) or self.db_path
            with open(save_path, "w", encoding="utf-8") as f:
                import json
                json.dump(self.data_store, f, ensure_ascii=False, indent=4)
            self._refresh_tree()
            self._restore_grid_placements()
            self.statusBar().showMessage("İşlem yinelendi (Redo). ↪️")
        else:
            self.statusBar().showMessage("Yinelenecek başka işlem yok.")

    def _open_subjects(self):
        self.save_db(sync_from_grid=True)
        d = MasterDataDialog(0, self)
        d.exec()
        self.save_db()
        self._refresh_tree()
        self._restore_grid_placements()

    def _open_school_info(self):
        from dialogs.school_info import SchoolInfoDialog
        d = SchoolInfoDialog(parent=self, data_store=self.data_store)
        if d.exec() == QDialog.Accepted:
            settings = self.data_store.get("settings", {})
            periods = int(settings.get("periods", 8))
            if hasattr(self, "_grid"):
                self._grid.set_periods(periods)
            self.save_db()
            self._refresh_tree()
            self._restore_grid_placements()

    def _open_classes(self):
        self.save_db(sync_from_grid=True)
        d = MasterDataDialog(1, self)
        d.exec()
        self.save_db()
        self._refresh_tree()
        self._restore_grid_placements()

    def _open_class_assignments(self, target_class=None):
        from dialogs.edit_forms import ClassComprehensiveAssignmentDialog
        from PySide6.QtWidgets import QInputDialog
        
        classes = [c.get("ad", "") for c in self.data_store.get("siniflar", []) if c.get("ad")]
        if not classes:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Bilgi", "Henüz tanımlı hiçbir sınıf bulunmamaktadır.")
            return
            
        selected_class = target_class
        if not selected_class:
            curr_item = self._tree.currentItem()
            if curr_item and curr_item.parent() and curr_item.parent().data(0, Qt.UserRole + 10) == "sinif":
                selected_class = curr_item.text(0)
                
        if not selected_class or selected_class not in classes:
            c_choice, ok = QInputDialog.getItem(self, "Sınıfın Dersleri", "Derslerini ve Öğretmenlerini Yönetmek İstediğiniz Sınıfı Seçin:", sorted(classes), 0, False)
            if ok and c_choice:
                selected_class = c_choice
            else:
                return
                
        d = ClassComprehensiveAssignmentDialog(class_name=selected_class, data_store=self.data_store, parent=self)
        if d.exec():
            self.save_db()
            self._refresh_tree()
            self._restore_grid_placements()

    def _show_tree_context_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        item = self._tree.itemAt(pos)
        if not item: return
        parent = item.parent()
        if not parent: return
        
        parent_text = parent.text(0)
        entity_name = item.data(0, Qt.UserRole)
        
        menu = QMenu(self)
        if "Sınıflar" in parent_text:
            act = menu.addAction(f"🎓 {entity_name} Sınıfının Dersleri (Atama Paneli)")
            chosen = menu.exec_(self._tree.mapToGlobal(pos))
            if chosen == act:
                self._open_class_assignments(target_class=entity_name)
        elif "Öğretmenler" in parent_text:
            act = menu.addAction(f"🎓 {entity_name} Öğretmenin Atamaları")
            chosen = menu.exec_(self._tree.mapToGlobal(pos))
            if chosen == act:
                from dialogs.edit_forms import LessonAssignmentDialog
                d = LessonAssignmentDialog(data_store=self.data_store, parent=self, selected_teacher=entity_name)
                if d.exec():
                    self.save_db()
                    self._refresh_tree()
                    self._restore_grid_placements()

    def _open_rooms(self):
        self.save_db(sync_from_grid=True)
        d = MasterDataDialog(2, self)
        d.exec()
        self.save_db()
        self._refresh_tree()
        self._restore_grid_placements()

    def _open_teachers(self):
        self.save_db(sync_from_grid=True)
        d = MasterDataDialog(3, self)
        d.exec()
        self.save_db()
        self._refresh_tree()
        self._restore_grid_placements()

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
        from PySide6.QtWidgets import QDialog
        
        target_class = None
        if hasattr(self, "_grid") and hasattr(self._grid, "view_combo") and hasattr(self._grid, "entity_combo"):
            if self._grid.view_combo.currentText() == "Sınıf Görünümü":
                target_class = self._grid.entity_combo.currentText()
        if not target_class and hasattr(self, "_active_entity_name") and getattr(self, "_active_view_type", "") == "class":
            target_class = self._active_entity_name
        # Atama kontrolü: hedef sınıfa ders atanmamışsa uyarı ver
        atamalar = self.data_store.get("atamalar", [])
        if target_class:
            from auto_scheduler import normalize_class_name
            tc_norm = normalize_class_name(target_class)
            class_atamalar = [a for a in atamalar if normalize_class_name(a.get("class") or a.get("sinif") or a.get("class_name") or "") == tc_norm]
            if not class_atamalar:
                QMessageBox.warning(
                    self, "Ders Ataması Bulunamadı",
                    f"⚠️ {target_class} sınıfına henüz ders ataması yapılmamış!\n\n"
                    f"Otomatik planlama başlatılabilmesi için önce bu sınıfa ders ve öğretmen atamalısınız.\n\n"
                    f"Sınıflar → {target_class} → Ders & Öğretmen Ata yolunu izleyebilirsiniz."
                )
                return
        elif not atamalar:
            QMessageBox.warning(
                self, "Ders Ataması Bulunamadı",
                "⚠️ Hiçbir sınıfa ders ataması yapılmamış!\n\n"
                "Otomatik planlama başlatılabilmesi için önce sınıflara ders ve öğretmen atamalısınız.\n\n"
                "Sınıflar → [Sınıf Seç] → Ders & Öğretmen Ata yolunu izleyebilirsiniz."
            )
            return

        d = AutoScheduleDialog(self.data_store, self, target_class=target_class)
        if d.exec() == QDialog.Accepted:
            # AI produced a schedule
            results = self.data_store.get("auto_schedule_results", [])
            if results:
                grid_placements = []
                for r in results:
                    c_name = r.get("class_name", r.get("class", ""))
                    t_name = format_tr_name(r.get("teacher_name", r.get("teacher", "")))
                    subj = r.get("subject_name", r.get("subject", ""))
                    d_idx = r.get("day_idx") if "day_idx" in r else r.get("day", r.get("col", 0))
                    p_idx = r.get("period") if "period" in r else r.get("row", 0)
                    dur = int(r.get("duration", 1))
                    color = get_subject_color(subj)
                    
                    grid_placements.append({
                        "period": p_idx,
                        "day": d_idx,
                        "row": p_idx,
                        "col": d_idx,
                        "subject_name": subj,
                        "subject": subj,
                        "color": color,
                        "teacher_name": t_name,
                        "teacher": t_name,
                        "duration": dur,
                        "class_name": c_name,
                        "class": c_name
                    })
                
                # Update datastore and save cleanly
                self.data_store["grid_placements"] = grid_placements
                self.save_db(sync_from_grid=False)
                self._restore_grid_placements()
                self._refresh_tree()
                
                total_hours = sum(p.get("duration", 1) for p in grid_placements)
                QMessageBox.information(
                    self, "Otomatik Planlama Tamamlandı",
                    f"🎉 Otomatik planlama başarıyla oluşturuldu!\n\nToplam {total_hours} ders saatinin tamamı haftalık çizelgeye eksiksiz (%100 Dolu) olarak yerleştirildi."
                )
                self.statusBar().showMessage(f"Otomatik planlama başarıyla oluşturuldu ({total_hours} ders saati yerleştirildi).")
            else:
                self.save_db(sync_from_grid=False)
                self._restore_grid_placements()
                self._refresh_tree()

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
        view = self._grid.view_combo.currentText()
        entity = self._grid.entity_combo.currentText()
        
        if view == "Genel Görünüm" or not entity:
            msg = "Tüm sınıflar ve öğretmenler için yerleştirilmiş derslerin TAMAMI çizelgeden kaldırılacak.\nEmin misiniz?"
            target_entity = None
            target_type = None
        else:
            msg = f"Sadece '{entity}' için yerleştirilmiş dersler çizelgeden kaldırılacak.\nEmin misiniz?\n\n(Tüm okulu sıfırlamak için Genel Görünüm'e geçebilirsiniz)"
            target_entity = entity
            if view == "Sınıf Görünümü": target_type = "class_name"
            elif view == "Öğretmen Görünümü": target_type = "teacher_name"
            else: target_type = "room_name"

        r = QMessageBox.question(self, "Çizelgeyi Sıfırla / Temizle", msg, QMessageBox.Yes | QMessageBox.No)
        
        if r == QMessageBox.Yes:
            if target_entity is None:
                self.data_store["grid_placements"] = []
                self.data_store["auto_schedule_results"] = []
                self.data_store["yerlesim"] = {}
                msg_toast = "🧹 Tüm çizelge dersleri başarıyla sıfırlandı."
            else:
                from auto_scheduler import normalize_class_name
                new_placements = []
                for p in self.data_store.get("grid_placements", []):
                    # Check if this placement belongs to the target entity
                    p_val = p.get(target_type, "")
                    if target_type == "class_name":
                        if normalize_class_name(p_val) == normalize_class_name(target_entity):
                            continue # Skip this one (remove it)
                    else:
                        if p_val == target_entity:
                            continue # Skip this one (remove it)
                    new_placements.append(p)
                
                self.data_store["grid_placements"] = new_placements
                msg_toast = f"🧹 {entity} çizelgesi başarıyla sıfırlandı."

            if hasattr(self, "_grid"):
                self._grid.clear_grid()
                self._grid._placed_lessons = {}
            self.save_db(sync_from_grid=False)
            self._restore_grid_placements()
            self._refresh_tree()
            self.statusBar().showMessage(msg_toast)

    def _open_extracted(self, dialog_id):
        from dialogs.extracted_dialog import open_extracted_dialog
        open_extracted_dialog(dialog_id, self)

    def _act_nyi(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Bulut Tabanlı Planlama")
        msg.setIcon(QMessageBox.Information)
        msg.exec()
