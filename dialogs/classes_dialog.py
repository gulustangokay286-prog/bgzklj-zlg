"""dialogs/classes_dialog.py — Sınıf Tanımlama"""
from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QLineEdit, QLabel, QSpinBox,
    QDialog, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from dialogs.base_dialog import BaseDialog


class ClassesDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__("Sınıflar", parent=parent)
        self.resize(700, 480)
        self._classes = []
        self._setup()

    def _setup(self):
        tb = QHBoxLayout()
        for label, fn in [("+ Ekle", self._add), ("- Sil", self._delete), ("Düzenle", self._edit)]:
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.setStyleSheet("background:#1E6DB5;color:white;border:none;border-radius:3px;padding:0 12px;")
            btn.clicked.connect(fn)
            tb.addWidget(btn)
        tb.addStretch(1)
        self.content_layout.addLayout(tb)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Sınıf Adı", "Kısaltma", "Sınıf No", "Öğrenci Sayısı", "Not"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet("QTableWidget{font-size:9pt;border:1px solid #CCC;} QTableWidget::item:alternate{background:#F5F8FC;}")
        self.content_layout.addWidget(self.table)

    def _add(self):
        d = _ClassEditDialog(self)
        if d.exec():
            self._classes.append(d.get_data())
            self._refresh()

    def _delete(self):
        row = self.table.currentRow()
        if row >= 0:
            self._classes.pop(row)
            self._refresh()

    def _edit(self):
        row = self.table.currentRow()
        if row >= 0:
            d = _ClassEditDialog(self, self._classes[row])
            if d.exec():
                self._classes[row] = d.get_data()
                self._refresh()

    def _refresh(self):
        self.table.setRowCount(len(self._classes))
        for i, c in enumerate(self._classes):
            for j, key in enumerate(["ad", "kisaltma", "no", "ogrenci", "not"]):
                self.table.setItem(i, j, QTableWidgetItem(str(c.get(key, ""))))


class _ClassEditDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Sınıf Ekle / Düzenle")
        self.setFixedSize(380, 280)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._w = {}
        for label, key in [("Sınıf Adı", "ad"), ("Kısaltma", "kisaltma"), ("Not", "not")]:
            row = QHBoxLayout()
            lbl = QLabel(label + ":", self); lbl.setFixedWidth(110); lbl.setFont(QFont("Segoe UI", 9))
            w = QLineEdit(self)
            if data: w.setText(str(data.get(key, "")))
            row.addWidget(lbl); row.addWidget(w)
            self._w[key] = w
            layout.addLayout(row)

        # Sınıf no
        row2 = QHBoxLayout()
        lbl2 = QLabel("Sınıf No:", self); lbl2.setFixedWidth(110); lbl2.setFont(QFont("Segoe UI", 9))
        self._no = QSpinBox(self); self._no.setRange(1, 13); self._no.setValue(int(data.get("no", 9)) if data else 9)
        row2.addWidget(lbl2); row2.addWidget(self._no); row2.addStretch(1)
        layout.addLayout(row2)

        # Öğrenci
        row3 = QHBoxLayout()
        lbl3 = QLabel("Öğrenci Sayısı:", self); lbl3.setFixedWidth(110); lbl3.setFont(QFont("Segoe UI", 9))
        self._ogrenci = QSpinBox(self); self._ogrenci.setRange(1, 60); self._ogrenci.setValue(int(data.get("ogrenci", 30)) if data else 30)
        row3.addWidget(lbl3); row3.addWidget(self._ogrenci); row3.addStretch(1)
        layout.addLayout(row3)

        btns = QHBoxLayout(); btns.addStretch(1)
        ok = QPushButton("Tamam"); ok.setStyleSheet("background:#1E6DB5;color:white;border:none;border-radius:4px;padding:5px 16px;")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("İptal"); cancel.clicked.connect(self.reject)
        btns.addWidget(ok); btns.addWidget(cancel)
        layout.addLayout(btns)

    def get_data(self):
        return {k: self._w[k].text() for k in self._w} | {"no": self._no.value(), "ogrenci": self._ogrenci.value()}
