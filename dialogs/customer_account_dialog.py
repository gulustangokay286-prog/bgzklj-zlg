"""
dialogs/customer_account_dialog.py – Kurum Anahtarı ve Müşteri Hesabı Oluşturma Penceresi
Sadece Master Admin (sehersanli@gmail.com vb.) tarafından erişilebilen lisans ve izole kurum yönetim paneli.
"""
import random
import string
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QWidget, QFrame, QRadioButton, QButtonGroup, QMessageBox, QApplication,
    QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"


class AppleCreateCustomerAccountDialog(QDialog):
    account_created = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kurum Anahtarı & Müşteri Hesabı")
        self.setFixedWidth(440)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #FFFFFF;
                font-family: {FONT_FAMILY};
            }}
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Header - Compact
        hdr = QVBoxLayout()
        hdr.setSpacing(2)
        t_lbl = QLabel("Yeni Müşteri & Kurum Hesabı")
        t_lbl.setFont(QFont(FONT_FAMILY, 12, QFont.Bold))
        t_lbl.setStyleSheet("color: #0F172A;")
        hdr.addWidget(t_lbl)

        sub_lbl = QLabel("Farklı bir kurum veya il için bağımsız lisans tanımlayın.")
        sub_lbl.setFont(QFont(FONT_FAMILY, 8.5))
        sub_lbl.setStyleSheet("color: #64748B;")
        hdr.addWidget(sub_lbl)
        layout.addLayout(hdr)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: #E2E8F0;")
        layout.addWidget(div)

        # Form Grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setContentsMargins(0, 2, 0, 2)

        # Row 1: Email
        lbl_email = QLabel("E-Posta / Lisans Kimliği *")
        lbl_email.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        lbl_email.setStyleSheet("color: #475569;")
        grid.addWidget(lbl_email, 0, 0)

        self.edit_email = QLineEdit()
        self.edit_email.setPlaceholderText("örn: izmir@chenki.net veya musteri@gmail.com")
        self.edit_email.setFixedHeight(30)
        self.edit_email.setStyleSheet(self._input_style())
        grid.addWidget(self.edit_email, 1, 0, 1, 2)

        # Row 2: Name
        lbl_name = QLabel("Kurum / Yetkili Adı *")
        lbl_name.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        lbl_name.setStyleSheet("color: #475569;")
        grid.addWidget(lbl_name, 2, 0)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("örn: İzmir Fen Lisesi")
        self.edit_name.setFixedHeight(30)
        self.edit_name.setStyleSheet(self._input_style())
        grid.addWidget(self.edit_name, 3, 0, 1, 2)

        # Row 3: Password + Generator
        lbl_pwd = QLabel("Giriş Şifresi *")
        lbl_pwd.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        lbl_pwd.setStyleSheet("color: #475569;")
        grid.addWidget(lbl_pwd, 4, 0)

        pwd_lay = QHBoxLayout()
        pwd_lay.setSpacing(6)
        self.edit_pwd = QLineEdit()
        self.edit_pwd.setFixedHeight(30)
        self.edit_pwd.setStyleSheet(self._input_style())
        pwd_lay.addWidget(self.edit_pwd, 1)

        btn_gen = QPushButton("Şifre Üret")
        btn_gen.setFont(QFont(FONT_FAMILY, 8, QFont.DemiBold))
        btn_gen.setFixedHeight(30)
        btn_gen.setCursor(Qt.PointingHandCursor)
        btn_gen.setStyleSheet("""
            QPushButton {
                background: #EFF6FF; color: #0071E3; border: 1px solid #BFDBFE;
                border-radius: 6px; padding: 0 10px; font-weight: 600;
            }
            QPushButton:hover { background: #DBEAFE; }
        """)
        btn_gen.clicked.connect(self._generate_random_password)
        pwd_lay.addWidget(btn_gen)
        grid.addLayout(pwd_lay, 5, 0, 1, 2)

        # Row 4: Initial Inst Name (Optional)
        lbl_first_inst = QLabel("İlk Kurum Adı (Opsiyonel)")
        lbl_first_inst.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        lbl_first_inst.setStyleSheet("color: #475569;")
        grid.addWidget(lbl_first_inst, 6, 0)

        self.edit_first_inst = QLineEdit()
        self.edit_first_inst.setPlaceholderText("Boş bırakılırsa sıfır kurumla başlar")
        self.edit_first_inst.setFixedHeight(30)
        self.edit_first_inst.setStyleSheet(self._input_style())
        grid.addWidget(self.edit_first_inst, 7, 0, 1, 2)

        layout.addLayout(grid)

        # Isolation Segment (Compact Box)
        iso_box = QFrame()
        iso_box.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 6px 8px;")
        iso_lay = QVBoxLayout(iso_box)
        iso_lay.setSpacing(4)
        iso_lay.setContentsMargins(4, 4, 4, 4)

        lbl_iso_title = QLabel("ERİŞİM VE İZOLASYON TÜRÜ")
        lbl_iso_title.setFont(QFont(FONT_FAMILY, 7.5, QFont.Bold))
        lbl_iso_title.setStyleSheet("color: #64748B; letter-spacing: 0.5px;")
        iso_lay.addWidget(lbl_iso_title)

        self.btn_group = QButtonGroup(self)

        self.radio_isolated = QRadioButton("Bağımsız / Dış Kurum (İzole - Bizim kurumlar gizli)")
        self.radio_isolated.setChecked(True)
        self.radio_isolated.setFont(QFont(FONT_FAMILY, 8.5, QFont.DemiBold))
        self.radio_isolated.setStyleSheet("color: #0F172A;")
        self.btn_group.addButton(self.radio_isolated)
        iso_lay.addWidget(self.radio_isolated)

        self.radio_internal = QRadioButton("Bizim Kurumlarımıza Bağlı (Tüm kurumları görür)")
        self.radio_internal.setFont(QFont(FONT_FAMILY, 8.5))
        self.radio_internal.setStyleSheet("color: #475569;")
        self.btn_group.addButton(self.radio_internal)
        iso_lay.addWidget(self.radio_internal)

        layout.addWidget(iso_box)

        # Status Error
        self.status_lbl = QLabel("")
        self.status_lbl.setFont(QFont(FONT_FAMILY, 8))
        self.status_lbl.setStyleSheet("color: #EF4444;")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.hide()
        layout.addWidget(self.status_lbl)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFixedHeight(32)
        btn_cancel.setFont(QFont(FONT_FAMILY, 8.5))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1;
                border-radius: 6px; padding: 0 14px;
            }
            QPushButton:hover { background: #E2E8F0; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        self.btn_submit = QPushButton("Hesabı ve Anahtarı Oluştur")
        self.btn_submit.setFixedHeight(32)
        self.btn_submit.setFont(QFont(FONT_FAMILY, 8.5, QFont.Bold))
        self.btn_submit.setCursor(Qt.PointingHandCursor)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 0 16px; font-weight: 600;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        self.btn_submit.clicked.connect(self._do_create_account)
        btn_box.addWidget(self.btn_submit, 1)

        layout.addLayout(btn_box)

        self._generate_random_password()

    def _input_style(self):
        return """
            QLineEdit {
                background: #F8FAFC; border: 1px solid #CBD5E1;
                border-radius: 6px; padding: 2px 8px; font-size: 12px; color: #0F172A;
            }
            QLineEdit:focus { border: 1.5px solid #0071E3; background: #FFFFFF; }
        """

    def _generate_random_password(self):
        chars = string.ascii_letters + string.digits
        pwd = "".join(random.choice(chars) for _ in range(8))
        self.edit_pwd.setText(pwd)

    def _do_create_account(self):
        email = self.edit_email.text().strip().lower()
        name = self.edit_name.text().strip()
        pwd = self.edit_pwd.text().strip()
        first_inst = self.edit_first_inst.text().strip()
        tenant_type = "isolated" if self.radio_isolated.isChecked() else "internal"

        if not email or "@" not in email:
            self._show_error("Lütfen geçerli bir e-posta / lisans kimliği girin.")
            return
        if not name:
            self._show_error("Lütfen kurum veya yetkili adını belirtin.")
            return
        if len(pwd) < 6:
            self._show_error("Şifre en az 6 karakter olmalıdır.")
            return

        from api_client import api_client
        ok, msg, acc_data = api_client.create_customer_account(
            email=email,
            password=pwd,
            full_name=name,
            tenant_type=tenant_type,
            initial_inst_name=first_inst
        )

        if not ok:
            self._show_error(msg)
            return

        self.account_created.emit(acc_data or {})
        self._show_success_modal(email, pwd, name, tenant_type, first_inst)
        self.accept()

    def _show_error(self, text: str):
        self.status_lbl.setText(text)
        self.status_lbl.show()

    def _show_success_modal(self, email: str, pwd: str, name: str, tenant_type: str, first_inst: str):
        iso_str = "Tamamen İzole (Bizim kurumlar kapalı)" if tenant_type == "isolated" else "Bizim Kurumlara Bağlı (Ortak Ağ)"
        copy_text = f"""--- CHENKI AKADEMİ GİRİŞ BİLGİLERİ ---
Yetkili / Kurum: {name}
Giriş E-Posta: {email}
Giriş Şifresi: {pwd}
Erişim Türü: {iso_str}
İlk Kurum: {first_inst or 'Sıfırdan Başlangıç'}
--------------------------------------"""

        dlg = QDialog(self)
        dlg.setWindowTitle("Hesap Bilgileri Hazır")
        dlg.setFixedWidth(380)
        dlg.setStyleSheet(f"background: #FFFFFF; font-family: {FONT_FAMILY};")
        d_lay = QVBoxLayout(dlg)
        d_lay.setContentsMargins(18, 16, 18, 16)
        d_lay.setSpacing(10)

        t_lbl = QLabel("Kurum Hesabı Oluşturuldu")
        t_lbl.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
        t_lbl.setStyleSheet("color: #059669;")
        d_lay.addWidget(t_lbl)

        info_box = QFrame()
        info_box.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px;")
        i_lay = QVBoxLayout(info_box)
        i_lay.setSpacing(3)

        i_lay.addWidget(QLabel(f"<b>Yetkili:</b> {name}"))
        i_lay.addWidget(QLabel(f"<b>E-Posta:</b> {email}"))
        i_lay.addWidget(QLabel(f"<b>Şifre:</b> {pwd}"))
        i_lay.addWidget(QLabel(f"<b>Ağ Tipi:</b> {iso_str}"))
        if first_inst:
            i_lay.addWidget(QLabel(f"<b>İlk Kurum:</b> {first_inst}"))
        d_lay.addWidget(info_box)

        b_row = QHBoxLayout()
        btn_copy = QPushButton("Bilgileri Kopyala")
        btn_copy.setFixedHeight(30)
        btn_copy.setFont(QFont(FONT_FAMILY, 8.5, QFont.Bold))
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 0 14px; font-weight: 600;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        btn_copy.clicked.connect(lambda: [QApplication.clipboard().setText(copy_text), btn_copy.setText("Kopyalandı")])
        b_row.addWidget(btn_copy)

        btn_ok = QPushButton("Kapat")
        btn_ok.setFixedHeight(30)
        btn_ok.setFont(QFont(FONT_FAMILY, 8.5))
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1;
                border-radius: 6px; padding: 0 14px;
            }
            QPushButton:hover { background: #E2E8F0; }
        """)
        btn_ok.clicked.connect(dlg.accept)
        b_row.addWidget(btn_ok)
        d_lay.addLayout(b_row)

        dlg.exec()
