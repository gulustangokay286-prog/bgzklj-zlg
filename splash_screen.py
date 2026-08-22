# -*- coding: utf-8 -*-
"""
splash_screen.py — Minimalist "Labor Illusion"
Full-screen, white background, precise left-to-right logo filling, thin loading bar, and animated tips.
"""
import os
import threading
import sys
import requests
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, 
                             QGraphicsOpacityEffect, QWidget)
from PySide6.QtCore import (Qt, QTimer, Property, QPropertyAnimation, 
                          QEasingCurve, QRect, QParallelAnimationGroup)
from PySide6.QtGui import QPainter, QColor, QFont, QPixmap

def resource_path(relative_path):
    candidates = []
    if hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, relative_path))
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, relative_path))
        candidates.append(os.path.join(exe_dir, "..", "Resources", relative_path))
        candidates.append(os.path.join(exe_dir, "..", "Frameworks", relative_path))
        candidates.append(os.path.join(exe_dir, "_internal", relative_path))
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(base_dir, relative_path))
    candidates.append(os.path.join(os.path.abspath("."), relative_path))
    
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.join(base_dir, relative_path)

class LogoRevealWidget(QWidget):
    def __init__(self, logo_path, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        
        original_pix = QPixmap()
        if logo_path and os.path.exists(logo_path):
            original_pix = QPixmap(logo_path)
            
        if original_pix.isNull():
            for fallback in ["11.png", "app_icon.png", "app_icon.ico", "app_icon.icns"]:
                p = resource_path(fallback)
                if os.path.exists(p):
                    original_pix = QPixmap(p)
                    if not original_pix.isNull():
                        break
                        
        if not original_pix.isNull():
            # Scale to a maximum size while preserving aspect ratio
            self.pixmap = original_pix.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            # Transparent fallback - never draw a gray solid box
            self.pixmap = QPixmap(280, 280)
            self.pixmap.fill(Qt.transparent)
            
        self.setFixedSize(self.pixmap.width(), self.pixmap.height())

    @Property(float)
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, val):
        self._progress = val
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        
        rect = self.rect()
        
        # 1. Draw base logo with very low opacity (e.g. 12%)
        p.setOpacity(0.12)
        p.drawPixmap(rect, self.pixmap)
        
        # 2. Draw highlighted logo with hard clipping from left to right
        p.setOpacity(1.0)
        clip_width = int(rect.width() * self._progress)
        clip_rect = QRect(rect.left(), rect.top(), clip_width, rect.height())
        
        p.setClipRect(clip_rect)
        p.drawPixmap(rect, self.pixmap)


class ThinProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(2)
        self.setFixedWidth(200)
        self._progress = 0.0

    @Property(float)
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, val):
        self._progress = val
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        # Background track
        p.fillRect(self.rect(), QColor("#E2E8F0"))
        
        # Progress fill
        fill_width = int(self.width() * self._progress)
        if fill_width > 0:
            fill_rect = QRect(0, 0, fill_width, self.height())
            p.fillRect(fill_rect, QColor("#111111"))


class HighTechSplashScreen(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
        # NOT WA_DeleteOnClose: this dialog is driven by exec(), and the caller reads
        # auth_data off it afterwards. Self-deleting on close meant the object died
        # inside its own finish handler while the modal loop was still unwinding, which
        # is what stranded the full-screen splash surface on screen. main.py owns the
        # lifetime and disposes of it once exec() has returned.
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setStyleSheet("background-color: #FFFFFF;")
        
        self.is_valid_token = False
        self.auth_data = None
        self._auth_thread = None
        self._auth_done = False
        
        self.tips = [
            "İpucu: Sınıf çakışmalarını önlemek için algoritma binlerce kombinasyonu değerlendirir.",
            "İpucu: VDS Bulut Sunucuları, verilerinizi yüksek şifreleme ile korur.",
            "İpucu: Ders atamalarında öğretmen müsaitlikleri anlık olarak hesaplanmaktadır.",
            "Sistem başlatılıyor, lütfen bekleyin..."
        ]
        self.current_tip_index = 0
        
        self._build_ui()
        self.setFixedSize(600, 400)
        self.show()
        
        # Start operations
        self._run_auth_check()
        self._start_progress_animation()
        self._start_tip_cycle()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # Use PyInstaller compatible resource_path
        logo_path = resource_path("11.png")
        self.logo_widget = LogoRevealWidget(logo_path, self)
        
        self.progress_bar = ThinProgressBar(self)
        
        layout.addStretch(1)
        layout.addWidget(self.logo_widget, 0, Qt.AlignCenter)
        layout.addSpacing(30)
        layout.addWidget(self.progress_bar, 0, Qt.AlignCenter)
        layout.addSpacing(50)
        
        self.tip_label = QLabel(self.tips[0])
        self.tip_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Normal))
        self.tip_label.setStyleSheet("color: #94A3B8; background: transparent;")
        self.tip_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.tip_label, 0, Qt.AlignCenter)
        layout.addStretch(1)

    def _start_progress_animation(self):
        # Snappy modern micro-transition
        self.anim_group = QParallelAnimationGroup(self)
        
        anim_logo = QPropertyAnimation(self.logo_widget, b"progress")
        anim_logo.setDuration(400)
        anim_logo.setStartValue(0.0)
        anim_logo.setEndValue(1.0)
        anim_logo.setEasingCurve(QEasingCurve.OutQuad)
        
        anim_bar = QPropertyAnimation(self.progress_bar, b"progress")
        anim_bar.setDuration(400)
        anim_bar.setStartValue(0.0)
        anim_bar.setEndValue(1.0)
        anim_bar.setEasingCurve(QEasingCurve.OutQuad)
        
        self.anim_group.addAnimation(anim_logo)
        self.anim_group.addAnimation(anim_bar)
        
        self.anim_group.finished.connect(self._finish)
        self.anim_group.start()

    def _start_tip_cycle(self):
        self.tip_timer = QTimer(self)
        self.tip_timer.timeout.connect(self._next_tip)
        self.tip_timer.start(1200)
        
    def _next_tip(self):
        self.current_tip_index = (self.current_tip_index + 1) % len(self.tips)
        self.tip_label.setText(self.tips[self.current_tip_index])

    def _run_auth_check(self):
        try:
            from api_client import api_client
            ok, auth = api_client.auto_authenticate()
            if ok and auth:
                self.is_valid_token = True
                self.auth_data = auth
        except Exception as e:
            print(f"[Splash] auth check note: {e}")

    def _finish(self):
        """Ends the modal loop — and nothing else.

        This used to run hide() -> close() -> accept(). With WA_DeleteOnClose set (it
        no longer is, see __init__), close() destroyed the C++ object, so accept() then
        ran against a half-destroyed window and left the native macOS window orphaned:
        the full-screen splash surface stayed on screen as a grey rectangle that
        nothing owned any more and nothing could close.

        accept() alone returns from exec(); the caller then disposes of the dialog.
        """
        for attr in ("tip_timer", "anim_group"):
            obj = getattr(self, attr, None)
            if obj is not None:
                try:
                    obj.stop()
                except Exception:
                    pass
        self.accept()
