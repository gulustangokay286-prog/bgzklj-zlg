import json
import os

db_path = "/Users/fookay/ders program/data/bgz_database.json"
if os.path.exists(db_path):
    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    data["grid_placements"] = []
    
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("Database grid_placements reset to empty list.")
else:
    print("Database not found.")
