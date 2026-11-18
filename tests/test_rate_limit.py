"""Device rate limit reads its numbers from settings (no network)."""

import pytest
from fastapi import HTTPException

from app.config.settings import settings
from app.services import rate_limit_service as rl


@pytest.fixture(autouse=True)
def clean_state():
    rl.device_requests.clear()
    rl.device_violations.clear()
    yield
    rl.device_requests.clear()
    rl.device_violations.clear()


def test_default_blocks_fifth_request_in_a_minute(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_MAX_REQUESTS", 4)
    for _ in range(4):
        rl.check_rate_limit("d1")
    with pytest.raises(HTTPException) as e:
        rl.check_rate_limit("d1")
    assert e.value.status_code == 429
    with pytest.raises(HTTPException) as e:
        rl.check_rate_limit("d1")
    assert e.value.status_code == 403  # now blocked


def test_demo_limit_allows_more(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_MAX_REQUESTS", 30)
    for _ in range(30):
        rl.check_rate_limit("d1")
    with pytest.raises(HTTPException):
        rl.check_rate_limit("d1")


def test_block_length_comes_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_MAX_REQUESTS", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_BLOCK_SECONDS", 30)
    rl.check_rate_limit("d1")
    with pytest.raises(HTTPException):
        rl.check_rate_limit("d1")
    assert 29 <= rl.device_violations["d1"] - __import__("time").time() <= 30


def test_devices_are_counted_separately(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_MAX_REQUESTS", 1)
    rl.check_rate_limit("d1")
    rl.check_rate_limit("d2")  # a different device is not affected
