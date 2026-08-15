import sys
import json
import os
import shutil
from PySide6.QtWidgets import QApplication
from auto_scheduler import AutoSchedulerWorker

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    
    db_path = "/Users/fookay/Downloads/program.roz"
    generated_path = "/Users/fookay/ders program/otomatik_olusturulan_cizelge.roz"
    
    # Backup the user's current file
    shutil.copy(db_path, db_path + ".backup")
    print("Backed up user's active DB.")
    
    with open(generated_path, "r", encoding="utf-8") as f:
        data_store = json.load(f)
        
    print(f"Loaded {len(data_store.get('atamalar', []))} assignments.")
    
    # Run auto scheduler for all classes (target_class=None)
    worker = AutoSchedulerWorker(data_store, target_class=None)
    
    result_ds = None
    
    def on_success(res):
        nonlocal result_ds
        result_ds = res
        print("Auto scheduling finished successfully.")
        
    def on_fail(err):
        print(f"Auto scheduling failed: {err}")
        
    def on_progress(msg, val):
        pass # don't flood logs
        
    worker.finished_successfully.connect(on_success)
    worker.failed.connect(on_fail)
    worker.progress_updated.connect(on_progress)
    
    # Run synchronously
    worker.run()
    
    if result_ds:
        # Save to both locations
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(result_ds, f, ensure_ascii=False, indent=4)
        
        local_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bgz_database.json")
        with open(local_db, "w", encoding="utf-8") as f:
            json.dump(result_ds, f, ensure_ascii=False, indent=4)
            
        print("Data saved. Placed lessons count:", len(result_ds.get("grid_placements", [])))

if __name__ == "__main__":
    main()
