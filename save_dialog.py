# -*- coding: utf-8 -*-
"""
save_dialog.py — Apple Minimalist Save & Sync Indicator
Displays an ultra-sleek, borderless card during application shutdown or navigation.
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QWidget, QGraphicsDropShadowEffect, QApplication
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QPen
import time

class MiniLoadingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(16)  # True 60 FPS (16.6ms)
        
    def _rotate(self):
        self._angle = (self._angle + 6) % 360  # Smooth continuous 60Hz rotation
        self.update()
        
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.translate(self.width() / 2, self.height() / 2)
        p.rotate(self._angle)
        
        # Draw sleek Apple style arc spinner
        pen = QPen(QColor("#0071E3"), 3.0, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(QRectF(-13, -13, 26, 26), 0, 270 * 16)

class AppleSaveDialog(QDialog):
    def __init__(self, title="Değişiklikler Kaydediliyor", message="Veritabanı ve bulut senkronizasyonu yapılıyor...", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(480, 190)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        container = QWidget(self)
        container.setObjectName("saveCard")
        container.setStyleSheet("""
            #saveCard {
                background: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 18px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)
        
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(28, 20, 28, 20)
        c_lay.setSpacing(8)
        c_lay.setAlignment(Qt.AlignCenter)
        
        self.spinner = MiniLoadingSpinner(self)
        c_lay.addWidget(self.spinner, 0, Qt.AlignCenter)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.title_lbl.setStyleSheet("color: #1D1D1F; background: transparent; border: none;")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setWordWrap(True)
        c_lay.addWidget(self.title_lbl)
        
        self.msg_lbl = QLabel(message)
        self.msg_lbl.setFont(QFont("Segoe UI", 9.5))
        self.msg_lbl.setStyleSheet("color: #636366; background: transparent; border: none;")
        self.msg_lbl.setAlignment(Qt.AlignCenter)
        self.msg_lbl.setWordWrap(True)
        c_lay.addWidget(self.msg_lbl)
        
        layout.addWidget(container)

def run_apple_save_sequence(parent, duration_seconds=0.0, title="Değişiklikler Kaydediliyor", message="Veritabanı ve bulut senkronizasyonu yapılıyor..."):
    # Instant non-blocking execution (zero delay)
    if hasattr(parent, "statusBar") and callable(parent.statusBar):
        parent.statusBar().showMessage(f"💾 {title}: {message}", 2000)
    return
