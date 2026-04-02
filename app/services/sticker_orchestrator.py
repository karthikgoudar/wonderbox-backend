"""
Sticker Generation Orchestrator
================================
Owns the in-memory job registry and the full async pipeline.

Job lifecycle
-------------
queued  →  processing  →  done
                       →  error

Job dict shape
--------------
{
    "status":        "queued" | "processing" | "done" | "error",
    "progress_step": str | None,   # last named step
    "text":          str | None,   # STT transcript
    "language":      str | None,   # ISO-639 detected language
    "image_url":     str | None,   # URL set once upload succeeds
    "sticker_id":    str | None,   # DB id, set when saved
    "error":         str | None,   # human-readable error message
    "created_at":    float,        # time.time() – for TTL cleanup
}
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from app.db.session import SessionLocal
from app.models.child import Child
from app.models.device import Device
from app.models.sticker import Sticker
from app.models.user import User
from app.services import (
    image_processing,
    image_service,
    limits_service,
    notification_service,
    storage_service,
    stt_service,
    translation_service,
)
from app.services.analytics_service import track_event
from app.utils.constants import DEFAULT_EXPIRY_DAYS

logger = logging.getLogger(__name__)

# ── In-memory job storage (swap for Redis when scaling) ──────────────────────
# Replace with Redis: `await redis.hset(job_id, mapping=job_dict)`
jobs: dict[str, dict] = {}

JOB_TTL_SECONDS: int = 300  # clean up stale jobs after 5 minutes


# ── Job helpers ───────────────────────────────────────────────────────────────

def create_job(job_id: str) -> dict:
    """Initialise a new job entry and return it."""
    job: dict = {
        "status": "queued",
        "progress_step": None,
        "text": None,
        "language": None,
        "image_url": None,
        "sticker_id": None,
        "error": None,
        "created_at": time.time(),
    }
    jobs[job_id] = job
    logger.info(f"[{job_id}] Job created")
    return job


def get_job(job_id: str) -> Optional[dict]:
    """Return the job dict or None if it does not exist."""
    return jobs.get(job_id)


def _update(job_id: str, **kwargs) -> None:
    """Merge kwargs into the job dict (no-op if job is missing)."""
    if job_id in jobs:
        jobs[job_id].update(kwargs)


def purge_stale_jobs() -> None:
    """Remove jobs older than JOB_TTL_SECONDS. Call periodically if needed."""
    cutoff = time.time() - JOB_TTL_SECONDS
    stale = [jid for jid, j in jobs.items() if j.get("created_at", 0) < cutoff]
    for jid in stale:
        del jobs[jid]
    if stale:
        logger.info(f"Purged {len(stale)} stale job(s)")


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def run_sticker_pipeline(
    job_id: str,
    audio_bytes: bytes,
    device_id: str,
    child_id: str,
) -> None:
    """
    Full async sticker-generation pipeline.
    Called as a background task — never awaited directly by the route.

    Updates jobs[job_id] at every stage so the SSE stream can pick up
    changes by polling.
    """
    db = SessionLocal()
    try:
        logger.info(f"[{job_id}] Pipeline starting  device={device_id}  child={child_id}")

        # ── Step 1 — Mark processing ─────────────────────────────────────────
        _update(job_id, status="processing", progress_step="starting")

        # ── Step 2 — Validate device ─────────────────────────────────────────
        _update(job_id, progress_step="validating_device")
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            logger.warning(f"[{job_id}] Device not found: {device_id}")
            _update(job_id, status="error", error="Device not found")
            return

        # ── Step 3 — Validate child ──────────────────────────────────────────
        _update(job_id, progress_step="validating_child")
        child = db.query(Child).filter(Child.id == child_id).first()
        if not child:
            logger.warning(f"[{job_id}] Child not found: {child_id}")
            _update(job_id, status="error", error="Child not found")
            return

        user: Optional[User] = None
        if device.parent_id:
            user = db.query(User).filter(User.id == device.parent_id).first()

        # ── Step 4 — Limits check ────────────────────────────────────────────
        _update(job_id, progress_step="checking_limits")
        try:
            limits_service.check_limits(db, device)
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            logger.warning(f"[{job_id}] Limit check failed: {detail}")
            _update(job_id, status="error", error=detail)
            return

        # ── Step 5 — Speech-to-Text ──────────────────────────────────────────
        logger.info(f"[{job_id}] Running STT…")
        _update(job_id, progress_step="transcribing")
        stt = await stt_service.transcribe(audio_bytes)
        original_text: str = stt.get("text", "").strip()
        language: str = stt.get("language", "en")

        if not original_text:
            logger.warning(f"[{job_id}] STT returned empty transcript")
            _update(job_id, status="error", error="Could not transcribe audio")
            return

        # Expose transcript immediately so the stream can forward it
        _update(job_id, text=original_text, language=language)
        logger.info(f"[{job_id}] Transcript: '{original_text}' [{language}]")

        # ── Step 6 — Translation ─────────────────────────────────────────────
        _update(job_id, progress_step="translating")
        if language and not language.lower().startswith("en"):
            logger.info(f"[{job_id}] Translating from {language} → English")
            prompt_text = await translation_service.to_english(original_text, language)
        else:
            prompt_text = original_text

        # ── Step 7 — Prompt normalisation ────────────────────────────────────
        normalized_prompt = (
            f"{prompt_text}, simple black and white line drawing, "
            "bold outlines, sticker style"
        )
        logger.info(f"[{job_id}] Prompt: {normalized_prompt}")

        # ── Step 8 — Image generation ────────────────────────────────────────
        logger.info(f"[{job_id}] Generating image…")
        _update(job_id, progress_step="generating_image")
        image_bytes = await image_service.generate_from_prompt(normalized_prompt)
        if not image_bytes:
            logger.error(f"[{job_id}] Image generation returned empty bytes")
            _update(job_id, status="error", error="Image generation failed")
            return

        # ── Step 9 — Image processing (1-bit PNG for thermal printer) ────────
        logger.info(f"[{job_id}] Processing image to 1-bit PNG…")
        _update(job_id, progress_step="processing_image")
        processed = await image_processing.to_1bit_png(image_bytes)

        # ── Step 10 — Upload to storage → publish URL ────────────────────────
        logger.info(f"[{job_id}] Uploading to storage…")
        _update(job_id, progress_step="uploading")
        filename = (
            f"stickers/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{device_id}.png"
        )
        image_url = await storage_service.upload_bytes(processed, filename)

        # Expose image_url so the SSE stream can emit image_ready immediately
        _update(job_id, image_url=image_url)
        logger.info(f"[{job_id}] Image URL: {image_url}")

        # ── Step 11 — Persist sticker record ─────────────────────────────────
        logger.info(f"[{job_id}] Saving sticker to DB…")
        _update(job_id, progress_step="saving")
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

        # ── Step 12 — Increment usage ────────────────────────────────────────
        limits_service.increment_usage(db, device, amount=1)

        # ── Step 13 — Notification (stub) ────────────────────────────────────
        child_name = getattr(child, "name", "Your child")
        notification_service.send_sticker_created(
            db, sticker, message=f"{child_name} imagined: {original_text}"
        )

        # ── Step 14 — Analytics ──────────────────────────────────────────────
        track_event(
            db,
            "sticker.generate.success",
            user_id=getattr(user, "id", None),
            device_id=getattr(device, "id", None),
            properties={
                "sticker_id": sticker.id,
                "language": language,
                "job_id": job_id,
            },
        )

        # ── Step 15 — Mark done ──────────────────────────────────────────────
        _update(job_id, status="done", sticker_id=str(sticker.id), progress_step=None)
        logger.info(f"[{job_id}] Pipeline complete  sticker_id={sticker.id}")

    except Exception as exc:
        logger.exception(f"[{job_id}] Unhandled pipeline error: {exc}")
        _update(job_id, status="error", error=str(exc))
    finally:
        db.close()
