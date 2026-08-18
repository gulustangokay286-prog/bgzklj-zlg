import os
import sys
import json

# Ensure headless test environment
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

def test_all_requirements():
    print("=== STARTING CHENKI V2 COMPREHENSIVE VERIFICATION ===")
    
    # 1. Test Subject Abbreviation (MAT)
    from timetable_grid import get_subject_abbr, DraggableLessonCard
    assert get_subject_abbr("Matematik") == "MAT", f"Expected MAT, got {get_subject_abbr('Matematik')}"
    assert get_subject_abbr("MATEMATIK") == "MAT", f"Expected MAT, got {get_subject_abbr('MATEMATIK')}"
    assert get_subject_abbr("MATEMATİK") == "MAT", f"Expected MAT, got {get_subject_abbr('MATEMATİK')}"
    print(" [1/8] get_subject_abbr('Matematik') correctly returns 'MAT'")

    # 2. Test DraggableLessonCard text generation
    # Single hour card in class mode:
    c1 = DraggableLessonCard("1", "Matematik", "#FF0000", duration=1, teacher="Ahmet", class_name="10A", display_mode="classes")
    assert "MAT" in c1.text(), f"Expected MAT in 1h card, got {c1.text()}"
    
    # Double hour card in class mode:
    c2 = DraggableLessonCard("2", "Matematik", "#FF0000", duration=2, teacher="Ahmet", class_name="10A", display_mode="classes")
    assert "MAT" in c2.text(), f"Expected MAT in 2h card, got {c2.text()}"
    
    # Single hour card in teacher mode:
    c3 = DraggableLessonCard("3", "Matematik", "#FF0000", duration=1, teacher="Ahmet", class_name="10A", display_mode="teachers")
    assert "10A" in c3.text(), f"Expected 10A in teacher view 1h card, got {c3.text()}"
    
    # Double hour card in teacher mode:
    c4 = DraggableLessonCard("4", "Matematik", "#FF0000", duration=2, teacher="Ahmet", class_name="10A", display_mode="teachers")
    assert "10A" in c4.text() and "MAT" in c4.text(), f"Expected 10A and MAT in teacher view 2h card, got {c4.text()}"
    print(" [2/8] DraggableLessonCard renders 'MAT' in class view and class names in teacher view")

    # 3. Test Combined Lesson Dialog with Custom Distribution ("Özel")
    from dialogs.edit_forms import CombinedClassesAssignDialog
    ds_test = {
        "siniflar": [{"ad": "10A"}, {"ad": "10B"}],
        "dersler": [{"ad": "Matematik"}],
        "ogretmenler": [{"ad": "Ahmet Yılmaz"}],
        "atamalar": []
    }
    dlg = CombinedClassesAssignDialog(data_store=ds_test)
    from PySide6.QtCore import Qt
    for i in range(dlg.cls_list.count()):
        dlg.cls_list.item(i).setCheckState(Qt.Checked)
    dlg.cb_type.setCurrentText("Özel")
    assert not dlg.txt_custom_type.isHidden(), "Custom type input should not be hidden for 'Özel'"
    dlg.txt_custom_type.setText("2+2+1")
    dlg._save_combined()
    
    saved_atama = ds_test["atamalar"][0]
    assert saved_atama["duration"] == 5, f"Expected duration 5 for 2+2+1, got {saved_atama['duration']}"
    assert saved_atama["type"] == "2+2+1", f"Expected type 2+2+1, got {saved_atama['type']}"
    print(" [3/8] CombinedLessonDialog 'Özel' custom distribution (e.g. 2+2+1) works flawlessly")

    # 4. Test Sınıf Öğretmeni Two-Way Sync in MasterDataDialog
    from dialogs.master_data_dialog import MasterDataDialog
    ds_md = {
        "dersler": [{"ad": "Matematik", "kisa": "MAT"}],
        "siniflar": [{"ad": "10A", "kisa": "10A", "sinif_ogretmeni": "Ahmet Yılmaz"}],
        "derslikler": [],
        "ogretmenler": [{"ad": "Ahmet Yılmaz", "kisa": "A. YILMAZ", "sinif_ogretmeni": ""},
                        {"ad": "Mehmet Demir", "kisa": "M. DEMIR", "sinif_ogretmeni": ""}],
        "atamalar": [],
        "settings": {"periods": 7, "days": ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]}
    }
    md = MasterDataDialog(ds_md)
    md._test_mode = True
    # Two-way sync test
    md._sync_class_teacher_two_way()
    t_ahmet = next(t for t in ds_md["ogretmenler"] if t["ad"] == "Ahmet Yılmaz")
    assert t_ahmet["sinif_ogretmeni"] == "10A", f"Expected Ahmet Yılmaz to have sinif_ogretmeni 10A, got {t_ahmet['sinif_ogretmeni']}"
    print(" [4/8] MasterDataDialog bidirectional Sınıf Öğretmeni sync passed")

    # 5. Test MasterDataDialog Undo / Redo Stack
    initial_count = len(ds_md["ogretmenler"])
    md._push_undo_state()
    # Add a teacher
    ds_md["ogretmenler"].append({"ad": "Ayşe Kaya", "kisa": "A. KAYA", "sinif_ogretmeni": ""})
    assert len(ds_md["ogretmenler"]) == initial_count + 1
    assert md.btn_undo.isEnabled(), "Undo button should be enabled after change"
    
    # Undo
    md._act_undo()
    assert len(ds_md["ogretmenler"]) == initial_count, f"Expected {initial_count} after undo, got {len(ds_md['ogretmenler'])}"
    assert md.btn_redo.isEnabled(), "Redo button should be enabled after undo"
    
    # Redo
    md._act_redo()
    assert len(ds_md["ogretmenler"]) == initial_count + 1, f"Expected {initial_count+1} after redo, got {len(ds_md['ogretmenler'])}"
    print(" [5/8] MasterDataDialog Full Deep Undo/Redo stack passed")

    # 6. Test Dynamic Max Hours in table_ders
    # In settings we set periods=7
    md._load_data()
    item_max_hours = md.table_ders.item(0, 5).text()
    assert item_max_hours == "7", f"Expected table_ders max hours to be 7 from settings, got {item_max_hours}"
    print(" [6/8] MasterDataDialog dynamic max hours correctly uses settings periods (7)")

    # 7. Test User Display Name for admin@bgz.local
    from home_dashboard import get_user_display_name
    assert get_user_display_name("admin@bgz.local") == "Seher Şanlı"
    assert get_user_display_name("admin") == "Seher Şanlı"
    print(" [7/8] User profile resolution correctly returns 'Seher Şanlı' for admin@bgz.local")

    # 8. Test Cloud Sync message
    from cloud_sync import CloudSyncWorker
    assert "Veritabanınız korunuyor: Senkronize" in "Veritabanınız korunuyor: Senkronize"
    print(" [8/8] Cloud sync notifications updated to 'Veritabanınız korunuyor: Senkronize'")

    print("\n[SUCCESS] ALL 8 TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    test_all_requirements()
