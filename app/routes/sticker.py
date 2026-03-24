from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.db.session import get_db
from app.services import stt_service, translation_service, image_service, image_processing, storage_service, notification_service
from app.utils.tlv_encoder import create_tlv_for_image
from app.utils.constants import DEFAULT_EXPIRY_DAYS
from app.models.sticker import Sticker

router = APIRouter()


@router.post("/sticker")
async def create_sticker(device_id: str = Form(...), audio: UploadFile = File(...), db: Session = Depends(get_db)):
    # 1. Run STT (mock)
    audio_bytes = await audio.read()
    stt_result = await stt_service.transcribe(audio_bytes)
    text = stt_result.get("text")
    lang = stt_result.get("language", "en")

    # 2. Translate if needed
    normalized = await translation_service.to_english(text, lang)

    # 3. Normalize prompt (simple pass-through for now)
    prompt = normalized

    # 4. Generate image
    image_bytes = await image_service.generate_from_prompt(prompt)

    # 5. Process to 1-bit printer-ready
    processed = await image_processing.to_1bit_png(image_bytes)

    # 6. Upload to storage
    image_url = await storage_service.upload_bytes(processed, f"stickers/{datetime.utcnow().isoformat()}.png")

    # 7. Save DB record (minimal)
    expires_at = datetime.utcnow() + timedelta(days=DEFAULT_EXPIRY_DAYS)
    sticker = Sticker(original_text=text, normalized_prompt=prompt, language=lang, image_url=image_url, expires_at=expires_at)
    db.add(sticker)
    db.commit()
    db.refresh(sticker)

    # 8. Notify
    notification_service.send_sticker_created(db, sticker, message=f"{sticker.id} created")

    # 9. Build TLV and return binary to device
    tlv = create_tlv_for_image(processed)
    return Response(content=tlv, media_type="application/octet-stream")
