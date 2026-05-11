"""Tests for the NBT parser."""
from __future__ import annotations

import struct
import pytest

from mcpycore.protocol.serializers.nbt import (
    parse_nbt, nbt_to_dict,
    NBTEnd, NBTByte, NBTShort, NBTInt, NBTLong,
    NBTFloat, NBTDouble, NBTString, NBTList, NBTCompound,
    NBTByteArray, NBTIntArray, NBTLongArray,
    TAG_END, TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG,
    TAG_FLOAT, TAG_DOUBLE, TAG_STRING, TAG_LIST,
    TAG_COMPOUND, TAG_BYTE_ARRAY, TAG_INT_ARRAY, TAG_LONG_ARRAY,
)


def _name(s: str) -> bytes:
    enc = s.encode("utf-8")
    return struct.pack(">H", len(enc)) + enc


def _tag(type_id: int, name: str, payload: bytes) -> bytes:
    return bytes([type_id]) + _name(name) + payload


def test_parse_byte():
    data = bytes([TAG_COMPOUND]) + _name("r") + _tag(TAG_BYTE, "b", b"\x7f") + b"\x00"
    root = parse_nbt(data)
    assert isinstance(root, NBTCompound)
    assert root.get("b") == 127


def test_parse_short():
    data = bytes([TAG_COMPOUND]) + _name("r") + _tag(TAG_SHORT, "s", struct.pack(">h", 1000)) + b"\x00"
    assert parse_nbt(data).get("s") == 1000


def test_parse_int():
    data = bytes([TAG_COMPOUND]) + _name("r") + _tag(TAG_INT, "i", struct.pack(">i", -99999)) + b"\x00"
    assert parse_nbt(data).get("i") == -99999


def test_parse_long():
    data = bytes([TAG_COMPOUND]) + _name("r") + _tag(TAG_LONG, "l", struct.pack(">q", 2**40)) + b"\x00"
    assert parse_nbt(data).get("l") == 2**40


def test_parse_float():
    data = bytes([TAG_COMPOUND]) + _name("r") + _tag(TAG_FLOAT, "f", struct.pack(">f", 3.14)) + b"\x00"
    assert abs(parse_nbt(data).get("f") - 3.14) < 1e-5


def test_parse_double():
    data = bytes([TAG_COMPOUND]) + _name("r") + _tag(TAG_DOUBLE, "d", struct.pack(">d", 1.23456789)) + b"\x00"
    assert abs(parse_nbt(data).get("d") - 1.23456789) < 1e-9


def test_parse_string():
    data = bytes([TAG_COMPOUND]) + _name("r") + _tag(TAG_STRING, "s", _name("hello world")) + b"\x00"
    assert parse_nbt(data).get("s") == "hello world"


def test_parse_string_unicode():
    data = bytes([TAG_COMPOUND]) + _name("r") + _tag(TAG_STRING, "u", _name("こんにちは")) + b"\x00"
    assert parse_nbt(data).get("u") == "こんにちは"


def test_parse_byte_array():
    payload = struct.pack(">i", 4) + bytes([1, 2, 3, 4])
    data = bytes([TAG_COMPOUND]) + _name("r") + _tag(TAG_BYTE_ARRAY, "ba", payload) + b"\x00"
    assert parse_nbt(data).get("ba") == bytes([1, 2, 3, 4])


def test_parse_int_array():
    payload = struct.pack(">i", 3) + struct.pack(">iii", 10, 20, 30)
    data = bytes([TAG_COMPOUND]) + _name("r") + _tag(TAG_INT_ARRAY, "ia", payload) + b"\x00"
    assert parse_nbt(data).get("ia") == [10, 20, 30]


def test_parse_long_array():
    payload = struct.pack(">i", 2) + struct.pack(">qq", 2**60, -1)
    data = bytes([TAG_COMPOUND]) + _name("r") + _tag(TAG_LONG_ARRAY, "la", payload) + b"\x00"
    assert parse_nbt(data).get("la") == [2**60, -1]


def test_parse_list_ints():
    payload = bytes([TAG_INT]) + struct.pack(">i", 3) + struct.pack(">iii", 1, 2, 3)
    data = bytes([TAG_COMPOUND]) + _name("r") + _tag(TAG_LIST, "lst", payload) + b"\x00"
    root = parse_nbt(data)
    lst = root.value["lst"]
    assert isinstance(lst, NBTList)
    assert [e.value for e in lst.value] == [1, 2, 3]


def test_parse_empty_list():
    payload = bytes([TAG_END]) + struct.pack(">i", 0)
    data = bytes([TAG_COMPOUND]) + _name("r") + _tag(TAG_LIST, "e", payload) + b"\x00"
    root = parse_nbt(data)
    assert root.value["e"].value == []


def test_nested_compound():
    data = (
        bytes([TAG_COMPOUND]) + _name("r") +
        bytes([TAG_COMPOUND]) + _name("inner") +
        _tag(TAG_INT, "x", struct.pack(">i", 42)) +
        b"\x00" +
        b"\x00"
    )
    root = parse_nbt(data)
    inner = root.value["inner"]
    assert isinstance(inner, NBTCompound)
    assert inner.get("x") == 42


def test_nbt_to_dict_simple():
    data = (
        bytes([TAG_COMPOUND]) + _name("r") +
        _tag(TAG_INT, "x", struct.pack(">i", 5)) +
        _tag(TAG_STRING, "n", _name("test")) +
        b"\x00"
    )
    d = nbt_to_dict(parse_nbt(data))
    assert d == {"x": 5, "n": "test"}


def test_nbt_to_dict_nested():
    data = (
        bytes([TAG_COMPOUND]) + _name("r") +
        bytes([TAG_COMPOUND]) + _name("pos") +
        _tag(TAG_INT, "x", struct.pack(">i", 10)) +
        _tag(TAG_INT, "y", struct.pack(">i", 64)) +
        b"\x00" +
        b"\x00"
    )
    d = nbt_to_dict(parse_nbt(data))
    assert d == {"pos": {"x": 10, "y": 64}}


def test_unknown_tag_raises():
    with pytest.raises(ValueError, match="Unknown"):
        parse_nbt(bytes([99]) + _name("bad") + b"\x00")


def test_nbt_end():
    e = NBTEnd()
    assert e.tag_id == 0


def test_nbt_compound_repr():
    c = NBTCompound(name="test", value={})
    assert "Compound" in repr(c)


def test_nbt_get_missing():
    c = NBTCompound(name="r", value={})
    assert c.get("nope") is None
    assert c.get("nope", 42) == 42


def test_nbt_multiple_tags():
    data = (
        bytes([TAG_COMPOUND]) + _name("r") +
        _tag(TAG_BYTE, "a", b"\x01") +
        _tag(TAG_BYTE, "b", b"\x02") +
        _tag(TAG_BYTE, "c", b"\x03") +
        b"\x00"
    )
    root = parse_nbt(data)
    assert root.get("a") == 1
    assert root.get("b") == 2
    assert root.get("c") == 3
