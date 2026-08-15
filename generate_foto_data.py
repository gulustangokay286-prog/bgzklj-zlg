import json
import uuid

# Mappings from transcript
assignments_raw = [
    ("9A", "Matematik 1", "HÜSEYİN BİLİR", 5),
    ("10A", "Matematik 1", "SULTAN YILMAZ", 5),
    ("11A (say)", "Matematik 1", "YASEMİN ÖZKAYA", 3),
    ("11C (ea)", "Matematik 1", "YASEMİN ÖZKAYA", 4),
    ("11E (ea)", "Matematik 1", "SULTAN YILMAZ", 4),
    ("11D (dil)", "Matematik 1", "SULTAN YILMAZ", 4),
    ("12 A(say)", "Matematik 1", "SULTAN YILMAZ", 3),
    ("12 B(say)", "Matematik 1", "SULTAN YILMAZ", 3),
    ("12 C(ea)", "Matematik 1", "SULTAN YILMAZ", 3),
    ("12 E(ea)", "Matematik 1", "SULTAN YILMAZ", 3),

    ("11A (say)", "Matematik 2", "SULTAN YILMAZ", 4),
    ("11C (ea)", "Matematik 2", "SULTAN YILMAZ", 3),
    ("11E (ea)", "Matematik 2", "SULTAN YILMAZ", 3),
    ("12 A(say)", "Matematik 2", "HÜSEYİN ARMAN", 4),
    ("12 B(say)", "Matematik 2", "HÜSEYİN ARMAN", 4),
    ("12 C(ea)", "Matematik 2", "ERMAN GÜRBÜZ", 4),
    ("12 E(ea)", "Matematik 2", "ERMAN GÜRBÜZ", 4),

    ("10A", "Geometri", "HÜSEYİN BİLİR", 2),
    ("11A (say)", "Geometri", "YASEMİN ÖZKAYA", 3),
    ("11C (ea)", "Geometri", "YASEMİN ÖZKAYA", 4),
    ("11E (ea)", "Geometri", "YASEMİN ÖZKAYA", 4),
    ("11D (dil)", "Geometri", "YASEMİN ÖZKAYA", 4),
    ("12 A(say)", "Geometri", "MUSTAFA YALÇIN", 3),
    ("12 B(say)", "Geometri", "MUSTAFA YALÇIN", 3),
    ("12 C(ea)", "Geometri", "MUSTAFA YALÇIN", 2),
    ("12 E(ea)", "Geometri", "MUSTAFA YALÇIN", 2),

    ("9A", "Türkçe", "ŞEYMA AKER", 4),
    ("10A", "Türkçe", "ŞEYMA AKER", 4),
    ("11A (say)", "Türkçe", "ŞEYMA AKER", 3),
    ("11C (ea)", "Türkçe", "ŞEYMA AKER", 4),
    ("11E (ea)", "Türkçe", "ŞEYMA AKER", 4),
    ("11D (dil)", "Türkçe", "MEHMET OĞUZ", 4),
    ("12 A(say)", "Türkçe", "ŞEYMA AKER", 1),
    ("12 B(say)", "Türkçe", "ŞEYMA AKER", 1),
    ("12 C(ea)", "Türkçe", "ŞEYMA AKER", 3),
    ("12 E(ea)", "Türkçe", "ŞEYMA AKER", 3),

    ("9A", "Edebiyat", "MEHMET OĞUZ", 2),
    ("10A", "Edebiyat", "MEHMET OĞUZ", 1),
    ("11C (ea)", "Edebiyat", "MEHMET OĞUZ", 5),
    ("11E (ea)", "Edebiyat", "MEHMET OĞUZ", 5),
    ("12 C(ea)", "Edebiyat", "MEHMET OĞUZ", 3),
    ("12 E(ea)", "Edebiyat", "MEHMET OĞUZ", 3),

    ("9A", "Fizik 1", "YAMAN ÖZTÜRK", 4),
    ("10A", "Fizik 1", "YAMAN ÖZTÜRK", 4),
    ("11A (say)", "Fizik 1", "YAMAN ÖZTÜRK", 2),
    ("11D (dil)", "Fizik 1", "YAMAN ÖZTÜRK", 3),
    ("12 A(say)", "Fizik 1", "SELİM KURTARAN", 2),
    ("12 B(say)", "Fizik 1", "SELİM KURTARAN", 2),

    ("11A (say)", "Fizik 2", "SELİM KURTARAN", 3),
    ("12 A(say)", "Fizik 2", "SELİM KURTARAN", 2),
    ("12 B(say)", "Fizik 2", "SELİM KURTARAN", 2),

    ("9A", "Kimya 1", "FATİH ÖZBİÇAKÇI", 4),
    ("10A", "Kimya 1", "FATİH ÖZBİÇAKÇI", 3),
    ("11A (say)", "Kimya 1", "FATİH ÖZBİÇAKÇI", 2),
    ("11D (dil)", "Kimya 1", "FATİH ÖZBİÇAKÇI", 2),
    ("12 A(say)", "Kimya 1", "NEZAKET ÇELİK", 2),
    ("12 B(say)", "Kimya 1", "NEZAKET ÇELİK", 2),

    ("11A (say)", "Kimya 2", "NEZAKET ÇELİK", 3),
    ("12 A(say)", "Kimya 2", "NEZAKET ÇELİK", 2),
    ("12 B(say)", "Kimya 2", "NEZAKET ÇELİK", 2),

    ("9A", "Biyoloji 1", "BEYZA BULUT", 4),
    ("10A", "Biyoloji 1", "BEYZA BULUT", 4),
    ("11A (say)", "Biyoloji 1", "BEYZA BULUT", 3),
    ("11D (dil)", "Biyoloji 1", "BEYZA BULUT", 3),
    ("12 A(say)", "Biyoloji 1", "H.BARIŞ KARATAŞ", 2),
    ("12 B(say)", "Biyoloji 1", "H.BARIŞ KARATAŞ", 2),

    ("11A (say)", "Biyoloji 2", "H.BARIŞ KARATAŞ", 3),
    ("12 A(say)", "Biyoloji 2", "H.BARIŞ KARATAŞ", 2),
    ("12 B(say)", "Biyoloji 2", "H.BARIŞ KARATAŞ", 2),

    ("9A", "Tarih", "MUHARREM YAVUZ", 2),
    ("10A", "Tarih", "MUHARREM YAVUZ", 2),
    ("11A (say)", "Tarih", "MUHARREM YAVUZ", 1),
    ("11C (ea)", "Tarih", "MUHARREM YAVUZ", 5),
    ("11E (ea)", "Tarih", "MUHARREM YAVUZ", 5),
    ("11D (dil)", "Tarih", "MUHARREM YAVUZ", 3),
    ("12 A(say)", "Tarih", "MUHARREM YAVUZ", 1),
    ("12 B(say)", "Tarih", "MUHARREM YAVUZ", 1),
    ("12 C(ea)", "Tarih", "MUHARREM YAVUZ", 5),
    ("12 E(ea)", "Tarih", "MUHARREM YAVUZ", 5),

    ("9A", "Coğrafya", "NİYAZİ KAYA", 2),
    ("10A", "Coğrafya", "NİYAZİ KAYA", 2),
    ("11A (say)", "Coğrafya", "NİYAZİ KAYA", 1),
    ("11C (ea)", "Coğrafya", "NİYAZİ KAYA", 5),
    ("11E (ea)", "Coğrafya", "NİYAZİ KAYA", 5),
    ("11D (dil)", "Coğrafya", "NİYAZİ KAYA", 3),
    ("12 A(say)", "Coğrafya", "NİYAZİ KAYA", 1),
    ("12 B(say)", "Coğrafya", "NİYAZİ KAYA", 1),
    ("12 C(ea)", "Coğrafya", "NİYAZİ KAYA", 5),
    ("12 E(ea)", "Coğrafya", "NİYAZİ KAYA", 5),

    ("9A", "Görsel Sanatlar", "SEÇİL ÖZKAN", 2),
    ("10A", "Görsel Sanatlar", "SEÇİL ÖZKAN", 2),

    ("9A", "Beden Eğitimi", "Atanmadı", 2),
    ("10A", "Beden Eğitimi", "Atanmadı", 2),
    ("11A (say)", "Beden Eğitimi", "Atanmadı", 2),
    ("11C (ea)", "Beden Eğitimi", "Atanmadı", 2),
    ("11E (ea)", "Beden Eğitimi", "Atanmadı", 2),
    ("11D (dil)", "Beden Eğitimi", "Atanmadı", 2),

    ("9A", "Din Kültürü", "Atanmadı", 1),
    ("10A", "Din Kültürü", "Atanmadı", 1),
    ("11A (say)", "Din Kültürü", "Atanmadı", 1),
    ("11C (ea)", "Din Kültürü", "Atanmadı", 1),
    ("11E (ea)", "Din Kültürü", "Atanmadı", 1),
    ("11D (dil)", "Din Kültürü", "Atanmadı", 1),

    ("11C (ea)", "Felsefe", "Atanmadı", 2),
    ("11E (ea)", "Felsefe", "Atanmadı", 2),

    ("9A", "İngilizce", "Atanmadı", 7),
    ("10A", "İngilizce", "Atanmadı", 7),
    ("11D (dil)", "İngilizce", "Atanmadı", 6),

    ("9A", "Rehberlik", "Atanmadı", 1),
    ("10A", "Rehberlik", "Atanmadı", 1)
]

