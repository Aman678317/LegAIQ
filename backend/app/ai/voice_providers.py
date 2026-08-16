"""Server-side speech providers (STT/TTS) for browsers without Web Speech.

Uses any OpenAI-compatible endpoint (Whisper for STT, TTS for speech).
When unconfigured, functions return None so callers can fall back to the
browser APIs — or surface an honest "not configured" error.
"""
import hashlib
from datetime import datetime, timezone

import httpx

from app.config import get_settings

settings = get_settings()

# Whisper returns BCP-47-ish names; map the ones we support
_LANGUAGE_MAP = {
    "english": "en", "hindi": "hi", "kannada": "kn", "tamil": "ta",
    "telugu": "te", "malayalam": "ml", "marathi": "mr", "bengali": "bn",
    "gujarati": "gu", "punjabi": "pa", "urdu": "ur",
    "en": "en", "hi": "hi", "kn": "kn", "ta": "ta", "te": "te", "ml": "ml",
    "mr": "mr", "bn": "bn", "gu": "gu", "pa": "pa", "ur": "ur",
}


def stt_configured() -> bool:
    return bool(settings.STT_API_KEY)


def tts_configured() -> bool:
    return bool(settings.TTS_API_KEY)


async def transcribe_audio(
    audio: bytes, filename: str, mime_type: str
) -> dict | None:
    """Transcribe speech via Whisper-compatible API. None when unconfigured."""
    if not stt_configured():
        return None

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f"{settings.STT_API_BASE}/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.STT_API_KEY}"},
            files={"file": (filename, audio, mime_type or "audio/webm")},
            data={"model": settings.STT_MODEL, "response_format": "verbose_json"},
        )
        resp.raise_for_status()
        data = resp.json()

    raw_lang = (data.get("language") or "").lower()
    language = _LANGUAGE_MAP.get(raw_lang, "en")
    return {
        "transcript": data.get("text", "").strip(),
        "language": language,
        "duration_s": data.get("duration"),
        "provider": f"whisper:{settings.STT_MODEL}",
    }


async def synthesize_speech(text: str, language: str = "en") -> tuple[bytes, str] | None:
    """Synthesize speech via OpenAI-compatible TTS. None when unconfigured."""
    if not tts_configured():
        return None

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f"{settings.TTS_API_BASE}/audio/speech",
            headers={"Authorization": f"Bearer {settings.TTS_API_KEY}"},
            json={
                "model": settings.TTS_MODEL,
                "voice": settings.TTS_VOICE,
                "input": text[:4000],
                "response_format": "mp3",
            },
        )
        resp.raise_for_status()
        return resp.content, "audio/mpeg"


def usage_signature(prefix: str) -> str:
    """Stable per-run signature for provider attribution in logs."""
    return hashlib.sha1(f"{prefix}:{datetime.now(timezone.utc).date()}".encode()).hexdigest()[:8]
