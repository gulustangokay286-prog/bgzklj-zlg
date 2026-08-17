import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from timetable_grid import get_subject_abbr
from dialogs.print_preview import get_subject_badge

test_subjects = [
    ("Geometri", "GEOM"),
    ("GEOMETRI", "GEOM"),
    ("Coğrafya", "COĞRAF"),
    ("COGRAFYA", "COĞRAF"),
    ("Matematik", "MATE"),
    ("MATEMATIK", "MATE"),
    ("Beden Eğitimi", "BEDEN"),
    ("BEDEN EGITIMI VE SPOR", "BEDEN"),
    ("Türk Dili ve Edebiyatı", "TDE"),
    ("Görsel Sanatlar", "GÖRSEL"),
    ("Din Kültürü ve Ahlak Bilgisi", "DİN"),
    ("İngilizce", "İNG"),
    ("Almanca", "ALM"),
    ("Fizik", "FİZİK"),
    ("Kimya", "KİMYA"),
    ("Biyoloji", "BİYO"),
    ("Rehberlik", "REHBER"),
    ("Felsefe", "FELS"),
    ("Geometri 2", "GEOM 2"),
    ("Matematik 1", "MATE 1"),
]

print("=== Testing get_subject_abbr ===")
for inp, expected in test_subjects:
    res = get_subject_abbr(inp)
    assert len(res) <= 6, f"Length of '{res}' exceeds 6 for input '{inp}'"
    print(f"[{inp}] -> '{res}' (len: {len(res)})")

print("\n=== Testing get_subject_badge ===")
for inp, expected in test_subjects:
    res = get_subject_badge(inp)
    assert len(res) <= 6, f"Length of '{res}' exceeds 6 for input '{inp}'"
    print(f"[{inp}] -> '{res}' (len: {len(res)})")

print("\nAll subject abbreviations tested and VERIFIED strictly <= 6 characters!")
