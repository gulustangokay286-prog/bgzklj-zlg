"""
dialogs/print_wizard.py – Gelişmiş Yazdırma Sihirbazı UI Yenilemesi
Modern, şık, kart ve arama destekli yazdırma seçim diyaloğu
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QTabWidget, QWidget, QLineEdit, QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QLinearGradient
import database

def make_wizard_icon(icon_type: str, size: int = 20) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    
    if icon_type == "print":
        grad = QLinearGradient(0, 0, 0, size)
        grad.setColorAt(0, QColor("#10B981"))
        grad.setColorAt(1, QColor("#059669"))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(2, 6, size - 4, size - 10, 3, 3)
        # Top sheet
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawRoundedRect(5, 2, size - 10, 6, 1.5, 1.5)
        # Bottom paper
        p.drawRoundedRect(5, size - 7, size - 10, 5, 1.5, 1.5)
    elif icon_type == "search":
        p.setPen(QPen(QColor("#64748B"), 1.8))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(3, 3, size - 9, size - 9)
        p.drawLine(size - 7, size - 7, size - 2, size - 2)
    elif icon_type == "check_all":
        p.setPen(QPen(QColor("#2563EB"), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(3, size/2, size/2 - 2, size - 4)
        p.drawLine(size/2 - 2, size - 4, size - 3, 3)
    p.end()
    return QIcon(pix)


class PrintWizardDialog(QDialog):
    def __init__(self, data_store=None, default_entity=None, default_view=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        self.default_entity = default_entity
        self.default_view = default_view or ""
        self.setWindowTitle("Gelişmiş Yazdırma Sihirbazı")
        self.resize(540, 580)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; }
            QTabWidget::pane { border: 1px solid #E2E8F0; background: #FFFFFF; border-radius: 8px; }
            QTabBar::tab {
                background: #E2E8F0; color: #475569; font-weight: bold; font-size: 12px;
                padding: 10px 24px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #2563EB; color: #FFFFFF;
            }
            QListWidget {
                border: none; background: transparent; padding: 6px;
            }
            QListWidget::item {
                padding: 8px 12px; margin: 2px 4px; border-radius: 6px; background: #F8FAFC;
                color: #0F172A; font-size: 13px; font-weight: 600; border: 1px solid #E2E8F0;
            }
            QListWidget::item:hover {
                background: #EFF6FF; border-color: #93C5FD;
            }
            QListWidget::item:selected {
                background: #DBEAFE; color: #1D4ED8; border-color: #3B82F6;
            }
            QLineEdit {
                border: 1px solid #CBD5E1; border-radius: 6px; padding: 6px 12px; font-size: 12px; background: #FFFFFF;
            }
            QLineEdit:focus {
                border: 2px solid #2563EB;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        
        # ── Header Banner
        header_frame = QFrame(self)
        header_frame.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 8px; }")
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(8, 4, 8, 4)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_wizard_icon("print", 28).pixmap(28, 28))
        h_layout.addWidget(icon_lbl)
        
        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(1)
        lbl_title = QLabel("Yazdırma ve Çıktı Sihirbazı")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F172A; border: none; background: transparent;")
        lbl_sub = QLabel("Baskı ve PDF çıktısı alınacak sınıf veya öğretmenleri seçin.")
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B; border: none; background: transparent;")
        info_vbox.addWidget(lbl_title)
        info_vbox.addWidget(lbl_sub)
        h_layout.addLayout(info_vbox)
        h_layout.addStretch(1)
        
        self.lbl_selected_count = QLabel("0 Seçili")
        self.lbl_selected_count.setStyleSheet("background: #EFF6FF; color: #1D4ED8; font-weight: bold; border-radius: 12px; padding: 4px 10px; font-size: 11px; border: 1px solid #BFDBFE;")
        h_layout.addWidget(self.lbl_selected_count)
        
        layout.addWidget(header_frame)
        
        # ── Search Box
        self.search_box = QLineEdit(self)
        self.search_box.setPlaceholderText("🔍 Hızlı filtrele (Sınıf / Öğretmen adı yazın)...")
        self.search_box.textChanged.connect(self._filter_list)
        layout.addWidget(self.search_box)
        
        # ── Tabs Container
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, stretch=1)
        
        # Classes Tab
        self.tab_classes = QWidget()
        l_classes = QVBoxLayout(self.tab_classes)
        l_classes.setContentsMargins(6, 6, 6, 6)
        self.list_classes = QListWidget()
        self.list_classes.itemChanged.connect(self._update_selected_count)
        l_classes.addWidget(self.list_classes)
        
        # Teachers Tab
        self.tab_teachers = QWidget()
        l_teachers = QVBoxLayout(self.tab_teachers)
        l_teachers.setContentsMargins(6, 6, 6, 6)
        self.list_teachers = QListWidget()
        self.list_teachers.itemChanged.connect(self._update_selected_count)
        l_teachers.addWidget(self.list_teachers)
        
        self.tabs.addTab(self.tab_classes, " Sınıflar")
        self.tabs.addTab(self.tab_teachers, " Öğretmenler")
        self.tabs.currentChanged.connect(lambda idx: self._update_selected_count())
        
        # Load data
        self._load_data()
        
        # ── Action Buttons Footer
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        btn_all = QPushButton("Tümünü Seç")
        btn_all.setCursor(Qt.PointingHandCursor)
        btn_all.setStyleSheet("QPushButton { background: #FFFFFF; color: #334155; border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px 14px; font-weight: bold; font-size: 12px; } QPushButton:hover { background: #F1F5F9; }")
        btn_all.clicked.connect(self._select_all)
        
        btn_none = QPushButton("Hiçbirini Seçme")
        btn_none.setCursor(Qt.PointingHandCursor)
        btn_none.setStyleSheet("QPushButton { background: #FFFFFF; color: #334155; border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px 14px; font-weight: bold; font-size: 12px; } QPushButton:hover { background: #F1F5F9; }")
        btn_none.clicked.connect(self._select_none)
        
        self.btn_print = QPushButton(" Seçilenleri Yazdır & Önizle")
        self.btn_print.setIcon(make_wizard_icon("print", 18))
        self.btn_print.setCursor(Qt.PointingHandCursor)
        self.btn_print.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #059669);
                color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 8px 20px; font-size: 13px; border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #059669, stop:1 #047857);
            }
        """)
        self.btn_print.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_print)
        
        layout.addLayout(btn_layout)
        self._update_selected_count()
        
    def _load_data(self):
        classes = self.data_store.get("siniflar", [])
        is_class_view = "Sınıf" in self.default_view or (self.default_entity and any(c.get("ad") == self.default_entity for c in classes))
        
        for c in classes:
            c_name = c.get("ad", "")
            if not c_name: continue
            item = QListWidgetItem(f"🎓  {c_name}")
            item.setData(Qt.UserRole, c_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if self.default_entity:
                item.setCheckState(Qt.Checked if c_name == self.default_entity else Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)
            self.list_classes.addItem(item)
            
        teachers = self.data_store.get("ogretmenler", [])
        is_teacher_view = "Öğretmen" in self.default_view or (self.default_entity and any(t.get("ad") == self.default_entity for t in teachers))
        
        for t in teachers:
            t_name = t.get("ad", "")
            if not t_name: continue
            item = QListWidgetItem(f"👤  {t_name}")
            item.setData(Qt.UserRole, t_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if self.default_entity and is_teacher_view:
                item.setCheckState(Qt.Checked if t_name == self.default_entity else Qt.Unchecked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.list_teachers.addItem(item)
            
        if is_teacher_view:
            self.tabs.setCurrentIndex(1)
        else:
            self.tabs.setCurrentIndex(0)
            
    def _filter_list(self, query):
        q = query.strip().lower()
        current_list = self.list_classes if self.tabs.currentIndex() == 0 else self.list_teachers
        for i in range(current_list.count()):
            item = current_list.item(i)
            text = (item.data(Qt.UserRole) or item.text()).lower()
            item.setHidden(bool(q and q not in text))

    def _select_all(self):
        current_list = self.list_classes if self.tabs.currentIndex() == 0 else self.list_teachers
        for i in range(current_list.count()):
            if not current_list.item(i).isHidden():
                current_list.item(i).setCheckState(Qt.Checked)
        self._update_selected_count()
            
    def _select_none(self):
        current_list = self.list_classes if self.tabs.currentIndex() == 0 else self.list_teachers
        for i in range(current_list.count()):
            current_list.item(i).setCheckState(Qt.Unchecked)
        self._update_selected_count()

    def _update_selected_count(self):
        current_list = self.list_classes if self.tabs.currentIndex() == 0 else self.list_teachers
        checked = sum(1 for i in range(current_list.count()) if current_list.item(i).checkState() == Qt.Checked)
        label_kind = "Sınıf" if self.tabs.currentIndex() == 0 else "Öğretmen"
        self.lbl_selected_count.setText(f"{checked} {label_kind} Seçili")
            
    def get_selected_filters(self):
        selected_classes = []
        for i in range(self.list_classes.count()):
            if self.list_classes.item(i).checkState() == Qt.Checked:
                selected_classes.append(self.list_classes.item(i).data(Qt.UserRole) or self.list_classes.item(i).text())
                
        selected_teachers = []
        for i in range(self.list_teachers.count()):
            if self.list_teachers.item(i).checkState() == Qt.Checked:
                selected_teachers.append(self.list_teachers.item(i).data(Qt.UserRole) or self.list_teachers.item(i).text())
                
        return {
            "classes": selected_classes,
            "teachers": selected_teachers
        }
