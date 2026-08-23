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
    QFileDialog, QWidget, QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QPixmap, QPainter, QPainterPath, QColor, QBrush, QPen

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"

# ── Cloudinary Configuration (IAL Projesi Entegrasyonu) ───────────────
CLOUDINARY_CLOUD_NAME = "dbfhcj6px"
CLOUDINARY_UPLOAD_PRESET = "ml_default"
CLOUDINARY_FOLDER = "profiles"
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


class AppleProfileDialog(QDialog):
    profile_updated = Signal(str, str)  # name, avatar_url
    
    def __init__(self, current_email: str = "admin@bgz.local", parent=None):
        super().__init__(parent)
        self.email = current_email
        self.profile_data = get_user_profile(current_email)
        self.current_avatar_url = self.profile_data.get("avatar_url", "")
        self.selected_local_file = ""
        
        self.setWindowTitle("Profili Düzenle")
        self.setFixedSize(460, 480)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        container = QWidget(self)
        container.setObjectName("profileCard")
        container.setStyleSheet("""
            #profileCard {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 20px;
            }
        """)
        
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(28, 24, 28, 24)
        c_lay.setSpacing(14)
        
        # Header
        t_lbl = QLabel("Kullanıcı Profilini Düzenle")
        t_lbl.setFont(QFont(FONT_FAMILY, 13, QFont.Bold))
        t_lbl.setStyleSheet("color: #0F172A; border: none; background: transparent;")
        c_lay.addWidget(t_lbl)
        
        sub_lbl = QLabel("Adınız, unvanınız ve Cloudinary destekli profil fotoğrafınız.")
        sub_lbl.setFont(QFont(FONT_FAMILY, 9))
        sub_lbl.setStyleSheet("color: #64748B; border: none; background: transparent;")
        c_lay.addWidget(sub_lbl)
        
        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: #E2E8F0; border: none;")
        c_lay.addWidget(div)
        
        # Avatar Row
        avatar_box = QHBoxLayout()
        avatar_box.setSpacing(16)
        
        self.avatar_preview = QLabel()
        self.avatar_preview.setFixedSize(68, 68)
        self._update_avatar_preview()
        avatar_box.addWidget(self.avatar_preview)
        
        av_btns_layout = QVBoxLayout()
        av_btns_layout.setSpacing(4)
        
        self.btn_change_photo = QPushButton("Fotoğraf Seç & Yükle")
        self.btn_change_photo.setFont(QFont(FONT_FAMILY, 9, QFont.DemiBold))
        self.btn_change_photo.setFixedHeight(32)
        self.btn_change_photo.setCursor(Qt.PointingHandCursor)
        self.btn_change_photo.setStyleSheet("""
            QPushButton {
                background: #EFF6FF; color: #0071E3; border: 1px solid #BFDBFE;
                border-radius: 16px; padding: 0 16px; font-weight: 600;
            }
            QPushButton:hover { background: #DBEAFE; }
        """)
        self.btn_change_photo.clicked.connect(self._select_photo)
        av_btns_layout.addWidget(self.btn_change_photo)
        
        self.upload_status_lbl = QLabel("Cloudinary CDN ile senkronize edilir")
        self.upload_status_lbl.setFont(QFont(FONT_FAMILY, 8))
        self.upload_status_lbl.setStyleSheet("color: #94A3B8; border: none;")
        av_btns_layout.addWidget(self.upload_status_lbl)
        
        avatar_box.addLayout(av_btns_layout, 1)
        c_lay.addLayout(avatar_box)
        
        # Field 1: Full Name
        name_title = QLabel("AD SOYAD *")
        name_title.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        name_title.setStyleSheet("color: #64748B; letter-spacing: 0.5px; border: none;")
        c_lay.addWidget(name_title)
        
        self.name_edit = QLineEdit(self.profile_data.get("name", "Seher Şanlı"))
        self.name_edit.setFixedHeight(36)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background: #F8FAFC; border: 1.5px solid #CBD5E1;
                border-radius: 8px; padding: 4px 12px; font-size: 13px; color: #0F172A;
            }
            QLineEdit:focus { border: 1.5px solid #0071E3; background: #FFFFFF; }
        """)
        c_lay.addWidget(self.name_edit)
        
        # Field 2: Role / Title
        title_title = QLabel("UNVAN / BRANŞ")
        title_title.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
        title_title.setStyleSheet("color: #64748B; letter-spacing: 0.5px; border: none;")
        c_lay.addWidget(title_title)
        
        self.title_edit = QLineEdit(self.profile_data.get("title", "Program Yöneticisi"))
        self.title_edit.setFixedHeight(36)
        self.title_edit.setStyleSheet("""
            QLineEdit {
                background: #F8FAFC; border: 1.5px solid #CBD5E1;
                border-radius: 8px; padding: 4px 12px; font-size: 13px; color: #0F172A;
            }
            QLineEdit:focus { border: 1.5px solid #0071E3; background: #FFFFFF; }
        """)
        c_lay.addWidget(self.title_edit)
        
        # Bottom Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        
        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setFont(QFont(FONT_FAMILY, 9, QFont.DemiBold))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F1F5F9; color: #1E293B; border: 1px solid #CBD5E1;
                border-radius: 18px; padding: 0 20px; font-weight: 500;
            }
            QPushButton:hover { background: #E2E8F0; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        
        self.btn_save = QPushButton("Profili Kaydet")
        self.btn_save.setFixedHeight(36)
        self.btn_save.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 18px; padding: 0 24px; font-weight: 600;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        self.btn_save.clicked.connect(self._save_profile)
        btn_box.addWidget(self.btn_save)
        
        c_lay.addLayout(btn_box)
        layout.addWidget(container)
        
    def _update_avatar_preview(self):
        name = self.name_edit.text() if hasattr(self, "name_edit") else self.profile_data.get("name", "U")
        parts = [p for p in name.strip().split() if p]
        initials = (parts[0][0] + parts[1][0]) if len(parts) >= 2 else (parts[0][:2] if parts else "U")
        
        img_src = self.selected_local_file or self.current_avatar_url
        pix = make_circular_avatar_pixmap(img_src, initials, size=68)
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
        self.upload_status_lbl.setText("Cloudinary'e yükleniyor...")
        self.upload_status_lbl.setStyleSheet("color: #0071E3; font-weight: bold; border: none;")
        
        self.worker = CloudinaryUploadWorker(file_path, self)
        self.worker.finished.connect(self._on_upload_finished)
        self.worker.failed.connect(self._on_upload_failed)
        self.worker.start()
        
    def _on_upload_finished(self, secure_url: str):
        self.current_avatar_url = secure_url
        self.selected_local_file = ""
        self._update_avatar_preview()
        self.upload_status_lbl.setText("Görsel Cloudinary CDN'e yüklendi")
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
        title = self.title_edit.text().strip() or "Program Yöneticisi"
        
        save_user_profile(
            email=self.email,
            name=name,
            avatar_url=self.current_avatar_url,
            title=title
        )
        self.profile_updated.emit(name, self.current_avatar_url)
        self.accept()
