"""login_dialog.py — BK Planner sign-in.

Rebuilt from the previous version for two concrete reasons, not just a
visual refresh: (1) it carried WindowStaysOnTopHint with no minimize
button, so it pinned itself above every other window on the machine with
no way to get it out of the way — a real, reported bug, not a style
complaint; (2) the old hero layout paired a stock illustration with the
brand mark, which reads as generic rather than as this institution's own
identity. This version uses the real shield mark and drops the
illustration for plain, quiet typography instead.
"""
import os
import sys

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QImage, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

import bk_branding
from api_client import api_client


def get_asset_path(rel_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.abspath(rel_path)


def ensure_checkmark_assets():
    res_dir = get_asset_path("resources")
    os.makedirs(res_dir, exist_ok=True)
    chk_path = os.path.join(res_dir, "chk_checked.png")
    unchk_path = os.path.join(res_dir, "chk_unchecked.png")

    if not os.path.exists(chk_path):
        img = QImage(24, 24, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(bk_branding.BRAND_BLUE))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(1, 1, 22, 22, 5, 5)
        pen = QPen(QColor("#FFFFFF"), 2.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(6, 12)
        path.lineTo(10, 16)
        path.lineTo(18, 8)
        p.drawPath(path)
        p.end()
        img.save(chk_path)

    if not os.path.exists(unchk_path):
        img2 = QImage(24, 24, QImage.Format_ARGB32)
        img2.fill(Qt.transparent)
        p2 = QPainter(img2)
        p2.setRenderHint(QPainter.Antialiasing)
        p2.setBrush(QColor("#FFFFFF"))
        p2.setPen(QPen(QColor("#D8D8D8"), 2.0))
        p2.drawRoundedRect(1, 1, 22, 22, 5, 5)
        p2.end()
        img2.save(unchk_path)


ensure_checkmark_assets()


class _FieldEdit(QLineEdit):
    def __init__(self, icon_type, placeholder, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.icon_type = icon_type
        self.setFixedHeight(46)
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet("""
            QLineEdit {
                background-color: #F7F7F8;
                border: 1.5px solid #E6E6E8;
                border-radius: 10px;
                color: #111111;
                padding-left: 42px;
                padding-right: 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                background-color: #FFFFFF;
                border: 1.5px solid """ + bk_branding.BRAND_BLUE + """;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#8A8A8E"), 1.7))
        p.setBrush(Qt.NoBrush)
        if self.icon_type == "mail":
            p.drawRoundedRect(14, 16, 18, 14, 2, 2)
            p.drawLine(14, 16, 23, 23)
            p.drawLine(32, 16, 23, 23)
        elif self.icon_type == "lock":
            p.drawRoundedRect(15, 20, 16, 12, 2, 2)
            p.drawArc(18, 13, 10, 14, 0, 180 * 16)
            p.drawPoint(23, 26)
        p.end()


class _TitleBarButton(QPushButton):
    def __init__(self, text, hover_bg, hover_fg, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: #9A9A9E; border: none;
                border-radius: 14px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {hover_bg}; color: {hover_fg}; }}
        """)


class LoginDialog(QDialog):
    """Frameless but fully manageable: draggable by its own header (no
    native title bar to grab), a real minimize button, and no
    WindowStaysOnTopHint — it behaves like any other window once it's
    open, the previous version's core complaint."""

    def __init__(self, logo_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{bk_branding.PRODUCT_NAME} — Giriş")
        self.setFixedSize(480, 660)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._drag_pos = QPoint()
        self.auth_data = None
        self.logo_path = logo_path or bk_branding.INNER_LOGO_PNG

        self._build_ui()
        self._animate_entrance()

    # --- UI ----------------------------------------------------------------
    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(14, 14, 14, 14)

        self.card = QWidget(self)
        self.card.setObjectName("loginCard")
        self.card.setStyleSheet("""
            QWidget#loginCard {
                background-color: #FFFFFF;
                border-radius: 18px;
                border: 1px solid #E6E6E8;
            }
        """)
        self._card_opacity = QGraphicsOpacityEffect(self.card)
        self._card_opacity.setOpacity(0.0)
        self.card.setGraphicsEffect(self._card_opacity)

        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(38, 16, 38, 26)
        card_lay.setSpacing(12)

        # Title bar: drag handle + minimize + close (frameless has no native ones)
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        btn_min = _TitleBarButton("—", "#F1F1F2", "#444444")
        btn_min.clicked.connect(self.showMinimized)
        top_bar.addWidget(btn_min)
        btn_close = _TitleBarButton("✕", "#FBE9E9", "#D64545")
        btn_close.clicked.connect(self.reject)
        top_bar.addWidget(btn_close)
        card_lay.addLayout(top_bar)

        # Brand: shield mark, centered, quiet
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        if self.logo_path and os.path.exists(self.logo_path):
            pix = QPixmap(self.logo_path)
            if not pix.isNull():
                logo_lbl.setPixmap(pix.scaledToHeight(84, Qt.SmoothTransformation))
        card_lay.addWidget(logo_lbl)
        card_lay.addSpacing(6)

        title_lbl = QLabel(bk_branding.PRODUCT_NAME)
        title_lbl.setFont(QFont("Segoe UI", 21, QFont.Bold))
        title_lbl.setStyleSheet("color: #111111; letter-spacing: -0.3px;")
        title_lbl.setAlignment(Qt.AlignCenter)
        card_lay.addWidget(title_lbl)

        subtitle_lbl = QLabel("Ders Dağıtım ve Yönetim Sistemi")
        subtitle_lbl.setFont(QFont("Segoe UI", 10.5))
        subtitle_lbl.setStyleSheet("color: #8A8A8E;")
        subtitle_lbl.setAlignment(Qt.AlignCenter)
        card_lay.addWidget(subtitle_lbl)

        card_lay.addSpacing(22)

        self.w_user = _FieldEdit("mail", "E-posta Adresi")
        self.w_pass = _FieldEdit("lock", "Şifre")
        self.w_pass.setEchoMode(QLineEdit.Password)
        self.w_pass.returnPressed.connect(self.check_login)
        self.w_user.returnPressed.connect(self._on_user_return)
        card_lay.addWidget(self.w_user)
        card_lay.addWidget(self.w_pass)

        chk_checked_file = os.path.join(get_asset_path("resources"), "chk_checked.png").replace("\\", "/")
        chk_unchk_file = os.path.join(get_asset_path("resources"), "chk_unchecked.png").replace("\\", "/")

        opt_lay = QHBoxLayout()
        self.chk_remember = QCheckBox("Beni Hatırla")
        self.chk_remember.setChecked(True)
        self.chk_remember.setStyleSheet(f"""
            QCheckBox {{ color: #6A6A6E; font-size: 12px; font-weight: 500; spacing: 8px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; }}
            QCheckBox::indicator:unchecked {{ image: url("{chk_unchk_file}"); }}
            QCheckBox::indicator:checked {{ image: url("{chk_checked_file}"); }}
        """)
        lbl_forgot = QLabel("Şifremi Unuttum")
        lbl_forgot.setCursor(Qt.PointingHandCursor)
        lbl_forgot.setStyleSheet(f"color: {bk_branding.BRAND_BLUE}; font-size: 12px; font-weight: 600;")
        opt_lay.addWidget(self.chk_remember)
        opt_lay.addStretch()
        opt_lay.addWidget(lbl_forgot)
        card_lay.addLayout(opt_lay)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #D64545; font-size: 12px; font-weight: 600;")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        card_lay.addWidget(self.lbl_error)

        card_lay.addSpacing(6)

        self.btn_login = QPushButton("Giriş Yap")
        self.btn_login.setFixedHeight(48)
        self.btn_login.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setStyleSheet(f"""
            QPushButton {{
                background: {bk_branding.BRAND_BLUE}; color: white; border-radius: 10px; border: none; font-size: 14px;
            }}
            QPushButton:hover {{ background: {bk_branding.BRAND_BLUE_DARK}; }}
            QPushButton:pressed {{ background: {bk_branding.BRAND_BLUE_DARK}; }}
        """)
        self.btn_login.setDefault(True)
        self.btn_login.clicked.connect(self.check_login)
        card_lay.addWidget(self.btn_login)

        card_lay.addStretch(1)

        lbl_footer = QLabel(f"{bk_branding.COMPANY_NAME} {bk_branding.COPYRIGHT[0]} 2026")
        lbl_footer.setStyleSheet("color: #B5B5B8; font-size: 11px;")
        lbl_footer.setAlignment(Qt.AlignCenter)
        card_lay.addWidget(lbl_footer)

        main_lay.addWidget(self.card)

    def _animate_entrance(self):
        anim = QPropertyAnimation(self._card_opacity, b"opacity", self)
        anim.setDuration(320)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._entrance_anim = anim

    # --- Drag-to-move (frameless has no native title bar) -------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    # --- Auth ----------------------------------------------------------------
    def _enter_offline(self):
        self.auth_data = {
            "email": self.w_user.text().strip() or "offline@local",
            "uid": "offline_local_user",
            "is_offline": True,
        }
        self.accept()

    def _on_user_return(self):
        if self.w_pass.text().strip():
            self.check_login()
        else:
            self.w_pass.setFocus()

    def check_login(self):
        email = self.w_user.text().strip()
        password = self.w_pass.text().strip()
        if not email or not password:
            self.lbl_error.setText("Lütfen e-posta ve şifre girin.")
            self.lbl_error.show()
            return
        self.btn_login.setText("Giriş Yapılıyor...")
        self.btn_login.setEnabled(False)
        self.lbl_error.hide()
        QTimer.singleShot(50, lambda: self._do_auth(email, password))

    def _do_auth(self, email, password):
        success, result = api_client.login(email, password)
        if success:
            self.auth_data = result
            import threading

            def _bg_pull():
                try:
                    api_client.pull_all_from_rtdb()
                except Exception as ex:
                    print(f"[Login] Background cloud pull note: {ex}")

            threading.Thread(target=_bg_pull, daemon=True).start()
            self.accept()
        else:
            self.lbl_error.setText(str(result))
            self.lbl_error.show()
            self.btn_login.setText("Giriş Yap")
            self.btn_login.setEnabled(True)
