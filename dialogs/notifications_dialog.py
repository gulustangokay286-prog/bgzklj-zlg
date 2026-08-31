"""
dialogs/notifications_dialog.py – Bildirimler ve Sistem Günlükleri Penceresi
Apple Human Interface Guidelines uyumlu, minimalist ve gerçek zamanlı bildirim merkezi.
"""
import os
import json
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, QLabel, 
    QPushButton, QFrame, QStackedWidget, QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor

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


import bk_ui


class AppleNotificationsDialog(bk_ui.HeroSheetDialog):
    """The notification centre, on the program's one sheet."""

    def __init__(self, parent=None):
        self.notifications = load_notifications()
        super().__init__(parent, width=520, height=480,
                         title="Bildirimler",
                         subtitle="Güncellemeler, güvenlik olayları ve eşitleme sonuçları.")
        self.setWindowTitle("Bildirimler")
        self._build_ui()
        self._render_state()

    def _build_ui(self):
        lay = self.card_layout
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(12)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")

        # ── Page 0: Empty State (Dead-Centered, Unclipped) ────────────
        self.empty_page = bk_ui.EmptyState(
            title="Bildirim Yok",
            message="Güncellemeler, güvenlik olayları ve eşitleme sonuçları burada toplanır.",
            glyph=bk_ui.check_glyph(bk_ui.INK_FAINT, 44)
        )
        self.stack.addWidget(self.empty_page)

        # ── Page 1: List View ─────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 6px; margin: 0; }
            QScrollBar::handle:vertical { background: #D5D5DB; border-radius: 3px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: #A0A0AA; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.setSpacing(0)

        scroll.setWidget(self.container)
        self.stack.addWidget(scroll)

        lay.addWidget(self.stack, 1)

        # ── Footer Separator & Row ───────────────────────────────────
        lay.addWidget(bk_ui.hairline())

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 2, 0, 0)
        footer_row.setSpacing(10)

        self.footer_count_lbl = QLabel("")
        self.footer_count_lbl.setFont(bk_ui.font(8.6))
        self.footer_count_lbl.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent; border: none;")
        footer_row.addWidget(self.footer_count_lbl, 0, Qt.AlignVCenter)
        footer_row.addStretch(1)

        self.btn_cancel = bk_ui.secondary_button("Tümünü Temizle", height=32)
        self.btn_cancel.setFont(bk_ui.font(8.8, QFont.Medium))
        self.btn_cancel.clicked.connect(self._clear_notifications)
        footer_row.addWidget(self.btn_cancel)

        self.btn_confirm = bk_ui.primary_button("Kapat", height=32)
        self.btn_confirm.setFont(bk_ui.font(8.8, QFont.DemiBold))
        self.btn_confirm.clicked.connect(self.accept)
        footer_row.addWidget(self.btn_confirm)

        lay.addLayout(footer_row)

    def _render_state(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.notifications:
            self.stack.setCurrentIndex(0)
            self.btn_cancel.hide()
            self.footer_count_lbl.setText("● Bildirim bulunmuyor")
        else:
            self.stack.setCurrentIndex(1)
            for i, item in enumerate(self.notifications):
                self.cards_layout.addWidget(
                    self._row(item, last=(i == len(self.notifications) - 1)))
            self.cards_layout.addStretch(1)
            self.btn_cancel.show()
            self.footer_count_lbl.setText(f"● {len(self.notifications)} Bildirim")

    def _clear_notifications(self):
        save_notifications([])
        self.notifications = []
        self._render_state()

    def _row(self, item, last=False):
        w = QFrame()
        w.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            + ("" if last else f"border-bottom: 1px solid {bk_ui.HAIRLINE};") + " }")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(2, 10, 2, 10)
        lay.setSpacing(12)

        dot = QLabel()
        dot.setFixedSize(10, 10)
        colour = item.get("tag_color") or bk_ui.BRAND
        dot.setStyleSheet(f"background: {colour}; border: none; border-radius: 5px;")
        dot.setToolTip(item.get("tag", "Bilgi"))
        lay.addWidget(dot, 0, Qt.AlignTop)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(3)

        head = QHBoxLayout()
        head.setSpacing(8)
        t = QLabel(item.get("title", "Bildirim"))
        t.setFont(bk_ui.font(9.6, QFont.DemiBold))
        t.setStyleSheet(f"color: {bk_ui.INK}; border: none; background: transparent;")
        head.addWidget(t)
        head.addStretch(1)
        when = QLabel(item.get("time", ""))
        when.setFont(bk_ui.font(8.4))
        when.setStyleSheet(f"color: {bk_ui.INK_FAINT}; border: none; background: transparent;")
        head.addWidget(when)
        col.addLayout(head)

        m = QLabel(item.get("message", ""))
        m.setFont(bk_ui.font(9.0))
        m.setWordWrap(True)
        m.setStyleSheet(f"color: {bk_ui.INK_SOFT}; border: none; background: transparent;")
        col.addWidget(m)

        lay.addLayout(col, 1)
        return w

