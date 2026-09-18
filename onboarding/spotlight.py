"""Spotlight: hedefi karartma içinde vurgulayan katman ve açıklama balonu.

Tur adımı şöyle işler: ekran kararır, yalnızca hedef widget'ın bulunduğu
dikdörtgen aydınlık kalır (yuvarlatılmış bir "delik"), etrafında nabız gibi
atan bir halka döner ve hemen yanında başlık + açıklama + "Devam" düğmesi
taşıyan bir balon belirir. Kullanıcı hedefi GERÇEKTEN görür; ekranın neresine
bakacağını tarif etmek yerine gösterilir.

Katman, hedefin bulunduğu pencerenin (ana pencere ya da diyalog) çocuğu olarak
kurulur; böylece diyalog içindeki adımlar da aynı şekilde çalışır.
"""
import math

from PySide6.QtCore import (Qt, QRect, QRectF, QPoint, QPointF, QTimer, Signal,
                            QPropertyAnimation, QEasingCurve, Property)
from PySide6.QtGui import QPainter, QColor, QPainterPath, QPen, QFont, QFontMetrics
from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout

BLUE = QColor("#2F6BE4")
CARD_BG = QColor(255, 255, 255)
CARD_BORDER = QColor(0, 0, 0, 26)
PAD = 14


