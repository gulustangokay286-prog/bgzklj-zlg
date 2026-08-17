import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from dialogs.print_preview import TimetablePrintPreview

app = QApplication.instance() or QApplication(sys.argv)

data_store = {
    "okul_adi": "Örnek Anadolu Lisesi",
    "siniflar": [{"ad": "9A"}, {"ad": "9B"}],
    "ogretmenler": [{"ad": "Ahmet Yılmaz", "kisa": "A.YILMAZ"}, {"ad": "Mehmet Demir", "kisa": "M.DEMİR"}],
    "dersler": [
        {"ad": "Geometri", "kisa": "GEOM"},
        {"ad": "Matematik", "kisa": "MATE"},
        {"ad": "Coğrafya", "kisa": "COĞRAF"}
    ],
    "grid_placements": [
        {
            "subject_name": "Geometri",
            "teacher_name": "Ahmet Yılmaz",
            "class_name": "9A",
            "col": 0, "day": 0, "row": 0, "period": 0,
            "duration": 2, "locked": True
        },
        {
            "subject_name": "Coğrafya",
            "teacher_name": "Mehmet Demir",
            "class_name": "9B",
            "col": 1, "day": 0, "row": 1, "period": 1,
            "duration": 1, "locked": False
        }
    ],
    "settings": {"periods": 8, "day_count": 5}
}

dlg = TimetablePrintPreview(data_store, {}, filters={"lock_mode": "Toplu Çarşaf Liste : Öğretmenler"})

# Verify teacher placements retrieval
placements_ahmet = dlg._get_pseudo_placements("Ahmet Yılmaz", is_teacher=True)
print("Placements for Ahmet Yılmaz:", placements_ahmet)
assert (0, 0) in placements_ahmet, "Monday period 0 should be placed for Ahmet Yılmaz"
assert (0, 1) in placements_ahmet, "Monday period 1 (2nd hour) should be placed for Ahmet Yılmaz"
assert placements_ahmet[(0, 0)]["class_name"] == "9A", "class_name must be '9A'"
assert placements_ahmet[(0, 0)]["subject_name"] == "Geometri", "subject_name must be 'Geometri'"

placements_mehmet = dlg._get_pseudo_placements("Mehmet Demir", is_teacher=True)
print("Placements for Mehmet Demir:", placements_mehmet)
assert (0, 1) in placements_mehmet, "Monday period 1 should be placed for Mehmet Demir"
assert placements_mehmet[(0, 1)]["class_name"] == "9B", "class_name must be '9B'"

print("\nSUCCESS: All pseudo placements, teacher çarşaf retrieval, and multi-hour spans verified successfully!")
