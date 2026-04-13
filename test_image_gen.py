"""
Quick test script for image generation service.

Usage:
    python test_image_gen.py

This will generate a test coloring book image using your configured provider.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.services.image_service import generate_from_prompt
from app.services.prompt_builder import build_sticker_prompt


async def test_image_generation():
    """Test image generation with a simple prompt."""
    
    print("=" * 60)
    print("WonderBox Image Generation Test")
    print("=" * 60)
    
    # Test prompt (this is what a child might say)
    raw_text = "A happy dragon flying in the sky"
    
    # Build the full prompt (adds coloring book style)
    full_prompt = build_sticker_prompt(raw_text, child_age=5)
    
    print(f"\nRaw text: {raw_text}")
    print(f"Full prompt: {full_prompt}")
    print("\nGenerating image...")
    
    try:
        # Generate the image
        image_bytes = await generate_from_prompt(full_prompt)
        
        # Save to file
        output_file = "test_sticker.png"
        with open(output_file, "wb") as f:
            f.write(image_bytes)
        
        print(f"\n✅ Success!")
        print(f"   Generated: {len(image_bytes):,} bytes")
        print(f"   Saved to: {output_file}")
        print(f"\nOpen '{output_file}' to see your coloring book image!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your .env file has correct API keys")
        print("2. Verify you installed dependencies: pip install -r requirements.txt")
        print("3. Check your internet connection")
        print("4. See docs/image_generation_guide.md for setup help")
        return 1
    
    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_image_generation())
    sys.exit(exit_code)
