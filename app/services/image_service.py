import io
from PIL import Image, ImageDraw, ImageFont
import asyncio

async def generate_from_prompt(prompt: str) -> bytes:
    # Mock image generation using Pillow: return simple PNG
    await asyncio.sleep(0.01)
    img = Image.new("RGB", (512, 512), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.load_default()
    except Exception:
        f = None
    d.text((10, 10), prompt, fill=(0, 0, 0), font=f)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
