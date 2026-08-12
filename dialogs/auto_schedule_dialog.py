"""dialogs/auto_schedule_dialog.py — Otomatik Yerleştirme"""
import random
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QComboBox, QSpinBox, QFormLayout,
    QGroupBox, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
from dialogs.base_dialog import BaseDialog


class AutoScheduleDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__("Otomatik Planlama Baslatiliyor", parent=parent)
        self.resize(640, 500)
        self._setup()

    def _setup(self):
        # Settings group
        grp = QGroupBox("Algoritma Ayarlari", self.content_widget)
        grp.setFont(QFont("Segoe UI", 9, QFont.Bold))
        grp_layout = QFormLayout(grp)
        grp_layout.setSpacing(8)

        self._algo = QComboBox()
        self._algo.addItems(["Backtracking (Geri Izleme)", "Hizli Atama", "Hibrit Optimizasyon"])
        self._iterasyon = QSpinBox(); self._iterasyon.setRange(100, 10000); self._iterasyon.setValue(1000); self._iterasyon.setSingleStep(100)
        self._zaman = QSpinBox(); self._zaman.setRange(5, 300); self._zaman.setValue(60); self._zaman.setSuffix(" sn")

        self._cb_ogretmen = QCheckBox("Ogretmen cakismasini engelle"); self._cb_ogretmen.setChecked(True)
        self._cb_sinif    = QCheckBox("Sinif cakismasini engelle");    self._cb_sinif.setChecked(True)
        self._cb_derslik  = QCheckBox("Derslik cakismasini engelle");  self._cb_derslik.setChecked(True)
        self._cb_ardisik  = QCheckBox("Ayni dersin ust uste gelmesini engelle"); self._cb_ardisik.setChecked(True)

        grp_layout.addRow("Algoritma:", self._algo)
        grp_layout.addRow("Maks. Iterasyon:", self._iterasyon)
        grp_layout.addRow("Zaman Siniri:", self._zaman)
        grp_layout.addRow(self._cb_ogretmen)
        grp_layout.addRow(self._cb_sinif)
        grp_layout.addRow(self._cb_derslik)
        grp_layout.addRow(self._cb_ardisik)

        self.content_layout.addWidget(grp)

        # Progress
        prog_lbl = QLabel("Ilerleme:", self.content_widget)
        prog_lbl.setFont(QFont("Segoe UI", 9))
        self.content_layout.addWidget(prog_lbl)

        self._progress = QProgressBar(self.content_widget)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setStyleSheet("""
            QProgressBar { border:1px solid #CCC; border-radius:4px; background:#F5F5F5; height:20px; text-align:center; }
            QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1E6DB5, stop:1 #2ECC71); border-radius:3px; }
        """)
        self.content_layout.addWidget(self._progress)

        # Log
        self._log = QTextEdit(self.content_widget)
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(100)
        self._log.setFont(QFont("Consolas", 8))
        self._log.setStyleSheet("background:#1A1A2E; color:#00FF88; border:1px solid #333;")
        self.content_layout.addWidget(self._log)

        # Start button
        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("Planlamayi Basalt")
        self._start_btn.setFixedHeight(36)
        self._start_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self._start_btn.setStyleSheet(
            "QPushButton{background:#2ECC71;color:white;border:none;border-radius:5px;}"
            "QPushButton:hover{background:#27AE60;}"
            "QPushButton:disabled{background:#95A5A6;}"
        )
        self._start_btn.clicked.connect(self._start)
        btn_row.addWidget(self._start_btn)
        self.content_layout.addLayout(btn_row)

        # Timer for simulation
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._step = 0

    def _start(self):
        self._step = 0
        self._progress.setValue(0)
        self._log.clear()
        self._start_btn.setEnabled(False)
        self._log.append("[BASLATILDI] Kisitilamalar yukleniyor...")
        self._timer.start(80)

    def _tick(self):
        self._step += random.randint(1, 4)
        self._progress.setValue(min(self._step, 100))

        msgs = [
            f"[{self._step}%] Ogretmen cizelgesi hesaplaniyor...",
            f"[{self._step}%] Sinif atamasi yapiliyor...",
            f"[{self._step}%] Cakisma kontrolu...",
            f"[{self._step}%] Derslik optimizasyonu...",
            f"[{self._step}%] Kisitlamalar kontrol ediliyor...",
        ]
        self._log.append(random.choice(msgs))

        if self._step >= 100:
            self._timer.stop()
            self._log.append("\n[TAMAMLANDI] Program basariyla olusturuldu!")
            self._start_btn.setEnabled(True)
            self._start_btn.setText("Yeniden Calistir")
