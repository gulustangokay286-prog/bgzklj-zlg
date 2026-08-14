from PySide6.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget, QLabel, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

FAQ_DATA = [
    ("Sınıf Ders ve Öğretmen Atama Ekranı nasıl kullanılır?", "Bu ekranda öğretmenlerinize dersleri sınıf bazında atayabilirsiniz. Öğretmeni seçip 'Daha Fazla Ders Atama' ile çoklu ders ekleyebilir, eşzamanlı olarak atandığı sınıfları görebilirsiniz."),
    ("Otomatik Planlama nasıl çalışır?", "Otomatik planlama, A* algoritması kullanarak manuel kilitlenmiş derslerin üzerine yazmadan en uygun boşluklara dersleri dağıtır. %100 yerleşim hedeflenir."),
    ("Çizelgede manuel yerleştirilen dersler korunur mu?", "Evet. Tahtaya (Grid) manuel olarak sürükleyip bıraktığınız veya atadığınız dersler, Otomatik Planlama başlatıldığında yerlerinden oynatılmaz (üzerlerine yazılmaz)."),
    ("Baskı Önizleme'de Kağıt Tasarrufu modu var mı?", "Evet. Çizelge Göster / Yazdır ekranında Rapor Türü listesinden 'Tüm Sınıflar (Kağıt Tasarrufu - Sayfada 6\\'lı)' seçeneği ile kağıttan tasarruf edebilirsiniz."),
    ("Birleşik Sınıflar özelliği ne işe yarar?", "Öğretmenin aynı saatte birden fazla sınıfa ortak derse girmesini sağlar. Sınıfları seçip çakışma durumunda kaydedebilirsiniz."),
    ("Çizelge Saatleri esnetilebilir mi?", "Temel Bilgiler (Ayarlar) menüsünden Günlük Ders Saatini 8'in üzerine (örn. 10, 12 saate) çıkarabilirsiniz. Çizelge otomatik ölçeklenecektir."),
    ("Destek almak için ne yapmalıyım?", "Ana menüdeki 'İnternet Hesabı' butonuna tıklayarak doğrudan https://chenki.net/ adresine gidip bizimle iletişime geçebilirsiniz.")
]

class FAQDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sıkça Sorulan Sorular ve Yanıtlar")
        self.resize(700, 500)
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        lbl_title = QLabel("📚 Sıkça Sorulan Sorular")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_title.setStyleSheet("color: #0078D7; margin-bottom: 10px;")
        layout.addWidget(lbl_title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        c_lay = QVBoxLayout(container)
        c_lay.setSpacing(15)
        
        for q, a in FAQ_DATA:
            q_lbl = QLabel(f"❓ <b>{q}</b>")
            q_lbl.setWordWrap(True)
            q_lbl.setStyleSheet("font-size: 14px; color: #333333;")
            
            a_lbl = QLabel(f"💡 {a}")
            a_lbl.setWordWrap(True)
            a_lbl.setStyleSheet("font-size: 13px; color: #555555; background: #F8F9FA; padding: 10px; border-radius: 6px; border-left: 3px solid #0078D7;")
            
            c_lay.addWidget(q_lbl)
            c_lay.addWidget(a_lbl)
            
        c_lay.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        btn_close = QPushButton("Kapat")
        btn_close.setFixedWidth(100)
        btn_close.setStyleSheet("background: #EAEAEA; border: 1px solid #CCC; padding: 6px; border-radius: 4px; font-weight: bold;")
        btn_close.clicked.connect(self.accept)
        
        b_lay = QHBoxLayout()
        b_lay.addStretch(1)
        b_lay.addWidget(btn_close)
        layout.addLayout(b_lay)
