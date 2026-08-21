"""
dialogs/save_location_dialog.py — Kaydet / Ana Sayfa / Kapat işlemlerinden önce gösterilen,
versiyonun hangi klasöre (örn. "Yaz Çizelgesi") kaydedileceğini soran seçim penceresi.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QWidget, QScrollArea, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt

import version_store


class _FolderRow(QFrame):
    clicked_folder_id = None  # set on the instance, not the class

    def __init__(self, folder_id, name, count, is_selected, on_pick, parent=None):
        super().__init__(parent)
        self.folder_id = folder_id
        self._on_pick = on_pick
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(46)
        self._selected = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(10)

        icon = QLabel("📁" if folder_id else "🗂️")
        icon.setFont(QFont("Segoe UI", 13))
        icon.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(icon)

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Segoe UI", 10.5, QFont.Bold))
        name_lbl.setStyleSheet("color: #1D1D1F; background: transparent; border: none;")
        lay.addWidget(name_lbl, 1)

        count_txt = "1 versiyon" if count == 1 else f"{count} versiyon"
        count_lbl = QLabel(count_txt)
        count_lbl.setFont(QFont("Segoe UI", 9))
        count_lbl.setStyleSheet("color: #86868B; background: transparent; border: none;")
        lay.addWidget(count_lbl)

        self.check_lbl = QLabel("")
        self.check_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.check_lbl.setStyleSheet("color: #0071E3; background: transparent; border: none;")
        self.check_lbl.setFixedWidth(18)
        lay.addWidget(self.check_lbl)

        self.set_selected(is_selected)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and callable(self._on_pick):
            self._on_pick(self.folder_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        self._selected = selected
        self.check_lbl.setText("✓" if selected else "")
        if selected:
            self.setStyleSheet("""
                QFrame { background: #EAF3FF; border: 1.5px solid #0071E3; border-radius: 10px; }
            """)
        else:
            self.setStyleSheet("""
                QFrame { background: #F8FAFC; border: 1.5px solid #E5E5EA; border-radius: 10px; }
                QFrame:hover { background: #F1F5F9; border-color: #CBD5E1; }
            """)


class SaveLocationDialog(QDialog):
    """Modal: pick an existing folder, create a new one, or leave it unfoldered ("Genel")."""

    def __init__(self, slug: str, parent=None):
        super().__init__(parent)
        self.slug = slug
        self.selected_folder_id = None  # None == "Genel" (no folder)
        self._rows = []

        self.setWindowTitle("Nereye Kaydedilsin?")
        self.setFixedSize(440, 520)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(15, 15, 15, 15)

        container = QWidget(self)
        container.setObjectName("saveLocCard")
        container.setStyleSheet("""
            #saveLocCard {
                background: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 20px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(0, 0, 0, 55))
        shadow.setOffset(0, 10)
        container.setGraphicsEffect(shadow)

        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(28, 24, 28, 22)
        c_lay.setSpacing(12)

        t_lbl = QLabel("Nereye Kaydedilsin?")
        t_lbl.setFont(QFont("Segoe UI", 13.5, QFont.Bold))
        t_lbl.setStyleSheet("color: #1D1D1F; background: transparent; border: none;")
        c_lay.addWidget(t_lbl)

        sub_lbl = QLabel("Bu versiyonu bir klasörde düzenleyebilir (örn. \"Yaz Çizelgesi\") ya da klasörsüz bırakabilirsiniz.")
        sub_lbl.setFont(QFont("Segoe UI", 9))
        sub_lbl.setStyleSheet("color: #86868B; background: transparent; border: none;")
        sub_lbl.setWordWrap(True)
        c_lay.addWidget(sub_lbl)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: #E5E5EA; border: none;")
        c_lay.addWidget(div)

        # Scrollable folder list
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 4, 0, 4)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch(1)

        self.scroll.setWidget(self.list_container)
        c_lay.addWidget(self.scroll, 1)

        # New-folder inline creator
        new_row = QHBoxLayout()
        new_row.setSpacing(8)
        self.new_folder_edit = QLineEdit()
        self.new_folder_edit.setPlaceholderText("Yeni klasör adı (Örn: Yaz Çizelgesi)...")
        self.new_folder_edit.setFixedHeight(36)
        self.new_folder_edit.setStyleSheet("""
            QLineEdit {
                background: #F8FAFC; border: 1.5px solid #CBD5E1; border-radius: 8px;
                padding: 4px 12px; font-size: 12px; color: #0F172A;
            }
            QLineEdit:focus { border: 1.5px solid #0071E3; background: #FFFFFF; }
        """)
        self.new_folder_edit.returnPressed.connect(self._create_folder)
        new_row.addWidget(self.new_folder_edit, 1)

        btn_new = QPushButton("+ Yeni Klasör")
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.setFixedHeight(36)
        btn_new.setStyleSheet("""
            QPushButton {
                background: #EEF2FF; color: #4F46E5; border: 1.5px dashed #6366F1;
                border-radius: 8px; padding: 4px 14px; font-weight: bold; font-size: 11.5px;
            }
            QPushButton:hover { background: #E0E7FF; }
        """)
        btn_new.clicked.connect(self._create_folder)
        new_row.addWidget(btn_new)
        c_lay.addLayout(new_row)

        self.warn_lbl = QLabel("")
        self.warn_lbl.setFont(QFont("Segoe UI", 8.5, QFont.Bold))
        self.warn_lbl.setStyleSheet("color: #DC2626; background: transparent; border: none;")
        self.warn_lbl.setVisible(False)
        c_lay.addWidget(self.warn_lbl)
        self.new_folder_edit.textEdited.connect(lambda _: self.warn_lbl.setVisible(False))

        # Bottom buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F2F2F7; color: #1D1D1F; border: 1px solid #E5E5EA;
                border-radius: 8px; padding: 6px 20px; font-weight: 500; font-size: 12px;
            }
            QPushButton:hover { background: #E5E5EA; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_ok = QPushButton("Kaydet")
        btn_ok.setFixedHeight(38)
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 6px 26px; font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background: #0062C4; }
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
    def choose(cls, parent, slug: str):
        """Shows the dialog. Returns (folder_id, cancelled: bool)."""
        dlg = cls(slug, parent=parent)
        result = dlg.exec()
        if result != QDialog.Accepted:
            return None, True
        return dlg.selected_folder_id, False
