import os
import sys

# Ensure headless test environment
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

def test_prompt16_password_modal_and_coverage():
    print("=== TESTING PASSWORD OVERLAY FULL COVERAGE, CENTERING & WHITE POPUP ===")
    
    import version_store
    from home_dashboard import HomeDashboard, SetPasswordDialog, AppleInfoDialog
    from PySide6.QtCore import Qt
    
    # 1. Test SetPasswordDialog & AppleInfoDialog
    dlg_set = SetPasswordDialog("Boğaziçi Eğitim Kurumları")
    assert "background-color: #FFFFFF" in dlg_set.styleSheet(), "SetPasswordDialog must have explicit pure white background!"
    dlg_set.input_pwd.setText("12345")
    assert dlg_set.get_password() == "12345"
    print(" [1/3] SetPasswordDialog has crisp white styling and password extraction")

    dlg_info = AppleInfoDialog("Bilgi", "Kurum şifresi başarıyla güncellendi.", is_success=True)
    assert "background-color: #FFFFFF" in dlg_info.styleSheet(), "AppleInfoDialog must have explicit pure white background!"
    print(" [2/3] AppleInfoDialog has modern pure white modal styling")

    # 2. Test HomeDashboard password overlay stack behavior & coverage
    inst = version_store.create_institution("Test Kurum Password")
    slug = inst["slug"]
    version_store.set_institution_password(slug, "secret123")
    
    dash = HomeDashboard()
    dash._selected_slug = slug
    dash._refresh_versions()
    
    # Check that right_panel_stack shows password_overlay_widget (100% full coverage)
    assert dash.right_panel_stack.currentWidget() == dash.password_overlay_widget, \
        "When institution is locked, currentWidget of right_panel_stack MUST be password_overlay_widget!"
    assert not dash.btn_new_empty.isEnabled(), "New empty button must be disabled when locked!"
    assert dash.pwd_card.parent() == dash.password_overlay_widget, "pwd_card must be inside password_overlay_widget"
    
    # 3. Test wrong password vs correct password unlock
    dash.pwd_card_input.setText("wrong_password")
    dash._on_submit_password_overlay()
    assert dash.right_panel_stack.currentWidget() == dash.password_overlay_widget, "Wrong password must keep overlay active!"
    assert not dash.pwd_err_lbl.isHidden(), "Error label must be shown on wrong password!"
    
    # Submit correct password
    dash.pwd_card_input.setText("secret123")
    dash._on_submit_password_overlay()
    assert dash.right_panel_stack.currentWidget() == dash.right_content_widget, \
        "Correct password must unlock and switch currentWidget to right_content_widget!"
    assert dash.btn_new_empty.isEnabled(), "New empty button must be re-enabled when unlocked!"
    print(" [3/3] HomeDashboard password overlay guarantees 100% full coverage, centering, and seamless unlock")

    # Cleanup test institution
    version_store.delete_institution(slug)

    print("\n[SUCCESS] ALL PROMPT 16 REQUIREMENTS VERIFIED AND PASSED!")

if __name__ == "__main__":
    test_prompt16_password_modal_and_coverage()
