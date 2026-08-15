import sys
import os

sys.path.insert(0, os.path.abspath("c:/Users/gokay/Desktop/aSc/ChenKi_v2"))

from PySide6.QtWidgets import QApplication
from dialogs.edit_forms import (
    CustomFieldsDialog,
    SubjectClassMultiSelectDialog,
    CombinedClassesDialog,
    LessonAssignmentDialog,
    OgretmenEditDialog,
    DersEditDialog,
    SinifEditDialog,
    DerslikEditDialog
)

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    
    mock_data_store = {
        "ogretmenler": [
            {"ad": "Ahmet Yılmaz", "kisa": "A. YILMAZ", "renk": "#27AE60", "ozel_alanlar": {"Telefon": "0555 111 2233"}},
            {"ad": "Fatma Kaya", "kisa": "F. KAYA", "renk": "#E67E22"}
        ],
        "siniflar": [
            {"ad": "9A", "kisa": "9A", "renk": "#A30F37"},
            {"ad": "9B", "kisa": "9B", "renk": "#3B82F6"},
            {"ad": "10A", "kisa": "10A", "renk": "#10B981"},
            {"ad": "10B", "kisa": "10B", "renk": "#F59E0B"}
        ],
        "dersler": [
            {"ad": "Matematik", "kisa": "MAT", "renk": "#3B82F6"},
            {"ad": "Geometri", "kisa": "GEO", "renk": "#10B981"},
            {"ad": "Fizik", "kisa": "FİZ", "renk": "#8B5CF6"}
        ],
        "derslikler": [
            {"ad": "Derslik 1", "kisa": "D1", "kapasite": "30"}
        ],
        "atamalar": [
            {"teacher": "Ahmet Yılmaz", "subject": "Matematik", "class": "9A", "duration": 2, "type": "2", "color": "#3B82F6"},
            {"teacher": "Ahmet Yılmaz", "subject": "Matematik", "class": "9B", "duration": 2, "type": "2", "color": "#3B82F6"}
        ],
        "grid_placements": [
            {"day": 0, "period": 0, "subject_name": "Matematik", "teacher_name": "Ahmet Yılmaz", "class_name": "9A", "duration": 2}
        ]
    }

    print("=== TEST 1: CustomFieldsDialog ===")
    cf_dlg = CustomFieldsDialog("Ahmet Yılmaz", "Öğretmen", {"Telefon": "0555 111 2233"})
    cf_dlg._add_field("E-Posta", "ahmet@okul.com")
    cf_dlg._save_and_accept()
    cf_data = cf_dlg.get_data()
    print("Custom Fields Data:", cf_data)
    assert cf_data.get("Telefon") == "0555 111 2233"
    assert cf_data.get("E-Posta") == "ahmet@okul.com"
    print("TEST 1 PASSED!")

    print("\n=== TEST 2: SubjectClassMultiSelectDialog ===")
    sc_dlg = SubjectClassMultiSelectDialog("Geometri", ["9A", "9B", "10A", "10B"], ["10A", "10B"])
    selected = sc_dlg.get_selected()
    print("Pre-selected classes for Geometri:", selected)
    assert "10A" in selected and "10B" in selected
    print("TEST 2 PASSED!")

    print("\n=== TEST 3: CombinedClassesDialog (Min 2 constraint & Conflict detection) ===")
    cc_dlg = CombinedClassesDialog(mock_data_store, ["9A", "9B"])
    assert len(cc_dlg.get_selected_classes()) == 2
    assert " + " in cc_dlg.get_combined_string()
    print("Combined String:", cc_dlg.get_combined_string())
    print("TEST 3 PASSED!")

    print("\n=== TEST 4: LessonAssignmentDialog Dynamic Auto Expansion ===")
    la_dlg = LessonAssignmentDialog(data_store=mock_data_store, selected_teacher="Ahmet Yılmaz")
    initial_rows = len(la_dlg.subject_rows)
    print(f"Initial subject rows loaded for Ahmet Yılmaz: {initial_rows}")
    
    # Simulate user changing subject in the trailing empty row -> auto expands!
    last_row = la_dlg.subject_rows[-1]
    last_row["cb_subject"].setCurrentText("Fizik")
    la_dlg._on_subject_changed(last_row, "Fizik")
    
    new_row_count = len(la_dlg.subject_rows)
    print(f"Row count after entering Fizik: {new_row_count} (Expected: {initial_rows + 1})")
    assert new_row_count == initial_rows + 1
    
    assignments = la_dlg.get_data()
    print(f"Generated assignments count: {len(assignments)}")
    for a in assignments:
        print(f"  - {a['teacher']} -> {a['subject']} -> {a['class']} ({a['duration']} Saat, Tip: {a['type']})")
    assert any(a["subject"] == "Matematik" for a in assignments)
    print("TEST 4 PASSED!")

    print("\n=== TEST 5: OgretmenEditDialog Integration ===")
    from PySide6.QtWidgets import QWidget
    class MockParent(QWidget):
        def __init__(self):
            super().__init__()
            self.data_store = mock_data_store
        def save_db(self, *args, **kwargs): pass
        def _refresh_tree(self): pass
    
    t_data = mock_data_store["ogretmenler"][0]
    mock_p = MockParent()
    oed = OgretmenEditDialog(parent=mock_p, existing_data=t_data)
    print("Loaded Ek Dersler:", oed.w_ek_dersler.text())
    assert "Matematik" in oed.w_ek_dersler.text()
    print("Assignments list count in UI:", oed.list_assignments.count())
    assert oed.list_assignments.count() >= 1
    print("OgretmenEditDialog get_data:", oed.get_data())
    assert oed.get_data()["ozel_alanlar"] == {"Telefon": "0555 111 2233"}
    print("TEST 5 PASSED!")

    print("\n=== TEST 6: DersEditDialog, SinifEditDialog, DerslikEditDialog Custom Fields ===")
    ded = DersEditDialog(parent=mock_p, existing_data=mock_data_store["dersler"][0])
    assert "ozel_alanlar" in ded.get_data()
    sed = SinifEditDialog(parent=mock_p, existing_data=mock_data_store["siniflar"][0])
    assert "ozel_alanlar" in sed.get_data()
    dled = DerslikEditDialog(parent=mock_p, existing_data=mock_data_store["derslikler"][0])
    assert "ozel_alanlar" in dled.get_data()
    print("TEST 6 PASSED!")

    print("\nALL PROMPT 2 VERIFICATION TESTS PASSED SUCCESSFULLY! ALL FEATURES WORKING!")

if __name__ == "__main__":
    run_tests()
