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

class CrossConflictResolutionDialog(QDialog):
    def __init__(self, conflicts, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(540, 420)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        card = QFrame()
        card.setObjectName("conflictCard")
        card.setStyleSheet("""
            #conflictCard {
                background: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 18px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)
        
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(24, 20, 24, 20)
        c_lay.setSpacing(12)
        
        # Header
        hdr = QHBoxLayout()
        icon_lbl = QLabel("⚠️")
        icon_lbl.setFont(QFont("Segoe UI", 20))
        hdr.addWidget(icon_lbl)
        
        t_col = QVBoxLayout()
        title = QLabel("Çapraz Kurum Öğretmen Çakışması")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet("color: #1D1D1F; background: transparent; border: none;")
        sub = QLabel("Aşağıdaki öğretmen(ler) diğer kurumlarda aynı saatte derstedir:")
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet("color: #86868B; background: transparent; border: none;")
        t_col.addWidget(title)
        t_col.addWidget(sub)
        hdr.addLayout(t_col)
        hdr.addStretch(1)
        c_lay.addLayout(hdr)
        
        # Scroll area with conflicts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #E5E5EA; border-radius: 8px; background: #F9F9FB; }")
        
        list_w = QWidget()
        list_w.setStyleSheet("background: transparent;")
        list_lay = QVBoxLayout(list_w)
        list_lay.setContentsMargins(8, 8, 8, 8)
        list_lay.setSpacing(6)
        
        seen = set()
        for c in conflicts:
            k = (c["teacher"], c["day"], c["period"], c["other_institution"])
            if k in seen:
                continue
            seen.add(k)
            
            c_row = QFrame()
            c_row.setStyleSheet("background: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 6px;")
            r_lay = QVBoxLayout(c_row)
            r_lay.setContentsMargins(10, 6, 10, 6)
            r_lay.setSpacing(2)
            
            lbl_t = QLabel(f"👨‍🏫 <b>{c['teacher']}</b> — {c['day']} {c['period']}. Ders Saati")
            lbl_t.setFont(QFont("Segoe UI", 9.5))
            lbl_t.setStyleSheet("color: #1D1D1F; background: transparent; border: none;")
            
            lbl_d = QLabel(f"• Diğer Kurum: <b>{c['other_institution']}</b> ({c['other_class']} - {c['other_subject']})\n• Bu Kurumdaki Hedef: <b>{c['this_class']} - {c['this_subject']}</b>")
            lbl_d.setFont(QFont("Segoe UI", 8.5))
            lbl_d.setStyleSheet("color: #D97706; background: transparent; border: none;")
            
            r_lay.addWidget(lbl_t)
            r_lay.addWidget(lbl_d)
            list_lay.addWidget(c_row)
            
        list_lay.addStretch(1)
        scroll.setWidget(list_w)
        c_lay.addWidget(scroll, 1)
        
        # Action Buttons
        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(10)
        
        btn_block = QPushButton("Engelle / Diğerlerine Devam Et")
        btn_block.setFont(QFont("Segoe UI", 9, QFont.Bold))
        btn_block.setCursor(Qt.PointingHandCursor)
        btn_block.setStyleSheet("""
            QPushButton {
                background: #F5F5F7; color: #DC2626; border: 1px solid #FCA5A5;
                border-radius: 8px; padding: 8px 16px;
            }
            QPushButton:hover { background: #FEE2E2; }
        """)
        btn_block.clicked.connect(self.reject)
        
        btn_ignore = QPushButton("Yoksay ve Yerleştir (Devam Et)")
        btn_ignore.setFont(QFont("Segoe UI", 9, QFont.Bold))
        btn_ignore.setCursor(Qt.PointingHandCursor)
        btn_ignore.setStyleSheet("""
            QPushButton {
                background: #0071E3; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 8px 18px;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        btn_ignore.clicked.connect(self.accept)
        
        btn_lay.addWidget(btn_block)
        btn_lay.addWidget(btn_ignore)
        c_lay.addLayout(btn_lay)
        
        layout.addWidget(card)

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

        self.cb_target_class = QComboBox()
        self.cb_target_class.addItem("🌐 Tüm Okul (Tüm Sınıflar & Öğretmenler - Tavsiye Edilen)", None)
        
        all_cls = []
        for c in (self.data_store.get("siniflar", []) if self.data_store else []):
            cad = c.get("ad", "").strip()
            if cad and cad not in all_cls:
                all_cls.append(cad)
        for a in (self.data_store.get("atamalar", []) if self.data_store else []):
            cad = (a.get("class") or a.get("sinif") or a.get("class_name") or "").strip()
            if cad and cad not in all_cls:
                all_cls.append(cad)
                
        for cn in sorted(all_cls):
            self.cb_target_class.addItem(f"🎯 Sadece {cn}", cn)
            
        if self.target_class:
            idx = self.cb_target_class.findData(self.target_class)
            if idx >= 0:
                self.cb_target_class.setCurrentIndex(idx)
        else:
            self.cb_target_class.setCurrentIndex(0)
            
        self.cb_target_class.setStyleSheet("font-weight: bold; color: #0284C7; min-height: 26px;")
        form_param.addRow("Planlanacak Kapsam:", self.cb_target_class)
        
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
        
        self.chk_fill_empty = QCheckBox("Tüm haftalık çizelgeyi derslerle %100 doldur (Sıfır Boşluk / Eksiksiz Planlama)")
        self.chk_fill_empty.setChecked(True)
        form_param.addRow("", self.chk_fill_empty)
        
        main_layout.addWidget(grp_param)
        
        # Progress area
        grp_prog = QGroupBox("İlerleme")
        prog_layout = QVBoxLayout(grp_prog)
        
        self.lbl_info = QLabel("Program oluşturmaya hazır. Kısıtlamalar ve mevcut kilitli dersler korunacaktır.")
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
        self.btn_start.setStyleSheet("background-color: #2563EB; color: white; border: none; padding: 8px 18px; border-radius: 4px; font-weight: bold;")
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
        chosen_target = self.cb_target_class.currentData()
        inst_slug = getattr(self.parent(), "institution_slug", None)
        self.worker = AutoSchedulerWorker(self.data_store, target_class=chosen_target, parent=self, fill_empty=fill_empty, institution_slug=inst_slug)
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
        cross_conflicts = result.get("cross_conflicts", [])
        
        # If cross-institution conflicts detected, ask the user interactively
        if cross_conflicts:
            c_dlg = CrossConflictResolutionDialog(cross_conflicts, parent=self)
            ignore_and_place = (c_dlg.exec() == QDialog.Accepted)
            if not ignore_and_place:
                # Filter out conflicting items and keep all other placed lessons
                conflicting_keys = {(c["day_idx"], c["period_idx"], c["teacher"]) for c in cross_conflicts}
                filtered_schedule = []
                for item in schedule:
                    t = item.get("teacher_name") or item.get("teacher") or ""
                    d = item.get("day_idx") if "day_idx" in item else item.get("day", 0)
                    p = item.get("period", 0)
                    dur = int(item.get("duration", 1))
                    has_c = any((d, p + off, t) in conflicting_keys for off in range(dur))
                    if not has_c:
                        filtered_schedule.append(item)
                schedule = filtered_schedule
                total_hrs = sum(item.get("duration", 1) for item in schedule)
        
        pct = int((total_hrs / max(1, target_hrs)) * 100)
        if total_hrs >= target_hrs:
            self.lbl_stats.setText(f"Yerleştirilen: {total_hrs} / {target_hrs} Ders Saati (Haftalık Program %100 Eksiksiz Dolduruldu)")
            self.lbl_info.setText("Program başarıyla oluşturuldu! (Tüm sınıflar ve dersler eksiksiz yerleştirildi)")
            self.lbl_info.setStyleSheet("color: #10B981; font-weight: bold;")
        else:
            unp = target_hrs - total_hrs
            self.lbl_stats.setText(f"Yerleştirilen: {total_hrs} / {target_hrs} Ders Saati (Haftalık Program %{pct} Dolduruldu • {unp} Saat Kapasite/Kısıt Nedeniyle Yerleşemedi)")
            self.lbl_info.setText(f"Program oluşturuldu ({total_hrs} saat yerleştirildi, {unp} saat kısıtlamalar nedeniyle dışarıda kaldı).")
            self.lbl_info.setStyleSheet("color: #D97706; font-weight: bold;")
            
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
                is_locked = bool(item.get("locked", False))
                new_placements.append({
                    "row": r, "col": c, "period": r, "day": c,
                    "teacher_name": t, "teacher": t,
                    "subject_name": s, "subject": s,
                    "class_name": cl, "class": cl,
                    "color": color,
                    "duration": dur,
                    "locked": is_locked
                })
                
        self.data_store["grid_placements"] = new_placements
        
        p = self.parent()
        if p:
            if hasattr(p, "save_db"):
                p.save_db(sync_from_grid=False)
            if hasattr(p, "_refresh_grid"):
                p._refresh_grid()
            if hasattr(p, "_refresh_tree"):
                p._refresh_tree()
            
            # Auto-save as a new version
            slug = getattr(p, "institution_slug", None)
            if slug:
                try:
                    import version_store
                    version_store.save_version(slug, self.data_store, source="auto", note="Otomatik planlayıcı tarafından oluşturuldu")
                except Exception as ve:
                    print(f"[AUTO_SCHEDULE] Version save error: {ve}")
                
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
