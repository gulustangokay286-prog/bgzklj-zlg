"""
relations_dialog.py – Planlama İlişkileri ve Gelişmiş Ders Bağıntıları Yönetimi
aSc Timetables birebir kopyası – gerçek zamanlı kaydetme ve A* entegrasyonu.
Apple Studio & Minimalist Tasarım Felsefesi (Sıfır Emoji, Vektörel İkonlar, Silindirik Butonlar).
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFrame, QCheckBox, QGroupBox, QSpinBox, QListWidget, QAbstractItemView,
    QWidget, QListWidgetItem, QLineEdit, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QRectF, QPointF, QSize
from PySide6.QtGui import QFont, QColor, QBrush, QIcon, QPixmap, QPainter, QPen, QPainterPath
from database import trigger_save_db

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"


# ─── Vektörel İkon Çizim Motoru (Retina 2x, Sıfır Emoji) ─────────
def make_vector_icon(name: str, size: int = 16, color_hex: str = "#0F172A") -> QIcon:
    scale = 2
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(scale, scale)
    color = QColor(color_hex)
    
    if name == 'plus':
        p.setPen(QPen(color, 2.0, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(size / 2.0, 3.5), QPointF(size / 2.0, size - 3.5))
        p.drawLine(QPointF(3.5, size / 2.0), QPointF(size - 3.5, size / 2.0))
        
    elif name == 'edit':
        p.setPen(QPen(color, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(size - 4, 3)
        path.lineTo(size - 3, 4)
        path.lineTo(5.5, size - 3)
        path.lineTo(3, size - 3)
        path.lineTo(3, size - 5.5)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(size - 6, 5), QPointF(size - 3, 8))
        
    elif name == 'trash':
        p.setPen(QPen(color, 1.3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        # Lid
        p.drawLine(QPointF(3, 4.5), QPointF(size - 3, 4.5))
        p.drawLine(QPointF(size/2.0 - 2.5, 2.5), QPointF(size/2.0 + 2.5, 2.5))
        # Bin body
        path = QPainterPath()
        path.moveTo(4.5, 4.5)
        path.lineTo(5.5, size - 2.5)
        path.lineTo(size - 5.5, size - 2.5)
        path.lineTo(size - 4.5, 4.5)
        p.drawPath(path)
        p.drawLine(QPointF(size/2.0 - 2, 7), QPointF(size/2.0 - 2, size - 5))
        p.drawLine(QPointF(size/2.0 + 2, 7), QPointF(size/2.0 + 2, size - 5))
        
    elif name == 'search':
        p.setPen(QPen(color, 1.4, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(3, 3, size - 7.5, size - 7.5))
        p.drawLine(QPointF(size - 5.5, size - 5.5), QPointF(size - 2.5, size - 2.5))
        
    elif name == 'check':
        p.setPen(QPen(color, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(QPointF(3, size * 0.52), QPointF(size * 0.42, size - 3.5))
        p.drawLine(QPointF(size * 0.42, size - 3.5), QPointF(size - 3, 3.5))
        
    elif name == 'cross':
        p.setPen(QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(4, 4), QPointF(size - 4, size - 4))
        p.drawLine(QPointF(size - 4, 4), QPointF(4, size - 4))
        
    elif name == 'rules':
        # Elegant Clipboard / Document with check lines
        p.setPen(QPen(color, 1.3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(2.5, 2.5, size - 5, size - 5), 2.5, 2.5)
        p.drawLine(QPointF(5.5, 6), QPointF(size - 5.5, 6))
        p.drawLine(QPointF(5.5, 9.5), QPointF(size - 5.5, 9.5))
        p.drawLine(QPointF(5.5, 13), QPointF(size - 8.5, 13))
        
    p.end()
    pix.setDevicePixelRatio(scale)
    return QIcon(pix)


# ─── Gelişmiş Arama & Çoklu Seçim Popup ──────────────────────────
class MultiSelectDialog(QDialog):
    def __init__(self, items, selected_items, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(380, 500)
        self.setStyleSheet(f"""
            QDialog {{ background: #F8FAFC; font-family: {FONT_FAMILY}; }}
            QLineEdit {{
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 7px 12px;
                font-size: 13px;
                color: #0F172A;
            }}
            QLineEdit:focus {{
                border-color: #0071E3;
            }}
            QListWidget {{
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                font-size: 13px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 8px 10px;
                border-radius: 6px;
                margin-bottom: 2px;
                color: #1E293B;
            }}
            QListWidget::item:hover {{
                background: #F1F5F9;
            }}
            QListWidget::item:selected {{
                background: #EFF6FF;
                color: #0071E3;
                font-weight: 600;
            }}
        """)
        self.all_items = list(items)
        self.selected = set(selected_items)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        lbl = QLabel(title)
        lbl.setFont(QFont(FONT_FAMILY, 12, QFont.Bold))
        lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        layout.addWidget(lbl)

        # Hızlı arama filtresi
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Listede filtrele...")
        self.search_input.textChanged.connect(self._filter_list)
        layout.addWidget(self.search_input)

        # Hızlı seçim butonları (Silindirik / Pill)
        btn_quick_lay = QHBoxLayout()
        btn_quick_lay.setSpacing(8)
        
        btn_sel_all = QPushButton(" Tümünü Seç")
        btn_sel_all.setIcon(make_vector_icon("check", 13, "#0071E3"))
        btn_sel_all.setFixedHeight(28)
        btn_sel_all.setCursor(Qt.PointingHandCursor)
        btn_sel_all.setStyleSheet("""
            QPushButton {
                background: #EFF6FF;
                color: #0071E3;
                border: 1px solid #BFDBFE;
                border-radius: 14px;
                font-size: 11px;
                font-weight: 600;
                padding: 0 12px;
            }
            QPushButton:hover { background: #DBEAFE; }
        """)
        
        btn_sel_none = QPushButton(" Temizle")
        btn_sel_none.setIcon(make_vector_icon("cross", 11, "#64748B"))
        btn_sel_none.setFixedHeight(28)
        btn_sel_none.setCursor(Qt.PointingHandCursor)
        btn_sel_none.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #64748B;
                border: 1px solid #CBD5E1;
                border-radius: 14px;
                font-size: 11px;
                font-weight: 600;
                padding: 0 12px;
            }
            QPushButton:hover { background: #F8FAFC; color: #0F172A; }
        """)
        
        btn_sel_all.clicked.connect(self._select_all)
        btn_sel_none.clicked.connect(self._select_none)
        btn_quick_lay.addWidget(btn_sel_all)
        btn_quick_lay.addWidget(btn_sel_none)
        btn_quick_lay.addStretch()
        layout.addLayout(btn_quick_lay)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.list_widget, 1)

        self._populate_list()

        # Alt Butonlar (Silindirik / Pill)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedHeight(34)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 17px;
                font-size: 12px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover { background: #F8FAFC; color: #0F172A; }
        """)
        
        btn_ok = QPushButton(" Uygula")
        btn_ok.setIcon(make_vector_icon("check", 14, "#FFFFFF"))
        btn_ok.setFixedHeight(34)
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 17px;
                font-size: 12px;
                font-weight: 600;
                padding: 0 24px;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def _populate_list(self, filter_text=""):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.isSelected():
                self.selected.add(item.text())
            else:
                self.selected.discard(item.text())

        self.list_widget.clear()
        filter_lower = filter_text.strip().lower()

        for item_text in sorted(self.all_items):
            if not filter_lower or filter_lower in item_text.lower():
                list_item = QListWidgetItem(item_text)
                self.list_widget.addItem(list_item)
                if item_text in self.selected:
                    list_item.setSelected(True)

    def _filter_list(self, text):
        self._populate_list(text)

    def _select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setSelected(True)
            self.selected.add(self.list_widget.item(i).text())

    def _select_none(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setSelected(False)
            self.selected.discard(self.list_widget.item(i).text())

    def get_selected(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.isSelected():
                self.selected.add(item.text())
            else:
                self.selected.discard(item.text())
        return sorted(list(self.selected))


# ─── Tek Kural Düzenleme Popup ────────────────────────────────────
class EditRelationDialog(QDialog):
    def __init__(self, data_store, relation_data=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        self.relation_data = relation_data or {}

        self.setWindowTitle("Planlama Kuralı Düzenle")
        self.resize(640, 560)

        self.setStyleSheet(f"""
            QDialog {{
                background: #F8FAFC;
                font-family: {FONT_FAMILY};
            }}
            QGroupBox {{
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                margin-top: 14px;
                font-weight: bold;
                padding: 16px 14px 14px 14px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 10px;
                color: #0F172A;
                font-size: 12px;
                font-weight: 700;
            }}
            QComboBox, QSpinBox {{
                border: 1px solid #CBD5E1;
                padding: 6px 10px;
                background: #FFFFFF;
                border-radius: 8px;
                font-size: 12.5px;
                color: #0F172A;
            }}
            QComboBox:focus, QSpinBox:focus {{
                border-color: #0071E3;
            }}
            QLabel {{
                color: #334155;
                font-size: 12px;
                font-weight: 500;
            }}
        """)

        self.selected_subjects = []
        self.selected_teachers = []
        self.selected_classes = []

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 1. Kural Seçimi
        grp_rule = QGroupBox("Kural Seçimi")
        rule_lay = QVBoxLayout(grp_rule)

        self.cb_rule = QComboBox()
        self.rules = [
            "Günde maksimum ders sayısı",
            "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun",
            "Aynı ders aynı gün tekrar etmesin",
            "Dersler haftanın günlerine eşit dağıtılsın",
            "Seçilen dersler aynı gün peş peşe gelsin",
            "İki ders aynı güne gelmesin",
            "Öğretmenin dersleri öğleden önce toplansın",
            "Öğretmenin dersleri öğleden sonra toplansın",
            "Son ders saatine zor ders konulmasın",
            "X dersi belirli saatlerde kalmalı",
            "İki zor ders art arda gelmesin",
        ]
        self.cb_rule.addItems(self.rules)
        self.cb_rule.setStyleSheet(f"font-size: 13px; font-weight: 700; color: #0071E3; font-family: {FONT_FAMILY};")
        self.cb_rule.currentIndexChanged.connect(self._rule_changed)
        rule_lay.addWidget(self.cb_rule)
        main_layout.addWidget(grp_rule)

        # 2. Filtreler
        grp_filters = QGroupBox("Uygulanacak Filtreler")
        filter_layout = QVBoxLayout(grp_filters)
        filter_layout.setSpacing(10)

        def _make_pill_btn(text, callback):
            b = QPushButton(text)
            b.setFixedWidth(74)
            b.setFixedHeight(28)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton {
                    background: #F1F5F9;
                    color: #0F172A;
                    border: 1px solid #CBD5E1;
                    border-radius: 14px;
                    font-size: 11.5px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #E2E8F0;
                    border-color: #0071E3;
                    color: #0071E3;
                }
            """)
            b.clicked.connect(callback)
            return b

        # Dersler
        lay_subj = QHBoxLayout()
        lbl_s = QLabel("Dersler:")
        lbl_s.setFixedWidth(80)
        lay_subj.addWidget(lbl_s)
        self.cb_subj = QComboBox()
        self.cb_subj.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cb_subj.currentIndexChanged.connect(self._on_subj_combo_changed)
        self.btn_subj = _make_pill_btn("Seç", self._change_subjects)
        lay_subj.addWidget(self.cb_subj)
        lay_subj.addWidget(self.btn_subj)
        filter_layout.addLayout(lay_subj)

        # Öğretmenler
        lay_teach = QHBoxLayout()
        lbl_t = QLabel("Öğretmenler:")
        lbl_t.setFixedWidth(80)
        lay_teach.addWidget(lbl_t)
        self.cb_teach = QComboBox()
        self.cb_teach.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cb_teach.currentIndexChanged.connect(self._on_teach_combo_changed)
        self.btn_teach = _make_pill_btn("Seç", self._change_teachers)
        lay_teach.addWidget(self.cb_teach)
        lay_teach.addWidget(self.btn_teach)
        filter_layout.addLayout(lay_teach)

        # Sınıflar
        lay_class = QHBoxLayout()
        lbl_c = QLabel("Sınıflar:")
        lbl_c.setFixedWidth(80)
        lay_class.addWidget(lbl_c)
        self.cb_class = QComboBox()
        self.cb_class.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cb_class.currentIndexChanged.connect(self._on_class_combo_changed)
        self.btn_class = _make_pill_btn("Seç", self._change_classes)
        lay_class.addWidget(self.cb_class)
        lay_class.addWidget(self.btn_class)
        filter_layout.addLayout(lay_class)
        main_layout.addWidget(grp_filters)

        # 3. Parametreler
        grp_param = QGroupBox("Parametre Ayarları")
        param_lay = QHBoxLayout(grp_param)
        self.lbl_param = QLabel("Maksimum günlük ders saati:")
        self.spin_param = QSpinBox()
        self.spin_param.setRange(1, 15)
        self.spin_param.setValue(2)
        param_lay.addWidget(self.lbl_param)
        param_lay.addWidget(self.spin_param)

        self.lbl_period = QLabel("Saat aralığı (örn: 1-4):")
        self.cb_period_start = QSpinBox()
        self.cb_period_start.setRange(1, 12)
        self.cb_period_start.setValue(1)
        self.cb_period_end = QSpinBox()
        self.cb_period_end.setRange(1, 12)
        self.cb_period_end.setValue(4)
        param_lay.addWidget(self.lbl_period)
        param_lay.addWidget(self.cb_period_start)
        param_lay.addWidget(QLabel("-"))
        param_lay.addWidget(self.cb_period_end)

        param_lay.addStretch()
        self.param_group = grp_param
        main_layout.addWidget(grp_param)

        # 4. Önem
        grp_imp = QGroupBox("Önem Derecesi")
        imp_lay = QHBoxLayout(grp_imp)
        self.cb_imp = QComboBox()
        self.cb_imp.addItems(["Sıkı (Kesinlikle uygulanmalı)", "Yüksek", "Normal", "Düşük (Mümkünse)"])
        self.cb_imp.setCurrentIndex(0)
        imp_lay.addWidget(self.cb_imp)
        main_layout.addWidget(grp_imp)

        main_layout.addStretch(1)

        # Alt Butonlar (Silindirik / Pill)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 17px;
                font-size: 12.5px;
                font-weight: 600;
                padding: 0 22px;
            }
            QPushButton:hover { background: #F8FAFC; color: #0F172A; }
        """)

        self.btn_ok = QPushButton(" Kaydet")
        self.btn_ok.setIcon(make_vector_icon("check", 14, "#FFFFFF"))
        self.btn_ok.setFixedHeight(34)
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.setStyleSheet("""
            QPushButton {
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 17px;
                font-size: 12.5px;
                font-weight: 700;
                padding: 0 26px;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        main_layout.addLayout(btn_layout)

        self._refresh_combos_ui()

    def _refresh_combos_ui(self):
        # 1. Dersler
        self.cb_subj.blockSignals(True)
        self.cb_subj.clear()
        self.cb_subj.addItem("Tüm dersler")
        if self.selected_subjects:
            txt = f"Seçili ({len(self.selected_subjects)} ders): {', '.join(self.selected_subjects[:3])}{'...' if len(self.selected_subjects) > 3 else ''}"
            self.cb_subj.addItem(txt)
            self.cb_subj.setCurrentIndex(1)
        else:
            self.cb_subj.addItem("Seçili dersler...")
            self.cb_subj.setCurrentIndex(0)
        self.cb_subj.blockSignals(False)

        # 2. Öğretmenler
        self.cb_teach.blockSignals(True)
        self.cb_teach.clear()
        self.cb_teach.addItem("Tüm öğretmenler")
        if self.selected_teachers:
            txt = f"Seçili ({len(self.selected_teachers)} öğretmen): {', '.join(self.selected_teachers[:3])}{'...' if len(self.selected_teachers) > 3 else ''}"
            self.cb_teach.addItem(txt)
            self.cb_teach.setCurrentIndex(1)
        else:
            self.cb_teach.addItem("Seçili öğretmenler...")
            self.cb_teach.setCurrentIndex(0)
        self.cb_teach.blockSignals(False)

        # 3. Sınıflar
        self.cb_class.blockSignals(True)
        self.cb_class.clear()
        self.cb_class.addItem("Tüm sınıflar")
        if self.selected_classes:
            txt = f"Seçili ({len(self.selected_classes)} sınıf): {', '.join(self.selected_classes[:3])}{'...' if len(self.selected_classes) > 3 else ''}"
            self.cb_class.addItem(txt)
            self.cb_class.setCurrentIndex(1)
        else:
            self.cb_class.addItem("Seçili sınıflar...")
            self.cb_class.setCurrentIndex(0)
        self.cb_class.blockSignals(False)

    def _on_subj_combo_changed(self, idx):
        if idx == 1 and not self.selected_subjects:
            self._change_subjects()

    def _on_teach_combo_changed(self, idx):
        if idx == 1 and not self.selected_teachers:
            self._change_teachers()

    def _on_class_combo_changed(self, idx):
        if idx == 1 and not self.selected_classes:
            self._change_classes()

    def _rule_changed(self):
        rule = self.cb_rule.currentText()
        show_max = rule in ["Günde maksimum ders sayısı", "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun"]
        show_period = rule == "X dersi belirli saatlerde kalmalı"

        if rule == "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun":
            self.lbl_param.setText("Maksimum günlük ders saati:")
            self.spin_param.setValue(2)
            if not self.selected_subjects:
                def is_practical(name):
                    norm = str(name).replace("i", "İ").replace("ı", "I").upper()
                    return any(k in norm for k in ["BEDEN", "MÜZ", "MUZ", "GÖR", "GOR", "RES", "SANAT", "SPOR", "UYGULAMA", "ATÖLYE", "ATOLYE"])
                practical = []
                for d in self.data_store.get("dersler", []):
                    if is_practical(d.get("ad", "")):
                        practical.append(d.get("ad", ""))
                for a in self.data_store.get("atamalar", []):
                    if is_practical(a.get("subject", "")) and a.get("subject") not in practical:
                        practical.append(a.get("subject"))
                if practical:
                    self.selected_subjects = practical
                    self._refresh_combos_ui()
        elif rule == "Günde maksimum ders sayısı":
            self.lbl_param.setText("Maksimum günlük ders saati:")
            if self.spin_param.value() > 4:
                self.spin_param.setValue(2)

        self.lbl_param.setVisible(show_max)
        self.spin_param.setVisible(show_max)
        self.lbl_period.setVisible(show_period)
        self.cb_period_start.setVisible(show_period)
        self.cb_period_end.setVisible(show_period)

        for i in range(self.param_group.layout().count()):
            w = self.param_group.layout().itemAt(i).widget()
            if isinstance(w, QLabel) and w.text() == "-":
                w.setVisible(show_period)

        self.param_group.setVisible(show_max or show_period)

    def _change_subjects(self):
        items_set = set()
        for d in self.data_store.get("dersler", []):
            if d.get("ad"): items_set.add(d.get("ad"))
        for a in self.data_store.get("atamalar", []):
            if a.get("subject"): items_set.add(a.get("subject"))
        items = sorted(list(items_set))
        if not items:
            items = ["Matematik", "Türkçe", "Fizik", "Kimya", "Biyoloji", "Beden Eğitimi", "İngilizce", "Görsel Sanatlar", "Müzik"]

        d = MultiSelectDialog(items, self.selected_subjects, "Dersleri Seç", self)
        if d.exec():
            self.selected_subjects = d.get_selected()
            self._refresh_combos_ui()

    def _change_teachers(self):
        items_set = set()
        for t in self.data_store.get("ogretmenler", []):
            if t.get("ad"): items_set.add(t.get("ad"))
        for a in self.data_store.get("atamalar", []):
            if a.get("teacher") and a.get("teacher") not in ["—", "Atanmadı"]: items_set.add(a.get("teacher"))
        items = sorted(list(items_set))

        d = MultiSelectDialog(items, self.selected_teachers, "Öğretmenleri Seç", self)
        if d.exec():
            self.selected_teachers = d.get_selected()
            self._refresh_combos_ui()

    def _change_classes(self):
        items_set = set()
        for s in self.data_store.get("siniflar", []):
            if s.get("ad"): items_set.add(s.get("ad"))
        for a in self.data_store.get("atamalar", []):
            if a.get("class"): items_set.add(a.get("class"))
        items = sorted(list(items_set))

        d = MultiSelectDialog(items, self.selected_classes, "Sınıfları Seç", self)
        if d.exec():
            self.selected_classes = d.get_selected()
            self._refresh_combos_ui()

    def _load_data(self):
        if self.relation_data:
            rule_text = self.relation_data.get("kural", "")
            idx = self.cb_rule.findText(rule_text)
            if idx >= 0:
                self.cb_rule.setCurrentIndex(idx)

            self.selected_subjects = list(self.relation_data.get("dersler", []))
            self.selected_teachers = list(self.relation_data.get("ogretmenler", []))
            self.selected_classes = list(self.relation_data.get("siniflar", []))

            self.spin_param.setValue(self.relation_data.get("parametre") or 2)
            self.cb_period_start.setValue(self.relation_data.get("period_start") or 1)
            self.cb_period_end.setValue(self.relation_data.get("period_end") or 4)

            imp = self.relation_data.get("onem", "Sıkı (Kesinlikle uygulanmalı)")
            idx_imp = self.cb_imp.findText(imp)
            if idx_imp >= 0:
                self.cb_imp.setCurrentIndex(idx_imp)

        self._refresh_combos_ui()
        self._rule_changed()

    def get_data(self):
        rule = self.cb_rule.currentText()
        has_param = rule in ["Günde maksimum ders sayısı", "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun"]
        has_period = rule == "X dersi belirli saatlerde kalmalı"
        return {
            "aktif": self.relation_data.get("aktif", True),
            "kural": rule,
            "dersler": self.selected_subjects if self.cb_subj.currentIndex() == 1 else [],
            "ogretmenler": self.selected_teachers if self.cb_teach.currentIndex() == 1 else [],
            "siniflar": self.selected_classes if self.cb_class.currentIndex() == 1 else [],
            "parametre": self.spin_param.value() if has_param else None,
            "period_start": self.cb_period_start.value() if has_period else None,
            "period_end": self.cb_period_end.value() if has_period else None,
            "onem": self.cb_imp.currentText()
        }


# ─── Ana Planlama İlişkileri Yöneticisi ──────────────────────────
class PlanningRelationsDialog(QDialog):
    def __init__(self, data_store=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        if "planlama_iliskileri" not in self.data_store:
            self.data_store["planlama_iliskileri"] = []

        self.setWindowTitle("Planlama İlişkileri — Ders Kısıtlamaları ve Kurallar")
        self.resize(960, 600)
        self.setStyleSheet(f"""
            QDialog {{
                background: #F8FAFC;
                font-family: {FONT_FAMILY};
            }}
            QTableWidget {{
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                gridline-color: #F1F5F9;
                font-size: 12.5px;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 6px 10px;
                border-bottom: 1px solid #F1F5F9;
            }}
            QTableWidget::item:selected {{
                background: #EFF6FF;
                color: #0071E3;
            }}
            QHeaderView::section {{
                background: #F8FAFC;
                border: none;
                border-bottom: 1.5px solid #E2E8F0;
                padding: 8px 10px;
                font-weight: 700;
                font-size: 12px;
                color: #475569;
                font-family: {FONT_FAMILY};
            }}
            QScrollBar:vertical {{
                background: #F8FAFC;
                width: 7px;
                border-radius: 3.5px;
            }}
            QScrollBar::handle:vertical {{
                background: #CBD5E1;
                border-radius: 3.5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #94A3B8;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self._build_ui()
        self._load_table()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(14)

        # Üst Başlık Kartı (Ferah & Vektörel İkonlu)
        header_card = QFrame(self)
        header_card.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 4px;")
        h_lay = QHBoxLayout(header_card)
        h_lay.setContentsMargins(14, 12, 14, 12)
        h_lay.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_vector_icon("rules", 26, "#0071E3").pixmap(26, 26))
        h_lay.addWidget(icon_lbl, 0, Qt.AlignTop)

        text_lay = QVBoxLayout()
        text_lay.setContentsMargins(0, 0, 0, 0)
        text_lay.setSpacing(3)

        lbl_title = QLabel("Planlama İlişkileri ve Gelişmiş Bağıntılar")
        lbl_title.setFont(QFont(FONT_FAMILY, 13, QFont.Bold))
        lbl_title.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        text_lay.addWidget(lbl_title)

        lbl_desc = QLabel("Otomatik ve manuel planlama sırasında uygulanacak pedagojik kısıtlamaları ve kuralları buradan yönetebilirsiniz. Aktif kurallar optimizasyon algoritmasında öncelikli olarak uygulanır.")
        lbl_desc.setFont(QFont(FONT_FAMILY, 9.5))
        lbl_desc.setStyleSheet("color: #64748B; background: transparent; border: none;")
        lbl_desc.setWordWrap(True)
        text_lay.addWidget(lbl_desc)

        h_lay.addLayout(text_lay, 1)
        main_layout.addWidget(header_card)

        # Tablo
        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(["Aktif", "Kural", "Dersler", "Sınıflar", "Öğretmenler", "Önem"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 140)
        self.table.setColumnWidth(5, 110)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.itemDoubleClicked.connect(self._edit_relation)
        self.table.itemChanged.connect(self._on_checkbox_changed)
        main_layout.addWidget(self.table, 1)

        # Alt Bilgi ve Buton Alanı
        bot_bar = QHBoxLayout()
        bot_bar.setSpacing(10)

        # Özet
        self.lbl_summary = QLabel()
        self.lbl_summary.setFont(QFont(FONT_FAMILY, 9.5, QFont.Bold))
        self.lbl_summary.setStyleSheet("color: #64748B; background: transparent; border: none;")

        # Silindirik / Pill Butonlar (border-radius: 17px)
        btn_add = QPushButton(" Kural Ekle")
        btn_add.setIcon(make_vector_icon("plus", 14, "#FFFFFF"))
        btn_add.setFixedHeight(34)
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet("""
            QPushButton {
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 17px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 20px;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        btn_add.clicked.connect(self._add_relation)

        btn_edit = QPushButton(" Düzenle")
        btn_edit.setIcon(make_vector_icon("edit", 14, "#0F172A"))
        btn_edit.setFixedHeight(34)
        btn_edit.setCursor(Qt.PointingHandCursor)
        btn_edit.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 17px;
                font-size: 12px;
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: #F8FAFC;
                border-color: #0071E3;
                color: #0071E3;
            }
        """)
        btn_edit.clicked.connect(self._edit_relation_btn)

        btn_del = QPushButton(" Sil")
        btn_del.setIcon(make_vector_icon("trash", 14, "#DC2626"))
        btn_del.setFixedHeight(34)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("""
            QPushButton {
                background: #FEF2F2;
                color: #DC2626;
                border: 1px solid #FECACA;
                border-radius: 17px;
                font-size: 12px;
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: #FEE2E2;
                border-color: #F87171;
            }
        """)
        btn_del.clicked.connect(self._del_relation)

        btn_toggle = QPushButton("Tümünü Aktifleştir / Kapat")
        btn_toggle.setFixedHeight(34)
        btn_toggle.setCursor(Qt.PointingHandCursor)
        btn_toggle.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #334155;
                border: 1px solid #CBD5E1;
                border-radius: 17px;
                font-size: 12px;
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover { background: #F8FAFC; border-color: #94A3B8; color: #0F172A; }
        """)
        btn_toggle.clicked.connect(self._toggle_all)

        btn_close = QPushButton(" Kapat ve Kaydet")
        btn_close.setIcon(make_vector_icon("check", 14, "#FFFFFF"))
        btn_close.setFixedHeight(34)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 17px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 22px;
            }
            QPushButton:hover { background: #059669; }
        """)
        btn_close.clicked.connect(self._close_and_save)

        bot_bar.addWidget(btn_add)
        bot_bar.addWidget(btn_edit)
        bot_bar.addWidget(btn_del)
        bot_bar.addWidget(btn_toggle)
        bot_bar.addSpacing(8)
        bot_bar.addWidget(self.lbl_summary)
        bot_bar.addStretch(1)
        bot_bar.addWidget(btn_close)

        main_layout.addLayout(bot_bar)

    def _load_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        items = self.data_store.get("planlama_iliskileri", [])

        active_count = 0
        for idx, item in enumerate(items):
            self.table.insertRow(idx)
            self.table.setRowHeight(idx, 38)

            # Checkbox using widget for perfect centering and clean design
            chk_widget = QWidget()
            chk_lay = QHBoxLayout(chk_widget)
            chk_lay.setContentsMargins(0, 0, 0, 0)
            chk_lay.setAlignment(Qt.AlignCenter)
            chk_box = QCheckBox()
            chk_box.setCursor(Qt.PointingHandCursor)
            is_active = item.get("aktif", True)
            chk_box.setChecked(is_active)
            chk_box.stateChanged.connect(lambda state, r=idx: self._on_widget_checkbox_changed(r, state))
            chk_lay.addWidget(chk_box)
            self.table.setCellWidget(idx, 0, chk_widget)
            
            dummy_item = QTableWidgetItem()
            dummy_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(idx, 0, dummy_item)
            if is_active:
                active_count += 1

            # Kural metni
            kural_text = item.get("kural", "")
            if item.get("parametre"):
                kural_text += f" (maks: {item['parametre']} saat)"
            if item.get("period_start") and item.get("period_end"):
                kural_text += f" ({item['period_start']}.–{item['period_end']}. saat)"
            kural_item = QTableWidgetItem(kural_text)
            if not is_active:
                kural_item.setForeground(QBrush(QColor("#94A3B8")))
                kural_item.setFont(QFont(FONT_FAMILY, 9.5))
            else:
                kural_item.setForeground(QBrush(QColor("#0F172A")))
                kural_item.setFont(QFont(FONT_FAMILY, 9.5, QFont.Bold))
            self.table.setItem(idx, 1, kural_item)

            # Dersler
            subj = item.get("dersler", [])
            subj_item = QTableWidgetItem(", ".join(subj) if subj else "Tüm dersler")
            if not subj:
                subj_item.setForeground(QBrush(QColor("#94A3B8")))
            else:
                subj_item.setForeground(QBrush(QColor("#334155")))
            self.table.setItem(idx, 2, subj_item)

            # Sınıflar
            cls = item.get("siniflar", [])
            cls_item = QTableWidgetItem(", ".join(cls) if cls else "Tüm sınıflar")
            if not cls:
                cls_item.setForeground(QBrush(QColor("#94A3B8")))
            else:
                cls_item.setForeground(QBrush(QColor("#334155")))
            self.table.setItem(idx, 3, cls_item)

            # Öğretmenler
            teach = item.get("ogretmenler", [])
            teach_item = QTableWidgetItem(", ".join(teach) if teach else "Tüm öğretmenler")
            if not teach:
                teach_item.setForeground(QBrush(QColor("#94A3B8")))
            else:
                teach_item.setForeground(QBrush(QColor("#334155")))
            self.table.setItem(idx, 4, teach_item)

            # Önem (Sleek Modern Capsule Badge)
            onem = item.get("onem", "Sıkı")
            onem_short = onem.split("(")[0].strip() if "(" in onem else onem
            
            badge_widget = QWidget()
            b_lay = QHBoxLayout(badge_widget)
            b_lay.setContentsMargins(6, 4, 6, 4)
            b_lay.setAlignment(Qt.AlignCenter)
            
            lbl_badge = QLabel(f" {onem_short} ")
            lbl_badge.setFont(QFont(FONT_FAMILY, 8, QFont.Bold))
            
            if "Sıkı" in onem_short:
                lbl_badge.setStyleSheet("background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; border-radius: 9px; padding: 2px 8px;")
            elif "Yüksek" in onem_short:
                lbl_badge.setStyleSheet("background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; border-radius: 9px; padding: 2px 8px;")
            elif "Normal" in onem_short:
                lbl_badge.setStyleSheet("background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; border-radius: 9px; padding: 2px 8px;")
            else:
                lbl_badge.setStyleSheet("background: #F1F5F9; color: #64748B; border: 1px solid #CBD5E1; border-radius: 9px; padding: 2px 8px;")
                
            b_lay.addWidget(lbl_badge)
            self.table.setCellWidget(idx, 5, badge_widget)

        self.table.blockSignals(False)
        total = len(items)
        self.lbl_summary.setText(f"Toplam {total} kural ({active_count} aktif)")

    def _on_widget_checkbox_changed(self, row, state):
        relations = self.data_store.get("planlama_iliskileri", [])
        if 0 <= row < len(relations):
            is_active = (state == Qt.Checked or state == 2)
            relations[row]["aktif"] = is_active

            kural_item = self.table.item(row, 1)
            if kural_item:
                if is_active:
                    kural_item.setForeground(QBrush(QColor("#0F172A")))
                    kural_item.setFont(QFont(FONT_FAMILY, 9.5, QFont.Bold))
                else:
                    kural_item.setForeground(QBrush(QColor("#94A3B8")))
                    kural_item.setFont(QFont(FONT_FAMILY, 9.5, QFont.Normal))

            active_count = sum(1 for r in relations if r.get("aktif", True))
            self.lbl_summary.setText(f"Toplam {len(relations)} kural ({active_count} aktif)")
            self._save()

    def _on_checkbox_changed(self, item):
        pass

    def _add_relation(self):
        d = EditRelationDialog(self.data_store, parent=self)
        if d.exec():
            new_data = d.get_data()
            if "planlama_iliskileri" not in self.data_store:
                self.data_store["planlama_iliskileri"] = []
            self.data_store["planlama_iliskileri"].append(new_data)
            self._save()
            self._load_table()

    def _edit_relation_btn(self):
        r = self.table.currentRow()
        if r >= 0:
            self._edit_relation(self.table.item(r, 1))

    def _edit_relation(self, item):
        if not item:
            return
        r = item.row()
        relations = self.data_store.get("planlama_iliskileri", [])
        if r >= len(relations):
            return
        rel_data = relations[r]
        d = EditRelationDialog(self.data_store, relation_data=rel_data, parent=self)
        if d.exec():
            updated_data = d.get_data()
            self.data_store["planlama_iliskileri"][r] = updated_data
            self._save()
            self._load_table()

    def _del_relation(self):
        r = self.table.currentRow()
        if r >= 0:
            resp = QMessageBox.question(self, "Kuralı Sil", "Bu kuralı silmek istediğinize emin misiniz?",
                                         QMessageBox.Yes | QMessageBox.No)
            if resp == QMessageBox.Yes:
                self.data_store["planlama_iliskileri"].pop(r)
                self._save()
                self._load_table()

    def _toggle_all(self):
        relations = self.data_store.get("planlama_iliskileri", [])
        all_active = all(r.get("aktif", True) for r in relations)
        new_state = not all_active
        for r in relations:
            r["aktif"] = new_state

        self._load_table()
        self._save()

    def _close_and_save(self):
        self._save()
        self.accept()

    def _save(self):
        # Gerçek zamanlı veritabanına kaydet
        trigger_save_db(self, self.data_store)

        # Ana pencereye bildir
        p = self.parent()
        while p:
            if hasattr(p, "save_db"):
                p.save_db()
                break
            p = p.parent()
