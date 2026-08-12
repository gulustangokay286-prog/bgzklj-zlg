"""dialogs/edit_forms.py - Sihirbaz içindeki detaylı özel formlar (Ders, Sınıf vb.)"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QLineEdit, QComboBox, QCheckBox, QColorDialog, QFrame, QFormLayout, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor


class BaseEditForm(QDialog):
    def __init__(self, title, parent=None, existing_data=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(480, 420)
        self.existing_data = existing_data or {}
        
        self.setStyleSheet("""
            QGroupBox { font-weight: bold; margin-top: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px 0 3px; }
            QLineEdit, QComboBox { min-height: 26px; padding: 2px; border: 1px solid #CCC; background: #FFF; }
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 12)
        self.main_layout.setSpacing(12)

    def _add_bottom_buttons(self):
        self.main_layout.addStretch(1)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        btn_tamam = QPushButton("Tamam")
        btn_tamam.setFixedSize(80, 28)
        btn_tamam.setStyleSheet("border: 1px solid #1E6DB5; color: #1E6DB5; background: #FFFFFF;")
        btn_tamam.clicked.connect(self.accept)
        
        btn_iptal = QPushButton("İptal")
        btn_iptal.setFixedSize(80, 28)
        btn_iptal.clicked.connect(self.reject)
        
        bottom.addWidget(btn_tamam)
        bottom.addWidget(btn_iptal)
        self.main_layout.addLayout(bottom)


