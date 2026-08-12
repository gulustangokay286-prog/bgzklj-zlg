from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QComboBox
from PySide6.QtPrintSupport import QPrintPreviewWidget, QPrinter
from PySide6.QtGui import QPainter, QPen, QFont, QColor, QPageLayout
from PySide6.QtCore import Qt, QRectF

class TimetablePrintPreview(QDialog):
    def __init__(self, timetable_data, class_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Yazdır - {class_name}")
        self.resize(900, 700)
        
        self.timetable_data = timetable_data  # dict of (row,col) -> lesson info
        self.class_name = class_name
        
        layout = QVBoxLayout(self)
        
        # Top bar with class selection
        top = QHBoxLayout()
        top.addWidget(QLabel("Sınıf:", self))
        self.class_combo = QComboBox(self)
        self.class_combo.addItem(class_name)
        self.class_combo.setFixedWidth(150)
        top.addWidget(self.class_combo)
        top.addStretch()
        layout.addLayout(top)
        
        self.printer = QPrinter(QPrinter.HighResolution)
        self.printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        
        self.preview = QPrintPreviewWidget(self.printer, self)
        self.preview.paintRequested.connect(self._render_page)
        
        layout.addWidget(self.preview)
        
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()
        btn_print = QPushButton("Yazdır")
        btn_print.setFixedSize(120, 35)
        btn_print.setStyleSheet("background: #0078D7; color: white; font-weight: bold; border-radius: 4px;")
        btn_print.clicked.connect(self.preview.print_)
        btn_lay.addWidget(btn_print)
        layout.addLayout(btn_lay)
        
    def _render_page(self, printer):
        painter = QPainter(printer)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        page_rect = printer.pageRect(QPrinter.DevicePixel)
        margin = 60
        content = page_rect.adjusted(margin, margin, -margin, -margin)
        w = content.width()
        h = content.height()
        x0 = content.x()
        y0 = content.y()
        
        days = ["Pa", "Sa", "Ça", "Pe", "Cu"]
        periods = 8
        times = [
            "9:00-9:40", "9:50-10:30", "10:40-11:20", "11:30-12:10",
            "12:20-13:00", "14:20-15:00", "15:10-15:50", "16:00-16:40"
        ]
        
        # Sizing
        title_h = 40
        grid_y = y0 + title_h
        grid_h = h - title_h - 40
        day_col_w = 50   
        header_h = 40    
        col_w = (w - day_col_w) / periods
        row_h = (grid_h - header_h) / len(days)
        
        # ── Title ──
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawText(QRectF(x0, y0, w, title_h), Qt.AlignCenter, self.class_name)
        
        painter.setFont(QFont("Arial", 6))
        painter.drawText(QRectF(x0, y0, w/2, title_h), Qt.AlignLeft | Qt.AlignBottom, "ÇORUM - MERKEZ / Özel Çorum Birey Özel Öğretim Kursu")
        
        grid_x = x0
        
        # ── Header Row (period numbers + times) ──
        painter.setPen(QPen(Qt.black, 1))
        
        # Top-left empty cell
        painter.setBrush(Qt.white)
        painter.drawRect(QRectF(grid_x, grid_y, day_col_w, header_h))
        
        header_font = QFont("Arial", 10, QFont.Bold)
        time_font = QFont("Arial", 6)
        
        for i in range(periods):
            cx = grid_x + day_col_w + i * col_w
            painter.setBrush(Qt.white)
            painter.drawRect(QRectF(cx, grid_y, col_w, header_h))
            
            painter.setFont(header_font)
            painter.setPen(QPen(Qt.black, 1))
            painter.drawText(QRectF(cx, grid_y, col_w, header_h * 0.5), Qt.AlignCenter, str(i + 1))
            
            painter.setFont(time_font)
            painter.drawText(QRectF(cx, grid_y + header_h * 0.5, col_w, header_h * 0.5), Qt.AlignCenter, times[i])
        
        # ── Day Rows ──
        day_font = QFont("Arial", 12, QFont.Bold)
        lesson_font = QFont("Arial", 9)
        teacher_font = QFont("Arial", 7)
        
        for d_idx, day in enumerate(days):
            ry = grid_y + header_h + d_idx * row_h
            
            # Day label cell
            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(Qt.white)
            painter.drawRect(QRectF(grid_x, ry, day_col_w, row_h))
            painter.setFont(day_font)
            painter.drawText(QRectF(grid_x, ry, day_col_w, row_h), Qt.AlignCenter, day)
            
            # Period cells
            for p_idx in range(periods):
                cx = grid_x + day_col_w + p_idx * col_w
                painter.setBrush(Qt.white)
                painter.drawRect(QRectF(cx, ry, col_w, row_h))
                
                lesson = self.timetable_data.get((p_idx, d_idx))
                if not lesson:
                    lesson = self.timetable_data.get((d_idx, p_idx))
                
                if lesson:
                    painter.setPen(QPen(Qt.black, 1))
                    
                    # Subject name
                    painter.setFont(lesson_font)
                    painter.drawText(QRectF(cx, ry, col_w, row_h * 0.6), Qt.AlignCenter | Qt.AlignBottom, lesson.get("subject_name", lesson.get("subject", "")))
                    
                    # Teacher name
                    painter.setFont(teacher_font)
                    painter.drawText(QRectF(cx, ry + row_h * 0.6, col_w, row_h * 0.4), Qt.AlignCenter | Qt.AlignTop, lesson.get("teacher_name", lesson.get("teacher", "")))
        
        # ── Footer ──
        footer_y = grid_y + grid_h + 10
        painter.setFont(QFont("Arial", 6))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawText(QRectF(x0, footer_y, w * 0.5, 20), Qt.AlignLeft, "Ders Planı Oluşturuldu: 02. 02. 2026")
        painter.drawText(QRectF(x0 + w * 0.5, footer_y, w * 0.5, 20), Qt.AlignRight, "aSc aSc Online")
        
        painter.end()
