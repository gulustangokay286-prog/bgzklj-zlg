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

def make_font(size, bold=False):
    f = QFont("Arial")
    f.setPixelSize(size)
    f.setBold(bold)
    return f

class TimetablePrintPreview(QDialog):
    def __init__(self, data_store=None, placed_lessons=None, filters=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Baskı Ön İzleme ve PDF Raporu")
        self.resize(1050, 780)
        
        self.data_store = data_store or {}
        self.placed_lessons = placed_lessons or {}
        self.filters = filters or {}

        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        
        # ── Controls Header Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)
        
        top_bar.addWidget(QLabel("Rapor Türü:", self))
        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems([
            "[BİREBİR] Tüm Sınıflar (Kağıt Tasarrufu - Sayfada 6'lı)",
            "[BİREBİR] Tüm Öğretmenler (Kağıt Tasarrufu - Sayfada 6'lı)",
            "Sınıf Dersleri & Atama Listesi (Liste Formatı)",
            "Sınıf Haftalık Ders Programı (Tam Sayfa Renkli Grid)",
            "Öğretmen Haftalık Ders Programı (Tam Sayfa Renkli Grid)",
            "Tüm Öğretmenlerin Ders Yükü Listesi"
        ])
        self.mode_combo.setMinimumWidth(340)
        
        if self.filters.get("entity_type") == "class":
            self.mode_combo.setCurrentIndex(3)
        elif self.filters.get("entity_type") == "teacher":
            self.mode_combo.setCurrentIndex(4)
            
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
        
        # ── Printer & Preview Widget
        self.printer = QPrinter(QPrinter.HighResolution)
        self.printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        
        self.preview = QPrintPreviewWidget(self.printer, self)
        self.preview.paintRequested.connect(self._render_page)
        main_layout.addWidget(self.preview, 1)
        
        self._populate_targets()
        
    def _on_mode_changed(self, idx):
        self._populate_targets()
        self._repaint()
        
    def _populate_targets(self):
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        mode_idx = self.mode_combo.currentIndex()
        
        if mode_idx in [0, 1]:  # Birebir aSc Formatları (Tüm Sınıflar / Tüm Öğretmenler)
            self.target_combo.addItem("Tümü (Çoklu Sayfa)")
        elif mode_idx in [2, 3]:  # Tekil Sınıf
            classes = self.filtered_classes
            self.target_combo.addItem("Tüm Sınıflar")
            for c in classes:
                self.target_combo.addItem(c.get("ad", "Sınıf"))
        elif mode_idx == 4:  # Tekil Öğretmen
            teachers = self.filtered_teachers
            self.target_combo.addItem("Tüm Öğretmenler")
            for t in teachers:
                self.target_combo.addItem(t.get("ad", "Öğretmen"))
        else:
            self.target_combo.addItem("Genel Özet")
            
        selected_item = None
        if self.filters:
            sel_list = self.filters.get("selected_items") or self.filters.get("classes") or self.filters.get("teachers")
            if sel_list:
                selected_item = sel_list[0]
                
        if selected_item:
            idx = self.target_combo.findText(selected_item)
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
            elif self.target_combo.count() > 1:
                self.target_combo.setCurrentIndex(1)

        self.target_combo.blockSignals(False)

    def _repaint(self):
        self.preview.updatePreview()

    @property
    def filtered_classes(self):
        all_classes = self.data_store.get("siniflar", [])
        if not self.filters:
            return all_classes
        target_list = self.filters.get("classes") or self.filters.get("selected_items") or []
        if not target_list:
            return all_classes
        return [c for c in all_classes if c.get("ad") in target_list]

    @property
    def filtered_teachers(self):
        all_teachers = self.data_store.get("ogretmenler", [])
        if not self.filters:
            return all_teachers
        target_list = self.filters.get("teachers") or self.filters.get("selected_items") or []
        if not target_list:
            return all_teachers
        return [t for t in all_teachers if t.get("ad") in target_list]

    def _update_preview(self):
        self.preview.print_()

    def _do_print(self):
        from PySide6.QtPrintSupport import QPrintDialog
        dialog = QPrintDialog(self.printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            self._render_page(self.printer)

    def direct_print(self):
        from PySide6.QtPrintSupport import QPrintDialog
        dialog = QPrintDialog(self.printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            self._render_page(self.printer)

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "PDF Olarak Kaydet", "Ders_Programi.pdf", "PDF Dosyaları (*.pdf)")
        if path:
            pdf_printer = QPrinter(QPrinter.HighResolution)
            pdf_printer.setOutputFormat(QPrinter.PdfFormat)
            pdf_printer.setOutputFileName(path)
            pdf_printer.setPageOrientation(QPageLayout.Orientation.Landscape)
            self._render_page(pdf_printer)
            QMessageBox.information(self, "PDF Başarılı", f"PDF raporu başarıyla kaydedildi:\n{path}")

    def _export_html(self):
        path, _ = QFileDialog.getSaveFileName(self, "HTML Web Çıktısı Olarak Kaydet", "Ders_Programi.html", "HTML Dosyaları (*.html)")
        if path:
            from py_export.html_exporter import export_to_html
            export_to_html(self.filtered_classes, self.filtered_teachers, self.data_store, self.placed_lessons, path)
            QMessageBox.information(self, "HTML Başarılı", f"Web için HTML raporu başarıyla kaydedildi:\n{path}")

    def _render_page(self, printer):
        painter = QPainter(printer)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        page_rect = printer.pageRect(QPrinter.DevicePixel)
        pw = page_rect.width()
        ph = page_rect.height()
        
        # Virtual coordinate system (1100 x 800) for resolution-independent pixel perfect layout
        VW, VH = 1100, 800
        painter.setViewport(int(page_rect.x()), int(page_rect.y()), int(pw), int(ph))
        painter.setWindow(0, 0, VW, VH)
        
        painter.fillRect(0, 0, VW, VH, Qt.white)
        
        mode_idx = self.mode_combo.currentIndex()
        if mode_idx == 0:
            self._render_asc_multi_grid(painter, printer, VW, VH, is_teacher=False)
        elif mode_idx == 1:
            self._render_asc_multi_grid(painter, printer, VW, VH, is_teacher=True)
        elif mode_idx == 2:
            self._render_class_lessons_list(painter, VW, VH)
        elif mode_idx == 3:
            self._render_weekly_grid(painter, VW, VH, is_teacher=False)
        elif mode_idx == 4:
            self._render_weekly_grid(painter, VW, VH, is_teacher=True)
        elif mode_idx == 5:
            self._render_teacher_summary_list(painter, VW, VH)
            
        painter.end()

    # =======================================================
    # BİREBİR aSc MULTI-GRID KAĞIT TASARRUFU RENDERER
    # =======================================================
    def _get_pseudo_placements(self, target_name, is_teacher):
        """Fetches actual grid cell placements for target class or teacher, indexed as (day_idx, period_idx)."""
        res = {}
        raw_placed = self.placed_lessons or self.data_store.get("grid_placements", {})
        
        for key, data in raw_placed.items():
            if isinstance(key, str) and "," in key:
                parts = key.split(",")
                r, c = int(parts[0]), int(parts[1])
            elif isinstance(key, (tuple, list)) and len(key) >= 2:
                r, c = int(key[0]), int(key[1])
            else:
                continue
                
            # Key format in grid_placements / _placed_lessons: r=period_idx (0..7), c=day_idx (0..4)
            period_idx = r
            day_idx = c
            
            t_name = data.get("teacher") or data.get("teacher_name", "")
            c_name = data.get("class") or data.get("class_name", "")
            s_name = data.get("subject") or data.get("subject_name", "")
            scolor = data.get("color", "")
            dur = int(data.get("duration", 1))
            
            match = (t_name == target_name) if is_teacher else (c_name == target_name or not c_name)
            if match:
                for d_off in range(dur):
                    p_curr = period_idx + d_off
                    if p_curr < 8:
                        res[(day_idx, p_curr)] = {
                            "subject_name": s_name,
                            "teacher_name": c_name if is_teacher else t_name,
                            "color": scolor
                        }
                        
        if res:
            return res

        # Fallback if grid has no placed cards for this item yet, pull from atamalar
        atamalar = self.data_store.get("atamalar", [])
        filtered = [a for a in atamalar if (is_teacher and a.get("teacher") == target_name) or (not is_teacher and a.get("class") == target_name)]
        for item in filtered:
            dur = int(item.get("duration", 1))
            sname = item.get("subject", "")
            tname = item.get("teacher", "") if not is_teacher else item.get("class", "")
            scolor = item.get("color", "")
            r, c = 0, 0
            for d_off in range(dur):
                while (c, r) in res:
                    r += 1
                    if r >= 8: r = 0; c += 1
                    if c >= 5: break
                if c >= 5: break
                res[(c, r)] = {"subject_name": sname, "teacher_name": tname, "color": scolor}
                r += 1
                if r >= 8: r = 0; c += 1
        return res

    def _render_asc_multi_grid(self, painter, printer, VW, VH, is_teacher=False):
        selected_target = self.target_combo.currentText()
        if selected_target and selected_target not in ["Tümü (Çoklu Sayfa)", "Tüm Sınıflar", "Tüm Öğretmenler", "Genel Özet"]:
            items = [selected_target]
        else:
            if is_teacher:
                items = [t.get("ad", "Öğretmen") for t in self.filtered_teachers]
            else:
                items = [c.get("ad", "Sınıf") for c in self.filtered_classes]
            
        if not items:
            items = ["Örnek 1"]
            
        school_name = self.data_store.get("okul_adi", "ÇORUM - MERKEZ / Özel Çorum Birey Özel Öğretim Kursu")
        
        # If single item selected (e.g. 12 / A), render large centered grid on full page!
        if len(items) == 1:
            cell_w = 980
            cell_h = 560
            margin_x = (VW - cell_w) / 2
            margin_y = (VH - cell_h) / 2
            placements = self._get_pseudo_placements(items[0], is_teacher)
            self._draw_mini_grid(painter, margin_x, margin_y, cell_w, cell_h, items[0], school_name, placements, is_single=True)
            return

        # Multi-grid layout (6 per page)
        rows, cols = 3, 2
        per_page = rows * cols
        
        margin_x, margin_y = 20, 20
        spacing_x, spacing_y = 25, 25
        
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
            self._draw_mini_grid(painter, x, y, cell_w, cell_h, item_name, school_name, placements, is_single=False)

    def _draw_mini_grid(self, painter, x, y, w, h, target_name, school_name, placements, is_single=False):
        top_font_size = 10 if is_single else 7
        title_font_size = 24 if is_single else 18
        
        painter.setFont(make_font(top_font_size))
        painter.setPen(QPen(QColor("#000000"), 1))
        title_h = 35 if is_single else 25
        painter.drawText(QRectF(x, y, w, title_h * 0.5), Qt.AlignLeft | Qt.AlignBottom, school_name)
        
        painter.setFont(make_font(title_font_size, True))
        painter.drawText(QRectF(x, y + title_h * 0.25, w, title_h), Qt.AlignCenter, target_name)
        
        painter.setFont(make_font(top_font_size))
        painter.drawText(QRectF(x, y, w, title_h * 0.5), Qt.AlignRight | Qt.AlignBottom, "Ders Planı: 2025")
        
        days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"] if is_single else ["Pa", "Sa", "Ça", "Pe", "Cu"]
        periods = 8
        
        header_space = 50 if is_single else 45
        grid_x = x
        grid_y = y + header_space
        grid_w = w
        grid_h = h - header_space
        
        hour_col_w = 80 if is_single else 40
        header_h = 32 if is_single else 25
        
        col_w = (grid_w - hour_col_w) / periods
        row_h = (grid_h - header_h) / len(days)
        
        pen_line = QPen(QColor("#000000"), 2 if is_single else 1)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen_line)
        
        # Top Left Cell
        painter.drawRect(QRectF(grid_x, grid_y, hour_col_w, header_h))
        
        times = [
            "9:00-9:40", "9:50-10:30", "10:40-11:20", "11:30-12:10",
            "12:20-13:00", "14:20-15:00", "15:10-15:50", "16:00-16:40"
        ]
        
        for p_idx in range(periods):
            cx = grid_x + hour_col_w + p_idx * col_w
            painter.drawRect(QRectF(cx, grid_y, col_w, header_h))
            painter.setFont(make_font(14 if is_single else 10, True))
            painter.drawText(QRectF(cx, grid_y, col_w, header_h * 0.55), Qt.AlignCenter | Qt.AlignBottom, str(p_idx + 1))
            painter.setFont(make_font(8 if is_single else 5))
            painter.drawText(QRectF(cx, grid_y + header_h * 0.55, col_w, header_h * 0.45), Qt.AlignCenter | Qt.AlignTop, times[p_idx])
            
        for d_idx, day_name in enumerate(days):
            ry = grid_y + header_h + d_idx * row_h
            painter.drawRect(QRectF(grid_x, ry, hour_col_w, row_h))
            painter.setFont(make_font(13 if is_single else 11, True))
            painter.drawText(QRectF(grid_x, ry, hour_col_w, row_h), Qt.AlignCenter, day_name)
            
            for p_idx in range(periods):
                cx = grid_x + hour_col_w + p_idx * col_w
                painter.drawRect(QRectF(cx, ry, col_w, row_h))
                
                # Fetch lesson at (day_idx, period_idx)
                lesson = placements.get((d_idx, p_idx))
                if lesson:
                    sname = lesson.get("subject_name", "")
                    tname = lesson.get("teacher_name", "")
                    
                    subj_font_size = 14 if is_single else 9
                    teacher_font_size = 11 if is_single else 7
                    
                    painter.setPen(QPen(QColor("#000000"), 1))
                    
                    painter.setFont(make_font(subj_font_size, True))
                    painter.drawText(QRectF(cx + 2, ry + 4, col_w - 4, row_h * 0.45), Qt.AlignCenter, sname)
                    
                    if tname:
                        painter.setFont(make_font(teacher_font_size))
                        painter.drawText(QRectF(cx + 2, ry + row_h * 0.5, col_w - 4, row_h * 0.45), Qt.AlignCenter, tname)

    # =======================================================
    # ESKİ LİSTE VE TAM SAYFA RENDERER (KORUNANLAR)
    # =======================================================
    def _render_class_lessons_list(self, painter, VW, VH):
        """Sınıfın Dersleri / Öğretmen Atama Listesi Formatı"""
        selected_class = self.target_combo.currentText()
        school_name = self.data_store.get("okul_adi", "ÇORUM - MERKEZ / Özel Çorum Birey Özel Öğretim Kursu")
        
        atamalar = self.data_store.get("atamalar", [])
        if selected_class and selected_class != "Tüm Sınıflar":
            atamalar = [a for a in atamalar if a.get("class") == selected_class]
            
        if not atamalar and self.data_store.get("dersler"):
            atamalar = []
            for d in self.data_store.get("dersler", []):
                atamalar.append({
                    "subject": d.get("ad", "Ders"),
                    "teacher": "Atanmadı",
                    "class": selected_class if selected_class != "Tüm Sınıflar" else "9A",
                    "duration": d.get("saat", 2),
                    "length": 1,
                    "color": d.get("renk")
                })

        painter.setPen(QPen(QColor("#CCCCCC"), 1))
        painter.setBrush(QBrush(QColor("#F5F7FA")))
        painter.drawRoundedRect(30, 20, VW - 60, 60, 6, 6)
        
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.setFont(make_font(14, True))
        painter.drawText(QRectF(50, 28, 400, 24), Qt.AlignLeft | Qt.AlignVCenter, "Sınıfın Dersleri")
        
        painter.setFont(make_font(13, True))
        target_title = selected_class if selected_class and selected_class != "Tüm Sınıflar" else "TÜM SINIFLAR"
        painter.drawText(QRectF(VW - 300, 28, 250, 24), Qt.AlignRight | Qt.AlignVCenter, target_title)
        
        painter.setFont(make_font(10))
        painter.drawText(QRectF(50, 52, 600, 20), Qt.AlignLeft | Qt.AlignVCenter, school_name)
        
        start_y = 95
        tbl_w = VW - 60
        cols = [
            ("Ders", 240), ("Öğretmen", 240), ("Sınıf", 100), ("Toplam", 90),
            ("Uzunluk", 90), ("Derslikler", 100), ("Hafta", 90), ("Dönem", 90)
        ]
        
        cur_x = 30
        header_h = 32
        painter.setBrush(QBrush(QColor("#E9ECEF")))
        painter.setPen(QPen(QColor("#BCC8D8"), 1))
        painter.drawRect(QRectF(30, start_y, tbl_w, header_h))
        
        painter.setFont(make_font(12, True))
        for col_name, col_width in cols:
            painter.drawText(QRectF(cur_x, start_y, col_width, header_h), Qt.AlignCenter, col_name)
            cur_x += col_width
            painter.drawLine(cur_x, start_y, cur_x, start_y + header_h)

        row_h = 30
        cur_y = start_y + header_h
        painter.setFont(make_font(10))
        
        for idx, item in enumerate(atamalar):
            if cur_y + row_h > VH - 50:
                break
                
            bg_color = QColor("#F8F9FA") if idx % 2 == 1 else QColor("#FFFFFF")
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(QColor("#E0E0E0"), 1))
            painter.drawRect(QRectF(30, cur_y, tbl_w, row_h))
            
            cur_x = 30
            subj_name = item.get("subject", "")
            teacher_name = item.get("teacher", "—")
            cls_name = item.get("class", selected_class)
            dur = str(item.get("duration", 1))
            
            subj_color = get_subject_color(subj_name, item.get("color"))
            painter.setBrush(QBrush(QColor(subj_color)))
            painter.drawRoundedRect(cur_x + 8, cur_y + 8, 14, 14, 3, 3)
            
            painter.setPen(QPen(QColor("#111111"), 1))
            painter.drawText(QRectF(cur_x + 30, cur_y, cols[0][1] - 35, row_h), Qt.AlignLeft | Qt.AlignVCenter, subj_name)
            cur_x += cols[0][1]
            
            painter.drawText(QRectF(cur_x + 10, cur_y, cols[1][1] - 10, row_h), Qt.AlignLeft | Qt.AlignVCenter, teacher_name)
            cur_x += cols[1][1]
            
            painter.drawText(QRectF(cur_x, cur_y, cols[2][1], row_h), Qt.AlignCenter, cls_name)
            cur_x += cols[2][1]
            
            painter.drawText(QRectF(cur_x, cur_y, cols[3][1], row_h), Qt.AlignCenter, dur)
            cur_x += cols[3][1]
            
            painter.drawText(QRectF(cur_x, cur_y, cols[4][1], row_h), Qt.AlignCenter, "1")
            cur_x += cols[4][1]
            
            painter.drawText(QRectF(cur_x, cur_y, cols[5][1], row_h), Qt.AlignCenter, "🏠")
            cur_x += cols[5][1]
            
            painter.drawText(QRectF(cur_x, cur_y, cols[6][1], row_h), Qt.AlignCenter, "1")
            cur_x += cols[6][1]
            
            painter.drawText(QRectF(cur_x, cur_y, cols[7][1], row_h), Qt.AlignCenter, "1")
            cur_y += row_h

        painter.setPen(QPen(QColor("#777777"), 1))
        painter.setFont(make_font(9))
        painter.drawText(QRectF(30, VH - 35, 400, 20), Qt.AlignLeft, f"Toplam Atanan Ders Sayısı: {len(atamalar)}")
        painter.drawText(QRectF(VW - 430, VH - 35, 400, 20), Qt.AlignRight, "BGZ Ders Planlama System v2025")

    def _render_weekly_grid(self, painter, VW, VH, is_teacher=False):
        """Eski Tam Sayfa Renkli Grid"""
        target_name = self.target_combo.currentText() or "Genel"
        school_name = self.data_store.get("okul_adi", "ÇORUM - MERKEZ / Özel Çorum Birey Özel Öğretim Kursu")
        
        painter.setFont(make_font(18, True))
        painter.setPen(QPen(QColor("#111111"), 1))
        title_str = f"{target_name} {'Öğretmeni' if is_teacher else 'Sınıfı'} Haftalık Ders Programı"
        painter.drawText(QRectF(30, 20, VW - 60, 30), Qt.AlignCenter, title_str)
        
        painter.setFont(make_font(10))
        painter.drawText(QRectF(30, 48, 600, 18), Qt.AlignLeft, school_name)
        
        days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
        periods = 8
        times = ["08:00-08:45", "08:55-09:40", "09:50-10:35", "10:45-11:30", "11:40-12:25", "13:15-14:00", "14:10-14:55", "15:05-15:50"]
        
        grid_x, grid_y = 30, 70
        grid_w, grid_h = VW - 60, VH - 120
        hour_col_w, header_h = 110, 45
        col_w = (grid_w - hour_col_w) / len(days)
        row_h = (grid_h - header_h) / periods
        
        painter.setBrush(QBrush(QColor("#D0D8E4")))
        painter.setPen(QPen(QColor("#BCC8D8"), 1))
        painter.drawRect(QRectF(grid_x, grid_y, hour_col_w, header_h))
        painter.setFont(make_font(12, True))
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.drawText(QRectF(grid_x, grid_y, hour_col_w, header_h), Qt.AlignCenter, "Saat / Gün")
        
        for d_idx, day_name in enumerate(days):
            cx = grid_x + hour_col_w + d_idx * col_w
            painter.setBrush(QBrush(QColor("#D0D8E4")))
            painter.setPen(QPen(QColor("#BCC8D8"), 1))
            painter.drawRect(QRectF(cx, grid_y, col_w, header_h))
            
            painter.setFont(make_font(13, True))
            painter.setPen(QPen(QColor("#111111"), 1))
            painter.drawText(QRectF(cx, grid_y, col_w, header_h), Qt.AlignCenter, day_name)

        placements = self._get_pseudo_placements(target_name, is_teacher)

        for p_idx in range(periods):
            ry = grid_y + header_h + p_idx * row_h
            painter.setBrush(QBrush(QColor("#F5F7FA")))
            painter.setPen(QPen(QColor("#DDDDDD"), 1))
            painter.drawRect(QRectF(grid_x, ry, hour_col_w, row_h))
            
            painter.setFont(make_font(12, True))
            painter.setPen(QPen(QColor("#111111"), 1))
            painter.drawText(QRectF(grid_x, ry, hour_col_w, row_h * 0.55), Qt.AlignCenter | Qt.AlignBottom, f"{p_idx+1}. Ders")
            
            painter.setFont(make_font(10))
            painter.setPen(QPen(QColor("#666666"), 1))
            painter.drawText(QRectF(grid_x, ry + row_h * 0.55, hour_col_w, row_h * 0.45), Qt.AlignCenter | Qt.AlignTop, times[p_idx])
            
            for d_idx in range(len(days)):
                cx = grid_x + hour_col_w + d_idx * col_w
                painter.setBrush(QBrush(QColor("#FFFFFF")))
                painter.setPen(QPen(QColor("#E0E0E0"), 1))
                painter.drawRect(QRectF(cx, ry, col_w, row_h))
                
                lesson = placements.get((d_idx, p_idx))
                if lesson:
                    sname = lesson.get("subject_name", "")
                    tname = lesson.get("teacher_name", "")
                    scolor = get_subject_color(sname, lesson.get("color"))
                    
                    painter.setBrush(QBrush(QColor(scolor)))
                    painter.setPen(QPen(QColor(scolor).darker(120), 1))
                    painter.drawRoundedRect(QRectF(cx + 2, ry + 2, col_w - 4, row_h - 4), 4, 4)
                    
                    c = QColor(scolor)
                    lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
                    t_color = QColor("#FFFFFF") if lum < 160 else QColor("#111111")
                    painter.setPen(QPen(t_color, 1))
                    
                    painter.setFont(make_font(12, True))
                    painter.drawText(QRectF(cx + 4, ry + 4, col_w - 8, row_h * 0.5), Qt.AlignCenter, sname)
                    if tname:
                        painter.setFont(make_font(10))
                        painter.drawText(QRectF(cx + 4, ry + row_h * 0.5, col_w - 8, row_h * 0.45), Qt.AlignCenter, tname)

        painter.setFont(make_font(9))
        painter.setPen(QPen(QColor("#777777"), 1))
        painter.drawText(QRectF(30, VH - 35, 400, 20), Qt.AlignLeft, "BGZ Ders Planlama Yazılımı v2025")
        painter.drawText(QRectF(VW - 430, VH - 35, 400, 20), Qt.AlignRight, "Sayfa 1 / 1")

    def _render_teacher_summary_list(self, painter, VW, VH):
        teachers = self.filtered_teachers
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
