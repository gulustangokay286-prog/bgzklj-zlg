from __future__ import annotations

"""
dialogs/new_schedule_dialog.py – Apple HIG Sleek Dual-Mode Schedule Creation Dialog.

Lists distinct DATA POOLS (Veri Havuzları) on the left panel (initially 1 primary data pool,
plus any additional pools created by the user), allowing the user to select which data to
continue from.
On the right panel, allows creating a completely independent, clean-slate empty data pool
with a custom data name, which is then registered and also appears on the left panel.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QWidget, QScrollArea, QRadioButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QIcon

import bk_ui
import version_store


class DataPoolCard(QFrame):
    """Clickable row representing an existing data pool."""
    clicked = Signal(str, str)  # pool_id, pool_name
    delete_requested = Signal(str, str)  # pool_id, pool_name

    def __init__(self, pool_info: dict, is_selected: bool = False, parent=None):
        super().__init__(parent)
        self.pool_info = pool_info
        self.pool_id = pool_info.get("id", "")
        self.pool_name = pool_info.get("name", "")
        self._is_selected = is_selected
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Radio indicator
        self.radio = QRadioButton()
        self.radio.setChecked(is_selected)
        self.radio.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.radio)

        # Text container
        vbox = QVBoxLayout()
        vbox.setSpacing(2)
        vbox.setContentsMargins(0, 0, 0, 0)

        lbl_name = QLabel(self.pool_name)
        lbl_name.setFont(bk_ui.font(9.8, QFont.DemiBold))
        lbl_name.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        vbox.addWidget(lbl_name)

        t_cnt = pool_info.get("teachers_count", 0)
        c_cnt = pool_info.get("classes_count", 0)
        is_def = pool_info.get("is_default", False)
        
        info_parts = []
        if is_def:
            info_parts.append("Ana Veri")
        if t_cnt > 0 or c_cnt > 0:
            info_parts.append(f"{t_cnt} Öğretmen")
            info_parts.append(f"{c_cnt} Sınıf")
        else:
            info_parts.append("Boş Veri Havuzu")

        lbl_sub = QLabel(" • ".join(info_parts))
        lbl_sub.setFont(bk_ui.font(8.2))
        lbl_sub.setStyleSheet("color: #64748B; background: transparent; border: none;")
        vbox.addWidget(lbl_sub)

        layout.addLayout(vbox, 1)

        # Delete button for non-default pools
        if not is_def:
            self.btn_del = QPushButton()
            self.btn_del.setFixedSize(28, 28)
            self.btn_del.setCursor(Qt.PointingHandCursor)
            self.btn_del.setIcon(QIcon(bk_ui.trash_glyph(bk_ui.DANGER, 14)))
            self.btn_del.setIconSize(bk_ui.QSize(14, 14) if hasattr(bk_ui, "QSize") else self.btn_del.sizeHint())
            self.btn_del.setToolTip("Bu veriyi sil")
            self.btn_del.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: #FEE2E2;
                }
            """)
            self.btn_del.clicked.connect(lambda: self.delete_requested.emit(self.pool_id, self.pool_name))
            layout.addWidget(self.btn_del, 0, Qt.AlignVCenter)

        self._update_style()

    def set_selected(self, sel: bool):
        self._is_selected = sel
        self.radio.setChecked(sel)
        self._update_style()

    def _update_style(self):
        if self._is_selected:
            self.setStyleSheet("""
                DataPoolCard {
                    background: #F0F7FF;
                    border: 1.5px solid #0071E3;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                DataPoolCard {
                    background: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }
                DataPoolCard:hover {
                    background: #F8FAFC;
                    border-color: #CBD5E1;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.pool_id, self.pool_name)
        super().mousePressEvent(event)


class AppleNewScheduleDialog(bk_ui.HeroSheetDialog):
    """
    Sleek, minimalist Apple HIG Sheet dialog for starting a new schedule.
    - Left Panel: List of available Data Pools (Data Names).
    - Right Panel: Creation of a new, clean-slate independent Data Pool.
    """
    def __init__(self, slug: str, parent=None):
        super().__init__(parent=parent, width=720, height=450,
                         title="Yeni Çizelge",
                         subtitle="Mevcut bir veriden devam edebilir veya sıfırdan yeni bir veri havuzu açabilirsiniz.")
        self.slug = slug
        self.selected_mode = None  # "current_data" or "empty_pool"
        self.selected_pool_id = None
        self.selected_pool_name = ""
        self.selected_schedule_name = ""

        self.card_layout.setContentsMargins(24, 18, 24, 18)
        self.card_layout.setSpacing(12)

        self._build_content()

    def _build_content(self):
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(18)

        # ═══════════════════════════════════════════════════════════════
        # LEFT PANEL: Existing Data Pools
        # ═══════════════════════════════════════════════════════════════
        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        left_hdr = QHBoxLayout()
        lbl_left_title = QLabel("Mevcut Veri")
        lbl_left_title.setFont(bk_ui.font(10.2, QFont.Bold))
        lbl_left_title.setStyleSheet("color: #0F172A; border: none; background: transparent;")
        left_hdr.addWidget(lbl_left_title)

        chip_keep = bk_ui.Chip("Veri Havuzları", "blue")
        left_hdr.addWidget(chip_keep, 0, Qt.AlignVCenter)
        left_hdr.addStretch(1)
        left_col.addLayout(left_hdr)

        lbl_left_sub = QLabel("Devam etmek istediğiniz veriyi seçin:")
        lbl_left_sub.setFont(bk_ui.font(8.6))
        lbl_left_sub.setStyleSheet("color: #64748B; border: none; background: transparent;")
        left_col.addWidget(lbl_left_sub)

        # Scrollable list for Data Pools (only distinct data pools, NOT individual versions!)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                background: #FAFAFC;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 2px 2px 2px 0;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                border-radius: 3px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94A3B8;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent; border: none;")
        self.pool_cards_layout = QVBoxLayout(scroll_content)
        self.pool_cards_layout.setContentsMargins(6, 6, 6, 6)
        self.pool_cards_layout.setSpacing(6)

        # Query distinct data pools
        pools = version_store.list_data_pools(self.slug)
        self.card_widgets = []
        pools = version_store.list_data_pools(self.slug)
        default_pool = pools[0] if pools else {"id": "default", "name": "Ana Veri"}
        self.selected_pool_id = default_pool["id"]
        self.selected_pool_name = default_pool["name"]

        scroll.setWidget(scroll_content)
        left_col.addWidget(scroll, 1)

        # Left Input: Schedule Name / Note
        lbl_sch_name = QLabel("Yeni Çizelge Adı / Notu:")
        lbl_sch_name.setFont(bk_ui.font(8.6, QFont.DemiBold))
        lbl_sch_name.setStyleSheet("color: #334155; border: none; background: transparent;")
        left_col.addWidget(lbl_sch_name)

        self.txt_left_name = QLineEdit()
        self.txt_left_name.setFixedHeight(32)
        self.txt_left_name.setText(f"{self.selected_pool_name} Planı")
        self.txt_left_name.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 7px;
                padding: 0 10px;
                font-size: 12px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border-color: #0071E3;
            }
        """)
        left_col.addWidget(self.txt_left_name)

        # Left Action Button
        btn_left = bk_ui.primary_button("Bu Veriyle Başla", height=34)
        btn_left.clicked.connect(self._on_confirm_current_data)
        left_col.addWidget(btn_left)

        columns_layout.addLayout(left_col, 5)

        # ── Vertical Divider
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Plain)
        sep.setStyleSheet("color: #E2E8F0; background-color: #E2E8F0; border: none; width: 1px;")
        columns_layout.addWidget(sep)

        # ═══════════════════════════════════════════════════════════════
        # RIGHT PANEL: New Empty Data Pool
        # ═══════════════════════════════════════════════════════════════
        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        right_hdr = QHBoxLayout()
        lbl_right_title = QLabel("Yeni Boş Veri")
        lbl_right_title.setFont(bk_ui.font(10.2, QFont.Bold))
        lbl_right_title.setStyleSheet("color: #0F172A; border: none; background: transparent;")
        right_hdr.addWidget(lbl_right_title)

        chip_empty = bk_ui.Chip("Sıfır Havuz", "neutral")
        right_hdr.addWidget(chip_empty, 0, Qt.AlignVCenter)
        right_hdr.addStretch(1)
        right_col.addLayout(right_hdr)

        lbl_right_sub = QLabel("Bağımsız, temiz bir veri havuzu oluşturun:")
        lbl_right_sub.setFont(bk_ui.font(8.6))
        lbl_right_sub.setStyleSheet("color: #64748B; border: none; background: transparent;")
        right_col.addWidget(lbl_right_sub)

        # Minimalist visual card
        empty_card = QFrame()
        empty_card.setStyleSheet("""
            QFrame {
                background: #F8FAFC;
                border: 1.5px dashed #CBD5E1;
                border-radius: 8px;
            }
        """)
        empty_card_lay = QVBoxLayout(empty_card)
        empty_card_lay.setContentsMargins(14, 14, 14, 14)
        empty_card_lay.setSpacing(8)
        empty_card_lay.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setPixmap(bk_ui.building_glyph("#0071E3", 30))
        empty_card_lay.addWidget(icon_lbl)

        txt_info = QLabel("Mevcut kuruma ait hiçbir tanım kopyalanmaz. Tamamen sıfır, bağımsız bir veri havuzu açılır.")
        txt_info.setFont(bk_ui.font(8.4))
        txt_info.setStyleSheet("color: #64748B; border: none; background: transparent;")
        txt_info.setAlignment(Qt.AlignCenter)
        txt_info.setWordWrap(True)
        empty_card_lay.addWidget(txt_info)

        right_col.addWidget(empty_card, 1)

        # Right Input: New Data Pool Name
        lbl_new_pool = QLabel("Yeni Veri Adı:")
        lbl_new_pool.setFont(bk_ui.font(8.6, QFont.DemiBold))
        lbl_new_pool.setStyleSheet("color: #334155; border: none; background: transparent;")
        right_col.addWidget(lbl_new_pool)

        self.txt_right_name = QLineEdit()
        self.txt_right_name.setFixedHeight(32)
        self.txt_right_name.setPlaceholderText("Örn: Fen Lisesi, Yeni Şube...")
        self.txt_right_name.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 7px;
                padding: 0 10px;
                font-size: 12px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border-color: #0071E3;
            }
        """)
        right_col.addWidget(self.txt_right_name)

        # Right Action Button
        btn_right = bk_ui.secondary_button("Boş Veri Oluştur", height=34)
        btn_right.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #0F172A;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #F1F5F9;
                border-color: #94A3B8;
            }
        """)
        btn_right.clicked.connect(self._on_confirm_empty_pool)
        right_col.addWidget(btn_right)

        columns_layout.addLayout(right_col, 4)
        self.card_layout.addLayout(columns_layout, 1)

        # ── Bottom Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch(1)

        btn_cancel = bk_ui.secondary_button("Vazgeç", height=30)
        btn_cancel.clicked.connect(self.reject)
        bottom_bar.addWidget(btn_cancel)

        self.card_layout.addLayout(bottom_bar)
        self._reload_pools()

    def _reload_pools(self):
        while self.pool_cards_layout.count() > 0:
            item = self.pool_cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.card_widgets = []
        pools = version_store.list_data_pools(self.slug)

        pool_ids = [p["id"] for p in pools]
        if self.selected_pool_id not in pool_ids:
            default_p = pools[0] if pools else {"id": "default", "name": "Ana Veri"}
            self.selected_pool_id = default_p["id"]
            self.selected_pool_name = default_p["name"]
            if hasattr(self, "txt_left_name"):
                self.txt_left_name.setText(f"{self.selected_pool_name} Planı")

        for p in pools:
            is_sel = (p["id"] == self.selected_pool_id)
            card = DataPoolCard(p, is_selected=is_sel)
            card.clicked.connect(self._on_pool_card_clicked)
            card.delete_requested.connect(self._on_delete_pool)
            self.pool_cards_layout.addWidget(card)
            self.card_widgets.append(card)

        self.pool_cards_layout.addStretch(1)

    def _on_delete_pool(self, pool_id: str, pool_name: str):
        if pool_id == "default":
            from bk_ui import show_apple_info
            show_apple_info(self, "Ana Veri Silinemez", "Kurumun ana veri havuzu silinemez. Yalnızca sonradan eklenen veri havuzlarını silebilirsiniz.", is_success=False)
            return

        from home_dashboard import AppleConfirmDialog
        from save_dialog import run_apple_save_sequence
        dlg = AppleConfirmDialog(
            title="Veri Havuzunu Sil",
            message=f"\"{pool_name}\" veri havuzu ve bu havuza ait tüm çizelgeler kalıcı olarak silinecektir. Devam etmek istiyor musunuz?",
            confirm_text="Veriyi Sil",
            cancel_text="Vazgeç",
            is_destructive=True,
            parent=self
        )
        if dlg.exec() == QDialog.Accepted:
            run_apple_save_sequence(self, duration_seconds=0.25, title="Veri Siliniyor", message=f"\"{pool_name}\" kaldırılıyor...")
            version_store.delete_data_pool(self.slug, pool_id)
            self._reload_pools()

    def _on_pool_card_clicked(self, pool_id: str, pool_name: str):
        self.selected_pool_id = pool_id
        self.selected_pool_name = pool_name
        for card in self.card_widgets:
            card.set_selected(card.pool_id == pool_id)
        self.txt_left_name.setText(f"{pool_name} Planı")

    def _on_confirm_current_data(self):
        self.selected_mode = "current_data"
        name = self.txt_left_name.text().strip()
        self.selected_schedule_name = name if name else f"{self.selected_pool_name} Planı"
        self.accept()

    def _on_confirm_empty_pool(self):
        name = self.txt_right_name.text().strip()
        if not name:
            name = "Yeni Veri Havuzu"
        self.selected_mode = "empty_pool"
        self.selected_pool_name = name
        self.selected_schedule_name = name
        self.accept()

    def get_selection(self) -> tuple[str, str, str | None, str | None]:
        """Returns (mode, schedule_name, pool_id, pool_name)."""
        return self.selected_mode, self.selected_schedule_name, self.selected_pool_id, self.selected_pool_name
