"""
dialogs/save_location_dialog.py — Kaydet / Ana Sayfa / Kapat işlemlerinden önce gösterilen,
versiyonun hangi klasöre (örn. "Yaz Çizelgesi") kaydedileceğini soran seçim penceresi (Apple Studio Minimalist UI).
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QWidget, QScrollArea, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QFont, QColor, QPixmap, QPainter, QLinearGradient, QBrush, QPen, QIcon, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF

import bk_ui
import version_store
from ui_icons import icon, pixmap

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"


def make_save_vector_icon(name: str, size: int = 16, color_hex: str = "#0071E3") -> QIcon:
    scale = 2
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(scale, scale)
    color = QColor(color_hex)
    
    if name == "folder":
        p.setBrush(QBrush(color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(1, 2, size * 0.45, 4), 2, 2)
        p.drawRoundedRect(QRectF(1, 4.5, size - 2, size - 6.5), 3, 3)
    elif name == "plus":
        p.setPen(QPen(color, 2.0, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(size / 2.0, 3.5), QPointF(size / 2.0, size - 3.5))
        p.drawLine(QPointF(3.5, size / 2.0), QPointF(size - 3.5, size / 2.0))
    elif name == "check":
        p.setPen(QPen(color, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(QPointF(3.5, size / 2.0), QPointF(size / 2.0 - 1, size - 4.5))
        p.drawLine(QPointF(size / 2.0 - 1, size - 4.5), QPointF(size - 3.5, 4))
        
    p.end()
    pix.setDevicePixelRatio(scale)
    return QIcon(pix)


class _FolderRow(QFrame):
    """Tek satır: klasör adı, kaç sürüm var, seçiliyse tik."""

    def __init__(self, folder_id, name, count, is_selected, on_pick, parent=None):
        super().__init__(parent)
        self.folder_id = folder_id
        self._on_pick = on_pick
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        self._selected = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(10)

        ico = QLabel()
        ico.setPixmap(make_save_vector_icon("folder", 16, bk_ui.INK_FAINT).pixmap(16, 16))
        ico.setFixedSize(16, 16)
        ico.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(ico)

        name_lbl = QLabel(name)
        name_lbl.setFont(bk_ui.font(10, QFont.Medium))
        name_lbl.setStyleSheet(f"color: {bk_ui.INK}; background: transparent; border: none;")
        name_lbl.setTextFormat(Qt.PlainText)
        lay.addWidget(name_lbl, 1)

        count_lbl = QLabel("1 sürüm" if count == 1 else f"{count} sürüm")
        count_lbl.setFont(bk_ui.font(9))
        count_lbl.setStyleSheet(f"color: {bk_ui.INK_FAINT}; background: transparent; border: none;")
        lay.addWidget(count_lbl)

        self.check_lbl = QLabel()
        self.check_lbl.setPixmap(make_save_vector_icon("check", 14, bk_ui.BRAND).pixmap(14, 14))
        self.check_lbl.setStyleSheet("background: transparent; border: none;")
        self.check_lbl.setFixedWidth(16)
        lay.addWidget(self.check_lbl)

        self.set_selected(is_selected)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and callable(self._on_pick):
            self._on_pick(self.folder_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        self._selected = selected
        self.check_lbl.setVisible(selected)
        if selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {bk_ui.BRAND_TINT};
                    border: 1px solid {bk_ui.BRAND_TINT_LINE};
                    border-radius: 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 10px;
                }}
                QFrame:hover {{ background: {bk_ui.HOVER}; }}
            """)


