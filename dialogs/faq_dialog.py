"""
dialogs/faq_dialog.py – Sıkça Sorulan Sorular ve Yanıtlar (SSS / FAQ)
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, QLabel, 
    QPushButton, QLineEdit, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

FAQ_DATA = [
    ("Ders Kısaltmaları ve Otomatik Kod Üretimi nasıl çalışır?",
     "Ders adını girdiğinizde sistem otomatik olarak standart Türkçe kısaltma üretir (Örn: Biyoloji ➔ BİYO, Matematik 1 ➔ MAT 1, Fizik 2 ➔ FİZ 2, Rehberlik ➔ REHBERLİK). Numaralar harflerden her zaman bir boşlukla ayrı durur."),
    
    ("Manuel Eklediğim Dersler Otomatik Planlama sırasında silinir mi?",
     "HAYIR! Çizelgeye elle yerleştirdiğiniz veya kilitlediğiniz tüm dersler A* Search algoritması tarafından başlangıç durumu olarak kilitlenir. Algoritma asla manuel derslerin üzerine ders yazmaz ve onları yerinden oynatmaz; sadece boş slotları doldurur."),
    
    ("Otomatik Planlama (A* Search) nasıl %100 doluluk sağlar?",
     "A* Search motoru, kalan boş saatleri ve tanımlı ders yüklerini eşleştirir. Ders bloklarını (2+2, 2+1 vb.) çakışmasız olarak yerleştirir. Çakışma durumunda veya sığmayan tek saatlik boşluklarda blokları otomatik bölerek tüm haftayı %100 eksiksiz tamamlar."),
    
    ("İki Zor Dersin Peş Peşe Gelmesi nasıl engellenir?",
     "Gelişmiş Kısıtlamalar ekranından 'İki zor ders (Matematik, Fizik, Kimya vb.) aynı gün art arda gelmesin' kuralı aktifleştirildiğinde, A* algoritması zor dersler arasına pedagojik dinlenme aralıkları veya sözel dersler yerleştirir."),
    
    ("Günlük Ders Saatini 8 saatin üzerine (Örn: 10, 12 saate) nasıl çıkarabilirim?",
     "Ana Menü ➔ Temel Bilgiler (Ayarlar) ekranından 'Çizelge Zamanı / Günlük Ders Saati' açılır kutusundan istediğiniz saat sayısını (8, 9, 10, 11, 12..16) seçebilirsiniz. Hem ana ekran çizelgesi hem de Yazdır/Önizleme çıktıları dinamik olarak ölçeklenecektir."),
    
    ("Ders Renk Paletini Hızlıca Nasıl Değiştirebilirim?",
     "Alt yerleşmemiş dersler panelindeki herhangi bir ders kartına SAĞ TIKLAYIP '🎨 Rengini Ayarla (Renk Paleti)...' seçeneğini tıklayarak ders rengini anında değiştirebilirsiniz. Değişiklik çizelgeye ve veritabanına anında kaydedilir."),
    
    ("Bir Öğretmene Birden Fazla Ders ve Farklı Sınıflar Nasıl Atanır?",
     "Öğretmenler ekranında öğretmene çift tıklayıp 'Bu Öğretmene Ders Ata' butonuna basın. Bir ders seçtiğinizde aşağıda otomatik yeni ders satırı açılır. Her dersin yanındaki '🎓 Sınıf(lar) Ata...' butonu ile o ders için hangi sınıflara gireceğini bağımsız seçebilirsiniz."),
    
    ("Birleşik Sınıflar (Ortak Ders) Nedir ve Nasıl Tanımlanır?",
     "Bir öğretmenin aynı saatte birden fazla sınıfa ortak derse girmesidir (Örn: 9A + 9B Beden Eğitimi). Sınıf seçimi ekranında 'Birleşik Sınıflar' butonuna tıklayarak en az 2 sınıf seçebilir, çakışma durumunda '⚠️ Çakışmayı Yoksay ve Birleştir' butonunu kullanabilirsiniz."),
    
    ("Özel Alanlar (Custom Fields) Nedir?",
     "Öğretmen, Sınıf, Ders ve Derslik kartlarına aSc standartlarında telefon, e-posta, sicil no, branş ve özel notlar gibi sınırsız meta veri eklemenizi sağlayan responsive bir modüldür."),
    
    ("Baskı ve PDF Çıktıları aSc Birebir Formatında mı Alınır?",
     "Evet! Sınıfın Dersleri dikey liste formatı, tam sayfa renkli haftalık grid ve kağıt tasarruflu (sayfada 6'lı) mini grid raporları aSc standartlarında yüksek çözünürlükte yazdırılabilir veya PDF olarak kaydedilebilir."),
    
    ("İnternet Hesabı ve Bulut Senkronizasyonu nasıl kullanılır?",
     "Ana Menüdeki 'İnternet Hesabı' butonuna tıklayarak https://chenki.net/ adresine gidebilir, okul hesabınızla evden ve okuldan tüm programları güvenli bulut sunucusunda senkronize edebilirsiniz.")
]

class FAQDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sıkça Sorulan Sorular ve Yanıtlar (SSS)")
        self.resize(820, 620)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; }
            QLineEdit { border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px 14px; font-size: 13px; background: white; }
            QLineEdit:focus { border: 1px solid #2563EB; }
            QPushButton { min-height: 32px; padding: 6px 18px; border-radius: 6px; font-weight: bold; }
        """)
        self._cards = []
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        # Header Card
        h_card = QFrame()
        h_card.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px;")
        h_lay = QVBoxLayout(h_card)
        
        lbl_title = QLabel("📚 BGZ Ders Planlama — Sıkça Sorulan Sorular ve Rehber")
        lbl_title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        lbl_title.setStyleSheet("color: #2563EB; border: none;")
        h_lay.addWidget(lbl_title)
        
        lbl_sub = QLabel("Programın tüm özellikleri, A* Search algoritması, kısıtlamalar ve kullanım ipuçları.")
        lbl_sub.setStyleSheet("color: #64748B; font-size: 12px; border: none;")
        h_lay.addWidget(lbl_sub)
        layout.addWidget(h_card)
        
        # Real-time search bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Soru veya konu ara (Örn: A* Search, manuel ders, kısaltma, saat)...")
        self.txt_search.textChanged.connect(self._filter_faqs)
        layout.addWidget(self.txt_search)
        
        # Scroll area for Q&A cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        self.c_lay = QVBoxLayout(container)
        self.c_lay.setSpacing(12)
        
        for q, a in FAQ_DATA:
            card = QFrame()
            card.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; }")
            card_lay = QVBoxLayout(card)
            card_lay.setSpacing(6)
            
            q_lbl = QLabel(f"❓ {q}")
            q_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
            q_lbl.setStyleSheet("color: #0F172A; border: none;")
            q_lbl.setWordWrap(True)
            
            a_lbl = QLabel(f"💡 {a}")
            a_lbl.setFont(QFont("Segoe UI", 10))
            a_lbl.setStyleSheet("color: #334155; line-height: 1.4; border: none; background: #F8FAFC; padding: 8px; border-radius: 6px; border-left: 3px solid #2563EB;")
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
        btn_web = QPushButton("🌐 chenki.net Destek Sayfasına Git")
        btn_web.setStyleSheet("background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE;")
        btn_web.clicked.connect(lambda: __import__('webbrowser').open("https://chenki.net/"))
        b_lay.addWidget(btn_web)
        
        b_lay.addStretch(1)
        
        btn_close = QPushButton("Kapat")
        btn_close.setStyleSheet("background: #2563EB; color: white; border: none;")
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

