"""
print_preview.py – Gelişmiş Baskı, Yazdırma ve PDF Dışa Aktarma Penceresi
Sınıf Haftalık Programı, Öğretmen Programı ve Fotoğraftaki Sınıf Dersleri / Atama Listesi Formatı Desteği
"""
import os
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QFileDialog, QMessageBox
)
from PySide6.QtPrintSupport import QPrintPreviewWidget, QPrinter
from PySide6.QtGui import QPainter, QPen, QFont, QColor, QPageLayout, QBrush
from PySide6.QtCore import Qt, QRectF

SUBJECT_COLORS = [
    "#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#E91E63",
    "#00BCD4", "#8BC34A", "#FFC107", "#795548", "#607D8B",
    "#3F51B5", "#009688", "#E67E22", "#D32F2F", "#16A085"
]

def get_subject_color(subject_name: str, custom_color: str = None) -> str:
    if custom_color and custom_color not in ["#FFFFFF", "#C4C4F0", ""]:
        return custom_color
    if not subject_name:
        return "#2196F3"
    hash_val = sum(ord(c) for c in subject_name)
    return SUBJECT_COLORS[hash_val % len(SUBJECT_COLORS)]

def format_tr_name(val):
    if not val:
        return ""
    val = str(val).strip()
    return val.replace("i", "İ").replace("ı", "I").upper()

def make_font(size, bold=False):
    f = QFont("Segoe UI, Arial")
    f.setPixelSize(size)
    f.setBold(bold)
    return f

def get_subject_badge(subj_name, data_store=None):
    if not subj_name:
        return ""
        
    s_clean = str(subj_name).strip()
    
    # 1. If manual short code exists in data_store and is short (<= 5 chars), return it
    if data_store and "dersler" in data_store:
        for d in data_store["dersler"]:
            if d.get("ad", "").strip().lower() == s_clean.lower():
                kisa = (d.get("kisa") or "").strip().upper()
                if kisa and len(kisa) <= 5 and kisa.lower() != d.get("ad", "").strip().lower():
                    return kisa

    import re
    # Extract trailing number if exists (e.g. "Matematik 1" -> "MAT 1")
    m = re.match(r'^(.*?)\s*(\d+)$', s_clean)
    base_name = m.group(1).strip() if m else s_clean
    num_str = f" {m.group(2)}" if m else ""
    
    tr_map = str.maketrans({'i': 'İ', 'ı': 'I', 'ç': 'Ç', 'ğ': 'Ğ', 'ö': 'Ö', 'ş': 'Ş', 'ü': 'Ü'})
    base_up = base_name.translate(tr_map).upper()
    
    STANDARDS = [
        ("MATEMATİK", "MAT"), ("MATEMATIK", "MAT"), ("MAT", "MAT"),
        ("FİZİK", "FİZ"), ("FIZIK", "FİZ"), ("FİZ", "FİZ"), ("FIZ", "FİZ"),
        ("KİMYA", "KİM"), ("KIMYA", "KİM"), ("KİM", "KİM"), ("KIM", "KİM"),
        ("BİYOLOJİ", "BİY"), ("BIYOLOJI", "BİY"), ("BİYO", "BİY"), ("BIYO", "BİY"), ("BİY", "BİY"), ("BIY", "BİY"),
        ("TÜRK DİLİ VE EDEBİYATI", "TDE"), ("EDEBİYAT", "TDE"), ("EDBIYAT", "TDE"), ("TÜRKÇE", "TRK"), ("TURKCE", "TRK"), ("TRK", "TRK"),
        ("TARİH", "TAR"), ("TARIH", "TAR"), ("TAR", "TAR"),
        ("COĞRAFYA", "COĞ"), ("COGRAFYA", "COĞ"), ("COĞ", "COĞ"), ("COG", "COĞ"),
        ("DİN KÜLTÜRÜ VE AHLAK BİLGİSİ", "DİN"), ("DİN KÜLTÜRÜ", "DİN"), ("DİN", "DİN"), ("DIN", "DİN"),
        ("FELSEFE", "FEL"), ("FEL", "FEL"),
        ("İNGİLİZCE", "İNG"), ("INGILIZCE", "İNG"), ("İNG", "İNG"), ("ING", "İNG"),
        ("ALMANCA", "ALM"), ("ALM", "ALM"),
        ("BEDEN EĞİTİMİ", "BED"), ("BEDEN", "BED"), ("BED", "BED"),
        ("GÖRSEL SANATLAR", "GÖR"), ("GÖRSEL", "GÖR"), ("RESİM", "GÖR"), ("GÖR", "GÖR"), ("GOR", "GÖR"),
        ("MÜZİK", "MÜZ"), ("MUZIK", "MÜZ"), ("MÜZ", "MÜZ"), ("MUZ", "MÜZ"),
        ("REHBERLİK", "REH"), ("REHBERLIK", "REH"), ("REH", "REH"),
        ("GEOMETRİ", "GEO"), ("GEOMETRI", "GEO"), ("GEO", "GEO"),
        ("PARAGRAF", "PRG"), ("PRG", "PRG")
    ]
    
    for k, v in STANDARDS:
        if base_up == k or base_up.startswith(k):
            return f"{v}{num_str}".strip()
            
    # Fallback to alphanumeric prefix
    clean_alpha = "".join(c for c in base_up if c.isalnum())
    return f"{clean_alpha[:4]}{num_str}".strip()

def format_teacher_display_name(t_name, data_store=None):
    if not t_name or t_name in ["—", "Atanmadı", "❌ Atama Yok"]:
        return "—"
    
    t_clean = str(t_name).strip()
    
    # Check if data_store has teacher with this name
    if data_store and "ogretmenler" in data_store:
        for t in data_store["ogretmenler"]:
            ad = t.get("ad", "").strip()
            kisa = t.get("kisa", "").strip()
            if ad.lower() == t_clean.lower() or kisa.lower() == t_clean.lower() or ad.lower().startswith(t_clean.lower()):
                if kisa and "." in kisa and len(kisa.split(".")[0]) <= 3:
                    return kisa.upper()
                parts = ad.split()
                if len(parts) >= 2:
                    first_initial = parts[0][0].upper()
                    last_name = " ".join(parts[1:]).upper()
                    return f"{first_initial}. {last_name}"
                elif len(parts) == 1:
                    return f"{parts[0][0].upper()}. {parts[0].upper()}"

    # If t_clean already has format "X. SOYAD" (e.g. "S. ÖZKAN")
    if "." in t_clean and len(t_clean.split(".")) == 2:
        p1, p2 = t_clean.split(".")
        if len(p1.strip()) <= 3:
            return f"{p1.strip().upper()}. {p2.strip().upper()}"
            
    # Generic format: split into words
    parts = t_clean.split()
    if len(parts) >= 2:
        first_initial = parts[0][0].upper()
        last_name = " ".join(parts[1:]).upper()
        return f"{first_initial}. {last_name}"
    elif len(parts) == 1:
        w = parts[0].upper()
        trunc_map = {
            "MESU": "M. MESUT", "MESUT": "M. MESUT",
            "CEYL": "C. CEYLAN", "CEYLAN": "C. CEYLAN",
            "RASI": "R. RASİM", "RASİM": "R. RASİM", "RASİ": "R. RASİM",
            "ÖZGE": "Ö. ÖZGE", "OZGE": "Ö. ÖZGE",
            "HAKAN": "H. BİLİR"
        }
        if w in trunc_map:
            return trunc_map[w]
        return f"{w[0]}. {w}"
        
    return t_clean.upper()

def draw_class_avatar_icon(painter, x, y):
    painter.save()
    painter.setPen(Qt.NoPen)
    # Background silhouette
    painter.setBrush(QBrush(QColor("#94A3B8")))
    painter.drawEllipse(QRectF(x + 14, y + 2, 13, 13))
    painter.drawRoundedRect(QRectF(x + 10, y + 15, 20, 11), 4, 4)
    # Foreground silhouette
    painter.setBrush(QBrush(QColor("#64748B")))
    painter.drawEllipse(QRectF(x + 4, y + 6, 14, 14))
    painter.drawRoundedRect(QRectF(x, y + 20, 22, 12), 4, 4)
    painter.restore()