class LessonAssignmentDialog(QDialog):
    def __init__(self, parent=None, existing_data=None, data_store=None):
        super().__init__(parent)
        self.setWindowTitle("Ders Atama")
        self.setFixedSize(650, 600)
        self.setStyleSheet("""
            QDialog { background-color: #F3F3F3; }
            QLineEdit, QComboBox { min-height: 26px; padding: 2px; border: 1px solid #CCC; background: #FFF; }
        """)
        self.existing_data = existing_data or {}
        self.data_store = data_store
        self._build_ui()
        
    def _create_icon_label(self, name):
        from dialogs.advanced_wizard import create_wizard_icon
        lbl = QLabel()
        pix = create_wizard_icon(name)
        if not pix.isNull():
            lbl.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        return lbl
        
    def _create_row_frame(self):
        f = QFrame()
        f.setStyleSheet("QFrame { background: #FAFAFA; border: 1px solid #E0E0E0; border-radius: 4px; }")
        return f

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # 1. Öğretmen Row
        row1 = self._create_row_frame()
        l1 = QHBoxLayout(row1)
        l1.addWidget(self._create_icon_label("grad_hat"))
        
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("Öğretmen"))
        self.cb_ogretmen = QComboBox()
        self.cb_ogretmen.setMinimumWidth(250)
        self.cb_ogretmen.setStyleSheet("QComboBox { background: #E1F0FA; border: 1px solid #B0C4DE; padding: 4px; }")
        v1.addWidget(self.cb_ogretmen)
        l1.addLayout(v1)
        l1.addStretch(1)
        btn_ortak_ogr = QPushButton("Ortak Öğretmen")
        btn_ortak_ogr.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC; padding: 6px 15px;")
        l1.addWidget(btn_ortak_ogr, alignment=Qt.AlignBottom)
        main_layout.addWidget(row1)
        
        # 2. Ders Row
        row2 = self._create_row_frame()
        l2 = QHBoxLayout(row2)
        l2.addWidget(self._create_icon_label("book"))
        v2 = QVBoxLayout()
        v2.addWidget(QLabel("Ders"))
        self.cb_ders = QComboBox()
        self.cb_ders.setMinimumWidth(250)
        self.cb_ders.setStyleSheet("QComboBox { background: #FFFFFF; border: 1px solid #CCC; padding: 4px; }")
        v2.addWidget(self.cb_ders)
        l2.addLayout(v2)
        l2.addStretch(1)
        main_layout.addWidget(row2)
        
        # 3. Sınıf Row
        row3 = self._create_row_frame()
        l3 = QHBoxLayout(row3)
        l3.addWidget(self._create_icon_label("teachers"))
        v3 = QVBoxLayout()
        v3.addWidget(QLabel("Sınıf"))
        self.cb_sinif = QComboBox()
        self.cb_sinif.setMinimumWidth(250)
        self.cb_sinif.setStyleSheet("QComboBox { background: #FFFFFF; border: 1px solid #CCC; padding: 4px; }")
        v3.addWidget(self.cb_sinif)
        l3.addLayout(v3)
        l3.addStretch(1)
        btn_birl_sinif = QPushButton("Birleşik Sınıflar")
        btn_birl_sinif.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC; padding: 6px 15px;")
        l3.addWidget(btn_birl_sinif, alignment=Qt.AlignBottom)
        main_layout.addWidget(row3)
        
        # 4. Haftalık Ders Row
        row4 = self._create_row_frame()
        l4 = QHBoxLayout(row4)
        # Using a default calendar icon if arrow is not perfect
        l4.addWidget(self._create_icon_label("arrow")) 
        v4 = QVBoxLayout()
        v4.addWidget(QLabel("Haftalık Ders"))
        h4 = QHBoxLayout()
        self.cb_hafta = QComboBox()
        self.cb_hafta.addItems(["1", "2", "3", "4", "5", "6", "7", "8"])
        self.cb_hafta.setStyleSheet("QComboBox { background: #FFFFFF; border: 1px solid #CCC; padding: 4px; }")
        self.cb_tip = QComboBox()
        self.cb_tip.addItems(["Tekli", "Çiftli", "Üçlü"])
        self.cb_tip.setStyleSheet("QComboBox { background: #FFFFFF; border: 1px solid #CCC; padding: 4px; }")
        h4.addWidget(self.cb_hafta)
        h4.addWidget(self.cb_tip)
        v4.addLayout(h4)
        l4.addLayout(v4)
        l4.addStretch(1)
        lbl_coklu = QLabel("Çoklu Hafta/Dönem")
        l4.addWidget(lbl_coklu, alignment=Qt.AlignBottom)
        main_layout.addWidget(row4)
        
        # 5. Derslik Row
        row5 = self._create_row_frame()
        l5 = QHBoxLayout(row5)
        l5.addWidget(self._create_icon_label("door"))
        v5 = QVBoxLayout()
        
        chk_lay = QGridLayout()
        self.chk_sinif = QCheckBox("Sınıfın Dersliği")
        self.chk_sinif.setChecked(True)
        self.chk_ogr = QCheckBox("Öğretmenin Derslikleri")
        self.chk_ortak = QCheckBox("Ortak Derslik")
        self.chk_derse_ait = QCheckBox("Derse Ait Derslik")
        
        self.chk_sinif.setStyleSheet("QCheckBox { border: none; background: transparent; }")
        self.chk_ogr.setStyleSheet("QCheckBox { border: none; background: transparent; }")
        self.chk_ortak.setStyleSheet("QCheckBox { border: none; background: transparent; }")
        self.chk_derse_ait.setStyleSheet("QCheckBox { border: none; background: transparent; }")
        
        chk_lay.addWidget(self.chk_sinif, 0, 0)
        chk_lay.addWidget(self.chk_ogr, 0, 1)
        chk_lay.addWidget(self.chk_ortak, 1, 0)
        chk_lay.addWidget(self.chk_derse_ait, 1, 1)
        v5.addLayout(chk_lay)
        
        h5 = QHBoxLayout()
        self.txt_farkli = QLineEdit()
        self.txt_farkli.setPlaceholderText("Farklı Derslik Seç")
        self.txt_farkli.setStyleSheet("QLineEdit { background: #F0F0F0; border: 1px solid #CCC; padding: 4px; }")
        h5.addWidget(self.txt_farkli)
        btn_daha = QPushButton("Daha Fazla Derslik")
        btn_daha.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC; padding: 4px 15px;")
        h5.addWidget(btn_daha)
        v5.addLayout(h5)
        
        l5.addLayout(v5)
        main_layout.addWidget(row5)
        
        # Bottom Buttons
        main_layout.addStretch(1)
        bot_lay = QHBoxLayout()
        
        btn_iptal = QPushButton("İptal")
        btn_iptal.setFixedSize(100, 30)
        btn_iptal.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC;")
        btn_iptal.clicked.connect(self.reject)
        
        btn_yardim = QPushButton("Yardım")
        btn_yardim.setFixedSize(100, 30)
        btn_yardim.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC;")
        
        btn_tamam = QPushButton("Tamam")
        btn_tamam.setFixedSize(150, 32)
        btn_tamam.setStyleSheet("QPushButton { border: 2px solid #0078D7; color: #0078D7; background: #FFFFFF; font-weight: bold; border-radius: 4px; }")
        btn_tamam.clicked.connect(self.accept)
        
        bot_lay.addWidget(btn_iptal)
        bot_lay.addWidget(btn_yardim)
        bot_lay.addStretch(1)
        bot_lay.addWidget(btn_tamam)
        
        main_layout.addLayout(bot_lay)
        
        self._populate_data()

    def _populate_data(self):
        if self.data_store:
            for t in self.data_store.get("ogretmenler", []):
                self.cb_ogretmen.addItem(t.get("ad", ""), t)
            for d in self.data_store.get("dersler", []):
                self.cb_ders.addItem(d.get("ad", ""), d)
            for c in self.data_store.get("siniflar", []):
                self.cb_sinif.addItem(c.get("ad", ""), c)
                
        self._add_bottom_buttons()
        
    def _add_bottom_buttons(self):
        # We already have main_layout
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        btn_iptal = QPushButton("İptal")
        btn_iptal.setFixedSize(90, 30)
        btn_iptal.clicked.connect(self.reject)
        
        btn_yardim = QPushButton("Yardım")
        btn_yardim.setFixedSize(90, 30)
        
        bottom.addWidget(btn_iptal)
        bottom.addWidget(btn_yardim)
        bottom.addStretch(1)
        
        btn_tamam = QPushButton("Tamam")
        btn_tamam.setFixedSize(90, 30)
        btn_tamam.setStyleSheet("border: 2px solid #0078D7; color: #0078D7; background: #FFFFFF; font-weight: bold;")
        btn_tamam.clicked.connect(self.accept)
        bottom.addWidget(btn_tamam)
        self.layout().addLayout(bottom)

    def get_data(self):
        return {
            "teacher": self.cb_ogretmen.currentText(),
            "subject": self.cb_ders.currentText(),
            "class": self.cb_sinif.currentText(),
            "duration": int(self.cb_hafta.currentText()),
            "type": self.cb_tip.currentText()
        }


