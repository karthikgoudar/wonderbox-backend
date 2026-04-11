import logging
import time

from fastapi import HTTPException


logger = logging.getLogger(__name__)

device_requests = {}
device_violations = {}

RATE_LIMIT_WINDOW = 60
MAX_REQUESTS = 4
BLOCK_DURATION = 300

CLEANUP_INTERVAL = 30
MAX_TRACKED_DEVICES = 10000

_last_cleanup_at = 0.0


def _cleanup_state(now: float) -> None:
    # Drop expired blocks.
    expired = [device_id for device_id, block_until in device_violations.items() if now >= block_until]
    for device_id in expired:
        del device_violations[device_id]

    # Drop stale request entries.
    stale = []
    for device_id, timestamps in device_requests.items():
        fresh = [request_time for request_time in timestamps if now - request_time < RATE_LIMIT_WINDOW]
        if fresh:
            device_requests[device_id] = fresh
        else:
            stale.append(device_id)
    for device_id in stale:
        del device_requests[device_id]

    # Hard cap for safety in long-running processes.
    if len(device_requests) > MAX_TRACKED_DEVICES:
        ranked = sorted(
            ((device_id, max(timestamps)) for device_id, timestamps in device_requests.items() if timestamps),
            key=lambda item: item[1],
        )
        overflow = len(device_requests) - MAX_TRACKED_DEVICES
        for device_id, _ in ranked[:overflow]:
            device_requests.pop(device_id, None)


def check_rate_limit(device_id: str):
    global _last_cleanup_at

    now = time.time()

    if now - _last_cleanup_at >= CLEANUP_INTERVAL:
        _cleanup_state(now)
        _last_cleanup_at = now

    if device_id in device_violations:
        block_until = device_violations[device_id]
        if now < block_until:
            logger.warning(f"device_blocked device={device_id}")
            raise HTTPException(status_code=403, detail="Device temporarily blocked")
        del device_violations[device_id]

    if device_id not in device_requests:
        device_requests[device_id] = []

    device_requests[device_id] = [
        request_time for request_time in device_requests[device_id] if now - request_time < RATE_LIMIT_WINDOW
    ]

    if len(device_requests[device_id]) >= MAX_REQUESTS:
        device_violations[device_id] = now + BLOCK_DURATION
        logger.warning(f"rate_limit_exceeded device={device_id}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    device_requests[device_id].append(now)