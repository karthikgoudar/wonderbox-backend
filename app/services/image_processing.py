import io
from PIL import Image
import asyncio

async def to_1bit_png(image_bytes: bytes) -> bytes:
    # Convert image to 1-bit (mode '1') PNG suitable for thermal printers
    await asyncio.sleep(0.01)
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    bw = img.point(lambda x: 0 if x < 128 else 255, '1')
    buf = io.BytesIO()
    bw.save(buf, format="PNG")
    return buf.getvalue()
