"""
Speech-to-Text Service with Multi-Provider Fallback
====================================================

Transcription priority:
1. Local Whisper (faster-whisper) - Free, runs on your server
2. Groq API (Whisper) - Free tier available, fast inference
3. OpenAI Whisper API - Paid, highly reliable

Supported languages: English (en), Hindi (hi)
"""

import asyncio
import io
import logging
import tempfile
from typing import Optional

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


async def transcribe(audio_bytes: bytes) -> dict:
    """
    Transcribe audio to text with automatic provider fallback.
    
    Args:
        audio_bytes: Raw audio file bytes (WAV, MP3, etc.)
    
    Returns:
        {
            "text": "transcribed text",
            "language": "en" or "hi",
            "provider": "local_whisper" | "groq" | "openai"
        }
    
    Raises:
        RuntimeError: If all providers fail
    """
    # Define provider order
    providers = []
    
    # Primary provider
    if settings.STT_PRIMARY_PROVIDER == "local_whisper":
        providers.append(("local_whisper", _transcribe_local_whisper))
    elif settings.STT_PRIMARY_PROVIDER == "groq":
        providers.append(("groq", _transcribe_groq))
    elif settings.STT_PRIMARY_PROVIDER == "openai":
        providers.append(("openai", _transcribe_openai))
    
    # Fallback providers (if enabled)
    if settings.STT_ENABLE_FALLBACK:
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
            return result
        except Exception as e:
            logger.warning(f"✗ {provider_name} failed: {e}")
            last_error = e
            continue
    
    # All providers failed
    error_msg = f"All transcription providers failed. Last error: {last_error}"
    logger.error(error_msg)
    raise RuntimeError(error_msg)