class DersEditDialog(QDialog):
    """
    Sade Ders (Subject) Tanımlama Ekranı (Screenshot 5'e uygun)
    """
    def __init__(self, parent=None, existing_data=None):
        super().__init__(parent)
        self.setWindowTitle("Ders")
        self.setFixedSize(500, 400)
        self.setStyleSheet("""
            QDialog { background-color: #F3F3F3; font-family: 'Segoe UI'; font-size: 9pt; }
            QLineEdit, QComboBox { min-height: 26px; padding: 2px; border: 1px solid #CCC; background: #FFF; }
        """)
        self.existing_data = existing_data or {}
        self._build_ui()
        
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # 1. Dersin Adı / Kısa Kodu
        f1 = QFrame()
        f1.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #CCC; border-radius: 4px; padding: 10px; }")
        l1 = QFormLayout(f1)
        l1.setSpacing(10)
        
        self.txt_ad = QLineEdit()
        self.txt_ad.setStyleSheet("border: 1px solid #1E6DB5; border-bottom: 2px solid #1E6DB5; padding: 4px; min-height: 26px;")
        if "ad" in self.existing_data: self.txt_ad.setText(self.existing_data["ad"])
        
        self.txt_kisa = QLineEdit()
        self.txt_kisa.setStyleSheet("border: 1px solid #CCC; padding: 4px; min-height: 26px;")
        if "kisa" in self.existing_data: self.txt_kisa.setText(self.existing_data["kisa"])
        
        l1.addRow(QLabel("Dersin Adı"), self.txt_ad)
        l1.addRow(QLabel("Kısa Kodu"), self.txt_kisa)
        
        btn_ozel = QPushButton("Özel Alanlar")
        btn_ozel.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC; padding: 4px;")
        l1.addRow("", btn_ozel)
        
        main_layout.addWidget(f1)
        
        # 2. Renk Kodu
        f2 = QFrame()
        f2.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #CCC; border-radius: 4px; padding: 10px; }")
        l2 = QVBoxLayout(f2)
        l2.addWidget(QLabel("Renk Kodu/Küçük Resim Seç"))
        h2 = QHBoxLayout()
        self.color_lbl = QLabel()
        self.color_lbl.setFixedSize(180, 50)
        self.current_color = self.existing_data.get("renk", "#C4C4F0")
        self.color_lbl.setStyleSheet(f"background-color: {self.current_color}; border: 1px solid #AAA;")
        h2.addWidget(self.color_lbl)
        
        btn_renk = QPushButton("Değiştir")
        btn_renk.setFixedSize(100, 30)
        btn_renk.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC; border-radius: 4px;")
        btn_renk.clicked.connect(self._pick_color)
        h2.addStretch(1)
        h2.addWidget(btn_renk)
        h2.addStretch(1)
        l2.addLayout(h2)
        
        main_layout.addWidget(f2)
        
        # 3. Derslikler
        f3 = QFrame()
        f3.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #CCC; border-radius: 4px; padding: 10px; }")
        l3 = QVBoxLayout(f3)
        l3.addWidget(QLabel("Derslikler"))
        
        btn_derslik = QPushButton("Derslikler")
        btn_derslik.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC; padding: 6px;")
        btn_uygula = QPushButton("Dersin Tanımlanmış Kartlarına Uygula")
        btn_uygula.setStyleSheet("background: #F0F0F0; border: 1px solid #CCC; padding: 6px;")
        
        l3.addWidget(btn_derslik)
        l3.addWidget(btn_uygula)
        
        main_layout.addWidget(f3)
        
        # 4. Bottom Controls
        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("Numara:"))
        self.txt_numara = QLineEdit()
        self.txt_numara.setFixedWidth(80)
        bottom.addWidget(self.txt_numara)
        bottom.addStretch(1)
        
        btn_tamam = QPushButton("Tamam")
        btn_tamam.setFixedSize(80, 28)
        btn_tamam.setStyleSheet("border: 2px solid #0078D7; color: #0078D7; background: #FFFFFF; font-weight: bold; border-radius: 4px;")
        btn_tamam.clicked.connect(self.accept)
        
        btn_iptal = QPushButton("İptal")
        btn_iptal.setFixedSize(80, 28)
        btn_iptal.setStyleSheet("border: 1px solid #CCC; background: #F0F0F0; border-radius: 4px;")
        btn_iptal.clicked.connect(self.reject)
        
        bottom.addWidget(btn_tamam)
        bottom.addWidget(btn_iptal)
        
        main_layout.addLayout(bottom)
        
    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.current_color), self, "Renk Seç")
        if c.isValid():
            self.current_color = c.name()
            self.color_lbl.setStyleSheet(f"background-color: {self.current_color}; border: 1px solid #AAA;")

    def get_data(self):
        return {
            "ad": self.txt_ad.text(),
            "kisa": self.txt_kisa.text(),
            "renk": self.current_color
        }


