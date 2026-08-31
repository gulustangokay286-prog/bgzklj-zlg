"""
dialogs/customer_account_dialog.py – Kurum Anahtarları ve Müşteri Lisansı Yönetim Paneli
Sade, minimalist ve Apple HIG standartlarında gerçek zamanlı bulut lisans yöneticisi.
"""
import random
import string
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QWidget, QFrame, QRadioButton, QButtonGroup, QMessageBox, QApplication,
    QScrollArea, QGraphicsDropShadowEffect, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor, QIcon

import bk_ui
from api_client import api_client

FONT_FAMILY = bk_ui.FONT_FAMILY


class AppleCreateCustomerAccountDialog(bk_ui.HeroSheetDialog):
    """Institution keys, on the program's one sheet.

    Two pages behind one title: the licences that exist, and the form
    that makes another. Keeping them in a stack rather than opening a
    second dialog follows the same rule the sign-in window's reset flow
    does — a modal inside a modal is where people lose the way back.

    Its own card, shadow, radius, close cross and two differently-shaped
    close buttons are gone; the sheet supplies all of it, and this class
    now describes only what is particular to managing keys.
    """

    account_created = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent, width=540, height=430,
                         title="",
                         subtitle="")
        self.setWindowTitle("Kurum Anahtarları")
        self._build_ui()
        self._load_and_render_accounts()

    def _build_ui(self):
        layout = self.card_layout
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(12)

        # Top Header Row: Left: Title & Subtitle, Right: Action Button
        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(0, 0, 0, 0)
        hdr_row.setSpacing(12)

        t_col = QVBoxLayout()
        t_col.setSpacing(2)
        t_col.setContentsMargins(0, 0, 0, 0)

        self.title_lbl = QLabel("Kurum Anahtarları")
        self.title_lbl.setFont(bk_ui.title_font(15))
        self.title_lbl.setStyleSheet(f"color: {bk_ui.INK}; background: transparent; border: none;")
        t_col.addWidget(self.title_lbl)

        self.sub_lbl = QLabel("Kayıtlı lisanslar ve bağımsız müşteri erişimleri.")
        self.sub_lbl.setFont(bk_ui.font(8.8))
        self.sub_lbl.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent; border: none;")
        t_col.addWidget(self.sub_lbl)

        hdr_row.addLayout(t_col, 1)

        self.btn_header_action = bk_ui.secondary_button("Yeni Anahtar", height=32)
        self.btn_header_action.setFont(bk_ui.font(8.8, QFont.DemiBold))
        self.btn_header_action.setIcon(QIcon(bk_ui.plus_glyph(bk_ui.INK_BODY, 12)))
        self.btn_header_action.setIconSize(QSize(12, 12))
        self.btn_header_action.clicked.connect(self._toggle_view)
        hdr_row.addWidget(self.btn_header_action, 0, Qt.AlignTop)

        layout.addLayout(hdr_row)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        self.page_list = self._build_list_page()
        self.stack.addWidget(self.page_list)
        self.page_create = self._build_create_page()
        self.stack.addWidget(self.page_create)
        layout.addWidget(self.stack, 1)

        # Balanced Footer with Hairline
        layout.addWidget(bk_ui.hairline())

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 2, 0, 0)
        footer_row.setSpacing(10)

        self.footer_info_lbl = QLabel("")
        self.footer_info_lbl.setFont(bk_ui.font(8.6))
        self.footer_info_lbl.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent; border: none;")
        footer_row.addWidget(self.footer_info_lbl, 0, Qt.AlignVCenter)
        footer_row.addStretch(1)

        self.btn_footer_cancel = bk_ui.secondary_button("Vazgeç", height=32)
        self.btn_footer_cancel.setFont(bk_ui.font(8.8, QFont.Medium))
        self.btn_footer_cancel.clicked.connect(self._show_list_view)
        self.btn_footer_cancel.hide()
        footer_row.addWidget(self.btn_footer_cancel)

        self.btn_footer_action = bk_ui.primary_button("Kapat", height=32)
        self.btn_footer_action.setFont(bk_ui.font(8.8, QFont.DemiBold))
        self.btn_footer_action.clicked.connect(self._on_footer_action_clicked)
        footer_row.addWidget(self.btn_footer_action)

        layout.addLayout(footer_row)

    def _on_footer_action_clicked(self):
        if self.stack.currentIndex() == 0:
            self.accept()
        else:
            self._do_create_account()

    def _toggle_view(self):
        if self.stack.currentIndex() == 0:
            self._show_create_view()
        else:
            self._show_list_view()

    def _show_list_view(self):
        self.stack.setCurrentIndex(0)
        self.title_lbl.setText("Kurum Anahtarları")
        self.sub_lbl.setText("Kayıtlı lisanslar ve bağımsız müşteri erişimleri.")
        self.btn_header_action.setText("Yeni Anahtar")
        self.btn_header_action.setIcon(QIcon(bk_ui.plus_glyph(bk_ui.INK_BODY, 12)))
        self.btn_header_action.show()
        self.btn_footer_cancel.hide()
        self.btn_footer_action.setText("Kapat")
        self.btn_footer_action.setStyleSheet(f"""
            QPushButton {{
                background: {bk_ui.BRAND}; color: #FFFFFF; border: none;
                border-radius: {bk_ui.R_CONTROL}px; padding: 0 20px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {bk_ui.BRAND_DARK}; }}
        """)
        self._load_and_render_accounts()

    def _show_create_view(self):
        self.stack.setCurrentIndex(1)
        self.title_lbl.setText("Yeni Kurum Anahtarı")
        self.sub_lbl.setText("Müşteri için bağımsız giriş ve lisans tanımlayın.")
        self.btn_header_action.setText("← Listeye Dön")
        self.btn_header_action.setIcon(QIcon())
        self.footer_info_lbl.setText("● Yeni Anahtar Tanımlama")
        self.btn_footer_cancel.show()
        self.btn_footer_action.setText("Anahtarı Oluştur")
        self.status_lbl.hide()
        self.edit_email.setFocus()

    # ─────────────────────────────────────────────────────────────────
    # Page 0: List View
    # ─────────────────────────────────────────────────────────────────
    def _build_list_page(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 6px; }
            QScrollBar::handle:vertical { background: #D5D5DB; border-radius: 3px; }
        """)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 2, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch(1)

        scroll.setWidget(self.list_container)
        lay.addWidget(scroll, 1)
        return w

    def _load_and_render_accounts(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        accounts = api_client.load_registered_accounts() or {}

        for email, acc in api_client.LOCAL_ACCOUNTS.items():
            if email not in accounts:
                accounts[email] = acc

        if not accounts:
            empty_box = QFrame()
            empty_box.setStyleSheet(f"""
                QFrame {{
                    background: {bk_ui.SURFACE_SUNK};
                    border: 1px dashed {bk_ui.HAIRLINE};
                    border-radius: 12px;
                    padding: 30px;
                }}
            """)
            e_lay = QVBoxLayout(empty_box)
            e_lay.setAlignment(Qt.AlignCenter)
            e_lay.setSpacing(8)

            e_txt = QLabel("Henüz kayıtlı müşteri anahtarı bulunmuyor.")
            e_txt.setFont(bk_ui.font(9.5, QFont.DemiBold))
            e_txt.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent; border: none;")
            e_lay.addWidget(e_txt, 0, Qt.AlignCenter)

            btn_c = QPushButton("+ Yeni Anahtar Oluştur")
            btn_c.setFixedHeight(32)
            btn_c.setFont(bk_ui.font(8.8, QFont.Bold))
            btn_c.setCursor(Qt.PointingHandCursor)
            btn_c.setStyleSheet(f"""
                QPushButton {{
                    background: {bk_ui.BRAND}; color: #FFFFFF; border: none;
                    border-radius: 16px; padding: 0 16px; font-weight: 600;
                }}
                QPushButton:hover {{ background: {bk_ui.BRAND_DARK}; }}
            """)
            btn_c.clicked.connect(self._show_create_view)
            e_lay.addWidget(btn_c, 0, Qt.AlignCenter)

            self.list_layout.insertWidget(0, empty_box)
            self.footer_info_lbl.setText("● Lisanslı hesap yok")
            return

        self.footer_info_lbl.setText(f"● {len(accounts)} Lisanslı Hesap")
        idx = 0
        for email, acc in accounts.items():
            card = self._create_account_row(email, acc)
            self.list_layout.insertWidget(idx, card)
            idx += 1

    def _create_account_row(self, email: str, acc: dict) -> QFrame:
        card = QFrame()
        card.setFixedHeight(54)
        card.setStyleSheet(f"""
            QFrame {{
                background: #FFFFFF;
                border: 1px solid {bk_ui.HAIRLINE};
                border-radius: 10px;
            }}
            QFrame:hover {{
                border-color: {bk_ui.HAIRLINE_STRONG};
                background: #FAFAFC;
            }}
        """)
        c_lay = QHBoxLayout(card)
        c_lay.setContentsMargins(12, 6, 12, 6)
        c_lay.setSpacing(12)

        full_name = acc.get("full_name") or email.split("@")[0].capitalize()
        pwd = acc.get("password", "")
        is_master = bool(acc.get("is_master", False) or email == "sehersanli@chenki.net")
        is_isolated = (acc.get("tenant_type", "isolated") == "isolated")

        # Left 3D Avatar
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(34, 34)
        icon_lbl.setAlignment(Qt.AlignCenter)
        color = bk_ui.BRAND if is_master else "#64748B"
        icon_lbl.setPixmap(bk_ui.key_glyph(color, 24))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        c_lay.addWidget(icon_lbl)

        # Info column
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.setContentsMargins(0, 0, 0, 0)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        lbl_name = QLabel(full_name)
        lbl_name.setFont(bk_ui.font(9.4, QFont.Bold))
        lbl_name.setStyleSheet(f"color: {bk_ui.INK}; background: transparent; border: none;")
        title_row.addWidget(lbl_name)

        if is_master:
            tag = QLabel("Ana Yönetici")
            tag.setFont(bk_ui.font(7.6, QFont.Bold))
            tag.setStyleSheet(f"color: {bk_ui.BRAND}; background: {bk_ui.BRAND_TINT}; border-radius: 4px; padding: 1px 6px;")
            title_row.addWidget(tag)
        elif not is_isolated:
            tag = QLabel("Ortak Ağ")
            tag.setFont(bk_ui.font(7.6))
            tag.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: {bk_ui.HOVER}; border-radius: 4px; padding: 1px 6px;")
            title_row.addWidget(tag)

        title_row.addStretch(1)
        info_col.addLayout(title_row)

        sub_text = f"{email}  ·  Şifre: {pwd}"
        lbl_sub = QLabel(sub_text)
        lbl_sub.setFont(bk_ui.font(8.2))
        lbl_sub.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent; border: none;")
        info_col.addWidget(lbl_sub)

        c_lay.addLayout(info_col, 1)

        # Actions
        btn_copy = QPushButton("Kopyala")
        btn_copy.setFixedHeight(28)
        btn_copy.setFont(bk_ui.font(8.2, QFont.DemiBold))
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setStyleSheet(f"""
            QPushButton {{
                background: {bk_ui.HOVER}; color: {bk_ui.INK_BODY};
                border: 1px solid {bk_ui.HAIRLINE}; border-radius: 6px; padding: 0 10px;
            }}
            QPushButton:hover {{ background: #E4E4E8; }}
        """)
        
        copy_text = f"Kurum: {full_name}\nE-Posta: {email}\nŞifre: {pwd}"
        btn_copy.clicked.connect(lambda _, t=copy_text, b=btn_copy: [
            QApplication.clipboard().setText(t),
            b.setText("Kopyalandı")
        ])
        c_lay.addWidget(btn_copy)

        if not is_master:
            btn_del = QPushButton("Sil")
            btn_del.setFixedHeight(28)
            btn_del.setFont(bk_ui.font(8.2))
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {bk_ui.INK_FAINT};
                    border: 1px solid {bk_ui.HAIRLINE}; border-radius: 6px; padding: 0 10px;
                }}
                QPushButton:hover {{ color: {bk_ui.DANGER}; border-color: {bk_ui.DANGER}; background: #FEF2F2; }}
            """)
            btn_del.clicked.connect(lambda _, e=email, n=full_name: self._confirm_delete_account(e, n))
            c_lay.addWidget(btn_del)

        return card

    def _confirm_delete_account(self, email: str, name: str):
        msg = QMessageBox(self)
        msg.setWindowTitle("Anahtarı Sil")
        msg.setText(f"{name} ({email}) anahtarını silmek istediğinize emin misiniz?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.button(QMessageBox.Yes).setText("Sil")
        msg.button(QMessageBox.No).setText("Vazgeç")
        if msg.exec() == QMessageBox.Yes:
            api_client.delete_customer_account(email)
            self._load_and_render_accounts()

    # ─────────────────────────────────────────────────────────────────
    # Page 1: Create View
    # ─────────────────────────────────────────────────────────────────
    def _build_create_page(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(10)

        # Field 1: Email
        f1 = QVBoxLayout()
        f1.setSpacing(3)
        lbl_e = QLabel("Lisans E-Postası")
        lbl_e.setFont(bk_ui.font(8.8, QFont.DemiBold))
        lbl_e.setStyleSheet(f"color: {bk_ui.INK_BODY}; background: transparent; border: none;")
        f1.addWidget(lbl_e)

        self.edit_email = QLineEdit()
        self.edit_email.setPlaceholderText("örn: izmir@chenki.net")
        self.edit_email.setFixedHeight(36)
        self.edit_email.setStyleSheet(self._input_style())
        f1.addWidget(self.edit_email)
        lay.addLayout(f1)

        # Field 2: Name
        f2 = QVBoxLayout()
        f2.setSpacing(3)
        lbl_n = QLabel("Kurum / Yetkili Adı")
        lbl_n.setFont(bk_ui.font(8.8, QFont.DemiBold))
        lbl_n.setStyleSheet(f"color: {bk_ui.INK_BODY}; background: transparent; border: none;")
        f2.addWidget(lbl_n)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("örn: İzmir Fen Lisesi")
        self.edit_name.setFixedHeight(36)
        self.edit_name.setStyleSheet(self._input_style())
        f2.addWidget(self.edit_name)
        lay.addLayout(f2)

        # Field 3: Password + Generator
        f3 = QVBoxLayout()
        f3.setSpacing(3)
        lbl_p = QLabel("Giriş Şifresi")
        lbl_p.setFont(bk_ui.font(8.8, QFont.DemiBold))
        lbl_p.setStyleSheet(f"color: {bk_ui.INK_BODY}; background: transparent; border: none;")
        f3.addWidget(lbl_p)

        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(8)
        self.edit_pwd = QLineEdit()
        self.edit_pwd.setFixedHeight(36)
        self.edit_pwd.setStyleSheet(self._input_style())
        pwd_row.addWidget(self.edit_pwd, 1)

        btn_gen = QPushButton("Şifre Üret")
        btn_gen.setFont(bk_ui.font(8.6, QFont.DemiBold))
        btn_gen.setFixedHeight(36)
        btn_gen.setCursor(Qt.PointingHandCursor)
        btn_gen.setStyleSheet(f"""
            QPushButton {{
                background: {bk_ui.HOVER}; color: {bk_ui.INK};
                border: 1px solid {bk_ui.HAIRLINE_STRONG};
                border-radius: 8px; padding: 0 14px; font-weight: 500;
            }}
            QPushButton:hover {{ background: {bk_ui.HAIRLINE}; }}
        """)
        btn_gen.clicked.connect(self._generate_random_password)
        pwd_row.addWidget(btn_gen)
        f3.addLayout(pwd_row)
        lay.addLayout(f3)

        # Field 4: Isolation Choice
        f4 = QVBoxLayout()
        f4.setSpacing(4)
        lbl_iso = QLabel("Erişim Türü")
        lbl_iso.setFont(bk_ui.font(8.8, QFont.DemiBold))
        lbl_iso.setStyleSheet(f"color: {bk_ui.INK_BODY}; background: transparent; border: none;")
        f4.addWidget(lbl_iso)

        self.btn_group = QButtonGroup(self)
        self.radio_isolated = QRadioButton("Bağımsız / İzole Kurum (Diğer kurumlar gizlidir)")
        self.radio_isolated.setChecked(True)
        self.radio_isolated.setFont(bk_ui.font(8.6))
        self.radio_isolated.setStyleSheet(f"color: {bk_ui.INK}; border: none;")
        self.btn_group.addButton(self.radio_isolated)
        f4.addWidget(self.radio_isolated)

        self.radio_internal = QRadioButton("Ortak Kurumlar Ağı")
        self.radio_internal.setFont(bk_ui.font(8.6))
        self.radio_internal.setStyleSheet(f"color: {bk_ui.INK_SOFT}; border: none;")
        self.btn_group.addButton(self.radio_internal)
        f4.addWidget(self.radio_internal)

        lay.addLayout(f4)

        # Status Banner
        self.status_lbl = QLabel("")
        self.status_lbl.setFont(bk_ui.font(8.6))
        self.status_lbl.setStyleSheet(f"color: {bk_ui.DANGER}; background: transparent; border: none;")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.hide()
        lay.addWidget(self.status_lbl)

        lay.addStretch(1)

        # Bottom Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        btn_back = QPushButton("Vazgeç")
        btn_back.setFixedHeight(36)
        btn_back.setFont(bk_ui.font(9.0, QFont.DemiBold))
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background: {bk_ui.HOVER}; color: {bk_ui.INK};
                border: 1px solid {bk_ui.HAIRLINE_STRONG};
                border-radius: 18px; padding: 0 18px; font-weight: 500;
            }}
            QPushButton:hover {{ background: {bk_ui.HAIRLINE}; }}
        """)
        btn_back.clicked.connect(self._show_list_view)
        btn_box.addWidget(btn_back)

        self.btn_submit = QPushButton("Anahtarı Oluştur")
        self.btn_submit.setFixedHeight(36)
        self.btn_submit.setFont(bk_ui.font(9.2, QFont.Bold))
        self.btn_submit.setCursor(Qt.PointingHandCursor)
        self.btn_submit.setStyleSheet(f"""
            QPushButton {{
                background: {bk_ui.BRAND}; color: #FFFFFF; border: none;
                border-radius: 18px; padding: 0 22px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {bk_ui.BRAND_DARK}; }}
        """)
        self.btn_submit.clicked.connect(self._do_create_account)
        btn_box.addWidget(self.btn_submit, 1)

        lay.addLayout(btn_box)
        self._generate_random_password()
        return w

    def _input_style(self):
        return f"""
            QLineEdit {{
                background: #FAFAFB; border: 1px solid {bk_ui.HAIRLINE_STRONG};
                border-radius: 8px; padding: 4px 12px; font-size: 13px; color: {bk_ui.INK};
            }}
            QLineEdit:focus {{ border: 1.5px solid {bk_ui.BRAND}; background: #FFFFFF; }}
        """

    def _generate_random_password(self):
        chars = string.ascii_letters + string.digits
        pwd = "".join(random.choice(chars) for _ in range(8))
        self.edit_pwd.setText(pwd)

    def _do_create_account(self):
        email = self.edit_email.text().strip().lower()
        name = self.edit_name.text().strip()
        pwd = self.edit_pwd.text().strip()
        tenant_type = "isolated" if self.radio_isolated.isChecked() else "internal"

        if not email or "@" not in email:
            self._show_error("Geçerli bir e-posta adresi girin.")
            return
        if not name:
            self._show_error("Kurum veya yetkili adını girin.")
            return
        if len(pwd) < 6:
            self._show_error("Şifre en az 6 karakter olmalıdır.")
            return

        self.btn_submit.setEnabled(False)
        self.status_lbl.setText("Anahtar oluşturuluyor...")
        self.status_lbl.setStyleSheet(f"color: {bk_ui.BRAND}; font-weight: 500; border: none;")
        self.status_lbl.show()
        QApplication.processEvents()

        ok, msg, acc_data = api_client.create_customer_account(
            email=email,
            password=pwd,
            full_name=name,
            tenant_type=tenant_type
        )

        self.btn_submit.setEnabled(True)

        if not ok:
            self._show_error(msg)
            return

        self.account_created.emit(acc_data or {})
        self.edit_email.clear()
        self.edit_name.clear()
        self._generate_random_password()
        self._show_list_view()

    def _show_error(self, text: str):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color: {bk_ui.DANGER}; font-weight: 500; border: none;")
        self.status_lbl.show()
