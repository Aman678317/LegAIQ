"""Result model shared by all recognizer families."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Match:
    """A single recognized entity.

    Field names intentionally mirror the canonical spec format
    (Text/Start/End/TypeName/Resolution) so the same JSON specs drive
    every language port of this library.
    """

    text: str
    start: int
    end: int  # inclusive, character offsets into the input text
    type_name: str
    resolution: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # lower wins during overlap resolution

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Text": self.text,
            "TypeName": self.type_name,
            "Start": self.start,
            "End": self.end,
            "Resolution": self.resolution,
        }
