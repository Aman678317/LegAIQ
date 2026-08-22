"""TurnState — conversation/user/temp scopes backed by pluggable storage."""

from __future__ import annotations

import copy
from typing import Any, Dict

from botbuilder.core import TurnContext


class TurnState:
    def __init__(self) -> None:
        self.conversation: Dict[str, Any] = {}
        self.user: Dict[str, Any] = {}
        self.temp: Dict[str, Any] = {}


class MemoryStorage:
    """In-memory storage. Swap in any Storage implementation for persistence."""

    def __init__(self) -> None:
        self._memory: Dict[str, Dict[str, Any]] = {}

    async def read(self, keys):
        return {key: copy.deepcopy(self._memory[key]) for key in keys if key in self._memory}

    async def write(self, changes: Dict[str, Dict[str, Any]]) -> None:
        for key, value in changes.items():
            self._memory[key] = copy.deepcopy(value)

    async def delete(self, keys) -> None:
        for key in keys:
            self._memory.pop(key, None)


def _storage_keys(ctx: TurnContext):
    channel = ctx.activity.channel_id or "unknown"
    conversation = (ctx.activity.conversation and ctx.activity.conversation.id) or f"{channel}/none"
    user = (ctx.activity.from_property and ctx.activity.from_property.id) if hasattr(ctx.activity, "from_property") else None
    if user is None:
        user = getattr(ctx.activity, "from_id", None) or "anonymous"
    return f"{channel}/{conversation}", f"{channel}/{user}"


async def load_state(ctx: TurnContext, storage: MemoryStorage) -> TurnState:
    conversation_key, user_key = _storage_keys(ctx)
    stored = await storage.read([conversation_key, user_key])
    state = TurnState()
    state.conversation = stored.get(conversation_key, {})
    state.user = stored.get(user_key, {})
    return state


async def save_state(ctx: TurnContext, storage: MemoryStorage, state: TurnState) -> None:
    conversation_key, user_key = _storage_keys(ctx)
    changes: Dict[str, Dict[str, Any]] = {}
    if state.conversation:
        changes[conversation_key] = state.conversation
    if state.user:
        changes[user_key] = state.user
    await storage.write(changes)
