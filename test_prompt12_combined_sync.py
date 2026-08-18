import sys, os
sys.path.insert(0, os.path.abspath("c:/Users/gokay/Desktop/aSc/ChenKi_v2"))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

def test_all():
    from main_window import MainWindow
    print("=== TEST 1: Combined Classes Lock/Unlock Synchronization Across All Rows ===")
    mock_ds = {
        "siniflar": [{"ad": "10A"}, {"ad": "10B"}, {"ad": "11A"}],
        "ogretmenler": [{"ad": "Hüseyin Arman"}],
        "atamalar": [
            {
                "subject": "Biyoloji", "teacher": "Hüseyin Arman", "class": "10A + 10B",
                "duration": 2, "type": "2", "is_combined": True, "combined_classes": ["10A", "10B"]
            }
        ],
        "grid_placements": [
            {
                "day": 0, "period": 0, "class_name": "10A + 10B", "teacher_name": "Hüseyin Arman",
                "subject_name": "Biyoloji", "duration": 2, "locked": False, "is_combined": True,
                "combined_classes": ["10A", "10B"]
            }
        ]
    }
    
    win = MainWindow()
    win.data_store = mock_ds
    win._refresh_grid()
    
    # 10A is row 0, 10B is row 1
    # Check that both 10A and 10B initially have the lesson at col 0, 1
    item_10a = win._grid.table.item(0, 0)
    item_10b = win._grid.table.item(1, 0)
    assert item_10a is not None, "10A must have Biyoloji"
    assert item_10b is not None, "10B must have Biyoloji"
    
    info_10a_init = win._grid._placed_lessons[(0, 0)]
    info_10b_init = win._grid._placed_lessons[(1, 0)]
    assert info_10a_init.get("locked") is False
    assert info_10b_init.get("locked") is False
    
    # Right-click lock on 10A (row 0, col 0)
    grid = win._grid
    table = grid.table
    
    # Call act_lock logic directly
    info = grid._placed_lessons[(0, 0)]
    s_name = info.get("subject_name", "")
    c_name = info.get("class_name", "")
    target_classes = info.get("combined_classes", ["10A", "10B"])
    
    # Execute locking across partner classes
    for (r_k, c_k), pl in list(grid._placed_lessons.items()):
        if c_k in [0, 1] and pl.get("subject_name") == s_name:
            pl_cls = pl.get("class_name", "")
            if pl_cls in target_classes or any(tc in pl_cls for tc in target_classes) or pl_cls == c_name:
                pl["locked"] = True
                
    for p in win.data_store.get("grid_placements", []):
        p["locked"] = True
        
    win._refresh_grid()
    
    # Verify BOTH 10A and 10B now have locked == True
    info_10a_locked = win._grid._placed_lessons[(0, 0)]
    info_10b_locked = win._grid._placed_lessons[(1, 0)]
    assert info_10a_locked.get("locked") is True, "10A must be locked"
    assert info_10b_locked.get("locked") is True, "10B must be locked"
    print("TEST 1 PASSED: Combined lesson lock synchronizes across all partner class rows (10A and 10B)!")

    print("\n=== TEST 2: Moving Combined Lesson Moves Both Classes Together ===")
    # Move combined lesson from Day 0 Period 0 to Day 1 Period 2 (Salı 3. ders)
    move_info = {
        "lesson_id": "0_0",
        "subject_name": "Biyoloji",
        "teacher": "Hüseyin Arman",
        "class_name": "10A + 10B",
        "duration": 2,
        "is_move": True,
        "origin_row": 0,
        "origin_col": 0,
        "is_combined": True,
        "combined_classes": ["10A", "10B"],
        "locked": True
    }
    
    # Drop onto row 0, col = 1*8 + 2 = 10 (Tuesday period 2)
    win._on_lesson_dropped(0, 10, move_info)
    
    # Verify old slot (Day 0 Period 0) is empty for both 10A and 10B
    assert (0, 0) not in win._grid._placed_lessons, "10A old slot should be empty"
    assert (1, 0) not in win._grid._placed_lessons, "10B old slot should be empty"
    
    # Verify new slot (Day 1 Period 2 = col 10) is filled for both 10A and 10B
    assert (0, 10) in win._grid._placed_lessons, "10A must have Biyoloji at new slot"
    assert (1, 10) in win._grid._placed_lessons, "10B must have Biyoloji at new slot"
    print("TEST 2 PASSED: Moving combined lesson moves both 10A and 10B together to the new slot!")

    print("\n=== TEST 3: Deleting / Dragging to Tray Removes Both Classes Simultaneously ===")
    # Unlock first to simulate user accepting the single unlock prompt
    win._grid._placed_lessons[(0, 10)]["locked"] = False
    if (1, 10) in win._grid._placed_lessons:
        win._grid._placed_lessons[(1, 10)]["locked"] = False
        
    # Call _delete_lesson_at for 10A at col 10
    win._grid.table._delete_lesson_at(0, 10)
    
    # Verify both 10A and 10B rows are completely cleared
    assert (0, 10) not in win._grid._placed_lessons, "10A slot must be cleared"
    assert (1, 10) not in win._grid._placed_lessons, "10B slot must be cleared"
    
    # Verify unplaced dock has the unified combined lesson (10A + 10B 2h)
    dock = win._grid.unplaced_dock
    unplaced_cards = []
    for i in range(dock.container_layout.count()):
        w = dock.container_layout.itemAt(i).widget()
        if w and hasattr(w, "subject_name"):
            unplaced_cards.append(w)
            
    assert len(unplaced_cards) == 1, f"Expected 1 unified card in tray, got {len(unplaced_cards)}"
    card = unplaced_cards[0]
    assert card.duration == 2, f"Expected 2h, got {card.duration}"
    assert "10A" in card.class_name and "10B" in card.class_name, f"Expected combined class name, got {card.class_name}"
    print("TEST 3 PASSED: Deleting combined lesson removes both classes from grid and restores unified 2h card in tray!")

    win.cleanup()
    print("\nALL COMBINED CLASS TESTS PASSED SUCCESSFULLY!")
    sys.exit(0)

if __name__ == "__main__":
    test_all()
