import sys
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

def test_manual_relations_sync():
    print("Testing real-time manual relations checking...")
    from main_window import MainWindow
    
    win = MainWindow()
    win.data_store = {
        "siniflar": [{"ad": "9A"}],
        "ogretmenler": [{"ad": "Ahmet Yılmaz"}],
        "dersler": [{"ad": "Matematik"}, {"ad": "Fizik"}],
        "atamalar": [],
        "planlama_iliskileri": [
            {
                "kural": "Günde maksimum ders sayısı",
                "deger": 2,
                "dersler": ["Matematik"],
                "siniflar": ["9A"],
                "aktif": True
            },
            {
                "kural": "İki ders aynı güne gelmesin",
                "dersler": ["Matematik", "Fizik"],
                "siniflar": ["9A"],
                "aktif": True
            }
        ]
    }
    
    # Check 1: Normal placement of 2 hours Matematik (should be OK)
    ok, msg = win._check_planning_relations(
        subject="Matematik", teacher="Ahmet Yılmaz", class_name="9A",
        day=0, period=0, duration=2
    )
    assert ok == True, f"Expected OK for 2h Matematik, got: {msg}"
    print("✅ Normal 2h Matematik valid!")
    
    # Place 2 hours Matematik on day 0
    win._grid.set_cell(0, 0, "Matematik", "#FF0000", "Ahmet Yılmaz", 2, class_name="9A")
    
    # Check 2: Try to place 2 MORE hours of Matematik on same day (total 4h > max 2h) -> Should fail!
    ok, msg = win._check_planning_relations(
        subject="Matematik", teacher="Ahmet Yılmaz", class_name="9A",
        day=0, period=3, duration=2
    )
    assert ok == False, "Expected violation for exceeding daily max hours"
    assert "Günde maksimum ders sayısı" in msg
    print("✅ Daily max hours violation caught in real-time!")
    
    # Check 3: Try to place Fizik on same day (Matematik + Fizik conflict) -> Should fail!
    ok, msg = win._check_planning_relations(
        subject="Fizik", teacher="Ahmet Yılmaz", class_name="9A",
        day=0, period=4, duration=2
    )
    assert ok == False, "Expected violation for conflicting subjects on same day"
    assert "İki ders aynı güne gelmesin" in msg
    print("✅ Conflicting subjects on same day caught in real-time!")
    
    # Check 4: Try to place Fizik on day 1 (different day) -> Should be OK!
    ok, msg = win._check_planning_relations(
        subject="Fizik", teacher="Ahmet Yılmaz", class_name="9A",
        day=1, period=0, duration=2
    )
    assert ok == True, f"Expected OK on day 1, got {msg}"
    if hasattr(win, "cloud_worker") and win.cloud_worker:
        win.cloud_worker.stop()
        win.cloud_worker.wait(1000)

    print("\n🎉 ALL REAL-TIME PLANNING RELATIONS TESTS PASSED!")

if __name__ == "__main__":
    test_manual_relations_sync()
