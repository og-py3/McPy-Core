"""
BridgeServer — WebSocket → MinecraftClient gateway.

Each incoming WebSocket connection gets its own MinecraftClient instance.
The session lives until the WebSocket closes or a 'disconnect' action is sent.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import uuid
from typing import Any

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    from websockets.exceptions import ConnectionClosed
    _HAS_WEBSOCKETS = True
except ImportError:
    _HAS_WEBSOCKETS = False
    WebSocketServerProtocol = Any  # type: ignore[misc]

from mcpycore.client.client import MinecraftClient
from mcpycore.client.connection import PlayerProfile, OfflineProfile
from mcpycore.events.emitter import Events
from mcpycore.humanize.humanizer import HumanizeConfig

log = logging.getLogger(__name__)


class BridgeSession:
    """One WebSocket ↔ MinecraftClient session."""

    def __init__(self, ws: Any) -> None:
        self._ws = ws
        self._client: MinecraftClient | None = None
        self._mc_task: asyncio.Task | None = None

    # ── Inbound (WebSocket → client) ──────────────────────────────────────

    async def handle(self) -> None:
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                    await self._dispatch(msg)
                except json.JSONDecodeError:
                    await self._send_error("Invalid JSON")
                except Exception as exc:
                    log.exception("Error handling message: %s", exc)
                    await self._send_error(str(exc))
        except ConnectionClosed:
            pass
        finally:
            await self._cleanup()

    async def _dispatch(self, msg: dict) -> None:
        action = msg.get("action", "")

        if action == "connect":
            await self._action_connect(msg)

        elif action == "disconnect":
            await self._cleanup()
            await self._push({"event": "disconnected", "reason": "Client requested"})

        elif action == "chat":
            if self._client:
                await self._client.send_chat(msg.get("message", ""))

        elif action == "move":
            if self._client:
                await self._client.move(
                    float(msg.get("x", 0)),
                    float(msg.get("y", 64)),
                    float(msg.get("z", 0)),
                    float(msg.get("yaw", 0)),
                    float(msg.get("pitch", 0)),
                )

        elif action == "look":
            if self._client:
                await self._client.look(
                    float(msg.get("yaw", 0)),
                    float(msg.get("pitch", 0)),
                )

        elif action == "swing_arm":
            if self._client:
                await self._client.swing_arm(int(msg.get("hand", 0)))

        elif action == "set_held_slot":
            if self._client:
                await self._client.set_held_slot(int(msg.get("slot", 0)))

        elif action == "respawn":
            if self._client:
                await self._client.respawn()

        else:
            await self._send_error(f"Unknown action: {action!r}")

    async def _action_connect(self, msg: dict) -> None:
        if self._client:
            await self._cleanup()

        host     = msg.get("host", "localhost")
        port     = int(msg.get("port", 25565))
        username = msg.get("username", "McPyCoreBot")
        protocol = int(msg.get("protocol", 775))
        token    = msg.get("access_token") or None

        # Humanize config
        humanize_raw = msg.get("humanize")
        if humanize_raw is True:
            humanize = HumanizeConfig()
        elif isinstance(humanize_raw, dict):
            humanize = HumanizeConfig(**{
                k: v for k, v in humanize_raw.items()
                if not k.startswith("_")
            })
        else:
            humanize = None

        self._client = MinecraftClient(
            host=host,
            port=port,
            username=username,
            access_token=token,
            protocol_version=protocol,
            humanize=humanize,
        )

        # Wire outbound events
        self._wire_events()

        # Start client in background
        self._mc_task = asyncio.create_task(
            self._run_client(),
            name=f"bridge-mc-{username}",
        )

    def _wire_events(self) -> None:
        """Subscribe to every client event and forward as WebSocket messages."""
        assert self._client is not None
        c = self._client

        @c.on(Events.CONNECT)
        async def on_connect(client: MinecraftClient) -> None:
            await self._push({
                "event": "connected",
                "version": client.version_name,
                "protocol": client.protocol_version,
            })

        @c.on(Events.DISCONNECT)
        async def on_disconnect(reason: str) -> None:
            await self._push({"event": "disconnected", "reason": reason})

        @c.on(Events.ERROR)
        async def on_error(exc: Exception) -> None:
            await self._push({"event": "error", "message": str(exc)})

        @c.on(Events.CHAT)
        async def on_chat(message: str, sender: uuid.UUID) -> None:
            await self._push({"event": "chat", "message": message, "sender": str(sender)})

        @c.on(Events.SYSTEM_CHAT)
        async def on_system_chat(content: str, overlay: bool) -> None:
            await self._push({"event": "system_chat", "content": content, "overlay": overlay})

        @c.on(Events.HEALTH)
        async def on_health(health: float, food: int, sat: float) -> None:
            await self._push({"event": "health", "health": health, "food": food, "saturation": sat})

        @c.on(Events.POSITION)
        async def on_position(x: float, y: float, z: float, yaw: float, pitch: float) -> None:
            await self._push({"event": "position", "x": x, "y": y, "z": z, "yaw": yaw, "pitch": pitch})

        @c.on(Events.SPAWN)
        async def on_spawn(x: float, y: float, z: float) -> None:
            await self._push({"event": "spawn", "x": x, "y": y, "z": z})

        @c.on(Events.LOGIN)
        async def on_login(eid: int, gm: int) -> None:
            await self._push({"event": "login", "entity_id": eid, "game_mode": gm})

        @c.on(Events.KEEPALIVE)
        async def on_keepalive(latency: float) -> None:
            await self._push({"event": "keepalive", "latency_ms": latency})

        @c.on(Events.DEATH)
        async def on_death(*_: Any) -> None:
            await self._push({"event": "death"})

        @c.on(Events.RESPAWN)
        async def on_respawn(data: bytes) -> None:
            await self._push({"event": "respawn", "data": base64.b64encode(data).decode()})

        @c.on(Events.BLOCK_UPDATE)
        async def on_block_update(x: int, y: int, z: int, state_id: int) -> None:
            await self._push({"event": "block_update", "x": x, "y": y, "z": z, "state_id": state_id})

        @c.on(Events.CHUNK_LOAD)
        async def on_chunk_load(cx: int, cz: int) -> None:
            await self._push({"event": "chunk_load", "cx": cx, "cz": cz})

        @c.on(Events.CHUNK_UNLOAD)
        async def on_chunk_unload(cx: int, cz: int) -> None:
            await self._push({"event": "chunk_unload", "cx": cx, "cz": cz})

        @c.on(Events.TITLE)
        async def on_title(text: str) -> None:
            await self._push({"event": "title", "text": text})

        @c.on(Events.ACTION_BAR)
        async def on_action_bar(text: str) -> None:
            await self._push({"event": "action_bar", "text": text})

        @c.on(Events.GAME_MODE)
        async def on_game_mode(gm: int) -> None:
            await self._push({"event": "game_mode", "game_mode": gm})

        @c.on(Events.TIME_UPDATE)
        async def on_time_update(world_age: int, tod: int) -> None:
            await self._push({"event": "time_update", "world_age": world_age, "time_of_day": tod})

        @c.on(Events.REMOVE_ENTITIES)
        async def on_remove_entities(ids: list) -> None:
            await self._push({"event": "remove_entities", "ids": ids})

        @c.on(Events.TRANSFER)
        async def on_transfer(host: str, port: int) -> None:
            await self._push({"event": "transfer", "host": host, "port": port})

    async def _run_client(self) -> None:
        assert self._client is not None
        try:
            await self._client.start()
        except Exception as exc:
            await self._push({"event": "error", "message": str(exc)})

    # ── Outbound (client → WebSocket) ─────────────────────────────────────

    async def _push(self, data: dict) -> None:
        try:
            await self._ws.send(json.dumps(data))
        except ConnectionClosed:
            pass
        except Exception as exc:
            log.debug("Failed to push event: %s", exc)

    async def _send_error(self, message: str) -> None:
        await self._push({"event": "error", "message": message})

    async def _cleanup(self) -> None:
        if self._client:
            try:
                await self._client.stop()
            except Exception:
                pass
            self._client = None
        if self._mc_task and not self._mc_task.done():
            self._mc_task.cancel()
            try:
                await self._mc_task
            except (asyncio.CancelledError, Exception):
                pass
            self._mc_task = None


# ── BridgeServer ──────────────────────────────────────────────────────────────

class BridgeServer:
    """
    WebSocket server that multiplexes multiple bot sessions.

    Each incoming connection is a separate bot instance.

    Usage::

        server = BridgeServer(host="0.0.0.0", port=25580)
        await server.serve()            # runs forever

        # Or as a context manager:
        async with BridgeServer(port=25580) as server:
            await server.wait_closed()
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 25580) -> None:
        if not _HAS_WEBSOCKETS:
            raise ImportError(
                "The 'websockets' package is required for the bridge. "
                "Install it with:  pip install websockets"
            )
        self.host = host
        self.port = port
        self._server = None

    async def _handler(self, ws: Any) -> None:
        session = BridgeSession(ws)
        log.info("New bridge session from %s", getattr(ws, "remote_address", "?"))
        await session.handle()
        log.info("Bridge session closed")

    async def serve(self) -> None:
        """Start the server and run forever."""
        import websockets
        log.info("McPy-Core bridge listening on ws://%s:%d", self.host, self.port)
        async with websockets.serve(self._handler, self.host, self.port) as server:
            self._server = server
            await server.wait_closed()

    async def __aenter__(self) -> "BridgeServer":
        import websockets
        self._server = await websockets.serve(self._handler, self.host, self.port)
        log.info("McPy-Core bridge listening on ws://%s:%d", self.host, self.port)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def wait_closed(self) -> None:
        if self._server:
            await self._server.wait_closed()
