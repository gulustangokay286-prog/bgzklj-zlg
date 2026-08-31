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
        self.setAttribute(Qt.WA_TranslucentBackground)

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

        btn_move = QPushButton("📁  Bu Klasöre Taşı")
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

        btn_copy = QPushButton("📋  Kopya Olarak Kaydet (+1 Versiyon)")
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
    """Modal: pick an existing folder, create a new one, or leave it unfoldered ("Genel")."""

    def __init__(self, slug: str, current_folder_id=None, parent=None):
        super().__init__(parent)
        self.slug = slug
        self.current_folder_id = current_folder_id
        self.selected_folder_id = current_folder_id
        self._rows = []

        self.setWindowTitle("Nereye Kaydedilsin?")
        self.setFixedSize(500, 560)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        container = QWidget(self)
        container.setObjectName("saveLocCard")
        container.setStyleSheet("""
            #saveLocCard {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 16px;
            }
        """)

        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(24, 22, 24, 20)
        c_lay.setSpacing(12)

        t_lbl = QLabel("Nereye Kaydedilsin?")
        t_lbl.setFont(QFont(FONT_FAMILY, 13, QFont.Bold))
        t_lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        c_lay.addWidget(t_lbl)

        sub_lbl = QLabel("Bu versiyonu bir klasörde düzenleyebilir (örn. \"Yaz Çizelgesi\") ya da klasörsüz bırakabilirsiniz.")
        sub_lbl.setFont(QFont(FONT_FAMILY, 9.5))
        sub_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
        sub_lbl.setWordWrap(True)
        c_lay.addWidget(sub_lbl)

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
        new_row.setSpacing(8)
        self.new_folder_edit = QLineEdit()
        self.new_folder_edit.setPlaceholderText("Yeni klasör adı (Örn: Yaz Çizelgesi)...")
        self.new_folder_edit.setFixedHeight(34)
        self.new_folder_edit.setStyleSheet(f"""
            QLineEdit {{
                background: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 17px;
                padding: 0 14px;
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
        btn_new.setIcon(make_save_vector_icon("plus", 12, "#0071E3"))
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.setFixedHeight(34)
        btn_new.setStyleSheet(f"""
            QPushButton {{
                background: #EFF6FF;
                color: #0071E3;
                border: 1px solid #BFDBFE;
                border-radius: 17px;
                padding: 0 16px;
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
        btn_box.setSpacing(10)
        btn_box.addStretch()

        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFixedHeight(34)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 17px;
                padding: 0 20px;
                font-weight: 600;
                font-size: 12px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{ background: #F8FAFC; color: #0F172A; }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_ok = QPushButton("Kaydet")
        btn_ok.setFixedHeight(34)
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 17px;
                padding: 0 26px;
                font-weight: 700;
                font-size: 12px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{ background: #0062C4; }}
        """)
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)

        c_lay.addLayout(btn_box)
        outer.addWidget(container)

        self._reload_rows()

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
    def choose(cls, parent, slug: str, current_folder_id=None, has_existing_version=False):
        """Shows the dialog. Returns (target_folder_id, action, cancelled: bool).
        action can be:
          - 'save': standard save in current/same folder
          - 'copy': copy to target folder as new version (+1 version number), keep previous version
          - 'move': move existing version to target folder
        """
        dlg = cls(slug, current_folder_id=current_folder_id, parent=parent)
        result = dlg.exec()
        if result != QDialog.Accepted:
            return None, None, True

        target_folder_id = dlg.selected_folder_id

        # If user selected a DIFFERENT folder and there is an existing version in the old folder:
        if has_existing_version and target_folder_id != current_folder_id:
            src_name = version_store.get_folder_name(slug, current_folder_id)
            dst_name = version_store.get_folder_name(slug, target_folder_id)

            transfer_dlg = FolderTransferChoiceDialog(src_name, dst_name, parent=parent)
            transfer_res = transfer_dlg.exec()
            if transfer_res != QDialog.Accepted or transfer_dlg.choice == "cancel":
                return None, None, True

            return target_folder_id, transfer_dlg.choice, False

        return target_folder_id, "save", False
