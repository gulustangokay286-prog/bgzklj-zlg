import os

file_path = "/Users/fookay/ders program/dialogs/edit_forms.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_list = """        my_atamalar = [a for a in atamalar if format_tr_name(a.get("teacher", "")) == format_tr_name(my_name)]
        my_subjects = list({a.get("subject", "") for a in my_atamalar if a.get("subject")})
        
        for a in my_atamalar:
            item_text = f"• {a.get('subject', '')}  →  {a.get('class', '')} ({a.get('duration', 0)} Saat)"
            item = QListWidgetItem(item_text)"""

new_list = """        my_atamalar = [a for a in atamalar if format_tr_name(a.get("ogretmen") or a.get("teacher", "")) == format_tr_name(my_name)]
        my_subjects = list({(a.get("ders") or a.get("subject", "")) for a in my_atamalar if (a.get("ders") or a.get("subject"))})
        
        for a in my_atamalar:
            s_name = a.get("ders") or a.get("subject", "")
            c_name = a.get("sinif") or a.get("class", "")
            dur = a.get("ders_sayisi") or a.get("duration", 0)
            item_text = f"• {s_name}  →  {c_name} ({dur} Saat)"
            item = QListWidgetItem(item_text)"""

content = content.replace(old_list, new_list)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Patched OgretmenEditDialog list rendering")
