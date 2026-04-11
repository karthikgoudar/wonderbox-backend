from typing import Optional

from fastapi import Depends, Form, Header
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services import auth_service, rate_limit_service


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_device(
    device_id: str = Form(...),
    x_device_token: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    device = auth_service.validate_device(db, device_id, x_device_token)
    rate_limit_service.check_rate_limit(device.device_id)
    return device
