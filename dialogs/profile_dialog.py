"""
dialogs/profile_dialog.py – Kullanıcı Profil Düzenleme ve Cloudinary Fotoğraf Yükleme Modülü
Apple Human Interface Guidelines uyumlu, Cloudinary CDN entegrasyonlu profil yöneticisi.
"""
import os
import json
import urllib.request
import requests
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QWidget, QFrame, QApplication, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, Signal, QThread, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QFont, QPixmap, QPainter, QPainterPath, QColor, QBrush, QPen, QIcon

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"

CLOUDINARY_CLOUD_NAME = "dbfhcj6px"
CLOUDINARY_UPLOAD_PRESET = "ml_default"
CLOUDINARY_FOLDER = "ial-mobil"
CLOUDINARY_UPLOAD_URL = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"


def get_profile_store_path() -> str:
    base_dir = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "bgz_user_profiles.json")


def get_avatar_cache_dir() -> str:
    cache_dir = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "avatar_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def load_all_profiles() -> dict:
    path = get_profile_store_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def get_user_profile(email: str) -> dict:
    clean_email = (email or "").strip().lower()
    profiles = load_all_profiles()
    
    if clean_email in profiles:
        return profiles[clean_email]
        
    # Default fallbacks
    name = "Seher Şanlı"
    if "birey" in clean_email:
        name = "Birey Kurum"
    elif clean_email and "@" in clean_email:
        name = clean_email.split("@")[0].capitalize()
        
    prof = {
        "name": name,
        "email": clean_email or "admin@bgz.local",
        "title": "Program Yöneticisi",
        "avatar_url": ""
    }
    return prof


def save_user_profile(email: str, name: str, avatar_url: str = "", title: str = "") -> dict:
    clean_email = (email or "").strip().lower() or "admin@bgz.local"
    profiles = load_all_profiles()
    
    existing = profiles.get(clean_email, {})
    existing["name"] = name.strip() or existing.get("name", "Kullanıcı")
    existing["email"] = clean_email
    if avatar_url is not None:
        existing["avatar_url"] = avatar_url.strip()
    if title:
        existing["title"] = title.strip()
        
    profiles[clean_email] = existing
    path = get_profile_store_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
        
    return existing


