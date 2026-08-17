import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPainter, QImage
from PySide6.QtCore import Qt

app = QApplication.instance() or QApplication(sys.argv)

from dialogs.report_selection_dialog import ReportSelectionDialog
from dialogs.print_preview import TimetablePrintPreview

data_store = {
    "okul_adi": "Örnek Anadolu Lisesi",
    "siniflar": [{"ad": "9A"}, {"ad": "10A"}, {"ad": "11C (ea)"}, {"ad": "12 A(say)"}],
    "ogretmenler": [{"ad": "Sultan Yılmaz", "brans": "Matematik"}, {"ad": "Mehmet Yavuz", "brans": "Tarih"}],
    "dersler": [{"ad": "Matematik 11", "kisa": "MAT 11"}, {"ad": "Tarih", "kisa": "TAR"}],
    "atamalar": [
        {"class": "11C (ea)", "subject": "Matematik 11", "teacher": "Sultan Yılmaz", "duration": 4},
        {"class": "12 A(say)", "subject": "Matematik 11", "teacher": "Sultan Yılmaz", "duration": 2},
        {"class": "9A", "subject": "Tarih", "teacher": "Mehmet Yavuz", "duration": 2}
    ],
    "grid_placements": [
        {"class_name": "11C (ea)", "subject_name": "Matematik 11", "teacher_name": "Sultan Yılmaz", "day": 0, "period": 0, "duration": 2, "locked": True},
        {"class_name": "12 A(say)", "subject_name": "Matematik 11", "teacher_name": "Sultan Yılmaz", "day": 0, "period": 2, "duration": 2, "locked": True}
    ],
    "settings": {"periods": 8, "day_count": 5}
}

# 1. Test Single Teacher Assignment List selection
dlg_sel_t = ReportSelectionDialog(data_store, default_type="teacher", default_entity="Sultan Yılmaz")
dlg_sel_t.rb_t_single.setChecked(True)
dlg_sel_t.rb_sub_t_asgn.setChecked(True)
dlg_sel_t._on_confirm()
res_t = dlg_sel_t.get_result()
print("ReportSelectionDialog result (single teacher asgn):", res_t)
assert res_t["mode"] == "Sınıf Dersleri & Atama Listesi (Liste Formatı)"
assert res_t["entity_type"] == "teacher"
assert res_t["entity_name"] == "Sultan Yılmaz"

# 2. Test PrintPreview with Teacher Assignment List
filters = {
    "lock_mode": res_t["mode"],
    "default_selection": res_t["entity_name"],
    "entity_type": res_t["entity_type"],
    "teachers": [res_t["entity_name"]]
}
preview = TimetablePrintPreview(data_store, {}, filters=filters)
assert preview.target_combo.currentText() == "Sultan Yılmaz", f"Expected Sultan Yılmaz, got {preview.target_combo.currentText()}"

img = QImage(800, 1120, QImage.Format_ARGB32)
img.fill(Qt.white)
painter = QPainter(img)
preview._render_class_lessons_list(painter, 800, 1120)
painter.end()
print("Successfully rendered Teacher Assignment List for Sultan Yılmaz!")

# 3. Test Teacher Weekly Grid (Must contain Class Name e.g. 11C (ea), not Sultan Yılmaz in cell)
placements = preview._get_pseudo_placements("Sultan Yılmaz", is_teacher=True)
print("Sultan Yılmaz pseudo placements:", placements)
assert (0, 0) in placements
cell_0 = placements[(0, 0)]
assert cell_0["class_name"] == "11C (ea)"
assert cell_0["subject_name"] == "Matematik 11"

# 4. Test Teacher Carsaf Span
img_carsaf = QImage(1120, 792, QImage.Format_ARGB32)
img_carsaf.fill(Qt.white)
painter_c = QPainter(img_carsaf)
preview._render_carsaf_liste(painter_c, None, 1120, 792, is_teacher=True)
painter_c.end()
print("Successfully rendered Teacher Carsaf with horizontal merged cells!")

print("\nALL REASONING CHECKS PASSED!")
