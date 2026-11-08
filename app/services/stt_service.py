"""
Speech-to-Text Service with Multi-Provider Fallback
====================================================

Providers (set STT_PRIMARY_PROVIDER; the rest act as fallbacks):
- sarvam:        Built for Indian languages (Kannada, Hindi, English, ...). Needs SARVAM_API_KEY.
- groq:          Whisper on Groq. Fast and cheap; weaker on Kannada.
- openai:        Whisper API. Paid.
- local_whisper: faster-whisper on this server. Free.

Every result has "language" as a short code: en, hi, kn, ...
Sarvam results may also carry "english_text" for non-English speech.
"""

import asyncio
import io
import logging
import tempfile
from typing import Optional

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Lazy-loaded to avoid import errors if packages aren't installed
_whisper_model = None
_groq_client = None
_openai_client = None


def _get_local_whisper_model():
    """Lazy load the local Whisper model."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            logger.info(
                f"Loading local Whisper model: {settings.WHISPER_MODEL_SIZE} "
                f"on {settings.WHISPER_DEVICE}"
            )
            _whisper_model = WhisperModel(
                settings.WHISPER_MODEL_SIZE,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
            )
            logger.info("Local Whisper model loaded successfully")
        except ImportError:
            logger.warning(
                "faster-whisper not installed. Install with: pip install faster-whisper"
            )
            _whisper_model = False  # Mark as unavailable
        except Exception as e:
            logger.error(f"Failed to load local Whisper model: {e}")
            _whisper_model = False
    return _whisper_model if _whisper_model is not False else None


def _get_groq_client():
    """Lazy load Groq client."""
    global _groq_client
    if _groq_client is None and settings.GROQ_API_KEY:
        try:
            from groq import Groq
            _groq_client = Groq(api_key=settings.GROQ_API_KEY)
            logger.info("Groq client initialized")
        except ImportError:
            logger.warning("groq package not installed. Install with: pip install groq")
            _groq_client = False
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            _groq_client = False
    return _groq_client if _groq_client is not False else None


def _get_openai_client():
    """Lazy load OpenAI client."""
    global _openai_client
    if _openai_client is None and settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized")
        except ImportError:
            logger.warning("openai package not installed. Install with: pip install openai")
            _openai_client = False
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            _openai_client = False
    return _openai_client if _openai_client is not False else None


async def _transcribe_local_whisper(audio_bytes: bytes) -> dict:
    """
    Transcribe using local Whisper model.
    
    Pros: Free, no API limits, private
    Cons: Requires CPU/GPU resources, slower on CPU
    """
    model = _get_local_whisper_model()
    if not model:
        raise RuntimeError("Local Whisper model not available")
    
    # faster-whisper requires a file path, so write to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_audio.write(audio_bytes)
        temp_path = temp_audio.name
    
    try:
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        segments, info = await loop.run_in_executor(
            None,
            lambda: model.transcribe(
                temp_path,
                language=None,  # Auto-detect between en/hi
                beam_size=5,
                vad_filter=True,  # Voice activity detection to filter silence
            )
        )
        
        # Combine all segments
        text = " ".join([segment.text.strip() for segment in segments])
        language = info.language
        
        logger.info(f"Local Whisper transcription: lang={language}, confidence={info.language_probability:.2f}")
        
        return {
            "text": text.strip(),
            "language": language,
            "provider": "local_whisper",
            "confidence": info.language_probability,
        }
    except Exception as e:
        logger.error(f"Local Whisper transcription failed: {e}")
        raise
    finally:
        # Clean up temp file
        import os
        try:
            os.unlink(temp_path)
        except Exception:
            pass


async def _transcribe_groq(audio_bytes: bytes) -> dict:
    """
    Transcribe using Groq API (has free tier).
    
    Pros: Fast inference, free tier available, good accuracy
    Cons: Requires API key, network dependency
    """
    client = _get_groq_client()
    if not client:
        raise RuntimeError("Groq client not available")
    
    try:
        # Groq expects a file-like object
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"  # Groq needs a filename
        
        # Run in thread pool since Groq SDK is synchronous
        loop = asyncio.get_event_loop()
        transcription = await loop.run_in_executor(
            None,
            lambda: client.audio.transcriptions.create(
                file=audio_file,
                model=settings.GROQ_MODEL,
                response_format="verbose_json",  # Includes language detection
                language=None,  # Auto-detect
            )
        )
        
        text = transcription.text
        language = getattr(transcription, "language", "en")  # Default to en if not provided
        
        logger.info(f"Groq transcription: lang={language}, text_length={len(text)}")
        
        return {
            "text": text.strip(),
            "language": language,
            "provider": "groq",
        }
    except Exception as e:
        logger.error(f"Groq transcription failed: {e}")
        raise


async def _transcribe_openai(audio_bytes: bytes) -> dict:
    """
    Transcribe using OpenAI Whisper API.
    
    Pros: Highly reliable, accurate, fast
    Cons: Paid service, costs per minute of audio
    """
    client = _get_openai_client()
    if not client:
        raise RuntimeError("OpenAI client not available")
    
    try:
        # OpenAI expects a file-like object
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        
        # Run in thread pool since OpenAI SDK is synchronous
        loop = asyncio.get_event_loop()
        transcription = await loop.run_in_executor(
            None,
            lambda: client.audio.transcriptions.create(
                file=audio_file,
                model=settings.OPENAI_WHISPER_MODEL,
                response_format="verbose_json",
                language=None,  # Auto-detect
            )
        )
        
        text = transcription.text
        language = getattr(transcription, "language", "en")
        
        logger.info(f"OpenAI transcription: lang={language}, text_length={len(text)}")
        
        return {
            "text": text.strip(),
            "language": language,
            "provider": "openai",
        }
    except Exception as e:
        logger.error(f"OpenAI transcription failed: {e}")
        raise


# ── Language codes ────────────────────────────────────────────────────────────
_LANGUAGE_NAMES = {
    "english": "en", "hindi": "hi", "kannada": "kn", "tamil": "ta", "telugu": "te",
    "marathi": "mr", "bengali": "bn", "gujarati": "gu", "malayalam": "ml", "punjabi": "pa",
}


def normalize_language(value) -> str:
    """Return a short code ("en", "hi", "kn") from 'hi-IN', 'Hindi', 'kn', ...

    Whisper providers return names like "hindi"; Sarvam returns "hi-IN".
    Missing or unknown values become "en", as before.
    """
    if not value:
        return "en"
    v = str(value).strip().lower()
    if v in _LANGUAGE_NAMES:
        return _LANGUAGE_NAMES[v]
    if v in ("unknown", "none", "null"):
        return "en"
    return v.split("-")[0].split("_")[0]


# ── Sarvam ────────────────────────────────────────────────────────────────────
def _sarvam_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=settings.SARVAM_TIMEOUT)


async def _sarvam_call(audio_bytes: bytes, mode: str) -> dict:
    """One call to Sarvam's /speech-to-text. mode: "transcribe" or "translate"."""
    if not settings.SARVAM_API_KEY:
        raise RuntimeError("Sarvam API key not set")
    async with _sarvam_client() as client:
        resp = await client.post(
            settings.SARVAM_URL,
            headers={"api-subscription-key": settings.SARVAM_API_KEY},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"model": settings.SARVAM_MODEL, "mode": mode, "language_code": "unknown"},
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"Sarvam HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.json()


