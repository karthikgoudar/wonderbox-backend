# Image Generation API Comparison & Recommendations

## For Coloring Book Style Images

Your use case is **perfect for AI image generation** because you need:
- ✅ Black and white line drawings
- ✅ Bold outlines
- ✅ Child-friendly content
- ✅ Sticker/coloring book style

## 🔑 Important: API Key Architecture

**API keys are held by the BACKEND ONLY.** Devices never have direct API access.

```
Devices (with device_token) → Backend validates → Backend calls API → Returns image
```

This protects your API costs and allows centralized quota management. See [API Key Architecture](api_key_architecture.md) for full details.

---

## Provider Comparison

### 🥇 **Recommended: Replicate (Flux Schnell)**

**Best for:** Getting started, budget-conscious production

**Pros:**
- ✅ **FREE tier** available (Flux Schnell model)
- ✅ Very fast generation (2-4 seconds)
- ✅ Excellent quality for line art
- ✅ Easy to use API
- ✅ Access to multiple models (Flux, SDXL, custom models)

**Cons:**
- ❌ Requires API token
- ❌ Free tier has rate limits

**Pricing:**
- Flux Schnell: **FREE** (rate limited)
- Flux Dev: ~$0.003 per image
- SDXL: ~$0.003 per image

**Quality for coloring books:** ⭐⭐⭐⭐⭐

**Setup:**
```bash
pip install replicate
# Get free token: https://replicate.com/account/api-tokens
```

**Example output:** Clean line art, perfect for coloring

---

### 🥈 **Stability AI (Stable Diffusion XL)**

**Best for:** High-quality production, fine control

**Pros:**
- ✅ SDXL has built-in **"line-art" preset** (perfect for you!)
- ✅ Excellent quality and control
- ✅ Negative prompts for better results
- ✅ Fast generation
- ✅ Reliable API

**Cons:**
- ❌ No free tier (paid from day 1)
- ❌ Requires credit card

**Pricing:**
- SDXL: ~$0.003 per image
- SD3 Medium: ~$0.035 per image
- SD3 Large: ~$0.065 per image

**Quality for coloring books:** ⭐⭐⭐⭐⭐

**Setup:**
```bash
# Uses httpx (already installed)
# Get API key: https://platform.stability.ai/account/keys
```

**Special feature:** The `style_preset: "line-art"` is designed exactly for your use case!

---

## Cost Analysis for Your Use Case

Assuming **1,000 stickers generated per month:**

| Provider | Cost/Month | Quality | Speed |
|----------|------------|---------|-------|
| Replicate (Flux Schnell) | **$0** (free tier) | Excellent | 2-4s |
| Replicate (Flux Dev) | **$3** | Excellent | 3-5s |
| Stability SDXL | **$3** | Excellent | 2-3s |

**Recommendation:** Start with **Replicate (Flux Schnell)** for free, then upgrade to Flux Dev or Stability SDXL if you need more volume.

**Note:** DALL-E has been retired and removed from this project.

---

## Sample Outputs for Coloring Books

All providers can generate excellent coloring book images when prompted correctly. Your `prompt_builder.py` already adds:
```
"simple black and white line drawing, bold outlines, sticker style"
```

The image service enhances this further with:
```
"coloring book page, thick black outlines, no shading, 
white background, simple shapes, child-friendly"
```

And uses **negative prompts** to avoid:
```
"color, colored, shading, gradient, photo, realistic"
```

This ensures you get clean, colorable line art!

---

## Recommended Configurations

### For Development/Testing
```env
IMAGE_PRIMARY_PROVIDER="replicate"
REPLICATE_API_TOKEN="your-free-token"
REPLICATE_MODEL="black-forest-labs/flux-schnell"
IMAGE_ENABLE_FALLBACK="false"
IMAGE_WIDTH=512
IMAGE_HEIGHT=512
```
**Why:** Free, fast, good quality for testing

---

### For Production (Budget Setup)
```env
IMAGE_PRIMARY_PROVIDER="replicate"
REPLICATE_API_TOKEN="your-token"
REPLICATE_MODEL="black-forest-labs/flux-dev"  # Better than Schnell
IMAGE_ENABLE_FALLBACK="true"
STABILITY_API_KEY="your-stability-key"  # Fallback
```
**Why:** Very cheap (~$3-5/month for 1000 images), reliable with fallback

