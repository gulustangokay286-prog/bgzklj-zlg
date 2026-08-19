import os

file_path = "/Users/fookay/ders program/auto_scheduler.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_kisit = """        kisitlamalar_store = self.data_store.get("kisitlamalar", {})"""
new_kisit = """        kisitlamalar_store = dict(self.data_store.get("kisitlamalar", {}))
        try:
            from version_store import load_global_kisitlamalar
            global_k = load_global_kisitlamalar()
            inst_slug = self.institution_slug or "varsayilan_kurum"
            for slug, k_data in global_k.items():
                if slug != inst_slug and isinstance(k_data, dict):
                    for entity_name, timeoff in k_data.items():
                        if entity_name not in kisitlamalar_store:
                            kisitlamalar_store[entity_name] = {}
                        # Merge cross-institution constraints (if locked in other, lock here)
                        if isinstance(timeoff, dict):
                            for k, v in timeoff.items():
                                if not v: # locked
                                    kisitlamalar_store[entity_name][k] = False
        except Exception as e:
            print("AutoScheduler global constraints merge error:", e)
"""

content = content.replace(old_kisit, new_kisit)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("auto_scheduler patched.")
