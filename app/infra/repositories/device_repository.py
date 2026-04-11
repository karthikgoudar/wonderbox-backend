from app.models.device import Device
from app.utils.security import generate_device_token, hash_token


def _prepare_token(device_data: dict) -> dict:
    payload = dict(device_data)
    raw_token = payload.get("token")

    if not raw_token:
        raw_token = generate_device_token()

    payload["token"] = hash_token(raw_token)
    payload["raw_token"] = raw_token
    return payload


def get_by_device_id(db, device_id: str):
    return db.query(Device).filter(Device.device_id == device_id).first()


def get_by_id(db, device_pk: int):
    return db.query(Device).filter(Device.id == device_pk).first()


def create(db, device_data: dict):
    prepared = _prepare_token(device_data)
    raw_token = prepared.pop("raw_token")
    device = Device(**prepared)
    db.add(device)
    db.commit()
    db.refresh(device)
    setattr(device, "raw_token", raw_token)
    return device


def update(db, device, updates: dict):
    payload = dict(updates)
    raw_token = None
    if "token" in payload and payload["token"]:
        raw_token = payload["token"]
        payload["token"] = hash_token(payload["token"])
    for key, value in payload.items():
        setattr(device, key, value)
    db.commit()
    db.refresh(device)
    if raw_token:
        setattr(device, "raw_token", raw_token)
    return device


def issue_new_token(db, device):
    raw_token = generate_device_token()
    device.token = hash_token(raw_token)
    db.commit()
    db.refresh(device)
    setattr(device, "raw_token", raw_token)
    return device


def backfill_missing_tokens(db) -> int:
    updated = 0
    devices = db.query(Device).filter(Device.token.is_(None)).all()
    for device in devices:
        device.token = hash_token(generate_device_token())
        updated += 1
    if updated:
        db.commit()
    return updated
