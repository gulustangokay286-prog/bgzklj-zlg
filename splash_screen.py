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
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class LogoRevealWidget(QWidget):
    def __init__(self, logo_path, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        
        original_pix = QPixmap(logo_path)
        if not original_pix.isNull():
            # Scale to a maximum size while preserving aspect ratio
            self.pixmap = original_pix.scaled(350, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            self.pixmap = QPixmap(350, 350)
            self.pixmap.fill(QColor("#E2E8F0"))
            
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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet("background-color: #FFFFFF;")
        
        self.is_valid_token = False
        self.auth_data = None
        
        self.tips = [
            "İpucu: Sınıf çakışmalarını önlemek için algoritma binlerce kombinasyonu değerlendirir.",
            "İpucu: VDS Bulut Sunucuları, verilerinizi yüksek şifreleme ile korur.",
            "İpucu: Ders atamalarında öğretmen müsaitlikleri anlık olarak hesaplanmaktadır.",
            "Sistem başlatılıyor, lütfen bekleyin..."
        ]
        self.current_tip_index = 0
        
        self._build_ui()
        self.showFullScreen()
        
        # Start operations
        QTimer.singleShot(100, self._run_auth_check)
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
        
        self.opacity_effect = QGraphicsOpacityEffect(self.tip_label)
        self.tip_label.setGraphicsEffect(self.opacity_effect)
        
        layout.addWidget(self.tip_label, 0, Qt.AlignCenter)
        layout.addStretch(1)

    def _start_progress_animation(self):
        # We use a group to animate both logo mask and the thin progress bar simultaneously
        self.anim_group = QParallelAnimationGroup(self)
        
        anim_logo = QPropertyAnimation(self.logo_widget, b"progress")
        anim_logo.setDuration(4000) # 4 seconds loading illusion
        anim_logo.setStartValue(0.0)
        anim_logo.setEndValue(1.0)
        anim_logo.setEasingCurve(QEasingCurve.InOutSine)
        
        anim_bar = QPropertyAnimation(self.progress_bar, b"progress")
        anim_bar.setDuration(4000)
        anim_bar.setStartValue(0.0)
        anim_bar.setEndValue(1.0)
        anim_bar.setEasingCurve(QEasingCurve.InOutSine)
        
        self.anim_group.addAnimation(anim_logo)
        self.anim_group.addAnimation(anim_bar)
        
        self.anim_group.finished.connect(self._finish)
        self.anim_group.start()

    def _start_tip_cycle(self):
        self.tip_timer = QTimer(self)
        self.tip_timer.timeout.connect(self._next_tip)
        self.tip_timer.start(1250)
        
    def _next_tip(self):
        self.current_tip_index += 1
        if self.current_tip_index < len(self.tips):
            # Fade out
            self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.fade_out.setDuration(250)
            self.fade_out.setStartValue(1.0)
            self.fade_out.setEndValue(0.0)
            self.fade_out.finished.connect(self._change_tip_text)
            self.fade_out.start()

    def _change_tip_text(self):
        if self.current_tip_index < len(self.tips):
            self.tip_label.setText(self.tips[self.current_tip_index])
            # Fade in
            self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.fade_in.setDuration(350)
            self.fade_in.setStartValue(0.0)
            self.fade_in.setEndValue(1.0)
            self.fade_in.start()

    def _run_auth_check(self):
        def check():
            from api_client import api_client
            if api_client.token:
                try:
                    resp = requests.get(f"{api_client.base_url}/api/institutions", headers=api_client.get_headers(), timeout=3)
                    if resp.status_code == 200:
                        self.is_valid_token = True
                        self.auth_data = {"access_token": api_client.token}
                except Exception:
                    pass
        threading.Thread(target=check, daemon=True).start()

    def _finish(self):
        # A tiny delay after logo reaches 100% before closing
        QTimer.singleShot(400, self.accept)
