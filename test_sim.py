import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auto_scheduler import AutoSchedulerWorker

data_store = {
    "okul_adi": "Test",
    "siniflar": [{"ad": "9A"}],
    "ogretmenler": [{"ad": "Ali Veli"}],
    "dersler": [{"ad": "Matematik"}],
    "atamalar": [
        {"class": "9A", "subject": "Matematik", "teacher": "Ali Veli", "duration": 4, "type": "2+2"}
    ],
    "grid_placements": [
        # Simulate user dropped 2-hour Math lesson on day 0, period 0 & 1
        {"class_name": "9A", "subject_name": "Matematik", "teacher_name": "Ali Veli", "col": 0, "row": 0, "duration": 1},
        {"class_name": "9A", "subject_name": "Matematik", "teacher_name": "Ali Veli", "col": 0, "row": 1, "duration": 1}
    ],
    "settings": {"periods": 8, "day_count": 5}
}

worker = AutoSchedulerWorker(data_store, target_class=None)

results = None
def on_finished(res):
    global results
    results = res

worker.finished_successfully.connect(on_finished)
worker.run()

# Check if Day 0 Period 0 is STILL Matematik by Ali Veli
p0 = [p for p in results["schedule"] if p["day"] == 0 and p["period"] == 0]
p1 = [p for p in results["schedule"] if p["day"] == 0 and p["period"] == 1]
print("Day 0 Period 0:", p0)
print("Day 0 Period 1:", p1)
print("Total placements:", len(results["schedule"]))
