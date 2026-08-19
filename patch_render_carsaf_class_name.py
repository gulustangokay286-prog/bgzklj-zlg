import os
import re

file_path = "/Users/fookay/ders program/dialogs/print_preview.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix class name truncation for Çarşaf Liste
old_class_name = """                if is_teacher and item.get("kisa"):
                    display_name = item.get("kisa")
                elif not is_teacher:
                    display_name = target_name.replace("(ea)", "(EA)").replace("(say)", "(SAY)").replace("(soz)", "(SÖZ)").replace("(dil)", "(DİL)")
                else:
                    display_name = target_name"""

new_class_name = """                if is_teacher and item.get("kisa"):
                    display_name = item.get("kisa")
                elif not is_teacher:
                    import re
                    display_name = re.sub(r'\\s*\\([^)]*\\)\\s*$', '', target_name).strip()
                else:
                    display_name = target_name"""

content = content.replace(old_class_name, new_class_name)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied for class name abbreviation.")
