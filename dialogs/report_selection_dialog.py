import re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QButtonGroup, 
    QComboBox, QPushButton, QLabel, QFrame, QWidget, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QByteArray, QPointF
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPainterPath, QPen, QBrush, QLinearGradient, QPixmap
)
from PySide6.QtSvg import QSvgRenderer


# ═══════════════════════════════════════════════════════════════════════
# 1. PURE 3D FLOATING VECTOR REPORT ICON WIDGET
# ═══════════════════════════════════════════════════════════════════════
class AppleReport3DIconWidget(QWidget):
    """
    Renders an exquisite 3D isometric floating report & document icon with soft shadow.
    """
    def __init__(self, size=48, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        
        self._svg_template = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="64" height="64">
  <defs>
    <radialGradient id="reportShadow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#000000" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="docGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FFFFFF"/>
      <stop offset="100%" stop-color="#E2E8F0"/>
    </linearGradient>
    <linearGradient id="docGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0071E3"/>
      <stop offset="100%" stop-color="#38BDF8"/>
    </linearGradient>
  </defs>
  <!-- Soft ground shadow -->
  <ellipse cx="50" cy="88" rx="34" ry="7" fill="url(#reportShadow)"/>
  
  <!-- Base Paper Tray -->
  <path d="M 20 54 L 50 70 L 80 54 L 50 38 Z" fill="#CBD5E1"/>
  <path d="M 20 54 L 50 70 L 50 73 L 20 57 Z" fill="#94A3B8"/>
  <path d="M 50 70 L 80 54 L 80 57 L 50 73 Z" fill="#64748B"/>
  
  <!-- Middle Sheet -->
  <path d="M 25 47 L 50 60 L 75 47 L 50 34 Z" fill="url(#docGrad1)"/>
  <path d="M 25 47 L 50 60 L 50 62 L 25 49 Z" fill="#CBD5E1"/>
  <path d="M 50 60 L 75 47 L 75 49 L 50 62 Z" fill="#94A3B8"/>
  
  <!-- Top Document Layer with Blue Gradient -->
  <path d="M 30 38 L 50 49 L 70 38 L 50 27 Z" fill="url(#docGrad2)"/>
  <path d="M 30 38 L 50 49 L 50 51 L 30 40 Z" fill="#0058B3"/>
  <path d="M 50 49 L 70 38 L 70 40 L 50 51 Z" fill="#004691"/>
  
  <!-- Content Lines on Top Document -->
  <line x1="38" y1="35" x2="52" y2="43" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" opacity="0.9"/>
  <line x1="42" y1="33" x2="60" y2="43" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" opacity="0.7"/>
  
  <!-- Glowing Cyan Laser / Print Beam -->
  <line x1="22" y1="51" x2="78" y2="51" stroke="#38BDF8" stroke-width="2" stroke-linecap="round" opacity="0.85"/>
</svg>"""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        renderer = QSvgRenderer(QByteArray(self._svg_template.encode('utf-8')))
        renderer.render(painter, self.rect())
        painter.end()


# ═══════════════════════════════════════════════════════════════════════
# 2. APPLE NATIVE CHEVRON COMBOBOX
# ═══════════════════════════════════════════════════════════════════════
class AppleComboBox(QComboBox):
    """
    Apple native ComboBox featuring custom anti-aliased vector chevron.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 9))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #D1D1D6;
                border-radius: 7px;
                padding: 4px 28px 4px 10px;
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui;
                font-size: 11.5px;
                color: #1D1D1F;
                text-align: left;
            }
            QComboBox:hover {
                border-color: #86868B;
            }
            QComboBox:focus {
                border: 1.5px solid #0071E3;
            }
            QComboBox:disabled {
                background-color: #F5F5F7;
                border-color: #E5E5EA;
                color: #8E8E93;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: none;
            }
            QComboBox::down-arrow {
                image: none;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #D1D1D6;
                border-radius: 8px;
                padding: 4px;
                selection-background-color: #0071E3;
                selection-color: #FFFFFF;
                outline: none;
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui;
                font-size: 11.5px;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        cx = w - 14
        cy = h / 2.0
        
        is_open = self.view().isVisible() if self.view() else False
        is_enabled = self.isEnabled()
        
        pen_color = QColor("#0071E3") if (self.hasFocus() or is_open) else (QColor("#86868B") if is_enabled else QColor("#C7C7CC"))
        pen = QPen(pen_color, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        path = QPainterPath()
        if is_open:
            path.moveTo(cx - 3.5, cy + 1.5)
            path.lineTo(cx, cy - 2.0)
            path.lineTo(cx + 3.5, cy + 1.5)
        else:
            path.moveTo(cx - 3.5, cy - 1.5)
            path.lineTo(cx, cy + 2.0)
            path.lineTo(cx + 3.5, cy - 1.5)
            
        painter.drawPath(path)
        painter.end()


# ═══════════════════════════════════════════════════════════════════════
# 3. MAIN APPLE REPORT SELECTION DIALOG
# ═══════════════════════════════════════════════════════════════════════
class ReportSelectionDialog(QDialog):
    """
    Apple Minimalist Print Preview & Report Selection Sheet.
    """
    def __init__(self, data_store, default_type=None, default_entity=None, is_direct_print=False, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        self.default_type = default_type
        self.default_entity = default_entity
        self.is_direct_print = is_direct_print
        
        self.setWindowTitle("Yazdırma & Baskı Önizleme")
        self.setFixedWidth(620)
        self.setModal(True)
        
        # Clean Apple Sheet Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F7;
            }
            QFrame#card {
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 12px;
            }
            #subPanel {
                background-color: #F8F9FA;
                border: 1px solid #E5E5EA;
                border-radius: 8px;
            }
            QLabel {
                color: #1D1D1F;
                background: transparent;
                border: none;
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui;
            }
            QLabel#sectionLabel {
                font-size: 10px;
                font-weight: 700;
                color: #86868B;
                letter-spacing: 0.5px;
            }
            QRadioButton {
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui;
                font-size: 12px;
                font-weight: 500;
                color: #1D1D1F;
                spacing: 8px;
                background: transparent;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 1.5px solid #C7C7CC;
                background: #FFFFFF;
            }
            QRadioButton::indicator:hover {
                border-color: #8E8E93;
            }
            QRadioButton::indicator:checked {
                border: 1.5px solid #0071E3;
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0.0 #0071E3, stop:0.45 #0071E3, stop:0.55 #FFFFFF, stop:1.0 #FFFFFF);
            }
            QRadioButton:disabled {
                color: #8E8E93;
            }
            QRadioButton::indicator:disabled {
                border-color: #E5E5EA;
                background: #F5F5F7;
            }
            #subPanel QRadioButton {
                font-size: 11.5px;
                font-weight: 500;
                color: #48484A;
                spacing: 6px;
            }
            #subPanel QRadioButton:checked {
                color: #0071E3;
            }
            QPushButton#btnCancel {
                background-color: #FFFFFF;
                color: #1D1D1F;
                border: 1px solid #D1D1D6;
                border-radius: 8px;
                padding: 7px 18px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#btnCancel:hover {
                background-color: #F5F5F7;
            }
            QPushButton#btnAction {
                background-color: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 7px 22px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#btnAction:hover {
                background-color: #0062C4;
            }
        """)
        
        self.selected_report_mode = None
        self.selected_entity_type = None
        self.selected_entity_name = None
        
        self._build_ui()
        self._apply_defaults()

    def _build_ui(self):
        from PySide6.QtWidgets import QSizePolicy
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 18, 20, 18)
        root_layout.setSpacing(12)
        
        # ═══ 1. HEADER (Locked 1px spacing) ═══
        header_widget = QWidget()
        header_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)
        
        self.icon_3d = AppleReport3DIconWidget(size=44)
        header_layout.addWidget(self.icon_3d, 0, Qt.AlignVCenter)
        
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)
        text_layout.setAlignment(Qt.AlignVCenter)
        
        lbl_title = QLabel("Yazdırma & Baskı Önizleme")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #1D1D1F; letter-spacing: -0.2px;")
        
        lbl_sub = QLabel("Yazdırmak veya dışa aktarmak istediğiniz rapor formatını seçin")
        lbl_sub.setStyleSheet("font-size: 11px; color: #86868B;")
        
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_sub)
        header_layout.addLayout(text_layout, 1)
        root_layout.addWidget(header_widget)
        
        self.btn_group = QButtonGroup(self)
        
        # ═══ 2. SINIF RAPORLARI CARD ═══
        card_cls = QFrame()
        card_cls.setObjectName("card")
        card_cls.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        lay_cls = QVBoxLayout(card_cls)
        lay_cls.setContentsMargins(14, 12, 14, 12)
        lay_cls.setSpacing(8)
        
        sec_cls = QLabel("SINIF RAPORLARI & ÇİZELGELERİ")
        sec_cls.setObjectName("sectionLabel")
        lay_cls.addWidget(sec_cls)
        
        self.rb_cls_all_carsaf = QRadioButton("Tüm Sınıflar (Büyük Çarşaf Tablo — Okul Geneli Yatay)")
        self.btn_group.addButton(self.rb_cls_all_carsaf)
        lay_cls.addWidget(self.rb_cls_all_carsaf)
        
        self.rb_cls_all_6li = QRadioButton("Tüm Sınıflar (Yatay Sayfada 6'lı Blok Çizelge)")
        self.btn_group.addButton(self.rb_cls_all_6li)
        lay_cls.addWidget(self.rb_cls_all_6li)
        
        # Single Class Selector Row
        row_single_cls = QHBoxLayout()
        row_single_cls.setSpacing(8)
        self.rb_cls_single = QRadioButton("Tek Bir Sınıf Seç:")
        self.btn_group.addButton(self.rb_cls_single)
        row_single_cls.addWidget(self.rb_cls_single)
        
        self.combo_classes = AppleComboBox()
        self.combo_classes.setMinimumWidth(160)
        self.combo_classes.setFixedHeight(28)
        
        import re
        def cls_sort_key(c):
            m = re.match(r"(\d+)(.*)", str(c).strip())
            return (int(m.group(1)), m.group(2)) if m else (999, str(c))
            
        siniflar = self.data_store.get("siniflar", [])
        c_names = sorted([c.get("ad", "").strip() for c in siniflar if c.get("ad")], key=cls_sort_key)
        for cn in c_names:
            self.combo_classes.addItem(cn)
            
        row_single_cls.addWidget(self.combo_classes)
        row_single_cls.addStretch(1)
        lay_cls.addLayout(row_single_cls)
        
        # Single Class Sub-Panel (Visible only when rb_cls_single is checked)
        self.cls_sub_panel = QFrame()
        self.cls_sub_panel.setObjectName("subPanel")
        lay_sub_cls = QHBoxLayout(self.cls_sub_panel)
        lay_sub_cls.setContentsMargins(12, 8, 12, 8)
        lay_sub_cls.setSpacing(14)
        
        self.btn_sub_cls_group = QButtonGroup(self)
        self.rb_sub_cls_carsaf = QRadioButton("Çarşaf Çizelgesi")
        self.rb_sub_cls_single = QRadioButton("Haftalık Tekil Çizelge")
        self.rb_sub_cls_asgn = QRadioButton("Ders Dağılım && Atama Listesi")
        
        self.btn_sub_cls_group.addButton(self.rb_sub_cls_carsaf)
        self.btn_sub_cls_group.addButton(self.rb_sub_cls_single)
        self.btn_sub_cls_group.addButton(self.rb_sub_cls_asgn)
        self.rb_sub_cls_carsaf.setChecked(True)
        
        lay_sub_cls.addWidget(self.rb_sub_cls_carsaf)
        lay_sub_cls.addWidget(self.rb_sub_cls_single)
        lay_sub_cls.addWidget(self.rb_sub_cls_asgn)
        lay_sub_cls.addStretch(1)
        lay_cls.addWidget(self.cls_sub_panel)
        self.cls_sub_panel.setVisible(False)
        
        root_layout.addWidget(card_cls)
        
        # ═══ 3. ÖĞRETMEN RAPORLARI CARD ═══
        card_t = QFrame()
        card_t.setObjectName("card")
        card_t.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        lay_t = QVBoxLayout(card_t)
        lay_t.setContentsMargins(14, 12, 14, 12)
        lay_t.setSpacing(8)
        
        sec_t = QLabel("ÖĞRETMEN RAPORLARI & ÇİZELGELERİ")
        sec_t.setObjectName("sectionLabel")
        lay_t.addWidget(sec_t)
        
        self.rb_t_all_carsaf = QRadioButton("Tüm Öğretmenler (Büyük Çarşaf Tablo — Okul Geneli)")
        self.btn_group.addButton(self.rb_t_all_carsaf)
        lay_t.addWidget(self.rb_t_all_carsaf)
        
        self.rb_t_all_6li = QRadioButton("Tüm Öğretmenler (Yatay Sayfada 6'lı Blok Çizelge)")
        self.btn_group.addButton(self.rb_t_all_6li)
        lay_t.addWidget(self.rb_t_all_6li)
        
        self.rb_t_all_asgn = QRadioButton("Toplu Ders && Branş Atama Listesi (Tüm Okul)")
        self.btn_group.addButton(self.rb_t_all_asgn)
        lay_t.addWidget(self.rb_t_all_asgn)
        
        self.rb_t_load = QRadioButton("Öğretmenlerin Haftalık Ders Yükü Tablosu")
        self.btn_group.addButton(self.rb_t_load)
        lay_t.addWidget(self.rb_t_load)
        
        # Single Teacher Selector Row
        row_single_t = QHBoxLayout()
        row_single_t.setSpacing(8)
        self.rb_t_single = QRadioButton("Tek Bir Öğretmen Seç:")
        self.btn_group.addButton(self.rb_t_single)
        row_single_t.addWidget(self.rb_t_single)
        
        self.combo_teachers = AppleComboBox()
        self.combo_teachers.setMinimumWidth(200)
        self.combo_teachers.setFixedHeight(28)
        
        ogretmenler = self.data_store.get("ogretmenler", [])
        t_names = sorted([t.get("ad", "").strip() for t in ogretmenler if t.get("ad")])
        for tn in t_names:
            self.combo_teachers.addItem(tn)
            
        row_single_t.addWidget(self.combo_teachers)
        row_single_t.addStretch(1)
        lay_t.addLayout(row_single_t)
        
        # Single Teacher Sub-Panel (Visible only when rb_t_single is checked)
        self.t_sub_panel = QFrame()
        self.t_sub_panel.setObjectName("subPanel")
        lay_sub_t = QHBoxLayout(self.t_sub_panel)
        lay_sub_t.setContentsMargins(12, 8, 12, 8)
        lay_sub_t.setSpacing(14)
        
        self.btn_sub_t_group = QButtonGroup(self)
        self.rb_sub_t_asgn = QRadioButton("Girdiği Sınıflar && Branş Listesi")
        self.rb_sub_t_single = QRadioButton("Haftalık Tekil Çizelge")
        
        self.btn_sub_t_group.addButton(self.rb_sub_t_asgn)
        self.btn_sub_t_group.addButton(self.rb_sub_t_single)
        self.rb_sub_t_asgn.setChecked(True)
        
        lay_sub_t.addWidget(self.rb_sub_t_asgn)
        lay_sub_t.addWidget(self.rb_sub_t_single)
        lay_sub_t.addStretch(1)
        lay_t.addWidget(self.t_sub_panel)
        self.t_sub_panel.setVisible(False)
        
        root_layout.addWidget(card_t)
        root_layout.addStretch(1)
        
        # Connect all radio buttons in group to selection changed handler
        self.btn_group.buttonToggled.connect(self._on_selection_changed)
        
        # ═══ 4. ACTION BUTTONS ═══
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        btn_layout.setSpacing(10)
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        
        btn_action_text = "Yazdır" if self.is_direct_print else "Baskı Önizleme Aç"
        self.btn_action = QPushButton(btn_action_text)
        self.btn_action.setObjectName("btnAction")
        self.btn_action.setCursor(Qt.PointingHandCursor)
        self.btn_action.setDefault(True)
        self.btn_action.clicked.connect(self._on_confirm)
        
        btn_layout.addStretch(1)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_action)
        root_layout.addLayout(btn_layout)

    def _on_selection_changed(self, *args):
        is_cls_single = self.rb_cls_single.isChecked()
        self.cls_sub_panel.setVisible(is_cls_single)
        self.combo_classes.setEnabled(is_cls_single)
        
        is_t_single = self.rb_t_single.isChecked()
        self.t_sub_panel.setVisible(is_t_single)
        self.combo_teachers.setEnabled(is_t_single)
        self.adjustSize()

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
