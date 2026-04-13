"""
Usage Limits & Quota Management
================================

Centralized quota enforcement for all devices.
Protects backend API costs across all external services (STT, image generation, etc.)

Limit hierarchy:
1. Device paused check (manual override)
2. Device daily limit (per-device quota)
3. Parent account limit (per-user quota, based on subscription)
4. Company daily limit (total system-wide quota)

API keys are held by BACKEND ONLY, never exposed to devices.
Devices authenticate with device tokens, backend enforces quotas before calling external APIs.
"""

from datetime import date
import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.infra.repositories import usage_repository
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Load limits from settings
COMPANY_DAILY_LIMIT = settings.COMPANY_DAILY_LIMIT
DEFAULT_DEVICE_LIMIT = settings.DEFAULT_DAILY_STICKER_LIMIT
SUBSCRIPTION_PREMIUM_LIMIT = settings.SUBSCRIPTION_OVERRIDE_LIMIT


def check_limits(db: Session, device) -> bool:
    """
    Check if device can generate a sticker based on all quota limits.
    
    Raises HTTPException with appropriate status code if limit exceeded.
    Returns True if all checks pass.
    """
    device_id = device.device_id
    
    # 1. Check if device is manually paused
    if getattr(device, "paused", False):
        logger.warning(f"Device {device_id} is paused")
        raise HTTPException(
            status_code=403,
            detail="Device is paused. Contact support to resume."
        )

    # 2. Check device daily limit (only if set - None means unlimited)
    today = date.today()
    usage = usage_repository.get_today_by_device(db, device_pk=device.id, day=today)
    current_device_usage = usage.count if usage else 0
    
    if device.daily_limit is not None and current_device_usage >= device.daily_limit:
        logger.warning(
            f"Device {device_id} hit daily limit: {current_device_usage}/{device.daily_limit}"
        )
        raise HTTPException(
            status_code=429,
            detail=f"Device daily limit reached ({current_device_usage}/{device.daily_limit}). Resets at midnight."
        )
    
    # 3. Check parent account limit (subscription-based)
    # TODO: When subscription system is implemented, check parent's subscription tier here
    # For now, this is handled by device.daily_limit which can be set per parent
    
    # 4. Check company-wide daily limit (cost protection)
    total_today = usage_repository.get_total_for_day(db, day=today)
    
    if COMPANY_DAILY_LIMIT and total_today >= COMPANY_DAILY_LIMIT:
        logger.error(
            f"Company daily limit reached: {total_today}/{COMPANY_DAILY_LIMIT}"
        )
        raise HTTPException(
            status_code=503,  # Service Unavailable
            detail="System capacity reached. Please try again tomorrow."
        )
    
    # Log successful check
    if device.daily_limit is not None:
        logger.info(
            f"Limits check passed for {device_id}: "
            f"device={current_device_usage}/{device.daily_limit}, "
            f"company={total_today}/{COMPANY_DAILY_LIMIT}"
        )
    else:
        logger.info(
            f"Limits check passed for {device_id}: "
            f"device=unlimited, company={total_today}/{COMPANY_DAILY_LIMIT}"
        )
    
    return True


def increment_usage(db: Session, device, amount: int = 1):
    """
    Increment usage counter for device after successful sticker generation.
    
    This tracks actual API usage for cost accounting and quota enforcement.
    """
    today = date.today()
    usage = usage_repository.increment_for_day(db, device_pk=device.id, day=today, amount=amount)
    
    logger.info(
        f"Usage incremented for device {device.device_id}: "
        f"new_count={usage.count}, date={today}"
    )
    
    return usage


def get_remaining_quota(db: Session, device) -> dict:
    """
    Get remaining quota information for a device.
    
    Useful for displaying limits in parent app or device UI.
    
    Returns:
        {
            "device_used": 5,
            "device_limit": 10,  # or None if unlimited
            "device_remaining": 5,  # or None if unlimited
            "company_used": 523,
            "company_limit": 1000,
        }
    """
    today = date.today()
    
    # Device usage
    usage = usage_repository.get_today_by_device(db, device_pk=device.id, day=today)
    device_used = usage.count if usage else 0
    
    # Company-wide usage
    company_used = usage_repository.get_total_for_day(db, day=today)
    
    result = {
        "device_used": device_used,
        "device_limit": device.daily_limit,  # Can be None (unlimited), 0 (blocked), or positive integer
        "company_used": company_used,
        "company_limit": COMPANY_DAILY_LIMIT,
        "resets_at": "midnight",
    }
    
    # Calculate remaining only if limit is set
    if device.daily_limit is not None:
        result["device_remaining"] = max(0, device.daily_limit - device_used)
    else:
        result["device_remaining"] = None  # Unlimited
    
    return result

