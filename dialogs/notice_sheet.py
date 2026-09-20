"""dialogs/notice_sheet.py — uzun gerekçeli uyarılar için sayfa.

Bu uyarılar QMessageBox'taydı. Kutu, kendisine verilen metni olduğu gibi
kabul edip yüksekliğini ona göre büyütüyor: yüzlerce maddelik bir teşhis
listesi verildiğinde pencere yirmi bin pikselden uzun açılıyor ve ekranda
içeriği boyanmamış kara bir dikdörtgen olarak duruyordu. Sonra metni
kısaltıp dökümü "Ayrıntılar"a taşıdık; kutu küçüldü ama sistem kutusu
olarak kaldı — sarı üçgen, "Show Details..", programın geri kalanıyla
alakasız bir dil.

Bu sayfa aynı bilgiyi programın kendi diliyle veriyor: başlık, iki satır
gerekçe, sayısı belli bir döküm ve tek bir düğme. Döküm kendi kaydırma
alanında; sayfa ne kadar uzun liste gelirse gelsin ekranda kalıyor.
"""
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QVBoxLayout
)

import bk_ui
import ui_icons

WARN = "#C9821A"
INFO = "#0F4AAB"


class NoticeSheet(QDialog):
    """NoticeSheet.show_notice(...) ile çağrılır."""

    def __init__(self, headline="", body="", detail="", kind="warn",
                 detail_label="Ayrıntılar", parent=None):
        super().__init__(parent)
        self._drag_from = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint
                            | Qt.NoDropShadowWindowHint)
        # Saydam değil: içeriği boyanmamış saydam pencere kara görünüyor.
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAutoFillBackground(True)
        self.setStyleSheet("QDialog { background: #FFFFFF; }")
        self.setModal(True)

        accent = WARN if kind == "warn" else INFO

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame(self)
        card.setObjectName("noticeCard")
        card.setStyleSheet("#noticeCard { background: #FFFFFF; border: none; }")
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(0)

        head = QHBoxLayout()
        head.setSpacing(12)
        ico = QLabel()
        ico.setFixedSize(30, 30)
        ico.setPixmap(ui_icons.pixmap("warning" if kind == "warn" else "info", 28, accent))
        ico.setStyleSheet("background: transparent; border: none;")
        head.addWidget(ico, 0, Qt.AlignTop)

        title = QLabel(headline)
        title.setFont(bk_ui.font(13.5, QFont.DemiBold, spacing=-0.2))
        title.setWordWrap(True)
        title.setStyleSheet(f"color: {bk_ui.INK}; background: transparent; border: none;")
        head.addWidget(title, 1)
        lay.addLayout(head)

        if body:
            lay.addSpacing(10)
            sub = QLabel(body)
            sub.setFont(bk_ui.font(9.8))
            sub.setWordWrap(True)
            sub.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent;"
                              " border: none;")
            lay.addWidget(sub)

        self.detail_box = None
        if detail:
            lay.addSpacing(12)
            # Döküm kendi kaydırma alanında: kaç madde olursa olsun sayfa
            # ekranda kalıyor. Sayfanın büyümesine izin veren tek şey
            # buydu.
            self.detail_box = QPlainTextEdit(detail)
            self.detail_box.setReadOnly(True)
            self.detail_box.setFixedHeight(220)
            self.detail_box.setFont(bk_ui.font(9.0))
            self.detail_box.setStyleSheet("""
                QPlainTextEdit {
                    background: #FBFCFD; color: #48505E;
                    border: 1px solid #E7EAF0; border-radius: 12px;
                    padding: 10px;
                }
            """)
            self.detail_box.setVisible(False)
            lay.addWidget(self.detail_box)

        lay.addSpacing(18)
        row = QHBoxLayout()
        row.setSpacing(8)

        if detail:
            self.btn_detail = QPushButton(f"{detail_label} göster")
            self.btn_detail.setCursor(Qt.PointingHandCursor)
            self.btn_detail.setFixedHeight(36)
            self.btn_detail.setFont(bk_ui.font(9.6, QFont.Medium))
            self.btn_detail.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {bk_ui.BRAND};
                    border: none; border-radius: 18px; padding: 0 14px;
                }}
                QPushButton:hover {{ background: rgba(15, 74, 171, 0.07); }}
            """)
            self.btn_detail.clicked.connect(self._toggle_detail)
            row.addWidget(self.btn_detail)

        row.addStretch(1)
        ok = QPushButton("Tamam")
        ok.setCursor(Qt.PointingHandCursor)
        ok.setFixedHeight(36)
        ok.setFont(bk_ui.font(9.8, QFont.DemiBold))
        ok.setStyleSheet(f"""
            QPushButton {{
                background: {accent}; color: #FFFFFF;
                border: none; border-radius: 18px; padding: 0 26px;
            }}
            QPushButton:hover {{ background: {QColor(accent).darker(112).name()}; }}
        """)
        ok.clicked.connect(self.accept)
        ok.setDefault(True)
        row.addWidget(ok)
        lay.addLayout(row)

        self.setFixedWidth(470)

    def _toggle_detail(self):
        shown = self.detail_box.isVisible()
        self.detail_box.setVisible(not shown)
        label = self.btn_detail.text().replace(" göster", "").replace(" gizle", "")
        self.btn_detail.setText(f"{label} {'gizle' if not shown else 'göster'}")
        self.adjustSize()
        self._center_on(self.parent())

    def _center_on(self, parent):
        self.adjustSize()
        ref = None
        if parent is not None:
            try:
                w = parent.window()
                if w is not None and w.isVisible():
                    ref = w.frameGeometry()
            except Exception:
                ref = None
        if ref is None:
            screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
            if screen is None:
                return
            ref = screen.availableGeometry()
        self.move(ref.center() - QPoint(self.width() // 2, self.height() // 2))

    def showEvent(self, e):
        super().showEvent(e)
        if not getattr(self, "_centered", False):
            self._centered = True
            self._center_on(self.parent())

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_from = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_from is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_from)

    def mouseReleaseEvent(self, e):
        self._drag_from = None

    @classmethod
    def show_notice(cls, parent, headline, body="", detail="", kind="warn",
                    detail_label="Ayrıntılar"):
        dlg = cls(headline, body, detail, kind, detail_label, parent)
        dlg.exec()
        return dlg
