import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional


@dataclass
class StickerJob:
    id: str
    device_id: str
    status: str = "queued"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)


_jobs: Dict[str, StickerJob] = {}
_jobs_lock = asyncio.Lock()


async def create_job(device_id: str) -> StickerJob:
    job_id = str(uuid.uuid4())
    job = StickerJob(id=job_id, device_id=device_id)
    async with _jobs_lock:
        _jobs[job_id] = job
    return job


async def get_job(job_id: str) -> Optional[StickerJob]:
    async with _jobs_lock:
        return _jobs.get(job_id)


async def publish_event(job_id: str, event: str, data: Dict[str, Any]) -> None:
    async with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return
    job.updated_at = datetime.utcnow()
    await job.queue.put({"event": event, "data": data})


async def set_running(job_id: str) -> None:
    async with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return
    job.status = "running"
    job.updated_at = datetime.utcnow()


async def set_done(job_id: str, payload: Dict[str, Any]) -> None:
    async with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return
    job.status = "done"
    job.updated_at = datetime.utcnow()
    await job.queue.put({"event": "done", "data": payload})


async def set_error(job_id: str, message: str, status_code: int = 500) -> None:
    async with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return
    job.status = "error"
    job.error = message
    job.updated_at = datetime.utcnow()
    await job.queue.put({"event": "error", "data": {"message": message, "status_code": status_code}})


async def stream_events(job_id: str) -> AsyncGenerator[Dict[str, Any], None]:
    job = await get_job(job_id)
    if not job:
        return

    # Initial state event so device can immediately react.
    await job.queue.put({"event": "status", "data": {"state": job.status}})

    while True:
        item = await job.queue.get()
        yield item
        if item["event"] in {"done", "error"}:
            break
