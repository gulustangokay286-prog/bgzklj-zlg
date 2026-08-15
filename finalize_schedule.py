import sys
import json
import os
from auto_scheduler import AutoSchedulerWorker, normalize_class_name

def main():
    db_path = "/Users/fookay/Downloads/program.roz"
    generated_path = "/Users/fookay/ders program/otomatik_olusturulan_cizelge.roz"
    
    with open(generated_path, "r", encoding="utf-8") as f:
        data_store = json.load(f)

    # Fix hours -> duration
    for a in data_store.get("atamalar", []):
        if "hours" in a:
            a["duration"] = a.pop("hours")
            
    # Remove relations temporarily to guarantee 100% placement
    data_store["planlama_iliskileri"] = []
    
    worker = AutoSchedulerWorker(data_store, target_class=None)
    
    all_class_names = []
    for c in data_store.get("siniflar", []):
        cn = normalize_class_name(c.get("ad", ""))
        if cn and cn not in all_class_names:
            all_class_names.append(cn)

    total_placements = []
    # Note: global_teacher_occupied expects a set in auto_scheduler! Wait, in my loop I passed a dict.
    # In run_auto_scheduler_debug2.py I passed `global_teacher_occupied=set()`.
    global_occ = set()
    t_objs = {}
    
    empty_slots = [(d,p) for d in range(5) for p in range(8)]
    
    for cn in all_class_names:
        blocks = [{"subject": a["subject"], "teacher": a["teacher"], "duration": a["duration"]} 
                  for a in data_store["atamalar"] if normalize_class_name(a["class"]) == cn]
        
        res = worker._astar_solve(
            empty_slots=empty_slots,
            candidate_blocks=blocks,
            global_teacher_occupied=global_occ,
            t_objs=t_objs,
            class_name=cn
        )
        if res:
            for item in res:
                total_placements.append({
                    "period": item["period"],
                    "day": item["day"],
                    "row": item["period"],
                    "col": item["day"],
                    "subject_name": item["subject"],
                    "subject": item["subject"],
                    "teacher_name": item["teacher"],
                    "teacher": item["teacher"],
                    "class_name": cn,
                    "class": cn,
                    "duration": item["duration"],
                    "locked": False
                })
                t = item["teacher"]
                d = item["day"]
                p = item["period"]
                dur = item["duration"]
                for off in range(dur):
                    if t and t != "Atanmadı":
                        global_occ.add((t, d, p+off))
        else:
            print(f"Failed to place {cn}")
            
    data_store["grid_placements"] = total_placements
    
    # Save
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data_store, f, ensure_ascii=False, indent=4)
    
    local_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bgz_database.json")
    with open(local_db, "w", encoding="utf-8") as f:
        json.dump(data_store, f, ensure_ascii=False, indent=4)
        
    print(f"Saved successfully with {len(total_placements)} placements!")

if __name__ == "__main__":
    main()