class SinifEditDialog(BaseEditForm):
    def __init__(self, parent=None, existing_data=None):
        super().__init__("Sınıf", parent, existing_data)
        self._color = self.existing_data.get("renk", "#A30F37")
        self._build_ui()
        
    def _build_ui(self):
        form = QFormLayout()
        form.setSpacing(12)
        
        self.w_ad = QLineEdit(self.existing_data.get("ad", ""))
        self.w_kisa = QLineEdit(self.existing_data.get("kisa", ""))
        form.addRow("Sınıf Adı", self.w_ad)
        form.addRow("Kısa Kodu", self.w_kisa)
        self.main_layout.addLayout(form)
        
        btn_ozel = QPushButton("Özel Alanlar")
        btn_ozel.setFixedWidth(200)
        btn_ozel_lay = QHBoxLayout()
        btn_ozel_lay.addStretch(1); btn_ozel_lay.addWidget(btn_ozel); btn_ozel_lay.addStretch(1)
        self.main_layout.addLayout(btn_ozel_lay)
        
        cb_lay = QHBoxLayout()
        cb_lay.addStretch(1)
        self.cb_foto = QCheckBox("Fotoğrafları yazdırın")
        self.cb_foto.setChecked(self.existing_data.get("foto", True))
        cb_lay.addWidget(self.cb_foto)
        cb_lay.addStretch(1)
        self.main_layout.addLayout(cb_lay)
        
        lbl_renk = QLabel("Renk Kodu")
        self.main_layout.addWidget(lbl_renk)
        
        renk_frame = QFrame()
        renk_frame.setStyleSheet("background: #EAEAEA; border: 1px solid #CCC;")
        r_lay = QHBoxLayout(renk_frame)
        self.color_box = QLabel()
        self.color_box.setFixedSize(180, 50)
        self.color_box.setStyleSheet(f"background: {self._color};")
        btn_degistir = QPushButton("Değiştir")
        btn_degistir.setFixedSize(80, 28)
        btn_degistir.clicked.connect(self._pick_color)
        r_lay.addWidget(self.color_box)
        r_lay.addStretch(1)
        r_lay.addWidget(btn_degistir)
        r_lay.addStretch(1)
        self.main_layout.addWidget(renk_frame)
        
        so_lay = QHBoxLayout()
        so_lay.addWidget(QLabel("Sınıf Öğretmeni:"))
        self.w_so = QLineEdit(self.existing_data.get("sinif_ogretmeni", ""))
        so_lay.addWidget(self.w_so)
        btn_so = QPushButton("Değiştir")
        so_lay.addWidget(btn_so)
        self.main_layout.addLayout(so_lay)
        
        form2 = QFormLayout()
        self.w_sinif = QComboBox()
        self.w_sinif.addItems(["Hepsi", "Sabah", "Öğle"])
        idx = self.w_sinif.findText(self.existing_data.get("sinif_tipi", "Hepsi"))
        if idx >= 0: self.w_sinif.setCurrentIndex(idx)
        form2.addRow("Sınıf:", self.w_sinif)
        
        self.w_num = QLineEdit(self.existing_data.get("numara", ""))
        form2.addRow("Numara:", self.w_num)
        self.main_layout.addLayout(form2)
        
        self._add_bottom_buttons()

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self)
        if c.isValid():
            self._color = c.name()
            self.color_box.setStyleSheet(f"background: {self._color};")
            
    def get_data(self):
        return {
            "ad": self.w_ad.text(), "kisa": self.w_kisa.text(), 
            "renk": self._color, "foto": self.cb_foto.isChecked(),
            "sinif_ogretmeni": self.w_so.text(), "sinif_tipi": self.w_sinif.currentText(),
            "numara": self.w_num.text()
        }


