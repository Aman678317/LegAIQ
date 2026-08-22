"""App — the activity router (mirrors the Node kit's App)."""

from __future__ import annotations

import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

from botbuilder.core import ActivityHandler, MessageFactory, TurnContext
from botbuilder.schema import Activity, ActivityTypes

from .ai import AI
from .state import MemoryStorage, TurnState, load_state, save_state
from .support import Recognizer, adaptive_card, render_card

MessageHandler = Callable[[TurnContext, TurnState], Awaitable[None]]
CardActionHandler = Callable[[TurnContext, TurnState, Dict[str, Any]], Awaitable[Any]]
MessageExtensionHandler = Callable[[TurnContext, TurnState, Dict[str, Any]], Awaitable[List[Dict[str, Any]]]]
UnfurlHandler = Callable[[TurnContext, TurnState, str], Awaitable[Optional[Dict[str, Any]]]]

UNFURL_TEMPLATE = {
    "type": "AdaptiveCard",
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.4",
    "body": [
        {"type": "TextBlock", "text": "{{title}}", "weight": "Bolder", "size": "Medium", "wrap": True},
        {"type": "TextBlock", "text": "{{subtitle}}", "isSubtle": True, "wrap": True, "spacing": "None"},
        {"type": "TextBlock", "text": "{{text}}", "wrap": True},
        {"type": "TextBlock", "text": "{{url}}", "size": "Small", "isSubtle": True, "wrap": True},
    ],
}


