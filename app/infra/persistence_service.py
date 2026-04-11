from datetime import datetime, timedelta

from app.models.sticker import Sticker
from app.infra import storage_service
from app.infra.repositories import sticker_repository
from app.utils.constants import DEFAULT_EXPIRY_DAYS


async def save_sticker(db, device, child, user, core_data) -> tuple[Sticker, str]:
    """Persist sticker artifacts: upload image and write DB record."""
    filename = f"stickers/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{device.device_id}.png"
    image_url = await storage_service.upload_bytes(core_data["processed_bytes"], filename)

    expires_at = datetime.utcnow() + timedelta(days=DEFAULT_EXPIRY_DAYS)
    sticker_data = {
        "user_id": getattr(user, "id", None),
        "device_id": getattr(device, "id", None),
        "child_id": getattr(child, "id", None),
        "original_text": core_data["text"],
        "normalized_prompt": core_data["prompt"],
        "language": core_data["language"],
        "image_url": image_url,
        "expires_at": expires_at,
    }
    sticker = sticker_repository.create_sticker(db, sticker_data)
    return sticker, image_url
