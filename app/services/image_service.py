"""
Image Generation Service with Multi-Provider Fallback
======================================================

Generates coloring book style images (black and white line art) from text prompts.

Architecture: Backend holds API keys, devices authenticate with device tokens.
This protects API costs and allows centralized quota management.

Providers:
1. Replicate (Flux/SDXL) - Cost-effective, free tier available, fast
2. Stability AI (SDXL) - High-quality, has "line-art" preset perfect for coloring

Optimized for: Children's coloring stickers (bold outlines, simple shapes)
"""

import asyncio
import io
import logging
import base64
from typing import Optional

import httpx
from PIL import Image

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Lazy-loaded clients
_replicate_client = None


def _get_replicate_client():
    """Lazy load Replicate client."""
    global _replicate_client
    if _replicate_client is None and settings.REPLICATE_API_TOKEN:
        try:
            import replicate
            _replicate_client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)
            logger.info("Replicate client initialized")
        except ImportError:
            logger.warning("replicate package not installed. Install with: pip install replicate")
            _replicate_client = False
        except Exception as e:
            logger.error(f"Failed to initialize Replicate client: {e}")
            _replicate_client = False
    return _replicate_client if _replicate_client is not False else None


def _enhance_prompt_for_coloring_book(prompt: str) -> str:
    """
    Enhance prompt to ensure coloring book style output.
    
    The prompt_builder already adds base style, but we can add provider-specific
    enhancements here if needed.
    """
    # Check if style keywords already present
    if "coloring book" in prompt.lower() or "line drawing" in prompt.lower():
        return prompt
    
    # Add coloring book style hints
    return (
        f"{prompt}, coloring book page, thick black outlines, "
        "no shading, white background, simple shapes, child-friendly"
    )


async def _generate_replicate(prompt: str) -> bytes:
    """
    Generate image using Replicate (Flux or SDXL).
    
    Pros: Cost-effective, free tier, fast (Flux Schnell)
    Cons: Requires API token, async polling
    
    Pricing: Flux Schnell is free tier, SDXL ~$0.003/image
    """
    client = _get_replicate_client()
    if not client:
        raise RuntimeError("Replicate client not available")
    
    try:
        enhanced_prompt = _enhance_prompt_for_coloring_book(prompt)
        
        # Run prediction
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(
            None,
            lambda: client.run(
                settings.REPLICATE_MODEL,
                input={
                    "prompt": enhanced_prompt,
                    "width": settings.IMAGE_WIDTH,
                    "height": settings.IMAGE_HEIGHT,
                    "num_outputs": 1,
                    # Flux-specific params (ignored by other models)
                    "num_inference_steps": 4,  # Schnell needs exactly 4
                    # SDXL-specific params
                    "guidance_scale": 7.5,
                    "negative_prompt": "color, colored, shading, gradient, photo, realistic",
                }
            )
        )
        
        # Output is usually a list of URLs or file objects
        if isinstance(output, list) and len(output) > 0:
            image_url = output[0]
        else:
            image_url = output
        
        # Download the image
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.get(str(image_url))
            response.raise_for_status()
            image_bytes = response.content
        
        logger.info(f"Replicate image generated: {len(image_bytes)} bytes")
        return image_bytes
        
    except Exception as e:
        logger.error(f"Replicate generation failed: {e}")
        raise


async def _generate_stability(prompt: str) -> bytes:
    """
    Generate image using Stability AI (Stable Diffusion XL).
    
    Pros: High quality, good control, excellent for line art
    Cons: Paid API, requires API key
    
    Pricing: ~$0.003-0.01 per image depending on model
    """
    if not settings.STABILITY_API_KEY:
        raise RuntimeError("Stability API key not configured")
    
    try:
        enhanced_prompt = _enhance_prompt_for_coloring_book(prompt)
        
        # Use SDXL or SD3 API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://api.stability.ai/v1/generation/{settings.STABILITY_MODEL}/text-to-image",
                headers={
                    "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
                    "Accept": "application/json",
                },
                json={
                    "text_prompts": [
                        {
                            "text": enhanced_prompt,
                            "weight": 1.0,
                        },
                        {
                            "text": "color, colored, shading, gradient, photo, realistic, blurry",
                            "weight": -1.0,  # Negative prompt
                        },
                    ],
                    "cfg_scale": 7.5,
                    "height": settings.IMAGE_HEIGHT,
                    "width": settings.IMAGE_WIDTH,
                    "samples": 1,
                    "steps": 30,
                    "style_preset": "line-art",  # Perfect for coloring books!
                },
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract base64 image from first artifact
            if "artifacts" in data and len(data["artifacts"]) > 0:
                image_b64 = data["artifacts"][0]["base64"]
                image_bytes = base64.b64decode(image_b64)
                
                logger.info(f"Stability AI image generated: {len(image_bytes)} bytes")
                return image_bytes
            else:
                raise RuntimeError("No image in Stability AI response")
                
    except Exception as e:
        logger.error(f"Stability AI generation failed: {e}")
        raise


async def generate_from_prompt(prompt: str) -> bytes:
    """
    Generate a coloring book style image from a text prompt.
    
    Attempts multiple providers with automatic fallback if enabled.
    
    Args:
        prompt: Text description of the image to generate.
                Should already include style hints from prompt_builder.
    
    Returns:
        Image as PNG bytes
    
    Raises:
        RuntimeError: If all providers fail
    """
    # Define provider order
    providers = []
    
    # Primary provider
    if settings.IMAGE_PRIMARY_PROVIDER == "replicate":
        providers.append(("replicate", _generate_replicate))
    elif settings.IMAGE_PRIMARY_PROVIDER == "stability":
        providers.append(("stability", _generate_stability))
    
    # Fallback providers (if enabled)
    if settings.IMAGE_ENABLE_FALLBACK:
        if settings.IMAGE_PRIMARY_PROVIDER != "replicate" and settings.REPLICATE_API_TOKEN:
            providers.append(("replicate", _generate_replicate))
        if settings.IMAGE_PRIMARY_PROVIDER != "stability" and settings.STABILITY_API_KEY:
            providers.append(("stability", _generate_stability))
    
    # Try each provider in order
    last_error = None
    for provider_name, provider_func in providers:
        try:
            logger.info(f"Attempting image generation with: {provider_name}")
            image_bytes = await provider_func(prompt)
            logger.info(f"✓ Image generation successful with {provider_name}")
            return image_bytes
        except Exception as e:
            logger.warning(f"✗ {provider_name} failed: {e}")
            last_error = e
            continue
    
    # All providers failed
    error_msg = f"All image generation providers failed. Last error: {last_error}"
    logger.error(error_msg)
    raise RuntimeError(error_msg)