class App(ActivityHandler):
    """Extend an ActivityHandler with command/intent/card/ME/unfurl routing + AI fallback."""

    def __init__(self, recognizer: Optional[Recognizer] = None, storage: Optional[MemoryStorage] = None) -> None:
        super().__init__()
        self.storage = storage or MemoryStorage()
        self.recognizer = recognizer
        self._messages: List[Dict[str, Any]] = []  # {"pattern": re, "handler": fn}
        self._intents: Dict[str, MessageHandler] = {}
        self._cards: Dict[str, CardActionHandler] = {}
        self._me_handlers: Dict[str, MessageExtensionHandler] = {}
        self._unfurl: Optional[UnfurlHandler] = None
        self._ai: Optional[AI] = None
        self._fallback: Optional[MessageHandler] = None

    # -- registration (each supports app.x(name, fn) and @app.x(name) styles) - #

    def message(self, pattern: str, handler: Optional[MessageHandler] = None):
        def register(fn: MessageHandler) -> MessageHandler:
            self._messages.append({"pattern": re.compile(r"^\s*" + re.escape(pattern) + r"(\s|$)", re.IGNORECASE), "handler": fn})
            return fn
        return register(handler) if handler else register

    def intent(self, name: str, handler: Optional[MessageHandler] = None):
        def register(fn: MessageHandler) -> MessageHandler:
            self._intents[name] = fn
            return fn
        return register(handler) if handler else register

    def card_action(self, name: str, handler: Optional[CardActionHandler] = None):
        def register(fn: CardActionHandler) -> CardActionHandler:
            self._cards[name] = fn
            return fn
        return register(handler) if handler else register

    def message_extension(self, command_id: str, handler: Optional[MessageExtensionHandler] = None):
        def register(fn: MessageExtensionHandler) -> MessageExtensionHandler:
            self._me_handlers[command_id] = fn
            return fn
        return register(handler) if handler else register

    def unfurl(self, handler: Optional[UnfurlHandler] = None):
        def register(fn: UnfurlHandler) -> UnfurlHandler:
            self._unfurl = fn
            return fn
        return register(handler) if handler else register

    def use_ai(self, ai: AI) -> "App":
        self._ai = ai
        return self

    def on_fallback(self, handler: MessageHandler) -> "App":
        self._fallback = handler
        return self

    # -- turn ----------------------------------------------------------------- #

    async def on_turn(self, ctx: TurnContext) -> None:
        """Entry point: wire this to your adapter/bot framework (see samples)."""
        state = await load_state(ctx, self.storage)
        state.temp["locale"] = ctx.activity.locale
        try:
            activity = ctx.activity
            if activity.type == ActivityTypes.invoke and (activity.name or "").startswith("composeExtension/"):
                await self._route_message_extension(ctx, state)
                return
            if activity.type == ActivityTypes.message:
                await self._route_message(ctx, state)
        finally:
            await save_state(ctx, self.storage, state)

    async def _route_message(self, ctx: TurnContext, state: TurnState) -> None:
        activity = ctx.activity
        value = getattr(activity, "value", None) or {}
        action_name = value.get("action") or value.get("actionId")
        if isinstance(action_name, str) and action_name in self._cards:
            outcome = await self._cards[action_name](ctx, state, value)
            if isinstance(outcome, str) and outcome:
                await ctx.send_activity(outcome)
            elif isinstance(outcome, dict):
                await ctx.send_activity(MessageFactory.attachment(adaptive_card(outcome)))
            return

        text = (activity.text or "").strip()
        if not text:
            return

        for entry in self._messages:
            if entry["pattern"].search(text):
                await entry["handler"](ctx, state)
                return

        if self.recognizer:
            intent = await self.recognizer.recognize(ctx, state, text)
            if intent and intent["name"] in self._intents:
                state.temp["intent"] = intent
                await self._intents[intent["name"]](ctx, state)
                return

        if self._ai:
            await self._ai.run(ctx, state, text)
            return

        if self._fallback:
            await self._fallback(ctx, state)
        else:
            await ctx.send_activity("I didn't catch that. Try /help.")

    async def _route_message_extension(self, ctx: TurnContext, state: TurnState) -> None:
        activity = ctx.activity
        name = activity.name or ""

        def respond(body: Dict[str, Any]) -> Awaitable[None]:
            return ctx.send_activity(Activity(type="invokeResponse", value={"statusCode": 200, "body": body}))

        try:
            if name == "composeExtension/query":
                value = activity.value or {}
                parameters = {parameter["name"]: parameter["value"] for parameter in (value.get("parameters") or [])}
                query = {"commandId": value.get("commandId", ""), "parameters": parameters}
                handler = self._me_handlers.get(query["commandId"])
                if not handler:
                    await respond(_error_body(f"Unknown command \"{query['commandId']}\""))
                    return
                results = await handler(ctx, state, query)
                await respond({"composeExtension": {"type": "result", "attachmentLayout": "list", "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.thumbnail",
                        "content": result.get("card") or {"title": result["title"], "subtitle": result.get("subtitle", ""), "text": result["text"]},
                        "preview": {"contentType": "application/vnd.microsoft.card.thumbnail",
                                    "content": {"title": result["title"], "text": result.get("subtitle") or result["text"]}},
                    }
                    for result in results
                ]}})
                return

            if name == "composeExtension/queryLink":
                url = (activity.value or {}).get("url", "")
                if not self._unfurl:
                    await respond(_error_body("No unfurl handler registered"))
                    return
                result = await self._unfurl(ctx, state, url)
                if not result:
                    await respond({"composeExtension": {"type": "result", "attachmentLayout": "list", "attachments": []}})
                    return
                card = result.get("card") or render_card(UNFURL_TEMPLATE, {
                    "title": result["title"], "subtitle": result.get("subtitle", ""), "text": result["text"], "url": url,
                })
                await respond({"composeExtension": {"type": "result", "attachmentLayout": "list", "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": card,
                        "preview": {"contentType": "application/vnd.microsoft.card.thumbnail",
                                    "content": {"title": result["title"], "text": result.get("subtitle") or result["text"]}},
                    }
                ]}})
                return

            await respond(_error_body(f"Unsupported invoke \"{name}\""))
        except Exception as exc:  # noqa: BLE001 — surface ME failures to the client
            await respond(_error_body(str(exc)))


def _error_body(message: str) -> Dict[str, Any]:
    return {"composeExtension": {"type": "message", "text": message}}
