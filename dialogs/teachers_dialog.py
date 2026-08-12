"""dialogs/teachers_dialog.py — Öğretmen Tanımlama"""
from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QLineEdit, QLabel, QColorDialog,
    QComboBox, QSpinBox, QDialog, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from dialogs.base_dialog import BaseDialog


class TeachersDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__("Öğretmenler", parent=parent)
        self.resize(820, 520)
        self._teachers = []
        self._setup()

    def _setup(self):
        # Toolbar
        tb = QHBoxLayout()
        for label, fn in [("+ Ekle", self._add), ("- Sil", self._delete), ("Düzenle", self._edit)]:
            btn = QPushButton(label, self.content_widget)
            btn.setFixedHeight(28)
            btn.setFont(QFont("Segoe UI", 9))
            btn.setStyleSheet(
                "QPushButton{background:#1E6DB5;color:white;border:none;border-radius:3px;padding:0 12px;}"
                "QPushButton:hover{background:#1557A0;}"
            )
            btn.clicked.connect(fn)
            tb.addWidget(btn)
        tb.addStretch(1)

        search = QLineEdit(self.content_widget)
        search.setPlaceholderText("Ara...")
        search.setFixedWidth(160)
        search.setStyleSheet("border:1px solid #CCC;border-radius:3px;padding:3px;")
        search.textChanged.connect(self._filter)
        tb.addWidget(search)
        self.content_layout.addLayout(tb)

        # Table
        self.table = QTableWidget(0, 6, self.content_widget)
        self.table.setHorizontalHeaderLabels(
            ["Ad", "Soyad", "Kısaltma", "Renk", "Maks.Saat/Gün", "Not"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget { font-size:9pt; border:1px solid #CCC; }
            QTableWidget::item:alternate { background:#F5F8FC; }
        """)
        self.content_layout.addWidget(self.table)

    def _add(self):
        d = _TeacherEditDialog(self)
        if d.exec():
            data = d.get_data()
            self._teachers.append(data)
            self._refresh()

    def _delete(self):
        row = self.table.currentRow()
        if row >= 0:
            self._teachers.pop(row)
            self._refresh()

    def _edit(self):
        row = self.table.currentRow()
        if row >= 0:
            d = _TeacherEditDialog(self, self._teachers[row])
            if d.exec():
                self._teachers[row] = d.get_data()
                self._refresh()

    def _refresh(self, data=None):
        rows = data or self._teachers
        self.table.setRowCount(len(rows))
        for i, t in enumerate(rows):
            for j, key in enumerate(["ad", "soyad", "kisaltma", "renk", "maks_saat", "not"]):
                val = str(t.get(key, ""))
                item = QTableWidgetItem(val)
                if key == "renk":
                    item.setBackground(QColor(val or "#FFFFFF"))
                self.table.setItem(i, j, item)

    def _filter(self, text):
        filtered = [t for t in self._teachers
                    if text.lower() in (t.get("ad","") + t.get("soyad","")).lower()]
        self._refresh(filtered)


class _TeacherEditDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Öğretmen Ekle / Düzenle")
        self.setFixedSize(400, 320)
        self._color = data.get("renk", "#3498DB") if data else "#3498DB"
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        fields = [
            ("Ad",        "ad",        QLineEdit),
            ("Soyad",     "soyad",     QLineEdit),
            ("Kısaltma",  "kisaltma",  QLineEdit),
            ("Not",       "not",       QLineEdit),
        ]
        self._widgets = {}
        for label, key, Widget in fields:
            row = QHBoxLayout()
            lbl = QLabel(label + ":", self)
            lbl.setFixedWidth(90)
            lbl.setFont(QFont("Segoe UI", 9))
            row.addWidget(lbl)
            w = Widget(self)
            if data:
                w.setText(str(data.get(key, "")))
            self._widgets[key] = w
            row.addWidget(w)
            layout.addLayout(row)

        # Max hours
        row2 = QHBoxLayout()
        lbl2 = QLabel("Maks.Saat/Gün:", self)
        lbl2.setFixedWidth(90)
        lbl2.setFont(QFont("Segoe UI", 9))
        self._maks = QSpinBox(self)
        self._maks.setRange(1, 12)
        self._maks.setValue(int(data.get("maks_saat", 8)) if data else 8)
        row2.addWidget(lbl2)
        row2.addWidget(self._maks)
        layout.addLayout(row2)

        # Color picker
        color_row = QHBoxLayout()
        color_lbl = QLabel("Renk:", self)
        color_lbl.setFixedWidth(90)
        color_lbl.setFont(QFont("Segoe UI", 9))
        self._color_btn = QPushButton(self)
        self._color_btn.setFixedSize(80, 28)
        self._color_btn.setStyleSheet(f"background: {self._color}; border:1px solid #CCC; border-radius:3px;")
        self._color_btn.clicked.connect(self._pick_color)
        color_row.addWidget(color_lbl)
        color_row.addWidget(self._color_btn)
        color_row.addStretch(1)
        layout.addLayout(color_row)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch(1)
        ok = QPushButton("Tamam", self)
        ok.setStyleSheet("background:#1E6DB5;color:white;border:none;border-radius:4px;padding:5px 16px;")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("İptal", self)
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok); btns.addWidget(cancel)
        layout.addLayout(btns)

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self)
        if c.isValid():
            self._color = c.name()
            self._color_btn.setStyleSheet(f"background:{self._color};border:1px solid #CCC;border-radius:3px;")

    def get_data(self):
        return {
            "ad":        self._widgets["ad"].text(),
            "soyad":     self._widgets["soyad"].text(),
            "kisaltma":  self._widgets["kisaltma"].text(),
            "not":       self._widgets["not"].text(),
            "maks_saat": self._maks.value(),
            "renk":      self._color,
        }
