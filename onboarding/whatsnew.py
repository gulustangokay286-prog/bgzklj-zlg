"""Sürüm yenilikleri kartı ve sürüm turu.

Uygulama açıldığında, BU sürümün tanıtımı daha önce gösterilmediyse ortada
bir kart belirir: sürümün yenilikleri sayfa sayfa, her sayfada bir "Göster"
düğmesiyle. "Göster" kartı kapatır, ilgili ekrana/ düğmeye gider, orayı
spotlight ile vurgular ve anlatır; adım bitince kart geri gelir ve sıradaki
yeniliğe geçer. Kullanıcı istediği an "Şimdilik geç" diyebilir; her iki
durumda da tanıtım görülmüş sayılır ve bir daha açılmaz.
"""
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QFont, QPainterPath, QPen, QBrush
from PySide6.QtWidgets import (QDialog, QWidget, QLabel, QPushButton, QVBoxLayout,
                               QHBoxLayout, QGraphicsOpacityEffect)

from . import state
from .spotlight import TourRunner

BLUE = "#2F6BE4"


def _grid(win):
    return getattr(win, "_grid", None)


def _ribbon_button(win, label_startswith):
    """Şerit düğmesini etiketine göre bulur ('Planlama' gibi)."""
    r = getattr(win, "ribbon", None) or getattr(win, "_ribbon", None)
    root = r if r is not None else win
    from PySide6.QtWidgets import QAbstractButton
    best = None
    for b in root.findChildren(QAbstractButton):
        txt = (getattr(b, "_label", None) or b.text() or "").replace("\n", " ")
        if txt.startswith(label_startswith) and b.isVisible():
            best = best or b
    return best


def _open_relations_with_tour(win):
    """Planlama İlişkileri ekranını açar ve tanıtım turunu zorla çalıştırır."""
    from . import state as _st
    _st.reset(KEY_RELATIONS)              # tanıtımda her hâlükârda gösterilsin
    fn = getattr(win, "_open_relations", None)
    if callable(fn):
        fn()


KEY_RELATIONS = "tour:relations"


PAGES = [
    {
        "key": "asistan",
        "title": "Chenkron Asistan",
        "body": "Artık programa yazarak iş verebilirsiniz: “Sultan Yılmaz'ın pazartesini aç”, "
                "“otomatik planlamayı başlat”, “çizelgeyi sıfırla”, “Birey'de Mesut Çolak'ın "
                "hangi saatleri kapalı?”. Sıralı işleri de sırayla yapar ve ne yaptığını yazar.",
        "step": {
            "target": lambda win: getattr(_grid(win), "btn_assistant", None),
            "title": "Asistan burada",
            "text": "Çizelgenin sağ üstündeki bu daireye tıklayın. Alttan açılan kutuya sorunuzu "
                    "yazın ya da işi tarif edin — yaptığı her adımı üstünde görürsünüz.",
        },
    },
    {
        "key": "motor",
        "title": "Motor artık tavana her koşuda çıkıyor",
        "body": "Otomatik planlama, kurallarınızla ulaşılabilecek EN ÇOK saati kanıtlayıp ona "
                "ulaşıyor. Tavan toplamın altındaysa sebebini de söylüyor: hangi kural, hangi "
                "sınıflar, hangi öğretmenin zaman tablosu.",
        "step": {
            "target": lambda win: _ribbon_button(win, "Otomatik"),
            "title": "Otomatik Planla",
            "text": "Aynı veriyle her çalıştırmada aynı en iyi sonuca ulaşır. Eksik kalırsa "
                    "rapor “şu kural şu sınıflarda şu kadar saati dışarıda bırakıyor” diye yazar.",
        },
    },
    {
        "key": "iliskiler",
        "title": "Planlama İlişkileri netleşti",
        "body": "“Seçilen dersler aynı ders sayılsın” kuralında artık gruplama zorunlu: Mat1+Mat2 "
                "ile Türkçe+Edebiyat'ı ayrı gruplara koymazsanız dördü birden TEK ders sayılır. "
                "Ekran bunu kaydetmeden önce söylüyor.",
        "step": {
            "target": lambda win: _ribbon_button(win, "Planlama"),
            "title": "Planlama İlişkileri",
            "text": "Kurallar burada. “Anladım”a basınca ekranı açıyorum ve içinde kısa bir tur "
                    "çalıştırıyorum: kural seçimi, süzgeçler, <b>gruplar</b> ve önem derecesi.",
            "next": "Anladım, aç",
        },
        # Adım bitince EKRANI AÇAR ve kendi turunu zorla çalıştırır.
        "after": lambda win: _open_relations_with_tour(win),
    },
    {
        "key": "elle",
        "title": "Elle yerleştirmede kural uyarısı",
        "body": "Bir dersi kuralın izin vermediği yere bıraktığınızda program artık susmuyor: hangi "
                "kural, neyle çakışıyor söylüyor ve “yine de yerleştir” demenizi bekliyor.",
        "step": {
            "target": lambda win: getattr(_grid(win), "btn_unlock_all", None),
            "title": "Çizelge üzerinde",
            "text": "Kart sürüklerken hücre rengi kuralları da hesaba katar. Kilitli dersler "
                    "planlamada yerinden oynamaz; buradan hepsini serbest bırakabilirsiniz.",
        },
    },
    {
        "key": "kurumlar",
        "title": "Kurumlar tamamen bağımsız",
        "body": "Bir kurumdaki değişiklik diğerinin zaman tablosunu artık hiçbir şekilde "
                "değiştirmiyor. Ortak öğretmenin başka kurumdaki dersi burada kısıt sayılmıyor; "
                "merak ederseniz asistana sorabilirsiniz.",
        "step": None,
    },
]


