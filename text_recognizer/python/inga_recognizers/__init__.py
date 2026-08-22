"""Inga Recognizers Text: multilingual number/percentage/unit/date-time recognition.

Quick use::

    from inga_recognizers import recognize
    results = recognize("Rent is $1,200.50 for 12 months from 1 March 2026", "en")
"""

from .cultures import available_cultures, load_culture
from .engine import ALL_TYPES, recognize

__all__ = ["recognize", "available_cultures", "load_culture", "ALL_TYPES"]
__version__ = "1.0.0"
