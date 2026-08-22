/**
 * AI — the orchestration loop: moderate input → plan with the model →
 * execute DO actions → SAY the reply. Mirrors the classic plan/moderate/act
 * model in a compact, provider-agnostic implementation.
 *
 * The loop:
 *  1. The user's input is appended to the conversation history.
 *  2. The model is prompted (system instructions list the available actions)
 *     and returns a plan: one or more SAY / DO commands.
 *  3. DO commands run their registered handlers; the observation is fed back
 *     and the model re-plans, until it emits a SAY or maxSteps is hit.
 *  4. The SAY text is sent to the user and recorded in history.
 */

import type { TurnContext } from "botbuilder";
import type { TurnState } from "./state";
import type { Model } from "./models";
import type { Moderator } from "./moderator";
import { parsePlan } from "./plan";

export type ActionHandler = (ctx: TurnContext, state: TurnState, args: Record<string, any>) => Promise<string>;

export type AIOptions = {
  model: Model;
  prompt?: string;
  moderator?: Moderator;
  maxSteps?: number;
  historyTurns?: number;
  onBlocked?: (ctx: TurnContext, state: TurnState, reason: string) => Promise<void>;
};

const DEFAULT_PROMPT = "You are a helpful assistant embedded in Microsoft Teams.";

export class AI {
  readonly model: Model;
  private actions = new Map<string, ActionHandler>();
  private prompt: string;
  private moderator: Moderator;
  private maxSteps: number;
  private historyTurns: number;
  private onBlocked?: AIOptions["onBlocked"];

  constructor(options: AIOptions) {
    this.model = options.model;
    this.prompt = options.prompt ?? DEFAULT_PROMPT;
    this.moderator = options.moderator ?? { reviewInput: async () => null };
    this.maxSteps = options.maxSteps ?? 4;
    this.historyTurns = options.historyTurns ?? 20;
    this.onBlocked = options.onBlocked;
  }

  action(name: string, handler: ActionHandler): this {
    this.actions.set(name, handler);
    return this;
  }

  private instructions(): string {
    const lines = [this.prompt, "", "Reply with a plan using EXACTLY one of these command forms:", "SAY <text to send to the user>", "DO <action> <json arguments>"];
    const names = [...this.actions.keys()];
    if (names.length > 0) {
      lines.push("", "Available actions:", ...names.map((name) => `- ${name}`));
      lines.push("", "Prefer DO when an action matches the user's request; otherwise SAY. After a DO completes you will see its result and may SAY a reply. Never invent actions.");
    }
    return lines.join("\n");
  }

  /** Run the full loop for one user input. Sends the SAY text (or fallbacks). */
  async run(ctx: TurnContext, state: TurnState, input: string): Promise<void> {
    const blocked = await this.moderator.reviewInput(ctx, state, input);
    if (blocked) {
      if (this.onBlocked) await this.onBlocked(ctx, state, blocked);
      else await ctx.sendActivity("I can't help with that request.");
      return;
    }

    state.conversation.history ??= [];
    state.conversation.history.push({ role: "user", text: input });
    state.temp.input = input;

    const observations: string[] = [];
    let steps = 0;
    let said = false;

    while (!said && steps <= this.maxSteps) {
      const transcript = (state.conversation.history ?? []).slice(-this.historyTurns).map((message) => ({ role: message.role, text: message.text }));
      for (const observation of observations) transcript.push({ role: "user", text: observation });

      const raw = await this.model.complete(this.instructions(), transcript);
      const commands = parsePlan(raw);

      for (const command of commands) {
        if (command.type === "SAY") {
          const text = command.text.trim();
          if (text) {
            await ctx.sendActivity(text);
            state.conversation.history!.push({ role: "assistant", text });
          }
          said = true;
        } else {
          steps += 1;
          const handler = this.actions.get(command.action);
          if (!handler) {
            observations.push(`ERROR: unknown action "${command.action}"`);
            continue;
          }
          const result = await handler(ctx, state, command.args ?? {});
          observations.push(`Observation [${command.action}]: ${String(result).slice(0, 500)}`);
        }
      }
      if (!said && commands.every((command) => command.type === "SAY" && !command.text.trim())) said = true;
    }

    if (!said) {
      await ctx.sendActivity("I wasn't able to finish that request — let's try again.");
    }
    // Keep history bounded.
    if ((state.conversation.history?.length ?? 0) > this.historyTurns * 2) {
      state.conversation.history = state.conversation.history!.slice(-this.historyTurns);
    }
  }
}
