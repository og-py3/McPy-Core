"""Client → Server packets during the Login state."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from mcpycore.packets.packet import Packet, PacketBuffer


@dataclass
class LoginStart(Packet):
    """0x00 — Client begins login with username and UUID."""

    packet_id = 0x00

    username: str = ""
    player_uuid: uuid.UUID = field(default_factory=uuid.uuid4)

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_string(self.username)
        buf.write_uuid(self.player_uuid)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "LoginStart":
        pkt = cls()
        pkt.username = buf.read_string()
        pkt.player_uuid = buf.read_uuid()
        return pkt


@dataclass
class EncryptionResponse(Packet):
    """0x01 — Client replies with encrypted shared secret and verify token."""

    packet_id = 0x01

    shared_secret: bytes = b""
    verify_token: bytes = b""

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_bytearray(self.shared_secret)
        buf.write_bytearray(self.verify_token)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "EncryptionResponse":
        pkt = cls()
        pkt.shared_secret = buf.read_bytearray()
        pkt.verify_token = buf.read_bytearray()
        return pkt


@dataclass
class LoginPluginResponse(Packet):
    """0x02 — Client responds to a plugin channel request."""

    packet_id = 0x02

    message_id: int = 0
    data: bytes | None = None

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_varint(self.message_id)
        if self.data is not None:
            buf.write_bool(True)
            buf.write_bytes(self.data)
        else:
            buf.write_bool(False)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "LoginPluginResponse":
        pkt = cls()
        pkt.message_id = buf.read_varint()
        has_data = buf.read_bool()
        pkt.data = buf.remaining() if has_data else None
        return pkt


@dataclass
class LoginAcknowledged(Packet):
    """0x03 — Client acknowledges LoginSuccess, transitions to Configuration state."""

    packet_id = 0x03

    def encode(self, buf: PacketBuffer) -> None:
        pass

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "LoginAcknowledged":
        return cls()
