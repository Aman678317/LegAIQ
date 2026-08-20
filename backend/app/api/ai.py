"""AI and Ollama provider API routes."""
from typing import Any, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.ai.provider import LLMRequest, generate_embedding, router as llm_router
from app.config import get_settings
from app.security.auth import AuthContext, get_auth_context, require_role

settings = get_settings()
router = APIRouter(prefix="/ai", tags=["ai"])


class ChatMessage(BaseModel):
    role: str
    content: str


class OllamaChatRequest(BaseModel):
    model: Optional[str] = "llama3"
    messages: list[ChatMessage]
    system: Optional[str] = None
    temperature: Optional[float] = 0.2
    json_mode: Optional[bool] = False


class EmbedRequest(BaseModel):
    text: str
    model: Optional[str] = None


@router.get("/ollama/status")
async def get_ollama_status():
    """Check if the local/configured Ollama server is running and list models."""
    base_url = (settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                raw_models = data.get("models", [])
                models = [m.get("name") for m in raw_models if m.get("name")]
                active_model = models[0] if models else settings.OLLAMA_MODEL
                return {
                    "online": True,
                    "base_url": base_url,
                    "models": models,
                    "active_model": active_model,
                    "total_models": len(models),
                }
    except Exception as e:
        return {
            "online": False,
            "base_url": base_url,
            "models": [],
            "active_model": None,
            "error": str(e),
            "help": "Start Ollama with: $env:OLLAMA_ORIGINS=\"*\" ; ollama serve",
        }

    return {
        "online": False,
        "base_url": base_url,
        "models": [],
        "active_model": None,
        "error": "Non-200 response from Ollama",
    }


@router.post("/ollama/chat")
async def chat_with_ollama(body: OllamaChatRequest, ctx: AuthContext = Depends(get_auth_context)):
    """Direct chat completion with Ollama through backend proxy."""
    base_url = (settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
    model = body.model or settings.OLLAMA_MODEL or "llama3"

    formatted_messages = []
    if body.system:
        formatted_messages.append({"role": "system", "content": body.system})
    for m in body.messages:
        formatted_messages.append({"role": m.role, "content": m.content})

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": formatted_messages,
                    "stream": False,
                    "options": {"temperature": body.temperature or 0.2},
                    **({"format": "json"} if body.json_mode else {}),
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "content": data.get("message", {}).get("content", ""),
                    "model": model,
                    "provider": "ollama",
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                }
    except Exception:
        pass

    # Fallback to standard ModelRouter
    user_prompt = body.messages[-1].content if body.messages else ""
    sys_prompt = body.system or "You are Jurisiva AI, Indian legal intelligence assistant."
    fallback_resp = await llm_router.complete(LLMRequest(
        system=sys_prompt,
        prompt=user_prompt,
        task="chat",
        model=model,
        temperature=body.temperature or 0.2,
        json_mode=bool(body.json_mode),
    ))
    return {
        "content": fallback_resp.content,
        "model": fallback_resp.model,
        "provider": fallback_resp.provider,
        "latency_ms": fallback_resp.latency_ms,
    }


@router.post("/embed")
async def create_embedding(body: EmbedRequest):
    """Generate vector embedding using Ollama or OpenAI."""
    vec = await generate_embedding(body.text)
    if not vec:
        raise HTTPException(status_code=503, detail="No embedding model currently available")
    return {"embedding": vec, "dimensions": len(vec)}


@router.get("/providers")
async def get_providers():
    """Return status of all configured AI providers."""
    ollama_status = await get_ollama_status()
    return {
        "nvidia": bool(settings.NVIDIA_API_KEY),
        "ollama": ollama_status,
        "openai": bool(settings.OPENAI_API_KEY),
        "anthropic": bool(settings.ANTHROPIC_API_KEY),
        "groq": bool(settings.STT_API_KEY),
        "default_provider": settings.DEFAULT_LLM_PROVIDER,
        "default_model": settings.DEFAULT_MODEL,
    }
