import os

file_path = "/Users/fookay/ders program/version_store.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_func = """def load_global_kisitlamalar():
    import json, os
    path = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "global_kisitlamalar.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_global_kisitlamalar(kisitlamalar):
    import json, os
    path = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "global_kisitlamalar.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(kisitlamalar, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving global_kisitlamalar:", e)"""


new_func = """def load_global_kisitlamalar():
    import json, os
    path = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "global_kisitlamalar.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and any(k for k in data.keys() if " " in k or len(k) > 30):
                    return {"varsayilan_kurum": data}
                return data
        except Exception:
            pass
    return {}

def save_global_kisitlamalar(institution_slug, kisitlamalar):
    import json, os
    path = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "global_kisitlamalar.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        global_data = load_global_kisitlamalar()
        global_data[institution_slug] = kisitlamalar
        with open(path, "w", encoding="utf-8") as f:
            json.dump(global_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving global_kisitlamalar:", e)"""

content = content.replace(old_func, new_func)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("version_store patched.")
