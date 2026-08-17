import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auto_scheduler import AutoSchedulerWorker

data_store = {
    "okul_adi": "Test Okulu",
    "siniflar": [{"ad": "9A"}, {"ad": "10A"}],
    "ogretmenler": [{"ad": "Sultan Yılmaz"}, {"ad": "Mehmet Yavuz"}],
    "dersler": [{"ad": "Matematik", "kisa": "MAT"}, {"ad": "Fizik", "kisa": "FİZ"}],
    "atamalar": [
        {"class": "9A", "subject": "Matematik", "teacher": "Sultan Yılmaz", "duration": 2, "type": "2"}
    ],
    "grid_placements": [
        # A manual placement on day 0, period 0 & 1, locked=False, is_manual not set
        {"class_name": "9A", "subject_name": "Fizik", "teacher_name": "Mehmet Yavuz", "day": 0, "period": 0, "duration": 1, "locked": False},
        {"class_name": "9A", "subject_name": "Fizik", "teacher_name": "Mehmet Yavuz", "day": 0, "period": 1, "duration": 1, "locked": False}
    ],
    "settings": {"periods": 8, "day_count": 5}
}

worker = AutoSchedulerWorker(data_store, target_class="9A")
# Let's mock _astar_solve and run
def _mock_astar(assignments_list, class_name, existing_placements=None):
    return []

results = None
def on_finished(res):
    global results
    results = res

worker.finished_successfully.connect(on_finished)
worker.run()
print("Auto Schedule Results:", results)
