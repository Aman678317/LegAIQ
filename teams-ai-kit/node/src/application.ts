/**
 * App — the router at the center of a bot. Wires a botbuilder adapter to:
 *
 *  - command handlers         app.message("/help", handler)
 *  - intents (recognizer)     app.intent("newTicket", handler)
 *  - adaptive card submits    app.cardAction("submitTicket", handler)
 *  - message extensions       app.messageExtension("searchDocs", handler)
 *  - link unfurling           app.unfurl(handler)
 *  - AI fallback              app.useAI(ai) — runs on unmatched messages
 *
 * and manages TurnState load/save around every turn.
 */

import { ActivityTypes, CloudAdapter, ConfigurationBotFrameworkAuthentication, TurnContext, type Activity } from "botbuilder";
import type { Request, Response } from "express";
import { AI } from "./ai";
import { adaptiveCard, renderCard } from "./cards";
import type { Recognizer } from "./recognizer";
import { MemoryStorage, loadState, saveState, type Storage, type TurnState } from "./state";

export type MessageHandler = (ctx: TurnContext, state: TurnState) => Promise<void>;
export type CardActionHandler = (ctx: TurnContext, state: TurnState, data: Record<string, any>) => Promise<string | object | void>;
export type MessageExtensionHandler = (ctx: TurnContext, state: TurnState, query: { commandId: string; parameters: Record<string, string> }) => Promise<{ title: string; subtitle: string; text: string; card?: object }[]>;
export type UnfurlHandler = (ctx: TurnContext, state: TurnState, url: string) => Promise<{ title: string; subtitle?: string; text: string; card?: object } | null>;

export type AppOptions = {
  adapter?: CloudAdapter;
  storage?: Storage;
  recognizer?: Recognizer;
};

export class App {
  /** The underlying botbuilder adapter, widened so the express-style
   *  process(req, res, logic) entry point is callable through strict types. */
  readonly adapter: CloudAdapter & { process(req: Request, res: any, logic: (ctx: TurnContext) => Promise<void>): Promise<void> };
  readonly storage: Storage;
  private recognizer?: Recognizer;
  private messageHandlers: { pattern: RegExp; handler: MessageHandler }[] = [];
  private intentHandlers = new Map<string, MessageHandler>();
  private cardHandlers = new Map<string, CardActionHandler>();
  private meHandlers = new Map<string, MessageExtensionHandler>();
  private unfurlHandler?: UnfurlHandler;
  private ai?: AI;
  private fallback?: MessageHandler;

  constructor(options: AppOptions = {}) {
    // Default adapter runs anonymously (no app id/password) so local testing
    // works out of the box; set BOT_ID / BOT_PASSWORD for a registered bot.
    const defaultAdapter = new CloudAdapter(new ConfigurationBotFrameworkAuthentication({
      MicrosoftAppId: process.env.BOT_ID ?? "",
      MicrosoftAppPassword: process.env.BOT_PASSWORD ?? "",
    }));
    this.adapter = (options.adapter ?? defaultAdapter) as App["adapter"];
    this.storage = options.storage ?? new MemoryStorage();
    this.recognizer = options.recognizer;
  }

  /** Register a command: a message that starts with the given text or matches a regex. */
  message(pattern: string | RegExp, handler: MessageHandler): this {
    const regex = typeof pattern === "string" ? new RegExp(`^\\s*${pattern.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(\\s|$)`, "i") : pattern;
    this.messageHandlers.push({ pattern: regex, handler });
    return this;
  }

  /** Register an intent handler, routed through the configured recognizer. */
  intent(name: string, handler: MessageHandler): this {
    this.intentHandlers.set(name, handler);
    return this;
  }

  /** Handle an Adaptive Card Action.Submit whose data contains {action: name}. */
  cardAction(name: string, handler: CardActionHandler): this {
    this.cardHandlers.set(name, handler);
    return this;
  }

  /** Handle a message-extension query for a command id. */
  messageExtension(commandId: string, handler: MessageExtensionHandler): this {
    this.meHandlers.set(commandId, handler);
    return this;
  }

  /** Handle link unfurling (composeExtension/queryLink). */
  unfurl(handler: UnfurlHandler): this {
    this.unfurlHandler = handler;
    return this;
  }

  /** Attach the AI system; unmatched messages run the AI loop. */
  useAI(ai: AI): this {
    this.ai = ai;
    return this;
  }

  /** Replace the default "unrecognized" behavior. */
  onFallback(handler: MessageHandler): this {
    this.fallback = handler;
    return this;
  }

  /** Express entry point: server.post("/api/messages", (req, res) => app.processActivity(req, res)). */
  async processActivity(req: Request, res: Response): Promise<void> {
    await this.adapter.process(req, res as any, (ctx) => this.turn(ctx));
  }

