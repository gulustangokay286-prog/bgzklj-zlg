"""bind_locks düzeltmesinin birim testi.

Senaryo:
  1. Bir kart duration=2 olarak üretildi.
  2. Motor onu bölüp iki 1-saatlik parça (is_split=True) olarak yerleştirdi.
  3. Kullanıcı satırı kilitledi → her parçaya locked=True.
  4. Çizelge sıfırlandı (sadece kilitliler kaldı).
  5. Oto planlayıcı tekrar çalıştırıldı → bind_locks eski kodu ValueError atardı.
     Yeni kod kilitli parçaları tanıyıp parent kartı kilitlemeli.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from scheduler.model import Card, World, norm_key, norm_class

def make_world():
    """Basit bir dünya: 5 gün, 8 saat, 1 sınıf, 1 öğretmen, 1 ders."""
    D, P = 5, 8
    cards = [
        Card(cid=0, classes=(0,), subject=0, teacher=0, duration=2,
             origin=0, group=0, subject_name="Matematik",
             teacher_name="Ali Bey", class_names=("9A",)),
        Card(cid=1, classes=(0,), subject=0, teacher=0, duration=2,
             origin=0, group=0, subject_name="Matematik",
             teacher_name="Ali Bey", class_names=("9A",)),
        Card(cid=2, classes=(0,), subject=1, teacher=1, duration=1,
             origin=1, group=1, subject_name="Fizik",
             teacher_name="Veli Bey", class_names=("9A",)),
    ]
    w = World(
        D=D, P=P,
        classes=["9A"],
        teachers=["Ali Bey", "Veli Bey"],
        subjects=["Matematik", "Fizik"],
        cards=cards,
        class_closed=[0], teacher_closed=[0, 0],
        class_avoid=[0], teacher_avoid=[0, 0],
        class_capacity=[40], class_demand=[5],
        families=["Matematik", "Fizik"],
        subject_family=[0, 1],
    )
    return w

def test_split_pieces_are_matched():
    """Bölünmüş parçalar (is_split=True) parent karta eşleşmeli."""
    from scheduler.engine import bind_locks

    w = make_world()
    # Simule: motor card 0'ı bölmüş, gün 0 saat 2 ve gün 1 saat 3'e koymuş
    placements = [
        {"class_name": "9A", "subject_name": "Matematik", "teacher_name": "Ali Bey",
         "day": 0, "period": 2, "duration": 1, "locked": True,
         "is_split": True, "block_id": "c0b0", "card_id": 0},
        {"class_name": "9A", "subject_name": "Matematik", "teacher_name": "Ali Bey",
         "day": 1, "period": 3, "duration": 1, "locked": True,
         "is_split": True, "block_id": "c0b1", "card_id": 0},
    ]
    warnings = bind_locks(w, placements)
    # Card 0 should be locked at the earliest piece (day=0, period=2 → idx=2)
    assert w.cards[0].locked_at == 2, f"Expected locked_at=2, got {w.cards[0].locked_at}"
    # Card 1 should NOT be locked (not in placements)
    assert w.cards[1].locked_at is None, f"Card 1 should not be locked"
    print(f"  PASS: split pieces matched, card 0 locked at idx=2")
    if warnings:
        print(f"  Warnings: {warnings}")

def test_normal_lock_exact():
    """Normal kilit (duration eşleşmesi) çalışmalı."""
    from scheduler.engine import bind_locks

    w = make_world()
    placements = [
        {"class_name": "9A", "subject_name": "Fizik", "teacher_name": "Veli Bey",
         "day": 2, "period": 5, "duration": 1, "locked": True},
    ]
    warnings = bind_locks(w, placements)
    assert w.cards[2].locked_at == 2 * 8 + 5, f"Expected locked_at=21, got {w.cards[2].locked_at}"
    print(f"  PASS: normal lock, card 2 locked at idx=21")

def test_normal_lock_duration_mismatch():
    """Duration uyumsuzluğu crash yerine uyarı vermeli."""
    from scheduler.engine import bind_locks

    w = make_world()
    # Placement says duration=3 but card has duration=2 → relaxed match
    placements = [
        {"class_name": "9A", "subject_name": "Matematik", "teacher_name": "Ali Bey",
         "day": 0, "period": 0, "duration": 3, "locked": True},
    ]
    warnings = bind_locks(w, placements)
    # Should still match card 0 via relaxed match (ignore duration)
    assert w.cards[0].locked_at == 0, f"Expected locked_at=0, got {w.cards[0].locked_at}"
    print(f"  PASS: duration mismatch handled via relaxed match")

def test_no_match_warns_not_crashes():
    """Eşleşmeyen kilit crash yerine uyarı döndürmeli."""
    from scheduler.engine import bind_locks

    w = make_world()
    placements = [
        {"class_name": "10B", "subject_name": "Kimya", "teacher_name": "Yok",
         "day": 0, "period": 0, "duration": 1, "locked": True},
    ]
    warnings = bind_locks(w, placements)
    assert len(warnings) == 1, f"Expected 1 warning, got {len(warnings)}"
    assert "eşleşemedi" in warnings[0]
    print(f"  PASS: unmatched lock produces warning, not crash")

if __name__ == "__main__":
    print("bind_locks testi başlıyor...")
    test_split_pieces_are_matched()
    test_normal_lock_exact()
    test_normal_lock_duration_mismatch()
    test_no_match_warns_not_crashes()
    print("\nTum testler gecti!")
