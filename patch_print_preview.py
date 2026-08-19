import os
import re

file_path = "/Users/fookay/ders program/dialogs/print_preview.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix ComboBox enabling for Çarşaf Liste
old_mode_check = """        elif "Tüm Sınıflar" in mode or "Tüm Öğretmenler" in mode or "Ders Yükü" in mode or ("Çarşaf Liste" in mode and not self.filters.get("classes") and not self.filters.get("teachers")) or "Tablo Olarak" in mode:
            self.target_combo.addItem("Tümü (Çoklu Sayfa)")
            self.target_combo.setEnabled(False)
        elif is_teacher_mode:"""
new_mode_check = """        elif "Tüm Sınıflar" in mode or "Tüm Öğretmenler" in mode or "Ders Yükü" in mode or "Tablo Olarak" in mode:
            self.target_combo.addItem("Tümü (Çoklu Sayfa)")
            self.target_combo.setEnabled(False)
        elif "Çarşaf Liste" in mode:
            self.target_combo.setEnabled(True)
            self.target_combo.addItem("Tümü (Çoklu Sayfa)")
            if is_teacher_mode:
                for t in self.filtered_teachers:
                    if t.get("ad"): self.target_combo.addItem(t.get("ad", ""))
            else:
                for c in self.filtered_classes:
                    if c.get("ad"): self.target_combo.addItem(c.get("ad", ""))
        elif is_teacher_mode:"""
content = content.replace(old_mode_check, new_mode_check)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied for ComboBox enabling.")