class WhatsNewDialog(QDialog):
    """Ortada beliren yenilik kartı (çerçevesiz, yumuşak)."""

    def __init__(self, win, version, pages=None):
        super().__init__(win)
        self.win = win
        self.version = version
        self.pages = list(pages if pages is not None else PAGES)
        self.index = 0
        self._tour_page = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # MODAL DEĞİL: "Göster" kartı gizleyip ana pencerede spotlight açıyor;
        # kart modal olsaydı uygulama girdiyi bloke eder ve tur tıklanamazdı.
        self.setModal(False)
        self.setWindowModality(Qt.NonModal)
        self.resize(560, 330)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.card = QWidget(self)
        self.card.setObjectName("wnCard")
        self.card.setStyleSheet(
            "#wnCard { background: #FFFFFF; border: 1px solid rgba(0,0,0,0.10); border-radius: 18px; }")
        root.addWidget(self.card)

        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(30, 26, 30, 20)
        lay.setSpacing(10)

        self.lbl_badge = QLabel(f"Chenkron {version} · Yenilikler", self.card)
        self.lbl_badge.setFont(QFont(".AppleSystemUIFont", 11, QFont.DemiBold))
        self.lbl_badge.setStyleSheet(f"color: {BLUE}; background: transparent;")
        lay.addWidget(self.lbl_badge)

        self.lbl_title = QLabel(self.card)
        self.lbl_title.setFont(QFont(".AppleSystemUIFont", 21, QFont.DemiBold))
        self.lbl_title.setStyleSheet("color: #0F172A; background: transparent;")
        self.lbl_title.setWordWrap(True)
        lay.addWidget(self.lbl_title)

        self.lbl_body = QLabel(self.card)
        self.lbl_body.setFont(QFont(".AppleSystemUIFont", 13))
        self.lbl_body.setStyleSheet("color: #475569; background: transparent;")
        self.lbl_body.setWordWrap(True)
        self.lbl_body.setTextFormat(Qt.RichText)
        lay.addWidget(self.lbl_body, 1)

        self.dots = QWidget(self.card)
        self.dots.setFixedHeight(10)
        self.dots.paintEvent = self._paint_dots
        lay.addWidget(self.dots)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_skip = QPushButton("Şimdilik geç", self.card)
        self.btn_skip.setCursor(Qt.PointingHandCursor)
        self.btn_skip.setStyleSheet(
            "QPushButton { background: transparent; color: #64748B; border: none; padding: 8px 10px; "
            "font-size: 12.5px; } QPushButton:hover { color: #0F172A; }")
        self.btn_skip.clicked.connect(self._finish)
        row.addWidget(self.btn_skip)
        row.addStretch(1)
        self.btn_show = QPushButton("Göster", self.card)
        self.btn_show.setCursor(Qt.PointingHandCursor)
        self.btn_show.setStyleSheet(
            "QPushButton { background: #EEF3FD; color: #1E40AF; border: none; border-radius: 9px; "
            "padding: 9px 18px; font-size: 13px; font-weight: 600; } "
            "QPushButton:hover { background: #E0EAFB; }")
        self.btn_show.clicked.connect(self._show_on_screen)
        row.addWidget(self.btn_show)
        self.btn_next = QPushButton("Devam", self.card)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setDefault(True)
        self.btn_next.setStyleSheet(
            "QPushButton { background: #2F6BE4; color: white; border: none; border-radius: 9px; "
            "padding: 9px 22px; font-size: 13px; font-weight: 600; } "
            "QPushButton:hover { background: #4A85F0; }")
        self.btn_next.clicked.connect(self._next)
        row.addWidget(self.btn_next)
        lay.addLayout(row)

        self._fx = QGraphicsOpacityEffect(self.card)
        self._fx.setOpacity(1.0)
        self.card.setGraphicsEffect(self._fx)
        self._fade = QPropertyAnimation(self._fx, b"opacity", self)
        self._fade.setDuration(180)
        self._render()

    # ── sayfalar ──
    def _paint_dots(self, _e):
        p = QPainter(self.dots)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        n = len(self.pages)
        w = n * 14
        x = (self.dots.width() - w) / 2
        for i in range(n):
            p.setBrush(QColor(BLUE) if i == self.index else QColor("#CBD5E1"))
            d = 7 if i == self.index else 6
            p.drawEllipse(QRectF(x + i * 14 + (7 - d) / 2, (10 - d) / 2, d, d))
        p.end()

    def _render(self):
        page = self.pages[self.index]
        self.lbl_title.setText(page["title"])
        self.lbl_body.setText(page["body"])
        self.btn_show.setVisible(bool(page.get("step")))
        self.btn_next.setText("Devam" if self.index < len(self.pages) - 1 else "Bitir")
        self.dots.update()
        self._fade.stop()
        self._fade.setStartValue(0.35)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def _next(self):
        if self.index < len(self.pages) - 1:
            self.index += 1
            self._render()
        else:
            self._finish()

    def _finish(self):
        state.mark_seen(f"whatsnew:{self.version}")
        self.close()

    # ── "Göster": ekranda vurgula ──
    def _show_on_screen(self):
        page = self.pages[self.index]
        step = dict(page.get("step") or {})
        if not step:
            self._next()
            return
        tgt = step.get("target")
        step["target"] = (lambda t=tgt: t(self.win)) if callable(tgt) else tgt
        step.setdefault("next", "Anladım")
        after = page.get("after")
        self.hide()

        def done():
            # Adımdan sonra ilgili ekran açılabilir (modal); kart o ekran
            # kapanınca geri gelir.
            if callable(after):
                try:
                    after(self.win)
                except Exception as exc:
                    print(f"[onboarding] ekran açılamadı: {exc}")
            # Tur adımı bitti: kart geri gelir ve sıradaki yeniliğe geçer.
            if self.index < len(self.pages) - 1:
                self.index += 1
                self._render()
                self.show()
                self.raise_()
            else:
                self._finish()

        runner = TourRunner(self.win, [step], on_finish=done)
        self._tour_page = runner
        QTimer.singleShot(60, runner.start)

    def showEvent(self, e):
        # Ana pencerenin ortasında dursun.
        if self.win is not None:
            g = self.win.geometry()
            self.move(g.center().x() - self.width() // 2, g.center().y() - self.height() // 2)
        super().showEvent(e)


def maybe_show(win, version, force=False):
    """Bu sürümün tanıtımı gösterilmediyse gösterir. True = gösterildi."""
    key = f"whatsnew:{version}"
    if not force and state.seen(key):
        return False
    try:
        dlg = WhatsNewDialog(win, version)
        win._whatsnew_dialog = dlg          # referans: GC toplamasın
        dlg.show()
        dlg.raise_()
        return True
    except Exception as exc:
        print(f"[onboarding] yenilikler kartı açılmadı: {exc}")
        state.mark_seen(key)
        return False
