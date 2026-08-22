"""Sample 1 — echobot (Python): a basic AI chat experience.

Runs offline with MockModel; set OPENAI_API_KEY to use real OpenAI.

    pip install -e ".[dev]" && python -m samples.echobot.bot
    python -m samples.client "hello"
"""

import os

from teams_ai_kit import AI, App, Localization, MockModel, OpenAIModerator, OpenAIModel
from samples.dev_server import run_dev_server

locales = (
    Localization()
    .add("en", {"welcome": "Hello! I'm EchoBot (Python). Ask me anything, or type /help.",
                "blocked": "That message was flagged by moderation and I won't respond to it."})
    .add("es", {"welcome": "¡Hola! Soy EchoBot (Python). Pregúntame lo que quieras o escribe /help.",
                "blocked": "Ese mensaje fue marcado por moderación y no responderé."})
)

model = (
    OpenAIModel(model=os.getenv("OPENAI_MODEL"))
    if os.getenv("OPENAI_API_KEY")
    else MockModel(say=lambda text: f"Echo: {text}")
)

app = App()


async def blocked(ctx, state):
    await ctx.send_activity(locales.t(state.temp.get("locale"), "blocked"))


ai = AI(
    model,
    prompt="You are EchoBot, a friendly assistant in Microsoft Teams. Be concise.",
    moderator=OpenAIModerator(),
    on_blocked=blocked,
)
app.use_ai(ai)


@app.message("/help")
async def help_command(ctx, state):
    await ctx.send_activity("Commands:\n/help — this message\n/hi — say hello\nanything else — AI reply (Mock echo offline, OpenAI when configured)")


@app.message("/hi")
async def hi(ctx, state):
    await ctx.send_activity(locales.t(state.temp.get("locale"), "welcome"))


@app.on_fallback
async def fallback(ctx, state):
    await ctx.send_activity(locales.t(state.temp.get("locale"), "welcome"))


if __name__ == "__main__":
    run_dev_server(app, "echobot", model.__class__.__name__, int(os.getenv("PORT", "3978")))
