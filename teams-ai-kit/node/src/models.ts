/**
 * Models — the chat-completion layer behind the AI system.
 *
 * All models implement one method: `complete(instructions, transcript) → text`.
 * The AI system asks models to answer with a plan (SAY / DO commands, see
 * plan.ts), which keeps behavior identical across OpenAI, Azure OpenAI, and
 * the offline MockModel used by tests and keyless sample runs.
 */

export interface ModelMessage {
  role: "system" | "user" | "assistant";
  text: string;
}

export interface Model {
  /** Returns the raw model output for a transcript. */
  complete(instructions: string, transcript: ModelMessage[]): Promise<string>;
}

export type OpenAIOptions = {
  model?: string;
  apiKey?: string;
  baseUrl?: string;
};

const DEFAULT_MODEL = "gpt-5.6-terra";

/** OpenAI (or any OpenAI-compatible endpoint) via the Responses API. */
export class OpenAIModel implements Model {
  private client: import("openai").OpenAI;
  private model: string;

  constructor(options: OpenAIOptions = {}) {
    // Lazy require so the openai package is only needed when actually used.
    const { OpenAI } = require("openai");
    const apiKey = options.apiKey ?? process.env.OPENAI_API_KEY;
    if (!apiKey) throw new Error("OpenAIModel needs an apiKey (or OPENAI_API_KEY in the environment).");
    this.client = new OpenAI({ apiKey, baseURL: options.baseUrl, timeout: 120_000 });
    this.model = options.model ?? process.env.OPENAI_MODEL ?? DEFAULT_MODEL;
  }

  async complete(instructions: string, transcript: ModelMessage[]): Promise<string> {
    const response = await this.client.responses.create({
      model: this.model,
      instructions,
      input: transcript.map((message) => ({ role: message.role, content: message.text })),
    });
    return response.output_text ?? "";
  }
}

export type AzureOpenAIOptions = {
  endpoint: string;
  apiKey?: string;
  apiVersion?: string;
  deployment?: string;
};

/** Azure OpenAI via the Responses API on a deployment. */
export class AzureOpenAIModel implements Model {
  private client: import("openai").AzureOpenAI;
  private deployment: string;

  constructor(options: AzureOpenAIOptions) {
    const { AzureOpenAI } = require("openai");
    const apiKey = options.apiKey ?? process.env.AZURE_OPENAI_API_KEY;
    if (!options.endpoint || !apiKey) {
      throw new Error("AzureOpenAIModel needs an endpoint and apiKey (or AZURE_OPENAI_API_KEY).");
    }
    this.client = new AzureOpenAI({
      endpoint: options.endpoint,
      apiKey,
      apiVersion: options.apiVersion ?? "2025-04-01-preview",
      timeout: 120_000,
    });
    this.deployment = options.deployment ?? process.env.AZURE_OPENAI_DEPLOYMENT ?? "gpt-5.6";
  }

  async complete(instructions: string, transcript: ModelMessage[]): Promise<string> {
    const response = await this.client.responses.create({
      model: this.deployment,
      instructions,
      input: transcript.map((message) => ({ role: message.role, content: message.text })),
    });
    return response.output_text ?? "";
  }
}

export type MockModelOptions = {
  /** Deterministic reply for SAY (default: echo). */
  say?: (lastUserText: string) => string;
  /** Keyword-triggered actions: when the pattern matches the last user text,
   *  the model emits `DO name {args}` instead of a reply. */
  do?: { pattern: RegExp; name: string; args?: Record<string, unknown> }[];
};

/**
 * MockModel — offline, deterministic, dependency-free. Used by tests and by
 * the sample bots when no API key is configured, so everything runs locally.
 */
export class MockModel implements Model {
  constructor(private options: MockModelOptions = {}) {}

  async complete(_instructions: string, transcript: ModelMessage[]): Promise<string> {
    const lastUser = [...transcript].reverse().find((message) => message.role === "user");
    const text = lastUser?.text ?? "";
    // After an action runs, the AI system feeds an "Observation ..." back as
    // the newest user message — reply (SAY) rather than re-triggering.
    const isObservation = text.startsWith("Observation");
    if (!isObservation) {
      for (const trigger of this.options.do ?? []) {
        if (trigger.pattern.test(text)) {
          return `DO ${trigger.name} ${JSON.stringify(trigger.args ?? {})}`;
        }
      }
    }
    const say = this.options.say ?? ((input: string) => `You said: ${input}`);
    return `SAY ${say(text)}`;
  }
}
