"""Tests for the NBT parser."""

import struct
import pytest
from mcpycore.utils.nbt import (
    NBTReader, NBTCompound, NBTList, NBTInt, NBTString, NBTByte,
    NBTShort, NBTLong, NBTFloat, NBTDouble, NBTByteArray,
    NBTIntArray, NBTLongArray, NBTEnd,
    TAG_INT, TAG_STRING, TAG_COMPOUND, TAG_LIST, TAG_BYTE, TAG_LONG,
    parse_nbt, nbt_to_dict,
)


def _make_string(s: str) -> bytes:
    enc = s.encode("utf-8")
    return struct.pack(">H", len(enc)) + enc


def _make_varint(v: int) -> bytes:
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _make_compound(children: list[bytes]) -> bytes:
    """Helper to build a TAG_Compound payload."""
    return b"".join(children) + b"\x00"


def _tag(type_id: int, name: str, payload: bytes) -> bytes:
    return bytes([type_id]) + _make_string(name) + payload


# ── Primitives ────────────────────────────────────────────────────────────────

def test_parse_byte():
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_BYTE, "b", b"\x7f") +
        b"\x00"
    )
    root = parse_nbt(data)
    assert isinstance(root, NBTCompound)
    assert root.get("b") == 127


def test_parse_short():
    from mcpycore.utils.nbt import TAG_SHORT
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_SHORT, "s", struct.pack(">h", 1234)) +
        b"\x00"
    )
    root = parse_nbt(data)
    assert root.get("s") == 1234


def test_parse_int():
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_INT, "x", struct.pack(">i", -99999)) +
        b"\x00"
    )
    root = parse_nbt(data)
    assert root.get("x") == -99999


def test_parse_long():
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_LONG, "l", struct.pack(">q", 2**40)) +
        b"\x00"
    )
    root = parse_nbt(data)
    assert root.get("l") == 2**40


def test_parse_float():
    from mcpycore.utils.nbt import TAG_FLOAT
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_FLOAT, "f", struct.pack(">f", 3.14)) +
        b"\x00"
    )
    root = parse_nbt(data)
    assert abs(root.get("f") - 3.14) < 1e-5


def test_parse_double():
    from mcpycore.utils.nbt import TAG_DOUBLE
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_DOUBLE, "d", struct.pack(">d", 3.14159265358979)) +
        b"\x00"
    )
    root = parse_nbt(data)
    assert abs(root.get("d") - 3.14159265358979) < 1e-12


def test_parse_string():
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_STRING, "name", _make_string("hello world")) +
        b"\x00"
    )
    root = parse_nbt(data)
    assert root.get("name") == "hello world"


def test_parse_string_unicode():
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_STRING, "uni", _make_string("こんにちは")) +
        b"\x00"
    )
    root = parse_nbt(data)
    assert root.get("uni") == "こんにちは"


def test_parse_byte_array():
    from mcpycore.utils.nbt import TAG_BYTE_ARRAY
    payload = struct.pack(">i", 4) + bytes([1, 2, 3, 4])
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_BYTE_ARRAY, "ba", payload) +
        b"\x00"
    )
    root = parse_nbt(data)
    assert root.get("ba") == bytes([1, 2, 3, 4])


def test_parse_int_array():
    from mcpycore.utils.nbt import TAG_INT_ARRAY
    payload = struct.pack(">i", 3) + struct.pack(">3i", 10, 20, 30)
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_INT_ARRAY, "ia", payload) +
        b"\x00"
    )
    root = parse_nbt(data)
    assert root.get("ia") == [10, 20, 30]


def test_parse_long_array():
    from mcpycore.utils.nbt import TAG_LONG_ARRAY
    payload = struct.pack(">i", 2) + struct.pack(">2q", 2**60, -1)
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_LONG_ARRAY, "la", payload) +
        b"\x00"
    )
    root = parse_nbt(data)
    assert root.get("la") == [2**60, -1]


# ── List ─────────────────────────────────────────────────────────────────────

def test_parse_list_of_ints():
    from mcpycore.utils.nbt import TAG_LIST
    payload = (
        bytes([TAG_INT]) +
        struct.pack(">i", 3) +
        struct.pack(">i", 1) + struct.pack(">i", 2) + struct.pack(">i", 3)
    )
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_LIST, "lst", payload) +
        b"\x00"
    )
    root = parse_nbt(data)
    lst = root.value["lst"]
    assert isinstance(lst, NBTList)
    assert [v.value for v in lst.value] == [1, 2, 3]


def test_parse_empty_list():
    from mcpycore.utils.nbt import TAG_LIST, TAG_END
    payload = bytes([TAG_END]) + struct.pack(">i", 0)
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_LIST, "empty", payload) +
        b"\x00"
    )
    root = parse_nbt(data)
    assert root.value["empty"].value == []


# ── Nested compound ───────────────────────────────────────────────────────────

def test_nested_compound():
    inner = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        bytes([TAG_COMPOUND]) + _make_string("inner") +
        _tag(TAG_INT, "val", struct.pack(">i", 42)) +
        b"\x00" +
        b"\x00"
    )
    root = parse_nbt(inner)
    inner_compound = root.value["inner"]
    assert isinstance(inner_compound, NBTCompound)
    assert inner_compound.get("val") == 42


def test_deeply_nested():
    def make_level(depth, value):
        if depth == 0:
            return _tag(TAG_INT, "val", struct.pack(">i", value)) + b"\x00"
        return (
            bytes([TAG_COMPOUND]) + _make_string(f"l{depth}") +
            make_level(depth - 1, value) +
            b"\x00"
        )

    data = bytes([TAG_COMPOUND]) + _make_string("root") + make_level(3, 999) + b"\x00"
    root = parse_nbt(data)
    l3 = root.value.get("l3")
    assert l3 is not None


# ── nbt_to_dict ───────────────────────────────────────────────────────────────

def test_nbt_to_dict_simple():
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        _tag(TAG_INT, "x", struct.pack(">i", 5)) +
        _tag(TAG_STRING, "name", _make_string("test")) +
        b"\x00"
    )
    root = parse_nbt(data)
    d = nbt_to_dict(root)
    assert d == {"x": 5, "name": "test"}


def test_nbt_to_dict_nested():
    data = (
        bytes([TAG_COMPOUND]) + _make_string("root") +
        bytes([TAG_COMPOUND]) + _make_string("pos") +
        _tag(TAG_INT, "x", struct.pack(">i", 10)) +
        _tag(TAG_INT, "y", struct.pack(">i", 64)) +
        _tag(TAG_INT, "z", struct.pack(">i", -20)) +
        b"\x00" +
        b"\x00"
    )
    root = parse_nbt(data)
    d = nbt_to_dict(root)
    assert d == {"pos": {"x": 10, "y": 64, "z": -20}}


# ── Repr / misc ───────────────────────────────────────────────────────────────

def test_nbt_compound_repr():
    c = NBTCompound(name="test", value={})
    assert "TAG_Compound" in repr(c) or "Compound" in repr(c)


def test_nbt_end_tag_id():
    e = NBTEnd()
    assert e.tag_id == 0


def test_unknown_tag_raises():
    bad_data = bytes([99]) + _make_string("wat") + b"\x00"
    with pytest.raises(ValueError, match="Unknown"):
        parse_nbt(bad_data)
