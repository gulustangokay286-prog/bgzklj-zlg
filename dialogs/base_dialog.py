"""
dialogs/base_dialog.py  –  All definition dialogs share this base
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor


class BaseDialog(QDialog):
    """aSc-style dialog with blue header and OK/Cancel footer"""
    def __init__(self, title: str, icon_key: str = "bilgi", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(600)
        self._build_frame(title)

    def _build_frame(self, title: str):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header = QWidget(self)
        header.setFixedHeight(44)
        header.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1E6DB5, stop:1 #2E86DE); color: white;"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 0, 12, 0)
        lbl = QLabel(title, header)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl.setStyleSheet("color: white;")
        hl.addWidget(lbl)
        outer.addWidget(header)

        # Content area (subclass fills this)
        self.content_widget = QWidget(self)
        self.content_widget.setStyleSheet("background: #FAFAFA;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(12, 12, 12, 8)
        outer.addWidget(self.content_widget, 1)

        # Footer
        footer = QWidget(self)
        footer.setFixedHeight(46)
        footer.setStyleSheet("background: #F0F0F0; border-top: 1px solid #DDD;")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(12, 6, 12, 6)
        fl.addStretch(1)

        self.ok_btn = QPushButton("Tamam", footer)
        self.ok_btn.setFixedSize(90, 30)
        self.ok_btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.ok_btn.setStyleSheet(
            "QPushButton { background:#1E6DB5; color:white; border:none; border-radius:4px;}"
            "QPushButton:hover { background:#1557A0; }"
        )
        self.ok_btn.clicked.connect(self._on_ok)

        self.cancel_btn = QPushButton("İptal", footer)
        self.cancel_btn.setFixedSize(80, 30)
        self.cancel_btn.setFont(QFont("Segoe UI", 9))
        self.cancel_btn.setStyleSheet(
            "QPushButton { background:#F0F0F0; color:#333; border:1px solid #CCC; border-radius:4px;}"
            "QPushButton:hover { background:#E0E0E0; }"
        )
        self.cancel_btn.clicked.connect(self.reject)

        fl.addWidget(self.ok_btn)
        fl.addWidget(self.cancel_btn)
        outer.addWidget(footer)

    def _on_ok(self):
        self.accept()
