"""Shared test helpers."""

import asyncio

import pytest

from app.orchestrator import sticker_orchestrator as orch


class FakeDB:
    def commit(self):
        pass

    def close(self):
        pass


class Thing:
    def __init__(self, **kw):
        self.__dict__.update(kw)


@pytest.fixture
def pipeline(monkeypatch):
    calls = {"image": 0}
    stt_reply = {}

    async def fake_transcribe(audio):
        return dict(stt_reply)

    async def fake_image(prompt):
        calls["image"] += 1
        raise RuntimeError("stop here")  # far enough to prove the gate let it through

    monkeypatch.setattr(orch, "SessionLocal", FakeDB)
    monkeypatch.setattr(orch.device_repository, "get_by_device_id",
                        lambda db, d: Thing(id=1, child_id=None, parent_id=None))
    monkeypatch.setattr(orch.child_repository, "get_by_id",
                        lambda db, c: Thing(id=7, date_of_birth=None))
    monkeypatch.setattr(orch.limits_service, "check_limits", lambda db, device: None)
    monkeypatch.setattr(orch.stt_service, "transcribe", fake_transcribe)
    monkeypatch.setattr(orch.image_service, "generate_from_prompt", fake_image)
    monkeypatch.setattr(orch, "RETRYABLE_ATTEMPTS", 1)
    from app.config.settings import settings
    monkeypatch.setattr(settings, "PROMPT_REWRITE", False)   # never call a real model in tests

    def go(reply):
        stt_reply.clear()
        stt_reply.update(reply)
        orch.create_job("j")
        asyncio.run(orch.run_sticker_pipeline("j", b"RIFF", "dev", "7"))
        return orch.get_job("j"), calls["image"]

    yield go
    orch.jobs.pop("j", None)
    orch.active_device_jobs.clear()
