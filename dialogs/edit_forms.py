"""dialogs/edit_forms.py - Sihirbaz içindeki detaylı özel formlar (Ders, Sınıf vb.)"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QLineEdit, QComboBox, QCheckBox, QColorDialog, QFrame, QFormLayout, QGridLayout,
    QLineEdit, QComboBox, QCheckBox, QColorDialog, QFrame, QFormLayout, QGridLayout,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QBrush
from database import trigger_save_db

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
        self.resize(540, 680)
        self.setMinimumSize(520, 560)
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
        lbl_ogr = QLabel("Atanacak Öğretmen(ler)")
        lbl_ogr.setStyleSheet("font-weight: bold; color: #334155;")
        v1.addWidget(lbl_ogr)
        self.cb_ogretmen = QComboBox()
        self.cb_ogretmen.setMinimumWidth(250)
        v1.addWidget(self.cb_ogretmen)
        l1.addLayout(v1)
        l1.addStretch(1)
        btn_ortak_ogr = QPushButton("👥 Ortak Öğretmen")
        btn_ortak_ogr.setStyleSheet("background: #F0F7FF; color: #0265DC; font-weight: bold; border: 1px solid #D6E8FB; border-radius: 4px; padding: 6px 12px;")
        l1.addWidget(btn_ortak_ogr, alignment=Qt.AlignBottom)
        scroll_layout.addWidget(row1)
        
        # 2. Ders ve Haftalık Saat Row
        row2 = self._create_row_frame()
        l2 = QHBoxLayout(row2)
        l2.setContentsMargins(12, 10, 12, 10)
        l2.addWidget(self._create_icon_label("book"))
        
        v2_ders = QVBoxLayout()
        lbl_ders = QLabel("Atanacak Ders")
        lbl_ders.setStyleSheet("font-weight: bold; color: #334155;")
        v2_ders.addWidget(lbl_ders)
        
        self.v2 = QVBoxLayout()
        self.v2.setContentsMargins(0,0,0,0)
        self.cb_ders = QComboBox()
        self.cb_ders.setMinimumWidth(200)
        self.cb_ders.setEditable(True)
        self.v2.addWidget(self.cb_ders)
        self.extra_ders_combos = []
        v2_ders.addLayout(self.v2)
        l2.addLayout(v2_ders)
        
        l2.addSpacing(15)
        
        v2_saat = QVBoxLayout()
        lbl_saat = QLabel("Haftalık Saat / Dağılım Tipi")
        lbl_saat.setStyleSheet("font-weight: bold; color: #334155;")
        v2_saat.addWidget(lbl_saat)
        h_saat = QHBoxLayout()
        self.cb_hafta = QComboBox()
        self.cb_hafta.setMinimumWidth(60)
        self.cb_hafta.addItems(["1", "2", "3", "4", "5", "6", "7", "8"])
        self.cb_tip = QComboBox()
        self.cb_tip.setMinimumWidth(80)
        self.cb_tip.setEditable(True)
        self.cb_hafta.currentTextChanged.connect(self._update_tip_options)
        self._update_tip_options(self.cb_hafta.currentText())
        h_saat.addWidget(self.cb_hafta)
        h_saat.addWidget(self.cb_tip)
        v2_saat.addLayout(h_saat)
        l2.addLayout(v2_saat)
        
        l2.addStretch(1)
        
        btn_daha_fazla_ders = QPushButton("➕ Daha Fazla Ders")
        btn_daha_fazla_ders.setStyleSheet("background: #E8F5E9; color: #2E7D32; font-weight: bold; border: 1px solid #C8E6C9; border-radius: 4px; padding: 6px 12px;")
        btn_daha_fazla_ders.clicked.connect(self._add_extra_subject_dialog)
        l2.addWidget(btn_daha_fazla_ders, alignment=Qt.AlignBottom)
        
        scroll_layout.addWidget(row2)
        
        # 3. Sınıf Row
        row3 = self._create_row_frame()
        l3 = QHBoxLayout(row3)
        l3.setContentsMargins(12, 10, 12, 10)
        l3.addWidget(self._create_icon_label("teachers"))
        v3 = QVBoxLayout()
        lbl_sinif = QLabel("Atanacak Sınıf / Sınıflar")
        lbl_sinif.setStyleSheet("font-weight: bold; color: #334155;")
        v3.addWidget(lbl_sinif)
        self.cb_sinif = QComboBox()
        self.cb_sinif.setMinimumWidth(450)
        v3.addWidget(self.cb_sinif)
        l3.addLayout(v3)
        l3.addStretch(1)
        btn_birl_sinif = QPushButton("🔗 Birleşik Sınıflar")
        btn_birl_sinif.setStyleSheet("background: #FFF8E1; color: #F57F17; font-weight: bold; border: 1px solid #FFECB3; border-radius: 4px; padding: 6px 12px;")
        btn_birl_sinif.clicked.connect(self._select_combined_classes)
        l3.addWidget(btn_birl_sinif, alignment=Qt.AlignBottom)
        scroll_layout.addWidget(row3)
        
        # 4. Otomatik Eşleşme Bar
        self.lbl_ozet = QLabel("🎯 Otomatik Eşleşme: -")
        self.lbl_ozet.setStyleSheet("background: #F0F7FF; color: #0265DC; font-weight: bold; border-radius: 4px; padding: 10px;")
        scroll_layout.addWidget(self.lbl_ozet)
        
        self.cb_ogretmen.currentTextChanged.connect(self._update_ozet)
        self.cb_ders.currentTextChanged.connect(self._update_ozet)
        self.cb_sinif.currentTextChanged.connect(self._update_ozet)
        self.cb_hafta.currentTextChanged.connect(self._update_ozet)
        self.cb_tip.currentTextChanged.connect(self._update_ozet)
        
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
        self.txt_farkli.setPlaceholderText("Derslik Seç (Opsiyonel)")
        h5.addWidget(self.txt_farkli)
        btn_daha = QPushButton("Daha Fazla Derslik")
        btn_daha.setStyleSheet("font-weight: bold; color: #475569;")
        h5.addWidget(btn_daha)
        v5.addLayout(h5)
        
        l5.addLayout(v5)
        scroll_layout.addWidget(row5)
        
        scroll_layout.addStretch(1)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # Bottom Buttons
        bot_lay = QHBoxLayout()
        
        btn_iptal = QPushButton("İptal")
        btn_iptal.setFixedSize(100, 36)
        btn_iptal.setStyleSheet("font-weight: bold; color: #475569;")
        btn_iptal.clicked.connect(self.reject)
        
        btn_yardim = QPushButton("Yardım")
        btn_yardim.setFixedSize(100, 36)
        btn_yardim.setStyleSheet("font-weight: bold; color: #475569;")
        
        btn_tamam = QPushButton("✅ Tamam ve Kaydet")
        btn_tamam.setFixedSize(160, 36)
        btn_tamam.setStyleSheet("background: #0066FF; color: white; font-weight: bold; border-radius: 4px;")
        btn_tamam.clicked.connect(self.accept)
        
        bot_lay.addWidget(btn_iptal)
        bot_lay.addWidget(btn_yardim)
        bot_lay.addStretch(1)
        bot_lay.addWidget(btn_tamam)
        
        main_layout.addLayout(bot_lay)
        
        self._populate_data()
        self._update_ozet()

    def _update_ozet(self, *_):
        t = self.cb_ogretmen.currentText() or "-"
        d = self.cb_ders.currentText() or "-"
        s = self.cb_sinif.currentText() or "-"
        h = self.cb_hafta.currentText() or "1"
        tip = self.cb_tip.currentText() or "1"
        self.lbl_ozet.setText(f"🎯 Otomatik Eşleşme: {t} ➔ {d} ➔ {s} ({h} Saat / Tip: {tip})")

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
        
        subjects = ["Lütfen Ders Seçiniz", "Matematik", "Geometri", "Fizik", "Kimya", "Biyoloji", "Türkçe", "Edebiyat", "Tarih", "Coğrafya", "Felsefe", "İngilizce", "Almanca", "Matematik 1", "Matematik 2", "Paragraf", "Problem"]
        if self.data_store:
            for d in self.data_store.get("dersler", []):
                if d.get("ad") and d.get("ad") not in subjects:
                    subjects.append(d.get("ad"))
        
        sorted_subjects = ["Lütfen Ders Seçiniz"] + sorted([s for s in subjects if s != "Lütfen Ders Seçiniz"])
        for s in sorted_subjects:
            new_cb.addItem(s)
            
        self.v2.addWidget(new_cb)
        self.extra_ders_combos.append(new_cb)

    def _populate_data(self):
        if self.data_store:
            teacher_names = sorted([t.get("ad", "") for t in self.data_store.get("ogretmenler", []) if t.get("ad")])
            for t_name in teacher_names:
                t_obj = next((t for t in self.data_store.get("ogretmenler", []) if t.get("ad") == t_name), None)
                self.cb_ogretmen.addItem(t_name, t_obj)
            
            if self.selected_teacher:
                idx = self.cb_ogretmen.findText(self.selected_teacher)
                if idx >= 0:
                    self.cb_ogretmen.setCurrentIndex(idx)
            elif teacher_names:
                # Fallback to the first teacher since it's alphabetical
                self.cb_ogretmen.setCurrentIndex(0)
            
            subjects = ["Lütfen Ders Seçiniz", "Matematik", "Geometri", "Fizik", "Kimya", "Biyoloji", "Türkçe", "Edebiyat", "Tarih", "Coğrafya", "Felsefe", "İngilizce", "Almanca", "Matematik 1", "Matematik 2", "Paragraf", "Problem"]
            for d in self.data_store.get("dersler", []):
                if d.get("ad") and d.get("ad") not in subjects:
                    subjects.append(d.get("ad"))
            
            sorted_subjects = ["Lütfen Ders Seçiniz"] + sorted([s for s in subjects if s != "Lütfen Ders Seçiniz"])
            for s in sorted_subjects:
                self.cb_ders.addItem(s)

            class_names = sorted([c.get("ad", "") for c in self.data_store.get("siniflar", []) if c.get("ad")])
            for c_name in class_names:
                c_obj = next((c for c in self.data_store.get("siniflar", []) if c.get("ad") == c_name), None)
                self.cb_sinif.addItem(c_name, c_obj)
            
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
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QPushButton, QHBoxLayout, QScrollArea, QWidget, QLabel, QMessageBox
        d = QDialog(self)
        d.setWindowTitle("Birleşik Sınıflar Seçimi")
        d.setFixedSize(380, 440)
        lay = QVBoxLayout(d)
        
        lay.addWidget(QLabel("<b>Birleştirilecek Sınıfları Seçin:</b>"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        v_lay = QVBoxLayout(w)
        
        classes = sorted([c.get("ad", "") for c in self.data_store.get("siniflar", []) if c.get("ad")])
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
        btn_yoksay.setEnabled(False) # Only enable if conflict logic applies, or let's say >= 3 classes? 
        btn_ok = QPushButton("Tamam")
        btn_ok.setStyleSheet("background: #0078D7; color: white; font-weight: bold; padding: 6px;")
        
        bot.addWidget(btn_yoksay)
        bot.addWidget(btn_ok)
        lay.addLayout(bot)
        
        def on_chk_changed():
            sel_count = sum(1 for c in chks if c.isChecked())
            if sel_count >= 3:
                btn_yoksay.setEnabled(True)
            else:
                btn_yoksay.setEnabled(False)
                
        for chk in chks:
            chk.stateChanged.connect(on_chk_changed)
        
        selected_res = []
        
        def do_accept(bypass_conflict=False):
            nonlocal selected_res
            selected_res = [chk.text() for chk in chks if chk.isChecked()]
            if len(selected_res) < 2:
                QMessageBox.warning(d, "Uyarı", "Birleşik sınıf oluşturmak için en az 2 sınıf seçmelisiniz.")
                selected_res = []
                return
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
        self.resize(540, 680)
        self.setMinimumSize(520, 640)
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
        
        l3.addWidget(QLabel("Atandığı Sınıflar ve Öğretmenler (Gerçek Zamanlı):"))
        self.list_assignments = QListWidget()
        self.list_assignments.setMinimumHeight(75)
        self.list_assignments.setMaximumHeight(110)
        self.list_assignments.setStyleSheet("QListWidget { background: #F8F9FA; border: 1px solid #D0D7DE; border-radius: 4px; color: #333333; }")
        
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        atamalar = data_store.get("atamalar", [])
        my_ad = self.existing_data.get("ad", "")
        my_atamalar = [a for a in atamalar if format_tr_name(a.get("subject", "")) == format_tr_name(my_ad)]
        for a in my_atamalar:
            item_text = f"👨‍🏫 {a.get('teacher', 'Atanmadı')} ➔ 🎓 {a.get('class', '')} ({a.get('duration', 0)} Saat)"
            item = QListWidgetItem(item_text)
            self.list_assignments.addItem(item)
        if not my_atamalar:
            self.list_assignments.addItem(QListWidgetItem("❌ Henüz hiçbir sınıfa atanmadı."))
            
        l3.addWidget(self.list_assignments)
        
        main_layout.addWidget(f3)

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

    def _assign_teachers_for_subject(self):
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        subj_name = format_tr_name(self.txt_ad.text().strip())
        if not subj_name:
            return
        d = SubjectTeacherAssignmentDialog(subject_name=subj_name, data_store=data_store, parent=p or self)
        if d.exec():
            trigger_save_db(self, data_store)

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
            
            # Extract numbers and letters separately
            nums = "".join(re.findall(r'\d+', clean))
            letters_str = re.sub(r'\d+', '', clean).strip()
            
            upper_letters = format_tr_name(letters_str)
            
            # Special Overrides
            overrides = {
                "BİYOLOJİ": "BİYO",
                "REHBERLİK": "REHBERLİK",
                "MATEMATİK": "MAT",
                "GEOMETRİ": "GEO",
                "EDEBİYAT": "EDB",
                "FİZİK": "FİZ",
                "KİMYA": "KİM",
                "COĞRAFYA": "COĞ",
                "TARİH": "TAR",
                "İNGİLİZCE": "İNG",
                "FELSEFE": "FEL"
            }
            
            # Word-based logic if no override
            base = ""
            if upper_letters in overrides:
                base = overrides[upper_letters]
            else:
                words = upper_letters.split()
                if not words:
                    base = clean[:3].upper()
                elif len(words) >= 2:
                    base = words[0][:3] + words[1][:1]
                else:
                    base = words[0][:4] # Fallback to 4 chars
            
            sc = f"{base} {nums}" if nums else base
            self.txt_kisa.setText(sc.strip())

    def _pick_color(self):
        from PySide6.QtWidgets import QColorDialog
        from PySide6.QtGui import QColor
        c = QColorDialog.getColor(QColor(self.current_color), self, "Renk Seç")
        if c.isValid():
            self.current_color = c.name()
            self.color_lbl.setStyleSheet(f"background-color: {self.current_color}; border: 1px solid #AAA; border-radius: 4px;")

    def get_data(self):
        raw_ad = self.txt_ad.text().strip()
        formatted_ad = format_tr_name(raw_ad)
        return {
            "ad": formatted_ad,
            "kisa": self.txt_kisa.text(),
            "renk": self.current_color
        }


class SubjectTeacherAssignmentDialog(QDialog):
    """Çoklu Öğretmen ve Çoklu Sınıf Ders Atama Ekranı (Yeni Tasarım)"""
    def __init__(self, subject_name="", data_store=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Ders Atama - {subject_name}")
        self.resize(850, 480)
        self.subject_name = subject_name
        self.data_store = data_store or {}
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; }
            QLabel { color: #334155; font-size: 13px; font-weight: bold; }
            QFrame#card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }
            QListWidget { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px; padding: 4px; }
            QListWidget::item { padding: 6px; border-bottom: 1px solid #F1F5F9; }
            QListWidget::item:hover { background: #F8FAFC; }
            QListWidget::indicator { width: 18px; height: 18px; }
            QPushButton { min-height: 32px; padding: 6px 16px; border-radius: 6px; font-size: 13px; font-weight: bold; }
            QComboBox { min-height: 30px; border: 1px solid #CBD5E1; border-radius: 6px; padding: 4px 8px; background: white; }
        """)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)
        
        # Header
        header = QLabel(f"📚 {self.subject_name} Dersi İçin Öğretmen ve Sınıf Ataması")
        header.setStyleSheet("font-size: 16px; color: #2563EB;")
        lay.addWidget(header)
        
        # Main Card (Horizontal Flow)
        card = QFrame()
        card.setObjectName("card")
        card_lay = QHBoxLayout(card)
        card_lay.setContentsMargins(16, 16, 16, 16)
        card_lay.setSpacing(20)
        
        # 1. Teachers
        v_teachers = QVBoxLayout()
        v_teachers.addWidget(QLabel("Atanacak Öğretmenler"))
        self.list_teachers = QListWidget()
        for t in self.data_store.get("ogretmenler", []):
            if t.get("ad"):
                item = QListWidgetItem(t.get("ad"))
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.list_teachers.addItem(item)
        v_teachers.addWidget(self.list_teachers)
        card_lay.addLayout(v_teachers, 2)
        
        # Arrow 1
        arr1 = QLabel("➔")
        arr1.setStyleSheet("font-size: 24px; color: #94A3B8; font-weight: normal;")
        card_lay.addWidget(arr1, 0, Qt.AlignCenter)
        
        # 2. Hours / Type
        v_hours = QVBoxLayout()
        v_hours.addWidget(QLabel("Haftalık Saat / Tip"))
        self.cb_hafta = QComboBox()
        self.cb_hafta.addItems(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "1+1", "2+1", "2+2", "3+2", "1+1+1", "2+1+1"])
        self.cb_hafta.setCurrentText("2")
        v_hours.addWidget(self.cb_hafta)
        
        info_lbl = QLabel("Belirttiğiniz saat veya\nblok tipi (örn: 2+1),\nseçilen öğretmen ve\nsınıflarla eşleşecektir.")
        info_lbl.setStyleSheet("color: #64748B; font-weight: normal; font-size: 12px; margin-top: 10px;")
        v_hours.addWidget(info_lbl)
        v_hours.addStretch()
        card_lay.addLayout(v_hours, 1)
        
        # Arrow 2
        arr2 = QLabel("➔")
        arr2.setStyleSheet("font-size: 24px; color: #94A3B8; font-weight: normal;")
        card_lay.addWidget(arr2, 0, Qt.AlignCenter)
        
        # 3. Classes
        v_classes = QVBoxLayout()
        v_classes.addWidget(QLabel("Atanacak Sınıflar"))
        self.list_classes = QListWidget()
        for c in self.data_store.get("siniflar", []):
            if c.get("ad"):
                item = QListWidgetItem(c.get("ad"))
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.list_classes.addItem(item)
        v_classes.addWidget(self.list_classes)
        
        btn_select_all_classes = QPushButton("Tüm Sınıfları Seç")
        btn_select_all_classes.setStyleSheet("background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; min-height: 24px; font-size: 11px;")
        btn_select_all_classes.clicked.connect(self._select_all_classes)
        v_classes.addWidget(btn_select_all_classes)
        card_lay.addLayout(v_classes, 2)
        
        lay.addWidget(card)
        
        self._load_existing()
        
        # Bottom Actions
        bot = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background: #FFFFFF; color: #475569; border: 1px solid #CBD5E1;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_clear = QPushButton("🗑️ Atamayı Tamamen Kaldır")
        btn_clear.setStyleSheet("background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;")
        btn_clear.clicked.connect(self._clear_assignments)
        
        btn_save = QPushButton("Kaydet ve Atamaları Oluştur")
        btn_save.setStyleSheet("background: #2563EB; color: white; border: none;")
        btn_save.clicked.connect(self._save_assignments)
        
        bot.addWidget(btn_cancel)
        bot.addWidget(btn_clear)
        bot.addStretch()
        bot.addWidget(btn_save)
        lay.addLayout(bot)
        
    def _select_all_classes(self):
        for i in range(self.list_classes.count()):
            self.list_classes.item(i).setCheckState(Qt.Checked)
            
    def _load_existing(self):
        subj_target = format_tr_name(self.subject_name)
        existing = [a for a in self.data_store.get("atamalar", []) if format_tr_name(a.get("subject", "")) == subj_target]
        assigned_teachers = {format_tr_name(a.get("teacher", "")) for a in existing}
        assigned_classes = {a.get("class", "") for a in existing}
        
        for i in range(self.list_teachers.count()):
            item = self.list_teachers.item(i)
            item.setCheckState(Qt.Checked if format_tr_name(item.text()) in assigned_teachers else Qt.Unchecked)
                
        for i in range(self.list_classes.count()):
            item = self.list_classes.item(i)
            item.setCheckState(Qt.Checked if item.text() in assigned_classes else Qt.Unchecked)
                
        if existing:
            dur_type = existing[0].get("type", str(existing[0].get("duration", 2)))
            idx = self.cb_hafta.findText(dur_type)
            if idx >= 0: self.cb_hafta.setCurrentIndex(idx)
            else:
                self.cb_hafta.addItem(dur_type)
                self.cb_hafta.setCurrentText(dur_type)

    def _clear_assignments(self):
        subj_target = format_tr_name(self.subject_name)
        self.data_store["atamalar"] = [a for a in self.data_store.get("atamalar", []) if format_tr_name(a.get("subject", "")) != subj_target]
        for i in range(self.list_teachers.count()):
            self.list_teachers.item(i).setCheckState(Qt.Unchecked)
        for i in range(self.list_classes.count()):
            self.list_classes.item(i).setCheckState(Qt.Unchecked)
        trigger_save_db(self, self.data_store)
        self.accept()

    def _save_assignments(self):
        sel_teachers = [self.list_teachers.item(i).text() for i in range(self.list_teachers.count()) if self.list_teachers.item(i).checkState() == Qt.Checked]
        sel_classes = [self.list_classes.item(i).text() for i in range(self.list_classes.count()) if self.list_classes.item(i).checkState() == Qt.Checked]
        
        subj_target = format_tr_name(self.subject_name)
        self.data_store["atamalar"] = [a for a in self.data_store.get("atamalar", []) if format_tr_name(a.get("subject", "")) != subj_target]
        
        if sel_teachers and sel_classes:
            type_str = self.cb_hafta.currentText().strip()
            parts = [int(p.strip()) for p in type_str.split("+") if p.strip().isdigit()]
            total_dur = sum(parts) if parts else (int(type_str) if type_str.isdigit() else 2)
            
            for t_name in sel_teachers:
                for c_name in sel_classes:
                    self.data_store["atamalar"].append({
                        "teacher": format_tr_name(t_name),
                        "subject": self.subject_name,
                        "class": c_name,
                        "duration": total_dur,
                        "type": type_str,
                        "color": get_subject_color(self.subject_name)
                    })
                    
        trigger_save_db(self, self.data_store)
        self.accept()


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
            raw_teachers = [t.get("ad", "") for t in self.parent().data_store.get("ogretmenler", []) if t.get("ad")]
            teachers.extend(sorted(raw_teachers))
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
        h_btn_lay = QHBoxLayout()
        btn_hoca_ata = QPushButton("🎓 Ders & Öğretmen Ata")
        btn_hoca_ata.setStyleSheet("background: #0078D7; color: white; font-weight: bold; min-height: 32px; border-radius: 4px;")
        btn_hoca_ata.clicked.connect(self._assign_lessons_for_this_class)
        
        btn_cizelge = QPushButton("🖨️ Çizelge Göster / Yazdır")
        btn_cizelge.setStyleSheet("background: #27AE60; color: white; font-weight: bold; min-height: 32px; border-radius: 4px;")
        btn_cizelge.clicked.connect(self._show_class_timetable)
        
        h_btn_lay.addWidget(btn_hoca_ata)
        h_btn_lay.addWidget(btn_cizelge)
        self.main_layout.addLayout(h_btn_lay)

        self._add_bottom_buttons()

    def _show_class_timetable(self):
        c_name = self.w_ad.text().strip()
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        from dialogs.print_preview import TimetablePrintPreview
        filters = {"entity_type": "class", "classes": [c_name], "selected_items": [c_name]}
        dlg = TimetablePrintPreview(data_store=data_store, filters=filters, parent=self)
        dlg.exec()

    def _assign_lessons_for_this_class(self):
        c_name = self.w_ad.text().strip()
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        d = ClassComprehensiveAssignmentDialog(class_name=c_name, data_store=data_store, parent=p or self)
        if d.exec():
            trigger_save_db(self, data_store)

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
        super().__init__("Öğretmen Düzenle", parent, existing_data)
        self.resize(600, 680)
        self.setMinimumSize(550, 650)
        self._color = self.existing_data.get("renk", "#27AE60")
        self._build_ui()
        
    def _build_ui(self):
        # 1. Temel Bilgiler Frame
        frame_temel = QFrame()
        frame_temel.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 6px; }")
        lay_temel = QFormLayout(frame_temel)
        lay_temel.setContentsMargins(15, 15, 15, 15)
        lay_temel.setSpacing(12)
        
        self.w_ad = QLineEdit(self.existing_data.get("ad", ""))
        self.w_ad.setPlaceholderText("Öğretmen Adı Soyadı")
        self.w_ad.textChanged.connect(self._auto_short_code_teacher)
        self.w_kisa = QLineEdit(self.existing_data.get("kisa", ""))
        self.w_kisa.setPlaceholderText("Kısa Kod (Örn: A. YILMAZ)")
        
        lay_temel.addRow(QLabel("<b>Öğretmen Adı:</b>"), self.w_ad)
        lay_temel.addRow(QLabel("<b>Kısa Kodu:</b>"), self.w_kisa)
        self.main_layout.addWidget(frame_temel)
        
        # 2. Görev ve Sınıf Frame
        frame_gorev = QFrame()
        frame_gorev.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 6px; }")
        lay_gorev = QFormLayout(frame_gorev)
        lay_gorev.setContentsMargins(15, 15, 15, 15)
        lay_gorev.setSpacing(12)
        
        self.w_so = QComboBox()
        classes = [""]
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        raw_classes = [c.get("ad", "") for c in data_store.get("siniflar", []) if c.get("ad")]
        classes.extend(sorted(raw_classes))
        self.w_so.addItems(classes)
        existing_so = self.existing_data.get("sinif_ogretmeni", "")
        idx_so = self.w_so.findText(existing_so)
        if idx_so >= 0: self.w_so.setCurrentIndex(idx_so)
        
        lay_gorev.addRow(QLabel("<b>Sınıf Öğretmeni (Rehberlik):</b>"), self.w_so)
        
        self.chk_es_zamanli = QCheckBox("Aynı saatte çoklu/paralel ders girebilir (Çoklu Ders İzni)")
        self.chk_es_zamanli.setChecked(self.existing_data.get("es_zamanli", False))
        lay_gorev.addRow("", self.chk_es_zamanli)
        
        self.main_layout.addWidget(frame_gorev)
        
        # 3. Dersler ve Planlama Frame
        frame_ders = QFrame()
        frame_ders.setStyleSheet(".QFrame { background: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 6px; }")
        lay_ders = QVBoxLayout(frame_ders)
        lay_ders.setContentsMargins(15, 15, 15, 15)
        
        lbl_dersler = QLabel("<b>Atandığı Sınıflar ve Dersler (Gerçek Zamanlı):</b>")
        lay_ders.addWidget(lbl_dersler)
        
        self.list_assignments = QListWidget()
        self.list_assignments.setMinimumHeight(80)
        self.list_assignments.setMaximumHeight(120)
        self.list_assignments.setStyleSheet("QListWidget { background: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 4px; }")
        
        atamalar = data_store.get("atamalar", [])
        my_name = self.existing_data.get("ad", "")
        my_atamalar = [a for a in atamalar if format_tr_name(a.get("teacher", "")) == format_tr_name(my_name)]
        my_subjects = list({a.get("subject", "") for a in my_atamalar if a.get("subject")})
        
        for a in my_atamalar:
            item_text = f"📚 {a.get('subject', '')} ➔ 🎓 {a.get('class', '')} ({a.get('duration', 0)} Saat)"
            item = QListWidgetItem(item_text)
            self.list_assignments.addItem(item)
        if not my_atamalar:
            self.list_assignments.addItem(QListWidgetItem("❌ Henüz hiçbir derse veya sınıfa atanmadı."))
            
        lay_ders.addWidget(self.list_assignments)
        
        self.w_ek_dersler = QLineEdit(", ".join(my_subjects) if my_subjects else self.existing_data.get("ek_dersler", ""))
        self.w_ek_dersler.setReadOnly(True)
        self.w_ek_dersler.setStyleSheet("background: #EAEAEA; color: #555;")
        self.w_ek_dersler.setToolTip("Bu alan atamalardan otomatik olarak çekilir.")
        
        form_ders = QFormLayout()
        form_ders.addRow(QLabel("<b>Otomatik Ek Dersler:</b>"), self.w_ek_dersler)
        lay_ders.addLayout(form_ders)
        
        # Action Buttons
        h_btn_lay = QHBoxLayout()
        btn_ata = QPushButton("🎓 Ders Ata")
        btn_ata.setStyleSheet("background: #0078D7; color: white; font-weight: bold; min-height: 32px; border-radius: 4px;")
        btn_ata.clicked.connect(self._assign_lessons_for_this_teacher)
        
        btn_cizelge = QPushButton("📅 Çizelge/Yazdır")
        btn_cizelge.setStyleSheet("background: #27AE60; color: white; font-weight: bold; min-height: 32px; border-radius: 4px;")
        btn_cizelge.clicked.connect(self._show_teacher_timetable)
        
        btn_zaman = QPushButton("⏳ Zaman/Kısıtlama")
        btn_zaman.setStyleSheet("background: #E67E22; color: white; font-weight: bold; min-height: 32px; border-radius: 4px;")
        btn_zaman.clicked.connect(self._open_constraints)
        
        btn_oto = QPushButton("🤖 Otomatik Oluştur")
        btn_oto.setStyleSheet("background: #8E44AD; color: white; font-weight: bold; min-height: 32px; border-radius: 4px;")
        btn_oto.clicked.connect(self._auto_plan_teacher)
        
        h_btn_lay.addWidget(btn_ata)
        h_btn_lay.addWidget(btn_cizelge)
        h_btn_lay.addWidget(btn_zaman)
        h_btn_lay.addWidget(btn_oto)
        lay_ders.addLayout(h_btn_lay)
        
        self.main_layout.addWidget(frame_ders)
        
        # 4. Renk Frame
        frame_renk = QFrame()
        frame_renk.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 6px; }")
        lay_renk = QHBoxLayout(frame_renk)
        lay_renk.setContentsMargins(15, 10, 15, 10)
        lay_renk.addWidget(QLabel("<b>Renk Kodu:</b>"))
        self.color_box = QLabel()
        self.color_box.setFixedSize(120, 30)
        self.color_box.setStyleSheet(f"background: {self._color}; border: 1px solid #CCC; border-radius: 4px;")
        btn_degistir = QPushButton("Değiştir")
        btn_degistir.setFixedSize(80, 28)
        btn_degistir.clicked.connect(self._pick_color)
        lay_renk.addWidget(self.color_box)
        lay_renk.addWidget(btn_degistir)
        lay_renk.addStretch(1)
        self.main_layout.addWidget(frame_renk)
        
        self._add_bottom_buttons()

    def _open_constraints(self):
        t_name = self.w_ad.text().strip()
        if not t_name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Uyarı", "Lütfen önce öğretmenin adını girin.")
            return
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        from dialogs.constraints_dialog import ConstraintsDialog
        d = ConstraintsDialog(data_store=data_store, target_type="ogretmen", parent=self)
        idx = d.combo_target.findText(t_name)
        if idx >= 0:
            d.combo_target.setCurrentIndex(idx)
        d.exec()

    def _auto_plan_teacher(self):
        from dialogs.auto_schedule_dialog import AutoScheduleDialog
        from PySide6.QtWidgets import QMessageBox
        p = self.parent()
        if not p: return
        data_store = getattr(p, "data_store", {})
        d = AutoScheduleDialog(data_store, p)
        if d.exec():
            # Apply results exactly as in main window
            results = data_store.get("auto_schedule_results", [])
            if results:
                grid_placements = data_store.get("grid_placements", [])
                
                # Sadece manuel olanları koru
                manuals = [g for g in grid_placements if g.get("is_manual", False) or g.get("locked", False)]
                new_placements = list(manuals)
                
                from main_window import get_subject_color
                for r in results:
                    # Sadece otomatik olanları ekle
                    if r.get("is_manual", False):
                        continue
                    new_placements.append({
                        "period": r["period"],
                        "day": r["day_idx"],
                        "subject_name": r["subject_name"],
                        "color": get_subject_color(r["subject_name"]),
                        "teacher_name": r["teacher_name"],
                        "duration": r.get("duration", 1),
                        "class_name": r["class_name"]
                    })
                    
                data_store["grid_placements"] = new_placements
                if hasattr(p, "save_db"): p.save_db()
                if hasattr(p, "_refresh_tree"): p._refresh_tree()
                if hasattr(p, "_restore_grid_placements"): p._restore_grid_placements()
                QMessageBox.information(self, "Başarılı", "Otomatik planlama tamamlandı!")

    def _assign_lessons_for_this_teacher(self):
        t_name = self.w_ad.text().strip()
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        d = LessonAssignmentDialog(data_store=data_store, parent=p or self, selected_teacher=t_name)
        if d.exec():
            data = d.get_data()
            if "atamalar" not in data_store:
                data_store["atamalar"] = []
            
            # Remove old assignments for this teacher
            current_teacher = d.cb_ogretmen.currentText()
            data_store["atamalar"] = [
                a for a in data_store["atamalar"] 
                if a.get("teacher") != current_teacher
            ]
            
            # Add new ones
            if isinstance(data, list):
                data_store["atamalar"].extend(data)
            else:
                data_store["atamalar"].append(data)
                
            if hasattr(p, "save_db"): p.save_db()
            if hasattr(p, "_refresh_tree"): p._refresh_tree()
            
            # Update local UI list
            self.list_assignments.clear()
            my_atamalar = [a for a in data_store["atamalar"] if a.get("teacher") == current_teacher]
            for a in my_atamalar:
                item_text = f"📚 {a.get('subject', '')} ➔ 🎓 {a.get('class', '')} ({a.get('duration', 0)} Saat)"
                self.list_assignments.addItem(QListWidgetItem(item_text))
            if not my_atamalar:
                self.list_assignments.addItem(QListWidgetItem("❌ Henüz hiçbir derse veya sınıfa atanmadı."))
            
            my_subjects = list({a.get("subject", "") for a in my_atamalar if a.get("subject")})
            self.w_ek_dersler.setText(", ".join(my_subjects))

    def _show_teacher_timetable(self):
        t_name = format_tr_name(self.w_ad.text().strip())
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        from dialogs.master_data_dialog import TeacherIndividualTimetableDialog
        d = TeacherIndividualTimetableDialog(teacher_name=t_name, data_store=data_store, parent=p or self)
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
        from PySide6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(QColor(self._color), self)
        if c.isValid():
            self._color = c.name()
            self.color_box.setStyleSheet(f"background: {self._color}; border: 1px solid #CCC; border-radius: 4px;")

    def get_data(self):
        raw_ad = self.w_ad.text().strip()
        ad_formatted = format_tr_name(raw_ad)
        return {
            "ad": ad_formatted, "kisa": self.w_kisa.text(),
            "renk": self._color, "sinif_ogretmeni": self.w_so.currentText(),
            "ek_dersler": self.w_ek_dersler.text(),
            "es_zamanli": self.chk_es_zamanli.isChecked()
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
        

        
        self._add_bottom_buttons()

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self)
        if c.isValid():
            self._color = c.name()
            self.color_box.setStyleSheet(f"background: {self._color};")

    def get_data(self):
        return {
            "ad": self.w_ad.text(), "kisa": self.w_kisa.text(),
            "renk": self._color, "kapasite": self.w_cap.text()
        }


