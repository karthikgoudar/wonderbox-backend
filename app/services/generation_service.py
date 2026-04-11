from app.services import image_processing, image_service, stt_service
from app.services.prompt_builder import build_sticker_prompt


async def generate_sticker_core(audio_bytes: bytes) -> dict:
    """Core generation flow without DB/storage/analytics side-effects."""
    stt_result = await stt_service.transcribe(audio_bytes)

    text = (stt_result.get("text") or "").strip()
    language = (stt_result.get("language") or "en").lower()

    if not text:
        raise ValueError("Could not transcribe audio")

    prompt = build_sticker_prompt(text)

    image_bytes = await image_service.generate_from_prompt(prompt)
    if not image_bytes:
        raise ValueError("Image generation failed")

    processed_bytes = await image_processing.to_1bit_png(image_bytes)
    if not processed_bytes:
        raise ValueError("Image processing failed")

    return {
        "text": text,
        "language": language,
        "prompt": prompt,
        "image_bytes": image_bytes,
        "processed_bytes": processed_bytes,
    }
