"""
New clientbound Play packets introduced in Minecraft 1.21.x
"""

from __future__ import annotations

from dataclasses import dataclass, field
from mcpycore.packets.packet import Packet, PacketBuffer


@dataclass
class Transfer(Packet):
    """
    Transfer (1.21+) — Server redirects the client to a different host/port.
    Packet ID varies by version; see versions.py registry.
    """
    packet_id = 0x73   # 1.21.1 value; overridden at runtime via registry

    host: str = ""
    port: int = 25565

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "Transfer":
        pkt = cls()
        pkt.host = buf.read_string()
        pkt.port = buf.read_varint()
        return pkt


@dataclass
class CookieRequest(Packet):
    """
    Cookie Request (1.21+) — Server requests a stored cookie value from the client.
    Packet ID varies by version.
    """
    packet_id = 0x17  # 1.21.1 approximate; check registry

    key: str = ""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "CookieRequest":
        pkt = cls()
        pkt.key = buf.read_string()
        return pkt


@dataclass
class StoreCookie(Packet):
    """
    Store Cookie (1.21+) — Server asks the client to persist a cookie.
    """
    packet_id = 0x6B  # 1.21.1 approximate

    key: str = ""
    payload: bytes = b""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "StoreCookie":
        pkt = cls()
        pkt.key = buf.read_string()
        pkt.payload = buf.read_bytearray()
        return pkt


@dataclass
class ResetScore(Packet):
    """
    Reset Score (1.20.3+) — Remove a score entry for a player.
    """
    packet_id = 0x42  # approximate

    entity_name: str = ""
    objective_name: str | None = None

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ResetScore":
        pkt = cls()
        pkt.entity_name = buf.read_string()
        has_obj = buf.read_bool()
        pkt.objective_name = buf.read_string() if has_obj else None
        return pkt


@dataclass
class ProjectilePower(Packet):
    """
    Projectile Power (1.21+) — Sets the power/speed of a fired projectile entity.
    """
    packet_id = 0x02  # approximate

    entity_id: int = 0
    power_x: float = 0.0
    power_y: float = 0.0
    power_z: float = 0.0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ProjectilePower":
        pkt = cls()
        pkt.entity_id = buf.read_varint()
        pkt.power_x = buf.read_double()
        pkt.power_y = buf.read_double()
        pkt.power_z = buf.read_double()
        return pkt


@dataclass
class DebugSample(Packet):
    """
    Debug Sample (1.21+) — Server-side performance debug data.
    Only sent when the client is in debug mode.
    """
    packet_id = 0x1E  # approximate

    sample: list[int] = field(default_factory=list)
    sample_type: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "DebugSample":
        pkt = cls()
        count = buf.read_varint()
        pkt.sample = [buf.read_long() for _ in range(count)]
        pkt.sample_type = buf.read_varint()
        return pkt
