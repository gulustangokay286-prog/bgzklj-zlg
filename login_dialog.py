# -*- coding: utf-8 -*-
"""login_dialog.py — BK Planner sign-in and password reset.

Landscape, not portrait. The screen this replaced was a 480x660 column:
centred logo, centred title, centred subtitle, two icon-in-the-input
fields and a full-width button stacked down the middle. That is the shape
every generic sign-in box takes, it said nothing about what the program
is, and it ran 660px down a laptop screen while leaving the axis a
desktop window actually has — width — unused.

Left, on brand navy: the institution's shield, the wordmark in the same
calligraphic face the splash screen draws letter by letter, and behind
them a real weekly timetable — Pzt..Cum with lessons laid into it. The
decoration is the thing the product makes. Under it, two facts worth
knowing before you type: who the software belongs to, and whether the
server is reachable right now.

Right: the form, left-aligned rather than centred, with labels above the
fields instead of icons inside them — and, on the same surface, the whole
password-reset flow as four more pages of a stack rather than a separate
dialog stack that loses your place.

Three controls here used to be painted on and are now real:

  * "Beni Hatırla" was a checkbox nothing ever read. It now decides
    whether the session is kept, through session_store, which mirrors it
    to every writable location so an update that relaunches under a
    different profile cannot lose it.
  * "Şifremi Unuttum" was a QLabel with a pointing-hand cursor and no
    click handler at all. It now opens a real reset: the server issues a
    six-digit code, mails it, checks it, and writes the new password into
    the table /auth/login reads.
  * The password could not be revealed. It has a Göster/Gizle toggle.

Kept from the previous rewrite because it fixed a reported bug: no
WindowStaysOnTopHint, a working minimize, drag-to-move, and Qt.Window in
the flags so minimising leaves a taskbar button to come back from.
"""
import json
import os
import re
import sys
import threading

from PySide6.QtCore import (
    QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRectF, Qt, QTimer,
)
from PySide6.QtGui import (
    QColor, QFont, QFontDatabase, QIcon, QImage, QLinearGradient, QPainter,
    QPainterPath, QPen, QPixmap,
)
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

import bk_branding
import bk_ui
from api_client import api_client

try:
    import session_store
except Exception:
    session_store = None

try:
    from version import APP_VERSION
except Exception:
    APP_VERSION = ""

# --- Geometry -------------------------------------------------------------
MARGIN = 0
CARD_W, CARD_H = 956, 568
PANEL_W = 388
RADIUS = 16
WIN_W, WIN_H = CARD_W, CARD_H

INK = bk_ui.INK
INK_SOFT = bk_ui.INK_SOFT
INK_FAINT = bk_ui.INK_FAINT
HAIRLINE = bk_ui.HAIRLINE
FIELD_LINE = bk_ui.HAIRLINE_STRONG
DANGER = bk_ui.DANGER

DAYS = ("Pzt", "Sal", "Çar", "Per", "Cum")
GRID_BLOCKS = (
    (0, 0, 2, False), (2, 0, 1, True),  (4, 0, 1, False),
    (1, 1, 2, False), (3, 1, 1, True),  (2, 2, 2, False),
    (4, 2, 2, False), (0, 3, 1, False), (3, 3, 2, False),
    (1, 4, 1, False), (0, 5, 2, False), (2, 5, 1, False),
    (4, 5, 2, False),
)

CODE_LEN = 6
RESEND_SECONDS = 60


def _prefs_path():
    base = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return os.path.join(base, "login_prefs.json")


