"""dialogs/plan_result_sheet.py — otomatik planlama sonucu.

Bu sonuç bir QMessageBox'ta duruyordu: ünlem ikonu, kalın iki satır, OK.
Ünlem yanlış işaretti (bir şey ters gitmiş gibi duruyordu), sayı cümlenin
içinde kayboluyordu ve saatler boş kaldığında ekrana sığmayan bir tablo
açılıyordu.

Burada sonuç ANLATILMIYOR, gösteriliyor: bir halka dolarken içindeki tik
çiziliyor, saat sayısı sıfırdan yukarı sayıyor, eksik kalan varsa halka
tamamlanmadan duruyor ve rengi değişiyor. Sayının kendisi de dolan
halkayla aynı anda yerine oturuyor, çünkü ikisi aynı şeyi söylüyor.
"""
import math

from PySide6.QtCore import (Qt, QPoint, QPointF, QRectF, QTimer, Property,
                            QPropertyAnimation, QEasingCurve,
                            QParallelAnimationGroup)
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPainterPath
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGraphicsDropShadowEffect, QScrollArea, QWidget, QApplication
)

import bk_ui

OK_GREEN = "#1E9E5A"
WARN_AMBER = "#C9821A"


class _ResultMedallion(QWidget):
    """Dolan halka + içinde çizilen tik (ya da eksik varsa ünlem yerine
    yarım kalan halka). İki değer animasyonlu: halkanın açısı ve tikin
    çizilen oranı."""

    def __init__(self, ratio=1.0, parent=None):
        super().__init__(parent)
        self.setFixedSize(108, 108)
        self._ratio = max(0.0, min(1.0, float(ratio)))
        self._sweep = 0.0        # halkanın dolan kısmı (0..1)
        self._check = 0.0        # tikin çizilen kısmı (0..1)
        self._glow = 0.0

    def _get_sweep(self):
        return self._sweep

    def _set_sweep(self, v):
        self._sweep = float(v)
        self.update()

    sweep = Property(float, _get_sweep, _set_sweep)

    def _get_check(self):
        return self._check

    def _set_check(self, v):
        self._check = float(v)
        self.update()

    check = Property(float, _get_check, _set_check)

    def _get_glow(self):
        return self._glow

    def _set_glow(self, v):
        self._glow = float(v)
        self.update()

    glow = Property(float, _get_glow, _set_glow)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        full = self._ratio >= 0.999
        accent = QColor(OK_GREEN if full else WARN_AMBER)

        box = QRectF(10, 10, w - 20, w - 20)

        # Halkanın izi: nereye kadar dolacağını baştan gösterir.
        p.setBrush(Qt.NoBrush)
        track = QPen(QColor(accent.red(), accent.green(), accent.blue(), 34), 7)
        track.setCapStyle(Qt.RoundCap)
        p.setPen(track)
        p.drawArc(box, 0, 360 * 16)

        # Dolan kısım: saat 12'den başlayıp saat yönünde.
        span = -360.0 * self._ratio * self._sweep
        if abs(span) > 0.5:
            arc = QPen(accent, 7)
            arc.setCapStyle(Qt.RoundCap)
            p.setPen(arc)
            p.drawArc(box, 90 * 16, int(span * 16))

        # İç disk + tik
        inner = box.adjusted(11, 11, -11, -11)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(accent.red(), accent.green(), accent.blue(),
                                 int(20 + 14 * self._glow))))
        p.drawEllipse(inner)

        if self._check > 0.001:
            cx, cy = inner.center().x(), inner.center().y()
            r = inner.width() / 2.0
            pts = [QPointF(cx - r * 0.42, cy + r * 0.04),
                   QPointF(cx - r * 0.12, cy + r * 0.36),
                   QPointF(cx + r * 0.46, cy - r * 0.34)]
            if not full:
                # Eksik kaldıysa tik değil, eksiği gösteren kısa bir çizgi.
                pts = [QPointF(cx - r * 0.34, cy), QPointF(cx + r * 0.34, cy)]

            path = QPainterPath(pts[0])
            seg = [pts[0].x(), pts[0].y()]
            total = sum(math.hypot(pts[i + 1].x() - pts[i].x(),
                                   pts[i + 1].y() - pts[i].y())
                        for i in range(len(pts) - 1)) or 1.0
            want = total * self._check
            done = 0.0
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i + 1]
                d = math.hypot(b.x() - a.x(), b.y() - a.y())
                if done + d <= want:
                    path.lineTo(b)
                    done += d
                else:
                    t = max(0.0, (want - done) / d) if d else 0.0
                    path.lineTo(QPointF(a.x() + (b.x() - a.x()) * t,
                                        a.y() + (b.y() - a.y()) * t))
                    break
            pen = QPen(accent, 8)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
        p.end()


