"""dialogs/reset_schedule_sheet.py — "Çizelgeyi sıfırla" onayı.

Burası bir QMessageBox'tı. Üç düğmeli bir sistem kutusu, soru işareti
ikonuyla: düğme yazıları kutuya sığmadığı için kırpılıyordu
("epsini Kald", "litliler Kals"), hangisinin yıkıcı hangisinin güvenli
olduğu anlaşılmıyordu ve soru işareti sorunun ne olduğunu anlatmıyordu.

Bu sayfa aynı soruyu soruyor ama gösteriyor: izometrik bir çizelge
tablası, üstünde havalanıp dağılan kartlar ve kilitli olduğu için
yerinde duran bir kart. Düğmeler tam boyunda, ağırlıkları yaptıkları işe
göre: kalıcı olan dolu ve kırmızı, korumalı olan dolu ve mavi,
vazgeçmek çıplak yazı.
"""
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QWidget, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor

import bk_ui
import ui_icons

# Dönüş değerleri
CANCEL = "cancel"
KEEP_LOCKED = "keep_locked"
CLEAR_ALL = "clear_all"


class ResetScheduleSheet(QDialog):
    """Sıfırlama onayı. ResetScheduleSheet.ask(...) ile çağrılır."""

    def __init__(self, locked_blocks=0, locked_hours=0, total_hours=0, parent=None):
        super().__init__(parent)
        self.choice = CANCEL
        self._drag_from = None
        # NoDropShadowWindowHint şart: çerçevesiz saydam bir pencereye
        # macOS kendi pencere gölgesini de ekliyordu. Kartın kendi gölgesi
        # zaten var, ikisi üst üste binince kartın etrafında ikinci bir
        # pencere varmış gibi duran gri bir kenar çıkıyordu.
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint
                            | Qt.NoDropShadowWindowHint)
        # SAYDAM DEĞİL: macOS'ta çerçevesiz + saydam bir pencere, alfası
        # çözülemediğinde OPAK SİYAH bir dikdörtgen olarak boyanıyor
        # (bkz. timetable_grid.py başındaki not). Sayfa arka arkaya
        # açılıp kapanırken ekranda siyah kareler kalıyordu. Kart
        # görünümü duruyor; kaybedilen tek şey köşelerin dışındaki
        # saydamlık.
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAutoFillBackground(False)
        # Pencerenin kendi zemini de açıkça şeffaf: WA_TranslucentBackground
        # tek başına stile bırakılan zemini her platformda temizlemiyor ve
        # kartın etrafında beyaz bir bant kalıyordu.
        self.setStyleSheet("QDialog { background: #FFFFFF; }")
        self.setModal(True)

        has_locked = locked_blocks > 0

        outer = QVBoxLayout(self)
        # Kenar payı yalnızca kartın gölgesi için: dar tutuluyor, yoksa
        # şeffaf alan pencere kenarı gibi okunuyor.
        outer.setContentsMargins(16, 14, 16, 16)

        card = QFrame(self)
        card.setObjectName("resetCard")
        card.setStyleSheet("""
            #resetCard {
                background: #FFFFFF;
                border: 1px solid rgba(15, 23, 42, 0.08);
                border-radius: 20px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(34)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(15, 23, 42, 52))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(30, 26, 30, 24)
        lay.setSpacing(0)

        # ── 3B resim ─────────────────────────────────────────────────
        art = QLabel()
        art.setAlignment(Qt.AlignCenter)
        art.setPixmap(bk_ui.reset_schedule_3d(104))
        art.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(art)
        lay.addSpacing(10)

        title = QLabel("Çizelgeyi sıfırla")
        title.setFont(bk_ui.font(14.5, QFont.DemiBold, spacing=-0.2))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {bk_ui.INK}; background: transparent; border: none;")
        lay.addWidget(title)
        lay.addSpacing(6)

        body = ("Yerleştirilmiş derslerin tamamı çizelgeden kaldırılacak."
                if not has_locked else
                "Yerleştirilmiş dersler çizelgeden kaldırılacak.")
        sub = QLabel(body)
        sub.setFont(bk_ui.font(9.6))
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent; border: none;")
        lay.addWidget(sub)

        # ── Kilitli dersler: asıl soru bu ────────────────────────────
        if has_locked:
            lay.addSpacing(14)
            strip = QFrame()
            strip.setStyleSheet("""
                QFrame {
                    background: #FFF8EC;
                    border: 1px solid #F3DFB8;
                    border-radius: 12px;
                }
            """)
            srow = QHBoxLayout(strip)
            srow.setContentsMargins(14, 10, 14, 10)
            srow.setSpacing(10)

            ico = QLabel()
            ico.setPixmap(ui_icons.pixmap("lock", 18, "#B7810F"))
            ico.setFixedSize(18, 18)
            ico.setStyleSheet("background: transparent; border: none;")
            srow.addWidget(ico, 0, Qt.AlignVCenter)

            txt = QLabel(
                f"<b>{locked_blocks} kilitli ders</b> var"
                + (f" ({locked_hours} saat)" if locked_hours != locked_blocks else "")
                + ".<br><span style='color:#8A6D1E;'>Kilitli dersler yerinde bırakılabilir.</span>")
            txt.setFont(bk_ui.font(9.4))
            txt.setTextFormat(Qt.RichText)
            txt.setWordWrap(True)
            txt.setStyleSheet("color: #7A5C10; background: transparent; border: none;")
            srow.addWidget(txt, 1)
            lay.addWidget(strip)

        lay.addSpacing(20)

        # ── Düğmeler ─────────────────────────────────────────────────
        row = QHBoxLayout()
        row.setSpacing(8)

        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setFixedHeight(38)
        btn_cancel.setFont(bk_ui.font(9.6, QFont.Medium))
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {bk_ui.INK_SOFT};
                border: none; border-radius: 19px; padding: 0 16px;
            }}
            QPushButton:hover {{ background: rgba(15, 23, 42, 0.05); color: {bk_ui.INK}; }}
        """)
        btn_cancel.clicked.connect(lambda: self._pick(CANCEL))
        row.addWidget(btn_cancel)
        row.addStretch(1)

        def filled(text, colour, hover, icon_name, icon_colour="#FFFFFF"):
            b = QPushButton(text)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(38)
            b.setFont(bk_ui.font(9.6, QFont.DemiBold))
            b.setIcon(ui_icons.icon(icon_name, 15, icon_colour))
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {colour}; color: #FFFFFF;
                    border: none; border-radius: 19px; padding: 0 20px;
                }}
                QPushButton:hover {{ background: {hover}; }}
            """)
            # Düğmenin gölgesi RENKLİ değil. Kırmızının kendi rengiyle
            # yayılan bir gölge, gölge gibi değil hâle gibi görünüyordu.
            sh = QGraphicsDropShadowEffect(b)
            sh.setBlurRadius(10)
            sh.setOffset(0, 2)
            sh.setColor(QColor(15, 23, 42, 45))
            b.setGraphicsEffect(sh)
            # Qt'nin ölçüsü ikon + yazı + dolgu için kıl payı kalıyor ve son
            # harf kırpılıyordu ("Kalsın" → "Kalsır"). Payı elle veriyoruz.
            b.setMinimumWidth(b.sizeHint().width() + 14)
            return b

        if has_locked:
            btn_all = QPushButton("Hepsini Kaldır")
            btn_all.setCursor(Qt.PointingHandCursor)
            btn_all.setFixedHeight(38)
            btn_all.setFont(bk_ui.font(9.6, QFont.Medium))
            btn_all.setStyleSheet("""
                QPushButton {
                    background: #FFFFFF; color: #B91C1C;
                    border: 1px solid #F3C7C7; border-radius: 19px; padding: 0 18px;
                }
                QPushButton:hover { background: #FEF2F2; border-color: #E9A9A9; }
            """)
            btn_all.setMinimumWidth(btn_all.sizeHint().width() + 10)
            btn_all.clicked.connect(lambda: self._pick(CLEAR_ALL))
            row.addWidget(btn_all)

            btn_keep = filled("Kilitliler Kalsın", bk_ui.BRAND, bk_ui.BRAND_DARK, "lock")
            btn_keep.clicked.connect(lambda: self._pick(KEEP_LOCKED))
            btn_keep.setDefault(True)
            row.addWidget(btn_keep)
        else:
            btn_all = filled("Sıfırla", "#C7392F", "#A22C24", "trash")
            btn_all.clicked.connect(lambda: self._pick(CLEAR_ALL))
            btn_all.setDefault(True)
            row.addWidget(btn_all)

        lay.addLayout(row)
        self.setFixedWidth(492)

    # ── etkileşim ────────────────────────────────────────────────────
    def _pick(self, choice):
        self.choice = choice
        self.accept() if choice != CANCEL else self.reject()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self._pick(CANCEL)
            return
        super().keyPressEvent(e)

    # Çerçevesiz pencere elle taşınır, yoksa ekranın ortasına çakılı kalır.
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_from = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_from is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_from)

    def mouseReleaseEvent(self, e):
        self._drag_from = None

    @classmethod
    def ask(cls, parent, locked_blocks=0, locked_hours=0, total_hours=0):
        """Sheet'i gösterir, seçimi döndürür: CANCEL / KEEP_LOCKED / CLEAR_ALL."""
        dlg = cls(locked_blocks, locked_hours, total_hours, parent)
        dlg._center_on(parent)
        dlg.exec()
        return dlg.choice

    def _center_on(self, parent):
        """Pencerenin ORTASINA yerleşir; pencere yoksa ekranın ortasına.

        Boyut önce kesinleşmeli: adjustSize çağrılmadan width() hâlâ
        varsayılan değeri döndürüyor ve sayfa merkezden kayıyordu —
        pencere küçükken fark büyüyor.
        """
        from PySide6.QtWidgets import QApplication
        self.adjustSize()
        size = self.size()
        ref = None
        if parent is not None:
            try:
                win = parent.window()
                if win is not None and win.isVisible():
                    ref = win.frameGeometry()
            except Exception:
                ref = None
        if ref is None:
            screen = (QApplication.screenAt(self.pos())
                      or QApplication.primaryScreen())
            if screen is None:
                return
            ref = screen.availableGeometry()
        self.move(ref.center() - QPoint(size.width() // 2, size.height() // 2))
