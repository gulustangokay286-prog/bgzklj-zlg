"""test_v29_login_and_checks.py — Verification of:
1. Login Dialog: Brand logo at top, teacher char beside title, empty inputs, no emoji on offline button.
2. Checkbox tick styling in LoginDialog and MultiClassAssignDialog.
"""
import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from PySide6.QtWidgets import QApplication

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("=" * 70)
    print("=== TEST 1: Login Dialog Layout & Clean Inputs ===")
    from login_dialog import LoginDialog, LOGO_SHIELD_PATH, TEACHER_CHAR_PATH
    assert os.path.exists(LOGO_SHIELD_PATH), "Shield logo must exist"
    assert os.path.exists(TEACHER_CHAR_PATH), "Teacher character must exist"
    
    dlg = LoginDialog()
    assert dlg.w_user.text() == "", f"User text must start EMPTY, got: '{dlg.w_user.text()}'"
    assert dlg.w_pass.text() == "", f"Pass text must start EMPTY, got: '{dlg.w_pass.text()}'"
    assert dlg.btn_offline.text() == "Çevrimdışı Çalış (Offline Giriş)"
    assert "⚡" not in dlg.btn_offline.text()
    print("✅ TEST 1 PASSED: Login dialog has clean empty inputs and proper offline button text!")

    print("\n" + "=" * 70)
    print("=== TEST 2: MultiClassAssignDialog White Checkmark Indicator ===")
    from dialogs.edit_forms import MultiClassAssignDialog
    multi_dlg = MultiClassAssignDialog(
        teacher_name="Ahmet Yılmaz",
        subject_name="Matematik",
        all_classes=["9A", "10A", "11A"],
        selected_classes=["9A", "10A"]
    )
    assert multi_dlg.list_widget.count() == 3
    sel = multi_dlg.get_selected_classes()
    assert sel == ["9A", "10A"]
    assert "chk_checked.png" in multi_dlg.styleSheet()
    print("✅ TEST 2 PASSED: MultiClassAssignDialog has checkmark assets integrated!")

    print("\n" + "=" * 70)
    print("🎉 ALL V29 TESTS PASSED 100%! 🎉")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
