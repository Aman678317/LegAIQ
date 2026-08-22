"""AI — the orchestration loop: moderate → plan → execute DO actions → SAY."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional

from botbuilder.core import TurnContext

from .models import Model
from .support import Moderator, NoopModerator  # noqa: F401  (NoopModerator re-exported for parity)
from .plan import parse_plan
from .state import TurnState

ActionHandler = Callable[[TurnContext, TurnState, Dict[str, Any]], Awaitable[str]]

DEFAULT_PROMPT = "You are a helpful assistant embedded in Microsoft Teams."


class AI:
    def __init__(
        self,
        model: Model,
        prompt: Optional[str] = None,
        moderator: Optional[Moderator] = None,
        max_steps: int = 4,
        history_turns: int = 20,
        on_blocked: Optional[Callable[[TurnContext, TurnState, str], Awaitable[None]]] = None,
    ) -> None:
        self.model = model
        self._prompt = prompt or DEFAULT_PROMPT
        self._moderator = moderator or NoopModerator()
        self._max_steps = max_steps
        self._history_turns = history_turns
        self._on_blocked = on_blocked
        self._actions: Dict[str, ActionHandler] = {}

    def action(self, name: str, handler: Optional[ActionHandler] = None):
        """Register an action — supports ai.action(name, fn) and @ai.action(name)."""
        def register(fn: ActionHandler) -> ActionHandler:
            self._actions[name] = fn
            return fn
        return register(handler) if handler else register

    def _instructions(self) -> str:
        lines = [
            self._prompt, "",
            "Reply with a plan using EXACTLY one of these command forms:",
            "SAY <text to send to the user>",
            "DO <action> <json arguments>",
        ]
        if self._actions:
            lines += ["", "Available actions:"] + [f"- {name}" for name in self._actions]
            lines += ["", "Prefer DO when an action matches the user's request; otherwise SAY. "
                           "After a DO completes you will see its result and may SAY a reply. Never invent actions."]
        return "\n".join(lines)

    async def run(self, ctx: TurnContext, state: TurnState, text: str) -> None:
        blocked = await self._moderator.review_input(ctx, state, text)
        if blocked:
            if self._on_blocked:
                await self._on_blocked(ctx, state, blocked)
            else:
                await ctx.send_activity("I can't help with that request.")
            return

        history: List[Dict[str, str]] = state.conversation.setdefault("history", [])
        history.append({"role": "user", "text": text})
        state.temp["input"] = text

        observations: List[str] = []
        steps = 0
        said = False

        while not said and steps <= self._max_steps:
            transcript = history[-self._history_turns:] + [{"role": "user", "text": observation} for observation in observations]
            commands = parse_plan(self.model.complete(self._instructions(), transcript))
            for command in commands:
                if command["type"] == "SAY":
                    reply = command["text"].strip()
                    if reply:
                        await ctx.send_activity(reply)
                        history.append({"role": "assistant", "text": reply})
                    said = True
                else:
                    steps += 1
                    handler = self._actions.get(command["action"])
                    if not handler:
                        observations.append(f"ERROR: unknown action \"{command['action']}\"")
                        continue
                    result = await handler(ctx, state, command.get("args") or {})
                    observations.append(f"Observation [{command['action']}]: {str(result)[:500]}")

        if not said:
            await ctx.send_activity("I wasn't able to finish that request — let's try again.")
        if len(history) > self._history_turns * 2:
            state.conversation["history"] = history[-self._history_turns:]
