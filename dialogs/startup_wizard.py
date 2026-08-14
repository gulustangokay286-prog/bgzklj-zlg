import os
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, 
    QPushButton, QStackedWidget, QWidget, QSpinBox, QCheckBox, QMessageBox,
    QFrame, QComboBox
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor

import database
from state_manager import store

def draw_placeholder_icon(icon_type):
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    if icon_type == "bank":
        p.setBrush(QColor("#DDE5ED"))
        p.setPen(QColor("#8399B0"))
        p.drawPolygon([QPoint(32, 10), QPoint(10, 26), QPoint(54, 26)])
        p.drawRect(12, 26, 40, 4)
        for i in range(4):
            p.drawRect(16 + i*10, 30, 4, 20)
        p.drawRect(12, 50, 40, 4)
    elif icon_type == "grid":
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QColor("#4EA0E8"))
        p.drawRect(15, 15, 34, 34)
        p.setPen(QColor("#D0D0D0"))
        for r in range(3):
            for c in range(5):
                p.drawPoint(18 + c*6, 35 + r*5)
    elif icon_type == "list":
        p.setPen(QColor("#888888"))
        for i in range(4):
            p.drawRect(10, 15 + i*10, 8, 8)
            p.drawLine(25, 19 + i*10, 50, 19 + i*10)
    p.end()
    return pix

class StartupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Program Yapılandır")
        self.resize(720, 520)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: 'Segoe UI', sans-serif; }
            QLabel { font-size: 13px; color: #1E293B; }
            h2 { color: #0F172A; }
            QLineEdit, QSpinBox, QComboBox { 
                padding: 6px; border: 1px solid #CBD5E1; 
                border-radius: 3px; font-size: 13px; background: white;
            }
            QPushButton { 
                padding: 8px 16px; font-weight: bold; 
                border-radius: 4px; border: 1px solid #CBD5E1;
                background-color: #F1F5F9; color: #334155;
            }
            QPushButton:hover { background-color: #E2E8F0; }
            QPushButton#nextBtn { background-color: #2563EB; color: white; border: none; }
            QPushButton#nextBtn:hover { background-color: #1D4ED8; }
            QFrame#h_line { background: #E2E8F0; max-height: 1px; }
            QWidget#sidebar { background-color: #F1F5F9; border-right: 1px solid #E2E8F0; }
            QLabel#stepLabel { padding: 8px; font-weight: bold; color: #64748B; border-radius: 4px; }
            QLabel#stepLabel[active="true"] { background-color: #DBEAFE; color: #1D4ED8; }
        """)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Sidebar for Steps
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 20, 15, 20)
        sidebar_layout.setSpacing(10)
        
        self.step_labels = []
        steps_text = [
            "1. Genel Bilgiler", "2. Gün ve Saatler", 
            "3. Dersler", "4. Sınıflar", 
            "5. Derslikler", "6. Öğretmenler", "7. Tamamla"
        ]
        
        for text in steps_text:
            lbl = QLabel(text)
            lbl.setObjectName("stepLabel")
            self.step_labels.append(lbl)
            sidebar_layout.addWidget(lbl)
            
        sidebar_layout.addStretch()
        self.layout.addWidget(self.sidebar)
        
        # Main Area
        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        self.stacked = QStackedWidget(self)
        main_layout.addWidget(self.stacked)
        
        # Build pages
        self._build_page_1()
        self._build_page_2()
        self._build_page_3("3. Dersleri Girin", "Ders", "Müzik, Matematik, Tarih", 0)
        self._build_page_3("4. Sınıfları Girin", "Sınıf", "9A, 10B, 11C", 1)
        self._build_page_3("5. Derslikleri Girin", "Derslik", "Lab 1, Spor Salonu", 2)
        self._build_page_3("6. Öğretmenleri Girin", "Öğretmen", "Ahmet, Ayşe", 3)
        self._build_page_7()
        
        # Navigation
        nav_layout = QHBoxLayout()
        self.btn_back = QPushButton("Geri")
        self.btn_back.clicked.connect(self._go_back)
        self.btn_back.setEnabled(False)
        
        self.btn_next = QPushButton("İleri")
        self.btn_next.setObjectName("nextBtn")
        self.btn_next.clicked.connect(self._go_next)
        
        nav_layout.addWidget(self.btn_back)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        
        main_layout.addLayout(nav_layout)
        self.layout.addWidget(main_area)
        
        self._update_nav()
        
    def _build_page_1(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(15)
        
        title = QLabel("<h2>Adım 1: Okul Bilgileri</h2>")
        lay.addWidget(title)
        
        sec1 = QHBoxLayout()
        icon1 = QLabel()
        icon1.setPixmap(draw_placeholder_icon("bank"))
        icon1.setFixedSize(70, 70)
        sec1.addWidget(icon1)
        
        grid1 = QGridLayout()
        grid1.setSpacing(10)
        
        grid1.addWidget(QLabel("Okul / Kurum Adı:"), 0, 0)
        self.txt_kurum_adi = QLineEdit("Pivot Akademi")
        grid1.addWidget(self.txt_kurum_adi, 0, 1, 1, 2)
        
        grid1.addWidget(QLabel("Başlangıç Tarihi:"), 1, 0)
        self.txt_baslangic = QLineEdit("12/09/2026")
        grid1.addWidget(self.txt_baslangic, 1, 1, 1, 2)
        
        grid1.addWidget(QLabel("Öğretim Yılı / Tebliğ Sayısı:"), 2, 0)
        self.txt_yil = QLineEdit("2026/2027")
        self.txt_teblig = QLineEdit()
        grid1.addWidget(self.txt_yil, 2, 1)
        grid1.addWidget(self.txt_teblig, 2, 2)
        
        grid1.addWidget(QLabel("Kurum Yetkilisi Ad/Unvan:"), 3, 0)
        self.txt_yetkili_ad = QLineEdit("Müdür Bey")
        self.txt_yetkili_unvan = QLineEdit("Okul Müdürü")
        grid1.addWidget(self.txt_yetkili_ad, 2, 1)
        grid1.addWidget(self.txt_yetkili_unvan, 2, 2)
        
        sec1.addLayout(grid1)
        sec1.addStretch()
        lay.addLayout(sec1)
        lay.addStretch()
        self.stacked.addWidget(page)
        
    def _build_page_2(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(15)
        
        title = QLabel("<h2>Adım 2: Gün ve Saat Ayarları</h2>")
        lay.addWidget(title)
        
        sec2 = QHBoxLayout()
        icon2 = QLabel()
        icon2.setPixmap(draw_placeholder_icon("grid"))
        icon2.setFixedSize(70, 70)
        sec2.addWidget(icon2)
        
        grid2 = QGridLayout()
        grid2.setSpacing(10)
        grid2.addWidget(QLabel("Günlük Ders Saati:"), 0, 0)
        self.spin_periods = QSpinBox()
        self.spin_periods.setRange(1, 15)
        self.spin_periods.setValue(7)
        grid2.addWidget(self.spin_periods, 0, 1)
        
        grid2.addWidget(QLabel("Gün Sayısı:"), 1, 0)
        self.spin_days = QSpinBox()
        self.spin_days.setRange(1, 7)
        self.spin_days.setValue(5)
        grid2.addWidget(self.spin_days, 1, 1)
        
        grid2.addWidget(QLabel("Hafta Sonu:"), 2, 0)
        self.cmb_weekend = QComboBox()
        self.cmb_weekend.addItems(["Cumartesi - Pazar", "Sadece Pazar", "Yok"])
        grid2.addWidget(self.cmb_weekend, 2, 1)
        
        sec2.addLayout(grid2)
        sec2.addStretch()
        lay.addLayout(sec2)
        
        chk = QCheckBox("Çok Dönemli veya Çok Haftalı Program")
        lay.addWidget(chk)
        
        lay.addStretch()
        self.stacked.addWidget(page)
        
    def _build_page_3(self, title_text, item_type, hint, tab_idx):
        page = QWidget()
        lay = QVBoxLayout(page)
        
        title = QLabel(f"<h2>{title_text}</h2>")
        lay.addWidget(title)
        
        desc = QLabel(f"Lütfen {item_type} tanımlamalarını yapmak için aşağıdaki butonu kullanın.\nBu ekran, sistemin mevcut gelişmiş tanımlama penceresini açacaktır.")
        desc.setStyleSheet("color: #64748B; font-size: 13px;")
        lay.addWidget(desc)
        
        btn = QPushButton(f"Gelişmiş {item_type} Tanımlama Ekranını Aç")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC; border: 2px dashed #CBD5E1; 
                border-radius: 8px; padding: 20px; font-size: 14px; font-weight: bold; color: #334155;
            }
            QPushButton:hover { background-color: #E2E8F0; border-color: #94A3B8; }
        """)
        
        def open_dialog():
            from dialogs.master_data_dialog import MasterDataDialog
            d = MasterDataDialog(tab_idx, self.parent())
            d.exec()
            if hasattr(self.parent(), "save_db"):
                self.parent().save_db()
                
        btn.clicked.connect(open_dialog)
        lay.addWidget(btn)
        
        lay.addStretch()
        self.stacked.addWidget(page)
        
    def _build_page_7(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(QLabel("<h2>Adım 7: Sihirbazı Tamamla</h2>"))
        
        self.lbl_status = QLabel("Bu işlem mevcut yerel verileri silecek ve tüm ayarlarınızı sıfırdan kuracaktır.\n\nHer şey hazır. Başlamak için 'Bitir ve Oluştur' butonuna tıklayın.")
        self.lbl_status.setStyleSheet("color: #0F172A; font-weight: bold;")
        self.lbl_status.setWordWrap(True)
        lay.addWidget(self.lbl_status)
        
        lay.addStretch()
        self.stacked.addWidget(page)
        
    def _go_back(self):
        idx = self.stacked.currentIndex()
        if idx > 0:
            self.stacked.setCurrentIndex(idx - 1)
        self._update_nav()
        
    def _go_next(self):
        idx = self.stacked.currentIndex()
        if idx == self.stacked.count() - 1:
            self._finish_wizard()
        else:
            self.stacked.setCurrentIndex(idx + 1)
        self._update_nav()
        
    def _update_nav(self):
        idx = self.stacked.currentIndex()
        self.btn_back.setEnabled(idx > 0)
        
        if idx == self.stacked.count() - 1:
            self.btn_next.setText("Bitir ve Oluştur")
        else:
            self.btn_next.setText("İleri")
            
        for i, lbl in enumerate(self.step_labels):
            lbl.setProperty("active", "true" if i == idx else "false")
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
            
    def _finish_wizard(self):
        try:
            p = self.parent()
            if hasattr(p, "data_store"):
                if "kurum" not in p.data_store: p.data_store["kurum"] = {}
                p.data_store["kurum"]["isim"] = self.txt_kurum_adi.text().strip()
                p.data_store["okul_adi"] = self.txt_kurum_adi.text().strip()
                p.data_store["ogretim_yili"] = self.txt_yil.text()
                p.data_store["gun_sayisi"] = self.spin_days.value()
                p.data_store["ders_saati"] = self.spin_periods.value()
                p.save_db()
                if hasattr(p, "_refresh_tree"):
                    p._refresh_tree()
                    
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Sihirbaz tamamlanırken hata oluştu:\n{str(e)}")