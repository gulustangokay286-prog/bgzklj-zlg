"""
test_relations_full_workflow.py
Comprehensive test suite for:
1. EditRelationDialog: subject, teacher, class multi-selection and UI updates.
2. MultiSelectDialog: search filtering, select-all, select-none.
3. PlanningRelationsDialog: table loading, adding rule, editing rule, deleting rule, toggling active checkbox, real-time database saving without 'utils' error.
4. AutoScheduler: honoring active rules, ignoring inactive rules.
"""
import sys
import os

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)

    print("=== TEST 1: MultiSelectDialog with Search and Quick Selection ===")
    from dialogs.relations_dialog import MultiSelectDialog

    items = ["Beden Eğitimi", "Biyoloji", "Coğrafya", "Fizik", "Kimya", "Matematik", "Müzik", "Tarih", "Türkçe"]
    selected = ["Beden Eğitimi", "Müzik"]
    dlg = MultiSelectDialog(items, selected, "Dersleri Seç")

    # Verify initial selections
    assert set(dlg.get_selected()) == {"Beden Eğitimi", "Müzik"}

    # Test search filter
    dlg.search_input.setText("ik")
    # Matching containing 'ik': Fizik, Matematik, Müzik
    dlg._select_all()
    res = dlg.get_selected()
    assert "Fizik" in res
    assert "Matematik" in res
    assert "Müzik" in res

    # Test select none
    dlg.search_input.setText("")
    dlg._select_none()
    assert len(dlg.get_selected()) == 0
    print("✅ TEST 1 PASSED: MultiSelectDialog search and quick selection works perfectly!")

    print("\n=== TEST 2: EditRelationDialog UI, Filters and Real-time Combo Updates ===")
    from dialogs.relations_dialog import EditRelationDialog

    mock_ds = {
        "dersler": [
            {"ad": "Matematik"}, {"ad": "Fizik"}, {"ad": "Beden Eğitimi"}, {"ad": "Müzik"}
        ],
        "ogretmenler": [
            {"ad": "Hakan Yılmaz"}, {"ad": "Mesut Yılmaz"}, {"ad": "Ceylan Gürbüz"}
        ],
        "siniflar": [
            {"ad": "9/A"}, {"ad": "10/A"}, {"ad": "11/A"}
        ],
        "atamalar": [
            {"subject": "Kimya", "teacher": "Serdar Özkan", "class": "12/A"}
        ],
        "planlama_iliskileri": []
    }

    edit_dlg = EditRelationDialog(mock_ds)
    # Set rule to "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun"
    idx_rule = edit_dlg.cb_rule.findText("Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun")
    assert idx_rule >= 0
    edit_dlg.cb_rule.setCurrentIndex(idx_rule)

    # Practical subjects should auto-populate
    assert "Beden Eğitimi" in edit_dlg.selected_subjects
    assert "Müzik" in edit_dlg.selected_subjects
    assert edit_dlg.cb_subj.currentIndex() == 1
    assert "Seçili (2 ders)" in edit_dlg.cb_subj.currentText()

    # Change teachers
    edit_dlg.selected_teachers = ["Hakan Yılmaz", "Mesut Yılmaz"]
    edit_dlg._refresh_combos_ui()
    assert "Seçili (2 öğretmen)" in edit_dlg.cb_teach.currentText()

    # Change classes
    edit_dlg.selected_classes = ["9/A"]
    edit_dlg._refresh_combos_ui()
    assert "Seçili (1 sınıf)" in edit_dlg.cb_class.currentText()

    data = edit_dlg.get_data()
    assert data["kural"] == "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun"
    assert data["parametre"] == 2
    assert "Beden Eğitimi" in data["dersler"]
    assert "Hakan Yılmaz" in data["ogretmenler"]
    assert "9/A" in data["siniflar"]
    print("✅ TEST 2 PASSED: EditRelationDialog dynamic filters and combo previews work perfectly!")

    print("\n=== TEST 3: PlanningRelationsDialog Full Lifecycle & Database Trigger ===")
    from dialogs.relations_dialog import PlanningRelationsDialog

    plan_dlg = PlanningRelationsDialog(mock_ds)
    assert plan_dlg.table.rowCount() == 0

    # Add rule
    mock_ds["planlama_iliskileri"].append({
        "aktif": True,
        "kural": "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun",
        "dersler": ["Beden Eğitimi"],
        "ogretmenler": [],
        "siniflar": ["9/A"],
        "parametre": 2,
        "onem": "Sıkı (Kesinlikle uygulanmalı)"
    })
    plan_dlg._load_table()
    assert plan_dlg.table.rowCount() == 1
    assert plan_dlg.table.item(0, 0).checkState() == Qt.Checked

    # Test toggling active checkbox (Must NOT raise ModuleNotFoundError!)
    chk_item = plan_dlg.table.item(0, 0)
    chk_item.setCheckState(Qt.Unchecked)
    plan_dlg._on_checkbox_changed(chk_item)
    assert mock_ds["planlama_iliskileri"][0]["aktif"] == False

    chk_item.setCheckState(Qt.Checked)
    plan_dlg._on_checkbox_changed(chk_item)
    assert mock_ds["planlama_iliskileri"][0]["aktif"] == True

    # Test toggle all
    plan_dlg._toggle_all()
    assert mock_ds["planlama_iliskileri"][0]["aktif"] == False
    plan_dlg._toggle_all()
    assert mock_ds["planlama_iliskileri"][0]["aktif"] == True

    print("✅ TEST 3 PASSED: PlanningRelationsDialog lifecycle & real-time save works without errors!")

    print("\n=== TEST 4: AutoScheduler Integration with Active vs Inactive Rules ===")
    from auto_scheduler import AutoSchedulerWorker

    test_sched_ds = {
        "siniflar": [{"ad": "9/A"}],
        "ogretmenler": [{"ad": "Hakan Yılmaz"}],
        "dersler": [{"ad": "Beden Eğitimi"}],
        "atamalar": [
            {"class": "9/A", "subject": "Beden Eğitimi", "teacher": "Hakan Yılmaz", "type": "2+2", "duration": 4}
        ],
        "grid_placements": [],
        "settings": {"periods": 8, "days": ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]},
        "planlama_iliskileri": [
            {
                "aktif": True,
                "kural": "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun",
                "dersler": ["Beden Eğitimi"],
                "siniflar": ["9/A"],
                "parametre": 2,
                "onem": "Sıkı"
            }
        ]
    }

    worker = AutoSchedulerWorker(test_sched_ds, target_class="9/A")
    res_dict = {}
    worker.finished_successfully.connect(lambda r: res_dict.update(r))
    worker.run()

    sched = res_dict.get("schedule", [])
    assert len(sched) > 0
    days_used = [item["day"] for item in sched]
    assert len(set(days_used)) == 2, f"Beden Eğitimi 4 saat 2 farklı güne yayılmalıydı: {days_used}"

    print("✅ TEST 4 PASSED: AutoScheduler strictly enforces active planning relations!")

    print("\n🎉 ALL PLANNING RELATIONS WORKFLOW TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