class _CountingLabel(QLabel):
    """Sıfırdan hedefe sayan sayı. 285 yazmak ile 285'e SAYMAK aynı şey
    değil: ikincisi büyüklüğü hissettiriyor."""

    def __init__(self, target, suffix="", parent=None):
        super().__init__(parent)
        self._target = int(target)
        self._suffix = suffix
        self._value = 0
        self.setAlignment(Qt.AlignCenter)
        self._render()

    def _get_value(self):
        return self._value

    def _set_value(self, v):
        self._value = int(v)
        self._render()

    value = Property(int, _get_value, _set_value)

    def _render(self):
        self.setText(f"{self._value}{self._suffix}")


class PlanResultSheet(QDialog):
    """Planlama sonucu. PlanResultSheet.show_result(...) ile çağrılır."""

    def __init__(self, total_hours=0, unplaced_hours=0, details_html="",
                 parent=None):
        super().__init__(parent)
        self._drag_from = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint
                            | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("QDialog { background: transparent; }")
        self.setModal(True)

        total_hours = max(0, int(total_hours or 0))
        unplaced_hours = max(0, int(unplaced_hours or 0))
        planned = total_hours + unplaced_hours
        ratio = (total_hours / planned) if planned else 1.0
        full = unplaced_hours == 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)

        card = QFrame(self)
        card.setObjectName("resultCard")
        card.setStyleSheet("""
            #resultCard {
                background: #FFFFFF;
                border: 1px solid rgba(15, 23, 42, 0.08);
                border-radius: 20px;
            }
        """)
        sh = QGraphicsDropShadowEffect(card)
        sh.setBlurRadius(34)
        sh.setOffset(0, 10)
        sh.setColor(QColor(15, 23, 42, 52))
        card.setGraphicsEffect(sh)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(30, 26, 30, 22)
        lay.setSpacing(0)

        self.medallion = _ResultMedallion(ratio)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.medallion)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addSpacing(12)

        title = QLabel("Planlama tamamlandı" if full else "Planlama bitti")
        title.setFont(bk_ui.font(14.5, QFont.DemiBold, spacing=-0.2))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {bk_ui.INK}; background: transparent; border: none;")
        lay.addWidget(title)
        lay.addSpacing(10)

        # Asıl rakam: sayarak yerine oturuyor.
        self.counter = _CountingLabel(total_hours)
        self.counter.setFont(bk_ui.font(28, QFont.DemiBold, spacing=-1.0))
        self.counter.setStyleSheet(
            f"color: {OK_GREEN if full else bk_ui.INK}; background: transparent;"
            " border: none;")
        lay.addWidget(self.counter)

        cap = QLabel("ders saati çizelgeye yerleşti")
        cap.setFont(bk_ui.font(9.6))
        cap.setAlignment(Qt.AlignCenter)
        cap.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent; border: none;")
        lay.addWidget(cap)

        if not full:
            lay.addSpacing(14)
            strip = QFrame()
            strip.setStyleSheet("""
                QFrame {
                    background: #FFF8EC;
                    border: 1px solid #F3DFB8;
                    border-radius: 12px;
                }
            """)
            srow = QVBoxLayout(strip)
            srow.setContentsMargins(14, 10, 14, 10)
            srow.setSpacing(2)
            head = QLabel(f"<b>{unplaced_hours} saat</b> yerleşemedi")
            head.setFont(bk_ui.font(9.6))
            head.setTextFormat(Qt.RichText)
            head.setStyleSheet("color: #7A5C10; background: transparent; border: none;")
            srow.addWidget(head)
            why = QLabel("Sebep planlayıcının yetersizliği değil: o saatlerde "
                         "ders verebilecek öğretmen yok.")
            why.setFont(bk_ui.font(9.0))
            why.setWordWrap(True)
            why.setStyleSheet("color: #8A6D1E; background: transparent; border: none;")
            srow.addWidget(why)
            lay.addWidget(strip)

            if details_html:
                lay.addSpacing(10)
                self.details = QScrollArea()
                self.details.setWidgetResizable(True)
                self.details.setFixedHeight(190)
                self.details.setStyleSheet("""
                    QScrollArea { border: 1px solid #ECEEF2; border-radius: 12px;
                                  background: #FBFCFD; }
                """)
                inner = QLabel(details_html)
                inner.setTextFormat(Qt.RichText)
                inner.setWordWrap(True)
                inner.setAlignment(Qt.AlignTop)
                inner.setContentsMargins(14, 12, 14, 12)
                inner.setStyleSheet("color: #48505E; font-size: 12px;"
                                    " background: transparent; border: none;")
                self.details.setWidget(inner)
                self.details.setVisible(False)
                lay.addWidget(self.details)

                self.btn_more = QPushButton("Ayrıntıları göster")
                self.btn_more.setCursor(Qt.PointingHandCursor)
                self.btn_more.setFixedHeight(30)
                self.btn_more.setFont(bk_ui.font(9.4, QFont.Medium))
                self.btn_more.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent; color: {bk_ui.BRAND};
                        border: none; padding: 0 8px;
                    }}
                    QPushButton:hover {{ color: {bk_ui.BRAND_DARK}; }}
                """)
                self.btn_more.clicked.connect(self._toggle_details)
                lay.addWidget(self.btn_more, 0, Qt.AlignCenter)

        lay.addSpacing(18)

        btn = QPushButton("Tamam" if full else "Anladım")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(38)
        btn.setFont(bk_ui.font(9.8, QFont.DemiBold))
        colour = OK_GREEN if full else bk_ui.BRAND
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {colour}; color: #FFFFFF;
                border: none; border-radius: 19px; padding: 0 30px;
            }}
            QPushButton:hover {{ background: {QColor(colour).darker(112).name()}; }}
        """)
        btn.clicked.connect(self.accept)
        brow = QHBoxLayout()
        brow.addStretch(1)
        brow.addWidget(btn)
        brow.addStretch(1)
        lay.addLayout(brow)

        self.setFixedWidth(430)
        self._build_animation(total_hours)

    def _toggle_details(self):
        shown = self.details.isVisible()
        self.details.setVisible(not shown)
        self.btn_more.setText("Ayrıntıları gizle" if not shown else "Ayrıntıları göster")
        self.adjustSize()

    def _build_animation(self, total_hours):
        """Halka dolar, tik çizilir, sayı sayar — üçü aynı anda başlar ama
        tik halkanın ardından gelir, çünkü önce iş biter sonra onaylanır."""
        group = QParallelAnimationGroup(self)

        ring = QPropertyAnimation(self.medallion, b"sweep", self)
        ring.setDuration(720)
        ring.setStartValue(0.0)
        ring.setEndValue(1.0)
        ring.setEasingCurve(QEasingCurve.OutCubic)
        group.addAnimation(ring)

        count = QPropertyAnimation(self.counter, b"value", self)
        count.setDuration(760)
        count.setStartValue(0)
        count.setEndValue(int(total_hours))
        count.setEasingCurve(QEasingCurve.OutCubic)
        group.addAnimation(count)

        glow = QPropertyAnimation(self.medallion, b"glow", self)
        glow.setDuration(900)
        glow.setStartValue(0.0)
        glow.setEndValue(1.0)
        glow.setEasingCurve(QEasingCurve.OutCubic)
        group.addAnimation(glow)

        self._group = group
        self._tick_anim = QPropertyAnimation(self.medallion, b"check", self)
        self._tick_anim.setDuration(340)
        self._tick_anim.setStartValue(0.0)
        self._tick_anim.setEndValue(1.0)
        self._tick_anim.setEasingCurve(QEasingCurve.OutCubic)

    def showEvent(self, e):
        super().showEvent(e)
        if not getattr(self, "_played", False):
            self._played = True
            self._group.start()
            QTimer.singleShot(430, self._tick_anim.start)

    # ── çerçevesiz pencere: elle taşınır, elle ortalanır ─────────────
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

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_from = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_from is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_from)

    def mouseReleaseEvent(self, e):
        self._drag_from = None

    @classmethod
    def show_result(cls, parent, total_hours=0, unplaced_hours=0, details_html=""):
        dlg = cls(total_hours, unplaced_hours, details_html, parent)
        dlg._center_on(parent)
        dlg.exec()
        return dlg
