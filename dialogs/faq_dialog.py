"""
dialogs/faq_dialog.py – Sıkça Sorulan Sorular ve Kullanım Rehberi (SSS / Help)
Apple Human Interface Guidelines uyumlu, temiz ve modern yardım penceresi.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, QLabel, 
    QPushButton, QLineEdit, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"

FAQ_DATA = [
    ("Ders Kısaltmaları ve Otomatik Kod Üretimi nasıl çalışır?",
     "Ders adını girdiğinizde sistem otomatik olarak standart Türkçe kısaltma üretir (Örn: Biyoloji -> BİYO, Matematik 1 -> MAT 1, Fizik 2 -> FİZ 2, Rehberlik -> REHBERLİK). Numaralar harflerden her zaman bir boşlukla ayrı tutulur."),
    
    ("Manuel Eklediğim Dersler Otomatik Planlama sırasında silinir mi?",
     "HAYIR. Çizelgeye elle yerleştirdiğiniz veya kilitlediğiniz tüm dersler A* Search algoritması tarafından başlangıç durumu olarak korunur. Algoritma asla manuel derslerin üzerine ders yazmaz ve yerlerini değiştirmez; sadece boş slotları doldurur."),
    
    ("Otomatik Planlama (A* Search) nasıl %100 doluluk sağlar?",
     "A* Search motoru, kalan boş saatleri ve tanımlı ders yüklerini eşleştirir. Ders bloklarını (2+2, 2+1 vb.) çakışmasız olarak yerleştirir. Çakışma durumunda veya sığmayan tek saatlik boşluklarda blokları otomatik bölerek tüm haftayı eksiksiz tamamlar."),
    
    ("İki Zor Dersin Peş Peşe Gelmesi nasıl engellenir?",
     "Gelişmiş Kısıtlamalar ekranından 'İki zor ders (Matematik, Fizik, Kimya vb.) aynı gün art arda gelmesin' kuralı aktifleştirildiğinde, A* algoritması zor dersler arasına pedagojik dinlenme aralıkları veya sözel dersler yerleştirir."),
    
    ("Günlük Ders Saatini 8 saatin üzerine nasıl çıkarabilirim?",
     "Ana Menü -> Temel Bilgiler (Ayarlar) ekranından 'Çizelge Zamanı / Günlük Ders Saati' açılır kutusundan istediğiniz saat sayısını (8, 9, 10, 11, 12...16) seçebilirsiniz. Hem ana ekran çizelgesi hem de Yazdır/Önizleme çıktıları dinamik olarak ölçeklenecektir."),
    
    ("Ders Renk Paletini Hızlıca Nasıl Değiştirebilirim?",
     "Alt yerleşmemiş dersler panelindeki herhangi bir ders kartına sağ tıklayıp 'Rengini Ayarla (Renk Paleti)...' seçeneğini tıklayarak ders rengini anında değiştirebilirsiniz. Değişiklik çizelgeye ve veritabanına anında kaydedilir."),
    
    ("Bir Öğretmene Birden Fazla Ders ve Farklı Sınıflar Nasıl Atanır?",
     "Öğretmenler ekranında öğretmene çift tıklayıp 'Bu Öğretmene Ders Ata' butonuna basın. Bir ders seçtiğinizde aşağıda otomatik yeni ders satırı açılır. Her dersin yanındaki 'Sınıf(lar) Ata...' butonu ile o ders için hangi sınıflara gireceğini bağımsız seçebilirsiniz."),
    
    ("Birleşik Sınıflar (Ortak Ders) Nedir ve Nasıl Tanımlanır?",
     "Bir öğretmenin aynı saatte birden fazla sınıfa ortak derse girmesidir (Örn: 9A + 9B Beden Eğitimi). Sınıf seçimi ekranında 'Birleşik Sınıflar' butonuna tıklayarak en az 2 sınıf seçebilir, çakışma durumunda 'Çakışmayı Yoksay ve Birleştir' seçeneğini kullanabilirsiniz."),
    
    ("Özel Alanlar (Custom Fields) Nedir?",
     "Öğretmen, Sınıf, Ders ve Derslik kartlarına aSc standartlarında telefon, e-posta, sicil no, branş ve özel notlar gibi sınırsız meta veri eklemenizi sağlayan responsive bir modüldür."),
    
    ("Baskı ve PDF Çıktıları aSc Birebir Formatında mı Alınır?",
     "Evet. Sınıfın Dersleri dikey liste formatı, tam sayfa renkli haftalık grid ve kağıt tasarruflu mini grid raporları aSc standartlarında yüksek çözünürlükte yazdırılabilir veya PDF olarak kaydedilebilir."),
    
    ("İnternet Hesabı ve Bulut Senkronizasyonu nasıl kullanılır?",
     "Ana Menüdeki 'İnternet Hesabı' seçeneğine tıklayarak chenki.net bulut sunucusu ile programınızı güvenle senkronize edebilirsiniz.")
]


class FAQDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yardım ve Sıkça Sorulan Sorular (SSS)")
        self.resize(780, 600)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #F8FAFC;
                font-family: {FONT_FAMILY};
            }}
            QLineEdit {{
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 13px;
                background: #FFFFFF;
                color: #0F172A;
            }}
            QLineEdit:focus {{
                border: 1.5px solid #0071E3;
            }}
        """)
        self._cards = []
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        
        # Header Card
        h_card = QFrame()
        h_card.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px;")
        h_lay = QVBoxLayout(h_card)
        h_lay.setSpacing(4)
        
        lbl_title = QLabel("Ders Planlama ve Akıllı Yerleşim Rehberi")
        lbl_title.setFont(QFont(FONT_FAMILY, 14, QFont.Bold))
        lbl_title.setStyleSheet("color: #0F172A; border: none;")
        h_lay.addWidget(lbl_title)
        
        lbl_sub = QLabel("Programın tüm özellikleri, A* Search algoritması, kısıtlamalar ve kullanım ipuçları.")
        lbl_sub.setFont(QFont(FONT_FAMILY, 9.5))
        lbl_sub.setStyleSheet("color: #64748B; border: none;")
        h_lay.addWidget(lbl_sub)
        layout.addWidget(h_card)
        
        # Real-time search bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Soru veya konu ara (Örn: A* Search, manuel ders, kısaltma, saat)...")
        self.txt_search.textChanged.connect(self._filter_faqs)
        layout.addWidget(self.txt_search)
        
        # Scroll area for Q&A cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: transparent; width: 6px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1; border-radius: 3px; min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #94A3B8; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.c_lay = QVBoxLayout(container)
        self.c_lay.setContentsMargins(0, 0, 4, 0)
        self.c_lay.setSpacing(10)
        
        for q, a in FAQ_DATA:
            card = QFrame()
            card.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px; }")
            card_lay = QVBoxLayout(card)
            card_lay.setSpacing(8)
            
            q_lbl = QLabel(q)
            q_lbl.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
            q_lbl.setStyleSheet("color: #0F172A; border: none; background: transparent;")
            q_lbl.setWordWrap(True)
            
            a_lbl = QLabel(a)
            a_lbl.setFont(QFont(FONT_FAMILY, 9.5))
            a_lbl.setStyleSheet("color: #334155; line-height: 1.4; border: none; background: #F8FAFC; padding: 10px 12px; border-radius: 8px; border-left: 3px solid #0071E3;")
            a_lbl.setWordWrap(True)
            
            card_lay.addWidget(q_lbl)
            card_lay.addWidget(a_lbl)
            
            self._cards.append((card, q.lower(), a.lower()))
            self.c_lay.addWidget(card)
            
        self.c_lay.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        
        # Bottom Buttons
        b_lay = QHBoxLayout()
        btn_web = QPushButton("chenki.net Destek Portalı")
        btn_web.setFont(QFont(FONT_FAMILY, 9, QFont.DemiBold))
        btn_web.setFixedHeight(34)
        btn_web.setCursor(Qt.PointingHandCursor)
        btn_web.setStyleSheet("""
            QPushButton {
                background: #EFF6FF; color: #0071E3; border: 1px solid #BFDBFE;
                border-radius: 17px; padding: 0 18px; font-weight: 600;
            }
            QPushButton:hover { background: #DBEAFE; }
        """)
        btn_web.clicked.connect(lambda: __import__('webbrowser').open("https://chenki.net/"))
        b_lay.addWidget(btn_web)
        
        b_lay.addStretch(1)
        
        btn_close = QPushButton("Kapat")
        btn_close.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        btn_close.setFixedHeight(34)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 17px; padding: 0 24px; font-weight: 600;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        btn_close.clicked.connect(self.accept)
        b_lay.addWidget(btn_close)
        
        layout.addLayout(b_lay)

    def _filter_faqs(self, text):
        query = text.strip().lower()
        for card, q_text, a_text in self._cards:
            if not query or query in q_text or query in a_text:
                card.setVisible(True)
            else:
                card.setVisible(False)
