import sys, os
sys.path.insert(0, os.path.abspath("c:/Users/gokay/Desktop/aSc/ChenKi_v2"))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

def test_all():
    print("=== TEST 1: SchoolInfoDialog Comprehensive Field Persistence ===")
    from dialogs.school_info import SchoolInfoDialog
    mock_ds = {
        "settings": {
            "school_name": "Pivot Akademi",
            "start_date": "12/09/2026",
            "academic_year": "2026 - 2027",
            "bulletin_no": "2026/45",
            "principal": "Ali ÇEKEN",
            "principal_title": "Okul Müdürü",
            "periods": 7,
            "day_count": 5,
            "weekend": "Cumartesi - Pazar",
            "multi_term": True,
            "school_type": "okul"
        },
        "kurum": {
            "isim": "Pivot Akademi",
            "yetkili": "Ali ÇEKEN"
        },
        "siniflar": [{"ad": "9A"}, {"ad": "10B"}, {"ad": "11A"}],
        "ogretmenler": [{"ad": "Hüseyin Arman"}],
        "atamalar": [
            {"subject": "Biyoloji", "teacher": "Hüseyin Arman", "class": "10B", "duration": 2, "type": "2"},
            {"subject": "Matematik", "teacher": "Hüseyin Arman", "class": "11A", "duration": 4, "type": "2+2"}
        ],
        "grid_placements": []
    }
    
    dlg = SchoolInfoDialog(data_store=mock_ds)
    # Verify loaded values match dialog UI fields
    assert dlg.txt_kurum_adi.text() == "Pivot Akademi", f"Expected 'Pivot Akademi', got {dlg.txt_kurum_adi.text()}"
    assert dlg.txt_baslangic.text() == "12/09/2026", f"Expected '12/09/2026', got {dlg.txt_baslangic.text()}"
    assert dlg.txt_yil.text() == "2026 - 2027", f"Expected '2026 - 2027', got {dlg.txt_yil.text()}"
    assert dlg.txt_teblig.text() == "2026/45", f"Expected '2026/45', got {dlg.txt_teblig.text()}"
    assert dlg.txt_yetkili_ad.text() == "Ali ÇEKEN", f"Expected 'Ali ÇEKEN', got {dlg.txt_yetkili_ad.text()}"
    assert dlg.cb_ders_saati.currentText() == "7", f"Expected '7', got {dlg.cb_ders_saati.currentText()}"
    assert dlg.cb_gun_sayisi.currentText() == "5", f"Expected '5', got {dlg.cb_gun_sayisi.currentText()}"
    assert dlg.chk_cok_donem.isChecked() is True
    assert dlg.radio_okul.isChecked() is True
    
    # Edit fields in dialog and save
    dlg.txt_kurum_adi.setText("Bogazici Koleji")
    dlg.txt_baslangic.setText("15/09/2026")
    dlg.txt_yil.setText("2026 - 2027 Pro")
    dlg.txt_teblig.setText("2026/99")
    dlg.txt_yetkili_ad.setText("Kemal Sunal")
    dlg.txt_yetkili_unvan.setText("Genel Mudur")
    dlg.cb_ders_saati.setCurrentText("8")
    dlg.cb_gun_sayisi.setCurrentText("6") # will auto-set weekend to "Yalniz Pazar"
    dlg.chk_cok_donem.setChecked(False)
    dlg.radio_fakulte.setChecked(True)
    
    dlg._save_and_accept()
    
    # Verify saved data in data_store
    assert mock_ds["okul_adi"] == "Bogazici Koleji"
    assert mock_ds["kurum"]["isim"] == "Bogazici Koleji"
    assert mock_ds["kurum"]["yetkili"] == "Kemal Sunal"
    assert mock_ds["kurum"]["yetkili_unvan"] == "Genel Mudur"
    assert mock_ds["settings"]["school_name"] == "Bogazici Koleji"
    assert mock_ds["settings"]["start_date"] == "15/09/2026"
    assert mock_ds["settings"]["academic_year"] == "2026 - 2027 Pro"
    assert mock_ds["settings"]["bulletin_no"] == "2026/99"
    assert mock_ds["settings"]["principal"] == "Kemal Sunal"
    assert mock_ds["settings"]["principal_title"] == "Genel Mudur"
    assert mock_ds["settings"]["periods"] == 8
    assert mock_ds["settings"]["day_count"] == 6
    assert mock_ds["settings"]["weekend"] == "Yalnız Pazar"
    assert mock_ds["settings"]["multi_term"] is False
    assert mock_ds["settings"]["school_type"] == "fakulte"
    assert len(mock_ds["settings"]["days"]) == 6
    print("TEST 1 PASSED: All SchoolInfoDialog fields saved and synchronized into data_store and settings!")

    print("\n=== TEST 2: Unplaced Lessons Tray Shows All Lessons by Default ===")
    from main_window import MainWindow
    win = MainWindow()
    win.data_store = mock_ds
    
    # Notice that class '9A' has 0 assignments, but '10B' and '11A' have 6 hours total
    # Calling _refresh_unplaced_lessons() without parameters MUST show all unplaced lessons across all classes!
    win._refresh_unplaced_lessons()
    
    # Check widgets inside unplaced dock
    dock = win._grid.unplaced_dock
    card_count = 0
    for i in range(dock.container_layout.count()):
        w = dock.container_layout.itemAt(i).widget()
        if w and hasattr(w, "subject_name"):
            card_count += 1
            print(f"Unplaced Card {card_count}: {w.class_name} - {w.subject_name} ({w.duration}h)")
            
    assert card_count == 3, f"Expected 3 cards (10B 2h, 11A 2h, 11A 2h), got {card_count}"
    print("TEST 2 PASSED: Bottom draggable dock shows ALL unplaced lessons across all classes automatically without needing row hover!")

    print("\n=== TEST 3: DraggableLessonCard Square & Sizing & Tooltip ===")
    from timetable_grid import DraggableLessonCard
    c1 = DraggableLessonCard(1, "Biyoloji", "#22C55E", duration=1, teacher="Hüseyin Arman", class_name="10B")
    c2 = DraggableLessonCard(2, "Biyoloji", "#22C55E", duration=2, teacher="Hüseyin Arman", class_name="10B")
    
    assert c1.width() == 30 and c1.height() == 28, f"Expected 30x28, got {c1.width()}x{c1.height()}"
    assert c2.width() == 62 and c2.height() == 28, f"Expected 62x28, got {c2.width()}x{c2.height()}"
    assert "10B" in c1.toolTip() and "Biyoloji" in c1.toolTip()
    assert "10B" in c2.toolTip() and "Hüseyin Arman" in c2.toolTip()
    print("TEST 3 PASSED: DraggableLessonCard dimensions (1h: 30x28, 2h: 62x28) and tooltips verified!")

    win.cleanup()
    print("\nALL TEST SUITE PASSED SUCCESSFULLY!")
    sys.exit(0)

if __name__ == "__main__":
    test_all()
