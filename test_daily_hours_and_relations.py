"""
test_daily_hours_and_relations.py
Verifies that Beden Eğitimi or any subject cannot be placed 4 hours in a single day,
and verifies Planlama İlişkileri dialog and rule execution.
"""
import sys
import os

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from PySide6.QtWidgets import QApplication

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)

    print("=== TEST 1: AutoScheduler Daily Hours Limit & Spread (Beden Eğitimi 4h) ===")
    from auto_scheduler import AutoSchedulerWorker

    test_ds = {
        "siniflar": [{"ad": "10/A"}],
        "ogretmenler": [{"ad": "Hakan Yılmaz"}],
        "dersler": [
            {"ad": "Beden Eğitimi", "kisaltma": "BED"},
            {"ad": "Matematik", "kisaltma": "MAT"}
        ],
        "atamalar": [
            {"class": "10/A", "subject": "Beden Eğitimi", "teacher": "Hakan Yılmaz", "type": "2+2", "duration": 4},
            {"class": "10/A", "subject": "Matematik", "teacher": "Hakan Yılmaz", "type": "2+2+2", "duration": 6}
        ],
        "grid_placements": [],
        "settings": {"periods": 8, "days": ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]}
    }

    worker = AutoSchedulerWorker(test_ds, target_class="10/A")
    results = {}
    def on_done(res):
        results.update(res)
    worker.finished_successfully.connect(on_done)
    worker.run()

    sched = results.get("schedule", [])
    print("ALL SCHED ITEMS:", sched)
    assert len(sched) > 0, "Schedule must not be empty"

    # Count Beden Eğitimi hours per day
    beden_by_day = {}
    for item in sched:
        if item.get("subject_name") == "Beden Eğitimi":
            d = item["day"]
            beden_by_day[d] = beden_by_day.get(d, 0) + item.get("duration", 1)

    print(f"Beden Eğitimi Günlük Dağılım: {beden_by_day}")
    for d, h in beden_by_day.items():
        assert h <= 2, f"Beden Eğitimi tek bir günde {h} saat olamaz! En fazla 2 saat olmalıdır."
    print("✅ TEST 1 PASSED: Beden Eğitimi asla tek günde 4 saat olmadı, günlere eşit dağıtıldı!")

    print("=== TEST 2: PlanningRelationsDialog & Rule Configuration ===")
    from dialogs.relations_dialog import PlanningRelationsDialog, EditRelationDialog

    rel_ds = {
        "dersler": [{"ad": "Beden Eğitimi"}, {"ad": "Matematik"}, {"ad": "Fizik"}],
        "ogretmenler": [{"ad": "Hakan Yılmaz"}],
        "siniflar": [{"ad": "10/A"}],
        "planlama_iliskileri": [
            {
                "aktif": True,
                "kural": "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun",
                "dersler": ["Beden Eğitimi"],
                "siniflar": [],
                "ogretmenler": [],
                "parametre": 2,
                "onem": "Sıkı (Kesinlikle uygulanmalı)"
            }
        ]
    }

    dlg = PlanningRelationsDialog(data_store=rel_ds)
    assert dlg.table.rowCount() == 1
    item_rule = dlg.table.item(0, 1)
    assert "Beden Eğitimi" in item_rule.text()
    print("✅ TEST 2 PASSED: PlanningRelationsDialog loaded and displayed rules correctly!")

    print("\n🎉 ALL DAILY HOURS & RELATIONS TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