data = {
    "siniflar": [],
    "ogretmenler": [],
    "dersler": [],
    "atamalar": [],
    "grid_placements": [],
    "planlama_iliskileri": [
        {
            "aktif": True,
            "kural": "Günde maksimum ders sayısı",
            "dersler": [],
            "ogretmenler": [],
            "siniflar": [],
            "parametre": 2,
            "period_start": None,
            "period_end": None,
            "onem": "Sıkı (Kesinlikle uygulanmalı)"
        }
    ],
    "settings": {
        "periods": 8,
        "school_name": "Chenki Akademi",
        "academic_year": "2023-2024",
        "manager_name": "Kurucu"
    }
}

classes_set = set()
teachers_set = set()
subjects_set = set()

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from dialogs.edit_forms import _auto_short_code

for c, s, t, h in assignments_raw:
    classes_set.add(c)
    if t != "Atanmadı":
        teachers_set.add(t)
    subjects_set.add(s)
    
    # 2 hours max per block unless it's 1 hour
    block_sizes = []
    if h == 1:
        block_sizes = [1]
    elif h == 2:
        block_sizes = [2]
    elif h == 3:
        block_sizes = [2, 1]
    elif h == 4:
        block_sizes = [2, 2]
    elif h == 5:
        block_sizes = [2, 2, 1]
    elif h == 6:
        block_sizes = [2, 2, 2]
    elif h == 7:
        block_sizes = [2, 2, 2, 1]
        
    for idx, b in enumerate(block_sizes):
        data["atamalar"].append({
            "id": str(uuid.uuid4()),
            "class": c,
            "subject": s,
            "teacher": t,
            "hours": b,
            "assigned_color": "#0097A7"
        })

colors = ["#F44336", "#E91E63", "#9C27B0", "#673AB7", "#3F51B5", "#2196F3", "#03A9F4", "#00BCD4", "#009688", "#4CAF50", "#8BC34A", "#CDDC39", "#FFEB3B", "#FFC107", "#FF9800", "#FF5722"]
c_idx = 0

for s in subjects_set:
    color = colors[c_idx % len(colors)]
    c_idx += 1
    data["dersler"].append({
        "ad": s,
        "kisa": _auto_short_code(s),
        "renk": color,
        "color": color
    })

for c in classes_set:
    data["siniflar"].append({"ad": c})
    
for t in teachers_set:
    data["ogretmenler"].append({"ad": t})

with open("otomatik_olusturulan_cizelge.roz", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("otomatik_olusturulan_cizelge.roz created successfully.")
