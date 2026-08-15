import sys
import json
import os
from auto_scheduler import AutoSchedulerWorker, normalize_class_name

def main():
    generated_path = "/Users/fookay/ders program/bgz_database.json"
    
    with open(generated_path, "r", encoding="utf-8") as f:
        data_store = json.load(f)

    # Let's clear the old placements
    data_store["grid_placements"] = []
    
    # Remove relations temporarily to guarantee 100% placement
    data_store["planlama_iliskileri"] = []
    
    worker = AutoSchedulerWorker(data_store, target_class=None)
    
    all_class_names = []
    for c in data_store.get("siniflar", []):
        cn = normalize_class_name(c.get("ad", ""))
        if cn and cn not in all_class_names:
            all_class_names.append(cn)

    total_placements = []
    global_occ = set()
    t_objs = {}
    
    empty_slots = [(d,p) for d in range(5) for p in range(8)]
    
    for cn in all_class_names:
        blocks = [{"subject": a["subject"], "teacher": a["teacher"], "duration": a.get("duration", 2)} 
                  for a in data_store.get("atamalar", []) if normalize_class_name(a.get("class","")) == cn]
        
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
    
    # Save to all known places
    for p in [
        "/Users/fookay/Downloads/program.roz",
        "/Users/fookay/ders program/bgz_database.json",
        "/Users/fookay/Desktop/GUNCEL_DOLU_PROGRAM.roz"
    ]:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data_store, f, ensure_ascii=False, indent=4)
        
    print(f"Saved successfully with {len(total_placements)} placements!")

if __name__ == "__main__":
    main()
