from datetime import datetime, timedelta
import logging
from typing import Optional

from fastapi import HTTPException, status
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.user import User
from app.infra.repositories import device_repository, user_repository
from app.utils.security import hash_token


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    expire_minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expires_at = datetime.utcnow() + timedelta(minutes=expire_minutes)
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        subject = payload.get("sub")
        if not subject:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return subject
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = user_repository.get_by_email(db, email)
    if not user or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user


def validate_device(db: Session, device_id: Optional[str] = None, device_token: Optional[str] = None):
    """
    Validate device by token and/or device_id.
    Allows header-only authentication (e.g. from ESP32 sending x-device-token),
    as well as form-based authentication.
    """
    device = None

    if device_token:
        hashed_token = hash_token(device_token)
        # Match either hashed token or raw token in DB
        device = (
            device_repository.get_by_token(db, hashed_token)
            or device_repository.get_by_token(db, device_token)
        )
        if not device and device_id:
            device = device_repository.get_by_device_id(db, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")
            expected_token = getattr(device, "token", None)
            if expected_token != hashed_token and expected_token != device_token:
                logger.warning(f"Invalid token for device {device_id}")
                raise HTTPException(status_code=401, detail="Invalid device token")
        elif not device:
            raise HTTPException(status_code=401, detail="Invalid device token")

        if device_id and device.device_id != device_id:
            logger.warning(f"Device ID mismatch: requested {device_id}, token belongs to {device.device_id}")
            raise HTTPException(status_code=401, detail="Device ID mismatch")

    elif device_id:
        device = device_repository.get_by_device_id(db, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        if getattr(device, "token", None):
            logger.warning(f"Device token required for device {device_id}")
            raise HTTPException(status_code=401, detail="Device token required")
    else:
        raise HTTPException(status_code=401, detail="Device credentials required (X-Device-Token or device_id)")

    return device
