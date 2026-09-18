"""Planlama İlişkileri ekranının kendi turu.

Ekran ilk kez açıldığında kısa bir tur çalışır ve ekranı gerçekten tarif eder:
kural listesi ne işe yarar, "Yeni Kural" ile ne olur, ders/öğretmen/sınıf
süzgeçleri kuralın kimi bağladığını nasıl belirler, gruplar niçin zorunludur
ve önem derecesi ne demektir. Tur bir kez gösterilir; menüden yeniden
çalıştırılabilir.
"""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QAbstractButton

from . import state
from .spotlight import TourRunner

KEY = "tour:relations"


def _button(dlg, *parts):
    """Etiketinde verilen parçalardan biri GEÇEN ilk görünür düğme.

    startswith kullanmak kırılgandı: ekrandaki düğme "＋ Kural Ekle" yazıyor,
    aranan "Ekle" ise baştan eşleşmiyordu ve adım sessizce atlanıyordu.
    """
    for want in parts:
        w = want.lower()
        for b in dlg.findChildren(QAbstractButton):
            if not b.isVisible():
                continue
            if w in (b.text() or "").replace("&", "").lower():
                return b
    return None


def _widget(dlg, name):
    return getattr(dlg, name, None)


def steps(dlg):
    return [
        {
            "target": lambda: _widget(dlg, "table") or _widget(dlg, "table_rules") or dlg,
            "title": "Kurallar listesi",
            "text": "Çizelgeyi bağlayan bütün kurallar burada durur. Bir satır = bir kural. "
                    "Kuralın hangi derslere, öğretmenlere ve sınıflara uygulandığı satırda yazar; "
                    "<b>pasif</b> bir kural motoru hiç etkilemez.",
            "allow_missing": True,
        },
        {
            "target": lambda: _button(dlg, "Kural Ekle", "Yeni", "Ekle"),
            "title": "Yeni kural eklemek",
            "text": "Kural türünü seçersiniz (“Aynı ders aynı gün tekrar etmesin”, “İki ders aynı "
                    "güne gelmesin”, “Seçilen dersler aynı ders sayılsın”, “Günde maksimum ders "
                    "sayısı”…). Her tür farklı bir şeyi kısıtlar; ekranda seçtiğiniz türe göre "
                    "yalnızca anlamlı alanlar açık kalır.",
            "allow_missing": True,
        },
        {
            "target": lambda: _button(dlg, "Düzenle", "Değiştir"),
            "next": "Devam",
            "title": "Süzgeçler: kim bağlanıyor?",
            "text": "Ders / öğretmen / sınıf alanları kuralın <b>kapsamıdır</b>. Boş bırakılan alan "
                    "“hepsi” demektir: sınıf seçmezseniz kural bütün sınıflarda geçerlidir. "
                    "Ders seçtiğinizde ilgili öğretmen ve sınıflar otomatik işaretlenir.",
            "allow_missing": True,
        },
        {
            "target": lambda: _widget(dlg, "table") or dlg,
            "title": "Gruplar zorunludur",
            "text": "“Seçilen dersler aynı ders sayılsın” ve “İki ders aynı güne gelmesin” "
                    "kurallarında seçtiğiniz dersler <b>tek bir küme</b> sayılır. Mat1+Mat2 ile "
                    "Türkçe+Edebiyat'ı aynı kuralda kullanacaksanız ders seçme penceresinde "
                    "<b>grup</b> oluşturmalısınız; gruplamazsanız dördü birden tek ders sayılır ve "
                    "çizelge oturmaz.",
            "allow_missing": True,
            "next": "Göster",
            "after": lambda: show_group_sheet(dlg),
        },
        {
            "target": lambda: _button(dlg, "Kapat ve Kaydet", "Kaydet", "Kapat", "Tamam"),
            "title": "Önem derecesi",
            "text": "<b>Sıkı</b> = kesin kural: motor asla çiğnemez, imkânsızsa dersi yerleştirmez ve "
                    "sebebini söyler. Diğer dereceler tercihtir: mümkünse uyulur, gerekirse esnetilir. "
                    "Bir kuralın neden uygulanmadığını Otomatik Planla raporunda görebilirsiniz.",
            "allow_missing": True,
            "next": "Bitir",
        },
    ]


