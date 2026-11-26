"""Rewriting English speech that hides Kannada/Hindi words (no network)."""

import asyncio
import json

import httpx
import pytest

from app.config.settings import settings
from app.services import prompt_rewrite


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def llm(monkeypatch):
    """Fake Groq/OpenAI: answers per host, records requests."""
    calls = []
    replies = {"api.groq.com": (200, "Monkey tractor on Mars"), "api.openai.com": (200, "A monkey tractor on Mars")}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append({"host": request.url.host, "model": body["model"], "auth": request.headers.get("authorization"),
                      "messages": body["messages"]})
        status, text = replies[request.url.host]
        if status != 200:
            return httpx.Response(status, json={"error": "nope"})
        return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})

    monkeypatch.setattr(settings, "PROMPT_REWRITE", True)
    monkeypatch.setattr(settings, "PROMPT_REWRITE_PROVIDERS", ["groq", "openai"])
    monkeypatch.setattr(settings, "GROQ_API_KEY", "g-key")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "o-key")
    monkeypatch.setattr(prompt_rewrite, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    return type("L", (), {"calls": calls, "replies": replies})


def test_groq_first(llm):
    assert run(prompt_rewrite.rewrite("Manga Tractory on Mars")) == "Monkey tractor on Mars"
    assert [c["host"] for c in llm.calls] == ["api.groq.com"]
    call = llm.calls[0]
    assert call["model"] == settings.PROMPT_REWRITE_GROQ_MODEL and call["auth"] == "Bearer g-key"
    assert call["messages"][1] == {"role": "user", "content": "Manga Tractory on Mars"}
    assert "manga" in call["messages"][0]["content"].lower()


def test_openai_backs_up_groq(llm):
    llm.replies["api.groq.com"] = (429, "")
    assert run(prompt_rewrite.rewrite("Manga Tractory on Mars")) == "A monkey tractor on Mars"
    assert [c["host"] for c in llm.calls] == ["api.groq.com", "api.openai.com"]


def test_everything_failing_keeps_the_childs_words(llm):
    llm.replies["api.groq.com"] = (500, "")
    llm.replies["api.openai.com"] = (401, "")
    assert run(prompt_rewrite.rewrite("Manga Tractory on Mars")) == "Manga Tractory on Mars"


@pytest.mark.parametrize("reply", ["", "   ", "Line one\nLine two", "x" * 500])
def test_odd_replies_are_not_used(llm, reply):
    llm.replies["api.groq.com"] = (200, reply)
    llm.replies["api.openai.com"] = (200, reply)
    assert run(prompt_rewrite.rewrite("Aane playing football")) == "Aane playing football"


def test_quotes_are_trimmed(llm):
    llm.replies["api.groq.com"] = (200, '"Elephant playing football"')
    assert run(prompt_rewrite.rewrite("Aane playing football")) == "Elephant playing football"


def test_missing_key_skips_that_provider(llm, monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    assert run(prompt_rewrite.rewrite("Manga Tractory on Mars")) == "A monkey tractor on Mars"
    assert [c["host"] for c in llm.calls] == ["api.openai.com"]


def test_switched_off(llm, monkeypatch):
    monkeypatch.setattr(settings, "PROMPT_REWRITE", False)
    assert run(prompt_rewrite.rewrite("Manga Tractory on Mars")) == "Manga Tractory on Mars"
    assert llm.calls == []


# ── In the sticker pipeline ──────────────────────────────────────────────────

@pytest.fixture
def seen(monkeypatch):
    log = []

    async def fake(text):
        log.append(text)
        return "Monkey tractor on Mars"

    monkeypatch.setattr(prompt_rewrite, "rewrite", fake)
    return log


def test_english_speech_is_rewritten_before_drawing(pipeline, seen, monkeypatch):
    from app.orchestrator import sticker_orchestrator as orch
    prompts = []
    monkeypatch.setattr(orch.prompt_builder, "build_sticker_prompt",
                        lambda text, child_age=None: prompts.append(text) or text)
    job, images = pipeline({"text": "Manga Tractory on Mars", "language": "en"})
    assert seen == ["Manga Tractory on Mars"]
    assert prompts == ["Monkey tractor on Mars"]
    assert job["text"] == "Manga Tractory on Mars"          # the screen still shows what was heard


def test_translated_speech_and_story_requests_skip_the_rewrite(pipeline, seen):
    pipeline({"text": "ಆನೆ", "language": "kn", "english_text": "An elephant"})
    pipeline({"text": "Tell me a story", "language": "en"})
    assert seen == []
