from fastapi import APIRouter, Form

from app.db.session import SessionLocal
from app.infra.repositories import device_repository

router = APIRouter()


@router.post("/device/{id}/pause")
def pause_device(id: str):
    return {"status": "paused", "device": id}


@router.post("/device/{id}/set-limit")
def set_limit(id: str):
    return {"status": "limit set", "device": id}


@router.post("/device/register")
def register_device(
    device_id: str = Form(...),
    parent_id: int = Form(...),
    child_id: int | None = Form(default=None),
):
    """Register a device and return a one-time raw token for provisioning."""
    db = SessionLocal()
    try:
        existing = device_repository.get_by_device_id(db, device_id)
        if existing:
            if not existing.token:
                existing = device_repository.issue_new_token(db, existing)
                return {
                    "status": "token_issued",
                    "device_id": existing.device_id,
                    "device_token": getattr(existing, "raw_token", None),
                }
            return {
                "status": "already_registered",
                "device_id": existing.device_id,
            }

        created = device_repository.create(
            db,
            {
                "device_id": device_id,
                "parent_id": parent_id,
                "child_id": child_id,
                "paused": False,
            },
        )
        return {
            "status": "registered",
            "device_id": created.device_id,
            "device_token": getattr(created, "raw_token", None),
        }
    finally:
        db.close()


@router.post("/device/{id}/rotate-token")
def rotate_device_token(id: str):
    """Rotate and return a new one-time raw device token."""
    db = SessionLocal()
    try:
        device = device_repository.get_by_device_id(db, id)
        if not device:
            return {"detail": "Device not found"}

        updated = device_repository.issue_new_token(db, device)
        return {
            "status": "rotated",
            "device": updated.device_id,
            "device_token": getattr(updated, "raw_token", None),
        }
    finally:
        db.close()
