"""Base Packet class and PacketBuffer for building/parsing raw packet data."""

from __future__ import annotations

import io
import struct
import uuid
from typing import Any

from mcpycore.utils.datatypes import (
    write_varint, write_varlong,
    write_string, write_bool,
    write_byte, write_ubyte,
    write_short, write_ushort,
    write_int, write_long,
    write_float, write_double,
    write_uuid, write_position,
    write_bytearray,
    read_varint, read_varlong,
    read_string, read_bool,
    read_byte, read_ubyte,
    read_short, read_ushort,
    read_int, read_long,
    read_float, read_double,
    read_uuid, read_position,
    read_bytearray,
    varint_from_bytes,
)


class PacketBuffer:
    """
    A helper buffer for building the payload of a packet before sending,
    or for reading bytes from a received packet payload.
    """

    def __init__(self, data: bytes = b"") -> None:
        self._buf = io.BytesIO(data)

    # ── Write helpers ─────────────────────────────────────────────────────────

    def write_varint(self, value: int) -> None:
        self._buf.write(write_varint(value))

    def write_varlong(self, value: int) -> None:
        self._buf.write(write_varlong(value))

    def write_string(self, value: str) -> None:
        self._buf.write(write_string(value))

    def write_bool(self, value: bool) -> None:
        self._buf.write(write_bool(value))

    def write_byte(self, value: int) -> None:
        self._buf.write(write_byte(value))

    def write_ubyte(self, value: int) -> None:
        self._buf.write(write_ubyte(value))

    def write_short(self, value: int) -> None:
        self._buf.write(write_short(value))

    def write_ushort(self, value: int) -> None:
        self._buf.write(write_ushort(value))

    def write_int(self, value: int) -> None:
        self._buf.write(write_int(value))

    def write_long(self, value: int) -> None:
        self._buf.write(write_long(value))

    def write_float(self, value: float) -> None:
        self._buf.write(write_float(value))

    def write_double(self, value: float) -> None:
        self._buf.write(write_double(value))

    def write_uuid(self, value: uuid.UUID) -> None:
        self._buf.write(write_uuid(value))

    def write_position(self, x: int, y: int, z: int) -> None:
        self._buf.write(write_position(x, y, z))

    def write_bytes(self, data: bytes) -> None:
        self._buf.write(data)

    def write_bytearray(self, data: bytes) -> None:
        self._buf.write(write_bytearray(data))

    # ── Read helpers ──────────────────────────────────────────────────────────

    def read_varint(self) -> int:
        result = 0
        for shift in range(0, 35, 7):
            raw = self._buf.read(1)
            if not raw:
                raise EOFError("Buffer exhausted reading VarInt")
            byte = raw[0]
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
        if result & 0x80000000:
            result -= 0x100000000
        return result

    def read_varlong(self) -> int:
        result = 0
        for shift in range(0, 70, 7):
            raw = self._buf.read(1)
            if not raw:
                raise EOFError("Buffer exhausted reading VarLong")
            byte = raw[0]
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
        if result & (1 << 63):
            result -= 1 << 64
        return result

    def read_string(self) -> str:
        length = self.read_varint()
        return self._buf.read(length).decode("utf-8")

    def read_bool(self) -> bool:
        return bool(self._buf.read(1)[0])

    def read_byte(self) -> int:
        return struct.unpack(">b", self._buf.read(1))[0]

    def read_ubyte(self) -> int:
        return self._buf.read(1)[0]

    def read_short(self) -> int:
        return struct.unpack(">h", self._buf.read(2))[0]

    def read_ushort(self) -> int:
        return struct.unpack(">H", self._buf.read(2))[0]

    def read_int(self) -> int:
        return struct.unpack(">i", self._buf.read(4))[0]

    def read_long(self) -> int:
        return struct.unpack(">q", self._buf.read(8))[0]

    def read_float(self) -> float:
        return struct.unpack(">f", self._buf.read(4))[0]

    def read_double(self) -> float:
        return struct.unpack(">d", self._buf.read(8))[0]

    def read_uuid(self) -> uuid.UUID:
        return uuid.UUID(bytes=self._buf.read(16))

    def read_position(self) -> tuple[int, int, int]:
        val = struct.unpack(">Q", self._buf.read(8))[0]
        x = (val >> 38) & 0x3FFFFFF
        z = (val >> 12) & 0x3FFFFFF
        y = val & 0xFFF
        if x >= 2**25:
            x -= 2**26
        if z >= 2**25:
            z -= 2**26
        if y >= 2**11:
            y -= 2**12
        return int(x), int(y), int(z)

    def read_bytes(self, n: int) -> bytes:
        return self._buf.read(n)

    def read_bytearray(self) -> bytes:
        length = self.read_varint()
        return self._buf.read(length)

    def remaining(self) -> bytes:
        return self._buf.read()

    def getvalue(self) -> bytes:
        return self._buf.getvalue()

    def tell(self) -> int:
        return self._buf.tell()

    def seek(self, pos: int) -> None:
        self._buf.seek(pos)


class Packet:
    """
    Base class for all Minecraft protocol packets.

    Subclasses must define:
        packet_id: int   — the numeric packet ID (server- or client-bound)

    To send a packet, call `to_bytes()` which returns the fully framed
    (length-prefixed, id-prefixed) bytes ready to be written to the socket.

    To receive a packet, call `Packet.from_buffer(buf)` on a PacketBuffer
    whose position is past the packet-id byte.
    """

    packet_id: int = -1

    def encode(self, buf: PacketBuffer) -> None:
        """Write packet fields into *buf*. Override in subclasses."""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "Packet":
        """Read packet fields from *buf* and return a new instance."""
        raise NotImplementedError

    def to_bytes(self) -> bytes:
        """Return the fully framed packet bytes (length + id + payload)."""
        payload_buf = PacketBuffer()
        payload_buf.write_varint(self.packet_id)
        self.encode(payload_buf)
        payload = payload_buf.getvalue()
        return write_varint(len(payload)) + payload

    def __repr__(self) -> str:
        fields = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        return f"{self.__class__.__name__}({fields})"
