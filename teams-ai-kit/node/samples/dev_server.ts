/**
 * Dev server for samples: exposes POST /api/messages (the bot endpoint) plus
 * a local loopback the Bot Framework connector uses to deliver the bot's
 * replies — so `samples/client.ts` (which sets serviceUrl to this origin)
 * can fetch them via GET /replies. No registration, emulator, or tunnel needed.
 */

import express from "express";
import type { App } from "../src";

export function startDevServer(app: App, port: number, name: string, model: string): void {
  const server = express();
  const replies: any[] = [];

  server.use(express.json());
  server.get("/health", (_req, res) => res.json({ ok: true, model }));
  server.post("/api/messages", (req, res) => app.processActivity(req, res));
  // Connector loopback: the adapter delivers replies here; we keep them for /replies.
  server.post(["/v3/conversations/:conversationId/activities", "/v3/conversations/:conversationId/activities/:activityId"], (req, res) => {
    replies.push(req.body);
    res.status(200).json({ id: String(replies.length) });
  });
  server.get("/replies", (_req, res) => res.json(replies.splice(0)));

  server.listen(port, () => {
    console.log(`${name} listening on http://localhost:${port}/api/messages (model: ${model})`);
    console.log(`local test: npx tsx samples/client.ts --url http://localhost:${port}/api/messages "hello"`);
  });
}