def upload_avatar_to_cloudinary(file_path: str) -> str:
    """Uploads a local image file to Cloudinary and returns the secure URL."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")
        
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {
            "upload_preset": CLOUDINARY_UPLOAD_PRESET,
            "folder": CLOUDINARY_FOLDER
        }
        resp = requests.post(CLOUDINARY_UPLOAD_URL, files=files, data=data, timeout=30)
        resp.raise_for_status()
        res_json = resp.json()
        return res_json.get("secure_url") or res_json.get("url") or ""


def get_cached_avatar_file(avatar_url: str) -> str:
    """Downloads avatar from Cloudinary URL if not cached, returns local path or empty."""
    if not avatar_url or not avatar_url.startswith("http"):
        return avatar_url if (avatar_url and os.path.exists(avatar_url)) else ""
        
    import hashlib
    url_hash = hashlib.md5(avatar_url.encode("utf-8")).hexdigest()
    ext = os.path.splitext(avatar_url.split("?")[0])[1] or ".png"
    local_path = os.path.join(get_avatar_cache_dir(), f"{url_hash}{ext}")
    
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        return local_path
        
    try:
        urllib.request.urlretrieve(avatar_url, local_path)
        return local_path
    except Exception:
        return ""


def make_circular_avatar_pixmap(image_path_or_url: str, initials: str, size: int = 28) -> QPixmap:
    """Creates a high-DPI crisp circular avatar pixmap from image or initials."""
    scale = 2
    actual_sz = size * scale
    pix = QPixmap(actual_sz, actual_sz)
    pix.fill(Qt.transparent)
    
    local_img_path = get_cached_avatar_file(image_path_or_url)
    loaded_img = None
    if local_img_path and os.path.exists(local_img_path):
        loaded_img = QPixmap(local_img_path)
        
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    
    # Clip to circle
    path = QPainterPath()
    path.addEllipse(0, 0, actual_sz, actual_sz)
    p.setClipPath(path)
    
    if loaded_img and not loaded_img.isNull():
        # Draw image smoothly scaled
        scaled = loaded_img.scaled(
            actual_sz, actual_sz,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        # Center crop
        ox = (scaled.width() - actual_sz) // 2
        oy = (scaled.height() - actual_sz) // 2
        p.drawPixmap(0, 0, scaled, ox, oy, actual_sz, actual_sz)
    else:
        # Fallback initials circle
        p.setBrush(QBrush(QColor("#E2E8F0")))
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, actual_sz, actual_sz)
        
        p.setPen(QColor("#0F172A"))
        font = QFont(FONT_FAMILY, int(size * 0.42 * scale), QFont.Bold)
        p.setFont(font)
        p.drawText(pix.rect(), Qt.AlignCenter, initials.upper())
        
    p.end()
    pix.setDevicePixelRatio(scale)
    return pix


STATIC_TITLES = [
    "Program Yöneticisi",
    "Okul Müdürü",
    "Müdür Başyardımcısı",
    "Müdür Yardımcısı",
    "Bölüm / Zümre Başkanı",
    "Ders Öğretmeni",
    "Bilişim & Sistem Sorumlusu",
    "Rehberlik & Psikolojik Danışman",
    "Eğitim Danışmanı",
    "Genel Koordinatör",
    "Diğer",
]


import bk_ui


class CloudinaryUploadWorker(QThread):
    finished = Signal(str)
    failed = Signal(str)
    
    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        
    def run(self):
        try:
            url = upload_avatar_to_cloudinary(self.file_path)
            if url:
                self.finished.emit(url)
            else:
                self.failed.emit("Sunucudan geçerli bir görsel bağlantısı alınamadı.")
        except Exception as e:
            self.failed.emit(str(e))


# ── Modern Apple Role Picker (Popover Menu Selection) ─────────────────

class AppleRolePickerButton(QPushButton):
    """Modern Apple-style Role / Title selector button that opens a HeroPopoverMenu."""
    role_changed = Signal(str)

    def __init__(self, current_role: str = "Program Yöneticisi", parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self._role = current_role or "Program Yöneticisi"

        self.setStyleSheet(f"""
            QPushButton {{
                background: {bk_ui.SURFACE};
                border: 1.5px solid {bk_ui.HAIRLINE_STRONG};
                border-radius: {bk_ui.R_CONTROL}px;
                padding: 0px;
                text-align: left;
                color: {bk_ui.INK};
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                border-color: {bk_ui.BRAND};
                background: #FFFFFF;
            }}
            QPushButton:pressed {{
                background: {bk_ui.SURFACE_SUNK};
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 2, 12, 2)
        layout.setSpacing(10)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(18, 18)
        self.icon_lbl.setStyleSheet("background: transparent; border: none;")
        self.icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.icon_lbl, 0, Qt.AlignVCenter)

        self.label = QLabel(self._role)
        self.label.setFont(bk_ui.font(9.6, QFont.Medium))
        self.label.setStyleSheet(f"color: {bk_ui.INK}; background: transparent; border: none;")
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.label, 1)

        self.chevron = QLabel()
        self.chevron.setFixedSize(14, 14)
        self.chevron.setStyleSheet("background: transparent; border: none;")
        self.chevron.setPixmap(bk_ui.chevron_glyph(bk_ui.INK_FAINT, 13, "down"))
        self.chevron.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.chevron, 0, Qt.AlignVCenter)

        self.clicked.connect(self._open_menu)
        self._update_icon()

    def currentText(self):
        return self._role

    def setRole(self, role: str):
        self._role = role
        self.label.setText(role)
        self._update_icon()
        self.role_changed.emit(role)

    def _update_icon(self):
        if "Müdür" in self._role:
            glyph = bk_ui.building_glyph(bk_ui.BRAND, 16)
        elif "Öğretmen" in self._role or "Zümre" in self._role:
            glyph = bk_ui.person_glyph(bk_ui.BRAND, 16)
        elif "Bilişim" in self._role or "Sistem" in self._role:
            glyph = bk_ui.settings_glyph(bk_ui.BRAND, 16)
        else:
            glyph = bk_ui.star_glyph(bk_ui.BRAND, 16)
        self.icon_lbl.setPixmap(glyph)

    def _open_menu(self):
        menu = bk_ui.HeroPopoverMenu(self)
        menu.card.setFixedWidth(280)

        for title in STATIC_TITLES:
            if title == "Diğer":
                menu.add_separator()
                menu.add_action("Diğer (Özel Unvan)...", bk_ui.pencil_glyph(bk_ui.BRAND, 16),
                                on_click=self._on_custom_role)
            else:
                is_selected = (title == self._role)
                if "Müdür" in title:
                    glyph = bk_ui.building_glyph(bk_ui.BRAND if is_selected else bk_ui.INK_SOFT, 16)
                elif "Öğretmen" in title or "Zümre" in title:
                    glyph = bk_ui.person_glyph(bk_ui.BRAND if is_selected else bk_ui.INK_SOFT, 16)
                elif "Bilişim" in title or "Sistem" in title:
                    glyph = bk_ui.settings_glyph(bk_ui.BRAND if is_selected else bk_ui.INK_SOFT, 16)
                else:
                    glyph = bk_ui.star_glyph(bk_ui.BRAND if is_selected else bk_ui.INK_SOFT, 16)

                menu.add_action(title, glyph, on_click=lambda t=title: self.setRole(t),
                                checkable=True, checked=is_selected)

        menu.popup_below(self, align="left", offset_y=4)

    def _on_custom_role(self):
        from dialogs.institution_dialogs import AppleInputDialog
        dlg = AppleInputDialog("Özel Unvan", "Görevinizi veya unvanınızı yazın:", default_text=self._role, parent=self.window())
        if dlg.exec() == QDialog.Accepted and dlg.text_value().strip():
            self.setRole(dlg.text_value().strip())


