from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "Jurisiva AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Database
    DATABASE_URL: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # AI Providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # OCR
    OCR_PROVIDER: str = "tesseract"
    TESSERACT_CMD: str = "tesseract"

    # Web Research
    SEARCH_API_KEY: str = ""

    # Voice — server-side providers for browsers without Web Speech
    STT_API_KEY: str = ""
    STT_API_BASE: str = "https://api.openai.com/v1"
    STT_MODEL: str = "whisper-1"
    TTS_API_KEY: str = ""
    TTS_API_BASE: str = "https://api.openai.com/v1"
    TTS_MODEL: str = "tts-1"
    TTS_VOICE: str = "alloy"

    # Storage
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: list[str] = ["application/pdf", "image/jpeg", "image/png", "image/tiff"]

    # Supported Languages
    SUPPORTED_LANGUAGES: list[str] = [
        "en", "hi", "kn", "ta", "te", "ml", "mr", "bn", "gu", "pa", "ur"
    ]

    # LLM Defaults
    DEFAULT_LLM_PROVIDER: str = "openai"
    DEFAULT_MODEL: str = "gpt-4o-mini"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"
    MAX_TOKEN_BUDGET: int = 4096

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
