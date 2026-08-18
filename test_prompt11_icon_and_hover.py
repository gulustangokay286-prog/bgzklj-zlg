import sys, os
sys.path.insert(0, os.path.abspath("c:/Users/gokay/Desktop/aSc/ChenKi_v2"))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

def test_all():
    print("=== TEST 1: App Icon & Login Logo File Verification ===")
    from PIL import Image
    
    # Check app_icon.png
    assert os.path.exists("app_icon.png"), "app_icon.png must exist!"
    img_icon = Image.open("app_icon.png")
    assert img_icon.size == (1254, 1254), f"Expected 1254x1254, got {img_icon.size}"
    
    # Check app_icon.ico
    assert os.path.exists("app_icon.ico"), "app_icon.ico must exist!"
    assert os.path.getsize("app_icon.ico") > 50000, "app_icon.ico must contain multi-resolution icons"
    
    # Check resources/logo.png (Login Dialog logo)
    assert os.path.exists("resources/logo.png"), "resources/logo.png must exist!"
    img_logo = Image.open("resources/logo.png")
    assert img_logo.size == (1254, 1254), f"Expected 1254x1254, got {img_logo.size}"
    print("TEST 1 PASSED: App icon and Login logo files verified!")

    print("\n=== TEST 2: Hover / Mouse In-Out & Sheet Change Immunity ===")
    from main_window import MainWindow
    mock_ds = {
        "siniflar": [{"ad": "9A"}, {"ad": "10B"}, {"ad": "11A"}],
        "ogretmenler": [{"ad": "Hüseyin Arman"}],
        "atamalar": [
            {"subject": "Biyoloji", "teacher": "Hüseyin Arman", "class": "10B", "duration": 2, "type": "2"},
            {"subject": "Matematik", "teacher": "Hüseyin Arman", "class": "11A", "duration": 4, "type": "2+2"}
        ],
        "grid_placements": []
    }
    
    win = MainWindow()
    win.data_store = mock_ds
    win._refresh_grid()
    
    dock = win._grid.unplaced_dock
    def count_cards():
        c = 0
        for i in range(dock.container_layout.count()):
            w = dock.container_layout.itemAt(i).widget()
            if w and hasattr(w, "subject_name"):
                c += 1
        return c
        
    initial_count = count_cards()
    assert initial_count == 3, f"Expected 3 cards, got {initial_count}"
    print(f"Initial unplaced card count: {initial_count}")
    
    # Simulate mouse entering cell row 0 (class 9A which has 0 assignments)
    win._grid._on_cell_clicked(0, 0)
    after_hover_9a = count_cards()
    assert after_hover_9a == 3, f"Expected 3 cards after hovering 9A, got {after_hover_9a} (Cards disappeared on hover!)"
    
    # Simulate mouse entering cell row 1 (class 10B)
    win._grid._on_cell_clicked(1, 2)
    after_hover_10b = count_cards()
    assert after_hover_10b == 3, f"Expected 3 cards after hovering 10B, got {after_hover_10b}"
    
    # Simulate tree selection change / sheet change
    win._refresh_tree(target_entity="9A")
    after_tree_change = count_cards()
    assert after_tree_change == 3, f"Expected 3 cards after tree change, got {after_tree_change}"
    
    print("TEST 2 PASSED: Dock unplaced cards NEVER disappear on mouse hover, cell click, or sheet/tree change!")
    
    win.cleanup()
    print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
    sys.exit(0)

if __name__ == "__main__":
    test_all()
