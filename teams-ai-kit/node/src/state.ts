/**
 * TurnState — scoped state for each turn, like the classic TurnState model:
 * `conversation` (shared per conversation), `user` (per user), `temp` (this turn).
 */

import type { TurnContext } from "botbuilder";

export type Scope = Record<string, any>;

export type TurnState = {
  conversation: Scope & { history?: { role: "user" | "assistant"; text: string }[] };
  user: Scope;
  temp: Scope & { locale?: string; input?: string; authTokens?: Scope };
};

export interface Storage {
  read(keys: string[]): Promise<Record<string, Scope>>;
  write(changes: Record<string, Scope>): Promise<void>;
  delete(keys: string[]): Promise<void>;
}

/** In-memory storage (default). Swap in any Storage implementation for persistence. */
export class MemoryStorage implements Storage {
  private memory = new Map<string, Scope>();

  async read(keys: string[]): Promise<Record<string, Scope>> {
    const result: Record<string, Scope> = {};
    for (const key of keys) {
      const value = this.memory.get(key);
      if (value) result[key] = JSON.parse(JSON.stringify(value));
    }
    return result;
  }

  async write(changes: Record<string, Scope>): Promise<void> {
    for (const [key, value] of Object.entries(changes)) {
      this.memory.set(key, JSON.parse(JSON.stringify(value)));
    }
  }

  async delete(keys: string[]): Promise<void> {
    for (const key of keys) this.memory.delete(key);
  }
}

function storageKeys(ctx: TurnContext): { conversation: string; user: string } {
  const channel = ctx.activity.channelId || "unknown";
  const conversation = ctx.activity.conversation?.id || `${channel}/no-conversation`;
  const user = ctx.activity.from?.id || "anonymous";
  return {
    conversation: `${channel}/${conversation}`,
    user: `${channel}/${user}`,
  };
}

/** Load the three scopes for this turn from storage. */
export async function loadState(ctx: TurnContext, storage: Storage): Promise<TurnState> {
  const keys = storageKeys(ctx);
  const stored = await storage.read([keys.conversation, keys.user]);
  return {
    conversation: stored[keys.conversation] ?? {},
    user: stored[keys.user] ?? {},
    temp: {},
  };
}

/** Persist the durable scopes (conversation + user; temp is per-turn only). */
export async function saveState(ctx: TurnContext, storage: Storage, state: TurnState): Promise<void> {
  const keys = storageKeys(ctx);
  const changes: Record<string, Scope> = {};
  if (Object.keys(state.conversation).length > 0) changes[keys.conversation] = state.conversation;
  if (Object.keys(state.user).length > 0) changes[keys.user] = state.user;
  await storage.write(changes);
}
