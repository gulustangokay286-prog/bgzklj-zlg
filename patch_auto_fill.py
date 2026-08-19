import os

file_path = "/Users/fookay/ders program/auto_scheduler.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix line 532
old_line = """                        a_t = format_tr_name(a.get("teacher") or "")"""
new_line = """                        a_t = format_tr_name(a.get("ogretmen") or a.get("teacher", ""))"""
content = content.replace(old_line, new_line)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Patched auto_scheduler.py line 532")
