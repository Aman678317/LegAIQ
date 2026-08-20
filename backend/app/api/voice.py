"""Voice assistant API (Phase 16).

Pipeline: browser STT transcript → voice agent (case-grounded, budgeted) →
answer + citations → client-side TTS (or provider TTS when configured).

The agent never claims to be a human lawyer. Language matching: respond in
the language spoken, or switch when the user asks.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from supabase import create_client

from app.ai.agents.registry import run_voice_agent
from app.config import get_settings
from app.security.auth import get_case_access, resource_case_access

settings = get_settings()
router = APIRouter(tags=["voice"])

SUPPORTED_VOICE_LANGS = {"en", "hi", "kn", "ta", "te", "ml", "mr", "bn", "gu", "pa", "ur"}


def _db():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None


class VoiceSessionCreate(BaseModel):
    language: str = "en"


class VoiceTurnRequest(BaseModel):
    session_id: str
    transcript: str = Field(min_length=1, max_length=2000)
    language: Optional[str] = None  # override session language per turn
    stt_provider: Optional[str] = None  # browser-webspeech | server-whisper | typed


@router.post("/cases/{case_id}/voice/session")
async def create_voice_session(case_id: str, body: VoiceSessionCreate, _=Depends(get_case_access)):
    ctx, case = _
    if body.language not in SUPPORTED_VOICE_LANGS:
        raise HTTPException(400, f"Unsupported language '{body.language}'")

    session = _db().table("voice_sessions").insert({
        "case_id": case_id,
        "user_id": ctx.user_id,
        "language": body.language,
        "status": "ACTIVE",
    }).execute().data[0]
    return session


@router.get("/cases/{case_id}/voice/sessions")
async def list_voice_sessions(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    return (
        _db().table("voice_sessions").select("*").eq("case_id", case_id)
        .order("created_at", desc=True).limit(20).execute().data
    )


@router.get("/voice/sessions/{session_id}/turns")
async def get_voice_turns(session_id: str, _=Depends(resource_case_access("voice_sessions", "session_id"))):
    ctx, case = _
    session = _db().table("voice_sessions").select("case_id").eq("id", session_id).single().execute()
    if not session.data or session.data["case_id"] != case["id"]:
        raise HTTPException(404, "Voice session not found in this case")
    return (
        _db().table("voice_turns").select("*").eq("session_id", session_id)
        .order("created_at").execute().data
    )


@router.post("/cases/{case_id}/voice/message")
async def voice_message(case_id: str, body: VoiceTurnRequest, _=Depends(get_case_access)):
    ctx, case = _
    db = _db()

    session = db.table("voice_sessions").select("*").eq("id", body.session_id).single().execute().data
    if not session or session["case_id"] != case_id:
        raise HTTPException(404, "Voice session not found in this case")
    if session["status"] != "ACTIVE":
        raise HTTPException(400, "Voice session has ended")

    language = body.language or session["language"]
    if language not in SUPPORTED_VOICE_LANGS:
        language = "en"
    # Update session language when the user switches mid-conversation
    if language != session["language"]:
        db.table("voice_sessions").update({"language": language}).eq("id", session["id"]).execute()

    # Record the user turn with the actual capture method
    db.table("voice_turns").insert({
        "session_id": session["id"], "case_id": case_id,
        "role": "user", "content": body.transcript,
        "language": language,
        "stt_provider": body.stt_provider or "browser-webspeech",
    }).execute()

    try:
        result = await run_voice_agent(
            case_id, body.transcript, language,
            organization_id=case["organization_id"], user_id=ctx.user_id,
        )
    except Exception as e:
        raise HTTPException(500, f"Voice agent failed: {e}")

    turn = db.table("voice_turns").insert({
        "session_id": session["id"], "case_id": case_id,
        "role": "assistant", "content": result["answer"],
        "language": result.get("language", language),
        "citations": result.get("citations"),
        "tts_provider": "client",  # speech synthesis happens on-device
    }, ).execute().data[0]

    return {
        "turn_id": turn["id"],
        "answer": result["answer"],
        "citations": result.get("citations", []),
        "language": result.get("language", language),
        "agent": "voice_agent",
    }


@router.post("/cases/{case_id}/voice/transcribe")
async def voice_transcribe(
    case_id: str,
    audio: UploadFile = File(...),
    _=Depends(get_case_access),
):
    """Server-side STT for browsers without Web Speech (Safari/Firefox).

    Accepts webm/ogg/mp3/wav recordings. Returns an honest error when no
    provider is configured — never a fake transcript.
    """
    ctx, case = _

    content = await audio.read()
    if not content:
        raise HTTPException(400, "Empty audio upload")
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(400, "Audio exceeds 25 MB limit")

    from app.ai.voice_providers import stt_configured, transcribe_audio
    if not stt_configured():
        raise HTTPException(
            503,
            "Server speech-to-text is not configured (STT_API_KEY missing). "
            "Use a browser with Web Speech support (Chrome/Edge) or set STT_API_KEY.",
        )

    try:
        result = await transcribe_audio(
            content, audio.filename or "speech.webm",
            audio.content_type or "audio/webm",
        )
    except Exception as e:
        raise HTTPException(502, f"Speech-to-text provider failed: {e}")

    if not result or not result["transcript"]:
        raise HTTPException(422, "No speech detected in the recording")

    return result


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: str = "en"


@router.post("/cases/{case_id}/voice/speak")
async def voice_speak(
    case_id: str, body: SpeakRequest, _=Depends(get_case_access)
):
    """Server-side TTS for browsers without speechSynthesis. Returns MP3 bytes."""
    ctx, case = _

    from app.ai.voice_providers import synthesize_speech, tts_configured
    if not tts_configured():
        raise HTTPException(
            503,
            "Server text-to-speech is not configured (TTS_API_KEY missing). "
            "Use a browser with speech synthesis or set TTS_API_KEY.",
        )

    try:
        audio = await synthesize_speech(body.text, body.language)
    except Exception as e:
        raise HTTPException(502, f"Text-to-speech provider failed: {e}")

    if not audio:
        raise HTTPException(502, "TTS provider returned no audio")

    content, media_type = audio
    return Response(content=content, media_type=media_type)


@router.post("/voice/sessions/{session_id}/end")
async def end_voice_session(session_id: str, _=Depends(resource_case_access("voice_sessions", "session_id"))):
    ctx, case = _
    db = _db()
    session = db.table("voice_sessions").select("case_id").eq("id", session_id).single().execute().data
    if not session or session["case_id"] != case["id"]:
        raise HTTPException(404, "Voice session not found in this case")
    return db.table("voice_sessions").update({
        "status": "ENDED", "ended_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", session_id).execute().data[0]
