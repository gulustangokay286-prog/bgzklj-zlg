"""Asistan ayarları."""
import os

MODEL = "gemini-3.1-flash-lite"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def api_key() -> str:
    """Anahtar: önce ortam değişkeni, sonra secrets.py (git dışı)."""
    key = os.environ.get("CHENKRON_GEMINI_KEY", "").strip()
    if key:
        return key
    try:
        from . import secrets
        return (getattr(secrets, "GEMINI_API_KEY", "") or "").strip()
    except Exception:
        return ""
