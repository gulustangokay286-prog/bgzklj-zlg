"""
test_institution_undo_redo.py — Test undo/redo fidelity on real institutions
"""
import os
import sys
import copy
import json

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

import version_store
from main_window import MainWindow
from dialogs.master_data_dialog import MasterDataDialog, check_undo_removes_assigned_entity
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

def test_institution(slug, inst_name):
    print(f"\n==================================================")
    print(f" TESTING INSTITUTION: {inst_name} ({slug})")
    print(f"==================================================")

    # 1. Load active version data
    v_name = version_store.get_active_version(slug)
    check(f"Active version exists for {slug}", v_name is not None)
    if not v_name:
        return

    data = copy.deepcopy(version_store.load_version(slug, v_name))
    lesson_count = len(data.get("dersler", []))
    teacher_count = len(data.get("ogretmenler", []))
    atama_count = len(data.get("atamalar", []))
    placement_count = len(data.get("grid_placements", []))
    print(f"Loaded: {lesson_count} lessons, {teacher_count} teachers, {atama_count} atamalar, {placement_count} placements")

    # 2. Instantiate MainWindow in test mode
    win = MainWindow()
    win._test_mode = True
    win._test_confirm_undo = True
    # Populate window with institution data
    win.institution_slug = slug
    win.data_store.clear()
    win.data_store.update(copy.deepcopy(data))
    win._history_stack.clear()
    win._redo_stack.clear()
    win._refresh_tree()
    win._refresh_unplaced_lessons()

    # 3. Test scenario: Add new lesson, assign it, try undo
    print("\n--- Subtest: Lesson add + assignment + undo confirmation check ---")
    win._push_undo_state() # snapshot before adding
    new_sub = {"ad": "YapayZekaDersi", "kisa": "YZD", "renk": "#3B82F6", "max_gunluk": 2}
    win.data_store["dersler"].append(new_sub)
    win.save_db(sync_from_grid=False)

    # Assign it
    first_teacher = win.data_store["ogretmenler"][0]["ad"]
    first_class = win.data_store["siniflar"][0]["ad"]
    new_atama = {
        "id": 88888,
        "subject": "YapayZekaDersi",
        "teacher": first_teacher,
        "class": first_class,
        "duration": 2,
        "total_hours": 2
    }
    win._push_undo_state() # snapshot before assigning
    win.data_store["atamalar"].append(new_atama)
    win.save_db(sync_from_grid=False)

    check("Lesson and assignment added to window",
          any(d.get("ad") == "YapayZekaDersi" for d in win.data_store["dersler"]) and
          any(a.get("subject") == "YapayZekaDersi" for a in win.data_store["atamalar"]))

    # Step A: Undo the assignment
    win._act_undo()
    check("Undo reverts assignment cleanly",
          not any(a.get("subject") == "YapayZekaDersi" for a in win.data_store["atamalar"]))
    check("Lesson still exists after undoing assignment",
          any(d.get("ad") == "YapayZekaDersi" for d in win.data_store["dersler"]))

    # Redo the assignment
    win._act_redo()
    check("Redo restores assignment",
          any(a.get("subject") == "YapayZekaDersi" for a in win.data_store["atamalar"]))

    # Step B: Try to Undo adding the lesson while assignment exists, but user declines
    # Prepare previous state where lesson didn't exist
    win._test_confirm_undo = False
    # If we undo both:
    # First undo assignment
    win._act_undo()
    # Now top of stack is state BEFORE lesson was added
    # Re-add assignment to current state to test prompt on reverting to state without lesson
    win.data_store["atamalar"].append(new_atama)
    win._test_confirm_undo = False
    win._act_undo() # Should be declined because YapayZekaDersi has an assignment
    check("Declining prompt aborted undo (lesson kept)",
          any(d.get("ad") == "YapayZekaDersi" for d in win.data_store["dersler"]))
    check("Declining prompt aborted undo (assignment kept)",
          any(a.get("subject") == "YapayZekaDersi" for a in win.data_store["atamalar"]))

    # Step C: Accept prompt
    win._test_confirm_undo = True
    win._act_undo()
    check("Accepting prompt undid lesson addition",
          not any(d.get("ad") == "YapayZekaDersi" for d in win.data_store["dersler"]))
    check("Accepting prompt purged assignments for removed lesson",
          not any(a.get("subject") == "YapayZekaDersi" for a in win.data_store["atamalar"]))

    # 4. Test scenario: Deleting a teacher with existing assignments and restoring via Undo
    print("\n--- Subtest: Delete teacher and 100% faithful restoration ---")
    win.data_store.clear()
    win.data_store.update(copy.deepcopy(data))
    win._history_stack.clear()
    win._redo_stack.clear()

    target_t = win.data_store["ogretmenler"][0]["ad"]
    t_fmt = format_tr_name(target_t)
    orig_t_atamalar = [a for a in win.data_store.get("atamalar", []) if _matches_teacher(a.get("teacher", ""), target_t) or format_tr_name(a.get("teacher", "")) == t_fmt]
    orig_t_placements = [p for p in win.data_store.get("grid_placements", []) if _matches_teacher(p.get("teacher_name") or p.get("teacher", ""), target_t) or format_tr_name(p.get("teacher_name") or p.get("teacher", "")) == t_fmt]
    print(f"Target teacher '{target_t}' has {len(orig_t_atamalar)} atamalar and {len(orig_t_placements)} placements")

    # Open MasterDataDialog on teachers tab
    dlg = MasterDataDialog(start_idx=3, data_store=win.data_store, parent=win)
    dlg._test_mode = True
    dlg.table_ogretmen.setCurrentCell(0, 0)
    dlg._act_delete()

    check("Teacher deleted via dialog", not any(t.get("ad") == target_t for t in win.data_store["ogretmenler"]))
    check("Teacher atamalar purged on deletion", not any((_matches_teacher(a.get("teacher", ""), target_t) or format_tr_name(a.get("teacher", "")) == t_fmt) for a in win.data_store["atamalar"]))

    # Undo deletion in dialog
    dlg._act_undo()
    check("Teacher restored on undo", any(t.get("ad") == target_t for t in win.data_store["ogretmenler"]))
    cur_t_atamalar = [a for a in win.data_store.get("atamalar", []) if _matches_teacher(a.get("teacher", ""), target_t) or format_tr_name(a.get("teacher", "")) == t_fmt]
    check("Teacher atamalar 100% restored on undo", len(cur_t_atamalar) == len(orig_t_atamalar), f"{len(cur_t_atamalar)} vs {len(orig_t_atamalar)}")
    cur_t_placements = [p for p in win.data_store.get("grid_placements", []) if _matches_teacher(p.get("teacher_name") or p.get("teacher", ""), target_t) or format_tr_name(p.get("teacher_name") or p.get("teacher", "")) == t_fmt]
    check("Teacher placements 100% restored on undo", len(cur_t_placements) == len(orig_t_placements), f"{len(cur_t_placements)} vs {len(orig_t_placements)}")

    # Redo deletion
    dlg._act_redo()
    check("Teacher deleted again on redo", not any(t.get("ad") == target_t for t in win.data_store["ogretmenler"]))

    # Close dialog and undo from MainWindow
    dlg.accept()
    win._act_undo()
    check("Teacher 100% restored via MainWindow undo", any(t.get("ad") == target_t for t in win.data_store["ogretmenler"]))
    cur_t_atamalar2 = [a for a in win.data_store.get("atamalar", []) if _matches_teacher(a.get("teacher", ""), target_t) or format_tr_name(a.get("teacher", "")) == t_fmt]
    check("Teacher atamalar 100% restored via MainWindow undo", len(cur_t_atamalar2) == len(orig_t_atamalar))

    dlg.close()
    win.close()

def main():
    institutions = version_store.list_institutions()
    print(f"Found {len(institutions)} institutions: {[i['slug'] for i in institutions]}")
    for inst in institutions:
        test_institution(inst["slug"], inst["name"])

    print("\n==================================================")
    print(" SUMMARY")
    print(f" Total Passed: {len(PASSED)}")
    print(f" Total Failed: {len(FAILED)}")
    print("==================================================")
    if FAILED:
        for fname, msg in FAILED:
            print(f" FAILED: {fname} -> {msg}")
        sys.exit(1)
    else:
        print("ALL INSTITUTION UNDO/REDO TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    main()
