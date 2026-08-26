"""
advisor_dialog.py — the window behind the "Danışman" button.

Shows advisor.analyse() as a readable list. It reports the arithmetic, not a verdict:
the user has repeatedly (and correctly) insisted the program should explain and warn
rather than block, so nothing here refuses to do anything.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout,
    QWidget,
)

import advisor

STYLES = {
    "error":   ("#DC2626", "#FEF2F2", "#FECACA", "Sorun"),
    "warning": ("#D97706", "#FFFBEB", "#FDE68A", "Uyarı"),
    "info":    ("#0284C7", "#F0F9FF", "#BAE6FD", "Bilgi"),
}


class AdvisorDialog(QDialog):
    def __init__(self, data_store, parent=None):
        super().__init__(parent)
        self.data_store = data_store if data_store is not None else {}
        self.setWindowTitle("Danışman — Çizelge Analizi")
        self.resize(760, 620)
        self.setStyleSheet("QDialog { background: #F8FAFC; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        self.header = QLabel()
        self.header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.header.setStyleSheet("color: #0F172A;")
        layout.addWidget(self.header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        self._holder = QWidget()
        self._holder.setStyleSheet("background: transparent;")
        self._list = QVBoxLayout(self._holder)
        self._list.setContentsMargins(0, 0, 6, 0)
        self._list.setSpacing(10)
        scroll.setWidget(self._holder)
        layout.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        refresh = QPushButton("Yeniden Analiz Et")
        refresh.setStyleSheet(
            "QPushButton { background: #FFFFFF; color: #475569; border: 1px solid #CBD5E1;"
            " border-radius: 6px; padding: 8px 16px; font-weight: bold; }"
            "QPushButton:hover { background: #F1F5F9; }")
        refresh.clicked.connect(self._reload)
        buttons.addWidget(refresh)
        buttons.addStretch(1)
        close = QPushButton("Kapat")
        close.setStyleSheet(
            "QPushButton { background: #2563EB; color: white; border: none;"
            " border-radius: 6px; padding: 8px 20px; font-weight: bold; }"
            "QPushButton:hover { background: #1D4ED8; }")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)

        self._reload()

    def _reload(self):
        while self._list.count():
            item = self._list.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

        try:
            findings = advisor.analyse(self.data_store)
        except Exception as exc:                    # analysis must never crash the app
            findings = [("error", "Analiz yapılamadı", str(exc), "")]

        errors = sum(1 for f in findings if f[0] == "error")
        warnings = sum(1 for f in findings if f[0] == "warning")
        if errors:
            self.header.setText(f"{errors} sorun, {warnings} uyarı bulundu")
        elif warnings:
            self.header.setText(f"{warnings} uyarı bulundu — engelleyici sorun yok")
        else:
            self.header.setText("Çizelge temiz görünüyor")

        for severity, title, detail, action in findings:
            self._list.addWidget(self._card(severity, title, detail, action))
        self._list.addStretch(1)

    def _card(self, severity, title, detail, action):
        color, bg, border, tag = STYLES.get(severity, STYLES["info"])
        card = QFrame()
        card.setStyleSheet(
            f".QFrame {{ background: {bg}; border: 1px solid {border}; border-radius: 8px; }}")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        top = QHBoxLayout()
        chip = QLabel(tag)
        chip.setStyleSheet(
            f"background: {color}; color: white; border-radius: 4px;"
            f" padding: 2px 8px; font-size: 11px; font-weight: bold;")
        top.addWidget(chip, 0, Qt.AlignTop)
        head = QLabel(title)
        head.setWordWrap(True)
        head.setFont(QFont("Segoe UI", 10, QFont.Bold))
        head.setStyleSheet("color: #0F172A;")
        top.addWidget(head, 1)
        lay.addLayout(top)

        if detail:
            body = QLabel(detail)
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextSelectableByMouse)
            body.setStyleSheet("color: #334155; font-size: 12px;")
            lay.addWidget(body)

        if action:
            act = QLabel("→ " + action)
            act.setWordWrap(True)
            act.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
            lay.addWidget(act)

        return card
