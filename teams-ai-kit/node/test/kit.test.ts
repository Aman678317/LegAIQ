import { TestAdapter } from "botbuilder";
import { describe, expect, it } from "vitest";
import { AI, App, Localization, MockModel, RegexRecognizer, adaptiveCard, parsePlan, renderCard, textCard } from "../src";

function harness(options?: ConstructorParameters<typeof App>[0]) {
  const app = new App(options);
  const adapter = new TestAdapter(async (ctx) => app.turn(ctx));
  adapter.sendTrace = false;
  return { app, adapter };
}

/* ------------------------------- plan.ts -------------------------------- */

describe("parsePlan", () => {
  it("parses SAY with continuation lines", () => {
    const plan = parsePlan("SAY hello\nsecond line");
    expect(plan).toEqual([{ type: "SAY", text: "hello\nsecond line" }]);
  });

  it("parses DO with json args and bare DO", () => {
    expect(parsePlan('DO createTicket {"priority":"high"}')).toEqual([
      { type: "DO", action: "createTicket", args: { priority: "high" } },
    ]);
    expect(parsePlan("DO listAll")).toEqual([{ type: "DO", action: "listAll", args: {} }]);
  });

  it("parses multi-command plans in order", () => {
    const plan = parsePlan('DO a {}\nDO b {"x":1}\nSAY done');
    expect(plan.map((command) => command.type)).toEqual(["DO", "DO", "SAY"]);
  });

  it("falls back to treating plain text as SAY", () => {
    expect(parsePlan("just chatting")).toEqual([{ type: "SAY", text: "just chatting" }]);
  });

  it("rejects DO with invalid json args", () => {
    expect(() => parsePlan("DO x {oops}")).toThrow();
  });
});

/* ------------------------------ state / i18n ---------------------------- */

describe("Localization", () => {
  const locales = new Localization().add("en", { hi: "Hello {{name}}" }).add("es", { hi: "Hola {{name}}" });
  it("resolves regional variants to the dictionary and interpolates", () => {
    expect(locales.t("es-MX", "hi", { name: "Ana" })).toBe("Hola Ana");
    expect(locales.t("en-US", "hi", { name: "Bob" })).toBe("Hello Bob");
  });
  it("falls back to the default locale for unknown languages", () => {
    expect(locales.t("fr-FR", "hi", { name: "Zoe" })).toBe("Hello Zoe");
  });
});

/* -------------------------------- cards.ts ------------------------------ */

describe("renderCard", () => {
  it("binds dot paths and blanks missing values", () => {
    const card = renderCard({ text: "{{ticket.title}}", note: "{{ticket.missing}}" }, { ticket: { title: "Printer" } });
    expect(card).toEqual({ text: "Printer", note: "" });
  });
  it("binds nested objects and arrays", () => {
    const card = renderCard({ items: ["{{a}}", "{{b}}"] }, { a: 1, b: true });
    expect(card).toEqual({ items: ["1", "true"] });
  });
});

/* ------------------------------ recognizer ------------------------------ */

describe("RegexRecognizer", () => {
  const recognizer = new RegexRecognizer({
    newTicket: { pattern: /\bnew ticket\b/i, entities: { title: /ticket (?:for|about) (.+)/i } },
    status: { pattern: /status/i },
  });

  it("recognizes intents with captured entities", async () => {
    const { app, adapter } = harness({ recognizer });
    app.intent("newTicket", async (ctx, state) => {
      ctx.sendActivity(`intent=${state.temp.intent!.name} title=${state.temp.intent!.entities.title}`);
    });
    await adapter.send("new ticket for the broken printer").assertReply("intent=newTicket title=the broken printer").startTest();
  });

  it("returns null for unmatched text", async () => {
    const intent = await recognizer.recognize({ activity: {} } as any, { conversation: {}, user: {}, temp: {} } as any, "hello there");
    expect(intent).toBeNull();
  });
});

