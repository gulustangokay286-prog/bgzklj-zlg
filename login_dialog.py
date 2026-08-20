"""login_dialog.py — BGZ Ders Planlama Modern Minimalist Beyaz UI Login Dialog"""
import os, sys, requests
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget, QGraphicsDropShadowEffect, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, QPoint, QSize, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPixmap, QCursor, QImage, QPainterPath
from api_client import api_client

def get_asset_path(rel_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.abspath(rel_path)

def find_logo_path():
    candidates = [
        get_asset_path("11.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "11.png"),
        os.path.abspath("11.png"),
        "/Users/fookay/ders program/11.png",
        get_asset_path("app_icon.png"),
        get_asset_path(os.path.join("resources", "logo.png")),
        get_asset_path(os.path.join("dist", "11.png")),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return get_asset_path("11.png")

def find_teacher_char_path():
    candidates = [
        get_asset_path("ChatGPT Image 16 Ağu 2026 10_31_17.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ChatGPT Image 16 Ağu 2026 10_31_17.png"),
        os.path.abspath("ChatGPT Image 16 Ağu 2026 10_31_17.png"),
        "/Users/fookay/ders program/ChatGPT Image 16 Ağu 2026 10_31_17.png"
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return get_asset_path("ChatGPT Image 16 Ağu 2026 10_31_17.png")

LOGO_SHIELD_PATH = find_logo_path()
TEACHER_CHAR_PATH = find_teacher_char_path()


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
        p.setBrush(QColor('#2563EB'))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(1, 1, 22, 22, 5, 5)
        pen = QPen(QColor('#FFFFFF'), 2.6)
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
        p2.setBrush(QColor('#FFFFFF'))
        p2.setPen(QPen(QColor('#CBD5E1'), 2.0))
        p2.drawRoundedRect(1, 1, 22, 22, 5, 5)
        p2.end()
        img2.save(unchk_path)

ensure_checkmark_assets()


class ModernWhiteLineEdit(QLineEdit):
    def __init__(self, icon_type, placeholder, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.icon_type = icon_type
        self.setFixedHeight(48)
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet("""
            QLineEdit {
                background-color: #F8FAFC;
                border: 1.5px solid #E2E8F0;
                border-radius: 10px;
                color: #0F172A;
                padding-left: 44px;
                padding-right: 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                background-color: #FFFFFF;
                border: 2px solid #2563EB;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#64748B"), 1.8))
        p.setBrush(Qt.NoBrush)
        
        if self.icon_type == "mail":
            # Clean Mail Icon
            p.drawRoundedRect(14, 17, 18, 14, 2, 2)
            p.drawLine(14, 17, 23, 24)
            p.drawLine(32, 17, 23, 24)
        elif self.icon_type == "lock":
            # Clean Lock Icon
            p.drawRoundedRect(15, 21, 16, 12, 2, 2)
            p.drawArc(18, 14, 10, 14, 0, 180 * 16)
            p.drawPoint(23, 27)
        p.end()


class LoginDialog(QDialog):
    """Ultra-clean, modern, minimalist pure-white login dialog for BGZ Ders Planlama"""
    def __init__(self, logo_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BGZ Ders Planlama - Yönetici Girişi")
        self.setFixedSize(540, 710)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._drag_pos = QPoint()
        self.auth_data = None
        self.logo_path = logo_path or LOGO_SHIELD_PATH
        
        self._build_ui()

    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(15, 15, 15, 15)
        
        self.card = QWidget(self)
        self.card.setObjectName("loginCard")
        self.card.setStyleSheet("""
            QWidget#loginCard {
                background-color: #FFFFFF;
                border-radius: 20px;
                border: 1px solid #E2E8F0;
            }
        """)
        
        # Soft modern shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(15, 23, 42, 35))
        shadow.setOffset(0, 10)
        self.card.setGraphicsEffect(shadow)
        
        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(36, 20, 36, 28)
        card_lay.setSpacing(14)
        
        # 1. Top Bar: Window Controls (Close & Drag)
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: #F1F5F9;
                color: #64748B;
                border: none;
                border-radius: 15px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FEE2E2;
                color: #EF4444;
            }
        """)
        btn_close.clicked.connect(self.reject)
        top_bar.addWidget(btn_close)
        card_lay.addLayout(top_bar)
        
        # 2. Top Shield/Brand Logo (IMG_4327 (1).PNG)
        top_logo_lay = QHBoxLayout()
        lbl_brand_logo = QLabel()
        lbl_brand_logo.setAlignment(Qt.AlignCenter)
        
        brand_path = LOGO_SHIELD_PATH if os.path.exists(LOGO_SHIELD_PATH) else self.logo_path
        if brand_path and os.path.exists(brand_path):
            pix_brand = QPixmap(brand_path)
            if not pix_brand.isNull():
                lbl_brand_logo.setPixmap(pix_brand.scaledToHeight(75, Qt.SmoothTransformation))
        top_logo_lay.addWidget(lbl_brand_logo)
        card_lay.addLayout(top_logo_lay)
        
        # 3. Hero Section: "BGZ Planlama" on left, Teacher Illustration on right
        hero_lay = QHBoxLayout()
        hero_lay.setSpacing(10)
        
        text_lay = QVBoxLayout()
        text_lay.setSpacing(2)
        
        lbl_title = QLabel("BGZ Planlama")
        lbl_title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        lbl_title.setStyleSheet("color: #0F172A; letter-spacing: -0.5px;")
        
        lbl_subtitle = QLabel("Ders Dağıtım ve Yönetim Sistemi")
        lbl_subtitle.setFont(QFont("Segoe UI", 11))
        lbl_subtitle.setStyleSheet("color: #64748B;")
        
        lbl_badge = QLabel("• 2026-2027 Pro")
        lbl_badge.setStyleSheet("color: #2563EB; font-weight: bold; font-size: 11px;")
        
        text_lay.addWidget(lbl_title)
        text_lay.addWidget(lbl_subtitle)
        text_lay.addWidget(lbl_badge)
        text_lay.addStretch()
        
        hero_lay.addLayout(text_lay, 3)
        
        # Enlarged Teacher Character Image
        lbl_char = QLabel()
        lbl_char.setAlignment(Qt.AlignCenter)
        if os.path.exists(TEACHER_CHAR_PATH):
            pix_char = QPixmap(TEACHER_CHAR_PATH)
            if not pix_char.isNull():
                lbl_char.setPixmap(pix_char.scaledToHeight(120, Qt.SmoothTransformation))
        hero_lay.addWidget(lbl_char, 2)
        
        card_lay.addLayout(hero_lay)
        card_lay.addSpacing(10)
        
        # 4. Form Fields (Start Completely Empty with Placeholders)
        self.w_user = ModernWhiteLineEdit("mail", "E-posta Adresi")
        self.w_pass = ModernWhiteLineEdit("lock", "Şifre")
        self.w_pass.setEchoMode(QLineEdit.Password)
        self.w_pass.returnPressed.connect(self.check_login)
        self.w_user.returnPressed.connect(self._on_user_return)
        
        card_lay.addWidget(self.w_user)
        card_lay.addWidget(self.w_pass)
        
        # 5. Options Row with White Checkmark Support
        chk_checked_file = os.path.join(get_asset_path("resources"), "chk_checked.png").replace("\\", "/")
        chk_unchk_file = os.path.join(get_asset_path("resources"), "chk_unchecked.png").replace("\\", "/")
        
        opt_lay = QHBoxLayout()
        self.chk_remember = QCheckBox("Beni Hatırla")
        self.chk_remember.setChecked(True)
        self.chk_remember.setStyleSheet(f"""
            QCheckBox {{
                color: #475569;
                font-size: 12px;
                font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:unchecked {{
                image: url("{chk_unchk_file}");
            }}
            QCheckBox::indicator:checked {{
                image: url("{chk_checked_file}");
            }}
        """)
        
        lbl_forgot = QLabel("Şifremi Unuttum")
        lbl_forgot.setCursor(Qt.PointingHandCursor)
        lbl_forgot.setStyleSheet("color: #2563EB; font-size: 12px; font-weight: 600;")
        
        opt_lay.addWidget(self.chk_remember)
        opt_lay.addStretch()
        opt_lay.addWidget(lbl_forgot)
        card_lay.addLayout(opt_lay)
        
        # Error Label
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600;")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.hide()
        card_lay.addWidget(self.lbl_error)
        
        card_lay.addSpacing(4)
        
        # 6. Action Buttons
        self.btn_login = QPushButton("Giriş Yap  →")
        self.btn_login.setFixedHeight(50)
        self.btn_login.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1D4ED8);
                color: white;
                border-radius: 10px;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1D4ED8, stop:1 #1E40AF);
            }
            QPushButton:pressed {
                background: #1E3A8A;
            }
        """)
        self.btn_login.setDefault(True)
        self.btn_login.clicked.connect(self.check_login)
        card_lay.addWidget(self.btn_login)
        
        # License Acquisition Button (Redirects directly to chenki.com)
        self.btn_license = QPushButton("Lisans Al")
        self.btn_license.setFixedHeight(44)
        self.btn_license.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.btn_license.setCursor(Qt.PointingHandCursor)
        self.btn_license.setStyleSheet("""
            QPushButton {
                background: #F8FAFC;
                color: #0284C7;
                border-radius: 10px;
                border: 1.5px solid #BAE6FD;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #E0F2FE;
                color: #0369A1;
                border-color: #7DD3FC;
            }
            QPushButton:pressed {
                background: #BAE6FD;
            }
        """)
        self.btn_license.clicked.connect(self._open_license_web)
        card_lay.addWidget(self.btn_license)
        
        card_lay.addStretch(1)
        
        # 7. Footer
        lbl_footer = QLabel("BGZ Eğitim Kurumları © 2026 • Lisanslı Kurum")
        lbl_footer.setStyleSheet("color: #94A3B8; font-size: 11px;")
        lbl_footer.setAlignment(Qt.AlignCenter)
        card_lay.addWidget(lbl_footer)
        
        main_lay.addWidget(self.card)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def _enter_offline(self):
        self.auth_data = {
            "email": self.w_user.text().strip() or "offline@bgz.local",
            "uid": "offline_local_user",
            "is_offline": True
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
            self.lbl_error.setText("Lütfen E-posta ve Şifre girin.")
            self.lbl_error.show()
            return
            
        self.btn_login.setText("Giriş Yapılıyor...")
        self.btn_login.setEnabled(False)
        self.lbl_error.hide()
        QTimer.singleShot(50, lambda: self._do_firebase_auth(email, password))
        
    def _do_firebase_auth(self, email, password):
        # Artık VDS API kullanılıyor. İsim uyumluluk için aynı bırakıldı.
        success, result = api_client.login(email, password)
        
        if success:
            self.auth_data = result
            # Cloud pull in background — do NOT block login UI
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

    def _open_license_web(self):
        import webbrowser
        webbrowser.open("https://chenki.net")
