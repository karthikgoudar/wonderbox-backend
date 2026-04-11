import os
import aiofiles
from app.config.settings import settings


async def upload_bytes(data: bytes, path: str) -> str:
    """Upload bytes to local storage. Returns the destination file path."""
    full_dir = settings.STORAGE_DIR
    os.makedirs(full_dir, exist_ok=True)
    dest = os.path.join(full_dir, os.path.basename(path))
    async with aiofiles.open(dest, "wb") as f:
        await f.write(data)
    return dest
