/**
 * Tiny Bot Framework REST client for poking at a running sample locally
 * (both the Node and Python samples expose POST /api/messages anonymously):
 *
 *   npx tsx samples/client.ts "hello"
 *   npx tsx samples/client.ts --url http://localhost:3979/api/messages "status"
 *   npx tsx samples/client.ts --invoke 'composeExtension/query' '{"commandId":"searchKB","parameters":[{"name":"searchTerm","value":"vpn"}]}'
 *
 * Replies are delivered by the adapter to serviceUrl (the same origin); the
 * client polls GET /replies there to print them.
 */

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const urlIndex = args.indexOf("--url");
  const url = urlIndex >= 0 ? args[urlIndex + 1] : "http://localhost:3978/api/messages";
  if (urlIndex >= 0) args.splice(urlIndex, 2);
  const invokeIndex = args.indexOf("--invoke");

  const base = {
    channelId: "test",
    serviceUrl: new URL(url).origin, // where the adapter sends replies back
    from: { id: "user1", name: "Test User" },
    conversation: { id: "conv1" },
    recipient: { id: "bot" },
    timestamp: new Date().toISOString(),
    id: String(Math.random()).slice(2),
  };

  const body = invokeIndex >= 0
    ? { ...base, type: "invoke", name: args[invokeIndex + 1], value: JSON.parse(args[invokeIndex + 2] ?? "{}") }
    : { ...base, type: "message", text: args.join(" ") };

  const response = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    console.error(`HTTP ${response.status}`);
    process.exit(1);
  }
  // Message activities return an empty body (replies arrive via the loopback).
  const raw = await response.text();
  const direct: any[] = raw.trim() ? (Array.isArray(JSON.parse(raw)) ? JSON.parse(raw) : [JSON.parse(raw)]) : [];

  // Poll the loopback for connector-delivered replies, then print everything.
  let activities: any[] = direct.filter((activity) => activity && (activity.text || activity.type === "invokeResponse"));
  await new Promise((resolve) => setTimeout(resolve, 600));
  try {
    const delivered = await fetch(new URL("/replies", url));
    if (delivered.ok) activities = activities.concat(await delivered.json());
  } catch {
    /* no loopback (e.g. remote bot) — direct replies only */
  }
  for (const activity of activities) {
    if (activity.text) console.log(activity.text);
    if (activity.type === "invokeResponse") console.log(JSON.stringify(activity.value, null, 2));
    if (activity.attachments?.length) console.log(`[${activity.attachments.length} attachment(s): ${activity.attachments.map((a: any) => a.contentType.split(".").pop()).join(", ")}]`);
  }
  // Invoke results arrive as the raw POST body ({ composeExtension: ... }).
  for (const direct_activity of direct) {
    if (direct_activity?.composeExtension) {
      const attachments = direct_activity.composeExtension.attachments ?? [];
      if (direct_activity.composeExtension.type === "message") console.log(direct_activity.composeExtension.text);
      else console.log(`[message extension: ${attachments.length} result(s)]`);
      for (const attachment of attachments) console.log("  •", JSON.stringify(attachment.preview?.content ?? attachment.content?.title ?? ""));
    }
  }
}

main();
