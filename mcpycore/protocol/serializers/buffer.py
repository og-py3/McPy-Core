"""
PacketBuffer — the central abstraction for reading and writing Minecraft protocol data.

All packet encode/decode methods operate exclusively through this class.
Supports both read (wrapping received bytes) and write (building outgoing packets) modes.
"""
from __future__ import annotations

import struct
import uuid
from typing import Any


class BufferUnderrun(Exception):
    """Raised when a read would go past the end of the buffer."""


class PacketBuffer:
    """
    Dual-mode buffer for Minecraft packet serialization.

    Write mode (default)::

        buf = PacketBuffer()
        buf.write_varint(123)
        buf.write_string("hello")
        data: bytes = buf.flush()

    Read mode::

        buf = PacketBuffer(raw_bytes)
        value = buf.read_varint()
        text  = buf.read_string()
    """

    __slots__ = ("_data", "_pos")

    def __init__(self, data: bytes | bytearray | None = None) -> None:
        self._data: bytearray = bytearray(data) if data else bytearray()
        self._pos: int = 0

    # ── Factory helpers ───────────────────────────────────────────────────

    @classmethod
    def from_bytes(cls, data: bytes | bytearray) -> "PacketBuffer":
        buf = cls.__new__(cls)
        buf._data = bytearray(data)
        buf._pos = 0
        return buf

    # ── Low-level read/write ──────────────────────────────────────────────

    def _require(self, n: int) -> None:
        if self._pos + n > len(self._data):
            raise BufferUnderrun(
                f"Need {n} bytes at pos {self._pos}, have {len(self._data) - self._pos}"
            )

    def _read_raw(self, n: int) -> bytes:
        self._require(n)
        chunk = bytes(self._data[self._pos : self._pos + n])
        self._pos += n
        return chunk

    def _write_raw(self, data: bytes | bytearray) -> None:
        self._data.extend(data)

    # ── VarInt / VarLong ──────────────────────────────────────────────────

    def read_varint(self) -> int:
        result = 0
        shift = 0
        while True:
            self._require(1)
            byte = self._data[self._pos]
            self._pos += 1
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7
            if shift >= 35:
                raise ValueError("VarInt too large")
        # sign-extend to 32-bit
        if result & 0x80000000:
            result -= 0x100000000
        return result

    def write_varint(self, value: int) -> None:
        if value < 0:
            value += 0x100000000  # two's complement 32-bit
        out = bytearray()
        while True:
            byte = value & 0x7F
            value >>= 7
            if value:
                out.append(byte | 0x80)
            else:
                out.append(byte)
                break
        self._write_raw(out)

    def read_varlong(self) -> int:
        result = 0
        shift = 0
        while True:
            self._require(1)
            byte = self._data[self._pos]
            self._pos += 1
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7
            if shift >= 70:
                raise ValueError("VarLong too large")
        if result & (1 << 63):
            result -= 1 << 64
        return result

    def write_varlong(self, value: int) -> None:
        if value < 0:
            value += 1 << 64
        out = bytearray()
        while True:
            byte = value & 0x7F
            value >>= 7
            if value:
                out.append(byte | 0x80)
            else:
                out.append(byte)
                break
        self._write_raw(out)

    # ── Numeric primitives ────────────────────────────────────────────────

    def read_bool(self) -> bool:
        return struct.unpack("?", self._read_raw(1))[0]

    def write_bool(self, value: bool) -> None:
        self._write_raw(struct.pack("?", value))

    def read_byte(self) -> int:
        return struct.unpack(">b", self._read_raw(1))[0]

    def write_byte(self, value: int) -> None:
        self._write_raw(struct.pack(">b", value))

    def read_ubyte(self) -> int:
        return struct.unpack(">B", self._read_raw(1))[0]

    def write_ubyte(self, value: int) -> None:
        self._write_raw(struct.pack(">B", value))

    def read_short(self) -> int:
        return struct.unpack(">h", self._read_raw(2))[0]

    def write_short(self, value: int) -> None:
        self._write_raw(struct.pack(">h", value))

    def read_ushort(self) -> int:
        return struct.unpack(">H", self._read_raw(2))[0]

    def write_ushort(self, value: int) -> None:
        self._write_raw(struct.pack(">H", value))

    def read_int(self) -> int:
        return struct.unpack(">i", self._read_raw(4))[0]

    def write_int(self, value: int) -> None:
        self._write_raw(struct.pack(">i", value))

    def read_uint(self) -> int:
        return struct.unpack(">I", self._read_raw(4))[0]

    def write_uint(self, value: int) -> None:
        self._write_raw(struct.pack(">I", value))

    def read_long(self) -> int:
        return struct.unpack(">q", self._read_raw(8))[0]

    def write_long(self, value: int) -> None:
        self._write_raw(struct.pack(">q", value))

    def read_ulong(self) -> int:
        return struct.unpack(">Q", self._read_raw(8))[0]

    def write_ulong(self, value: int) -> None:
        self._write_raw(struct.pack(">Q", value))

    def read_float(self) -> float:
        return struct.unpack(">f", self._read_raw(4))[0]

    def write_float(self, value: float) -> None:
        self._write_raw(struct.pack(">f", value))

    def read_double(self) -> float:
        return struct.unpack(">d", self._read_raw(8))[0]

    def write_double(self, value: float) -> None:
        self._write_raw(struct.pack(">d", value))

    # ── String ────────────────────────────────────────────────────────────

    def read_string(self, max_length: int = 32767) -> str:
        length = self.read_varint()
        if length > max_length * 4:
            raise ValueError(f"String too long: {length} bytes")
        return self._read_raw(length).decode("utf-8")

    def write_string(self, value: str) -> None:
        encoded = value.encode("utf-8")
        self.write_varint(len(encoded))
        self._write_raw(encoded)

    def read_identifier(self) -> str:
        return self.read_string(32767)

    def write_identifier(self, value: str) -> None:
        self.write_string(value)

    # ── UUID ─────────────────────────────────────────────────────────────

    def read_uuid(self) -> uuid.UUID:
        return uuid.UUID(bytes=self._read_raw(16))

    def write_uuid(self, value: uuid.UUID) -> None:
        self._write_raw(value.bytes)

    # ── Byte arrays ──────────────────────────────────────────────────────

    def read_bytes(self, n: int) -> bytes:
        return self._read_raw(n)

    def write_bytes(self, data: bytes | bytearray) -> None:
        self._write_raw(data)

    def read_byte_array(self) -> bytes:
        length = self.read_varint()
        return self._read_raw(length)

    def write_byte_array(self, data: bytes | bytearray) -> None:
        self.write_varint(len(data))
        self._write_raw(data)

    # ── Optional ─────────────────────────────────────────────────────────

    def read_optional_string(self) -> str | None:
        if self.read_bool():
            return self.read_string()
        return None

    def write_optional_string(self, value: str | None) -> None:
        self.write_bool(value is not None)
        if value is not None:
            self.write_string(value)

    def read_optional_uuid(self) -> uuid.UUID | None:
        if self.read_bool():
            return self.read_uuid()
        return None

    def write_optional_uuid(self, value: uuid.UUID | None) -> None:
        self.write_bool(value is not None)
        if value is not None:
            self.write_uuid(value)

    # ── Block position ────────────────────────────────────────────────────

    def read_position(self) -> tuple[int, int, int]:
        val = self.read_ulong()
        # Wire format: ((x & 0x3FFFFFF) << 38) | ((z & 0x3FFFFFF) << 12) | (y & 0xFFF)
        x = (val >> 38) & 0x3FFFFFF
        z = (val >> 12) & 0x3FFFFFF
        y = val & 0xFFF
        # sign extend to signed integers
        if x >= 0x2000000:
            x -= 0x4000000
        if z >= 0x2000000:
            z -= 0x4000000
        if y >= 0x800:
            y -= 0x1000
        return x, y, z

    def write_position(self, x: int, y: int, z: int) -> None:
        val = (
            ((x & 0x3FFFFFF) << 38) |
            ((z & 0x3FFFFFF) << 12) |
            (y & 0xFFF)
        )
        self.write_ulong(val)

    # ── Angle ─────────────────────────────────────────────────────────────

    def read_angle(self) -> float:
        return self.read_ubyte() * 360.0 / 256.0

    def write_angle(self, degrees: float) -> None:
        self.write_ubyte(int(degrees * 256.0 / 360.0) & 0xFF)

    # ── Fixed-point velocity ───────────────────────────────────────────────

    def read_velocity(self) -> float:
        return self.read_short() / 8000.0

    def write_velocity(self, value: float) -> None:
        self.write_short(int(value * 8000.0))

    # ── Remaining data ────────────────────────────────────────────────────

    def remaining(self) -> bytes:
        data = bytes(self._data[self._pos:])
        self._pos = len(self._data)
        return data

    def remaining_bytes(self) -> int:
        return len(self._data) - self._pos

    def peek(self, n: int) -> bytes:
        self._require(n)
        return bytes(self._data[self._pos : self._pos + n])

    # ── Flush / reset ─────────────────────────────────────────────────────

    def flush(self) -> bytes:
        """Return all written bytes and reset."""
        data = bytes(self._data)
        self._data = bytearray()
        self._pos = 0
        return data

    def getvalue(self) -> bytes:
        """Return all written bytes without resetting."""
        return bytes(self._data)

    def reset(self) -> None:
        self._pos = 0

    # ── Dunder ────────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        written = len(self._data)
        read = self._pos
        return f"PacketBuffer(written={written}, pos={read}, remaining={written - read})"
