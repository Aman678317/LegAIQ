"""teams-ai-kit (Python) — smart bots and app extensions for Teams & Bot Framework channels.

API-mirrored with the Node/TypeScript kit (see ../node); see README.md.
"""

from .ai import AI
from .application import App
from .models import AzureOpenAIModel, MockModel, OpenAIModel
from .plan import PlanFormatError, parse_plan
from .state import MemoryStorage, TurnState, load_state, save_state
from .support import (
    ADAPTIVE_CARD_TYPE,
    Intent,
    Localization,
    Moderator,
    NoopModerator,
    OpenAIModerator,
    Recognizer,
    RegexRecognizer,
    adaptive_card,
    render_card,
    text_card,
)

__version__ = "0.1.0"
