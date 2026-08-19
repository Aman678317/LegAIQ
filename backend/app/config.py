from typing import Any, ClassVar
from functools import lru_cache
from pydantic import field_validator, computed_field, Field
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    APP_NAME: str = "Jurisiva AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
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
    CORS_ORIGINS_RAW: str = Field(default="*", validation_alias="CORS_ORIGINS")

    @computed_field
    @property
    def CORS_ORIGINS(self) -> list[str]:
        raw = self.CORS_ORIGINS_RAW
        if not raw or not raw.strip():
            return ["*"]
        raw = raw.strip()
        # JSON array
        if raw.startswith("[") and raw.endswith("]"):
            try:
                import json
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(x).strip().strip('"').strip("'") for x in parsed if str(x).strip()]
            except Exception:
                pass
        # comma-separated
        parts = [p.strip().strip('"').strip("'") for p in raw.split(",") if p.strip()]
        return parts if parts else ["*"]

    # AI Providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # Ollama Local AI
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # OCR
    OCR_PROVIDER: str = "tesseract"
    TESSERACT_CMD: str = "tesseract"

    # Web Research
    SEARCH_API_KEY: str = ""

    # Voice — server-side providers for browsers without Web Speech
    STT_API_KEY: str = ""
    STT_API_BASE: str = "https://api.groq.com/openai/v1"
    STT_MODEL: str = "whisper-large-v3-turbo"
    TTS_API_KEY: str = ""
    TTS_API_BASE: str = "https://api.openai.com/v1"
    TTS_MODEL: str = "tts-1"
    TTS_VOICE: str = "alloy"

    # Storage
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES_RAW: str = Field(
        default="application/pdf,image/jpeg,image/png,image/tiff",
        validation_alias="ALLOWED_FILE_TYPES"
    )

    @computed_field
    @property
    def ALLOWED_FILE_TYPES(self) -> list[str]:
        raw = self.ALLOWED_FILE_TYPES_RAW
        if not raw:
            return []
        try:
            import json
            if raw.strip().startswith("["):
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
        except Exception:
            pass
        return [p.strip() for p in raw.split(",") if p.strip()]

    # Supported Languages (13 Major Indian Languages + English)
    SUPPORTED_LANGUAGES_RAW: str = Field(
        default="en,hi,kn,ta,te,ml,mr,bn,gu,pa,ur,or,as",
        validation_alias="SUPPORTED_LANGUAGES"
    )

    @computed_field
    @property
    def SUPPORTED_LANGUAGES(self) -> list[str]:
        raw = self.SUPPORTED_LANGUAGES_RAW
        if not raw:
            return []
        try:
            import json
            if raw.strip().startswith("["):
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
        except Exception:
            pass
        return [p.strip() for p in raw.split(",") if p.strip()]

    # LLM Defaults
    DEFAULT_LLM_PROVIDER: str = "openai"
    DEFAULT_MODEL: str = "gpt-4o-mini"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"
    MAX_TOKEN_BUDGET: int = 4096

    # Look for .env in project root (parent of backend/)
    _env_path: ClassVar[str] = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    model_config: ClassVar[dict] = {"env_file": _env_path, "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()