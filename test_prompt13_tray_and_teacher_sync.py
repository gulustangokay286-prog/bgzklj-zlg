"""
Prompt 13 Verification Test Suite
Tests:
1. _refresh_unplaced_lessons correctly deduplicates combined class placed hours
2. Block-by-block (2+2) card generation is accurate
3. MasterDataDialog cascading deletion 
4. btn_birl_quick removed from LessonAssignmentDialog
"""
import sys, os
sys.path.insert(0, os.path.abspath("c:/Users/gokay/Desktop/aSc/ChenKi_v2"))

from PySide6.QtWidgets import QApplication, QPushButton
app = QApplication.instance() or QApplication(sys.argv)

def test_all():
    from main_window import MainWindow
    
    # ══════════════════════════════════════════════════════════
    # TEST 1: Block-by-block unplaced card generation (2+2)
    # ══════════════════════════════════════════════════════════
    print("=== TEST 1: Block-by-Block Unplaced Card Generation (2+2) ===")
    
    win = MainWindow()
    mock_ds = {
        "siniflar": [{"ad": "10A"}],
        "ogretmenler": [{"ad": "Ahmet Yılmaz"}],
        "atamalar": [
            {
                "subject": "Matematik", "teacher": "Ahmet Yılmaz", "class": "10A",
                "duration": 4, "type": "2+2"
            }
        ],
        "grid_placements": []
    }
    win.data_store = mock_ds
    win._refresh_grid()
    
    dock = win._grid.unplaced_dock
    def get_tray_cards():
        cards = []
        for i in range(dock.container_layout.count()):
            w = dock.container_layout.itemAt(i).widget()
            if w and hasattr(w, "subject_name"):
                cards.append(w)
        return cards
        
    # With no placements, expect 2 cards (2h + 2h)
    init_cards = get_tray_cards()
    assert len(init_cards) == 2, f"Expected 2 cards for 2+2, got {len(init_cards)}"
    assert init_cards[0].duration == 2 and init_cards[1].duration == 2
    print(f"  ✅ Initial 2+2 -> 2 cards (each 2h)")
    
    # Place one 2h block via grid_placements
    mock_ds["grid_placements"] = [
        {"day": 0, "period": 0, "class_name": "10A", "subject_name": "Matematik", 
         "teacher_name": "Ahmet Yılmaz", "duration": 1},
        {"day": 0, "period": 1, "class_name": "10A", "subject_name": "Matematik", 
         "teacher_name": "Ahmet Yılmaz", "duration": 1},
    ]
    win._refresh_unplaced_lessons()
    cards_after_one = get_tray_cards()
    assert len(cards_after_one) == 1, f"Expected 1 card remaining, got {len(cards_after_one)}"
    assert cards_after_one[0].duration == 2
    print(f"  ✅ After placing 1st 2h block: 1 card remaining (2h)")
    
    # Place second 2h block
    mock_ds["grid_placements"].extend([
        {"day": 1, "period": 0, "class_name": "10A", "subject_name": "Matematik", 
         "teacher_name": "Ahmet Yılmaz", "duration": 1},
        {"day": 1, "period": 1, "class_name": "10A", "subject_name": "Matematik", 
         "teacher_name": "Ahmet Yılmaz", "duration": 1},
    ])
    win._refresh_unplaced_lessons()
    cards_after_two = get_tray_cards()
    assert len(cards_after_two) == 0, f"Expected 0 cards, got {len(cards_after_two)}"
    print(f"  ✅ After placing 2nd 2h block: 0 cards (100% placed)")
    
    # Remove second block -> 1 card should return
    mock_ds["grid_placements"] = mock_ds["grid_placements"][:2]
    win._refresh_unplaced_lessons()
    cards_restored = get_tray_cards()
    assert len(cards_restored) == 1, f"Expected 1 card restored, got {len(cards_restored)}"
    print(f"  ✅ After removing 2nd block: 1 card restored (2h)")
    
    # Remove all placements -> 2 cards return
    mock_ds["grid_placements"] = []
    win._refresh_unplaced_lessons()
    cards_all = get_tray_cards()
    assert len(cards_all) == 2, f"Expected 2 cards, got {len(cards_all)}"
    print("  ✅ After removing all: 2 cards restored")
    print("TEST 1 PASSED!")
    
    # ══════════════════════════════════════════════════════════
    # TEST 2: Combined class (10A + 10B) NO double-count
    # ══════════════════════════════════════════════════════════
    print("\n=== TEST 2: Combined Classes (10A + 10B) No Double-Count ===")
    mock_ds_comb = {
        "siniflar": [{"ad": "10A"}, {"ad": "10B"}],
        "ogretmenler": [{"ad": "Hüseyin Arman"}],
        "atamalar": [
            {
                "subject": "Biyoloji", "teacher": "Hüseyin Arman", "class": "10A + 10B",
                "duration": 4, "type": "2+2", "is_combined": True, "combined_classes": ["10A", "10B"]
            }
        ],
        "grid_placements": []
    }
    win.data_store = mock_ds_comb
    win._refresh_grid()
    
    comb_init = get_tray_cards()
    assert len(comb_init) == 2, f"Expected 2 combined cards, got {len(comb_init)}"
    print(f"  ✅ Initial: 2 combined cards (each 2h)")
    
    # Simulate placing one 2h combined block (both 10A and 10B rows, same day/period)
    mock_ds_comb["grid_placements"] = [
        {"day": 0, "period": 0, "class_name": "10A + 10B", "subject_name": "Biyoloji",
         "teacher_name": "Hüseyin Arman", "duration": 1, "is_combined": True, "combined_classes": ["10A", "10B"]},
        {"day": 0, "period": 1, "class_name": "10A + 10B", "subject_name": "Biyoloji",
         "teacher_name": "Hüseyin Arman", "duration": 1, "is_combined": True, "combined_classes": ["10A", "10B"]},
    ]
    win._refresh_unplaced_lessons()
    comb_after = get_tray_cards()
    assert len(comb_after) == 1, f"Expected 1 card remaining (not 0 from double-count), got {len(comb_after)}"
    print(f"  ✅ After placing 1st combined 2h: 1 card remaining — no double counting!")
    
    # Place second combined block
    mock_ds_comb["grid_placements"].extend([
        {"day": 1, "period": 0, "class_name": "10A + 10B", "subject_name": "Biyoloji",
         "teacher_name": "Hüseyin Arman", "duration": 1, "is_combined": True, "combined_classes": ["10A", "10B"]},
        {"day": 1, "period": 1, "class_name": "10A + 10B", "subject_name": "Biyoloji",
         "teacher_name": "Hüseyin Arman", "duration": 1, "is_combined": True, "combined_classes": ["10A", "10B"]},
    ])
    win._refresh_unplaced_lessons()
    comb_all_placed = get_tray_cards()
    assert len(comb_all_placed) == 0, f"Expected 0 cards, got {len(comb_all_placed)}"
    print(f"  ✅ After placing both combined 2h blocks: 0 cards (100% placed)")
    
    # Remove one block -> 1 card restores
    mock_ds_comb["grid_placements"] = mock_ds_comb["grid_placements"][:2]
    win._refresh_unplaced_lessons()
    comb_restored = get_tray_cards()
    assert len(comb_restored) == 1, f"Expected 1 card restored, got {len(comb_restored)}"
    print(f"  ✅ After removing 1 block: 1 card restored")
    print("TEST 2 PASSED!")
    
    # ══════════════════════════════════════════════════════════
    # TEST 3: Teacher cascading deletion via MasterDataDialog
    # ══════════════════════════════════════════════════════════
    print("\n=== TEST 3: Teacher Cascading Deletion ===")
    from dialogs.master_data_dialog import MasterDataDialog
    master_ds = {
        "siniflar": [{"ad": "10A", "sinif_ogretmeni": "Hüseyin Arman"}, {"ad": "10B"}],
        "ogretmenler": [{"ad": "Hüseyin Arman", "brans": "Biyoloji", "kisa": "HA"}],
        "dersler": [{"ad": "Biyoloji", "kisa": "BİYO"}],
        "derslikler": [],
        "atamalar": [
            {"subject": "Biyoloji", "teacher": "Hüseyin Arman", "class": "10A", "duration": 2, "type": "2"}
        ],
        "grid_placements": [
            {"day": 0, "period": 0, "class_name": "10A", "subject_name": "Biyoloji", 
             "teacher_name": "Hüseyin Arman", "duration": 1}
        ],
        "kisitlamalar": {"Hüseyin Arman": {"0,0": False}},
        "auto_schedule_results": [
            {"day": 0, "period": 0, "class_name": "10A", "subject_name": "Biyoloji", 
             "teacher_name": "Hüseyin Arman", "duration": 1}
        ]
    }
    
    dlg = MasterDataDialog(start_idx=3, parent=win, data_store=master_ds)
    dlg._test_mode = True
    
    # Verify class teacher column
    t_row_class_teacher = dlg.table_ogretmen.item(0, 4).text()
    assert t_row_class_teacher == "10A", f"Expected 10A, got '{t_row_class_teacher}'"
    print(f"  ✅ Class teacher column shows '10A'")
    
    # Delete teacher
    dlg.table_ogretmen.setCurrentCell(0, 0)
    dlg._act_delete()
    
    assert len(master_ds["ogretmenler"]) == 0, f"Teacher not deleted: {master_ds['ogretmenler']}"
    assert len(master_ds["atamalar"]) == 0, f"Atamalar not cleared: {master_ds['atamalar']}"
    assert len(master_ds["grid_placements"]) == 0, f"Grid placements not cleared: {master_ds['grid_placements']}"
    assert len(master_ds.get("auto_schedule_results", [])) == 0, f"Auto schedule results not cleared"
    assert master_ds["siniflar"][0]["sinif_ogretmeni"] == "", f"Class teacher ref not cleared: {master_ds['siniflar'][0]}"
    assert "Hüseyin Arman" not in master_ds.get("kisitlamalar", {}), "Constraint not removed"
    print("  ✅ Teacher, atamalar, grid_placements, auto_schedule_results all cleared")
    print("  ✅ Class teacher reference cleaned")
    print("  ✅ Constraints removed")
    print("TEST 3 PASSED!")
    
    # ══════════════════════════════════════════════════════════
    # TEST 4: btn_birl_quick removed from LessonAssignmentDialog
    # ══════════════════════════════════════════════════════════
    print("\n=== TEST 4: Redundant Button Removed ===")
    from dialogs.edit_forms import LessonAssignmentDialog
    t_dlg = LessonAssignmentDialog(parent=win, data_store={"ogretmenler": [], "dersler": [], "siniflar": [], "atamalar": []}, selected_teacher="")
    # Search for any btn with "Birleşik" text in header area
    found_birl = False
    for child in t_dlg.findChildren(QPushButton):
        if "Birleşik Ders Ekle" in (child.text() or ""):
            found_birl = True
            break
    assert not found_birl, "btn_birl_quick still exists!"
    print("  ✅ No redundant 'Yeni Birleşik Ders Ekle' button in header")
    print("TEST 4 PASSED!")
    
    win.cleanup()
    print("\n═══════════════════════════════════════")
    print("ALL 4 TESTS PASSED SUCCESSFULLY!")
    print("═══════════════════════════════════════")
    sys.exit(0)

if __name__ == "__main__":
    test_all()
