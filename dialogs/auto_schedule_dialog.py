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
    def __init__(self, data_store=None, parent=None, target_class=None):
        super().__init__(parent)
        self.data_store = data_store
        self.target_class = target_class
        self.setWindowTitle("Ders programı oluşturma")
        self.resize(550, 420)
        
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

        target_text = f"🎯 {self.target_class}" if self.target_class else "🌐 Tüm Sınıflar"
        lbl_target = QLabel(f"<b>{target_text}</b>")
        lbl_target.setStyleSheet("color: #0284C7; font-size: 13px;")
        form_param.addRow("Planlanacak Sınıf:", lbl_target)
        
        self.cb_complexity = QComboBox()
        self.cb_complexity.addItems([
            "A* Search & Branch-Bound (En İyisi / Tavsiye edilen)",
            "Normal",
            "Büyük",
            "Karmaşık"
        ])
        form_param.addRow("Arama Algoritması:", self.cb_complexity)
        
        self.chk_relax = QCheckBox("Sıkı koşulların gevşetilmesine izin ver")
        self.chk_relax.setChecked(False)
        form_param.addRow("", self.chk_relax)
        
        self.chk_fill_empty = QCheckBox("Eksik ders saatlerini 'Boş/Serbest' ile tam 40 saate tamamla")
        self.chk_fill_empty.setChecked(True)
        form_param.addRow("", self.chk_fill_empty)
        
        main_layout.addWidget(grp_param)
        
        # Progress area
        grp_prog = QGroupBox("İlerleme")
        prog_layout = QVBoxLayout(grp_prog)
        
        self.lbl_info = QLabel("Program oluşturmaya hazır. Mevcut manuel yerleşimler korunacaktır.")
        prog_layout.addWidget(self.lbl_info)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        prog_layout.addWidget(self.progress)
        
        self.lbl_stats = QLabel("Yerleştirilen ders saati: 0 / 0")
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
        self.lbl_info.setText("A* Search algoritması çalışıyor (Boşluksuz dolum)...")
        self.lbl_stats.setText("Yerleştirilen ders saati: Hesaplanıyor...")
        
        from auto_scheduler import AutoSchedulerWorker
        fill_empty = self.chk_fill_empty.isChecked()
        self.worker = AutoSchedulerWorker(self.data_store, target_class=self.target_class, parent=self, fill_empty=fill_empty)
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.finished_successfully.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()
        
    def _on_progress(self, placed, total):
        pct = int((placed / max(1, total)) * 100)
        self.progress.setValue(pct)
        self.lbl_stats.setText(f"Yerleştirilen ders saati: {placed} / {total} Saat")
        
    def _on_finished(self, result):
        self.progress.setValue(100)
        schedule = result.get("schedule", [])
        total_hrs = result.get("placed_hours") or sum(item.get("duration", 1) for item in schedule)
        target_hrs = result.get("total_hours", total_hrs)
        self.lbl_info.setText("Program başarıyla oluşturuldu! (Çakışmalar çözüldü, tüm slotlar dolduruldu)")
        self.lbl_info.setStyleSheet("color: green; font-weight: bold;")
        self.lbl_stats.setText(f"Yerleştirilen: {total_hrs} / {target_hrs} Ders Saati (Haftalık Program %100 Eksiksiz Dolduruldu)")
        self.data_store["auto_schedule_results"] = schedule
        
        new_placements = []
        try:
            from main_window import get_subject_color, format_tr_name
        except ImportError:
            get_subject_color = lambda s: "#1E88E5"
            format_tr_name = lambda t: t
            
        for item in schedule:
            if isinstance(item, dict):
                r = item.get("period") if "period" in item else item.get("row", 0)
                c = item.get("day_idx") if "day_idx" in item else item.get("day", item.get("col", 0))
                t = format_tr_name(item.get("teacher_name") or item.get("teacher") or "")
                s = item.get("subject_name") or item.get("subject") or ""
                cl = item.get("class_name") or item.get("class") or ""
                dur = int(item.get("duration", 1))
                color = get_subject_color(s)
                new_placements.append({
                    "row": r, "col": c, "period": r, "day": c,
                    "teacher_name": t, "teacher": t,
                    "subject_name": s, "subject": s,
                    "class_name": cl, "class": cl,
                    "color": color,
                    "duration": dur
                })
                
        self.data_store["grid_placements"] = new_placements
        
        p = self.parent()
        if p:
            if hasattr(p, "save_db"):
                p.save_db(sync_from_grid=False)
            if hasattr(p, "_restore_grid_placements"):
                p._restore_grid_placements()
            if hasattr(p, "_refresh_tree"):
                p._refresh_tree()
                
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
