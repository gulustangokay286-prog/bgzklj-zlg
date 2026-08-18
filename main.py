"""
main.py — Chenki Akademi v2 Entry Point
Login → Home Dashboard → Timetable Editor akışı
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication, QSplashScreen, QMainWindow, QStackedWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap, QColor, QPainter, QIcon, QPalette

from login_dialog import LoginDialog
from home_dashboard import HomeDashboard
from main_window import MainWindow
import traceback
import database
import version_store

def global_exception_handler(exc_type, exc_value, exc_traceback):
    from PySide6.QtWidgets import QMessageBox
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(error_msg)
    QMessageBox.critical(None, "Kritik Hata", f"Uygulama çöktü:\n\n{error_msg}")

sys.excepthook = global_exception_handler

def get_asset_path(rel_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.abspath(rel_path)

class AppShell(QMainWindow):
    """Top-level window that holds Dashboard ↔ Editor via QStackedWidget."""
    
    def __init__(self, logo_path, auth_data):
        super().__init__()
        self.logo_path = logo_path
        self.auth_data = auth_data
        self.setWindowTitle("BGZ Ders Planlama — Kurum & Çizelge Yönetimi")
        self.setMinimumSize(1100, 700)
        self.showMaximized()
        
        if logo_path and os.path.exists(logo_path):
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(logo_path))
        
        # Stacked widget: 0=Dashboard, 1=Editor
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        
        # Page 0: Home Dashboard
        self._dashboard = HomeDashboard(auth_data=auth_data)
        self._dashboard.open_timetable.connect(self._open_timetable)
        self._dashboard.new_empty_timetable.connect(self._open_empty_timetable)
        self._dashboard.logout_requested.connect(self._handle_logout)
        self._stack.addWidget(self._dashboard)
        
        # Page 1: Will be created when a timetable is opened
        self._editor = None
        self._active_slug = None
        self._active_version = None

    def _handle_logout(self):
        try:
            from api_client import token_manager
            token_manager.delete_token()
        except Exception:
            pass
        self.close()
        login = LoginDialog(self.logo_path if self.logo_path and os.path.exists(self.logo_path) else None)
        if login.exec() == LoginDialog.Accepted:
            new_auth = getattr(login, "auth_data", None)
            self._new_shell = AppShell(logo_path=self.logo_path, auth_data=new_auth)
            self._new_shell.show()
    
    def _open_timetable(self, slug, version_filename):
        """Load a version and switch to the timetable editor."""
        data = version_store.load_version(slug, version_filename)
        if not data:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Hata", f"Versiyon dosyası yüklenemedi:\n{version_filename}")
            return
        
        self._active_slug = slug
        self._active_version = version_filename
        
        # Remove old editor if exists
        if self._editor:
            self._stack.removeWidget(self._editor)
            self._editor.deleteLater()
            self._editor = None
        
        # Create new editor with the loaded data
        meta = version_store.get_institution_meta(slug)
        inst_name = meta.get("name", slug)
        
        # Save version data to a temp path for MainWindow to load
        temp_roz = os.path.join(
            os.path.expanduser("~"), ".chenki_akademi",
            "institutions", slug, "versions", version_filename
        )
        
        self._editor = MainWindow(
            logo_path=self.logo_path,
            auth_data=self.auth_data,
            override_db_path=temp_roz,
            institution_slug=slug,
            institution_name=inst_name,
            version_filename=version_filename,
        )
        self._editor.go_home_requested = self._go_home
        
        self._stack.addWidget(self._editor)
        self._stack.setCurrentWidget(self._editor)
        
        # Update title
        v_num = ""
        import re
        m = re.match(r"v(\d+)_", version_filename)
        if m:
            v_num = f"v{int(m.group(1))}"
        self.setWindowTitle(f"BGZ Ders Planlama — {inst_name} — {v_num}")
    
    def _open_empty_timetable(self, slug):
        """Create a new empty version and open it."""
        meta = version_store.get_institution_meta(slug)
        inst_name = meta.get("name", slug)
        empty_data = {
            "dersler": [], "siniflar": [], "derslikler": [],
            "ogretmenler": [], "atamalar": [], "settings": {},
            "grid_placements": [], "kisitlamalar": {},
        }
        vf = version_store.save_version(slug, empty_data, source="manual", note="Yeni boş çizelge")
        self._open_timetable(slug, vf)
    
    def _go_home(self):
        """Switch back to the dashboard."""
        # Save current work before going home
        if self._editor:
            try:
                if hasattr(self._editor, "save_db"):
                    self._editor.save_db()
            except Exception as e:
                print(f"[GO_HOME] Save error: {e}")
        
        # Switch to dashboard FIRST
        self._dashboard._refresh_institutions()
        self._stack.setCurrentWidget(self._dashboard)
        self.setWindowTitle("BGZ Ders Planlama — Kurum & Çizelge Yönetimi")
        
        # Safely clean up and destroy editor
        if self._editor:
            editor = self._editor
            self._editor = None
            if hasattr(editor, "cleanup"):
                editor.cleanup()
            self._stack.removeWidget(editor)
            editor.deleteLater()

    def closeEvent(self, event):
        """Save active editor and flush database & cloud sync before closing the application."""
        if self._editor and hasattr(self._editor, "save_db"):
            try:
                self._editor.save_db(sync_from_grid=True)
            except Exception as e:
                print(f"[CLOSE] Auto-save error: {e}")
                
        # 1-second graceful database and cloud sync flush as requested
        import time
        t_end = time.time() + 1.0
        while time.time() < t_end:
            QApplication.processEvents()
            time.sleep(0.05)
            
        super().closeEvent(event)

    @property
    def data_store(self):
        return self._editor.data_store if self._editor else {}
        
    def save_db(self, *args, **kwargs):
        if self._editor and hasattr(self._editor, "save_db"):
            self._editor.save_db(*args, **kwargs)
            
    def _refresh_grid(self, *args, **kwargs):
        if self._editor and hasattr(self._editor, "_refresh_grid"):
            self._editor._refresh_grid(*args, **kwargs)
            
    def _refresh_unplaced_lessons(self, *args, **kwargs):
        if self._editor and hasattr(self._editor, "_refresh_unplaced_lessons"):
            self._editor._refresh_unplaced_lessons(*args, **kwargs)
            
    def _refresh_tree(self, *args, **kwargs):
        if self._editor and hasattr(self._editor, "_refresh_tree"):
            self._editor._refresh_tree(*args, **kwargs)
            
    def mark_dirty(self, *args, **kwargs):
        if self._editor and hasattr(self._editor, "mark_dirty"):
            self._editor.mark_dirty(*args, **kwargs)


def main():
    # Initialize the local SQLite database
    database.init_db()

    app = QApplication(sys.argv)
    
    # Force light mode
    app.setStyle("Fusion")
    
    from PySide6.QtGui import QPalette, QColor
    from PySide6.QtCore import Qt
    
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, Qt.black)
    palette.setColor(QPalette.Base, Qt.white)
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.black)
    palette.setColor(QPalette.Text, Qt.black)
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, Qt.black)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(palette)
    
    app.setApplicationName("Chenki Planlama")
    app.setOrganizationName("Chenki")

    icon_path = get_asset_path("app_icon.png")
    if not os.path.exists(icon_path):
        icon_path = get_asset_path("app_icon.ico")
        
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    font = QFont("Segoe UI", 9)
    app.setFont(font)

    logo_path = icon_path if os.path.exists(icon_path) else get_asset_path("ChatGPT Image 5 Tem 2026 01_04_30.png")

    # Splash
    if os.path.exists(logo_path):
        pix = QPixmap(logo_path).scaled(320, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    else:
        pix = QPixmap(320, 120)
        pix.fill(QColor("#1E6DB5"))
        p = QPainter(pix)
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", 14, QFont.Bold))
        p.drawText(pix.rect(), Qt.AlignCenter, "BGZ Ders Planlama")
        p.end()

    splash = QSplashScreen(pix)
    splash.show()
    app.processEvents()

    # Login
    QTimer.singleShot(800, splash.close)

    login = LoginDialog(logo_path if os.path.exists(logo_path) else None)
    if login.exec() != LoginDialog.Accepted:
        sys.exit(0)
        
    auth_data = getattr(login, "auth_data", None)

    # App Shell (Dashboard + Editor)
    shell = AppShell(
        logo_path=logo_path if os.path.exists(logo_path) else None,
        auth_data=auth_data
    )
    shell.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
