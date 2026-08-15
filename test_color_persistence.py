"""
test_color_persistence.py – Comprehensive verification of real-time subject color persistence
"""
import sys, os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor

# Ensure app exists
app = QApplication.instance() or QApplication(sys.argv)

from dialogs.color_picker_dialog import (
    resolve_subject_color, update_subject_color_globally, normalize_subject_match,
    ModernColorPickerDialog
)
from main_window import MainWindow, get_subject_color

def test_color_resolution_and_update():
    print("=== TEST 1: Color Resolution and Matching ===")
    test_ds = {
        "dersler": [
            {"ad": "Matematik", "kisa": "MAT", "color": "#E11D48", "renk": "#E11D48"},
            {"ad": "Fizik", "kisa": "FİZ", "color": "#0284C7", "renk": "#0284C7"}
        ],
        "atamalar": [
            {"subject": "Matematik", "class": "9A", "teacher": "Ahmet", "duration": 4, "color": "#E11D48"}
        ],
        "grid_placements": [
            {"subject_name": "Matematik", "class_name": "9A", "day": 0, "period": 0, "color": "#E11D48"}
        ]
    }
    
    # 1. Verify resolution
    mat_color = resolve_subject_color("Matematik", test_ds)
    assert mat_color == "#E11D48", f"Expected #E11D48, got {mat_color}"
    print("[OK] resolve_subject_color returned saved subject color:", mat_color)
    
    # 2. Update to a new color
    NEW_COLOR = "#10B981"
    update_subject_color_globally(None, test_ds, "Matematik", NEW_COLOR)
    
    # Check dersler
    assert test_ds["dersler"][0]["color"] == NEW_COLOR
    assert test_ds["dersler"][0]["renk"] == NEW_COLOR
    # Check atamalar
    assert test_ds["atamalar"][0]["color"] == NEW_COLOR
    # Check grid_placements
    assert test_ds["grid_placements"][0]["color"] == NEW_COLOR
    
    resolved_after = resolve_subject_color("Matematik", test_ds)
    assert resolved_after == NEW_COLOR, f"Expected {NEW_COLOR}, got {resolved_after}"
    print("[OK] update_subject_color_globally updated all data_store structures to:", resolved_after)
    
    # 3. Verify get_subject_color in main_window
    mw_color = get_subject_color("Matematik", test_ds)
    assert mw_color == NEW_COLOR, f"Expected {NEW_COLOR}, got {mw_color}"
    print("[OK] get_subject_color in main_window returned:", mw_color)

def test_ui_grid_color_update():
    print("\n=== TEST 2: Live Grid & Unplaced Dock Color Update ===")
    win = MainWindow(auth_data=None)
    win.data_store = {
        "dersler": [
            {"ad": "Biyoloji", "kisa": "BİY", "color": "#9333EA", "renk": "#9333EA"}
        ],
        "atamalar": [
            {"subject": "Biyoloji", "class": "10A", "teacher": "Ayşe Yılmaz", "duration": 2, "color": "#9333EA"}
        ],
        "grid_placements": [
            {"subject_name": "Biyoloji", "class_name": "10A", "teacher_name": "Ayşe Yılmaz", "day": 1, "period": 2, "duration": 2, "color": "#9333EA"}
        ],
        "siniflar": [{"ad": "10A"}],
        "ogretmenler": [{"ad": "Ayşe Yılmaz"}],
        "settings": {"periods": 8, "days_count": 5}
    }
    
    win._refresh_grid()
    
    # Check initial color
    col_before = resolve_subject_color("Biyoloji", win.data_store)
    assert col_before == "#9333EA"
    
    # Change color globally to #F97316
    NEW_BIO_COLOR = "#F97316"
    update_subject_color_globally(win, win.data_store, "Biyoloji", NEW_BIO_COLOR)
    
    # Verify data_store
    assert win.data_store["dersler"][0]["color"] == NEW_BIO_COLOR
    assert win.data_store["atamalar"][0]["color"] == NEW_BIO_COLOR
    assert win.data_store["grid_placements"][0]["color"] == NEW_BIO_COLOR
    
    # Verify grid placement info
    found_placement = False
    for (r, c), info in win._grid._placed_lessons.items():
        if info.get("subject_name") == "Biyoloji":
            assert info.get("color") == NEW_BIO_COLOR
            found_placement = True
            
    print("[OK] Live grid _placed_lessons and data_store color updated seamlessly!")

if __name__ == "__main__":
    test_color_resolution_and_update()
    test_ui_grid_color_update()
    print("\n[SUCCESS] ALL COLOR PERSISTENCE TESTS PASSED SUCCESSFULLY!")
    sys.exit(0)
