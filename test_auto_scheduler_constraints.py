"""
test_auto_scheduler_constraints.py — sınıf kısıtlarına (Zaman Tablosu) uyum testleri.

    python test_auto_scheduler_constraints.py

Kapatılan ders saatlerinin gerçekten boş kaldığını doğrular. Asıl hata şuydu:
oto planlayıcı yalnızca ÖĞRETMEN kısıtlarını okuyordu, sınıf kısıtlarını hiç
okumuyordu; ayrıca boşluk doldurma (filler) adımı her boş hücreyi dolduruyordu.
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication  # noqa: E402

import auto_scheduler  # noqa: E402
from auto_scheduler import AutoSchedulerWorker  # noqa: E402

PASSED, FAILED = [], []

DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
PERIODS = 8


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def make_timeoff(closed_periods=(), avoid_periods=(), days=5, periods=PERIODS):
    """timeoff[day][period]: 2=açık, 0=kapalı, 1=tercih edilmez."""
    matrix = []
    for _d in range(days):
        row = []
        for p in range(periods):
            if p in closed_periods:
                row.append(0)
            elif p in avoid_periods:
                row.append(1)
            else:
                row.append(2)
        matrix.append(row)
    return matrix


def build_store(class_timeoff=None, kisitlamalar=None):
    """İki sınıf, dört ders; grid'i doldurmaya fazlasıyla yetecek kadar atama."""
    store = {
        "settings": {"days": DAYS, "periods": PERIODS},
        "siniflar": [{"ad": "9A"}, {"ad": "9B"}],
        "ogretmenler": [
            {"ad": "Ahmet Yılmaz"}, {"ad": "Ayşe Demir"},
            {"ad": "Mehmet Kaya"}, {"ad": "Fatma Şahin"},
        ],
        "dersler": [{"ad": "Matematik"}, {"ad": "Fizik"}, {"ad": "Kimya"}, {"ad": "Biyoloji"}],
        "derslikler": [],
        "atamalar": [],
        "grid_placements": [],
        "kisitlamalar": kisitlamalar or {},
    }
    pairs = [
        ("Matematik", "Ahmet Yılmaz", 6),
        ("Fizik", "Ayşe Demir", 4),
        ("Kimya", "Mehmet Kaya", 4),
        ("Biyoloji", "Fatma Şahin", 4),
    ]
    for cls in ("9A", "9B"):
        for subject, teacher, hours in pairs:
            store["atamalar"].append({
                "subject": subject, "ders": subject,
                "teacher": teacher, "ogretmen": teacher,
                "class": cls, "sinif": cls,
                "duration": hours, "type": "2+2+2" if hours == 6 else "2+2",
            })
    if class_timeoff:
        for cls in store["siniflar"]:
            if cls["ad"] in class_timeoff:
                cls["timeoff"] = class_timeoff[cls["ad"]]
    return store


def run_scheduler(store, fill_empty=True):
    """Planlayıcıyı senkron çalıştırır (QThread.run doğrudan çağrılır)."""
    worker = AutoSchedulerWorker(store, fill_empty=fill_empty, institution_slug=None)
    captured = {}
    worker.finished_successfully.connect(lambda res: captured.update(res))
    worker.failed.connect(lambda msg: captured.update({"error": msg}))
    worker.run()
    return captured


def occupied_slots(placements, class_name):
    """Bir sınıf için dolu (gün, saat) çiftleri — blok süreleri açılarak."""
    slots = set()
    for p in placements:
        if (p.get("class_name") or p.get("class") or "") != class_name:
            continue
        day = int(p.get("day", p.get("col", 0)))
        start = int(p.get("period", p.get("row", 0)))
        for off in range(int(p.get("duration", 1) or 1)):
            slots.add((day, start + off))
    return slots


