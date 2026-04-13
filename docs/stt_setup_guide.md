# STT Provider Comparison & Recommendations

## Cost-Benefit Analysis

### Local Whisper (faster-whisper)

**Use when:**
- You have a dedicated server (cloud VM or on-premise)
- Budget-conscious (100% free)
- Privacy is critical (data never leaves your server)
- High volume of requests

**Server Requirements:**
- **CPU-only setup:**
  - Model: `base` 
  - RAM: 2GB minimum
  - Best for: <100 requests/day
  
- **GPU setup (recommended for production):**
  - GPU: NVIDIA with 4GB+ VRAM (e.g., T4, RTX 3060)
  - RAM: 4GB
  - Best for: High volume, fast processing
  - Cost: ~$0.35/hour on AWS (g4dn.xlarge)

**Pros:**
- ✅ No per-request cost
- ✅ No API rate limits
- ✅ Data privacy (no external calls)
- ✅ Supports Hindi/English equally well
- ✅ Works offline

**Cons:**
- ❌ Requires compute resources
- ❌ Slower on CPU (5-10s for 30s audio)
- ❌ Initial model download (~1GB)

---

### Groq API

**Use when:**
- You want free API with fast inference
- Limited budget
- Don't want to manage infrastructure
- Medium volume (<1000/day on free tier)

**Pricing:**
- **Free tier:** Very generous limits
- **Speed:** <1s for typical child audio (5-10 seconds)
- **Quality:** Same as OpenAI (uses Whisper large-v3)

**Pros:**
- ✅ FREE tier with good limits
- ✅ Blazing fast (optimized inference)
- ✅ No infrastructure management
- ✅ Excellent Hindi support
- ✅ Easy to scale

**Cons:**
- ❌ Network dependency
- ❌ Rate limits (though generous)
- ❌ Data leaves your server

**Get API Key:**
https://console.groq.com/keys

---

### OpenAI Whisper API

**Use when:**
- Maximum reliability is critical
- Budget allows for paid service
- Fallback option for other providers

**Pricing:**
- $0.006 per minute of audio
- Example: 10,000 requests/month × 10 seconds each = $10/month

**Pros:**
- ✅ Highest reliability
- ✅ Best documentation
- ✅ 99.9% uptime SLA
- ✅ Excellent support

**Cons:**
- ❌ Costs money (though cheap)
- ❌ Slower than Groq
- ❌ Rate limits on free tier

**Get API Key:**
https://platform.openai.com/api-keys

---

## Recommended Setups

### For Development / Testing
```env
STT_PRIMARY_PROVIDER="local_whisper"
WHISPER_MODEL_SIZE="base"
WHISPER_DEVICE="cpu"
STT_ENABLE_FALLBACK="false"
```
**Why:** No API keys needed, test everything locally

---

### For Production (Low-Medium Volume)
```env
STT_PRIMARY_PROVIDER="groq"
GROQ_API_KEY="your-key"
STT_ENABLE_FALLBACK="true"
WHISPER_MODEL_SIZE="base"
```
**Why:** Free + fast, with local fallback if API is down

---

### For Production (High Volume)
```env
STT_PRIMARY_PROVIDER="local_whisper"
WHISPER_MODEL_SIZE="small"
WHISPER_DEVICE="cuda"
STT_ENABLE_FALLBACK="true"
GROQ_API_KEY="your-key"
```
**Why:** GPU server handles bulk, Groq as fallback

Deploy on:
- AWS EC2 g4dn.xlarge (~$0.35/hour = $250/month)
- Google Cloud GPU VMs
- Your own server with NVIDIA GPU

---

## Hindi + English Performance

All three providers support both languages well:

| Provider | English | Hindi | Auto-detect |
|----------|---------|-------|-------------|
| Local Whisper | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ |
| Groq | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ |
| OpenAI | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ |

**Tip:** For children's speech, use at least `base` model size for better accuracy with unclear pronunciation.

---

## Installation Commands

### Linux/Mac
```bash
# Local Whisper
pip install faster-whisper

# Groq
pip install groq

# OpenAI
pip install openai

# All providers
pip install -r requirements.txt
```

### GPU Support (NVIDIA)
```bash
# Install CUDA-enabled version
pip install faster-whisper[cuda]

# Verify GPU detection
python -c "import torch; print(torch.cuda.is_available())"
```

---

## Testing Your Setup

```python
# Test transcription
import asyncio
from app.services.stt_service import transcribe

async def test():
    with open("test_audio.wav", "rb") as f:
        audio_bytes = f.read()
    
    result = await transcribe(audio_bytes)
    print(f"Text: {result['text']}")
    print(f"Language: {result['language']}")
    print(f"Provider: {result['provider']}")

asyncio.run(test())
```

---

## Troubleshooting

### "Local Whisper model not available"
- Install: `pip install faster-whisper`
- Check: `python -c "import faster_whisper"`

### "Groq client not available"
- Install: `pip install groq`
- Check API key is set in `.env`

### "All transcription providers failed"
- At least one provider must be configured
- Check `.env` file settings
- Check network connectivity for API providers
- Check server has enough RAM for local model

### Slow transcription on CPU
- Use smaller model: `WHISPER_MODEL_SIZE="tiny"`
- Or upgrade to GPU server
- Or switch to Groq API (fast)
