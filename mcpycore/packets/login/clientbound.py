"""Server → Client packets during the Login state."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from mcpycore.packets.packet import Packet, PacketBuffer


@dataclass
class LoginDisconnect(Packet):
    """0x00 — Server kicks the client with a JSON reason."""

    packet_id = 0x00

    reason: str = ""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "LoginDisconnect":
        pkt = cls()
        pkt.reason = buf.read_string()
        return pkt


@dataclass
class EncryptionRequest(Packet):
    """0x01 — Server sends its public key and verify token."""

    packet_id = 0x01

    server_id: str = ""
    public_key: bytes = b""
    verify_token: bytes = b""
    should_authenticate: bool = True

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "EncryptionRequest":
        pkt = cls()
        pkt.server_id = buf.read_string()
        pkt.public_key = buf.read_bytearray()
        pkt.verify_token = buf.read_bytearray()
        pkt.should_authenticate = buf.read_bool()
        return pkt


@dataclass
class LoginSuccess(Packet):
    """0x02 — Server confirms login, transitions to Play state."""

    packet_id = 0x02

    player_uuid: uuid.UUID = field(default_factory=uuid.uuid4)
    username: str = ""
    properties: list[dict] = field(default_factory=list)
    strict_error_handling: bool = False

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "LoginSuccess":
        pkt = cls()
        pkt.player_uuid = buf.read_uuid()
        pkt.username = buf.read_string()
        num_props = buf.read_varint()
        for _ in range(num_props):
            name = buf.read_string()
            value = buf.read_string()
            is_signed = buf.read_bool()
            signature = buf.read_string() if is_signed else None
            pkt.properties.append({"name": name, "value": value, "signature": signature})
        pkt.strict_error_handling = buf.read_bool()
        return pkt


@dataclass
class SetCompression(Packet):
    """0x03 — Server enables zlib compression for subsequent packets."""

    packet_id = 0x03

    threshold: int = -1

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SetCompression":
        pkt = cls()
        pkt.threshold = buf.read_varint()
        return pkt


@dataclass
class LoginPluginRequest(Packet):
    """0x04 — Server requests a plugin channel message."""

    packet_id = 0x04

    message_id: int = 0
    channel: str = ""
    data: bytes = b""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "LoginPluginRequest":
        pkt = cls()
        pkt.message_id = buf.read_varint()
        pkt.channel = buf.read_string()
        pkt.data = buf.remaining()
        return pkt
