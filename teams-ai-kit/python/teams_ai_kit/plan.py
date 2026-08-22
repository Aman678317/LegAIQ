"""Plan parsing — SAY/DO commands, identical to the Node kit."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Union

SAY_RE = re.compile(r"^SAY\s*(.*)$", re.IGNORECASE)
DO_RE = re.compile(r"^DO\s+([A-Za-z0-9_.-]+)\s*(.*)$", re.IGNORECASE)

PlanCommand = Dict[str, Any]


class PlanFormatError(Exception):
    pass


def parse_plan(raw: str) -> List[PlanCommand]:
    commands: List[PlanCommand] = []
    say_lines: List[str] = []

    def flush_say():
        if say_lines:
            text = "\n".join(say_lines).strip()
            if text:
                commands.append({"type": "SAY", "text": text})
        say_lines.clear()

    for line in raw.strip().splitlines():
        say = SAY_RE.match(line)
        do = DO_RE.match(line)
        if say and not say_lines:
            say_lines.append(say.group(1))
            continue
        if do:
            flush_say()
            args: Dict[str, Any] = {}
            rest = do.group(2).strip()
            if rest:
                try:
                    parsed = json.loads(rest)
                    args = parsed if isinstance(parsed, dict) else {"value": parsed}
                except json.JSONDecodeError as exc:
                    raise PlanFormatError(f"DO command has invalid JSON arguments: {rest[:60]}") from exc
            commands.append({"type": "DO", "action": do.group(1), "args": args})
            continue
        if say_lines:
            say_lines.append(line)
    flush_say()

    if not commands:
        text = raw.strip()
        if not text:
            raise PlanFormatError("The model returned an empty plan.")
        return [{"type": "SAY", "text": text}]
    return commands
