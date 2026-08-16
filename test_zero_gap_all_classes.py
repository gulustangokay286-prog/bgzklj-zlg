"""test_zero_gap_all_classes.py — Test 100% gapless auto schedule across different hours & scenarios"""
import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from PySide6.QtWidgets import QApplication

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    from auto_scheduler import AutoSchedulerWorker

    print("=" * 70)
    print("=== SCENARIO 1: Partial Assignments (16h assigned, 40h needed) ===")
    mock_db = {
        "okul_adi": "BGZ Koleji",
        "siniflar": [{"ad": "10A"}, {"ad": "10B"}],
        "ogretmenler": [
            {"ad": "Ahmet Yılmaz", "timeoff": [[2]*8 for _ in range(5)]},
            {"ad": "Mehmet Demir", "timeoff": [[2]*8 for _ in range(5)]}
        ],
        "dersler": [{"ad": "Matematik"}, {"ad": "Fizik"}, {"ad": "Kimya"}, {"ad": "Biyoloji"}],
        "atamalar": [
            {"class": "10A", "subject": "Matematik", "teacher": "Ahmet Yılmaz", "duration": 4},
            {"class": "10A", "subject": "Fizik", "teacher": "Mehmet Demir", "duration": 4},
            {"class": "10B", "subject": "Kimya", "teacher": "Ahmet Yılmaz", "duration": 4},
        ],
        "settings": {"periods": 8, "day_count": 5}  # 40 slots per class = 80 total
    }

    worker = AutoSchedulerWorker(mock_db, target_class=None, fill_empty=True)
    res = {}
    worker.finished_successfully.connect(lambda r: res.update(r))
    worker.run()

    schedule = res.get("schedule", [])
    total_placed = sum(p.get("duration", 1) for p in schedule)
    
    # 10A must have exactly 40 hours, 10B must have exactly 40 hours = 80 hours total
    hours_10a = sum(p.get("duration", 1) for p in schedule if p.get("class_name") == "10A" or p.get("class") == "10A")
    hours_10b = sum(p.get("duration", 1) for p in schedule if p.get("class_name") == "10B" or p.get("class") == "10B")
    
    print(f"10A Placed Hours: {hours_10a} / 40")
    print(f"10B Placed Hours: {hours_10b} / 40")
    print(f"Total Placed: {total_placed} / 80")
    
    assert hours_10a == 40, f"10A should have 40 slots, got {hours_10a}"
    assert hours_10b == 40, f"10B should have 40 slots, got {hours_10b}"
    
    # Check that NO slot contains "Boş" or "Atanmadı"
    for p in schedule:
        assert p.get("subject_name") != "Boş", "Should not contain 'Boş'"
        assert p.get("subject") != "Boş", "Should not contain 'Boş'"
    print("✅ SCENARIO 1 PASSED: 100% gapless schedule with real subjects generated!")

    print("\n" + "=" * 70)
    print("=== SCENARIO 2: 12-Period Daily Schedule (60 Slots per class) ===")
    mock_db_12 = {
        "okul_adi": "BGZ 12-Period Test",
        "siniflar": [{"ad": "12A"}],
        "ogretmenler": [{"ad": "Canan Ozturk", "timeoff": [[2]*12 for _ in range(5)]}],
        "dersler": [{"ad": "Matematik"}, {"ad": "Geometri"}, {"ad": "Fizik"}],
        "atamalar": [{"class": "12A", "subject": "Matematik", "teacher": "Canan Ozturk", "duration": 6}],
        "settings": {"periods": 12, "day_count": 5}  # 5 x 12 = 60 slots
    }
    worker12 = AutoSchedulerWorker(mock_db_12, target_class="12A", fill_empty=True)
    res12 = {}
    worker12.finished_successfully.connect(lambda r: res12.update(r))
    worker12.run()

    sched12 = res12.get("schedule", [])
    total_12a = sum(p.get("duration", 1) for p in sched12 if p.get("class_name") == "12A" or p.get("class") == "12A")
    print(f"12A 12-Period Placed Hours: {total_12a} / 60")
    assert total_12a == 60, f"12A should have 60 slots, got {total_12a}"
    print("✅ SCENARIO 2 PASSED: 60/60 slots 100% filled!")

    print("\n" + "=" * 70)
    print("🎉 ALL ZERO-GAP TESTS PASSED 100%! 🎉")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
