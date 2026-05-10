"""Tests for VarInt, VarLong, and other primitive read/write helpers."""

import struct
import socket
import io
import pytest
from unittest.mock import MagicMock, patch

from mcpycore.utils.datatypes import (
    write_varint, write_varlong,
    write_string, write_bool,
    write_byte, write_ubyte,
    write_short, write_ushort,
    write_int, write_long,
    write_float, write_double,
    write_position,
    varint_from_bytes,
)
from mcpycore.packets.packet import PacketBuffer


# ── VarInt round-trip via PacketBuffer ────────────────────────────────────────

@pytest.mark.parametrize("value", [
    0, 1, 127, 128, 255, 2047, 2048, 2097151, 2147483647, -1, -2147483648,
])
def test_varint_roundtrip(value):
    encoded = write_varint(value)
    result, consumed = varint_from_bytes(encoded)
    assert result == value
    assert consumed == len(encoded)


@pytest.mark.parametrize("value,expected_bytes", [
    (0, b"\x00"),
    (1, b"\x01"),
    (127, b"\x7f"),
    (128, b"\x80\x01"),
    (255, b"\xff\x01"),
    (25565, b"\xdd\xc7\x01"),
    (2147483647, b"\xff\xff\xff\xff\x07"),
    (-1, b"\xff\xff\xff\xff\x0f"),
    (-2147483648, b"\x80\x80\x80\x80\x08"),
])
def test_varint_encoding(value, expected_bytes):
    assert write_varint(value) == expected_bytes


# ── PacketBuffer read/write helpers ──────────────────────────────────────────

def test_packet_buffer_bool():
    buf = PacketBuffer()
    buf.write_bool(True)
    buf.write_bool(False)
    buf.seek(0)
    assert buf.read_bool() is True
    assert buf.read_bool() is False


def test_packet_buffer_string():
    buf = PacketBuffer()
    buf.write_string("Hello, Minecraft!")
    buf.seek(0)
    assert buf.read_string() == "Hello, Minecraft!"


def test_packet_buffer_int():
    buf = PacketBuffer()
    buf.write_int(123456)
    buf.write_int(-42)
    buf.seek(0)
    assert buf.read_int() == 123456
    assert buf.read_int() == -42


def test_packet_buffer_long():
    buf = PacketBuffer()
    buf.write_long(9999999999999)
    buf.seek(0)
    assert buf.read_long() == 9999999999999


def test_packet_buffer_float():
    buf = PacketBuffer()
    buf.write_float(3.14)
    buf.seek(0)
    val = buf.read_float()
    assert abs(val - 3.14) < 1e-5


def test_packet_buffer_double():
    buf = PacketBuffer()
    buf.write_double(3.141592653589793)
    buf.seek(0)
    assert buf.read_double() == pytest.approx(3.141592653589793)


def test_packet_buffer_varint():
    buf = PacketBuffer()
    for v in [0, 1, 128, 2097151, -1, -2147483648]:
        buf.write_varint(v)
    buf.seek(0)
    for expected in [0, 1, 128, 2097151, -1, -2147483648]:
        assert buf.read_varint() == expected


# ── Block position ────────────────────────────────────────────────────────────

def test_position_roundtrip():
    buf = PacketBuffer()
    buf.write_position(100, 64, -200)
    buf.seek(0)
    x, y, z = buf.read_position()
    assert (x, y, z) == (100, 64, -200)


def test_position_negative_xz():
    buf = PacketBuffer()
    buf.write_position(-1000000, 0, -1000000)
    buf.seek(0)
    x, y, z = buf.read_position()
    assert (x, y, z) == (-1000000, 0, -1000000)


# ── UUID ─────────────────────────────────────────────────────────────────────

def test_uuid_roundtrip():
    import uuid
    original = uuid.uuid4()
    buf = PacketBuffer()
    buf.write_uuid(original)
    buf.seek(0)
    result = buf.read_uuid()
    assert result == original


# ── Byte array ────────────────────────────────────────────────────────────────

def test_bytearray_roundtrip():
    data = b"\xDE\xAD\xBE\xEF" * 10
    buf = PacketBuffer()
    buf.write_bytearray(data)
    buf.seek(0)
    result = buf.read_bytearray()
    assert result == data