def _load_prefs():
    try:
        with open(_prefs_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_prefs(prefs):
    try:
        with open(_prefs_path(), "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


_WORDMARK_FACES = (
    ("Gabriola", 1.50), ("Palatino Linotype", 1.04), ("Palatino", 1.04),
    ("Georgia", 1.00), ("Segoe UI", 0.96),
)


def _wordmark_font(base_pt):
    """Same calligraphic face the splash screen traces, with the same
    per-family size correction: Gabriola sets optically much smaller than
    Georgia at an equal point size, so one number would shrink the
    wordmark on Windows and grow it everywhere else."""
    try:
        families = set(QFontDatabase.families())
    except Exception:
        families = set()
    for name, scale in _WORDMARK_FACES:
        if name in families:
            f = QFont(name)
            f.setPointSizeF(base_pt * scale)
            f.setStyleStrategy(QFont.PreferAntialias)
            if name == "Segoe UI":
                f.setWeight(QFont.DemiBold)
            return f
    return bk_ui.font(base_pt, QFont.DemiBold)


class _WinButton(QPushButton):
    """Minimise/close, drawn rather than typed. "—" and "✕" as label text
    land on whatever glyph the fallback font happens to have and sit off
    the optical centre; two strokes from a painter do not."""

    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self._hover = False
        self.setFixedSize(30, 30)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#FBE9E9") if self.kind == "close" else QColor("#F0F0F3"))
            p.drawEllipse(self.rect())
            fg = QColor(DANGER) if self.kind == "close" else QColor("#4A4A52")
        else:
            fg = QColor("#9C9CA4")
        pen = QPen(fg, 1.4)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        c = self.rect().center()
        cx, cy = c.x() + 0.5, c.y() + 0.5
        if self.kind == "min":
            p.drawLine(QPointF(cx - 5, cy + 0.5), QPointF(cx + 5, cy + 0.5))
        else:
            p.drawLine(QPointF(cx - 4.5, cy - 4.5), QPointF(cx + 4.5, cy + 4.5))
            p.drawLine(QPointF(cx + 4.5, cy - 4.5), QPointF(cx - 4.5, cy + 4.5))
        p.end()


class _Field(QLineEdit):
    """Box, hairline, label above — never an icon inside. The border's
    width is constant across states so focusing a field cannot nudge the
    text sitting in it."""

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(48)
        self.setFont(bk_ui.font(10.5))
        self._error = False
        self._pad_right = 14
        self._apply_style()

    def _apply_style(self):
        line = DANGER if self._error else FIELD_LINE
        self.setStyleSheet(f"""
            QLineEdit {{
                background: #FFFFFF;
                border: 1.5px solid {line};
                border-radius: 9px;
                color: {INK};
                selection-background-color: {bk_ui.BRAND};
                selection-color: #FFFFFF;
                padding: 0px {self._pad_right}px 0px 14px;
                font-size: 14px;
            }}
            QLineEdit:focus {{ border: 1.5px solid {bk_ui.BRAND}; }}
            QLineEdit:disabled {{ background: {bk_ui.SURFACE_SUNK}; color: {INK_FAINT}; }}
        """)

    def set_error(self, on):
        if on != self._error:
            self._error = on
            self._apply_style()


class _PasswordField(_Field):
    def __init__(self, placeholder="", parent=None):
        super().__init__(placeholder, parent)
        self.setEchoMode(QLineEdit.Password)
        self._pad_right = 74
        self._apply_style()
        self._toggle = QPushButton("Göster", self)
        self._toggle.setCursor(Qt.PointingHandCursor)
        self._toggle.setFocusPolicy(Qt.NoFocus)
        self._toggle.setFixedSize(52, 26)
        self._toggle.setStyleSheet(f"""
            QPushButton {{
                border: none; background: transparent; padding: 0px;
                color: {INK_SOFT}; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ color: {bk_ui.BRAND}; }}
            QPushButton:disabled {{ color: #C4C4CC; }}
        """)
        self._toggle.clicked.connect(self._flip)

    def _flip(self):
        show = self.echoMode() == QLineEdit.Password
        self.setEchoMode(QLineEdit.Normal if show else QLineEdit.Password)
        self._toggle.setText("Gizle" if show else "Göster")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_toggle"):
            self._toggle.move(self.width() - self._toggle.width() - 12,
                              (self.height() - self._toggle.height()) // 2)


_CHECK_PATH = None


def _check_asset():
    """A white tick, drawn once and cached to disk.

    Qt stylesheets cannot draw a checkmark — only fill a box — so a styled
    QCheckBox without an image is a solid square that says nothing about
    whether it is on. It is written to the user's own config directory
    rather than next to the executable, which under Program Files is not
    writable and left the indicator blank in an installed build.
    """
    global _CHECK_PATH
    if _CHECK_PATH and os.path.exists(_CHECK_PATH):
        return _CHECK_PATH.replace("\\", "/")
    base = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    path = os.path.join(base, "check_white.png")
    if not os.path.exists(path):
        pix = bk_ui.check_glyph("#FFFFFF", 14)
        pix.save(path)
    _CHECK_PATH = path
    return path.replace("\\", "/")


def _field_label(text):
    lbl = QLabel(text.upper())
    lbl.setFont(bk_ui.font(9.0, QFont.DemiBold, spacing=1.1))
    lbl.setStyleSheet(f"color: {INK_FAINT};")
    return lbl


def _hint_label():
    lbl = QLabel("")
    lbl.setFont(bk_ui.font(9.5))
    lbl.setWordWrap(False)
    lbl.setFixedHeight(20)
    lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    return lbl


def _back_link(text="← Giriş ekranına dön"):
    btn = bk_ui.link_button(text)
    btn.setFont(bk_ui.font(9.4, QFont.DemiBold))
    return btn


class LoginDialog(QDialog):
    def __init__(self, logo_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{bk_branding.PRODUCT_NAME} — Giriş")
        self.setFixedSize(WIN_W, WIN_H)
        # Qt.Window (not just a frameless dialog) so minimising leaves a
        # taskbar button to restore from. Explicitly no StaysOnTop.
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        if os.path.exists(bk_branding.ICON_PNG):
            self.setWindowIcon(QIcon(bk_branding.ICON_PNG))

        self._drag_pos = None
        self._entrance_anim = None
        self._shake_anim = None
        self.auth_data = None
        # The horizontal lockup, not the shield: the shield asset on disk
        # is no longer the shield, and the lockup is the mark that carries
        # the institution's name — which is the thing worth saying on the
        # one screen where the user has not yet chosen anything.
        self.logo_path = logo_path or bk_branding.LOCKUP_PNG

        self._prefs = _load_prefs()
        self._probe_result = []
        self._reset_email = ""
        self._reset_ticket = ""
        self._resend_left = 0

        self._build_ui()
        self._restore_prefs()
        self._start_server_probe()

    # --- Painting ---------------------------------------------------------
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        card = QRectF(0, 0, CARD_W, CARD_H)

        path = QPainterPath()
        path.addRoundedRect(card, RADIUS, RADIUS)
        p.save()
        p.setClipPath(path)
        p.fillRect(card, QColor("#FFFFFF"))
        self._paint_brand_panel(p, QRectF(card.left(), card.top(), PANEL_W, card.height()))
        p.restore()

        # The hairline is there to separate a white card from a light
        # desktop. Over the blue panel it has nothing to separate and reads
        # as a stray rim light, so it is clipped to the white half.
        p.save()
        p.setClipRect(QRectF(card.left() + PANEL_W, card.top() - 2,
                             card.width() - PANEL_W + 2, card.height() + 4))
        p.setPen(QPen(QColor(HAIRLINE), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(card.adjusted(0.5, 0.5, -0.5, -0.5), RADIUS, RADIUS)
        p.restore()
        p.end()

    def _paint_brand_panel(self, p, rect):
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor("#1657AE"))
        grad.setColorAt(0.55, QColor(bk_ui.BRAND))
        grad.setColorAt(1.0, QColor(bk_ui.BRAND_DARK))
        p.fillRect(rect, grad)

        p.save()
        p.setClipRect(rect, Qt.IntersectClip)
        self._paint_timetable(p, rect)
        p.restore()

        # Scrim so the footer type stays readable over the grid.
        scrim = QRectF(rect.left(), rect.bottom() - 170, rect.width(), 170)
        sg = QLinearGradient(scrim.topLeft(), scrim.bottomLeft())
        c0 = QColor(bk_ui.BRAND_DARK); c0.setAlpha(0)
        c1 = QColor(bk_ui.BRAND_DARK); c1.setAlpha(215)
        sg.setColorAt(0.0, c0)
        sg.setColorAt(1.0, c1)
        p.fillRect(scrim, sg)

    def _paint_timetable(self, p, rect):
        """A real week grid — Pzt..Cum, lessons dropped into it — bleeding
        off the bottom edge. This is what the program produces; a generic
        abstract pattern here would be decoration about nothing."""
        left = rect.left() + 40
        width = rect.width() - 80
        col_w = width / len(DAYS)
        row_h = 34.0
        top = rect.top() + 276

        p.setBrush(Qt.NoBrush)
        p.setFont(bk_ui.font(8.0, QFont.DemiBold, spacing=0.8))
        p.setPen(QColor(255, 255, 255, 105))
        for i, day in enumerate(DAYS):
            p.drawText(QRectF(left + i * col_w, top - 22, col_w, 16),
                       Qt.AlignHCenter | Qt.AlignVCenter, day)

        for c, r, span, accent in GRID_BLOCKS:
            block = QRectF(left + c * col_w + 3, top + r * row_h + 3,
                           col_w - 6, row_h * span - 6)
            if accent:
                col = QColor(bk_branding.BRAND_RED); col.setAlpha(205)
            else:
                col = QColor(255, 255, 255, 48)
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawRoundedRect(block, 4, 4)

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 34), 1))
        for i in range(len(DAYS) + 1):
            x = left + i * col_w
            p.drawLine(QPointF(x, top), QPointF(x, rect.bottom()))
        j = 0
        while top + j * row_h <= rect.bottom():
            p.drawLine(QPointF(left, top + j * row_h),
                       QPointF(left + width, top + j * row_h))
            j += 1

    # --- UI ---------------------------------------------------------------
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        root.setSpacing(0)
        root.addWidget(self._build_brand_panel())
        root.addWidget(self._build_form_pane(), 1)

    def _build_brand_panel(self):
        panel = QWidget()
        panel.setFixedWidth(PANEL_W)
        panel.setAttribute(Qt.WA_TranslucentBackground)

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(40, 40, 40, 34)
        lay.setSpacing(0)

        mark = QLabel()
        mark.setAttribute(Qt.WA_TranslucentBackground)
        candidates = [
            bk_branding.asset_path("chenkron_logo_white.png"),
            bk_branding.asset_path("chenkron_logo.png"),
            self.logo_path,
            bk_branding.LOCKUP_PNG,
            bk_branding.INNER_LOGO_PNG
        ]
        chosen_path = None
        for c in candidates:
            if c and os.path.exists(c):
                chosen_path = c
                break

        if chosen_path:
            img = QImage(chosen_path)
            if not img.isNull():
                img = img.convertToFormat(QImage.Format_ARGB32)
                # Recolor black/dark pixels to pure white
                for y in range(img.height()):
                    for x in range(img.width()):
                        c = img.pixelColor(x, y)
                        if c.alpha() > 30 and c.red() < 90 and c.green() < 90 and c.blue() < 90:
                            img.setPixelColor(x, y, QColor(255, 255, 255, c.alpha()))
                
                pix = QPixmap.fromImage(img)
                dpr = self.devicePixelRatioF() or 1.0
                target_w = 76
                scaled = pix.scaledToWidth(int(target_w * dpr), Qt.SmoothTransformation)
                scaled.setDevicePixelRatio(dpr)
                mark.setPixmap(scaled)
                mark.setFixedSize(target_w, int(round(target_w * pix.height() / max(1, pix.width()))))
        lay.addWidget(mark)
        lay.addSpacing(16)

        wordmark = QLabel("Chenkron")
        wordmark.setFont(_wordmark_font(25))
        wordmark.setStyleSheet("color: #FFFFFF;")
        wordmark.setFixedHeight(40)
        lay.addWidget(wordmark)

        tagline = QLabel("Ders Dağıtım ve Yönetim Sistemi")
        tagline.setFont(bk_ui.font(9.2, spacing=0.4))
        tagline.setStyleSheet("color: rgba(255, 255, 255, 0.62);")
        lay.addWidget(tagline)

        lay.addStretch(1)

        # Connection status label
        self.lbl_conn = QLabel()
        self.lbl_conn.setTextFormat(Qt.RichText)
        self.lbl_conn.setFont(bk_ui.font(9.0))
        self.lbl_conn.setWordWrap(True)
        self._set_conn(None, "chenki.net")
        lay.addWidget(self.lbl_conn)

        lay.addSpacing(14)
        meta_bits = ["© Chenkron · 2026"]
        if APP_VERSION:
            meta_bits.append(f"Sürüm {APP_VERSION}")
        else:
            meta_bits.append("Sürüm 3.1.2")
        meta = QLabel("\n".join(meta_bits))
        meta.setFont(bk_ui.font(8.8))
        meta.setStyleSheet("color: rgba(255, 255, 255, 0.54);")
        lay.addWidget(meta)
        return panel

    def _build_form_pane(self):
        pane = QWidget()
        pane.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(pane)
        outer.setContentsMargins(56, 20, 44, 40)
        outer.setSpacing(0)

        bar = QHBoxLayout()
        bar.setSpacing(2)
        bar.addStretch(1)
        btn_min = _WinButton("min")
        btn_min.setToolTip("Simge durumuna küçült")
        btn_min.clicked.connect(self.showMinimized)
        bar.addWidget(btn_min)
        btn_close = _WinButton("close")
        btn_close.setToolTip("Kapat")
        btn_close.clicked.connect(self.reject)
        bar.addWidget(btn_close)
        outer.addLayout(bar)

        outer.addSpacing(18)

        # One stack, not a pile of dialogs. Apple's own modality guidance
        # warns against a hierarchy of modal views inside a modal view:
        # people lose the way back. Reset is four more pages of the same
        # window, and every one of them has a visible way home.
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        self.page_signin = self._build_page_signin()
        self.page_email = self._build_page_email()
        self.page_code = self._build_page_code()
        self.page_new = self._build_page_new()
        self.page_done = self._build_page_done()
        for pg in (self.page_signin, self.page_email, self.page_code,
                   self.page_new, self.page_done):
            self.stack.addWidget(pg)
        outer.addWidget(self.stack, 1)

        self.setTabOrder(self.w_user, self.w_pass)
        self.setTabOrder(self.w_pass, self.btn_login)
        return pane

    def _page(self):
        w = QWidget()
        w.setAttribute(Qt.WA_TranslucentBackground)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        return w, lay

    def _heading(self, lay, title, sub):
        h = QLabel(title)
        h.setFont(bk_ui.font(21, QFont.DemiBold, spacing=-0.3))
        h.setStyleSheet(f"color: {INK};")
        lay.addWidget(h)
        lay.addSpacing(6)
        s = QLabel(sub)
        s.setFont(bk_ui.font(10.5))
        s.setStyleSheet(f"color: {INK_SOFT};")
        s.setWordWrap(True)
        lay.addWidget(s)

    # -- page 1: sign in --------------------------------------------------
    def _build_page_signin(self):
        w, lay = self._page()
        lay.addStretch(1)
        self._heading(lay, "Oturum açın", "Kurum hesabınızla devam edin.")
        lay.addSpacing(30)

        lay.addWidget(_field_label("E-POSTA"))
        lay.addSpacing(8)
        self.w_user = _Field()
        self.w_user.returnPressed.connect(self._on_user_return)
        self.w_user.textEdited.connect(self._clear_error)
        lay.addWidget(self.w_user)

        lay.addSpacing(16)
        lay.addWidget(_field_label("ŞİFRE"))
        lay.addSpacing(8)
        self.w_pass = _PasswordField()
        self.w_pass.returnPressed.connect(self.check_login)
        self.w_pass.textEdited.connect(self._clear_error)
        lay.addWidget(self.w_pass)

        lay.addSpacing(8)
        self.lbl_hint = _hint_label()
        self._set_hint("")
        lay.addWidget(self.lbl_hint)

        opts = QHBoxLayout()
        opts.setSpacing(0)
        self.chk_remember = QCheckBox("Beni hatırla")
        self.chk_remember.setCursor(Qt.PointingHandCursor)
        self.chk_remember.setFont(bk_ui.font(9.5))
        self.chk_remember.setStyleSheet(f"""
            QCheckBox {{ color: {INK_SOFT}; spacing: 9px; }}
            QCheckBox::indicator {{
                width: 17px; height: 17px; border-radius: 5px;
                border: 1.5px solid {FIELD_LINE}; background: #FFFFFF;
            }}
            QCheckBox::indicator:checked {{
                background: {bk_ui.BRAND}; border-color: {bk_ui.BRAND};
                image: url("{_check_asset()}");
            }}
        """)
        opts.addWidget(self.chk_remember)
        opts.addStretch(1)
        self.btn_forgot = bk_ui.link_button("Şifremi unuttum")
        self.btn_forgot.clicked.connect(self._open_reset)
        opts.addWidget(self.btn_forgot)
        lay.addLayout(opts)

        lay.addSpacing(22)
        self.btn_login = bk_ui.primary_button("Giriş Yap", height=50)
        self.btn_login.setDefault(True)
        self.btn_login.setAutoDefault(True)
        self.btn_login.clicked.connect(self.check_login)
        lay.addWidget(self.btn_login)
        lay.addStretch(1)
        return w

    # -- page 2: which address --------------------------------------------
    def _build_page_email(self):
        w, lay = self._page()
        lay.addStretch(1)
        back = _back_link()
        back.clicked.connect(self._back_to_signin)
        lay.addWidget(back)
        lay.addSpacing(14)
        self._heading(lay, "Şifrenizi sıfırlayın",
                      "Hesabınızın e-posta adresini girin. Bu adrese 6 haneli "
                      "bir doğrulama kodu göndereceğiz.")
        lay.addSpacing(26)

        lay.addWidget(_field_label("E-POSTA"))
        lay.addSpacing(8)
        self.w_reset_email = _Field()
        self.w_reset_email.returnPressed.connect(self._send_code)
        self.w_reset_email.textEdited.connect(
            lambda *_: (self.w_reset_email.set_error(False), self._set_hint_on(self.lbl_hint_email, "")))
        lay.addWidget(self.w_reset_email)

        lay.addSpacing(8)
        self.lbl_hint_email = _hint_label()
        lay.addWidget(self.lbl_hint_email)

        lay.addSpacing(14)
        self.btn_send_code = bk_ui.primary_button("Kod Gönder", height=50)
        self.btn_send_code.clicked.connect(self._send_code)
        lay.addWidget(self.btn_send_code)
        lay.addStretch(1)
        return w

    # -- page 3: the code --------------------------------------------------
    def _build_page_code(self):
        w, lay = self._page()
        lay.addStretch(1)
        back = _back_link()
        back.clicked.connect(self._back_to_signin)
        lay.addWidget(back)
        lay.addSpacing(14)

        h = QLabel("Kodu girin")
        h.setFont(bk_ui.font(21, QFont.DemiBold, spacing=-0.3))
        h.setStyleSheet(f"color: {INK};")
        lay.addWidget(h)
        lay.addSpacing(6)
        self.lbl_code_sub = QLabel("")
        self.lbl_code_sub.setFont(bk_ui.font(10.5))
        self.lbl_code_sub.setStyleSheet(f"color: {INK_SOFT};")
        self.lbl_code_sub.setWordWrap(True)
        lay.addWidget(self.lbl_code_sub)
        lay.addSpacing(26)

        lay.addWidget(_field_label("DOĞRULAMA KODU"))
        lay.addSpacing(8)
        self.w_code = _Field()
        self.w_code.setMaxLength(CODE_LEN)
        self.w_code.setAlignment(Qt.AlignCenter)
        f = bk_ui.font(15, QFont.DemiBold, spacing=8)
        self.w_code.setFont(f)
        self.w_code.textEdited.connect(self._on_code_typed)
        self.w_code.returnPressed.connect(self._verify_code)
        lay.addWidget(self.w_code)

        lay.addSpacing(8)
        self.lbl_hint_code = _hint_label()
        lay.addWidget(self.lbl_hint_code)

        row = QHBoxLayout()
        row.setSpacing(0)
        self.btn_resend = bk_ui.link_button("Yeni kod gönder")
        self.btn_resend.clicked.connect(self._send_code)
        row.addWidget(self.btn_resend)
        row.addStretch(1)
        lay.addLayout(row)

        lay.addSpacing(18)
        self.btn_verify = bk_ui.primary_button("Doğrula", height=50)
        self.btn_verify.clicked.connect(self._verify_code)
        lay.addWidget(self.btn_verify)
        lay.addStretch(1)
        return w

    # -- page 4: the new password -----------------------------------------
    def _build_page_new(self):
        w, lay = self._page()
        lay.addStretch(1)
        back = _back_link()
        back.clicked.connect(self._back_to_signin)
        lay.addWidget(back)
        lay.addSpacing(14)
        self._heading(lay, "Yeni şifre belirleyin",
                      "En az 6 karakter. Kaydettiğinizde diğer cihazlardaki "
                      "oturumlar etkilenmez.")
        lay.addSpacing(24)

        lay.addWidget(_field_label("YENİ ŞİFRE"))
        lay.addSpacing(8)
        self.w_new1 = _PasswordField()
        lay.addWidget(self.w_new1)

        lay.addSpacing(14)
        lay.addWidget(_field_label("YENİ ŞİFRE (TEKRAR)"))
        lay.addSpacing(8)
        self.w_new2 = _PasswordField()
        self.w_new2.returnPressed.connect(self._submit_new_password)
        lay.addWidget(self.w_new2)

        lay.addSpacing(8)
        self.lbl_hint_new = _hint_label()
        lay.addWidget(self.lbl_hint_new)

        lay.addSpacing(14)
        self.btn_save_pwd = bk_ui.primary_button("Şifreyi Kaydet", height=50)
        self.btn_save_pwd.clicked.connect(self._submit_new_password)
        lay.addWidget(self.btn_save_pwd)
        lay.addStretch(1)
        return w

    # -- page 5: done ------------------------------------------------------
    def _build_page_done(self):
        w, lay = self._page()
        lay.addStretch(1)
        mark = QLabel()
        mark.setPixmap(bk_ui.check_glyph(bk_ui.OK, 40))
        lay.addWidget(mark)
        lay.addSpacing(16)
        self._heading(lay, "Şifreniz güncellendi",
                      "Yeni şifrenizle giriş yapabilirsiniz.")
        lay.addSpacing(26)
        btn = bk_ui.primary_button("Giriş ekranına dön", height=50)
        btn.clicked.connect(self._back_to_signin)
        lay.addWidget(btn)
        lay.addStretch(1)
        return w

    # --- State ------------------------------------------------------------
    def _restore_prefs(self):
        remembered = self._prefs.get("email", "") if self._prefs.get("remember", True) else ""
        self.chk_remember.setChecked(bool(self._prefs.get("remember", True)))
        if remembered:
            self.w_user.setText(remembered)
            QTimer.singleShot(0, self.w_pass.setFocus)
        else:
            QTimer.singleShot(0, self.w_user.setFocus)

    def _set_hint_on(self, lbl, text, error=False):
        lbl.setText(text)
        colour = DANGER if error else INK_SOFT
        weight = "600" if error else "400"
        lbl.setStyleSheet(f"color: {colour}; font-weight: {weight};")

    def _set_hint(self, text, error=False):
        self._set_hint_on(self.lbl_hint, text, error)

    def _clear_error(self, *_):
        self.w_user.set_error(False)
        self.w_pass.set_error(False)
        if self.lbl_hint.text():
            self._set_hint("")

    def _set_conn(self, dot_colour=None, text="chenki.net"):
        self.lbl_conn.setText('<span style="color:rgba(255,255,255,0.72); font-size:12px; font-weight:500;">chenki.net</span>')

    # --- Server reachability ----------------------------------------------
    def _start_server_probe(self):
        threading.Thread(target=self._probe_server, daemon=True).start()
        self._probe_timer = QTimer(self)
        self._probe_timer.timeout.connect(self._poll_probe)
        self._probe_timer.start(200)

    def _probe_server(self):
        ok = False
        try:
            import requests
            resp = requests.get(api_client.base_url, timeout=4)
            ok = resp.status_code < 600
        except Exception:
            ok = False
        self._probe_result.append(ok)

    def _poll_probe(self):
        if not self._probe_result:
            return
        self._probe_timer.stop()
        self._set_conn(None, "chenki.net")

    # --- Entrance / drag ---------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        if self._entrance_anim is None:
            self.setWindowOpacity(0.0)
            anim = QPropertyAnimation(self, b"windowOpacity", self)
            anim.setDuration(260)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start(QPropertyAnimation.DeleteWhenStopped)
            self._entrance_anim = anim

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        # Escape steps back through the reset flow instead of closing the
        # window out from under a half-finished password change.
        if event.key() == Qt.Key_Escape and self.stack.currentWidget() is not self.page_signin:
            self._back_to_signin()
            return
        super().keyPressEvent(event)

    def _shake(self):
        """A rejected password shakes the window, the way every desktop
        login has since Mac OS X — the message alone, in a line that was
        empty a moment ago, is easy to miss when you are looking at the
        button you just pressed."""
        start = self.pos()
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(320)
        for frac, dx in ((0.0, 0), (0.15, -9), (0.35, 8), (0.55, -6), (0.78, 4), (1.0, 0)):
            anim.setKeyValueAt(frac, start + QPoint(dx, 0))
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._shake_anim = anim

    # --- Reset flow --------------------------------------------------------
    def _open_reset(self):
        self.w_reset_email.setText(self.w_user.text().strip())
        self._set_hint_on(self.lbl_hint_email, "")
        self.stack.setCurrentWidget(self.page_email)
        QTimer.singleShot(0, self.w_reset_email.setFocus)

    def _back_to_signin(self):
        self._reset_ticket = ""
        self.w_code.clear()
        self.w_new1.clear()
        self.w_new2.clear()
        self.stack.setCurrentWidget(self.page_signin)
        if self._reset_email:
            self.w_user.setText(self._reset_email)
            self.w_pass.clear()
            QTimer.singleShot(0, self.w_pass.setFocus)

    def _busy(self, btn, on, busy_text, idle_text):
        btn.setEnabled(not on)
        btn.setText(busy_text if on else idle_text)

    def _send_code(self):
        email = self.w_reset_email.text().strip()
        if not email or "@" not in email:
            self.w_reset_email.set_error(True)
            self._set_hint_on(self.lbl_hint_email, "Geçerli bir e-posta adresi girin.", True)
            return
        self._busy(self.btn_send_code, True, "Gönderiliyor…", "Kod Gönder")
        self.w_reset_email.setEnabled(False)
        QTimer.singleShot(30, lambda: self._do_send_code(email))

    def _do_send_code(self, email):
        ok, msg = api_client.request_password_reset(email)
        self._busy(self.btn_send_code, False, "", "Kod Gönder")
        self.w_reset_email.setEnabled(True)
        if not ok:
            self.w_reset_email.set_error(True)
            self._set_hint_on(self.lbl_hint_email, str(msg), True)
            return
        self._reset_email = email
        self.lbl_code_sub.setText(f"{email} adresine gönderilen 6 haneli kodu girin.")
        self._set_hint_on(self.lbl_hint_code, "")
        self.w_code.clear()
        self.stack.setCurrentWidget(self.page_code)
        QTimer.singleShot(0, self.w_code.setFocus)
        self._start_resend_countdown()

    def _start_resend_countdown(self):
        self._resend_left = RESEND_SECONDS
        if not hasattr(self, "_resend_timer"):
            self._resend_timer = QTimer(self)
            self._resend_timer.timeout.connect(self._tick_resend)
        self.btn_resend.setEnabled(False)
        self.btn_resend.setText(f"Yeni kod gönder ({self._resend_left} sn)")
        self._resend_timer.start(1000)

    def _tick_resend(self):
        self._resend_left -= 1
        if self._resend_left <= 0:
            self._resend_timer.stop()
            self.btn_resend.setEnabled(True)
            self.btn_resend.setText("Yeni kod gönder")
        else:
            self.btn_resend.setText(f"Yeni kod gönder ({self._resend_left} sn)")

    def _on_code_typed(self, text):
        digits = re.sub(r"\D", "", text)[:CODE_LEN]
        if digits != text:
            self.w_code.setText(digits)
        self.w_code.set_error(False)
        self._set_hint_on(self.lbl_hint_code, "")
        # Six digits is the whole input; asking for a button press after it
        # is asking the user to confirm something they already finished.
        if len(digits) == CODE_LEN:
            QTimer.singleShot(80, self._verify_code)

    def _verify_code(self):
        code = re.sub(r"\D", "", self.w_code.text())
        if len(code) != CODE_LEN:
            self.w_code.set_error(True)
            self._set_hint_on(self.lbl_hint_code, f"{CODE_LEN} haneli kodu girin.", True)
            return
        self._busy(self.btn_verify, True, "Doğrulanıyor…", "Doğrula")
        self.w_code.setEnabled(False)
        QTimer.singleShot(30, lambda: self._do_verify(code))

    def _do_verify(self, code):
        ok, res = api_client.verify_reset_code(self._reset_email, code)
        self._busy(self.btn_verify, False, "", "Doğrula")
        self.w_code.setEnabled(True)
        if not ok:
            self.w_code.set_error(True)
            self._set_hint_on(self.lbl_hint_code, str(res), True)
            self.w_code.selectAll()
            self.w_code.setFocus()
            return
        self._reset_ticket = res
        self._set_hint_on(self.lbl_hint_new, "")
        self.stack.setCurrentWidget(self.page_new)
        QTimer.singleShot(0, self.w_new1.setFocus)

    def _submit_new_password(self):
        p1, p2 = self.w_new1.text(), self.w_new2.text()
        if len(p1) < 6:
            self.w_new1.set_error(True)
            self._set_hint_on(self.lbl_hint_new, "Şifre en az 6 karakter olmalıdır.", True)
            return
        if p1 != p2:
            self.w_new2.set_error(True)
            self._set_hint_on(self.lbl_hint_new, "Şifreler birbiriyle eşleşmiyor.", True)
            return
        self.w_new1.set_error(False)
        self.w_new2.set_error(False)
        self._busy(self.btn_save_pwd, True, "Kaydediliyor…", "Şifreyi Kaydet")
        QTimer.singleShot(30, lambda: self._do_submit(p1))

    def _do_submit(self, new_password):
        ok, msg = api_client.submit_new_password(
            self._reset_email, self._reset_ticket, new_password)
        self._busy(self.btn_save_pwd, False, "", "Şifreyi Kaydet")
        if not ok:
            self._set_hint_on(self.lbl_hint_new, str(msg), True)
            return
        self._reset_ticket = ""
        self.stack.setCurrentWidget(self.page_done)

    # --- Auth --------------------------------------------------------------
    def _on_user_return(self):
        if self.w_pass.text().strip():
            self.check_login()
        else:
            self.w_pass.setFocus()

    def _set_busy(self, busy):
        self.btn_login.setEnabled(not busy)
        self.btn_login.setText("Giriş yapılıyor…" if busy else "Giriş Yap")
        self.w_user.setEnabled(not busy)
        self.w_pass.setEnabled(not busy)

    def check_login(self):
        email = self.w_user.text().strip()
        password = self.w_pass.text().strip()
        if not email or not password:
            self.w_user.set_error(not email)
            self.w_pass.set_error(not password)
            self._set_hint("Lütfen e-posta ve şifrenizi girin.", error=True)
            self._shake()
            (self.w_user if not email else self.w_pass).setFocus()
            return
        self._set_hint("")
        self._set_busy(True)
        QTimer.singleShot(50, lambda: self._do_auth(email, password))

    def _do_auth(self, email, password):
        success, result = api_client.login(email, password)
        if success:
            self.auth_data = result
            remember = self.chk_remember.isChecked()
            self._prefs["remember"] = remember
            self._prefs["email"] = email if remember else ""
            _save_prefs(self._prefs)
            if session_store is not None:
                try:
                    if remember and isinstance(result, dict):
                        session_store.write(result)
                    elif not remember:
                        session_store.clear()
                except Exception as exc:
                    print(f"[Login] session_store note: {exc}")

            def _bg_pull():
                try:
                    api_client.pull_all_from_rtdb()
                except Exception as ex:
                    print(f"[Login] Background cloud pull note: {ex}")

            threading.Thread(target=_bg_pull, daemon=True).start()
            self.accept()
        else:
            self._set_busy(False)
            self.w_pass.set_error(True)
            self._set_hint(str(result), error=True)
            self.w_pass.selectAll()
            self.w_pass.setFocus()
            self._shake()
