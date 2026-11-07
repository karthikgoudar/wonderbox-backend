import os
import aiofiles
from app.config.settings import settings


async def upload_bytes(data: bytes, path: str) -> str:
    """
    Upload bytes to local storage and return the fully qualified public URL.
    Preserves subdirectories (e.g. 'stickers/...' or 'stories/...').
    """
    rel_path = path.lstrip("/").replace("\\", "/")
    full_dest = os.path.join(settings.STORAGE_DIR, rel_path)
    os.makedirs(os.path.dirname(full_dest), exist_ok=True)

    async with aiofiles.open(full_dest, "wb") as f:
        await f.write(data)

    base = settings.BASE_URL.rstrip("/")
    return f"{base}/storage/{rel_path}"
