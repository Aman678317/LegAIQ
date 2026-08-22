/**
 * Sample 1 — echobot: a basic AI chat experience.
 *
 * Runs with NO configuration (offline MockModel that echoes smartly), and
 * automatically upgrades to real OpenAI when OPENAI_API_KEY is set.
 *
 *   npm install && npx tsx samples/echobot/bot.ts
 *   curl -s localhost:3978/health
 *   npx tsx samples/client.ts "hello there"
 */

import express from "express";
import { App, AI, MockModel, OpenAIModel, Localization, OpenAIModerator } from "../../src";
import { startDevServer } from "../dev_server";

// --- localization ------------------------------------------------------- //
const locales = new Localization().add("en", {
  welcome: "Hello! I'm EchoBot. Ask me anything, or type /help.",
  blocked: "That message was flagged by moderation and I won't respond to it.",
}).add("es", {
  welcome: "¡Hola! Soy EchoBot. Pregúntame lo que quieras o escribe /help.",
  blocked: "Ese mensaje fue marcado por moderación y no responderé.",
});

// --- model: real when configured, mock otherwise ------------------------ //
const model = process.env.OPENAI_API_KEY
  ? new OpenAIModel({ model: process.env.OPENAI_MODEL })
  : new MockModel({
      say: (text) => `Echo: ${text}`,
    });

// --- the app ------------------------------------------------------------- //
const app = new App();

const ai = new AI({
  model,
  prompt: "You are EchoBot, a friendly assistant in Microsoft Teams. Be concise.",
  moderator: new OpenAIModerator(), // active only when a key is configured
  onBlocked: async (ctx, state) => {
    await ctx.sendActivity(locales.t(state.temp.locale, "blocked"));
  },
});
app.useAI(ai);

app.message("/help", async (ctx, state) => {
  await ctx.sendActivity("Commands:\n/help — this message\n/hi — say hello\nanything else — AI reply (Mock echo offline, OpenAI when configured)");
});

app.message("/hi", async (ctx, state) => {
  await ctx.sendActivity(locales.t(state.temp.locale, "welcome"));
});

// First contact: greet with a card (Teams conversationUpdate).
app.onFallback(async (ctx) => {
  await ctx.sendActivity(locales.t(ctx.activity.locale, "welcome"));
});

// --- web server ----------------------------------------------------------- //
startDevServer(app, Number(process.env.PORT ?? 3978), "echobot", model.constructor.name);
