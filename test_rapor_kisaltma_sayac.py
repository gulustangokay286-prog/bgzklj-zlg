"""
test_rapor_kisaltma_sayac.py — yazdırma raporları, ders kısaltmaları, sheet özeti
ve ana ekranın canlı dinlemesi.

    python test_rapor_kisaltma_sayac.py

Dört şikâyetin regresyon kilidi:

1. "Tüm Öğretmenlerin Ders Yükü Listesi" sayfaya sığmayan öğretmenleri `break`
   ile atıyordu (sayfaya 19 satır sığıyor; 23 kadroda 4 kişi kayboluyordu).
   Şimdi satır yüksekliği kadroya göre daralıyor: herkes tek sayfaya sığıyor,
   ancak okunaklık sınırında bile sığmazsa sayfalanıyor — kimse kaybolmuyor.

2. Ders kısaltmaları kullanıcının "kisa" alanından ham geliyordu; "GÖRSEL
   SANATLAR" (15 karakter) gibi değerler dar sütuna sığmayınca font 4.5 piksele
   düşüyor ve çizelgede okunmuyordu. Artık kısaltmalar bütçeye sıkıştırılıyor
   ve font tabanı 7 piksel.

3. Dersler/Sınıflar/Derslikler/Öğretmenler sheet'lerinin sağ üstünde sade bir
   özet var: kaç kayıt, kaç saat; solunda tooltip taşıyan bilgi simgesi.

"""
import json
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication  # noqa: E402

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bgz_database.json")


def load_store():
    with open(DB, encoding="utf-8") as f:
        return json.load(f)


class RecPainter:
    """drawText çağrılarını ve kullanılan font boyutlarını kaydeden sahte painter."""

    def __init__(self):
        self.texts = []
        self.sizes = []

    def drawText(self, *a):
        if a and isinstance(a[-1], str):
            self.texts.append(a[-1])

    def setFont(self, f):
        try:
            self.sizes.append(f.pixelSize())
        except Exception:
            pass

    def fontMetrics(self):
        class FM:
            def horizontalAdvance(self, t):
                return len(t) * 5.2

            def elidedText(self, t, mode, w):
                return t
        return FM()

    def __getattr__(self, n):
        return lambda *a, **k: None


class FakePrinter:
    def __init__(self):
        self.pages = 1

    def newPage(self):
        self.pages += 1

    def width(self):
        return 1120

    def height(self):
        return 792


def _preview(ds):
    from dialogs.print_preview import TimetablePrintPreview
    dlg = TimetablePrintPreview.__new__(TimetablePrintPreview)
    dlg.data_store = ds
    dlg.filtered_teachers = None
    dlg.filtered_classes = None
    dlg._placements_cache = {}

    class _Combo:
        def currentText(self):
            return "Tümü"
    dlg.target_combo = _Combo()
    return dlg


# ── 1. Ders yükü listesi: kimse düşmesin, gereksiz kağıt harcanmasın ─────────
def test_ders_yuku_listesi():
    print("\n[tüm öğretmenlerin ders yükü listesi]")
    from dialogs.print_preview import TimetablePrintPreview

    base = load_store()
    for n in (5, 16, 19, 23, 40, 120):
        ds = json.loads(json.dumps(base))
        names = [f"Öğretmen {i:03d}" for i in range(n)]
        ds["ogretmenler"] = [{"ad": x, "kisa": x[:4]} for x in names]

        dlg = _preview(ds)
        p, pr = RecPainter(), FakePrinter()
        TimetablePrintPreview._render_teacher_summary_list(dlg, p, 1120, 792, pr)

        drawn = set(p.texts)
        missing = [x for x in names if x not in drawn]
        check(f"{n} öğretmenin hepsi raporda", not missing,
              f"eksik {len(missing)}: {missing[:3]}")

    # Tek sayfaya sığma: makul kadrolar tek kağıda basılmalı.
    for n, want in ((16, 1), (23, 1), (40, 1)):
        ds = json.loads(json.dumps(base))
        ds["ogretmenler"] = [{"ad": f"Öğretmen {i:03d}", "kisa": "X"} for i in range(n)]
        dlg = _preview(ds)
        p, pr = RecPainter(), FakePrinter()
        TimetablePrintPreview._render_teacher_summary_list(dlg, p, 1120, 792, pr)
        check(f"{n} öğretmen tek kağıda sığıyor", pr.pages == want, f"{pr.pages} sayfa")

    # Sağ üstte toplam sayı yazmalı ki eksik olup olmadığı görülsün.
    ds = json.loads(json.dumps(base))
    dlg = _preview(ds)
    p, pr = RecPainter(), FakePrinter()
    TimetablePrintPreview._render_teacher_summary_list(dlg, p, 1120, 792, pr)
    check("raporda toplam öğretmen sayısı yazıyor",
          any("Toplam" in t and "Öğretmen" in t for t in p.texts))


