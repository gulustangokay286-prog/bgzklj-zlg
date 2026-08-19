import os
import sys
from PySide6.QtWidgets import QApplication

# Ensure offscreen Qt platform
os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication(sys.argv)

from dialogs.edit_forms import (
    MultiClassAssignDialog,
    SubjectTeacherAssignmentDialog,
    ClassComprehensiveAssignmentDialog,
    format_tr_name,
    matches_class
)
from auto_scheduler import AutoSchedulerWorker

def test_multi_class_assign_dialog_selection():
    all_classes = ["9A", "10A", "11C", "12B"]
    
    # 1. Test separate and combined selection
    dlg = MultiClassAssignDialog(
        teacher_name="Ahmet Yılmaz",
        subject_name="Beden Eğitimi",
        all_classes=all_classes,
        selected_classes=["9A", "11C", "12B"],
        combined_classes=["11C", "12B"],
        is_combined=True
    )
    
    assert dlg.get_selected_classes() == ["9A", "11C", "12B"]
    assert dlg.get_combined_classes() == ["11C", "12B"]
    assert dlg.get_is_combined() is True
    
    # Test preview label text
    dlg._update_preview()
    preview_txt = dlg.lbl_preview.text()
    assert "11C+12B" in preview_txt
    assert "9A" in preview_txt


def test_subject_teacher_assignment_workflow():
    ds = {
        "ogretmenler": [
            {"ad": "Ahmet Yılmaz", "brans": "Beden Eğitimi"},
            {"ad": "Ayşe Demir", "brans": "Matematik"}
        ],
        "siniflar": [
            {"ad": "9A"}, {"ad": "11C"}, {"ad": "12B"}
        ],
        "dersler": [
            {"ad": "Beden Eğitimi", "saat": 2, "renk": "#2196F3"},
            {"ad": "Matematik", "saat": 4, "renk": "#E91E63"}
        ],
        "atamalar": [],
        "grid_placements": [],
        "yerlesim": {}
    }
    
    # Open dialog for Beden Eğitimi with target class 9A
    dlg = SubjectTeacherAssignmentDialog(
        subject_name="Beden Eğitimi",
        data_store=ds,
        current_class="9A"
    )
    
    # Set Ahmet Yılmaz: 9A gets 2 hours ("2"), and combined group 11C+12B gets 5 hours ("2+2+1")
    ahmet_cfg = dlg.teacher_configs["Ahmet Yılmaz"]
    ahmet_cfg["checked"] = True
    ahmet_cfg["current_class_type"] = "2"
    ahmet_cfg["combined_type"] = "2+2+1"
    ahmet_cfg["classes"] = ["9A", "11C", "12B"]
    ahmet_cfg["combined_classes"] = ["11C", "12B"]
    ahmet_cfg["is_combined"] = True
    
    # Test display text formatting
    display_txt, is_comb = dlg._format_class_display_text(ahmet_cfg)
    assert is_comb is True
    assert "9A, 11C+12B (🔗 Birleşik)" == display_txt
    assert "\n" not in display_txt, "Display text must be a single clean non-duplicate line"
    
    # Save assignments
    dlg._save_assignments()
    
    atamalar = ds["atamalar"]
    assert len(atamalar) == 2, f"Expected 2 assignments, got: {atamalar}"
    
    comb_asgn = next((a for a in atamalar if a.get("is_combined")), None)
    assert comb_asgn is not None
    assert comb_asgn["teacher"] == "Ahmet Yılmaz"
    assert comb_asgn["subject"] == "Beden Eğitimi"
    assert comb_asgn["duration"] == 5
    assert comb_asgn["type"] == "2+2+1"
    assert comb_asgn["class"] == "11C + 12B"
    assert comb_asgn["combined_classes"] == ["11C", "12B"]
    
    sep_asgn = next((a for a in atamalar if not a.get("is_combined")), None)
    assert sep_asgn is not None
    assert sep_asgn["teacher"] == "Ahmet Yılmaz"
    assert sep_asgn["subject"] == "Beden Eğitimi"
    assert sep_asgn["class"] == "9A"
    assert sep_asgn["duration"] == 2
    assert sep_asgn["type"] == "2"
    
    # Reopen dialog for target_class 12B and check reconstructed data
    dlg2 = SubjectTeacherAssignmentDialog(
        subject_name="Beden Eğitimi",
        data_store=ds,
        current_class="12B"
    )
    ahmet_reloaded = dlg2.teacher_configs["Ahmet Yılmaz"]
    assert ahmet_reloaded["checked"] is True
    assert "12B" in ahmet_reloaded["classes"]
    assert ahmet_reloaded["is_combined"] is True
    assert set(ahmet_reloaded["combined_classes"]) == {"11C", "12B"}
    assert ahmet_reloaded["combined_type"] == "2+2+1"


