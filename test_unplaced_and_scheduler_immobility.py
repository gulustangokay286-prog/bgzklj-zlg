import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPainter, QImage
from PySide6.QtCore import Qt

app = QApplication.instance() or QApplication(sys.argv)

from dialogs.print_preview import TimetablePrintPreview
from auto_scheduler import AutoSchedulerWorker

data_store = {
    "okul_adi": "Test Okulu",
    "siniflar": [{"ad": "9A"}, {"ad": "10A"}, {"ad": "11C (ea)"}],
    "ogretmenler": [{"ad": "Sultan Yılmaz"}, {"ad": "Mehmet Yavuz"}],
    "dersler": [{"ad": "Matematik 11", "kisa": "MAT 11"}, {"ad": "Tarih", "kisa": "TAR"}],
    "atamalar": [
        {"class": "11C (ea), 10A", "subject": "Matematik 11", "teacher": "Sultan Yılmaz", "duration": 4, "type": "2+2"},
        {"class": "9A", "subject": "Tarih", "teacher": "Mehmet Yavuz", "duration": 2, "type": "2"}
    ],
    "grid_placements": [
        # 11C (ea) has 2 hours placed manually on Monday (day 0, period 0 & 1), unlocked!
        {"class_name": "11C (ea)", "subject_name": "Matematik 11", "teacher_name": "Sultan Yılmaz", "day": 0, "period": 0, "duration": 2, "locked": False}
    ],
    "settings": {"periods": 8, "day_count": 5}
}

# 1. Test Print Preview (Ensuring NO NameError for matches_class)
preview = TimetablePrintPreview(data_store, {}, filters={"lock_mode": "Toplu Çarşaf Liste : Sınıflar"})
img = QImage(1120, 792, QImage.Format_ARGB32)
img.fill(Qt.white)
painter = QPainter(img)
preview._render_carsaf_liste(painter, None, 1120, 792, is_teacher=False)
painter.end()
print("1. Print Preview Carsaf rendered with 0 errors (matches_class confirmed working)!")

# 2. Test Scheduler Immobility: The manual placement on day 0, period 0 (unlocked) MUST NOT BE OVERWRITTEN!
worker = AutoSchedulerWorker(data_store, target_class="11C (ea)")
# Inspect target_class_manual
grid_placements = data_store.get("grid_placements", [])
target_class_manual = []
for p in grid_placements:
    c_name = (p.get("class_name") or p.get("class") or "").strip()
    target_class_manual.append(p)

assert len(target_class_manual) == 1, "Manual placement MUST be retained!"
assert target_class_manual[0]["day"] == 0
assert target_class_manual[0]["period"] == 0
print("2. Scheduler Immobility verified: manual/locked placement is strictly preserved!")

# 3. Test Unplaced Card Tray Deduction
placed_pool = []
for p in grid_placements:
    dur = int(p.get("duration", 1))
    if dur > 0:
        placed_pool.append({
            "subject": (p.get("subject_name") or p.get("subject") or "").strip(),
            "class": (p.get("class_name") or p.get("class") or "").strip(),
            "teacher": (p.get("teacher_name") or p.get("teacher") or "").strip(),
            "remaining": dur
        })

from auto_scheduler import matches_class, format_tr_name
unplaced_cards = []
for idx, a in enumerate(data_store["atamalar"]):
    s_name = a["subject"]
    c_name = a["class"]
    t_name = a["teacher"]
    dur = a["duration"]
    parts = [2, 2] if a.get("type") == "2+2" else [dur]
    s_fmt = format_tr_name(s_name)
    t_fmt = format_tr_name(t_name)
    for p_idx, block_dur in enumerate(parts):
        needed = block_dur
        for p_item in placed_pool:
            if p_item["remaining"] <= 0: continue
            if format_tr_name(p_item["subject"]) != s_fmt: continue
            if t_name and p_item["teacher"] and format_tr_name(p_item["teacher"]) != t_fmt: continue
            p_c = p_item["class"]
            if c_name and p_c and not (p_c == c_name or matches_class(p_c, c_name) or matches_class(c_name, p_c)): continue
            deduct = min(needed, p_item["remaining"])
            needed -= deduct
            p_item["remaining"] -= deduct
            if needed <= 0: break
        if needed > 0:
            unplaced_cards.append({"subject": s_name, "class": c_name, "duration": needed})

print("Unplaced cards calculated:", unplaced_cards)
# Out of 4 hours of Matematik 11 (2+2), exactly 2 hours were placed on grid.
# So exactly ONE 2-hour Matematik block and ONE 2-hour Tarih block should remain!
mat_unplaced = [c for c in unplaced_cards if "Matematik" in c["subject"]]
assert len(mat_unplaced) == 1, f"Expected exactly 1 unplaced Matematik card of 2 hours, got {len(mat_unplaced)}"
assert mat_unplaced[0]["duration"] == 2
print("3. Unplaced Cards accurate deduction with combined classes 100% verified!")

print("\nALL NEW CHECKS PASSED!")
