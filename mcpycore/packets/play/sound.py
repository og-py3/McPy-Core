"""Sound-related packets (clientbound play)."""

from __future__ import annotations

from dataclasses import dataclass

from mcpycore.packets.packet import Packet, PacketBuffer

# Sound categories
CATEGORY_MASTER         = 0
CATEGORY_MUSIC          = 1
CATEGORY_RECORD         = 2
CATEGORY_WEATHER        = 3
CATEGORY_BLOCK          = 4
CATEGORY_HOSTILE        = 5
CATEGORY_NEUTRAL        = 6
CATEGORY_PLAYERS        = 7
CATEGORY_AMBIENT        = 8
CATEGORY_VOICE          = 9


@dataclass
class SoundEffect(Packet):
    """0x60 — Play a named sound effect at a world position."""
    packet_id = 0x60

    sound_id: int = 0
    sound_name: str | None = None   # only if sound_id == 0 (custom)
    has_fixed_range: bool = False
    fixed_range: float | None = None
    category: int = CATEGORY_MASTER
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    volume: float = 1.0
    pitch: float = 1.0
    seed: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SoundEffect":
        pkt = cls()
        pkt.sound_id = buf.read_varint()
        if pkt.sound_id == 0:
            pkt.sound_name = buf.read_string()
            pkt.has_fixed_range = buf.read_bool()
            if pkt.has_fixed_range:
                pkt.fixed_range = buf.read_float()
        pkt.category = buf.read_varint()
        pkt.x = buf.read_int() / 8.0
        pkt.y = buf.read_int() / 8.0
        pkt.z = buf.read_int() / 8.0
        pkt.volume = buf.read_float()
        pkt.pitch  = buf.read_float()
        pkt.seed   = buf.read_long()
        return pkt


@dataclass
class EntitySoundEffect(Packet):
    """0x5F — Play a named sound effect on an entity."""
    packet_id = 0x5F

    sound_id: int = 0
    sound_name: str | None = None
    category: int = CATEGORY_MASTER
    entity_id: int = 0
    volume: float = 1.0
    pitch: float = 1.0
    seed: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "EntitySoundEffect":
        pkt = cls()
        pkt.sound_id = buf.read_varint()
        if pkt.sound_id == 0:
            pkt.sound_name = buf.read_string()
            buf.read_bool()   # has_fixed_range
        pkt.category   = buf.read_varint()
        pkt.entity_id  = buf.read_varint()
        pkt.volume     = buf.read_float()
        pkt.pitch      = buf.read_float()
        pkt.seed       = buf.read_long()
        return pkt


@dataclass
class StopSound(Packet):
    """0x62 — Stop a currently playing sound."""
    packet_id = 0x62

    flags: int = 0
    category: int | None = None
    sound_name: str | None = None

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "StopSound":
        pkt = cls()
        pkt.flags = buf.read_byte()
        if pkt.flags & 0x1:
            pkt.category = buf.read_varint()
        if pkt.flags & 0x2:
            pkt.sound_name = buf.read_string()
        return pkt
