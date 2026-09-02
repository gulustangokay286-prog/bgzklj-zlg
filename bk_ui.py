# -*- coding: utf-8 -*-
"""bk_ui.py — one place the whole program gets its look from.

Before this file the program had two design languages arguing with each
other. The sign-in window used the institution's real navy, #0F4AAB,
sampled off the supplied brand mark. The dashboard used #0071E3 — Apple's
blue — and called itself "Apple HIG minimalist" in its own docstring. The
dialogs then picked whichever of the two they were written next to, plus
a few greys of their own. Nothing was wrong in isolation; together they
read as three products in a trench coat.

So the tokens live here and nowhere else, and the primitives below are
the only place a border radius, a focus ring or a button height is
decided. A screen that needs a button asks for one; it does not describe
one. That is what makes "redesign every dialog" a finite job instead of
sixty separate judgement calls.

The rules the tokens encode, so they are not re-litigated per screen:

  * One accent. Brand navy carries every primary action and every
    selected state. Green, amber and red mean success, caution and
    danger — they are never decoration.
  * Type does the work that borders used to. Four sizes, three weights.
    Section labels are small, letter-spaced and quiet; headings are the
    only large type on a screen.
  * Surfaces are separated by a hairline and a radius, not by a shadow.
    Shadows are for things that float above the window — sheets — and
    are painted, not blurred by a graphics effect.
  * A control's height never changes between its states. Focus and error
    change a border's colour, never its width, or the text inside shifts.
"""
import os

from PySide6.QtCore import (
    Property as QtProperty, QEasingCurve, QParallelAnimationGroup, QPoint,
    QPointF, QPropertyAnimation, QRect, QRectF, QSize, Qt, Signal, QTimer,
)
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontDatabase, QFontMetrics, QIcon, QImage,
    QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractButton, QApplication, QDialog, QFrame, QGraphicsBlurEffect,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QGraphicsPixmapItem, QGraphicsScene, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

import bk_branding

# ── Colour ────────────────────────────────────────────────────────────
BRAND = bk_branding.BRAND_BLUE            # #0F4AAB — sampled from the mark
BRAND_DARK = bk_branding.BRAND_BLUE_DARK  # pressed / hover
BRAND_DEEP = "#082B67"                    # active
BRAND_TINT = "#EDF2FB"                    # selected row, quiet fill
BRAND_TINT_LINE = "#D5E0F3"
ACCENT_RED = bk_branding.BRAND_RED        # the flame in the shield

INK = "#111114"        # headings, primary text
INK_BODY = "#4A4A52"   # body copy
INK_SOFT = "#6E6E76"   # secondary / captions
INK_FAINT = "#9A9AA2"  # labels, disabled, metadata

CANVAS = "#F6F7F9"     # window behind the cards
SURFACE = "#FFFFFF"    # cards, sidebars, sheets
SURFACE_SUNK = "#F2F3F6"  # search fields, inset wells
HOVER = "#F4F5F7"

HAIRLINE = "#E4E4E8"
HAIRLINE_STRONG = "#D8DAE0"

OK = "#2E9E5B"
OK_TINT = "#E9F7EF"
WARN = "#C9821A"
WARN_TINT = "#FDF3E3"
DANGER = "#D64545"
DANGER_TINT = "#FBE9E9"

# ── Geometry ──────────────────────────────────────────────────────────
R_CONTROL = 9    # inputs, buttons
R_CARD = 12      # cards, rows
R_SHEET = 18     # floating sheets
H_CONTROL = 40   # compact control height
H_FIELD = 46     # text input
H_BUTTON = 44    # standalone button

# ── Type ──────────────────────────────────────────────────────────────
UI_FAMILIES = ["SF Pro Text", "Inter", "Segoe UI", "-apple-system", "Helvetica Neue", "Arial", "sans-serif"]
FONT_FAMILY = "SF Pro Text, Inter, Segoe UI, Helvetica Neue, Arial, sans-serif"


def font(pt=9.5, weight=QFont.Normal, spacing=0.0):
    f = QFont()
    f.setFamilies(UI_FAMILIES)
    f.setPointSizeF(pt)
    f.setWeight(weight)
    if spacing:
        f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return f


# Handwriting, for the one place the program speaks in its own voice: the
# section marker on the dashboard. The institution's own lockup carries a
# red script line ("Geleceğiniz için…"), so the hand is already part of
# this identity rather than an ornament borrowed for the occasion.
#
# Each face gets its own size multiplier because script faces vary wildly
# in optical size — Snell Roundhand at 14pt reads about as large as Segoe
# Script at 11pt — and one point size would give a different-sized header
# on every machine.
_SCRIPT_FACES = (
    ("Segoe Script", 1.00),        # Windows
    ("Bradley Hand", 1.12),        # macOS
    ("Noteworthy", 1.00),
    ("Snell Roundhand", 1.32),
    ("Apple Chancery", 1.18),
    ("Lucida Handwriting", 1.02),
    ("Gabriola", 1.45),
    ("Palatino", 1.05),            # last resorts: at least not a UI sans
    ("Georgia", 1.00),
)


def script_family(default="Georgia"):
    """The name of the best handwriting face present, for use inside Qt
    rich text — where a font has to be named as a string, not built."""
    try:
        families = set(QFontDatabase.families())
    except Exception:
        return default
    for name, _scale in _SCRIPT_FACES:
        if name in families:
            return name
    return default


# A separate list for the ampersand alone. The section marker sets its
# "&" a size and a half up, so that one glyph is doing real typographic
# work — and the faces differ wildly in how good their ampersand is.
# Bradley Hand's is a squiggle that reads as an "S"; Snell Roundhand's and
# Apple Chancery's are the classic swash form. Ordered by that, not by
# what happens to be first in the handwriting list.
_AMPERSAND_FACES = (
    "Snell Roundhand",      # macOS — the classic swash ampersand
    "Apple Chancery",
    "Segoe Script",         # Windows
    "Palatino Linotype",
    "Palatino",
    "Georgia",
)


def ampersand_family(default="Georgia"):
    try:
        families = set(QFontDatabase.families())
    except Exception:
        return default
    for name in _AMPERSAND_FACES:
        if name in families:
            return name
    return default


def script_font(base_pt=12.5, weight=QFont.Normal):
    try:
        families = set(QFontDatabase.families())
    except Exception:
        families = set()
    for name, scale in _SCRIPT_FACES:
        if name in families:
            f = QFont(name)
            f.setPointSizeF(base_pt * scale)
            f.setStyleStrategy(QFont.PreferAntialias)
            f.setWeight(weight)
            return f
    f = font(base_pt, weight)
    f.setItalic(True)
    return f


def title_font(pt=16):
    return font(pt, QFont.DemiBold, spacing=-0.2)


def label_font():
    """Small, letter-spaced, quiet — the voice used for the name of a
    group of things rather than for a thing."""
    return font(8.2, QFont.DemiBold, spacing=0.8)


# ── Text ──────────────────────────────────────────────────────────────
def heading(text, pt=19):
    lbl = QLabel(text)
    lbl.setFont(title_font(pt))
    lbl.setStyleSheet(f"color: {INK}; background: transparent;")
    return lbl


def subheading(text):
    lbl = QLabel(text)
    lbl.setFont(font(10.5))
    lbl.setStyleSheet(f"color: {INK_SOFT}; background: transparent;")
    lbl.setWordWrap(True)
    return lbl


def section_label(text):
    lbl = QLabel(text.upper())
    lbl.setFont(label_font())
    lbl.setStyleSheet(f"color: {INK_FAINT}; background: transparent;")
    return lbl


def caption(text, colour=None):
    lbl = QLabel(text)
    lbl.setFont(font(9.2))
    lbl.setStyleSheet(f"color: {colour or INK_FAINT}; background: transparent;")
    return lbl


def hairline(vertical=False):
    line = QFrame()
    if vertical:
        line.setFixedWidth(1)
    else:
        line.setFixedHeight(1)
    line.setStyleSheet(f"background: {HAIRLINE}; border: none;")
    return line


# ── Buttons ───────────────────────────────────────────────────────────
def _button_base(text, height):
    btn = QPushButton(text)
    btn.setFixedHeight(height)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFont(font(10.2, QFont.DemiBold))
    return btn


