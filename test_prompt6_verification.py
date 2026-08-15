import sys
import os

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Ensure headless Qt
app = QApplication.instance() or QApplication(sys.argv)

def test_no_scroll_combobox():
    print("Testing NoScrollComboBox...")
    from dialogs.edit_forms import NoScrollComboBox
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtCore import QPointF, QPoint
    
    cb = NoScrollComboBox()
    cb.addItems(["A", "B", "C"])
    cb.setCurrentIndex(0)
    
    # Simulate wheel event while popup is closed
    event = QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(0, 120), QPoint(0, 120), Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
    cb.wheelEvent(event)
    assert cb.currentIndex() == 0, f"Expected index 0 after scroll, got {cb.currentIndex()}"
    print("✅ NoScrollComboBox wheel scroll safely ignored!")

def test_subject_class_multi_select_dialog():
    print("Testing SubjectClassMultiSelectDialog with per-class hours...")
    from dialogs.edit_forms import SubjectClassMultiSelectDialog
    
    dlg = SubjectClassMultiSelectDialog(
        subject_name="Matematik",
        all_classes=["9A", "10A", "11A"],
        selected_classes=["9A", "11A"],
        default_distribution="2+2",
        class_configs={
            "9A": {"type": "2+2", "duration": 4},
            "11A": {"type": "2+1", "duration": 3}
        }
    )
    
    selected = dlg.get_selected()
    configs = dlg.get_configs()
    
    assert "9A" in selected and "11A" in selected, "Expected 9A and 11A selected"
    assert configs["9A"]["type"] == "2+2" and configs["9A"]["duration"] == 4
    assert configs["11A"]["type"] == "2+1" and configs["11A"]["duration"] == 3
    print("✅ SubjectClassMultiSelectDialog per-class hours verified!")

def test_combined_classes_removal():
    print("Testing CombinedClassesDialog removal / clear...")
    from dialogs.edit_forms import CombinedClassesDialog
    
    ds = {"siniflar": [{"ad": "9A"}, {"ad": "10A"}, {"ad": "11A"}]}
    dlg = CombinedClassesDialog(data_store=ds, selected_classes=["9A", "10A"])
    assert len(dlg.selected_classes) == 2
    
    dlg._do_clear()
    assert dlg.get_selected_classes() == [], f"Expected empty list after clear, got {dlg.get_selected_classes()}"
    print("✅ CombinedClassesDialog clear/removal verified!")

def test_lesson_assignment_dialog():
    print("Testing LessonAssignmentDialog persistence and autocomplete...")
    from dialogs.edit_forms import LessonAssignmentDialog
    
    ds = {
        "ogretmenler": [{"ad": "Sultan Yılmaz"}],
        "siniflar": [{"ad": "9A"}, {"ad": "10A"}, {"ad": "11A"}],
        "dersler": [{"ad": "Matematik 9"}, {"ad": "Matematik 10"}],
        "atamalar": []
    }
    
    dlg = LessonAssignmentDialog(data_store=ds, selected_teacher="Sultan Yılmaz")
    assert dlg.cb_ogretmen.currentText() == "Sultan Yılmaz"
    
    # Configure first row
    r0 = dlg.subject_rows[0]
    r0["cb_subject"].setCurrentText("Matematik 9")
    r0["classes"] = ["9A", "11A"]
    r0["class_configs"] = {
        "9A": {"type": "2+2", "duration": 4},
        "11A": {"type": "2+1", "duration": 3}
    }
    dlg._update_row_badge(r0)
    
    # Call accept and check persistence in data_store
    dlg.accept()
    
    atamalar = ds["atamalar"]
    assert len(atamalar) == 2, f"Expected 2 atama items, got {len(atamalar)}"
    
    a_9a = next(a for a in atamalar if a["class"] == "9A")
    a_11a = next(a for a in atamalar if a["class"] == "11A")
    
    assert a_9a["duration"] == 4 and a_9a["type"] == "2+2"
    assert a_11a["duration"] == 3 and a_11a["type"] == "2+1"
    print("✅ LessonAssignmentDialog per-class assignment persistence verified!")

def test_auto_short_code_updates():
    print("Testing auto shortcode updates...")
    from dialogs.edit_forms import _auto_short_code, OgretmenEditDialog, SinifEditDialog, DersEditDialog
    
    assert _auto_short_code("Biyoloji") == "BİYO"
    assert _auto_short_code("Rehberlik") == "REHBERLİK"
    assert _auto_short_code("Matematik 10") == "MAT 10"
    assert _auto_short_code("Beden") == "BEDEN"
    assert _auto_short_code("Tarih") == "TARİH"
    assert _auto_short_code("Türkçe") == "TÜRKÇE"
    
    # Test edit dialogs updating shortcodes even with existing data
    ds = {"siniflar": [{"ad": "9A"}], "ogretmenler": [{"ad": "Ahmet Yılmaz", "kisa": "A. YILMAZ"}]}
    
    t_dlg = OgretmenEditDialog(existing_data={"ad": "Ahmet Yılmaz", "kisa": "A. YILMAZ"})
    t_dlg.w_ad.setText("Sultan Yılmaz")
    assert t_dlg.w_kisa.text() == "S. YILMAZ", f"Expected S. YILMAZ, got {t_dlg.w_kisa.text()}"
    
    c_dlg = SinifEditDialog(existing_data={"ad": "10 A", "kisa": "10A"})
    c_dlg.w_ad.setText("11 B")
    assert c_dlg.w_kisa.text() == "11B", f"Expected 11B, got {c_dlg.w_kisa.text()}"
    
    d_dlg = DersEditDialog(existing_data={"ad": "Fizik", "kisa": "FİZİK"})
    d_dlg.txt_ad.setText("Biyoloji")
    assert d_dlg.txt_kisa.text() == "BİYO", f"Expected BİYO, got {d_dlg.txt_kisa.text()}"
    
    print("✅ Auto shortcode updates on GÜNCELLE verified!")

if __name__ == "__main__":
    test_no_scroll_combobox()
    test_subject_class_multi_select_dialog()
    test_combined_classes_removal()
    test_lesson_assignment_dialog()
    test_auto_short_code_updates()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
