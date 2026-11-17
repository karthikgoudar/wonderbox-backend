"""OpenAI image provider and its place in the provider order (no network)."""

import asyncio
import base64
import io
import json

import httpx
import pytest
from PIL import Image

from app.config.settings import settings
from app.services import image_service


def run(coro):
    return asyncio.run(coro)


def _png_b64() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def openai(monkeypatch):
    """Fake OpenAI images endpoint: records requests, replies with a small PNG."""
    calls = []
    state = {"status": 200, "body": {"data": [{"b64_json": _png_b64()}]}}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append({"url": str(request.url), "auth": request.headers.get("authorization"),
                      "json": json.loads(request.read())})
        return httpx.Response(state["status"], json=state["body"])

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "OPENAI_IMAGE_MODEL", "gpt-image-1.5")
    monkeypatch.setattr(settings, "OPENAI_IMAGE_QUALITY", "medium")
    monkeypatch.setattr(settings, "OPENAI_IMAGE_SIZE", "1024x1024")
    monkeypatch.setattr(
        image_service, "_openai_image_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    return type("O", (), {"calls": calls, "state": state})


@pytest.fixture
def no_cloudflare(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCOUNT_ID", "")
    monkeypatch.setattr(settings, "CLOUDFLARE_API_TOKEN", "")
    monkeypatch.setattr(settings, "REPLICATE_API_TOKEN", "")
    monkeypatch.setattr(settings, "STABILITY_API_KEY", "")


def test_returns_png_and_sends_right_request(openai):
    png = run(image_service._generate_openai("a happy cat on a rocket"))
    assert png.startswith(b"\x89PNG")
    call = openai.calls[0]
    assert call["url"] == "https://api.openai.com/v1/images/generations"
    assert call["auth"] == "Bearer sk-test"
    body = call["json"]
    assert body["model"] == "gpt-image-1.5" and body["quality"] == "medium"
    assert body["size"] == "1024x1024" and body["n"] == 1
    assert "response_format" not in body  # GPT Image models reject it
    assert "a happy cat on a rocket" in body["prompt"] and "coloring book" in body["prompt"]


def test_dalle_asks_for_base64_and_skips_quality(openai, monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_IMAGE_MODEL", "dall-e-3")
    run(image_service._generate_openai("x"))
    body = openai.calls[0]["json"]
    assert body["response_format"] == "b64_json" and "quality" not in body


def test_no_credit_error_is_readable(openai):
    openai.state.update(status=429, body={"error": {
        "code": "credit_balance_exhausted", "message": "You have no credits remaining."}})
    with pytest.raises(RuntimeError, match="credit_balance_exhausted"):
        run(image_service._generate_openai("x"))


def test_missing_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    with pytest.raises(RuntimeError, match="not configured"):
        run(image_service._generate_openai("x"))


def test_openai_as_primary(openai, no_cloudflare, monkeypatch):
    monkeypatch.setattr(settings, "IMAGE_PRIMARY_PROVIDER", "openai")
    assert run(image_service.generate_from_prompt("x")).startswith(b"\x89PNG")
    assert len(openai.calls) == 1


def test_cloudflare_backs_up_openai_when_out_of_credit(openai, monkeypatch):
    """No credit on OpenAI: the free Cloudflare picture is used instead."""
    openai.state.update(status=429, body={"error": {"code": "credit_balance_exhausted"}})
    cf_calls = []

    async def fake_cloudflare(prompt):
        cf_calls.append(prompt)
        return b"\x89PNG-cloudflare"

    monkeypatch.setattr(image_service, "_generate_cloudflare", fake_cloudflare)
    monkeypatch.setattr(settings, "IMAGE_PRIMARY_PROVIDER", "openai")
    monkeypatch.setattr(settings, "IMAGE_ENABLE_FALLBACK", True)
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCOUNT_ID", "acc")
    monkeypatch.setattr(settings, "CLOUDFLARE_API_TOKEN", "tok")
    assert run(image_service.generate_from_prompt("x")) == b"\x89PNG-cloudflare"
    assert len(openai.calls) == 1 and cf_calls == ["x"]


def test_openai_is_never_a_silent_paid_fallback(no_cloudflare, monkeypatch):
    called = []

    async def fake_openai(prompt):
        called.append(prompt)
        return b"png"

    monkeypatch.setattr(image_service, "_generate_openai", fake_openai)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "IMAGE_PRIMARY_PROVIDER", "replicate")
    monkeypatch.setattr(settings, "IMAGE_ENABLE_FALLBACK", True)
    with pytest.raises(RuntimeError):
        run(image_service.generate_from_prompt("x"))
    assert called == []
