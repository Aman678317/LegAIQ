"""Tests for the Python kit — mirrors the Node suite's coverage."""

import pytest

from teams_ai_kit import (
    AI,
    App,
    Localization,
    MockModel,
    RegexRecognizer,
    adaptive_card,
    parse_plan,
    render_card,
    text_card,
)
from teams_ai_kit.plan import PlanFormatError
from teams_ai_kit.state import MemoryStorage, TurnState, load_state, save_state


# --------------------------------- plan ---------------------------------- #

def test_parse_say_with_continuation():
    assert parse_plan("SAY hello\nsecond line") == [{"type": "SAY", "text": "hello\nsecond line"}]


def test_parse_do_with_and_without_args():
    assert parse_plan('DO createTicket {"priority":"high"}') == [
        {"type": "DO", "action": "createTicket", "args": {"priority": "high"}}
    ]
    assert parse_plan("DO listAll") == [{"type": "DO", "action": "listAll", "args": {}}]


def test_parse_plain_text_becomes_say():
    assert parse_plan("just chatting") == [{"type": "SAY", "text": "just chatting"}]


def test_parse_invalid_json_raises():
    with pytest.raises(PlanFormatError):
        parse_plan("DO x {oops}")


# ------------------------------- support ---------------------------------- #

def test_localization_fallback_chain():
    locales = Localization().add("en", {"hi": "Hello {{name}}"}).add("es", {"hi": "Hola {{name}}"})
    assert locales.t("es-MX", "hi", {"name": "Ana"}) == "Hola Ana"
    assert locales.t("fr-FR", "hi", {"name": "Zoe"}) == "Hello Zoe"


def test_render_card_binds_paths():
    card = render_card({"text": "{{ticket.title}}", "note": "{{ticket.missing}}"}, {"ticket": {"title": "Printer"}})
    assert card == {"text": "Printer", "note": ""}


def test_text_card_submit_action():
    card = text_card("hi", {"title": "Go", "actionName": "go"})
    assert card["actions"][0]["data"] == {"action": "go"}


# ------------------------------- recognizer -------------------------------- #

async def test_regex_recognizer_entities():
    recognizer = RegexRecognizer({
        "newTicket": {"pattern": r"\bnew ticket\b", "entities": {"title": r"ticket (?:for|about) (.+)"}},
    })
    intent = await recognizer.recognize(None, TurnState(), "new ticket for the broken printer")
    assert intent["name"] == "newTicket"
    assert intent["entities"]["title"] == "the broken printer"


# ----------------------------------- AI ------------------------------------ #

class FakeContext:
    def __init__(self):
        self.sent = []

    async def send_activity(self, text):
        self.sent.append(text)


async def test_ai_do_then_say():
    ctx = FakeContext()
    state = TurnState()
    model = MockModel(say=lambda _text: "Handled", do=[{"pattern": "new ticket", "name": "createTicket", "args": {"priority": "low"}}])
    ai = AI(model)

    async def create(_ctx, _state, args):
        state.conversation["created"] = args
        return "ticket stored"

    ai.action("createTicket", create)

    await ai.run(ctx, state, "new ticket please")
    assert ctx.sent == ["Handled"]
    assert state.conversation["created"] == {"priority": "low"}


async def test_ai_moderation_blocks():
    ctx = FakeContext()

    class Blocker:
        async def review_input(self, *_):
            return "moderation_blocked"

    async def blocked(c, _s, _reason):
        await c.send_activity("blocked!")

    ai = AI(MockModel(), moderator=Blocker(), on_blocked=blocked)
    await ai.run(ctx, TurnState(), "something bad")
    assert ctx.sent == ["blocked!"]


async def test_ai_history_round_trips():
    ctx = FakeContext()
    state = TurnState()
    ai = AI(MockModel(say=lambda text: f"You said: {text}"))
    await ai.run(ctx, state, "first")
    await ai.run(ctx, state, "second")
    assert ctx.sent == ["You said: first", "You said: second"]
    assert [m["text"] for m in state.conversation["history"]] == ["first", "You said: first", "second", "You said: second"]


# ---------------------------------- state ---------------------------------- #

async def test_state_round_trip():
    class FakeActivity:
        channel_id = "test"
        conversation = type("C", (), {"id": "c1"})()
        from_property = type("U", (), {"id": "u1"})()

    class FakeCtx:
        activity = FakeActivity()

    storage = MemoryStorage()
    state = await load_state(FakeCtx(), storage)
    state.conversation["tickets"] = [{"id": "1001"}]
    await save_state(FakeCtx(), storage, state)
    reloaded = await load_state(FakeCtx(), storage)
    assert reloaded.conversation["tickets"] == [{"id": "1001"}]
    assert reloaded.user == {}
