"""Tests for PacketBuffer — all read/write primitives."""
from __future__ import annotations

import struct
import uuid
import pytest

from mcpycore.protocol.serializers.buffer import PacketBuffer, BufferUnderrun


# ── VarInt ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value,expected_bytes", [
    (0,           b"\x00"),
    (1,           b"\x01"),
    (127,         b"\x7f"),
    (128,         b"\x80\x01"),
    (255,         b"\xff\x01"),
    (25565,       b"\xdd\xc7\x01"),
    (2097151,     b"\xff\xff\x7f"),
    (2147483647,  b"\xff\xff\xff\xff\x07"),
    (-1,          b"\xff\xff\xff\xff\x0f"),
    (-2147483648, b"\x80\x80\x80\x80\x08"),
])
def test_varint_encoding(value, expected_bytes):
    buf = PacketBuffer()
    buf.write_varint(value)
    assert buf.getvalue() == expected_bytes


@pytest.mark.parametrize("value", [
    0, 1, 127, 128, 255, 300, 2097151, 2147483647, -1, -128, -2147483648,
])
def test_varint_roundtrip(value):
    buf = PacketBuffer()
    buf.write_varint(value)
    buf2 = PacketBuffer.from_bytes(buf.getvalue())
    assert buf2.read_varint() == value


def test_varint_max_size_rejected():
    # 6 continuation bytes = too large
    bad = bytes([0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x01])
    buf = PacketBuffer.from_bytes(bad)
    with pytest.raises(ValueError, match="VarInt too large"):
        buf.read_varint()


# ── VarLong ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value", [
    0, 1, 127, 2**40, 2**63 - 1, -1, -(2**63),
])
def test_varlong_roundtrip(value):
    buf = PacketBuffer()
    buf.write_varlong(value)
    buf2 = PacketBuffer.from_bytes(buf.getvalue())
    assert buf2.read_varlong() == value


# ── Numerics ──────────────────────────────────────────────────────────────────

def test_bool_true():
    buf = PacketBuffer()
    buf.write_bool(True)
    assert PacketBuffer.from_bytes(buf.getvalue()).read_bool() is True


def test_bool_false():
    buf = PacketBuffer()
    buf.write_bool(False)
    assert PacketBuffer.from_bytes(buf.getvalue()).read_bool() is False


@pytest.mark.parametrize("v", [-128, -1, 0, 1, 127])
def test_byte_roundtrip(v):
    buf = PacketBuffer()
    buf.write_byte(v)
    assert PacketBuffer.from_bytes(buf.getvalue()).read_byte() == v


@pytest.mark.parametrize("v", [0, 1, 127, 255])
def test_ubyte_roundtrip(v):
    buf = PacketBuffer()
    buf.write_ubyte(v)
    assert PacketBuffer.from_bytes(buf.getvalue()).read_ubyte() == v


@pytest.mark.parametrize("v", [-32768, -1, 0, 1, 32767])
def test_short_roundtrip(v):
    buf = PacketBuffer()
    buf.write_short(v)
    assert PacketBuffer.from_bytes(buf.getvalue()).read_short() == v


@pytest.mark.parametrize("v", [-2**31, -1, 0, 1, 2**31 - 1])
def test_int_roundtrip(v):
    buf = PacketBuffer()
    buf.write_int(v)
    assert PacketBuffer.from_bytes(buf.getvalue()).read_int() == v


@pytest.mark.parametrize("v", [-(2**63), -1, 0, 1, 2**63 - 1])
def test_long_roundtrip(v):
    buf = PacketBuffer()
    buf.write_long(v)
    assert PacketBuffer.from_bytes(buf.getvalue()).read_long() == v


def test_float_roundtrip():
    buf = PacketBuffer()
    buf.write_float(3.14)
    result = PacketBuffer.from_bytes(buf.getvalue()).read_float()
    assert abs(result - 3.14) < 1e-5


def test_double_roundtrip():
    buf = PacketBuffer()
    buf.write_double(3.141592653589793)
    result = PacketBuffer.from_bytes(buf.getvalue()).read_double()
    assert abs(result - 3.141592653589793) < 1e-12


# ── String ────────────────────────────────────────────────────────────────────

def test_string_ascii():
    buf = PacketBuffer()
    buf.write_string("hello")
    assert PacketBuffer.from_bytes(buf.getvalue()).read_string() == "hello"


def test_string_unicode():
    buf = PacketBuffer()
    buf.write_string("こんにちは世界")
    assert PacketBuffer.from_bytes(buf.getvalue()).read_string() == "こんにちは世界"


def test_string_empty():
    buf = PacketBuffer()
    buf.write_string("")
    assert PacketBuffer.from_bytes(buf.getvalue()).read_string() == ""


def test_string_max_length_exceeded():
    long_str = "A" * 50000
    buf = PacketBuffer()
    buf.write_string(long_str)
    buf2 = PacketBuffer.from_bytes(buf.getvalue())
    with pytest.raises(ValueError, match="too long"):
        buf2.read_string(max_length=100)


# ── UUID ─────────────────────────────────────────────────────────────────────

