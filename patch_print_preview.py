import os

file_path = "/Users/fookay/ders program/dialogs/print_preview.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_items = """        if is_teacher:
            items = sorted([t.get("ad", "Öğretmen") for t in (self.filtered_teachers if self.filtered_teachers else self.data_store.get("ogretmenler", []))])
        else:
            items = sorted([c.get("ad", "Sınıf") for c in (self.filtered_classes if self.filtered_classes else self.data_store.get("siniflar", []))], key=natural_sort_key)
            
        if not items:"""

new_items = """        sel_target = self.target_combo.currentText().strip()
        
        if sel_target and "Çoklu Sayfa" not in sel_target and sel_target != "Tümü":
            items = [sel_target]
        else:
            if is_teacher:
                items = sorted([t.get("ad", "Öğretmen") for t in (self.filtered_teachers if self.filtered_teachers else self.data_store.get("ogretmenler", []))])
            else:
                items = sorted([c.get("ad", "Sınıf") for c in (self.filtered_classes if self.filtered_classes else self.data_store.get("siniflar", []))], key=natural_sort_key)
            
        if not items:"""

content = content.replace(old_items, new_items)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Patched _render_asc_multi_grid")
