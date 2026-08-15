import sys
import json
import os
from PySide6.QtWidgets import QApplication
from auto_scheduler import AutoSchedulerWorker

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    
    db_path = "/Users/fookay/Downloads/program.roz"
    generated_path = "/Users/fookay/ders program/otomatik_olusturulan_cizelge.roz"
    
    with open(generated_path, "r", encoding="utf-8") as f:
        data_store = json.load(f)
        
    data_store["planlama_iliskileri"] = []
    
    worker = AutoSchedulerWorker(data_store, target_class=None)
    
    all_cls = []
    for c in data_store.get("siniflar", []):
        if c.get("ad"): all_cls.append(c["ad"])
    print("Classes in store:", all_cls)
    
    result_ds = None
    
    def on_success(res):
        nonlocal result_ds
        result_ds = res
        print("Success!")
        
    def on_fail(err):
        print(f"Failed: {err}")
        
    worker.finished_successfully.connect(on_success)
    worker.failed.connect(on_fail)
    
    worker.run()
    
    if result_ds:
        print("Placed count:", len(result_ds.get("grid_placements", [])))

if __name__ == "__main__":
    main()
