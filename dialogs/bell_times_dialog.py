"""dialogs/bell_times_dialog.py — Zil ve Teneffüs Saatleri Gelişmiş Yönetim Penceresi (Apple Studio Minimalist UI)"""
import os
import tempfile
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QTimeEdit, QSpinBox, QHeaderView, QGroupBox,
    QGridLayout, QFrame, QComboBox, QCheckBox, QMessageBox, QWidget
)
from PySide6.QtCore import Qt, QTime, QRectF, QPointF, QPoint
from PySide6.QtGui import QFont, QColor, QBrush, QIcon, QPixmap, QPainter, QPen, QPainterPath, QPolygon

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, Helvetica Neue, Segoe UI, sans-serif"


def get_arrow_icon_path(direction: str) -> str:
    """Creates and returns a crisp, high-resolution vector arrow icon path for QSS steppers."""
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, f"chenki_stepper_arrow_{direction}.png").replace("\\", "/")
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.setBrush(QColor("#475569"))
    p.setPen(Qt.NoPen)
    if direction == "up":
        p.drawPolygon(QPolygon([QPoint(7, 20), QPoint(16, 9), QPoint(25, 20)]))
    else:
        p.drawPolygon(QPolygon([QPoint(7, 12), QPoint(16, 23), QPoint(25, 12)]))
    p.end()
    pix.save(path)
    return path


