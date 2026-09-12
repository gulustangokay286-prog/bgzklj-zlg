"""
scheduler — çizelge motoru.

Katmanlar (her biri tek işten sorumlu, ayrı test edilebilir):

    model.py       Kart ve Dünya tipleri, Türkçe duyarlı normalizasyon
    build.py       data_store -> World, dağılım metni -> kartlar
    rules.py       Planlama İlişkileri -> tipli Rule; sessiz kayıp yok
    problem.py     kurallardan C++ arama modeli
    native/        gün ve saati birlikte onaran C++ araması
    native_bridge.py derleme, iptal ve canlı ilerleme
    verify.py      bağımsız son denetim
    diagnostics.py kısıt uyuşmazlığı tanıkları
    engine.py      dışa açık solve()
"""

from .engine import solve, Result          # noqa: F401
from .build import build_world, attach_slots, parse_distribution   # noqa: F401
from .rules import compile_rules           # noqa: F401

__all__ = ["solve", "Result", "build_world", "attach_slots",
           "parse_distribution", "compile_rules"]
