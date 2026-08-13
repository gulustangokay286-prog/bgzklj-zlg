"""login_dialog.py  –  Pivot Akademi Modern Dark UI Login"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QPoint, QRect, QSize, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPainterPath, QPen, QBrush, QLinearGradient, QIcon, QPixmap
import requests
from cloud_sync import FIREBASE_API_KEY

class IconLineEdit(QLineEdit):
    def __init__(self, icon_type, placeholder, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.icon_type = icon_type
        self.setFixedHeight(48)
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet("""
            QLineEdit {
                background-color: #162032;
                border: 1px solid #1F2C41;
                border-radius: 8px;
                color: #FFFFFF;
                padding-left: 44px;
            }
            QLineEdit:focus {
                border: 1px solid #2A64F6;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#7B8B9E"), 1.5))
        p.setBrush(Qt.NoBrush)
        
        if self.icon_type == "mail":
            # Zarf ikonu
            p.drawRect(16, 18, 16, 12)
            p.drawLine(16, 18, 24, 24)
            p.drawLine(32, 18, 24, 24)
        elif self.icon_type == "lock":
            # Kilit ikonu
            p.drawRect(16, 22, 14, 10)
            p.drawArc(19, 16, 8, 12, 0, 180 * 16)
        p.end()

class ToggleSwitch(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 20)
        self.checked = False

    def mouseReleaseEvent(self, event):
        self.checked = not self.checked
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.checked:
            p.setBrush(QColor("#2A64F6"))
        else:
            p.setBrush(QColor("#3A4B66"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, 36, 20, 10, 10)
        
        p.setBrush(QColor("#FFFFFF"))
        if self.checked:
            p.drawEllipse(18, 2, 16, 16)
        else:
            p.drawEllipse(2, 2, 16, 16)
        p.end()

class LoginDialog(QDialog):
    def __init__(self, logo_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BGZ Ders Planlama - Yetkili Girişi")
        self.setFixedSize(1000, 600)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.logo_path = logo_path
        self._build_ui()

    def _build_ui(self):
        # Ana layout yok, her şey absolute/paint ile veya widgetları ortalayarak
        self.main_widget = QWidget(self)
        self.main_widget.setFixedSize(1000, 600)
        
        layout = QVBoxLayout(self.main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addSpacing(20)
        
        # Logo P (Kendimiz çiziyoruz -> Real PNG)
        lbl_logo_p = QLabel()
        pix = QPixmap(r"C:\Users\gokay\Desktop\aSc\IMG_4327 (1).PNG")
        if not pix.isNull():
            lbl_logo_p.setPixmap(pix.scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lbl_logo_p.setAlignment(Qt.AlignCenter)
        
        # BGZ Ders Planlama Yazısı
        lbl_text = QLabel('<span style="color:white; font-size:32px; font-weight:900;">BGZ </span><span style="color:#F44336; font-size:32px; font-weight:900;">Ders Planlama</span>')
        lbl_text.setAlignment(Qt.AlignCenter)
        lbl_text.setFont(QFont("Segoe UI", 24, QFont.Bold))
        
        lbl_yetkili = QLabel("YETKİLİ GİRİŞİ")
        lbl_yetkili.setStyleSheet("color: #556070; font-size: 11px; font-weight: bold; letter-spacing: 2px;")
        lbl_yetkili.setAlignment(Qt.AlignCenter)
        
        lbl_lutfen = QLabel("LÜTFEN HESABINIZA GİRİŞ YAPIN")
        lbl_lutfen.setStyleSheet("color: #A0B0C0; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        lbl_lutfen.setAlignment(Qt.AlignCenter)
        
        # Form Container
        form_container = QWidget()
        form_container.setFixedWidth(400)
        form_lay = QVBoxLayout(form_container)
        form_lay.setSpacing(16)
        
        self.w_user = IconLineEdit("mail", "E-posta")
        self.w_pass = IconLineEdit("lock", "Şifre")
        self.w_pass.setEchoMode(QLineEdit.Password)
        
        # Options row
        opt_lay = QHBoxLayout()
        self.toggle = ToggleSwitch()
        lbl_beni = QLabel("Beni Hatırla")
        lbl_beni.setStyleSheet("color: #A0B0C0; font-size: 11px; font-weight: bold;")
        lbl_sifremi = QLabel("Şifremi unuttum?")
        lbl_sifremi.setStyleSheet("color: #7B8B9E; font-size: 11px; font-weight: bold;")
        lbl_sifremi.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        opt_lay.addWidget(self.toggle)
        opt_lay.addWidget(lbl_beni)
        opt_lay.addStretch(1)
        opt_lay.addWidget(lbl_sifremi)
        
        self.btn_login = QPushButton("Giriş Yap  →")
        self.btn_login.setFixedHeight(48)
        self.btn_login.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #2A64F6;
                color: white;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #1A54E6; }
            QPushButton:pressed { background-color: #0A44D6; }
        """)
        self.btn_login.clicked.connect(self.check_login)
        
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #FF5252; font-size: 12px; font-weight: bold;")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.hide()
        
        form_lay.addWidget(self.w_user)
        form_lay.addWidget(self.w_pass)
        form_lay.addSpacing(12)
        form_lay.addLayout(opt_lay)
        form_lay.addWidget(self.lbl_error)
        form_lay.addSpacing(10)
        form_lay.addWidget(self.btn_login)
        
        # Add to main layout
        layout.addWidget(lbl_logo_p)
        layout.addWidget(lbl_text)
        layout.addSpacing(30)
        layout.addWidget(lbl_yetkili)
        layout.addSpacing(8)
        layout.addWidget(lbl_lutfen)
        layout.addSpacing(25)
        layout.addWidget(form_container, 0, Qt.AlignHCenter)
        layout.addStretch(1)
        
        # FOOTER
        lbl_footer = QLabel("Chenki Akademi © 2026")
        lbl_footer.setStyleSheet("color: #556070; font-size: 11px;")
        lbl_footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_footer)
        layout.addSpacing(20)

        self.auth_data = None

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
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        
        try:
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                self.auth_data = {
                    "email": email,
                    "password": password,
                    "idToken": data.get("idToken"),
                    "uid": data.get("localId"),
                    "expiresIn": data.get("expiresIn", 3600)
                }
                self.accept()
            else:
                err_data = resp.json()
                self.lbl_error.setText("E-posta veya Şifre Hatalı!")
                self.lbl_error.show()
                self.btn_login.setText("Giriş Yap  →")
                self.btn_login.setEnabled(True)
        except Exception as e:
            self.lbl_error.setText("Bağlantı Hatası! İnterneti kontrol edin.")
            self.lbl_error.show()
            self.btn_login.setText("Giriş Yap  →")
            self.btn_login.setEnabled(True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Arka plan Koyu Lacivert
        p.setBrush(QColor("#0E1624"))
        p.setPen(Qt.NoPen)
        p.drawRect(self.rect())
        
        # Gölge için offset path
        shadow_path = QPainterPath()
        shadow_path.moveTo(0, 0)
        shadow_path.lineTo(1000, 0)
        shadow_path.lineTo(1000, 215)
        shadow_path.quadTo(500, 295, 0, 215)
        shadow_path.closeSubpath()
        p.setBrush(QColor(0, 0, 0, 80)) # Semi-transparent black
        p.drawPath(shadow_path)
        
        # Üst kavisli açık alan (Premium Dark Blue Gradient)
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(1000, 0)
        path.lineTo(1000, 210)
        path.quadTo(500, 290, 0, 210)
        path.closeSubpath()
        
        grad = QLinearGradient(0, 0, 0, 290)
        grad.setColorAt(0, QColor("#223348")) # Lighter blue at the top
        grad.setColorAt(1, QColor("#111A28")) # Darker blue at the curve
        p.setBrush(grad)
        p.drawPath(path)
        
        # Arkada hafif logolar (su izi efekti)
        p.setPen(QPen(QColor(255, 255, 255, 10), 2))
        p.setBrush(Qt.NoBrush)
        # Kitap
        p.drawRect(150, 450, 40, 30)
        p.drawLine(170, 450, 170, 480)
        # Kep
        p.drawPolygon([QPoint(100, 300), QPoint(140, 320), QPoint(100, 340), QPoint(60, 320)])
        # Kitap 2
        p.drawRect(800, 280, 50, 35)
        # Rozet
        p.drawEllipse(820, 500, 30, 30)
        p.drawLine(825, 525, 820, 550)
        p.drawLine(845, 525, 850, 550)
        
        p.end()
