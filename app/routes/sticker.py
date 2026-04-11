"""
Sticker routes
==============
Two-step SSE architecture

  POST /sticker/submit          → returns {"job_id": "..."}
  GET  /sticker/{job_id}/stream → SSE stream of pipeline events

SSE event sequence
------------------
  event: status       data: {"state": "processing"}
  event: progress     data: {"step": "<named_step>"}      (repeated)
  event: text         data: {"text": "...", "language": "en"}
  event: image_ready  data: {"image_url": "https://..."}
  event: done         data: {"sticker_id": "..."}
  event: error        data: {"message": "..."}
"""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_current_device
from app.db.session import SessionLocal
from app.infra.repositories import child_repository
from app.orchestrator.sticker_orchestrator import (
    create_job,
    get_job,
    jobs,
    run_sticker_pipeline,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# How often the SSE generator polls the job dict (seconds)
_POLL_INTERVAL: float = 0.5
# Maximum time to wait for a job to complete before sending a timeout error
_STREAM_TIMEOUT: float = 120.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    """Format a single SSE frame."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ── Submit endpoint ───────────────────────────────────────────────────────────

@router.post("/sticker/submit")
async def submit_sticker(
    child_id: str = Form(...),
    audio: UploadFile = File(...),
    device=Depends(get_current_device),
):
    """
    Step 1 — Accept audio and kick off the pipeline in the background.

    Returns immediately with a job_id the client can use to open the SSE stream.
    Does NOT block. Does NOT stream. Does NOT process the audio here.
    """
    # Child existence check before accepting the job
    db = SessionLocal()
    try:
        child = child_repository.get_by_id(db, child_id)
        if not child:
            return Response(
                content=json.dumps({"detail": f"Child '{child_id}' not found"}),
                status_code=404,
                media_type="application/json",
            )
    finally:
        db.close()

    audio_bytes = await audio.read()
    job_id = str(uuid.uuid4())
    create_job(job_id)

    logger.info(f"[{job_id}] Accepted submit for device={device.device_id} child={child_id}")

    # Fire-and-forget background task — pipeline updates jobs[job_id] as it runs
    asyncio.create_task(
        run_sticker_pipeline(
            job_id=job_id,
            audio_bytes=audio_bytes,
            device_id=device.device_id,
            child_id=child_id,
        )
    )

    return {"job_id": job_id}


# ── SSE stream endpoint ───────────────────────────────────────────────────────

@router.get("/sticker/{job_id}/stream")
async def stream_sticker(job_id: str):
    """
    Step 2 — Stream real-time pipeline updates over Server-Sent Events.

    Polls jobs[job_id] every 0.5 s and yields new events as state changes.
    Safe to reconnect — the stream replays all unsent events from current state.
    Terminates when the job reaches 'done' or 'error', or after the timeout.
    """
    job = get_job(job_id)
    if job is None:
        return Response(
            content=json.dumps({"detail": "Job not found"}),
            status_code=404,
            media_type="application/json",
        )

    async def event_generator():
        sent_status = False
        sent_text = False
        sent_image_ready = False
        last_progress_step: str | None = None
        deadline = asyncio.get_event_loop().time() + _STREAM_TIMEOUT

        while True:
            current = get_job(job_id)

            # Job disappeared (e.g. purged) — treat as error
            if current is None:
                yield _sse("error", {"message": "Job no longer exists"})
                return

            # ── status (sent once at the start) ──────────────────────────────
            if not sent_status:
                yield _sse("status", {"state": "processing"})
                sent_status = True

            # ── progress (sent whenever the step name changes) ────────────────
            current_step = current.get("progress_step")
            if current_step and current_step != last_progress_step:
                yield _sse("progress", {"step": current_step})
                last_progress_step = current_step

            # ── text (sent once when transcript is available) ─────────────────
            if not sent_text and current.get("text"):
                yield _sse(
                    "text",
                    {
                        "text": current["text"],
                        "language": current.get("language", "en"),
                    },
                )
                sent_text = True

            # ── image_ready (sent once when image_url is available) ───────────
            if not sent_image_ready and current.get("image_url"):
                yield _sse("image_ready", {"image_url": current["image_url"]})
                sent_image_ready = True

            # ── terminal: done ────────────────────────────────────────────────
            if current.get("status") == "done":
                yield _sse("done", {"sticker_id": current.get("sticker_id")})
                logger.info(f"[{job_id}] Stream closed — done")
                return

            # ── terminal: error ───────────────────────────────────────────────
            if current.get("status") == "error":
                error = current.get("error") or {}
                if isinstance(error, dict):
                    yield _sse(
                        "error",
                        {
                            "message": error.get("message", "Unknown error"),
                            "code": error.get("code", "UNKNOWN_ERROR"),
                        },
                    )
                else:
                    yield _sse("error", {"message": error or "Unknown error", "code": "UNKNOWN_ERROR"})
                logger.info(f"[{job_id}] Stream closed — error: {current.get('error')}")
                return

            # ── timeout guard ─────────────────────────────────────────────────
            if asyncio.get_event_loop().time() >= deadline:
                jobs[job_id].update(
                    {
                        "status": "error",
                        "error": {"code": "TIMEOUT", "message": "Pipeline timed out"},
                    }
                )
                yield _sse("error", {"message": "Pipeline timed out", "code": "TIMEOUT"})
                logger.warning(f"[{job_id}] Stream timed out after {_STREAM_TIMEOUT}s")
                return

            await asyncio.sleep(_POLL_INTERVAL)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
