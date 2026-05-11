"""
MinecraftClient — the high-level async entry point for McPy-Core.

Usage::

    import asyncio
    from mcpycore import MinecraftClient
    from mcpycore.events.emitter import Events

    async def main():
        client = MinecraftClient("play.example.com", username="BotName")

        @client.event
        async def on_chat(message, sender):
            print(f"[{sender}] {message}")
            await client.send_chat(f"Echo: {message}")

        await client.start()

    asyncio.run(main())
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Coroutine

from mcpycore.client.connection import Connection, PlayerProfile, OfflineProfile, LoginError
from mcpycore.client.reconnect import ReconnectPolicy, NoReconnect
from mcpycore.debug.inspector import PacketInspector
from mcpycore.events.emitter import AsyncEventEmitter, Events
from mcpycore.extensions.loader import ExtensionLoader
from mcpycore.network.stream import StreamError, StreamClosedError
from mcpycore.protocol.registry.registry import PacketRegistry, Direction, global_registry
from mcpycore.protocol.serializers.buffer import PacketBuffer
from mcpycore.protocol.states.machine import State
from mcpycore.protocol.versions.base import version_name, PROTOCOL_LATEST
from mcpycore.utils.logging import get_logger
from mcpycore.utils.metrics import MetricsCollector

log = get_logger(__name__)


class MinecraftClient:
    """
    High-level async Minecraft client.

    Parameters
    ----------
    host:
        Server hostname or IP address.
    port:
        Server port (default 25565).
    username:
        Player username.
    access_token:
        Microsoft access token for online-mode auth (None = offline mode).
    protocol_version:
        Protocol version integer (default: 775 = 1.21.11).
    reconnect_policy:
        A ReconnectPolicy instance. Defaults to NoReconnect.
    debug:
        Enable verbose packet debug logging.
    timeout:
        Socket timeout in seconds.

    Events fired::

        connect          — when connection established and play state entered
        disconnect       — when connection is lost; args: (reason: str)
        reconnect        — before each reconnect attempt
        error            — on unhandled handler exceptions
        packet           — for every received packet; args: (packet_id, buf)
        chat             — player chat; args: (message, sender_uuid)
        system_chat      — system messages; args: (content, overlay)
        health           — health update; args: (health, food, saturation)
        position         — position sync; args: (x, y, z, yaw, pitch)
        spawn            — first position received (login complete)
        login            — play login packet received; args: (entity_id, game_mode)
        respawn          — dimension change / respawn; args: packet
        keepalive        — keep-alive round-trip; args: (latency_ms,)
        chunk_load       — chunk data received; args: (cx, cz)
        chunk_unload     — chunk unloaded; args: (cx, cz)
        block_update     — single block changed; args: (x, y, z, state_id)
        spawn_entity     — entity spawned; args: packet
        entity_move      — entity moved; args: packet
        remove_entities  — entities despawned; args: (ids,)
        title            — title text; args: (text,)
        boss_bar         — boss bar update; args: packet
        player_list      — tab list update; args: packet
        death            — player died; args: packet
        transfer         — server transfer (1.21+); args: (host, port)
    """

    def __init__(
        self,
        host: str,
        port: int = 25565,
        username: str = "McPyCoreBot",
        access_token: str | None = None,
        protocol_version: int = PROTOCOL_LATEST,
        reconnect_policy: ReconnectPolicy | None = None,
        debug: bool = False,
        timeout: float = 30.0,
    ) -> None:
        self.host = host
        self.port = port
        self.protocol_version = protocol_version
        self.debug = debug

        self.profile = PlayerProfile(
            username=username,
            access_token=access_token,
        )
        self._reconnect_policy = reconnect_policy or NoReconnect()
        self._timeout = timeout

        self._conn: Connection | None = None
        self.events = AsyncEventEmitter()
        self.inspector = PacketInspector(enabled=debug)
        self.extensions = ExtensionLoader(self)
        self.metrics = MetricsCollector()

        # Player state
        self.x: float = 0.0
        self.y: float = 0.0
        self.z: float = 0.0
        self.yaw: float = 0.0
        self.pitch: float = 0.0
        self.health: float = 20.0
        self.food: int = 20
        self.food_saturation: float = 5.0
        self.game_mode: int = 0
        self.entity_id: int = 0
        self.on_ground: bool = True

        self._running = False
        self._spawned = False
        self._sequence = 0

        # Packet dispatch table: packet_id → handler
        self._handlers: dict[int, Callable[[PacketBuffer], Coroutine]] = {}
        self._build_handlers()

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def version_name(self) -> str:
        return version_name(self.protocol_version)

    @property
    def position(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z

    @property
    def is_creative(self) -> bool:
        return self.game_mode == 1

    @property
    def is_connected(self) -> bool:
        return self._conn is not None and self._conn.is_connected

    # ── Event decorator ───────────────────────────────────────────────────

    def event(self, coro: Callable) -> Callable:
        """
        Decorator to register an event handler by function name convention.

        Function name must be ``on_<event_name>``::

            @client.event
            async def on_chat(message, sender):
                ...
        """
        name = coro.__name__
        if name.startswith("on_"):
            event_name = name[3:]
            self.events.on(event_name, coro)
        else:
            raise ValueError(
                f"Event handler name must start with 'on_', got {name!r}"
            )
        return coro

    def on(self, event: str, handler: Callable | None = None):
        """
        Register an event listener (decorator or direct call).

        Use constants from ``mcpycore.events.emitter.Events`` to avoid typos.
        """
        return self.events.on(event, handler)

    def once(self, event: str, handler: Callable | None = None):
        """Register a one-shot listener."""
        return self.events.once(event, handler)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """
        Connect and run the packet loop, with automatic reconnection.

        Blocks until permanently disconnected or stopped.
        """
        attempt = 0
        while True:
            try:
                await self._connect_once()
                attempt = 0
                self._reconnect_policy.on_success()
            except (StreamError, ConnectionError, LoginError) as exc:
                log.error("Connection error: %s", exc)
                await self.events.emit(Events.ERROR, exc)
            except Exception as exc:
                log.exception("Unexpected error: %s", exc)
                await self.events.emit(Events.ERROR, exc)
            finally:
                if self._conn:
                    await self._conn.disconnect()
                    self._conn = None

            if not self._running:
                break

            await self.events.emit(Events.RECONNECT, attempt)
            should_retry = await self._reconnect_policy.wait(attempt)
            if not should_retry:
                break
            attempt += 1

    async def stop(self) -> None:
        """Gracefully stop the client."""
        self._running = False
        if self._conn:
            await self._conn.disconnect()

    async def _connect_once(self) -> None:
        """One full connect → play → disconnect cycle."""
        self._conn = Connection(
            host=self.host,
            port=self.port,
            profile=self.profile,
            protocol_version=self.protocol_version,
            timeout=self._timeout,
        )
        await self._conn.connect()
        self._running = True
        self._spawned = False
        self._build_handlers()   # rebuild for any version changes
        await self.events.emit(Events.CONNECT, self)
        await self._packet_loop()

    # ── Packet loop ───────────────────────────────────────────────────────

    async def _packet_loop(self) -> None:
        assert self._conn is not None
        while self._running and self._conn.is_connected:
            try:
                packet_id, buf = await self._conn.read_packet()
            except StreamClosedError:
                await self.events.emit(Events.DISCONNECT, "Connection closed")
                break
            except StreamError as exc:
                await self.events.emit(Events.DISCONNECT, str(exc))
                break

            self.metrics.count_packet_in(packet_id)
            self.inspector.log_recv(packet_id, buf)
            await self.events.emit(Events.PACKET, packet_id, buf)

            handler = self._handlers.get(packet_id)
            if handler:
                try:
                    await handler(buf)
                except Exception as exc:
                    log.exception("Handler error for packet 0x%02X: %s", packet_id, exc)
                    await self.events.emit(Events.ERROR, exc)

    # ── Packet handler registration ───────────────────────────────────────

    def _cb(self, name: str) -> int | None:
        """Get clientbound packet ID for current protocol version."""
        from mcpycore.protocol.versions.v1_21.packets import CB_IDS
        table = CB_IDS.get(self.protocol_version, CB_IDS.get(775, {}))
        return table.get(name)

    def _sb(self, name: str) -> int | None:
        """Get serverbound packet ID for current protocol version."""
        from mcpycore.protocol.versions.v1_21.packets import SB_IDS
        table = SB_IDS.get(self.protocol_version, SB_IDS.get(775, {}))
        return table.get(name)

    def _build_handlers(self) -> None:
        mapping = {
            "keep_alive":                  self._on_keep_alive,
            "player_position_and_look":    self._on_position,
            "set_health":                  self._on_health,
            "disconnect":                  self._on_disconnect,
            "login":                       self._on_login,
            "respawn":                     self._on_respawn,
            "game_event":                  self._on_game_event,
            "system_chat_message":         self._on_system_chat,
            "chat_message":                self._on_chat,
            "time_update":                 self._on_time_update,
            "spawn_entity":                self._on_spawn_entity,
            "entity_position":             self._on_entity_position,
            "entity_position_and_rotation": self._on_entity_pos_rot,
            "entity_rotation":             self._on_entity_rotation,
            "remove_entities":             self._on_remove_entities,
            "block_update":                self._on_block_update,
            "chunk_data":                  self._on_chunk_data,
            "unload_chunk":                self._on_unload_chunk,
            "boss_bar":                    self._on_boss_bar,
            "set_title_text":              self._on_title,
            "set_subtitle_text":           self._on_subtitle,
            "set_action_bar_text":         self._on_action_bar,
            "player_info_update":          self._on_player_list,
            "set_container_content":       self._on_inventory,
            "set_container_slot":          self._on_slot_update,
            "combat_death":                self._on_death,
            "hurt_animation":              self._on_hurt,
            "transfer":                    self._on_transfer,
            "chunk_batch_finished":        self._on_chunk_batch_finished,
        }
        self._handlers = {}
        for name, handler in mapping.items():
            pid = self._cb(name)
            if pid is not None:
                self._handlers[pid] = handler

    # ── Send helpers ──────────────────────────────────────────────────────

    async def _send(self, name: str, payload: bytes) -> None:
        pid = self._sb(name)
        if pid is None:
            log.warning("No serverbound ID for %r at protocol %d", name, self.protocol_version)
            return
        assert self._conn is not None
        self.inspector.log_send(pid, payload)
        self.metrics.count_packet_out(pid)
        await self._conn.write_packet(pid, payload)

    # ── Player actions ────────────────────────────────────────────────────

    async def send_chat(self, message: str) -> None:
        """Send a chat message or slash command."""
        import time as _time
        if message.startswith("/"):
            buf = PacketBuffer()
            buf.write_string(message[1:])
            buf.write_long(int(_time.time() * 1000))
            buf.write_long(0)       # salt
            buf.write_varint(0)     # no argument signatures
            buf.write_bool(False)   # signed preview
            await self._send("chat_command", buf.flush())
        else:
            buf = PacketBuffer()
            buf.write_string(message)
            buf.write_long(int(_time.time() * 1000))
            buf.write_long(0)
            buf.write_bool(False)
            buf.write_varint(0)
            await self._send("chat_message", buf.flush())

    async def move(self, x: float, y: float, z: float,
                   yaw: float = 0.0, pitch: float = 0.0) -> None:
        """Send a position + rotation update."""
        self.x, self.y, self.z = x, y, z
        self.yaw, self.pitch = yaw, pitch
        buf = PacketBuffer()
        buf.write_double(x)
        buf.write_double(y)
        buf.write_double(z)
        buf.write_float(yaw)
        buf.write_float(pitch)
        buf.write_bool(self.on_ground)
        await self._send("move_player_pos_rot", buf.flush())

    async def look(self, yaw: float, pitch: float) -> None:
        """Change look direction without moving."""
        self.yaw, self.pitch = yaw, pitch
        buf = PacketBuffer()
        buf.write_float(yaw)
        buf.write_float(pitch)
        buf.write_bool(self.on_ground)
        await self._send("move_player_rot", buf.flush())

    async def swing_arm(self, hand: int = 0) -> None:
        buf = PacketBuffer()
        buf.write_varint(hand)
        await self._send("swing_arm", buf.flush())

    async def attack(self, entity_id: int) -> None:
        buf = PacketBuffer()
        buf.write_varint(entity_id)
        buf.write_varint(1)       # attack
        buf.write_bool(False)     # sneaking
        await self._send("interact_entity", buf.flush())

    async def use_item(self, hand: int = 0) -> None:
        self._sequence += 1
        buf = PacketBuffer()
        buf.write_varint(hand)
        buf.write_varint(self._sequence)
        await self._send("use_item", buf.flush())

    async def sneak(self, sneaking: bool = True) -> None:
        buf = PacketBuffer()
        buf.write_varint(self.entity_id)
        buf.write_varint(0 if sneaking else 1)
        buf.write_varint(0)
        await self._send("player_command", buf.flush())

    async def sprint(self, sprinting: bool = True) -> None:
        buf = PacketBuffer()
        buf.write_varint(self.entity_id)
        buf.write_varint(3 if sprinting else 4)
        buf.write_varint(0)
        await self._send("player_command", buf.flush())

    async def respawn(self) -> None:
        buf = PacketBuffer()
        buf.write_varint(0)   # action: perform respawn
        await self._send("client_status", buf.flush())

    async def set_held_slot(self, slot: int) -> None:
        if not 0 <= slot <= 8:
            raise ValueError(f"Slot must be 0–8, got {slot}")
        buf = PacketBuffer()
        buf.write_short(slot)
        await self._send("set_held_item", buf.flush())

    # ── Packet handlers ───────────────────────────────────────────────────

    async def _on_keep_alive(self, buf: PacketBuffer) -> None:
        t0 = time.monotonic()
        ka_id = buf.read_long()
        resp = PacketBuffer()
        resp.write_long(ka_id)
        await self._send("keep_alive", resp.flush())
        latency = (time.monotonic() - t0) * 1000
        self.metrics.record_latency(latency)
        await self.events.emit(Events.KEEPALIVE, latency)

    async def _on_position(self, buf: PacketBuffer) -> None:
        x = buf.read_double()
        y = buf.read_double()
        z = buf.read_double()
        yaw = buf.read_float()
        pitch = buf.read_float()
        flags = buf.read_byte()
        teleport_id = buf.read_varint()

        self.x = self.x + x if flags & 0x01 else x
        self.y = self.y + y if flags & 0x02 else y
        self.z = self.z + z if flags & 0x04 else z
        self.yaw   = self.yaw   + yaw   if flags & 0x08 else yaw
        self.pitch = self.pitch + pitch if flags & 0x10 else pitch

        # Confirm teleport
        resp = PacketBuffer()
        resp.write_varint(teleport_id)
        await self._send("confirm_teleportation", resp.flush())

        await self.events.emit(Events.POSITION, self.x, self.y, self.z, self.yaw, self.pitch)

        if not self._spawned:
            self._spawned = True
            await self.events.emit(Events.SPAWN, self.x, self.y, self.z)

    async def _on_health(self, buf: PacketBuffer) -> None:
        self.health = buf.read_float()
        self.food = buf.read_varint()
        self.food_saturation = buf.read_float()
        await self.events.emit(Events.HEALTH, self.health, self.food, self.food_saturation)
        if self.health <= 0:
            await self.events.emit(Events.DEATH)

    async def _on_system_chat(self, buf: PacketBuffer) -> None:
        content = buf.read_string()
        overlay = buf.read_bool()
        await self.events.emit(Events.SYSTEM_CHAT, content, overlay)

    async def _on_chat(self, buf: PacketBuffer) -> None:
        sender = buf.read_uuid()
        buf.read_varint()   # index
        has_sig = buf.read_bool()
        if has_sig:
            buf.read_bytes(256)
        message = buf.read_string()
        await self.events.emit(Events.CHAT, message, sender)

    async def _on_disconnect(self, buf: PacketBuffer) -> None:
        reason = buf.read_string()
        self._running = False
        await self.events.emit(Events.DISCONNECT, reason)

    async def _on_login(self, buf: PacketBuffer) -> None:
        self.entity_id = buf.read_int()
        _hardcore = buf.read_bool()
        self.game_mode = buf.read_ubyte()
        buf.remaining()   # drain rest (dimension codec etc.)
        await self.events.emit(Events.LOGIN, self.entity_id, self.game_mode)

    async def _on_respawn(self, buf: PacketBuffer) -> None:
        data = buf.remaining()
        await self.events.emit(Events.RESPAWN, data)

    async def _on_game_event(self, buf: PacketBuffer) -> None:
        event_id = buf.read_ubyte()
        value = buf.read_float()
        if event_id == 3:
            self.game_mode = int(value)
            await self.events.emit(Events.GAME_MODE, self.game_mode)

    async def _on_time_update(self, buf: PacketBuffer) -> None:
        world_age = buf.read_long()
        time_of_day = buf.read_long()
        await self.events.emit(Events.TIME_UPDATE, world_age, time_of_day)

    async def _on_spawn_entity(self, buf: PacketBuffer) -> None:
        await self.events.emit(Events.SPAWN_ENTITY, buf.getvalue())

    async def _on_entity_position(self, buf: PacketBuffer) -> None:
        await self.events.emit(Events.ENTITY_MOVE, buf.getvalue())

    async def _on_entity_pos_rot(self, buf: PacketBuffer) -> None:
        await self.events.emit(Events.ENTITY_MOVE, buf.getvalue())

    async def _on_entity_rotation(self, buf: PacketBuffer) -> None:
        pass

    async def _on_remove_entities(self, buf: PacketBuffer) -> None:
        count = buf.read_varint()
        ids = [buf.read_varint() for _ in range(count)]
        await self.events.emit(Events.REMOVE_ENTITIES, ids)

    async def _on_block_update(self, buf: PacketBuffer) -> None:
        x, y, z = buf.read_position()
        state_id = buf.read_varint()
        await self.events.emit(Events.BLOCK_UPDATE, x, y, z, state_id)

    async def _on_chunk_data(self, buf: PacketBuffer) -> None:
        cx = buf.read_int()
        cz = buf.read_int()
        await self.events.emit(Events.CHUNK_LOAD, cx, cz)

    async def _on_unload_chunk(self, buf: PacketBuffer) -> None:
        cz = buf.read_int()
        cx = buf.read_int()
        await self.events.emit(Events.CHUNK_UNLOAD, cx, cz)

    async def _on_boss_bar(self, buf: PacketBuffer) -> None:
        await self.events.emit(Events.BOSS_BAR, buf.remaining())

    async def _on_title(self, buf: PacketBuffer) -> None:
        text = buf.read_string()
        await self.events.emit(Events.TITLE, text)

    async def _on_subtitle(self, buf: PacketBuffer) -> None:
        text = buf.read_string()
        await self.events.emit(Events.SUBTITLE, text)

    async def _on_action_bar(self, buf: PacketBuffer) -> None:
        text = buf.read_string()
        await self.events.emit(Events.ACTION_BAR, text)

    async def _on_player_list(self, buf: PacketBuffer) -> None:
        await self.events.emit(Events.PLAYER_LIST, buf.remaining())

    async def _on_inventory(self, buf: PacketBuffer) -> None:
        await self.events.emit(Events.INVENTORY, buf.remaining())

    async def _on_slot_update(self, buf: PacketBuffer) -> None:
        await self.events.emit(Events.SLOT_UPDATE, buf.remaining())

    async def _on_death(self, buf: PacketBuffer) -> None:
        await self.events.emit(Events.DEATH, buf.remaining())

    async def _on_hurt(self, buf: PacketBuffer) -> None:
        await self.events.emit(Events.HURT, buf.remaining())

    async def _on_transfer(self, buf: PacketBuffer) -> None:
        host = buf.read_string()
        port = buf.read_varint()
        await self.events.emit(Events.TRANSFER, host, port)

    async def _on_chunk_batch_finished(self, buf: PacketBuffer) -> None:
        # ACK chunk batch
        import struct
        pid = self._sb("chunk_batch_received") or 0x08
        payload = struct.pack(">f", 10.0)
        if self._conn:
            await self._conn.write_packet(pid, payload)

    # ── Extension / plugin support ────────────────────────────────────────

    def load_extension(self, name: str) -> None:
        """Load a named extension (see mcpycore.extensions.loader)."""
        self.extensions.load(name)

    def unload_extension(self, name: str) -> None:
        self.extensions.unload(name)

    # ── Repr ──────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"MinecraftClient({self.host}:{self.port}, "
            f"user={self.profile.username!r}, "
            f"version={self.version_name!r}, "
            f"connected={self.is_connected})"
        )
