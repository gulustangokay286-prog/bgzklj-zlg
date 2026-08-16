"""test_branch_teacher_substitution.py — Verify branch teacher substitution on restricted slots"""
import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from PySide6.QtWidgets import QApplication

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("=" * 75)
    print("=== TEST 1: Same Branch Teacher Substitution on Blocked Slots ===")
    from auto_scheduler import AutoSchedulerWorker
    
    # 2 Math Teachers in school:
    # 1. Fatma Kaya (Assigned to 10A Matematik, but blocked Wed + Fri)
    # 2. Ahmet Yılmaz (Math teacher, free Wed + Fri)
    test_db = {
        "okul_adi": "BGZ Test Koleji",
        "settings": {"periods": 8, "days_count": 5},
        "ogretmenler": [
            {
                "ad": "Fatma Kaya",
                "brans": "Matematik",
                # Block Wednesday (day 2) and Friday (day 4) completely
                "timeoff": [
                    [2, 2, 2, 2, 2, 2, 2, 2],
                    [2, 2, 2, 2, 2, 2, 2, 2],
                    [0, 0, 0, 0, 0, 0, 0, 0], # Wed blocked
                    [2, 2, 2, 2, 2, 2, 2, 2],
                    [0, 0, 0, 0, 0, 0, 0, 0]  # Fri blocked
                ]
            },
            {
                "ad": "Ahmet Yılmaz",
                "brans": "Matematik",
                "timeoff": [
                    [2, 2, 2, 2, 2, 2, 2, 2],
                    [2, 2, 2, 2, 2, 2, 2, 2],
                    [2, 2, 2, 2, 2, 2, 2, 2],
                    [2, 2, 2, 2, 2, 2, 2, 2],
                    [2, 2, 2, 2, 2, 2, 2, 2]
                ]
            }
        ],
        "siniflar": [{"ad": "10A"}],
        "dersler": [{"ad": "Matematik", "saat": 40}],
        "atamalar": [
            {"subject": "Matematik", "teacher": "Fatma Kaya", "class": "10A", "type": "2+2+2+2+2+2+2+2+2+2+2+2+2+2+2+2+2+2+2+2", "duration": 40}
        ],
        "kisitlamalar": {}
    }
    
    worker = AutoSchedulerWorker(test_db, target_class="10A")
    worker.run()
    
    placements = test_db.get("grid_placements", [])
    total_hours = sum(p.get("duration", 1) for p in placements)
    print(f"Total Placed Hours for 10A: {total_hours} / 40 (Placements count: {len(placements)})")
    assert total_hours == 40, f"Expected 40 hours, got {total_hours}"
    
    fatma_wed_fri = [p for p in placements if p.get("teacher") == "Fatma Kaya" and p.get("day") in [2, 4]]
    ahmet_wed_fri = [p for p in placements if p.get("teacher") == "Ahmet Yılmaz" and p.get("day") in [2, 4]]
    
    print(f"Fatma Kaya (Blocked on Wed/Fri) lessons on Wed/Fri: {len(fatma_wed_fri)}")
    print(f"Ahmet Yılmaz (Same Branch Math Substitute) lessons on Wed/Fri: {len(ahmet_wed_fri)}")
    
    assert len(fatma_wed_fri) == 0, "Fatma Kaya must have 0 lessons on Wed/Fri!"
    assert len(ahmet_wed_fri) > 0, "Ahmet Yılmaz must be substituted as the same-branch math teacher on Wed/Fri!"
    print("✅ TEST 1 PASSED: Same branch teacher substitute automatically assigned on blocked slots!")

    print("\n" + "=" * 75)
    print("=== TEST 2: Login Dialog URL is https://chenki.net ===")
    from login_dialog import LoginDialog
    dlg = LoginDialog()
    assert hasattr(dlg, "btn_license")
    import inspect
    src = inspect.getsource(dlg._open_license_web)
    assert "https://chenki.net" in src, f"Expected https://chenki.net in _open_license_web, got {src}"
    print("✅ TEST 2 PASSED: License URL is verified to be https://chenki.net!")

    print("\n" + "=" * 75)
    print("🎉 ALL BRANCH TEACHER SUBSTITUTION TESTS PASSED 100%! 🎉")
    print("=" * 75)
    sys.exit(0)

if __name__ == "__main__":
    run_tests()
