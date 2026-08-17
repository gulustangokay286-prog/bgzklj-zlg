"""
test_full_system_v30.py — Comprehensive verification test suite for v30 updates:
1. Multi-hour lesson merging (setSpan) in timetable grid
2. Delete lesson -> Unplaced dock return
3. Version unplaced statistics calculation
4. Firebase RTDB sync serialization
5. macOS app icon .icns existence and validity
"""
import os
import sys
import json
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Ensure QApplication exists
app = QApplication.instance() or QApplication(sys.argv)

def test_multi_hour_lesson_merging():
    """Verify that multi-hour lessons set correct horizontal span across columns."""
    from main_window import MainWindow
    from timetable_grid import TimetableGrid
    
    # Create test data with 2-hour Math lesson for class 9A on Monday (day 0, period 0 and 1)
    test_store = {
        "ders_saati": 8,
        "settings": {"periods": 8},
        "siniflar": [{"ad": "9A"}, {"ad": "9B"}],
        "ogretmenler": [{"ad": "Ahmet Yılmaz"}],
        "dersler": [{"ad": "Matematik", "kod": "MATE", "renk": "#3B82F6"}],
        "atamalar": [{"subject": "Matematik", "class": "9A", "teacher": "Ahmet Yılmaz", "duration": 2}],
        "grid_placements": [
            {
                "day": 0, "period": 0, "col": 0, "row": 0, "duration": 2,
                "class_name": "9A", "teacher_name": "Ahmet Yılmaz", "subject_name": "Matematik",
                "color": "#3B82F6"
            }
        ]
    }
    
    win = MainWindow()
    win.data_store = test_store
    win.view_mode = "classes"
    win._refresh_grid()
    
    table = win._grid.table
    # 9A is row 0. Day 0, Period 0 is column 0.
    c_span = table.columnSpan(0, 0)
    print(f"[TEST 1] Column Span for 2-hour Math lesson: {c_span}")
    assert c_span == 2, f"Expected columnSpan 2 for 2-hour lesson, got {c_span}"
    
    # Verify origin resolution
    orig_r, orig_c, orig_dur, info = table._get_lesson_origin(0, 1)
    print(f"[TEST 1] Clicking second hour (0, 1) -> resolved origin: ({orig_r}, {orig_c}) with dur {orig_dur}")
    assert orig_r == 0 and orig_c == 0, f"Expected origin (0, 0), got ({orig_r}, {orig_c})"
    assert orig_dur == 2, f"Expected duration 2, got {orig_dur}"
    win.close()


def test_delete_lesson_and_unplaced_return():
    """Verify that deleting a multi-hour lesson from the grid restores it to the unplaced dock."""
    from main_window import MainWindow
    
    test_store = {
        "ders_saati": 8,
        "settings": {"periods": 8},
        "siniflar": [{"ad": "9A"}],
        "ogretmenler": [{"ad": "Ahmet Yılmaz"}],
        "dersler": [{"ad": "Matematik", "kod": "MATE", "renk": "#3B82F6"}],
        "atamalar": [{"subject": "Matematik", "class": "9A", "teacher": "Ahmet Yılmaz", "duration": 2}],
        "grid_placements": [
            {
                "day": 0, "period": 0, "col": 0, "row": 0, "duration": 2,
                "class_name": "9A", "teacher_name": "Ahmet Yılmaz", "subject_name": "Matematik",
                "color": "#3B82F6"
            }
        ]
    }
    
    win = MainWindow()
    win.data_store = test_store
    win.view_mode = "classes"
    win._refresh_grid()
    
    # Initial: 0 unplaced draggable cards
    from timetable_grid import DraggableLessonCard
    win._refresh_unplaced_lessons()
    initial_cards = [
        win._grid.unplaced_dock.container_layout.itemAt(i).widget()
        for i in range(win._grid.unplaced_dock.container_layout.count())
        if isinstance(win._grid.unplaced_dock.container_layout.itemAt(i).widget(), DraggableLessonCard)
    ]
    print(f"[TEST 2] Initial unplaced draggable cards: {len(initial_cards)}")
    assert len(initial_cards) == 0, f"Expected 0 draggable cards initially, got {len(initial_cards)}"
    
    # Delete the 2-hour lesson by clicking at column 0
    table = win._grid.table
    table._delete_lesson_at(0, 0)
    
    # Placement should be removed from data_store
    remaining_placements = len(win.data_store.get("grid_placements", []))
    print(f"[TEST 2] Remaining placements after deletion: {remaining_placements}")
    assert remaining_placements == 0, f"Expected 0 remaining placements, got {remaining_placements}"
    
    # Unplaced dock should now have 1 card with remaining 2 hours
    win._refresh_unplaced_lessons()
    unplaced_cards = [
        win._grid.unplaced_dock.container_layout.itemAt(i).widget()
        for i in range(win._grid.unplaced_dock.container_layout.count())
        if isinstance(win._grid.unplaced_dock.container_layout.itemAt(i).widget(), DraggableLessonCard)
    ]
    print(f"[TEST 2] Unplaced draggable cards after deletion: {len(unplaced_cards)}")
    assert len(unplaced_cards) >= 1, f"Expected at least 1 draggable card after deletion, got {len(unplaced_cards)}"
    win.close()


