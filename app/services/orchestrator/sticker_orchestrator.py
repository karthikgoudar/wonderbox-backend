import asyncio
from datetime import datetime, timedelta
import time
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.services import stt_service, translation_service, image_service, image_processing, storage_service, notification_service, limits_service
from app.models.device import Device
from app.models.child import Child
from app.models.user import User
from app.models.sticker import Sticker
from app.utils.constants import DEFAULT_EXPIRY_DAYS


async def generate_sticker(db: Session, device_id: str, audio_file: UploadFile) -> dict:
    start = time.perf_counter()

    # Step 1 — Fetch Device + Child + User
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    child = None
    user = None
    if device.child_id:
        child = db.query(Child).filter(Child.id == device.child_id).first()
    if device.parent_id:
        user = db.query(User).filter(User.id == device.parent_id).first()

    # Step 2 — LIMIT CHECK
    limits_service.check_limits(db, device)

    # Step 3 — Speech to Text
    audio_bytes = await audio_file.read()
    stt = await stt_service.transcribe(audio_bytes)
    original_text = stt.get("text")
    language = stt.get("language", "en")
    if not original_text:
        raise HTTPException(status_code=400, detail="Could not transcribe audio")

    # Step 4 — Translation
    if language and not language.lower().startswith("en"):
        prompt_text = await translation_service.to_english(original_text, language)
    else:
        prompt_text = original_text

    # Step 5 — Normalize Prompt
    normalized_prompt = f"{prompt_text}, simple black and white line drawing, bold outlines, sticker style"

    # Step 6 — Image Generation
    image_bytes = await image_service.generate_from_prompt(normalized_prompt)
    if not image_bytes:
        raise HTTPException(status_code=500, detail="Image generation failed")

    # Step 7 — Image Processing
    processed = await image_processing.to_1bit_png(image_bytes)

    # Step 8 — Upload to Storage
    filename = f"stickers/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{device_id}.png"
    image_url = await storage_service.upload_bytes(processed, filename)

    # Step 9 — Save to Database
    expires_at = datetime.utcnow() + timedelta(days=DEFAULT_EXPIRY_DAYS)
    sticker = Sticker(
        user_id=getattr(user, "id", None),
        device_id=getattr(device, "id", None),
        child_id=getattr(child, "id", None),
        original_text=original_text,
        normalized_prompt=normalized_prompt,
        language=language,
        image_url=image_url,
        expires_at=expires_at,
    )
    db.add(sticker)
    db.commit()
    db.refresh(sticker)

    # Step 10 — Update Usage
    limits_service.increment_usage(db, device, amount=1)

    # Step 11 — Notification
    child_name = getattr(child, "name", "Your child")
    note_msg = f"{child_name} imagined a {original_text} 🧠✨"
    notification_service.send_sticker_created(db, sticker, message=note_msg)

    # Step 12 — Return Response
    elapsed = time.perf_counter() - start
    return {
        "status": "success",
        "image_url": image_url,
        "prompt": normalized_prompt,
        "sticker_id": sticker.id,
        "timings": {"elapsed_seconds": elapsed},
    }