# ── 2. Ders kısaltmaları okunaklı olsun ──────────────────────────────────────
def test_kisaltmalar():
    print("\n[ders kısaltmaları]")
    from dialogs.print_preview import TimetablePrintPreview

    ds = load_store()
    # Kullanıcının bildirdiği bozuk vakalar + uzun "kisa" değerleri
    ds["dersler"] = ds["dersler"] + [
        {"ad": "Paragraf", "kisa": "PARAG"},
        {"ad": "Matematik 11", "kisa": "MATE 11"},
        {"ad": "Biyoloji 11", "kisa": "BİYO 11"},
        {"ad": "Coğrafya 2", "kisa": "COĞRAF"},
        {"ad": "Görsel Sanatlar 2", "kisa": "GÖRSEL SANATLAR 2"},
    ]

    dlg = _preview(ds)
    p, pr = RecPainter(), FakePrinter()
    TimetablePrintPreview._render_carsaf_liste(dlg, p, pr, 1120, 792, is_teacher=False)

    check("çarşaf tek sayfaya sığıyor", pr.pages == 1, f"{pr.pages} sayfa")

    tiny = [s for s in p.sizes if 0 < s < 7]
    check("hiçbir yazı 7 pikselin altına düşmüyor", not tiny,
          f"{len(tiny)} kez, en küçük {min(tiny) if tiny else '-'}")

    abbr = dlg._smart_abbr
    long_codes = [(d["ad"], abbr(d["ad"])) for d in ds["dersler"] if len(abbr(d["ad"])) > 5]
    check("her kısaltma en fazla 5 karakter", not long_codes, str(long_codes[:3]))

    # Sayı korunmalı: "Matematik 1" ile "Matematik 2" karışmamalı.
    check("sondaki ders numarası korunuyor",
          abbr("Matematik 1") != abbr("Matematik 2")
          and any(ch.isdigit() for ch in abbr("Matematik 1")),
          f"{abbr('Matematik 1')} / {abbr('Matematik 2')}")

    codes = {}
    dup = []
    for d in ds["dersler"]:
        c = abbr(d["ad"])
        if c in codes and codes[c] != d["ad"]:
            dup.append((codes[c], d["ad"], c))
        codes[c] = d["ad"]
    check("iki farklı ders aynı kodu almıyor", not dup, str(dup[:3]))


# ── 3. Sheet sağ üstündeki sade özet ────────────────────────────────────────
def test_sheet_ozeti():
    print("\n[veri sheet'lerinin sağ üst özeti]")
    from dialogs.master_data_dialog import MasterDataDialog

    ds = load_store()
    ds.setdefault("derslikler", [{"ad": "A-101"}, {"ad": "A-102"}, {"ad": "Lab-1"}])
    d = MasterDataDialog(0, parent=None, data_store=ds)
    d.data_store = ds
    d._load_existing_data()

    check("dört sekmenin de özeti var", len(d.count_labels) == 4, str(len(d.count_labels)))
    check("dört sekmenin de bilgi simgesi var", len(d.count_icons) == 4)

    for lbl in d.count_labels:
        check(f"sade (kutusuz) görünüm: {lbl.text()[:22]!r}",
              "background: transparent" in lbl.styleSheet()
              and "border: none" in lbl.styleSheet()
              and "border-radius" not in lbl.styleSheet())

    for ic in d.count_icons:
        check("bilgi simgesinde tooltip var", bool(ic.toolTip()))

    n_t = len(ds["ogretmenler"])
    h = sum(int(a.get("duration") or 1) for a in ds["atamalar"]
            if str(a.get("teacher") or "").strip())
    check("öğretmen özeti sayı ve saat gösteriyor",
          d.count_labels[3].text() == f"{n_t} öğretmen  ·  {h} saat",
          d.count_labels[3].text())
    check("derslikte saat gösterilmiyor",
          "saat" not in d.count_labels[2].text(), d.count_labels[2].text())

    ds["atamalar"].append({"subject": "X", "class": "9A",
                           "teacher": ds["ogretmenler"][0]["ad"], "duration": 5})
    d._load_existing_data()
    check("atama eklenince saat güncelleniyor",
          d.count_labels[3].text().endswith(f"{h + 5} saat"), d.count_labels[3].text())
    d.close()


# NOT: "ana ekran canlı dinleme" testi kaldırıldı. O bölüm cloud_sync'teki
# watch_many / 1 saniyelik yoklama değişikliklerini sınıyordu; bu değişiklikler
# kullanıcının isteğiyle geri alındı, dolayısıyla test artık var olmayan bir
# özelliği bekliyordu. cloud_sync.py'nin güncel hâli ayrıca başka bir çalışmanın
# (CAS çakışma yönetimi) parçası — buradan doğrulanmıyor.


def run():
    test_ders_yuku_listesi()
    test_kisaltmalar()
    test_sheet_ozeti()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    try:
        run()
    except Exception:
        import traceback
        traceback.print_exc()
        FAILED.append(("beklenmeyen hata", "traceback"))
    finally:
        print("\n" + "=" * 60)
        print(f"geçen: {len(PASSED)}   kalan: {len(FAILED)}")
        for f in FAILED:
            print(f"  - {f}")
        print("=" * 60)
    sys.exit(1 if FAILED else 0)
