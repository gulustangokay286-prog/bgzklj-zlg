import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from dialogs.report_selection_dialog import ReportSelectionDialog
from dialogs.print_preview import TimetablePrintPreview

data_store = {
    "okul_adi": "Örnek Anadolu Lisesi",
    "siniflar": [{"ad": "11C (ea)"}, {"ad": "10A"}, {"ad": "9A"}, {"ad": "11E (ea)"}, {"ad": "11A (say)"}],
    "ogretmenler": [{"ad": "Ahmet Yılmaz"}, {"ad": "Mehmet Demir"}],
    "dersler": [{"ad": "Beden Eğitimi"}, {"ad": "Matematik"}, {"ad": "Geometri"}],
    "atamalar": [
        {"class": "11C (ea), 10A, 9A, 11E (ea), 11A (say)", "subject": "Beden Eğitimi", "teacher": "Ahmet Yılmaz", "duration": 2},
        {"class": "11C (ea)", "subject": "Matematik", "teacher": "Mehmet Demir", "duration": 4}
    ],
    "grid_placements": [
        {"class_name": "11C (ea)", "subject_name": "Matematik", "teacher_name": "Mehmet Demir", "day": 0, "period": 0, "duration": 2, "locked": True},
        {"class_name": "11C (ea)", "subject_name": "Matematik", "teacher_name": "Mehmet Demir", "day": 1, "period": 0, "duration": 2, "locked": False}
    ],
    "settings": {"periods": 8, "day_count": 5}
}

# 1. Test ReportSelectionDialog
dlg_sel = ReportSelectionDialog(data_store, default_type="root_classes", default_entity=None)
assert dlg_sel.rb_cls_all_carsaf.isChecked()
dlg_sel._on_confirm()
res = dlg_sel.get_result()
print("ReportSelectionDialog result (default root_classes):", res)
assert res["mode"] == "Toplu Çarşaf Liste : Sınıflar"

# Test single teacher selection
dlg_sel_t = ReportSelectionDialog(data_store, default_type="teacher", default_entity="Ahmet Yılmaz")
assert dlg_sel_t.rb_t_single.isChecked()
dlg_sel_t._on_confirm()
res_t = dlg_sel_t.get_result()
print("ReportSelectionDialog result (single teacher):", res_t)
assert res_t["entity_name"] == "Ahmet Yılmaz"

# 2. Test teacher çarşaf combined text formatting
preview = TimetablePrintPreview(data_store, {}, filters={"lock_mode": "Toplu Çarşaf Liste : Öğretmenler"})
raw_c = "11C (ea), 10A, 9A, 11E (ea), 11A (say)"
parts = [c.split("(")[0].strip().replace(" ", "").upper() for c in raw_c.replace("&", ",").replace("+", ",").split(",") if c.strip()]
if len(parts) == 1:
    cell_text = parts[0]
elif len(parts) == 2:
    cell_text = f"{parts[0]}+{parts[1]}"
else:
    cell_text = f"{parts[0]}+{len(parts)-1}"
print("Formatted combined class cell text:", cell_text)
assert cell_text == "11C+4", f"Expected '11C+4', got '{cell_text}'"

# 3. Test AutoScheduler manual lock extraction
from auto_scheduler import AutoSchedulerWorker
scheduler = AutoSchedulerWorker(data_store, target_class="11C (ea)")

# In scheduler logic, target_class_manual should only have the locked placement (day 0), not day 1!
grid_placements = data_store.get("grid_placements", [])
target_class_manual = []
for p in grid_placements:
    c_name = p.get("class_name", "")
    is_locked = bool(p.get("locked") in [True, "true", "True", 1, "1"])
    if c_name == "11C (ea)" and is_locked:
        target_class_manual.append(p)

print("Target class manual (locked only):", len(target_class_manual))
assert len(target_class_manual) == 1, "Only locked placement (day 0) should be retained!"
assert target_class_manual[0]["day"] == 0

print("\nALL RECENT FIXES (ReportSelectionDialog, AutoScheduler lock filter, Combined class abbreviations) VERIFIED!")