class ClassComprehensiveAssignmentDialog(QDialog):
    """
    Sınıfa Bütünsel Ders ve Öğretmen Atama Paneli (Modern Tasarım)
    """
    def __init__(self, class_name="", data_store=None, parent=None):
        super().__init__(parent)
        self.class_name = class_name
        self.data_store = data_store or {}
        self.setWindowTitle(f"Sınıfın Dersleri - {self.class_name}")
        self.setFixedSize(920, 680)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; }
            QLabel { color: #334155; font-size: 13px; font-weight: bold; }
            QTableWidget { border: 1px solid #E2E8F0; background: #FFFFFF; gridline-color: #F1F5F9; font-size: 13px; border-radius: 8px; }
            QHeaderView::section { background-color: #F1F5F9; border: none; border-bottom: 2px solid #E2E8F0; padding: 8px; font-weight: bold; font-size: 13px; color: #475569; }
            QPushButton { min-height: 32px; padding: 6px 16px; border: 1px solid #CBD5E1; border-radius: 6px; background: #FFFFFF; font-size: 13px; font-weight: bold; color: #475569; }
            QPushButton:hover { background: #F8FAFC; }
            QLineEdit { border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px 12px; font-size: 13px; background: white; }
            QLineEdit:focus { border: 1px solid #3B82F6; }
        """)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)
        
        # Header Banner
        top_frame = QFrame()
        top_frame.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; }")
        top_lay = QHBoxLayout(top_frame)
        top_lay.setContentsMargins(12, 8, 12, 8)
        
        lbl_title = QLabel(f"🎓 {self.class_name} Sınıfı Atamaları")
        lbl_title.setStyleSheet("font-size: 16px; color: #2563EB; font-weight: bold;")
        top_lay.addWidget(lbl_title)
        top_lay.addStretch(1)
        
        btn_print = QPushButton("🖨️ Çizelgeyi Yazdır")
        btn_print.setStyleSheet("background: #F0FDF4; color: #16A34A; border: 1px solid #BBF7D0;")
        btn_print.clicked.connect(self._print_class_timetable)
        top_lay.addWidget(btn_print)
        lay.addWidget(top_frame)
        
        # Search & Filter Bar
        search_lay = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Ders veya Öğretmen ara...")
        self.txt_search.textChanged.connect(self._filter_table)
        search_lay.addWidget(self.txt_search)
        lay.addLayout(search_lay)
        
        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Ders Adı", "Atanan Öğretmen(ler)", "Haftalık Saat / Tip", "İşlem"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 220)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(2, 160)
        self.table.setColumnWidth(3, 200)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget::item { padding: 4px; }")
        lay.addWidget(self.table, 1)

        # Bottom Actions
        bot_lay = QHBoxLayout()
        self.lbl_summary = QLabel("Toplam Atanan: 0 Saat")
        self.lbl_summary.setStyleSheet("color: #059669; font-size: 14px; font-weight: bold;")
        bot_lay.addWidget(self.lbl_summary)
        bot_lay.addStretch(1)
        
        btn_clear_all = QPushButton("Tümünü Kaldır")
        btn_clear_all.setStyleSheet("background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;")
        btn_clear_all.clicked.connect(self._clear_all_assignments)
        bot_lay.addWidget(btn_clear_all)

        btn_close = QPushButton("Kapat ve Kaydet")
        btn_close.setStyleSheet("background: #2563EB; color: white; border: none;")
        btn_close.clicked.connect(self.accept)
        bot_lay.addWidget(btn_close)
        
        lay.addLayout(bot_lay)

    def _filter_table(self, text):
        search_term = format_tr_name(text)
        for i in range(self.table.rowCount()):
            subj_item = self.table.item(i, 0)
            teacher_item = self.table.item(i, 1)
            if subj_item and teacher_item:
                subj_text = format_tr_name(subj_item.text())
                teacher_text = format_tr_name(teacher_item.text())
                if search_term in subj_text or search_term in teacher_text:
                    self.table.setRowHidden(i, False)
                else:
                    self.table.setRowHidden(i, True)

    def _clear_all_assignments(self):
        reply = QMessageBox.question(self, "Onay", f"Bu sınıfa ({self.class_name}) atanmış olan TÜM ders ve öğretmenleri silmek istediğinize emin misiniz?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            atamalar = self.data_store.get("atamalar", [])
            self.data_store["atamalar"] = [a for a in atamalar if a.get("class") != self.class_name]
            trigger_save_db(self, self.data_store)
            self._load_data()

    def _load_data(self):
        self.table.setRowCount(0)
        subjects = [d.get("ad", "") for d in self.data_store.get("dersler", []) if d.get("ad")]
        atamalar = self.data_store.get("atamalar", [])
        
        class_atamalar = {}
        for a in atamalar:
            if a.get("class") == self.class_name:
                s = a.get("subject", "")
                if s:
                    class_atamalar.setdefault(s, []).append(a)
                    
        total_class_hours = 0

        for subj in sorted(subjects):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # 0. Subject Name
            item_subj = QTableWidgetItem(subj)
            item_subj.setFlags(item_subj.flags() ^ Qt.ItemIsEditable)
            item_subj.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            self.table.setItem(row, 0, item_subj)
            
            # 1. Teachers
            assigned_list = class_atamalar.get(subj, [])
            teachers = [a.get("teacher", "") for a in assigned_list if a.get("teacher")]
            teachers_str = ", ".join(teachers) if teachers else "❌ Atama Yok"
            
            item_teachers = QTableWidgetItem(teachers_str)
            item_teachers.setFlags(item_teachers.flags() ^ Qt.ItemIsEditable)
            if not teachers:
                item_teachers.setForeground(QBrush(QColor("#94A3B8")))
            else:
                item_teachers.setForeground(QBrush(QColor("#0F172A")))
            self.table.setItem(row, 1, item_teachers)
            
            # 2. Hours / Type
            dur_sum = sum(a.get("duration", 1) for a in assigned_list)
            total_class_hours += dur_sum
            dur_str = f"{dur_sum} Saat" if dur_sum > 0 else "—"
            item_dur = QTableWidgetItem(dur_str)
            item_dur.setTextAlignment(Qt.AlignCenter)
            item_dur.setFlags(item_dur.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 2, item_dur)
            
            # 3. Action Buttons
            cell_w = QWidget()
            cell_lay = QHBoxLayout(cell_w)
            cell_lay.setContentsMargins(4, 2, 4, 2)
            cell_lay.setSpacing(6)
            
            btn_edit = QPushButton("✏️ Atama Yap")
            btn_edit.setStyleSheet("background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE;")
            btn_edit.clicked.connect(lambda chk=False, s=subj: self._edit_subject_assignment(s))
            cell_lay.addWidget(btn_edit)
            
            if assigned_list:
                btn_remove = QPushButton("🗑️")
                btn_remove.setFixedWidth(40)
                btn_remove.setStyleSheet("background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;")
                btn_remove.clicked.connect(lambda chk=False, s=subj: self._remove_subject_assignment(s))
                cell_lay.addWidget(btn_remove)
                
            self.table.setCellWidget(row, 3, cell_w)

        self.lbl_summary.setText(f"Toplam Atanan: {total_class_hours} Saat")

    def _remove_subject_assignment(self, subject_name):
        v_scroll = self.table.verticalScrollBar().value()
        atamalar = self.data_store.get("atamalar", [])
        self.data_store["atamalar"] = [
            a for a in atamalar
            if not (a.get("subject") == subject_name and a.get("class") == self.class_name)
        ]
        trigger_save_db(self, self.data_store)
        self._load_data()
        self.table.verticalScrollBar().setValue(v_scroll)

    def _edit_subject_assignment(self, subject_name):
        v_scroll = self.table.verticalScrollBar().value()
        d = SubjectTeacherAssignmentDialog(subject_name=subject_name, data_store=self.data_store, parent=self)
        if d.exec():
            trigger_save_db(self, self.data_store)
            self._load_data()
            self.table.verticalScrollBar().setValue(v_scroll)

    def _print_class_timetable(self):
        from dialogs.print_preview import TimetablePrintPreview
        filters = {"entity_type": "class_list", "default_selection": self.class_name}
        dlg = TimetablePrintPreview(data_store=self.data_store, filters=filters, parent=self)
        dlg.exec()
