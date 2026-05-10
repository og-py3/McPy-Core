"""
Configuration-state packets introduced in 1.20.2 and extended in 1.21.

These are exchanged between LoginAcknowledged and FinishConfiguration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from mcpycore.packets.packet import Packet, PacketBuffer


# ── Clientbound ───────────────────────────────────────────────────────────────

@dataclass
class ConfigDisconnect(Packet):
    """0x02 — Server disconnects client during configuration."""
    packet_id = 0x02

    reason: str = ""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ConfigDisconnect":
        pkt = cls()
        pkt.reason = buf.read_string()
        return pkt


@dataclass
class FinishConfiguration(Packet):
    """0x03 — Server signals end of configuration state."""
    packet_id = 0x03

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "FinishConfiguration":
        return cls()


@dataclass
class RegistryData(Packet):
    """
    0x05 (1.20.2) / 0x07 (1.21) — Server sends registry data (dimensions, biomes, etc.).
    We skip parsing and just store the raw bytes.
    """
    packet_id = 0x05

    raw: bytes = b""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "RegistryData":
        pkt = cls()
        pkt.raw = buf.remaining()
        return pkt


@dataclass
class SelectKnownPacks(Packet):
    """
    0x0D (1.21+) — Server queries which data packs the client knows about.
    Clients respond with the same packet (serverbound).
    """
    packet_id = 0x0D

    packs: list[tuple[str, str, str]] = field(default_factory=list)  # (namespace, id, version)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SelectKnownPacks":
        pkt = cls()
        count = buf.read_varint()
        for _ in range(count):
            ns = buf.read_string()
            pid = buf.read_string()
            ver = buf.read_string()
            pkt.packs.append((ns, pid, ver))
        return pkt


# ── Serverbound ───────────────────────────────────────────────────────────────

@dataclass
class AcknowledgeFinishConfiguration(Packet):
    """0x03 — Client acknowledges end of configuration state."""
    packet_id = 0x03

    def encode(self, buf: PacketBuffer) -> None:
        pass

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "AcknowledgeFinishConfiguration":
        return cls()


@dataclass
class ClientInformationConfig(Packet):
    """0x00 — Client settings sent during configuration state."""
    packet_id = 0x00

    locale: str = "en_us"
    view_distance: int = 10
    chat_mode: int = 0
    chat_colors: bool = True
    displayed_skin_parts: int = 0x7F
    main_hand: int = 1
    enable_text_filtering: bool = False
    allow_listing: bool = True

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_string(self.locale)
        buf.write_byte(self.view_distance)
        buf.write_varint(self.chat_mode)
        buf.write_bool(self.chat_colors)
        buf.write_ubyte(self.displayed_skin_parts)
        buf.write_varint(self.main_hand)
        buf.write_bool(self.enable_text_filtering)
        buf.write_bool(self.allow_listing)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ClientInformationConfig":
        pkt = cls()
        pkt.locale = buf.read_string()
        pkt.view_distance = buf.read_byte()
        pkt.chat_mode = buf.read_varint()
        pkt.chat_colors = buf.read_bool()
        pkt.displayed_skin_parts = buf.read_ubyte()
        pkt.main_hand = buf.read_varint()
        pkt.enable_text_filtering = buf.read_bool()
        pkt.allow_listing = buf.read_bool()
        return pkt


@dataclass
class SelectKnownPacksSB(Packet):
    """0x0E — Client responds to SelectKnownPacks with the packs it knows."""
    packet_id = 0x0E

    packs: list[tuple[str, str, str]] = field(default_factory=list)

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_varint(len(self.packs))
        for ns, pid, ver in self.packs:
            buf.write_string(ns)
            buf.write_string(pid)
            buf.write_string(ver)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SelectKnownPacksSB":
        pkt = cls()
        count = buf.read_varint()
        for _ in range(count):
            ns = buf.read_string()
            pid = buf.read_string()
            ver = buf.read_string()
            pkt.packs.append((ns, pid, ver))
        return pkt
