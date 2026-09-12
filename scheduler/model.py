"""
scheduler/model.py — Dünya modeli: donmuş girdi.

Çizelgeleyicinin gördüğü her şey burada tanımlanır. data_store'un dağınık ve
tarihsel olarak birikmiş biçimi TEK SEFERDE burada normalize edilir; motorun
geri kalanı ham sözlüklere asla dokunmaz.

Temel birim KART'tır. Kart, kullanıcının "2+2" yazdığında kastettiği şeydir:
iki saatlik, BİTİŞİK, BÖLÜNEMEZ bir parça. Bir kart ya tamamen yerleşir ya hiç
yerleşmez. Bu kural motorun her yerinde geçerlidir ve hiçbir koşulda esnetilmez.

Izgara tek boyutlu indekslenir:  idx = gun * P + saat
Böylece bütün doluluk bilgisi tek bir tamsayı bitmaskesine sığar ve çakışma
kontrolü tek bir AND işlemine iner.
"""

from dataclasses import dataclass, field
from typing import Optional
import unicodedata

# ── Türkçe duyarlı normalizasyon ────────────────────────────────────────────
# Ders ve öğretmen adları veriye üç ayrı ekrandan giriyor ve aralarında büyük/
# küçük harf, boşluk ve Türkçe karakter farkları oluyor. Motorun her yerinde
# TEK normalizasyon kullanılır; iki farklı normalizasyon "Matematik" ile
# "MATEMATİK"i ayrı ders sanmaya yol açar ve kural sessizce boşa düşer.

_TR_LOWER = str.maketrans({
    "I": "ı", "İ": "i", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç",
})


def tr_lower(s: str) -> str:
    """Türkçe kurallarına göre küçük harfe çevirir (I→ı, İ→i)."""
    return str(s or "").translate(_TR_LOWER).lower()


# Türkçe harfleri ASCII karşılığına katlar. Bu tablo OLMADAN "ı" ile "i" ayrı
# harf kalır ve "Aynı ders..." ile "Ayni ders..." iki farklı kural sanılır —
# kural adı eşleşmez, kural sessizce yok olur. Tam olarak bu hata eski motorda
# vardı, bu yüzden katlama burada açıkça yazılıdır.
_TR_FOLD = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "i": "i",
    "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o",
    "ç": "c", "Ç": "c", "â": "a", "Â": "a",
    "î": "i", "Î": "i", "û": "u", "Û": "u",
})


def norm_key(s: str) -> str:
    """Karşılaştırma anahtarı: Türkçe katlanmış, aksansız, boşluksuz, küçük harf."""
    t = str(s or "").translate(_TR_FOLD).lower()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return "".join(ch for ch in t if ch.isalnum())


def subject_family(name: str) -> str:
    """Ders adının kimlik anahtarı: ADIN TAMAMI.

        "Matematik1", "Matematik2"  ->  ayrı dersler
        "Matematik",  "Geometri"    ->  ayrı dersler

    "Aynı ders aynı gün tekrar etmesin" kuralı bu anahtar üzerinden ölçülür.

    Bir ara bu işlev sondaki rakamları atıp "Matematik1" ile "Matematik2"yi tek
    aile sayıyordu. Kullanıcının kastı bu değil: numaralı adlar Birey'de ayrı
    ders saatleridir ve aynı güne gelmeleri sorun değil ("mat1 mat2 yan yana
    gelebilir sıkıntı yok"). Birleştirme, kuralı olduğundan sert yapıyordu ve
    ölçülen bedeli tam 2 saatti: Birey v111'de aile birleştirmesi açıkken tavan
    235/237, kapalıyken 237/237 (ikisi de CP-SAT OPTIMAL). Kural artık ekranda
    yazdığı gibi çalışıyor — aynı ders, yani aynı ad.
    """
    return norm_key(name)


def norm_class(s: str) -> str:
    """Sınıf adı anahtarı: '11A (MF)' -> '11amf', '9-A' -> '9a'."""
    return norm_key(s)


# ── Kart ────────────────────────────────────────────────────────────────────

@dataclass
class Card:
    """Yerleştirilecek atomik parça.

    duration saat BİTİŞİK olarak tek bir günün ardışık saatlerine oturur.
    classes birden fazlaysa kart birleşik derstir: tek öğretmen, tek saat,
    birden fazla sınıf. Birleşik kart öğretmen için TEK doluluk üretir.
    """
    cid: int
    classes: tuple            # sınıf indeksleri
    subject: int              # ders indeksi
    teacher: int              # öğretmen indeksi (-1 = atanmamış)
    duration: int
    origin: int               # kaynak atamanın indeksi (rapor için)
    group: int                # aynı atamadan gelen kartlar aynı grup
    locked_at: Optional[int] = None   # kilitli kart: sabit idx
    family: int = -1                  # ders ailesi (Matematik9/10/11 -> aynı)

    # Ön hesaplanan aday yerler; World.build() doldurur.
    slots: tuple = field(default_factory=tuple)      # (idx, footprint) çiftleri
    subject_name: str = ""
    teacher_name: str = ""
    class_names: tuple = field(default_factory=tuple)

    def __repr__(self):
        return (f"<Kart {'+'.join(self.class_names)} {self.subject_name} "
                f"{self.teacher_name} {self.duration}s>")


# ── Dünya ───────────────────────────────────────────────────────────────────

@dataclass
class World:
    D: int
    P: int
    classes: list             # sınıf adları
    teachers: list            # öğretmen adları
    subjects: list            # ders adları
    cards: list               # Card listesi

    class_closed: list        # sınıf -> bitmask (kapalı hücreler)
    teacher_closed: list      # öğretmen -> bitmask (kapalı + çapraz kurum)
    class_avoid: list         # sınıf -> bitmask (kaçınılacak)
    teacher_avoid: list       # öğretmen -> bitmask (kaçınılacak)

    class_capacity: list      # sınıf -> açık hücre sayısı
    class_demand: list        # sınıf -> gereken saat

    def cells(self) -> int:
        return self.D * self.P

    def idx(self, d: int, p: int) -> int:
        return d * self.P + p

    def dp(self, idx: int) -> tuple:
        return divmod(idx, self.P)

    def footprint(self, d: int, p: int, dur: int) -> int:
        """Kartın kapladığı hücrelerin bitmaskesi. Gün sınırını aşarsa 0."""
        if p + dur > self.P:
            return 0
        base = self.idx(d, p)
        return ((1 << dur) - 1) << base

    def total_hours(self) -> int:
        return sum(c.duration * len(c.classes) for c in self.cards)
