"""
New serverbound Play packets introduced in Minecraft 1.21.x
"""

from __future__ import annotations

from dataclasses import dataclass
from mcpycore.packets.packet import Packet, PacketBuffer


@dataclass
class CookieResponse(Packet):
    """
    Cookie Response (1.21+) — Client replies to a Cookie Request.
    """
    packet_id = 0x01  # approximate; verify with registry

    key: str = ""
    has_payload: bool = False
    payload: bytes = b""

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_string(self.key)
        buf.write_bool(self.has_payload)
        if self.has_payload:
            buf.write_bytearray(self.payload)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "CookieResponse":
        pkt = cls()
        pkt.key = buf.read_string()
        pkt.has_payload = buf.read_bool()
        if pkt.has_payload:
            pkt.payload = buf.read_bytearray()
        return pkt


@dataclass
class AcknowledgeMessage(Packet):
    """
    Acknowledge Message (1.20.3+) — Client acknowledges chat messages from the server.
    """
    packet_id = 0x03  # approximate

    message_count: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_varint(self.message_count)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "AcknowledgeMessage":
        pkt = cls()
        pkt.message_count = buf.read_varint()
        return pkt


@dataclass
class DebugSampleSubscription(Packet):
    """
    Debug Sample Subscription (1.21+) — Client subscribes to debug samples.
    """
    packet_id = 0x09  # approximate

    sample_type: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_varint(self.sample_type)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "DebugSampleSubscription":
        pkt = cls()
        pkt.sample_type = buf.read_varint()
        return pkt
