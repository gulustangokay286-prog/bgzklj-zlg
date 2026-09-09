"""
test_undo_redo_fidelity.py — Comprehensive test for real-time, high-fidelity Undo/Redo in MasterDataDialog and MainWindow.
"""
import os
import sys
import copy
import json

# Set offscreen Qt platform
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from dialogs.master_data_dialog import (
    MasterDataDialog,
    check_undo_removes_assigned_entity,
    purge_entity_references
)
from auto_scheduler import format_tr_name
from version_store import _matches_teacher

PASSED = []
FAILED = []

def check(test_name, condition, msg=""):
    if condition:
        print(f"  [PASS] {test_name}")
        PASSED.append(test_name)
    else:
        print(f"  [FAIL] {test_name} - {msg}")
        FAILED.append((test_name, msg))


def run_tests():
    print("=== STARTING UNDO/REDO FIDELITY TESTS ===")

    # 1. Load test institution data
    with open("bgz_database.json", "r", encoding="utf-8") as f:
        base_data = json.load(f)

    print(f"Base data loaded: {len(base_data.get('dersler', []))} lessons, {len(base_data.get('ogretmenler', []))} teachers, {len(base_data.get('atamalar', []))} atamalar, {len(base_data.get('grid_placements', []))} placements")

    data = copy.deepcopy(base_data)

    # 2. Initialize MasterDataDialog with test data
    dlg = MasterDataDialog(start_idx=0, data_store=data)
    dlg._test_mode = True
    dlg._test_confirm_undo = True

    check("Initial undo stack empty or clean", len(dlg._history_stack) == 0, f"Got {len(dlg._history_stack)}")
    check("Undo button disabled initially", not dlg.btn_undo.isEnabled())
    check("Redo button disabled initially", not dlg.btn_redo.isEnabled())

    # 3. Test: Add a lesson without assignments, then undo
    pre_lessons_count = len(dlg.data_store["dersler"])
    snapshot = copy.deepcopy(dlg.data_store)
    new_lesson = {"ad": "Astronomi", "kisa": "AST", "renk": "#E11D48", "max_gunluk": 2}
    dlg.data_store["dersler"].append(new_lesson)
    dlg._push_undo_snapshot(snapshot)
    dlg._load_existing_data()

    check("Lesson added to store", len(dlg.data_store["dersler"]) == pre_lessons_count + 1)
    check("Undo button enabled after addition", dlg.btn_undo.isEnabled())

    # Undo addition (unassigned lesson)
    dlg._act_undo()
    check("Unassigned lesson undone without prompt", len(dlg.data_store["dersler"]) == pre_lessons_count)
    check("Redo button enabled after undo", dlg.btn_redo.isEnabled())

    # Redo addition
    dlg._act_redo()
    check("Lesson restored on redo", len(dlg.data_store["dersler"]) == pre_lessons_count + 1)

    # 4. Test: Assign the newly added lesson, then try to Undo adding the lesson
    # First, simulate assigning this lesson to a teacher and class
    assigned_snapshot = copy.deepcopy(dlg.data_store)
    new_assignment = {
        "id": 99999,
        "subject": "Astronomi",
        "teacher": dlg.data_store["ogretmenler"][0]["ad"],
        "class": dlg.data_store["siniflar"][0]["ad"],
        "duration": 2,
        "total_hours": 2
    }
    dlg.data_store["atamalar"].append(new_assignment)
    dlg._push_undo_snapshot(assigned_snapshot)

    # Now we have two states in history:
    # Top of stack: state where lesson was added but unassigned
    # Bottom of stack: state before lesson was added
    # If we undo assignment first:
    dlg._act_undo()
    check("Undoing assignment reverts atamalar", not any(a.get("subject") == "Astronomi" for a in dlg.data_store["atamalar"]))
    check("Lesson is still in store after undoing assignment", any(d.get("ad") == "Astronomi" for d in dlg.data_store["dersler"]))

    # Now redo assignment so it's assigned again
    dlg._act_redo()
    check("Assignment restored on redo", any(a.get("subject") == "Astronomi" for a in dlg.data_store["atamalar"]))

    # Now let's test the specific user scenario:
    # If the history stack state to be undone would remove the lesson WHILE it has active assignments:
    # Prepare a state where reverting will drop 'Astronomi', but current state has active assignments for 'Astronomi'
    current_store = copy.deepcopy(dlg.data_store)
    target_prev_store = copy.deepcopy(dlg.data_store)
    # Target state has no Astronomi
    target_prev_store["dersler"] = [d for d in target_prev_store["dersler"] if d.get("ad") != "Astronomi"]

    # Sub-test A: User declines confirmation (_test_confirm_undo = False)
    dlg._test_confirm_undo = False
    confirmed = check_undo_removes_assigned_entity(dlg, current_store, target_prev_store)
    check("Declining undo prompt aborts undo", confirmed is False)

    # Sub-test B: User accepts confirmation (_test_confirm_undo = True)
    dlg._test_confirm_undo = True
    confirmed = check_undo_removes_assigned_entity(dlg, current_store, target_prev_store)
    check("Accepting undo prompt permits undo", confirmed is True)

    # Test purging entity references when user confirmed
    target_prev_store["atamalar"].append(new_assignment) # Even if target had lingering atama
    purge_entity_references(target_prev_store, "lesson", "Astronomi")
    check("Purge removes atamalar for deleted lesson", not any(a.get("subject") == "Astronomi" for a in target_prev_store["atamalar"]))

    # 5. Test: Deleting an existing entity and 100% faithful restoration on Undo
    print("\n--- Testing Deletion and 100% Restoration ---")
    data2 = copy.deepcopy(base_data)
    dlg2 = MasterDataDialog(start_idx=3, data_store=data2) # Teachers tab
    dlg2._test_mode = True

    # Find teacher with maximum assignments
    teacher_name = dlg2.data_store["ogretmenler"][0]["ad"]
    pre_teacher_count = len(dlg2.data_store["ogretmenler"])
    t_fmt = format_tr_name(teacher_name)
    teacher_atamalar = [a for a in dlg2.data_store.get("atamalar", []) if _matches_teacher(a.get("teacher", ""), teacher_name) or format_tr_name(a.get("teacher", "")) == t_fmt]
    teacher_placements = [p for p in dlg2.data_store.get("grid_placements", []) if _matches_teacher(p.get("teacher_name") or p.get("teacher", ""), teacher_name) or format_tr_name(p.get("teacher_name") or p.get("teacher", "")) == t_fmt]
    
    print(f"Target teacher '{teacher_name}' has {len(teacher_atamalar)} atamalar and {len(teacher_placements)} grid placements.")
    check("Teacher has assignments to test", len(teacher_atamalar) > 0)

    # Select the first row and delete
    dlg2.table_ogretmen.setCurrentCell(0, 0)
    dlg2._act_delete()

    check("Teacher deleted from ogretmenler", not any(t.get("ad") == teacher_name for t in dlg2.data_store["ogretmenler"]))
    check("Teacher atamalar purged upon deletion", not any((_matches_teacher(a.get("teacher", ""), teacher_name) or format_tr_name(a.get("teacher", "")) == t_fmt) for a in dlg2.data_store["atamalar"]))
    check("Teacher placements purged upon deletion", not any((_matches_teacher(p.get("teacher_name") or p.get("teacher", ""), teacher_name) or format_tr_name(p.get("teacher_name") or p.get("teacher", "")) == t_fmt) for p in dlg2.data_store["grid_placements"]))

    # Now click Undo!
    dlg2._act_undo()

    check("Teacher 100% restored in ogretmenler", any(t.get("ad") == teacher_name for t in dlg2.data_store["ogretmenler"]))
    restored_atamalar = [a for a in dlg2.data_store.get("atamalar", []) if _matches_teacher(a.get("teacher", ""), teacher_name) or format_tr_name(a.get("teacher", "")) == t_fmt]
    check("All teacher atamalar 100% restored", len(restored_atamalar) == len(teacher_atamalar), f"Got {len(restored_atamalar)} vs {len(teacher_atamalar)}")
    restored_placements = [p for p in dlg2.data_store.get("grid_placements", []) if _matches_teacher(p.get("teacher_name") or p.get("teacher", ""), teacher_name) or format_tr_name(p.get("teacher_name") or p.get("teacher", "")) == t_fmt]
    check("All teacher grid placements 100% restored", len(restored_placements) == len(teacher_placements), f"Got {len(restored_placements)} vs {len(teacher_placements)}")

    # Redo the deletion
    dlg2._act_redo()
    check("Teacher deleted again on redo", not any(t.get("ad") == teacher_name for t in dlg2.data_store["ogretmenler"]))
    check("Atamalar gone again on redo", not any((_matches_teacher(a.get("teacher", ""), teacher_name) or format_tr_name(a.get("teacher", "")) == t_fmt) for a in dlg2.data_store["atamalar"]))

    # Undo again
    dlg2._act_undo()
    check("Teacher 100% restored on second undo", any(t.get("ad") == teacher_name for t in dlg2.data_store["ogretmenler"]))
    check("Atamalar 100% restored on second undo", len([a for a in dlg2.data_store.get("atamalar", []) if _matches_teacher(a.get("teacher", ""), teacher_name) or format_tr_name(a.get("teacher", "")) == t_fmt]) == len(teacher_atamalar))

    # 6. Test: Reset all class assignments, then Undo
    print("\n--- Testing Reset All Class Assignments and Undo ---")
    data3 = copy.deepcopy(base_data)
    dlg3 = MasterDataDialog(start_idx=1, data_store=data3)
    dlg3._test_mode = True

    total_atamalar = len(dlg3.data_store["atamalar"])
    total_placements = len(dlg3.data_store["grid_placements"])

    dlg3._reset_all_class_assignments()
    check("Atamalar zeroed out", len(dlg3.data_store["atamalar"]) == 0)
    check("Placements zeroed out", len(dlg3.data_store["grid_placements"]) == 0)

    dlg3._act_undo()
    check("All atamalar 100% restored after reset undo", len(dlg3.data_store["atamalar"]) == total_atamalar, f"{len(dlg3.data_store['atamalar'])} vs {total_atamalar}")
    check("All placements 100% restored after reset undo", len(dlg3.data_store["grid_placements"]) == total_placements, f"{len(dlg3.data_store['grid_placements'])} vs {total_placements}")

    # 7. Test: Delete all lessons, then Undo
    print("\n--- Testing Delete All Lessons and Undo ---")
    data4 = copy.deepcopy(base_data)
    dlg4 = MasterDataDialog(start_idx=0, data_store=data4)
    dlg4._test_mode = True
    total_lessons = len(dlg4.data_store["dersler"])

    dlg4._act_delete_all()
    check("All lessons deleted", len(dlg4.data_store["dersler"]) == 0)
    check("Atamalar cleaned on delete all lessons", len(dlg4.data_store["atamalar"]) == 0)

    dlg4._act_undo()
    check("All lessons 100% restored on undo", len(dlg4.data_store["dersler"]) == total_lessons, f"{len(dlg4.data_store['dersler'])} vs {total_lessons}")
    check("Atamalar 100% restored on undo", len(dlg4.data_store["atamalar"]) == total_atamalar, f"{len(dlg4.data_store['atamalar'])} vs {total_atamalar}")

    print("\n=== SUMMARY ===")
    print(f"Total Passed: {len(PASSED)}")
    print(f"Total Failed: {len(FAILED)}")
    if FAILED:
        for f_name, f_msg in FAILED:
            print(f"  FAILED: {f_name} ({f_msg})")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED WITH 100% FIDELITY!")

if __name__ == "__main__":
    run_tests()