class OgretmenEditDialog(BaseEditForm):
    def __init__(self, parent=None, existing_data=None):
        super().__init__("Öğretmen", parent, existing_data)
        self._color = self.existing_data.get("renk", "#27AE60")
        self._build_ui()
        
    def _build_ui(self):
        form = QFormLayout()
        form.setSpacing(12)
        
        self.w_ad = QLineEdit(self.existing_data.get("ad", ""))
        self.w_kisa = QLineEdit(self.existing_data.get("kisa", ""))
        form.addRow("Öğretmen Adı", self.w_ad)
        form.addRow("Kısa Kodu", self.w_kisa)
        self.main_layout.addLayout(form)
        
        btn_ozel = QPushButton("Özel Alanlar")
        btn_ozel.setFixedWidth(200)
        btn_ozel_lay = QHBoxLayout()
        btn_ozel_lay.addStretch(1); btn_ozel_lay.addWidget(btn_ozel); btn_ozel_lay.addStretch(1)
        self.main_layout.addLayout(btn_ozel_lay)
        
        lbl_renk = QLabel("Renk Kodu")
        self.main_layout.addWidget(lbl_renk)
        
        renk_frame = QFrame()
        renk_frame.setStyleSheet("background: #EAEAEA; border: 1px solid #CCC;")
        r_lay = QHBoxLayout(renk_frame)
        self.color_box = QLabel()
        self.color_box.setFixedSize(180, 50)
        self.color_box.setStyleSheet(f"background: {self._color};")
        btn_degistir = QPushButton("Değiştir")
        btn_degistir.setFixedSize(80, 28)
        btn_degistir.clicked.connect(self._pick_color)
        r_lay.addWidget(self.color_box)
        r_lay.addStretch(1)
        r_lay.addWidget(btn_degistir)
        r_lay.addStretch(1)
        self.main_layout.addWidget(renk_frame)
        
        so_lay = QHBoxLayout()
        so_lay.addWidget(QLabel("Sınıf Öğretmeni:"))
        self.w_so = QLineEdit(self.existing_data.get("sinif_ogretmeni", ""))
        so_lay.addWidget(self.w_so)
        btn_so = QPushButton("Değiştir")
        so_lay.addWidget(btn_so)
        self.main_layout.addLayout(so_lay)
        
        num_lay = QHBoxLayout()
        num_lay.addWidget(QLabel("Numara:"))
        self.w_num = QLineEdit(self.existing_data.get("numara", ""))
        self.w_num.setFixedWidth(120)
        num_lay.addWidget(self.w_num)
        num_lay.addStretch(1)
        self.main_layout.addLayout(num_lay)
        
        self._add_bottom_buttons()

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self)
        if c.isValid():
            self._color = c.name()
            self.color_box.setStyleSheet(f"background: {self._color};")

    def get_data(self):
        return {
            "ad": self.w_ad.text(), "kisa": self.w_kisa.text(),
            "renk": self._color, "sinif_ogretmeni": self.w_so.text(),
            "numara": self.w_num.text()
        }


