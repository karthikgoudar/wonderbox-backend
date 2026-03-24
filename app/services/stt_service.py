import asyncio

async def transcribe(audio_bytes: bytes) -> dict:
    # Mock implementation: in real system call Whisper or other STT
    await asyncio.sleep(0.01)
    # For demo, return a fixed text and language
    return {"text": "A flying dragon", "language": "en"}
