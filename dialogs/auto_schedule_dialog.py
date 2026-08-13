"""
auto_schedule_dialog.py — Otomatik Yerleştirme (aSc Timetables stili)
"""
import random
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QComboBox, QFormLayout, QGroupBox, QCheckBox, QWidget, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

class AutoScheduleDialog(QDialog):
    def __init__(self, data_store=None, parent=None):
        super().__init__(parent)
        self.data_store = data_store
        self.setWindowTitle("Ders programı oluşturma")
        self.resize(550, 400)
        
        self.setStyleSheet("""
            QDialog { background-color: #F0F0F0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 12px; }
            QGroupBox { border: 1px solid #B0B0B0; margin-top: 2ex; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; }
            QPushButton { padding: 6px 16px; border: 1px solid #ADADAD; background: #E1E1E1; border-radius: 3px; font-weight: bold; }
            QPushButton:hover { background: #E5F1FB; border: 1px solid #0078D7; }
            QPushButton#btn_start { padding: 10px 20px; font-size: 14px; background: #E1E1E1; }
            QComboBox { border: 1px solid #ADADAD; padding: 3px; background: white; }
            QProgressBar { border: 1px solid #B0B0B0; text-align: center; }
            QProgressBar::chunk { background-color: #0078D7; }
        """)
        
        self._build_ui()
        self._step = 0
        
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Parameters Group
        grp_param = QGroupBox("Oluşturma Parametreleri")
        form_param = QFormLayout(grp_param)
        
        self.cb_complexity = QComboBox()
        self.cb_complexity.addItems([
            "Normal (Tavsiye edilen)",
            "Büyük",
            "Çok büyük",
            "Karmaşık"
        ])
        form_param.addRow("Karmaşıklık:", self.cb_complexity)
        
        self.chk_relax = QCheckBox("Sıkı koşulların gevşetilmesine izin ver")
        self.chk_relax.setChecked(False)
        form_param.addRow("", self.chk_relax)
        
        main_layout.addWidget(grp_param)
        
        # Progress area
        grp_prog = QGroupBox("İlerleme")
        prog_layout = QVBoxLayout(grp_prog)
        
        self.lbl_info = QLabel("Program oluşturmaya hazır.")
        prog_layout.addWidget(self.lbl_info)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        prog_layout.addWidget(self.progress)
        
        self.lbl_stats = QLabel("Yerleştirilen kart sayısı: 0 / 0")
        prog_layout.addWidget(self.lbl_stats)
        
        main_layout.addWidget(grp_prog)
        
        main_layout.addStretch(1)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Planlamayı Başlat")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self._start_generation)
        
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)
        
    def _start_generation(self):
        self.progress.setValue(0)
        self.btn_start.setEnabled(False)
        self.btn_cancel.setText("Durdur")
        self.lbl_info.setText("Planlama algoritması çalışıyor (Yapay Zeka devrede)...")
        self.lbl_stats.setText("Yerleştirilen kart sayısı: Hesaplanıyor...")
        
        from auto_scheduler import AutoSchedulerWorker
        self.worker = AutoSchedulerWorker(self.data_store, self)
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.finished_successfully.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()
        
    def _on_progress(self, placed, total):
        pct = int((placed / max(1, total)) * 100)
        self.progress.setValue(pct)
        self.lbl_stats.setText(f"Yerleştirilen kart sayısı: {placed} / {total}")
        
    def _on_finished(self, result):
        self.progress.setValue(100)
        self.lbl_info.setText("Program başarıyla oluşturuldu! (Çakışmalar çözüldü)")
        self.lbl_info.setStyleSheet("color: green; font-weight: bold;")
        
        # Save results to data_store and close
        schedule = result.get("schedule", [])
        
        # Grid'e yansıtılması için formatla: { "row,col": { class_name, teacher_name, subject_name } }
        # Not: Bütün okul görünümü için bu yeterli değil, ama geçici olarak `grid_placements` içine ekleyebiliriz.
        # Gerçek aSc mimarisinde her sınıfın kendi tablosu vardır.
        self.data_store["auto_schedule_results"] = schedule
        
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Tamam")
        self.btn_start.clicked.disconnect()
        self.btn_start.clicked.connect(self.accept)
        self.btn_cancel.setText("Kapat")
        
    def _on_failed(self, err_msg):
        self.lbl_info.setText(f"Hata: {err_msg}")
        self.lbl_info.setStyleSheet("color: red; font-weight: bold;")
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Tekrar Dene")
        self.btn_cancel.setText("Kapat")

    def reject(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        super().reject()

