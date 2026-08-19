import sys

with open("/Users/fookay/ders program/timetable_grid.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix currentCellChanged to be more reliable
old_connect = "self.table.currentCellChanged.connect(lambda r, c, pr, pc: self._on_cell_clicked(r, c) if r >= 0 and c >= 0 else None)"
new_connect = """self.table.currentCellChanged.connect(lambda r, c, pr, pc: self._on_cell_clicked(r, c) if r >= 0 and c >= 0 else None)
        self.table.cellPressed.connect(self._on_cell_clicked)"""
content = content.replace(old_connect, new_connect)

# Fix update_info_panel
old_panel = """    def update_info_panel(self, info):
        if info:
            subj = info.get("subject_name", "") or info.get("subject", "")
            teacher = info.get("teacher_name", "") or info.get("teacher", "")
            cls = info.get("class_name", "") or info.get("class", "")
            
            win = self.window()"""

new_panel = """    def update_info_panel(self, info):
        if not info:
            self.info_color_box.setStyleSheet("background: transparent; border: 1px dashed #94A3B8; border-radius: 4px;")
            self.info_subject_lbl.setText("Ders Seçilmedi")
            self.info_class_lbl.setText("-")
            self.info_teacher_lbl.setText("-")
            return
            
        if info:
            subj = info.get("subject_name", "") or info.get("subject", "")
            teacher = info.get("teacher_name", "") or info.get("teacher", "")
            cls = info.get("class_name", "") or info.get("class", "")
            
            win = self.window()"""
content = content.replace(old_panel, new_panel)

with open("/Users/fookay/ders program/timetable_grid.py", "w", encoding="utf-8") as f:
    f.write(content)

