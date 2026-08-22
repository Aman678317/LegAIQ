"""Tiny Bot Framework REST client — the Python twin of node/samples/client.ts.

    python -m samples.client "hello"
    python -m samples.client --url http://localhost:3979/api/messages "status"
    python -m samples.client --invoke 'composeExtension/query' '{"commandId":"searchKB","parameters":[...]}'
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import urllib.request
from urllib.parse import urlsplit


async def main() -> None:
    args = sys.argv[1:]
    url = "http://localhost:3978/api/messages"
    if "--url" in args:
        index = args.index("--url")
        url = args[index + 1]
        del args[index:index + 2]

    invoke_body = None
    if "--invoke" in args:
        index = args.index("--invoke")
        invoke_body = (args[index + 1], json.loads(args[index + 2]))
        del args[index:index + 3]

    origin = urlsplit(url)._replace(path="", query="").geturl()
    base = {
        "channelId": "test",
        "serviceUrl": origin,
        "from": {"id": "user1", "name": "Test User"},
        "conversation": {"id": "conv1"},
        "recipient": {"id": "bot"},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "id": str(int(time.time() * 1000) % 10**10),
    }
    body = invoke_body and {"type": "invoke", "name": invoke_body[0], "value": invoke_body[1], **base} \
        or {"type": "message", "text": " ".join(args), **base}

    def post(target: str, payload: dict):
        request = urllib.request.Request(target, data=json.dumps(payload).encode(), headers={"content-type": "application/json"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode()

    raw = post(url, body)
    if raw.strip():
        payload = json.loads(raw)
        if isinstance(payload, dict) and payload.get("composeExtension"):
            attachments = payload["composeExtension"].get("attachments", [])
            print(f"[message extension: {len(attachments)} result(s)]")
            for attachment in attachments:
                preview = attachment.get("preview", {}).get("content", {})
                print("  •", json.dumps(preview.get("title", ""), ensure_ascii=False), preview.get("text", ""))

    await asyncio.sleep(0.6)
    try:
        with urllib.request.urlopen(f"{origin}/replies", timeout=10) as response:
            for activity in json.load(response):
                if activity.get("text"):
                    print(activity["text"])
                if activity.get("attachments"):
                    kinds = ",".join(a["contentType"].rsplit(".", 1)[-1] for a in activity["attachments"])
                    print(f"[{len(activity['attachments'])} attachment(s): {kinds}]")
    except Exception:
        pass


asyncio.run(main())
