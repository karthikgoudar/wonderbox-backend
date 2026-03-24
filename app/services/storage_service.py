import os
from datetime import datetime
from app.config.settings import settings


async def upload_bytes(data: bytes, path: str) -> str:
    # Minimal S3-like upload to local storage directory.
    base = settings.STORAGE_DIR
    os.makedirs(base, exist_ok=True)
    # sanitize path
    filename = path.replace("..", "")
    dest = os.path.join(base, filename)
    dirpath = os.path.dirname(dest)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
    # Return a file:// style path for now
    return f"file://{os.path.abspath(dest)}"
import os
import aiofiles
from app.config.settings import settings
import asyncio


async def upload_bytes(data: bytes, path: str) -> str:
    # Simple local storage implementation. Returns file URL/path.
    await asyncio.sleep(0.01)
    full_dir = os.path.join(settings.STORAGE_DIR)
    os.makedirs(full_dir, exist_ok=True)
    dest = os.path.join(full_dir, os.path.basename(path))
    async with aiofiles.open(dest, "wb") as f:
        await f.write(data)
    return dest
