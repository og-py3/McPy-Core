"""
MinecraftClient — high-level async Minecraft client for McPy-Core.

Supports every Java Edition protocol 1.7.2 (protocol 4) → 1.21.11 (protocol 775).

Quick start::

    import asyncio
    from mcpycore import MinecraftClient

    async def main():
        client = MinecraftClient("play.example.com", username="BotName")

        @client.event
        async def on_chat(message, sender):
            print(f"[{sender}] {message}")

        await client.start()

    asyncio.run(main())
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Callable

from mcpycore.client.connection import Connection, PlayerProfile, OfflineProfile, LoginError
from mcpycore.client.reconnect import ReconnectPolicy, NoReconnect
from mcpycore.debug.inspector import PacketInspector
from mcpycore.events.emitter import AsyncEventEmitter, Events
from mcpycore.extensions.loader import ExtensionLoader
from mcpycore.humanize.humanizer import Humanizer, HumanizeConfig
from mcpycore.network.stream import StreamError, StreamClosedError
from mcpycore.protocol.registry.registry import PacketRegistry, Direction, global_registry
from mcpycore.protocol.serializers.buffer import PacketBuffer
from mcpycore.protocol.states.machine import State
from mcpycore.protocol.versions.adapters import get_cb_ids, get_sb_ids
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
        Protocol version integer (default: 775 = 1.21.11). Set to the exact
        version your target server runs, e.g. 47 for 1.8, 340 for 1.12.2.
    reconnect_policy:
        A ReconnectPolicy instance. Defaults to NoReconnect.
    humanize:
        A HumanizeConfig (or True for defaults) to enable anti-bot-detection
        timing jitter and auto-login helpers. None disables it entirely.
    debug:
        Enable verbose packet debug logging.
    timeout:
        Socket timeout in seconds.

    Events fired (see ``mcpycore.events.emitter.Events`` for all names)::

        connect          — connection established and play state entered
        disconnect       — connection lost; args: (reason: str)
        reconnect        — before each reconnect attempt; args: (attempt: int)
        error            — unhandled exception; args: (exc,)
        packet           — every received packet; args: (packet_id, buf)
        chat             — player chat; args: (message, sender_uuid)
        system_chat      — system messages; args: (content, overlay)
        health           — health update; args: (health, food, saturation)
        position         — position sync; args: (x, y, z, yaw, pitch)
        spawn            — first position received; args: (x, y, z)
        login            — play login; args: (entity_id, game_mode)
        respawn          — dimension change / respawn; args: (raw_bytes,)
        keepalive        — keep-alive round-trip; args: (latency_ms,)
        chunk_load       — chunk data received; args: (cx, cz)
        chunk_unload     — chunk unloaded; args: (cx, cz)
        block_update     — single block changed; args: (x, y, z, state_id)
        spawn_entity     — entity spawned; args: (raw_bytes,)
        entity_move      — entity moved; args: (raw_bytes,)
        remove_entities  — entities despawned; args: (ids,)
        title            — title text; args: (text,)
        subtitle         — subtitle text; args: (text,)
        action_bar       — action bar text; args: (text,)
        boss_bar         — boss bar update; args: (raw_bytes,)
        player_list      — tab list update; args: (raw_bytes,)
        inventory        — window/inventory contents; args: (raw_bytes,)
        slot_update      — single slot change; args: (raw_bytes,)
        death            — player died; args: (raw_bytes,)
        hurt             — hurt animation; args: (raw_bytes,)
        game_mode        — game-mode changed; args: (game_mode: int)
        time_update      — world time; args: (world_age, time_of_day)
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
        humanize: HumanizeConfig | bool | None = None,
        debug: bool = False,
        timeout: float = 30.0,
    ) -> None:
        self.host = host
        self.port = port
        self.protocol_version = protocol_version

        # Profile — online mode when access_token provided, offline otherwise
        if access_token:
            self.profile: PlayerProfile = PlayerProfile(username, access_token=access_token)
        else:
            self.profile = OfflineProfile(username)

        self._reconnect_policy = reconnect_policy or NoReconnect()
        self._timeout = timeout
        self._running = False

        # Humanizer setup
        if humanize is True:
            self._humanizer: Humanizer | None = Humanizer(HumanizeConfig())
        elif isinstance(humanize, HumanizeConfig):
            self._humanizer = Humanizer(humanize)
        else:
            self._humanizer = None

        # Subsystems
        self.events    = AsyncEventEmitter()
        self.metrics   = MetricsCollector()
        self.inspector = PacketInspector(enabled=debug)
        self.extensions = ExtensionLoader()

        # Connection state (populated during start)
        self._conn: Connection | None = None
        self._handlers: dict[int, Callable] = {}
        self._spawned = False
        self._sequence = 0

        # Player state
        self.entity_id = 0
        self.game_mode = 0
        self.x = self.y = self.z = 0.0
        self.yaw = self.pitch = 0.0
        self.on_ground = True
        self.health = 20.0
        self.food = 20
        self.food_saturation = 5.0

        # Register humanizer chat triggers once events are set up
        if self._humanizer:
            for trigger in self._humanizer.build_chat_handlers(self.send_chat):
                self.events.on(Events.SYSTEM_CHAT,
                               lambda content, _overlay, t=trigger: t(content))
                self.events.on(Events.CHAT,
                               lambda msg, _uuid, t=trigger: t(msg))

    # ── Properties ────────────────────────────────────────────────────────

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
        Decorator to register a handler by function name.

        The function name must start with ``on_``::

            @client.event
            async def on_chat(message, sender):
                ...
        """
        name = coro.__name__
        if not name.startswith("on_"):
            raise ValueError(f"Event handler name must start with 'on_', got {name!r}")
        self.events.on(name[3:], coro)
        return coro

    def on(self, event: str, handler: Callable | None = None) -> Any:
        """Register an event listener (decorator or direct call)."""
        return self.events.on(event, handler)

    def once(self, event: str, handler: Callable | None = None) -> Any:
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
            humanizer=self._humanizer,
        )
        await self._conn.connect()
        self._running = True
        self._spawned = False
        self._sequence = 0
        self._build_handlers()
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

    # ── Packet ID helpers (use full adapter table — all protocol eras) ────

    def _cb(self, name: str) -> int | None:
        """Return the clientbound packet ID for *name* at the current protocol."""
        return get_cb_ids(self.protocol_version).get(name)

    def _sb(self, name: str) -> int | None:
        """Return the serverbound packet ID for *name* at the current protocol."""
        return get_sb_ids(self.protocol_version).get(name)

    def _build_handlers(self) -> None:
        """Rebuild the packet-ID → handler map for the current protocol version."""
        mapping: dict[str, Callable] = {
            "keep_alive":                    self._on_keep_alive,
            "player_position_and_look":      self._on_position,
            "set_health":                    self._on_health,
            "update_health":                 self._on_health,
            "disconnect":                    self._on_disconnect,
            "login":                         self._on_login,
            "respawn":                       self._on_respawn,
            "game_event":                    self._on_game_event,
            "system_chat_message":           self._on_system_chat,
            "chat_message":                  self._on_chat,
            "time_update":                   self._on_time_update,
            "spawn_entity":                  self._on_spawn_entity,
            "entity_position":               self._on_entity_position,
            "entity_position_and_rotation":  self._on_entity_pos_rot,
            "entity_rotation":               self._on_entity_rotation,
            "remove_entities":               self._on_remove_entities,
            "destroy_entities":              self._on_remove_entities,
            "block_update":                  self._on_block_update,
            "chunk_data":                    self._on_chunk_data,
            "unload_chunk":                  self._on_unload_chunk,
            "boss_bar":                      self._on_boss_bar,
            "set_title_text":                self._on_title,
            "title":                         self._on_title,
            "set_subtitle_text":             self._on_subtitle,
            "set_action_bar_text":           self._on_action_bar,
            "player_info_update":            self._on_player_list,
            "player_list_item":              self._on_player_list,
            "set_container_content":         self._on_inventory,
            "set_container_slot":            self._on_slot_update,
            "combat_death":                  self._on_death,
            "hurt_animation":                self._on_hurt,
            "transfer":                      self._on_transfer,
            "chunk_batch_finished":          self._on_chunk_batch_finished,
        }
        self._handlers = {}
        seen_pids: set[int] = set()
        for name, handler in mapping.items():
            pid = self._cb(name)
            if pid is not None and pid not in seen_pids:
                self._handlers[pid] = handler
                seen_pids.add(pid)

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
        """Send a chat message or slash command. Works across all protocol eras."""
        import time as _time
        if message.startswith("/"):
            buf = PacketBuffer()
            cmd = message[1:]
            buf.write_string(cmd)
            if self.protocol_version >= 759:
                # 1.19+: timestamp + salt + signatures
                buf.write_long(int(_time.time() * 1000))
                buf.write_long(0)       # salt
                buf.write_varint(0)     # no argument signatures
                if self.protocol_version < 761:
                    buf.write_bool(False)   # signed preview (1.19–1.19.2 only)
            await self._send("chat_command", buf.flush())
        else:
            buf = PacketBuffer()
            buf.write_string(message)
            if self.protocol_version >= 759:
                buf.write_long(int(_time.time() * 1000))
                buf.write_long(0)
                if self.protocol_version < 761:
                    buf.write_bool(False)
                buf.write_varint(0)
            await self._send("chat_message", buf.flush())

    async def move(
        self,
        x: float, y: float, z: float,
        yaw: float = 0.0, pitch: float = 0.0,
    ) -> None:
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
        """Swing main hand (0) or off hand (1)."""
        buf = PacketBuffer()
        buf.write_varint(hand)
        await self._send("swing_arm", buf.flush())

    async def attack(self, entity_id: int) -> None:
        """Left-click an entity."""
        buf = PacketBuffer()
        buf.write_varint(entity_id)
        buf.write_varint(1)       # interact_at type = attack
        buf.write_bool(False)     # sneaking
        await self._send("interact_entity", buf.flush())

    async def use_item(self, hand: int = 0) -> None:
        """Right-click / use held item."""
        self._sequence += 1
        buf = PacketBuffer()
        buf.write_varint(hand)
        if self.protocol_version >= 764:
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
        """Respawn after death."""
        buf = PacketBuffer()
        buf.write_varint(0)   # perform respawn
        await self._send("client_status", buf.flush())

    async def set_held_slot(self, slot: int) -> None:
        """Switch hotbar slot (0–8)."""
        if not 0 <= slot <= 8:
            raise ValueError(f"Slot must be 0–8, got {slot}")
        buf = PacketBuffer()
        buf.write_short(slot)
        await self._send("set_held_item", buf.flush())

    # ── Packet handlers ───────────────────────────────────────────────────

    async def _on_keep_alive(self, buf: PacketBuffer) -> None:
        """
        Echo the keep-alive ID back to the server.

        The wire type differs across protocol versions:
          1.7/1.8  (4–47)   : INT   (4 bytes)
          1.9–1.11 (107–316): VarInt
          1.12+    (335+)   : Long  (8 bytes)
        """
        t0 = time.monotonic()

        # Read keep-alive ID using the correct wire type
        assert self._conn is not None
        ka_id = self._conn.read_keepalive_id(buf)

        if self._humanizer:
            await self._humanizer.keepalive_jitter()

        resp = PacketBuffer()
        self._conn.write_keepalive_id(resp, ka_id)
        await self._send("keep_alive", resp.flush())

        latency = (time.monotonic() - t0) * 1000
        self.metrics.record_latency(latency)
        await self.events.emit(Events.KEEPALIVE, latency)

    async def _on_position(self, buf: PacketBuffer) -> None:
        """Handle player-position-and-look / synchronize-player-position."""
        x = buf.read_double()
        y = buf.read_double()
        z = buf.read_double()
        yaw   = buf.read_float()
        pitch = buf.read_float()
        flags = buf.read_byte()

        # Apply relative flags
        self.x = self.x + x if flags & 0x01 else x
        self.y = self.y + y if flags & 0x02 else y
        self.z = self.z + z if flags & 0x04 else z
        self.yaw   = self.yaw   + yaw   if flags & 0x08 else yaw
        self.pitch = self.pitch + pitch if flags & 0x10 else pitch

        if self._humanizer:
            await self._humanizer.position_confirm()

        if self.protocol_version >= 107:
            # 1.9+: confirm teleport
            teleport_id = buf.read_varint()
            resp = PacketBuffer()
            resp.write_varint(teleport_id)
            await self._send("confirm_teleportation", resp.flush())
        # 1.7/1.8: no teleport confirmation needed

        # Override with natural spawn angles on first position
        if not self._spawned and self._humanizer:
            nat_yaw, nat_pitch = self._humanizer.spawn_angles()
            self.yaw, self.pitch = nat_yaw, nat_pitch

        await self.events.emit(Events.POSITION, self.x, self.y, self.z, self.yaw, self.pitch)

        if not self._spawned:
            self._spawned = True
            await self.events.emit(Events.SPAWN, self.x, self.y, self.z)
            if self._humanizer:
                asyncio.ensure_future(
                    self._humanizer.settle(self.look)
                )

    async def _on_health(self, buf: PacketBuffer) -> None:
        self.health = buf.read_float()
        self.food = buf.read_varint()
        self.food_saturation = buf.read_float()
        await self.events.emit(Events.HEALTH, self.health, self.food, self.food_saturation)
        if self.health <= 0:
            await self.events.emit(Events.DEATH)

    async def _on_system_chat(self, buf: PacketBuffer) -> None:
        content = buf.read_string()
        try:
            overlay = buf.read_bool()
        except Exception:
            overlay = False
        await self.events.emit(Events.SYSTEM_CHAT, content, overlay)

    async def _on_chat(self, buf: PacketBuffer) -> None:
        # Format varies significantly across protocol versions
        try:
            if self.protocol_version >= 764:
                # 1.20.2+: sender uuid → index → optional sig → message
                sender = buf.read_uuid()
                buf.read_varint()           # index
                has_sig = buf.read_bool()
                if has_sig:
                    buf.read_bytes(256)
                message = buf.read_string()
            elif self.protocol_version >= 759:
                # 1.19–1.20.1
                sender = buf.read_uuid()
                try:
                    buf.read_varint()       # index
                    has_sig = buf.read_bool()
                    if has_sig:
                        buf.read_bytes(256)
                except Exception:
                    pass
                message = buf.read_string()
            else:
                # 1.7–1.18: simple JSON string
                message = buf.read_string()
                sender = uuid.UUID(int=0)
        except Exception:
            message = ""
            sender = uuid.UUID(int=0)

        await self.events.emit(Events.CHAT, message, sender)

    async def _on_disconnect(self, buf: PacketBuffer) -> None:
        try:
            reason = buf.read_string()
        except Exception:
            reason = "Unknown"
        self._running = False
        await self.events.emit(Events.DISCONNECT, reason)

    async def _on_login(self, buf: PacketBuffer) -> None:
        self.entity_id = buf.read_int()
        try:
            _hardcore = buf.read_bool()
            self.game_mode = buf.read_ubyte()
        except Exception:
            pass
        buf.remaining()   # drain dimension codec etc.
        if self._conn:
            self._conn.entity_id = self.entity_id
            self._conn.game_mode = self.game_mode
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
        pass  # not emitted — very high frequency, handled by user if needed

    async def _on_remove_entities(self, buf: PacketBuffer) -> None:
        try:
            count = buf.read_varint()
            ids = [buf.read_varint() for _ in range(count)]
        except Exception:
            ids = []
        await self.events.emit(Events.REMOVE_ENTITIES, ids)

    async def _on_block_update(self, buf: PacketBuffer) -> None:
        try:
            x, y, z = buf.read_position()
            state_id = buf.read_varint()
            await self.events.emit(Events.BLOCK_UPDATE, x, y, z, state_id)
        except Exception:
            pass

    async def _on_chunk_data(self, buf: PacketBuffer) -> None:
        try:
            cx = buf.read_int()
            cz = buf.read_int()
            await self.events.emit(Events.CHUNK_LOAD, cx, cz)
        except Exception:
            pass

    async def _on_unload_chunk(self, buf: PacketBuffer) -> None:
        try:
            if self.protocol_version >= 764:
                cz = buf.read_int()
                cx = buf.read_int()
            else:
                cx = buf.read_int()
                cz = buf.read_int()
            await self.events.emit(Events.CHUNK_UNLOAD, cx, cz)
        except Exception:
            pass

    async def _on_boss_bar(self, buf: PacketBuffer) -> None:
        await self.events.emit(Events.BOSS_BAR, buf.remaining())

    async def _on_title(self, buf: PacketBuffer) -> None:
        try:
            text = buf.read_string()
        except Exception:
            text = ""
        await self.events.emit(Events.TITLE, text)

    async def _on_subtitle(self, buf: PacketBuffer) -> None:
        try:
            text = buf.read_string()
        except Exception:
            text = ""
        await self.events.emit(Events.SUBTITLE, text)

    async def _on_action_bar(self, buf: PacketBuffer) -> None:
        try:
            text = buf.read_string()
        except Exception:
            text = ""
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
        try:
            host = buf.read_string()
            port = buf.read_varint()
            await self.events.emit(Events.TRANSFER, host, port)
        except Exception:
            pass

    async def _on_chunk_batch_finished(self, buf: PacketBuffer) -> None:
        import struct
        pid = self._sb("chunk_batch_received")
        if pid is not None and self._conn:
            payload = struct.pack(">f", 10.0)
            await self._conn.write_packet(pid, payload)

    # ── Extension support ─────────────────────────────────────────────────

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
