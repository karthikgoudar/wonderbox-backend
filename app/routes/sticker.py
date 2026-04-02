import asyncio
import json

from fastapi import APIRouter, UploadFile, File, Form, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.db.session import get_db
from app.db.session import SessionLocal
from app.services import stt_service, translation_service, image_service, image_processing, storage_service, notification_service
from app.services.analytics_service import track_event
from app.services.sticker_job_manager import (
    create_job,
    get_job,
    publish_event,
    set_done,
    set_error,
    set_running,
    stream_events,
)
from app.services.orchestrator.sticker_orchestrator import generate_sticker_with_events
from app.utils.tlv_encoder import create_tlv_for_image
from app.utils.constants import DEFAULT_EXPIRY_DAYS
from app.models.sticker import Sticker

router = APIRouter()


def _sse_format(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _run_sticker_job(job_id: str, device_id: str, audio_bytes: bytes):
    db = SessionLocal()
    try:
        await set_running(job_id)

        async def emit(event: str, data: dict):
            await publish_event(job_id, event, data)

        result = await generate_sticker_with_events(db=db, device_id=device_id, audio_bytes=audio_bytes, event_cb=emit)
        await set_done(job_id, result)
    except Exception as exc:
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        await set_error(job_id, str(detail), status_code=status_code)
    finally:
        db.close()


@router.post("/sticker/submit")
async def submit_sticker(device_id: str = Form(...), audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    job = await create_job(device_id=device_id)
    asyncio.create_task(_run_sticker_job(job.id, device_id, audio_bytes))
    return {
        "status": "accepted",
        "job_id": job.id,
        "stream_url": f"/sticker/{job.id}/stream",
    }


@router.get("/sticker/{job_id}/stream")
async def stream_sticker(job_id: str):
    job = await get_job(job_id)
    if not job:
        return Response(content=json.dumps({"detail": "Job not found"}), status_code=404, media_type="application/json")

    async def event_generator():
        async for item in stream_events(job_id):
            yield _sse_format(item["event"], item["data"])

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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

    track_event(
        db,
        "sticker.route.success",
        properties={"sticker_id": sticker.id, "language": lang, "device_external_id": device_id},
    )

    # 8. Notify
    notification_service.send_sticker_created(db, sticker, message=f"{sticker.id} created")

    # 9. Build TLV and return binary to device
    tlv = create_tlv_for_image(processed)
    return Response(content=tlv, media_type="application/octet-stream")
