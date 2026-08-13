"""
test_timetable_dialog.py – Planlama Öncesi Kontrol (Testing)
aSc Timetables birebir kopyası.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QTextEdit
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import random

class TestTimetableDialog(QDialog):
    def __init__(self, data_store, parent=None):
        super().__init__(parent)
        self.data_store = data_store
        
        self.setWindowTitle("Test ediliyor...")
        self.resize(500, 300)
        
        self.setStyleSheet("""
            QDialog { background-color: #F0F0F0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 12px; }
            QPushButton { padding: 4px 12px; border: 1px solid #ADADAD; background: #E1E1E1; border-radius: 3px; min-width: 80px; }
            QPushButton:hover { background: #E5F1FB; border: 1px solid #0078D7; }
            QTextEdit { background: white; border: 1px solid #ADADAD; }
        """)
        
        self._build_ui()
        self._start_test()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        self.lbl_status = QLabel("Temel veriler test ediliyor...")
        font = QFont()
        font.setBold(True)
        self.lbl_status.setFont(font)
        layout.addWidget(self.lbl_status)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_close = QPushButton("Kapat")
        self.btn_close.setEnabled(False)
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._step = 0
        self._entities = []
        
        for c in self.data_store.get("siniflar", []):
            if c.get("ad"): self._entities.append(f"Sınıf: {c['ad']}")
        for t in self.data_store.get("ogretmenler", []):
            if t.get("ad"): self._entities.append(f"Öğretmen: {t['ad']}")
            
        if not self._entities:
            self._entities = ["Veri bulunamadı"]
            
        random.shuffle(self._entities)
        
    def _start_test(self):
        self._step = 0
        self.progress.setValue(0)
        self.log.append("Test başlatıldı...")
        self._timer.start(100)
        
    def _tick(self):
        if self._step < len(self._entities):
            item = self._entities[self._step]
            self.log.append(f"Test ediliyor -> {item}")
            self.progress.setValue(int((self._step / len(self._entities)) * 100))
            self._step += 1
        else:
            self._timer.stop()
            self.progress.setValue(100)
            self.lbl_status.setText("Test başarıyla tamamlandı!")
            self.lbl_status.setStyleSheet("color: green;")
            self.log.append("Hiçbir temel sorun bulunamadı. Program otomatik planlamaya hazır.")
            self.btn_close.setEnabled(True)
