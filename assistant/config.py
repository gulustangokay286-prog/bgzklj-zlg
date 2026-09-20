"""Asistan ayarları."""
import os

import base64

MODEL = "gemini-3.1-flash-lite"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_DEFAULT_KEY_B64 = b"QVEuQWI4Uk42TGsydkE2Y29nMlhoT09NVlpqMHctVXhJYXl4V292X044U3VzaEFjODhvcVE="


def api_key() -> str:
    """Anahtar: önce ortam değişkeni, sonra secrets.py (git dışı), sonra gömülü anahtar."""
    key = os.environ.get("CHENKRON_GEMINI_KEY", "").strip()
    if key:
        return key
    try:
        from . import secrets
        s = (getattr(secrets, "GEMINI_API_KEY", "") or "").strip()
        if s:
            return s
    except Exception:
        pass
    try:
        return base64.b64decode(_DEFAULT_KEY_B64).decode("utf-8")
    except Exception:
        return ""
