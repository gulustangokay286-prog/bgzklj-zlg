"""Tanıtımların kalıcı durumu.

Bir tanıtım BİR KEZ gösterilir: kullanıcı gördükten sonra her açılışta önüne
çıkmaz. İşaretler ~/.chenki_akademi/onboarding.json içinde, anahtar bazında
tutulur (sürüm yenilikleri "whatsnew:5.1.0", ekran turları "tour:relations").
Dosya okunamazsa tanıtım gösterilir ama yazılamazsa sessizce geçilir: bu
yüzünden uygulama hiçbir zaman durmaz.
"""
import json
import os

_PATH = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "onboarding.json")


def _load() -> dict:
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def seen(key: str) -> bool:
    return bool(_load().get(key))


def mark_seen(key: str) -> None:
    data = _load()
    data[key] = True
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        tmp = _PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _PATH)
    except Exception:
        pass


def reset(key: str = None) -> None:
    """Test ve 'tanıtımı yeniden göster' için."""
    data = {} if key is None else {k: v for k, v in _load().items() if k != key}
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
