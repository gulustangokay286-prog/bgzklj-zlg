"""
test_drop_policy.py — öğretmenlerin bıraktığı notun kuralı.

    python test_drop_policy.py

Notta üç cümle var:

  1) "Öğretmen kapalıysa o gün sürükleme manuel yapılsa bile o kısma yerleşim
      yapılamaz."                 -> KAPALI SAAT = KESİN RET, elle bile olmaz
  2) "Sadece sürüklenen yerde çakışan ders var derse yine de yerleştir kısmı
      olmalı."                    -> DOLU HÜCRE = uyar, kullanıcı çözsün
  3) "Fakat şu an öğretmen kapalı olsa dahi manuel yerleşiyor."
                                  -> bildirilen hata

Bu test, kapalı saatin hiçbir yoldan aşılamadığını ve dolu hücrenin hâlâ
aşılabildiğini kilitler. İkisinin karışması, öğretmenlerin çizelgesini sessizce
bozan türden bir hatadır.
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
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


def timeoff(closed=()):
    g = [[2] * P for _ in DAYS]
    for d, p in closed:
        g[d][p] = 0
    return g


def analyze(data, les, day, period, slug=None):
    snap = pe.TimetableSnapshot(data, institution_slug=slug,
                                exclude_block_id=les.get("block_id"))
    return pe.analyze(snap, les, pe.CandidatePlacement(les, day, period))


def run():
    lesson = {"class_name": "9A", "subject_name": "Matematik",
              "teacher_name": "Ahmet Yılmaz", "duration": 1, "block_id": "dragged"}
    base = {
        "settings": {"days": DAYS, "days_count": 5, "periods": P},
        "siniflar": [{"ad": "9A"}, {"ad": "9B"}],
        "ogretmenler": [{"ad": "Ahmet Yılmaz"}, {"ad": "Ayşe Demir"}],
        "dersler": [{"ad": "Matematik"}, {"ad": "Fizik"}],
        "derslikler": [], "atamalar": [], "kisitlamalar": {},
        "grid_placements": [],
    }

    print("\n[1. cümle] öğretmen kapalıysa YERLEŞTİRİLEMEZ")
    d = dict(base, ogretmenler=[{"ad": "Ahmet Yılmaz", "timeoff": timeoff([(0, 2)])},
                                {"ad": "Ayşe Demir"}])
    r = analyze(d, lesson, 0, 2)
    check("öğretmen kapalı -> FORBIDDEN", r.status == pe.FORBIDDEN, r.status)
    check("gri yanıyor", r.visual == pe.V_GREY, r.visual)
    check("gerekçe öğretmen müsaitliği",
          any(c.type == pe.TEACHER_UNAVAILABLE for c in r.conflicts),
          str([c.type for c in r.conflicts]))

    print("\n[1. cümle] sınıf kapalıysa da yerleştirilemez")
    d2 = dict(base, siniflar=[{"ad": "9A", "timeoff": timeoff([(1, 4)])}, {"ad": "9B"}])
    r2 = analyze(d2, lesson, 1, 4)
    check("sınıf kapalı -> FORBIDDEN", r2.status == pe.FORBIDDEN, r2.status)

    print("\n[2. cümle] dolu hücre yerleştirmeye AÇIK kalmalı")
    d3 = dict(base, grid_placements=[
        {"class_name": "9A", "subject_name": "Fizik", "teacher_name": "Ayşe Demir",
         "day": 0, "period": 0, "duration": 1, "block_id": "b1"}])
    r3 = analyze(d3, lesson, 0, 0)
    check("dolu hücre -> CONFLICT", r3.status == pe.CONFLICT, r3.status)
    check("kırmızı yanıyor", r3.visual == pe.V_RED, r3.visual)
    check("bırakmaya açık (placeable)", r3.placeable is True)

    print("\n[ayrım] kapalı saat bırakmaya KAPALI")
    check("kapalı saat placeable değil", analyze(d, lesson, 0, 2).placeable is False)

    print("\n[başka kurumda meşgul: kapalı değil, MEŞGUL]")
    # Uygulamada 'Diğer Kurumları Yoksay' seçeneği bilerek var; bu yüzden başka
    # kurumdaki ders kırmızıdır (aşılabilir), gri değil.
    snap = pe.TimetableSnapshot(base, exclude_block_id="dragged")
    snap.cross_busy = {pe.teacher_key("Ahmet Yılmaz"): {
        (2, 1): {"institution_name": "Birey", "class": "10A", "subject": "Mat"}}}
    r4 = pe.analyze(snap, lesson, pe.CandidatePlacement(lesson, 2, 1))
    check("başka kurumda ders -> CONFLICT", r4.status == pe.CONFLICT, r4.status)
    check("kırmızı", r4.visual == pe.V_RED, r4.visual)
    check("kullanıcı aşabilir", r4.placeable is True)
    check("gerekçe kurumlar arası",
          any(c.type == pe.CROSS_INSTITUTION for c in r4.conflicts),
          str([c.type for c in r4.conflicts]))

    print("\n[3. cümle] kapalı saat uyarısı gerekçesiyle ÇIKAR ve kararı sorar")
    import io
    import re
    src = io.open("main_window.py", encoding="utf-8").read()
    start = src.index("def _on_lesson_dropped")
    body = src[start:start + 26000]
    # Kapalı saatte artık sessizce yerleştirme de, sorgusuz ret de yok:
    # her ret yolu _ask_place_anyway'den geçip kullanıcıya soruyor. Uyarı
    # metni ortak yardımcıda (main_window.ask_place_anyway) durduğu için
    # burada çağrının varlığı aranıyor.
    offenders = re.findall(r"kısıtlamayı yok sayıp", body)
    check("sessiz override yok", not offenders, str(offenders))
    check("kapalı saat kararı kullanıcıya soruluyor",
          "_ask_place_anyway" in body, "çağrı bulunamadı")
    check("uyarı başlığı yardımcıda duruyor",
          "Bu Saate Yerleştirilemez" in src, "başlık kayboldu")
    check("dolu hücre akışı duruyor",
          "Takas Edilemiyor" in body or "Dersleri Yer Değiştir" in body)

    print("\n[iki saatlik ders: ikinci saati kapalıysa da ret]")
    d5 = dict(base, ogretmenler=[{"ad": "Ahmet Yılmaz", "timeoff": timeoff([(0, 3)])},
                                 {"ad": "Ayşe Demir"}])
    les2 = dict(lesson, duration=2)
    r5 = analyze(d5, les2, 0, 2)
    check("ayak izinin ikinci saati kapalı -> FORBIDDEN",
          r5.status == pe.FORBIDDEN, r5.status)
    check("mesaj taşmayı/kapalıyı anlatıyor", "kapalı" in r5.explanation.lower(),
          r5.explanation)


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