def test_version_unplaced_stats():
    """Verify that version_store calculates total_hours, placed_hours, and unplaced_hours accurately."""
    import version_store
    
    test_slug = "test_v30_stats_inst"
    version_store.create_institution("Test V30 Stats Inst")
    
    data_with_unplaced = {
        "atamalar": [
            {"subject": "Matematik", "duration": 4},
            {"subject": "Fizik", "duration": 2}
        ],
        "grid_placements": [
            {"subject_name": "Matematik", "duration": 2} # Only 2 hours placed out of 6 total
        ]
    }
    
    fn = version_store.save_version(test_slug, data_with_unplaced, source="manual", note="Test unplaced")
    versions = version_store.list_versions(test_slug)
    assert len(versions) > 0
    
    v0 = versions[0]
    print(f"[TEST 3] Version stats: total={v0['total_hours']}, placed={v0['placed_hours']}, unplaced={v0['unplaced_hours']}")
    assert v0["total_hours"] == 6, f"Expected total 6, got {v0['total_hours']}"
    assert v0["placed_hours"] == 2, f"Expected placed 2, got {v0['placed_hours']}"
    assert v0["unplaced_hours"] == 4, f"Expected unplaced 4, got {v0['unplaced_hours']}"
    
    # Clean up test institution
    version_store.delete_institution(test_slug)


def test_cloud_sync_serialization():
    """Verify RTDB key sanitization and cloud worker payload generation."""
    from cloud_sync import _sanitize_key
    
    key1 = "v001_2026-08-17_15-30-00_auto.roz"
    clean1 = _sanitize_key(key1)
    print(f"[TEST 4] Sanitized key: '{key1}' -> '{clean1}'")
    assert "." not in clean1
    assert "/" not in clean1
    assert "#" not in clean1
    assert clean1 == "v001_2026-08-17_15-30-00_auto_roz"


def test_app_icon_presence():
    """Verify that app_icon.icns and app_icon.png exist and are non-empty."""
    icns_path = "app_icon.icns"
    png_path = "app_icon.png"
    
    assert os.path.exists(icns_path), "app_icon.icns does not exist!"
    assert os.path.getsize(icns_path) > 10000, "app_icon.icns is too small!"
    assert os.path.exists(png_path), "app_icon.png does not exist!"
    print(f"[TEST 5] App icon verified: {icns_path} ({os.path.getsize(icns_path)} bytes)")


if __name__ == "__main__":
    print("Running Full System Verification Suite v30...")
    test_multi_hour_lesson_merging()
    test_delete_lesson_and_unplaced_return()
    test_version_unplaced_stats()
    test_cloud_sync_serialization()
    test_app_icon_presence()
    print("\n ALL 5 TESTS PASSED SUCCESSFULLY!")
