"""Turn what a child said into a clear English picture description.

Children here mix Kannada or Hindi words into English sentences. Speech-to-
text then hears the sentence as English and writes those words in English
letters ("Manga Tractory on Mars": manga = ಮಂಗ, monkey), so there is no
translation and the image model misreads them (manga = Japanese comics).

A small, fast language model rewrites such sentences ("Monkey tractor on
Mars") and fixes slight mishearings. Clear English comes back unchanged.

Providers are tried in order (PROMPT_REWRITE_PROVIDERS, default groq then
openai). Any failure or odd reply keeps the original words: the rewrite can
never stop a sticker from being made.

Compared on 26 Nov 2026 (10 test sentences): Groq openai/gpt-oss-20b got all
10 right in about 0.5 s; OpenAI gpt-5.4-nano also 10/10 in about 1 s.
"""

import logging
import time

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You turn what a child said to a sticker-making toy into a short English description of the picture to draw. "
    "The children live in Karnataka, India. They often mix Kannada or Hindi words, written in English letters, into English sentences, "
    "and speech-to-text sometimes mishears a word slightly.\n"
    "Step 1: Find every Kannada or Hindi word and replace it with its English meaning. Common ones: manga, mangaa or kothi = monkey; "
    "aane, haathi or hathi = elephant; bekku or billi = cat; nayi or kutta = dog; chidiya or hakki = bird; bandar = monkey; "
    "matte or aur = and; ek or ondu = a. 'Manga' means monkey unless the child is clearly talking about comic books.\n"
    "Step 2: If an English word is not quite a real word, change it to the real English word that sounds closest "
    "(Rockety = rocket, Tractory = tractor). Never swap it for a different word.\n"
    "Keep exactly the child's idea; do not add new objects or details. Leave sentences that are already clear English unchanged.\n"
    "Examples: 'Aane eating ice cream' -> 'Elephant eating ice cream'; 'Billi on a bus' -> 'Cat on a bus'; "
    "'Ondu rockety in space' -> 'A rocket in space'; 'Hakki matte nayi playing' -> 'Bird and dog playing'; "
    "'Robot cooking pasta' -> 'Robot cooking pasta'.\n"
    "Reply with only the description, no quotes."
)

_PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "PROMPT_REWRITE_GROQ_MODEL",
             {"reasoning_effort": "low", "temperature": 0}),
    "openai": ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY", "PROMPT_REWRITE_OPENAI_MODEL",
               {"reasoning_effort": "low"}),
}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=settings.PROMPT_REWRITE_TIMEOUT)


def _clean(reply: str, original: str):
    """The model's answer, or None if it does not look like a picture description."""
    text = (reply or "").strip().strip('"').strip("'").strip()
    if not text or "\n" in text:
        return None
    if len(text) > max(200, 3 * len(original)):
        return None
    return text


async def _ask(provider: str, text: str) -> str:
    url, key_name, model_name, extra = _PROVIDERS[provider]
    key = getattr(settings, key_name, "")
    if not key:
        raise RuntimeError(f"{key_name} not set")
    body = {
        "model": getattr(settings, model_name),
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}],
        **extra,
    }
    async with _client() as client:
        resp = await client.post(url, headers={"Authorization": f"Bearer {key}"}, json=body)
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:150]}")
    return resp.json()["choices"][0]["message"]["content"] or ""


async def rewrite(text: str) -> str:
    """English picture description for `text`; the original if anything fails."""
    text = (text or "").strip()
    if not text or not settings.PROMPT_REWRITE:
        return text
    for provider in settings.PROMPT_REWRITE_PROVIDERS:
        if provider not in _PROVIDERS:
            continue
        started = time.monotonic()
        try:
            cleaned = _clean(await _ask(provider, text), text)
        except Exception as e:
            logger.warning(f"Prompt rewrite with {provider} failed: {e}")
            continue
        took = time.monotonic() - started
        if cleaned is None:
            logger.warning(f"Prompt rewrite with {provider} gave an unusable reply ({took:.2f} s)")
            continue
        logger.info(f"Prompt rewrite ({provider}, {took:.2f} s): '{text}' -> '{cleaned}'")
        return cleaned
    return text
