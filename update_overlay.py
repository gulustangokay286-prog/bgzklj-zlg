"""
update_overlay.py — ekranin ortasinda acilan guncelleme sheet'i.

Anasayfadaki SyncCenterLoadingOverlay ile AYNI gorsel dili kullanir (ayni
karti, ayni rozet dili, ayni ilerleme cubugu, ayni loş arka plan): kullanici
icin "bir sey iniyor" hissi zaten o pencereye bagli, guncellemenin bambaska
gorunen ikinci bir penceresi olmasi icin bir sebep yok. Fark yalnizca
icerikte: kurum verisi degil programin kendisi iniyor, ve is bitince
kapanip gitmek yerine tek bir karar soruyor (simdi yeniden baslat / daha
sonra).

Durumlar:
    show_checking()            mavi, belirsiz  - "Guncellemeler denetleniyor"
    show_downloading(d, t)     mavi, yuzdeli   - "Guncelleme indiriliyor"
    show_staging()             mavi, %100'e yakin - "Paket dogrulaniyor"
    show_ready(version)        yesil + 2 dugme - "Guncelleme hazir"
    show_up_to_date()          yesil, kendi kapanir
    show_failed(msg)           kirmizi, kendi kapanir

Pencere degil, ebeveyn widget'in uzerine serilen bir kaplamadir: baslik
cubugu yoktur, ebeveynle birlikte boyutlanir ve macOS'ta bos saydam
pencerelerin siyah dikdortgen olarak takili kalmasi sorununa acik degildir.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import bk_branding
import bk_ui

_BLUE = bk_branding.BRAND_BLUE
_BLUE_DARK = bk_branding.BRAND_BLUE_DARK
_GREEN = "#10B981"
_GREEN_DEEP = "#065F46"
_RED = "#EF4444"
_RED_DEEP = "#991B1B"


def _human_size(num_bytes: int) -> str:
    if num_bytes <= 0:
        return "0 MB"
    mb = num_bytes / (1024 * 1024)
    if mb < 1:
        return f"{num_bytes / 1024:.0f} KB"
    if mb < 1024:
        return f"{mb:.1f} MB"
    return f"{mb / 1024:.2f} GB"


class UpdateBadgeIcon(QWidget):
    """36x36 vektor rozet: mavi (calisiyor, doner), yesil (onay), kirmizi
    (hata). Anasayfadaki SyncBadgeIcon'un guncelleme rengi."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self._state = "busy"
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(25)
        self._timer.timeout.connect(self._on_tick)

    def set_state(self, state: str) -> None:
        self._state = state
        if state == "busy":
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _on_tick(self) -> None:
        self._angle = (self._angle + 12) % 360
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        cx, cy = rect.width() / 2.0, rect.height() / 2.0
        r = min(cx, cy) - 2

        if self._state == "busy":
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#DBEAFE"))
            p.drawEllipse(QPointF(cx, cy), r, r)
            p.save()
            p.translate(cx, cy)
            p.rotate(self._angle)
            p.setPen(QPen(QColor(_BLUE), 2.6, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            arc_r = r - 5.5
            p.drawArc(QRectF(-arc_r, -arc_r, arc_r * 2, arc_r * 2), 30 * 16, 120 * 16)
            p.drawArc(QRectF(-arc_r, -arc_r, arc_r * 2, arc_r * 2), 210 * 16, 120 * 16)
            p.restore()
        elif self._state == "green":
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#DCFCE7"))
            p.drawEllipse(QPointF(cx, cy), r, r)
            p.setPen(QPen(QColor("#16A34A"), 2.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            path = QPainterPath()
            path.moveTo(cx - 5.5, cy + 0.2)
            path.lineTo(cx - 1.5, cy + 4.5)
            path.lineTo(cx + 6.0, cy - 4.5)
            p.drawPath(path)
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#FEE2E2"))
            p.drawEllipse(QPointF(cx, cy), r, r)
            p.setPen(QPen(QColor("#DC2626"), 2.5, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            p.drawLine(QPointF(cx, cy - 5), QPointF(cx, cy + 1))
            p.drawPoint(QPointF(cx, cy + 5))
        p.end()


class UpdateCenterOverlay(QWidget):
    """Ortada beliren guncelleme karti.

    restart_requested: kullanici "Şimdi Yeniden Başlat"a basti.
    dismissed:         kullanici "Daha Sonra"yi secti.
    """

    restart_requested = Signal()
    dismissed = Signal()

    CARD_W = 460
    CARD_H_PLAIN = 134
    CARD_H_ACTIONS = 196

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._auto_hide = QTimer(self)
        self._auto_hide.setSingleShot(True)
        self._auto_hide.timeout.connect(self.hide)
        self._positioned_for_height = -1

        self.card = QFrame(self)
        self.card.setObjectName("updateCard")
        self.card.setFixedSize(self.CARD_W, self.CARD_H_PLAIN)
        self.card.setStyleSheet(
            """
            QFrame#updateCard {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 16px;
            }
            """
        )

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        self.badge = UpdateBadgeIcon(self.card)
        top_row.addWidget(self.badge, 0, Qt.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        self.title_lbl = QLabel("Güncellemeler Denetleniyor…")
        self.title_lbl.setFont(bk_ui.font(11.5, QFont.Bold, spacing=-0.2))
        self.subtitle_lbl = QLabel("Sunucuya bağlanılıyor…")
        self.subtitle_lbl.setFont(bk_ui.font(9.5, QFont.Normal))
        self.subtitle_lbl.setWordWrap(True)
        text_col.addWidget(self.title_lbl)
        text_col.addWidget(self.subtitle_lbl)
        top_row.addLayout(text_col, 1)

        self.percent_lbl = QLabel("")
        self.percent_lbl.setFont(bk_ui.font(9.5, QFont.DemiBold))
        top_row.addWidget(self.percent_lbl, 0, Qt.AlignRight | Qt.AlignVCenter)

        card_layout.addLayout(top_row)

        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(7)
        self.pbar.setTextVisible(False)
        self.pbar.setRange(0, 100)
        self.pbar.setValue(0)
        card_layout.addWidget(self.pbar)

        self.actions = QWidget(self.card)
        self.actions.setAttribute(Qt.WA_StyledBackground, True)
        act_row = QHBoxLayout(self.actions)
        act_row.setContentsMargins(0, 6, 0, 0)
        act_row.setSpacing(10)
        act_row.addStretch(1)

        self.btn_later = QPushButton("Daha Sonra")
        self.btn_later.setObjectName("updateSecondary")
        self.btn_later.setCursor(Qt.PointingHandCursor)
        self.btn_later.clicked.connect(self._on_later)
        act_row.addWidget(self.btn_later)

        self.btn_restart = QPushButton("Şimdi Yeniden Başlat")
        self.btn_restart.setObjectName("updatePrimary")
        self.btn_restart.setCursor(Qt.PointingHandCursor)
        self.btn_restart.clicked.connect(self._on_restart)
        act_row.addWidget(self.btn_restart)

        self.actions.setStyleSheet(
            f"""
            QWidget {{ background: transparent; }}
            QPushButton#updatePrimary {{
                background-color: {_BLUE}; color: #FFFFFF; border: none;
                border-radius: 9px; padding: 9px 18px; font-size: 13px; font-weight: 600;
            }}
            QPushButton#updatePrimary:hover {{ background-color: {_BLUE_DARK}; }}
            QPushButton#updateSecondary {{
                background-color: transparent; color: #64748B; border: none;
                padding: 9px 14px; font-size: 13px;
            }}
            QPushButton#updateSecondary:hover {{ color: #0F172A; }}
            """
        )
        card_layout.addWidget(self.actions)
        self.actions.hide()

        self._paint_busy()
        parent.installEventFilter(self)
        self.hide()

    # --- Konumlandirma ---------------------------------------------------
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self.parentWidget() and event.type() in (QEvent.Resize, QEvent.Move):
            if self.isVisible():
                self._reposition()
        return super().eventFilter(obj, event)

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.setGeometry(parent.rect())
        cx = (self.width() - self.card.width()) // 2
        cy = (self.height() - self.card.height()) // 2
        self.card.move(cx, max(40, cy))
        self._positioned_for_height = self.card.height()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(15, 23, 42, 35))
        p.end()

    def _surface(self) -> None:
        """Zaten acikken ve kart ayni boydayken yeniden konumlandirip one
        almiyoruz: indirme ilerlemesi parca basina geliyor (300 MB'lik bir
        pakette binden fazla kez) ve her seferinde raise_() cagirmak
        arayuzu bosuna mesgul eder.

        Kartin boyu degistiyse (karar dugmeleri acilip kapandiginda oluyor)
        yeniden ortalamak SART, yoksa kart asagi dogru buyuyup merkezden
        kayiyor."""
        if self.isVisible() and self.card.height() == self._positioned_for_height:
            return
        self._reposition()
        self.show()
        self.raise_()

    # --- Gorunum yardimcilari --------------------------------------------
    def _set_bar_color(self, color_hex: str) -> None:
        self.pbar.setStyleSheet(
            f"""
            QProgressBar {{
                background: #F1F5F9; border: none; border-radius: 3.5px;
            }}
            QProgressBar::chunk {{
                background: {color_hex}; border-radius: 3.5px;
            }}
            """
        )

    def _set_actions_visible(self, visible: bool) -> None:
        self.actions.setVisible(visible)
        self.card.setFixedHeight(self.CARD_H_ACTIONS if visible else self.CARD_H_PLAIN)

    def _paint_busy(self) -> None:
        self.badge.set_state("busy")
        self._set_bar_color(_BLUE)
        self.title_lbl.setStyleSheet("color: #0F172A; background: transparent;")
        self.subtitle_lbl.setStyleSheet("color: #64748B; background: transparent;")
        self.percent_lbl.setStyleSheet(f"color: {_BLUE}; background: transparent;")

    # --- Durumlar --------------------------------------------------------
    def show_checking(self) -> None:
        self._auto_hide.stop()
        self._set_actions_visible(False)
        self._paint_busy()
        self.title_lbl.setText("Güncellemeler Denetleniyor…")
        self.subtitle_lbl.setText("Sürüm sunucusuna bağlanılıyor.")
        self.percent_lbl.setText("")
        self.pbar.setRange(0, 0)  # belirsiz
        self._surface()

    def show_downloading(self, downloaded: int, total: int, version: str = "") -> None:
        self._auto_hide.stop()
        self._set_actions_visible(False)
        self._paint_busy()
        self.pbar.setRange(0, 100)
        pct = int(100 * downloaded / total) if total else 0
        pct = max(0, min(99, pct))
        self.title_lbl.setText(
            f"Güncelleme İndiriliyor… (v{version})" if version else "Güncelleme İndiriliyor…"
        )
        self.subtitle_lbl.setText(
            f"{_human_size(downloaded)} / {_human_size(total)} — yalnızca değişen parçalar iniyor."
        )
        self.pbar.setValue(pct)
        self.percent_lbl.setText(f"{pct}%")
        self._surface()

    def show_staging(self, version: str = "") -> None:
        self._auto_hide.stop()
        self._set_actions_visible(False)
        self._paint_busy()
        self.pbar.setRange(0, 100)
        self.title_lbl.setText(
            f"Paket Doğrulanıyor… (v{version})" if version else "Paket Doğrulanıyor…"
        )
        self.subtitle_lbl.setText("İmza ve dosya sağlamaları kontrol ediliyor.")
        self.pbar.setValue(99)
        self.percent_lbl.setText("99%")
        self._surface()

    def show_ready(self, version: str, notes: str = "") -> None:
        self._auto_hide.stop()
        self.badge.set_state("green")
        self._set_bar_color(_GREEN)
        self.pbar.setRange(0, 100)
        self.pbar.setValue(100)
        self.percent_lbl.setText("100%")
        self.percent_lbl.setStyleSheet(f"color: {_GREEN}; background: transparent; font-weight: bold;")
        self.title_lbl.setText("Güncelleme Hazır")
        self.title_lbl.setStyleSheet(f"color: {_GREEN_DEEP}; background: transparent; font-weight: bold;")
        detail = (notes or "").strip().splitlines()
        first_line = detail[0] if detail else ""
        self.subtitle_lbl.setText(
            f"{bk_branding.PRODUCT_NAME} {version} indirildi ve doğrulandı."
            + (f" {first_line}" if first_line else "")
        )
        self.subtitle_lbl.setStyleSheet("color: #475569; background: transparent;")
        self._set_actions_visible(True)
        self._surface()

    def show_up_to_date(self) -> None:
        self._set_actions_visible(False)
        self.badge.set_state("green")
        self._set_bar_color(_GREEN)
        self.pbar.setRange(0, 100)
        self.pbar.setValue(100)
        self.percent_lbl.setText("100%")
        self.percent_lbl.setStyleSheet(f"color: {_GREEN}; background: transparent; font-weight: bold;")
        self.title_lbl.setText("Program Güncel")
        self.title_lbl.setStyleSheet(f"color: {_GREEN_DEEP}; background: transparent; font-weight: bold;")
        self.subtitle_lbl.setText(
            f"En son sürümü kullanıyorsunuz ({bk_branding.PRODUCT_NAME} {_app_version()})."
        )
        self.subtitle_lbl.setStyleSheet("color: #475569; background: transparent;")
        self._surface()
        self._auto_hide.start(1600)

    def show_failed(self, message: str) -> None:
        self._set_actions_visible(False)
        self.badge.set_state("red")
        self._set_bar_color(_RED)
        self.pbar.setRange(0, 100)
        self.pbar.setValue(100)
        self.percent_lbl.setText("Hata")
        self.percent_lbl.setStyleSheet(f"color: {_RED}; background: transparent; font-weight: bold;")
        self.title_lbl.setText("Güncelleme Yapılamadı")
        self.title_lbl.setStyleSheet(f"color: {_RED_DEEP}; background: transparent; font-weight: bold;")
        self.subtitle_lbl.setText(message or "Güncelleme sunucusuna ulaşılamadı.")
        self.subtitle_lbl.setStyleSheet("color: #475569; background: transparent;")
        self._surface()
        self._auto_hide.start(4000)

    # --- Dugmeler --------------------------------------------------------
    def _on_later(self) -> None:
        self.hide()
        self.dismissed.emit()

    def _on_restart(self) -> None:
        self._set_actions_visible(False)
        self._paint_busy()
        self.pbar.setRange(0, 0)
        self.title_lbl.setText("Güncelleme Uygulanıyor…")
        self.subtitle_lbl.setText("Program kapanıp yeni sürümle yeniden açılacak.")
        self.percent_lbl.setText("")
        self._surface()
        self.restart_requested.emit()


def _app_version() -> str:
    try:
        from version import APP_VERSION

        return APP_VERSION
    except Exception:
        return ""
