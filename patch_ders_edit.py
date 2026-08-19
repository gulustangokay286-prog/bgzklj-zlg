file_path = "/Users/fookay/ders program/dialogs/edit_forms.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_code = """        my_atamalar = [a for a in atamalar if format_tr_name(a.get("subject", "")) == format_tr_name(my_ad)]
        for a in my_atamalar:
            item_text = f"• {a.get('teacher', 'Atanmadı')}  →  {a.get('class', '')} ({a.get('duration', 0)} Saat, Tip: {a.get('type', '-')})"
            item = QListWidgetItem(item_text)
            self.list_assignments.addItem(item)
        if not my_atamalar:
            self.list_assignments.addItem(QListWidgetItem("Henüz hiçbir sınıfa / öğretmene atanmadı."))"""

new_code = """        my_atamalar = [a for a in atamalar if format_tr_name(a.get("ders") or a.get("subject", "")) == format_tr_name(my_ad)]
        for a in my_atamalar:
            t_str = a.get("ogretmen") or a.get("teacher") or "Atanmadı"
            c_str = a.get("sinif") or a.get("class") or ""
            dur_str = a.get("ders_sayisi") or a.get("duration", 0)
            tip_str = a.get("dagilim") or a.get("type", "-")
            item_text = f"• {t_str}  →  {c_str} ({dur_str} Saat, Tip: {tip_str})"
            item = QListWidgetItem(item_text)
            self.list_assignments.addItem(item)
        if not my_atamalar:
            self.list_assignments.addItem(QListWidgetItem("Henüz hiçbir sınıfa / öğretmene atanmadı."))"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched DersEditDialog")
else:
    print("old_code not found")