def test_uuid_roundtrip():
    uid = uuid.uuid4()
    buf = PacketBuffer()
    buf.write_uuid(uid)
    assert PacketBuffer.from_bytes(buf.getvalue()).read_uuid() == uid


def test_uuid_nil():
    uid = uuid.UUID(int=0)
    buf = PacketBuffer()
    buf.write_uuid(uid)
    assert PacketBuffer.from_bytes(buf.getvalue()).read_uuid() == uid


# ── Optional ─────────────────────────────────────────────────────────────────

def test_optional_string_some():
    buf = PacketBuffer()
    buf.write_optional_string("hello")
    b2 = PacketBuffer.from_bytes(buf.getvalue())
    assert b2.read_optional_string() == "hello"


def test_optional_string_none():
    buf = PacketBuffer()
    buf.write_optional_string(None)
    b2 = PacketBuffer.from_bytes(buf.getvalue())
    assert b2.read_optional_string() is None


def test_optional_uuid_some():
    uid = uuid.uuid4()
    buf = PacketBuffer()
    buf.write_optional_uuid(uid)
    assert PacketBuffer.from_bytes(buf.getvalue()).read_optional_uuid() == uid


def test_optional_uuid_none():
    buf = PacketBuffer()
    buf.write_optional_uuid(None)
    assert PacketBuffer.from_bytes(buf.getvalue()).read_optional_uuid() is None


# ── Byte arrays ───────────────────────────────────────────────────────────────

def test_byte_array_roundtrip():
    data = bytes(range(256))
    buf = PacketBuffer()
    buf.write_byte_array(data)
    assert PacketBuffer.from_bytes(buf.getvalue()).read_byte_array() == data


def test_byte_array_empty():
    buf = PacketBuffer()
    buf.write_byte_array(b"")
    assert PacketBuffer.from_bytes(buf.getvalue()).read_byte_array() == b""


def test_read_bytes_exact():
    buf = PacketBuffer.from_bytes(b"\x01\x02\x03\x04\x05")
    assert buf.read_bytes(3) == b"\x01\x02\x03"
    assert buf.read_bytes(2) == b"\x04\x05"


# ── Block position ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("x, y, z", [
    (0, 0, 0),
    (1, 64, 1),
    (-1, -64, -1),
    (33554431, 2047, 33554431),
    (-33554432, -2048, -33554432),
])
def test_position_roundtrip(x, y, z):
    buf = PacketBuffer()
    buf.write_position(x, y, z)
    result = PacketBuffer.from_bytes(buf.getvalue()).read_position()
    assert result == (x, y, z)


def test_position_overworld_y():
    buf = PacketBuffer()
    buf.write_position(100, -64, 200)
    assert PacketBuffer.from_bytes(buf.getvalue()).read_position() == (100, -64, 200)


# ── Angle ─────────────────────────────────────────────────────────────────────

def test_angle_roundtrip():
    buf = PacketBuffer()
    buf.write_angle(90.0)
    result = PacketBuffer.from_bytes(buf.getvalue()).read_angle()
    assert abs(result - 90.0) < 2.0   # 256-step resolution


# ── Buffer mechanics ──────────────────────────────────────────────────────────

def test_remaining():
    buf = PacketBuffer.from_bytes(b"\x01\x02\x03")
    buf.read_bytes(1)
    assert buf.remaining() == b"\x02\x03"


def test_remaining_bytes():
    buf = PacketBuffer.from_bytes(b"\x01\x02\x03\x04")
    buf.read_bytes(2)
    assert buf.remaining_bytes() == 2


def test_underrun_raises():
    buf = PacketBuffer.from_bytes(b"\x01")
    with pytest.raises(BufferUnderrun):
        buf.read_bytes(5)


def test_flush_resets():
    buf = PacketBuffer()
    buf.write_int(42)
    data = buf.flush()
    assert len(data) == 4
    assert len(buf) == 0


def test_getvalue_no_reset():
    buf = PacketBuffer()
    buf.write_int(42)
    _ = buf.getvalue()
    assert len(buf) == 4   # still has data


def test_len():
    buf = PacketBuffer()
    buf.write_int(1)
    buf.write_int(2)
    assert len(buf) == 8


def test_peek():
    buf = PacketBuffer.from_bytes(b"\x01\x02\x03")
    assert buf.peek(2) == b"\x01\x02"
    assert buf.remaining_bytes() == 3   # peek doesn't consume


def test_from_bytes_factory():
    buf = PacketBuffer.from_bytes(b"\x7f")
    assert buf.read_varint() == 127


def test_repr():
    buf = PacketBuffer()
    buf.write_int(1)
    r = repr(buf)
    assert "PacketBuffer" in r


def test_multiple_writes_sequential():
    buf = PacketBuffer()
    buf.write_varint(300)
    buf.write_string("hi")
    buf.write_bool(True)
    buf2 = PacketBuffer.from_bytes(buf.getvalue())
    assert buf2.read_varint() == 300
    assert buf2.read_string() == "hi"
    assert buf2.read_bool() is True
