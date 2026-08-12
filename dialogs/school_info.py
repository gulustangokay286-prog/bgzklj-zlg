"""dialogs/school_info.py — Temel Okul Bilgileri"""
from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLineEdit, QLabel, QSpinBox, QComboBox, QFormLayout
)
from PySide6.QtGui import QFont
from dialogs.base_dialog import BaseDialog


class SchoolInfoDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__("Temel Bilgiler / Okul Ayarları", parent=parent)
        self.resize(580, 420)
        self._setup()

    def _setup(self):
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        from PySide6.QtCore import Qt

        lbl_style = "font-size:9pt; color:#444;"

        self._okul_adi = QLineEdit(); self._okul_adi.setPlaceholderText("Okul adını girin...")
        self._mudurluk = QLineEdit(); self._mudurluk.setPlaceholderText("İl/İlçe...")
        self._yil      = QSpinBox(); self._yil.setRange(2020, 2035); self._yil.setValue(2025)
        self._donem    = QComboBox(); self._donem.addItems(["1. Dönem", "2. Dönem", "Yıllık"])
        self._gun_sayisi = QSpinBox(); self._gun_sayisi.setRange(1, 6); self._gun_sayisi.setValue(5)
        self._ders_saati = QSpinBox(); self._ders_saati.setRange(4, 12); self._ders_saati.setValue(8)
        self._ders_sure  = QSpinBox(); self._ders_sure.setRange(30, 90); self._ders_sure.setValue(40); self._ders_sure.setSuffix(" dk")
        self._teneffus   = QSpinBox(); self._teneffus.setRange(5, 30); self._teneffus.setValue(10); self._teneffus.setSuffix(" dk")

        for lbl, w in [
            ("Okul Adı:",          self._okul_adi),
            ("Müdürlük / Şehir:",  self._mudurluk),
            ("Öğretim Yılı:",      self._yil),
            ("Dönem:",             self._donem),
            ("Gün Sayısı:",        self._gun_sayisi),
            ("Günlük Ders Saati:", self._ders_saati),
            ("Ders Süresi:",       self._ders_sure),
            ("Teneffüs Süresi:",   self._teneffus),
        ]:
            lbl_w = QLabel(lbl); lbl_w.setFont(QFont("Segoe UI", 9)); lbl_w.setStyleSheet(lbl_style)
            w.setFont(QFont("Segoe UI", 9))
            form.addRow(lbl_w, w)

        self.content_layout.addLayout(form)
        self.content_layout.addStretch(1)

    def get_data(self):
        return {
            "okul_adi":   self._okul_adi.text(),
            "mudurluk":   self._mudurluk.text(),
            "yil":        self._yil.value(),
            "donem":      self._donem.currentText(),
            "gun_sayisi": self._gun_sayisi.value(),
            "ders_saati": self._ders_saati.value(),
            "ders_sure":  self._ders_sure.value(),
            "teneffus":   self._teneffus.value(),
        }
