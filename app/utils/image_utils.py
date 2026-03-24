from PIL import Image
import io

def pil_from_bytes(b: bytes) -> Image.Image:
    return Image.open(io.BytesIO(b))
