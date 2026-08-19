import os

file_path = "/Users/fookay/ders program/dialogs/edit_forms.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_tip = """    def _on_tip_changed(self, row_data):
        self._update_row_badge(row_data)
        self._update_ozet()"""

new_tip = """    def _on_tip_changed(self, row_data):
        new_tip = row_data["cb_tip"].currentText().strip()
        configs = row_data.get("class_configs", {})
        for c in list(configs.keys()):
            configs[c]["type"] = new_tip
            if "+" in new_tip:
                configs[c]["duration"] = sum(int(x) for x in new_tip.split("+") if x.strip().isdigit())
            elif new_tip.isdigit():
                configs[c]["duration"] = int(new_tip)
        self._update_row_badge(row_data)
        self._update_ozet()"""

content = content.replace(old_tip, new_tip)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Patched _on_tip_changed")