/* ---------------------------------- AI ---------------------------------- */

describe("AI loop", () => {
  it("runs DO then SAY, sending only the SAY text", async () => {
    const { app, adapter } = harness();
    const model = new MockModel({
      say: () => "Handled",
      do: [{ pattern: /new ticket/, name: "createTicket", args: { priority: "low" } }],
    });
    const ai = new AI({ model });
    ai.action("createTicket", async (_ctx, state, args) => {
      state.conversation.created = args;
      return "ticket stored";
    });
    app.useAI(ai);
    await adapter.send("new ticket please").assertReply("Handled").startTest();
  });

  it("blocks flagged input through the moderator", async () => {
    const { app, adapter } = harness();
    const ai = new AI({
      model: new MockModel(),
      moderator: { reviewInput: async () => "moderation_blocked" },
      onBlocked: async (ctx) => ctx.sendActivity("blocked!"),
    });
    app.useAI(ai);
    await adapter.send("something bad").assertReply("blocked!").startTest();
  });

  it("keeps conversation history across turns", async () => {
    const { app, adapter } = harness();
    app.useAI(new AI({ model: new MockModel({ say: (text) => `You said: ${text}` }) }));
    await adapter.send("first").assertReply("You said: first")
      .send("second").assertReply("You said: second").startTest();
  });
});

/* --------------------------------- App ---------------------------------- */

describe("App routing", () => {
  it("routes explicit commands before the AI fallback", async () => {
    const { app, adapter } = harness();
    app.message("/help", async (ctx) => ctx.sendActivity("help text"));
    app.useAI(new AI({ model: new MockModel() }));
    await adapter.send("/help").assertReply("help text")
      .send("anything").assertReply("You said: anything").startTest();
  });

  it("routes adaptive-card submits by action name", async () => {
    const { app, adapter } = harness();
    app.cardAction("submitTicket", async (_ctx, state, data) => {
      state.conversation.tickets = [{ id: "1001", ...(data as any) }];
      return `created ${data.title}`;
    });
    await adapter.send({ type: "message", text: "", value: { action: "submitTicket", title: "Printer jam" } })
      .assertReply("created Printer jam").startTest();
  });

  it("answers message-extension queries with an invokeResponse", async () => {
    const { app, adapter } = harness();
    app.messageExtension("searchKB", async () => [{ title: "VPN reset", subtitle: "IT", text: "Use the portal." }]);
    const reply = await runInvoke(adapter, app, baseInvoke("composeExtension/query", {
      commandId: "searchKB", parameters: [{ name: "searchTerm", value: "vpn" }],
    }));
    const attachments = reply.value.body.composeExtension.attachments;
    expect(reply.value.statusCode).toBe(200);
    expect(attachments[0].content.title).toBe("VPN reset");
  });

  it("unfurls known links and ignores others", async () => {
    const { app, adapter } = harness();
    app.unfurl(async () => null);
    const reply = await runInvoke(adapter, app, baseInvoke("composeExtension/queryLink", { url: "https://x.example.com/1" }));
    expect(reply.value.body.composeExtension.attachments).toEqual([]);
  });
});

function baseInvoke(name: string, value: any) {
  return {
    type: "invoke", name, value,
    channelId: "test", from: { id: "u" }, conversation: { id: "c" }, recipient: { id: "bot" },
    id: "1", timestamp: new Date().toISOString(),
  };
}

/** Drive one invoke activity through the app and capture the invokeResponse. */
async function runInvoke(adapter: TestAdapter, app: App, activity: any): Promise<any> {
  let reply: any;
  await (adapter as any).processActivity(activity, async (ctx: any) => {
    ctx.onSendActivities(async (_context: any, activities: any[], next: () => Promise<void>) => {
      reply = activities.find((sent: any) => sent.type === "invokeResponse");
      return next();
    });
    await app.turn(ctx);
  });
  return reply;
}
