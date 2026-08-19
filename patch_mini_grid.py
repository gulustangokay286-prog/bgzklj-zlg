import os
import re

file_path = "/Users/fookay/ders program/dialogs/master_data_dialog.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Define MiniTimeoffGridWidget
mini_grid_code = """
class MiniTimeoffGridWidget(QWidget):
    def __init__(self, timeoff_data=None, days=5, periods=8, parent=None):
        super().__init__(parent)
        self.timeoff_data = timeoff_data or []
        self.days = days
        self.periods = periods
        self.setToolTip("Yeşil: Müsait, Kırmızı: Kapalı")
        # Ensure minimum size to be visible
        self.setMinimumSize(40, 24)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate cell sizes based on widget width/height and grid size
        w = self.width()
        h = self.height()
        
        margin_x = max(2, (w - (self.days * 4)) // 2)
        margin_y = max(2, (h - (self.periods * 3)) // 2)
        
        cell_w = min(6, (w - margin_x*2) / self.days)
        cell_h = min(4, (h - margin_y*2) / self.periods)
        
        if cell_w < 2: cell_w = 2
        if cell_h < 2: cell_h = 2
        
        # Draw grid
        for d in range(self.days):
            for p in range(self.periods):
                val = 2 # default open
                if self.timeoff_data and d < len(self.timeoff_data) and p < len(self.timeoff_data[d]):
                    val = self.timeoff_data[d][p]
                
                if val == 2:
                    color = QColor("#86EFAC") # Green
                elif val == 1:
                    color = QColor("#FDE047") # Yellow
                else:
                    color = QColor("#FCA5A5") # Red
                    
                x = margin_x + d * (cell_w + 1)
                y = margin_y + p * (cell_h + 1)
                
                painter.fillRect(int(x), int(y), int(cell_w), int(cell_h), color)
"""

# Insert MiniTimeoffGridWidget after the imports
if "class MiniTimeoffGridWidget" not in content:
    content = content.replace("class ActionButton(QPushButton):", mini_grid_code + "\nclass ActionButton(QPushButton):")

# 2. Modify _add_row to accept timeoff
old_add_row = """    def _add_row(self, table, texts):
        r = table.rowCount()
        table.insertRow(r)
        for c, txt in enumerate(texts):
            item = QTableWidgetItem(str(txt))
            if c == 3 and table == self.table_ogretmen:
                item.setForeground(QBrush(QColor("#0078D7")))
                item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            table.setItem(r, c, item)"""

new_add_row = """    def _add_row(self, table, texts, timeoff=None, days_cnt=5, periods_cnt=8):
        r = table.rowCount()
        table.insertRow(r)
        for c, txt in enumerate(texts):
            item = QTableWidgetItem(str(txt))
            
            # If this is the "Zaman Tablosu" column (index 3) and it's a known table
            if c == 3 and table in [self.table_ogretmen, self.table_sinif, self.table_ders, self.table_derslik]:
                # Instead of text, add the MiniTimeoffGridWidget
                item.setText("") # Clear text
                table.setItem(r, c, item)
                
                mini_grid = MiniTimeoffGridWidget(timeoff_data=timeoff, days=days_cnt, periods=periods_cnt)
                
                # Center the widget in the cell
                container = QWidget()
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setAlignment(Qt.AlignCenter)
                container_layout.addWidget(mini_grid)
                
                table.setCellWidget(r, c, container)
            else:
                table.setItem(r, c, item)"""

content = content.replace(old_add_row, new_add_row)

# 3. Update _load_existing_data calls to _add_row to pass timeoff data
# Dersler
content = content.replace('self._add_row(self.table_ders, [data.get("ad",""), data.get("kisa",""), toplam, "Mevcut", "İdeal", str(data.get("max_gunluk", periods))])', 'self._add_row(self.table_ders, [data.get("ad",""), data.get("kisa",""), toplam, "Mevcut", "İdeal", str(data.get("max_gunluk", periods))], timeoff=data.get("timeoff"), days_cnt=len(days), periods_cnt=periods)')
# Siniflar
content = content.replace('self._add_row(self.table_sinif, [data.get("ad",""), data.get("kisa",""), toplam, zaman_str, data.get("ders_bitimi","15:30"), data.get("sinif_ogretmeni",""), data.get("kapasite","30")])', 'self._add_row(self.table_sinif, [data.get("ad",""), data.get("kisa",""), toplam, zaman_str, data.get("ders_bitimi","15:30"), data.get("sinif_ogretmeni",""), data.get("kapasite","30")], timeoff=data.get("timeoff"), days_cnt=len(days), periods_cnt=periods)')
# Derslikler
content = content.replace('self._add_row(self.table_derslik, [data.get("ad",""), data.get("kisa",""), "0", "Mevcut", data.get("kapasite",""), "Merkez"])', 'self._add_row(self.table_derslik, [data.get("ad",""), data.get("kisa",""), "0", "Mevcut", data.get("kapasite",""), "Merkez"], timeoff=data.get("timeoff"), days_cnt=len(days), periods_cnt=periods)')
# Ogretmenler
content = content.replace('self._add_row(self.table_ogretmen, [\n                t_name, data.get("kisa",""), toplam, zaman_str, so_class, brans, atanan_dersler_str\n            ])', 'self._add_row(self.table_ogretmen, [\n                t_name, data.get("kisa",""), toplam, zaman_str, so_class, brans, atanan_dersler_str\n            ], timeoff=data.get("timeoff"), days_cnt=len(days), periods_cnt=periods)')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied for mini grid.")
