"""Culture registry: loads the shared per-language JSON definitions.

The JSON files under ``text_recognizer/cultures`` are the single source of
truth for every port of this library (Python, .NET, future TypeScript).
Each implementation reads the exact same files, which keeps behavior in
lockstep across language versions.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

_FALLBACK_CULTURE = "en"


def _default_cultures_dir() -> Path:
    override = os.environ.get("INGA_RECOGNIZERS_CULTURES")
    if override:
        return Path(override)
    # <repo>/text_recognizer/python/inga_recognizers/cultures.py ->
    # <repo>/text_recognizer/cultures
    return Path(__file__).resolve().parents[2] / "cultures"


def available_cultures() -> list[str]:
    return sorted(p.stem for p in _default_cultures_dir().glob("*.json"))


@lru_cache(maxsize=None)
def load_culture(culture: str) -> Dict[str, Any]:
    """Load a culture definition; unknown cultures fall back to English."""
    culture = (culture or _FALLBACK_CULTURE).lower()
    path = _default_cultures_dir() / f"{culture}.json"
    if not path.exists():
        path = _default_cultures_dir() / f"{_FALLBACK_CULTURE}.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)
