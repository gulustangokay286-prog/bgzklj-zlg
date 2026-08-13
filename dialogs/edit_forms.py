"""dialogs/edit_forms.py - Sihirbaz içindeki detaylı özel formlar (Ders, Sınıf vb.)"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QLineEdit, QComboBox, QCheckBox, QColorDialog, QFrame, QFormLayout, QGridLayout,
    QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

PASTEL_DISTINCT_COLORS = [
    "#1E88E5", "#43A047", "#FB8C00", "#8E24AA", "#E53935",
    "#00ACC1", "#7CB342", "#FFB300", "#6D4C41", "#546E7A",
    "#3949AB", "#00897B", "#F4511E", "#D81B60", "#00838F",
    "#5E35B1", "#A1887F", "#0097A7", "#C2185B", "#F57C00"
]

def format_tr_name(name_str: str) -> str:
    """Capitalizes Turkish names properly (e.g. 'hüseyin arman' -> 'Hüseyin Arman', 'ali ihsan' -> 'Ali İhsan')."""
    if not name_str:
        return name_str
    words = name_str.strip().split()
    formatted = []
    tr_upper_map = {'i': 'İ', 'ı': 'I', 'ç': 'Ç', 'ğ': 'Ğ', 'ö': 'Ö', 'ş': 'Ş', 'ü': 'Ü'}
    tr_lower_map = {'İ': 'i', 'I': 'ı', 'Ç': 'ç', 'Ğ': 'ğ', 'Ö': 'ö', 'Ş': 'ş', 'Ü': 'ü'}
    
    for w in words:
        if not w:
            continue
        first = w[0]
        rest = w[1:]
        first_cap = tr_upper_map.get(first, first.upper())
        rest_lower = "".join(tr_lower_map.get(c, c.lower()) for c in rest)
        formatted.append(first_cap + rest_lower)
        
    return " ".join(formatted)

def get_subject_color(subject_name: str) -> str:
    """Returns a deterministic, vibrant, distinct color for any subject name."""
    if not subject_name:
        return "#1E88E5"
    hash_val = sum(ord(c) * (i + 1) for i, c in enumerate(subject_name.strip()))
    return PASTEL_DISTINCT_COLORS[hash_val % len(PASTEL_DISTINCT_COLORS)]


class BaseEditForm(QDialog):
    def __init__(self, title, parent=None, existing_data=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(500, 480)
        self.existing_data = existing_data or {}
        
        self.setStyleSheet("""
            QDialog { background-color: #F4F6F9; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; }
            QGroupBox { font-weight: bold; margin-top: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px 0 3px; }
            QLabel { border: none; background: transparent; color: #333; font-size: 13px; }
            QLineEdit { min-height: 28px; padding: 3px 8px; border: 1px solid #CCCCCC; border-radius: 4px; background: #FFFFFF; font-size: 13px; color: #333; }
            QLineEdit:focus { border: 1px solid #0078D7; }
            QComboBox { min-height: 28px; padding: 3px 8px; border: 1px solid #CCCCCC; border-radius: 4px; background: #FFFFFF; font-size: 13px; color: #333; }
            QPushButton { min-height: 28px; padding: 4px 12px; border: 1px solid #CCCCCC; border-radius: 4px; background: #F8F9FA; font-size: 13px; color: #333; }
            QPushButton:hover { background: #EAEAEA; }
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
    def __init__(self, *args, **kwargs):
        data_store = kwargs.get("data_store")
        parent = kwargs.get("parent")
        existing_data = kwargs.get("existing_data")
        
        for arg in args:
            if isinstance(arg, dict) and data_store is None:
                data_store = arg
            elif isinstance(arg, QWidget) and parent is None:
                parent = arg
                
        super().__init__(parent)
        self.setWindowTitle("Ders Atama")
        self.setFixedSize(660, 580)
        self.setStyleSheet("""
            QDialog { background-color: #F4F6F9; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; }
            QLabel { border: none; background: transparent; color: #333; font-size: 13px; }
            QLineEdit, QComboBox { min-height: 28px; padding: 3px 8px; border: 1px solid #CCCCCC; border-radius: 4px; background: #FFFFFF; font-size: 13px; color: #333; }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #0078D7; }
            QPushButton { min-height: 28px; padding: 4px 12px; border: 1px solid #CCCCCC; border-radius: 4px; background: #F8F9FA; font-size: 13px; color: #333; }
            QPushButton:hover { background: #EAEAEA; }
        """)
        self.existing_data = existing_data or {}
        self.data_store = data_store or {}
        self.selected_teacher = kwargs.get("selected_teacher") or kwargs.get("target_teacher")
        self._build_ui()
        
    def _create_icon_label(self, name):
        from dialogs.advanced_wizard import create_wizard_icon
        lbl = QLabel()
        pix = create_wizard_icon(name)
        if not pix.isNull():
            lbl.setPixmap(pix.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        return lbl
        
    def _create_row_frame(self):
        f = QFrame()
        f.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
        return f

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; } QWidget#scrollContent { background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)
        
        # 1. Öğretmen Row
        row1 = self._create_row_frame()
        l1 = QHBoxLayout(row1)
        l1.setContentsMargins(12, 10, 12, 10)
        l1.addWidget(self._create_icon_label("grad_hat"))
        
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("Öğretmen"))
        self.cb_ogretmen = QComboBox()
        self.cb_ogretmen.setMinimumWidth(250)
        v1.addWidget(self.cb_ogretmen)
        l1.addLayout(v1)
        l1.addStretch(1)
        btn_ortak_ogr = QPushButton("Ortak Öğretmen")
        l1.addWidget(btn_ortak_ogr, alignment=Qt.AlignBottom)
        scroll_layout.addWidget(row1)
        
        # 2. Ders Row
        row2 = self._create_row_frame()
        l2 = QHBoxLayout(row2)
        l2.setContentsMargins(12, 10, 12, 10)
        l2.addWidget(self._create_icon_label("book"))
        self.v2 = QVBoxLayout()
        self.v2.addWidget(QLabel("Ders"))
        self.cb_ders = QComboBox()
        self.cb_ders.setMinimumWidth(250)
        self.cb_ders.setEditable(True)
        self.v2.addWidget(self.cb_ders)
        self.extra_ders_combos = []
        l2.addLayout(self.v2)
        l2.addStretch(1)
        
        btn_daha_fazla_ders = QPushButton("Daha Fazla Ders Atama")
        btn_daha_fazla_ders.setStyleSheet("background: #EBF3FB; color: #0078D7; font-weight: bold; border: 1px solid #0078D7; border-radius: 4px;")
        btn_daha_fazla_ders.clicked.connect(self._add_extra_subject_dialog)
        l2.addWidget(btn_daha_fazla_ders, alignment=Qt.AlignBottom)
        
        scroll_layout.addWidget(row2)
        
        # 3. Sınıf Row
        row3 = self._create_row_frame()
        l3 = QHBoxLayout(row3)
        l3.setContentsMargins(12, 10, 12, 10)
        l3.addWidget(self._create_icon_label("teachers"))
        v3 = QVBoxLayout()
        v3.addWidget(QLabel("Sınıf"))
        self.cb_sinif = QComboBox()
        self.cb_sinif.setMinimumWidth(250)
        v3.addWidget(self.cb_sinif)
        l3.addLayout(v3)
        l3.addStretch(1)
        btn_birl_sinif = QPushButton("Birleşik Sınıflar")
        btn_birl_sinif.clicked.connect(self._select_combined_classes)
        l3.addWidget(btn_birl_sinif, alignment=Qt.AlignBottom)
        scroll_layout.addWidget(row3)
        
        # 4. Haftalık Ders Row
        row4 = self._create_row_frame()
        l4 = QHBoxLayout(row4)
        l4.setContentsMargins(12, 10, 12, 10)
        l4.addWidget(self._create_icon_label("arrow")) 
        v4 = QVBoxLayout()
        v4.addWidget(QLabel("Haftalık Ders (Saat / Tip)"))
        h4 = QHBoxLayout()
        self.cb_hafta = QComboBox()
        self.cb_hafta.addItems(["1", "2", "3", "4", "5", "6", "7", "8"])
        self.cb_tip = QComboBox()
        self.cb_tip.setEditable(True)
        self.cb_hafta.currentTextChanged.connect(self._update_tip_options)
        self._update_tip_options(self.cb_hafta.currentText())
        h4.addWidget(self.cb_hafta)
        h4.addWidget(self.cb_tip)
        v4.addLayout(h4)
        l4.addLayout(v4)
        l4.addStretch(1)
        lbl_coklu = QLabel("Çoklu Hafta/Dönem")
        l4.addWidget(lbl_coklu, alignment=Qt.AlignBottom)
        scroll_layout.addWidget(row4)
        
        # 5. Derslik Row
        row5 = self._create_row_frame()
        l5 = QHBoxLayout(row5)
        l5.setContentsMargins(12, 10, 12, 10)
        l5.addWidget(self._create_icon_label("door"))
        v5 = QVBoxLayout()
        
        chk_lay = QGridLayout()
        self.chk_sinif = QCheckBox("Sınıfın Dersliği")
        self.chk_sinif.setChecked(True)
        self.chk_ogr = QCheckBox("Öğretmenin Derslikleri")
        self.chk_ortak = QCheckBox("Ortak Derslik")
        self.chk_derse_ait = QCheckBox("Derse Ait Derslik")
        
        chk_lay.addWidget(self.chk_sinif, 0, 0)
        chk_lay.addWidget(self.chk_ogr, 0, 1)
        chk_lay.addWidget(self.chk_ortak, 1, 0)
        chk_lay.addWidget(self.chk_derse_ait, 1, 1)
        v5.addLayout(chk_lay)
        
        h5 = QHBoxLayout()
        self.txt_farkli = QLineEdit()
        self.txt_farkli.setPlaceholderText("Farklı Derslik Seç")
        h5.addWidget(self.txt_farkli)
        btn_daha = QPushButton("Daha Fazla Derslik")
        h5.addWidget(btn_daha)
        v5.addLayout(h5)
        
        l5.addLayout(v5)
        scroll_layout.addWidget(row5)
        
        scroll_layout.addStretch(1)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # Bottom Buttons (Single clean set)
        bot_lay = QHBoxLayout()
        
        btn_iptal = QPushButton("İptal")
        btn_iptal.setFixedSize(90, 32)
        btn_iptal.clicked.connect(self.reject)
        
        btn_yardim = QPushButton("Yardım")
        btn_yardim.setFixedSize(90, 32)
        
        btn_tamam = QPushButton("Tamam")
        btn_tamam.setFixedSize(120, 32)
        btn_tamam.setStyleSheet("QPushButton { border: 2px solid #0078D7; color: #0078D7; background: #FFFFFF; font-weight: bold; border-radius: 4px; } QPushButton:hover { background: #EBF3FB; }")
        btn_tamam.clicked.connect(self.accept)
        
        bot_lay.addWidget(btn_iptal)
        bot_lay.addWidget(btn_yardim)
        bot_lay.addStretch(1)
        bot_lay.addWidget(btn_tamam)
        
        main_layout.addLayout(bot_lay)
        
        self._populate_data()

    def _update_tip_options(self, text):
        h = int(text) if text.isdigit() else 1
        self.cb_tip.blockSignals(True)
        self.cb_tip.clear()
        
        patterns = {
            1: ["1"],
            2: ["2", "1+1"],
            3: ["3", "2+1", "1+2", "1+1+1"],
            4: ["4", "2+2", "3+1", "1+3", "2+1+1", "1+1+1+1"],
            5: ["5", "3+2", "2+3", "4+1", "1+4", "2+2+1", "1+1+1+1+1"],
            6: ["6", "3+3", "2+2+2", "4+2", "2+4", "3+2+1"],
            7: ["7", "4+3", "3+4", "3+2+2", "2+2+2+1"],
            8: ["8", "4+4", "3+3+2", "2+2+2+2", "4+2+2"]
        }
        opts = patterns.get(h, [str(h)])
        self.cb_tip.addItems(opts)
        self.cb_tip.blockSignals(False)

    def _add_extra_subject_dialog(self):
        new_cb = QComboBox()
        new_cb.setMinimumWidth(250)
        new_cb.setEditable(True)
        
        subjects = ["Matematik", "Geometri", "Fizik", "Kimya", "Biyoloji", "Türkçe", "Edebiyat", "Tarih", "Coğrafya", "Felsefe", "İngilizce", "Almanca", "Matematik 1", "Matematik 2", "Paragraf", "Problem"]
        if self.data_store:
            for d in self.data_store.get("dersler", []):
                if d.get("ad") and d.get("ad") not in subjects:
                    subjects.append(d.get("ad"))
        for s in subjects:
            new_cb.addItem(s)
            
        self.v2.addWidget(new_cb)
        self.extra_ders_combos.append(new_cb)

    def _populate_data(self):
        if self.data_store:
            for t in self.data_store.get("ogretmenler", []):
                self.cb_ogretmen.addItem(t.get("ad", ""), t)
            
            if self.selected_teacher:
                idx = self.cb_ogretmen.findText(self.selected_teacher)
                if idx >= 0:
                    self.cb_ogretmen.setCurrentIndex(idx)
            elif self.data_store.get("ogretmenler"):
                # Select the latest added teacher by default!
                last_t = self.data_store["ogretmenler"][-1].get("ad")
                idx = self.cb_ogretmen.findText(last_t)
                if idx >= 0:
                    self.cb_ogretmen.setCurrentIndex(idx)
            
            subjects = ["Matematik", "Geometri", "Fizik", "Kimya", "Biyoloji", "Türkçe", "Edebiyat", "Tarih", "Coğrafya", "Felsefe", "İngilizce", "Almanca", "Matematik 1", "Matematik 2", "Paragraf", "Problem"]
            for d in self.data_store.get("dersler", []):
                if d.get("ad") and d.get("ad") not in subjects:
                    subjects.append(d.get("ad"))
            for s in subjects:
                self.cb_ders.addItem(s)

            for c in self.data_store.get("siniflar", []):
                self.cb_sinif.addItem(c.get("ad", ""), c)
            
            # Load existing assignments for this teacher
            teacher_name = self.cb_ogretmen.currentText()
            existing = [a for a in self.data_store.get("atamalar", []) if a.get("teacher") == teacher_name]
            
            if existing:
                # Fill first assignment into primary fields
                first = existing[0]
                s_idx = self.cb_ders.findText(first.get("subject", ""))
                if s_idx >= 0:
                    self.cb_ders.setCurrentIndex(s_idx)
                c_idx = self.cb_sinif.findText(first.get("class", ""))
                if c_idx >= 0:
                    self.cb_sinif.setCurrentIndex(c_idx)
                
                dur = str(first.get("duration", 1))
                h_idx = self.cb_hafta.findText(dur)
                if h_idx >= 0:
                    self.cb_hafta.setCurrentIndex(h_idx)
                
                tip = first.get("type", "")
                if tip:
                    t_idx = self.cb_tip.findText(tip)
                    if t_idx >= 0:
                        self.cb_tip.setCurrentIndex(t_idx)
                    else:
                        self.cb_tip.setCurrentText(tip)
                
                # Add remaining assignments as extra rows
                for extra in existing[1:]:
                    self._add_extra_subject_dialog()
                    last_cb = self.extra_ders_combos[-1]
                    e_idx = last_cb.findText(extra.get("subject", ""))
                    if e_idx >= 0:
                        last_cb.setCurrentIndex(e_idx)
                    else:
                        last_cb.setCurrentText(extra.get("subject", ""))

    def _select_combined_classes(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QPushButton, QHBoxLayout, QScrollArea, QWidget, QLabel
        d = QDialog(self)
        d.setWindowTitle("Birleşik Sınıflar Seçimi")
        d.setFixedSize(380, 440)
        lay = QVBoxLayout(d)
        
        lay.addWidget(QLabel("<b>Birleştirilecek Sınıfları Seçin:</b>"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        v_lay = QVBoxLayout(w)
        
        classes = [c.get("ad", "") for c in self.data_store.get("siniflar", []) if c.get("ad")]
        chks = []
        for c in classes:
            chk = QCheckBox(c)
            v_lay.addWidget(chk)
            chks.append(chk)
            
        scroll.setWidget(w)
        lay.addWidget(scroll)
        
        bot = QHBoxLayout()
        btn_yoksay = QPushButton("Çakışmayı Yoksay ve Birleştir")
        btn_yoksay.setStyleSheet("background: #FB8C00; color: white; font-weight: bold; padding: 6px;")
        btn_ok = QPushButton("Tamam")
        btn_ok.setStyleSheet("background: #0078D7; color: white; font-weight: bold; padding: 6px;")
        
        bot.addWidget(btn_yoksay)
        bot.addWidget(btn_ok)
        lay.addLayout(bot)
        
        selected_res = []
        
        def do_accept(bypass_conflict=False):
            nonlocal selected_res
            selected_res = [chk.text() for chk in chks if chk.isChecked()]
            if bypass_conflict:
                self.bypass_conflict = True
            d.accept()
            
        btn_ok.clicked.connect(lambda: do_accept(False))
        btn_yoksay.clicked.connect(lambda: do_accept(True))
        
        if d.exec() == QDialog.Accepted and selected_res:
            combined_name = " + ".join(selected_res)
            idx = self.cb_sinif.findText(combined_name)
            if idx < 0:
                self.cb_sinif.addItem(combined_name)
                idx = self.cb_sinif.findText(combined_name)
            self.cb_sinif.setCurrentIndex(idx)

    def get_data(self):
        dur_str = self.cb_hafta.currentText()
        type_val = self.cb_tip.currentText().strip()
        
        if "+" in type_val:
            parts = [int(p.strip()) for p in type_val.split("+") if p.strip().isdigit()]
            duration = sum(parts) if parts else (int(dur_str) if dur_str.isdigit() else 1)
        else:
            duration = int(type_val) if type_val.isdigit() else (int(dur_str) if dur_str.isdigit() else 1)
            
        all_subjs = [self.cb_ders.currentText().strip()] + [cb.currentText().strip() for cb in self.extra_ders_combos if cb.currentText().strip()]
        unique_subjs = list(dict.fromkeys(filter(None, all_subjs)))

        teacher_name = format_tr_name(self.cb_ogretmen.currentText())
        assignments = []
        for subj in unique_subjs:
            assignments.append({
                "teacher": teacher_name,
                "subject": subj,
                "class": self.cb_sinif.currentText(),
                "duration": duration,
                "type": type_val,
                "color": get_subject_color(subj)
            })
            
        return assignments if assignments else [{
            "teacher": teacher_name,
            "subject": "Ders",
            "class": self.cb_sinif.currentText(),
            "duration": duration,
            "type": type_val,
            "color": get_subject_color("Ders")
        }]

    def accept(self):
        super().accept()


class DersEditDialog(QDialog):
    """
    Sade Ders (Subject) Tanımlama Ekranı
    """
    def __init__(self, parent=None, existing_data=None):
        super().__init__(parent)
        self.setWindowTitle("Ders")
        self.setFixedSize(520, 560)
        self.setStyleSheet("""
            QDialog { background-color: #F4F6F9; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; }
            QLabel { border: none; background: transparent; color: #333; font-size: 13px; }
            QLineEdit { min-height: 28px; padding: 3px 8px; border: 1px solid #CCCCCC; border-radius: 4px; background: #FFFFFF; font-size: 13px; color: #333; }
            QLineEdit:focus { border: 1px solid #0078D7; }
            QComboBox { min-height: 28px; padding: 3px 8px; border: 1px solid #CCCCCC; border-radius: 4px; background: #FFFFFF; font-size: 13px; }
            QPushButton { min-height: 28px; padding: 4px 12px; border: 1px solid #CCCCCC; border-radius: 4px; background: #F8F9FA; font-size: 13px; color: #333; }
            QPushButton:hover { background: #EAEAEA; }
        """)
        self.existing_data = existing_data or {}
        self.current_color = self.existing_data.get("renk", "#C4C4F0")
        self._build_ui()
        
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # 1. Dersin Adı / Kısa Kodu
        f1 = QFrame()
        f1.setObjectName("card1")
        f1.setStyleSheet("#card1 { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
        l1 = QFormLayout(f1)
        l1.setContentsMargins(12, 12, 12, 12)
        l1.setSpacing(10)
        
        self.txt_ad = QLineEdit()
        if "ad" in self.existing_data: self.txt_ad.setText(self.existing_data["ad"])
        self.txt_ad.textChanged.connect(self._auto_short_code)
        
        self.txt_kisa = QLineEdit()
        if "kisa" in self.existing_data: self.txt_kisa.setText(self.existing_data["kisa"])
        
        l1.addRow(QLabel("Dersin Adı"), self.txt_ad)
        l1.addRow(QLabel("Kısa Kodu"), self.txt_kisa)
        
        btn_ozel = QPushButton("Özel Alanlar")
        l1.addRow("", btn_ozel)
        
        main_layout.addWidget(f1)

        # 2. Renk Kodu
        f2 = QFrame()
        f2.setObjectName("card2")
        f2.setStyleSheet("#card2 { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
        l2 = QVBoxLayout(f2)
        l2.setContentsMargins(12, 12, 12, 12)
        l2.setSpacing(8)
        
        lbl_renk_title = QLabel("Renk Kodu / Küçük Resim Seç")
        lbl_renk_title.setStyleSheet("font-weight: bold;")
        l2.addWidget(lbl_renk_title)
        
        h2 = QHBoxLayout()
        self.color_lbl = QLabel()
        self.color_lbl.setFixedSize(140, 36)
        self.color_lbl.setStyleSheet(f"background-color: {self.current_color}; border: 1px solid #AAA; border-radius: 4px;")
        h2.addWidget(self.color_lbl)
        
        btn_renk = QPushButton("Değiştir")
        btn_renk.setFixedSize(90, 32)
        btn_renk.clicked.connect(self._pick_color)
        h2.addStretch(1)
        h2.addWidget(btn_renk)
        h2.addStretch(1)
        l2.addLayout(h2)
        
        main_layout.addWidget(f2)
        
        # 3. Derslikler
        f3 = QFrame()
        f3.setObjectName("card3")
        f3.setStyleSheet("#card3 { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
        l3 = QVBoxLayout(f3)
        l3.setContentsMargins(12, 12, 12, 12)
        l3.setSpacing(8)
        
        lbl_derslik_title = QLabel("Derslikler")
        lbl_derslik_title.setStyleSheet("font-weight: bold;")
        l3.addWidget(lbl_derslik_title)
        
        btn_derslik = QPushButton("Derslikler")
        btn_derslik.clicked.connect(self._open_derslikler)
        btn_uygula = QPushButton("Dersin Tanımlanmış Kartlarına Uygula")
        btn_uygula.clicked.connect(self._apply_to_cards)
        btn_hoca_ata = QPushButton("🎓 Dersin Öğretmenlerini ve Sınıflarını Ata")
        btn_hoca_ata.setStyleSheet("background: #0078D7; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        btn_hoca_ata.clicked.connect(self._assign_teachers_for_subject)
        
        l3.addWidget(btn_derslik)
        l3.addWidget(btn_uygula)
        l3.addWidget(btn_hoca_ata)
        
        main_layout.addWidget(f3)

    def _assign_teachers_for_subject(self):
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        subj_name = self.txt_ad.text().strip()
        if not subj_name:
            return
        d = LessonAssignmentDialog(data_store=data_store, parent=p or self)
        idx = d.cb_ders.findText(subj_name)
        if idx >= 0: d.cb_ders.setCurrentIndex(idx)
        else: d.cb_ders.setCurrentText(subj_name)
        if d.exec():
            if p and hasattr(p, "save_db"): p.save_db()
        
        # 4. Bottom Controls (Kaydet / İptal)
        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("Numara:"))
        self.txt_numara = QLineEdit()
        self.txt_numara.setFixedWidth(80)
        bottom.addWidget(self.txt_numara)
        bottom.addStretch(1)
        
        btn_tamam = QPushButton("Kaydet")
        btn_tamam.setFixedSize(110, 34)
        btn_tamam.setStyleSheet("QPushButton { background: #0078D7; color: white; font-weight: bold; border-radius: 4px; font-size: 13px; } QPushButton:hover { background: #005A9E; }")
        btn_tamam.clicked.connect(self.accept)
        
        btn_iptal = QPushButton("İptal")
        btn_iptal.setFixedSize(90, 34)
        btn_iptal.setStyleSheet("QPushButton { background: #F0F0F0; border: 1px solid #CCC; border-radius: 4px; } QPushButton:hover { background: #E5E5E5; }")
        btn_iptal.clicked.connect(self.reject)
        
        bottom.addWidget(btn_iptal)
        bottom.addWidget(btn_tamam)
        
        main_layout.addLayout(bottom)

    def _open_derslikler(self):
        from dialogs.master_data_dialog import MasterDataDialog
        d = MasterDataDialog(start_idx=2, parent=self)
        d.exec()

    def _apply_to_cards(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Derslik Ayarı", "Derslik seçimleri bu dersin tüm tanımlı kartlarına uygulandı.")

    def _auto_short_code(self, text):
        if text and not self.existing_data.get("kisa"):
            clean = text.strip()
            import re
            nums = "".join(re.findall(r'\d+', clean))
            letters_words = re.findall(r'[A-Za-zÇçĞğİıÖöŞşÜü]+', clean)
            if letters_words:
                if len(letters_words) >= 2:
                    base = (letters_words[0][:3] + letters_words[1][:1]).capitalize()
                else:
                    base = letters_words[0][:3].capitalize()
            else:
                base = clean[:3]
            sc = f"{base}{nums}" if nums else base
            self.txt_kisa.setText(sc)

    def _pick_color(self):
        from PySide6.QtWidgets import QColorDialog
        from PySide6.QtGui import QColor
        c = QColorDialog.getColor(QColor(self.current_color), self, "Renk Seç")
        if c.isValid():
            self.current_color = c.name()
            self.color_lbl.setStyleSheet(f"background-color: {self.current_color}; border: 1px solid #AAA; border-radius: 4px;")

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
        self.w_ad.textChanged.connect(self._auto_short_code_class)
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
        renk_frame.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
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
        
        self.w_so = QComboBox()
        teachers = [""]
        if self.parent() and hasattr(self.parent(), "data_store"):
            teachers.extend([t.get("ad", "") for t in self.parent().data_store.get("ogretmenler", []) if t.get("ad")])
        self.w_so.addItems(teachers)
        
        existing_so = self.existing_data.get("sinif_ogretmeni", "")
        idx_so = self.w_so.findText(existing_so)
        if idx_so >= 0:
            self.w_so.setCurrentIndex(idx_so)
            
        so_lay.addWidget(self.w_so)
        self.main_layout.addLayout(so_lay)
        
        form2 = QFormLayout()
        self.w_sinif = QComboBox()
        self.w_sinif.addItems(["Hepsi", "Sabah", "Öğle"])
        idx = self.w_sinif.findText(self.existing_data.get("sinif_tipi", "Hepsi"))
        if idx >= 0: self.w_sinif.setCurrentIndex(idx)
        form2.addRow("Sınıf:", self.w_sinif)
        
        self.w_num = QLineEdit(str(self.existing_data.get("kapasite", "30")))
        form2.addRow("Öğrenci Sayısı (Kapasite):", self.w_num)
        
        self.w_max_gunluk = QLineEdit(str(self.existing_data.get("ders_bitimi", "15:30")))
        form2.addRow("Ders Bitim Saati:", self.w_max_gunluk)
        self.main_layout.addLayout(form2)
        
        self._add_bottom_buttons()

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self)
        if c.isValid():
            self._color = c.name()
            self.color_box.setStyleSheet(f"background: {self._color};")
            
    def _auto_short_code_class(self, text):
        if text and not self.existing_data.get("kisa"):
            self.w_kisa.setText(text.strip())

    def get_data(self):
        return {
            "ad": self.w_ad.text(), "kisa": self.w_kisa.text(), 
            "renk": self._color, "foto": self.cb_foto.isChecked(),
            "sinif_ogretmeni": self.w_so.currentText(), "sinif_tipi": self.w_sinif.currentText(),
            "kapasite": self.w_num.text(), "ders_bitimi": self.w_max_gunluk.text()
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
        self.w_ad.textChanged.connect(self._auto_short_code_teacher)
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
        renk_frame.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
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
        
        ek_lay = QFormLayout()
        self.w_ek_dersler = QLineEdit(self.existing_data.get("ek_dersler", "Geometri, Matematik 2"))
        self.w_ek_dersler.setPlaceholderText("Örn: Geometri, Analitik Geometri (2 - 4 ek ders)")
        ek_lay.addRow("Ek Branşlar / Dersler:", self.w_ek_dersler)
        self.main_layout.addLayout(ek_lay)

        self.chk_es_zamanli = QCheckBox("Aynı saatte çoklu/paralel ders girebilir (Çoklu Ders İzni)")
        self.chk_es_zamanli.setChecked(self.existing_data.get("es_zamanli", False))
        self.main_layout.addWidget(self.chk_es_zamanli)

        num_lay = QHBoxLayout()
        num_lay.addWidget(QLabel("Numara:"))
        self.w_num = QLineEdit(self.existing_data.get("numara", ""))
        self.w_num.setFixedWidth(120)
        num_lay.addWidget(self.w_num)
        num_lay.addStretch(1)
        self.main_layout.addLayout(num_lay)
        
        btn_ata = QPushButton("🎓 Bu Öğretmene Ders Ata")
        btn_ata.setStyleSheet("background: #0078D7; color: white; font-weight: bold; min-height: 32px; border-radius: 4px;")
        btn_ata.clicked.connect(self._assign_lessons_for_this_teacher)
        self.main_layout.addWidget(btn_ata)

        self._add_bottom_buttons()

    def _assign_lessons_for_this_teacher(self):
        t_name = self.w_ad.text().strip()
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        d = LessonAssignmentDialog(data_store=data_store, parent=p or self, selected_teacher=t_name)
        d.exec()

    def _auto_short_code_teacher(self, text):
        if text and not self.existing_data.get("kisa"):
            clean = text.strip()
            if len(clean) <= 5:
                sc = clean.upper()
            else:
                parts = clean.split()
                if len(parts) >= 2:
                    sc = f"{parts[0][0].upper()}. {' '.join(parts[1:]).upper()}"
                else:
                    sc = clean[:5].upper()
            self.w_kisa.setText(sc)

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self)
        if c.isValid():
            self._color = c.name()
            self.color_box.setStyleSheet(f"background: {self._color};")

    def get_data(self):
        raw_ad = self.w_ad.text().strip()
        ad_formatted = format_tr_name(raw_ad)
        return {
            "ad": ad_formatted, "kisa": self.w_kisa.text(),
            "renk": self._color, "sinif_ogretmeni": self.w_so.text(),
            "ek_dersler": self.w_ek_dersler.text(),
            "es_zamanli": self.chk_es_zamanli.isChecked(),
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
        renk_frame.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
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
        d_frame.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 6px; }")
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
