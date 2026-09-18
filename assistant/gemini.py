"""Gemini REST istemcisi — araç (fonksiyon) çağrısı destekli.

SDK yok, yalnızca `requests`: uygulama PyInstaller ile paketleniyor, bağımlılık
ne kadar azsa derleme o kadar sağlam. generateContent'in ham JSON'u burada
sarılır; üst katmanlar yalnızca `Reply` görür.
"""
import json
import time

from . import config


class GeminiError(Exception):
    """Ağ, yetki ya da model hatası — kullanıcıya gösterilecek kısa mesajla."""


class Reply:
    """Modelin bir turluk cevabı."""

    def __init__(self, parts, usage=None):
        self.parts = parts or []          # geçmişe olduğu gibi eklenir (thoughtSignature dahil)
        self.usage = usage or {}

    @property
    def text(self) -> str:
        return "".join(p.get("text", "") for p in self.parts if "text" in p).strip()

    @property
    def calls(self):
        """[(id, ad, argümanlar)] — model sırayla çağrılmasını istiyor."""
        out = []
        for p in self.parts:
            fc = p.get("functionCall")
            if fc:
                out.append((fc.get("id") or "", fc.get("name") or "", dict(fc.get("args") or {})))
        return out


class GeminiClient:
    def __init__(self, api_key=None, model=None, timeout=45.0):
        self.api_key = api_key if api_key is not None else config.api_key()
        self.model = model or config.MODEL
        self.timeout = timeout

    def generate(self, contents, system=None, tools=None, temperature=0.2):
        """contents: [{"role": "user"|"model", "parts": [...]}] -> Reply"""
        if not self.api_key:
            raise GeminiError("Yapay zekâ anahtarı tanımlı değil.")
        import requests
        body = {"contents": contents,
                "generationConfig": {"temperature": temperature}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if tools:
            body["tools"] = [{"functionDeclarations": tools}]
            body["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}
        url = config.ENDPOINT.format(model=self.model) + "?key=" + self.api_key
        last = None
        for attempt in range(2):
            try:
                resp = requests.post(url, json=body, timeout=self.timeout)
            except requests.exceptions.Timeout:
                last = GeminiError("Yapay zekâ cevap vermedi (zaman aşımı).")
                continue
            except Exception as exc:
                raise GeminiError(f"Bağlantı kurulamadı: {exc}")
            if resp.status_code == 429 and attempt == 0:
                time.sleep(1.5)
                continue
            if resp.status_code != 200:
                msg = ""
                try:
                    msg = resp.json().get("error", {}).get("message", "")
                except Exception:
                    pass
                raise GeminiError(f"Yapay zekâ hatası (HTTP {resp.status_code}): {msg[:160]}")
            try:
                data = resp.json()
            except Exception:
                raise GeminiError("Yapay zekâ cevabı okunamadı.")
            cands = data.get("candidates") or []
            if not cands:
                reason = (data.get("promptFeedback") or {}).get("blockReason", "")
                raise GeminiError("Model cevap üretmedi." + (f" ({reason})" if reason else ""))
            parts = (cands[0].get("content") or {}).get("parts") or []
            return Reply(parts, data.get("usageMetadata"))
        raise last or GeminiError("Yapay zekâ cevap vermedi.")


def user_turn(text):
    return {"role": "user", "parts": [{"text": text}]}


def model_turn(parts):
    return {"role": "model", "parts": list(parts)}


def tool_results_turn(results):
    """results: [(id, ad, sonuç sözlüğü)] -> functionResponse parçaları."""
    parts = []
    for call_id, name, result in results:
        part = {"functionResponse": {"name": name, "response": result}}
        if call_id:
            part["functionResponse"]["id"] = call_id
        parts.append(part)
    return {"role": "user", "parts": parts}


def compact(obj, limit=4000):
    """Araç sonucu çok büyükse kısalt — istem bütçesi ve hız için."""
    s = json.dumps(obj, ensure_ascii=False)
    if len(s) <= limit:
        return obj
    return {"ozet": s[:limit] + "…"}
