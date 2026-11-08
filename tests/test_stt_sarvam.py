"""Sarvam speech-to-text provider, language codes and provider order (no network)."""

import asyncio

import httpx
import pytest

from app.config.settings import settings
from app.services import stt_service


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def sarvam(monkeypatch):
    """Fake Sarvam: replies per `mode`, records every request."""
    calls = []
    replies = {
        "transcribe": {"transcript": "ನನಗೆ ಆನೆ ಬೇಕು", "language_code": "kn-IN"},
        "translate": {"transcript": "I want an elephant", "language_code": "en-IN"},
    }
    fail = {"translate": False, "all": None}

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        mode = "translate" if b'name="mode"\r\n\r\ntranslate' in body else "transcribe"
        calls.append({"mode": mode, "key": request.headers.get("api-subscription-key"), "body": body})
        if fail["all"]:
            return httpx.Response(fail["all"], json={"error": "boom"})
        if mode == "translate" and fail["translate"]:
            return httpx.Response(500, json={"error": "boom"})
        return httpx.Response(200, json=replies[mode])

    monkeypatch.setattr(settings, "SARVAM_API_KEY", "test-key")
    monkeypatch.setattr(settings, "SARVAM_TRANSLATE", True)
    monkeypatch.setattr(
        stt_service, "_sarvam_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    return type("S", (), {"calls": calls, "replies": replies, "fail": fail})


def test_normalize_language():
    n = stt_service.normalize_language
    assert [n(x) for x in ("kn-IN", "hi-IN", "en-IN", "Hindi", "kannada", "english")] == [
        "kn", "hi", "en", "hi", "kn", "en"]
    assert n(None) == "en" and n("unknown") == "en" and n("") == "en"
    assert n("kok-IN") == "kok"


def test_kannada_gets_text_language_and_english(sarvam):
    r = run(stt_service._transcribe_sarvam(b"RIFFfake"))
    assert r == {"text": "ನನಗೆ ಆನೆ ಬೇಕು", "language": "kn", "provider": "sarvam",
                 "english_text": "I want an elephant"}
    assert [c["mode"] for c in sarvam.calls] == ["transcribe", "translate"]
    assert all(c["key"] == "test-key" for c in sarvam.calls)
    assert b"RIFFfake" in sarvam.calls[0]["body"]
    assert b'name="model"\r\n\r\nsaaras:v3' in sarvam.calls[0]["body"]


def test_english_makes_one_call(sarvam):
    sarvam.replies["transcribe"] = {"transcript": "I want a dog", "language_code": "en-IN"}
    r = run(stt_service._transcribe_sarvam(b"x"))
    assert r["language"] == "en" and "english_text" not in r
    assert len(sarvam.calls) == 1


def test_translation_failure_keeps_original(sarvam):
    sarvam.fail["translate"] = True
    r = run(stt_service._transcribe_sarvam(b"x"))
    assert r["text"] == "ನನಗೆ ಆನೆ ಬೇಕು" and "english_text" not in r


def test_translation_can_be_turned_off(sarvam, monkeypatch):
    monkeypatch.setattr(settings, "SARVAM_TRANSLATE", False)
    run(stt_service._transcribe_sarvam(b"x"))
    assert len(sarvam.calls) == 1


def test_http_error_raises(sarvam):
    sarvam.fail["all"] = 401
    with pytest.raises(RuntimeError, match="401"):
        run(stt_service._transcribe_sarvam(b"x"))


def test_missing_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "")
    with pytest.raises(RuntimeError, match="key"):
        run(stt_service._transcribe_sarvam(b"x"))


def _patch_providers(monkeypatch, order_log, failing=()):
    def make(name):
        async def f(audio):
            order_log.append(name)
            if name in failing:
                raise RuntimeError(f"{name} down")
            return {"text": "hi", "language": "Hindi", "provider": name}
        return f
    for name in ("sarvam", "groq", "openai", "local_whisper"):
        monkeypatch.setattr(stt_service, f"_transcribe_{name}", make(name))


def test_sarvam_primary_falls_back_to_groq(monkeypatch):
    log = []
    _patch_providers(monkeypatch, log, failing=("sarvam",))
    monkeypatch.setattr(settings, "STT_PRIMARY_PROVIDER", "sarvam")
    monkeypatch.setattr(settings, "STT_ENABLE_FALLBACK", True)
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "k")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "k")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    r = run(stt_service.transcribe(b"x"))
    assert log == ["sarvam", "groq"]
    assert r["provider"] == "groq"
    assert r["language"] == "hi"  # "Hindi" normalised for every provider


def test_sarvam_used_as_fallback_when_key_present(monkeypatch):
    log = []
    _patch_providers(monkeypatch, log, failing=("groq",))
    monkeypatch.setattr(settings, "STT_PRIMARY_PROVIDER", "groq")
    monkeypatch.setattr(settings, "STT_ENABLE_FALLBACK", True)
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "k")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "k")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    assert run(stt_service.transcribe(b"x"))["provider"] == "sarvam"
    assert log == ["groq", "sarvam"]
