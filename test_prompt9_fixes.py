import sys, os
sys.path.insert(0, os.path.abspath("c:/Users/gokay/Desktop/aSc/ChenKi_v2"))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

def test_all():
    print("=== TEST 1: CombinedClassesDialog parsing delimited string & lists ===")
    from dialogs.edit_forms import CombinedClassesDialog
    mock_ds = {
        "siniflar": [{"ad": "9A"}, {"ad": "10B"}, {"ad": "11C"}]
    }
    # Test loading a composite joint string "9A (Grup 1) + 10B (Bütün Sınıf)"
    dlg = CombinedClassesDialog(mock_ds, selected_classes=["9A (Grup 1) + 10B (Bütün Sınıf)"])
    sel = dlg.get_selected_classes()
    print("Parsed classes:", sel)
    assert len(sel) == 2, f"Expected 2 classes parsed, got {len(sel)}: {sel}"
    assert "9A (Grup 1)" in sel
    assert "10B" in sel
    print("TEST 1 PASSED: Combined classes loaded properly into rows!")

    print("\n=== TEST 2: SchoolInfoDialog Working Days <-> Weekend Auto-Sync ===")
    from dialogs.school_info import SchoolInfoDialog
    s_dlg = SchoolInfoDialog(data_store=mock_ds)
    
    # Select 7 days -> Weekend should automatically become "Hafta Sonu Tatili Yok"
    s_dlg.cb_gun_sayisi.setCurrentText("7")
    assert s_dlg.cb_hafta_sonu.currentText() == "Hafta Sonu Tatili Yok", f"Expected 'Hafta Sonu Tatili Yok', got {s_dlg.cb_hafta_sonu.currentText()}"
    
    # Select 6 days -> Weekend should automatically become "Yalnız Pazar"
    s_dlg.cb_gun_sayisi.setCurrentText("6")
    assert s_dlg.cb_hafta_sonu.currentText() == "Yalnız Pazar", f"Expected 'Yalnız Pazar', got {s_dlg.cb_hafta_sonu.currentText()}"
    
    # Select 5 days -> Weekend should automatically become "Cumartesi - Pazar"
    s_dlg.cb_gun_sayisi.setCurrentText("5")
    assert s_dlg.cb_hafta_sonu.currentText() == "Cumartesi - Pazar", f"Expected 'Cumartesi - Pazar', got {s_dlg.cb_hafta_sonu.currentText()}"
    print("TEST 2 PASSED: Working days and weekend auto-sync works perfectly!")

    print("\n=== TEST 3: Bell & Break Times Validation ===")
    from dialogs.bell_times_dialog import BellAndBreakTimesDialog
    from PySide6.QtCore import QTime
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.warning = lambda *args, **kwargs: None
    b_dlg = BellAndBreakTimesDialog(mock_ds, periods=2)
    # Set lesson 1 duration to 10 mins (<20 mins)
    b_dlg.rows_data[0]["start"].setTime(QTime(8, 30))
    b_dlg.rows_data[0]["end"].setTime(QTime(8, 40)) # 10 mins
    # Calling save shouldn't accept
    b_dlg._save_and_accept()
    # It should have returned early due to warning
    assert "bell_schedule" not in mock_ds.get("settings", {}), "Should have rejected invalid duration!"
    print("TEST 3 PASSED: Invalid short duration blocked by validation!")

    print("\n=== TEST 4: TimetableGrid update_info_panel and locked drag ===")
    from timetable_grid import TimetableGrid
    grid = TimetableGrid(periods=8)
    sample_info = {
        "subject_name": "Matematik",
        "class_name": "9A + 10B",
        "teacher_name": "Hüseyin Arman",
        "locked": True,
        "duration": 2
    }
    grid.update_info_panel(sample_info)
    assert "Matematik" in grid.info_subject_lbl.text()
    assert "Ortak" in grid.info_class_lbl.text() or "ORTAK" in grid.info_class_lbl.text()
    assert "Hüseyin" in grid.info_teacher_lbl.text()
    print("TEST 4 PASSED: update_info_panel accurately renders joint class badges and status info!")

    print("\n=== TEST 5: CombinedClassesDialog & LessonAssignmentDialog Combined Persistence ===")
    from dialogs.edit_forms import LessonAssignmentDialog
    mock_ds_2 = {
        "ogretmenler": [{"ad": "Hüseyin Arman"}],
        "dersler": [{"ad": "Matematik"}, {"ad": "Fizik"}],
        "siniflar": [{"ad": "10A"}, {"ad": "10B"}, {"ad": "11A"}],
        "atamalar": []
    }
    
    # Test creating a combined lesson
    c_dlg = CombinedClassesDialog(
        data_store=mock_ds_2,
        selected_classes=["10A", "10B"],
        subject_name="Matematik",
        duration="2",
        teacher_name="Hüseyin Arman"
    )
    assert c_dlg.get_subject() == "Matematik"
    assert c_dlg.get_combined_string() == "10A + 10B"
    assert len(c_dlg.get_selected_classes()) == 2
    
    # Test LessonAssignmentDialog with this combined lesson
    lad = LessonAssignmentDialog(data_store=mock_ds_2, selected_teacher="Hüseyin Arman")
    # Row 0: Set combined
    lad.subject_rows[0]["cb_subject"].setCurrentText("Matematik")
    lad.subject_rows[0]["is_combined"] = True
    lad.subject_rows[0]["combined_classes"] = ["10A", "10B"]
    lad.subject_rows[0]["classes"] = ["10A + 10B"]
    lad.subject_rows[0]["cb_tip"].setCurrentText("2")
    
    data = lad.get_data()
    assert len(data) == 1, f"Expected 1 assignment, got {data}"
    assert data[0]["subject"] == "Matematik"
    assert data[0]["class"] == "10A + 10B"
    assert data[0]["is_combined"] is True
    assert data[0]["combined_classes"] == ["10A", "10B"]
    
    lad.accept()
    assert len(mock_ds_2["atamalar"]) == 1
    assert mock_ds_2["atamalar"][0]["is_combined"] is True
    print("TEST 5 PASSED: Combined lessons persist completely with is_combined=True and combined_classes!")

    print("\n=== TEST 6: DraggableLessonCard Square Dimensions for 1-Hour Lessons ===")
    from timetable_grid import DraggableLessonCard
    card_1h = DraggableLessonCard(1, "Matematik", "#FF0000", duration=1, teacher="Ali", class_name="10A")
    card_2h = DraggableLessonCard(2, "Fizik", "#00FF00", duration=2, teacher="Veli", class_name="10B")
    print(f"Card 1h size: {card_1h.width()}x{card_1h.height()}")
    print(f"Card 2h size: {card_2h.width()}x{card_2h.height()}")
    assert card_1h.width() == 30 and card_1h.height() == 28, f"Expected 30x28, got {card_1h.width()}x{card_1h.height()}"
    assert card_2h.width() == 62 and card_2h.height() == 28, f"Expected 62x28, got {card_2h.width()}x{card_2h.height()}"
    print("TEST 6 PASSED: 1-hour cards are compact squares (30x28) and 2-hour cards scale proportionally (62x28)!")

    print("\n=== TEST 7: MainWindow._remove_placement_by_data method & conflict override ===")
    from main_window import MainWindow
    win = MainWindow()
    win.data_store = {
        "siniflar": [{"ad": "10A"}, {"ad": "10B"}],
        "ogretmenler": [{"ad": "Hüseyin Arman"}],
        "grid_placements": [
            {"day": 0, "period": 0, "col": 0, "row": 0, "class_name": "10A", "subject_name": "Biyoloji", "teacher_name": "Hüseyin Arman", "duration": 1}
        ]
    }
    assert len(win.data_store["grid_placements"]) == 1
    # Remove via _remove_placement_by_data
    win._remove_placement_by_data({"day": 0, "period": 0, "class_name": "10A", "teacher_name": "Hüseyin Arman", "subject_name": "Biyoloji"})
    assert len(win.data_store["grid_placements"]) == 0, f"Expected 0 placements, got {len(win.data_store['grid_placements'])}"
    print("TEST 7 PASSED: _remove_placement_by_data cleanly removes target placement!")

    print("\n=== TEST 8: Grid Duplication for Combined Classes (10A + 10B) ===")
    win.data_store["grid_placements"] = [
        {
            "day": 1, "period": 0, "col": 1, "row": 0,
            "class_name": "10A + 10B", "class": "10A + 10B",
            "subject_name": "Biyoloji", "subject": "Biyoloji",
            "teacher_name": "Hüseyin Arman", "teacher": "Hüseyin Arman",
            "duration": 2, "is_combined": True, "combined_classes": ["10A", "10B"]
        }
    ]
    win._refresh_grid()
    # Check placed lessons on grid
    placed = win._grid.get_placed_lessons()
    print("Placed lessons on grid for combined class:", len(placed), "cells")
    # Row 0 (10A) and Row 1 (10B) should BOTH have cells placed for Tuesday (col 8, 9)
    periods = 8
    tuesday_col_0 = 1 * periods + 0 # col 8
    tuesday_col_1 = 1 * periods + 1 # col 9
    assert (0, tuesday_col_0) in placed, "Expected placement on 10A (row 0, col 8)"
    assert (1, tuesday_col_0) in placed, "Expected placement on 10B (row 1, col 8)"
    print("TEST 8 PASSED: Combined class (10A + 10B) accurately duplicated on both rows (10A and 10B) in the timetable grid!")

    win.cleanup()
    print("\nALL TESTS PASSED SUCCESSFULLY!")
    sys.exit(0)