class SpotlightOverlay(QWidget):
    """Tek bir tur adımı. next_clicked / skip_clicked ile ilerletilir."""

    next_clicked = Signal()
    skip_clicked = Signal()

    def __init__(self, host, target, title, text, index=0, total=0,
                 next_label="Devam", parent=None):
        super().__init__(parent or host)
        self.host = host
        self.target = target
        self._title = title or ""
        self._text = text or ""
        self._index = index
        self._total = total
        self._phase = 0.0
        self._reveal = 0.0
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setGeometry(host.rect())

        self.card = QWidget(self)
        self.card.setObjectName("tourCard")
        self.card.setStyleSheet(
            "#tourCard { background: #FFFFFF; border: 1px solid rgba(0,0,0,0.10); "
            "border-radius: 14px; }")
        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(8)

        self.lbl_title = QLabel(self._title, self.card)
        self.lbl_title.setFont(QFont(".AppleSystemUIFont", 14, QFont.DemiBold))
        self.lbl_title.setStyleSheet("color: #0F172A; background: transparent;")
        self.lbl_title.setWordWrap(True)
        lay.addWidget(self.lbl_title)

        self.lbl_text = QLabel(self._text, self.card)
        self.lbl_text.setFont(QFont(".AppleSystemUIFont", 12))
        self.lbl_text.setStyleSheet("color: #475569; background: transparent;")
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setTextFormat(Qt.RichText)
        lay.addWidget(self.lbl_text)

        row = QHBoxLayout()
        row.setSpacing(8)
        # Tek adımlık turlarda "1 / 1" bilgi taşımaz, gösterilmez.
        self.lbl_step = QLabel(f"{index + 1} / {total}" if total > 1 else "", self.card)
        self.lbl_step.setFont(QFont(".AppleSystemUIFont", 11))
        self.lbl_step.setStyleSheet("color: #94A3B8; background: transparent;")
        row.addWidget(self.lbl_step)
        row.addStretch(1)
        self.btn_skip = QPushButton("Turu bitir" if total > 1 else "Kapat", self.card)
        self.btn_skip.setCursor(Qt.PointingHandCursor)
        self.btn_skip.setStyleSheet(
            "QPushButton { background: transparent; color: #64748B; border: none; "
            "padding: 6px 10px; font-size: 12px; } QPushButton:hover { color: #0F172A; }")
        self.btn_skip.clicked.connect(self.skip_clicked.emit)
        row.addWidget(self.btn_skip)
        self.btn_next = QPushButton(next_label, self.card)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setDefault(True)
        self.btn_next.setStyleSheet(
            "QPushButton { background: #2F6BE4; color: white; border: none; border-radius: 8px; "
            "padding: 7px 18px; font-size: 12.5px; font-weight: 600; } "
            "QPushButton:hover { background: #4A85F0; }")
        self.btn_next.clicked.connect(self.next_clicked.emit)
        row.addWidget(self.btn_next)
        lay.addLayout(row)

        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

        self._anim = QPropertyAnimation(self, b"reveal", self)
        self._anim.setDuration(280)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    # ── açılış ──
    def start(self):
        self.setGeometry(self.host.rect())
        self._layout_card()
        self.show()
        self.raise_()
        self.btn_next.setFocus()
        self._timer.start()
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def stop(self):
        self._timer.stop()
        self.hide()
        self.deleteLater()

    def _tick(self):
        self._phase += 0.08
        self.update()

    def _get_reveal(self):
        return self._reveal

    def _set_reveal(self, v):
        self._reveal = float(v)
        self.update()

    reveal = Property(float, _get_reveal, _set_reveal)

    # ── geometri ──
    def target_rect(self):
        """Hedefin bu katmandaki dikdörtgeni; hedef yoksa ekranın ortası."""
        w = self.target
        if w is None or not w.isVisible():
            c = self.rect().center()
            return QRect(c.x() - 60, c.y() - 60, 120, 120)
        tl = w.mapTo(self.host, QPoint(0, 0))
        return QRect(tl, w.size()).adjusted(-8, -8, 8, 8)

    def _layout_card(self):
        self.card.adjustSize()
        cw = min(380, max(260, self.width() - 60))
        self.lbl_title.setFixedWidth(cw - 36)
        self.lbl_text.setFixedWidth(cw - 36)
        self.card.setFixedWidth(cw)
        self.card.adjustSize()
        ch = self.card.height()
        tr = self.target_rect()
        # Balon hedefin altına, sığmazsa üstüne; yatayda hedefle hizalı ama
        # ekran dışına taşmaz.
        x = min(max(12, tr.center().x() - cw // 2), self.width() - cw - 12)
        if tr.bottom() + 16 + ch <= self.height() - 12:
            y = tr.bottom() + 16
        elif tr.top() - 16 - ch >= 12:
            y = tr.top() - 16 - ch
        else:
            y = max(12, min(self.height() - ch - 12, tr.center().y() - ch // 2))
        self.card.move(int(x), int(y))

    def resizeEvent(self, e):
        self.setGeometry(self.host.rect())
        self._layout_card()
        super().resizeEvent(e)

    # ── etkileşim ──
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.skip_clicked.emit()
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.next_clicked.emit()
        else:
            super().keyPressEvent(e)

    def mousePressEvent(self, e):
        # Hedefe tıklanırsa adım ilerler; boşluğa tıklamak hiçbir şey yapmaz
        # (yanlışlıkla turu kapatmasın).
        if self.target_rect().contains(e.pos()):
            self.next_clicked.emit()
        super().mousePressEvent(e)

    # ── çizim ──
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        tr = QRectF(self.target_rect())
        # delik açılırken büyür
        grow = 1.0 + 0.25 * (1.0 - self._reveal)
        hole = QRectF(tr.center().x() - tr.width() * grow / 2,
                      tr.center().y() - tr.height() * grow / 2,
                      tr.width() * grow, tr.height() * grow)
        radius = min(18.0, hole.height() / 2)

        mask = QPainterPath()
        mask.addRect(QRectF(self.rect()))
        cut = QPainterPath()
        cut.addRoundedRect(hole, radius, radius)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(15, 23, 42, int(150 * self._reveal)))
        p.drawPath(mask.subtracted(cut))

        # nabız halkası
        pulse = 0.5 + 0.5 * math.sin(self._phase)
        ring = hole.adjusted(-4 - 4 * pulse, -4 - 4 * pulse, 4 + 4 * pulse, 4 + 4 * pulse)
        pen = QPen(QColor(47, 107, 228, int((150 - 90 * pulse) * self._reveal)), 2.5)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(ring, radius + 4, radius + 4)
        p.setPen(QPen(QColor(255, 255, 255, int(220 * self._reveal)), 1.5))
        p.drawRoundedRect(hole, radius, radius)
        p.end()


class TourRunner:
    """Adımları sırayla oynatır.

    Adım: dict(target=çağrılabilir -> QWidget | QWidget, title, text,
               before=çağrılabilir (adımdan önce çalışır), next="Devam")
    Hedef bulunamayan adım atlanır — eksik bir düğme yüzünden tur çökmez.
    """

    def __init__(self, host, steps, on_finish=None):
        self.host = host
        self.steps = list(steps or [])
        self.on_finish = on_finish
        self.i = -1
        self.overlay = None

    def start(self):
        self._next()

    def _resolve(self, step):
        t = step.get("target")
        try:
            w = t() if callable(t) else t
        except Exception:
            w = None
        return w if (w is not None and getattr(w, "isVisible", lambda: False)()) else None

    def _next(self):
        if self.overlay is not None:
            self.overlay.stop()
            self.overlay = None
        self.i += 1
        while self.i < len(self.steps):
            step = self.steps[self.i]
            before = step.get("before")
            if callable(before):
                try:
                    before()
                except Exception:
                    pass
            target = self._resolve(step)
            if target is not None or step.get("allow_missing"):
                self.overlay = SpotlightOverlay(
                    self.host, target, step.get("title", ""), step.get("text", ""),
                    index=self.i, total=len(self.steps),
                    next_label=step.get("next", "Devam" if self.i < len(self.steps) - 1 else "Bitir"))
                self.overlay.next_clicked.connect(self._next)
                self.overlay.skip_clicked.connect(self._finish)
                self.overlay.start()
                return
            self.i += 1
        self._finish()

    def _finish(self):
        if self.overlay is not None:
            self.overlay.stop()
            self.overlay = None
        if callable(self.on_finish):
            try:
                self.on_finish()
            except Exception:
                pass