def make_bell_vector_icon(name: str, size: int = 18, color_hex: str = "#0071E3") -> QIcon:
    scale = 2
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(scale, scale)
    color = QColor(color_hex)
    
    if name == "bell":
        p.setPen(QPen(color, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(size / 2.0, 2.5)
        path.quadTo(size - 3.5, 5, size - 3.5, size - 5.5)
        path.lineTo(2.5, size - 5.5)
        path.quadTo(2.5, 5, size / 2.0, 2.5)
        p.drawPath(path)
        p.drawLine(QPointF(size / 2.0 - 2.5, size - 3), QPointF(size / 2.0 + 2.5, size - 3))
        
    elif name == "zap":
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(color))
        path = QPainterPath()
        path.moveTo(size / 2.0 + 1, 2)
        path.lineTo(3.5, size / 2.0 + 1)
        path.lineTo(size / 2.0, size / 2.0 + 1)
        path.lineTo(size / 2.0 - 1, size - 2)
        path.lineTo(size - 3.5, size / 2.0 - 1)
        path.lineTo(size / 2.0, size / 2.0 - 1)
        path.closeSubpath()
        p.drawPath(path)
        
    elif name == "check":
        p.setPen(QPen(color, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawLine(QPointF(3.5, size / 2.0), QPointF(size / 2.0 - 1, size - 4.5))
        p.drawLine(QPointF(size / 2.0 - 1, size - 4.5), QPointF(size - 3.5, 4))
        
    p.end()
    pix.setDevicePixelRatio(scale)
    return QIcon(pix)


class BellAndBreakTimesDialog(QDialog):
    """Gelişmiş Zil, Ders ve Teneffüs Saatleri Yönetim Penceresi (1-16 Saat Destekli)"""
    def __init__(self, data_store=None, periods=8, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        self.periods = max(1, min(16, int(periods)))
        
        self.setWindowTitle("Zil ve Teneffüs Saatleri Ayarları (Saat Saat Özelleştirme)")
        self.resize(860, 640)
        
        arrow_up = get_arrow_icon_path("up")
        arrow_down = get_arrow_icon_path("down")
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #F8FAFC;
                font-family: {FONT_FAMILY};
                color: #0F172A;
            }}
            QTableWidget {{
                border: 1px solid #CBD5E1;
                border-radius: 10px;
                background: #FFFFFF;
                alternate-background-color: #F8FAFC;
                gridline-color: #CBD5E1;
                font-size: 12px;
                font-family: {FONT_FAMILY};
            }}
            QTableWidget::item {{
                border: none;
                background: transparent;
                padding: 0px;
            }}
            QTableWidget::item:selected {{
                background-color: transparent;
            }}
            QHeaderView::section {{
                background-color: #F8FAFC;
                color: #64748B;
                font-weight: 600;
                padding: 10px 8px;
                border: none;
                border-bottom: 1px solid #CBD5E1;
                font-size: 12px;
                font-family: {FONT_FAMILY};
            }}
            QTimeEdit, QSpinBox {{
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 2px 2px 2px 6px;
                min-height: 28px;
                max-height: 28px;
                background: #FFFFFF;
                color: #0F172A;
                font-size: 12px;
                font-weight: 600;
                font-family: {FONT_FAMILY};
            }}
            QComboBox {{
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 2px 8px;
                min-height: 28px;
                max-height: 28px;
                background: #FFFFFF;
                color: #0F172A;
                font-size: 12px;
                font-family: {FONT_FAMILY};
            }}
            QTimeEdit:focus, QSpinBox:focus, QComboBox:focus {{
                border: 1.5px solid #0071E3;
                background: #FFFFFF;
            }}
            QTimeEdit::up-button, QSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 17px;
                border-left: none;
                border-bottom: 1px solid #CBD5E1;
                border-top-right-radius: 5px;
                background: #F8FAFC;
            }}
            QTimeEdit::up-button:hover, QSpinBox::up-button:hover {{
                background: #E2E8F0;
            }}
            QTimeEdit::up-arrow, QSpinBox::up-arrow {{
                image: url({arrow_up});
                width: 7px;
                height: 7px;
            }}
            QTimeEdit::down-button, QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 17px;
                border-left: none;
                border-bottom-right-radius: 5px;
                background: #F8FAFC;
            }}
            QTimeEdit::down-button:hover, QSpinBox::down-button:hover {{
                background: #E2E8F0;
            }}
            QTimeEdit::down-arrow, QSpinBox::down-arrow {{
                image: url({arrow_down});
                width: 7px;
                height: 7px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 22px;
                border-left: none;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                background: #F8FAFC;
            }}
            QComboBox::drop-down:hover {{
                background: #E2E8F0;
            }}
            QComboBox::down-arrow {{
                image: url({arrow_down});
                width: 7px;
                height: 7px;
            }}
        """)
        
        self._build_ui()
        self._load_data()
        self.setFocus()
        
    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(20, 16, 20, 16)
        main_lay.setSpacing(12)
        
        # 1. Info Banner (Nude Minimalist Header — No Box, No Circle Frame)
        info_lay = QHBoxLayout()
        info_lay.setContentsMargins(4, 2, 4, 2)
        info_lay.setSpacing(10)
        
        bell_icon = QLabel()
        bell_icon.setPixmap(make_bell_vector_icon("bell", 18, "#0071E3").pixmap(18, 18))
        bell_icon.setStyleSheet("background: transparent; border: none;")
        info_lay.addWidget(bell_icon, 0, Qt.AlignTop)
        
        info_lbl = QLabel(
            f"<b>Zil ve Teneffüs Saatleri:</b> Günlük ders saatinize ({self.periods} Saat) göre her bir dersin başlangıç, "
            "bitiş ve teneffüs sürelerini saat saat elle özelleştirebilir veya sihirbaz ile tek tıkla otomatik hesaplatabilirsiniz."
        )
        info_lbl.setFont(QFont(FONT_FAMILY, 9.5))
        info_lbl.setStyleSheet("color: #475569; background: transparent; border: none;")
        info_lbl.setWordWrap(True)
        info_lay.addWidget(info_lbl, 1)
        
        main_lay.addLayout(info_lay)
        
        # 2. Hızlı Otomatik Hesaplama Sihirbazı Kartı
        card_wiz = QFrame()
        card_wiz.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;")
        lay_wiz = QGridLayout(card_wiz)
        lay_wiz.setContentsMargins(16, 14, 16, 14)
        lay_wiz.setSpacing(10)
        
        lbl_w_title = QLabel("Hızlı Otomatik Doldurma ve Hesaplama")
        lbl_w_title.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
        lbl_w_title.setStyleSheet("color: #0F172A; border: none;")
        lay_wiz.addWidget(lbl_w_title, 0, 0, 1, 6)
        
        lbl_s1 = QLabel("1. Ders Başlangıcı:")
        lbl_s1.setStyleSheet("font-weight: 600; color: #475569; border: none;")
        lay_wiz.addWidget(lbl_s1, 1, 0)
        self.tm_start = QTimeEdit(QTime(8, 30))
        self.tm_start.setDisplayFormat("HH:mm")
        self.tm_start.setAlignment(Qt.AlignCenter)
        self.tm_start.setFixedWidth(96)
        lay_wiz.addWidget(self.tm_start, 1, 1)
        
        lbl_s2 = QLabel("Ders Süresi (dk):")
        lbl_s2.setStyleSheet("font-weight: 600; color: #475569; border: none;")
        lay_wiz.addWidget(lbl_s2, 1, 2)
        self.sp_lesson_dur = QSpinBox()
        self.sp_lesson_dur.setRange(20, 90)
        self.sp_lesson_dur.setValue(40)
        self.sp_lesson_dur.setAlignment(Qt.AlignCenter)
        self.sp_lesson_dur.setFixedWidth(96)
        lay_wiz.addWidget(self.sp_lesson_dur, 1, 3)
        
        lbl_s3 = QLabel("Standart Teneffüs (dk):")
        lbl_s3.setStyleSheet("font-weight: 600; color: #475569; border: none;")
        lay_wiz.addWidget(lbl_s3, 1, 4)
        self.sp_break_dur = QSpinBox()
        self.sp_break_dur.setRange(0, 60)
        self.sp_break_dur.setValue(10)
        self.sp_break_dur.setAlignment(Qt.AlignCenter)
        self.sp_break_dur.setFixedWidth(96)
        lay_wiz.addWidget(self.sp_break_dur, 1, 5)
        
        lbl_s4 = QLabel("Öğle Arası Saati:")
        lbl_s4.setStyleSheet("font-weight: 600; color: #475569; border: none;")
        lay_wiz.addWidget(lbl_s4, 2, 0)
        self.cb_lunch_period = QComboBox()
        self.cb_lunch_period.addItem("Öğle Arası Yok", 0)
        for i in range(1, self.periods):
            self.cb_lunch_period.addItem(f"{i}. Ders Sonrası", i)
        if self.periods >= 4:
            self.cb_lunch_period.setCurrentIndex(4)
        self.cb_lunch_period.setFixedWidth(135)
        lay_wiz.addWidget(self.cb_lunch_period, 2, 1)
        
        lbl_s5 = QLabel("Öğle Arası Süresi (dk):")
        lbl_s5.setStyleSheet("font-weight: 600; color: #475569; border: none;")
        lay_wiz.addWidget(lbl_s5, 2, 2)
        self.sp_lunch_dur = QSpinBox()
        self.sp_lunch_dur.setRange(15, 120)
        self.sp_lunch_dur.setValue(45)
        self.sp_lunch_dur.setAlignment(Qt.AlignCenter)
        self.sp_lunch_dur.setFixedWidth(96)
        lay_wiz.addWidget(self.sp_lunch_dur, 2, 3)
        
        # Connect signals for real-time live calculation
        self.tm_start.timeChanged.connect(self._auto_calculate_times)
        self.sp_lesson_dur.valueChanged.connect(self._auto_calculate_times)
        self.sp_break_dur.valueChanged.connect(self._auto_calculate_times)
        self.cb_lunch_period.currentIndexChanged.connect(self._auto_calculate_times)
        self.sp_lunch_dur.valueChanged.connect(self._auto_calculate_times)
        
        btn_calc = QPushButton("  Tüm Saatleri Otomatik Hesapla")
        btn_calc.setIcon(make_bell_vector_icon("zap", 13, "#FFFFFF"))
        btn_calc.setCursor(Qt.PointingHandCursor)
        btn_calc.setFixedHeight(30)
        btn_calc.setStyleSheet("""
            QPushButton {
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                border-radius: 15px;
                font-weight: 600;
                font-size: 11.5px;
                padding: 0 16px;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        btn_calc.clicked.connect(self._auto_calculate_times)
        lay_wiz.addWidget(btn_calc, 2, 4, 1, 2)
        
        main_lay.addWidget(card_wiz)
        
        # 3. Manuel Düzenleme Tablosu (Sade, Ferah, Minimalist Apple Stili)
        self.table = QTableWidget(self.periods, 5)
        self.table.setHorizontalHeaderLabels([
            "Ders No", "Başlangıç Saati", "Bitiş Saati", "Ders Süresi", "Sonraki Teneffüs (dk)"
        ])
        self.table.setShowGrid(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.rows_data = []
        for i in range(self.periods):
            # 1. Ders No
            it_no = QTableWidgetItem(f"  {i+1}. Ders  ")
            it_no.setFlags(Qt.ItemIsEnabled)
            it_no.setTextAlignment(Qt.AlignCenter)
            it_no.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
            it_no.setForeground(QColor("#0F172A"))
            self.table.setItem(i, 0, it_no)
            
            # 2. Start Time
            w1 = QWidget()
            w1.setStyleSheet("background: transparent; border: none;")
            l1 = QHBoxLayout(w1)
            l1.setContentsMargins(8, 2, 8, 2)
            l1.setAlignment(Qt.AlignCenter)
            tm_s = QTimeEdit()
            tm_s.wheelEvent = lambda event: event.ignore()
            tm_s.setDisplayFormat("HH:mm")
            tm_s.setAlignment(Qt.AlignCenter)
            tm_s.setFixedWidth(96)
            l1.addWidget(tm_s)
            self.table.setCellWidget(i, 1, w1)
            
            # 3. End Time
            w2 = QWidget()
            w2.setStyleSheet("background: transparent; border: none;")
            l2 = QHBoxLayout(w2)
            l2.setContentsMargins(8, 2, 8, 2)
            l2.setAlignment(Qt.AlignCenter)
            tm_e = QTimeEdit()
            tm_e.wheelEvent = lambda event: event.ignore()
            tm_e.setDisplayFormat("HH:mm")
            tm_e.setAlignment(Qt.AlignCenter)
            tm_e.setFixedWidth(96)
            l2.addWidget(tm_e)
            self.table.setCellWidget(i, 2, w2)
            
            # 4. Duration Display
            it_dur = QTableWidgetItem("  40 dk  ")
            it_dur.setTextAlignment(Qt.AlignCenter)
            it_dur.setFlags(Qt.ItemIsEnabled)
            it_dur.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
            it_dur.setForeground(QColor("#0071E3"))
            self.table.setItem(i, 3, it_dur)
            
            # 5. Break Duration
            w3 = QWidget()
            w3.setStyleSheet("background: transparent; border: none;")
            l3 = QHBoxLayout(w3)
            l3.setContentsMargins(8, 2, 8, 2)
            l3.setAlignment(Qt.AlignCenter)
            sp_b = QSpinBox()
            sp_b.wheelEvent = lambda event: event.ignore()
            sp_b.setRange(0, 120)
            sp_b.setValue(10 if i < self.periods - 1 else 0)
            sp_b.setSuffix(" dk")
            sp_b.setAlignment(Qt.AlignCenter)
            sp_b.setFixedWidth(96)
            l3.addWidget(sp_b)
            self.table.setCellWidget(i, 4, w3)
            
            self.rows_data.append({
                "start": tm_s, "end": tm_e, "dur_item": it_dur, "break": sp_b
            })
            
            # Connect live duration updates
            tm_s.timeChanged.connect(lambda _, row=i: self._on_time_modified(row))
            tm_e.timeChanged.connect(lambda _, row=i: self._on_time_modified(row))
            sp_b.valueChanged.connect(lambda _, row=i: self._on_break_modified(row))
            
        main_lay.addWidget(self.table, 1)
        
        # 4. Bottom Buttons (Silindirik / Pill)
        bot = QHBoxLayout()
        bot.setSpacing(10)
        
        btn_preset_meb = QPushButton("Standart MEB Şablonu")
        btn_preset_meb.setCursor(Qt.PointingHandCursor)
        btn_preset_meb.setFixedHeight(34)
        btn_preset_meb.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                color: #334155;
                border-radius: 17px;
                font-weight: 600;
                font-size: 12px;
                padding: 0 16px;
            }
            QPushButton:hover { background: #F8FAFC; color: #0F172A; }
        """)
        btn_preset_meb.clicked.connect(self._apply_meb_preset)
        bot.addWidget(btn_preset_meb)
        
        btn_preset_kurs = QPushButton("Kurs / Özel Öğretim Şablonu")
        btn_preset_kurs.setCursor(Qt.PointingHandCursor)
        btn_preset_kurs.setFixedHeight(34)
        btn_preset_kurs.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                color: #334155;
                border-radius: 17px;
                font-weight: 600;
                font-size: 12px;
                padding: 0 16px;
            }
            QPushButton:hover { background: #F8FAFC; color: #0F172A; }
        """)
        btn_preset_kurs.clicked.connect(self._apply_kurs_preset)
        bot.addWidget(btn_preset_kurs)
        
        bot.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setFixedHeight(34)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                color: #475569;
                border-radius: 17px;
                font-weight: 600;
                font-size: 12px;
                padding: 0 20px;
            }
            QPushButton:hover { background: #F8FAFC; color: #0F172A; }
        """)
        btn_cancel.clicked.connect(self.reject)
        bot.addWidget(btn_cancel)
        
        btn_save = QPushButton("  Zil ve Teneffüsleri Kaydet")
        btn_save.setIcon(make_bell_vector_icon("check", 13, "#FFFFFF"))
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setFixedHeight(34)
        btn_save.setStyleSheet("""
            QPushButton {
                background: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 17px;
                font-weight: 700;
                font-size: 12px;
                padding: 0 24px;
            }
            QPushButton:hover { background: #059669; }
        """)
        btn_save.clicked.connect(self._save_and_accept)
        bot.addWidget(btn_save)
        
        main_lay.addLayout(bot)
        
    def _on_time_modified(self, row, cascade=True):
        if row < len(self.rows_data):
            s = self.rows_data[row]["start"].time()
            e = self.rows_data[row]["end"].time()
            diff_mins = (e.hour() * 60 + e.minute()) - (s.hour() * 60 + s.minute())
            if diff_mins > 0:
                self.rows_data[row]["dur_item"].setText(f"  {diff_mins} dk  ")
                if cascade:
                    self._cascade_from(row)
            else:
                self.rows_data[row]["dur_item"].setText("  Geçersiz  ")

    def _on_break_modified(self, row):
        if row < len(self.rows_data):
            self._cascade_from(row)

    def _cascade_from(self, row):
        if row + 1 < len(self.rows_data):
            e = self.rows_data[row]["end"].time()
            b_dur = self.rows_data[row]["break"].value()
            
            next_start = e.addSecs(b_dur * 60)
            
            next_s = self.rows_data[row+1]["start"].time()
            next_e = self.rows_data[row+1]["end"].time()
            next_dur = (next_e.hour() * 60 + next_e.minute()) - (next_s.hour() * 60 + next_s.minute())
            if next_dur <= 0: next_dur = 40
            
            new_next_e = next_start.addSecs(next_dur * 60)
            
            self.rows_data[row+1]["start"].blockSignals(True)
            self.rows_data[row+1]["end"].blockSignals(True)
            
            self.rows_data[row+1]["start"].setTime(next_start)
            self.rows_data[row+1]["end"].setTime(new_next_e)
            
            self.rows_data[row+1]["start"].blockSignals(False)
            self.rows_data[row+1]["end"].blockSignals(False)
            
            self._on_time_modified(row + 1, cascade=False)
            self._cascade_from(row + 1)
                
    def _auto_calculate_times(self):
        curr = self.tm_start.time()
        l_dur = self.sp_lesson_dur.value()
        b_dur = self.sp_break_dur.value()
        lunch_after = int(self.cb_lunch_period.currentData() or 0)
        lunch_mins = self.sp_lunch_dur.value()
        
        # Block signals during batch recalculation to guarantee accurate cascade calculation
        for row in self.rows_data:
            row["start"].blockSignals(True)
            row["end"].blockSignals(True)
            row["break"].blockSignals(True)
            
        for i, row in enumerate(self.rows_data):
            row["start"].setTime(curr)
            end_t = curr.addSecs(l_dur * 60)
            row["end"].setTime(end_t)
            row["dur_item"].setText(f"  {l_dur} dk  ")
            
            # Determine break
            if i == self.periods - 1:
                row["break"].setValue(0)
            elif lunch_after > 0 and (i + 1) == lunch_after:
                row["break"].setValue(lunch_mins)
                curr = end_t.addSecs(lunch_mins * 60)
            else:
                row["break"].setValue(b_dur)
                curr = end_t.addSecs(b_dur * 60)
                
        for row in self.rows_data:
            row["start"].blockSignals(False)
            row["end"].blockSignals(False)
            row["break"].blockSignals(False)
                
    def _apply_meb_preset(self):
        self.tm_start.setTime(QTime(8, 30))
        self.sp_lesson_dur.setValue(40)
        self.sp_break_dur.setValue(10)
        if self.periods >= 4:
            self.cb_lunch_period.setCurrentIndex(4)
        self.sp_lunch_dur.setValue(45)
        self._auto_calculate_times()
        
    def _apply_kurs_preset(self):
        self.tm_start.setTime(QTime(9, 0))
        self.sp_lesson_dur.setValue(45)
        self.sp_break_dur.setValue(15)
        if self.periods >= 4:
            self.cb_lunch_period.setCurrentIndex(4)
        self.sp_lunch_dur.setValue(40)
        self._auto_calculate_times()

    def _load_data(self):
        settings = self.data_store.get("settings", {}) if isinstance(self.data_store.get("settings"), dict) else {}
        saved = (
            settings.get("bell_schedule")
            or self.data_store.get("bell_schedule")
            or self.data_store.get("bell_times")
            or settings.get("bell_times")
            or settings.get("zil_saatleri")
            or self.data_store.get("zil_saatleri")
        )
        if saved and len(saved) >= self.periods:
            for i in range(self.periods):
                item = saved[i]
                s_t = QTime.fromString(item.get("start", "08:30"), "HH:mm") if isinstance(item, dict) else QTime(8, 30)
                e_t = QTime.fromString(item.get("end", "09:10"), "HH:mm") if isinstance(item, dict) else QTime(9, 10)
                b_val = item.get("break_duration", 10) if isinstance(item, dict) else 10
                
                self.rows_data[i]["start"].setTime(s_t)
                self.rows_data[i]["end"].setTime(e_t)
                self.rows_data[i]["break"].setValue(b_val)
                
                dur = (e_t.hour() * 60 + e_t.minute()) - (s_t.hour() * 60 + s_t.minute())
                self.rows_data[i]["dur_item"].setText(f"  {dur} dk  " if dur > 0 else "  40 dk  ")
        else:
            self._auto_calculate_times()
            
    def _save_and_accept(self):
        schedule = []
        for i in range(self.periods):
            s_str = self.rows_data[i]["start"].time().toString("HH:mm")
            e_str = self.rows_data[i]["end"].time().toString("HH:mm")
            b_val = self.rows_data[i]["break"].value()
            
            s = self.rows_data[i]["start"].time()
            e = self.rows_data[i]["end"].time()
            dur = (e.hour() * 60 + e.minute()) - (s.hour() * 60 + s.minute())
            if dur <= 0:
                QMessageBox.warning(self, "Hata", f"{i+1}. Dersin bitiş saati başlangıç saatinden önce veya eşit olamaz!")
                return
                
            schedule.append({
                "period": i + 1,
                "start": s_str,
                "end": e_str,
                "duration": dur,
                "break_duration": b_val
            })
            
        settings = self.data_store.setdefault("settings", {})
        settings["bell_schedule"] = schedule
        settings["bell_times"] = schedule
        settings["zil_saatleri"] = schedule
        self.data_store["bell_schedule"] = schedule
        self.data_store["bell_times"] = schedule
        self.data_store["zil_saatleri"] = schedule
        self.data_store["zil_programi"] = {str(item["period"] - 1): item for item in schedule}
        
        # Direct and Reliable Real-Time Persistence (SQLite + JSON Version + VDS Cloud + UI Grid)
        win = self.window()
        main_win = None
        curr = self
        while curr:
            if hasattr(curr, "save_db") and hasattr(curr, "_refresh_grid"):
                main_win = curr
                break
            curr = curr.parent() if hasattr(curr, "parent") else None
            
        if main_win:
            main_win.save_db(sync_from_grid=False)
            main_win._refresh_grid()
            main_win._refresh_tree()
        else:
            from database import sync_data_store_to_vds
            sync_data_store_to_vds(self.data_store)
            
        self.accept()
