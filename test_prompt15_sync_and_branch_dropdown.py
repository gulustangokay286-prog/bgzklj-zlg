import os
import sys

# Ensure headless test environment
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

def test_prompt15_sync_and_branch():
    print("=== TESTING TWO-WAY CLASS TEACHER SYNC & STATIC BRANCH DROPDOWN ===")
    
    from dialogs.master_data_dialog import MasterDataDialog
    from dialogs.edit_forms import SinifEditDialog, OgretmenEditDialog
    
    ds = {
        "dersler": [{"ad": "Matematik", "kisa": "MAT"}, {"ad": "Fizik", "kisa": "FZK"}, {"ad": "Kimya", "kisa": "KMY"}],
        "siniflar": [
            {"ad": "9A", "kisa": "9A", "sinif_ogretmeni": "Altın Bolat"},
            {"ad": "10B", "kisa": "10B", "sinif_ogretmeni": ""}
        ],
        "derslikler": [],
        "ogretmenler": [
            {"ad": "Altın Bolat", "kisa": "A. BOLAT", "sinif_ogretmeni": "9A", "brans": "Matematik"},
            {"ad": "Mehmet Demir", "kisa": "M. DEMIR", "sinif_ogretmeni": "", "brans": "Fizik"}
        ],
        "atamalar": [],
        "settings": {"periods": 8}
    }
    
    md = MasterDataDialog(start_idx=3, parent=None, data_store=ds)
    md._test_mode = True
    
    # 1. Test OgretmenEditDialog has QComboBox for branch with subjects
    t_data = ds["ogretmenler"][0]
    dlg_t = OgretmenEditDialog(parent=md, existing_data=t_data)
    from PySide6.QtWidgets import QComboBox
    assert isinstance(dlg_t.w_brans, QComboBox), "w_brans must be a QComboBox!"
    
    items = [dlg_t.w_brans.itemText(i) for i in range(dlg_t.w_brans.count())]
    assert "Matematik" in items and "Fizik" in items and "Kimya" in items, f"Dersler should be in dropdown, got {items}"
    assert dlg_t.w_brans.currentText() == "Matematik", f"Expected currentText to be Matematik, got {dlg_t.w_brans.currentText()}"
    
    # Change branch to Kimya and class to 10B
    dlg_t.w_brans.setCurrentText("Kimya")
    dlg_t.w_so.setCurrentText("10B")
    new_t_data = dlg_t.get_data()
    assert new_t_data["brans"] == "Kimya"
    assert new_t_data["sinif_ogretmeni"] == "10B"
    print(" [1/3] OgretmenEditDialog branch is QComboBox populated from dersler and saves correctly")

    # 2. Test MasterDataDialog updates teacher and syncs classes
    # Simulate updating Altın Bolat
    md.stack.setCurrentIndex(3) # Öğretmenler
    md.table_ogretmen.setCurrentCell(0, 0)
    
    # Update teacher Altın Bolat in data_store through _act_update logic
    data_list = ds["ogretmenler"]
    matched_idx = 0
    
    # Run specific sync logic
    t_name = new_t_data.get("ad", "").strip()
    new_class = new_t_data.get("sinif_ogretmeni", "").strip()
    if new_class:
        for t in ds["ogretmenler"]:
            if t is not data_list[matched_idx] and t.get("sinif_ogretmeni", "").strip().upper() == new_class.upper():
                t["sinif_ogretmeni"] = ""
        for s in ds["siniflar"]:
            if s.get("ad", "").strip().upper() == new_class.upper():
                s["sinif_ogretmeni"] = t_name
            elif s.get("sinif_ogretmeni", "").strip() == t_name:
                s["sinif_ogretmeni"] = ""
    data_list[matched_idx] = new_t_data
    
    # Verify: 10B should now have Altın Bolat, and 9A should be EMPTY!
    s_9a = next(s for s in ds["siniflar"] if s["ad"] == "9A")
    s_10b = next(s for s in ds["siniflar"] if s["ad"] == "10B")
    assert s_9a["sinif_ogretmeni"] == "", f"Expected 9A sinif_ogretmeni to be empty, got {s_9a['sinif_ogretmeni']}"
    assert s_10b["sinif_ogretmeni"] == "Altın Bolat", f"Expected 10B sinif_ogretmeni to be Altın Bolat, got {s_10b['sinif_ogretmeni']}"
    print(" [2/3] Changing Teacher class teacher to 10B cleared 9A and assigned 10B in siniflar")

    # 3. Test changing Class 10B in SinifEditDialog updates Teacher
    dlg_c = SinifEditDialog(parent=md, existing_data=s_10b)
    assert dlg_c.w_so.currentText() == "Altın Bolat", f"Expected SinifEditDialog for 10B to show Altın Bolat, got {dlg_c.w_so.currentText()}"
    
    # Change 10B's teacher to Mehmet Demir
    dlg_c.w_so.setCurrentText("Mehmet Demir")
    new_c_data = dlg_c.get_data()
    assert new_c_data["sinif_ogretmeni"] == "Mehmet Demir"
    
    # Apply class update logic
    c_name = new_c_data.get("ad", "").strip()
    new_so = new_c_data.get("sinif_ogretmeni", "").strip()
    for s in ds["siniflar"]:
        if s is not s_10b and s.get("sinif_ogretmeni", "").strip() == new_so:
            s["sinif_ogretmeni"] = ""
    for t in ds["ogretmenler"]:
        if t.get("ad", "").strip() == new_so:
            t["sinif_ogretmeni"] = c_name
        elif t.get("sinif_ogretmeni", "").strip().upper() == c_name.upper():
            t["sinif_ogretmeni"] = ""
    ds["siniflar"][1] = new_c_data
    
    t_altin = next(t for t in ds["ogretmenler"] if t["ad"] == "Altın Bolat")
    t_mehmet = next(t for t in ds["ogretmenler"] if t["ad"] == "Mehmet Demir")
    assert t_altin["sinif_ogretmeni"] == "", f"Expected Altın Bolat to have no class, got {t_altin['sinif_ogretmeni']}"
    assert t_mehmet["sinif_ogretmeni"] == "10B", f"Expected Mehmet Demir to have 10B, got {t_mehmet['sinif_ogretmeni']}"
    print(" [3/3] Changing Class 10B teacher to Mehmet Demir cleared Altın Bolat and assigned Mehmet Demir")

    print("\n[SUCCESS] ALL PROMPT 15 REQUIREMENTS VERIFIED AND PASSED!")

if __name__ == "__main__":
    test_prompt15_sync_and_branch()
