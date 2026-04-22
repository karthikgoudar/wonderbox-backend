# WonderBox Backend

Production-ready foundation for the WonderBox device backend (Sticker Mode v1).

## Quick Start

### 1. Environment Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and configure your STT provider (see Configuration section below).

### 3. Run the Server

```bash
uvicorn app.main:app --reload
```

The server will start at `http://localhost:8000`

## Speech-to-Text (STT) Configuration

The backend supports **3 STT providers** with automatic fallback:

### Option 1: Local Whisper (Recommended for Development)

**Pros:** Free, private, no API limits  
**Cons:** Requires server resources, slower on CPU

```bash
# Install faster-whisper
pip install faster-whisper

# In .env file:
STT_PRIMARY_PROVIDER="local_whisper"
WHISPER_MODEL_SIZE="base"  # tiny, base, small, medium, large
WHISPER_DEVICE="cpu"        # or "cuda" if you have NVIDIA GPU
```

**First run:** Model will auto-download (~1GB for base model)

### Option 2: Groq API (Recommended for Production)

**Pros:** Free tier, very fast, accurate  
**Cons:** Requires API key, network dependency

```bash
# Install Groq SDK
pip install groq

# Get free API key from: https://console.groq.com/keys

# In .env file:
STT_PRIMARY_PROVIDER="groq"
GROQ_API_KEY="your-api-key-here"
```

### Option 3: OpenAI Whisper API

**Pros:** Highly reliable, accurate  
**Cons:** Paid (~$0.006/minute of audio)

```bash
# Install OpenAI SDK
pip install openai

# Get API key from: https://platform.openai.com/api-keys

# In .env file:
STT_PRIMARY_PROVIDER="openai"
OPENAI_API_KEY="your-api-key-here"
```

### Multi-Provider Fallback

Enable automatic fallback if primary provider fails:

```bash
STT_ENABLE_FALLBACK="true"
```

**Fallback order:** Primary → Groq → OpenAI → Local Whisper

## Supported Languages

- **English** (en)
- **Hindi** (hi)

Language is auto-detected from the audio.

## Image Generation Configuration

The backend supports **2 image generation providers** for creating coloring book style stickers:

**Important:** API keys are held by the BACKEND only. Devices authenticate with device tokens, and the backend enforces quotas to protect API costs. See [API Key Architecture](docs/api_key_architecture.md) for details.

### Option 1: Replicate (Flux Schnell) - Recommended

**Pros:** Free tier, very fast (2-4s), excellent for line art  
**Cons:** Requires API token

```bash
# Install Replicate SDK
pip install replicate

# Get free token: https://replicate.com/account/api-tokens

# In .env file:
IMAGE_PRIMARY_PROVIDER="replicate"
REPLICATE_API_TOKEN="your-token-here"
REPLICATE_MODEL="black-forest-labs/flux-schnell"
```

### Option 2: Stability AI (SDXL)

**Pros:** Built-in "line-art" preset perfect for coloring books, high quality  
**Cons:** Paid (~$0.003/image)

```bash
# Get API key: https://platform.stability.ai/account/keys

# In .env file:
IMAGE_PRIMARY_PROVIDER="stability"
STABILITY_API_KEY="your-key-here"
```

**Recommendation:** Start with **Replicate (Flux Schnell)** for free development, then upgrade to Flux Dev or Stability SDXL for production (~$3/1000 images).

See [Image Generation Guide](docs/image_generation_guide.md) for detailed comparison and [API Key Architecture](docs/api_key_architecture.md) for multi-device quota management.

## Supported Languages

- **English** (en)
- **Hindi** (hi)

Language is auto-detected from the audio.

## API Endpoints

### POST /sticker/submit
Submit audio for sticker generation. Returns a `job_id`.

**Request:**
- `device_id` (form): Device identifier
- `child_id` (form): Child identifier  
- `audio` (file): Audio file (WAV, MP3, etc.)
- `x-device-token` (header): Device authentication token

**Response:**
```json
{"job_id": "uuid-here"}
```

### GET /sticker/{job_id}/stream
Stream real-time pipeline updates via Server-Sent Events (SSE).

**Events:**
- `status`: Processing started
- `progress`: Current pipeline step
- `text`: Transcribed text + language
- `image_ready`: Image URL available
- `done`: Sticker generation complete
- `error`: Pipeline error

## Architecture

See [docs/architecture.md](docs/architecture.md) for system design details.