class FolderTransferChoiceDialog(QDialog):
    """Apple-styled modal dialog asking whether to copy as a new version or move to the selected new folder."""

    def __init__(self, src_folder_name: str, dst_folder_name: str, parent=None):
        super().__init__(parent)
        self.choice = "cancel"  # "copy", "move", "cancel"

        self.setWindowTitle("Klasör Değişikliği")
        self.setFixedSize(520, 270)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        # Saydam DEĞİL: içeriği henüz boyanmamış saydam bir pencere
        # macOS'ta kapkara görünüyor. Bu pencereler arayüzün meşgul
        # olduğu anlarda (kaydetme, motoru durdurma) açıldığı için
        # ekranda siyah dikdörtgenler olarak kalıyordu.
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAutoFillBackground(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        container = QWidget(self)
        container.setObjectName("transferCard")
        container.setStyleSheet("""
            #transferCard {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 16px;
            }
        """)

        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(24, 22, 24, 20)
        c_lay.setSpacing(12)

        t_lbl = QLabel("Klasör Değişikliği / Çizelge Aktarımı")
        t_lbl.setFont(QFont(FONT_FAMILY, 13, QFont.Bold))
        t_lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        c_lay.addWidget(t_lbl)

        sub_lbl = QLabel(
            f"Bu çizelge şu an <b>{src_folder_name}</b> klasöründe bulunuyor.<br>"
            f"Seçilen <b>{dst_folder_name}</b> klasörüne nasıl aktarılsın?"
        )
        sub_lbl.setFont(QFont(FONT_FAMILY, 10))
        sub_lbl.setStyleSheet("color: #475569; background: transparent; border: none;")
        sub_lbl.setWordWrap(True)
        c_lay.addWidget(sub_lbl)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: #E2E8F0; border: none;")
        c_lay.addWidget(div)

        c_lay.addStretch(1)

        # Action Buttons Layout (Pill style)
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: #FFFFFF;
                color: #64748B;
                border: 1px solid #CBD5E1;
                border-radius: 18px;
                padding: 0 18px;
                font-weight: 600;
                font-size: 12px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{ background: #F8FAFC; color: #0F172A; }}
        """)
        btn_cancel.clicked.connect(self._on_cancel)
        btn_box.addWidget(btn_cancel)

        btn_box.addStretch(1)

        btn_move = QPushButton(" Bu Klasöre Taşı")
        btn_move.setIcon(icon("folder", 15, "#0F172A"))
        btn_move.setFixedHeight(36)
        btn_move.setCursor(Qt.PointingHandCursor)
        btn_move.setToolTip("Çizelgeyi doğrudan bu klasöre taşır (eski klasörde kopya bırakmaz).")
        btn_move.setStyleSheet(f"""
            QPushButton {{
                background: #F1F5F9;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 18px;
                padding: 0 18px;
                font-weight: 600;
                font-size: 12px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{ background: #E2E8F0; }}
        """)
        btn_move.clicked.connect(self._on_move)
        btn_box.addWidget(btn_move)

        btn_copy = QPushButton(" Kopya Olarak Kaydet (+1 Versiyon)")
        btn_copy.setIcon(icon("save", 15, "#0F172A"))
        btn_copy.setFixedHeight(36)
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setToolTip("Mevcut çizelgeyi önceki klasörde korur, bu klasöre yeni bir versiyon olarak kopyalar.")
        btn_copy.setStyleSheet(f"""
            QPushButton {{
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 18px;
                padding: 0 20px;
                font-weight: 700;
                font-size: 12px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{ background: #0062C4; }}
        """)
        btn_copy.clicked.connect(self._on_copy)
        btn_box.addWidget(btn_copy)

        c_lay.addLayout(btn_box)
        outer.addWidget(container)

    def _on_cancel(self):
        self.choice = "cancel"
        self.reject()

    def _on_move(self):
        self.choice = "move"
        self.accept()

    def _on_copy(self):
        self.choice = "copy"
        self.accept()


class SaveLocationDialog(QDialog):
    """Kaydetme sayfası: isim, not, klasör; en altta üç düğme.

    Burası 760×620'lik, kenarlı-gölgeli bir karttı; "Nereye Kaydedilsin?"
    başlığı, iki cümlelik açıklama, aç-kapa düğmeleriyle açılan isim ve
    not kutuları, kapsül rozetler. Kullanıcı bir sürümü kaydetmek için
    bunların hiçbirine ihtiyaç duymuyor. Şimdi: tek başlık, iki satır
    (isim, not — ikisi de isteğe bağlı ve hep görünür), klasör listesi,
    üç düğme. Programın öbür sayfalarıyla aynı dil: beyaz, çerçevesiz,
    gölgesiz, dış çerçevesiz.

    "Kaydetmeden Çık" ikinci bir pencere açmaz; düğme sırası yerinde
    "Değişiklikler kaybolacak — Vazgeç / Evet" biçimine döner.
    """

    def __init__(self, slug: str, current_folder_id=None, parent=None,
                 version_num: int = 1, initial_custom_name: str = "", initial_note: str = "",
                 allow_discard: bool = False):
        super().__init__(parent)
        # allow_discard yalnızca çıkarken (ana sayfa / kapat) açık: "Kaydet"
        # düğmesinden gelen kullanıcıya "kaydetme" seçeneği sunulmaz.
        self.allow_discard = bool(allow_discard)
        self.discarded = False
        self.slug = slug
        self.current_folder_id = current_folder_id
        self.selected_folder_id = current_folder_id
        self.version_num = version_num or 1
        self._rows = []
        self._drag_from = None

        self.setWindowTitle("Kaydet")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        # Saydam değil: içeriği boyanmamış saydam pencere macOS'ta kara görünüyor.
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAutoFillBackground(True)
        self.setStyleSheet("QDialog { background: #FFFFFF; }")
        self.setModal(True)
        self.setFixedWidth(520)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(0)

        title = QLabel("Kaydet")
        title.setFont(bk_ui.font(14.5, QFont.DemiBold, spacing=-0.2))
        title.setStyleSheet(f"color: {bk_ui.INK}; background: transparent; border: none;")
        lay.addWidget(title)
        lay.addSpacing(16)

        # ── İsim: sürüm numarası + isteğe bağlı isim, tek satır ────────
        field_css = f"""
            QFrame#field {{
                background: #FFFFFF;
                border: 1px solid {bk_ui.HAIRLINE_STRONG};
                border-radius: 10px;
            }}
            QFrame#field:hover {{ border-color: {bk_ui.INK_FAINT}; }}
        """
        edit_css = f"""
            QLineEdit {{
                border: none; background: transparent; padding: 0;
                color: {bk_ui.INK};
            }}
        """
        name_box = QFrame()
        name_box.setObjectName("field")
        name_box.setFixedHeight(40)
        name_box.setStyleSheet(field_css)
        name_lay = QHBoxLayout(name_box)
        name_lay.setContentsMargins(8, 0, 12, 0)
        name_lay.setSpacing(10)

        self.prefix_badge = QLabel(f"v{self.version_num}")
        self.prefix_badge.setFont(bk_ui.font(9, QFont.DemiBold))
        self.prefix_badge.setAlignment(Qt.AlignCenter)
        self.prefix_badge.setStyleSheet(f"""
            QLabel {{
                background: {bk_ui.BRAND_TINT}; color: {bk_ui.BRAND};
                border: none; border-radius: 7px; padding: 0 9px;
                min-height: 22px; max-height: 22px;
            }}
        """)
        name_lay.addWidget(self.prefix_badge)

        self.name_edit = QLineEdit()
        self.name_edit.setFont(bk_ui.font(10))
        self.name_edit.setPlaceholderText("İsim (isteğe bağlı)")
        self.name_edit.setStyleSheet(edit_css)
        if initial_custom_name:
            self.name_edit.setText(initial_custom_name)
        name_lay.addWidget(self.name_edit, 1)
        lay.addWidget(name_box)
        lay.addSpacing(8)

        # ── Not ───────────────────────────────────────────────────────
        note_box = QFrame()
        note_box.setObjectName("field")
        note_box.setFixedHeight(40)
        note_box.setStyleSheet(field_css)
        note_lay = QHBoxLayout(note_box)
        note_lay.setContentsMargins(12, 0, 12, 0)
        self.note_edit = QLineEdit()
        self.note_edit.setFont(bk_ui.font(10))
        self.note_edit.setPlaceholderText("Not (isteğe bağlı)")
        self.note_edit.setStyleSheet(edit_css)
        if initial_note:
            self.note_edit.setText(initial_note)
        note_lay.addWidget(self.note_edit, 1)
        lay.addWidget(note_box)
        # Eski arayüzle uyum: bu iki kutu her zaman görünür.
        self.name_box, self.note_box = name_box, note_box

        lay.addSpacing(18)

        # ── Klasör ────────────────────────────────────────────────────
        sec = QLabel("KLASÖR")
        sec.setFont(bk_ui.font(8.2, QFont.DemiBold, spacing=0.8))
        sec.setStyleSheet(f"color: {bk_ui.INK_FAINT}; background: transparent; border: none;")
        lay.addWidget(sec)
        lay.addSpacing(6)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(2)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.list_container)
        lay.addWidget(self.scroll)

        # Yeni klasör: listenin altında tek satır, Enter ile eklenir.
        new_row = QFrame()
        new_row.setObjectName("field")
        new_row.setFixedHeight(40)
        new_row.setStyleSheet(field_css.replace("#FFFFFF", bk_ui.SURFACE_SUNK, 1))
        new_lay = QHBoxLayout(new_row)
        new_lay.setContentsMargins(12, 0, 8, 0)
        new_lay.setSpacing(10)
        plus = QLabel()
        plus.setPixmap(make_save_vector_icon("plus", 14, bk_ui.INK_FAINT).pixmap(14, 14))
        plus.setFixedSize(16, 16)
        plus.setStyleSheet("background: transparent; border: none;")
        new_lay.addWidget(plus)
        self.new_folder_edit = QLineEdit()
        self.new_folder_edit.setFont(bk_ui.font(10))
        self.new_folder_edit.setPlaceholderText("Yeni klasör")
        self.new_folder_edit.setStyleSheet(edit_css)
        self.new_folder_edit.returnPressed.connect(self._create_folder)
        new_lay.addWidget(self.new_folder_edit, 1)
        btn_new = QPushButton("Ekle")
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.setFixedHeight(28)
        btn_new.setFont(bk_ui.font(9.4, QFont.DemiBold))
        btn_new.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {bk_ui.BRAND};
                border: none; border-radius: 14px; padding: 0 12px;
            }}
            QPushButton:hover {{ background: rgba(15, 74, 171, 0.07); }}
        """)
        btn_new.clicked.connect(self._create_folder)
        new_lay.addWidget(btn_new)
        lay.addSpacing(4)
        lay.addWidget(new_row)

        self.warn_lbl = QLabel("")
        self.warn_lbl.setFont(bk_ui.font(9))
        self.warn_lbl.setStyleSheet(f"color: {bk_ui.DANGER}; background: transparent; border: none;")
        self.warn_lbl.setVisible(False)
        lay.addSpacing(4)
        lay.addWidget(self.warn_lbl)
        self.new_folder_edit.textEdited.connect(lambda _: self.warn_lbl.setVisible(False))

        lay.addSpacing(18)

        # ── Düğmeler ─────────────────────────────────────────────────
        def naked(text, colour, hover_bg):
            b = QPushButton(text)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(38)
            b.setFont(bk_ui.font(9.6, QFont.Medium))
            b.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {colour};
                    border: none; border-radius: 19px; padding: 0 16px;
                }}
                QPushButton:hover {{ background: {hover_bg}; }}
            """)
            return b

        def filled(text, colour, hover):
            b = QPushButton(text)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(38)
            b.setFont(bk_ui.font(9.6, QFont.DemiBold))
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {colour}; color: #FFFFFF;
                    border: none; border-radius: 19px; padding: 0 22px;
                }}
                QPushButton:hover {{ background: {hover}; }}
            """)
            b.setMinimumWidth(b.sizeHint().width() + 14)
            return b

        # Asıl sıra
        self._row_main = QWidget()
        row = QHBoxLayout(self._row_main)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        if self.allow_discard:
            btn_discard = naked("Kaydetmeden Çık", bk_ui.DANGER, bk_ui.DANGER_TINT)
            btn_discard.clicked.connect(self._ask_discard)
            row.addWidget(btn_discard)
        row.addStretch(1)
        btn_cancel = naked("Vazgeç", bk_ui.INK_SOFT, "rgba(15, 23, 42, 0.05)")
        btn_cancel.clicked.connect(self.reject)
        row.addWidget(btn_cancel)
        btn_ok = filled("Kaydet", bk_ui.BRAND, bk_ui.BRAND_DARK)
        btn_ok.clicked.connect(self.accept)
        btn_ok.setDefault(True)
        row.addWidget(btn_ok)
        lay.addWidget(self._row_main)

        # "Kaydetmeden çık" onayı: aynı yerde, ikinci pencere yok.
        self._row_discard = QWidget()
        drow = QHBoxLayout(self._row_discard)
        drow.setContentsMargins(0, 0, 0, 0)
        drow.setSpacing(8)
        warn = QLabel("Değişiklikler kaybolacak.")
        warn.setFont(bk_ui.font(9.6))
        warn.setStyleSheet(f"color: {bk_ui.INK}; background: transparent; border: none;")
        drow.addWidget(warn)
        drow.addStretch(1)
        btn_back = naked("Vazgeç", bk_ui.INK_SOFT, "rgba(15, 23, 42, 0.05)")
        btn_back.clicked.connect(lambda: self._show_discard(False))
        drow.addWidget(btn_back)
        btn_yes = filled("Evet, kaydetmeden çık", bk_ui.DANGER, "#B93A3A")
        btn_yes.clicked.connect(self._on_discard)
        drow.addWidget(btn_yes)
        self._row_discard.setVisible(False)
        lay.addWidget(self._row_discard)

        self._reload_rows()

    # ── kaydetmeden çık ──────────────────────────────────────────────
    def _ask_discard(self):
        self._show_discard(True)

    def _show_discard(self, on):
        self._row_main.setVisible(not on)
        self._row_discard.setVisible(on)

    def _on_discard(self):
        """Değişiklikleri atarak çık; onay aynı sayfada alındı."""
        self.discarded = True
        self.reject()

    # ── konum ────────────────────────────────────────────────────────
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
            from PySide6.QtWidgets import QApplication
            screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
            if screen is None:
                return
            ref = screen.availableGeometry()
        from PySide6.QtCore import QPoint
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

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            if self._row_discard.isVisible():
                self._show_discard(False)
                return
            self.reject()
            return
        super().keyPressEvent(e)

    @property
    def custom_name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def note(self) -> str:
        return self.note_edit.text().strip()

    def _reload_rows(self):
        # Listeyi baştan kur: önce Genel, sonra klasörler, en altta esneme.
        # (Eskiden esneme ilk yeniden kurulumda siliniyor ve Genel listenin
        # sonuna düşüyordu.)
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self._rows = []

        try:
            versions = version_store.list_versions(self.slug)
        except Exception:
            versions = []
        counts_by_folder = {}
        for v in versions:
            counts_by_folder[v.get("folder_id")] = counts_by_folder.get(v.get("folder_id"), 0) + 1

        general_row = _FolderRow(None, "Genel", counts_by_folder.get(None, 0),
                                  self.selected_folder_id is None, self._pick_folder)
        self.list_layout.addWidget(general_row)
        self._rows.append(general_row)

        try:
            folders = version_store.list_folders(self.slug)
        except Exception:
            folders = []
        for folder in folders:
            fid = folder.get("id")
            row = _FolderRow(fid, folder.get("name", ""), counts_by_folder.get(fid, 0),
                              self.selected_folder_id == fid, self._pick_folder)
            self.list_layout.addWidget(row)
            self._rows.append(row)
        self.list_layout.addStretch(1)

        # Liste kadar yer: az klasörde boşluk yok, çokta en çok beş satır
        # görünür, gerisi kayar.
        rows = max(1, len(self._rows))
        self.scroll.setFixedHeight(min(rows, 5) * 42)
        self.adjustSize()

    def _pick_folder(self, folder_id):
        self.selected_folder_id = folder_id
        for row in self._rows:
            row.set_selected(row.folder_id == folder_id)

    def _create_folder(self):
        name = self.new_folder_edit.text().strip()
        if not name:
            self.new_folder_edit.setFocus()
            return
        folder, created = version_store.create_folder(self.slug, name)
        if not folder:
            return
        if not created:
            self.warn_lbl.setText(f"\"{name}\" adında bir klasör zaten var — ona geçildi.")
            self.warn_lbl.setVisible(True)
        else:
            self.warn_lbl.setVisible(False)
        self.new_folder_edit.clear()
        self._reload_rows()
        self._pick_folder(folder.get("id"))

    @classmethod
    def choose(cls, parent, slug: str, current_folder_id=None, has_existing_version=False,
               version_num: int = 1, initial_custom_name: str = "", initial_note: str = "",
               allow_discard: bool = False):
        """Shows the dialog. Returns (target_folder_id, action, custom_name, note, cancelled: bool).
        action can be:
          - 'save': standard save in current/same folder
          - 'copy': copy to target folder as new version (+1 version number), keep previous version
          - 'move': move existing version to target folder
          - 'discard': kullanıcı kaydetmeden çıkmayı seçti (allow_discard ile)
        """
        dlg = cls(slug, current_folder_id=current_folder_id, parent=parent,
                  version_num=version_num, initial_custom_name=initial_custom_name,
                  initial_note=initial_note, allow_discard=allow_discard)
        result = dlg.exec()
        if getattr(dlg, "discarded", False):
            # İptal DEĞİL: çağıran işine devam etsin, ama hiçbir şey yazmasın.
            return None, "discard", "", "", False
        if result != QDialog.Accepted:
            return None, None, "", "", True

        target_folder_id = dlg.selected_folder_id
        custom_name = dlg.custom_name
        note = dlg.note

        # If user selected a DIFFERENT folder and there is an existing version in the old folder:
        if has_existing_version and target_folder_id != current_folder_id:
            src_name = version_store.get_folder_name(slug, current_folder_id)
            dst_name = version_store.get_folder_name(slug, target_folder_id)

            transfer_dlg = FolderTransferChoiceDialog(src_name, dst_name, parent=parent)
            transfer_res = transfer_dlg.exec()
            if transfer_res != QDialog.Accepted or transfer_dlg.choice == "cancel":
                return None, None, "", "", True

            return target_folder_id, transfer_dlg.choice, custom_name, note, False

        return target_folder_id, "save", custom_name, note, False
