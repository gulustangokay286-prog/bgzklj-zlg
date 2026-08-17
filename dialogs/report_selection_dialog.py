import re
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QButtonGroup, 
                               QComboBox, QPushButton, QLabel, QGroupBox, QFrame, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

class ReportSelectionDialog(QDialog):
    """
    Kullanıcının yazdırma veya önizleme öncesinde hangi raporu, hangi sınıfı veya
    öğretmeni istediğini eksiksiz ve kristal netliğinde seçmesini sağlayan detaylı diyalog.
    """
    def __init__(self, data_store, default_type=None, default_entity=None, is_direct_print=False, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        self.default_type = default_type
        self.default_entity = default_entity
        self.is_direct_print = is_direct_print
        
        self.setWindowTitle("🖨️ Yazdırma & Baskı Ön İzleme Seçimi")
        self.setMinimumWidth(560)
        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                color: #1E293B;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 14px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: #FFFFFF;
                color: #0F172A;
            }
            QRadioButton {
                font-size: 12px;
                color: #334155;
                spacing: 8px;
                padding: 4px 0;
            }
            QRadioButton:hover {
                color: #0078D7;
            }
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 12px;
                color: #0F172A;
            }
            QComboBox:focus {
                border-color: #0078D7;
            }
            QPushButton {
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        
        self.selected_report_mode = None
        self.selected_entity_type = None
        self.selected_entity_name = None
        
        self._build_ui()
        self._apply_defaults()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)
        
        # Header
        lbl_title = QLabel("📄 Lütfen Yazdırmak / Önizlemek İstediğiniz Raporu Seçin:")
        lbl_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lbl_title.setStyleSheet("color: #0F172A;")
        main_layout.addWidget(lbl_title)
        
        self.btn_group = QButtonGroup(self)
        
        # ── 1. Sınıf Raporları ──────────────────────────────────────────
        grp_classes = QGroupBox("🏫 Sınıf Raporları & Çizelgeleri")
        vbox_cls = QVBoxLayout(grp_classes)
        vbox_cls.setContentsMargins(14, 12, 14, 12)
        vbox_cls.setSpacing(8)
        
        self.rb_cls_all_carsaf = QRadioButton("📋 Tüm Sınıflar (Dev Çarşaf Tablo - Okul Geneli Yatay)")
        self.btn_group.addButton(self.rb_cls_all_carsaf)
        vbox_cls.addWidget(self.rb_cls_all_carsaf)
        
        self.rb_cls_all_6li = QRadioButton("📑 Tüm Sınıflar (Yatay Sayfada 6'lı Blok Çizelge)")
        self.btn_group.addButton(self.rb_cls_all_6li)
        vbox_cls.addWidget(self.rb_cls_all_6li)
        
        # Tek Sınıf Seçimi
        hbox_single_cls = QHBoxLayout()
        self.rb_cls_single = QRadioButton("🎓 Tek Bir Sınıf Seç:")
        self.btn_group.addButton(self.rb_cls_single)
        hbox_single_cls.addWidget(self.rb_cls_single)
        
        self.combo_classes = QComboBox()
        self.combo_classes.setMinimumWidth(180)
        siniflar = self.data_store.get("siniflar", [])
        for c in siniflar:
            c_name = c.get("ad", "").strip()
            if c_name: self.combo_classes.addItem(c_name)
        hbox_single_cls.addWidget(self.combo_classes)
        hbox_single_cls.addStretch()
        vbox_cls.addLayout(hbox_single_cls)
        
        # Tek sınıf için alt seçenekler
        self.cls_sub_panel = QWidget()
        hbox_sub_cls = QHBoxLayout(self.cls_sub_panel)
        hbox_sub_cls.setContentsMargins(26, 0, 0, 0)
        self.btn_sub_cls_group = QButtonGroup(self)
        self.rb_sub_cls_carsaf = QRadioButton("Bu Sınıfın Çarşaf Çizelgesi")
        self.rb_sub_cls_single = QRadioButton("Haftalık Ders Programı (Tekil Çizelge)")
        self.rb_sub_cls_asgn = QRadioButton("Sınıf Dersleri & Atama Listesi")
        self.btn_sub_cls_group.addButton(self.rb_sub_cls_carsaf)
        self.btn_sub_cls_group.addButton(self.rb_sub_cls_single)
        self.btn_sub_cls_group.addButton(self.rb_sub_cls_asgn)
        self.rb_sub_cls_carsaf.setChecked(True)
        hbox_sub_cls.addWidget(self.rb_sub_cls_carsaf)
        hbox_sub_cls.addWidget(self.rb_sub_cls_single)
        hbox_sub_cls.addWidget(self.rb_sub_cls_asgn)
        hbox_sub_cls.addStretch()
        vbox_cls.addWidget(self.cls_sub_panel)
        
        main_layout.addWidget(grp_classes)
        
        # ── 2. Öğretmen Raporları ────────────────────────────────────────
        grp_teachers = QGroupBox("👨‍🏫 Öğretmen Raporları & Çizelgeleri")
        vbox_t = QVBoxLayout(grp_teachers)
        vbox_t.setContentsMargins(14, 12, 14, 12)
        vbox_t.setSpacing(8)
        
        self.rb_t_all_carsaf = QRadioButton("📋 Tüm Öğretmenler (Dev Çarşaf Tablo - Okul Geneli)")
        self.btn_group.addButton(self.rb_t_all_carsaf)
        vbox_t.addWidget(self.rb_t_all_carsaf)
        
        self.rb_t_all_6li = QRadioButton("📑 Tüm Öğretmenler (Yatay Sayfada 6'lı Blok Çizelge)")
        self.btn_group.addButton(self.rb_t_all_6li)
        vbox_t.addWidget(self.rb_t_all_6li)
        
        self.rb_t_all_asgn = QRadioButton("📚 Toplu Ders & Branş Atama Listesi (Tüm Okul)")
        self.btn_group.addButton(self.rb_t_all_asgn)
        vbox_t.addWidget(self.rb_t_all_asgn)
        
        self.rb_t_load = QRadioButton("📊 Tüm Öğretmenlerin Ders Yükü Listesi")
        self.btn_group.addButton(self.rb_t_load)
        vbox_t.addWidget(self.rb_t_load)
        
        # Tek Öğretmen Seçimi
        hbox_single_t = QHBoxLayout()
        self.rb_t_single = QRadioButton("👨‍🏫 Tek Bir Öğretmen Seç:")
        self.btn_group.addButton(self.rb_t_single)
        hbox_single_t.addWidget(self.rb_t_single)
        
        self.combo_teachers = QComboBox()
        self.combo_teachers.setMinimumWidth(220)
        ogretmenler = self.data_store.get("ogretmenler", [])
        for t in ogretmenler:
            t_name = t.get("ad", "").strip()
            if t_name: self.combo_teachers.addItem(t_name)
        hbox_single_t.addWidget(self.combo_teachers)
        hbox_single_t.addStretch()
        vbox_t.addLayout(hbox_single_t)
        
        # Tek öğretmen için alt seçenekler
        self.t_sub_panel = QWidget()
        hbox_sub_t = QHBoxLayout(self.t_sub_panel)
        hbox_sub_t.setContentsMargins(26, 0, 0, 0)
        self.btn_sub_t_group = QButtonGroup(self)
        self.rb_sub_t_asgn = QRadioButton("Bu Öğretmenin Girdiği Sınıflar & Branş Listesi")
        self.rb_sub_t_single = QRadioButton("Haftalık Ders Programı (Tekil Çizelge)")
        self.btn_sub_t_group.addButton(self.rb_sub_t_asgn)
        self.btn_sub_t_group.addButton(self.rb_sub_t_single)
        self.rb_sub_t_asgn.setChecked(True)
        hbox_sub_t.addWidget(self.rb_sub_t_asgn)
        hbox_sub_t.addWidget(self.rb_sub_t_single)
        hbox_sub_t.addStretch()
        vbox_t.addWidget(self.t_sub_panel)
        
        main_layout.addWidget(grp_teachers)
        
        # Signals to enable/disable subpanels
        self.rb_cls_single.toggled.connect(self._on_selection_changed)
        self.rb_t_single.toggled.connect(self._on_selection_changed)
        
        # ── Bottom Action Buttons ─────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 10, 0, 0)
        
        btn_cancel = QPushButton("❌ İptal")
        btn_cancel.setStyleSheet("background-color: #E2E8F0; color: #334155; border: 1px solid #CBD5E1;")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_layout.addStretch()
        
        if not self.is_direct_print:
            self.btn_action = QPushButton("👁️ Baskı Ön İzleme Aç")
            self.btn_action.setStyleSheet("background-color: #0078D7; color: white;")
        else:
            self.btn_action = QPushButton("🖨️ Yazdır")
            self.btn_action.setStyleSheet("background-color: #10B981; color: white;")
            
        self.btn_action.setDefault(True)
        self.btn_action.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self.btn_action)
        
        main_layout.addLayout(btn_layout)

    def _on_selection_changed(self):
        self.cls_sub_panel.setEnabled(self.rb_cls_single.isChecked())
        self.combo_classes.setEnabled(self.rb_cls_single.isChecked())
        self.t_sub_panel.setEnabled(self.rb_t_single.isChecked())
        self.combo_teachers.setEnabled(self.rb_t_single.isChecked())

    def _apply_defaults(self):
        if self.default_type == "class" and self.default_entity:
            self.rb_cls_single.setChecked(True)
            idx = self.combo_classes.findText(self.default_entity)
            if idx >= 0: self.combo_classes.setCurrentIndex(idx)
        elif self.default_type == "root_classes":
            self.rb_cls_all_carsaf.setChecked(True)
        elif self.default_type == "teacher" and self.default_entity:
            self.rb_t_single.setChecked(True)
            idx = self.combo_teachers.findText(self.default_entity)
            if idx >= 0: self.combo_teachers.setCurrentIndex(idx)
        elif self.default_type == "root_teachers":
            self.rb_t_all_carsaf.setChecked(True)
        else:
            self.rb_cls_all_carsaf.setChecked(True)
            
        self._on_selection_changed()

    def _on_confirm(self):
        # Determine mode & target
        if self.rb_cls_all_carsaf.isChecked():
            self.selected_report_mode = "Toplu Çarşaf Liste : Sınıflar"
            self.selected_entity_type = "classes_all"
            self.selected_entity_name = None
        elif self.rb_cls_all_6li.isChecked():
            self.selected_report_mode = "[BİREBİR] Tüm Sınıflar (Yatay Sayfada 6'lı Çizelge)"
            self.selected_entity_type = "classes_all"
            self.selected_entity_name = None
        elif self.rb_cls_single.isChecked():
            c_name = self.combo_classes.currentText()
            self.selected_entity_type = "class"
            self.selected_entity_name = c_name
            if self.rb_sub_cls_carsaf.isChecked():
                self.selected_report_mode = "Toplu Çarşaf Liste : Sınıflar"
            elif self.rb_sub_cls_single.isChecked():
                self.selected_report_mode = "Sınıf Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)"
            else:
                self.selected_report_mode = "Sınıf Dersleri & Atama Listesi (Liste Formatı)"
        elif self.rb_t_all_carsaf.isChecked():
            self.selected_report_mode = "Toplu Çarşaf Liste : Öğretmenler"
            self.selected_entity_type = "teachers_all"
            self.selected_entity_name = None
        elif self.rb_t_all_6li.isChecked():
            self.selected_report_mode = "[BİREBİR] Tüm Öğretmenler (Yatay Sayfada 6'lı Çizelge)"
            self.selected_entity_type = "teachers_all"
            self.selected_entity_name = None
        elif self.rb_t_all_asgn.isChecked():
            self.selected_report_mode = "Sınıf Dersleri & Atama Listesi (Liste Formatı)"
            self.selected_entity_type = "teachers_all"
            self.selected_entity_name = None
        elif self.rb_t_load.isChecked():
            self.selected_report_mode = "Tüm Öğretmenlerin Ders Yükü Listesi"
            self.selected_entity_type = "teachers_all"
            self.selected_entity_name = None
        elif self.rb_t_single.isChecked():
            t_name = self.combo_teachers.currentText()
            self.selected_entity_type = "teacher"
            self.selected_entity_name = t_name
            if self.rb_sub_t_asgn.isChecked():
                self.selected_report_mode = "Sınıf Dersleri & Atama Listesi (Liste Formatı)"
            else:
                self.selected_report_mode = "Öğretmen Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)"
        else:
            self.selected_report_mode = "Toplu Çarşaf Liste : Sınıflar"
            self.selected_entity_type = "classes_all"
            self.selected_entity_name = None

        self.accept()

    def get_result(self):
        return {
            "mode": self.selected_report_mode,
            "entity_type": self.selected_entity_type,
            "entity_name": self.selected_entity_name
        }
