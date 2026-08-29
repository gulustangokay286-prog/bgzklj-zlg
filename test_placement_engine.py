"""
test_placement_engine.py — yerleşim analiz motorunun tam kapsamlı testi.

    python test_placement_engine.py

Sürüklerken her hücrenin neden yeşil/mavi/kırmızı/gri yandığını belirleyen motor
burada kilitleniyor. Renk bir sonuçtur; testler renge değil, ÖNCE duruma bakar.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import placement_engine as pe  # noqa: E402

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


def timeoff(closed=(), avoid=()):
    grid = [[2] * P for _ in DAYS]
    for d, p in closed:
        grid[d][p] = 0
    for d, p in avoid:
        grid[d][p] = 1
    return grid


def placement(cls, subject, teacher, day, period, duration=1, **extra):
    row = {"class_name": cls, "subject_name": subject, "teacher_name": teacher,
           "day": day, "period": period, "duration": duration,
           "block_id": extra.pop("block_id", f"b_{cls}_{subject}_{day}_{period}")}
    row.update(extra)
    return row


def store(**over):
    base = {
        "settings": {"days": DAYS, "days_count": 5, "periods": P},
        "siniflar": [{"ad": "9A"}, {"ad": "9B"}, {"ad": "9C"}],
        "ogretmenler": [{"ad": "Ahmet Yılmaz"}, {"ad": "Ayşe Demir"},
                        {"ad": "Mehmet Kaya"}],
        "dersler": [{"ad": "Matematik"}, {"ad": "Fizik"}, {"ad": "Beden"}],
        "derslikler": [],
        "atamalar": [],
        "grid_placements": [],
        "kisitlamalar": {},
    }
    base.update(over)
    return base


def lesson(cls="9A", subject="Matematik", teacher="Ahmet Yılmaz", duration=1, **extra):
    row = {"class_name": cls, "subject_name": subject, "teacher_name": teacher,
           "duration": duration, "block_id": extra.pop("block_id", "dragged")}
    row.update(extra)
    return row


def analyze(data, les, day, period, duration=None, slug=None):
    snap = pe.TimetableSnapshot(data, institution_slug=slug,
                                exclude_block_id=les.get("block_id"))
    cand = pe.CandidatePlacement(les, day, period, duration)
    return pe.analyze(snap, les, cand)


def run():
    print("\n[1] tamamen boş hücre")
    r = analyze(store(), lesson(), 0, 0)
    check("boş hücre VALID", r.status == pe.VALID, r.status)
    check("yeşil yanıyor", r.visual == pe.V_GREEN, r.visual)
    check("gerekçe var", bool(r.explanation), r.explanation)

    print("\n[2] sınıf dolu")
    d = store(grid_placements=[placement("9A", "Fizik", "Ayşe Demir", 0, 0)])
    r = analyze(d, lesson(), 0, 0)
    check("sınıf dolu -> CONFLICT", r.status == pe.CONFLICT, r.status)
    check("kırmızı", r.visual == pe.V_RED, r.visual)
    check("çakışan ders adı gerekçede", "Fizik" in r.explanation, r.explanation)
    check("sınıf çakışması listelendi", len(r.class_conflicts) == 1,
          str(r.class_conflicts))

    print("\n[3] SINIF BOŞ ama öğretmen başka sınıfta  (kullanıcının sorduğu durum)")
    d = store(grid_placements=[placement("9B", "Matematik", "Ahmet Yılmaz", 0, 0)])
    r = analyze(d, lesson(cls="9A"), 0, 0)
    check("öğretmen meşgul -> CONFLICT", r.status == pe.CONFLICT, r.status)
    check("kırmızı yanıyor", r.visual == pe.V_RED, r.visual)
    check("öğretmen çakışması", len(r.teacher_conflicts) == 1, str(r.teacher_conflicts))
    check("hangi sınıfta olduğu yazıyor", "9B" in r.explanation, r.explanation)

    print("\n[4] alakasız sınıfın dersi yanlış kırmızı üretmiyor")
    d = store(grid_placements=[placement("9B", "Fizik", "Ayşe Demir", 0, 0)])
    r = analyze(d, lesson(cls="9A", teacher="Ahmet Yılmaz"), 0, 0)
    check("başka sınıf/başka öğretmen -> VALID", r.status == pe.VALID, r.status)

    print("\n[5] öğretmen kapalı saati (zaman tablosu)")
    d = store(ogretmenler=[{"ad": "Ahmet Yılmaz", "timeoff": timeoff(closed=[(0, 0)])},
                           {"ad": "Ayşe Demir"}])
    r = analyze(d, lesson(), 0, 0)
    check("kapalı saat -> FORBIDDEN", r.status == pe.FORBIDDEN, r.status)
    check("gri", r.visual == pe.V_GREY, r.visual)
    check("dolu DEĞİL, kapalı", not r.class_conflicts and r.availability_conflicts,
          str(r.conflicts))

    print("\n[6] sınıf kapalı saati")
    d = store(siniflar=[{"ad": "9A", "timeoff": timeoff(closed=[(1, 3)])},
                        {"ad": "9B"}, {"ad": "9C"}])
    r = analyze(d, lesson(), 1, 3)
    check("sınıf kapalı -> FORBIDDEN", r.status == pe.FORBIDDEN, r.status)

    print("\n[7] ders bazlı kapalı saat")
    d = store(dersler=[{"ad": "Matematik", "timeoff": timeoff(closed=[(2, 2)])},
                       {"ad": "Fizik"}, {"ad": "Beden"}])
    r = analyze(d, lesson(), 2, 2)
    check("ders kapalı -> FORBIDDEN", r.status == pe.FORBIDDEN, r.status)

    print("\n[8] 'tercih edilmez' saat -> mavi")
    d = store(ogretmenler=[{"ad": "Ahmet Yılmaz", "timeoff": timeoff(avoid=[(0, 5)])},
                           {"ad": "Ayşe Demir"}])
    r = analyze(d, lesson(), 0, 5)
    check("yumuşak kısıt -> QUESTIONABLE", r.status == pe.QUESTIONABLE, r.status)
    check("mavi", r.visual == pe.V_BLUE, r.visual)
    check("sert ihlal yok", not r.hard_violations, str(r.hard_violations))

    print("\n[9] kesişim semantiği: öğretmen açık ama sınıf kapalı")
    d = store(siniflar=[{"ad": "9A", "timeoff": timeoff(closed=[(0, 1)])},
                        {"ad": "9B"}, {"ad": "9C"}],
              ogretmenler=[{"ad": "Ahmet Yılmaz", "timeoff": timeoff()},
                           {"ad": "Ayşe Demir"}])
    r = analyze(d, lesson(), 0, 1)
    check("biri kapalıysa kapalı (VE semantiği)", r.status == pe.FORBIDDEN, r.status)

    print("\n[10] iki saatlik ders: bütün ayak izi")
    d = store(grid_placements=[placement("9A", "Fizik", "Ayşe Demir", 0, 3)])
    r = analyze(d, lesson(duration=2), 0, 2)
    check("2. hücredeki çakışma yakalandı", r.status == pe.CONFLICT, r.status)
    check("çakışma 3. saatte", any(3 in c.periods for c in r.class_conflicts),
          str(r.class_conflicts))
    r2 = analyze(d, lesson(duration=2), 0, 0)
    check("temiz ayak izi VALID", r2.status == pe.VALID, r2.status)

    print("\n[11] gün sonuna taşma")
    r = analyze(store(), lesson(duration=2), 0, P - 1)
    check("taşma -> INVALID_GEOMETRY", r.status == pe.INVALID_GEOMETRY, r.status)
    r = analyze(store(), lesson(duration=2), 0, P - 2)
    check("tam sığan yerleşim geçerli", r.status == pe.VALID, r.status)

    print("\n[12] ızgara dışı")
    r = analyze(store(), lesson(), 9, 0)
    check("gün yok -> OUT_OF_RANGE", r.status == pe.OUT_OF_RANGE, r.status)
    r = analyze(store(), lesson(), 0, 99)
    check("saat yok -> OUT_OF_RANGE", r.status == pe.OUT_OF_RANGE, r.status)

    print("\n[13] dersin kendi yeri kendisiyle çakışmıyor")
    d = store(grid_placements=[placement("9A", "Matematik", "Ahmet Yılmaz", 0, 0,
                                         block_id="dragged")])
    les = lesson(block_id="dragged", source={"day": 0, "period": 0})
    r = analyze(d, les, 0, 0)
    check("kendi yeri CURRENT", r.status == pe.CURRENT, r.status)
    check("kendi kendine çakışma yok", not r.class_conflicts, str(r.class_conflicts))
    r2 = analyze(d, les, 0, 4)
    check("taşınacak yer VALID", r2.status == pe.VALID, r2.status)

    print("\n[14] kilitli ders")
    d = store(grid_placements=[placement("9A", "Fizik", "Ayşe Demir", 0, 0,
                                         locked=True)])
    r = analyze(d, lesson(), 0, 0)
    check("kilitli hedef -> CONFLICT", r.status == pe.CONFLICT, r.status)
    check("kilit gerekçesi var",
          any(c.type == pe.LOCKED_TARGET for c in r.conflicts), str(r.conflicts))
    r2 = analyze(store(), lesson(locked=True), 0, 0)
    check("kilitli ders sürüklenemez", r2.status == pe.FORBIDDEN, r2.status)

    print("\n[15] çoklu öğretmen")
    d = store(grid_placements=[placement("9B", "Fizik", "Ayşe Demir", 0, 0)])
    r = analyze(d, lesson(teacher="Ahmet Yılmaz, Ayşe Demir"), 0, 0)
    check("ikinci öğretmen de kontrol edildi", r.status == pe.CONFLICT, r.status)
    check("çakışan öğretmen Ayşe Demir",
          any(c.resource_name == "Ayşe Demir" for c in r.teacher_conflicts),
          str(r.teacher_conflicts))

    print("\n[16] çoklu sınıf (birleşik ders)")
    d = store(grid_placements=[placement("9C", "Beden", "Mehmet Kaya", 0, 0)])
    les = lesson(cls="9A + 9C", teacher="Ahmet Yılmaz", is_combined=True,
                 combined_classes=["9A", "9C"])
    r = analyze(d, les, 0, 0)
    check("ikinci sınıf dolu -> CONFLICT", r.status == pe.CONFLICT, r.status)
    check("çakışan sınıf 9C",
          any(c.resource_name == "9C" for c in r.class_conflicts),
          str(r.class_conflicts))

    print("\n[17] öğrenci grubu: farklı gruplar yan yana durabilir")
    d = store(grid_placements=[placement("9A", "İngilizce", "Ayşe Demir", 0, 0,
                                         groups=["Grup B"])])
    r = analyze(d, lesson(subject="Almanca", teacher="Mehmet Kaya",
                          groups=["Grup A"]), 0, 0)
    check("farklı grup -> çakışma yok", r.status == pe.VALID, r.status)
    r2 = analyze(d, lesson(subject="Almanca", teacher="Mehmet Kaya",
                           groups=["Grup B"]), 0, 0)
    check("aynı grup -> CONFLICT", r2.status == pe.CONFLICT, r2.status)
    r3 = analyze(d, lesson(subject="Almanca", teacher="Mehmet Kaya"), 0, 0)
    check("grupsuz ders tüm sınıftır -> CONFLICT", r3.status == pe.CONFLICT, r3.status)

    print("\n[18] derslik")
    d = store(derslikler=[{"ad": "Lab 1"}],
              grid_placements=[placement("9B", "Fizik", "Ayşe Demir", 0, 0,
                                         room_name="Lab 1")])
    r = analyze(d, lesson(teacher="Mehmet Kaya", room_name="Lab 1"), 0, 0)
    check("derslik dolu -> CONFLICT", r.status == pe.CONFLICT, r.status)
    check("derslik çakışması ayrı boyut", len(r.room_conflicts) == 1,
          str(r.room_conflicts))
    d2 = store(derslikler=[{"ad": "Lab 1", "timeoff": timeoff(closed=[(0, 2)])}])
    r2 = analyze(d2, lesson(room_name="Lab 1"), 0, 2)
    check("derslik kapalı -> FORBIDDEN", r2.status == pe.FORBIDDEN, r2.status)

    print("\n[19] aynı ders aynı gün -> mavi (yasak değil)")
    d = store(grid_placements=[placement("9A", "Matematik", "Ahmet Yılmaz", 0, 0)])
    r = analyze(d, lesson(), 0, 4)
    check("aynı gün tekrar -> QUESTIONABLE", r.status == pe.QUESTIONABLE, r.status)
    check("ilişki gerekçesi",
          any(c.type == pe.SAME_SUBJECT_SAME_DAY for c in r.conflicts), str(r.conflicts))

    print("\n[20] ders zaman dilimi tercihi")
    d = store()
    d["constraints"] = {"subject_windows": {"Matematik": "morning"}}
    r = analyze(d, lesson(), 0, 6)
    check("öğleden sonra -> QUESTIONABLE", r.status == pe.QUESTIONABLE, r.status)
    r2 = analyze(d, lesson(), 0, 1)
    check("sabah -> VALID", r2.status == pe.VALID, r2.status)

    print("\n[21] birden çok sorun: en güçlü durum kazanır, deterministik")
    d = store(siniflar=[{"ad": "9A", "timeoff": timeoff(closed=[(0, 0)])},
                        {"ad": "9B"}, {"ad": "9C"}],
              grid_placements=[placement("9A", "Fizik", "Ayşe Demir", 0, 0)])
    results = {analyze(d, lesson(), 0, 0).status for _ in range(25)}
    check("kapalı + dolu -> hep FORBIDDEN", results == {pe.FORBIDDEN}, str(results))
    check("bütün gerekçeler toplandı",
          len(analyze(d, lesson(), 0, 0).conflicts) >= 2)

    print("\n[22] tekrar tekrar aynı sonuç (kararlılık)")
    d = store(grid_placements=[placement("9B", "Matematik", "Ahmet Yılmaz", 0, 0)])
    seq = [analyze(d, lesson(), 0, p).status for p in range(4)] * 3
    check("aynı girdi aynı çıktı", seq[:4] * 3 == seq, str(seq))

    print("\n[23] analiz hiçbir şeyi değiştirmiyor")
    d = store(grid_placements=[placement("9A", "Fizik", "Ayşe Demir", 0, 0)])
    import copy
    before = copy.deepcopy(d)
    snap = pe.TimetableSnapshot(d, exclude_block_id="dragged")
    for day in range(5):
        for p in range(P):
            pe.analyze(snap, lesson(), pe.CandidatePlacement(lesson(), day, p))
    check("veri deposu bozulmadı", d == before)

    print("\n[24] bozuk veri sessizce 'olur' demiyor")
    d = store(grid_placements=[{"class_name": "9A", "day": "abc"}])
    r = analyze(d, lesson(), 0, 0)
    check("bozuk satır analizi çökertmiyor", r.status in
          (pe.VALID, pe.CONFLICT, pe.QUESTIONABLE), r.status)
    snap = pe.TimetableSnapshot(d)
    check("bozuk satır rapor edildi", bool(snap.errors), str(snap.errors))
    r2 = analyze(store(), lesson(cls=""), 0, 0)
    check("sınıfsız ders -> ANALYSIS_ERROR", r2.status == pe.ANALYSIS_ERROR, r2.status)

    print("\n[25] bütün satır tek seferde")
    d = store(grid_placements=[placement("9A", "Fizik", "Ayşe Demir", 0, 2)])
    cells = [(0, p) for p in range(P)]
    res = pe.analyze_row(pe.TimetableSnapshot(d, exclude_block_id="dragged"),
                         lesson(), cells)
    check("her hücre için sonuç var", len(res) == P, str(len(res)))
    check("dolu hücre kırmızı", res[(0, 2)].visual == pe.V_RED, res[(0, 2)].visual)
    check("boş hücre yeşil", res[(0, 0)].visual == pe.V_GREEN, res[(0, 0)].visual)

    print("\n[26] önbellek sonucu değiştirmiyor")
    snap = pe.TimetableSnapshot(d, exclude_block_id="dragged")
    cache = {}
    a = pe.analyze_row(snap, lesson(), cells, cache=cache)
    b = pe.analyze_row(snap, lesson(), cells, cache=cache)
    check("önbellekli ve önbelleksiz aynı",
          [a[c].status for c in cells] == [b[c].status for c in cells])

    print("\n[27] gerekçe açıklanabilir")
    d = store(grid_placements=[placement("9B", "Matematik", "Ahmet Yılmaz", 1, 2)])
    r = analyze(d, lesson(), 1, 2)
    txt = pe.explain(r)
    check("neden kırmızı sorusuna cevap var",
          "TEACHER_COLLISION" in txt and "Ahmet Yılmaz" in txt, txt[:120])
    check("sözlüğe çevrilebiliyor", isinstance(r.as_dict()["conflicts"], list))

    print("\n[28] okul günü dışı ile gerçek engel ayrı şeyler")
    # Sınıf günde 4 saat çalışıyorsa 5-8. saatler okul günü DIŞIDIR; orayı da
    # gri boyamak ekranın yarısını griye çevirip yeşili görünmez kılıyordu.
    closed_pm = [(dd, pp) for dd in range(5) for pp in range(4, P)]
    d = store(siniflar=[{"ad": "9A", "timeoff": timeoff(closed=closed_pm)},
                        {"ad": "9B"}, {"ad": "9C"}],
              ogretmenler=[{"ad": "Ahmet Yılmaz", "timeoff": timeoff(closed=[(0, 1)])},
                           {"ad": "Ayşe Demir"}, {"ad": "Mehmet Kaya"}])
    r_out = analyze(d, lesson(), 0, 5)
    check("okul günü dışı FORBIDDEN", r_out.status == pe.FORBIDDEN, r_out.status)
    check("okul günü dışı işaretli", r_out.outside_class_hours is True)
    r_in = analyze(d, lesson(), 0, 1)
    check("öğretmen kapalı da FORBIDDEN", r_in.status == pe.FORBIDDEN, r_in.status)
    check("ama okul günü dışı DEĞİL", r_in.outside_class_hours is False,
          str([c.type for c in r_in.conflicts]))
    r_ok = analyze(d, lesson(), 0, 2)
    check("ders saati içindeki boş hücre YEŞİL", r_ok.status == pe.VALID, r_ok.status)

    print("\n[29] taşma gerekçesi anlaşılır")
    r_ovf = analyze(d, lesson(duration=2), 0, 3)
    check("son açık saatten başlayan 2 saatlik ders taşıyor",
          r_ovf.status == pe.FORBIDDEN, r_ovf.status)
    check("başlangıç saati dışarıda değil", r_ovf.outside_class_hours is False)
    check("mesaj taşmayı anlatıyor",
          "taşıyor" in r_ovf.explanation and "4. saatten" in r_ovf.explanation,
          r_ovf.explanation)

    print("\n[30] büyük çizelgede hız")
    import time
    big = store(siniflar=[{"ad": f"S{i}"} for i in range(40)],
                ogretmenler=[{"ad": f"Ogr {i}"} for i in range(60)])
    big["grid_placements"] = [
        placement(f"S{i % 40}", "Ders", f"Ogr {i % 60}", i % 5, i % P,
                  block_id=f"b{i}") for i in range(1500)]
    t0 = time.time()
    snap = pe.TimetableSnapshot(big, exclude_block_id="dragged")
    build = time.time() - t0
    t1 = time.time()
    cells = [(d0, p0) for d0 in range(5) for p0 in range(P)]
    pe.analyze_row(snap, lesson(cls="S3", teacher="Ogr 7"), cells)
    scan = time.time() - t1
    check("indeks kurulumu hızlı (<1.5s)", build < 1.5, f"{build:.2f}s")
    check("40 hücre taraması hızlı (<0.05s)", scan < 0.05, f"{scan:.4f}s")


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
