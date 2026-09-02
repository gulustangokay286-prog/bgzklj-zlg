"""
main.py — BK Planner Entry Point
Login → Home Dashboard → Timetable Editor akışı
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import platform
# Windows Low-End Device Optimization & Anti-Lag CPU/GPU Settings
if platform.system() == "Windows":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QSG_RENDER_LOOP"] = "basic"
    os.environ["QT_THREAD_PRIORITY"] = "high"

from PySide6.QtWidgets import QApplication, QSplashScreen, QMainWindow, QStackedWidget
from PySide6.QtCore import Qt, QTimer, QCoreApplication
from PySide6.QtGui import QFont, QPixmap, QColor, QPainter, QIcon, QPalette

from login_dialog import LoginDialog
from home_dashboard import HomeDashboard
from main_window import MainWindow
import traceback
import database
import version_store
import bk_branding
import bk_update
import update_notifications

def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print("[UNCAUGHT_EXCEPTION]", error_msg)
    try:
        from PySide6.QtWidgets import QMessageBox, QApplication
        app = QApplication.instance()
        if app:
            app.processEvents()
            parent = app.activeWindow()
            QMessageBox.critical(parent, "Kritik Hata", f"Uygulamada bir hata oluştu:\n\n{error_msg[:600]}")
    except Exception as e:
        print("[EXCEPTHOOK_FAIL]", e)

sys.excepthook = global_exception_handler

def get_asset_path(rel_path):
    candidates = []
    if hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, rel_path))
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, rel_path))
        candidates.append(os.path.join(exe_dir, "..", "Resources", rel_path))
        candidates.append(os.path.join(exe_dir, "..", "Frameworks", rel_path))
        candidates.append(os.path.join(exe_dir, "_internal", rel_path))
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(base_dir, rel_path))
    candidates.append(os.path.join(os.path.abspath("."), rel_path))
    
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.join(base_dir, rel_path)

class AppShell(QMainWindow):
    """Top-level window that holds Dashboard ↔ Editor via QStackedWidget."""
    
    def __init__(self, logo_path, auth_data):
        super().__init__()
        self.logo_path = logo_path
        self.auth_data = auth_data
        self.setWindowTitle("Chenkron — Ders Dağıtım ve Yönetim Sistemi")
        self.setMinimumSize(1100, 700)
        
        if logo_path and os.path.exists(logo_path):
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(logo_path))
        
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(255, 255, 255))
        pal.setColor(QPalette.Base, QColor(255, 255, 255))
        self.setPalette(pal)
        
        # Stacked widget: 0=Dashboard, 1=Editor
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: #FFFFFF;")
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
        meta = version_store.get_institution_meta(slug)
        inst_name = meta.get("name", slug)
        
        import re
        m = re.match(r"v(\d+)_", version_filename)
        v_label = f"Versiyon {int(m.group(1))}" if m else "Çizelge"
        
        from save_dialog import AppleSaveDialog
        dlg = AppleSaveDialog(
            title="Hazırlanıyor...",
            message=f"{inst_name} · {v_label}\nÇalışma alanı ve ders programı hazırlanıyor...",
            parent=self,
            show_spinner=True
        )
        dlg.show()
        QApplication.processEvents()
        
        data = version_store.load_version(slug, version_filename)
        if not data:
            dlg.close()
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
        QApplication.processEvents()
        
        # Auto-set opened version as active and update timestamp
        version_store.set_active_version(slug, version_filename)
        version_store.touch_institution_timestamp(slug)
        
        # Smoothly dismiss preparation sheet
        # Hazırlık sayfası, hazırlık bitince kapanır. Burada sabit 800 ms
        # bekleniyordu: editör kurulumu artık dörtte bir saniyeye indiği için
        # bu bekleme, gecikmenin kendisinden uzun kalıyordu.
        dlg.close_smooth()
        
        # Update title
        v_num = ""
        import re
        m = re.match(r"v(\d+)_", version_filename)
        if m:
            v_num = f"v{int(m.group(1))}"
        self.setWindowTitle(f"Chenkron — {inst_name} — {v_num}")
    
    def _open_empty_timetable(self, slug):
        """Create a new version that inherits master data from the current active version (fresh grid)."""
        meta = version_store.get_institution_meta(slug)
        inst_name = meta.get("name", slug)
        
        # Try to load current active version's master data
        active_ver = version_store.get_active_version(slug)
        base_data = None
        if active_ver:
            base_data = version_store.load_version(slug, active_ver)
        
        if base_data and any(base_data.get(k) for k in ("dersler", "siniflar", "ogretmenler", "atamalar")):
            # Inherit ALL master data, constraints, bell schedules, plan relations — only reset grid
            new_data = {
                "dersler": list(base_data.get("dersler", [])),
                "siniflar": list(base_data.get("siniflar", [])),
                "derslikler": list(base_data.get("derslikler", [])),
                "ogretmenler": list(base_data.get("ogretmenler", [])),
                "atamalar": list(base_data.get("atamalar", [])),
                "settings": dict(base_data.get("settings", {})),
                "grid_placements": [],  # Fresh empty grid
                "kisitlamalar": dict(base_data.get("kisitlamalar", {})) if isinstance(base_data.get("kisitlamalar"), dict) else base_data.get("kisitlamalar", {}),
                "ders_programlari": base_data.get("ders_programlari", {}),
                "plan_iliskileri": base_data.get("plan_iliskileri", {}),
                "zil_programi": base_data.get("zil_programi", {}),
                "temel_bilgiler": base_data.get("temel_bilgiler", {}),
                "gun_sayisi": base_data.get("gun_sayisi", 5),
                "ders_saati": base_data.get("ders_saati", 8),
            }
            note = f"Yeni çizelge — '{inst_name}' verileri aktarıldı (boş yerleşim)"
        else:
            new_data = {
                "dersler": [], "siniflar": [], "derslikler": [],
                "ogretmenler": [], "atamalar": [], "settings": {},
                "grid_placements": [], "kisitlamalar": {},
            }
            note = "Yeni boş çizelge"
        
        vf = version_store.save_version(slug, new_data, source="manual", note=note)
        self._open_timetable(slug, vf)
    
    def _go_home(self):
        """Switch back to the dashboard smoothly, instantaneously and safely.

        Note: saving (with the folder-picker dialog, when there are unsaved changes) has
        ALREADY happened by the time this runs — MainWindow._go_home does that itself and
        only invokes this callback afterward (and only if the user didn't cancel the
        picker), via self.go_home_requested. Re-doing the save here would just be redundant
        duplicate logic racing the one above.
        """
        editor = self._editor
        self._editor = None

        if editor:
            try:
                slug = getattr(editor, "institution_slug", None)
                if slug:
                    self._dashboard._selected_slug = slug
            except Exception as e:
                print(f"[GO_HOME] Error: {e}")

            # 2. Cleanup background workers safely
            try:
                if hasattr(editor, "cleanup"):
                    editor.cleanup()
            except Exception as ce:
                print(f"[GO_HOME] Cleanup error: {ce}")

        # 3. Switch to dashboard instantly
        from save_dialog import run_apple_save_sequence
        run_apple_save_sequence(self, duration_seconds=0.1, title="Kaydedildi", message="Anasayfaya dönülüyor...")
        
        self._stack.setCurrentWidget(self._dashboard)
        self.setWindowTitle("Chenkron — Ders Dağıtım ve Yönetim Sistemi")
        try:
            self._dashboard._refresh_institutions()
            if hasattr(self._dashboard, "_selected_slug") and self._dashboard._selected_slug:
                self._dashboard._refresh_versions()
        except Exception as re_err:
            print(f"[GO_HOME] Dashboard refresh error: {re_err}")

        # 4. Remove and delete editor safely
        if editor:
            try:
                self._stack.removeWidget(editor)
                editor.deleteLater()
            except Exception:
                pass

    def closeEvent(self, event):
        """Save active editor (asking which folder to save into, if there's anything new
        to save) and flush database & cloud sync before closing the application."""
        if self._editor and hasattr(self._editor, "_save_new_version_with_folder_picker"):
            if not self._editor._save_new_version_with_folder_picker("Kapanış kaydı", force=False):
                event.ignore()  # user cancelled the folder picker — don't close
                return

        from save_dialog import run_apple_save_sequence
        run_apple_save_sequence(self, duration_seconds=0.2, title="Kapatılıyor", message="Veriler kaydedildi.")

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
    # Initialize VDS Cloud and local version storage directories
    database.init_db()

    app = QApplication(sys.argv)
    
    # Force light mode
    app.setStyle("Fusion")
    
    from PySide6.QtGui import QPalette, QColor
    from PySide6.QtCore import Qt
    
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(255, 255, 255))
    palette.setColor(QPalette.WindowText, QColor(15, 23, 42))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(248, 250, 252))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ToolTipText, QColor(15, 23, 42))
    palette.setColor(QPalette.Text, QColor(15, 23, 42))
    palette.setColor(QPalette.Button, QColor(255, 255, 255))
    palette.setColor(QPalette.ButtonText, QColor(15, 23, 42))
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Highlight, QColor(bk_branding.BRAND_BLUE))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(palette)

    app.setApplicationName(bk_branding.PRODUCT_NAME)
    app.setOrganizationName(bk_branding.COMPANY_NAME)

    icon_path = bk_branding.ICON_ICO if os.path.exists(bk_branding.ICON_ICO) else bk_branding.ICON_PNG
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    app.setStyleSheet("""
        QToolTip {
            background-color: #1D1D1F;
            color: #FFFFFF;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            padding: 5px 9px;
            font-size: 11px;
            font-family: Segoe UI, -apple-system, sans-serif;
        }
        QMessageBox {
            background-color: #F8F9FA;
            color: #111111;
        }
        QMessageBox QLabel {
            color: #111111;
        }
        QMessageBox QPushButton {
            background-color: #E2E8F0;
            color: #111111;
            border: 1px solid #CBD5E1;
            border-radius: 4px;
            padding: 5px 15px;
            min-width: 60px;
        }
        QMessageBox QPushButton:hover {
            background-color: #CBD5E1;
        }
    """)

    logo_path = bk_branding.INNER_LOGO_PNG if os.path.exists(bk_branding.INNER_LOGO_PNG) else icon_path

    from splash_screen import BKSplashScreen
    splash = BKSplashScreen(bk_update.install_root())
    splash.exec()
    auth_data = splash.auth_data if splash.is_valid_token else None
    del splash

    if not auth_data:
        login = LoginDialog(logo_path if os.path.exists(logo_path) else None)
        if login.exec() != LoginDialog.Accepted:
            sys.exit(0)
        auth_data = getattr(login, "auth_data", None)

    # App Shell (Dashboard + Editor)
    shell = AppShell(
        logo_path=logo_path if os.path.exists(logo_path) else None,
        auth_data=auth_data
    )
    shell.resize(1200, 800)
    shell.show()

    # "What's new" toast reads State/pending_notes.json, written once by the
    # splash-time update engine right after activating a new version — see
    # update_notifications.py's docstring. The in-session checker (polling,
    # no standalone background process — see bk_update.py's module
    # docstring) replaces the old silent restart-watcher toast with a real
    # "update now / later" sheet.
    try:
        QTimer.singleShot(500, lambda: update_notifications.check_and_show_whats_new(shell))
        bk_update.start_in_session_checker(shell)
    except Exception:
        pass  # must never block app startup

    exit_code = app.exec()

    # Safety net for "uygulamadan çıkınca kapatmıyor": if some background
    # resource (a non-daemon thread, an open socket) survives the window
    # closing, sys.exit() below can leave the OS process alive indefinitely
    # since Python only fully exits once every non-daemon thread has ended.
    # This guarantees the process is gone within 3 seconds of the last
    # window closing, no matter what's still running.
    import threading as _threading
    import time as _time

    _threading.Thread(target=lambda: (_time.sleep(3), os._exit(exit_code)), daemon=True).start()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
