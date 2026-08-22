/**
 * Recognizers — turn raw user text into a named intent (+ entities) so the
 * app can route to a handler without an LLM round-trip. RegexRecognizer is
 * deterministic; the AI system itself is the "smart" recognizer.
 */

import type { TurnContext } from "botbuilder";
import type { TurnState } from "./state";

export type Intent = {
  name: string;
  entities: Record<string, string>;
  score: number;
};

export interface Recognizer {
  recognize(ctx: TurnContext, state: TurnState, text: string): Promise<Intent | null>;
}

export type IntentRule = {
  pattern: RegExp;
  entities?: Record<string, RegExp>; // first capture group becomes the entity value
};

export class RegexRecognizer implements Recognizer {
  private rules: Record<string, IntentRule>;

  constructor(rules: Record<string, IntentRule>) {
    this.rules = rules;
  }

  async recognize(_ctx: TurnContext, _state: TurnState, text: string): Promise<Intent | null> {
    for (const [name, rule] of Object.entries(this.rules)) {
      const match = rule.pattern.exec(text);
      if (!match) continue;
      const entities: Record<string, string> = {};
      for (const [entity, entityPattern] of Object.entries(rule.entities ?? {})) {
        const entityMatch = entityPattern.exec(text);
        if (entityMatch) entities[entity] = entityMatch[1] ?? entityMatch[0];
      }
      return { name, entities, score: match[0].length / Math.max(text.length, 1) };
    }
    return null;
  }
}
