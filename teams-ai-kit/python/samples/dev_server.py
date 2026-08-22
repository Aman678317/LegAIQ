"""Shared dev server for the Python samples (aiohttp): bot endpoint + reply loopback."""

from __future__ import annotations

from typing import Any, List

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity

from teams_ai_kit.application import App


def run_dev_server(app: App, name: str, model: str, port: int) -> None:
    replies: List[Any] = []
    # Anonymous adapter (empty app id/password) — same local behavior as the Node kit.
    adapter = BotFrameworkAdapter(BotFrameworkAdapterSettings(app_id="", app_password=""))

    async def messages(request: Request) -> Response:
        activity = Activity().deserialize(await request.json())

        async def logic(ctx: TurnContext) -> None:
            await app.on_turn(ctx)

        await adapter.process_activity(activity, "", logic)  # empty auth header = anonymous
        return Response(status=200)

    async def loopback(request: Request) -> Response:
        replies.append(await request.json())
        return web.json_response({"id": str(len(replies))})

    async def get_replies(request: Request) -> Response:
        out, replies[:] = replies[:], []
        return web.json_response(out)

    async def health(request: Request) -> Response:
        return web.json_response({"ok": True, "model": model})

    server = web.Application()
    server.router.add_post("/api/messages", messages)
    server.router.add_post("/v3/conversations/{conversation_id}/activities", loopback)
    server.router.add_post("/v3/conversations/{conversation_id}/activities/{activity_id}", loopback)
    server.router.add_get("/replies", get_replies)
    server.router.add_get("/health", health)

    print(f"{name} listening on http://localhost:{port}/api/messages (model: {model})")
    web.run_app(server, host="0.0.0.0", port=port, print=None)
