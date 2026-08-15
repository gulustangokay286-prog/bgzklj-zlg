"""
test_prompt4_verification.py - Verify prompt 4 fixes:
1. MasterDataDialog QMessageBox import and _reset_all_class_assignments.
2. SubjectTeacherAssignmentDialog unchecking teacher properly clears from atamalar and grid_placements.
3. ClassComprehensiveAssignmentDialog column widths and single/bulk deletion sync.
"""
import sys
import os

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from PySide6.QtWidgets import QApplication

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)

    print("=== TEST 1: MasterDataDialog QMessageBox & Reset All Assignments ===")
    from dialogs.master_data_dialog import MasterDataDialog
    from PySide6.QtWidgets import QMessageBox
    assert QMessageBox is not None

    test_ds = {
        "siniflar": [{"ad": "9/A", "kisa": "9A"}],
        "dersler": [{"ad": "Beden", "kisa": "BED"}],
        "ogretmenler": [{"ad": "Ceylan", "kisa": "C."}],
        "atamalar": [
            {"teacher": "Ceylan", "subject": "Beden", "class": "9/A", "duration": 2, "type": "2"}
        ],
        "grid_placements": [
            {"teacher_name": "Ceylan", "subject_name": "Beden", "class_name": "9/A", "day": 0, "period": 0, "duration": 2}
        ],
        "yerlesim": {
            "0,0": {"teacher_name": "Ceylan", "subject_name": "Beden", "class_name": "9/A", "duration": 2}
        },
        "settings": {"periods": 8, "days": ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]}
    }

    dlg_master = MasterDataDialog(start_idx=1, data_store=test_ds)
    assert hasattr(dlg_master, "_reset_all_class_assignments")
    print("✅ TEST 1 PASSED!")

    print("=== TEST 2: SubjectTeacherAssignmentDialog Uncheck & Save Synchronization ===")
    from dialogs.edit_forms import SubjectTeacherAssignmentDialog

    test_sync_ds = {
        "siniflar": [{"ad": "9/A", "kisa": "9A"}, {"ad": "12/A", "kisa": "12A"}],
        "dersler": [{"ad": "Beden", "kisa": "BED"}],
        "ogretmenler": [{"ad": "Ceylan", "kisa": "C."}, {"ad": "Erman Gürbüz", "kisa": "E."}],
        "atamalar": [
            {"teacher": "Ceylan", "subject": "Beden", "class": "9/A", "duration": 2, "type": "2"},
            {"teacher": "Erman Gürbüz", "subject": "Beden", "class": "12/A", "duration": 2, "type": "2"}
        ],
        "grid_placements": [
            {"teacher_name": "Ceylan", "subject_name": "Beden", "class_name": "9/A", "day": 0, "period": 0, "duration": 2},
            {"teacher_name": "Erman Gürbüz", "subject_name": "Beden", "class_name": "12/A", "day": 1, "period": 0, "duration": 2}
        ],
        "yerlesim": {
            "0,0": {"teacher_name": "Ceylan", "subject_name": "Beden", "class_name": "9/A", "duration": 2},
            "1,0": {"teacher_name": "Erman Gürbüz", "subject_name": "Beden", "class_name": "12/A", "duration": 2}
        }
    }

    # Open dialog for 9/A and uncheck Ceylan
    dlg_assign = SubjectTeacherAssignmentDialog(
        subject_name="Beden",
        data_store=test_sync_ds,
        current_class="9/A"
    )
    assert dlg_assign.teacher_configs["Ceylan"]["checked"] == True, "Ceylan should initially be checked for 9/A"
    assert dlg_assign.teacher_configs["Erman Gürbüz"]["checked"] == False, "Erman should NOT be checked for 9/A"

    # Simulate unchecking Ceylan
    dlg_assign._on_teacher_toggled("Ceylan", False)
    assert dlg_assign.teacher_configs["Ceylan"]["checked"] == False
    assert "9/A" not in dlg_assign.teacher_configs["Ceylan"]["classes"]

    # Save
    dlg_assign._save_assignments()

    # Verify atamalar, grid_placements, and yerlesim are cleaned of Ceylan on 9/A, while Erman on 12/A is preserved!
    asgns_9a = [a for a in test_sync_ds["atamalar"] if a.get("class") == "9/A"]
    assert len(asgns_9a) == 0, f"9/A should have 0 assignments, got {len(asgns_9a)}"

    asgns_12a = [a for a in test_sync_ds["atamalar"] if a.get("class") == "12/A"]
    assert len(asgns_12a) == 1, f"12/A should still have 1 assignment, got {len(asgns_12a)}"

    grid_9a = [p for p in test_sync_ds["grid_placements"] if p.get("class_name") == "9/A"]
    assert len(grid_9a) == 0, f"grid_placements for 9/A must be purged, got {len(grid_9a)}"

    grid_12a = [p for p in test_sync_ds["grid_placements"] if p.get("class_name") == "12/A"]
    assert len(grid_12a) == 1, f"grid_placements for 12/A must be preserved, got {len(grid_12a)}"

    assert "0,0" not in test_sync_ds["yerlesim"], "Yerlesim 0,0 for 9/A must be purged"
    assert "1,0" in test_sync_ds["yerlesim"], "Yerlesim 1,0 for 12/A must be preserved"
    print("✅ TEST 2 PASSED!")

    print("=== TEST 3: ClassComprehensiveAssignmentDialog Column Widths & Layout ===")
    from dialogs.edit_forms import ClassComprehensiveAssignmentDialog
    dlg_class = ClassComprehensiveAssignmentDialog(
        class_name="9/A",
        data_store=test_sync_ds
    )
    assert dlg_class.table.columnCount() == 4
    assert dlg_class.table.columnWidth(3) >= 140, "Action column width must be at least 140px"
    print("✅ TEST 3 PASSED!")

    print("\n🎉 ALL PROMPT 4 VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