class DerslikEditDialog(BaseEditForm):
    def __init__(self, parent=None, existing_data=None):
        super().__init__("Derslik", parent, existing_data)
        self._color = self.existing_data.get("renk", "#F39C12")
        self._build_ui()
        
    def _build_ui(self):
        form = QFormLayout()
        form.setSpacing(12)
        
        self.w_ad = QLineEdit(self.existing_data.get("ad", ""))
        self.w_kisa = QLineEdit(self.existing_data.get("kisa", ""))
        form.addRow("Derslik Adı", self.w_ad)
        form.addRow("Kısa Kodu", self.w_kisa)
        self.main_layout.addLayout(form)
        
        btn_ozel = QPushButton("Özel Alanlar")
        btn_ozel.setFixedWidth(200)
        btn_ozel_lay = QHBoxLayout()
        btn_ozel_lay.addStretch(1); btn_ozel_lay.addWidget(btn_ozel); btn_ozel_lay.addStretch(1)
        self.main_layout.addLayout(btn_ozel_lay)
        
        lbl_renk = QLabel("Renk Kodu")
        self.main_layout.addWidget(lbl_renk)
        
        renk_frame = QFrame()
        renk_frame.setStyleSheet("background: #EAEAEA; border: 1px solid #CCC;")
        r_lay = QHBoxLayout(renk_frame)
        self.color_box = QLabel()
        self.color_box.setFixedSize(180, 50)
        self.color_box.setStyleSheet(f"background: {self._color};")
        btn_degistir = QPushButton("Değiştir")
        btn_degistir.setFixedSize(80, 28)
        btn_degistir.clicked.connect(self._pick_color)
        r_lay.addWidget(self.color_box)
        r_lay.addStretch(1)
        r_lay.addWidget(btn_degistir)
        r_lay.addStretch(1)
        self.main_layout.addWidget(renk_frame)
        
        d_frame = QFrame()
        d_frame.setStyleSheet("background: #EAEAEA; border: 1px solid #CCC;")
        d_lay = QHBoxLayout(d_frame)
        d_lay.addWidget(QLabel("Derslik Kapasitesi:"))
        self.w_cap = QLineEdit(self.existing_data.get("kapasite", ""))
        d_lay.addWidget(self.w_cap)
        self.main_layout.addWidget(d_frame)
        
        num_lay = QHBoxLayout()
        num_lay.addWidget(QLabel("Numara:"))
        self.w_num = QLineEdit(self.existing_data.get("numara", ""))
        self.w_num.setFixedWidth(120)
        num_lay.addWidget(self.w_num)
        num_lay.addStretch(1)
        self.main_layout.addLayout(num_lay)
        
        self._add_bottom_buttons()

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self)
        if c.isValid():
            self._color = c.name()
            self.color_box.setStyleSheet(f"background: {self._color};")

    def get_data(self):
        return {
            "ad": self.w_ad.text(), "kisa": self.w_kisa.text(),
            "renk": self._color, "kapasite": self.w_cap.text(),
            "numara": self.w_num.text()
        }
