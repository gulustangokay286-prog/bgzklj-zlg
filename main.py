"""
main.py — Chenki Akademi v2 Entry Point
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap, QColor, QPainter

from login_dialog import LoginDialog
from main_window import MainWindow
import traceback

def global_exception_handler(exc_type, exc_value, exc_traceback):
    from PySide6.QtWidgets import QMessageBox
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(error_msg)
    QMessageBox.critical(None, "Kritik Hata", f"Uygulama çöktü:\n\n{error_msg}")

sys.excepthook = global_exception_handler

def main():
    app = QApplication(sys.argv)
    
    # 1. İşletim sisteminin Karanlık Modunu (Dark Mode) yoksay ve Klasik stili zorla
    app.setStyle("Fusion")
    
    # 2. Bütün program için (tablolar, butonlar, arkaplanlar) açık renk (beyaz/gri) palet zorla
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
    
    app.setApplicationName("BGZ Ders Planlama")
    app.setOrganizationName("BGZ")
    app.setStyle("Fusion")

    font = QFont("Segoe UI", 9)
    app.setFont(font)

    logo_path = r"C:\Users\gokay\Desktop\aSc\ChatGPT Image 5 Tem 2026 01_04_30.png"

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

    # Main window
    win = MainWindow(logo_path=logo_path if os.path.exists(logo_path) else None)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