class AppleProfileDialog(bk_ui.HeroSheetDialog):
    """Profile, on the program's one sheet."""

    profile_updated = Signal(str, str, str)  # name, avatar_url, title

    def __init__(self, current_email: str = "admin@bgz.local", parent=None):
        self.email = current_email
        self.profile_data = get_user_profile(current_email)
        self.current_avatar_url = self.profile_data.get("avatar_url", "")
        self.selected_local_file = ""

        super().__init__(parent, width=470, height=452,
                         title="Profili Düzenle",
                         subtitle="Adınız ve unvanınız her ekranda görünür.")
        self.setWindowTitle("Profili Düzenle")
        self._build_ui()

    def _build_ui(self):
        lay = self.card_layout

        # -- avatar ----------------------------------------------------
        avatar_box = QHBoxLayout()
        avatar_box.setSpacing(16)

        self.avatar_preview = QLabel()
        self.avatar_preview.setFixedSize(64, 64)
        self._update_avatar_preview()
        avatar_box.addWidget(self.avatar_preview)

        av_col = QVBoxLayout()
        av_col.setSpacing(5)
        av_col.addStretch(1)

        self.btn_change_photo = bk_ui.secondary_button("Fotoğraf Seç", height=34)
        self.btn_change_photo.setFont(bk_ui.font(9.2, QFont.DemiBold))
        self.btn_change_photo.clicked.connect(self._select_photo)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.btn_change_photo)
        row.addStretch(1)
        av_col.addLayout(row)

        self.upload_status_lbl = QLabel("JPG veya PNG, en az 128×128 piksel")
        self.upload_status_lbl.setFont(bk_ui.font(8.6))
        self.upload_status_lbl.setStyleSheet(
            f"color: {bk_ui.INK_FAINT}; border: none; background: transparent;")
        av_col.addWidget(self.upload_status_lbl)
        av_col.addStretch(1)

        avatar_box.addLayout(av_col, 1)
        lay.addLayout(avatar_box)
        lay.addSpacing(4)

        # -- name ------------------------------------------------------
        lay.addWidget(bk_ui.field_label("Ad Soyad"))
        self.name_edit = bk_ui.Field(height=40, font_px=13)
        self.name_edit.setText(self.profile_data.get("name", ""))
        self.name_edit.textChanged.connect(lambda *_: self._update_avatar_preview())
        lay.addWidget(self.name_edit)

        # -- title (Modern Role Picker) --------------------------------
        lay.addWidget(bk_ui.field_label("Unvan / Görev"))
        cur_title = self.profile_data.get("title", "Program Yöneticisi")
        self.title_combo = AppleRolePickerButton(current_role=cur_title, parent=self)
        lay.addWidget(self.title_combo)

        self.add_footer("Profili Kaydet", "Vazgeç", on_confirm=self._save_profile)
        self.btn_save = self.btn_confirm     # old name, same button

    def _update_avatar_preview(self):
        name = self.name_edit.text() if hasattr(self, "name_edit") else self.profile_data.get("name", "U")
        parts = [p for p in name.strip().split() if p]
        initials = (parts[0][0] + parts[1][0]) if len(parts) >= 2 else (parts[0][:2] if parts else "U")
        
        img_src = self.selected_local_file or self.current_avatar_url
        pix = make_circular_avatar_pixmap(img_src, initials, size=64)
        self.avatar_preview.setPixmap(pix)
        
    def _select_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Profil Fotoğrafı Seç", "", "Görseller (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not file_path:
            return
            
        self.selected_local_file = file_path
        self._update_avatar_preview()
        
        # Start Cloudinary upload
        self.btn_change_photo.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.upload_status_lbl.setText("Fotoğraf yükleniyor...")
        self.upload_status_lbl.setStyleSheet("color: #0071E3; font-weight: bold; border: none;")
        
        self.worker = CloudinaryUploadWorker(file_path, self)
        self.worker.finished.connect(self._on_upload_finished)
        self.worker.failed.connect(self._on_upload_failed)
        self.worker.start()
        
    def _on_upload_finished(self, secure_url: str):
        self.current_avatar_url = secure_url
        self.selected_local_file = ""
        self._update_avatar_preview()
        self.upload_status_lbl.setText("Fotoğraf başarıyla yüklendi")
        self.upload_status_lbl.setStyleSheet("color: #059669; font-weight: bold; border: none;")
        self.btn_change_photo.setEnabled(True)
        self.btn_save.setEnabled(True)
        
    def _on_upload_failed(self, error_msg: str):
        self.upload_status_lbl.setText(f"Yükleme hatası: {error_msg[:35]}...")
        self.upload_status_lbl.setStyleSheet("color: #EF4444; border: none;")
        self.btn_change_photo.setEnabled(True)
        self.btn_save.setEnabled(True)

    def _save_profile(self):
        name = self.name_edit.text().strip() or "Kullanıcı"
        title = self.title_combo.currentText().strip() or "Program Yöneticisi"
        
        save_user_profile(
            email=self.email,
            name=name,
            avatar_url=self.current_avatar_url,
            title=title
        )
        self.profile_updated.emit(name, self.current_avatar_url, title)
        self.accept()


# ── Password Reset / Security Dialog ─────────────────────────────────

class AppleChangePasswordDialog(bk_ui.HeroSheetDialog):
    """Change password with Apple HIG styling, live criteria checklist, and eye icon toggle."""

    password_changed = Signal()

    def __init__(self, user_email: str = None, parent=None):
        self.user_email = user_email or ""
        super().__init__(parent, width=460, height=450,
                         title="Hesap Şifresini Belirle",
                         subtitle="Yeni şifrenizi belirleyin; diğer cihazlardaki "
                                  "oturumlar güvenliğiniz için sonlandırılır.")
        self.setWindowTitle("Şifre Sıfırla & Güvenlik")
        self._build_ui()

    def _pwd_field(self, placeholder):
        f = bk_ui.Field(placeholder, height=40, font_px=13)
        f.setEchoMode(QLineEdit.Password)
        f._pad_right = 44
        f._restyle()

        btn = QPushButton(f)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setFixedSize(30, 30)
        btn.setIcon(QIcon(bk_ui.eye_glyph(bk_ui.INK_SOFT, 16)))
        btn.setIconSize(QSize(16, 16))
        btn.setToolTip("Şifreyi Göster / Gizle")
        btn.setStyleSheet("""
            QPushButton {
                border: none; background: transparent; padding: 0px; border-radius: 6px;
            }
            QPushButton:hover { background: rgba(0, 0, 0, 0.05); }
        """)

        def _flip():
            show = f.echoMode() == QLineEdit.Password
            f.setEchoMode(QLineEdit.Normal if show else QLineEdit.Password)
            if show:
                btn.setIcon(QIcon(bk_ui.eye_slash_glyph(bk_ui.BRAND, 16)))
            else:
                btn.setIcon(QIcon(bk_ui.eye_glyph(bk_ui.INK_SOFT, 16)))

        btn.clicked.connect(_flip)

        def _place(_event=None):
            btn.move(f.width() - btn.width() - 6, (f.height() - btn.height()) // 2)

        f.resizeEvent = lambda e: (bk_ui.Field.resizeEvent(f, e), _place())
        _place()
        return f

    def _build_ui(self):
        lay = self.card_layout

        lay.addWidget(bk_ui.field_label("Yeni Şifre"))
        self.new_pwd_edit = self._pwd_field("Yeni şifrenizi girin")
        self.new_pwd_edit.textChanged.connect(self._update_criteria)
        lay.addWidget(self.new_pwd_edit)

        lay.addWidget(bk_ui.field_label("Yeni Şifre (Tekrar)"))
        self.conf_pwd_edit = self._pwd_field("Yeni şifreyi tekrar girin")
        self.conf_pwd_edit.textChanged.connect(self._update_criteria)
        lay.addWidget(self.conf_pwd_edit)

        # ── Live Password Criteria Checklist ─────────────────────────
        crit_box = QFrame()
        crit_box.setStyleSheet(f"""
            QFrame {{
                background: {bk_ui.SURFACE_SUNK};
                border: 1px solid {bk_ui.HAIRLINE};
                border-radius: 10px;
            }}
        """)
        crit_lay = QVBoxLayout(crit_box)
        crit_lay.setContentsMargins(12, 10, 12, 10)
        crit_lay.setSpacing(6)

        def _crit_row(label_text):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)

            dot = QLabel("○")
            dot.setFont(bk_ui.font(8.8, QFont.Bold))
            dot.setFixedWidth(16)
            dot.setAlignment(Qt.AlignCenter)
            dot.setStyleSheet(f"color: {bk_ui.INK_FAINT}; background: transparent; border: none;")
            row.addWidget(dot)

            lbl = QLabel(label_text)
            lbl.setFont(bk_ui.font(8.6))
            lbl.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent; border: none;")
            row.addWidget(lbl, 1)
            crit_lay.addLayout(row)
            return dot, lbl

        self.crit_len_dot, self.crit_len_lbl = _crit_row("En az 6 karakter")
        self.crit_mix_dot, self.crit_mix_lbl = _crit_row("En az bir harf ve bir rakam")
        self.crit_match_dot, self.crit_match_lbl = _crit_row("Şifreler birbiriyle eşleşiyor")

        lay.addWidget(crit_box)

        # Status Line
        self.status_lbl = QLabel("")
        self.status_lbl.setFont(bk_ui.font(9.0))
        self.status_lbl.setFixedHeight(18)
        self.status_lbl.setStyleSheet(
            f"color: {bk_ui.DANGER}; font-weight: 600; border: none; background: transparent;")
        self.status_lbl.hide()
        lay.addWidget(self.status_lbl)

        self.add_footer("Şifreyi Güncelle", "Vazgeç",
                        on_confirm=self._do_change_password)
        self.btn_submit = self.btn_confirm

    def _update_criteria(self):
        new_p = self.new_pwd_edit.text()
        conf_p = self.conf_pwd_edit.text()

        # 1. Length
        c_len = len(new_p) >= 6
        self._set_crit_state(self.crit_len_dot, self.crit_len_lbl, c_len)

        # 2. Letter and digit
        has_letter = any(c.isalpha() for c in new_p)
        has_digit = any(c.isdigit() for c in new_p)
        c_mix = has_letter and has_digit
        self._set_crit_state(self.crit_mix_dot, self.crit_mix_lbl, c_mix)

        # 3. Match
        c_match = bool(new_p and conf_p and new_p == conf_p)
        self._set_crit_state(self.crit_match_dot, self.crit_match_lbl, c_match)

        if self.status_lbl.isVisible():
            self.status_lbl.hide()

    def _set_crit_state(self, dot_lbl, text_lbl, satisfied: bool):
        if satisfied:
            dot_lbl.setText("✓")
            dot_lbl.setStyleSheet("color: #059669; font-weight: bold; background: transparent; border: none;")
            text_lbl.setStyleSheet("color: #059669; font-weight: 500; background: transparent; border: none;")
        else:
            dot_lbl.setText("○")
            dot_lbl.setStyleSheet(f"color: {bk_ui.INK_FAINT}; font-weight: normal; background: transparent; border: none;")
            text_lbl.setStyleSheet(f"color: {bk_ui.INK_SOFT}; font-weight: normal; background: transparent; border: none;")

    def _do_change_password(self):
        new_p = self.new_pwd_edit.text().strip()
        conf_p = self.conf_pwd_edit.text().strip()

        if not new_p:
            self._show_error("Lütfen yeni şifrenizi girin.")
            return
        if len(new_p) < 6:
            self._show_error("Yeni şifre en az 6 karakter olmalıdır.")
            return
        if new_p != conf_p:
            self._show_error("Yeni şifreler birbiriyle eşleşmiyor.")
            return

        from api_client import api_client
        email = self.user_email
        if not email:
            stored = api_client.get_stored_auth_data() or {}
            email = stored.get("email", "")

        self.btn_submit.setEnabled(False)
        self.status_lbl.setText("Şifre güncelleniyor...")
        self.status_lbl.setStyleSheet("color: #0071E3; font-weight: 500; border: none;")
        self.status_lbl.show()
        QApplication.processEvents()

        ok, msg = api_client.change_password(email, "", new_p)
        if not ok:
            self._show_error(msg)
            self.btn_submit.setEnabled(True)
            return

        self.status_lbl.setText("✓ " + msg)
        self.status_lbl.setStyleSheet("color: #059669; font-weight: bold; border: none;")
        self.status_lbl.show()
        self.password_changed.emit()

        from PySide6.QtCore import QTimer
        QTimer.singleShot(1000, self.accept)

    def _show_error(self, text: str):
        self.status_lbl.setText("⚠ " + text)
        self.status_lbl.setStyleSheet("color: #EF4444; font-weight: 500; border: none;")
        self.status_lbl.show()
