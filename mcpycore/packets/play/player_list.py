"""Player list (tab list) packets."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from mcpycore.packets.packet import Packet, PacketBuffer

# PlayerInfoUpdate action flags (bitmask)
ACTION_ADD_PLAYER        = 0x01
ACTION_INITIALIZE_CHAT   = 0x02
ACTION_UPDATE_GAME_MODE  = 0x04
ACTION_UPDATE_LISTED     = 0x08
ACTION_UPDATE_LATENCY    = 0x10
ACTION_UPDATE_DISPLAY    = 0x20

GAME_MODE_SURVIVAL  = 0
GAME_MODE_CREATIVE  = 1
GAME_MODE_ADVENTURE = 2
GAME_MODE_SPECTATOR = 3


@dataclass
class PlayerEntry:
    """Represents one player in the tab list."""
    player_uuid: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    properties: list[dict] = field(default_factory=list)
    game_mode: int = GAME_MODE_SURVIVAL
    listed: bool = True
    latency: int = 0
    display_name: str | None = None


@dataclass
class PlayerInfoUpdate(Packet):
    """
    0x3C (1.20.4) / varies — Update the player tab list.
    Replaces the old PlayerInfo packet from older versions.
    """
    packet_id = 0x3C

    actions: int = 0
    players: list[PlayerEntry] = field(default_factory=list)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "PlayerInfoUpdate":
        pkt = cls()
        pkt.actions = buf.read_byte()
        count = buf.read_varint()

        for _ in range(count):
            entry = PlayerEntry()
            entry.player_uuid = buf.read_uuid()

            if pkt.actions & ACTION_ADD_PLAYER:
                entry.name = buf.read_string()
                num_props = buf.read_varint()
                for _ in range(num_props):
                    prop_name = buf.read_string()
                    prop_val  = buf.read_string()
                    signed    = buf.read_bool()
                    sig       = buf.read_string() if signed else None
                    entry.properties.append({"name": prop_name, "value": prop_val, "signature": sig})

            if pkt.actions & ACTION_INITIALIZE_CHAT:
                has_sig = buf.read_bool()
                if has_sig:
                    buf.read_uuid()     # chat session uuid
                    buf.read_long()     # expires_at
                    buf.read_bytearray()  # public_key
                    buf.read_bytearray()  # key_signature

            if pkt.actions & ACTION_UPDATE_GAME_MODE:
                entry.game_mode = buf.read_varint()

            if pkt.actions & ACTION_UPDATE_LISTED:
                entry.listed = buf.read_bool()

            if pkt.actions & ACTION_UPDATE_LATENCY:
                entry.latency = buf.read_varint()

            if pkt.actions & ACTION_UPDATE_DISPLAY:
                has_display = buf.read_bool()
                if has_display:
                    entry.display_name = buf.read_string()

            pkt.players.append(entry)

        return pkt


@dataclass
class PlayerInfoRemove(Packet):
    """0x3B (1.20.4) — Remove players from the tab list."""
    packet_id = 0x3B

    uuids: list[uuid.UUID] = field(default_factory=list)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "PlayerInfoRemove":
        pkt = cls()
        count = buf.read_varint()
        for _ in range(count):
            pkt.uuids.append(buf.read_uuid())
        return pkt


@dataclass
class SetTabListHeaderAndFooter(Packet):
    """0x65 — Update the tab list header/footer text."""
    packet_id = 0x65

    header: str = ""
    footer: str = ""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SetTabListHeaderAndFooter":
        pkt = cls()
        pkt.header = buf.read_string()
        pkt.footer = buf.read_string()
        return pkt
