file_path = "/Users/fookay/ders program/dialogs/master_data_dialog.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_c = """        teacher_atamalar = [a for a in self.data_store.get("atamalar", []) if is_teacher_match(a.get("teacher", ""), self.teacher_name, teacher_objs)]
        total_assigned_hours = sum(int(a.get("duration", 1)) for a in teacher_atamalar)"""

new_c = """        teacher_atamalar = [a for a in self.data_store.get("atamalar", []) if is_teacher_match(a.get("ogretmen") or a.get("teacher", ""), self.teacher_name, teacher_objs)]
        total_assigned_hours = sum(int(a.get("ders_sayisi") or a.get("duration", 1)) for a in teacher_atamalar if str(a.get("ders_sayisi") or a.get("duration", 1)).isdigit())"""

if old_c in content:
    content = content.replace(old_c, new_c)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched master_data_dialog.py")
else:
    print("old_c not found")
