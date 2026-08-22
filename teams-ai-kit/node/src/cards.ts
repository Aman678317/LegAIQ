/**
 * Adaptive Cards helpers — a small data binder plus attachment factories.
 *
 * `renderCard` substitutes `{{dot.path}}` placeholders anywhere in the
 * template with values from a data object (missing paths render as empty
 * strings). For full Adaptive Cards templating (`$schema`, `$data`, `$when`)
 * use the official adaptivecards-templating package — this binder is
 * intentionally tiny so the library has no card-engine dependency.
 */

type Json = string | number | boolean | null | Json[] | { [key: string]: Json };

const ADAPTIVE_CARD_TYPE = "application/vnd.microsoft.card.adaptive";

export function renderCard(template: Json, data: Record<string, any>): Json {
  if (typeof template === "string") {
    return template.replace(/\{\{\s*([\w.]+)\s*\}\}/g, (_match, path: string) => {
      const value = path.split(".").reduce<any>((acc, key) => (acc == null ? undefined : acc[key]), data);
      return value === undefined || value === null ? "" : String(value);
    });
  }
  if (Array.isArray(template)) return template.map((item) => renderCard(item, data));
  if (template && typeof template === "object") {
    const out: { [key: string]: Json } = {};
    for (const [key, value] of Object.entries(template)) out[key] = renderCard(value, data);
    return out;
  }
  return template;
}

export function adaptiveCard(content: object): { contentType: string; content: object } {
  return { contentType: ADAPTIVE_CARD_TYPE, content };
}

/** A minimal valid adaptive card with text + optional submit action. */
export function textCard(text: string, action?: { title: string; actionName: string; data?: Record<string, unknown> }): object {
  const card: Record<string, unknown> = {
    $schema: "http://adaptivecards.io/schemas/adaptive-card.json",
    type: "AdaptiveCard",
    version: "1.4",
    body: [{ type: "TextBlock", text, wrap: true }],
  };
  if (action) {
    card.actions = [{
      type: "Action.Submit",
      title: action.title,
      data: { action: action.actionName, ...action.data },
    }];
  }
  return card;
}

/** Thumbnail card attachment for message-extension result lists. */
export function resultCard(title: string, subtitle: string, text: string): object {
  return {
    contentType: "application/vnd.microsoft.card.thumbnail",
    content: { title, subtitle, text },
  };
}
