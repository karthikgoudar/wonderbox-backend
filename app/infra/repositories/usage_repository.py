from datetime import date

from sqlalchemy import func

from app.models.usage import Usage


def get_today_by_device(db, device_pk: int, day: date):
    return db.query(Usage).filter(Usage.device_id == device_pk, Usage.date == day).first()


def get_total_for_day(db, day: date) -> int:
    return db.query(func.coalesce(func.sum(Usage.count), 0)).filter(Usage.date == day).scalar() or 0


def increment_for_day(db, device_pk: int, day: date, amount: int = 1) -> Usage:
    usage = get_today_by_device(db, device_pk=device_pk, day=day)
    if not usage:
        usage = Usage(device_id=device_pk, date=day, count=amount)
        db.add(usage)
    else:
        usage.count = usage.count + amount
    db.commit()
    return usage
