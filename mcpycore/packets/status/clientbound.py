"""Server → Client packets during the Status state."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from mcpycore.packets.packet import Packet, PacketBuffer


@dataclass
class StatusResponse(Packet):
    """0x00 — Server responds with JSON server status."""

    packet_id = 0x00

    raw_json: str = "{}"

    @property
    def data(self) -> dict:
        return json.loads(self.raw_json)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "StatusResponse":
        pkt = cls()
        pkt.raw_json = buf.read_string()
        return pkt


@dataclass
class PingResponse(Packet):
    """0x01 — Server echoes the ping payload."""

    packet_id = 0x01

    payload: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "PingResponse":
        pkt = cls()
        pkt.payload = buf.read_long()
        return pkt
