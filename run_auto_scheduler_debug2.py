import sys
import json
from auto_scheduler import AutoSchedulerWorker, normalize_class_name

generated_path = "/Users/fookay/ders program/otomatik_olusturulan_cizelge.roz"
with open(generated_path, "r", encoding="utf-8") as f:
    data_store = json.load(f)

for a in data_store.get("atamalar", []):
    if "hours" in a:
        a["duration"] = a.pop("hours")
data_store["planlama_iliskileri"] = []

all_class_names = []
for c in data_store.get("siniflar", []):
    cn = normalize_class_name(c.get("ad", ""))
    if cn and cn not in all_class_names:
        all_class_names.append(cn)

worker = AutoSchedulerWorker(data_store, target_class=None)

for cn in all_class_names:
    res = worker._astar_solve(
        empty_slots=[(d,p) for d in range(5) for p in range(8)],
        candidate_blocks=[{"subject": a["subject"], "teacher": a["teacher"], "duration": a["duration"]} for a in data_store["atamalar"] if normalize_class_name(a["class"]) == cn],
        global_teacher_occupied=set(),
        t_objs={},
        class_name=cn
    )
    if not res:
        print(f"FAILED on {cn}")
    else:
        print(f"{cn} success: {len(res)}")
