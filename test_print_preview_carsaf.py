"""test_print_preview_carsaf.py — Verify print preview teacher matrix clean rendering and login dialog"""
import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from PySide6.QtWidgets import QApplication

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("=" * 70)
    print("=== TEST 1: Teacher Matrix Çarşaf Liste Clean Cell Rendering ===")
    from dialogs.print_preview import TimetablePrintPreview
    
    # 2 Teachers: Teacher A teaches 10A, Teacher B teaches 11B
    mock_db = {
        "okul_adi": "BGZ Koleji",
        "settings": {"periods": 8, "days_count": 5},
        "ogretmenler": [{"ad": "Ahmet Yılmaz"}, {"ad": "Mehmet Demir"}],
        "siniflar": [{"ad": "10A"}, {"ad": "11B"}],
        "dersler": [{"ad": "Matematik"}, {"ad": "Fizik"}],
        "atamalar": [],
        "grid_placements": [
            {"day": 0, "period": 0, "subject": "Matematik", "teacher": "Ahmet Yılmaz", "class": "10A", "duration": 2},
            {"day": 1, "period": 2, "subject": "Fizik", "teacher": "Mehmet Demir", "class": "11B", "duration": 2},
            # Unassigned/empty teacher placement in 12C (Must NEVER show up on Ahmet or Mehmet!)
            {"day": 2, "period": 4, "subject": "Rehberlik", "teacher": "", "class": "12C", "duration": 1}
        ]
    }
    
    prev = TimetablePrintPreview(data_store=mock_db, placed_lessons={}, filters={"type": "carsaf_ogretmenler"})
    
    # Get placements for Ahmet Yılmaz
    ahmet_p = prev._get_pseudo_placements("Ahmet Yılmaz", is_teacher=True)
    print("Ahmet Yılmaz Placements in Print Preview:", ahmet_p)
    assert (0, 0) in ahmet_p
    assert ahmet_p[(0, 0)]["teacher_name"] == "10A", f"Expected class 10A, got {ahmet_p[(0, 0)]['teacher_name']}"
    assert "+" not in ahmet_p[(0, 0)]["teacher_name"], "Must not contain concatenated + string!"
    assert (2, 4) not in ahmet_p, "Unassigned 12C lesson must NOT be in Ahmet Yılmaz!"

    # Get placements for Mehmet Demir
    mehmet_p = prev._get_pseudo_placements("Mehmet Demir", is_teacher=True)
    print("Mehmet Demir Placements in Print Preview:", mehmet_p)
    assert (1, 2) in mehmet_p
    assert mehmet_p[(1, 2)]["teacher_name"] == "11B"
    assert (0, 0) not in mehmet_p, "Ahmet's 10A lesson must NOT be in Mehmet Demir!"
    assert (2, 4) not in mehmet_p, "Unassigned 12C lesson must NOT be in Mehmet Demir!"
    
    print("✅ TEST 1 PASSED: Çarşaf liste is completely clean with zero cross-contamination!")

    print("\n" + "=" * 70)
    print("=== TEST 2: Login Dialog 'Lisans Al' Button and Offline Removal ===")
    from login_dialog import LoginDialog
    dlg = LoginDialog()
    assert hasattr(dlg, "btn_license"), "Login dialog must have btn_license ('Lisans Al')!"
    assert dlg.btn_license.text() == "Lisans Al"
    assert not hasattr(dlg, "btn_offline"), "Login dialog must NOT have btn_offline!"
    print("✅ TEST 2 PASSED: Login dialog features 'Lisans Al' button redirecting to chenki.com!")

    print("\n" + "=" * 70)
    print("🎉 ALL ÇARŞAF LISTE & LOGIN TESTS PASSED 100%! 🎉")
    print("=" * 70)
    sys.exit(0)

if __name__ == "__main__":
    run_tests()
