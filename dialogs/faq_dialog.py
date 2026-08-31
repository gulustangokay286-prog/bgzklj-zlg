"""
dialogs/faq_dialog.py – Sıkça Sorulan Sorular ve Kullanım Rehberi (SSS / Help)
Apple HIG tasarım dili, zarif tipografi, hafif köşeli modern kartlar ve birleşik renk paleti.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, QLabel, 
    QPushButton, QLineEdit, QFrame, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor, QIcon
import bk_ui

CATEGORIES = [
    "Tümü", "Otomatik Planlama", "Ders & Sınıf", "Kısıtlamalar & Ayarlar", "Yazdırma & Bulut"
]

CATEGORY_DISPLAY = {
    "Tümü": "Tümü",
    "Otomatik Planlama": "Otomatik Planlama",
    "Ders & Sınıf": "Ders && Sınıf",
    "Kısıtlamalar & Ayarlar": "Kısıtlamalar && Ayarlar",
    "Yazdırma & Bulut": "Yazdırma && Bulut",
}

FAQ_ITEMS = [
    {
        "cat": "Otomatik Planlama",
        "q": "Manuel eklediğim dersler otomatik planlama sırasında silinir mi?",
        "a": "Hayır. Çizelgeye elle yerleştirdiğiniz veya kilitlediğiniz tüm dersler akıllı planlama motoru tarafından başlangıç durumu olarak korunur. Sistem asla manuel derslerin üzerine ders yazmaz ve yerlerini değiştirmez; sadece kalan boş saatleri doldurur."
    },
    {
        "cat": "Otomatik Planlama",
        "q": "Otomatik planlama nasıl %100 doluluk sağlar?",
        "a": "Akıllı planlama motoru, kalan boş saatleri ve tanımlı ders yüklerini eşleştirir. Ders bloklarını (2+2, 2+1 vb.) çakışmasız olarak yerleştirir. Çakışma durumunda veya sığmayan tek saatlik boşluklarda blokları otomatik bölerek tüm haftayı eksiksiz tamamlar."
    },
    {
        "cat": "Ders & Sınıf",
        "q": "Ders kısaltmaları ve otomatik kod üretimi nasıl çalışır?",
        "a": "Ders adını girdiğinizde sistem otomatik olarak standart Türkçe kısaltma üretir (Örn: Biyoloji -> BİYO, Matematik 1 -> MAT 1, Fizik 2 -> FİZ 2, Rehberlik -> REHBERLİK). Numaralar harflerden her zaman bir boşlukla ayrı tutulur."
    },
    {
        "cat": "Kısıtlamalar & Ayarlar",
        "q": "İki zor dersin aynı gün peş peşe gelmesi nasıl engellenir?",
        "a": "Gelişmiş Kısıtlamalar ekranından 'İki zor ders (Matematik, Fizik, Kimya vb.) aynı gün art arda gelmesin' kuralı aktifleştirildiğinde, otomatik planlama motoru zor dersler arasına pedagojik dinlenme aralıkları veya sözel dersler yerleştirir."
    },
    {
        "cat": "Kısıtlamalar & Ayarlar",
        "q": "Günlük ders saatini 8 saatin üzerine nasıl çıkarabilirim?",
        "a": "Ana Menü -> Temel Bilgiler (Ayarlar) ekranından 'Çizelge Zamanı / Günlük Ders Saati' açılır kutusundan istediğiniz saat sayısını (8, 9, 10, 11, 12...16) seçebilirsiniz. Çizelge ve yazdırma çıktıları dinamik olarak ölçeklenir."
    },
    {
        "cat": "Ders & Sınıf",
        "q": "Bir öğretmene birden fazla ders ve farklı sınıflar nasıl atanır?",
        "a": "Öğretmenler ekranında öğretmene çift tıklayıp 'Bu Öğretmene Ders Ata' butonuna basın. Bir ders seçtiğinizde aşağıda otomatik yeni ders satırı açılır. Her dersin yanındaki 'Sınıf(lar) Ata...' butonu ile o ders için hangi sınıflara gireceğini bağımsız seçebilirsiniz."
    },
    {
        "cat": "Ders & Sınıf",
        "q": "Birleşik sınıflar (ortak ders) nedir ve nasıl tanımlanır?",
        "a": "Bir öğretmenin aynı saatte birden fazla sınıfa ortak derse girmesidir (Örn: 9A + 9B Beden Eğitimi). Sınıf seçimi ekranında 'Birleşik Sınıflar' butonuna tıklayarak en az 2 sınıf seçebilir, çakışma durumunda 'Çakışmayı Yoksay ve Birleştir' seçeneğini kullanabilirsiniz."
    },
    {
        "cat": "Ders & Sınıf",
        "q": "Ders renk paletini hızlıca nasıl değiştirebilirim?",
        "a": "Alt yerleşmemiş dersler panelindeki herhangi bir ders kartına sağ tıklayıp 'Rengini Ayarla (Renk Paleti)...' seçeneğini tıklayarak ders rengini anında değiştirebilirsiniz. Değişiklik anında kaydedilir."
    },
    {
        "cat": "Yazdırma & Bulut",
        "q": "Baskı ve PDF çıktıları aSc birebir formatında mı alınır?",
        "a": "Evet. Sınıfın Dersleri dikey liste formatı, tam sayfa renkli haftalık grid ve kağıt tasarruflu mini grid raporları aSc standartlarında yüksek çözünürlükte yazdırılabilir veya PDF olarak kaydedilebilir."
    },
    {
        "cat": "Yazdırma & Bulut",
        "q": "İnternet hesabı ve bulut senkronizasyonu nasıl kullanılır?",
        "a": "Ana Menüdeki 'İnternet Hesabı' seçeneğine tıklayarak chenki.net bulut sunucusu ile programınızı güvenle senkronize edebilir, kurumlar arası anında geçiş yapabilirsiniz."
    }
]


class AppleAccordionItem(QFrame):
    """Modern Apple HIG tekil akordeon soru-cevap kartı."""

    def __init__(self, cat: str, q: str, a: str, parent=None):
        super().__init__(parent)
        self.cat = cat
        self.q = q
        self.a = a
        self.is_expanded = False
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("appleFaqCard")
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)

        # Header Area
        header_box = QHBoxLayout()
        header_box.setSpacing(12)

        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(2)

        self.cat_lbl = QLabel(self.cat.upper())
        self.cat_lbl.setFont(bk_ui.font(7.5, QFont.Bold))
        self.cat_lbl.setStyleSheet(f"color: {bk_ui.INK_SOFT}; background: transparent; border: none; letter-spacing: 0.4px;")
        text_vbox.addWidget(self.cat_lbl)

        self.q_lbl = QLabel(self.q)
        self.q_lbl.setFont(bk_ui.font(9.6, QFont.DemiBold))
        self.q_lbl.setStyleSheet(f"color: {bk_ui.INK}; background: transparent; border: none;")
        self.q_lbl.setWordWrap(True)
        text_vbox.addWidget(self.q_lbl)

        header_box.addLayout(text_vbox, 1)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(14, 14)
        self.icon_lbl.setStyleSheet("background: transparent; border: none;")
        self.icon_lbl.setPixmap(bk_ui.chevron_glyph(bk_ui.INK_SOFT, 13, "right"))
        header_box.addWidget(self.icon_lbl, 0, Qt.AlignVCenter)

        lay.addLayout(header_box)

        # Answer Body
        self.a_box = QWidget()
        self.a_box.setStyleSheet(f"background: {bk_ui.SURFACE_SUNK}; border-radius: 8px; border: 1px solid {bk_ui.HAIRLINE};")
        a_lay = QVBoxLayout(self.a_box)
        a_lay.setContentsMargins(14, 10, 14, 10)

        self.a_lbl = QLabel(self.a)
        self.a_lbl.setFont(bk_ui.font(9.0))
        self.a_lbl.setStyleSheet("color: #334155; line-height: 1.5; border: none; background: transparent;")
        self.a_lbl.setWordWrap(True)
        a_lay.addWidget(self.a_lbl)

        self.a_box.hide()
        lay.addWidget(self.a_box)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle()
        super().mousePressEvent(event)

    def _update_style(self):
        if self.is_expanded:
            self.setStyleSheet(f"""
                #appleFaqCard {{
                    background: #FFFFFF;
                    border: 1.5px solid {bk_ui.HAIRLINE_STRONG};
                    border-radius: 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                #appleFaqCard {{
                    background: #FFFFFF;
                    border: 1px solid {bk_ui.HAIRLINE};
                    border-radius: 10px;
                }}
                #appleFaqCard:hover {{
                    border-color: {bk_ui.HAIRLINE_STRONG};
                    background: #FAFAFC;
                }}
            """)

    def toggle(self):
        self.is_expanded = not self.is_expanded
        self.a_box.setVisible(self.is_expanded)
        self.icon_lbl.setPixmap(
            bk_ui.chevron_glyph(bk_ui.INK if self.is_expanded else bk_ui.INK_SOFT, 13,
                                "down" if self.is_expanded else "right")
        )
        self._update_style()


class FAQDialog(bk_ui.HeroSheetDialog):
    """Help & FAQ on the program's unified Apple HIG sheet."""

    def __init__(self, parent=None):
        self._cards = []
        self._current_cat = "Tümü"
        super().__init__(parent, width=760, height=600,
                         title="Sıkça Sorulan Sorular",
                         subtitle="Planlama algoritması, kısıtlar, kısaltmalar ve pratik kullanım rehberi.")
        self.setWindowTitle("Sıkça Sorulan Sorular")
        self._build_ui()

    def _build_ui(self):
        c_lay = self.card_layout
        c_lay.setContentsMargins(24, 20, 24, 18)
        c_lay.setSpacing(10)

        # Search Bar
        self.search_input = bk_ui.Field(placeholder="Soru veya konu ara... (Örn: planlama, manuel ders, çakışma, saat)", height=38, font_px=13)
        self.search_input.textChanged.connect(self._filter_items)
        c_lay.addWidget(self.search_input)

        # Category Chips Row (Slightly rounded rectangular chips: 7px)
        chips_box = QHBoxLayout()
        chips_box.setSpacing(6)
        self.chip_group = QButtonGroup(self)
        self.chip_buttons = []

        for i, cat_name in enumerate(CATEGORIES):
            btn = QPushButton(CATEGORY_DISPLAY.get(cat_name, cat_name))
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(28)
            if i == 0:
                btn.setChecked(True)
            self._style_chip(btn, btn.isChecked())
            btn.clicked.connect(lambda chk=False, b=btn, c=cat_name: self._on_category_changed(b, c))
            self.chip_group.addButton(btn, i)
            self.chip_buttons.append(btn)
            chips_box.addWidget(btn)

        chips_box.addStretch(1)
        c_lay.addLayout(chips_box)

        # Scroll Area for FAQ Items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 6px; margin: 0; }
            QScrollBar::handle:vertical { background: #D5D5DB; border-radius: 3px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: #A0A0AA; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        self.items_layout = QVBoxLayout(scroll_widget)
        self.items_layout.setContentsMargins(0, 0, 4, 0)
        self.items_layout.setSpacing(8)

        for item_data in FAQ_ITEMS:
            item = AppleAccordionItem(item_data["cat"], item_data["q"], item_data["a"])
            self._cards.append((item, item_data["cat"], item_data["q"].lower(), item_data["a"].lower()))
            self.items_layout.addWidget(item)

        # Open first card by default
        if self._cards:
            self._cards[0][0].toggle()

        self.items_layout.addStretch(1)
        scroll.setWidget(scroll_widget)
        c_lay.addWidget(scroll, 1)

        # Footer Separator & Row
        c_lay.addWidget(bk_ui.hairline())

        f_box = QHBoxLayout()
        f_box.setContentsMargins(0, 2, 0, 0)
        f_box.setSpacing(10)

        btn_web = bk_ui.secondary_button("Destek Portalı", height=34)
        btn_web.setFont(bk_ui.font(8.8, QFont.Medium))
        btn_web.clicked.connect(lambda: __import__('webbrowser').open("https://chenki.net/"))
        f_box.addWidget(btn_web)

        f_box.addStretch(1)

        btn_close = bk_ui.primary_button("Kapat", height=34)
        btn_close.setFont(bk_ui.font(8.8, QFont.DemiBold))
        btn_close.clicked.connect(self.accept)
        f_box.addWidget(btn_close)

        c_lay.addLayout(f_box)

    def _style_chip(self, btn: QPushButton, is_active: bool):
        if is_active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 12px;
                    font-weight: 600;
                    background: {bk_ui.BRAND};
                    color: #FFFFFF;
                    border: none;
                    border-radius: 7px;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    background: {bk_ui.BRAND_DARK};
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 12px;
                    font-weight: 500;
                    background: #F1F3F5;
                    color: {bk_ui.INK_BODY};
                    border: 1px solid {bk_ui.HAIRLINE};
                    border-radius: 7px;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    background: #E5E7EB;
                    border-color: {bk_ui.HAIRLINE_STRONG};
                }}
            """)

    def _on_category_changed(self, clicked_btn: QPushButton, cat_name: str):
        self._current_cat = cat_name
        for b in self.chip_buttons:
            self._style_chip(b, b == clicked_btn)
        self._filter_items(self.search_input.text())

    def _filter_items(self, query: str):
        q = (query or "").strip().lower()
        for item, cat, item_q, item_a in self._cards:
            cat_match = (self._current_cat == "Tümü") or (self._current_cat == cat)
            text_match = (not q) or (q in item_q) or (q in item_a)
            item.setVisible(cat_match and text_match)
