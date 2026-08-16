"""test_ribbon_menu_button.py — Verify RibbonWidget tab bar layout and integrated M menu button"""
import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from PySide6.QtWidgets import QApplication

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("=" * 70)
    print("=== TEST 1: RibbonWidget File Menu Button Integration ===")
    from ribbon_widget import RibbonWidget
    ribbon = RibbonWidget()
    assert hasattr(ribbon, "file_btn"), "Ribbon must have file_btn directly on tab bar!"
    assert hasattr(ribbon, "file_menu"), "Ribbon must have file_menu!"
    assert ribbon.file_btn.parent() == ribbon._tab_bar, "file_btn must be inside _tab_bar!"
    
    p1 = ribbon.add_tab("Ana Menü")
    p2 = ribbon.add_tab("Giriş")
    assert len(ribbon._tab_buttons) == 2
    print("✅ TEST 1 PASSED: Menu button is directly on the tab bar in line with 'Ana Menü'!")

    print("\n" + "=" * 70)
    print("=== TEST 2: MainWindow Initialization without floating TitleBar ===")
    from main_window import MainWindow
    win = MainWindow()
    assert hasattr(win, "_ribbon"), "MainWindow must have _ribbon"
    assert win._ribbon.file_btn is not None
    assert len(win._ribbon.file_menu.actions()) >= 5, "File menu actions must be populated!"
    if hasattr(win, "cloud_worker") and win.cloud_worker:
        win.cloud_worker.stop()
    win.close()
    print("✅ TEST 2 PASSED: MainWindow cleanly initialized with integrated ribbon menu!")

    print("\n" + "=" * 70)
    print("🎉 ALL RIBBON MENU ALIGNMENT TESTS PASSED 100%! 🎉")
    print("=" * 70)
    sys.exit(0)

if __name__ == "__main__":
    run_tests()