def primary_button(text, height=H_BUTTON):
    """The one action a screen is for. At most one per screen."""
    btn = _button_base(text, height)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {BRAND}; color: #FFFFFF;
            border: none; border-radius: {R_CONTROL}px; padding: 0px 20px;
        }}
        QPushButton:hover {{ background: {BRAND_DARK}; }}
        QPushButton:pressed {{ background: {BRAND_DEEP}; }}
        QPushButton:disabled {{ background: #9EB4D8; color: #F0F4FB; }}
    """)
    return btn


def secondary_button(text, height=H_BUTTON):
    """Everything else that is still a button. Outlined, not filled, so a
    row of three does not read as three equally urgent choices."""
    btn = _button_base(text, height)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {SURFACE}; color: {INK};
            border: 1.5px solid {HAIRLINE_STRONG};
            border-radius: {R_CONTROL}px; padding: 0px 18px;
        }}
        QPushButton:hover {{ background: {HOVER}; border-color: {INK_FAINT}; }}
        QPushButton:pressed {{ background: {SURFACE_SUNK}; }}
        QPushButton:disabled {{ color: {INK_FAINT}; border-color: {HAIRLINE}; }}
    """)
    return btn


def danger_button(text, height=H_BUTTON):
    btn = _button_base(text, height)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {DANGER}; color: #FFFFFF;
            border: none; border-radius: {R_CONTROL}px; padding: 0px 20px;
        }}
        QPushButton:hover {{ background: #BE3A3A; }}
        QPushButton:pressed {{ background: #A63333; }}
        QPushButton:disabled {{ background: #E7A9A9; color: #FBF0F0; }}
    """)
    return btn


def link_button(text, colour=None):
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFlat(True)
    btn.setFocusPolicy(Qt.NoFocus)
    btn.setFont(font(9.5, QFont.DemiBold))
    c = colour or BRAND
    btn.setStyleSheet(f"""
        QPushButton {{
            border: none; background: transparent; padding: 0px;
            text-align: left; color: {c};
        }}
        QPushButton:hover {{ color: {BRAND_DARK}; }}
        QPushButton:disabled {{ color: {INK_FAINT}; }}
    """)
    return btn


class IconButton(QPushButton):
    """A borderless square that only shows its shape on hover. Toolbar
    icons that carry a permanent box turn a header into a control panel."""

    def __init__(self, pixmap=None, tooltip="", size=32, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        if tooltip:
            self.setToolTip(tooltip)
        if pixmap is not None:
            self.setIcon(QIcon(pixmap))
            self.setIconSize(QSize(int(size * 0.55), int(size * 0.55)))
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                border-radius: {size // 2}px;
            }}
            QPushButton:hover {{ background: {HOVER}; }}
            QPushButton:pressed {{ background: {SURFACE_SUNK}; }}
        """)


# ── Inputs ────────────────────────────────────────────────────────────
class Field(QLineEdit):
    """Box, hairline, label above — never an icon inside. The border's
    width is constant across states so focusing a field cannot nudge the
    text sitting in it."""

    def __init__(self, placeholder="", parent=None, height=H_FIELD, font_px=13.5):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(height)
        self._font_px = font_px
        self._error = False
        self._restyle()

    def _restyle(self):
        line = DANGER if self._error else HAIRLINE_STRONG
        self.setStyleSheet(f"""
            QLineEdit {{
                background: {SURFACE};
                border: 1.5px solid {line};
                border-radius: {R_CONTROL}px;
                color: {INK};
                selection-background-color: {BRAND};
                selection-color: #FFFFFF;
                padding: 0px 13px;
                font-size: {self._font_px}px;
            }}
            QLineEdit:focus {{ border: 1.5px solid {BRAND}; }}
            QLineEdit:disabled {{ background: {SURFACE_SUNK}; color: {INK_FAINT}; }}
        """)

    def set_error(self, on):
        if on != self._error:
            self._error = on
            self._restyle()


def field_label(text):
    lbl = QLabel(text.upper())
    lbl.setFont(label_font())
    lbl.setStyleSheet(f"color: {INK_FAINT}; background: transparent;")
    return lbl


class SearchField(QFrame):
    """Sunk rather than outlined: a search box is a place to type, not a
    field in a form, and giving it the same border as a form input makes
    every header look like it is asking a question."""

    def __init__(self, placeholder="Ara", width=260, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        if width:
            self.setFixedWidth(width)
        self.setStyleSheet(f"""
            QFrame {{
                background: {SURFACE_SUNK};
                border: 1px solid transparent;
                border-radius: {R_CONTROL}px;
            }}
            QFrame:focus-within {{ background: {SURFACE}; border: 1px solid {BRAND}; }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(11, 0, 10, 0)
        lay.setSpacing(8)

        glass = QLabel()
        glass.setFixedSize(14, 14)
        glass.setPixmap(search_glyph(INK_FAINT, 14))
        glass.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(glass)

        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setFont(font(10))
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent; border: none; padding: 0px;
                color: {INK}; font-size: 13px;
                selection-background-color: {BRAND}; selection-color: #FFFFFF;
            }}
        """)
        lay.addWidget(self.input, 1)

    def text(self):
        return self.input.text()

    def setText(self, value):
        self.input.setText(value)


# ── Painted glyphs ────────────────────────────────────────────────────
# Drawn rather than shipped as PNGs: they follow the token colours, stay
# sharp at any DPI, and cannot go missing from a PyInstaller bundle.
def _canvas(size, dpr=None):
    try:
        if dpr is None:
            dpr = _screen_dpr()
    except Exception:
        dpr = 2.0
    dpr = max(2.0, float(dpr or 2.0))
    actual_sz = int(round(size * dpr))
    pix = QPixmap(actual_sz, actual_sz)
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    return pix, p


def _stroke(p, colour, width):
    pen = QPen(QColor(colour), width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    return pen


def search_glyph(colour=INK_FAINT, size=16):
    pix, p = _canvas(size)
    s = size / 16.0
    _stroke(p, colour, 1.6 * s)
    p.drawEllipse(QRectF(2.4 * s, 2.4 * s, 8.4 * s, 8.4 * s))
    p.drawLine(QPointF(10.4 * s, 10.4 * s), QPointF(13.6 * s, 13.6 * s))
    p.end()
    return pix


def chevron_glyph(colour=INK_FAINT, size=16, direction="right"):
    pix, p = _canvas(size)
    s = size / 16.0
    _stroke(p, colour, 1.7 * s)
    path = QPainterPath()
    if direction == "right":
        path.moveTo(6 * s, 3.5 * s); path.lineTo(10.5 * s, 8 * s); path.lineTo(6 * s, 12.5 * s)
    elif direction == "down":
        path.moveTo(3.5 * s, 6 * s); path.lineTo(8 * s, 10.5 * s); path.lineTo(12.5 * s, 6 * s)
    else:
        path.moveTo(10 * s, 3.5 * s); path.lineTo(5.5 * s, 8 * s); path.lineTo(10 * s, 12.5 * s)
    p.drawPath(path)
    p.end()
    return pix


def plus_glyph(colour="#111114", size=16, dpr=None):
    pix, p = _canvas(size, dpr=dpr)
    s = size / 16.0
    _stroke(p, colour, 1.9 * s)
    p.drawLine(QPointF(8 * s, 3.2 * s), QPointF(8 * s, 12.8 * s))
    p.drawLine(QPointF(3.2 * s, 8 * s), QPointF(12.8 * s, 8 * s))
    p.end()
    return pix


def check_glyph(colour=OK, size=16):
    pix, p = _canvas(size)
    s = size / 16.0
    _stroke(p, colour, 1.9 * s)
    path = QPainterPath()
    path.moveTo(3.4 * s, 8.4 * s); path.lineTo(6.7 * s, 11.7 * s); path.lineTo(12.6 * s, 4.8 * s)
    p.drawPath(path)
    p.end()
    return pix


def dots_glyph(colour=INK_SOFT, size=16):
    pix, p = _canvas(size)
    s = size / 16.0
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(colour))
    for cx in (4.0, 8.0, 12.0):
        p.drawEllipse(QPointF(cx * s, 8 * s), 1.25 * s, 1.25 * s)
    p.end()
    return pix


def user_glyph(colour=INK, size=16, dpr=None):
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    p.drawEllipse(QRectF(5.2 * s, 2.2 * s, 5.6 * s, 5.6 * s))
    path = QPainterPath()
    path.moveTo(2.4 * s, 13.8 * s)
    path.quadTo(2.6 * s, 9.6 * s, 8.0 * s, 9.6 * s)
    path.quadTo(13.4 * s, 9.6 * s, 13.6 * s, 13.8 * s)
    p.drawPath(path)
    p.end()
    return pix


def key_glyph(colour=INK, size=16, dpr=None):
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    p.drawEllipse(QRectF(2.6 * s, 2.6 * s, 6.0 * s, 6.0 * s))
    p.drawLine(QPointF(7.0 * s, 7.0 * s), QPointF(13.4 * s, 13.4 * s))
    p.drawLine(QPointF(11.2 * s, 11.2 * s), QPointF(12.8 * s, 9.6 * s))
    p.drawLine(QPointF(13.4 * s, 13.4 * s), QPointF(14.6 * s, 12.2 * s))
    p.end()
    return pix


def building_glyph(colour=INK, size=16, dpr=None):
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    p.drawRoundedRect(QRectF(3.0 * s, 2.5 * s, 10.0 * s, 11.0 * s), 1.5 * s, 1.5 * s)
    p.drawLine(QPointF(5.5 * s, 5.5 * s), QPointF(7.0 * s, 5.5 * s))
    p.drawLine(QPointF(9.0 * s, 5.5 * s), QPointF(10.5 * s, 5.5 * s))
    p.drawLine(QPointF(5.5 * s, 8.5 * s), QPointF(7.0 * s, 8.5 * s))
    p.drawLine(QPointF(9.0 * s, 8.5 * s), QPointF(10.5 * s, 8.5 * s))
    p.drawLine(QPointF(6.5 * s, 13.5 * s), QPointF(6.5 * s, 11.0 * s))
    p.drawLine(QPointF(6.5 * s, 11.0 * s), QPointF(9.5 * s, 11.0 * s))
    p.drawLine(QPointF(9.5 * s, 11.0 * s), QPointF(9.5 * s, 13.5 * s))
    p.end()
    return pix


def cloud_glyph(colour=INK, size=16, dpr=None):
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    path = QPainterPath()
    path.moveTo(4.0 * s, 12.5 * s)
    path.lineTo(12.0 * s, 12.5 * s)
    path.arcTo(QRectF(10.0 * s, 7.5 * s, 4.0 * s, 5.0 * s), 270, 180)
    path.arcTo(QRectF(6.0 * s, 4.0 * s, 6.0 * s, 6.0 * s), 0, 180)
    path.arcTo(QRectF(2.0 * s, 7.5 * s, 4.0 * s, 5.0 * s), 90, 180)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return pix


def sync_glyph(colour=INK, size=16, dpr=None):
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    path1 = QPainterPath()
    path1.arcTo(QRectF(2.5 * s, 2.5 * s, 11.0 * s, 11.0 * s), 45, 150)
    p.drawPath(path1)
    p.drawLine(QPointF(12.5 * s, 3.5 * s), QPointF(12.5 * s, 7.5 * s))
    p.drawLine(QPointF(12.5 * s, 7.5 * s), QPointF(8.5 * s, 7.5 * s))
    
    path2 = QPainterPath()
    path2.arcTo(QRectF(2.5 * s, 2.5 * s, 11.0 * s, 11.0 * s), 225, 150)
    p.drawPath(path2)
    p.drawLine(QPointF(3.5 * s, 12.5 * s), QPointF(3.5 * s, 8.5 * s))
    p.drawLine(QPointF(3.5 * s, 8.5 * s), QPointF(7.5 * s, 8.5 * s))
    p.end()
    return pix


def settings_glyph(colour=INK_SOFT, size=16, dpr=None):
    """Settings / gear icon."""
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.4 * s)
    cx, cy = 8.0 * s, 8.0 * s
    p.drawEllipse(QPointF(cx, cy), 3.0 * s, 3.0 * s)
    import math
    for i in range(6):
        ang = i * (math.pi / 3.0)
        x1 = cx + math.cos(ang) * 4.2 * s
        y1 = cy + math.sin(ang) * 4.2 * s
        x2 = cx + math.cos(ang) * 6.6 * s
        y2 = cy + math.sin(ang) * 6.6 * s
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    p.end()
    return pix


gear_glyph = settings_glyph


def logout_glyph(colour=DANGER, size=16, dpr=None):
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    path = QPainterPath()
    path.moveTo(7.0 * s, 2.5 * s)
    path.lineTo(3.0 * s, 2.5 * s)
    path.lineTo(3.0 * s, 13.5 * s)
    path.lineTo(7.0 * s, 13.5 * s)
    p.drawPath(path)
    p.drawLine(QPointF(6.0 * s, 8.0 * s), QPointF(13.5 * s, 8.0 * s))
    p.drawLine(QPointF(11.0 * s, 5.5 * s), QPointF(13.5 * s, 8.0 * s))
    p.drawLine(QPointF(11.0 * s, 10.5 * s), QPointF(13.5 * s, 8.0 * s))
    p.end()
    return pix


def pencil_glyph(colour=INK, size=16, dpr=None):
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    path = QPainterPath()
    path.moveTo(11.5 * s, 2.5 * s)
    path.lineTo(13.5 * s, 4.5 * s)
    path.lineTo(5.5 * s, 12.5 * s)
    path.lineTo(2.5 * s, 13.5 * s)
    path.lineTo(3.5 * s, 10.5 * s)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return pix


def trash_glyph(colour=DANGER, size=16, dpr=None):
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    p.drawLine(QPointF(2.5 * s, 4.5 * s), QPointF(13.5 * s, 4.5 * s))
    p.drawLine(QPointF(6.0 * s, 4.5 * s), QPointF(6.0 * s, 2.8 * s))
    p.drawLine(QPointF(6.0 * s, 2.8 * s), QPointF(10.0 * s, 2.8 * s))
    p.drawLine(QPointF(10.0 * s, 2.8 * s), QPointF(10.0 * s, 4.5 * s))
    path = QPainterPath()
    path.moveTo(4.0 * s, 4.5 * s)
    path.lineTo(4.5 * s, 13.5 * s)
    path.lineTo(11.5 * s, 13.5 * s)
    path.lineTo(12.0 * s, 4.5 * s)
    p.drawPath(path)
    p.drawLine(QPointF(6.8 * s, 6.8 * s), QPointF(6.8 * s, 11.2 * s))
    p.drawLine(QPointF(9.2 * s, 6.8 * s), QPointF(9.2 * s, 11.2 * s))
    p.end()
    return pix


def folder_line_glyph(colour=INK, size=16, dpr=None):
    """The flat, line-art folder — for buttons and menus.

    It needs its own name because `folder_glyph` is defined twice in this
    file and the later definition, which forwards to the 3-D drawing,
    wins. That is fine for lists, where a folder earns its detail; inside
    a 36px button an illustration is noise, and the icon should be a line
    at the weight of the text beside it.
    """
    return _folder_line(colour, size, dpr)


def _folder_line(colour=INK, size=16, dpr=None):
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    path = QPainterPath()
    path.moveTo(2.5 * s, 4.0 * s)
    path.lineTo(6.5 * s, 4.0 * s)
    path.lineTo(8.0 * s, 5.5 * s)
    path.lineTo(13.5 * s, 5.5 * s)
    path.lineTo(13.5 * s, 12.5 * s)
    path.lineTo(2.5 * s, 12.5 * s)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return pix


def star_glyph(colour=INK, size=16, dpr=None):
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    path = QPainterPath()
    path.moveTo(8.0 * s, 2.0 * s)
    path.lineTo(9.8 * s, 5.8 * s)
    path.lineTo(14.0 * s, 6.4 * s)
    path.lineTo(11.0 * s, 9.3 * s)
    path.lineTo(11.7 * s, 13.5 * s)
    path.lineTo(8.0 * s, 11.5 * s)
    path.lineTo(4.3 * s, 13.5 * s)
    path.lineTo(5.0 * s, 9.3 * s)
    path.lineTo(2.0 * s, 6.4 * s)
    path.lineTo(6.2 * s, 5.8 * s)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return pix


def folder_3d_glyph(colour=None, size=30, dpr=None):
    """Draws a rich, modern 3D folder in perspective with lighting, inner document and glossy highlight."""
    if dpr is None:
        dpr = _screen_dpr()
    dpr = max(1.0, float(dpr))
    # The folder is drawn in whatever colour it is handed, not always in
    # amber. Every school folder used to come out the same orange, which
    # made the colour useless for telling one from another — the whole
    # reason for giving a folder a colour. The five stops below are
    # derived from one hue so the shading stays a real light study rather
    # than five unrelated swatches.
    _c = QColor(colour) if colour else QColor("#FFA000")
    if not _c.isValid():
        _c = QColor("#FFA000")
    _h = _c.hue() if _c.hue() >= 0 else 38
    _s = max(60, _c.saturation())

    def _tone(sat_mul, val):
        return QColor.fromHsv(_h, max(0, min(255, int(_s * sat_mul))),
                              max(0, min(255, int(val))))

    BACK_HI, BACK_MID, BACK_LO = _tone(1.00, 205), _tone(1.05, 186), _tone(1.10, 148)
    FRONT_HI, FRONT_A = _tone(0.72, 246), _tone(0.82, 236)
    FRONT_B, FRONT_LO = _tone(0.95, 214), _tone(1.02, 196)

    actual_sz = int(round(size * dpr))
    pix = QPixmap(actual_sz, actual_sz)
    pix.fill(Qt.transparent)
    
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    
    scale = actual_sz / 32.0
    p.scale(scale, scale)
    
    # 1. Back Tab & Back Cover (Golden Amber 3D)
    back_path = QPainterPath()
    back_path.moveTo(3, 9)
    back_path.lineTo(3, 7)
    back_path.quadTo(3, 5, 5, 5)
    back_path.lineTo(11.5, 5)
    back_path.quadTo(13.2, 5, 14.6, 6.6)
    back_path.lineTo(16.2, 8.2)
    back_path.lineTo(27, 8.2)
    back_path.quadTo(29, 8.2, 29, 10.2)
    back_path.lineTo(29, 24)
    back_path.quadTo(29, 26, 27, 26)
    back_path.lineTo(5, 26)
    back_path.quadTo(3, 26, 3, 24)
    back_path.closeSubpath()
    
    back_grad = QLinearGradient(0, 5, 0, 26)
    back_grad.setColorAt(0.0, BACK_HI)
    back_grad.setColorAt(0.5, BACK_MID)
    back_grad.setColorAt(1.0, BACK_LO)
    p.setBrush(QBrush(back_grad))
    p.setPen(Qt.NoPen)
    p.drawPath(back_path)
    
    # 2. Inner Document
    doc_path = QPainterPath()
    doc_path.moveTo(7, 7.5)
    doc_path.lineTo(25, 7.5)
    doc_path.lineTo(25, 18)
    doc_path.lineTo(7, 18)
    doc_path.closeSubpath()
    doc_grad = QLinearGradient(0, 7.5, 0, 18)
    doc_grad.setColorAt(0.0, QColor('#FFFFFF'))
    doc_grad.setColorAt(1.0, QColor('#EDF2F7'))
    p.setBrush(QBrush(doc_grad))
    p.drawPath(doc_path)
    
    # Document lines
    p.setPen(QPen(QColor('#CBD5E1'), 1.0, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(10, 10.5), QPointF(22, 10.5))
    p.drawLine(QPointF(10, 13.5), QPointF(18, 13.5))
    
    # 3. Ambient depth shadow behind front flap
    shadow_path = QPainterPath()
    shadow_path.moveTo(2.5, 13)
    shadow_path.lineTo(29.5, 13)
    shadow_path.lineTo(29.5, 19)
    shadow_path.lineTo(2.5, 19)
    shadow_path.closeSubpath()
    p.setBrush(QColor(0, 0, 0, 45))
    p.setPen(Qt.NoPen)
    p.drawPath(shadow_path)
    
    # 4. 3D Front Flap (Angled in perspective)
    front_path = QPainterPath()
    front_path.moveTo(2.6, 12)
    front_path.lineTo(29.4, 12)
    front_path.quadTo(30.4, 12, 30.1, 13.4)
    front_path.lineTo(28.2, 25.4)
    front_path.quadTo(27.8, 26.8, 26.0, 26.8)
    front_path.lineTo(4.0, 26.8)
    front_path.quadTo(2.2, 26.8, 1.8, 25.4)
    front_path.lineTo(1.9, 13.4)
    front_path.quadTo(1.6, 12, 2.6, 12)
    front_path.closeSubpath()
    
    front_grad = QLinearGradient(0, 12, 0, 27)
    front_grad.setColorAt(0.0, FRONT_HI)
    front_grad.setColorAt(0.3, FRONT_A)
    front_grad.setColorAt(0.7, FRONT_B)
    front_grad.setColorAt(1.0, FRONT_LO)
    p.setBrush(QBrush(front_grad))
    p.drawPath(front_path)
    
    # 5. Top rim gloss / highlight on front flap
    p.setPen(QPen(QColor(255, 255, 255, 220), 1.2, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(3.6, 12.6), QPointF(28.4, 12.6))
    
    # Bottom edge 3D shadow
    p.setPen(QPen(QColor(180, 80, 0, 110), 1.0, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(4.2, 26.5), QPointF(25.8, 26.5))
    
    p.end()
    pix.setDevicePixelRatio(dpr)
    return pix


def folder_glyph(colour=INK_SOFT, size=18, dpr=None):
    return folder_3d_glyph(colour, size, dpr=dpr)


def archive_3d_glyph(colour=None, size=30, dpr=None):
    """Draws a 3D Slate / Archive Folder for unfoldered / past version groups."""
    if dpr is None:
        dpr = _screen_dpr()
    dpr = max(1.0, float(dpr))
    actual_sz = int(round(size * dpr))
    pix = QPixmap(actual_sz, actual_sz)
    pix.fill(Qt.transparent)
    
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    
    scale = actual_sz / 32.0
    p.scale(scale, scale)
    
    back_path = QPainterPath()
    back_path.moveTo(3, 9)
    back_path.lineTo(3, 7)
    back_path.quadTo(3, 5, 5, 5)
    back_path.lineTo(11.5, 5)
    back_path.quadTo(13.2, 5, 14.6, 6.6)
    back_path.lineTo(16.2, 8.2)
    back_path.lineTo(27, 8.2)
    back_path.quadTo(29, 8.2, 29, 10.2)
    back_path.lineTo(29, 24)
    back_path.quadTo(29, 26, 27, 26)
    back_path.lineTo(5, 26)
    back_path.quadTo(3, 26, 3, 24)
    back_path.closeSubpath()
    
    back_grad = QLinearGradient(0, 5, 0, 26)
    back_grad.setColorAt(0.0, QColor('#64748B'))
    back_grad.setColorAt(0.5, QColor('#475569'))
    back_grad.setColorAt(1.0, QColor('#334155'))
    p.setBrush(QBrush(back_grad))
    p.setPen(Qt.NoPen)
    p.drawPath(back_path)
    
    # Inner Document
    doc_path = QPainterPath()
    doc_path.moveTo(7, 7.5)
    doc_path.lineTo(25, 7.5)
    doc_path.lineTo(25, 18)
    doc_path.lineTo(7, 18)
    doc_path.closeSubpath()
    p.setBrush(QBrush(QColor('#F8FAFC')))
    p.drawPath(doc_path)
    
    p.setPen(QPen(QColor('#94A3B8'), 1.0, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(10, 10.5), QPointF(22, 10.5))
    p.drawLine(QPointF(10, 13.5), QPointF(18, 13.5))
    
    # Front Flap
    front_path = QPainterPath()
    front_path.moveTo(2.6, 12)
    front_path.lineTo(29.4, 12)
    front_path.quadTo(30.4, 12, 30.1, 13.4)
    front_path.lineTo(28.2, 25.4)
    front_path.quadTo(27.8, 26.8, 26.0, 26.8)
    front_path.lineTo(4.0, 26.8)
    front_path.quadTo(2.2, 26.8, 1.8, 25.4)
    front_path.lineTo(1.9, 13.4)
    front_path.quadTo(1.6, 12, 2.6, 12)
    front_path.closeSubpath()
    
    front_grad = QLinearGradient(0, 12, 0, 27)
    front_grad.setColorAt(0.0, QColor('#94A3B8'))
    front_grad.setColorAt(0.3, QColor('#64748B'))
    front_grad.setColorAt(0.8, QColor('#475569'))
    front_grad.setColorAt(1.0, QColor('#334155'))
    p.setBrush(QBrush(front_grad))
    p.drawPath(front_path)
    
    p.setPen(QPen(QColor(255, 255, 255, 170), 1.2, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(3.6, 12.6), QPointF(28.4, 12.6))
    
    p.end()
    pix.setDevicePixelRatio(dpr)
    return pix


def active_3d_glyph(size=30, dpr=None):
    """Draws a 3D active timetable calendar glyph with emerald/blue depth."""
    if dpr is None:
        dpr = _screen_dpr()
    dpr = max(1.0, float(dpr))
    actual_sz = int(round(size * dpr))
    pix = QPixmap(actual_sz, actual_sz)
    pix.fill(Qt.transparent)
    
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    
    scale = actual_sz / 32.0
    p.scale(scale, scale)
    
    card_path = QPainterPath()
    card_path.addRoundedRect(QRectF(3, 3, 26, 26), 5, 5)
    card_grad = QLinearGradient(0, 3, 0, 29)
    card_grad.setColorAt(0.0, QColor('#3B82F6'))
    card_grad.setColorAt(0.5, QColor('#2563EB'))
    card_grad.setColorAt(1.0, QColor('#1D4ED8'))
    p.setBrush(QBrush(card_grad))
    p.setPen(Qt.NoPen)
    p.drawPath(card_path)
    
    # Grid lines inside
    p.setPen(QPen(QColor(255, 255, 255, 120), 1.2, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(3, 10), QPointF(29, 10))
    p.drawLine(QPointF(11.5, 10), QPointF(11.5, 29))
    p.drawLine(QPointF(20.5, 10), QPointF(20.5, 29))
    
    # White checkmark
    p.setPen(QPen(QColor('#FFFFFF'), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p_chk = QPainterPath()
    p_chk.moveTo(11, 6.5)
    p_chk.lineTo(14, 9)
    p_chk.lineTo(21, 4.5)
    p.drawPath(p_chk)
    
    p.end()
    pix.setDevicePixelRatio(dpr)
    return pix


def grid_glyph(colour=INK_SOFT, size=18):
    """A timetable, which is what a version actually is."""
    pix, p = _canvas(size)
    s = size / 18.0
    _stroke(p, colour, 1.35 * s)
    p.drawRoundedRect(QRectF(2.4 * s, 2.4 * s, 13.2 * s, 13.2 * s), 2.2 * s, 2.2 * s)
    p.drawLine(QPointF(2.4 * s, 6.8 * s), QPointF(15.6 * s, 6.8 * s))
    p.drawLine(QPointF(7.0 * s, 6.8 * s), QPointF(7.0 * s, 15.6 * s))
    p.drawLine(QPointF(11.4 * s, 6.8 * s), QPointF(11.4 * s, 15.6 * s))
    p.end()
    return pix


def institution_glyph(colour=None, size=20):
    """A flat mark, not an isometric 3-D building. The old icon lit a
    little rendered schoolhouse from the top-left with four tones of the
    accent colour; at 20px that is mush, and next to flat type it reads
    as clip art borrowed from somewhere else."""
    pix, p = _canvas(size)
    s = size / 20.0
    c = QColor(colour or BRAND)
    p.setPen(Qt.NoPen)
    p.setBrush(c)
    p.drawRoundedRect(QRectF(2.5 * s, 7.5 * s, 15 * s, 10 * s), 1.6 * s, 1.6 * s)
    roof = QPainterPath()
    roof.moveTo(10 * s, 2.2 * s)
    roof.lineTo(18.4 * s, 7.0 * s)
    roof.lineTo(1.6 * s, 7.0 * s)
    roof.closeSubpath()
    p.drawPath(roof)
    p.setBrush(QColor(255, 255, 255, 235))
    p.drawRoundedRect(QRectF(8.6 * s, 11.4 * s, 2.8 * s, 6.1 * s), 0.7 * s, 0.7 * s)
    p.drawRoundedRect(QRectF(4.6 * s, 10.4 * s, 2.4 * s, 2.4 * s), 0.6 * s, 0.6 * s)
    p.drawRoundedRect(QRectF(13.0 * s, 10.4 * s, 2.4 * s, 2.4 * s), 0.6 * s, 0.6 * s)
    p.end()
    return pix


def _school_mark(p, size, colour, weight=1.0):
    """A school drawn as flat geometry: pitched roof, body, doorway, two
    windows, a mast. No isometric projection and no fake sun — the shape
    reads at 18px, which the lit 3-D version did not."""
    s = size / 40.0
    c = QColor(colour)
    p.setPen(Qt.NoPen)
    p.setBrush(c)

    roof = QPainterPath()
    roof.moveTo(20 * s, 8.4 * s)
    roof.lineTo(32.6 * s, 17.4 * s)
    roof.lineTo(7.4 * s, 17.4 * s)
    roof.closeSubpath()
    p.drawPath(roof)

    p.drawRoundedRect(QRectF(10.2 * s, 17.4 * s, 19.6 * s, 14.4 * s), 1.8 * s, 1.8 * s)

    # mast: the one asymmetric detail, so the mark has a direction
    p.drawRoundedRect(QRectF(19.2 * s, 3.2 * s, 1.6 * s, 5.6 * s), 0.8 * s, 0.8 * s)

    # cut-outs
    p.setBrush(QColor(0, 0, 0, 0))
    p.setCompositionMode(QPainter.CompositionMode_Clear)
    p.drawRoundedRect(QRectF(17.6 * s, 23.4 * s, 4.8 * s, 8.4 * s), 1.2 * s, 1.2 * s)
    p.drawRoundedRect(QRectF(12.6 * s, 20.4 * s, 3.6 * s, 3.6 * s), 0.9 * s, 0.9 * s)
    p.drawRoundedRect(QRectF(23.8 * s, 20.4 * s, 3.6 * s, 3.6 * s), 0.9 * s, 0.9 * s)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)


_ICON_CACHE = {}


def _screen_dpr():
    try:
        from PySide6.QtGui import QGuiApplication

        app = QGuiApplication.instance()
        if app is not None:
            scr = app.primaryScreen()
            if scr is not None:
                return float(scr.devicePixelRatio())
    except Exception:
        pass
    return 1.0


def institution_3d(name="", colour=None, size=44, dpr=None):
    """An institution's mark: an isometric building on a base slab.

    Built to the shape of a real office/school block: a tall volume on a
    plinth that overhangs its footprint, banded storeys of glazing on both
    visible faces, a taller glazed ground floor, and a roof with a
    recessed deck inside its parapet.

    Three things this drawing has to get right, each of which it got wrong
    once:

    Resolution. The pixmap used to be rasterised at exactly the logical
    size and handed to a label, so on any hi-DPI screen — every Mac, every
    Windows machine above 100% scaling — the compositor scaled a 36px
    bitmap up and the mark looked soft and cheap. It is now drawn at
    3x supersampling on top of the screen's own device pixel ratio and
    resolved down with a smooth filter, then tagged with that ratio so Qt
    lays it out at the right size. Thin isometric seams need the
    supersampling as much as the DPI: a 1px diagonal rasterised directly
    is a staircase.

    Contour. Every face was a flat fill with no edge, so the white variant
    used on the navy hero collapsed into one white blob — nothing
    separated roof from wall from glass. Each face now carries a hairline
    in a dark slate at low alpha, which reads as a soft contour on pale
    surfaces and as a seam on saturated ones.

    Achromatic colours. Tones were derived by scaling saturation, so at
    saturation zero — pure white — glass, wall and roof all resolved to
    the same white. A white building now runs on its own value ladder
    instead, and keeps its glazing.

    Earlier attempts, so they are not repeated: four tones lit from the
    top-left with a rooftop flag (mush at 36px); a flat tile with a white
    cut-out (lost the depth the rest of the program is drawn with); a
    steep-roofed cottage (read as a house, not an institution).
    """
    if dpr is None:
        dpr = _screen_dpr()
    dpr = max(1.0, float(dpr))

    c = QColor(colour) if colour else QColor(BRAND)
    if not c.isValid():
        c = QColor(BRAND)

    key = (c.name(), int(size), round(dpr, 2))
    hit = _ICON_CACHE.get(key)
    if hit is not None:
        return hit

    h = c.hue() if c.hue() >= 0 else 220
    sat, val = c.saturation(), c.value()
    achromatic = sat < 40

    def tone(sat_mul, value, grey):
        if achromatic:
            return QColor.fromHsv(0, 0, max(0, min(255, int(grey))))
        return QColor.fromHsv(h, max(0, min(255, int(sat * sat_mul))),
                              max(0, min(255, int(value))))

    slab_top = tone(0.05, 247, 250)
    slab_side = tone(0.10, 224, 227)
    wall_lit = tone(0.07, 253, 255)
    wall_shade = tone(0.13, 219, 226)
    roof_rim = tone(0.06, 255, 255)
    roof_deck = tone(0.16, 233, 238)
    glass_lit = tone(0.72, val * 1.06, 196)
    glass_shade = tone(0.84, val * 0.80, 168)
    entrance = tone(0.88, val * 0.62, 146)

    SS = 3
    px = max(8, int(round(size * dpr * SS)))
    pix = QPixmap(px, px)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    u = px / 44.0

    edge = QColor(18, 26, 43, 58)
    edge_pen = QPen(edge, max(0.75, u * 0.42))
    edge_pen.setJoinStyle(Qt.MiterJoin)

    def poly(pts, brush, outline=True):
        path = QPainterPath()
        path.moveTo(pts[0][0] * u, pts[0][1] * u)
        for x, y in pts[1:]:
            path.lineTo(x * u, y * u)
        path.closeSubpath()
        p.setBrush(brush)
        p.setPen(edge_pen if outline else Qt.NoPen)
        p.drawPath(path)

    # ── Base slab ──────────────────────────────────────────────────────
    SW, SH, SCY, TH = 16.6, 7.2, 33.4, 2.3
    L = (22 - SW, SCY); B = (22, SCY - SH); R = (22 + SW, SCY); F = (22, SCY + SH)
    poly([L, F, (F[0], F[1] + TH), (L[0], L[1] + TH)], slab_side)
    poly([F, R, (R[0], R[1] + TH), (F[0], F[1] + TH)], slab_side)
    poly([L, B, R, F], slab_top)

    # ── Massing ────────────────────────────────────────────────────────
    BW, BD, BCY, HGT = 11.3, 5.0, 31.4, 18.2
    bl = (22 - BW, BCY); bb = (22, BCY - BD)
    br = (22 + BW, BCY); bf = (22, BCY + BD)
    tl = (bl[0], bl[1] - HGT); tb = (bb[0], bb[1] - HGT)
    tr = (br[0], br[1] - HGT); tf = (bf[0], bf[1] - HGT)

    poly([bl, bf, tf, tl], wall_lit)
    poly([bf, br, tr, tf], wall_shade)

    def left_pt(uu, vv):
        return (tl[0] + uu * BW, tl[1] + uu * BD + vv)

    def right_pt(uu, vv):
        return (tf[0] + uu * BW, tf[1] - uu * BD + vv)

    def band(mapper, v0, v1, brush, u0=0.11, u1=0.89):
        poly([mapper(u0, v0), mapper(u1, v0), mapper(u1, v1), mapper(u0, v1)],
             brush, outline=False)

    # ── Glazing ────────────────────────────────────────────────────────
    FLOORS, TOP_PAD, PITCH, GLASS_H = 4, 2.5, 3.0, 2.1
    for i in range(FLOORS):
        v0 = TOP_PAD + i * PITCH
        band(left_pt, v0, v0 + GLASS_H, glass_lit)
        band(right_pt, v0, v0 + GLASS_H, glass_shade)

    ground = TOP_PAD + FLOORS * PITCH + 0.7
    band(left_pt, ground, ground + 3.2, entrance, 0.15, 0.85)
    band(right_pt, ground, ground + 3.2, glass_shade, 0.15, 0.85)

    # ── Roof ───────────────────────────────────────────────────────────
    poly([tl, tb, tr, tf], roof_rim)
    k = 0.72
    poly([
        (22 + (tl[0] - 22) * k, tb[1] + (tl[1] - tb[1]) * k),
        (22, tb[1] + 0.9),
        (22 + (tr[0] - 22) * k, tb[1] + (tr[1] - tb[1]) * k),
        (22, tf[1] - 0.9),
    ], roof_deck)

    p.end()

    out = QPixmap.fromImage(
        pix.toImage().scaled(int(round(size * dpr)), int(round(size * dpr)),
                             Qt.KeepAspectRatio, Qt.SmoothTransformation))
    out.setDevicePixelRatio(dpr)
    _ICON_CACHE[key] = out
    return out


def institution_tile(name="", colour=None, size=40, radius=None):
    """An institution's mark: a tile in the school's own colour with a flat
    white school cut out of it.

    Two earlier attempts are worth naming so they are not tried again. An
    isometric building lit from the top-left in four tones was clip art at
    the sizes it is used, and — worse — it was the same drawing for every
    school. Initials on a tinted square distinguished them but looked like
    a contact list, not a product. This keeps the colour as the thing that
    tells schools apart and gives the mark a real silhouette.
    """
    c = QColor(colour) if colour else QColor(BRAND)
    if not c.isValid():
        c = QColor(BRAND)

    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    top = QColor.fromHsv(c.hue() if c.hue() >= 0 else 220,
                         c.saturation(), min(255, int(c.value() * 1.16)))
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0.0, top)
    grad.setColorAt(1.0, c)
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    r = radius if radius is not None else size * 0.28
    p.drawRoundedRect(QRectF(0, 0, size, size), r, r)

    _school_mark(p, size, "#FFFFFF")
    p.end()
    return pix


def glass_tile(size=44, radius=None, mark_alpha=235):
    """The same mark for a dark ground: a translucent white tile with the
    school cut out of it. Tinting the coloured tile light enough to read on
    navy destroyed the very shading it is drawn for."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(255, 255, 255, 46), 1.2))
    p.setBrush(QColor(255, 255, 255, 30))
    r = radius if radius is not None else size * 0.28
    p.drawRoundedRect(QRectF(0.6, 0.6, size - 1.2, size - 1.2), r, r)
    _school_mark(p, size, QColor(255, 255, 255, mark_alpha))
    p.end()
    return pix


def monogram(text, colour=None, size=36, radius=None):
    """An institution's mark: its initials on a tinted tile.

    This replaced a filled building silhouette. The silhouette was the
    same shape for every institution — so it identified nothing — and as
    a solid mass at 36px it was the heaviest object in a sidebar built
    otherwise from hairlines and light type. Initials distinguish one
    school from the next, sit at the weight of the text around them, and
    survive being scaled down.
    """
    c = QColor(colour) if colour else QColor(BRAND)
    if not c.isValid():
        c = QColor(BRAND)

    words = [w for w in str(text or "").replace("-", " ").split() if w]
    initials = "".join(w[0] for w in words[:2]).upper() or "?"

    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    tint = QColor(c)
    tint.setAlpha(30)
    p.setBrush(tint)
    r = radius if radius is not None else size * 0.28
    p.drawRoundedRect(QRectF(0, 0, size, size), r, r)

    f = font(size * 0.32, QFont.DemiBold, spacing=0.3)
    p.setFont(f)
    p.setPen(c)
    p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, initials)
    p.end()
    return pix


_SHIELD_CACHE = {}


def shield_silhouette(height, colour="#FFFFFF", alpha=40, dpr=None):
    """The institution's shield, flattened to a single-colour silhouette.

    Used large and very faint as a watermark. It is deliberately NOT the
    full-colour mark: a photographic-looking logo dropped behind live type
    at 8% opacity still carries its red flame and its white keyline, which
    read as artefacts rather than as texture. Taking only the artwork's
    alpha and filling it with one tone gives a shape that behaves like a
    watermark instead of like a picture someone forgot to delete.
    """
    if dpr is None:
        dpr = _screen_dpr()
    dpr = max(1.0, float(dpr))
    key = (int(height), str(colour), int(alpha), round(dpr, 2))
    hit = _SHIELD_CACHE.get(key)
    if hit is not None:
        return hit

    path = getattr(bk_branding, "SHIELD_PNG", None)
    if not path or not os.path.exists(path):
        return QPixmap()

    src = QImage(path)
    if src.isNull():
        return QPixmap()

    px_h = max(8, int(round(height * dpr)))
    src = src.scaledToHeight(px_h, Qt.SmoothTransformation)
    src = src.convertToFormat(QImage.Format_ARGB32)

    tinted = QImage(src.size(), QImage.Format_ARGB32)
    c = QColor(colour)
    c.setAlpha(255)
    tinted.fill(c)
    # Keep only where the artwork had ink: the mask is its own alpha.
    p = QPainter(tinted)
    p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    p.drawImage(0, 0, src)
    p.end()

    out_img = QImage(src.size(), QImage.Format_ARGB32)
    out_img.fill(Qt.transparent)
    p2 = QPainter(out_img)
    p2.setOpacity(max(0.0, min(1.0, alpha / 255.0)))
    p2.drawImage(0, 0, tinted)
    p2.end()

    out = QPixmap.fromImage(out_img)
    out.setDevicePixelRatio(dpr)
    _SHIELD_CACHE[key] = out
    return out


# ── Texture ───────────────────────────────────────────────────────────
# Flat surfaces, separated by hairlines and layering — not by gradients.
# Apple's own guidance puts it plainly: depth comes from materials and
# layers, and the transition between a control area and content is an
# edge, not a fade. Every gradient in this program has been replaced by
# one of two things: a flat tint, or this texture.
#
# The texture is the week grid the program exists to produce. It is drawn
# once, here, so the banner, the sidebar and the empty floor below the
# list all carry the same weave at the same weight instead of three
# hand-tuned imitations of each other.

GRID_COL_W = 58.0
GRID_ROW_H = 27.0

# Hand-placed, so the composition is identical in every screenshot and no
# two blocks ever land in a way that reads as noise.
GRID_BLOCKS = ((0, 0, 2), (2, 0, 1), (4, 1, 2), (1, 1, 1), (3, 2, 1),
               (5, 0, 1), (6, 2, 2), (5, 3, 1))


def paint_grid_texture(p, rect, colour, line_alpha=22, block_alpha=28,
                       columns=7, anchor="right", blocks=True):
    """The week grid, as texture on a flat surface.

    `anchor` picks which edge the grid hangs from — "right" for the
    banner, "bottom" for the floor under the list. Nothing here fades:
    the weave is one weight all the way across, and it is the surface
    beneath it that decides how present it looks.
    """
    c = QColor(colour)
    if not c.isValid():
        c = QColor(BRAND)

    def ink(alpha):
        out = QColor(c)
        out.setAlpha(alpha)
        return out

    if anchor == "bottom":
        left = rect.right() - GRID_COL_W * columns + 26
        top = rect.bottom() - GRID_ROW_H * (int(rect.height() / GRID_ROW_H) + 1)
    else:
        left = rect.right() + 26 - GRID_COL_W * columns
        top = rect.top() - 12

    if blocks:
        p.setPen(Qt.NoPen)
        p.setBrush(ink(block_alpha))
        for col, row, span in GRID_BLOCKS:
            if col >= columns:
                continue
            p.drawRoundedRect(
                QRectF(left + col * GRID_COL_W + 3, top + row * GRID_ROW_H + 3,
                       GRID_COL_W - 6, GRID_ROW_H * span - 6), 4, 4)

    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(ink(line_alpha), 1))
    for i in range(columns + 1):
        x = left + i * GRID_COL_W
        p.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
    j = 0
    while top + j * GRID_ROW_H <= rect.bottom():
        y = top + j * GRID_ROW_H
        if y >= rect.top():
            p.drawLine(QPointF(left, y), QPointF(left + GRID_COL_W * columns, y))
        j += 1


def flat_tint(colour, strength=0.14):
    """A flat wash of an accent over the canvas — one colour, no ramp.

    Mixed against the canvas rather than drawn with alpha so the result is
    an opaque value that can be handed to a stylesheet as well as to a
    painter, and so two surfaces asking for the same tint get the same
    pixel regardless of what is behind them.
    """
    c = QColor(colour)
    if not c.isValid():
        c = QColor(BRAND)
    base = QColor(CANVAS)
    t = max(0.0, min(1.0, strength))
    return QColor(int(base.red() * (1 - t) + c.red() * t),
                  int(base.green() * (1 - t) + c.green() * t),
                  int(base.blue() * (1 - t) + c.blue() * t))


def pencil_glyph(colour=INK_SOFT, size=16, dpr=None):
    """Rename. Drawn, not stubbed.

    This and the two below returned an empty transparent pixmap — a
    function that satisfies every call site and puts nothing on screen.
    That is why the profile menu's "Şifre Sıfırla" row had no icon while
    its neighbours did, and why the menu's left edge looked ragged: half
    the rows were reserving space for a glyph that never arrived.
    """
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    p.drawLine(QPointF(3.0 * s, 13.0 * s), QPointF(3.0 * s, 10.4 * s))
    p.drawLine(QPointF(3.0 * s, 13.0 * s), QPointF(5.6 * s, 13.0 * s))
    p.drawLine(QPointF(3.0 * s, 10.4 * s), QPointF(10.6 * s, 2.8 * s))
    p.drawLine(QPointF(5.6 * s, 13.0 * s), QPointF(13.2 * s, 5.4 * s))
    p.drawLine(QPointF(10.6 * s, 2.8 * s), QPointF(13.2 * s, 5.4 * s))
    p.drawLine(QPointF(9.2 * s, 4.2 * s), QPointF(11.8 * s, 6.8 * s))
    p.end()
    return pix


def key_glyph(colour=INK_SOFT, size=16, dpr=None):
    """Password / institution key."""
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    p.drawEllipse(QRectF(2.2 * s, 5.4 * s, 6.4 * s, 6.4 * s))
    p.drawLine(QPointF(8.2 * s, 8.6 * s), QPointF(14.0 * s, 8.6 * s))
    p.drawLine(QPointF(11.6 * s, 8.6 * s), QPointF(11.6 * s, 11.2 * s))
    p.drawLine(QPointF(13.6 * s, 8.6 * s), QPointF(13.6 * s, 10.6 * s))
    p.end()
    return pix


def trash_glyph(colour=DANGER, size=16, dpr=None):
    """Delete. Defaults to the danger colour, because it is the one action
    in any of these menus that cannot be undone."""
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    p.drawLine(QPointF(2.6 * s, 4.4 * s), QPointF(13.4 * s, 4.4 * s))
    p.drawLine(QPointF(6.2 * s, 4.4 * s), QPointF(6.2 * s, 2.6 * s))
    p.drawLine(QPointF(6.2 * s, 2.6 * s), QPointF(9.8 * s, 2.6 * s))
    p.drawLine(QPointF(9.8 * s, 2.6 * s), QPointF(9.8 * s, 4.4 * s))
    path = QPainterPath()
    path.moveTo(4.0 * s, 4.4 * s)
    path.lineTo(4.8 * s, 13.4 * s)
    path.lineTo(11.2 * s, 13.4 * s)
    path.lineTo(12.0 * s, 4.4 * s)
    p.drawPath(path)
    p.drawLine(QPointF(6.8 * s, 6.6 * s), QPointF(7.0 * s, 11.4 * s))
    p.drawLine(QPointF(9.2 * s, 6.6 * s), QPointF(9.0 * s, 11.4 * s))
    p.end()
    return pix


def palette_glyph(colour=INK_SOFT, size=16, dpr=None):
    """Change colour."""
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    p.drawEllipse(QRectF(2.4 * s, 2.4 * s, 11.2 * s, 11.2 * s))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(colour))
    for cx, cy in ((5.6, 5.6), (10.0, 5.2), (11.2, 9.2)):
        p.drawEllipse(QPointF(cx * s, cy * s), 1.0 * s, 1.0 * s)
    p.end()
    return pix


def person_glyph(colour=INK_SOFT, size=16, dpr=None):
    """Profile."""
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    p.drawEllipse(QRectF(5.0 * s, 2.6 * s, 6.0 * s, 6.0 * s))
    path = QPainterPath()
    path.moveTo(3.0 * s, 13.8 * s)
    path.quadTo(3.0 * s, 10.4 * s, 8.0 * s, 10.4 * s)
    path.quadTo(13.0 * s, 10.4 * s, 13.0 * s, 13.8 * s)
    p.drawPath(path)
    p.end()
    return pix


def eye_glyph(colour=INK_SOFT, size=16, dpr=None):
    """Show password eye icon."""
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.4 * s)
    path = QPainterPath()
    cx, cy = 8.0 * s, 8.0 * s
    path.moveTo(2.2 * s, cy)
    path.quadTo(cx, cy - 4.4 * s, 13.8 * s, cy)
    path.quadTo(cx, cy + 4.4 * s, 2.2 * s, cy)
    p.drawPath(path)
    p.setBrush(QColor(colour))
    p.drawEllipse(QPointF(cx, cy), 1.8 * s, 1.8 * s)
    p.end()
    return pix


def eye_slash_glyph(colour=INK_SOFT, size=16, dpr=None):
    """Hide password eye slash icon."""
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.4 * s)
    path = QPainterPath()
    cx, cy = 8.0 * s, 8.0 * s
    path.moveTo(2.2 * s, cy)
    path.quadTo(cx, cy - 4.4 * s, 13.8 * s, cy)
    path.quadTo(cx, cy + 4.4 * s, 2.2 * s, cy)
    p.drawPath(path)
    p.setBrush(QColor(colour))
    p.drawEllipse(QPointF(cx, cy), 1.8 * s, 1.8 * s)
    p.drawLine(QPointF(3.0 * s, 3.0 * s), QPointF(13.0 * s, 13.0 * s))
    p.end()
    return pix


def logout_glyph(colour=INK_SOFT, size=16, dpr=None):
    """Sign out."""
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    path = QPainterPath()
    path.moveTo(9.2 * s, 3.0 * s)
    path.lineTo(3.4 * s, 3.0 * s)
    path.lineTo(3.4 * s, 13.0 * s)
    path.lineTo(9.2 * s, 13.0 * s)
    p.drawPath(path)
    p.drawLine(QPointF(7.0 * s, 8.0 * s), QPointF(13.4 * s, 8.0 * s))
    path2 = QPainterPath()
    path2.moveTo(11.0 * s, 5.6 * s)
    path2.lineTo(13.4 * s, 8.0 * s)
    path2.lineTo(11.0 * s, 10.4 * s)
    p.drawPath(path2)
    p.end()
    return pix


def cloud_glyph(colour=INK_SOFT, size=16, dpr=None):
    """Cloud sync."""
    pix, p = _canvas(size, dpr)
    s = size / 16.0
    _stroke(p, colour, 1.5 * s)
    path = QPainterPath()
    path.moveTo(4.6 * s, 11.4 * s)
    path.quadTo(1.8 * s, 11.2 * s, 2.4 * s, 8.6 * s)
    path.quadTo(2.9 * s, 6.6 * s, 5.2 * s, 6.9 * s)
    path.quadTo(5.9 * s, 3.6 * s, 9.2 * s, 4.0 * s)
    path.quadTo(11.9 * s, 4.4 * s, 12.0 * s, 7.2 * s)
    path.quadTo(14.4 * s, 7.6 * s, 13.9 * s, 9.9 * s)
    path.quadTo(13.5 * s, 11.5 * s, 11.4 * s, 11.4 * s)
    p.drawPath(path)
    p.end()
    return pix


# ── Containers ────────────────────────────────────────────────────────
class Card(QFrame):
    """A hairline and a radius. No shadow: a card sitting on the canvas is
    not floating above it, and giving everything a shadow leaves nothing
    able to look raised when something genuinely is."""

    def __init__(self, parent=None, radius=R_CARD, padding=(20, 18, 20, 18)):
        super().__init__(parent)
        self.setObjectName("bkCard")
        self.setStyleSheet(f"""
            QFrame#bkCard {{
                background: {SURFACE};
                border: 1px solid {HAIRLINE};
                border-radius: {radius}px;
            }}
        """)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(*padding)
        self.layout_.setSpacing(0)


class Chip(QLabel):
    """A small, quiet status. Tinted background, no border, never shouting
    — the text is the message, the colour is only the category."""

    def __init__(self, text, tone="neutral", parent=None):
        super().__init__(text, parent)
        fg, bg = {
            "brand": (BRAND, BRAND_TINT),
            "ok": (OK, OK_TINT),
            "warn": (WARN, WARN_TINT),
            "danger": (DANGER, DANGER_TINT),
        }.get(tone, (INK_SOFT, SURFACE_SUNK))
        self.setFont(font(8.6, QFont.DemiBold, spacing=0.3))
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(21)
        self.setStyleSheet(f"""
            QLabel {{
                color: {fg}; background: {bg};
                border: none; border-radius: 6px; padding: 0px 9px;
            }}
        """)


class EmptyState(QWidget):
    """What a screen says when it has nothing to show. It names the thing
    that is missing and offers the one action that fixes it — an empty
    panel with no words is the most common way a program looks broken
    when it is merely new."""

    def __init__(self, title, message, action=None, glyph=None, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addStretch(1)

        if glyph is not None:
            mark = QLabel()
            mark.setPixmap(glyph)
            mark.setAlignment(Qt.AlignCenter)
            mark.setStyleSheet("background: transparent;")
            lay.addWidget(mark)
            lay.addSpacing(18)

        h = heading(title, 14)
        h.setAlignment(Qt.AlignCenter)
        lay.addWidget(h)

        lay.addSpacing(7)
        m = subheading(message)
        m.setAlignment(Qt.AlignCenter)
        m.setMaximumWidth(420)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(m)
        row.addStretch(1)
        lay.addLayout(row)

        if action is not None:
            lay.addSpacing(22)
            arow = QHBoxLayout()
            arow.addStretch(1)
            arow.addWidget(action)
            arow.addStretch(1)
            lay.addLayout(arow)

        lay.addStretch(1)


_SHADOW_CACHE = {}

def get_smooth_shadow(w: int, h: int, radius: float, blur: int = 16, offset_y: int = 4, alpha: int = 40) -> tuple:
    key = (w, h, int(radius), blur, offset_y, alpha)
    if key in _SHADOW_CACHE:
        return _SHADOW_CACHE[key]
        
    pad = blur * 2
    pw = w + pad * 2
    ph = h + pad * 2
    
    scale = 2
    img = QImage(pw * scale, ph * scale, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(scale, scale)
    
    # Draw soft dark core rounded rect
    rect = QRectF(pad, pad + offset_y, w, h)
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    p.fillPath(path, QColor(15, 23, 42, alpha))
    p.end()
    
    # Multi-step smooth downscale & upscale provides pristine Gaussian blur
    down = img.scaled(pw // 2, ph // 2, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    down2 = down.scaled(pw // 4, ph // 4, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    up = down2.scaled(pw * scale, ph * scale, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    
    pm = QPixmap.fromImage(up)
    pm.setDevicePixelRatio(scale)
    _SHADOW_CACHE[key] = (pm, pad)
    return _SHADOW_CACHE[key]


def paint_sheet_shadow(painter, rect, radius=R_SHEET, layers=None, offset=0):
    """Clean no-op: eliminates all fake wireframe shadow loops and ghost outlines."""
    pass


def elide(text, widget, width):
    return QFontMetrics(widget.font()).elidedText(text, Qt.ElideRight, width)


# ── Hero Sheet Dialog Base ───────────────────────────────────────────
class HeroSheetDialog(QDialog):
    """The one modal sheet every dialog in the program is built on.

    A sheet is: a frameless card, a title that names the task, a body,
    and a footer where the confirming action sits on the right.
    """

    def __init__(self, parent=None, width=480, height=520, title="", subtitle=""):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(width, height)
        self._radius = R_SHEET

        self._outer_lay = QVBoxLayout(self)
        self._outer_lay.setContentsMargins(0, 0, 0, 0)
        self._outer_lay.setSpacing(0)

        self.card = QFrame(self)
        self.card.setObjectName("heroSheetCard")
        self.card.setStyleSheet(f"""
            QFrame#heroSheetCard {{
                background: {SURFACE};
                border: 1px solid {HAIRLINE};
                border-radius: {R_SHEET}px;
            }}
        """)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(28, 24, 28, 22)
        self.card_layout.setSpacing(14)
        self._outer_lay.addWidget(self.card)

        if title:
            self.set_title(title, subtitle)

    # -- structure -----------------------------------------------------
    def set_title(self, title, subtitle=""):
        """Names the task. A sheet whose title is missing is a sheet the
        user has to reverse-engineer from its buttons."""
        head = QLabel(title)
        head.setFont(title_font(16))
        head.setStyleSheet(f"color: {INK}; background: transparent;")
        self.card_layout.addWidget(head)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setFont(font(9.8))
            sub.setWordWrap(True)
            sub.setStyleSheet(f"color: {INK_SOFT}; background: transparent;")
            self.card_layout.addWidget(sub)
        self.card_layout.addSpacing(6)

    def add_footer(self, confirm_text="Kaydet", cancel_text="Vazgeç",
                   on_confirm=None, danger=False):
        """The way out and the way on, in the order every desktop uses:
        the dismissing action on the left, the confirming one on the
        right, and the confirming one the only filled control."""
        self.card_layout.addStretch(1)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addStretch(1)

        self.btn_cancel = secondary_button(cancel_text, height=H_CONTROL)
        self.btn_cancel.clicked.connect(self.reject)
        row.addWidget(self.btn_cancel)

        make = danger_button if danger else primary_button
        self.btn_confirm = make(confirm_text, height=H_CONTROL)
        self.btn_confirm.clicked.connect(on_confirm or self.accept)
        row.addWidget(self.btn_confirm)

        self.card_layout.addLayout(row)
        return row

    def paintEvent(self, _event):
        pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)



# These two used to redefine folder_3d_glyph here, at the bottom of the
# file, shadowing the real drawing 800 lines above — and calling
# folder_glyph, which calls folder_3d_glyph, which is now this stub. That
# mutual call is the TypeError the dashboard died on. The archive icon
# keeps a thin alias; the folder keeps its real implementation.
def archive_3d_glyph(size=30):
    return folder_3d_glyph(size=size)

def active_3d_glyph(size=30):
    return check_glyph(size=size)

def star_glyph(colour=INK_SOFT, size=16):
    return check_glyph(colour=colour, size=size)

# ── Motion ────────────────────────────────────────────────────────────
# One place decides how long things take and how they ease, so a sheet
# opening in one corner of the program feels like a sheet opening in
# another. The numbers are short on purpose: an interface animation is
# there to explain where a thing came from, and anything past a quarter
# of a second stops explaining and starts costing.
DUR_FAST = 110      # hover, small state flips
DUR_BASE = 170      # sheets, overlays, morphs
DUR_SLOW = 260      # something crossing the whole window

EASE_OUT = QEasingCurve.OutCubic       # arriving
EASE_IN = QEasingCurve.InCubic         # leaving
EASE_SPRING = QEasingCurve.OutBack     # arriving with a little overshoot


def blur_pixmap(source, radius=18, tint=None, tint_alpha=120):
    """Ultra-fast frosted backdrop generation: downsamples by 4x for instantaneous GPU/CPU blurring."""
    if source is None or source.isNull():
        return QPixmap()

    dpr = source.devicePixelRatio() or 1.0
    w = max(32, int(source.width() / 4))
    h = max(32, int(source.height() / 4))
    small = source.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    flat = QPixmap(small)
    flat.setDevicePixelRatio(1.0)

    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(flat)
    fx = QGraphicsBlurEffect()
    fx.setBlurRadius(radius / 2.0)
    fx.setBlurHints(QGraphicsBlurEffect.PerformanceHint)
    item.setGraphicsEffect(fx)
    scene.addItem(item)

    out = QImage(flat.size(), QImage.Format_ARGB32_Premultiplied)
    out.fill(Qt.transparent)
    p = QPainter(out)
    target = QRectF(0, 0, flat.width(), flat.height())
    scene.render(p, target, QRectF(0, 0, flat.width(), flat.height()))
    if tint is not None:
        c = QColor(tint)
        c.setAlpha(tint_alpha)
        p.fillRect(out.rect(), c)
    p.end()

    result = QPixmap.fromImage(out).scaled(source.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    result.setDevicePixelRatio(dpr)
    return result


class MorphOverlay(QWidget):
    """A panel that grows out of the control that summoned it.
    60 FPS hardware-accelerated animated overlay with instant search responsiveness.
    """

    closed = Signal()

    def __init__(self, host, radius=R_SHEET, dim=54, blur=18, parent=None):
        super().__init__(parent or host)
        self._host = host
        self._radius = radius
        self._dim = dim
        self._blur = blur
        self._fade = 0.0
        self._backdrop = QPixmap()
        self._sharp = QPixmap()
        self._cutout = QRect()
        self._anims = None
        self._opening = False
        self._closing = False
        self._last_host_size = None
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.hide()

        self.panel = QFrame(self)
        self.panel.setObjectName("morphPanel")
        self.panel.setStyleSheet(f"""
            QFrame#morphPanel {{
                background: {SURFACE};
                border: 1px solid {HAIRLINE};
                border-radius: {radius}px;
            }}
        """)
        panel_lay = QVBoxLayout(self.panel)
        panel_lay.setContentsMargins(0, 0, 0, 0)
        panel_lay.setSpacing(0)

        self.body = QWidget(self.panel)
        self.body.setStyleSheet("background: transparent;")
        panel_lay.addWidget(self.body)

        self._body_fx = QGraphicsOpacityEffect(self.body)
        self._body_fx.setOpacity(0.0)
        self.body.setGraphicsEffect(self._body_fx)

        self._panel_fx = QGraphicsOpacityEffect(self.panel)
        self._panel_fx.setOpacity(1.0)
        self.panel.setGraphicsEffect(self._panel_fx)

    def _get_fade(self):
        return self._fade

    def _set_fade(self, value):
        self._fade = float(value)
        self.update()

    fade = QtProperty(float, _get_fade, _set_fade)

    def open_from(self, anchor, target_rect):
        if getattr(self, "_closing", False):
            self._closing = False

        if self._anims is not None:
            try:
                self._anims.stop()
            except Exception:
                pass
            self._anims = None

        host = self._host
        self.setGeometry(host.rect())

        # Grab and blur host only if not already cached for current window size
        if self._backdrop.isNull() or self._last_host_size != host.size():
            self._sharp = host.grab()
            self._backdrop = blur_pixmap(self._sharp, self._blur)
            self._last_host_size = host.size()

        self._panel_fx.setOpacity(1.0)
        self._body_fx.setOpacity(0.0)

        if anchor is not None and anchor.isVisible():
            tl0 = anchor.mapTo(host, QPoint(0, 0))
            self._cutout = QRect(tl0.x(), tl0.y(), anchor.width(), anchor.height())
            start = QRect(tl0.x(), tl0.y(), anchor.width(), anchor.height())
        else:
            self._cutout = QRect()
            start = QRect(target_rect.center().x() - 40,
                          target_rect.center().y() - 20, 80, 40)

        self.panel.setGeometry(start)
        self.show()
        self.raise_()

        grow = QPropertyAnimation(self.panel, b"geometry", self)
        grow.setDuration(DUR_BASE)
        grow.setStartValue(start)
        grow.setEndValue(target_rect)
        grow.setEasingCurve(EASE_OUT)

        veil = QPropertyAnimation(self, b"fade", self)
        veil.setDuration(DUR_BASE)
        veil.setStartValue(0.0)
        veil.setEndValue(1.0)
        veil.setEasingCurve(EASE_OUT)

        ink = QPropertyAnimation(self._body_fx, b"opacity", self)
        ink.setDuration(DUR_BASE)
        ink.setStartValue(0.0)
        ink.setKeyValueAt(0.35, 0.0)
        ink.setEndValue(1.0)
        ink.setEasingCurve(EASE_OUT)

        group = QParallelAnimationGroup(self)
        for a in (grow, veil, ink):
            group.addAnimation(a)
        self._opening = True
        group.finished.connect(self._opened)
        group.start()
        self._anims = group

    def _opened(self):
        self._opening = False

    def resize_panel_to(self, rect, animated=True):
        if self._opening or not self.isVisible() or getattr(self, "_closing", False):
            return
        if not animated:
            self.panel.setGeometry(rect)
            return
        anim = QPropertyAnimation(self.panel, b"geometry", self)
        anim.setDuration(DUR_FAST)
        anim.setStartValue(self.panel.geometry())
        anim.setEndValue(rect)
        anim.setEasingCurve(EASE_OUT)
        anim.start()
        self._resize_anim = anim

    def refresh_backdrop(self):
        if not self.isVisible() or getattr(self, "_closing", False):
            return
        was_geo = self.panel.geometry()
        self.hide()
        self.setGeometry(self._host.rect())
        self._sharp = self._host.grab()
        self._backdrop = blur_pixmap(self._sharp, self._blur)
        self._last_host_size = self._host.size()
        anchor = getattr(self, "_anchor", None)
        if anchor is not None and anchor.isVisible():
            tl = anchor.mapTo(self._host, QPoint(0, 0))
            self._cutout = QRect(tl.x(), tl.y(), anchor.width(), anchor.height())
        self.show()
        self.raise_()
        self.panel.setGeometry(was_geo)

    def close_to(self, anchor):
        if not self.isVisible() or getattr(self, "_closing", False):
            return
        self._closing = True
        if self._anims is not None:
            try:
                self._anims.stop()
            except Exception:
                pass
            self._anims = None

        host = self._host
        if anchor is not None and anchor.isVisible():
            tl = anchor.mapTo(host, QPoint(0, 0))
            end = QRect(tl.x(), tl.y(), anchor.width(), anchor.height())
        else:
            g = self.panel.geometry()
            end = QRect(g.center().x() - 40, g.center().y() - 20, 80, 40)

        shrink = QPropertyAnimation(self.panel, b"geometry", self)
        shrink.setDuration(DUR_FAST)
        shrink.setStartValue(self.panel.geometry())
        shrink.setEndValue(end)
        shrink.setEasingCurve(EASE_OUT)

        veil = QPropertyAnimation(self, b"fade", self)
        veil.setDuration(DUR_FAST)
        veil.setStartValue(self._fade)
        veil.setEndValue(0.0)
        veil.setEasingCurve(EASE_OUT)

        ink = QPropertyAnimation(self._body_fx, b"opacity", self)
        ink.setDuration(int(DUR_FAST * 0.4))
        ink.setStartValue(self._body_fx.opacity())
        ink.setEndValue(0.0)

        panel_out = QPropertyAnimation(self._panel_fx, b"opacity", self)
        panel_out.setDuration(DUR_FAST)
        panel_out.setStartValue(self._panel_fx.opacity())
        panel_out.setEndValue(0.0)
        panel_out.setEasingCurve(EASE_OUT)

        group = QParallelAnimationGroup(self)
        for a in (shrink, veil, ink, panel_out):
            group.addAnimation(a)
        group.finished.connect(self._finish_close)
        group.start()
        self._anims = group

    def _finish_close(self):
        self._closing = False
        self._opening = False
        self.hide()
        self.closed.emit()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        fade_val = max(0.0, min(1.0, self._fade))
        if fade_val > 0.001:
            p.setOpacity(fade_val)
            dim_color = QColor(15, 20, 32, self._dim)

            if not self._cutout.isNull():
                # Hardware-accelerated OddEven fill with smooth 10px rounded rect cutout (zero sharp white corner artifacts)
                path = QPainterPath()
                path.setFillRule(Qt.OddEvenFill)
                path.addRect(QRectF(self.rect()))
                path.addRoundedRect(QRectF(self._cutout), 10.0, 10.0)
                p.fillPath(path, dim_color)

                # Crisp subtle outline around live anchor
                p.setPen(QPen(QColor(255, 255, 255, int(60 * fade_val)), 1.0))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(QRectF(self._cutout).adjusted(0.5, 0.5, -0.5, -0.5), 10.0, 10.0)
            else:
                p.fillRect(self.rect(), dim_color)

        # 2. Panel drop shadow (lightweight 2-pass shadow for rock-solid 60fps)
        if self._panel_fx.opacity() > 0.02 and self.panel.isVisible():
            p.setOpacity(self._panel_fx.opacity() * fade_val)
            paint_sheet_shadow(p, self.panel.geometry(), self._radius, layers=2, offset=5)

        p.end()

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        # Clicking the control that opened this must not dismiss it —
        # people click back into the search field to keep typing.
        if not self._cutout.isNull() and self._cutout.contains(pos):
            anchor = getattr(self, "_anchor", None)
            if anchor is not None:
                anchor.setFocus()
            return
        if not self.panel.geometry().contains(pos):
            self.request_close()
        else:
            super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.request_close()
            return
        super().keyPressEvent(event)

    def request_close(self):
        self.close_to(getattr(self, "_anchor", None))


# ── Hero Popover & Action Menus ───────────────────────────────────────
class HeroMenuItem(QFrame):
    """An Apple-style menu item with micro-icon, clean typography, hover pill, and danger states."""
    clicked = Signal()

    def __init__(self, label: str, icon_pixmap: QPixmap = None, is_danger: bool = False,
                 shortcut: str = "", checkable: bool = False, checked: bool = False, parent=None):
        super().__init__(parent)
        self.is_danger = is_danger
        self.checkable = checkable
        self._checked = checked
        self._hovered = False
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("heroMenuItem")
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet("background: transparent; border: none;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(10)

        # Both columns are ALWAYS laid out, even when empty.
        #
        # They used to be added only when there was something to put in
        # them, so an item with an icon started its text 26px further
        # right than an item without one, and a menu of five actions came
        # out with a ragged left edge — which is what "menüler bozuk"
        # was. A menu is a column of labels; the labels have to start on
        # the same line whether or not each one happens to have a glyph.
        if self.checkable:
            self.check_lbl = QLabel()
            self.check_lbl.setFixedSize(14, 14)
            self.check_lbl.setAlignment(Qt.AlignCenter)
            self.check_lbl.setStyleSheet("background: transparent; border: none;")
            if self._checked:
                self.check_lbl.setPixmap(check_glyph(BRAND, 14))
            lay.addWidget(self.check_lbl)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(16, 16)
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("background: transparent; border: none;")
        if icon_pixmap and not icon_pixmap.isNull():
            self.icon_lbl.setPixmap(icon_pixmap)
        lay.addWidget(self.icon_lbl)

        self.text_lbl = QLabel(label)
        self.text_lbl.setFont(font(9.0, QFont.Medium))
        color = DANGER if is_danger else INK
        self.text_lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        lay.addWidget(self.text_lbl, 1)

        if shortcut:
            self.sc_lbl = QLabel(shortcut)
            self.sc_lbl.setFont(font(8.0))
            self.sc_lbl.setStyleSheet("color: #8E8E93; background: transparent; border: none;")
            lay.addWidget(self.sc_lbl)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        if self._hovered:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setPen(Qt.NoPen)
            bg = QColor("#FEF2F2") if self.is_danger else QColor("#F4F5F7")
            p.setBrush(bg)
            p.drawRoundedRect(QRectF(self.rect()), 7.0, 7.0)
            p.end()
        super().paintEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class HeroPopoverMenu(QWidget):
    """Ultra-modern floating Apple-style popover menu with smooth entrance & exit animations."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        outer_lay = QVBoxLayout(self)
        outer_lay.setContentsMargins(12, 12, 12, 12)
        outer_lay.setSpacing(0)

        self.card = QFrame(self)
        self.card.setObjectName("heroPopoverCard")
        self.card.setStyleSheet("""
            QFrame#heroPopoverCard {
                background: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.09);
                border-radius: 14px;
            }
        """)

        # shadow = QGraphicsDropShadowEffect(self.card)
        # shadow.setBlurRadius(24)
        # shadow.setColor(QColor(0, 0, 0, 34))
        # shadow.setOffset(0, 6)
        # self.card.setGraphicsEffect(shadow)

        self.card_lay = QVBoxLayout(self.card)
        self.card_lay.setContentsMargins(6, 6, 6, 6)
        self.card_lay.setSpacing(2)

        outer_lay.addWidget(self.card)
        self._closing = False
        self._anim = None

    def add_user_header(self, name: str, email_or_role: str, avatar_pixmap: QPixmap = None):
        header = QFrame()
        header.setStyleSheet("background: transparent; border: none;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(8, 6, 8, 6)
        h_lay.setSpacing(10)

        if avatar_pixmap and not avatar_pixmap.isNull():
            av_lbl = QLabel()
            av_lbl.setFixedSize(34, 34)
            av_lbl.setPixmap(avatar_pixmap)
            av_lbl.setAlignment(Qt.AlignCenter)
            av_lbl.setStyleSheet("background: transparent; border: none;")
            h_lay.addWidget(av_lbl)

        t_col = QVBoxLayout()
        t_col.setSpacing(1)
        t_col.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(name)
        name_lbl.setFont(font(9.5, QFont.DemiBold))
        name_lbl.setStyleSheet("color: #111114; background: transparent; border: none;")
        t_col.addWidget(name_lbl)

        if email_or_role:
            sub_lbl = QLabel(email_or_role)
            sub_lbl.setFont(font(8.0))
            sub_lbl.setStyleSheet("color: #8E8E93; background: transparent; border: none;")
            t_col.addWidget(sub_lbl)

        h_lay.addLayout(t_col, 1)
        self.card_lay.addWidget(header)
        self.add_separator()

    def add_action(self, label: str, icon: QPixmap = None, on_click=None, is_danger: bool = False,
                   shortcut: str = "", checkable: bool = False, checked: bool = False):
        item = HeroMenuItem(label, icon, is_danger, shortcut, checkable, checked, self.card)
        if on_click:
            item.clicked.connect(lambda: self._on_item_triggered(on_click))
        else:
            item.clicked.connect(self.close)
        self.card_lay.addWidget(item)
        return item

    def add_separator(self):
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #EFEFF2; border: none; margin: 3px 6px;")
        self.card_lay.addWidget(sep)

    def _on_item_triggered(self, cb):
        self.close()
        QTimer.singleShot(50, cb)

    def popup_below(self, anchor_widget, align="right", offset_y=4):
        self.adjustSize()
        if anchor_widget:
            g_pos = anchor_widget.mapToGlobal(QPoint(0, 0))
            if align == "right":
                x = g_pos.x() + anchor_widget.width() - self.width() + 12
            else:
                x = g_pos.x() - 12
            y = g_pos.y() + anchor_widget.height() + offset_y - 12
        else:
            x, y = QCursor.pos().x() - 12, QCursor.pos().y() - 12

        screen = QApplication.screenAt(QPoint(x, y)) or QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = max(geo.left() + 8, min(x, geo.right() - self.width() - 8))
            y = max(geo.top() + 8, min(y, geo.bottom() - self.height() - 8))

        self.move(x, y)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(140)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._anim = anim

    def popup_at(self, target_pos: QPoint):
        self.adjustSize()
        x, y = target_pos.x() - 12, target_pos.y() - 12
        screen = QApplication.screenAt(QPoint(x, y)) or QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = max(geo.left() + 8, min(x, geo.right() - self.width() - 8))
            y = max(geo.top() + 8, min(y, geo.bottom() - self.height() - 8))

        self.move(x, y)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(140)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._anim = anim

    def close_hero(self):
        self.close()


# ── Hero Sheet Dialog Base ───────────────────────────────────────────


# ── Apple macOS Segmented Control ─────────────────────────────────────
class AppleSegmentedControl(QFrame):
    """Native macOS-style Segmented Control (Tabs/Filters)."""
    segment_changed = Signal(int, str)

    def __init__(self, segments, initial_index=0, parent=None):
        super().__init__(parent)
        self.segments = segments
        self._current_index = initial_index
        self._buttons = []

        self.setFixedHeight(32)
        self.setStyleSheet("""
            AppleSegmentedControl {
                background: #EBECEF;
                border: 1px solid rgba(0, 0, 0, 0.04);
                border-radius: 8px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        for i, text in enumerate(segments):
            btn = QPushButton(text)
            btn.setFixedHeight(26)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.clicked.connect(lambda _, idx=i: self.set_active_index(idx))
            layout.addWidget(btn)
            self._buttons.append(btn)

        self._update_button_styles()

    def set_active_index(self, index):
        if 0 <= index < len(self.segments):
            self._current_index = index
            self._update_button_styles()
            self.segment_changed.emit(index, self.segments[index])

    def current_index(self):
        return self._current_index

    def current_text(self):
        return self.segments[self._current_index] if 0 <= self._current_index < len(self.segments) else ""

    def _update_button_styles(self):
        for i, btn in enumerate(self._buttons):
            if i == self._current_index:
                btn.setFont(font(8.8, QFont.DemiBold))
                btn.setStyleSheet("""
                    QPushButton {
                        background: #FFFFFF;
                        color: #1D1D1F;
                        border: 0.5px solid rgba(0, 0, 0, 0.08);
                        border-radius: 6px;
                        padding: 0 12px;
                    }
                """)
            else:
                btn.setFont(font(8.8, QFont.Medium))
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        color: #6E6E73;
                        border: none;
                        border-radius: 6px;
                        padding: 0 12px;
                    }
                    QPushButton:hover {
                        color: #1D1D1F;
                        background: rgba(0, 0, 0, 0.03);
                    }
                """)

