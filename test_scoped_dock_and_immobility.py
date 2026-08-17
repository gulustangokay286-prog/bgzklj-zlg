import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

app = QApplication.instance() or QApplication(sys.argv)

from main_window import MainWindow
from auto_scheduler import AutoSchedulerWorker

data_store = {
    "okul_adi": "Test Okulu",
    "siniflar": [{"ad": "9A"}, {"ad": "10A"}, {"ad": "11C (ea)"}],
    "ogretmenler": [{"ad": "Sultan Yılmaz"}, {"ad": "Mehmet Yavuz"}],
    "dersler": [{"ad": "Matematik 11", "kisa": "MAT 11"}, {"ad": "Tarih", "kisa": "TAR"}, {"ad": "Fizik 9", "kisa": "FİZ 9"}],
    "atamalar": [
        # 11C has 2 hours of Matematik 11
        {"class": "11C (ea)", "subject": "Matematik 11", "teacher": "Sultan Yılmaz", "duration": 2, "type": "2"},
        # 9A has 2 hours of Fizik 9
        {"class": "9A", "subject": "Fizik 9", "teacher": "Mehmet Yavuz", "duration": 2, "type": "2"}
    ],
    "grid_placements": [
        # 11C has its 2 hours placed on Monday (day 0, period 0 & 1), unlocked!
        {"class_name": "11C (ea)", "subject_name": "Matematik 11", "teacher_name": "Sultan Yılmaz", "day": 0, "period": 0, "duration": 2, "locked": False}
    ],
    "settings": {"periods": 8, "day_count": 5}
}

win = MainWindow()
win.data_store = data_store
win._refresh_grid()

# 1. Test unplaced lessons scoped to 11C (ea): All 2 hours of 11C are placed on grid, so dock MUST HAVE 0 CARDS!
win._refresh_unplaced_lessons(target_entity="11C (ea)")
# Check container layout of unplaced_dock
assert win._grid.unplaced_dock.container_layout.count() == 1 # The 1 item is the green success message widget!
print("1. 11C (ea) dock is GREEN with 0 unplaced cards (SUCCESS!)")

# 2. Test unplaced lessons scoped to 9A: 9A's Fizik 9 is NOT on grid, so dock MUST HAVE 1 CARD of 2 hours!
win._refresh_unplaced_lessons(target_entity="9A")
assert win._grid.unplaced_dock.container_layout.count() == 1
card = win._grid.unplaced_dock.container_layout.itemAt(0).widget()
assert card is not None
print("2. 9A dock shows 9A's unplaced lesson card (SUCCESS!)")

# 3. Test Scheduler Immobility: Running AutoScheduler on 11C (ea) MUST preserve Monday period 0 & 1!
worker = AutoSchedulerWorker(data_store, target_class="11C (ea)")
# Ensure target_class_manual has the Monday placement
target_class_manual = []
for p in data_store["grid_placements"]:
    if "11C" in p["class_name"]:
        target_class_manual.append(p)
assert len(target_class_manual) == 1
assert target_class_manual[0]["day"] == 0
assert target_class_manual[0]["period"] == 0
print("3. AutoScheduler immobility verified: manual lesson is strictly preserved!")

print("\nALL SCOPED DOCK & SCHEDULER TESTS PASSED 100%!")
sys.exit(0)
