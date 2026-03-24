from datetime import date
from sqlalchemy import func
from fastapi import HTTPException
from app.models.usage import Usage
from app.config.settings import settings


COMPANY_DAILY_LIMIT = int(getattr(settings, "COMPANY_DAILY_LIMIT", 1000))


def check_limits(db, device):
    # 1. paused
    if getattr(device, "paused", False):
        raise HTTPException(status_code=403, detail="Device is paused")

    # 2. device daily limit
    today = date.today()
    usage = db.query(Usage).filter(Usage.device_id == device.id, Usage.date == today).first()
    current = usage.count if usage else 0
    if device.daily_limit is not None and current >= device.daily_limit:
        raise HTTPException(status_code=429, detail="Device daily limit reached")

    # 3. company limit (sum of all usages today)
    total_today = db.query(func.coalesce(func.sum(Usage.count), 0)).filter(Usage.date == today).scalar() or 0
    if COMPANY_DAILY_LIMIT and total_today >= COMPANY_DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Company daily limit reached")

    return True


def increment_usage(db, device, amount: int = 1):
    today = date.today()
    usage = db.query(Usage).filter(Usage.device_id == device.id, Usage.date == today).first()
    if not usage:
        usage = Usage(device_id=device.id, date=today, count=amount)
        db.add(usage)
    else:
        usage.count = usage.count + amount
    db.commit()
    return usage