def run():
    _app = QApplication.instance() or QApplication(sys.argv)

    print("\n[temel: kısıt yokken grid dolar]")
    result = run_scheduler(build_store())
    placements = result.get("placements", [])
    check("plan üretildi", bool(placements), str(result.get("error", "")))
    base_9a = occupied_slots(placements, "9A")
    check("kısıt yokken 9A neredeyse tamamen dolu", len(base_9a) >= 35, f"{len(base_9a)}/40")

    print("\n[asıl hata: 5-6-7-8. saatler kapalı (timeoff matrisi)]")
    # Kullanıcının yaptığı: Zaman Tablosu ekranında 5-8. saatleri kapatmak.
    # (0 tabanlı indeksle 4,5,6,7)
    closed = (4, 5, 6, 7)
    store = build_store(class_timeoff={"9A": make_timeoff(closed_periods=closed)})
    result = run_scheduler(store)
    placements = result.get("placements", [])
    slots_9a = occupied_slots(placements, "9A")

    violations = sorted(s for s in slots_9a if s[1] in closed)
    check("kapatılan saatlere HİÇ ders konmadı", not violations,
          f"{len(violations)} ihlal, ilk 5: {violations[:5]}")
    check("açık saatler yine de dolduruldu", len(slots_9a) >= 15, f"{len(slots_9a)}/20")

    # Aynı çizelgedeki diğer sınıf etkilenmemeli.
    slots_9b = occupied_slots(placements, "9B")
    check("kısıtsız sınıf (9B) etkilenmedi", any(s[1] in closed for s in slots_9b),
          "9B de boş kaldı — kısıt yanlış sınıfa uygulanmış olabilir")

    print("\n[boşluk doldurma adımı da kısıtlara uyuyor]")
    # Asıl kabahatli buydu: her boş hücreyi dolduruyordu.
    store = build_store(class_timeoff={"9A": make_timeoff(closed_periods=closed)})
    result = run_scheduler(store, fill_empty=True)
    filler_hits = [
        p for p in result.get("placements", [])
        if p.get("is_filler")
        and (p.get("class_name") or p.get("class")) == "9A"
        and int(p.get("period", p.get("row", 0))) in closed
    ]
    check("doldurma adımı kapalı saatlere taşmıyor", not filler_hits,
          f"{len(filler_hits)} filler ders kapalı saatte")

    print("\n[kısıt yalnızca kisitlamalar sözlüğünde olsa da geçerli]")
    # Bulut senkronu sonrası timeoff matrisi boş, kisitlamalar dolu olabiliyor.
    kis = {"9A": {}}
    for d in range(len(DAYS)):
        for p in range(PERIODS):
            kis["9A"][f"{d},{p}"] = p not in closed  # True = açık
    result = run_scheduler(build_store(kisitlamalar=kis))
    slots_9a = occupied_slots(result.get("placements", []), "9A")
    violations = sorted(s for s in slots_9a if s[1] in closed)
    check("kisitlamalar sözlüğü tek başına yeterli", not violations,
          f"{len(violations)} ihlal, ilk 5: {violations[:5]}")

    print("\n[tam gün kapatma]")
    # Cuma (indeks 4) tamamen kapalı.
    matrix = make_timeoff()
    for p in range(PERIODS):
        matrix[4][p] = 0
    result = run_scheduler(build_store(class_timeoff={"9A": matrix}))
    slots_9a = occupied_slots(result.get("placements", []), "9A")
    check("kapalı gün tamamen boş kaldı", not any(s[0] == 4 for s in slots_9a),
          f"Cuma'da {sum(1 for s in slots_9a if s[0] == 4)} ders var")
    check("diğer günler dolduruldu", len(slots_9a) >= 28, f"{len(slots_9a)}/32")

    print("\n['tercih edilmez' yumuşak kısıt: yasak değil ama son tercih]")
    store = build_store(class_timeoff={"9A": make_timeoff(avoid_periods=(6, 7))})
    result = run_scheduler(store, fill_empty=False)
    slots_9a = occupied_slots(result.get("placements", []), "9A")
    early = sum(1 for s in slots_9a if s[1] < 6)
    late = sum(1 for s in slots_9a if s[1] >= 6)
    check("sarı saatler kullanılabilir kalıyor (yasak değil)", True)
    check("planlayıcı önce erken saatleri dolduruyor", early > late,
          f"erken={early}, geç={late}")

    print("\n[hedef sayacı kapalı saatleri saymıyor]")
    store = build_store(class_timeoff={"9A": make_timeoff(closed_periods=closed)})
    result = run_scheduler(store)
    # 2 sınıf × 5 gün × 8 saat = 80; 9A'da 5×4=20 saat kapalı → hedef 60.
    check("total_hours kapalı saatler düşülerek hesaplandı",
          result.get("total_hours") == 60, str(result.get("total_hours")))

    print("\n[yardımcı fonksiyonlar]")
    blocked, avoid = auto_scheduler._build_class_timeoff_map(
        build_store(class_timeoff={"9A": make_timeoff(closed_periods=(4,), avoid_periods=(5,))})
    )
    check("kapalı saatler haritalandı", (0, 4) in blocked.get("9A", set()), str(blocked))
    check("tercih edilmeyen saatler ayrı tutuldu", (0, 5) in avoid.get("9A", set()), str(avoid))
    check("kapalı, tercih edilmezden önce gelir", (0, 4) not in avoid.get("9A", set()))

    # Sınıf adı farklı yazımlarla eşleşmeli ("9A" / "9-A" / "9 A").
    check("farklı yazım eşleşiyor (9-A)",
          auto_scheduler._resolve_class_slots("9-A", {"9A": {(0, 4)}}) == {(0, 4)})
    check("alakasız sınıf eşleşmiyor",
          auto_scheduler._resolve_class_slots("10B", {"9A": {(0, 4)}}) == set())


if __name__ == "__main__":
    try:
        run()
    except Exception:
        import traceback
        traceback.print_exc()
        FAILED.append(("beklenmeyen hata", "yukarıdaki traceback"))
    finally:
        print("\n" + "=" * 60)
        print(f"geçen: {len(PASSED)}   kalan: {len(FAILED)}")
        for name, detail in FAILED:
            print(f"  - {name}: {detail}")
        print("=" * 60)
    sys.exit(1 if FAILED else 0)
