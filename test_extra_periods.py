"""
test_extra_periods.py — bir sınıfa fazladan saat açmak çizelgeyi BOZMAMALI.

    python test_extra_periods.py

Şikâyet: "bir sınıfın 5. saatini açtığımda, ya da birden fazla sınıfa daha fazla
saat açtığımda yine dolduramıyor."

Sebebi şuydu: yalnız bir sınıfın açık olduğu bir saate ancak o sınıfın dersi
konabilir; gün dağıtımı ise bir öğretmene o gün fazladan saat verebiliyordu ve
beşinci saat zorunlu olarak o tek hücreye düşmek zorunda kalıyordu. Gün
çözülemiyor, eksiksiz çözüm hiç bulunamıyor, çizelge sezgisel sonuca — yani
boşluklara — düşüyordu. Üç düzeltme yapıldı:

  * SAAT PENCERESİ  — sınıf günün ilk "pay" kadar saatini kullanır, fazlası
                      günün sonunda boş kalır (sınıf erken çıkar, ortada boşluk olmaz)
  * EN İYİ HAL      — tavlama, bulduğu en iyi gün dağıtımını saklayıp ona döner
  * ONARIM          — çözülemeyen günden blok taşınır, taşınamıyorsa takas edilir

Buradaki testler bunların hepsini birden kilitler.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collections import defaultdict  # noqa: E402

from PySide6.QtCore import QCoreApplication  # noqa: E402

import auto_scheduler  # noqa: E402
import constraint_sync  # noqa: E402

PASSED, FAILED = [], []
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
P = 8


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def timeoff(open_periods):
    return [[2 if p in open_periods else 0 for p in range(P)] for _ in DAYS]


def build(open_by_class, hours_by_class):
    """Her sınıfa 4 ders, 4 öğretmen; öğretmenler tam müsait."""
    subjects = ["Matematik", "Fizik", "Kimya", "Biyoloji", "Tarih"]
    teachers = ["Ahmet Yılmaz", "Ayşe Demir", "Mehmet Kaya", "Zeynep Ak", "Ali Su"]
    store = {
        "settings": {"days": DAYS, "days_count": 5, "periods": P},
        "siniflar": [{"ad": c, "timeoff": timeoff(op)}
                     for c, op in open_by_class.items()],
        "ogretmenler": [{"ad": t, "timeoff": timeoff(set(range(P)))} for t in teachers],
        "dersler": [{"ad": s} for s in subjects],
        "derslikler": [],
        "atamalar": [],
        "kisitlamalar": {},
        "grid_placements": [],
    }
    # Her sınıfın saatini 5 derse böl: her ders bir öğretmene ait.
    for cls, total in hours_by_class.items():
        base, rem = divmod(total, len(subjects))
        for i, (s, t) in enumerate(zip(subjects, teachers)):
            hours = base + (1 if i < rem else 0)
            if hours <= 0:
                continue
            parts, left = [], hours
            while left > 0:
                parts.append(min(2, left))
                left -= min(2, left)
            store["atamalar"].append({
                "class": cls, "subject": s, "teacher": t,
                "duration": hours, "type": "+".join(str(x) for x in parts)})
    return store


def schedule(store, label):
    res = {}
    w = auto_scheduler.AutoSchedulerWorker(store, fill_empty=True, institution_slug=None)
    w.finished_successfully.connect(lambda r: res.update(r))
    w.failed.connect(lambda m: res.update({"error": m}))
    w.run()
    placed = res.get("placed_real_hours", 0)
    demand = sum(int(a["duration"]) for a in store["atamalar"])
    print(f"    {label}: {placed}/{demand} ders saati yerleşti")
    return res, placed, demand


def gaps_in_days(res, store):
    """Sınıf günlerinde ORTADA kalan boş saat sayısı."""
    closed = {}
    for c in store["siniflar"]:
        m = constraint_sync.get_matrix(c, c["ad"], store)
        closed[c["ad"]] = {(d, p) for d in range(5) for p in range(P) if m[d][p] != 2}
    used = defaultdict(set)
    for pl in res.get("placements") or []:
        cls = pl.get("class_name") or pl.get("class")
        d = int(pl.get("day", 0))
        p0 = int(pl.get("period", 0))
        for off in range(int(pl.get("duration", 1))):
            used[(cls, d)].add(p0 + off)
    total = 0
    for (cls, d), slots in used.items():
        if not slots:
            continue
        for p in range(min(slots), max(slots)):
            if p not in slots and (d, p) not in closed[cls]:
                total += 1
    return total


def run():
    QCoreApplication.instance() or QCoreApplication(sys.argv)
    classes = ["9A", "9B", "9C"]

    print("\n[1] herkes 4 saat açık, 20'şer saat ders — tam dolmalı")
    store = build({c: {0, 1, 2, 3} for c in classes}, {c: 20 for c in classes})
    res, placed, demand = schedule(store, "temel")
    check("bütün dersler yerleşti", placed == demand, f"{placed}/{demand}")

    print("\n[2] 9A'ya 5. saat açıldı, ders EKLENMEDİ")
    store2 = build({"9A": {0, 1, 2, 3, 4}, "9B": {0, 1, 2, 3}, "9C": {0, 1, 2, 3}},
                   {c: 20 for c in classes})
    res2, placed2, demand2 = schedule(store2, "9A +1 saat")
    check("fazladan saat açmak yerleşimi bozmadı", placed2 == demand2,
          f"{placed2}/{demand2}")
    check("boş saat sınıf gününün ORTASINDA değil", gaps_in_days(res2, store2) == 0,
          f"{gaps_in_days(res2, store2)} boşluk")

    print("\n[3] 9A'ya 5. saat açıldı ve 5 saat ders EKLENDİ — grid tamamen dolmalı")
    store3 = build({"9A": {0, 1, 2, 3, 4}, "9B": {0, 1, 2, 3}, "9C": {0, 1, 2, 3}},
                   {"9A": 25, "9B": 20, "9C": 20})
    res3, placed3, demand3 = schedule(store3, "9A 25 saat")
    check("bütün dersler yerleşti", placed3 == demand3, f"{placed3}/{demand3}")
    per_class = defaultdict(int)
    for pl in res3.get("placements") or []:
        per_class[pl.get("class_name") or pl.get("class")] += int(pl.get("duration", 1))
    check("9A'nın 25 saati tamamen doldu", per_class.get("9A") == 25, str(dict(per_class)))

    print("\n[4] üç sınıfa da 6 saat açıldı, ders eklenmedi")
    store4 = build({c: {0, 1, 2, 3, 4, 5} for c in classes}, {c: 20 for c in classes})
    res4, placed4, demand4 = schedule(store4, "hepsine +2 saat")
    check("bütün dersler yerleşti", placed4 == demand4, f"{placed4}/{demand4}")
    check("boş saatler günün sonunda", gaps_in_days(res4, store4) == 0,
          f"{gaps_in_days(res4, store4)} boşluk")

    print("\n[5] sınıflar farklı saatlerde açık (karışık kurulum)")
    store5 = build({"9A": {0, 1, 2, 3, 4}, "9B": {0, 1, 2, 3, 4, 5}, "9C": {0, 1, 2}},
                   {"9A": 20, "9B": 22, "9C": 15})
    res5, placed5, demand5 = schedule(store5, "karışık")
    check("bütün dersler yerleşti", placed5 == demand5, f"{placed5}/{demand5}")

    print("\n[6] kapalı saate ders konmadı")
    bad = 0
    for st, rs in ((store2, res2), (store3, res3), (store4, res4), (store5, res5)):
        closed = {}
        for c in st["siniflar"]:
            m = constraint_sync.get_matrix(c, c["ad"], st)
            closed[c["ad"]] = {(d, p) for d in range(5) for p in range(P) if m[d][p] != 2}
        for pl in rs.get("placements") or []:
            cls = pl.get("class_name") or pl.get("class")
            d, p0 = int(pl.get("day", 0)), int(pl.get("period", 0))
            for off in range(int(pl.get("duration", 1))):
                if (d, p0 + off) in closed[cls]:
                    bad += 1
    check("kapalı saatlerde ders yok", bad == 0, f"{bad} ihlal")

    print("\n[7] öğretmen çakışması yok")
    clashes = 0
    for rs in (res2, res3, res4, res5):
        busy = defaultdict(set)
        for pl in rs.get("placements") or []:
            t = pl.get("teacher_name") or pl.get("teacher")
            d, p0 = int(pl.get("day", 0)), int(pl.get("period", 0))
            for off in range(int(pl.get("duration", 1))):
                if (d, p0 + off) in busy[t]:
                    clashes += 1
                busy[t].add((d, p0 + off))
    check("aynı öğretmen aynı saatte tek yerde", clashes == 0, f"{clashes} çakışma")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # pragma: no cover
        import traceback
        traceback.print_exc()
        FAILED.append(("beklenmeyen hata", str(exc)))

    print("\n" + "=" * 60)
    print(f"geçen: {len(PASSED)}   kalan: {len(FAILED)}")
    for name, detail in FAILED:
        print(f"  - {name} {detail}")
    print("=" * 60)
    sys.exit(1 if FAILED else 0)
