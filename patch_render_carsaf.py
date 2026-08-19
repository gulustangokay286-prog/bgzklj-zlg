import os

file_path = "/Users/fookay/ders program/dialogs/print_preview.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_items_logic = """        if is_teacher:
            items = sorted(self.filtered_teachers if self.filtered_teachers else self.data_store.get("ogretmenler", []), key=lambda t: t.get("ad", ""))
        else:
            items = sorted(self.filtered_classes if self.filtered_classes else self.data_store.get("siniflar", []), key=natural_sort_key)"""
new_items_logic = """        if is_teacher:
            items = sorted(self.filtered_teachers if self.filtered_teachers else self.data_store.get("ogretmenler", []), key=lambda t: t.get("ad", ""))
        else:
            items = sorted(self.filtered_classes if self.filtered_classes else self.data_store.get("siniflar", []), key=natural_sort_key)
            
        # Filter by combo box selection if not "Tümü"
        sel_items = self.filters.get("selected_items", [])
        if sel_items and "Tümü" not in sel_items[0]:
            items = [item for item in items if item.get("ad", "") in sel_items]"""
content = content.replace(old_items_logic, new_items_logic)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied for master list filtering.")
