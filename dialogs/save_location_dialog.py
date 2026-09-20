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
    clicked_folder_id = None

    def __init__(self, folder_id, name, count, is_selected, on_pick, parent=None):
        super().__init__(parent)
        self.folder_id = folder_id
        self._on_pick = on_pick
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(50)
        self._selected = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(12)

        icon = QLabel()
        folder_color = "#0071E3" if (folder_id is None) else "#F59E0B"
        icon.setPixmap(make_save_vector_icon("folder", 18, folder_color).pixmap(18, 18))
        icon.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(icon)

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont(FONT_FAMILY, 10.5, QFont.Bold))
        name_lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        name_lbl.setTextFormat(Qt.PlainText)
        lay.addWidget(name_lbl, 1)

        # Full Cylindrical Pill Version Count Badge
        count_txt = "1 versiyon" if count == 1 else f"{count} versiyon"
        count_badge = QLabel(count_txt)
        count_badge.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        count_badge.setAlignment(Qt.AlignCenter)
        count_badge.setStyleSheet("""
            QLabel {
                background: #F1F5F9;
                color: #475569;
                border-radius: 13px;
                min-height: 26px;
                max-height: 26px;
                padding: 0 12px;
                border: 1px solid #E2E8F0;
            }
        """)
        lay.addWidget(count_badge)

        self.check_lbl = QLabel()
        self.check_lbl.setPixmap(make_save_vector_icon("check", 14, "#0071E3").pixmap(14, 14))
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
            self.setStyleSheet("""
                QFrame {
                    background: #EFF6FF;
                    border: 1.5px solid #0071E3;
                    border-radius: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                }
                QFrame:hover {
                    background: #F8FAFC;
                    border-color: #CBD5E1;
                }
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
    """Modal: pick an existing folder, create a new one, or leave it unfoldered ("Genel").
    Also allows defining a custom schedule name (e.g. 'v200 Oturmaya Yakın') and custom note.
    """

    def __init__(self, slug: str, current_folder_id=None, parent=None,
                 version_num: int = 1, initial_custom_name: str = "", initial_note: str = "",
                 allow_discard: bool = False):
        super().__init__(parent)
        # Bu pencere iki farklı soruyla açılıyor: "Kaydet"e basıldığında
        # (nereye kaydedeyim?) ve çıkarken (kaydedeyim mi?). İkincisinde
        # üçüncü bir cevap var: kaydetme. allow_discard yalnızca o
        # durumda açılır — "Kaydet" düğmesinden gelen kullanıcıya
        # "kaydetme" seçeneği sunmak saçma olurdu.
        self.allow_discard = bool(allow_discard)
        self.discarded = False
        self.slug = slug
        self.current_folder_id = current_folder_id
        self.selected_folder_id = current_folder_id
        self.version_num = version_num or 1
        self._rows = []

        self.setWindowTitle("Nereye Kaydedilsin?")
        self.setFixedSize(760, 620)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        # Saydam DEĞİL: içeriği henüz boyanmamış saydam bir pencere
        # macOS'ta kapkara görünüyor. Bu pencereler arayüzün meşgul
        # olduğu anlarda (kaydetme, motoru durdurma) açıldığı için
        # ekranda siyah dikdörtgenler olarak kalıyordu.
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAutoFillBackground(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)

        container = QWidget(self)
        container.setObjectName("saveLocCard")
        container.setStyleSheet("""
            #saveLocCard {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 18px;
            }
        """)

        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(26, 24, 26, 22)
        c_lay.setSpacing(12)

        # ── Header & Action Buttons Row ──────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        t_lbl = QLabel("Nereye Kaydedilsin?")
        t_lbl.setFont(QFont(FONT_FAMILY, 14, QFont.Bold))
        t_lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        title_col.addWidget(t_lbl)

        sub_lbl = QLabel("Bu versiyonu bir klasörde düzenleyebilir (örn. \"Yaz Çizelgesi\") ya da klasörsüz bırakabilirsiniz.")
        sub_lbl.setFont(QFont(FONT_FAMILY, 9.5))
        sub_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
        sub_lbl.setWordWrap(True)
        title_col.addWidget(sub_lbl)
        header_row.addLayout(title_col, 1)

        # Action buttons: "İsim Tanımla" and "Not Ekle"
        btn_action_box = QHBoxLayout()
        btn_action_box.setSpacing(8)

        self.btn_add_name = QPushButton(" İsim Tanımla")
        self.btn_add_name.setIcon(icon("tag", 14, "#0F172A"))
        self.btn_add_name.setFixedHeight(34)
        self.btn_add_name.setCursor(Qt.PointingHandCursor)
        self.btn_add_name.setToolTip("Çizelgeye 'v200 Oturmaya Yakın' gibi özel bir isim tanımlayın")
        btn_action_box.addWidget(self.btn_add_name)

        self.btn_add_note = QPushButton(" Not Ekle")
        self.btn_add_note.setIcon(icon("note", 14, "#0F172A"))
        self.btn_add_note.setFixedHeight(34)
        self.btn_add_note.setCursor(Qt.PointingHandCursor)
        self.btn_add_note.setToolTip("Versiyona ait özel bir not ekleyin")
        btn_action_box.addWidget(self.btn_add_note)

        header_row.addLayout(btn_action_box)
        c_lay.addLayout(header_row)

        # ── SCHEDULE NAME COMPONENT BOX (v200 otomatik + text input aynı kutuda) ──
        self.name_box = QFrame()
        self.name_box.setObjectName("scheduleNameBox")
        self.name_box.setFixedHeight(44)
        self.name_box.setStyleSheet("""
            #scheduleNameBox {
                background: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 12px;
            }
            #scheduleNameBox:hover {
                border-color: #94A3B8;
            }
        """)
        name_lay = QHBoxLayout(self.name_box)
        name_lay.setContentsMargins(8, 4, 10, 4)
        name_lay.setSpacing(10)

        # Automatic Version Prefix Badge (v200) inside the component box
        self.prefix_badge = QLabel(f"v{self.version_num}")
        self.prefix_badge.setFont(QFont(FONT_FAMILY, 9.5, QFont.Bold))
        self.prefix_badge.setAlignment(Qt.AlignCenter)
        self.prefix_badge.setStyleSheet("""
            QLabel {
                background: #EFF6FF;
                color: #0071E3;
                border: 1px solid #BFDBFE;
                border-radius: 8px;
                padding: 3px 12px;
                min-height: 24px;
                max-height: 24px;
                font-weight: bold;
            }
        """)
        name_lay.addWidget(self.prefix_badge)

        # Editable Text Field for Custom Schedule Name
        self.name_edit = QLineEdit()
        self.name_edit.setFont(QFont(FONT_FAMILY, 10.5))
        self.name_edit.setPlaceholderText("Çizelge ismi tanımlayın (örn: Oturan Program, Oturmaya Yakın, Salı Boş)...")
        self.name_edit.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background: transparent;
                color: #0F172A;
                font-family: {FONT_FAMILY};
                font-size: 12.5px;
                padding: 0;
            }}
        """)
        if initial_custom_name:
            self.name_edit.setText(initial_custom_name)
        name_lay.addWidget(self.name_edit, 1)

        btn_clear_name = QPushButton("✕")
        btn_clear_name.setFixedSize(22, 22)
        btn_clear_name.setCursor(Qt.PointingHandCursor)
        btn_clear_name.setToolTip("İsmi temizle ve kutuyu kapat")
        btn_clear_name.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                border: none;
                border-radius: 11px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #F1F5F9;
                color: #0F172A;
            }
        """)
        name_lay.addWidget(btn_clear_name)
        c_lay.addWidget(self.name_box)

        # ── NOTE COMPONENT BOX ───────────────────────────────────────────────────
        self.note_box = QFrame()
        self.note_box.setObjectName("scheduleNoteBox")
        self.note_box.setFixedHeight(44)
        self.note_box.setStyleSheet("""
            #scheduleNoteBox {
                background: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 12px;
            }
            #scheduleNoteBox:hover {
                border-color: #94A3B8;
            }
        """)
        note_lay = QHBoxLayout(self.note_box)
        note_lay.setContentsMargins(8, 4, 10, 4)
        note_lay.setSpacing(10)

        note_badge = QLabel("Not")
        note_badge.setFont(QFont(FONT_FAMILY, 9.5, QFont.Bold))
        note_badge.setAlignment(Qt.AlignCenter)
        note_badge.setStyleSheet("""
            QLabel {
                background: #F1F5F9;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 3px 12px;
                min-height: 24px;
                max-height: 24px;
                font-weight: bold;
            }
        """)
        note_lay.addWidget(note_badge)

        self.note_edit = QLineEdit()
        self.note_edit.setFont(QFont(FONT_FAMILY, 10.5))
        self.note_edit.setPlaceholderText("Çizelgeye özel not ekleyin (örn: Cuma öğleden sonra boşaltıldı)...")
        self.note_edit.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background: transparent;
                color: #0F172A;
                font-family: {FONT_FAMILY};
                font-size: 12.5px;
                padding: 0;
            }}
        """)
        if initial_note:
            self.note_edit.setText(initial_note)
        note_lay.addWidget(self.note_edit, 1)

        btn_clear_note = QPushButton("✕")
        btn_clear_note.setFixedSize(22, 22)
        btn_clear_note.setCursor(Qt.PointingHandCursor)
        btn_clear_note.setToolTip("Notu temizle ve kutuyu kapat")
        btn_clear_note.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                border: none;
                border-radius: 11px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #F1F5F9;
                color: #0F172A;
            }
        """)
        note_lay.addWidget(btn_clear_note)
        c_lay.addWidget(self.note_box)

        # Wire up actions
        def _toggle_name():
            vis = not self.name_box.isVisible()
            self.name_box.setVisible(vis)
            self._update_btn_states()
            if vis:
                self.name_edit.setFocus()
                self.name_edit.selectAll()

        def _toggle_note():
            vis = not self.note_box.isVisible()
            self.note_box.setVisible(vis)
            self._update_btn_states()
            if vis:
                self.note_edit.setFocus()
                self.note_edit.selectAll()

        def _clear_and_hide_name():
            self.name_edit.clear()
            self.name_box.setVisible(False)
            self._update_btn_states()

        def _clear_and_hide_note():
            self.note_edit.clear()
            self.note_box.setVisible(False)
            self._update_btn_states()

        self.btn_add_name.clicked.connect(_toggle_name)
        self.btn_add_note.clicked.connect(_toggle_note)
        btn_clear_name.clicked.connect(_clear_and_hide_name)
        btn_clear_note.clicked.connect(_clear_and_hide_note)

        self.name_edit.textChanged.connect(lambda _: self._update_btn_states())
        self.note_edit.textChanged.connect(lambda _: self._update_btn_states())

        # Initial visibility: if custom name or note is pre-filled, show respective box
        self.name_box.setVisible(bool(initial_custom_name))
        self.note_box.setVisible(bool(initial_note))
        self._update_btn_states()

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: #E2E8F0; border: none;")
        c_lay.addWidget(div)

        # Scrollable folder list
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(2, 4, 2, 4)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch(1)

        self.scroll.setWidget(self.list_container)
        c_lay.addWidget(self.scroll, 1)

        # New-folder inline creator
        new_row = QHBoxLayout()
        new_row.setSpacing(10)
        self.new_folder_edit = QLineEdit()
        self.new_folder_edit.setPlaceholderText("Yeni klasör adı (Örn: Yaz Çizelgesi)...")
        self.new_folder_edit.setFixedHeight(36)
        self.new_folder_edit.setStyleSheet(f"""
            QLineEdit {{
                background: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 18px;
                padding: 0 16px;
                font-size: 12px;
                font-family: {FONT_FAMILY};
                color: #0F172A;
            }}
            QLineEdit:focus {{
                border-color: #0071E3;
                background: #FFFFFF;
            }}
        """)
        self.new_folder_edit.returnPressed.connect(self._create_folder)
        new_row.addWidget(self.new_folder_edit, 1)

        btn_new = QPushButton("  Yeni Klasör")
        btn_new.setIcon(icon("folder", 15, "#0F172A"))
        btn_new.setIcon(make_save_vector_icon("plus", 12, "#0071E3"))
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.setFixedHeight(36)
        btn_new.setStyleSheet(f"""
            QPushButton {{
                background: #EFF6FF;
                color: #0071E3;
                border: 1px solid #BFDBFE;
                border-radius: 18px;
                padding: 0 18px;
                font-weight: 700;
                font-size: 11.5px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{ background: #DBEAFE; }}
        """)
        btn_new.clicked.connect(self._create_folder)
        new_row.addWidget(btn_new)
        c_lay.addLayout(new_row)

        self.warn_lbl = QLabel("")
        self.warn_lbl.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self.warn_lbl.setStyleSheet("color: #DC2626; background: transparent; border: none;")
        self.warn_lbl.setVisible(False)
        c_lay.addWidget(self.warn_lbl)
        self.new_folder_edit.textEdited.connect(lambda _: self.warn_lbl.setVisible(False))

        # Bottom buttons (Silindirik / Pill)
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        if self.allow_discard:
            # SOLDA, ÇERÇEVESİZ, TEK BAŞINA.
            #
            # Geri dönüşü olmayan seçenek, kaydetme düğmesinin yanında
            # aynı ağırlıkta durmamalı: yan yana iki kapsülden birine
            # yanlışlıkla basmak bir günlük işi siler. Bu yüzden karşı
            # tarafta ve çıplak duruyor; rengi ne yaptığını söylüyor.
            btn_discard = QPushButton("Kaydetmeden Çık")
            btn_discard.setFixedHeight(36)
            btn_discard.setCursor(Qt.PointingHandCursor)
            btn_discard.setToolTip("Bu çizelgede yaptığınız değişiklikler kaydedilmez.")
            btn_discard.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: #B91C1C;
                    border: none;
                    border-radius: 18px;
                    padding: 0 16px;
                    font-weight: 600;
                    font-size: 12px;
                    font-family: {FONT_FAMILY};
                }}
                QPushButton:hover {{ background: #FEF2F2; color: #991B1B; }}
                QPushButton:pressed {{ background: #FEE2E2; }}
            """)
            btn_discard.clicked.connect(self._on_discard)
            btn_box.addWidget(btn_discard)

        btn_box.addStretch()

        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 18px;
                padding: 0 24px;
                font-weight: 600;
                font-size: 12px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{ background: #F8FAFC; color: #0F172A; }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_ok = QPushButton("Kaydet")
        btn_ok.setFixedHeight(36)
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 18px;
                padding: 0 32px;
                font-weight: 700;
                font-size: 12.5px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{ background: #0062C4; }}
        """)
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)

        c_lay.addLayout(btn_box)
        outer.addWidget(container)

        self._reload_rows()

    def _on_discard(self):
        """Değişiklikleri atarak çık — önce bir kez sorulur."""
        from PySide6.QtWidgets import QMessageBox
        ret = QMessageBox.warning(
            self, "Kaydetmeden çıkılsın mı?",
            "Bu çizelgede yaptığınız değişiklikler <b>kaydedilmeyecek</b>.<br><br>"
            "Çizelge en son kaydedilen hâline döner.",
            QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Cancel)
        if ret != QMessageBox.Discard:
            return
        self.discarded = True
        self.reject()

    def _update_btn_states(self):
        # Name button style
        is_name_active = self.name_box.isVisible() or bool(self.name_edit.text().strip())
        if is_name_active:
            self.btn_add_name.setStyleSheet(f"""
                QPushButton {{
                    background: #EFF6FF;
                    color: #0071E3;
                    border: 1.5px solid #0071E3;
                    border-radius: 17px;
                    padding: 0 16px;
                    font-weight: 700;
                    font-size: 12px;
                    font-family: {FONT_FAMILY};
                }}
            """)
        else:
            self.btn_add_name.setStyleSheet(f"""
                QPushButton {{
                    background: #F8FAFC;
                    color: #334155;
                    border: 1px solid #CBD5E1;
                    border-radius: 17px;
                    padding: 0 16px;
                    font-weight: 600;
                    font-size: 12px;
                    font-family: {FONT_FAMILY};
                }}
                QPushButton:hover {{
                    background: #EFF6FF;
                    border-color: #93C5FD;
                    color: #0071E3;
                }}
            """)

        # Note button style
        is_note_active = self.note_box.isVisible() or bool(self.note_edit.text().strip())
        if is_note_active:
            self.btn_add_note.setStyleSheet(f"""
                QPushButton {{
                    background: #EFF6FF;
                    color: #0071E3;
                    border: 1.5px solid #0071E3;
                    border-radius: 17px;
                    padding: 0 16px;
                    font-weight: 700;
                    font-size: 12px;
                    font-family: {FONT_FAMILY};
                }}
            """)
        else:
            self.btn_add_note.setStyleSheet(f"""
                QPushButton {{
                    background: #F8FAFC;
                    color: #334155;
                    border: 1px solid #CBD5E1;
                    border-radius: 17px;
                    padding: 0 16px;
                    font-weight: 600;
                    font-size: 12px;
                    font-family: {FONT_FAMILY};
                }}
                QPushButton:hover {{
                    background: #EFF6FF;
                    border-color: #93C5FD;
                    color: #0071E3;
                }}
            """)

    @property
    def custom_name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def note(self) -> str:
        return self.note_edit.text().strip()

    def _reload_rows(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._rows = []

        try:
            versions = version_store.list_versions(self.slug)
        except Exception:
            versions = []
        counts_by_folder = {}
        for v in versions:
            counts_by_folder[v.get("folder_id")] = counts_by_folder.get(v.get("folder_id"), 0) + 1

        general_row = _FolderRow(None, "Genel (Klasörsüz)", counts_by_folder.get(None, 0),
                                  self.selected_folder_id is None, self._pick_folder)
        self.list_layout.insertWidget(self.list_layout.count() - 1, general_row)
        self._rows.append(general_row)

        try:
            folders = version_store.list_folders(self.slug)
        except Exception:
            folders = []
        for folder in folders:
            fid = folder.get("id")
            row = _FolderRow(fid, folder.get("name", ""), counts_by_folder.get(fid, 0),
                              self.selected_folder_id == fid, self._pick_folder)
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)
            self._rows.append(row)

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
