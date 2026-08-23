"""
dialogs/notifications_dialog.py – Bildirimler ve Sistem Günlükleri Penceresi
Apple Human Interface Guidelines uyumlu, modern bildirim merkezi.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, QLabel, 
    QPushButton, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"

DEFAULT_NOTIFICATIONS = [
    {
        "title": "Ders Çizelgesi Motoru Hazır",
        "message": "A* Search algoritması 9 sınıf ve tanımlı ders yükleri ile optimize edildi. Tam yerleşim ve çakışmasız planlama devrede.",
        "time": "Bugün, 13:40",
        "tag": "Sistem",
        "tag_color": "#0071E3",
        "tag_bg": "#EFF6FF",
    },
    {
        "title": "Bulut Senkronizasyon Durumu",
        "message": "Tüm kurum ve versiyon verileri yerel veritabanında güvenle yedeklendi. Chenki bulut senkronizasyonu aktif.",
        "time": "Bugün, 12:15",
        "tag": "Bulut",
        "tag_color": "#059669",
        "tag_bg": "#ECFDF5",
    },
    {
        "title": "Kurum Bilgileri ve İzolasyon",
        "message": "Boğaziçi Eğitim Kurumları ve Birey Kurum bağımsız ders programı alanları başarıyla ayrıştırıldı.",
        "time": "Dün, 18:30",
        "tag": "Kurum",
        "tag_color": "#7C3AED",
        "tag_bg": "#F5F3FF",
    },
    {
        "title": "Otomatik Yedekleme",
        "message": "Son yapılan değişiklikler yerel .chenki_akademi/ versiyon havuzunda koruma altına alındı.",
        "time": "Dün, 16:00",
        "tag": "Yedek",
        "tag_color": "#D97706",
        "tag_bg": "#FEF3C7",
    }
]


class AppleNotificationsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bildirimler")
        self.resize(540, 520)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #F8FAFC;
                font-family: {FONT_FAMILY};
            }}
        """)
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        
        # Header Row
        hdr_box = QHBoxLayout()
        title_lbl = QLabel("Bildirimler")
        title_lbl.setFont(QFont(FONT_FAMILY, 15, QFont.Bold))
        title_lbl.setStyleSheet("color: #0F172A;")
        hdr_box.addWidget(title_lbl)
        hdr_box.addStretch(1)
        
        count_lbl = QLabel(f"{len(DEFAULT_NOTIFICATIONS)} Yeni")
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
        
        for item in DEFAULT_NOTIFICATIONS:
            card = QFrame()
            card.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px; }")
            c_lay = QVBoxLayout(card)
            c_lay.setSpacing(6)
            
            top_row = QHBoxLayout()
            t_lbl = QLabel(item["title"])
            t_lbl.setFont(QFont(FONT_FAMILY, 10.5, QFont.Bold))
            t_lbl.setStyleSheet("color: #0F172A; border: none;")
            top_row.addWidget(t_lbl)
            top_row.addStretch(1)
            
            tag = QLabel(item["tag"])
            tag.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
            tag.setStyleSheet(f"background: {item['tag_bg']}; color: {item['tag_color']}; padding: 2px 8px; border-radius: 6px; border: none;")
            top_row.addWidget(tag)
            c_lay.addLayout(top_row)
            
            m_lbl = QLabel(item["message"])
            m_lbl.setFont(QFont(FONT_FAMILY, 9))
            m_lbl.setStyleSheet("color: #64748B; border: none; line-height: 1.3;")
            m_lbl.setWordWrap(True)
            c_lay.addWidget(m_lbl)
            
            time_lbl = QLabel(item["time"])
            time_lbl.setFont(QFont(FONT_FAMILY, 8))
            time_lbl.setStyleSheet("color: #94A3B8; border: none;")
            c_lay.addWidget(time_lbl)
            
            self.cards_layout.addWidget(card)
            
        self.cards_layout.addStretch(1)
        scroll.setWidget(self.container)
        layout.addWidget(scroll, 1)
        
        # Bottom Buttons
        b_lay = QHBoxLayout()
        
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
        
    def _clear_notifications(self):
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        empty_lbl = QLabel("Henüz okunmamış bildirim bulunmuyor.")
        empty_lbl.setFont(QFont(FONT_FAMILY, 10))
        empty_lbl.setStyleSheet("color: #94A3B8; padding: 30px;")
        empty_lbl.setAlignment(Qt.AlignCenter)
        self.cards_layout.addWidget(empty_lbl)
