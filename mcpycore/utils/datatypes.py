"""
Low-level Minecraft protocol data type read/write helpers.

All read_* functions take a socket or bytes-like and advance position.
All write_* functions return bytes.
"""

from __future__ import annotations

import struct
import socket
import uuid
from typing import BinaryIO


# ─── VarInt / VarLong ────────────────────────────────────────────────────────

def read_varint(sock: socket.socket) -> int:
    """Read a VarInt from the socket (up to 5 bytes)."""
    result = 0
    for shift in range(0, 35, 7):
        byte = _read_exactly(sock, 1)[0]
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
    else:
        raise ValueError("VarInt is too big (> 5 bytes)")
    # Sign-extend to 32-bit
    if result & 0x80000000:
        result -= 0x100000000
    return result


def read_varlong(sock: socket.socket) -> int:
    """Read a VarLong from the socket (up to 10 bytes)."""
    result = 0
    for shift in range(0, 70, 7):
        byte = _read_exactly(sock, 1)[0]
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
    else:
        raise ValueError("VarLong is too big (> 10 bytes)")
    if result & (1 << 63):
        result -= 1 << 64
    return result


def varint_from_bytes(data: bytes, offset: int = 0) -> tuple[int, int]:
    """
    Read a VarInt from a bytes buffer starting at *offset*.
    Returns (value, bytes_consumed).
    """
    result = 0
    for i in range(5):
        if offset + i >= len(data):
            raise ValueError("Buffer too short for VarInt")
        byte = data[offset + i]
        result |= (byte & 0x7F) << (7 * i)
        if not (byte & 0x80):
            return result if result < 0x80000000 else result - 0x100000000, i + 1
    raise ValueError("VarInt is too big")


def write_varint(value: int) -> bytes:
    """Encode an integer as a VarInt."""
    value &= 0xFFFFFFFF
    out = bytearray()
    while True:
        if value & ~0x7F:
            out.append((value & 0x7F) | 0x80)
            value >>= 7
        else:
            out.append(value)
            break
    return bytes(out)


def write_varlong(value: int) -> bytes:
    """Encode an integer as a VarLong."""
    value &= 0xFFFFFFFFFFFFFFFF
    out = bytearray()
    while True:
        if value & ~0x7F:
            out.append((value & 0x7F) | 0x80)
            value >>= 7
        else:
            out.append(value)
            break
    return bytes(out)


# ─── Strings ─────────────────────────────────────────────────────────────────

def read_string(sock: socket.socket) -> str:
    """Read a UTF-8 string prefixed by its VarInt byte length."""
    length = read_varint(sock)
    raw = _read_exactly(sock, length)
    return raw.decode("utf-8")


def write_string(value: str) -> bytes:
    """Encode a string as VarInt-length-prefixed UTF-8."""
    encoded = value.encode("utf-8")
    return write_varint(len(encoded)) + encoded


# ─── Fixed-width primitives ───────────────────────────────────────────────────

def read_bool(sock: socket.socket) -> bool:
    return bool(_read_exactly(sock, 1)[0])


def write_bool(value: bool) -> bytes:
    return b"\x01" if value else b"\x00"


def read_byte(sock: socket.socket) -> int:
    return struct.unpack(">b", _read_exactly(sock, 1))[0]


def write_byte(value: int) -> bytes:
    return struct.pack(">b", value)


def read_ubyte(sock: socket.socket) -> int:
    return _read_exactly(sock, 1)[0]


def write_ubyte(value: int) -> bytes:
    return struct.pack(">B", value)


def read_short(sock: socket.socket) -> int:
    return struct.unpack(">h", _read_exactly(sock, 2))[0]


def write_short(value: int) -> bytes:
    return struct.pack(">h", value)


def read_ushort(sock: socket.socket) -> int:
    return struct.unpack(">H", _read_exactly(sock, 2))[0]


def write_ushort(value: int) -> bytes:
    return struct.pack(">H", value)


def read_int(sock: socket.socket) -> int:
    return struct.unpack(">i", _read_exactly(sock, 4))[0]


def write_int(value: int) -> bytes:
    return struct.pack(">i", value)


def read_long(sock: socket.socket) -> int:
    return struct.unpack(">q", _read_exactly(sock, 8))[0]


def write_long(value: int) -> bytes:
    return struct.pack(">q", value)


def read_float(sock: socket.socket) -> float:
    return struct.unpack(">f", _read_exactly(sock, 4))[0]


def write_float(value: float) -> bytes:
    return struct.pack(">f", value)


def read_double(sock: socket.socket) -> float:
    return struct.unpack(">d", _read_exactly(sock, 8))[0]


def write_double(value: float) -> bytes:
    return struct.pack(">d", value)


# ─── UUID ─────────────────────────────────────────────────────────────────────

def read_uuid(sock: socket.socket) -> uuid.UUID:
    raw = _read_exactly(sock, 16)
    return uuid.UUID(bytes=raw)


def write_uuid(value: uuid.UUID) -> bytes:
    return value.bytes


# ─── Position (packed 64-bit block position) ─────────────────────────────────

def read_position(sock: socket.socket) -> tuple[int, int, int]:
    val = struct.unpack(">Q", _read_exactly(sock, 8))[0]
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


def write_position(x: int, y: int, z: int) -> bytes:
    val = ((x & 0x3FFFFFF) << 38) | ((z & 0x3FFFFFF) << 12) | (y & 0xFFF)
    return struct.pack(">Q", val)


# ─── Byte arrays ─────────────────────────────────────────────────────────────

def read_bytearray(sock: socket.socket) -> bytes:
    """Read a VarInt-prefixed byte array."""
    length = read_varint(sock)
    return _read_exactly(sock, length)


def write_bytearray(data: bytes) -> bytes:
    return write_varint(len(data)) + data


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _read_exactly(sock: socket.socket, n: int) -> bytes:
    """Read exactly n bytes from the socket, blocking until available."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise EOFError("Connection closed by server")
        buf += chunk
    return buf
