import asyncio

async def to_english(text: str, language: str) -> str:
    # Mock translation: if already english, return text
    await asyncio.sleep(0.01)
    if language and language.lower().startswith("en"):
        return text
    # In production, call Google Translate or GPT
    return f"{text} (translated to English)"
