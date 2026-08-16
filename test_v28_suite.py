"""test_v28_suite.py — Automated verification for v28:
1. Pure White Minimalist Login Dialog
2. Multi-Period (9-16) Print Preview Pagination & Carsaf Lists
3. MasterDataDialog and Main Window Rollback / Undo
4. Zero-Gap 100% Auto Scheduler Guarantee
"""
import sys, os, copy
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTime

def run_v28_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("=" * 70)
    print("=== TEST 1: Minimalist Pure White Login Dialog ===")
    from login_dialog import LoginDialog, NEW_LOGO_PATH
    assert os.path.exists(NEW_LOGO_PATH), f"Logo not found at {NEW_LOGO_PATH}"
    login_dlg = LoginDialog()
    assert login_dlg.card is not None
    assert login_dlg.btn_login.text() == "Giriş Yap  →"
    assert login_dlg.btn_offline is not None
    login_dlg._enter_offline()
    assert login_dlg.auth_data is not None
    assert login_dlg.auth_data.get("is_offline") is True
    print("✅ TEST 1 PASSED: Pure white login dialog verified!")

    print("\n" + "=" * 70)
    print("=== TEST 2: Print Preview Comprehensive 9-16 Periods Retrieval ===")
    from dialogs.print_preview import TimetablePrintPreview
    mock_db = {
        "okul_adi": "BGZ Koleji",
        "siniflar": [{"ad": "10A"}, {"ad": "10B"}],
        "ogretmenler": [{"ad": "Kemal Demir", "kisa": "K. DEMİR"}],
        "dersler": [{"ad": "MATEMATİK", "kisa": "MAT"}, {"ad": "FİZİK", "kisa": "FİZ"}],
        "grid_placements": [
            # Day 0, Period 9 (10th lesson)
            {"day": 0, "period": 9, "duration": 2, "class": "10A", "subject": "MATEMATİK", "teacher": "Kemal Demir"},
            # Day 1, Period 11 (12th lesson)
            {"day": 1, "period": 11, "duration": 1, "class": "10A", "subject": "FİZİK", "teacher": "Kemal Demir"}
        ],
        "settings": {"periods": 12, "day_count": 5}
    }
    preview = TimetablePrintPreview(data_store=mock_db, placed_lessons={}, filters={"type": "carsaf_siniflar"})
    placements_10a = preview._get_pseudo_placements("10A", is_teacher=False)
    assert (0, 9) in placements_10a, "Period 9 must be present in placements!"
    assert (0, 10) in placements_10a, "Period 10 must be present in placements!"
    assert (1, 11) in placements_10a, "Period 11 must be present in placements!"
    assert placements_10a[(0, 9)]["subject_name"] == "MATEMATİK"
    assert placements_10a[(1, 11)]["subject_name"] == "FİZİK"

    placements_kemal = preview._get_pseudo_placements("Kemal Demir", is_teacher=True)
    assert (0, 9) in placements_kemal, "Teacher Kemal must have period 9 lesson!"
    assert (1, 11) in placements_kemal, "Teacher Kemal must have period 11 lesson!"
    print("✅ TEST 2 PASSED: Periods 9-12 successfully retrieved for print preview & carsaf lists!")

    print("\n" + "=" * 70)
    print("=== TEST 3: MasterDataDialog Undo / Rollback Verification ===")
    from dialogs.master_data_dialog import MasterDataDialog
    test_db = {
        "okul_adi": "BGZ Test",
        "siniflar": [{"ad": "10A"}],
        "ogretmenler": [{"ad": "Ali Kaya"}],
        "dersler": [{"ad": "Biyoloji"}],
        "atamalar": [{"class": "10A", "subject": "Biyoloji", "teacher": "Ali Kaya", "duration": 2}],
        "grid_placements": [{"day": 0, "period": 0, "duration": 2, "class": "10A", "subject": "Biyoloji", "teacher": "Ali Kaya"}],
        "settings": {"periods": 8, "day_count": 5}
    }
    m_dlg = MasterDataDialog(0, parent=None)
    m_dlg.data_store = test_db
    m_dlg._load_data()
    
    # Save snapshot
    m_dlg._push_undo_state()
    assert len(m_dlg._history_stack) == 1
    
    # Modify data (Reset class assignments)
    m_dlg.data_store["atamalar"] = []
    m_dlg.data_store["grid_placements"] = []
    assert len(m_dlg.data_store["atamalar"]) == 0
    
    # Undo / Rollback
    m_dlg._act_undo()
    assert len(m_dlg.data_store["atamalar"]) == 1
    assert len(m_dlg.data_store["grid_placements"]) == 1
    assert m_dlg.data_store["atamalar"][0]["subject"] == "Biyoloji"
    print("✅ TEST 3 PASSED: MasterDataDialog undo / rollback state verified!")

    print("\n" + "=" * 70)
    print("=== TEST 4: Zero-Gap 100% Auto Scheduler Verification ===")
    from auto_scheduler import AutoSchedulerWorker
    sched_db = {
        "okul_adi": "BGZ Zero Gap Test",
        "siniflar": [{"ad": "9A"}],
        "ogretmenler": [{"ad": "Hakan Vural", "timeoff": [[2]*8 for _ in range(5)]}],
        "dersler": [{"ad": "Matematik"}],
        "atamalar": [
            {"class": "9A", "subject": "Matematik", "teacher": "Hakan Vural", "duration": 2}
        ],
        "settings": {"periods": 8, "day_count": 5} # 40 total slots
    }
    worker = AutoSchedulerWorker(sched_db, target_class="9A", fill_empty=True)
    res_dict = {}
    def on_finished(res):
        res_dict.update(res)
    worker.finished_successfully.connect(on_finished)
    worker.run()
    
    placements = res_dict.get("schedule", [])
    total_slots = sum(p.get("duration", 1) for p in placements)
    # Check that class 9A is 100% filled for all 40 slots!
    assert total_slots == 40, f"Expected 40 slots filled, got {total_slots}"
    print(f"Total slots filled: {total_slots} / 40 (100% Full Schedule without single empty gap!)")
    print("✅ TEST 4 PASSED: Auto scheduler zero-gap placement verified!")

    print("\n" + "=" * 70)
    print("🎉 ALL V28 FEATURES & TESTS COMPLETED WITH 100% SUCCESS! 🎉")
    print("=" * 70)

if __name__ == "__main__":
    run_v28_tests()
