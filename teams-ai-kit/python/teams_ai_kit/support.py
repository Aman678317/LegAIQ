"""Moderation, localization, recognizer, and card helpers (mirrors the Node kit)."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional

from botbuilder.core import TurnContext

from .state import TurnState


# ------------------------------- moderation -------------------------------- #

class Moderator:
    async def review_input(self, ctx: TurnContext, state: TurnState, text: str) -> Optional[str]:
        return None


class NoopModerator(Moderator):
    """The default moderator: allows everything."""


class OpenAIModerator(Moderator):
    """Flags input via OpenAI's moderation endpoint; degrades open without a key."""

    def __init__(self, model: str = "omni-moderation-latest") -> None:
        self._model = model
        self._client = None

    async def review_input(self, _ctx: TurnContext, _state: TurnState, text: str) -> Optional[str]:
        import os

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not text.strip():
            return None
        try:
            if self._client is None:
                from openai import OpenAI

                self._client = OpenAI(api_key=api_key)
            result = self._client.moderations.create(model=self._model, input=text)
            first = result.results[0] if getattr(result, "results", None) else None
            return "moderation_blocked" if first and first.flagged else None
        except Exception:  # moderation is best-effort
            return None


# ------------------------------ localization -------------------------------- #

class Localization:
    def __init__(self, default_locale: str = "en") -> None:
        self._dictionaries: Dict[str, Dict[str, str]] = {}
        self._fallback = default_locale

    def add(self, locale: str, dictionary: Dict[str, str]) -> "Localization":
        self._dictionaries[locale.lower()] = dictionary
        return self

    def resolve_locale(self, locale: Optional[str] = None) -> str:
        wanted = (locale or self._fallback).lower()
        if wanted in self._dictionaries:
            return wanted
        language = wanted.split("-")[0]
        if language in self._dictionaries:
            return language
        return self._fallback

    def t(self, locale: Optional[str], key: str, vars: Optional[Dict[str, str]] = None) -> str:
        dictionary = self._dictionaries.get(self.resolve_locale(locale), {})
        text = dictionary.get(key, self._dictionaries.get(self._fallback, {}).get(key, key))
        for name, value in (vars or {}).items():
            text = text.replace("{{" + name + "}}", value)
        return text


# ------------------------------- recognizer -------------------------------- #

class Intent(dict):
    pass


class Recognizer:
    async def recognize(self, ctx: TurnContext, state: TurnState, text: str) -> Optional[Intent]:
        return None


class RegexRecognizer(Recognizer):
    def __init__(self, intents: Dict[str, Dict[str, Any]]) -> None:
        self._intents = intents  # {"name": {"pattern": re, "entities": {"name": re}}}

    async def recognize(self, _ctx: TurnContext, _state: TurnState, text: str) -> Optional[Intent]:
        for name, rule in self._intents.items():
            if re.search(rule["pattern"], text):
                entities: Dict[str, str] = {}
                for entity, entity_pattern in (rule.get("entities") or {}).items():
                    match = re.search(entity_pattern, text)
                    if match:
                        entities[entity] = match.group(1) if match.groups() else match.group(0)
                return Intent(name=name, entities=entities, score=1.0)
        return None


# --------------------------------- cards ----------------------------------- #

ADAPTIVE_CARD_TYPE = "application/vnd.microsoft.card.adaptive"


def render_card(template: Any, data: Dict[str, Any]) -> Any:
    """Substitute {{dot.path}} placeholders anywhere in an Adaptive Card template."""
    if isinstance(template, str):
        def replace(match: "re.Match[str]") -> str:
            value: Any = data
            for key in match.group(1).split("."):
                value = value.get(key) if isinstance(value, dict) else None
            return "" if value is None else str(value)
        return re.sub(r"\{\{\s*([\w.]+)\s*\}\}", replace, template)
    if isinstance(template, list):
        return [render_card(item, data) for item in template]
    if isinstance(template, dict):
        return {key: render_card(value, data) for key, value in template.items()}
    return template


def adaptive_card(content: Dict[str, Any]) -> Dict[str, Any]:
    return {"contentType": ADAPTIVE_CARD_TYPE, "content": content}


def text_card(text: str, action: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    card: Dict[str, Any] = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [{"type": "TextBlock", "text": text, "wrap": True}],
    }
    if action:
        card["actions"] = [{
            "type": "Action.Submit",
            "title": action["title"],
            "data": {"action": action["actionName"], **action.get("data", {})},
        }]
    return card
