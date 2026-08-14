"""dialogs/wizard_dialog.py — Sihirbaz"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWizard, QWizardPage, QLineEdit, QSpinBox, QComboBox, QFormLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap, QColor


class WizardDialog(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Ders Programı Sihirbazı")
        self.setMinimumSize(600, 450)
        self.setWizardStyle(QWizard.ModernStyle)

        self.addPage(self._page_welcome())
        self.addPage(self._page_school())
        self.addPage(self._page_schedule())
        self.addPage(self._page_finish())

        self.setButtonText(QWizard.BackButton, "< Geri")
        self.setButtonText(QWizard.NextButton, "İleri >")
        self.setButtonText(QWizard.FinishButton, "Tamamla")
        self.setButtonText(QWizard.CancelButton, "Iptal")

    def _page_welcome(self):
        page = QWizardPage()
        page.setTitle("Yeni Ders Programı Olustur")
        page.setSubTitle("Bu sihirbaz size adim adim yeni bir ders programi olusturmanizda yardimci olacaktir.")
        layout = QVBoxLayout(page)
        lbl = QLabel(
            "<b>Baslamadan once asagidaki bilgileri hazirlayin:</b><br><br>"
            "- Okul adi ve donem bilgileri<br>"
            "- Haftalik gun ve ders saati sayisi<br>"
            "- Ogretmen, sinif ve derslik listesi<br>"
            "- Her sinif icin haftalik ders dagilimi<br>",
            page
        )
        lbl.setFont(QFont("Segoe UI", 10))
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        return page

    def _page_school(self):
        page = QWizardPage()
        page.setTitle("Okul Bilgileri")
        page.setSubTitle("Okul ve takvim bilgilerini girin.")
        form = QFormLayout(page)
        form.setSpacing(10)

        self._w_okul = QLineEdit(); self._w_okul.setPlaceholderText("Örn: Atatürk Anadolu Lisesi")
        self._w_yil  = QSpinBox(); self._w_yil.setRange(2020, 2035); self._w_yil.setValue(2026)
        self._w_gun  = QSpinBox(); self._w_gun.setRange(1, 6); self._w_gun.setValue(5)
        self._w_ders = QSpinBox(); self._w_ders.setRange(4, 12); self._w_ders.setValue(8)

        form.addRow("Okul Adi:", self._w_okul)
        form.addRow("Ogretim Yili:", self._w_yil)
        form.addRow("Haftada Calisilan Gun:", self._w_gun)
        form.addRow("Gunluk Ders Saati:", self._w_ders)
        return page

    def _page_schedule(self):
        page = QWizardPage()
        page.setTitle("Program Ayarlari")
        page.setSubTitle("Otomatik program olusturma tercihlerini belirleyin.")
        form = QFormLayout(page)
        form.setSpacing(10)

        self._w_algo = QComboBox()
        self._w_algo.addItems(["Backtracking (Geri Izleme)", "Hizli Atama", "Rastgele + Optimize"])
        self._w_maks_ogr = QSpinBox(); self._w_maks_ogr.setRange(1, 10); self._w_maks_ogr.setValue(6)

        form.addRow("Algoritma:", self._w_algo)
        form.addRow("Ogretmen Maks. Ardisik Ders:", self._w_maks_ogr)
        return page

    def _page_finish(self):
        page = QWizardPage()
        page.setTitle("Tamamlandi")
        page.setSubTitle("Ders programi olusturmaya hazirsiniz.")
        layout = QVBoxLayout(page)
        lbl = QLabel(
            "<b>Harika! Sihirbaz tamamlandi.</b><br><br>"
            "'Tamamla' butonuna basin ve ders programinizi olusturmaya baslayin.<br><br>"
            "Tanimlamalar menusunden ogretmen, sinif ve derslik ekleyebilirsiniz.",
            page
        )
        lbl.setFont(QFont("Segoe UI", 10))
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        return page