def test_class_comprehensive_assignment_dialog():
    ds = {
        "ogretmenler": [
            {"ad": "Ahmet Yılmaz", "brans": "Beden Eğitimi"}
        ],
        "siniflar": [
            {"ad": "9A"}, {"ad": "11C"}, {"ad": "12B"}
        ],
        "dersler": [
            {"ad": "Beden Eğitimi", "saat": 2, "renk": "#2196F3"}
        ],
        "atamalar": [
            {
                "teacher": "Ahmet Yılmaz",
                "subject": "Beden Eğitimi",
                "class": "11C + 12B",
                "duration": 4,
                "type": "2+2",
                "is_combined": True,
                "combined_classes": ["11C", "12B"]
            },
            {
                "teacher": "Ahmet Yılmaz",
                "subject": "Beden Eğitimi",
                "class": "9A",
                "duration": 2,
                "type": "2",
                "is_combined": False,
                "combined_classes": []
            }
        ],
        "grid_placements": [],
        "yerlesim": {}
    }
    
    # Dialog for 11C
    dlg_11c = ClassComprehensiveAssignmentDialog("11C", data_store=ds)
    item_teacher_11c = dlg_11c.table.item(0, 1)
    assert item_teacher_11c is not None
    assert "Ahmet Yılmaz" in item_teacher_11c.text()
    assert "🔗 11C + 12B Birleşik" in item_teacher_11c.text()
    
    # Dialog for 9A
    dlg_9a = ClassComprehensiveAssignmentDialog("9A", data_store=ds)
    item_teacher_9a = dlg_9a.table.item(0, 1)
    assert item_teacher_9a is not None
    assert item_teacher_9a.text() == "Ahmet Yılmaz  (9A)"
    assert "Birleşik" not in item_teacher_9a.text()
    
    # Test inline hour modification on 9A
    dlg_9a._on_inline_sep_hour_committed("Beden Eğitimi", "3")
    asgn_9a = next(a for a in ds["atamalar"] if a["class"] == "9A")
    assert asgn_9a["duration"] == 3
    assert asgn_9a["type"] == "3"
    assert "Toplam Atanan: 3 / 40 Saat" in dlg_9a.lbl_summary.text()


def test_auto_scheduler_combined_synchronization():
    ds = {
        "ogretmenler": [
            {"ad": "Ahmet Yılmaz", "brans": "Beden Eğitimi"}
        ],
        "siniflar": [
            {"ad": "11C"}, {"ad": "12B"}
        ],
        "dersler": [
            {"ad": "Beden Eğitimi", "saat": 2, "renk": "#2196F3"}
        ],
        "atamalar": [
            {
                "teacher": "Ahmet Yılmaz",
                "subject": "Beden Eğitimi",
                "class": "11C + 12B",
                "duration": 2,
                "type": "2",
                "is_combined": True,
                "combined_classes": ["11C", "12B"]
            }
        ],
        "grid_placements": [],
        "yerlesim": {}
    }
    
    worker = AutoSchedulerWorker(ds)
    worker.run()
    
    placements = ds.get("grid_placements", [])
    assert len(placements) >= 2, f"Expected placements for both classes, got: {placements}"
    
    p_11c = next((p for p in placements if matches_class(p.get("class_name", ""), "11C")), None)
    p_12b = next((p for p in placements if matches_class(p.get("class_name", ""), "12B")), None)
    
    assert p_11c is not None
    assert p_12b is not None
    # Must be on the exact same day and period
    assert p_11c["day"] == p_12b["day"]
    assert p_11c["period"] == p_12b["period"]
    assert p_11c["teacher_name"] == "Ahmet Yılmaz"
    assert p_12b["teacher_name"] == "Ahmet Yılmaz"

if __name__ == "__main__":
    print("Testing test_multi_class_assign_dialog_selection...")
    test_multi_class_assign_dialog_selection()
    print("[PASS] test_multi_class_assign_dialog_selection")

    print("Testing test_subject_teacher_assignment_workflow...")
    test_subject_teacher_assignment_workflow()
    print("[PASS] test_subject_teacher_assignment_workflow")

    print("Testing test_class_comprehensive_assignment_dialog...")
    test_class_comprehensive_assignment_dialog()
    print("[PASS] test_class_comprehensive_assignment_dialog")

    print("Testing test_auto_scheduler_combined_synchronization...")
    test_auto_scheduler_combined_synchronization()
    print("[PASS] test_auto_scheduler_combined_synchronization")
    
    print("\nALL TESTS PASSED SUCCESSFULLY!")
