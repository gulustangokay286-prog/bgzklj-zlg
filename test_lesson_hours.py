"""
test_lesson_hours.py — sınıf ekranı, öğretmen ekranı ve planlayıcı aynı saati mi görüyor?

    python test_lesson_hours.py

Bu testlerin varlık sebebi: aynı atama listesi ekrandan ekrana farklı toplam
veriyordu. Sınıf ekranı `duration`, öğretmen ekranı `ders_sayisi`, istatistik
ekranı hiç yazılmayan `saat` alanını okuyordu; gridin "Böl/Birleştir" menüsü de
tek dersi çok satıra bölüp `hours=1` bırakıyordu. Artık hepsi lesson_hours'tan
okur ve burası onu kilitler.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lesson_hours  # noqa: E402

passed, failed = 0, []


def check(name, cond, detail=""):
    global passed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def demo_store():
    return {
        "siniflar": [{"ad": "9A"}, {"ad": "9B"}],
        "ogretmenler": [{"ad": "Ali Veli"}, {"ad": "Ayşe Can"}],
        "atamalar": [
            {"class": "9A", "subject": "Matematik", "teacher": "Ali Veli",
             "duration": 4, "type": "2+2"},
            # sınıf ekranından saati 3'e çekilmiş ama eski alan 2'de kalmış satır
            {"class": "9A", "subject": "Türkçe", "teacher": "Ayşe Can",
             "duration": 3, "type": "2+1", "ders_sayisi": 2, "saat": 2},
            # gridin böl/birleştir menüsünün bıraktığı satır
            {"class": "9B", "subject": "Fizik", "teacher": "Ali Veli",
             "duration": 5, "type": "2+2+1", "hours": 1, "distribution": [2, 2, 1]},
        ],
    }


print("\n[saat okuma]")
d = demo_store()
a_mat, a_tur, a_fiz = d["atamalar"]
check("dağılımdan saat ('2+2' -> 4)", lesson_hours.hours(a_mat) == 4,
      str(lesson_hours.hours(a_mat)))
check("bayat ders_sayisi saati bozmuyor", lesson_hours.hours(a_tur) == 3,
      str(lesson_hours.hours(a_tur)))
check("bayat hours=1 saati bozmuyor", lesson_hours.hours(a_fiz) == 5,
      str(lesson_hours.hours(a_fiz)))
check("liste dağılım okunuyor", lesson_hours.parse_type([2, 2, 1]) == 5)
check("dağılım parçaları", lesson_hours.parts_of(a_fiz) == [2, 2, 1],
      str(lesson_hours.parts_of(a_fiz)))
check("dağılımsız satır 2'şer bölünüyor",
      lesson_hours.parts_of({"duration": 3}) == [2, 1])

print("\n[iki taraf aynı toplamı görüyor mu]")
check("sınıf toplamları", lesson_hours.per_class(d) == {"9A": 7, "9B": 5},
      str(lesson_hours.per_class(d)))
check("öğretmen toplamları",
      lesson_hours.per_teacher(d) == {"Ali Veli": 9, "Ayşe Can": 3},
      str(lesson_hours.per_teacher(d)))
check("genel toplam", lesson_hours.total(d) == 12, str(lesson_hours.total(d)))
audit = lesson_hours.audit(d)
check("çelişen satırlar yakalandı", len(audit["stale_rows"]) == 2,
      str(audit["stale_rows"]))
check("sınıf ve öğretmen toplamı eşit",
      audit["class_total"] == audit["teacher_total"] == 12,
      f"{audit['class_total']} / {audit['teacher_total']}")

print("\n[alanları eşitleme]")
lesson_hours.sync_all(d["atamalar"])
check("ders_sayisi düzeldi", a_tur["ders_sayisi"] == 3, str(a_tur))
check("saat düzeldi", a_tur["saat"] == 3, str(a_tur))
check("hours düzeldi", a_fiz["hours"] == 5, str(a_fiz))
check("distribution LİSTE kaldı", isinstance(a_fiz["distribution"], list),
      str(type(a_fiz["distribution"])))
check("eşitleme sonrası çelişki yok",
      lesson_hours.audit(d)["stale_rows"] == [],
      str(lesson_hours.audit(d)["stale_rows"]))
check("toplam değişmedi", lesson_hours.total(d) == 12)

print("\n[kayıt yolu: sanitize_atamalar]")
import version_store  # noqa: E402

raw = [{"class": "9A", "subject": "Kimya", "teacher": "Ali Veli",
        "duration": 4, "type": "2+2", "ders_sayisi": 1, "saat": 1}]
clean = version_store.sanitize_atamalar(raw)
check("kayıtta eski alanlar da güncelleniyor",
      clean[0]["ders_sayisi"] == 4 and clean[0]["saat"] == 4, str(clean[0]))

print("\n[tanınmayan isimler bildiriliyor]")
d2 = demo_store()
d2["atamalar"].append({"class": "9A", "subject": "Beden", "teacher": "Olmayan Hoca",
                       "duration": 2, "type": "2"})
a2 = lesson_hours.audit(d2)
check("öğretmen listesinde olmayan isim yakalandı",
      len(a2["unknown_teachers"]) == 1, str(a2["unknown_teachers"]))
d3 = demo_store()
d3["atamalar"].append({"class": "12Z", "subject": "Beden", "teacher": "Ali Veli",
                       "duration": 2, "type": "2"})
check("sınıf listesinde olmayan sınıf yakalandı",
      len(lesson_hours.audit(d3)["unknown_classes"]) == 1)

print("\n[birleşik ders]")
d4 = {
    "siniflar": [{"ad": "9A"}, {"ad": "9B"}],
    "ogretmenler": [{"ad": "Ali Veli"}],
    "atamalar": [{"class": "9A + 9B", "subject": "Beden", "teacher": "Ali Veli",
                  "duration": 2, "type": "2", "is_combined": True,
                  "combined_classes": ["9A", "9B"]}],
}
check("birleşik ders her sınıfa yazılıyor",
      lesson_hours.per_class(d4) == {"9A": 2, "9B": 2},
      str(lesson_hours.per_class(d4)))
check("birleşik ders öğretmene bir kez",
      lesson_hours.per_teacher(d4) == {"Ali Veli": 2},
      str(lesson_hours.per_teacher(d4)))

print("\n[danışman ve planlayıcı aynı kaynağı okuyor]")
import advisor  # noqa: E402

d5 = demo_store()
check("advisor sınıf talebi = lesson_hours",
      advisor.demand_per_class(d5) == lesson_hours.per_class(d5))
check("advisor öğretmen talebi = lesson_hours",
      advisor.demand_per_teacher(d5) == lesson_hours.per_teacher(d5))

import auto_scheduler  # noqa: E402

check("planlayıcı satır saatini aynı okuyor",
      (auto_scheduler.lesson_hours.hours(d5["atamalar"][2]) == 5))

print("\n[gerçek veri: sınıf ekranı = öğretmen ekranı]")
try:
    import json
    import version_store as vs

    slug = "bogazici_egitim_kurumlari"
    active = vs.get_active_version(slug)
    path = os.path.join(vs._versions_dir(slug), active) if active else ""
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            real = json.load(f)
        au = lesson_hours.audit(real)
        check("gerçek veride iki taraf eşit",
              au["class_total"] == au["teacher_total"],
              f"{au['class_total']} / {au['teacher_total']}")
        check("gerçek veride tanınmayan öğretmen yok",
              not au["unknown_teachers"], str(au["unknown_teachers"][:3]))
    else:
        print("  ATLA  aktif versiyon bulunamadı")
except Exception as e:  # pragma: no cover
    print(f"  ATLA  gerçek veri okunamadı: {e}")

print("\n" + "=" * 60)
print(f"geçen: {passed}   kalan: {len(failed)}")
for name, detail in failed:
    print(f"  - {name} {detail}")
print("=" * 60)
sys.exit(1 if failed else 0)
