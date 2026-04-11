# Daily limits guard for device + company totals
from datetime import date
from fastapi import HTTPException
from app.infra.repositories import usage_repository
from app.config.settings import settings


COMPANY_DAILY_LIMIT = int(getattr(settings, "COMPANY_DAILY_LIMIT", 1000))


def check_limits(db, device):
    # 1. paused
    if getattr(device, "paused", False):
        raise HTTPException(status_code=403, detail="Device is paused")

    # 2. device daily limit
    today = date.today()
    usage = usage_repository.get_today_by_device(db, device_pk=device.id, day=today)
    current = usage.count if usage else 0
    if device.daily_limit is not None and current >= device.daily_limit:
        raise HTTPException(status_code=429, detail="Device daily limit reached")

    # 3. company daily limit (sum of all usages today)
    total_today = usage_repository.get_total_for_day(db, day=today)
    if COMPANY_DAILY_LIMIT and total_today >= COMPANY_DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Company daily limit reached")

    return True


def increment_usage(db, device, amount: int = 1):
    today = date.today()
    usage = usage_repository.increment_for_day(db, device_pk=device.id, day=today, amount=amount)
    return usage