async def _transcribe_sarvam(audio_bytes: bytes) -> dict:
    """
    Transcribe with Sarvam AI (auto-detects Kannada, Hindi, English, ...).

    For non-English speech it makes a second call in "translate" mode to get
    English text, which the image step draws from. That second call is best
    effort: if it fails, the original-language text is still returned.
    """
    data = await _sarvam_call(audio_bytes, "transcribe")
    text = (data.get("transcript") or "").strip()
    language = normalize_language(data.get("language_code"))
    logger.info(f"Sarvam transcription: lang={language}, text_length={len(text)}")

    result = {"text": text, "language": language, "provider": "sarvam"}

    if text and language != "en" and settings.SARVAM_TRANSLATE:
        try:
            tr = await _sarvam_call(audio_bytes, "translate")
            english = (tr.get("transcript") or "").strip()
            if english:
                result["english_text"] = english
                logger.info(f"Sarvam translation to English: text_length={len(english)}")
        except Exception as e:
            logger.warning(f"Sarvam translation failed; using original text: {e}")
    return result


async def transcribe(audio_bytes: bytes) -> dict:
    """
    Transcribe audio to text with automatic provider fallback.
    
    Args:
        audio_bytes: Raw audio file bytes (WAV, MP3, etc.)
    
    Returns:
        {
            "text": "transcribed text",
            "language": "en" | "hi" | "kn" | ...,
            "provider": "sarvam" | "local_whisper" | "groq" | "openai",
            "english_text": optional English version (Sarvam, non-English speech)
        }
    
    Raises:
        RuntimeError: If all providers fail
    """
    # Define provider order
    providers = []
    
    # Primary provider
    if settings.STT_PRIMARY_PROVIDER == "sarvam":
        providers.append(("sarvam", _transcribe_sarvam))
    elif settings.STT_PRIMARY_PROVIDER == "local_whisper":
        providers.append(("local_whisper", _transcribe_local_whisper))
    elif settings.STT_PRIMARY_PROVIDER == "groq":
        providers.append(("groq", _transcribe_groq))
    elif settings.STT_PRIMARY_PROVIDER == "openai":
        providers.append(("openai", _transcribe_openai))
    
    # Fallback providers (if enabled)
    if settings.STT_ENABLE_FALLBACK:
        if settings.STT_PRIMARY_PROVIDER != "sarvam" and settings.SARVAM_API_KEY:
            providers.append(("sarvam", _transcribe_sarvam))
        if settings.STT_PRIMARY_PROVIDER != "groq" and settings.GROQ_API_KEY:
            providers.append(("groq", _transcribe_groq))
        if settings.STT_PRIMARY_PROVIDER != "openai" and settings.OPENAI_API_KEY:
            providers.append(("openai", _transcribe_openai))
        if settings.STT_PRIMARY_PROVIDER != "local_whisper":
            providers.append(("local_whisper", _transcribe_local_whisper))
    
    # Try each provider in order
    last_error = None
    for provider_name, provider_func in providers:
        try:
            logger.info(f"Attempting transcription with: {provider_name}")
            result = await provider_func(audio_bytes)
            logger.info(f"✓ Transcription successful with {provider_name}")
            result["language"] = normalize_language(result.get("language"))
            return result
        except Exception as e:
            logger.warning(f"✗ {provider_name} failed: {e}")
            last_error = e
            continue
    
    # All providers failed
    error_msg = f"All transcription providers failed. Last error: {last_error}"
    logger.error(error_msg)
    raise RuntimeError(error_msg)
