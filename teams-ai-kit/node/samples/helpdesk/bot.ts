/**
 * Sample 2 — helpdesk: a real workflow bot.
 *
 * Shows intent routing, an AI action, adaptive-card forms with submits,
 * conversation state, a message extension, and link unfurling — the pieces a
 * production Teams app needs. Runs offline with MockModel; set
 * OPENAI_API_KEY to use real OpenAI.
 *
 *   npm install && npx tsx samples/helpdesk/bot.ts
 *   npx tsx samples/client.ts "new ticket for the printer"
 */

import {
  App, AI, MockModel, OpenAIModel, RegexRecognizer, textCard, adaptiveCard, renderCard,
} from "../../src";
import { startDevServer } from "../dev_server";

// --- in-memory "systems" the bot works on -------------------------------- //
type Ticket = { id: string; title: string; priority: "low" | "high"; status: string };
const KB = [
  { title: "How to reset your VPN", subtitle: "IT knowledge base", text: "Use the self-service portal → Reset VPN, then restart the client." },
  { title: "Expense policy 2026", subtitle: "Finance", text: "Meals capped at $75/day; submit within 30 days of the trip." },
  { title: "Booking meeting rooms", subtitle: "Facilities", text: "Rooms 4A-4F book via Outlook; external guests need front-desk notice." },
];

const ticketForm = {
  type: "AdaptiveCard",
  $schema: "http://adaptivecards.io/schemas/adaptive-card.json",
  version: "1.4",
  body: [
    { type: "TextBlock", text: "New ticket", weight: "Bolder", size: "Medium" },
    { type: "Input.Text", id: "title", label: "What is the problem?", placeholder: "Printer on floor 3 is jamming" },
    {
      type: "Input.ChoiceSet", id: "priority", label: "Priority", style: "compact", value: "low",
      choices: [
        { title: "Low", value: "low" },
        { title: "High", value: "high" },
      ],
    },
  ],
  actions: [{ type: "Action.Submit", title: "Create ticket", data: { action: "submitTicket" } }],
};

// --- app with intent routing --------------------------------------------- //
const app = new App({
  recognizer: new RegexRecognizer({
    newTicket: { pattern: /\b(new|create|open|file)\s+(a\s+)?ticket\b/i, entities: { title: /ticket\s+(?:for|about)\s+(.+)/i } },
    ticketStatus: { pattern: /\b(ticket\s+)?status\b/i },
    helpIntent: { pattern: /^\s*(help|what can you do)/i },
  }),
});

app.intent("helpIntent", async (ctx) => {
  await ctx.sendActivity("I can: create tickets (\"new ticket for X\"), check status (\"status\"), search the knowledge base via the message extension, and unfurl ticket links.");
});

app.intent("ticketStatus", async (ctx, state) => {
  const tickets: Ticket[] = state.conversation.tickets ?? [];
  await ctx.sendActivity(tickets.length === 0
    ? "No tickets in this conversation yet. Say \"new ticket for …\" to create one."
    : tickets.map((ticket) => `#${ticket.id} [${ticket.priority}] ${ticket.title} — ${ticket.status}`).join("\n"));
});

app.intent("newTicket", async (ctx, state) => {
  const title = state.temp.intent?.entities?.title as string | undefined;
  if (title) {
    // The AI path also lands here through the createTicket action.
    await createAndConfirm(ctx, state, title, "low");
  } else {
    // No title parsed → collect it with an adaptive card form.
    await ctx.sendActivity({ attachments: [adaptiveCard(renderCard(ticketForm, {}))] });
  }
});

async function createAndConfirm(ctx: any, state: any, title: string, priority: Ticket["priority"]) {
  const tickets: Ticket[] = state.conversation.tickets ?? [];
  const ticket: Ticket = { id: String(1000 + tickets.length + 1), title, priority, status: "open" };
  tickets.push(ticket);
  state.conversation.tickets = tickets;
  await ctx.sendActivity({ attachments: [adaptiveCard(textCard(
    `Ticket #${ticket.id} created — "${title}" (${priority}, ${ticket.status}).`,
    { title: "Resolve", actionName: "resolveTicket", data: { ticketId: ticket.id } },
  ))] });
}

// Adaptive card submit handlers ------------------------------------------- //
app.cardAction("submitTicket", async (ctx, state, data) => {
  await createAndConfirm(ctx, state, String(data.title ?? "Untitled"), data.priority === "high" ? "high" : "low");
  return; // createAndConfirm already sent the confirmation card
});

app.cardAction("resolveTicket", async (ctx, state, data) => {
  const tickets: Ticket[] = state.conversation.tickets ?? [];
  const ticket = tickets.find((entry) => entry.id === data.ticketId);
  if (ticket) ticket.status = "resolved";
  return `Ticket #${data.ticketId} marked resolved. ✅`;
});

// Message extension + link unfurling --------------------------------------- //
app.messageExtension("searchKB", async (_ctx, _state, query) => {
  const term = (query.parameters.searchTerm ?? Object.values(query.parameters)[0] ?? "").toLowerCase();
  return KB.filter((entry) => !term || entry.title.toLowerCase().includes(term) || entry.text.toLowerCase().includes(term));
});

app.unfurl(async (_ctx, state, url) => {
  const match = /tickets?\.example\.com\/(\d+)/i.exec(url);
  if (!match) return null;
  const ticket = (state.conversation.tickets ?? []).find((entry) => entry.id === match[1]);
  return ticket
    ? { title: `Ticket #${ticket.id} — ${ticket.title}`, subtitle: `priority: ${ticket.priority}`, text: `Status: ${ticket.status}` }
    : { title: `Ticket #${match[1]}`, subtitle: "helpdesk", text: "No details found in this conversation." };
});

// AI fallback with an action ----------------------------------------------- //
const model = process.env.OPENAI_API_KEY
  ? new OpenAIModel({ model: process.env.OPENAI_MODEL })
  : new MockModel({
      say: (text) => `Here's what I know: ${KB.map((entry) => entry.title).join("; ")}. Try "new ticket for …" or "status".`,
      do: [{ pattern: /\b(broken|doesn'?t work|issue|problem|failing)\b/i, name: "createTicket", args: { priority: "low" } }],
    });

const ai = new AI({ model, prompt: "You are a corporate helpdesk assistant inside Teams. Create tickets for reported problems." });
ai.action("createTicket", async (ctx, state, args) => {
  const title = String(args.title ?? state.temp.input ?? "Unspecified issue");
  await createAndConfirm(ctx, state, title, args.priority === "high" ? "high" : "low");
  return `Ticket created for "${title}".`;
});
app.useAI(ai);

// --- web server ------------------------------------------------------------ //
startDevServer(app, Number(process.env.PORT ?? 3979), "helpdesk", model.constructor.name);
