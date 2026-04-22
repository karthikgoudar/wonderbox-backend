import os

class Settings:
    PROJECT_NAME = "WonderBox Backend"
    STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage")
    DEFAULT_EXPIRY_DAYS = int(os.getenv("DEFAULT_EXPIRY_DAYS", "25"))
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # STT (Speech-to-Text) Configuration
    STT_PRIMARY_PROVIDER = os.getenv("STT_PRIMARY_PROVIDER", "local_whisper")  # local_whisper, groq, openai
    STT_ENABLE_FALLBACK = os.getenv("STT_ENABLE_FALLBACK", "true").lower() == "true"
    
    # Local Whisper settings
    WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")  # tiny, base, small, medium, large
    WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")  # cpu, cuda
    WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # int8, float16, float32
    
    # Groq API (has free tier with Whisper models)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")  # Add your Groq API key
    GROQ_MODEL = os.getenv("GROQ_MODEL", "whisper-large-v3")
    
    # OpenAI Whisper API (paid fallback)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # Add your OpenAI API key
    OPENAI_WHISPER_MODEL = os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")
    
    # Image Generation Configuration
    IMAGE_PRIMARY_PROVIDER = os.getenv("IMAGE_PRIMARY_PROVIDER", "replicate")  # replicate, stability
    IMAGE_ENABLE_FALLBACK = os.getenv("IMAGE_ENABLE_FALLBACK", "true").lower() == "true"
    
    # Image generation settings
    IMAGE_WIDTH = int(os.getenv("IMAGE_WIDTH", "512"))
    IMAGE_HEIGHT = int(os.getenv("IMAGE_HEIGHT", "512"))
    IMAGE_STYLE = os.getenv("IMAGE_STYLE", "coloring_book")  # coloring_book, realistic, cartoon
    
    # Replicate (access to multiple models including Flux, SDXL)
    # Backend uses ONE API token for all devices
    REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
    REPLICATE_MODEL = os.getenv(
        "REPLICATE_MODEL",
        "black-forest-labs/flux-schnell"  # Fast, free tier available
        # Alternative: "black-forest-labs/flux-dev" (better quality, paid)
        # Alternative: "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
    )
    
    # Stability AI (Stable Diffusion)
    # Backend uses ONE API key for all devices
    STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")
    STABILITY_MODEL = os.getenv("STABILITY_MODEL", "stable-diffusion-xl-1024-v1-0")  # or sd3-medium
    
    # Usage Limits & Quotas (enforced at backend level)
    # These limits protect YOUR API costs across all devices
    DEFAULT_DAILY_STICKER_LIMIT = int(os.getenv("DEFAULT_DAILY_STICKER_LIMIT", "10"))  # Per device
    COMPANY_DAILY_LIMIT = int(os.getenv("COMPANY_DAILY_LIMIT", "1000"))  # Total across all devices
    SUBSCRIPTION_OVERRIDE_LIMIT = int(os.getenv("SUBSCRIPTION_OVERRIDE_LIMIT", "50"))  # Premium users


settings = Settings()