  /** Process one activity (used by tests; the adapter calls this internally too). */
  async turn(ctx: TurnContext): Promise<void> {
    const state = await loadState(ctx, this.storage);
    state.temp.locale = ctx.activity.locale;
    try {
      await this.route(ctx, state);
    } finally {
      await saveState(ctx, this.storage, state);
    }
  }

  private async route(ctx: TurnContext, state: TurnState): Promise<void> {
    const activity = ctx.activity;

    if (activity.type === ActivityTypes.Invoke && activity.name?.startsWith("composeExtension/")) {
      await this.routeMessageExtension(ctx, state);
      return;
    }

    if (activity.type !== ActivityTypes.Message) return;

    // 1. Adaptive card submits arrive as messages with a value payload.
    const actionName = activity.value?.action ?? activity.value?.actionId;
    if (typeof actionName === "string" && this.cardHandlers.has(actionName)) {
      const handler = this.cardHandlers.get(actionName)!;
      const outcome = await handler(ctx, state, activity.value ?? {});
      if (typeof outcome === "string" && outcome) await ctx.sendActivity(outcome);
      else if (outcome && typeof outcome === "object") await ctx.sendActivity({ attachments: [adaptiveCard(outcome)] });
      return;
    }

    const text = (activity.text ?? "").trim();
    if (!text) return;

    // 2. Explicit command handlers.
    for (const { pattern, handler } of this.messageHandlers) {
      if (pattern.test(text)) {
        await handler(ctx, state);
        return;
      }
    }

    // 3. Recognized intents.
    if (this.recognizer) {
      const intent = await this.recognizer.recognize(ctx, state, text);
      if (intent && this.intentHandlers.has(intent.name)) {
        state.temp.intent = intent;
        await this.intentHandlers.get(intent.name)!(ctx, state);
        return;
      }
    }

    // 4. AI fallback.
    if (this.ai) {
      await this.ai.run(ctx, state, text);
      return;
    }

    // 5. Nothing matched.
    if (this.fallback) await this.fallback(ctx, state);
    else await ctx.sendActivity("I didn't catch that. Try /help.");
  }

  private async routeMessageExtension(ctx: TurnContext, state: TurnState): Promise<void> {
    const activity = ctx.activity;
    const name = activity.name!;

    const respond = (body: object) =>
      ctx.sendActivity({ type: "invokeResponse" as ActivityTypes, value: { statusCode: 200, body } } as Partial<Activity>);

    try {
      if (name === "composeExtension/query") {
        const value = activity.value ?? {};
        const query = {
          commandId: value.commandId ?? "",
          parameters: Object.fromEntries((value.parameters ?? []).map((parameter: any) => [parameter.name, parameter.value])),
        };
        const handler = this.meHandlers.get(query.commandId);
        if (!handler) return void (await respond(errorBody(`Unknown command "${query.commandId}"`)));
        const results = await handler(ctx, state, query);
        await respond({
          composeExtension: {
            type: "result",
            attachmentLayout: "list",
            attachments: results.map((result) => ({
              contentType: "application/vnd.microsoft.card.thumbnail",
              content: result.card ?? { title: result.title, subtitle: result.subtitle, text: result.text },
              preview: { contentType: "application/vnd.microsoft.card.thumbnail", content: { title: result.title, text: result.subtitle || result.text } },
            })),
          },
        });
        return;
      }

      if (name === "composeExtension/queryLink") {
        const url: string = activity.value?.url ?? "";
        if (!this.unfurlHandler) return void (await respond(errorBody("No unfurl handler registered")));
        const result = await this.unfurlHandler(ctx, state, url);
        if (!result) return void (await respond({ composeExtension: { type: "result", attachmentLayout: "list", attachments: [] } }));
        await respond({
          composeExtension: {
            type: "result",
            attachmentLayout: "list",
            attachments: [{
              contentType: "application/vnd.microsoft.card.adaptive",
              content: result.card ?? renderCard(unfurlTemplate as any, { title: result.title, subtitle: result.subtitle ?? "", text: result.text, url }),
              preview: { contentType: "application/vnd.microsoft.card.thumbnail", content: { title: result.title, text: result.subtitle || result.text } },
            }],
          },
        });
        return;
      }

      await respond(errorBody(`Unsupported invoke "${name}"`));
    } catch (error) {
      await respond(errorBody(error instanceof Error ? error.message : "Message extension failed"));
    }
  }
}

function errorBody(message: string) {
  return { composeExtension: { type: "message", text: message } };
}

const unfurlTemplate = {
  type: "AdaptiveCard",
  $schema: "http://adaptivecards.io/schemas/adaptive-card.json",
  version: "1.4",
  body: [
    { type: "TextBlock", text: "{{title}}", weight: "Bolder", size: "Medium", wrap: true },
    { type: "TextBlock", text: "{{subtitle}}", isSubtle: true, wrap: true, spacing: "None" },
    { type: "TextBlock", text: "{{text}}", wrap: true },
    { type: "TextBlock", text: "{{url}}", size: "Small", isSubtle: true, wrap: true },
  ],
};
