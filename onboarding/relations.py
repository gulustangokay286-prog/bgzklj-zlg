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
