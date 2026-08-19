import os

file_path = "/Users/fookay/ders program/dialogs/master_data_dialog.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update MiniTimeoffGridWidget to expand and pass mouse events
old_mini_grid = """
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
"""

new_mini_grid = """
class MiniTimeoffGridWidget(QWidget):
    def __init__(self, timeoff_data=None, days=5, periods=8, parent=None):
        super().__init__(parent)
        self.timeoff_data = timeoff_data or []
        self.days = days
        self.periods = periods
        self.setToolTip("Çift Tıklayarak Zaman Tablosu / Kısıtlama Ayarlarını Açın")
        self.setMinimumSize(40, 24)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        margin_x = 4
        margin_y = 2
        
        cell_w = (w - margin_x*2) / max(1, self.days)
        cell_h = (h - margin_y*2) / max(1, self.periods)
"""

content = content.replace(old_mini_grid.strip(), new_mini_grid.strip())

# 2. Update double click handler to trigger timeoff dialogue
old_dbl = """    def _on_table_double_clicked(self, row, col):
        idx = self.stack.currentIndex()
        if idx == 3 and col == 3: # Zaman Tablosu & Çizelge column
            item = self.table_ogretmen.item(row, 0)
            if item:
                t_name = item.text().strip()
                d = TeacherIndividualTimetableDialog(t_name, self.data_store, self)
                d.exec()
                return
        self._act_update()
        return"""

new_dbl = """    def _on_table_double_clicked(self, row, col):
        idx = self.stack.currentIndex()
        if col == 3: # Zaman Tablosu column (for any entity)
            self._act_timeoff()
            return
        self._act_update()
        return"""

content = content.replace(old_dbl.strip(), new_dbl.strip())

# 3. Update single click handler
old_sgl = """    def _on_table_clicked(self, row, col):
        idx = self.stack.currentIndex()
        if idx == 3 and col == 3: # Zaman Tablosu & Çizelge column
            item = self.table_ogretmen.item(row, 0)
            if item:
                t_name = item.text().strip()
                d = TeacherIndividualTimetableDialog(t_name, self.data_store, self)
                d.exec()"""

new_sgl = """    def _on_table_clicked(self, row, col):
        pass # Let row selection happen naturally"""

content = content.replace(old_sgl.strip(), new_sgl.strip())

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied for mini grid sizing and click handling.")
