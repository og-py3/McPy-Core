"""
MinecraftClient — the main entry point for Mcpycore.

Handles the full connection lifecycle:
  Handshake → Login → Configuration (1.20.2+) → Play

Supports Minecraft 1.20.2 through 1.21.11 (protocol 764–775)
plus snapshot builds (auto-falls back to nearest stable dispatch).

Usage::

    from mcpycore import MinecraftClient, OfflineAuth
    from mcpycore.versions import PROTOCOL_LATEST

    client = MinecraftClient("play.example.com",
                             auth=OfflineAuth("BotPlayer"),
                             protocol_version=PROTOCOL_LATEST)

    @client.on("chat_message")
    def on_chat(packet):
        print(packet.message)

    client.connect()
    client.run()
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid
import warnings
from collections import defaultdict
from typing import Callable, Any, Union

from cryptography.hazmat.primitives.serialization import load_der_public_key
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.backends import default_backend

from mcpycore.connection import Connection
from mcpycore.authentication import OfflineAuth, MicrosoftAuth, PlayerProfile
from mcpycore.packets.packet import PacketBuffer
from mcpycore.packets import login as lp
from mcpycore.packets import status as sp
from mcpycore.packets import play as pp
from mcpycore.world import World, Chunk
from mcpycore.entity import Entity, EntityManager
from mcpycore.player import PlayerInventory, TabList, TabListEntry
from mcpycore.versions import (
    PROTOCOL_LATEST, version_name, is_snapshot, nearest_stable,
    get_clientbound_id, get_serverbound_id,
    get_config_clientbound_id, get_config_serverbound_id,
)
from mcpycore import exceptions as exc

from mcpycore.packets.play.inventory import (
    SetContainerContent, SetContainerSlot, OpenScreen,
    CloseContainer, SetHeldItem,
)
from mcpycore.packets.play.boss_bar import BossBar
from mcpycore.packets.play.title import (
    SetTitleText, SetSubtitleText, SetActionBarText,
    SetTitleAnimationTimes, ClearTitles,
)
from mcpycore.packets.play.player_list import (
    PlayerInfoUpdate, PlayerInfoRemove, SetTabListHeaderAndFooter,
    ACTION_ADD_PLAYER, ACTION_UPDATE_GAME_MODE,
    ACTION_UPDATE_LISTED, ACTION_UPDATE_LATENCY, ACTION_UPDATE_DISPLAY,
)
from mcpycore.packets.play.scoreboard import (
    UpdateObjectives, DisplayObjective, UpdateScore, ResetScore, UpdateTeams,
)
from mcpycore.packets.play.sound import SoundEffect, EntitySoundEffect, StopSound

logger = logging.getLogger(__name__)


class MinecraftClient:
    """
    High-level Minecraft client supporting protocol versions 764–775
    (Minecraft 1.20.2 → 1.21.11) plus snapshot builds.

    Parameters
    ----------
    host:
        Server hostname or IP.
    port:
        Server port (default 25565).
    auth:
        An ``OfflineAuth`` or ``MicrosoftAuth`` instance.
        Defaults to ``OfflineAuth("McpycoreBot")``.
    protocol_version:
        Numeric Minecraft protocol version.
        Default: 775 (Minecraft 1.21.11 / latest).
        Use constants from ``mcpycore.versions``.
        Snapshot versions (>= 0x40000000) are supported — packet
        dispatch falls back to the nearest stable version.
    timeout:
        Socket timeout in seconds.
    """

    def __init__(
        self,
        host: str,
        port: int = 25565,
        auth: Union[OfflineAuth, MicrosoftAuth, None] = None,
        protocol_version: int = PROTOCOL_LATEST,
        timeout: float = 30.0,
    ) -> None:
        self.host = host
        self.port = port
        self.auth: Union[OfflineAuth, MicrosoftAuth] = auth or OfflineAuth("McpycoreBot")
        self.protocol_version = protocol_version

        if is_snapshot(protocol_version):
            warnings.warn(
                f"Snapshot protocol {protocol_version:#010x} detected — "
                f"falling back to {version_name(nearest_stable(protocol_version))} "
                "for packet dispatch. Packet IDs may differ.",
                stacklevel=2,
            )

        self._conn = Connection(host, port, timeout=timeout)
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._running = False

        self.profile: PlayerProfile | None = None
        self.world = World()
        self.entities = EntityManager()
        self.inventory = PlayerInventory()
        self.tab_list = TabList()
        self.boss_bars: dict[uuid.UUID, BossBar] = {}

        # Position
        self.x: float = 0.0
        self.y: float = 0.0
        self.z: float = 0.0
        self.yaw: float = 0.0
        self.pitch: float = 0.0
        self.on_ground: bool = True

        # Vitals
        self.health: float = 20.0
        self.food: int = 20
        self.food_saturation: float = 5.0

        # Abilities
        self.is_flying: bool = False
        self.allow_flying: bool = False
        self.invulnerable: bool = False
        self.instant_build: bool = False
        self.fly_speed: float = 0.05
        self.walk_speed: float = 0.1

        # Game state
        self.game_mode: int = 0   # 0=survival, 1=creative, 2=adventure, 3=spectator
        self.dimension: str = "minecraft:overworld"
        self.difficulty: int = 2

        # Internal
        self._player_entity_id: int = 0
        self._sequence: int = 0
        self._play_handlers: dict[int, Callable[[PacketBuffer], Any]] = {}
        self._build_play_dispatch()

    # ── Event system ──────────────────────────────────────────────────────────

    def on(self, event: str) -> Callable:
        """
        Decorator to register an event listener.
        Use string constants from ``mcpycore.events`` to avoid typos.

        Example::

            from mcpycore.events import EVT_CHAT

            @client.on(EVT_CHAT)
            def on_chat(pkt):
                print(pkt.message)
        """
        def decorator(func: Callable) -> Callable:
            self._handlers[event].append(func)
            return func
        return decorator

    def emit(self, event: str, *args: Any) -> None:
        """Fire all handlers registered for *event*."""
        for handler in self._handlers.get(event, []):
            try:
                handler(*args)
            except Exception:
                logger.exception(
                    "Unhandled exception in handler for event %r (handler: %s)",
                    event,
                    getattr(handler, "__qualname__", repr(handler)),
                )

    # ── Connection / lifecycle ────────────────────────────────────────────────

    def connect(self) -> None:
        """
        Connect and complete the full login + configuration sequence.
        After this returns the client is in the play state.
        """
        self._conn.connect()
        self.profile = self.auth.get_profile()
        self._handshake()
        self._login()
        self.emit("connected", self)

    def run(self) -> None:
        """
        Start the packet-processing loop.  Blocks until disconnected.
        Call ``connect()`` first.
        """
        self._running = True
        try:
            self._packet_loop()
        except exc.PlayKickError as e:
            self.emit("disconnect", e.reason)
        except exc.McpycoreConnectionError as e:
            self.emit("disconnect", str(e))
        finally:
            self._running = False
            self._conn.close()

    def disconnect(self) -> None:
        """Gracefully stop the packet loop and close the socket."""
        self._running = False

    # ── High-level player actions ─────────────────────────────────────────────

    def send_chat(self, message: str) -> None:
        """
        Send a chat message or slash command.
        Messages starting with '/' are sent as commands.
        """
        if message.startswith("/"):
            pkt = pp.ChatCommand(
                command=message[1:],
                timestamp=int(time.time() * 1000),
                salt=int.from_bytes(os.urandom(8), "big"),
            )
            self._send_sb(pkt, "chat_command")
        else:
            pkt = pp.ChatMessageSB(
                message=message,
                timestamp=int(time.time() * 1000),
                salt=int.from_bytes(os.urandom(8), "big"),
            )
            self._send_sb(pkt, "chat_message")

    def move_to(
        self, x: float, y: float, z: float,
        yaw: float = 0.0, pitch: float = 0.0,
    ) -> None:
        """Send a position + rotation update to the server."""
        self.x, self.y, self.z = x, y, z
        self.yaw, self.pitch = yaw, pitch
        pkt = pp.MovePlayerPosRot(
            x=x, y=y, z=z, yaw=yaw, pitch=pitch, on_ground=self.on_ground,
        )
        self._send_sb(pkt, "move_player_pos_rot")

    def look_at(self, yaw: float, pitch: float) -> None:
        """Change look direction without moving."""
        self.yaw, self.pitch = yaw, pitch
        pkt = pp.MovePlayerRot(yaw=yaw, pitch=pitch, on_ground=self.on_ground)
        self._send_sb(pkt, "move_player_rot")

    def swing_arm(self, hand: int = 0) -> None:
        """Swing main (0) or off-hand (1)."""
        pkt = pp.SwingArm(hand=hand)
        self._send_sb(pkt, "swing_arm")

    def attack_entity(self, entity_id: int) -> None:
        """Left-click / attack an entity."""
        pkt = pp.InteractEntity(entity_id=entity_id, interaction_type=1, sneaking=False)
        self._send_sb(pkt, "interact_entity")

    def interact_entity(self, entity_id: int, hand: int = 0) -> None:
        """Right-click / interact with an entity."""
        pkt = pp.InteractEntity(entity_id=entity_id, interaction_type=0, hand=hand, sneaking=False)
        self._send_sb(pkt, "interact_entity")

    def use_item(self, hand: int = 0) -> None:
        """Right-click in air (use held item)."""
        self._sequence += 1
        pkt = pp.UseItem(hand=hand, sequence=self._sequence)
        self._send_sb(pkt, "use_item")

    def use_item_on_block(
        self,
        x: int, y: int, z: int,
        face: int = 1,
        hand: int = 0,
        cx: float = 0.5, cy: float = 0.5, cz: float = 0.5,
    ) -> None:
        """Right-click on a block face."""
        self._sequence += 1
        pkt = pp.UseItemOn(
            hand=hand, x=x, y=y, z=z, face=face,
            cursor_x=cx, cursor_y=cy, cursor_z=cz,
            inside_block=False, sequence=self._sequence,
        )
        self._send_sb(pkt, "use_item_on")

    def dig_block(self, x: int, y: int, z: int, face: int = 1) -> None:
        """Start digging a block (sends PlayerAction START_DIG)."""
        pkt = pp.PlayerAction(status=0, x=x, y=y, z=z, face=face, sequence=self._sequence)
        self._send_sb(pkt, "player_action")

    def drop_item(self, drop_stack: bool = False) -> None:
        """Drop the held item or the entire stack."""
        pkt = pp.PlayerAction(
            status=4 if drop_stack else 3,
            x=0, y=0, z=0, face=0, sequence=0,
        )
        self._send_sb(pkt, "player_action")

    def start_sneaking(self) -> None:
        pkt = pp.PlayerCommand(entity_id=self._player_entity_id, action_id=0)
        self._send_sb(pkt, "player_command")

    def stop_sneaking(self) -> None:
        pkt = pp.PlayerCommand(entity_id=self._player_entity_id, action_id=1)
        self._send_sb(pkt, "player_command")

    def start_sprinting(self) -> None:
        pkt = pp.PlayerCommand(entity_id=self._player_entity_id, action_id=3)
        self._send_sb(pkt, "player_command")

    def stop_sprinting(self) -> None:
        pkt = pp.PlayerCommand(entity_id=self._player_entity_id, action_id=4)
        self._send_sb(pkt, "player_command")

    def set_held_slot(self, slot: int) -> None:
        """Change the active hotbar slot (0–8)."""
        if not 0 <= slot <= 8:
            raise ValueError(f"Hotbar slot must be 0–8, got {slot}")
        self.inventory.held_slot = slot
        pkt = pp.SetHeldItemSB(slot=slot)
        self._send_sb(pkt, "set_held_item")

    def close_container(self, window_id: int = 0) -> None:
        """Close an open container."""
        pkt = CloseContainer(window_id=window_id)
        self._send_sb(pkt, "close_container")

    def set_creative_slot(self, slot: int, item_id: int, count: int = 1) -> None:
        """(Creative mode) Set a slot directly."""
        from mcpycore.packets.play.inventory import ItemStack
        item = ItemStack(present=True, item_id=item_id, count=count)
        pkt = pp.SetCreativeModeSlot(slot=slot, item=item)
        self._send_sb(pkt, "set_creative_mode_slot")

    def respawn(self) -> None:
        """Send client status to respawn (after death)."""
        pkt = pp.ClientStatus(action_id=0)
        self._send_sb(pkt, "client_status")

    # ── Static: server status ping ────────────────────────────────────────────

    @classmethod
    def ping(
        cls,
        host: str,
        port: int = 25565,
        timeout: float = 5.0,
        protocol_version: int = PROTOCOL_LATEST,
    ) -> dict:
        """
        Ping a Minecraft server without logging in.

        Returns the server's status JSON dict::

            info = MinecraftClient.ping("play.hypixel.net")
            print(info["description"])
            print(info["players"]["online"], "/", info["players"]["max"])
        """
        from mcpycore.utils.datatypes import write_varint as wv, write_string, write_ushort

        conn = Connection(host, port, timeout=timeout)
        conn.connect()
        try:
            handshake = (
                b"\x00"
                + wv(protocol_version)
                + write_string(host)
                + write_ushort(port)
                + wv(1)     # next_state = 1 (status)
            )
            conn._raw_send(wv(len(handshake)) + handshake)
            conn._raw_send(b"\x01\x00")   # status request
            packet_id, resp_buf = conn.read_packet_raw()
            return sp.StatusResponse.decode(resp_buf).data
        finally:
            conn.close()

    # ── Version helpers ───────────────────────────────────────────────────────

    @property
    def version_name(self) -> str:
        """Human-readable version string."""
        return version_name(self.protocol_version)

    @property
    def position(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z

    @property
    def is_creative(self) -> bool:
        return self.game_mode == 1

    @property
    def is_survival(self) -> bool:
        return self.game_mode == 0

    def _cb_id(self, name: str) -> int | None:
        return get_clientbound_id(name, self.protocol_version)

    def _sb_id(self, name: str) -> int | None:
        return get_serverbound_id(name, self.protocol_version)

    def _cfg_cb_id(self, name: str) -> int | None:
        return get_config_clientbound_id(name, self.protocol_version)

    def _cfg_sb_id(self, name: str) -> int | None:
        return get_config_serverbound_id(name, self.protocol_version)

    def _send_sb(self, pkt: Any, name: str) -> None:
        """Send a serverbound packet, stamping it with the version-correct packet ID."""
        pid = self._sb_id(name)
        if pid is not None:
            # Set on the instance, not the class, to avoid mutating shared state.
            pkt.packet_id = pid
        self._conn.send_packet(pkt)

    def _send_cfg_sb(self, pkt: Any, name: str) -> None:
        """Send a configuration-state serverbound packet with the correct ID."""
        pid = self._cfg_sb_id(name)
        if pid is not None:
            pkt.packet_id = pid
        self._conn.send_packet(pkt)

    # ── Internals: connection sequence ────────────────────────────────────────

    def _handshake(self) -> None:
        from mcpycore.utils.datatypes import write_varint as wv, write_string, write_ushort
        payload = (
            b"\x00"
            + wv(self.protocol_version)
            + write_string(self.host)
            + write_ushort(self.port)
            + wv(2)   # next_state = 2 (login)
        )
        self._conn._raw_send(wv(len(payload)) + payload)

    def _login(self) -> None:
        assert self.profile is not None
        self._conn.send_packet(
            lp.LoginStart(username=self.profile.username, player_uuid=self.profile.player_uuid)
        )
        while True:
            packet_id, buf = self._conn.read_packet_raw()
            if packet_id == 0x00:
                pkt = lp.LoginDisconnect.decode(buf)
                raise exc.LoginKickError(pkt.reason)
            elif packet_id == 0x01:
                self._handle_encryption(lp.EncryptionRequest.decode(buf))
            elif packet_id == 0x02:
                pkt = lp.LoginSuccess.decode(buf)
                self.profile.username = pkt.username
                self.profile.player_uuid = pkt.player_uuid
                self._conn.send_packet(lp.LoginAcknowledged())
                self._configuration_state()
                break
            elif packet_id == 0x03:
                pkt = lp.SetCompression.decode(buf)
                self._conn.set_compression(pkt.threshold)
            elif packet_id == 0x04:
                pkt = lp.LoginPluginRequest.decode(buf)
                self._conn.send_packet(lp.LoginPluginResponse(message_id=pkt.message_id, data=None))

    def _handle_encryption(self, pkt: lp.EncryptionRequest) -> None:
        shared_secret = os.urandom(16)
        sha1 = hashlib.sha1()
        sha1.update(pkt.server_id.encode("ascii"))
        sha1.update(shared_secret)
        sha1.update(pkt.public_key)
        digest = int.from_bytes(sha1.digest(), "big", signed=True)
        server_hash = format(digest, "x")
        if hasattr(self.auth, "join_session") and self.profile is not None:
            self.auth.join_session(server_hash, self.profile)
        pub_key = load_der_public_key(pkt.public_key, backend=default_backend())
        self._conn.send_packet(lp.EncryptionResponse(
            shared_secret=pub_key.encrypt(shared_secret, PKCS1v15()),
            verify_token=pub_key.encrypt(pkt.verify_token, PKCS1v15()),
        ))
        self._conn.enable_encryption(shared_secret)

    def _configuration_state(self) -> None:
        """
        Handle the Configuration state (1.20.2+).

        Packet IDs are resolved from the version registry instead of being
        hardcoded, so this works correctly across all supported protocol versions.
        """
        from mcpycore.packets.play.configuration import (
            ClientInformationConfig,
            SelectKnownPacksSB,
            AcknowledgeFinishConfiguration,
        )

        # Resolve configuration-state packet IDs for this protocol version.
        finish_cb_id   = self._cfg_cb_id("config_finish")           # CB: server signals end
        disconnect_cb_id = self._cfg_cb_id("config_disconnect")     # CB: server kicks
        known_packs_cb_id = self._cfg_cb_id("config_select_known_packs")  # CB: server queries
        keepalive_cb_id = self._cfg_cb_id("config_keep_alive")      # CB: keep-alive ping

        # Send ClientInformation (configuration variant) with the correct SB ID.
        ci = ClientInformationConfig()
        self._send_cfg_sb(ci, "config_client_information")

        logger.debug(
            "Configuration state: finish_cb=0x%s disconnect_cb=0x%s known_packs_cb=0x%s",
            f"{finish_cb_id:02X}" if finish_cb_id is not None else "N/A",
            f"{disconnect_cb_id:02X}" if disconnect_cb_id is not None else "N/A",
            f"{known_packs_cb_id:02X}" if known_packs_cb_id is not None else "N/A",
        )

        while True:
            packet_id, buf = self._conn.read_packet_raw()

            if finish_cb_id is not None and packet_id == finish_cb_id:
                # Server signals end of configuration — send acknowledgement.
                ack = AcknowledgeFinishConfiguration()
                self._send_cfg_sb(ack, "config_acknowledge_finish")
                break

            elif disconnect_cb_id is not None and packet_id == disconnect_cb_id:
                raise exc.LoginKickError(buf.read_string())

            elif known_packs_cb_id is not None and packet_id == known_packs_cb_id:
                # Server asks which data packs we know — respond with an empty list.
                response = SelectKnownPacksSB(packs=[])
                self._send_cfg_sb(response, "config_select_known_packs")

            elif keepalive_cb_id is not None and packet_id == keepalive_cb_id:
                # Echo the keep-alive ID back.
                ka_id = buf.read_long()
                from mcpycore.utils.datatypes import write_varint as wv, write_long
                ka_sb_id = self._cfg_sb_id("config_keep_alive") or 0x04
                payload = wv(ka_sb_id) + write_long(ka_id)
                self._conn._raw_send(wv(len(payload)) + payload)

            else:
                # Plugin messages, registry data, feature flags, etc. — safe to drain.
                buf.remaining()

    # ── Play dispatch table ───────────────────────────────────────────────────

    def _build_play_dispatch(self) -> None:
        """Build {packet_id: handler} using the version registry."""
        mapping: dict[str, Callable] = {
            # Core
            "keep_alive":                   self._on_keep_alive,
            "player_position_and_look":     self._on_player_position_and_look,
            "set_health":                   self._on_set_health,
            "disconnect":                   self._on_disconnect,
            "login":                        self._on_login,
            "respawn":                      self._on_respawn,
            "game_event":                   self._on_game_event,
            # Chat
            "system_chat_message":          self._on_system_chat,
            "chat_message":                 self._on_chat_message,
            "disguised_chat_message":       self._on_disguised_chat,
            # Time
            "time_update":                  self._on_time_update,
            # Entities
            "spawn_entity":                 self._on_spawn_entity,
            "entity_position":              self._on_entity_position,
            "entity_position_and_rotation": self._on_entity_position_rotation,
            "entity_rotation":              self._on_entity_rotation,
            "remove_entities":              self._on_remove_entities,
            "entity_effect":                self._on_entity_effect,
            # World
            "block_update":                 self._on_block_update,
            "multi_block_change":           self._on_multi_block_change,
            "chunk_data":                   self._on_chunk_data,
            "unload_chunk":                 self._on_unload_chunk,
            "explosion":                    self._on_explosion,
            "world_event":                  self._on_world_event,
            # Inventory
            "set_container_content":        self._on_set_container_content,
            "set_container_slot":           self._on_set_container_slot,
            "open_screen":                  self._on_open_screen,
            "set_held_item":                self._on_set_held_item,
            # Boss bar
            "boss_bar":                     self._on_boss_bar,
            # Title
            "set_title_text":               self._on_title,
            "set_subtitle_text":            self._on_subtitle,
            "set_action_bar_text":          self._on_action_bar,
            "set_title_animation_times":    self._on_title_times,
            "clear_titles":                 self._on_clear_titles,
            # Player list
            "player_info_update":           self._on_player_info_update,
            "player_info_remove":           self._on_player_info_remove,
            "set_tab_list_header_and_footer": self._on_tab_header_footer,
            # Player state
            "player_abilities":             self._on_player_abilities,
            # Scoreboard
            "update_objectives":            self._on_update_objectives,
            "display_objective":            self._on_display_objective,
            "update_score":                 self._on_update_score,
            "reset_score":                  self._on_reset_score,
            "update_teams":                 self._on_update_teams,
            # Sound
            "sound_effect":                 self._on_sound,
            "entity_sound_effect":          self._on_entity_sound,
            "stop_sound":                   self._on_stop_sound,
            # Combat
            "combat_death":                 self._on_death,
            "hurt_animation":               self._on_hurt,
            "damage_event":                 self._on_damage,
            # Transfer (1.21+)
            "transfer":                     self._on_transfer,
            # Chunk batch (just ACK)
            "chunk_batch_start":            self._on_chunk_batch_start,
            "chunk_batch_finished":         self._on_chunk_batch_finished,
        }
        for name, handler in mapping.items():
            pid = self._cb_id(name)
            if pid is not None:
                if pid in self._play_handlers:
                    existing_name = next(
                        (n for n, h in mapping.items() if h == self._play_handlers[pid]),
                        "unknown",
                    )
                    logger.warning(
                        "Packet ID collision during dispatch build at protocol %d: "
                        "0x%02X is claimed by both %r and %r — %r wins.",
                        self.protocol_version, pid, existing_name, name, name,
                    )
                self._play_handlers[pid] = handler

    # ── Main packet loop ──────────────────────────────────────────────────────

    def _packet_loop(self) -> None:
        while self._running:
            try:
                packet_id, buf = self._conn.read_packet_raw()
            except exc.McpycoreConnectionError:
                raise
            except Exception as e:
                raise exc.McpycoreConnectionError(f"Packet read failed: {e}") from e

            handler = self._play_handlers.get(packet_id)
            if handler is not None:
                try:
                    handler(buf)
                except exc.PlayKickError:
                    raise
                except Exception:
                    logger.exception(
                        "Error handling play packet 0x%02X", packet_id
                    )
            else:
                logger.debug("Unhandled play packet 0x%02X (%d bytes)", packet_id, len(buf.remaining()))

    # ── Play packet handlers ──────────────────────────────────────────────────

    def _on_keep_alive(self, buf: PacketBuffer) -> None:
        ka_id = buf.read_long()
        pkt = pp.KeepAlive(keep_alive_id=ka_id)
        self._send_sb(pkt, "keep_alive")

    def _on_player_position_and_look(self, buf: PacketBuffer) -> None:
        pkt = pp.PlayerPositionAndLook.decode(buf)
        self.x, self.y, self.z = pkt.x, pkt.y, pkt.z
        self.yaw, self.pitch = pkt.yaw, pkt.pitch
        # Confirm the teleport
        tp_confirm = pp.ConfirmTeleportation(teleport_id=pkt.teleport_id)
        self._send_sb(tp_confirm, "confirm_teleportation")
        self.emit("position", self.x, self.y, self.z, self.yaw, self.pitch)

    def _on_set_health(self, buf: PacketBuffer) -> None:
        pkt = pp.SetHealth.decode(buf)
        self.health = pkt.health
        self.food = pkt.food
        self.food_saturation = pkt.food_saturation
        self.emit("set_health", pkt)

    def _on_disconnect(self, buf: PacketBuffer) -> None:
        reason = buf.read_string()
        raise exc.PlayKickError(reason)

    def _on_login(self, buf: PacketBuffer) -> None:
        pkt = pp.Login.decode(buf)
        self._player_entity_id = pkt.entity_id
        self.game_mode = pkt.game_mode
        self.dimension = pkt.dimension_name
        self.entities.clear()

    def _on_respawn(self, buf: PacketBuffer) -> None:
        pkt = pp.Respawn.decode(buf)
        self.dimension = pkt.dimension_name
        self.game_mode = pkt.game_mode
        self.entities.clear()
        self.emit("respawn", pkt)

    def _on_game_event(self, buf: PacketBuffer) -> None:
        pkt = pp.GameEvent.decode(buf)
        if pkt.event == 3:   # change_game_mode
            self.game_mode = int(pkt.value)
        self.emit("game_event", pkt)

    def _on_system_chat(self, buf: PacketBuffer) -> None:
        pkt = pp.SystemChatMessage.decode(buf)
        self.emit("system_message", pkt)

    def _on_chat_message(self, buf: PacketBuffer) -> None:
        pkt = pp.ChatMessage.decode(buf)
        self.emit("chat_message", pkt)

    def _on_disguised_chat(self, buf: PacketBuffer) -> None:
        pkt = pp.DisguisedChatMessage.decode(buf)
        self.emit("chat_message", pkt)

    def _on_time_update(self, buf: PacketBuffer) -> None:
        pkt = pp.TimeUpdate.decode(buf)
        self.emit("time_update", pkt)

    def _on_spawn_entity(self, buf: PacketBuffer) -> None:
        pkt = pp.SpawnEntity.decode(buf)
        entity = Entity(
            entity_id=pkt.entity_id,
            entity_uuid=pkt.entity_uuid,
            entity_type=pkt.entity_type,
            x=pkt.x, y=pkt.y, z=pkt.z,
            yaw=pkt.yaw, pitch=pkt.pitch,
        )
        self.entities.add(entity)
        self.emit("spawn_entity", entity)

    def _on_entity_position(self, buf: PacketBuffer) -> None:
        pkt = pp.EntityPosition.decode(buf)
        entity = self.entities.get(entity_id=pkt.entity_id)
        if entity is not None:
            entity.x += pkt.delta_x / 4096
            entity.y += pkt.delta_y / 4096
            entity.z += pkt.delta_z / 4096
            self.emit("entity_move", entity)

    def _on_entity_position_rotation(self, buf: PacketBuffer) -> None:
        pkt = pp.EntityPositionAndRotation.decode(buf)
        entity = self.entities.get(entity_id=pkt.entity_id)
        if entity is not None:
            entity.x += pkt.delta_x / 4096
            entity.y += pkt.delta_y / 4096
            entity.z += pkt.delta_z / 4096
            entity.yaw = pkt.yaw
            entity.pitch = pkt.pitch
            self.emit("entity_move", entity)

    def _on_entity_rotation(self, buf: PacketBuffer) -> None:
        pkt = pp.EntityRotation.decode(buf)
        entity = self.entities.get(entity_id=pkt.entity_id)
        if entity is not None:
            entity.yaw = pkt.yaw
            entity.pitch = pkt.pitch
            self.emit("entity_move", entity)

    def _on_remove_entities(self, buf: PacketBuffer) -> None:
        pkt = pp.RemoveEntities.decode(buf)
        for eid in pkt.entity_ids:
            self.entities.remove(eid)
        self.emit("remove_entities", pkt.entity_ids)

    def _on_entity_effect(self, buf: PacketBuffer) -> None:
        self.emit("entity_effect", buf.remaining())

    def _on_block_update(self, buf: PacketBuffer) -> None:
        pkt = pp.BlockUpdate.decode(buf)
        x, y, z = pkt.location
        self.world.set_block_state(x, y, z, pkt.block_state_id)
        self.emit("block_update", pkt)

    def _on_multi_block_change(self, buf: PacketBuffer) -> None:
        pkt = pp.MultiBlockChange.decode(buf)
        self.emit("multi_block_change", pkt)

    def _on_chunk_data(self, buf: PacketBuffer) -> None:
        try:
            chunk = Chunk.decode(buf)
            self.world.add_chunk(chunk)
            self.emit("chunk_load", chunk)
        except Exception:
            logger.exception("Error decoding chunk data")

    def _on_unload_chunk(self, buf: PacketBuffer) -> None:
        chunk_x = buf.read_int()
        chunk_z = buf.read_int()
        self.world.remove_chunk(chunk_x, chunk_z)
        self.emit("chunk_unload", chunk_x, chunk_z)

    def _on_explosion(self, buf: PacketBuffer) -> None:
        self.emit("explosion", buf.remaining())

    def _on_world_event(self, buf: PacketBuffer) -> None:
        self.emit("world_event", buf.remaining())

    def _on_set_container_content(self, buf: PacketBuffer) -> None:
        pkt = SetContainerContent.decode(buf)
        if pkt.window_id == 0:
            self.inventory.set_all(pkt.slots)
        self.emit("set_container_content", pkt)

    def _on_set_container_slot(self, buf: PacketBuffer) -> None:
        pkt = SetContainerSlot.decode(buf)
        if pkt.window_id == 0 or pkt.window_id == -2:
            try:
                self.inventory.set(pkt.slot, pkt.item)
            except IndexError:
                pass
        self.emit("set_container_slot", pkt)

    def _on_open_screen(self, buf: PacketBuffer) -> None:
        pkt = OpenScreen.decode(buf)
        self.emit("open_screen", pkt)

    def _on_set_held_item(self, buf: PacketBuffer) -> None:
        pkt = SetHeldItem.decode(buf)
        self.inventory.held_slot = pkt.slot
        self.emit("set_held_item", pkt)

    def _on_boss_bar(self, buf: PacketBuffer) -> None:
        pkt = BossBar.decode(buf)
        if pkt.is_remove:
            self.boss_bars.pop(pkt.boss_uuid, None)
        else:
            self.boss_bars[pkt.boss_uuid] = pkt
        self.emit("boss_bar", pkt)

    def _on_title(self, buf: PacketBuffer) -> None:
        pkt = SetTitleText.decode(buf)
        self.emit("title", pkt)

    def _on_subtitle(self, buf: PacketBuffer) -> None:
        pkt = SetSubtitleText.decode(buf)
        self.emit("subtitle", pkt)

    def _on_action_bar(self, buf: PacketBuffer) -> None:
        pkt = SetActionBarText.decode(buf)
        self.emit("action_bar", pkt)

    def _on_title_times(self, buf: PacketBuffer) -> None:
        pkt = SetTitleAnimationTimes.decode(buf)
        self.emit("title_times", pkt)

    def _on_clear_titles(self, buf: PacketBuffer) -> None:
        pkt = ClearTitles.decode(buf)
        self.emit("clear_titles", pkt)

    def _on_player_info_update(self, buf: PacketBuffer) -> None:
        try:
            pkt = PlayerInfoUpdate.decode(buf)
            for entry_data in pkt.players:
                existing = self.tab_list.get(entry_data.player_uuid)
                if existing is None:
                    existing = TabListEntry(player_uuid=entry_data.player_uuid)
                if pkt.actions & ACTION_ADD_PLAYER:
                    existing.name = entry_data.name
                if pkt.actions & ACTION_UPDATE_GAME_MODE:
                    existing.game_mode = entry_data.game_mode
                if pkt.actions & ACTION_UPDATE_LISTED:
                    existing.listed = entry_data.listed
                if pkt.actions & ACTION_UPDATE_LATENCY:
                    existing.latency = entry_data.latency
                if pkt.actions & ACTION_UPDATE_DISPLAY:
                    existing.display_name = entry_data.display_name
                self.tab_list.add_or_update(existing)
            self.emit("player_info_update", pkt)
        except Exception:
            logger.debug("Failed to parse PlayerInfoUpdate", exc_info=True)

    def _on_player_info_remove(self, buf: PacketBuffer) -> None:
        try:
            pkt = PlayerInfoRemove.decode(buf)
            for uid in pkt.uuids:
                self.tab_list.remove(uid)
            self.emit("player_info_remove", pkt)
        except Exception:
            logger.debug("Failed to parse PlayerInfoRemove", exc_info=True)

    def _on_tab_header_footer(self, buf: PacketBuffer) -> None:
        try:
            pkt = SetTabListHeaderAndFooter.decode(buf)
            self.tab_list.header = pkt.header
            self.tab_list.footer = pkt.footer
            self.emit("tab_header_footer", pkt)
        except Exception:
            logger.debug("Failed to parse SetTabListHeaderAndFooter", exc_info=True)

    def _on_player_abilities(self, buf: PacketBuffer) -> None:
        pkt = pp.PlayerAbilities.decode(buf)
        flags = pkt.flags if hasattr(pkt, "flags") else 0
        self.invulnerable = bool(flags & 0x01)
        self.is_flying    = bool(flags & 0x02)
        self.allow_flying = bool(flags & 0x04)
        self.instant_build = bool(flags & 0x08)
        self.fly_speed    = pkt.fly_speed if hasattr(pkt, "fly_speed") else 0.05
        self.walk_speed   = pkt.walk_speed if hasattr(pkt, "walk_speed") else 0.1
        self.emit("player_abilities", pkt)

    def _on_update_objectives(self, buf: PacketBuffer) -> None:
        try:
            pkt = UpdateObjectives.decode(buf)
            self.emit("update_objectives", pkt)
        except Exception:
            logger.debug("Failed to parse UpdateObjectives", exc_info=True)

    def _on_display_objective(self, buf: PacketBuffer) -> None:
        try:
            pkt = DisplayObjective.decode(buf)
            self.emit("display_objective", pkt)
        except Exception:
            logger.debug("Failed to parse DisplayObjective", exc_info=True)

    def _on_update_score(self, buf: PacketBuffer) -> None:
        try:
            pkt = UpdateScore.decode(buf)
            self.emit("update_score", pkt)
        except Exception:
            logger.debug("Failed to parse UpdateScore", exc_info=True)

    def _on_reset_score(self, buf: PacketBuffer) -> None:
        try:
            pkt = ResetScore.decode(buf)
            self.emit("reset_score", pkt)
        except Exception:
            logger.debug("Failed to parse ResetScore", exc_info=True)

    def _on_update_teams(self, buf: PacketBuffer) -> None:
        try:
            pkt = UpdateTeams.decode(buf)
            self.emit("update_teams", pkt)
        except Exception:
            logger.debug("Failed to parse UpdateTeams", exc_info=True)

    def _on_sound(self, buf: PacketBuffer) -> None:
        try:
            pkt = SoundEffect.decode(buf)
            self.emit("sound_effect", pkt)
        except Exception:
            logger.debug("Failed to parse SoundEffect", exc_info=True)

    def _on_entity_sound(self, buf: PacketBuffer) -> None:
        try:
            pkt = EntitySoundEffect.decode(buf)
            self.emit("entity_sound_effect", pkt)
        except Exception:
            logger.debug("Failed to parse EntitySoundEffect", exc_info=True)

    def _on_stop_sound(self, buf: PacketBuffer) -> None:
        try:
            pkt = StopSound.decode(buf)
            self.emit("stop_sound", pkt)
        except Exception:
            logger.debug("Failed to parse StopSound", exc_info=True)

    def _on_death(self, buf: PacketBuffer) -> None:
        self.emit("combat_death", buf.remaining())

    def _on_hurt(self, buf: PacketBuffer) -> None:
        self.emit("hurt_animation", buf.remaining())

    def _on_damage(self, buf: PacketBuffer) -> None:
        self.emit("damage_event", buf.remaining())

    def _on_chunk_batch_start(self, buf: PacketBuffer) -> None:
        pass   # no response needed for batch start

    def _on_chunk_batch_finished(self, buf: PacketBuffer) -> None:
        from mcpycore.utils.datatypes import write_varint as wv
        import struct
        pid = self._sb_id("chunk_batch_received") or 0x08
        chunks_per_tick = struct.pack(">f", 10.0)
        payload = wv(pid) + chunks_per_tick
        self._conn._raw_send(wv(len(payload)) + payload)

    def _on_transfer(self, buf: PacketBuffer) -> None:
        from mcpycore.packets.play.clientbound_1_21 import Transfer
        pkt = Transfer.decode(buf)
        self.emit("transfer", pkt.host, pkt.port)

    # ── Repr ─────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        user = self.profile.username if self.profile else "unauthenticated"
        return (
            f"MinecraftClient({self.host}:{self.port}, "
            f"user={user!r}, version={self.version_name!r})"
        )
