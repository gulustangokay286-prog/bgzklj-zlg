"""
dialogs/notifications_dialog.py – Bildirimler ve Sistem Günlükleri Penceresi
Apple Human Interface Guidelines uyumlu, minimalist ve gerçek zamanlı bildirim merkezi.
"""
import os
import json
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, QLabel, 
    QPushButton, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"

def _get_notifications_file():
    base = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "notifications.json")

def load_notifications() -> list:
    path = _get_notifications_file()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []

def save_notifications(items: list):
    path = _get_notifications_file()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def add_system_notification(title: str, message: str, tag: str = "Sistem", tag_color: str = "#0071E3", tag_bg: str = "#EFF6FF"):
    items = load_notifications()
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    items.insert(0, {
        "title": title,
        "message": message,
        "time": now_str,
        "tag": tag,
        "tag_color": tag_color,
        "tag_bg": tag_bg
    })
    items = items[:50]
    save_notifications(items)


class AppleNotificationsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bildirimler")
        self.resize(520, 480)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #F8FAFC;
                font-family: {FONT_FAMILY};
            }}
        """)
        self.notifications = load_notifications()
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        
        # Header Row
        hdr_box = QHBoxLayout()
        title_lbl = QLabel("Bildirim Merkezi")
        title_lbl.setFont(QFont(FONT_FAMILY, 15, QFont.Bold))
        title_lbl.setStyleSheet("color: #0F172A;")
        hdr_box.addWidget(title_lbl)
        hdr_box.addStretch(1)
        
        count = len(self.notifications)
        if count > 0:
            count_lbl = QLabel(f"{count} Yeni")
            count_lbl.setFont(QFont(FONT_FAMILY, 8.5, QFont.Bold))
            count_lbl.setStyleSheet("background: #E0E7FF; color: #4338CA; padding: 3px 10px; border-radius: 10px;")
            hdr_box.addWidget(count_lbl)
        layout.addLayout(hdr_box)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: transparent; width: 6px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1; border-radius: 3px; min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #94A3B8; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.setSpacing(10)
        
        if not self.notifications:
            empty_frame = QFrame()
            empty_frame.setStyleSheet("background: #FFFFFF; border: 1px dashed #CBD5E1; border-radius: 12px; padding: 36px;")
            e_lay = QVBoxLayout(empty_frame)
            e_lay.setAlignment(Qt.AlignCenter)
            
            e_txt = QLabel("Henüz okunmamış bildirim bulunmuyor.")
            e_txt.setFont(QFont(FONT_FAMILY, 11))
            e_txt.setStyleSheet("color: #64748B; font-weight: 500;")
            e_txt.setAlignment(Qt.AlignCenter)
            e_lay.addWidget(e_txt)
            
            self.cards_layout.addWidget(empty_frame)
        else:
            for item in self.notifications:
                card = QFrame()
                card.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px; }")
                c_lay = QVBoxLayout(card)
                c_lay.setSpacing(6)
                
                top_row = QHBoxLayout()
                t_lbl = QLabel(item.get("title", "Bildirim"))
                t_lbl.setFont(QFont(FONT_FAMILY, 10.5, QFont.Bold))
                t_lbl.setStyleSheet("color: #0F172A; border: none;")
                top_row.addWidget(t_lbl)
                top_row.addStretch(1)
                
                tag_txt = item.get("tag", "Bilgi")
                tag_color = item.get("tag_color", "#0071E3")
                tag_bg = item.get("tag_bg", "#EFF6FF")
                tag = QLabel(tag_txt)
                tag.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
                tag.setStyleSheet(f"background: {tag_bg}; color: {tag_color}; padding: 2px 8px; border-radius: 6px; border: none;")
                top_row.addWidget(tag)
                c_lay.addLayout(top_row)
                
                m_lbl = QLabel(item.get("message", ""))
                m_lbl.setFont(QFont(FONT_FAMILY, 9))
                m_lbl.setStyleSheet("color: #64748B; border: none; line-height: 1.3;")
                m_lbl.setWordWrap(True)
                c_lay.addWidget(m_lbl)
                
                time_lbl = QLabel(item.get("time", ""))
                time_lbl.setFont(QFont(FONT_FAMILY, 8))
                time_lbl.setStyleSheet("color: #94A3B8; border: none;")
                c_lay.addWidget(time_lbl)
                
                self.cards_layout.addWidget(card)
            
        self.cards_layout.addStretch(1)
        scroll.setWidget(self.container)
        layout.addWidget(scroll, 1)
        
        # Bottom Buttons
        b_lay = QHBoxLayout()
        
        if self.notifications:
            btn_clear = QPushButton("Tümünü Temizle")
            btn_clear.setFont(QFont(FONT_FAMILY, 9, QFont.DemiBold))
            btn_clear.setFixedHeight(34)
            btn_clear.setCursor(Qt.PointingHandCursor)
            btn_clear.setStyleSheet("""
                QPushButton {
                    background: #F1F5F9; color: #64748B; border: 1px solid #CBD5E1;
                    border-radius: 17px; padding: 0 18px; font-weight: 500;
                }
                QPushButton:hover { background: #E2E8F0; color: #0F172A; }
            """)
            btn_clear.clicked.connect(self._clear_notifications)
            b_lay.addWidget(btn_clear)
        
        b_lay.addStretch(1)
        
        btn_close = QPushButton("Kapat")
        btn_close.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        btn_close.setFixedHeight(34)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 17px; padding: 0 24px; font-weight: 600;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        btn_close.clicked.connect(self.accept)
        b_lay.addWidget(btn_close)
        
        layout.addLayout(b_lay)

