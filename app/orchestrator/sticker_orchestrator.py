"""
Sticker Generation Orchestrator
================================
Owns the in-memory job registry and the full async pipeline.

Job lifecycle
-------------
queued  →  processing  →  done
                       →  error
                       →  cancelled

Job dict shape
--------------
{
    "status":        "queued" | "processing" | "done" | "error" | "cancelled",
    "progress_step": str | None,
    "text":          str | None,
    "language":      str | None,
    "image_url":     str | None,
    "sticker_id":    str | None,
    "error":         dict | None,
    "created_at":    float,
}
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Optional

from app.db.session import SessionLocal
from app.models.sticker import Sticker
from app.infra.repositories import child_repository, device_repository, user_repository
from app.services import (
    image_processing,
    image_service,
    limits_service,
    prompt_builder,
    stt_service,
    translation_service,
)
from app.infra import storage_service
from app.side_effects import notification_service
from app.side_effects.analytics_service import track_event
from app.utils.constants import DEFAULT_EXPIRY_DAYS

logger = logging.getLogger(__name__)

jobs: dict[str, dict] = {}
active_device_jobs: dict[str, str] = {}

JOB_TTL_SECONDS: int = 300

STT_TIMEOUT_SECONDS: int = 10
TRANSLATION_TIMEOUT_SECONDS: int = 5
IMAGE_GENERATION_TIMEOUT_SECONDS: int = 20
IMAGE_PROCESSING_TIMEOUT_SECONDS: int = 10
UPLOAD_TIMEOUT_SECONDS: int = 10

RETRYABLE_ATTEMPTS: int = 3


class PipelineError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def create_job(job_id: str) -> dict:
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
    return jobs.get(job_id)


def _update(job_id: str, **kwargs) -> None:
    if job_id not in jobs:
        return

    current_status = jobs[job_id].get("status")
    if current_status in {"done", "cancelled"} and "status" not in kwargs:
        return

    jobs[job_id].update(kwargs)


def purge_stale_jobs() -> None:
    cutoff = time.time() - JOB_TTL_SECONDS
    stale = [jid for jid, j in jobs.items() if j.get("created_at", 0) < cutoff]
    for jid in stale:
        del jobs[jid]
    if stale:
        logger.info(f"Purged {len(stale)} stale job(s)")


def _build_error(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def _set_error(job_id: str, code: str, message: str) -> None:
    _update(job_id, status="error", error=_build_error(code, message), progress_step=None)


def _is_cancelled(job_id: str) -> bool:
    job = get_job(job_id)
    return bool(job and job.get("status") == "cancelled")


def _check_cancelled(job_id: str, step_name: str) -> bool:
    if not _is_cancelled(job_id):
        return False
    logger.info(f"[{job_id}] Cancelled before step={step_name}")
    _update(job_id, progress_step=None)
    return True


def _log_step_duration(job_id: str, step_name: str, started_at: float) -> None:
    elapsed = time.perf_counter() - started_at
    logger.info(f"[{job_id}] Step completed step={step_name} duration={elapsed:.3f}s")


async def _run_with_timeout(
    *,
    job_id: str,
    step_name: str,
    timeout: float,
    operation: Callable[[], Awaitable[Any]],
) -> Any:
    started_at = time.perf_counter()
    try:
        result = await asyncio.wait_for(operation(), timeout=timeout)
        _log_step_duration(job_id, step_name, started_at)
        return result
    except asyncio.TimeoutError as exc:
        logger.warning(f"[{job_id}] Timeout step={step_name} timeout={timeout}s")
        raise PipelineError("TIMEOUT", f"{step_name} timed out after {timeout} seconds") from exc


async def _run_with_retry(
    *,
    job_id: str,
    step_name: str,
    timeout: float,
    operation: Callable[[], Awaitable[Any]],
    failure_code: str,
    failure_message: str,
    attempts: int = RETRYABLE_ATTEMPTS,
) -> Any:
    last_error: Exception | None = None

    for attempt in range(attempts):
        if _check_cancelled(job_id, step_name):
            raise PipelineError("UNKNOWN_ERROR", "Job was cancelled")

        try:
            return await _run_with_timeout(
                job_id=job_id,
                step_name=step_name,
                timeout=timeout,
                operation=operation,
            )
        except PipelineError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt == attempts - 1:
                break

            backoff = 0.5 * (2 ** attempt)
            logger.warning(
                f"[{job_id}] Retry step={step_name} attempt={attempt + 2}/{attempts} backoff={backoff:.1f}s error={exc}"
            )
            await asyncio.sleep(backoff)

    logger.warning(f"[{job_id}] Failed step={step_name} attempts={attempts} error={last_error}")
    raise PipelineError(failure_code, failure_message) from last_error


async def run_sticker_pipeline(
    job_id: str,
    audio_bytes: bytes,
    device_id: str,
    child_id: str,
    device_token: Optional[str] = None,
) -> None:
    job = get_job(job_id)
    if not job:
        logger.warning(f"[{job_id}] Missing job state; aborting pipeline start")
        return

    current_status = job.get("status")
    if current_status == "done":
        logger.info(f"[{job_id}] Skipping duplicate execution; job already done")
        return
    if current_status == "processing":
        logger.info(f"[{job_id}] Skipping duplicate execution; job already processing")
        return
    if current_status == "cancelled":
        logger.info(f"[{job_id}] Skipping execution; job already cancelled")
        return

    db = SessionLocal()
    try:
        logger.info(f"[{job_id}] Pipeline starting device={device_id} child={child_id}")
        _update(job_id, status="processing", progress_step="starting", error=None)

        if not audio_bytes:
            logger.warning(f"[{job_id}] Audio payload is empty")
            _set_error(job_id, "STT_FAILED", "Audio payload is empty")
            return

        existing_job_id = active_device_jobs.get(device_id)
        if existing_job_id and existing_job_id != job_id:
            logger.warning(f"[{job_id}] Device busy device={device_id} active_job={existing_job_id}")
            _set_error(job_id, "DEVICE_BUSY", "Another sticker job is already running for this device")
            return
        active_device_jobs[device_id] = job_id

        if _check_cancelled(job_id, "validating_device"):
            return
        _update(job_id, progress_step="validating_device")
        device = device_repository.get_by_device_id(db, device_id)
        if not device:
            logger.warning(f"[{job_id}] Device not found: {device_id}")
            _set_error(job_id, "DEVICE_NOT_FOUND", "Device not found")
            return

        if _check_cancelled(job_id, "validating_child"):
            return
        _update(job_id, progress_step="validating_child")
        child = child_repository.get_by_id(db, child_id)
        if not child:
            logger.warning(f"[{job_id}] Child not found: {child_id}")
            _set_error(job_id, "CHILD_NOT_FOUND", "Child not found")
            return

        if device.child_id != child.id:
            logger.warning(
                f"[{job_id}] Child mismatch device_child_id={device.child_id} requested_child_id={child.id}"
            )
            _set_error(job_id, "CHILD_MISMATCH", "Child mismatch")
            return

        user = None
        if device.parent_id:
            user = user_repository.get_by_id(db, device.parent_id)

        if _check_cancelled(job_id, "checking_limits"):
            return
        _update(job_id, progress_step="checking_limits")
        try:
            limits_service.check_limits(db, device)
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            logger.warning(f"[{job_id}] Limit check failed: {detail}")
            _set_error(job_id, "LIMIT_EXCEEDED", str(detail))
            return

        if _check_cancelled(job_id, "transcribing"):
            return
        logger.info(f"[{job_id}] Running STT")
        _update(job_id, progress_step="transcribing")
        try:
            stt = await _run_with_timeout(
                job_id=job_id,
                step_name="stt",
                timeout=STT_TIMEOUT_SECONDS,
                operation=lambda: stt_service.transcribe(audio_bytes),
            )
        except PipelineError as exc:
            _set_error(job_id, exc.code, exc.message)
            return
        except Exception as exc:
            logger.warning(f"[{job_id}] STT failed error={exc}")
            _set_error(job_id, "STT_FAILED", "Could not transcribe audio")
            return

        original_text = str(stt.get("text", "") or "").strip()
        language = str(stt.get("language", "en") or "en").strip().lower()
        if not original_text:
            logger.warning(f"[{job_id}] STT returned empty transcript")
            _set_error(job_id, "STT_FAILED", "Could not transcribe audio")
            return
        
        prompt_text = original_text
        
        _update(job_id, text=original_text, language=language)
        logger.info(f"[{job_id}] Transcript='{original_text}' language={language}")

        # if _check_cancelled(job_id, "translating"):
           # return
        # _update(job_id, progress_step="translating")
        # if language and not language.startswith("en"):
            # logger.info(f"[{job_id}] Translating from {language} to English")
            # try:
                # prompt_text = await _run_with_retry(
                  # job_id=job_id,
                    # step_name="translation",
                    # timeout=TRANSLATION_TIMEOUT_SECONDS,
                    # operation=lambda: translation_service.to_english(original_text, language),
                    # failure_code="TRANSLATION_FAILED",
                    # failure_message="Translation failed",
                #)
            # except PipelineError as exc:
               # _set_error(job_id, exc.code, exc.message)
                # return

        if _check_cancelled(job_id, "normalizing_prompt"):
            return
        
        # Calculate child's age from date of birth
        child_age = None
        if child.date_of_birth:
            today = datetime.now().date()
            age_delta = today - child.date_of_birth
            child_age = age_delta.days // 365  # Simple age calculation
            logger.info(f"[{job_id}] Child age: {child_age} years")
        
        # Build age-appropriate prompt
        normalized_prompt = prompt_builder.build_sticker_prompt(prompt_text, child_age=child_age)
        logger.info(f"[{job_id}] Prompt={normalized_prompt}")

        if _check_cancelled(job_id, "generating_image"):
            return
        logger.info(f"[{job_id}] Generating image")
        _update(job_id, progress_step="generating_image")
        try:
            image_bytes = await _run_with_retry(
                job_id=job_id,
                step_name="image_generation",
                timeout=IMAGE_GENERATION_TIMEOUT_SECONDS,
                operation=lambda: image_service.generate_from_prompt(normalized_prompt),
                failure_code="IMAGE_GENERATION_FAILED",
                failure_message="Image generation failed",
            )
        except PipelineError as exc:
            _set_error(job_id, exc.code, exc.message)
            return

        if not image_bytes:
            logger.warning(f"[{job_id}] Image generation returned empty bytes")
            _set_error(job_id, "IMAGE_GENERATION_FAILED", "Image generation failed")
            return

        if _check_cancelled(job_id, "processing_image"):
            return
        # logger.info(f"[{job_id}] Processing image")
        # _update(job_id, progress_step="processing_image")
        # try:
        #     processed = await _run_with_timeout(
        #         job_id=job_id,
        #         step_name="image_processing",
        #         timeout=IMAGE_PROCESSING_TIMEOUT_SECONDS,
        #         operation=lambda: image_processing.to_1bit_png(image_bytes),
        #     )
        # except PipelineError as exc:
        #     _set_error(job_id, exc.code, exc.message)
        #     return
        # except Exception as exc:
        #     logger.warning(f"[{job_id}] Image processing failed error={exc}")
        #     _set_error(job_id, "IMAGE_PROCESSING_FAILED", "Image processing failed")
        #     return

        # if not processed:
        #     logger.warning(f"[{job_id}] Image processing returned empty bytes")
        #     _set_error(job_id, "IMAGE_PROCESSING_FAILED", "Image processing failed")
        #     return

        if _check_cancelled(job_id, "uploading"):
            return
        logger.info(f"[{job_id}] Uploading to storage")
        _update(job_id, progress_step="uploading")
        filename = f"stickers/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{device_id}.png"
        try:
            image_url = await _run_with_retry(
                job_id=job_id,
                step_name="upload",
                timeout=UPLOAD_TIMEOUT_SECONDS,
                operation=lambda: storage_service.upload_bytes(image_bytes, filename),
                failure_code="UPLOAD_FAILED",
                failure_message="Image upload failed",
            )
        except PipelineError as exc:
            _set_error(job_id, exc.code, exc.message)
            return

        _update(job_id, image_url=image_url)
        logger.info(f"[{job_id}] Image URL={image_url}")

        if _check_cancelled(job_id, "saving"):
            return
        logger.info(f"[{job_id}] Saving sticker to DB")
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
        try:
            db.add(sticker)
            db.commit()
            db.refresh(sticker)
        except Exception as exc:
            db.rollback()
            logger.exception(f"[{job_id}] DB save failed error={exc}")
            _set_error(job_id, "DB_SAVE_FAILED", "Failed to save sticker")
            return

        if _check_cancelled(job_id, "incrementing_usage"):
            return
        limits_service.increment_usage(db, device, amount=1)

        if _check_cancelled(job_id, "sending_notification"):
            return
        child_name = getattr(child, "name", "Your child")
        notification_service.send_sticker_created(
            db,
            sticker,
            message=f"{child_name} imagined: {original_text}",
        )

        if _check_cancelled(job_id, "tracking_analytics"):
            return
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

        _update(job_id, status="done", sticker_id=str(sticker.id), progress_step=None)
        logger.info(f"[{job_id}] Pipeline complete sticker_id={sticker.id}")

    except Exception as exc:
        logger.exception(f"[{job_id}] Unhandled pipeline error: {exc}")
        _set_error(job_id, "UNKNOWN_ERROR", "Unexpected error during sticker generation")
    finally:
        if active_device_jobs.get(device_id) == job_id:
            active_device_jobs.pop(device_id, None)
        db.close()
