"""Client → Server packets during the Status state."""

from __future__ import annotations

from dataclasses import dataclass

from mcpycore.packets.packet import Packet, PacketBuffer


@dataclass
class StatusRequest(Packet):
    """0x00 — Client requests the server status JSON."""

    packet_id = 0x00

    def encode(self, buf: PacketBuffer) -> None:
        pass

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "StatusRequest":
        return cls()


@dataclass
class PingRequest(Packet):
    """0x01 — Client sends a ping with a timestamp payload."""

    packet_id = 0x01

    payload: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_long(self.payload)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "PingRequest":
        pkt = cls()
        pkt.payload = buf.read_long()
        return pkt
