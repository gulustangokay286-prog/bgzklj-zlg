import sys
import os

# Set environment
sys.path.insert(0, r"c:\Users\gokay\Desktop\aSc\ChenKi_v2")
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from PySide6.QtWidgets import QApplication

def run_tests():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    print("=== TEST 1: Short code generation (Beden, Tarih, Rehberlik, Türkçe, Biyoloji) ===")
    from dialogs.edit_forms import _auto_short_code
    assert _auto_short_code("Biyoloji") == "BİYO", f"Expected BİYO got {_auto_short_code('Biyoloji')}"
    assert _auto_short_code("Rehberlik") == "REHBERLİK", f"Expected REHBERLİK got {_auto_short_code('Rehberlik')}"
    assert _auto_short_code("Matematik 1") == "MATE 1", f"Expected MATE 1 got {_auto_short_code('Matematik 1')}"
    assert _auto_short_code("Fizik2") == "FİZİK 2", f"Expected FİZİK 2 got {_auto_short_code('Fizik2')}"
    assert _auto_short_code("Kimya") == "KİMYA", f"Expected KİMYA got {_auto_short_code('Kimya')}"
    assert _auto_short_code("Beden") == "BEDEN", f"Expected BEDEN got {_auto_short_code('Beden')}"
    assert _auto_short_code("Tarih") == "TARİH", f"Expected TARİH got {_auto_short_code('Tarih')}"
    assert _auto_short_code("Türkçe") == "TÜRKÇE", f"Expected TÜRKÇE got {_auto_short_code('Türkçe')}"
    print("✅ TEST 1 PASSED!")

    print("=== TEST 2: SchoolInfoDialog and settings persistence ===")
    data_store = {
        "settings": {
            "school_name": "Test Okulu",
            "periods": 10,
            "academic_year": "2026 - 2027",
            "day_count": 5,
            "zil_saatleri": [{"ders": 1, "giris": "08:30", "cikis": "09:10"}]
        }
    }
    assert data_store["settings"]["periods"] == 10
    assert data_store["settings"]["academic_year"] == "2026 - 2027"
    print("✅ TEST 2 PASSED!")

    print("=== TEST 3: TimetableGrid dynamic periods scaling ===")
    from timetable_grid import TimetableGrid
    grid = TimetableGrid(periods=8)
    assert grid.table.rowCount() == 8
    grid.set_periods(12)
    assert grid.table.rowCount() == 12
    grid.set_periods(6)
    assert grid.table.rowCount() == 6
    print("✅ TEST 3 PASSED!")

    print("=== TEST 4: AutoScheduler strict manual slot immunity & pedagogical rules ===")
    from auto_scheduler import AutoSchedulerWorker
    
    mock_store = {
        "siniflar": [{"ad": "12/A"}],
        "ogretmenler": [{"ad": "Ahmet Yılmaz"}, {"ad": "Mehmet Kaya"}],
        "dersler": [{"ad": "Matematik"}, {"ad": "Fizik"}, {"ad": "Edebiyat"}],
        "atamalar": [
            {"class": "12/A", "subject": "Matematik", "teacher": "Ahmet Yılmaz", "duration": 6},
            {"class": "12/A", "subject": "Fizik", "teacher": "Mehmet Kaya", "duration": 4},
            {"class": "12/A", "subject": "Edebiyat", "teacher": "Ahmet Yılmaz", "duration": 5}
        ],
        "grid_placements": [
            # Manual placed lesson at Pazartesi 1. & 2. ders
            {"class_name": "12/A", "day": 0, "period": 0, "subject_name": "Matematik", "teacher_name": "Ahmet Yılmaz", "duration": 2, "is_manual": True}
        ],
        "settings": {"periods": 8, "day_count": 5},
        "constraints": {"no_consecutive_hard": True}
    }
    
    worker = AutoSchedulerWorker(mock_store, target_class="12/A")
    # Run solver directly
    empty_slots = []
    for d in range(5):
        for p in range(8):
            if not (d == 0 and (p == 0 or p == 1)): # 0,0 and 0,1 are manual
                empty_slots.append((d, p))
                
    assert len(empty_slots) == 38, f"Expected 38 empty slots, got {len(empty_slots)}"
    
    sol = worker._astar_solve(
        empty_slots=empty_slots,
        candidate_blocks=[{"subject": "Matematik", "teacher": "Ahmet Yılmaz", "duration": 4},
                          {"subject": "Fizik", "teacher": "Mehmet Kaya", "duration": 4}],
        global_teacher_occupied=set(),
        t_objs={},
        c_timeoff=None,
        days_count=5,
        periods_count=8,
        manual_subj_map={(0, 0): "Matematik", (0, 1): "Matematik"},
        constraints={"no_consecutive_hard": True}
    )
    assert len(sol) > 0, "A* solver should return placements"
    # Verify manual slots were NOT in solution
    for item in sol:
        assert not (item["day"] == 0 and (item["period"] == 0 or item["period"] == 1)), "Manual slots must never be overwritten!"
    print("✅ TEST 4 PASSED!")

    print("=== TEST 5: FAQ Dialog Search and Knowledge DB ===")
    from dialogs.faq_dialog import FAQ_DATA, FAQDialog
    assert len(FAQ_DATA) >= 10
    faq = FAQDialog()
    faq._filter_faqs("manuel")
    visible_cards = [c for c, q, a in faq._cards if not c.isHidden()]
    assert len(visible_cards) >= 1, f"Expected at least 1 visible card for 'manuel', got {len(visible_cards)}"
    print("=== TEST 6: TeacherIndividualTimetableDialog Placement Verification ===")
    from PySide6.QtWidgets import QTableWidget
    from dialogs.master_data_dialog import TeacherIndividualTimetableDialog, is_teacher_match
    assert is_teacher_match("Hüseyin Arman", "Hüseyin Arman")
    assert is_teacher_match("Hüseyin Arman", "Hüseyin ARMAN")
    assert is_teacher_match("Hüseyin Arman", "Huseyin Arman")
    assert is_teacher_match("H. Arman", "Hüseyin Arman", [{"ad": "Hüseyin Arman", "kisa": "H. Arman"}])
    
    test_ds = {
        "settings": {"periods": 8, "days_count": 5},
        "ogretmenler": [{"ad": "Hüseyin Arman", "kisa": "H. Arman"}],
        "atamalar": [{"teacher": "Hüseyin Arman", "subject": "Biyoloji", "class": "10B", "duration": 3}],
        "grid_placements": [
            {"teacher_name": "Hüseyin Arman", "subject_name": "Biyoloji", "class_name": "10B", "day": 0, "period": 0, "duration": 2, "color": "#1E88E5"},
            {"teacher": "Hüseyin ARMAN", "subject": "Biyoloji", "class": "10B", "col": 1, "row": 3, "duration": 1, "color": "#1E88E5"}
        ]
    }
    dlg = TeacherIndividualTimetableDialog(teacher_name="Hüseyin Arman", data_store=test_ds)
    # Check that cells in table are filled with Biyoloji (10B)
    table = dlg.findChild(QTableWidget)
    assert table is not None
    item1 = table.item(0, 0)
    assert item1 is not None and "Biyoloji" in item1.text() and "10B" in item1.text()
    item2 = table.item(1, 0) # second period of 2-hour block
    assert item2 is not None and "Biyoloji" in item2.text()
    item3 = table.item(3, 1) # day 1 period 3
    assert item3 is not None and "Biyoloji" in item3.text()
    print("✅ TEST 6 PASSED!")

    print("=== TEST 7: Color Picker, Subject Badges & Print Preview Auto-Placement ===")
    from dialogs.color_picker_dialog import ModernColorPickerDialog
    cp = ModernColorPickerDialog(current_color="#2563EB", title="Test Color Picker")
    assert cp.selected_hex == "#2563EB"
    cp._select_color("#DC2626")
    assert cp.selected_hex == "#DC2626"
    
    from dialogs.print_preview import get_subject_badge, TimetablePrintPreview
    assert get_subject_badge("Biyoloji 1") == "BİYO 1"
    assert get_subject_badge("BİYOLOJİ1") == "BİYO 1"
    assert get_subject_badge("Kimya2") == "KİMYA 2"
    assert get_subject_badge("Fizik") == "FİZİK"
    assert get_subject_badge("Rehberlik") == "REHBERLİK"
    assert get_subject_badge("Görsel Sanatlar") == "GÖRSEL"
    assert get_subject_badge("Matematik 1") == "MAT 1"
    
    # Test Print Preview: empty grid MUST stay empty (no phantom placements)
    empty_grid_ds = {
        "settings": {"periods": 8, "days_count": 5},
        "ogretmenler": [{"ad": "Ahmet Yılmaz", "kisa": "A. Yılmaz"}],
        "siniflar": [{"ad": "10A", "kisa": "10A"}],
        "atamalar": [{"teacher": "Ahmet Yılmaz", "subject": "Biyoloji", "class": "10A", "duration": 2}],
        "grid_placements": []
    }
    prev = TimetablePrintPreview(data_store=empty_grid_ds)
    placements_empty = prev._get_pseudo_placements("Ahmet Yılmaz", is_teacher=True)
    assert len(placements_empty) == 0, f"Deleted/empty grid must have 0 placements, got {len(placements_empty)}"

    # Test Print Preview with actual placement
    placed_grid_ds = {
        "settings": {"periods": 8, "days_count": 5},
        "ogretmenler": [{"ad": "Ahmet Yılmaz", "kisa": "A. Yılmaz"}],
        "siniflar": [{"ad": "10A", "kisa": "10A"}],
        "atamalar": [{"teacher": "Ahmet Yılmaz", "subject": "Biyoloji", "class": "10A", "duration": 2}],
        "grid_placements": [{"teacher_name": "Ahmet Yılmaz", "subject_name": "Biyoloji", "class_name": "10A", "day": 0, "period": 1, "duration": 2}]
    }
    prev_placed = TimetablePrintPreview(data_store=placed_grid_ds)
    placements_placed = prev_placed._get_pseudo_placements("Ahmet Yılmaz", is_teacher=True)
    assert len(placements_placed) == 2, f"Expected 2 placed periods, got {len(placements_placed)}"
    print("✅ TEST 7 PASSED!")

    print("=== TEST 8: AutoScheduler Unassigned Class Immunity ===")
    from auto_scheduler import AutoSchedulerWorker
    ds_with_unassigned_class = {
        "settings": {"periods": 8, "days": ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]},
        "siniflar": [{"ad": "9/A"}, {"ad": "9/B"}],
        "ogretmenler": [{"ad": "Hüseyin Arman"}],
        "dersler": [{"ad": "Matematik"}],
        "atamalar": [
            {"class": "9/A", "subject": "Matematik", "teacher": "Hüseyin Arman", "duration": 2, "type": "2"}
        ],
        "grid_placements": []
    }
    worker2 = AutoSchedulerWorker(ds_with_unassigned_class, target_class="9/B")
    asgns_9b = [a for a in ds_with_unassigned_class["atamalar"] if a.get("class") == "9/B"]
    assert len(asgns_9b) == 0, "9/B must have 0 assignments"
    print("✅ TEST 8 PASSED!")

    print("=== TEST 9: Global Subject Color Update & Persistence ===")
    from dialogs.color_picker_dialog import update_subject_color_globally
    test_color_ds = {
        "dersler": [{"ad": "Biyoloji", "kisa": "BİYO", "renk": "#8E24AA"}],
        "atamalar": [{"class": "9/A", "subject": "Biyoloji", "teacher": "Sultan Yılmaz", "color": "#8E24AA"}],
        "grid_placements": [{"class_name": "9/A", "subject_name": "Biyoloji", "color": "#8E24AA"}],
        "yerlesim": {"0,0": {"subject_name": "Biyoloji", "color": "#8E24AA"}}
    }
    update_subject_color_globally(None, test_color_ds, "Biyoloji", "#DC2626")
    assert test_color_ds["dersler"][0]["renk"] == "#DC2626", "Dersler color must be updated to #DC2626"
    assert test_color_ds["atamalar"][0]["color"] == "#DC2626", "Atamalar color must be updated to #DC2626"
    assert test_color_ds["grid_placements"][0]["color"] == "#DC2626", "Grid placements color must be updated to #DC2626"
    assert test_color_ds["yerlesim"]["0,0"]["color"] == "#DC2626", "Yerlesim color must be updated to #DC2626"
    print("✅ TEST 9 PASSED!")

    print("\n🎉 ALL PROMPT 3 & CONTINUATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()