def show_group_sheet(dlg):
    """Ders seçme sayfasını (gruplama sheet'i) tanıtım amacıyla açar.

    Turun en önemli maddesi gruplama; onu anlatıp geçmek yetmiyor, sayfanın
    kendisi açılıp "Seçilenleri Grup Yap" düğmesi gösteriliyor. Seçim hiçbir
    yere kaydedilmez: sayfa örnek iki grupla (Mat1+Mat2 | Türkçe+Edebiyat)
    açılır, kullanıcı kapatınca tur devam eder.
    """
    try:
        from dialogs.relations_dialog import MultiSelectDialog
    except Exception as exc:
        print(f"[onboarding] ders seçme sayfası açılamadı: {exc}")
        return
    store = getattr(dlg, "data_store", {}) or {}
    items = sorted({(d.get("ad") or "").strip() for d in store.get("dersler", []) if isinstance(d, dict)}
                   | {(a.get("subject") or "").strip() for a in store.get("atamalar", []) if isinstance(a, dict)}
                   - {""})
    if not items:
        items = ["Matematik1", "Matematik2", "Türkçe", "Edebiyat", "Fizik", "Kimya"]

    def _pick(*names):
        out = []
        for n in names:
            hit = next((i for i in items if i.replace(" ", "").lower() == n.replace(" ", "").lower()), None)
            if hit:
                out.append(hit)
        return out

    demo = [g for g in (_pick("Matematik1", "Matematik2"), _pick("Türkçe", "Edebiyat")) if len(g) >= 2]
    if not demo:
        demo = [items[:2]] if len(items) >= 2 else []
    sheet = MultiSelectDialog(items, [x for g in demo for x in g],
                              "Dersleri Seç — GRUP oluşturma (tanıtım)", dlg,
                              groups=demo or None)
    steps_sheet = [
        {
            "target": lambda: _button(sheet, "Grup Yap", "Seçilenleri Grup"),
            "title": "Grup burada oluşturulur",
            "text": "Soldan <b>Mat1</b> ve <b>Mat2</b>'yi işaretleyip bu düğmeye basarsanız ikisi "
                    "BİR ders olur. Sonra <b>Türkçe</b> ile <b>Edebiyat</b>'ı işaretleyip yine "
                    "basarsanız ikinci grup olur. Gruplar birbirinden bağımsızdır.",
            "next": "Devam",
        },
        {
            "target": lambda: _button(sheet, "Grubu Kaldır", "Kaldır"),
            "title": "Grup yapmazsanız ne olur?",
            "text": "Seçtiğiniz bütün dersler <b>tek grup</b> sayılır: Mat1, Mat2, Türkçe, Edebiyat "
                    "dördü birden aynı ders kabul edilir ve çizelge oturmaz. Sayfanın altındaki not "
                    "bunu hatırlatır.",
            "next": "Devam",
        },
        {
            "target": lambda: _button(sheet, "Uygula", "Tamam"),
            "title": "Uygula",
            "text": "Gruplar burada onaylanır ve kural satırında “Mat1 + Mat2 | Türkçe + Edebiyat” "
                    "şeklinde görünür. Bu tanıtım penceresinde yaptığınız seçim kaydedilmez.",
            "next": "Bitir",
        },
    ]
    runner = TourRunner(sheet, steps_sheet, on_finish=sheet.reject)
    sheet._tour = runner
    QTimer.singleShot(240, runner.start)
    sheet.exec()


def maybe_run(dlg, force=False):
    """Ekran ilk kez açıldıysa turu başlatır."""
    if not force and state.seen(KEY):
        return False
    try:
        runner = TourRunner(dlg, steps(dlg), on_finish=lambda: state.mark_seen(KEY))
        dlg._relations_tour = runner          # referans: GC toplamasın
        QTimer.singleShot(260, runner.start)
        return True
    except Exception as exc:
        print(f"[onboarding] ilişkiler turu çalışmadı: {exc}")
        state.mark_seen(KEY)
        return False
