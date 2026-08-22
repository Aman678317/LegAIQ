/**
 * Moderation — a safety gate in front of (and behind) the model.
 * The default moderator allows everything; OpenAIModerator flags input using
 * OpenAI's moderation endpoint and blocks the turn with a localized message.
 */

import type { TurnContext } from "botbuilder";
import type { TurnState } from "./state";

export interface Moderator {
  /** Return null to allow the turn, or a block-reason token to reject it. */
  reviewInput(ctx: TurnContext, state: TurnState, text: string): Promise<string | null>;
}

export class NoopModerator implements Moderator {
  async reviewInput(): Promise<string | null> {
    return null;
  }
}

export class OpenAIModerator implements Moderator {
  private client: import("openai").OpenAI | null = null;

  constructor(private model: string = "omni-moderation-latest") {}

  async reviewInput(_ctx: TurnContext, _state: TurnState, text: string): Promise<string | null> {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey || !text.trim()) return null; // degrade open when unconfigured
    try {
      if (!this.client) {
        const { OpenAI } = require("openai");
        this.client = new OpenAI({ apiKey });
      }
      const result = await this.client!.moderations.create({ model: this.model, input: text });
      const first = result && Array.isArray(result.results) ? result.results[0] : null;
      return first && first.flagged ? "moderation_blocked" : null;
    } catch {
      return null; // moderation is best-effort; never take the bot down
    }
  }
}
