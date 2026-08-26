"""dialogs/days_dialog.py — Çalışma Günleri ve Tatil Günleri Özelleştirme Penceresi (Apple Studio Minimalist UI)"""
import os
import tempfile
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QFrame, QMessageBox, QWidget
)
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QFont, QColor, QPixmap, QPainter, QPen, QBrush, QIcon, QPainterPath

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"
DAYS_ALL = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def get_checkbox_icon_path(checked: bool) -> str:
    """Renders crisp retina vector checkbox icons for QSS indicators."""
    temp_dir = tempfile.gettempdir()
    name = "chenki_chk_on.png" if checked else "chenki_chk_off.png"
    path = os.path.join(temp_dir, name).replace("\\", "/")
    
    size = 20
    scale = 2
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(scale, scale)
    
    if checked:
        # Filled Blue Rounded Box with White Checkmark
        p.setBrush(QColor("#0071E3"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(1, 1, size - 2, size - 2), 4, 4)
        
        # Crisp White Check
        p.setPen(QPen(QColor("#FFFFFF"), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(QPointF(5.5, size / 2.0 + 0.5), QPointF(8.5, size - 5.5))
        p.drawLine(QPointF(8.5, size - 5.5), QPointF(size - 5.5, 5.5))
    else:
        # Soft Slate Outlined Box
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QPen(QColor("#CBD5E1"), 1.5))
        p.drawRoundedRect(QRectF(1, 1, size - 2, size - 2), 4, 4)
        
    p.end()
    pix.save(path)
    return path


def sync_dialog_data_to_vds(dialog_instance, data_store: dict):
    """Guarantees instant real-time persistence across VDS Cloud, Version files, and Grid UI."""
    win = dialog_instance.window()
    main_win = None
    curr = dialog_instance
    while curr:
        if hasattr(curr, "save_db") and hasattr(curr, "_refresh_grid"):
            main_win = curr
            break
        curr = curr.parent() if hasattr(curr, "parent") else None
        
    if main_win:
        main_win.save_db(sync_from_grid=False)
        main_win._refresh_grid()
        main_win._refresh_tree()
        return

    from database import sync_data_store_to_vds
    sync_data_store_to_vds(data_store)


class DaysAndHolidaysDialog(QDialog):
    """Haftalık Çalışma Günleri ve Tatil Günleri Gelişmiş Seçim Penceresi (Sade Apple Minimalist UI)"""
    def __init__(self, data_store=None, days_count=5, parent=None):
        super().__init__(parent)
        self.data_store = data_store if data_store is not None else {}
        self.days_count = max(1, min(7, int(days_count)))
        
        self.setWindowTitle("Çalışma Günleri Ayarları")
        self.resize(480, 530)
        
        chk_on = get_checkbox_icon_path(True)
        chk_off = get_checkbox_icon_path(False)
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #F8FAFC;
                font-family: {FONT_FAMILY};
                color: #0F172A;
            }}
            QCheckBox {{
                font-size: 13px;
                font-weight: 600;
                color: #1E293B;
                spacing: 12px;
                background: transparent;
                border: none;
                outline: none;
                padding: 0px;
                margin: 0px;
            }}
            QCheckBox:focus {{
                border: none;
                outline: none;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: none;
                outline: none;
            }}
            QCheckBox::indicator:unchecked {{
                image: url({chk_off});
            }}
            QCheckBox::indicator:checked {{
                image: url({chk_on});
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        
        self._build_ui()
        self._load_data()
        self.setFocus()
        
    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)
        
        # 1. Nude Header Area (No Boxes, No Circles)
        head_lay = QVBoxLayout()
        head_lay.setContentsMargins(0, 0, 0, 2)
        head_lay.setSpacing(3)
        
        title_lbl = QLabel("Haftalık Çalışma Günleri")
        title_lbl.setFont(QFont(FONT_FAMILY, 13, QFont.Bold))
        title_lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        head_lay.addWidget(title_lbl)
        
        desc_lbl = QLabel("Çizelgede ders planlaması yapılacak aktif günleri belirleyin.")
        desc_lbl.setFont(QFont(FONT_FAMILY, 9.5))
        desc_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
        head_lay.addWidget(desc_lbl)
        
        lay.addLayout(head_lay)
        
        # 2. Unified Card Box with explicit dividers (No border inheritance to children)
        card = QFrame()
        card.setStyleSheet("""
            QFrame#day_card {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
            }
        """)
        card.setObjectName("day_card")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)
        
        self.day_checks = []
        for i, day_name in enumerate(DAYS_ALL):
            row_w = QWidget()
            row_w.setStyleSheet("background: transparent; border: none;")
            r_lay = QHBoxLayout(row_w)
            r_lay.setContentsMargins(16, 9, 16, 9)
            
            chk = QCheckBox(day_name)
            chk.setFocusPolicy(Qt.NoFocus)
            r_lay.addWidget(chk)
            r_lay.addStretch()
            
            if i >= 5:
                tag = QLabel("Hafta Sonu")
                tag.setStyleSheet("color: #D97706; font-size: 11px; font-weight: 600; background: transparent; border: none;")
                r_lay.addWidget(tag)
            else:
                tag = QLabel("Hafta İçi")
                tag.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500; background: transparent; border: none;")
                r_lay.addWidget(tag)
                
            card_lay.addWidget(row_w)
            self.day_checks.append((day_name, chk))
            
            if i < len(DAYS_ALL) - 1:
                div = QFrame()
                div.setFrameShape(QFrame.HLine)
                div.setStyleSheet("background-color: #E2E8F0; border: none; max-height: 1px; min-height: 1px;")
                card_lay.addWidget(div)
            
        lay.addWidget(card)
        
        # 3. Hızlı Şablonlar (Sade Pill Butonlar)
        tpl_lay = QHBoxLayout()
        tpl_lay.setSpacing(8)
        
        lbl_tpl = QLabel("Hızlı Seçim:")
        lbl_tpl.setFont(QFont(FONT_FAMILY, 9.5, QFont.Bold))
        lbl_tpl.setStyleSheet("color: #64748B; background: transparent; border: none;")
        tpl_lay.addWidget(lbl_tpl)
        
        btn_5d = QPushButton("5 Gün (Pzt - Cuma)")
        btn_5d.setCursor(Qt.PointingHandCursor)
        btn_5d.setFixedHeight(28)
        btn_5d.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                color: #334155;
                border-radius: 14px;
                font-weight: 600;
                font-size: 11px;
                padding: 0 12px;
            }
            QPushButton:hover { background: #F1F5F9; color: #0F172A; }
        """)
        btn_5d.clicked.connect(lambda: self._apply_template(5))
        tpl_lay.addWidget(btn_5d)
        
        btn_6d = QPushButton("6 Gün (+Cumartesi)")
        btn_6d.setCursor(Qt.PointingHandCursor)
        btn_6d.setFixedHeight(28)
        btn_6d.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                color: #334155;
                border-radius: 14px;
                font-weight: 600;
                font-size: 11px;
                padding: 0 12px;
            }
            QPushButton:hover { background: #F1F5F9; color: #0F172A; }
        """)
        btn_6d.clicked.connect(lambda: self._apply_template(6))
        tpl_lay.addWidget(btn_6d)
        
        btn_7d = QPushButton("7 Gün (Tüm Hafta)")
        btn_7d.setCursor(Qt.PointingHandCursor)
        btn_7d.setFixedHeight(28)
        btn_7d.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                color: #334155;
                border-radius: 14px;
                font-weight: 600;
                font-size: 11px;
                padding: 0 12px;
            }
            QPushButton:hover { background: #F1F5F9; color: #0F172A; }
        """)
        btn_7d.clicked.connect(lambda: self._apply_template(7))
        tpl_lay.addWidget(btn_7d)
        
        tpl_lay.addStretch()
        lay.addLayout(tpl_lay)
        
        # 4. Alt Butonlar (Silindirik / Pill)
        bot = QHBoxLayout()
        bot.setSpacing(10)
        bot.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setFixedHeight(34)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                color: #475569;
                border-radius: 17px;
                font-weight: 600;
                font-size: 12px;
                padding: 0 20px;
            }
            QPushButton:hover { background: #F8FAFC; color: #0F172A; }
        """)
        btn_cancel.clicked.connect(self.reject)
        bot.addWidget(btn_cancel)
        
        btn_save = QPushButton("Gün Ayarlarını Kaydet")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setFixedHeight(34)
        btn_save.setStyleSheet("""
            QPushButton {
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 17px;
                font-weight: 700;
                font-size: 12px;
                padding: 0 24px;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        btn_save.clicked.connect(self._save_and_accept)
        bot.addWidget(btn_save)
        
        lay.addLayout(bot)
        
    def _apply_template(self, count):
        for i, (_, chk) in enumerate(self.day_checks):
            chk.setChecked(i < count)
            
    def _load_data(self):
        settings = self.data_store.get("settings", {})
        saved_days = settings.get("active_days_list", [])
        
        if saved_days and len(saved_days) == 7:
            for item in saved_days:
                d_name = item.get("name")
                d_act = item.get("active", True)
                for name, chk in self.day_checks:
                    if name == d_name:
                        chk.setChecked(d_act)
                        break
        else:
            cnt = self.days_count or self.data_store.get("gun_sayisi", 5)
            try:
                cnt = int(cnt)
            except Exception:
                cnt = 5
            self._apply_template(cnt)
            
    def _save_and_accept(self):
        active_days = []
        for i, (name, chk) in enumerate(self.day_checks):
            active_days.append({
                "day_index": i,
                "name": name,
                "active": chk.isChecked()
            })
            
        active_count = sum(1 for d in active_days if d["active"])
        if active_count == 0:
            QMessageBox.warning(self, "Hata", "Lütfen en az bir çalışma günü seçiniz!")
            return
            
        settings = self.data_store.setdefault("settings", {})
        settings["active_days_list"] = active_days
        settings["days_count"] = active_count
        settings["day_count"] = active_count
        settings["days"] = [d["name"] for d in active_days if d["active"]]
        self.data_store["gun_sayisi"] = active_count
        
        if active_count >= 7:
            settings["weekend_option"] = "Hafta Sonu Tatili Yok"
        elif active_count == 6:
            settings["weekend_option"] = "Yalnız Pazar"
        elif active_count == 5:
            settings["weekend_option"] = "Cumartesi - Pazar"
            
        sync_dialog_data_to_vds(self, self.data_store)
        self.accept()
