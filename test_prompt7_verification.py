import sys
import os
import unittest
from PySide6.QtWidgets import QApplication

def test_manual_empty_day_no_false_alarm():
    print("Testing manual placement on empty day (no false warning)...")
    app = QApplication.instance() or QApplication(sys.argv)
    from main_window import MainWindow
    
    ds = {
        "planlama_iliskileri": [
            {
                "kural": "Günde maksimum ders sayısı",
                "dersler": [],
                "deger": 2,
                "aktif": True
            }
        ]
    }
    
    win = MainWindow(auth_data=None)
    win.data_store = ds
    
    # 1. First 2-hour Matematik block on empty day (Pazartesi, c=0, p=0, dur=2)
    valid, msg = win._check_planning_relations(
        subject="Matematik 9",
        teacher="Ahmet Hoca",
        class_name="9A",
        day=0,
        period=0,
        duration=2,
        is_move=False
    )
    assert valid is True, f"Expected valid=True for fresh placement on empty day, but got violation: {msg}"
    print("✅ Placing 2h Matematik on empty day correctly produces NO warning!")
    
    # 2. Simulate placed lesson on Pazartesi
    win._grid._placed_lessons[(0, 0)] = {
        "subject_name": "Matematik 9",
        "subject": "Matematik 9",
        "teacher_name": "Ahmet Hoca",
        "class_name": "9A",
        "duration": 2
    }
    
    # 3. Placing ANOTHER 2h Matematik block on the same day (Pazartesi, c=0, p=2, dur=2) -> should violate
    valid, msg = win._check_planning_relations(
        subject="Matematik 9",
        teacher="Ahmet Hoca",
        class_name="9A",
        day=0,
        period=2,
        duration=2,
        is_move=False
    )
    assert valid is False, "Expected violation when placing 2nd block on same day exceeding limit!"
    print("✅ Placing second block on same day correctly warns with limit violation!")
    
    # 4. Placing on Salı (day=1) -> should be valid
    valid, msg = win._check_planning_relations(
        subject="Matematik 9",
        teacher="Ahmet Hoca",
        class_name="9A",
        day=1,
        period=0,
        duration=2,
        is_move=False
    )
    assert valid is True, f"Expected valid=True for placement on Tuesday, but got: {msg}"
    print("✅ Placing on Tuesday correctly permitted!")
    if hasattr(win, "cloud_worker") and win.cloud_worker:
        win.cloud_worker.stop()
        win.cloud_worker.wait(1000)

def test_auto_scheduler_block_distribution():
    print("Testing auto scheduler 2+2 block separation across days...")
    from auto_scheduler import AutoSchedulerWorker
    
    ds = {
        "okul_bilgileri": {"gun_sayisi": 5, "gunluk_ders_saati": 8},
        "siniflar": [{"ad": "9A"}],
        "ogretmenler": [{"ad": "Ahmet Hoca"}],
        "dersler": [{"ad": "Matematik"}],
        "atamalar": [
            {"teacher": "Ahmet Hoca", "subject": "Matematik", "class": "9A", "duration": 4, "type": "2+2"}
        ],
        "planlama_iliskileri": []
    }
    
    worker = AutoSchedulerWorker(ds, target_class="9A")
    result = []
    
    def on_finished(data):
        result.append(data)
        
    worker.finished_successfully.connect(on_finished)
    worker.run()
    
    assert len(result) > 0, "Scheduler did not return result!"
    sched = result[0]["schedule"]
    
    # Check that Matematik blocks are on 2 DIFFERENT days and each is 2 hours
    mat_placements = [p for p in sched if p["subject_name"] == "Matematik"]
    assert len(mat_placements) == 2, f"Expected exactly 2 blocks of 2 hours, got {len(mat_placements)}"
    
    day0 = mat_placements[0]["day"]
    day1 = mat_placements[1]["day"]
    assert day0 != day1, f"Expected 2+2 to be placed on 2 different days, but both were placed on day {day0}"
    assert mat_placements[0]["duration"] == 2 and mat_placements[1]["duration"] == 2, "Each block must be 2 hours"
    print(f"✅ AutoScheduler correctly placed 2+2 on day {day0} and day {day1} without adding a 3rd hour or merging!")

if __name__ == "__main__":
    test_manual_empty_day_no_false_alarm()
    test_auto_scheduler_block_distribution()
    print("\n🎉 ALL PROMPT 7 VERIFICATIONS PASSED SUCCESSFULLY!")