**Cost:** ~$0.003 per image

---

### For Production (Quality Setup)
```env
IMAGE_PRIMARY_PROVIDER="stability"
STABILITY_API_KEY="your-key"
STABILITY_MODEL="stable-diffusion-xl-1024-v1-0"
IMAGE_ENABLE_FALLBACK="true"
REPLICATE_API_TOKEN="your-token"  # Fallback
```
**Why:** SDXL's "line-art" preset is perfect for coloring books

**Cost:** ~$0.003 per image

---

## Installation

```bash
# Install all image generation dependencies
pip install replicate httpx

# For Stability AI (uses httpx, already in requirements.txt)
# Just need your API key in .env file
```

**Note:** The `openai` package is installed for STT (Whisper) but is NOT used for image generation in this project.

---

## Getting API Keys

### Replicate (Recommended - Has Free Tier!)
1. Sign up: https://replicate.com
2. Get token: https://replicate.com/account/api-tokens
3. Free tier includes Flux Schnell model
4. Paid models are very cheap (~$0.003/image)

### Stability AI
1. Sign up: https://platform.stability.ai
2. Get API key: https://platform.stability.ai/account/keys
3. Add credits (starts at $10 minimum)
4. ~$0.003 per SDXL image

---

## Testing Your Setup

Create a test script:

```python
# test_image_generation.py
import asyncio
from app.services.image_service import generate_from_prompt

async def test():
    prompt = "A happy dragon, simple black and white line drawing, bold outlines, sticker style"
    
    print("Generating image...")
    image_bytes = await generate_from_prompt(prompt)
    
    print(f"✓ Generated {len(image_bytes)} bytes")
    
    # Save to file
    with open("test_sticker.png", "wb") as f:
        f.write(image_bytes)
    
    print("Saved to test_sticker.png")

asyncio.run(test())
```

Run:
```bash
python test_image_generation.py
```

---

## Quality Tips for Coloring Images

### ✅ DO:
- Use simple, clear descriptions: "a cute cat", "a flying rocket"
- Let the prompt_builder add style keywords
- Trust the automatic negative prompts
- Use 512x512 for printer-friendly stickers

### ❌ DON'T:
- Don't ask for colors in prompt
- Don't ask for shading or gradients
- Don't use overly complex scenes (kids can't color them easily)
- Don't go above 1024x1024 (unnecessary for stickers, costs more)

---

## Troubleshooting

### "Replicate client not available"
```bash
pip install replicate
# Check: python -c "import replicate; print('OK')"
```

### "Stability API key not configured"
- Check `.env` file has `STABILITY_API_KEY="sk-..."`
- Verify key is valid at https://platform.stability.ai

### "All image generation providers failed"
- At least one provider must be configured
- Check API keys are valid
- Check internet connectivity
- Check API quotas/credits

### Images have too much color/shading
- Check prompt_builder is adding style keywords
- Check negative prompts are working
- Try Stability AI with `style_preset: "line-art"`

### Generation is slow
- Replicate Flux Schnell: 2-4s (fastest, free)
- Stability SDXL: 2-3s (fast)
- Use Replicate for fastest results

---

## My Recommendation

**Start here:**
1. ✅ Use **Replicate with Flux Schnell** (free tier)
2. ✅ Enable fallback to Stability AI (paid)

**Why this combo:**
- Free for development/testing
- ~$3-5/month for 1000 images in production
- Excellent quality for coloring books
- Reliable with fallback
- Fast generation (2-4 seconds)

**When to upgrade:**
- If you exceed free tier limits → switch primary to Flux Dev or Stability SDXL
- If quality issues → add Stability SDXL with line-art preset
- For enterprise scale → contact Replicate/Stability for volume pricing

---

## Sample Costs at Scale

| Monthly Volume | Replicate (Flux) | Stability SDXL |
|---------------|------------------|----------------|
| 1,000 images | $0 (free tier) | $3 |
| 5,000 images | $15 | $15 |
| 10,000 images | $30 | $30 |
| 50,000 images | $150 | $150 |

**The winner:** Replicate (Flux) or Stability SDXL for cost-effective production 🎉
