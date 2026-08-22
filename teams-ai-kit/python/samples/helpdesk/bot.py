"""Sample 2 — helpdesk (Python): a real workflow bot.

Intent routing, AI action, adaptive-card forms + submits, conversation state,
message extension, and link unfurling — mirroring the Node helpdesk sample.

    pip install -e ".[dev]" && python -m samples.helpdesk.bot
    python -m samples.client --url http://localhost:3979/api/messages "new ticket for the printer"
"""

import os
import re

from teams_ai_kit import AI, App, MockModel, OpenAIModel, RegexRecognizer, adaptive_card, render_card, text_card
from samples.dev_server import run_dev_server

KB = [
    {"title": "How to reset your VPN", "subtitle": "IT knowledge base", "text": "Use the self-service portal → Reset VPN, then restart the client."},
    {"title": "Expense policy 2026", "subtitle": "Finance", "text": "Meals capped at $75/day; submit within 30 days of the trip."},
    {"title": "Booking meeting rooms", "subtitle": "Facilities", "text": "Rooms 4A-4F book via Outlook; external guests need front-desk notice."},
]

TICKET_FORM = {
    "type": "AdaptiveCard",
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.4",
    "body": [
        {"type": "TextBlock", "text": "New ticket", "weight": "Bolder", "size": "Medium"},
        {"type": "Input.Text", "id": "title", "label": "What is the problem?", "placeholder": "Printer on floor 3 is jamming"},
        {"type": "Input.ChoiceSet", "id": "priority", "label": "Priority", "style": "compact", "value": "low",
         "choices": [{"title": "Low", "value": "low"}, {"title": "High", "value": "high"}]},
    ],
    "actions": [{"type": "Action.Submit", "title": "Create ticket", "data": {"action": "submitTicket"}}],
}

app = App(recognizer=RegexRecognizer({
    "newTicket": {"pattern": r"\b(new|create|open|file)\s+(a\s+)?ticket\b",
                  "entities": {"title": r"ticket\s+(?:for|about)\s+(.+)"}},
    "ticketStatus": {"pattern": r"\b(ticket\s+)?status\b"},
    "helpIntent": {"pattern": r"^\s*(help|what can you do)"},
}))


async def create_and_confirm(ctx, state, title, priority):
    tickets = state.conversation.setdefault("tickets", [])
    ticket = {"id": str(1000 + len(tickets) + 1), "title": title, "priority": priority, "status": "open"}
    tickets.append(ticket)
    await ctx.send_activity({"attachments": [adaptive_card(text_card(
        f"Ticket #{ticket['id']} created — \"{title}\" ({priority}, open).",
        {"title": "Resolve", "actionName": "resolveTicket", "data": {"ticketId": ticket["id"]}},
    ))]})


@app.intent("helpIntent")
async def help_intent(ctx, state):
    await ctx.send_activity("I can: create tickets (\"new ticket for X\"), check status (\"status\"), search the knowledge base via the message extension, and unfurl ticket links.")


@app.intent("ticketStatus")
async def ticket_status(ctx, state):
    tickets = state.conversation.get("tickets", [])
    if not tickets:
        await ctx.send_activity("No tickets in this conversation yet. Say \"new ticket for …\" to create one.")
    else:
        await ctx.send_activity("\n".join(
            f"#{t['id']} [{t['priority']}] {t['title']} — {t['status']}" for t in tickets
        ))


@app.intent("newTicket")
async def new_ticket(ctx, state):
    intent = state.temp.get("intent") or {}
    title = (intent.get("entities") or {}).get("title")
    if title:
        await create_and_confirm(ctx, state, title, "low")
    else:
        await ctx.send_activity({"attachments": [adaptive_card(render_card(TICKET_FORM, {}))]})


@app.card_action("submitTicket")
async def submit_ticket(ctx, state, data):
    await create_and_confirm(ctx, state, str(data.get("title", "Untitled")), "high" if data.get("priority") == "high" else "low")
    return None  # confirmation already sent


@app.card_action("resolveTicket")
async def resolve_ticket(ctx, state, data):
    for ticket in state.conversation.get("tickets", []):
        if ticket["id"] == data.get("ticketId"):
            ticket["status"] = "resolved"
    return f"Ticket #{data.get('ticketId')} marked resolved. ✅"


@app.message_extension("searchKB")
async def search_kb(ctx, state, query):
    term = (query["parameters"].get("searchTerm") or "").lower()
    return [entry for entry in KB if not term or term in entry["title"].lower() or term in entry["text"].lower()]


@app.unfurl
async def unfurl(ctx, state, url):
    match = re.search(r"tickets?\.example\.com/(\d+)", url, re.IGNORECASE)
    if not match:
        return None
    ticket = next((t for t in state.conversation.get("tickets", []) if t["id"] == match.group(1)), None)
    if ticket:
        return {"title": f"Ticket #{ticket['id']} — {ticket['title']}", "subtitle": f"priority: {ticket['priority']}", "text": f"Status: {ticket['status']}"}
    return {"title": f"Ticket #{match.group(1)}", "subtitle": "helpdesk", "text": "No details found in this conversation."}


model = (
    OpenAIModel(model=os.getenv("OPENAI_MODEL"))
    if os.getenv("OPENAI_API_KEY")
    else MockModel(
        say=lambda text: "Here's what I know: " + "; ".join(entry["title"] for entry in KB) + '. Try "new ticket for …" or "status".',
        do=[{"pattern": r"\b(broken|doesn'?t work|issue|problem|failing)\b", "name": "createTicket", "args": {"priority": "low"}}],
    )
)

ai = AI(model, prompt="You are a corporate helpdesk assistant inside Teams. Create tickets for reported problems.")


@ai.action("createTicket")
async def create_ticket(ctx, state, args):
    title = str(args.get("title") or state.temp.get("input") or "Unspecified issue")
    await create_and_confirm(ctx, state, title, "high" if args.get("priority") == "high" else "low")
    return f"Ticket created for \"{title}\"."


app.use_ai(ai)

if __name__ == "__main__":
    run_dev_server(app, "helpdesk", model.__class__.__name__, int(os.getenv("PORT", "3979")))
