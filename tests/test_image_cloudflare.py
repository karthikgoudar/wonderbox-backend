"""Cloudflare Workers AI image provider and provider order (no network)."""

import asyncio
import base64
import io

import httpx
import pytest
from PIL import Image

from app.config.settings import settings
from app.services import image_service


def run(coro):
    return asyncio.run(coro)


def _jpeg_b64() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def cloudflare(monkeypatch):
    """Fake Cloudflare: records requests, replies with a small JPEG."""
    calls = []
    state = {"status": 200, "body": {"success": True, "result": {"image": _jpeg_b64()}}}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append({"url": str(request.url), "auth": request.headers.get("authorization"),
                      "json": __import__("json").loads(request.read())})
        return httpx.Response(state["status"], json=state["body"])

    monkeypatch.setattr(settings, "CLOUDFLARE_ACCOUNT_ID", "acc123")
    monkeypatch.setattr(settings, "CLOUDFLARE_API_TOKEN", "tok456")
    monkeypatch.setattr(settings, "CLOUDFLARE_IMAGE_STEPS", 4)
    monkeypatch.setattr(
        image_service, "_cloudflare_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    return type("C", (), {"calls": calls, "state": state})


def test_returns_png_and_sends_right_request(cloudflare):
    png = run(image_service._generate_cloudflare("a happy cat on a rocket"))
    assert png.startswith(b"\x89PNG")
    call = cloudflare.calls[0]
    assert call["url"].endswith("/accounts/acc123/ai/run/@cf/black-forest-labs/flux-1-schnell")
    assert call["auth"] == "Bearer tok456"
    assert call["json"]["steps"] == 4
    assert "a happy cat on a rocket" in call["json"]["prompt"]
    assert "coloring book" in call["json"]["prompt"]  # line-art style hints added


def test_steps_are_kept_in_range(cloudflare, monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_IMAGE_STEPS", 50)
    run(image_service._generate_cloudflare("x"))
    assert cloudflare.calls[0]["json"]["steps"] == 8


def test_error_reply_raises_with_message(cloudflare):
    cloudflare.state.update(status=429, body={"success": False, "errors": [{"message": "daily limit"}]})
    with pytest.raises(RuntimeError, match="daily limit"):
        run(image_service._generate_cloudflare("x"))


def test_missing_settings_raise(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_API_TOKEN", "")
    with pytest.raises(RuntimeError, match="not configured"):
        run(image_service._generate_cloudflare("x"))


def test_cloudflare_as_primary(cloudflare, monkeypatch):
    monkeypatch.setattr(settings, "IMAGE_PRIMARY_PROVIDER", "cloudflare")
    monkeypatch.setattr(settings, "IMAGE_ENABLE_FALLBACK", False)
    assert run(image_service.generate_from_prompt("x")).startswith(b"\x89PNG")


def test_cloudflare_as_fallback_when_replicate_fails(cloudflare, monkeypatch):
    monkeypatch.setattr(settings, "IMAGE_PRIMARY_PROVIDER", "replicate")
    monkeypatch.setattr(settings, "IMAGE_ENABLE_FALLBACK", True)
    monkeypatch.setattr(settings, "REPLICATE_API_TOKEN", "")
    monkeypatch.setattr(settings, "STABILITY_API_KEY", "")
    assert run(image_service.generate_from_prompt("x")).startswith(b"\x89PNG")
    assert len(cloudflare.calls) == 1
