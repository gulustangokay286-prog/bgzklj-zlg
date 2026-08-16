"""test_teacher_restrictions_deep.py — Deep verification test for teacher restrictions and dynamic periods"""
import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from PySide6.QtWidgets import QApplication

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("=" * 70)
    print("=== TEST 1: Fully Blocked Teacher Must Have 0 Lessons Placed ===")
    from auto_scheduler import AutoSchedulerWorker
    
    # 8-Period Daily Schedule (40 slots per class), 2 classes, 3 teachers
    # Teacher 1 (Fatma Kaya) is 100% BLOCKED across all 5 days and 8 periods!
    # Teacher 2 & 3 are available.
    blocked_timeoff = [[0]*8 for _ in range(5)]
    open_timeoff = [[2]*8 for _ in range(5)]
    
    test_db = {
        "settings": {"periods": 8, "days_count": 5},
        "siniflar": [{"ad": "9A"}, {"ad": "9B"}],
        "dersler": [{"ad": "Matematik"}, {"ad": "Fizik"}, {"ad": "Tarih"}],
        "ogretmenler": [
            {"ad": "Fatma Kaya", "timeoff": blocked_timeoff}, # ⛔ 100% BLOCKED
            {"ad": "Ahmet Yılmaz", "timeoff": open_timeoff},
            {"ad": "Mehmet Demir", "timeoff": open_timeoff}
        ],
        "atamalar": [
            {"class": "9A", "subject": "Matematik", "teacher": "Fatma Kaya", "total_hours": 6, "block_type": "2+2+2"},
            {"class": "9A", "subject": "Fizik", "teacher": "Ahmet Yılmaz", "total_hours": 4, "block_type": "2+2"},
            {"class": "9A", "subject": "Tarih", "teacher": "Mehmet Demir", "total_hours": 2, "block_type": "2"},
            {"class": "9B", "subject": "Matematik", "teacher": "Fatma Kaya", "total_hours": 6, "block_type": "2+2+2"},
            {"class": "9B", "subject": "Fizik", "teacher": "Ahmet Yılmaz", "total_hours": 4, "block_type": "2+2"}
        ],
        "grid_placements": []
    }
    
    worker = AutoSchedulerWorker(test_db, fill_empty=True)
    worker.run()
    
    results = test_db.get("grid_placements", [])
    total_h = sum(p.get("duration", 1) for p in results)
    print(f"Total Placed Hours across all classes: {total_h} / 80")
    assert total_h == 80, f"Expected 80 total placed hours (40 for 9A + 40 for 9B), got {total_h}"
    
    fatma_lessons = [p for p in results if "Fatma" in str(p.get("teacher"))]
    print(f"Fatma Kaya (100% Kısıtlı Öğretmen) Placed Lessons: {len(fatma_lessons)}")
    assert len(fatma_lessons) == 0, f"ERROR: Blocked teacher Fatma Kaya received {len(fatma_lessons)} lessons! Must be 0!"
    print("✅ TEST 1 PASSED: Fully blocked teacher received EXACTLY 0 lessons, and classes are 100% filled (80/80)!")

    print("\n" + "=" * 70)
    print("=== TEST 2: 12-Period Day Schedule with Partially Blocked Teacher (Wed & Fri Blocked) ===")
    # 12 periods per day (60 slots per class)
    # Teacher (Canan Ozturk) has Wednesday (day 2) and Friday (day 4) completely blocked (0)!
    partially_blocked_timeoff = [
        [2]*12, # Pazartesi (Open)
        [2]*12, # Salı (Open)
        [0]*12, # Çarşamba (⛔ BLOCKED)
        [2]*12, # Perşembe (Open)
        [0]*12  # Cuma (⛔ BLOCKED)
    ]
    test_db_12 = {
        "settings": {"periods": 12, "days_count": 5},
        "siniflar": [{"ad": "10A"}],
        "dersler": [{"ad": "Biyoloji"}, {"ad": "Kimya"}],
        "ogretmenler": [
            {"ad": "Canan Ozturk", "timeoff": partially_blocked_timeoff},
            {"ad": "Hakan Vural", "timeoff": [[2]*12 for _ in range(5)]}
        ],
        "atamalar": [
            {"class": "10A", "subject": "Biyoloji", "teacher": "Canan Ozturk", "total_hours": 10, "block_type": "2+2+2+2+2"},
            {"class": "10A", "subject": "Kimya", "teacher": "Hakan Vural", "total_hours": 10, "block_type": "2+2+2+2+2"}
        ],
        "grid_placements": []
    }
    
    worker_12 = AutoSchedulerWorker(test_db_12, fill_empty=True)
    worker_12.run()
    
    results_12 = test_db_12.get("grid_placements", [])
    total_h_12 = sum(p.get("duration", 1) for p in results_12)
    print(f"Total Placed Hours for 10A in 12-period day: {total_h_12} / 60")
    assert total_h_12 == 60, f"Expected 60 placed hours for 10A in 12-period day, got {total_h_12}"
    
    canan_wed_fri = [p for p in results_12 if "Canan" in str(p.get("teacher")) and p.get("day") in (2, 4)]
    print(f"Canan Ozturk Placed Lessons on Wed & Fri (Blocked Days): {len(canan_wed_fri)}")
    assert len(canan_wed_fri) == 0, f"ERROR: Canan received lessons on blocked days: {canan_wed_fri}"
    print("✅ TEST 2 PASSED: Partially blocked teacher received 0 lessons on blocked days in 12-period schedule!")

    print("\n" + "=" * 70)
    print("=== TEST 3: Dynamic Period Dimensions in TimeoffDialog & ConstraintsDialog (16-Hour Schedule) ===")
    from dialogs.timeoff_dialog import TimeoffDialog
    from dialogs.constraints_dialog import ConstraintsDialog
    
    db_16 = {
        "settings": {"periods": 16, "days_count": 5},
        "ogretmenler": [{"ad": "Test Hoca"}],
        "siniflar": [{"ad": "11A"}]
    }
    
    dlg_toff = TimeoffDialog(db_16["ogretmenler"][0], "Öğretmen", db_16)
    assert dlg_toff.table.rowCount() == 16, f"TimeoffDialog row count must be 16, got {dlg_toff.table.rowCount()}"
    assert dlg_toff.table.columnCount() == 5, f"TimeoffDialog col count must be 5, got {dlg_toff.table.columnCount()}"
    assert dlg_toff.table.verticalHeaderItem(15).text() == "16. Ders", "16th row header must be '16. Ders'!"
    print(f"TimeoffDialog Table Dimensions: {dlg_toff.table.rowCount()} Rows (Y-axis) x {dlg_toff.table.columnCount()} Columns (X-axis)")

    dlg_const = ConstraintsDialog(db_16, "ogretmen")
    assert dlg_const.table.rowCount() == 16, f"ConstraintsDialog row count must be 16, got {dlg_const.table.rowCount()}"
    assert dlg_const.table.columnCount() == 5, f"ConstraintsDialog col count must be 5, got {dlg_const.table.columnCount()}"
    assert dlg_const.table.verticalHeaderItem(15).text() == "16. Ders", "16th row header must be '16. Ders'!"
    print(f"ConstraintsDialog Table Dimensions: {dlg_const.table.rowCount()} Rows (Y-axis) x {dlg_const.table.columnCount()} Columns (X-axis)")
    print("✅ TEST 3 PASSED: Both dialogs dynamically scale up to 16 periods along the Y-axis!")

    print("\n" + "=" * 70)
    print("🎉 ALL TEACHER RESTRICTION & DYNAMIC PERIOD TESTS PASSED 100%! 🎉")
    print("=" * 70)
    sys.exit(0)

if __name__ == "__main__":
    run_tests()