class TimetablePrintPreview(QDialog):
    def __init__(self, data_store=None, placed_lessons=None, filters=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Baskı Ön İzleme ve PDF Raporu")
        self.resize(1050, 780)
        
        self.data_store = data_store or {}
        self.placed_lessons = placed_lessons or {}
        self.filters = filters or {}

        self.filtered_classes = self.data_store.get("siniflar", [])
        self.filtered_teachers = self.data_store.get("ogretmenler", [])
        
        if self.filters.get("classes"):
            self.filtered_classes = [c for c in self.filtered_classes if c.get("ad") in self.filters.get("classes")]
        if self.filters.get("teachers"):
            self.filtered_teachers = [t for t in self.filtered_teachers if t.get("ad") in self.filters.get("teachers")]
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        
        # ── Controls Header Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)
        
        self.ALL_REPORT_MODES = [
            "Toplu Çarşaf Liste : Sınıflar",
            "Toplu Çarşaf Liste : Öğretmenler",
            "Tablo Olarak : Dersler",
            "[BİREBİR] Tüm Sınıflar (Yatay Sayfada 6'lı Çizelge)",
            "[BİREBİR] Tüm Öğretmenler (Yatay Sayfada 6'lı Çizelge)",
            "Sınıf Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)",
            "Öğretmen Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)",
            "Sınıf Dersleri & Atama Listesi (Liste Formatı)",
            "Tüm Öğretmenlerin Ders Yükü Listesi"
        ]
        
        top_bar.addWidget(QLabel("Rapor Türü:", self))
        self.mode_combo = QComboBox(self)
        self.mode_combo.setMinimumWidth(340)
        self.mode_combo.addItems(self.ALL_REPORT_MODES)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        top_bar.addWidget(self.mode_combo)
        
        top_bar.addWidget(QLabel("Seçim:", self))
        self.target_combo = QComboBox(self)
        self.target_combo.setMinimumWidth(160)
        self.target_combo.currentIndexChanged.connect(self._repaint)
        top_bar.addWidget(self.target_combo)
        
        top_bar.addStretch(1)
        
        btn_html = QPushButton("HTML (Web) Çıktısı")
        btn_html.setFixedSize(140, 32)
        btn_html.setStyleSheet("background: #E67E22; color: white; font-weight: bold; border-radius: 4px;")
        btn_html.clicked.connect(self._export_html)
        top_bar.addWidget(btn_html)
        
        btn_pdf = QPushButton("PDF Olarak Kaydet")
        btn_pdf.setFixedSize(140, 32)
        btn_pdf.setStyleSheet("background: #27AE60; color: white; font-weight: bold; border-radius: 4px;")
        btn_pdf.clicked.connect(self._export_pdf)
        top_bar.addWidget(btn_pdf)
        
        btn_print = QPushButton("Yazdır")
        btn_print.setFixedSize(100, 32)
        btn_print.setStyleSheet("background: #0078D7; color: white; font-weight: bold; border-radius: 4px;")
        btn_print.clicked.connect(self._do_print)
        top_bar.addWidget(btn_print)
        
        main_layout.addLayout(top_bar)
        
        # ── Print Preview Widget
        self.preview = QPrintPreviewWidget(self)
        self.preview.paintRequested.connect(self._paint)
        main_layout.addWidget(self.preview, 1)
        
        # Filter mode preselection
        lock_mode = self.filters.get("lock_mode")
        entity_type = self.filters.get("entity_type")
        
        target_mode_idx = 0
        if lock_mode:
            for idx, m_text in enumerate(self.ALL_REPORT_MODES):
                if lock_mode in m_text or m_text in lock_mode:
                    target_mode_idx = idx
                    break
        elif entity_type == "teacher":
            target_mode_idx = 2  # Öğretmen Haftalık Ders Programı (Tekil Çizelge)
        elif entity_type in ["class", "sinif"]:
            target_mode_idx = 3  # Sınıf Haftalık Ders Programı (Tekil Çizelge)
            
        self.mode_combo.setCurrentIndex(target_mode_idx)
        self._populate_targets()
        
        mode = self.mode_combo.currentText()
        is_portrait = ("Sınıf Dersleri" in mode)
        self.preview.setOrientation(QPageLayout.Orientation.Portrait if is_portrait else QPageLayout.Orientation.Landscape)

    def _on_mode_changed(self):
        mode = self.mode_combo.currentText()
        is_portrait = ("Sınıf Dersleri" in mode)
        self.preview.setOrientation(QPageLayout.Orientation.Portrait if is_portrait else QPageLayout.Orientation.Landscape)
        self._populate_targets()
        self._repaint()

    def _populate_targets(self):
        mode = self.mode_combo.currentText()
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        
        if "Tüm Sınıflar" in mode or "Tüm Öğretmenler" in mode or "Ders Yükü" in mode or "Çarşaf Liste" in mode or "Tablo Olarak" in mode:
            self.target_combo.addItem("Tümü (Çoklu Sayfa)")
            self.target_combo.setEnabled(False)
        elif "Öğretmen" in mode:
            self.target_combo.setEnabled(True)
            for t in self.filtered_teachers:
                self.target_combo.addItem(t.get("ad", ""))
        else:
            self.target_combo.setEnabled(True)
            for c in self.filtered_classes:
                self.target_combo.addItem(c.get("ad", ""))
                
        # If filters specified selected_items or default_selection, select it
        sel = self.filters.get("selected_items") or ([self.filters.get("default_selection")] if self.filters.get("default_selection") else [])
        if sel and len(sel) > 0 and sel[0]:
            idx = self.target_combo.findText(sel[0])
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
                
        self.target_combo.blockSignals(False)

    def _repaint(self):
        self.preview.updatePreview()

    def _export_html(self):
        path, _ = QFileDialog.getSaveFileName(self, "HTML Olarak Kaydet", "Ders_Programi.html", "HTML Files (*.html)")
        if not path:
            return
        try:
            mode = self.mode_combo.currentText()
            target = self.target_combo.currentText()
            html = f"<html><head><meta charset='utf-8'><title>{target} - Program</title></head><body>"
            html += f"<h1>{target} - {mode}</h1><p>BGZ Ders Planlama 2026 - 2027</p></body></html>"
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            QMessageBox.information(self, "Başarılı", f"HTML başarıyla kaydedildi:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"HTML kaydedilemedi: {e}")

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "PDF Olarak Kaydet", "Ders_Programi.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            mode = self.mode_combo.currentText()
            is_portrait = ("Sınıf Dersleri" in mode)
            printer.setPageOrientation(QPageLayout.Orientation.Portrait if is_portrait else QPageLayout.Orientation.Landscape)
            self._paint(printer)
            QMessageBox.information(self, "Başarılı", f"PDF başarıyla kaydedildi:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"PDF kaydedilemedi: {e}")

    def _do_print(self):
        from PySide6.QtPrintSupport import QPrintDialog
        printer = QPrinter(QPrinter.HighResolution)
        mode = self.mode_combo.currentText()
        is_portrait = ("Sınıf Dersleri" in mode)
        printer.setPageOrientation(QPageLayout.Orientation.Portrait if is_portrait else QPageLayout.Orientation.Landscape)
        dlg = QPrintDialog(printer, self)
        if dlg.exec():
            self._paint(printer)

    def _paint(self, printer):
        painter = QPainter(printer)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        mode = self.mode_combo.currentText()
        is_portrait = ("Sınıf Dersleri" in mode)
        VW, VH = (800, 1150) if is_portrait else (1150, 800)
        
        # Normalize coordinate space so PDF, screen preview, and physical printers are 100% identical and high-res
        painter.setViewport(0, 0, printer.width(), printer.height())
        painter.setWindow(0, 0, VW, VH)
        
        try:
            if "Çarşaf Liste : Sınıflar" in mode:
                self._render_carsaf_liste(painter, printer, VW, VH, is_teacher=False)
            elif "Çarşaf Liste : Öğretmenler" in mode:
                self._render_carsaf_liste(painter, printer, VW, VH, is_teacher=True)
            elif "Tablo Olarak : Dersler" in mode:
                self._render_tablo_dersler(painter, printer, VW, VH)
            elif "Tüm Sınıflar" in mode:
                self._render_asc_multi_grid(painter, printer, VW, VH, is_teacher=False)
            elif "Tüm Öğretmenler" in mode:
                self._render_asc_multi_grid(painter, printer, VW, VH, is_teacher=True)
            elif "Sınıf Dersleri" in mode:
                self._render_class_lessons_list(painter, VW, VH)
            elif "Öğretmen Haftalık" in mode:
                self._render_weekly_grid(painter, VW, VH, is_teacher=True)
            elif "Sınıf Haftalık" in mode:
                self._render_weekly_grid(painter, VW, VH, is_teacher=False)
            elif "Tüm Öğretmenlerin Ders Yükü" in mode:
                self._render_teacher_summary_list(painter, VW, VH)
            else:
                self._render_weekly_grid(painter, VW, VH, is_teacher=False)
        except Exception as e:
            import traceback
            traceback.print_exc()
            painter.fillRect(0, 0, VW, VH, Qt.white)
            painter.setFont(QFont("Segoe UI", 12))
            painter.setPen(QPen(QColor("#DC2626"), 1))
            painter.drawText(QRectF(40, 40, VW - 80, VH - 80), Qt.AlignCenter, f"Yazdırma Görünümü Oluşturulurken Hata:\n{e}\n\n(Veriler boş veya eksik olabilir)")
        finally:
            painter.end()

    def _get_pseudo_placements(self, target_name, is_teacher=False):
        """Fetch placements for a class or teacher (day, period) mapped directly from grid_placements and live state."""
        if not hasattr(self, "_placements_cache"):
            self._placements_cache = {}
            
        cache_key = (target_name, is_teacher)
        if cache_key in self._placements_cache:
            return self._placements_cache[cache_key]
            
        res = {}
        
        tr_map = str.maketrans({'İ': 'i', 'I': 'ı', 'ı': 'i', 'Ş': 's', 'ş': 's', 'Ğ': 'g', 'ğ': 'g', 'Ü': 'u', 'ü': 'u', 'Ö': 'o', 'ö': 'o', 'Ç': 'c', 'ç': 'c'})
        
        from functools import lru_cache
        @lru_cache(maxsize=2048)
        def normalize_clean(s):
            if not s: return ""
            raw = str(s).strip()
            # Remove parenthesized class type suffixes like (EA), (SAY), (SÖZ), (DİL)
            import re
            raw = re.sub(r'\s*\((?:ea|say|söz|soz|dil)\)\s*$', '', raw, flags=re.IGNORECASE)
            clean = "".join(c for c in raw.translate(tr_map).lower() if c.isalnum())
            return clean
            
        target_norm = normalize_clean(target_name)
        periods_per_day = int(self.data_store.get("settings", {}).get("periods", 8))
        
        # Comprehensive placements collector across all sources
        # Source 1: data_store["grid_placements"] and auto_schedule_results
        grid_data = list(self.data_store.get("grid_placements", []))
        if not grid_data and self.data_store.get("auto_schedule_results"):
            grid_data.extend(self.data_store.get("auto_schedule_results", []))
        elif self.data_store.get("auto_schedule_results"):
            grid_data.extend(self.data_store.get("auto_schedule_results", []))
            
        for item in grid_data:
            if not isinstance(item, dict): continue
            raw_col = int(item.get("col", 0))
            raw_day = item.get("day")
            raw_period = item.get("period")
            
            if raw_day is not None and raw_period is not None:
                d_idx = int(raw_day)
                p_idx = int(raw_period)
            elif raw_col >= periods_per_day:
                d_idx = raw_col // periods_per_day
                p_idx = raw_col % periods_per_day
            else:
                d_idx = int(item.get("day", item.get("col", 0)))
                p_idx = int(item.get("period", item.get("row", 0)))
                
            dur = int(item.get("duration", 1))
            t_name = item.get("teacher_name") or item.get("teacher") or ""
            c_name = item.get("class_name") or item.get("class") or ""
            s_name = item.get("subject_name") or item.get("subject") or ""
            scolor = item.get("color") or get_subject_color(s_name)
            
            match = False
            if is_teacher:
                if not t_name or not t_name.strip():
                    continue
                tn = normalize_clean(t_name)
                if tn == target_norm or format_tr_name(t_name) == format_tr_name(target_name):
                    match = True
                    other_name = c_name
            else:
                if not c_name or not c_name.strip():
                    continue
                cn = normalize_clean(c_name)
                from auto_scheduler import matches_class
                if cn == target_norm or matches_class(c_name, target_name):
                    match = True
                    other_name = t_name
                    
            if match:
                for off in range(dur):
                    res[(d_idx, p_idx + off)] = {
                        "subject_name": s_name,
                        "teacher_name": other_name,
                        "color": scolor,
                        "is_start": (off == 0),
                        "duration": dur
                    }

        # Source 2: Live placed_lessons from TimetableGrid (if not already set)
        if self.placed_lessons and isinstance(self.placed_lessons, dict):
            for (r, c), item in self.placed_lessons.items():
                if not isinstance(item, dict): continue
                t_name = item.get("teacher_name") or item.get("teacher") or ""
                c_name = item.get("class_name") or item.get("class") or ""
                s_name = item.get("subject_name") or item.get("subject") or ""
                scolor = item.get("color") or get_subject_color(s_name)
                dur = int(item.get("duration", 1))
                
                # Check multi-sheet vs single entity coordinate system
                if c >= periods_per_day:
                    d_idx = c // periods_per_day
                    p_idx = c % periods_per_day
                elif item.get("day") is not None and item.get("period") is not None:
                    d_idx = int(item["day"])
                    p_idx = int(item["period"])
                else:
                    d_idx = c
                    p_idx = r
                    
                match = False
                if is_teacher:
                    if not t_name or not t_name.strip():
                        continue
                    tn = normalize_clean(t_name)
                    if tn == target_norm or format_tr_name(t_name) == format_tr_name(target_name):
                        match = True
                        other_name = c_name
                else:
                    if not c_name or not c_name.strip():
                        continue
                    cn = normalize_clean(c_name)
                    from auto_scheduler import matches_class
                    if cn == target_norm or matches_class(c_name, target_name):
                        match = True
                        other_name = t_name
                        
                if match:
                    for off in range(dur):
                        if (d_idx, p_idx + off) not in res:
                            res[(d_idx, p_idx + off)] = {
                                "subject_name": s_name,
                                "teacher_name": other_name,
                                "color": scolor,
                                "is_start": (off == 0),
                                "duration": dur
                            }
        if res:
            self._placements_cache[cache_key] = res
            return res

        # 3. Third priority: data_store["yerlesim"] (dict)
        yerlesim_data = self.data_store.get("yerlesim", {})
        if isinstance(yerlesim_data, dict) and yerlesim_data:
            for key_str, item in yerlesim_data.items():
                if not isinstance(item, dict): continue
                t_name = item.get("teacher_name") or item.get("teacher") or ""
                c_name = item.get("class_name") or item.get("class") or ""
                s_name = item.get("subject_name") or item.get("subject") or ""
                scolor = item.get("color") or get_subject_color(s_name)
                dur = int(item.get("duration", 1))
                
                match = False
                if is_teacher:
                    if not t_name or not t_name.strip():
                        continue
                    tn = normalize_clean(t_name)
                    if tn == target_norm or format_tr_name(t_name) == format_tr_name(target_name):
                        match = True
                        other_name = c_name
                else:
                    if not c_name or not c_name.strip():
                        continue
                    cn = normalize_clean(c_name)
                    from auto_scheduler import matches_class
                    if cn == target_norm or matches_class(c_name, target_name):
                        match = True
                        other_name = t_name
                        
                if match and "," in str(key_str):
                    try:
                        parts = str(key_str).split(",")
                        r, c = int(parts[0]), int(parts[1])
                        d_idx = c
                        p_idx = r
                        for off in range(dur):
                            res[(d_idx, p_idx + off)] = {
                                "subject_name": s_name,
                                "teacher_name": other_name,
                                "color": scolor,
                                "is_start": (off == 0),
                                "duration": dur
                            }
                    except Exception:
                        pass

        self._placements_cache[cache_key] = res
        return res

    def _render_asc_multi_grid(self, painter, printer, VW, VH, is_teacher=False):
        if is_teacher:
            items = [t.get("ad", "Öğretmen") for t in (self.filtered_teachers if self.filtered_teachers else self.data_store.get("ogretmenler", []))]
        else:
            items = [c.get("ad", "Sınıf") for c in (self.filtered_classes if self.filtered_classes else self.data_store.get("siniflar", []))]
            
        if not items:
            items = ["Örnek 1"]
            
        school_name = self.data_store.get("okul_adi") or self.data_store.get("settings", {}).get("school_name", "Özel Öğretim Kurumu")
        
        # Single entity selected (e.g. 9A or single teacher) -> Center full page with high scale!
        if len(items) == 1:
            margin_x = 35
            margin_y = 25
            cell_w = VW - (2 * margin_x)
            cell_h = VH - (2 * margin_y)
            x = margin_x
            y = margin_y
            placements = self._get_pseudo_placements(items[0], is_teacher)
            self._draw_mini_grid(painter, x, y, cell_w, cell_h, items[0], school_name, placements, is_teacher=is_teacher, is_single_page=True)
            return

        # Grid layout math: 2 columns x 3 rows (6 boxes per page on A4 Landscape)
        cols, rows = 2, 3
        per_page = cols * rows
        
        margin_x, margin_y = 25, 20
        spacing_x, spacing_y = 30, 25
        
        cell_w = (VW - (2 * margin_x) - (cols - 1) * spacing_x) / cols
        cell_h = (VH - (2 * margin_y) - (rows - 1) * spacing_y) / rows
        
        for i, item_name in enumerate(items):
            if i > 0 and i % per_page == 0:
                printer.newPage()
                painter.fillRect(0, 0, VW, VH, Qt.white)
                
            page_idx = i % per_page
            col_idx = page_idx % cols
            row_idx = page_idx // cols
            
            x = margin_x + col_idx * (cell_w + spacing_x)
            y = margin_y + row_idx * (cell_h + spacing_y)
            
            placements = self._get_pseudo_placements(item_name, is_teacher)
            self._draw_mini_grid(painter, x, y, cell_w, cell_h, item_name, school_name, placements, is_teacher=is_teacher, is_single_page=False)

    def _draw_mini_grid(self, painter, x, y, w, h, target_name, school_name, placements, is_teacher=False, is_single_page=False):
        """Draws exact timetable grid matching photo: Pa..Cu on left, 1..8 on top, Bold Subject + Teacher/Class"""
        import datetime
        date_str = datetime.datetime.now().strftime("%d/%m/%Y")
        acad_year = self.data_store.get("settings", {}).get("academic_year", "2026 - 2027")
        year_short = acad_year[:4] if len(acad_year) >= 4 else "2026"
        
        # 1. Header Row
        header_h = 36 if is_single_page else 18
        
        # Top Left: Date (e.g. 12/09/2026)
        painter.setFont(make_font(14 if is_single_page else 8, False))
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawText(QRectF(x, y, w * 0.35, header_h), Qt.AlignLeft | Qt.AlignVCenter, date_str)
        
        # Top Center: Class / Teacher Name (e.g. 9A, 11A, Hüseyin Arman)
        painter.setFont(make_font(32 if is_single_page else 16, True))
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawText(QRectF(x, y - (2 if is_single_page else 0), w, header_h + (12 if is_single_page else 4)), Qt.AlignCenter, str(target_name).upper())
        
        # Top Right: Ders Planı : 2026
        painter.setFont(make_font(14 if is_single_page else 8, False))
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawText(QRectF(x + w * 0.65, y, w * 0.35, header_h), Qt.AlignRight | Qt.AlignVCenter, f"Ders Planı : {year_short}")
        
        # 2. Table Grid
        top_gap = 48 if is_single_page else 22
        grid_x = x
        grid_y = y + top_gap
        grid_w = w
        grid_h = h - top_gap
        
        days = ["Pa", "Sa", "Ça", "Pe", "Cu"]
        periods = int(self.data_store.get("settings", {}).get("periods", 8))
        
        hour_col_w = max(55 if is_single_page else 40, grid_w * (0.08 if is_single_page else 0.08))
        col_header_h = max(32 if is_single_page else 24, grid_h * (0.10 if is_single_page else 0.14))
        
        col_w = (grid_w - hour_col_w) / periods
        row_h = (grid_h - col_header_h) / len(days)
        
        painter.setPen(QPen(QColor("#000000"), 1.4 if is_single_page else 1.0))
        painter.setBrush(Qt.NoBrush)
        
        # Top-Left Corner Box
        painter.drawRect(QRectF(grid_x, grid_y, hour_col_w, col_header_h))
        
        times = [
            "9:00-9:40", "9:50-10:30", "10:40-11:20", "11:30-12:10",
            "12:20-13:00", "14:20-15:00", "15:10-15:50", "16:00-16:40",
            "16:50-17:30", "17:40-18:20", "18:30-19:10", "19:20-20:00"
        ]
        
        # Top Period Column Headers (1..periods with times underneath)
        for p_idx in range(periods):
            cx = grid_x + hour_col_w + p_idx * col_w
            painter.drawRect(QRectF(cx, grid_y, col_w, col_header_h))
            
            painter.setFont(make_font(20 if is_single_page else 10, True))
            painter.drawText(QRectF(cx, grid_y + 1, col_w, col_header_h * 0.55), Qt.AlignCenter | Qt.AlignBottom, str(p_idx + 1))
            
            t_str = times[p_idx] if p_idx < len(times) else f"{8+p_idx}:00-{8+p_idx}:40"
            painter.setFont(make_font(12 if is_single_page else 6, False))
            painter.drawText(QRectF(cx, grid_y + col_header_h * 0.56, col_w, col_header_h * 0.42), Qt.AlignCenter | Qt.AlignTop, t_str)
            
        # Left Day Column Headers & Content Cells
        for d_idx, day_name in enumerate(days):
            ry = grid_y + col_header_h + d_idx * row_h
            painter.drawRect(QRectF(grid_x, ry, hour_col_w, row_h))
            
            painter.setFont(make_font(24 if is_single_page else 12, True))
            painter.drawText(QRectF(grid_x, ry, hour_col_w, row_h), Qt.AlignCenter, day_name)
            
            p_idx = 0
            while p_idx < periods:
                lesson = placements.get((d_idx, p_idx))
                
                cx = grid_x + hour_col_w + p_idx * col_w
                
                if lesson and lesson.get("is_start", True):
                    dur = lesson.get("duration", 1)
                    dur = min(dur, periods - p_idx)
                    block_w = col_w * dur
                    
                    painter.drawRect(QRectF(cx, ry, block_w, row_h))
                    
                    sname = lesson.get("subject_name", "")
                    other_name = lesson.get("teacher_name", "")
                    
                    # Line 1: Subject Short Code in Bold (e.g. BİYO 1, BED, GÖR, MAT)
                    short_subj = get_subject_badge(sname, self.data_store)
                    painter.setFont(make_font(20 if is_single_page else 10, True))
                    painter.setPen(QPen(QColor("#000000"), 1))
                    painter.drawText(QRectF(cx + 2, ry + 2, block_w - 4, row_h * 0.52), Qt.AlignCenter | Qt.AlignVCenter, short_subj)
                    
                    # Line 2: Teacher / Class Name
                    if other_name:
                        if not is_teacher:
                            display_other = format_teacher_display_name(other_name, self.data_store)
                        else:
                            display_other = other_name.replace(" ", "").replace("/", "").replace("-", "").upper()
                            
                        painter.setFont(make_font(15 if is_single_page else 7.5, False))
                        painter.setPen(QPen(QColor("#111111"), 1))
                        painter.drawText(QRectF(cx + 2, ry + row_h * 0.5, block_w - 4, row_h * 0.46), Qt.AlignCenter | Qt.AlignVCenter, display_other)
                    
                    p_idx += dur
                else:
                    if not lesson:
                        painter.drawRect(QRectF(cx, ry, col_w, row_h))
                    p_idx += 1

    def _render_class_lessons_list(self, painter, VW, VH):
        """Sınıfın Dersleri / Öğretmen Atama Listesi Formatı (Fotoğraftaki Birebir aSc Dikey Formu)"""
        selected_class = self.target_combo.currentText()
        if not selected_class or selected_class == "Tümü (Çoklu Sayfa)":
            if self.filtered_classes:
                selected_class = self.filtered_classes[0].get("ad", "11SAY")
            else:
                selected_class = "11SAY"
                
        atamalar = self.data_store.get("atamalar", [])
        if selected_class and selected_class != "Tümü (Çoklu Sayfa)":
            atamalar = [a for a in atamalar if a.get("class") == selected_class]
            
        if not atamalar and self.data_store.get("dersler"):
            atamalar = []
            for d in self.data_store.get("dersler", []):
                atamalar.append({
                    "subject": d.get("ad", "Ders"),
                    "teacher": "Atanmadı",
                    "class": selected_class,
                    "duration": d.get("saat", 2),
                    "length": 1,
                    "color": d.get("renk")
                })

        tbl_x = 25
        tbl_w = VW - 50  # 750 px (Fits perfectly in 800px width portrait)
        
        # 1. Top Window Frame Header
        painter.setPen(QPen(QColor("#94A3B8"), 1))
        painter.setBrush(QBrush(QColor("#E2E8F0")))
        painter.drawRect(QRectF(tbl_x, 20, tbl_w, 24))
        
        painter.setPen(QPen(QColor("#0F172A"), 1))
        painter.setFont(make_font(10, True))
        painter.drawText(QRectF(tbl_x + 8, 20, 20, 24), Qt.AlignCenter, "🗂️")
        painter.drawText(QRectF(tbl_x + 30, 20, 200, 24), Qt.AlignLeft | Qt.AlignVCenter, "Sınıfın Dersleri")
        
        # Class Header Panel
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawRect(QRectF(tbl_x, 44, tbl_w, 48))
        
        # Class Avatar Icon
        draw_class_avatar_icon(painter, tbl_x + 14, 50)
        
        # Class Name (Large Bold) & Subtitle
        painter.setFont(make_font(15, True))
        painter.setPen(QPen(QColor("#0F172A"), 1))
        painter.drawText(QRectF(tbl_x + 56, 48, 300, 22), Qt.AlignLeft | Qt.AlignVCenter, selected_class.upper())
        
        painter.setFont(make_font(9, False))
        painter.setPen(QPen(QColor("#64748B"), 1))
        clean_code = selected_class.replace(" ", "").replace("/", "").replace("-", "").upper()
        painter.drawText(QRectF(tbl_x + 56, 70, 300, 16), Qt.AlignLeft | Qt.AlignVCenter, clean_code)
        
        # 2. Table Headers
        start_y = 96
        header_h = 24
        
        cols = [
            ("Ders", 200),
            ("Öğretmen", 190),
            ("Sınıf", 75),
            ("Topla...", 75),
            ("Uzunluk", 70),
            ("Derslikler", 70),
            ("Hafta", 35),
            ("Dönem", 35)
        ]
        
        painter.setBrush(QBrush(QColor("#E2E8F0")))
        painter.setPen(QPen(QColor("#94A3B8"), 1))
        painter.drawRect(QRectF(tbl_x, start_y, tbl_w, header_h))
        
        painter.setFont(make_font(9, True))
        painter.setPen(QPen(QColor("#1E293B"), 1))
        cur_x = tbl_x
        for col_idx, (col_name, col_width) in enumerate(cols):
            align = Qt.AlignLeft | Qt.AlignVCenter if col_idx < 2 else Qt.AlignCenter
            pad = 8 if col_idx < 2 else 0
            painter.drawText(QRectF(cur_x + pad, start_y, col_width - pad, header_h), align, col_name)
            cur_x += col_width
            if col_idx < len(cols) - 1:
                painter.drawLine(cur_x, start_y, cur_x, start_y + header_h)

        # 3. Table Rows
        row_h = 26
        cur_y = start_y + header_h
        
        for idx, item in enumerate(atamalar):
            if cur_y + row_h > VH - 40:
                break
                
            bg_color = QColor("#F8FAFC") if idx % 2 == 1 else QColor("#FFFFFF")
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawRect(QRectF(tbl_x, cur_y, tbl_w, row_h))
            
            cur_x = tbl_x
            subj_name = item.get("subject", "")
            teacher_name = item.get("teacher", "—")
            cls_name = item.get("class", selected_class)
            dur = str(item.get("duration", 1))
            
            # --- Col 0: Ders (Sol tarafı Rozet/Badge + Sağında Tam İsim) ---
            col_w0 = cols[0][1]
            badge_text = get_subject_badge(subj_name, self.data_store)
            
            # Neutral rounded pill badge
            badge_w = 56
            badge_rect = QRectF(cur_x + 6, cur_y + 3, badge_w, row_h - 6)
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.drawRoundedRect(badge_rect, 3, 3)
            
            painter.setFont(make_font(8.5, True))
            painter.setPen(QPen(QColor("#1E293B"), 1))
            painter.drawText(badge_rect, Qt.AlignCenter, badge_text)
            
            # Full uppercase subject name right next to badge
            painter.setFont(make_font(8.5, True))
            painter.setPen(QPen(QColor("#0F172A"), 1))
            painter.drawText(QRectF(cur_x + 68, cur_y, col_w0 - 70, row_h), Qt.AlignLeft | Qt.AlignVCenter, subj_name.upper())
            
            cur_x += col_w0
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 1: Öğretmen ---
            col_w1 = cols[1][1]
            t_display = format_teacher_display_name(teacher_name, self.data_store)
            painter.setFont(make_font(9, False))
            painter.setPen(QPen(QColor("#1E293B"), 1))
            painter.drawText(QRectF(cur_x + 8, cur_y, col_w1 - 10, row_h), Qt.AlignLeft | Qt.AlignVCenter, t_display)
            cur_x += col_w1
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 2: Sınıf ---
            col_w2 = cols[2][1]
            c_clean = cls_name.replace(" ", "").replace("/", "").replace("-", "").upper()
            painter.setFont(make_font(9, False))
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.drawText(QRectF(cur_x, cur_y, col_w2, row_h), Qt.AlignCenter, c_clean)
            cur_x += col_w2
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 3: Topla... ---
            col_w3 = cols[3][1]
            painter.setFont(make_font(9, False))
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.drawText(QRectF(cur_x, cur_y, col_w3, row_h), Qt.AlignCenter, dur)
            cur_x += col_w3
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 4: Uzunluk ---
            col_w4 = cols[4][1]
            painter.setFont(make_font(9, False))
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.drawText(QRectF(cur_x, cur_y, col_w4, row_h), Qt.AlignCenter, "1")
            cur_x += col_w4
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 5: Derslikler ---
            col_w5 = cols[5][1]
            painter.setFont(make_font(10, False))
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.drawText(QRectF(cur_x, cur_y, col_w5, row_h), Qt.AlignCenter, "🏠")
            cur_x += col_w5
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 6: Hafta ---
            col_w6 = cols[6][1]
            painter.setFont(make_font(9, False))
            painter.setPen(QPen(QColor("#0F172A"), 1))
            painter.drawText(QRectF(cur_x, cur_y, col_w6, row_h), Qt.AlignCenter, "")
            cur_x += col_w6
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(cur_x, cur_y, cur_x, cur_y + row_h)
            
            # --- Col 7: Dönem ---
            col_w7 = cols[7][1]
            painter.setFont(make_font(9, False))
            painter.setPen(QPen(QColor("#0F172A"), 1))
            painter.drawText(QRectF(cur_x, cur_y, col_w7, row_h), Qt.AlignCenter, "")
            
            cur_y += row_h

        painter.setPen(QPen(QColor("#64748B"), 1))
        painter.setFont(make_font(9))
        painter.drawText(QRectF(tbl_x, VH - 35, 400, 20), Qt.AlignLeft, f"Toplam Atanan Ders Sayısı: {len(atamalar)}")
        painter.drawText(QRectF(VW - tbl_x - 300, VH - 35, 300, 20), Qt.AlignRight, "BGZ Ders Planlama Sistemi 2026 - 2027")

    def _render_weekly_grid(self, painter, VW, VH, is_teacher=False):
        """Single class or single teacher timetable on one page (Same exact layout as photo)"""
        target_name = self.target_combo.currentText() or ("Öğretmen" if is_teacher else "Sınıf")
        school_name = self.data_store.get("okul_adi") or self.data_store.get("settings", {}).get("school_name", "Özel Öğretim Kurumu")
        placements = self._get_pseudo_placements(target_name, is_teacher)
        
        margin_x = 35
        margin_y = 25
        grid_w = VW - (2 * margin_x)
        grid_h = VH - (2 * margin_y)
        
        self._draw_mini_grid(painter, margin_x, margin_y, grid_w, grid_h, target_name, school_name, placements, is_teacher=is_teacher, is_single_page=True)

    def _render_teacher_summary_list(self, painter, VW, VH):
        teachers = self.data_store.get("ogretmenler", [])
        atamalar = self.data_store.get("atamalar", [])
        
        painter.setPen(QPen(QColor("#CCCCCC"), 1))
        painter.setBrush(QBrush(QColor("#F5F7FA")))
        painter.drawRoundedRect(30, 20, VW - 60, 50, 6, 6)
        
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.setFont(make_font(16, True))
        painter.drawText(QRectF(50, 25, 600, 40), Qt.AlignLeft | Qt.AlignVCenter, "Tüm Öğretmenlerin Ders Yükü Raporu")
        
        start_y = 85
        tbl_w = VW - 60
        cols = [("Öğretmen Adı", 300), ("Kısa Kodu", 150), ("Atanan Dersler", 400), ("Toplam Saat", 190)]
        
        cur_x = 30
        header_h = 32
        painter.setBrush(QBrush(QColor("#E9ECEF")))
        painter.setPen(QPen(QColor("#BCC8D8"), 1))
        painter.drawRect(QRectF(30, start_y, tbl_w, header_h))
        
        painter.setFont(make_font(12, True))
        for col_name, col_w in cols:
            painter.drawText(QRectF(cur_x, start_y, col_w, header_h), Qt.AlignCenter, col_name)
            cur_x += col_w
            
        cur_y = start_y + header_h
        row_h = 30
        painter.setFont(make_font(11))
        
        for idx, t in enumerate(teachers):
            if cur_y + row_h > VH - 50:
                break
            bg_color = QColor("#F8F9FA") if idx % 2 == 1 else QColor("#FFFFFF")
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(QColor("#E0E0E0"), 1))
            painter.drawRect(QRectF(30, cur_y, tbl_w, row_h))
            
            tname = t.get("ad", "")
            tkisa = t.get("kisa", "")
            t_atamalar = [a for a in atamalar if a.get("teacher") == tname]
            subs_str = ", ".join(list({a.get("subject", "") for a in t_atamalar})) or "—"
            tot_hours = sum(a.get("duration", 1) for a in t_atamalar)
            
            cur_x = 30
            painter.drawText(QRectF(cur_x + 10, cur_y, cols[0][1] - 10, row_h), Qt.AlignLeft | Qt.AlignVCenter, tname)
            cur_x += cols[0][1]
            
            painter.drawText(QRectF(cur_x, cur_y, cols[1][1], row_h), Qt.AlignCenter, tkisa)
            cur_x += cols[1][1]
            
            painter.drawText(QRectF(cur_x + 10, cur_y, cols[2][1] - 10, row_h), Qt.AlignLeft | Qt.AlignVCenter, subs_str)
            cur_x += cols[2][1]
            
            painter.drawText(QRectF(cur_x, cur_y, cols[3][1], row_h), Qt.AlignCenter, f"{tot_hours} Saat")
            cur_y += row_h

    def _render_carsaf_liste(self, painter, printer, VW, VH, is_teacher=False):
        """Toplu Çarşaf Liste: Sınıflar/Öğretmenler. 8 saatlik birebir aSc formatı."""
        import datetime
        import re
        
        date_str = datetime.datetime.now().strftime("%d.%m.%Y")
        school_name = self.data_store.get("okul_adi") or self.data_store.get("settings", {}).get("school_name", "Okul Adı")
        
        def smart_abbr(subject_name):
            s = str(subject_name).strip().upper()
            match = re.search(r'([A-ZÇĞİÖŞÜ]+)\s*(\d+)$', s)
            if match:
                word, num = match.group(1), match.group(2)
                if "MAT" in word: return f"M{num}"
                if "FİZ" in word or "FIZ" in word: return f"F{num}"
                if "KİM" in word or "KIM" in word:
                    if num == "2": return f"KİM2"
                    return f"K{num}"
                if "BİY" in word or "BIY" in word: return f"B{num}"
                return f"{word[:2]}{num}"
                
            if "MAT" in s: return "MAT"
            if "EDE" in s: return "EDE"
            if "TAR" in s: return "TAR"
            if "FİZ" in s or "FIZ" in s: return "FİZ"
            if "BED" in s: return "BED"
            if "KİM" in s or "KIM" in s: return "KİM"
            if "BİY" in s or "BIY" in s: return "BİY"
            if "COĞ" in s or "COG" in s: return "COĞ"
            if "FEL" in s: return "FEL"
            if "DİN" in s or "DIN" in s: return "DİN"
            if "İNG" in s or "ING" in s: return "İNG"
            if "ALM" in s: return "ALM"
            if "MÜZ" in s or "MUZ" in s: return "MÜZ"
            if "GÖR" in s or "GOR" in s: return "GÖR"
            if "REH" in s: return "REH"
            
            words = s.split()
            if len(words) >= 2: return (words[0][:2] + words[1][:1]).upper()
            return s[:3].upper()
            
        items = self.filtered_teachers if is_teacher else self.filtered_classes
        if not items:
            items = [{"ad": "Örnek 1"}]
            
        base_title = "Toplu Çarşaf Liste : Öğretmenler" if is_teacher else "Toplu Çarşaf Liste : Sınıflar"
        
        margin_x, margin_y = 25, 35
        w = VW - (2 * margin_x)
        h = VH - (2 * margin_y)
        
        settings = self.data_store.get("settings", {})
        total_periods = int(settings.get("periods", self.data_store.get("ders_saati", 8)))
        day_cnt = int(settings.get("day_count", self.data_store.get("gun_sayisi", 5)))
        all_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        days = settings.get("days", all_days[:day_cnt])
        if not days:
            days = all_days[:5]
            
        # Period blocks for printing: If total_periods > 8, split into 1-8 and 9-total_periods
        if total_periods <= 8:
            period_blocks = [(0, total_periods)]
        else:
            period_blocks = [(0, 8), (8, total_periods)]
            
        name_col_w = max(100, min(140, int(w * 0.10)))
        grid_w = w - name_col_w
        
        header_h = 42
        row_h = max(32, min(44, int((h - 80) // min(len(items), 12))))
        rows_per_page = max(1, int((h - 80) // row_h))
        total_item_pages = (len(items) + rows_per_page - 1) // rows_per_page
        
        first_page = True
        for b_idx, (start_p, end_p) in enumerate(period_blocks):
            cur_periods_count = end_p - start_p
            if len(period_blocks) > 1:
                title = f"{base_title} (Bölüm {b_idx + 1}: {start_p + 1}–{end_p}. Dersler)"
            else:
                title = base_title
                
            day_w = grid_w / len(days)
            period_w = day_w / cur_periods_count
            
            for p_idx in range(total_item_pages):
                if not first_page:
                    printer.newPage()
                first_page = False
                
                painter.fillRect(0, 0, VW, VH, Qt.white)
                painter.setFont(make_font(18, True))
                painter.setPen(QPen(QColor("#0F172A"), 1))
                painter.drawText(QRectF(margin_x, margin_y, w, 30), Qt.AlignCenter, title)
                painter.setFont(make_font(10, True))
                painter.setPen(QPen(QColor("#475569"), 1))
                painter.drawText(QRectF(margin_x, margin_y + 22, w, 18), Qt.AlignLeft | Qt.AlignBottom, school_name)
                
                cur_y = margin_y + 44
                
                # --- Table Header ---
                painter.setPen(QPen(QColor("#0F172A"), 1.5))
                painter.setBrush(QBrush(QColor("#F1F5F9")))
                painter.drawRect(QRectF(margin_x, cur_y, name_col_w, header_h))
                painter.setFont(make_font(10.5, True))
                painter.setPen(QPen(QColor("#0F172A"), 1))
                header_col_title = "Öğretmen" if is_teacher else "Sınıf"
                painter.drawText(QRectF(margin_x, cur_y, name_col_w, header_h), Qt.AlignCenter, header_col_title)
                
                for d_idx, day_name in enumerate(days):
                    dx = margin_x + name_col_w + d_idx * day_w
                    painter.setPen(QPen(QColor("#0F172A"), 1.5))
                    painter.setBrush(QBrush(QColor("#E2E8F0")))
                    painter.drawRect(QRectF(dx, cur_y, day_w, header_h / 2))
                    painter.setFont(make_font(11, True))
                    painter.setPen(QPen(QColor("#0F172A"), 1))
                    painter.drawText(QRectF(dx, cur_y, day_w, header_h / 2), Qt.AlignCenter, day_name)
                    
                    for p_offset in range(cur_periods_count):
                        p = start_p + p_offset
                        px = dx + p_offset * period_w
                        painter.setPen(QPen(QColor("#0F172A"), 0.8))
                        painter.setBrush(QBrush(QColor("#F8FAFC")))
                        painter.drawRect(QRectF(px, cur_y + header_h / 2, period_w, header_h / 2))
                        painter.setFont(make_font(9.5, True))
                        painter.setPen(QPen(QColor("#334155"), 1))
                        painter.drawText(QRectF(px, cur_y + header_h / 2, period_w, header_h / 2), Qt.AlignCenter, str(p + 1))
                
                cur_y += header_h
                
                page_items = items[p_idx * rows_per_page : (p_idx + 1) * rows_per_page]
                used_subjects = {} # {abbr: full_name}
                
                for item in page_items:
                    target_name = item.get("ad", "")
                    
                    painter.setPen(QPen(QColor("#0F172A"), 1.5))
                    painter.setBrush(QBrush(QColor("#F8FAFC")))
                    painter.drawRect(QRectF(margin_x, cur_y, name_col_w, row_h))
                    painter.setPen(QPen(QColor("#0F172A"), 1))
                    
                    if is_teacher and item.get("kisa"):
                        display_name = item.get("kisa")
                    elif not is_teacher:
                        display_name = target_name.replace("(ea)", "(EA)").replace("(say)", "(SAY)").replace("(soz)", "(SÖZ)").replace("(dil)", "(DİL)")
                    else:
                        display_name = target_name
                        
                    # Dynamically fit font size so name never overflows
                    font_sz = 11.0
                    painter.setFont(make_font(font_sz, True))
                    while painter.fontMetrics().horizontalAdvance(display_name) > (name_col_w - 10) and font_sz > 7.0:
                        font_sz -= 0.5
                        painter.setFont(make_font(font_sz, True))
                        
                    painter.drawText(QRectF(margin_x + 4, cur_y, name_col_w - 8, row_h), Qt.AlignCenter, display_name)
                    
                    placements = self._get_pseudo_placements(target_name, is_teacher)
                    
                    for d_idx in range(len(days)):
                        dx = margin_x + name_col_w + d_idx * day_w
                        for p_offset in range(cur_periods_count):
                            p = start_p + p_offset
                            px = dx + p_offset * period_w
                            
                            lesson = placements.get((d_idx, p))
                            if lesson:
                                sname = lesson.get("subject_name", "")
                                if str(sname).strip().lower() in ["boş", "bos", "-", "—"]:
                                    painter.setBrush(QBrush(QColor("#FFFFFF")))
                                    painter.setPen(QPen(QColor("#0F172A"), 0.8))
                                    painter.drawRect(QRectF(px, cur_y, period_w, row_h))
                                    continue
                                    
                                if is_teacher:
                                    raw_c = str(lesson.get("class_name", ""))
                                    if "," in raw_c or "&" in raw_c or "+" in raw_c:
                                        parts = [c.split("(")[0].strip().replace(" ", "").upper() for c in raw_c.replace("&", ",").replace("+", ",").split(",") if c.strip()]
                                        cell_text = "+".join(parts) if parts else ""
                                    else:
                                        cell_text = raw_c.split("(")[0].strip().replace(" ", "").upper()
                                else:
                                    cell_text = smart_abbr(sname)
                                    used_subjects[cell_text] = sname
                                    
                                painter.setBrush(QBrush(QColor("#FFFFFF")))
                                painter.setPen(QPen(QColor("#0F172A"), 0.8))
                                painter.drawRect(QRectF(px, cur_y, period_w, row_h))
                                
                                if cell_text:
                                    font_sz = 9.5
                                    painter.setFont(make_font(font_sz, True))
                                    while painter.fontMetrics().horizontalAdvance(cell_text) > (period_w - 2) and font_sz > 5.0:
                                        font_sz -= 0.5
                                        painter.setFont(make_font(font_sz, True))
                                    painter.setPen(QPen(QColor("#0F172A"), 1))
                                    
                                    painter.save()
                                    painter.setClipRect(QRectF(px + 1, cur_y + 1, period_w - 2, row_h - 2))
                                    painter.drawText(QRectF(px + 1, cur_y + 1, period_w - 2, row_h - 2), Qt.AlignCenter, cell_text)
                                    painter.restore()
                            else:
                                painter.setBrush(QBrush(QColor("#FFFFFF")))
                                painter.setPen(QPen(QColor("#0F172A"), 0.8))
                                painter.drawRect(QRectF(px, cur_y, period_w, row_h))
                    
                    cur_y += row_h
                    
                # --- Structured Legend Section Immediately Under Table ---
                if not is_teacher:
                    if not used_subjects:
                        for d_item in self.data_store.get("dersler", []):
                            d_name = d_item.get("ad", "").strip()
                            if d_name:
                                used_subjects[smart_abbr(d_name)] = d_name

                legend_items = sorted([(k, v) for k, v in used_subjects.items() if k and v], key=lambda x: x[0])
                
                leg_start_y = cur_y + 12
                if legend_items:
                    num_cols = 5
                    col_w = (w - 20) / num_cols
                    item_h = 16
                    num_rows = (len(legend_items) + num_cols - 1) // num_cols
                    box_h = 24 + num_rows * item_h + 8
                    
                    # Boundary safety
                    if leg_start_y + box_h > VH - margin_y - 25:
                        box_h = max(30, VH - margin_y - 25 - leg_start_y)
                        
                    painter.setPen(QPen(QColor("#CBD5E1"), 1.2))
                    painter.setBrush(QBrush(QColor("#F8FAFC")))
                    painter.drawRoundedRect(QRectF(margin_x, leg_start_y, w, box_h), 5, 5)
                    
                    # Legend Header
                    painter.setFont(make_font(9.5, True))
                    painter.setPen(QPen(QColor("#1E293B"), 1))
                    painter.drawText(QRectF(margin_x + 10, leg_start_y + 4, w - 20, 16), Qt.AlignLeft | Qt.AlignVCenter, "📌 Ders Kısaltmaları ve Açıklamaları:")
                    
                    # Legend Items Grid
                    for idx, (abbr, full_name) in enumerate(legend_items):
                        c_idx = idx % num_cols
                        r_idx = idx // num_cols
                        
                        item_x = margin_x + 12 + c_idx * col_w
                        item_y = leg_start_y + 22 + r_idx * item_h
                        
                        if item_y + item_h <= leg_start_y + box_h:
                            painter.setFont(make_font(8.5, True))
                            painter.setPen(QPen(QColor("#0F172A"), 1))
                            prefix = f"• {abbr}: "
                            p_w = painter.fontMetrics().horizontalAdvance(prefix)
                            painter.drawText(QRectF(item_x, item_y, p_w + 4, item_h), Qt.AlignLeft | Qt.AlignVCenter, prefix)
                            
                            painter.setFont(make_font(8.5, False))
                            painter.setPen(QPen(QColor("#334155"), 1))
                            val_rect = QRectF(item_x + p_w, item_y, col_w - p_w - 6, item_h)
                            painter.drawText(val_rect, Qt.AlignLeft | Qt.AlignVCenter, full_name)
                            
                    leg_bottom = leg_start_y + box_h + 8
                else:
                    leg_bottom = leg_start_y + 8

                # Footer
                painter.setFont(make_font(8.5, False))
                painter.setPen(QPen(QColor("#64748B"), 1))
                painter.drawText(QRectF(margin_x, min(leg_bottom, VH - margin_y + 14), w / 2, 18), Qt.AlignLeft, f"Ders Planı Oluşturuldu: {date_str}")
                painter.drawText(QRectF(margin_x + w / 2, min(leg_bottom, VH - margin_y + 14), w / 2, 18), Qt.AlignRight, "BGZ Ders Planlama")


    def _render_tablo_dersler(self, painter, printer, VW, VH):
        """Tablo Olarak: Dersler. Her ders ayrı bir sayfada."""
        import datetime
        date_str = datetime.datetime.now().strftime("%d.%m.%Y")
        school_name = self.data_store.get("okul_adi") or self.data_store.get("settings", {}).get("school_name", "Okul Adı")
        
        dersler = self.data_store.get("dersler", [])
        if not dersler:
            dersler = [{"ad": "MATEMATİK", "kisa": "MAT"}]
            
        margin_x, margin_y = 60, 60
        w = VW - (2 * margin_x)
        h = VH - (2 * margin_y)
        
        days = ["Pa", "Sa", "Ça", "Pe", "Cu"]
        periods = 8
        times = [
            "8:00 - 8:45", "9:00 - 9:45", "10:00 - 10:45", "11:00 - 11:45",
            "12:00 - 12:45", "13:00 - 13:45", "14:00 - 14:45", "15:00 - 15:45"
        ]
        
        day_col_w = 80
        grid_w = w - day_col_w
        period_w = grid_w / periods
        
        header_h = 60
        row_h = (h - header_h - 80) / len(days) # 80 is for title space
        
        for i, ders in enumerate(dersler):
            if i > 0:
                printer.newPage()
                painter.fillRect(0, 0, VW, VH, Qt.white)
                
            sname = ders.get("ad", "")
            short_name = ders.get("kisa") or get_subject_badge(sname, self.data_store)
            
            # Title
            painter.setFont(make_font(36, False))
            painter.setPen(QPen(QColor("#000000"), 1))
            painter.drawText(QRectF(margin_x, margin_y, w, 50), Qt.AlignCenter, short_name)
            
            # School Name
            painter.setFont(make_font(10, False))
            painter.drawText(QRectF(margin_x, margin_y + 45, w, 20), Qt.AlignLeft | Qt.AlignBottom, school_name)
            
            table_y = margin_y + 70
            
            # Grid
            painter.setPen(QPen(QColor("#000000"), 1.5))
            painter.setBrush(Qt.NoBrush)
            
            # Empty top-left
            painter.drawRect(QRectF(margin_x, table_y, day_col_w, header_h))
            
            # Column headers (Periods & Times)
            for p in range(periods):
                px = margin_x + day_col_w + p * period_w
                painter.drawRect(QRectF(px, table_y, period_w, header_h))
                
                painter.setFont(make_font(16, False))
                painter.drawText(QRectF(px, table_y + 5, period_w, header_h / 2), Qt.AlignCenter | Qt.AlignBottom, str(p + 1))
                
                painter.setFont(make_font(8, False))
                t_str = times[p] if p < len(times) else f"{8+p}:00 - {8+p}:45"
                painter.drawText(QRectF(px, table_y + header_h / 2, period_w, header_h / 2), Qt.AlignCenter | Qt.AlignTop, t_str)
                
            cur_y = table_y + header_h
            
            # Gather all placements for this subject across all classes
            subj_placements = {} # (day, period) -> list of (class, teacher)
            
            # Ensure we are reading live grid data or saved grid_placements
            grid_data = self.data_store.get("grid_placements", [])
            for item in grid_data:
                if item.get("subject_name") == sname or item.get("subject") == sname:
                    r = int(item.get("period", item.get("row", 0)))
                    c = int(item.get("day", item.get("col", 0)))
                    dur = int(item.get("duration", 1))
                    cls = item.get("class_name") or item.get("class") or ""
                    tchr = item.get("teacher_name") or item.get("teacher") or ""
                    
                    for off in range(dur):
                        if (c, r + off) not in subj_placements:
                            subj_placements[(c, r + off)] = []
                        subj_placements[(c, r + off)].append((cls, tchr))
            
            # Rows (Days)
            for d_idx, day_name in enumerate(days):
                ry = cur_y + d_idx * row_h
                painter.drawRect(QRectF(margin_x, ry, day_col_w, row_h))
                painter.setFont(make_font(24, False))
                painter.drawText(QRectF(margin_x, ry, day_col_w, row_h), Qt.AlignCenter, day_name)
                
                for p in range(periods):
                    px = margin_x + day_col_w + p * period_w
                    painter.drawRect(QRectF(px, ry, period_w, row_h))
                    
                    placements = subj_placements.get((d_idx, p), [])
                    if placements:
                        # Draw first placement (typically there's only 1 or 2 classes doing this subject at this time)
                        cls, tchr = placements[0]
                        if "," in cls or "&" in cls or "+" in cls:
                            parts = [c.split("(")[0].strip().replace(" ", "").upper() for c in cls.replace("&", ",").replace("+", ",").split(",") if c.strip()]
                            cls_str = "+".join(parts) if parts else ""
                        else:
                            cls_str = cls.split("(")[0].strip().replace(" ", "").upper()
                        
                        font_sz = 12
                        painter.setFont(make_font(font_sz, True))
                        while painter.fontMetrics().horizontalAdvance(cls_str) > (period_w - 4) and font_sz > 5.0:
                            font_sz -= 0.5
                            painter.setFont(make_font(font_sz, True))
                            
                        painter.drawText(QRectF(px, ry, period_w, row_h / 2), Qt.AlignCenter | Qt.AlignBottom, cls_str)
                        
                        painter.setFont(make_font(10, False))
                        if tchr:
                            # Short teacher name (e.g. H. ARMAN)
                            parts = tchr.split()
                            if len(parts) >= 2:
                                t_str = f"{parts[0][0].upper()}. {parts[1].upper()}"
                            else:
                                t_str = tchr.upper()
                            painter.drawText(QRectF(px, ry + row_h / 2, period_w, row_h / 2), Qt.AlignCenter | Qt.AlignTop, t_str)
            
            # Footer
            painter.setFont(make_font(8, False))
            painter.drawText(QRectF(margin_x, cur_y + len(days) * row_h + 10, w / 2, 20), Qt.AlignLeft, f"Ders Planı Oluşturuldu:{date_str}")
            painter.drawText(QRectF(margin_x + w / 2, cur_y + len(days) * row_h + 10, w / 2, 20), Qt.AlignRight, "BGZ Ders Planlama")
