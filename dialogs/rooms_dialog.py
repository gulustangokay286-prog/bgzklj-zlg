"""dialogs/rooms_dialog.py — Derslik Tanımlama"""
from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QLineEdit, QLabel, QSpinBox, QDialog, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from dialogs.base_dialog import BaseDialog


class RoomsDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__("Derslikler", parent=parent)
        self.resize(700, 460)
        self._rooms = []
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
        self.table.setHorizontalHeaderLabels(["Derslik Adı", "Kısaltma", "Kapasite", "Tür", "Not"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet("QTableWidget{font-size:9pt;border:1px solid #CCC;} QTableWidget::item:alternate{background:#F5F8FC;}")
        self.content_layout.addWidget(self.table)

    def _add(self):
        d = _RoomEditDialog(self)
        if d.exec():
            self._rooms.append(d.get_data())
            self._refresh()

    def _delete(self):
        row = self.table.currentRow()
        if row >= 0:
            self._rooms.pop(row)
            self._refresh()

    def _edit(self):
        row = self.table.currentRow()
        if row >= 0:
            d = _RoomEditDialog(self, self._rooms[row])
            if d.exec():
                self._rooms[row] = d.get_data()
                self._refresh()

    def _refresh(self):
        self.table.setRowCount(len(self._rooms))
        for i, r in enumerate(self._rooms):
            for j, key in enumerate(["ad", "kisaltma", "kapasite", "tur", "not"]):
                self.table.setItem(i, j, QTableWidgetItem(str(r.get(key, ""))))


class _RoomEditDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Derslik Ekle / Düzenle")
        self.setFixedSize(380, 260)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._w = {}
        for label, key in [("Derslik Adı", "ad"), ("Kısaltma", "kisaltma"), ("Not", "not")]:
            row = QHBoxLayout()
            lbl = QLabel(label + ":", self); lbl.setFixedWidth(110); lbl.setFont(QFont("Segoe UI", 9))
            w = QLineEdit(self)
            if data: w.setText(str(data.get(key, "")))
            row.addWidget(lbl); row.addWidget(w)
            self._w[key] = w
            layout.addLayout(row)

        row2 = QHBoxLayout()
        lbl2 = QLabel("Kapasite:", self); lbl2.setFixedWidth(110); lbl2.setFont(QFont("Segoe UI", 9))
        self._kap = QSpinBox(self); self._kap.setRange(1, 200); self._kap.setValue(int(data.get("kapasite", 30)) if data else 30)
        row2.addWidget(lbl2); row2.addWidget(self._kap); row2.addStretch(1)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        lbl3 = QLabel("Tür:", self); lbl3.setFixedWidth(110); lbl3.setFont(QFont("Segoe UI", 9))
        self._tur = QComboBox(self)
        self._tur.addItems(["Standart Sınıf", "Laboratuvar", "Spor Salonu", "Müzik Odası", "Bilgisayar Odası", "Özel Derslik"])
        if data: self._tur.setCurrentText(data.get("tur", "Standart Sınıf"))
        row3.addWidget(lbl3); row3.addWidget(self._tur)
        layout.addLayout(row3)

        btns = QHBoxLayout(); btns.addStretch(1)
        ok = QPushButton("Tamam"); ok.setStyleSheet("background:#1E6DB5;color:white;border:none;border-radius:4px;padding:5px 16px;")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("İptal"); cancel.clicked.connect(self.reject)
        btns.addWidget(ok); btns.addWidget(cancel)
        layout.addLayout(btns)

    def get_data(self):
        return {k: self._w[k].text() for k in self._w} | {"kapasite": self._kap.value(), "tur": self._tur.currentText()}
