"""Models — one complete() method behind the AI system (mirrors the Node kit)."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

DEFAULT_MODEL = "gpt-5.6-terra"


class Model:
    """Interface: complete(instructions, transcript) -> raw model output."""

    def complete(self, instructions: str, transcript: List[Dict[str, str]]) -> str:
        raise NotImplementedError


class ModelMessage(Dict[str, str]):
    pass


def message(role: str, text: str) -> Dict[str, str]:
    return {"role": role, "text": text}


class OpenAIModel:
    """OpenAI (or OpenAI-compatible endpoint) via the Responses API."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        from openai import OpenAI  # imported lazily

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAIModel needs api_key or OPENAI_API_KEY in the environment.")
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=120)
        self._model = model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL

    def complete(self, instructions: str, transcript: List[Dict[str, str]]) -> str:
        response = self._client.responses.create(
            model=self._model,
            instructions=instructions,
            input=[{"role": item["role"], "content": item["text"]} for item in transcript],
        )
        return response.output_text or ""


class AzureOpenAIModel:
    """Azure OpenAI via the Responses API on a deployment."""

    def __init__(self, endpoint: str, api_key: Optional[str] = None, api_version: str = "2025-04-01-preview", deployment: Optional[str] = None) -> None:
        from openai import AzureOpenAI

        api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        if not endpoint or not api_key:
            raise ValueError("AzureOpenAIModel needs endpoint and api_key (or AZURE_OPENAI_API_KEY).")
        self._client = AzureOpenAI(endpoint=endpoint, api_key=api_key, api_version=api_version, timeout=120)
        self._deployment = deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT") or "gpt-5.6"

    def complete(self, instructions: str, transcript: List[Dict[str, str]]) -> str:
        response = self._client.responses.create(
            model=self._deployment,
            instructions=instructions,
            input=[{"role": item["role"], "content": item["text"]} for item in transcript],
        )
        return response.output_text or ""


class MockModel:
    """Offline, deterministic model for tests and keyless sample runs."""

    def __init__(self, say=None, do: Optional[List[Dict[str, Any]]] = None) -> None:
        self._say = say or (lambda text: f"You said: {text}")
        self._do = do or []

    def complete(self, _instructions: str, transcript: List[Dict[str, str]]) -> str:
        last_user = next((item for item in reversed(transcript) if item["role"] == "user"), None)
        text = last_user["text"] if last_user else ""
        if not text.startswith("Observation"):  # reply, don't re-trigger, after actions
            for trigger in self._do:
                if re.search(trigger["pattern"], text):
                    return f"DO {trigger['name']} {json.dumps(trigger.get('args', {}))}"
        return f"SAY {self._say(text)}"
