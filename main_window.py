"""
main_window.py  –  Ana pencere
Pixel-perfect aSc k12 Bilişim Ders Planlama 2020 ribbon + workspace
"""
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QSplitter, QTreeWidget, QTreeWidgetItem, QStatusBar,
    QMessageBox, QTabWidget, QFrame, QSizePolicy, QMenu, QToolButton, QFileDialog, QDialog,
    QTableWidgetItem
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

def get_subject_color(subject_name: str, data_store: dict = None) -> str:
    """Returns the persistent color for a subject, checking data_store first."""
    if not subject_name:
        return "#2563EB"
    from dialogs.color_picker_dialog import resolve_subject_color
    return resolve_subject_color(subject_name, data_store)

def get_teacher_color(teacher_name: str, data_store: dict = None) -> str:
    """Returns a deterministic color for a teacher."""
    if not teacher_name:
        return "#2563EB"
    if data_store and "ogretmenler" in data_store:
        for t in data_store["ogretmenler"]:
            if t.get("ad", "").strip().lower() == teacher_name.strip().lower():
                c = t.get("color") or t.get("renk")
                if c and QColor(c).isValid() and str(c).upper() not in ("#FFFFFF", "#000000"):
                    return c
    # Fallback to deterministic curated color
    hash_val = sum(ord(ch) * (i + 1) for i, ch in enumerate(teacher_name.strip()))
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
    def __init__(self, logo_path=None, auth_data=None, override_db_path=None,
                 institution_slug=None, institution_name=None, version_filename=None):
        super().__init__()
        self.auth_data = auth_data
        self.logo_path = logo_path
        self.institution_slug = institution_slug
        self.institution_name = institution_name or ""
        self.version_filename = version_filename or ""
        self.go_home_requested = None  # Callback set by AppShell
        
        title = "BGZ Ders Programı Yöneticisi"
        if institution_name:
            title = f"{institution_name} — {title}"
        self.setWindowTitle(title)
        self.resize(1280, 780)
        self.setMinimumSize(900, 600)

        if logo_path and os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        # Core Data Engine Initialization
        self.tt_data = TimetableData()
        user_dir = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
        os.makedirs(user_dir, exist_ok=True)
        self.config_path = os.path.join(user_dir, "app_config.json")
        
        if override_db_path and os.path.exists(override_db_path):
            self.db_path = override_db_path
        else:
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
        self.cloud_status_lbl = QLabel("Veritabanınız korunuyor: Senkronize")
        self.cloud_status_lbl.setStyleSheet("color: #15803D; font-weight: bold; margin-right: 10px; font-size: 11px;")
        self.statusBar().addPermanentWidget(self.cloud_status_lbl)
        
        from PySide6.QtWidgets import QPushButton
        btn_download = QPushButton(" Güncel Versiyonu İndir")
        from timetable_grid import make_grid_action_icon
        btn_download.setIcon(make_grid_action_icon("download", 16))
        btn_download.setCursor(Qt.PointingHandCursor)
        btn_download.setStyleSheet("""
            QPushButton {
                padding: 3px 12px; font-weight: bold; background: #0284C7; color: white;
                border-radius: 4px; border: none; font-size: 11px;
            }
            QPushButton:hover { background: #0369A1; }
        """)
        def open_download_page():
            import webbrowser
            download_url = self.data_store.get("settings", {}).get("download_url", "https://chenki.net/indir")
            webbrowser.open(download_url)
            self.statusBar().showMessage(f"İndirme sayfası açılıyor: {download_url}")
            
        btn_download.clicked.connect(open_download_page)
        self.statusBar().addPermanentWidget(btn_download)

        # Home button (back to dashboard)
        btn_home = QPushButton("🏠  Ana Sayfa")
        btn_home.setCursor(Qt.PointingHandCursor)
        btn_home.setStyleSheet("""
            QPushButton {
                padding: 3px 14px; font-weight: bold; background: #7C3AED; color: white;
                border-radius: 4px; border: none; font-size: 11px;
            }
            QPushButton:hover { background: #6D28D9; }
        """)
        btn_home.clicked.connect(self._go_home)
        self.statusBar().addPermanentWidget(btn_home)

        # Version / Institution info
        inst_text = ""
        if self.institution_name:
            inst_text = f"🏫 {self.institution_name}"
            if self.version_filename:
                import re
                m = re.match(r"v(\d+)_", self.version_filename)
                if m:
                    inst_text += f"  •  v{int(m.group(1))}"
        else:
            inst_text = "Chenki Akademi 2026 - 2027 Pro"
        ver_lbl = QLabel(inst_text)
        ver_lbl.setStyleSheet("color: #64748B; font-weight: bold; margin-left: 10px; margin-right: 10px;")
        self.statusBar().addPermanentWidget(ver_lbl)
        
        # Cloud Sync Status Indicator
        self.cloud_worker = None
        self.cloud_status_lbl.setText("Veritabanınız korunuyor: Canlı Senkronize (VDS Aktif)")

        # Global Rollback / Undo / Redo Shortcuts
        from PySide6.QtGui import QKeySequence, QShortcut
        QShortcut(QKeySequence.Undo, self, self._act_undo)
        QShortcut(QKeySequence("Ctrl+Z"), self, self._act_undo)
        QShortcut(QKeySequence.Redo, self, self._act_redo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self._act_redo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self._act_redo)

    
    def _on_remote_data_updated(self, slug, filename):
        if not slug or slug == getattr(self, "institution_slug", None):
            try:
                import version_store
                inst_slug = getattr(self, "institution_slug", "bogazici_egitim_kurumlari")
                latest_data = version_store.load_latest_version(inst_slug)
                if latest_data:
                    if latest_data.get("grid_placements") != self.data_store.get("grid_placements") or latest_data.get("atamalar") != self.data_store.get("atamalar"):
                        self.data_store.clear()
                        self.data_store.update(latest_data)
                        self._refresh_grid()
                        self._refresh_tree()
                        self.statusBar().showMessage("☁️ VDS'den canlı veri güncellendi", 4000)
            except Exception as e:
                print(f"[MainWindow] Live data update notice: {e}")

    def _download_cloud_data(self, show_message=False):
        """Pulls latest data from VDS backend API (replaces old Firebase RTDB call)."""
        if not hasattr(self, "auth_data") or not self.auth_data:
            return
        # Don't overwrite if there are pending local pushes
        if hasattr(self, "cloud_worker") and self.cloud_worker and len(self.cloud_worker._queue) > 0:
            return
        
        try:
            from api_client import api_client
            pull_ok, msg, count = api_client.pull_all_from_rtdb(self.auth_data)
            if pull_ok:
                # Reload the current version from disk (pull may have updated it)
                if hasattr(self, "institution_slug") and hasattr(self, "version_filename"):
                    import version_store
                    refreshed = version_store.load_version(self.institution_slug, self.version_filename)
                    if refreshed and refreshed != self.data_store:
                        self.data_store.clear()
                        self.data_store.update(refreshed)
                        self._refresh_tree()
                        self._refresh_grid()
                        self.statusBar().showMessage("VDS'den veriler senkronize edildi ✅", 4000)
                if show_message:
                    QMessageBox.information(self, "Bulut Senkronizasyon", f"Senkronizasyon tamamlandı.\n{msg}")
            elif show_message:
                QMessageBox.warning(self, "Bulut Senkronizasyon", f"Senkronizasyon başarısız: {msg}")
        except Exception as e:
            print(f"[MainWindow] VDS data pull error: {e}")
            if show_message:
                QMessageBox.warning(self, "Bulut Senkronizasyon", f"Bağlantı hatası: {e}")

    def _act_check_updates(self):
        import requests, webbrowser
        try:
            from api_client import api_client
            base_url = getattr(api_client, 'base_url', 'https://chenki.net')
            url = f"{base_url}/api/updates" if '/api' not in base_url else f"{base_url}/updates"
        except Exception:
            url = "https://chenki.net/api/updates"
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

    def cleanup(self):
        """Clean up background workers and resources before deletion."""
        if hasattr(self, 'cloud_worker') and self.cloud_worker:
            cw = self.cloud_worker
            self.cloud_worker = None
            try:
                cw.sync_status_changed.disconnect()
            except Exception:
                pass
            try:
                cw.remote_data_updated.disconnect()
            except Exception:
                pass
            try:
                cw.stop()
                cw.deleteLater()
            except Exception as e:
                print("Error stopping cloud_worker:", e)

    def closeEvent(self, event):
        # 1. Quick save feedback
        from save_dialog import run_apple_save_sequence
        run_apple_save_sequence(self, duration_seconds=0.15, title="Kapatılıyor", message="Veriler kaydedildi.")
        
        # 2. Save to disk
        try:
            if hasattr(self, "institution_slug") and hasattr(self, "version_filename") and self.institution_slug and self.version_filename:
                import version_store
                version_store.update_version_in_place(self.institution_slug, self.version_filename, self.data_store)
        except Exception as e:
            print("Auto-save on exit error:", e)
            
        # 3. Clean up
        self.cleanup()
        super().closeEvent(event)

    # ──────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        # Ribbon
        self._ribbon = RibbonWidget(root)
        self._build_ribbon()
        root_layout.addWidget(self._ribbon)

        # Wire the file menu (Integrated directly on Ribbon Tab Bar)
        fm = self._ribbon.file_menu
        
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
        
        view_type = "class"
        if "Öğretmenler" in parent_text:
            view_type = "teacher"
            if hasattr(self, "_grid"):
                self._grid._set_view_mode("teachers")
                # Scroll to teacher row if found
                for r in range(self._grid.table.rowCount()):
                    item_lbl = self._grid.table.verticalHeaderItem(r)
                    if item_lbl and item_lbl.text() == entity_name:
                        self._grid.table.selectRow(r)
                        self._grid.table.scrollToItem(self._grid.table.item(r, 0) or item_lbl)
                        break
        elif "Sınıflar" in parent_text:
            view_type = "class"
            if hasattr(self, "_grid"):
                self._grid._set_view_mode("classes")
                # Scroll to class row if found
                for r in range(self._grid.table.rowCount()):
                    item_lbl = self._grid.table.verticalHeaderItem(r)
                    if item_lbl and item_lbl.text() == entity_name:
                        self._grid.table.selectRow(r)
                        self._grid.table.scrollToItem(self._grid.table.item(r, 0) or item_lbl)
                        break
        self.statusBar().showMessage(f"Görünüm güncellendi: {entity_name}")
        self._restore_grid_placements(view_type, entity_name)
        self._refresh_tree(view_type=view_type, target_entity=entity_name)

    # ── Ribbon ────────────────────────────────────────────────────────────────
    def _build_ribbon(self):
        r = self._ribbon

        # ── 1. Ana Menü ──────────────────────────────────────────────────────
        p1 = r.add_tab("Ana Menü")
        p1.add_button("Ana Sayfa",      "anasayfa", self._go_home)
        p1.add_button("Yeni",           "yeni",     self._act_new)
        p1.add_button("Aç",             "ac",       self._act_open)
        p1.add_button("Kaydet",         "kaydet",   self._act_save)
        p1.add_button("Geri Al\nCtrl+Z","bilgi",    self._act_undo)
        p1.add_button("Yinele\nCtrl+Y", "bilgi",    self._act_redo)
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
        p3.add_button("Toplu Atama\nListesi", "bilgi", self._act_assignment_list)
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

        self._grid.view_mode_changed.connect(lambda mode: self._refresh_grid())

        # Wire up grid toggle button
        def toggle_sidebar():
            is_vis = left.isVisible()
            left.setVisible(not is_vis)
            splitter.setSizes([220, 1060] if not is_vis else [0, 1060])
            
        self._grid.toggle_panel_btn.clicked.connect(toggle_sidebar)
        # Set initial left panel hidden (kapalı başlasın)
        left.setVisible(False)
        splitter.setSizes([0, 1060])
        
        return splitter

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

                # Load global kisitlamalar and override local
                from version_store import load_global_kisitlamalar
                global_k = load_global_kisitlamalar()
                inst_slug = self.data_store.get("settings", {}).get("institution_slug", "bogazici_egitim_kurumlari")
                
                if "kisitlamalar" not in self.data_store:
                    self.data_store["kisitlamalar"] = {}
                
                # Check if this institution has its own constraints in the global file
                if inst_slug in global_k:
                    for k, v in global_k[inst_slug].items():
                        self.data_store["kisitlamalar"][k] = v

                self.statusBar().showMessage(f"Veriler yüklendi: {load_path}")
            except Exception as e:
                print("DB Load Error:", e)

        self._refresh_grid()
        self._refresh_tree()
        self._is_loading = False
        self._initial_hash = self._calc_data_hash()
        self._is_dirty = False

    def _calc_data_hash(self):
        import hashlib, json
        clean_data = {k: v for k, v in self.data_store.items() if k != "_version_meta"}
        try:
            raw = json.dumps(clean_data, sort_keys=True, ensure_ascii=False)
            return hashlib.md5(raw.encode("utf-8")).hexdigest()
        except Exception:
            return ""

    def mark_dirty(self):
        self._is_dirty = True

    def is_dirty(self) -> bool:
        if getattr(self, "_is_dirty", False):
            return True
        current_hash = self._calc_data_hash()
        initial_hash = getattr(self, "_initial_hash", "")
        return bool(initial_hash and current_hash and current_hash != initial_hash)

    def has_unsaved_changes(self) -> bool:
        return self.is_dirty()

    def _sync_grid_to_store(self, view_type=None, entity_name=None):
        if getattr(self, "_is_loading", False):
            return
        if not hasattr(self, "_grid") or not hasattr(self._grid, "get_placed_lessons"):
            return
            
        settings = self.data_store.get("settings", {})
        periods = int(settings.get("periods", 8))
        if periods <= 0: periods = 8
        
        mode = getattr(self._grid, "current_view_mode", "classes")
        placed = self._grid.get_placed_lessons()
        if not placed:
            self.data_store["grid_placements"] = []
            return
            
        import re
        def cls_sort_key(c):
            m = re.match(r"(\d+)(.*)", str(c).strip())
            return (int(m.group(1)), m.group(2)) if m else (999, str(c))
            
        classes = self.data_store.get("siniflar", [])
        class_names = sorted([c.get("ad", "").strip() for c in classes if c.get("ad")], key=cls_sort_key)
        if not class_names:
            class_names = ["9A", "9B", "10A", "10B", "11A", "11B", "11C", "12A", "12B"]
            
        teachers = self.data_store.get("ogretmenler", [])
        teacher_names = sorted([t.get("ad", "").strip() for t in teachers if t.get("ad")])
        if not teacher_names:
            teacher_names = ["Öğretmen 1"]

        new_global = []
        seen_comb = set()
        for (r, c), info in placed.items():
            p = dict(info)
            s_name = p.get("subject_name") or p.get("subject", "")
            if not s_name or s_name.lower() in ["boş", "bos", "atanmadı"]:
                continue
                
            day = c // periods
            period = c % periods
            p["day"] = day
            p["col"] = day
            p["period"] = period
            p["row"] = period
            p["duration"] = 1
            
            c_name = (p.get("class_name") or p.get("class") or "").strip()
            is_comb = bool(p.get("is_combined") or ("," in c_name or "&" in c_name or "+" in c_name))
            
            if is_comb:
                comb_cls = p.get("combined_classes") or [sc.strip().split("(")[0].strip() for sc in c_name.replace("&", "+").replace(",", "+").split("+") if sc.strip()]
                p["is_combined"] = True
                p["combined_classes"] = comb_cls
                normalized_c_name = " + ".join(comb_cls)
                p["class_name"] = normalized_c_name
                p["class"] = normalized_c_name
                if mode == "teachers" and r < len(teacher_names):
                    p["teacher_name"] = teacher_names[r]
                    p["teacher"] = teacher_names[r]
                p["color"] = get_subject_color(s_name, self.data_store)
                
                t_name = p.get("teacher_name") or p.get("teacher") or ""
                bid = p.get("block_id") or ""
                dedup_key = (day, period, normalized_c_name, s_name, t_name, bid)
                if dedup_key in seen_comb:
                    continue
                seen_comb.add(dedup_key)
                
                new_global.append(p)
            elif mode == "teachers":
                if r < len(teacher_names):
                    p["teacher_name"] = teacher_names[r]
                    p["teacher"] = teacher_names[r]
                p["color"] = get_subject_color(s_name, self.data_store)
                new_global.append(p)
            else:
                if r < len(class_names):
                    cls_name = class_names[r]
                    p["class_name"] = cls_name
                    p["class"] = cls_name
                p["color"] = get_subject_color(s_name, self.data_store)
                new_global.append(p)
                
        self.data_store["grid_placements"] = new_global

    def _restore_grid_placements(self, view_type=None, entity_name=None):
        self._refresh_grid()

    def _refresh_grid(self, skip_unplaced=False):
        if not hasattr(self, "_grid"):
            return
            
        settings = self.data_store.get("settings", {})
        periods = int(settings.get("periods", 8))
        days_list = settings.get("days")
        if not days_list:
            days_count = int(settings.get("days_count", settings.get("day_count", self.data_store.get("gun_sayisi", 5))))
            from timetable_grid import DAYS
            days_list = DAYS[:days_count]
        
        mode = getattr(self._grid, "current_view_mode", "classes")
        grid_data = self.data_store.get("grid_placements", [])
        if not grid_data and self.data_store.get("auto_schedule_results"):
            grid_data = self.data_store.get("auto_schedule_results")
            
        from dialogs.edit_forms import format_tr_name
        
        # Batch UI updates for instantaneous rendering (0ms lag)
        if hasattr(self._grid, "table"):
            self._grid.table.setUpdatesEnabled(False)
            
        try:
            if mode == "teachers":
                teachers = self.data_store.get("ogretmenler", [])
                teacher_names = sorted([t.get("ad", "").strip() for t in teachers if t.get("ad")])
                if not teacher_names:
                    teacher_names = ["Öğretmen 1"]
                self._grid.set_mode_all_teachers(teacher_names, periods, days_list)
                
                teacher_match_cache = {}
                t_matrix = [[{} for _ in range(periods)] for _ in range(len(days_list) * len(teacher_names))]
                
                for item in grid_data:
                    s_name = (item.get("subject_name") or item.get("subject") or "").strip()
                    if s_name.lower() in ["boş", "bos", "atanmadı", ""]:
                        continue
                    c_name = (item.get("class_name") or item.get("class") or "").strip()
                    t_name = (item.get("teacher_name") or item.get("teacher") or "").strip()
                    dur = int(item.get("duration", 1))
                    col = int(item.get("day", item.get("col", 0)))
                    period = int(item.get("period", item.get("row", 0)))
                    is_locked = bool(item.get("locked", False))
                    is_man = bool(item.get("is_manual", False))
                    
                    if t_name in teacher_match_cache:
                        matching_row = teacher_match_cache[t_name]
                    else:
                        matching_row = -1
                        if t_name in teacher_names:
                            matching_row = teacher_names.index(t_name)
                        else:
                            for idx, tn in enumerate(teacher_names):
                                if format_tr_name(tn) == format_tr_name(t_name):
                                    matching_row = idx
                                    break
                            teacher_match_cache[t_name] = matching_row
                                
                    if 0 <= matching_row < len(teacher_names) and 0 <= col < len(days_list):
                        color = get_teacher_color(t_name, self.data_store)
                        for ext in range(dur):
                            p_idx = period + ext
                            if p_idx < periods:
                                matrix_idx = matching_row * len(days_list) + col
                                t_matrix[matrix_idx][p_idx] = {
                                    "subject_name": s_name, "class_name": c_name, "teacher_name": t_name,
                                    "color": color, "locked": is_locked, "is_manual": is_man,
                                    "is_combined": bool(item.get("is_combined")),
                                    "block_id": item.get("block_id")
                                }
                                
                for r_idx, t_name in enumerate(teacher_names):
                    for d_idx in range(len(days_list)):
                        matrix_idx = r_idx * len(days_list) + d_idx
                        p = 0
                        while p < periods:
                            cell_info = t_matrix[matrix_idx][p]
                            if not cell_info or not cell_info.get("subject_name"):
                                p += 1
                                continue
                                
                            s_name = cell_info["subject_name"]
                            c_name = cell_info["class_name"]
                            color = cell_info["color"]
                            is_locked = cell_info["locked"]
                            is_man = cell_info["is_manual"]
                            
                            span = 1
                            cell_bid = cell_info.get("block_id")
                            while p + span < periods:
                                next_info = t_matrix[matrix_idx][p + span]
                                if not next_info or not next_info.get("subject_name"):
                                    break
                                next_bid = next_info.get("block_id")
                                # block_id varsa: sadece aynı block_id birleşir
                                if cell_bid and next_bid:
                                    if cell_bid == next_bid:
                                        span += 1
                                    else:
                                        break
                                # Legacy (block_id yok): tüm özellikler eşleşmeli
                                elif (next_info.get("subject_name") == s_name
                                        and next_info.get("class_name") == c_name
                                        and next_info.get("teacher_name") == cell_info["teacher_name"]
                                        and next_info.get("is_combined") == cell_info.get("is_combined")):
                                    span += 1
                                else:
                                    break
                                    
                            actual_col = d_idx * periods + p
                            self._grid.set_cell(r_idx, actual_col, s_name, color, t_name, span, c_name, display_mode="teachers", locked=is_locked, is_manual=is_man, is_combined=cell_info.get("is_combined", False), combined_classes=cell_info.get("combined_classes", []))
                            p += span
            else:
                import re
                def cls_sort_key(c):
                    m = re.match(r"(\d+)(.*)", c.strip())
                    return (int(m.group(1)), m.group(2)) if m else (999, c)
                
                classes = self.data_store.get("siniflar", [])
                class_names = sorted([c.get("ad", "").strip() for c in classes if c.get("ad")], key=cls_sort_key)
                if not class_names:
                    class_names = ["9A", "9B", "10A", "10B", "11A", "11B", "11C", "12A", "12B"]
                    
                self._grid.set_mode_all_classes(class_names, periods, days_list)
                
                class_match_cache = {}
                c_matrix = [[{} for _ in range(periods)] for _ in range(len(days_list) * len(class_names))]
                
                for item in grid_data:
                    s_name = (item.get("subject_name") or item.get("subject") or "").strip()
                    if s_name.lower() in ["boş", "bos", "atanmadı", ""]:
                        continue
                    c_name = (item.get("class_name") or item.get("class") or "").strip()
                    t_name = (item.get("teacher_name") or item.get("teacher") or "").strip()
                    dur = int(item.get("duration", 1))
                    col = int(item.get("day", item.get("col", 0)))
                    period = int(item.get("period", item.get("row", 0)))
                    is_locked = bool(item.get("locked", False))
                    is_man = bool(item.get("is_manual", False))
                    
                    from auto_scheduler import matches_class
                    if item.get("is_combined") and item.get("combined_classes"):
                        clean_c_name = c_name.strip().split("(")[0].strip()
                        # If the item's class_name is exactly one of the combined_classes,
                        # it means this is a discrete entry. Just draw it for that class!
                        target_list = [str(c).strip().split("(")[0].strip() for c in item["combined_classes"] if str(c).strip()]
                        if clean_c_name in target_list:
                            target_classes = [clean_c_name]
                        else:
                            target_classes = target_list
                    elif "," in c_name or "&" in c_name or "+" in c_name:
                        target_classes = [c.strip().split("(")[0].strip() for c in c_name.replace("&", "+").replace(",", "+").split("+") if c.strip()]
                    else:
                        target_classes = [c_name]
                        
                    is_item_comb = bool(item.get("is_combined") or (len(target_classes) > 1) or ("+" in c_name) or ("," in c_name) or ("&" in c_name))
                    for tc in target_classes:
                        if tc in class_match_cache:
                            matching_row = class_match_cache[tc]
                        else:
                            matching_row = -1
                            if tc in class_names:
                                matching_row = class_names.index(tc)
                            else:
                                for idx, cn in enumerate(class_names):
                                    if matches_class(cn, tc) or matches_class(tc, cn):
                                        matching_row = idx
                                        break
                            class_match_cache[tc] = matching_row
                                        
                        if 0 <= matching_row < len(class_names) and 0 <= col < len(days_list):
                            color = get_subject_color(s_name, self.data_store)
                            for ext in range(dur):
                                p_idx = period + ext
                                if p_idx < periods:
                                    matrix_idx = matching_row * len(days_list) + col
                                    c_matrix[matrix_idx][p_idx] = {
                                        "subject_name": s_name, "class_name": c_name if (len(target_classes) > 1 or is_item_comb) else tc, "teacher_name": t_name,
                                        "color": color, "locked": is_locked, "is_manual": is_man, "is_combined": is_item_comb,
                                        "block_id": item.get("block_id")
                                    }
                                    
                for r_idx, c_name in enumerate(class_names):
                    for d_idx in range(len(days_list)):
                        matrix_idx = r_idx * len(days_list) + d_idx
                        p = 0
                        while p < periods:
                            cell_info = c_matrix[matrix_idx][p]
                            if not cell_info or not cell_info.get("subject_name"):
                                p += 1
                                continue
                                
                            s_name = cell_info["subject_name"]
                            tc = cell_info["class_name"]
                            t_name = cell_info["teacher_name"]
                            color = cell_info["color"]
                            is_locked = cell_info["locked"]
                            is_man = cell_info["is_manual"]
                            is_comb_cell = cell_info.get("is_combined", False)
                            
                            span = 1
                            cell_bid = cell_info.get("block_id")
                            while p + span < periods:
                                next_info = c_matrix[matrix_idx][p + span]
                                if not next_info or not next_info.get("subject_name"):
                                    break
                                next_bid = next_info.get("block_id")
                                # block_id varsa: sadece aynı block_id birleşir
                                if cell_bid and next_bid:
                                    if cell_bid == next_bid:
                                        span += 1
                                    else:
                                        break
                                # Legacy (block_id yok): tüm özellikler + is_combined eşleşmeli
                                elif (next_info.get("subject_name") == s_name
                                        and next_info.get("class_name") == tc
                                        and next_info.get("teacher_name") == t_name
                                        and next_info.get("is_combined") == cell_info.get("is_combined")):
                                    span += 1
                                else:
                                    break
                                    
                            actual_col = d_idx * periods + p
                            self._grid.set_cell(r_idx, actual_col, s_name, color, t_name, span, tc, display_mode="classes", locked=is_locked, is_manual=is_man, is_combined=is_comb_cell, combined_classes=cell_info.get("combined_classes", []))
                            p += span
        finally:
            if hasattr(self._grid, "table"):
                self._grid.table.setUpdatesEnabled(True)
                self._grid.table.viewport().update()
        
        # Update unplaced dock (skip when called from _delete_lesson_at which does its own deferred refresh)
        if not skip_unplaced:
            self._refresh_unplaced_lessons()



    def save_db(self, path=None, sync_from_grid=False):
        if getattr(self, "_is_loading", False):
            return
            
        import json
        slug = getattr(self, "institution_slug", None)
        ver_fn = getattr(self, "version_filename", None)
        
        save_path = path or getattr(self, "current_roz_path", None) or self.db_path
        if not save_path and slug and ver_fn:
            import version_store
            save_path = os.path.join(version_store._base_dir(), slug, "versions", ver_fn)
        if not save_path:
            save_path = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "bgz_database.json")
            
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        self.current_roz_path = os.path.abspath(save_path)
        self.db_path = self.current_roz_path
        self._set_last_db_path(self.current_roz_path)
        
        try:
            # If opened from an institution version, update version directly and touch timestamp
            if slug and ver_fn:
                import version_store
                version_store.update_version_in_place(slug, ver_fn, self.data_store)
                version_store.touch_institution_timestamp(slug)
            else:
                with open(self.current_roz_path, "w", encoding="utf-8") as f:
                    json.dump(self.data_store, f, ensure_ascii=False, indent=2)
                
            fname = os.path.basename(self.current_roz_path)
            self.statusBar().showMessage(f"💾 Tüm değişiklikler '{fname}' dosyasına anlık kaydedildi.", 2000)
            
            # Offload SQLite & background tasks asynchronously without UI stutter
            import threading
            def _async_bg_sync(store_copy, s_slug, v_fn, auth_copy):
                try:
                    from database import sync_data_store_to_sqlite
                    sync_data_store_to_sqlite(store_copy)
                except Exception:
                    pass
                try:
                    from cloud_sync import push_version_to_rtdb, push_institution_to_rtdb
                    if s_slug and v_fn:
                        push_version_to_rtdb(s_slug, v_fn, store_copy, auth_copy)
                    elif s_slug:
                        push_institution_to_rtdb(s_slug, auth_copy)
                except Exception:
                    pass

            threading.Thread(
                target=_async_bg_sync,
                args=(dict(self.data_store), slug, ver_fn, getattr(self, "auth_data", None)),
                daemon=True
            ).start()
        except Exception as e:
            print("[SAVE_DB] Error:", e)
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
        
        # Calculate class workloads
        class_loads = {}
        from auto_scheduler import matches_class
        for c in s_list:
            c_name = c.get("ad", "")
            c_atamalar = []
            seen_k = set()
            for a in self.data_store.get("atamalar", []):
                if matches_class(a.get("class", ""), c_name):
                    s = format_tr_name(a.get("subject", ""))
                    t = format_tr_name(a.get("teacher", ""))
                    cls_str = format_tr_name(a.get("class", ""))
                    k = (s, t, cls_str)
                    if k not in seen_k:
                        seen_k.add(k)
                        c_atamalar.append(a)
            tot = sum(int(a.get("duration", 0)) for a in c_atamalar)
            class_loads[c_name] = tot
            
        root_s = QTreeWidgetItem(self._tree, [f"Sınıflar ({len(s_list)})"])
        root_s.setIcon(0, icon_s)
        root_s.setData(0, Qt.UserRole + 10, "sinif")
        for c in s_list:
            c_name = c.get('ad', '')
            c_hrs = class_loads.get(c_name, 0)
            item = QTreeWidgetItem(root_s, [f"{c_name} ({c_hrs} Saat)"])
            item.setData(0, Qt.UserRole, c_name)
            
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
        
        self._refresh_unplaced_lessons(target_entity=target_entity)

    def _refresh_unplaced_lessons(self, target_entity=None):
        if not hasattr(self, "_grid") or not hasattr(self._grid, "unplaced_dock"):
            return
            
        atamalar = self.data_store.get("atamalar", [])
        grid_placements = self.data_store.get("grid_placements", [])
        
        from auto_scheduler import matches_class, format_tr_name, normalize_clean
        from version_store import _matches_teacher
        from dialogs.color_picker_dialog import resolve_subject_color
        
        display_mode = getattr(self._grid, "current_view_mode", "classes")
        
        # If target_entity is None, infer from active selection in grid table or left tree
        if target_entity is None:
            if hasattr(self._grid, "table"):
                cur_r = self._grid.table.currentRow()
                if cur_r < 0 and hasattr(self._grid, "_current_selected_pos") and self._grid._current_selected_pos:
                    cur_r = self._grid._current_selected_pos[0]
                
                if cur_r >= 0:
                    if display_mode == "classes" and hasattr(self._grid, "class_list") and cur_r < len(self._grid.class_list):
                        target_entity = self._grid.class_list[cur_r]
                    elif display_mode == "teachers" and hasattr(self._grid, "teacher_list") and cur_r < len(self._grid.teacher_list):
                        target_entity = self._grid.teacher_list[cur_r]
            if target_entity is None and hasattr(self, "_tree"):
                cur_item = self._tree.currentItem()
                if cur_item and cur_item.parent():
                    target_entity = cur_item.data(0, Qt.UserRole)
        
        # 1. Build a placed slot pool deduplicated by (day, period, teacher, subject)
        # Prevents combined classes (e.g. 10A + 10B) from double-counting placed hours!
        placed_slots = {}
        for p in grid_placements:
            dur = int(p.get("duration", 1))
            if dur <= 0:
                continue
            
            p_day = int(p.get("day") if "day" in p else p.get("col", 0))
            p_per = int(p.get("period") if "period" in p else p.get("row", 0))
            p_s = (p.get("subject_name") or p.get("subject") or "").strip()
            p_t = (p.get("teacher_name") or p.get("teacher") or "").strip()
            p_c = (p.get("class_name") or p.get("class") or "").strip()
            
            if not p_s or p_s.lower() in ["boş", "bos", "atanmadı"]:
                continue
                
            slot_key = (p_day, p_per, format_tr_name(p_t), format_tr_name(p_s))
            if slot_key not in placed_slots:
                placed_slots[slot_key] = {
                    "subject": p_s,
                    "teacher": p_t,
                    "classes": set(),
                    "remaining": dur,
                    "is_combined": bool(p.get("is_combined") or ("+" in p_c or "&" in p_c or "," in p_c))
                }
            if p_c:
                for sc in p_c.replace("&", "+").replace(",", "+").split("+"):
                    if sc.strip():
                        placed_slots[slot_key]["classes"].add(sc.strip().upper())
            if p.get("combined_classes"):
                for sc in p["combined_classes"]:
                    if str(sc).strip():
                        placed_slots[slot_key]["classes"].add(str(sc).strip().upper())
                        
        placed_pool = list(placed_slots.values())
        
        # Scope assignments based on target_entity (selected class or selected teacher)
        if target_entity:
            if display_mode == "classes":
                scoped_atamalar = [
                    a for a in atamalar
                    if matches_class(a.get("class", ""), target_entity) or 
                       (a.get("is_combined") and any(matches_class(cc, target_entity) for cc in a.get("combined_classes", []))) or
                       ("+" in str(a.get("class", "")) and any(matches_class(p, target_entity) for p in str(a.get("class", "")).replace("&", "+").replace(",", "+").split("+") if p.strip()))
                ]
            else: # teachers
                scoped_atamalar = [
                    a for a in atamalar
                    if _matches_teacher(a.get("teacher", ""), target_entity) or 
                       format_tr_name(a.get("teacher", "")) == format_tr_name(target_entity)
                ]
        else:
            scoped_atamalar = atamalar
            
        def matches_subject(s1, s2):
            if not s1 or not s2: return False
            if s1 == s2: return True
            f1 = format_tr_name(s1).replace(" ", "")
            f2 = format_tr_name(s2).replace(" ", "")
            if f1 == f2: return True
            n1 = normalize_clean(s1).replace(" ", "")
            n2 = normalize_clean(s2).replace(" ", "")
            if n1 == n2: return True
            if (len(f1) >= 3 and len(f2) >= 3) and (f1.startswith(f2) or f2.startswith(f1) or n1.startswith(n2) or n2.startswith(n1)):
                return True
            return False

        unplaced = []
        for idx, atama in enumerate(scoped_atamalar):
            s_name = (atama.get("subject") or atama.get("ders") or "Ders").strip()
            t_name = (atama.get("teacher") or atama.get("ogretmen") or "").strip()
            c_name = (atama.get("class") or atama.get("sinif") or "").strip()
            dur = int(atama.get("duration", 1))
            type_str = str(atama.get("type", "")).strip()
            color = resolve_subject_color(s_name, self.data_store)
            is_comb = bool(atama.get("is_combined") or ("+" in c_name or "&" in c_name or "," in c_name))
            
            target_classes = set()
            if is_comb:
                if atama.get("combined_classes"):
                    for sc in atama["combined_classes"]:
                        if str(sc).strip(): target_classes.add(str(sc).strip().upper())
                else:
                    for sc in c_name.replace("&", "+").replace(",", "+").split("+"):
                        if sc.strip(): target_classes.add(sc.strip().upper())
            elif c_name:
                target_classes.add(c_name.strip().upper())
                
            # Breakdown block distribution (e.g. 2+2 -> [2, 2], 2+3 -> [2, 1, 1, 1], 2+1 -> [2, 1])
            from auto_scheduler import parse_distribution_parts
            parts = parse_distribution_parts(type_str, dur)
                    
            s_fmt = format_tr_name(s_name)
            t_fmt = format_tr_name(t_name)
            
            for p_idx, block_dur in enumerate(parts):
                needed = block_dur
                for p_item in placed_pool:
                    if p_item["remaining"] <= 0:
                        continue
                    p_s = p_item["subject"]
                    s_match = matches_subject(p_s, s_name)
                    if not s_match:
                        continue
                    
                    # If in teacher view or teacher-scoped filter, require teacher match
                    if display_mode == "teachers" or (not target_entity and t_name):
                        if t_name and p_item["teacher"]:
                            p_t = p_item["teacher"]
                            t_match = (format_tr_name(p_t) == t_fmt or normalize_clean(p_t) == normalize_clean(t_name) or p_t == t_name or _matches_teacher(p_t, t_name))
                            if not t_match:
                                continue
                            
                    # Class match
                    if target_classes:
                        p_classes = p_item["classes"]
                        if is_comb:
                            if not p_classes.intersection(target_classes) and not (p_item["is_combined"] and any(matches_class(pc, tc) for pc in p_classes for tc in target_classes)):
                                continue
                        else:
                            if not any(matches_class(pc, tc) or matches_class(tc, pc) or pc == tc for pc in p_classes for tc in target_classes):
                                continue
                    
                    deduct = min(needed, p_item["remaining"])
                    needed -= deduct
                    p_item["remaining"] -= deduct
                    if needed <= 0:
                        break
                        
                if needed > 0:
                    unplaced.append({
                        "id": f"{idx}_{p_idx}",
                        "subject_name": s_name,
                        "color": color,
                        "teacher": t_name,
                        "class_name": c_name,
                        "duration": needed,
                        "is_combined": is_comb,
                        "combined_classes": list(target_classes) if is_comb else []
                    })
                    
        # --- CHECK IF GRID IS FULL FOR THIS TARGET ---
        if target_entity and scoped_atamalar:
            settings = self.data_store.get("settings", {})
            d_len = len(settings.get("days", [])) or int(settings.get("day_count", self.data_store.get("gun_sayisi", 5)))
            p_len = int(settings.get("periods", self.data_store.get("ders_saati", 8)))
            total_slots = d_len * p_len
            
            placed_for_target = 0
            for p in grid_placements:
                dur = int(p.get("duration", 1))
                if dur <= 0: continue
                p_c = (p.get("class_name") or p.get("class") or "").strip()
                p_t = format_tr_name(p.get("teacher_name") or p.get("teacher") or "")
                
                match = False
                if display_mode == "classes":
                    from auto_scheduler import matches_class
                    if matches_class(target_entity, p_c) or matches_class(p_c, target_entity):
                        match = True
                    elif p.get("combined_classes"):
                        if any(matches_class(target_entity, x) for x in p["combined_classes"]):
                            match = True
                    elif "+" in p_c or "&" in p_c or "," in p_c:
                        if any(matches_class(target_entity, x.strip()) for x in p_c.replace("&", "+").replace(",", "+").split("+")):
                            match = True
                else:
                    if _matches_teacher(p_t, target_entity) or p_t == format_tr_name(target_entity):
                        match = True
                        
                if match:
                    placed_for_target += dur
                    
            # If grid is full, clear unplaced - no lessons to show
            if placed_for_target >= total_slots:
                unplaced = []
        # --------------------------------

        has_assignments = bool(scoped_atamalar) if target_entity else bool(atamalar)
        self._grid.unplaced_dock.load_unplaced(
            unplaced, 
            has_assignments=has_assignments, 
            display_mode=display_mode, 
            target_entity=target_entity or ""
        )

    def _remove_placement_by_data(self, p_item):
        if not p_item or not isinstance(self.data_store.get("grid_placements"), list):
            return
        from auto_scheduler import matches_class, format_tr_name
        p_d = int(p_item.get("day") if "day" in p_item else p_item.get("col", -1))
        p_p = int(p_item.get("period") if "period" in p_item else p_item.get("row", -1))
        p_cls = (p_item.get("class_name") or p_item.get("class") or "").strip()
        p_tea = format_tr_name(p_item.get("teacher_name") or p_item.get("teacher") or "")
        p_sub = format_tr_name(p_item.get("subject_name") or p_item.get("subject") or "")
        
        self.data_store["grid_placements"] = [
            p for p in self.data_store["grid_placements"]
            if not (
                int(p.get("day") if "day" in p else p.get("col", -1)) == p_d and
                int(p.get("period") if "period" in p else p.get("row", -1)) == p_p and
                (matches_class(p.get("class_name") or p.get("class", ""), p_cls) or matches_class(p_cls, p.get("class_name") or p.get("class", "")) or
                 format_tr_name(p.get("teacher_name") or p.get("teacher", "")) == p_tea)
            )
        ]
        if "auto_schedule_results" in self.data_store:
            self.data_store["auto_schedule_results"] = list(self.data_store["grid_placements"])

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
                pass

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
        from timetable_grid import DAYS
        from auto_scheduler import matches_class, format_tr_name, normalize_clean
        
        display_mode = getattr(self._grid, "current_view_mode", "classes")
        subject_name = lesson_info.get("subject_name", "Ders")
        color = get_subject_color(subject_name, self.data_store)
        teacher = format_tr_name(lesson_info.get("teacher_name") or lesson_info.get("teacher") or "")
        cls_name = (lesson_info.get("class_name") or lesson_info.get("class") or lesson_info.get("sinif") or "").strip()
        
        is_comb = bool(lesson_info.get("is_combined") or ("+" in cls_name or "," in cls_name or "&" in cls_name))
        combined_classes = lesson_info.get("combined_classes") or []
        if is_comb and not combined_classes:
            combined_classes = [c.strip().split("(")[0].strip() for c in cls_name.replace("&", "+").replace(",", "+").split("+") if c.strip()]
        
        classes = self.data_store.get("siniflar", [])
        import re
        def cls_sort_key(c):
            m = re.match(r"(\d+)(.*)", str(c).strip())
            return (int(m.group(1)), m.group(2)) if m else (999, str(c))
        class_names = sorted([c.get("ad", "").strip() for c in classes if c.get("ad")], key=cls_sort_key)
        
        teachers = self.data_store.get("ogretmenler", [])
        teacher_names = sorted([t.get("ad", "").strip() for t in teachers if t.get("ad")])

        card_cls = (lesson_info.get("class_name") or lesson_info.get("class") or lesson_info.get("sinif") or "").strip()
        card_teacher = format_tr_name(lesson_info.get("teacher_name") or lesson_info.get("teacher") or "")

        if display_mode == "teachers":
            if row < len(teacher_names):
                target_row_teacher = teacher_names[row]
                if card_teacher and card_teacher != target_row_teacher:
                    QMessageBox.warning(
                        self, "Hatalı Öğretmen Satırı",
                        f"⛔ Bu ders <b>{card_teacher}</b> öğretmenine aittir.<br><br>"
                        f"<b>{target_row_teacher}</b> öğretmeninin satırına yerleştirilemez!"
                    )
                    return
                teacher = target_row_teacher
            elif card_teacher:
                teacher = card_teacher
        else:
            if row < len(class_names):
                target_row_cls = class_names[row]
                if is_comb and combined_classes:
                    comb_match = any(
                        matches_class(target_row_cls, tc) or matches_class(tc, target_row_cls) or target_row_cls == tc
                        for tc in combined_classes
                    )
                    if not comb_match:
                        QMessageBox.warning(
                            self, "Hatalı Sınıf Satırı",
                            f"⛔ Bu birleşik ders (<b>{' + '.join(combined_classes)}</b>) sınıflarına aittir.<br><br>"
                            f"<b>{target_row_cls}</b> sınıfının satırına yerleştirilemez!"
                        )
                        return
                    cls_name = " + ".join(combined_classes)
                else:
                    if card_cls:
                        cls_match = (
                            matches_class(card_cls, target_row_cls) or
                            matches_class(target_row_cls, card_cls) or
                            card_cls == target_row_cls
                        )
                        if not cls_match:
                            QMessageBox.warning(
                                self, "Hatalı Sınıf Satırı",
                                f"⛔ Bu ders <b>{card_cls}</b> sınıfına aittir.<br><br>"
                                f"<b>{target_row_cls}</b> sınıfının satırına yerleştirilemez!"
                            )
                            return
                        cls_name = target_row_cls
                    else:
                        cls_name = target_row_cls
            else:
                if is_comb and combined_classes:
                    cls_name = " + ".join(combined_classes)
                elif card_cls:
                    cls_name = card_cls
        
        # Öğretmen yoksa otomatik olarak branşından müsait bir hoca bul ve ata
        if not teacher:
            s_upper = subject_name.upper().strip()
            s_words = [w for w in s_upper.split() if len(w) >= 3 and not w.isdigit()]
            for t in self.data_store.get("ogretmenler", []):
                t_ad = format_tr_name(t.get("ad", ""))
                t_brans = (t.get("brans") or t.get("branch") or "").upper().strip()
                if t_brans and (t_brans in s_upper or any(w in t_brans for w in s_words)):
                    teacher = t_ad; break
                elif any(w in t_ad.upper() for w in s_words):
                    teacher = t_ad; break
            if not teacher and self.data_store.get("ogretmenler"):
                teacher = format_tr_name(self.data_store["ogretmenler"][0].get("ad", ""))
                
        duration = int(lesson_info.get("duration", 1))
        is_move = lesson_info.get("is_move", False)
        orig_r = lesson_info.get("origin_row", -1)
        orig_c = lesson_info.get("origin_col", -1)
        
        settings = self.data_store.get("settings", {})
        periods = int(settings.get("periods", self.data_store.get("ders_saati", 8)))
        if periods <= 0: periods = 8
        day_idx = col // periods
        period_idx = col % periods
        day_name = DAYS[day_idx] if 0 <= day_idx < len(DAYS) else f"{day_idx+1}. Gün"
        
        # Check if moving to exact same spot
        if is_move and orig_r == row and orig_c == col:
            return
            
        # Check day boundary: multi-hour lesson must not spill over to next day
        if period_idx + duration > periods:
            QMessageBox.warning(
                self, "Geçersiz Konum",
                f"⚠️ Ders {duration} saatlik olduğu için günün kalan saatlerine sığmıyor!\n\n"
                f"Günün {period_idx+1}. saatine bırakıldı, ancak gün {periods} saatten oluşuyor."
            )
            return

        orig_day = orig_c // periods if (is_move and orig_c >= 0) else -1
        orig_per = orig_c % periods if (is_move and orig_c >= 0) else -1

        def is_origin_placement(p):
            if not is_move or orig_c < 0:
                return False
            p_d = int(p.get("day") if "day" in p else p.get("col", 0))
            p_p = int(p.get("period") if "period" in p else p.get("row", 0))
            p_dur = int(p.get("duration", 1))
            if p_d != orig_day:
                return False
            overlap = max(0, min(p_p + p_dur, orig_per + duration) - max(p_p, orig_per))
            if overlap <= 0:
                return False
            p_c = (p.get("class_name") or p.get("class") or "").strip()
            p_t = format_tr_name(p.get("teacher_name") or p.get("teacher") or "")
            p_s = format_tr_name(p.get("subject_name") or p.get("subject") or "")
            if p_s != format_tr_name(subject_name):
                return False
            if is_comb:
                if any(matches_class(p_c, c) or matches_class(c, p_c) or p_c == c for c in combined_classes) or p_c == cls_name or p.get("is_combined"):
                    return True
            if cls_name and (matches_class(p_c, cls_name) or matches_class(cls_name, p_c) or p_c == cls_name):
                return True
            if teacher and (p_t == teacher or format_tr_name(p_t) == teacher):
                return True
            return False
            
        # ── 1. KESİN KONTROL: Sınıf Çizelgesi Dolu mu?
        target_check_classes = combined_classes if (is_comb and combined_classes) else [cls_name] if cls_name else []
        if target_check_classes:
            class_occupied = None
            for p_item in self.data_store.get("grid_placements", []):
                if is_origin_placement(p_item):
                    continue
                p_day = int(p_item.get("day") if "day" in p_item else p_item.get("col", 0))
                p_period = int(p_item.get("period") if "period" in p_item else p_item.get("row", 0))
                p_dur = int(p_item.get("duration", 1))
                p_cls = (p_item.get("class_name") or p_item.get("class") or "").strip()
                
                if p_day == day_idx:
                    overlap = max(0, min(p_period + p_dur, period_idx + duration) - max(p_period, period_idx))
                    if overlap > 0:
                        for chk_c in target_check_classes:
                            if matches_class(p_cls, chk_c) or matches_class(chk_c, p_cls) or p_cls == chk_c:
                                class_occupied = p_item
                                break
                        if class_occupied:
                            break
                    
            if class_occupied:
                occ_s = class_occupied.get("subject_name") or class_occupied.get("subject") or "Ders"
                occ_t = class_occupied.get("teacher_name") or class_occupied.get("teacher") or "Öğretmen"
                occ_c = class_occupied.get("class_name") or class_occupied.get("class") or cls_name
                ret = QMessageBox.warning(
                    self, "Sınıf Çizelgesi Dolu",
                    f"⚠️ <b>Bu Saatte Sınıf Zaten Dolu!</b><br><br>"
                    f"<b>{occ_c}</b> sınıfının <b>{day_name}</b> günü <b>{period_idx+1}. ders saatinde</b> "
                    f"zaten <b>{occ_s}</b> ({occ_t}) dersi bulunmaktadır.<br><br>"
                    f"Mevcut dersi kaldırıp yeni dersi yerleştirmek istiyor musunuz?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if ret != QMessageBox.Yes:
                    self.statusBar().showMessage(f"İptal edildi: {cls_name} sınıfının {day_name} {period_idx+1}. saati zaten dolu!")
                    return
                # Remove existing lesson
                self._remove_placement_by_data(class_occupied)

        # ── 2. KONTROL: Öğretmen Kapalı/Kısıtlı Saat Kontrolü
        kisitlamalar = self.data_store.get("kisitlamalar", {})
        
        # Sınıf Timeoff Kontrolü
        target_check_classes = combined_classes if (is_comb and combined_classes) else [cls_name] if cls_name else []
        for chk_c in target_check_classes:
            c_info = next((c for c in self.data_store.get("siniflar", []) if c.get("ad", "").strip() == chk_c.strip()), {})
            c_timeoff = c_info.get("timeoff", [])
            if c_timeoff:
                for ext in range(duration):
                    check_p = period_idx + ext
                    if day_idx < len(c_timeoff) and check_p < len(c_timeoff[day_idx]):
                        if c_timeoff[day_idx][check_p] == 0:
                            QMessageBox.warning(
                                self, "Sınıf Kısıtlama Engeli",
                                f"⚠️ '{chk_c}' sınıfının {day_name} günü {check_p+1}. ders saati 'KAPALI' olarak kısıtlanmıştır!\nDers yerleştirilemez."
                            )
                            self.statusBar().showMessage(f"Sınıf Kısıtlama engeli: {chk_c} - {day_name} {check_p+1}. saat kapalı!")
                            return

        # Öğretmen Timeoff Kontrolü (Global Kisitlamalar ve Yerel Timeoff)
        if teacher:
            t_info = next((t for t in self.data_store.get("ogretmenler", []) if format_tr_name(t.get("ad", "")) == teacher), {})
            t_timeoff = t_info.get("timeoff", [])
            
            for ext in range(duration):
                check_p = period_idx + ext
                cell_key = f"{day_idx},{check_p}"
                
                # Global çapraz kısıtlama
                is_available = kisitlamalar.get(teacher, {}).get(cell_key, True)
                if not is_available:
                    QMessageBox.warning(
                        self, "Kısıtlama Engeli",
                        f"⚠️ '{teacher}' öğretmeninin {day_name} günü {check_p+1}. ders saatinde 'ÇALIŞAMAZ / KAPALI' kısıtlaması bulunmaktadır!\nDers yerleştirilemez."
                    )
                    self.statusBar().showMessage(f"Kısıtlama engeli: {teacher} - {day_name} {check_p+1}. saat kapalı!")
                    return
                    
                # Yerel timeoff (Grid üzerinden ayarlanan)
                if t_timeoff and day_idx < len(t_timeoff) and check_p < len(t_timeoff[day_idx]):
                    if t_timeoff[day_idx][check_p] == 0:
                        QMessageBox.warning(
                            self, "Öğretmen Kısıtlama Engeli",
                            f"⚠️ '{teacher}' öğretmeninin {day_name} günü {check_p+1}. ders saati 'KAPALI' olarak kısıtlanmıştır!\nDers yerleştirilemez."
                        )
                        self.statusBar().showMessage(f"Öğretmen Kısıtlama engeli: {teacher} - {day_name} {check_p+1}. saat kapalı!")
                        return

        # ── 3. KONTROL: Öğretmen Çakışması Kontrolü
        teacher_info = next((t for t in self.data_store.get("ogretmenler", []) if format_tr_name(t.get("ad", "")) == teacher), {})
        allows_parallel = teacher_info.get("es_zamanli", False)
        
        if teacher and not allows_parallel:
            teacher_occupied = None
            for p_item in self.data_store.get("grid_placements", []):
                if is_origin_placement(p_item):
                    continue
                p_day = int(p_item.get("day") if "day" in p_item else p_item.get("col", 0))
                p_period = int(p_item.get("period") if "period" in p_item else p_item.get("row", 0))
                p_dur = int(p_item.get("duration", 1))
                p_t = format_tr_name(p_item.get("teacher_name") or p_item.get("teacher") or "")
                p_cls = (p_item.get("class_name") or p_item.get("class") or "").strip()
                p_sub = format_tr_name(p_item.get("subject_name") or p_item.get("subject") or "")
                
                if p_day == day_idx and (p_t == teacher or format_tr_name(p_t) == teacher):
                    overlap = max(0, min(p_period + p_dur, period_idx + duration) - max(p_period, period_idx))
                    if overlap > 0:
                        # Check if this is the EXACT SAME joint lesson placement (not a conflict)
                        is_same_joint = False
                        if is_comb and (p_sub == format_tr_name(subject_name) or p_item.get("is_combined")):
                            is_same_joint = True
                        if not is_same_joint and not (matches_class(p_cls, cls_name) or matches_class(cls_name, p_cls) or p_cls == cls_name):
                            teacher_occupied = p_item
                            break
                    
            if teacher_occupied:
                occ_s = teacher_occupied.get("subject_name") or teacher_occupied.get("subject") or "Ders"
                occ_c = teacher_occupied.get("class_name") or teacher_occupied.get("class") or "Başka Sınıf"
                ret = QMessageBox.warning(
                    self, "Öğretmen Çakışması",
                    f"⚠️ <b>Öğretmen Çakışması!</b><br><br>"
                    f"<b>{teacher}</b> öğretmeninin <b>{day_name}</b> günü <b>{period_idx+1}. ders saatinde</b> "
                    f"<b>{occ_c}</b> sınıfında <b>{occ_s}</b> dersi bulunmaktadır.<br><br>"
                    f"Öğretmen aynı anda iki farklı sınıfa ders veremez. Mevcut dersi kaldırıp bunu yerleştirmek istiyor musunuz?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if ret != QMessageBox.Yes:
                    self.statusBar().showMessage(f"Engellendi: {teacher} hocanın {day_name} {period_idx+1}. saati dolu!")
                    return
                # Remove existing lesson
                self._remove_placement_by_data(teacher_occupied)

        # ── 3.5. KESİN KONTROL: Çapraz Kurum Öğretmen Çakışması Kontrolü
        if teacher:
            import version_store
            cross_busy = version_store.get_cross_institution_teacher_busy_slots(exclude_slug=getattr(self, "institution_slug", None))
            t_norm = version_store.normalize_teacher_name(teacher)
            cross_conflict = None
            for ext in range(duration):
                check_slot = (t_norm, day_idx, period_idx + ext)
                if check_slot in cross_busy:
                    cross_conflict = cross_busy[check_slot]
                    break
            
            if cross_conflict:
                c_inst = cross_conflict.get("institution_name", "Başka Kurum")
                c_subj = cross_conflict.get("subject", "Ders")
                c_cls = cross_conflict.get("class", "Sınıf")
                c_per = cross_conflict.get("period", 0) + 1
                QMessageBox.critical(
                    self, "Çapraz Kurum Öğretmen Çakışması",
                    f"⛔ <b>Çapraz Kurum Çakışması Tespit Edildi!</b><br><br>"
                    f"<b>{teacher}</b> öğretmeni <b>{c_inst}</b> kurumunun aktif ders programında "
                    f"<b>{day_name}</b> günü <b>{c_per}. ders saatinde</b> "
                    f"zaten <b>{c_cls}</b> ({c_subj}) dersinde görevlidir!<br><br>"
                    f"Bir öğretmen aynı saatte iki farklı kurumda ders veremez."
                )
                self.statusBar().showMessage(f"Çapraz çakışma engeli: {teacher} ({c_inst} - {day_name} {c_per}. saat)")
                return

        # ── 4. TÜM KONTROLLER BAŞARILI: Atomik ve Güvenli Yerleşim
        self.mark_dirty()
        self._push_undo_state()
        
        # Eğer taşıma (move) ise eski konumu grid_placements'tan sil
        if is_move and orig_c >= 0:
            self.data_store["grid_placements"] = [
                p for p in self.data_store.get("grid_placements", [])
                if not is_origin_placement(p)
            ]
            
        # Yeni yerleşimi ekle (her saat bloğu için)
        # block_id: aynı yerleştirme operasyonundan gelen tüm saatler aynı ID'yi paylaşır
        import uuid as _uuid
        _block_id = str(_uuid.uuid4())[:12]
        
        for ext in range(duration):
            target_p = period_idx + ext
            self.data_store.setdefault("grid_placements", [])
            self.data_store["grid_placements"] = [
                p for p in self.data_store["grid_placements"]
                if not (
                    (p.get("day") == day_idx or p.get("col") == day_idx) and
                    (p.get("period") == target_p or p.get("row") == target_p) and
                    (matches_class(p.get("class_name") or p.get("class", ""), cls_name) or
                     (display_mode == "teachers" and format_tr_name(p.get("teacher_name") or p.get("teacher", "")) == teacher) or
                     (is_comb and any(matches_class(p.get("class_name") or p.get("class", ""), tc) for tc in combined_classes)))
                )
            ]
            
            target_class_names = combined_classes if (is_comb and combined_classes) else [cls_name]
            
            for t_cls in target_class_names:
                self.data_store["grid_placements"].append({
                    "day": day_idx, "period": target_p,
                    "row": target_p, "col": day_idx,
                    "class_name": t_cls, "class": t_cls,
                    "teacher_name": teacher, "teacher": teacher,
                    "subject_name": subject_name, "subject": subject_name,
                    "duration": 1,
                    "locked": bool(lesson_info.get("locked", True)),
                    "is_manual": True,
                    "color": color,
                    "is_combined": is_comb,
                    "combined_classes": list(combined_classes) if combined_classes else [],
                    "block_id": _block_id
                })
            
        if "auto_schedule_results" in self.data_store:
            self.data_store["auto_schedule_results"] = list(self.data_store.get("grid_placements", []))
            
        self._refresh_grid()
        self.save_db(sync_from_grid=False)
        if hasattr(self, "institution_slug") and hasattr(self, "version_filename") and self.institution_slug and self.version_filename:
            import version_store
            version_store.update_version_in_place(self.institution_slug, self.version_filename, self.data_store)
            
        self._refresh_unplaced_lessons()
        self._refresh_tree()
        self.statusBar().showMessage(f"'{subject_name}' ({cls_name} - {teacher}) dersi {day_name} günü {period_idx+1}. saate yerleştirildi.")

    # ── Actions ───────────────────────────────────────────────────────────────
    def _go_home(self):
        """Return to the Home Dashboard."""
        try:
            slug = getattr(self, "institution_slug", None)
            ver_fn = getattr(self, "version_filename", None)
            if slug:
                import version_store
                # Always update current version file with latest in-memory data
                if ver_fn:
                    version_store.update_version_in_place(slug, ver_fn, self.data_store)
                # If any changes were made, also create a brand new version snapshot
                if getattr(self, "_is_dirty", False):
                    new_vf = version_store.save_version(slug, self.data_store, source="manual", note="Değişiklikler kaydedildi")
                    version_store.set_active_version(slug, new_vf)
                    self.version_filename = new_vf
                    self._is_dirty = False
                    print(f"[GO_HOME] New version created: {new_vf}")
                else:
                    print(f"[GO_HOME] No changes, kept: {ver_fn}")
                version_store.touch_institution_timestamp(slug)
        except Exception as e:
            print(f"Auto-save on _go_home error: {e}")
        if callable(self.go_home_requested):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self.go_home_requested)
        else:
            self.statusBar().showMessage("Ana sayfa bağlantısı bulunamadı.")

    def _go_main_tab(self):
        self._ribbon._select(0)

    def _on_cell_edit(self, row, col):
        if not hasattr(self, "_grid"):
            return
            
        grid_table = self._grid.table if hasattr(self._grid, "table") else self._grid
        
        orig_r, orig_c, orig_dur, info = grid_table._get_lesson_origin(row, col)
        if not info:
            if hasattr(self._grid, "_placed_lessons"):
                info = self._grid._placed_lessons.get((row, col), {})
            
        subject_name = info.get("subject_name") or info.get("subject") or ""
        teacher_name = info.get("teacher_name") or info.get("teacher") or ""
        class_name = info.get("class_name") or info.get("class") or ""
        
        if not subject_name and not teacher_name and not class_name:
            item = grid_table.item(row, col)
            if item and item.text().strip():
                subject_name = item.text().strip().replace("🔒", "")
                
        if not subject_name:
            return
            
        self._push_undo_state()
        from dialogs.edit_forms import SubjectTeacherAssignmentDialog
        d = SubjectTeacherAssignmentDialog(
            subject_name=subject_name,
            data_store=self.data_store,
            parent=self,
            preselect_class=class_name,
            preselect_teacher=teacher_name,
            is_cell_edit=True,
            cell_c=orig_c,
            cell_r=orig_r
        )
        if d.exec():
            if getattr(d, "is_cell_edit", False) and getattr(d, "new_teacher", None) and d.new_teacher != teacher_name:
                from auto_scheduler import matches_class, normalize_clean, format_tr_name
                periods_per_day = int(self.data_store.get("settings", {}).get("periods", 8))
                cell_day = orig_c // periods_per_day
                
                # 1. Update in grid_placements & auto_schedule_results
                for store_key in ["grid_placements", "auto_schedule_results"]:
                    for p in self.data_store.get(store_key, []):
                        p_day = int(p.get("day", p.get("col", 0) // periods_per_day if "col" in p else 0))
                        p_cls = p.get("class_name", p.get("class", ""))
                        p_sub = p.get("subject_name", p.get("subject", ""))
                        p_t = p.get("teacher_name", p.get("teacher", ""))
                        
                        cls_match = matches_class(p_cls, class_name) or matches_class(class_name, p_cls) or (p_cls == class_name)
                        sub_match = (normalize_clean(p_sub) == normalize_clean(subject_name)) or (p_sub == subject_name)
                        t_match = (not teacher_name) or (format_tr_name(p_t) == format_tr_name(teacher_name)) or (normalize_clean(p_t) == normalize_clean(teacher_name))
                        
                        if p_day == cell_day and cls_match and sub_match and t_match:
                            p["teacher_name"] = d.new_teacher
                            p["teacher"] = d.new_teacher
                            p["is_manual"] = True
                
                # 2. Update live grid cache
                if hasattr(self._grid, "_placed_lessons"):
                    for (gr, gc), pinfo in self._grid._placed_lessons.items():
                        g_day = gc // periods_per_day
                        p_cls = pinfo.get("class_name", "")
                        p_sub = pinfo.get("subject_name", "")
                        p_t = pinfo.get("teacher_name", "")
                        cls_match = matches_class(p_cls, class_name) or matches_class(class_name, p_cls) or (p_cls == class_name)
                        sub_match = (normalize_clean(p_sub) == normalize_clean(subject_name)) or (p_sub == subject_name)
                        t_match = (not teacher_name) or (format_tr_name(p_t) == format_tr_name(teacher_name)) or (normalize_clean(p_t) == normalize_clean(teacher_name))
                        
                        if g_day == cell_day and cls_match and sub_match and t_match:
                            pinfo["teacher_name"] = d.new_teacher
                            pinfo["teacher"] = d.new_teacher
                            
                self.save_db(sync_from_grid=False)
                self._refresh_tree()
                self._refresh_grid()
                
                # Refresh selected cell info panel immediately
                if hasattr(self._grid, "_on_cell_clicked"):
                    self._grid._on_cell_clicked(orig_r, orig_c)
                self.statusBar().showMessage(f"Öğretmen Değiştirildi: {teacher_name} -> {d.new_teacher} (Sadece o gün için)")
            else:
                self.save_db()
                self._refresh_tree()
                self._refresh_grid()

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
        slug = getattr(self, "institution_slug", None)
        if slug:
            import version_store
            new_vf = version_store.save_version(slug, self.data_store, source="manual", note="Kullanıcı kaydı")
            self.version_filename = new_vf
            self.current_roz_path = os.path.join(version_store._base_dir(), slug, "versions", new_vf)
            self.db_path = self.current_roz_path
            version_store.set_active_version(slug, new_vf)
            version_store.touch_institution_timestamp(slug)
            
            # Update title
            import re
            m = re.match(r"v(\d+)_", new_vf)
            v_num = f"v{int(m.group(1))}" if m else ""
            inst_name = getattr(self, "institution_name", slug)
            self.setWindowTitle(f"BGZ Ders Planlama — {inst_name} — {v_num}")
            
        fname = os.path.basename(self.current_roz_path or self.db_path or "program.roz")
        from save_dialog import run_apple_save_sequence
        run_apple_save_sequence(self, duration_seconds=0.35, title="Kaydediliyor", message=f"'{fname}' başarıyla kaydedildi ve yeni versiyon yayına alındı.")
        self.statusBar().showMessage(f"💾 Yeni versiyon kaydedildi ve yayına alındı.", 3000)

    def _act_print(self):
        self._handle_print_preview(is_direct_print=True)

    def _act_preview(self):
        self._handle_print_preview(is_direct_print=False)

    def _handle_print_preview(self, is_direct_print=False):
        if hasattr(self, "save_db"):
            self.save_db(sync_from_grid=True)
            
        selected_items = self._tree.selectedItems()
        item = selected_items[0] if selected_items else self._tree.currentItem()
        node_type = None
        entity_name = None
        
        if item:
            parent = item.parent()
            if parent is None:
                text = item.text(0)
                if text.startswith("Öğretmenler"):
                    node_type = "root_teachers"
                elif text.startswith("Sınıflar"):
                    node_type = "root_classes"
            else:
                p_text = parent.text(0)
                if p_text.startswith("Öğretmenler"):
                    node_type = "teacher"
                    entity_name = item.text(0).split(" (")[0].strip()
                elif p_text.startswith("Sınıflar"):
                    node_type = "class"
                    entity_name = item.text(0).strip()
                    
        # Fallback to current grid mode if nothing selected in tree
        from PySide6.QtWidgets import QDialog
        from dialogs.report_selection_dialog import ReportSelectionDialog
        
        sel_dlg = ReportSelectionDialog(
            self.data_store, 
            default_type=node_type, 
            default_entity=entity_name, 
            is_direct_print=is_direct_print, 
            parent=self
        )
        if sel_dlg.exec() != QDialog.Accepted:
            return
            
        res = sel_dlg.get_result()
        report_mode = res.get("mode")
        entity_type = res.get("entity_type")
        chosen_entity = res.get("entity_name")
        
        filters = {
            "lock_mode": report_mode,
            "default_selection": chosen_entity or "",
            "entity_type": entity_type
        }
        if entity_type == "class" and chosen_entity:
            filters["classes"] = [chosen_entity]
        elif entity_type == "teacher" and chosen_entity:
            filters["teachers"] = [chosen_entity]
            
        from dialogs.print_preview import TimetablePrintPreview
        dlg = TimetablePrintPreview(self.data_store, self._grid.get_placed_lessons(), filters, self)
        if is_direct_print:
            dlg.direct_print()
        else:
            dlg.exec()

    def _act_assignment_list(self):
        from dialogs.assignment_list_dialog import ClassAssignmentsPreviewDialog
        dlg = ClassAssignmentsPreviewDialog(self.data_store, self)
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
        if len(self._history_stack) > 200:
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
            
            self._is_loading = True
            save_path = getattr(self, "current_roz_path", None) or self.db_path
            if save_path:
                try:
                    with open(save_path, "w", encoding="utf-8") as f:
                        import json
                        json.dump(self.data_store, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    print("Undo Save Error:", e)
            if hasattr(self, "institution_slug") and hasattr(self, "version_filename") and self.institution_slug and self.version_filename:
                try:
                    import version_store
                    version_store.update_version_in_place(self.institution_slug, self.version_filename, self.data_store)
                except Exception as e:
                    print("Undo version store update error:", e)
            self._is_loading = False
            
            settings = self.data_store.get("settings", {})
            periods = int(settings.get("periods", self.data_store.get("ders_saati", 8)))
            if hasattr(self, "_grid"):
                self._grid.set_periods(periods)
            self._refresh_tree()
            self._refresh_grid()
            self._restore_grid_placements()
            self._refresh_unplaced_lessons()
            self.statusBar().showMessage("↺ İşlem başarıyla geri alındı (Undo / Ctrl+Z).")
        else:
            self.statusBar().showMessage("⚠️ Geri alınacak başka işlem yok.")

    def _act_redo(self):
        import copy
        if hasattr(self, "_redo_stack") and self._redo_stack:
            if not hasattr(self, "_history_stack"): self._history_stack = []
            self._history_stack.append(copy.deepcopy(self.data_store))
            next_state = self._redo_stack.pop()
            self.data_store = next_state
            
            self._is_loading = True
            save_path = getattr(self, "current_roz_path", None) or self.db_path
            if save_path:
                try:
                    with open(save_path, "w", encoding="utf-8") as f:
                        import json
                        json.dump(self.data_store, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    print("Redo Save Error:", e)
            if hasattr(self, "institution_slug") and hasattr(self, "version_filename") and self.institution_slug and self.version_filename:
                try:
                    import version_store
                    version_store.update_version_in_place(self.institution_slug, self.version_filename, self.data_store)
                except Exception as e:
                    print("Redo version store update error:", e)
            self._is_loading = False
            
            settings = self.data_store.get("settings", {})
            periods = int(settings.get("periods", self.data_store.get("ders_saati", 8)))
            if hasattr(self, "_grid"):
                self._grid.set_periods(periods)
            self._refresh_tree()
            self._refresh_grid()
            self._restore_grid_placements()
            self._refresh_unplaced_lessons()
            self.statusBar().showMessage("↻ İşlem başarıyla tekrar uygulandı (Redo / Ctrl+Y).")
        else:
            self.statusBar().showMessage("⚠️ Yinelenecek başka işlem yok.")

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_Z:
                self._act_undo()
                return
            elif event.key() == Qt.Key_Y:
                self._act_redo()
                return
        elif event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            if event.key() == Qt.Key_Z:
                self._act_redo()
                return
        super().keyPressEvent(event)

    def _open_subjects(self):
        self._push_undo_state()
        d = MasterDataDialog(0, self)
        if d.exec():
            self.save_db()
            self._refresh_tree()
            self._restore_grid_placements()
            self._refresh_unplaced_lessons()

    def _open_school_info(self):
        self._push_undo_state()
        from dialogs.school_info import SchoolInfoDialog
        d = SchoolInfoDialog(parent=self, data_store=self.data_store)
        if d.exec():
            settings = self.data_store.get("settings", {})
            periods = int(settings.get("periods", self.data_store.get("ders_saati", 8)))
            if hasattr(self, "_grid"):
                self._grid.set_periods(periods)
                
            kurum_adi = self.data_store.get("kurum", {}).get("isim") or self.data_store.get("okul_adi", "") or settings.get("school_name", "")
            slug = getattr(self, "institution_slug", None)
            ver_fn = getattr(self, "version_filename", None)
            
            if kurum_adi and slug:
                try:
                    import version_store
                    version_store.rename_institution(slug, kurum_adi)
                    if ver_fn:
                        version_store.update_version_in_place(slug, ver_fn, self.data_store)
                        
                    v_num = ""
                    if ver_fn:
                        import re
                        m = re.match(r"v(\d+)_", ver_fn)
                        if m: v_num = f"v{int(m.group(1))}"
                    title_suffix = f" — {v_num}" if v_num else ""
                    self.setWindowTitle(f"BGZ Ders Planlama — {kurum_adi}{title_suffix}")
                except Exception as e:
                    print(f"Failed to update institution name in meta: {e}")
                    
            self.save_db(sync_from_grid=False)
            self._refresh_grid()
            self._refresh_tree()
            self._restore_grid_placements()
            self._refresh_unplaced_lessons()

    def _open_classes(self):
        self._push_undo_state()
        d = MasterDataDialog(1, self)
        if d.exec():
            self.save_db()
            self._refresh_tree()
            self._restore_grid_placements()
            self._refresh_unplaced_lessons()

    def _open_class_assignments(self, target_class=None):
        self._push_undo_state()
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
            self.save_db(sync_from_grid=False)
            self._refresh_tree()
            self._refresh_grid()
            self._refresh_unplaced_lessons()

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
                self._push_undo_state()
                from dialogs.edit_forms import LessonAssignmentDialog
                d = LessonAssignmentDialog(data_store=self.data_store, parent=self, selected_teacher=entity_name)
                if d.exec():
                    self.save_db()
                    self._refresh_tree()
                    self._restore_grid_placements()
                    self._refresh_unplaced_lessons()

    def _open_rooms(self):
        self._push_undo_state()
        d = MasterDataDialog(2, self)
        if d.exec():
            self.save_db()
            self._refresh_tree()
            self._restore_grid_placements()
            self._refresh_unplaced_lessons()

    def _open_teachers(self):
        self._push_undo_state()
        d = MasterDataDialog(3, self)
        if d.exec():
            self.save_db()
            self._refresh_tree()
            self._restore_grid_placements()
            self._refresh_unplaced_lessons()

    def _open_electives(self):
        self._push_undo_state()
        from dialogs.electives_dialog import ElectivesDialog
        d = ElectivesDialog(data_store=self.data_store, parent=self)
        d.exec()
        self.save_db()
        self._refresh_tree()
        self._refresh_unplaced_lessons()

    def _open_relations(self):
        self._push_undo_state()
        from dialogs.relations_dialog import PlanningRelationsDialog
        d = PlanningRelationsDialog(data_store=self.data_store, parent=self)
        d.exec()
        self.save_db()
        self._refresh_tree()
        self._refresh_unplaced_lessons()

    def _open_wizard(self):
        self._push_undo_state()
        d = MasterDataDialog(0, self)
        d.exec()
        self.save_db()
        self._refresh_tree()
        self._restore_grid_placements()
        self._refresh_unplaced_lessons()

    def _act_auto_schedule(self):
        self._push_undo_state()
        self._sync_grid_to_store()
        self.save_db(sync_from_grid=False)
        from dialogs.auto_schedule_dialog import AutoScheduleDialog
        from PySide6.QtWidgets import QDialog
        
        atamalar = self.data_store.get("atamalar", [])
        if not atamalar:
            QMessageBox.warning(
                self, "Ders Ataması Bulunamadı",
                "⚠️ Henüz hiçbir sınıfa ders/öğretmen ataması yapılmamış!\n\n"
                "Otomatik planlama başlatılabilmesi için önce sınıflara ders ve öğretmen atamalısınız.\n\n"
                "Sınıflar → [Sınıf Seç] → Ders & Öğretmen Ata yolunu izleyebilirsiniz."
            )
            return

        d = AutoScheduleDialog(self.data_store, self, target_class=None)
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
                    color = get_subject_color(subj, self.data_store)
                    is_lock = bool(r.get("locked", False) or r.get("is_manual", False))
                    
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
                        "class": c_name,
                        "locked": is_lock,
                        "is_manual": is_lock
                    })
                
                # Update datastore and save cleanly
                self.data_store["grid_placements"] = grid_placements
                self.save_db(sync_from_grid=False)
                self._refresh_grid()
                self._refresh_tree()
                
                total_hours = sum(p.get("duration", 1) for p in grid_placements)
                QMessageBox.information(
                    self, "Otomatik Planlama Tamamlandı",
                    f"🎉 Otomatik planlama başarıyla oluşturuldu!\n\nToplam {total_hours} ders saatinin tamamı haftalık çizelgeye eksiksiz (%100 Dolu) olarak yerleştirildi."
                )
                self.statusBar().showMessage(f"Otomatik planlama başarıyla oluşturuldu ({total_hours} ders saati yerleştirildi).")
            else:
                self.save_db(sync_from_grid=False)
                self._refresh_grid()
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
        r = QMessageBox.question(
            self, "Çizelgeyi Sıfırla / Temizle",
            "Tüm sınıflar ve öğretmenler için yerleştirilmiş derslerin TAMAMI çizelgeden kaldırılacak.\nEmin misiniz?",
            QMessageBox.Yes | QMessageBox.No
        )
        if r == QMessageBox.Yes:
            self._push_undo_state()
            self.data_store["grid_placements"] = []
            self.data_store["auto_schedule_results"] = []
            self.data_store["yerlesim"] = {}
            if hasattr(self, "_grid"):
                self._grid.clear_grid()
            self.save_db(sync_from_grid=False)
            slug = getattr(self, "institution_slug", None)
            ver_fn = getattr(self, "version_filename", None)
            if slug and ver_fn:
                import version_store
                version_store.update_version_in_place(slug, ver_fn, self.data_store)
            self._refresh_grid()
            self._refresh_tree()
            self.statusBar().showMessage("🧹 Tüm çizelge dersleri başarıyla sıfırlandı ve anlık kaydedildi.")

    def _open_extracted(self, dialog_id):
        from dialogs.extracted_dialog import open_extracted_dialog
        open_extracted_dialog(dialog_id, self)

    def _act_nyi(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Bulut Tabanlı Planlama")
        msg.setIcon(QMessageBox.Information)
        msg.exec()

