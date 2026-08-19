import os

file_path = "/Users/fookay/ders program/main_window.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_code = """                # Load global kisitlamalar and override local
                from version_store import load_global_kisitlamalar
                global_k = load_global_kisitlamalar()
                if global_k:
                    if "kisitlamalar" not in self.data_store:
                        self.data_store["kisitlamalar"] = {}
                    # Update local with global
                    for k, v in global_k.items():
                        self.data_store["kisitlamalar"][k] = v"""

new_code = """                # Load global kisitlamalar and override local
                from version_store import load_global_kisitlamalar
                global_k = load_global_kisitlamalar()
                inst_slug = self.data_store.get("settings", {}).get("institution_slug", "varsayilan_kurum")
                
                if "kisitlamalar" not in self.data_store:
                    self.data_store["kisitlamalar"] = {}
                
                # Check if this institution has its own constraints in the global file
                if inst_slug in global_k:
                    for k, v in global_k[inst_slug].items():
                        self.data_store["kisitlamalar"][k] = v"""

content = content.replace(old_code, new_code)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("main_window patched.")
