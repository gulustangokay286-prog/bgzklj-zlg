import sys
from PySide6.QtWidgets import QApplication
from dialogs.edit_forms import OgretmenEditDialog, LessonAssignmentDialog
from dialogs.print_preview import TimetablePrintPreview

app = QApplication.instance() or QApplication(sys.argv)

mock_data_store = {
    "ogretmenler": [{"ad": "Sultan Yılmaz", "kisa": "S. YILMAZ", "renk": "#27AE60"}],
    "dersler": [{"ad": "Matematik10"}, {"ad": "Matematik1"}],
    "siniflar": [{"ad": "10A"}, {"ad": "11C"}, {"ad": "12A"}],
    "atamalar": [],
    "grid_placements": [],
    "settings": {"periods": 8, "days_count": 5}
}

print("=== TEST 1: LessonAssignmentDialog Saving ===")
lad = LessonAssignmentDialog(data_store=mock_data_store, selected_teacher="Sultan Yılmaz")
# Simulating row data
lad._add_subject_row(subject_name="Matematik10", hours="5", distribution="2+2+1", assigned_classes=["10A"], class_configs={"10A": {"type": "2+2+1", "duration": 5}})
lad.accept()

print("Atamalar count after LAD accept:", len(mock_data_store["atamalar"]))
assert len(mock_data_store["atamalar"]) > 0, "Atamalar should have at least 1 item"
atama = mock_data_store["atamalar"][0]
print("Atama entry:", atama)
assert atama.get("ogretmen") == "Sultan Yılmaz"
assert atama.get("teacher") == "Sultan Yılmaz"
assert atama.get("ders") == "Matematik10"
assert atama.get("sinif") == "10A"
assert atama.get("ders_sayisi") == 5
assert atama.get("duration") == 5
print("✅ Test 1 Passed: Both Turkish and English keys correctly saved!")

print("\n=== TEST 2: OgretmenEditDialog List Display ===")
oed = OgretmenEditDialog(parent=None, existing_data={"ad": "Sultan Yılmaz", "kisa": "S. YILMAZ"})
oed._update_assignments_list(mock_data_store)
item_count = oed.list_assignments.count()
print("List items count:", item_count)
assert item_count == 1, f"Expected 1 item in list, got {item_count}"
item_text = oed.list_assignments.item(0).text()
print("List item text:", item_text)
assert "Matematik10" in item_text and "10A" in item_text and "5 Saat" in item_text
print("✅ Test 2 Passed: OgretmenEditDialog renders assignments correctly!")

print("\n=== TEST 3: Print Preview Single & Multi Mode Combo ===")
tpp = TimetablePrintPreview(data_store=mock_data_store, parent=None)

# 1. Test class mode targets
tpp._populate_targets()
class_items = [tpp.target_combo.itemText(i) for i in range(tpp.target_combo.count())]
print("Class mode items:", class_items)
assert "10A" in class_items
assert "Tüm Sınıflar (Çoklu Sayfa)" in class_items

# 2. Switch to teacher mode
idx_mode = tpp.mode_combo.findText("[BİREBİR] Tüm Öğretmenler (Yatay Sayfada 6'lı Çizelge)")
if idx_mode >= 0:
    tpp.mode_combo.setCurrentIndex(idx_mode)
    teacher_items = [tpp.target_combo.itemText(i) for i in range(tpp.target_combo.count())]
    print("Teacher mode items:", teacher_items)
    assert "Sultan Yılmaz" in teacher_items
    assert "Tüm Öğretmenler (Çoklu Sayfa)" in teacher_items
    
    # 3. Select single teacher and verify repaint
    idx_t = tpp.target_combo.findText("Sultan Yılmaz")
    tpp.target_combo.setCurrentIndex(idx_t)
    tpp._repaint()
    print("✅ Single teacher repaint successful!")

print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
