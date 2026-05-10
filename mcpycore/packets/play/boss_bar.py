"""Boss bar packet (clientbound play)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from mcpycore.packets.packet import Packet, PacketBuffer

# Action IDs
ACTION_ADD           = 0
ACTION_REMOVE        = 1
ACTION_UPDATE_HEALTH = 2
ACTION_UPDATE_TITLE  = 3
ACTION_UPDATE_STYLE  = 4
ACTION_UPDATE_FLAGS  = 5

# Color IDs
COLOR_PINK   = 0
COLOR_BLUE   = 1
COLOR_RED    = 2
COLOR_GREEN  = 3
COLOR_YELLOW = 4
COLOR_PURPLE = 5
COLOR_WHITE  = 6

# Division IDs
DIV_NONE = 0
DIV_6    = 1
DIV_10   = 2
DIV_12   = 3
DIV_20   = 4


@dataclass
class BossBar(Packet):
    """0x0A — Boss bar update (add, remove, update health/title/style/flags)."""
    packet_id = 0x0A

    boss_uuid: uuid.UUID = field(default_factory=uuid.uuid4)
    action: int = ACTION_ADD

    # ADD fields
    title: str = ""
    health: float = 1.0
    color: int = COLOR_PURPLE
    division: int = DIV_NONE
    flags: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "BossBar":
        pkt = cls()
        pkt.boss_uuid = buf.read_uuid()
        pkt.action = buf.read_varint()

        if pkt.action == ACTION_ADD:
            pkt.title  = buf.read_string()
            pkt.health = buf.read_float()
            pkt.color  = buf.read_varint()
            pkt.division = buf.read_varint()
            pkt.flags  = buf.read_ubyte()

        elif pkt.action == ACTION_UPDATE_HEALTH:
            pkt.health = buf.read_float()

        elif pkt.action == ACTION_UPDATE_TITLE:
            pkt.title = buf.read_string()

        elif pkt.action == ACTION_UPDATE_STYLE:
            pkt.color    = buf.read_varint()
            pkt.division = buf.read_varint()

        elif pkt.action == ACTION_UPDATE_FLAGS:
            pkt.flags = buf.read_ubyte()

        # ACTION_REMOVE has no extra fields
        return pkt

    @property
    def is_add(self) -> bool:
        return self.action == ACTION_ADD

    @property
    def is_remove(self) -> bool:
        return self.action == ACTION_REMOVE
