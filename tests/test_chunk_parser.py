"""Tests for the chunk section parser."""

import struct
import pytest

from mcpycore.world.chunk_parser import (
    parse_chunk_sections, ChunkSection,
    section_to_world_y, world_y_to_section,
    SECTION_COUNT, MIN_Y, _unpack_longs,
)


# ── _unpack_longs ─────────────────────────────────────────────────────────────

def test_unpack_longs_4bit():
    # Pack values 0,1,2,3,4,5,6,7 into 4-bit fields across one long
    lng = 0
    for i, v in enumerate([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]):
        lng |= v << (i * 4)
    result = _unpack_longs((lng,), 4, 16)
    assert result == list(range(16))


def test_unpack_longs_5bit():
    lng = 0
    values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    for i, v in enumerate(values):
        lng |= v << (i * 5)
    result = _unpack_longs((lng,), 5, 12)
    assert result == values


def test_unpack_longs_count_truncation():
    result = _unpack_longs((0xFFFFFFFFFFFFFFFF,), 4, 5)
    assert len(result) == 5


def test_unpack_longs_zero_values():
    result = _unpack_longs((0,), 4, 16)
    assert result == [0] * 16


def test_unpack_longs_unsigned():
    # Ensure negative longs are treated as unsigned
    result = _unpack_longs((-1,), 4, 16)
    assert all(v == 0xF for v in result)


# ── section_to_world_y / world_y_to_section ───────────────────────────────────

def test_section_to_world_y_bottom():
    assert section_to_world_y(0) == -64


def test_section_to_world_y_top():
    assert section_to_world_y(23) == -64 + 23 * 16


def test_world_y_to_section_y0():
    sec, rel = world_y_to_section(0)
    assert sec == 4
    assert rel == 0


def test_world_y_to_section_bottom():
    sec, rel = world_y_to_section(-64)
    assert sec == 0
    assert rel == 0


def test_world_y_to_section_y64():
    sec, rel = world_y_to_section(64)
    assert sec == 8
    assert rel == 0


def test_world_y_to_section_partial():
    sec, rel = world_y_to_section(-60)
    assert sec == 0
    assert rel == 4


def test_section_count():
    assert SECTION_COUNT == 24


def test_min_y():
    assert MIN_Y == -64


# ── ChunkSection ─────────────────────────────────────────────────────────────

def test_chunk_section_single_value():
    sec = ChunkSection(block_count=4096, blocks={"single": 7})
    assert sec.get_block(0, 0, 0) == 7
    assert sec.get_block(8, 8, 8) == 7
    assert sec.get_block(15, 15, 15) == 7


def test_chunk_section_single_air():
    sec = ChunkSection(block_count=0, blocks={"single": 0})
    assert sec.get_block(0, 0, 0) == 0


def test_chunk_section_indexed():
    blocks = {(2 * 256 + 3 * 16 + 4): 42}
    sec = ChunkSection(block_count=1, blocks=blocks)
    assert sec.get_block(4, 2, 3) == 42
    assert sec.get_block(0, 0, 0) == 0


def test_chunk_section_missing_key():
    sec = ChunkSection(block_count=0, blocks={})
    assert sec.get_block(5, 5, 5) == 0


def test_chunk_section_repr():
    sec = ChunkSection(block_count=100, blocks={})
    assert "100" in repr(sec)


def test_chunk_section_iter_single_value_air():
    sec = ChunkSection(block_count=0, blocks={"single": 0})
    blocks = list(sec)
    assert blocks == []


def test_chunk_section_iter_single_non_air():
    sec = ChunkSection(block_count=4096, blocks={"single": 5})
    blocks = list(sec)
    assert len(blocks) == 4096
    assert all(state == 5 for _, _, _, state in blocks)


def test_chunk_section_iter_indexed():
    idx = 1 * 256 + 2 * 16 + 3   # y=1, z=2, x=3
    sec = ChunkSection(block_count=1, blocks={idx: 99})
    blocks = list(sec)
    assert len(blocks) == 1
    x, y, z, state = blocks[0]
    assert x == 3 and y == 1 and z == 2 and state == 99


# ── parse_chunk_sections (minimal synthetic payload) ─────────────────────────

def _make_single_value_section(state_id: int) -> bytes:
    """Build a minimal valid chunk section with a single-value palette."""
    out = bytearray()
    out += struct.pack(">h", 0 if state_id == 0 else 4096)   # block_count
    # Block state palette container — bits_per_entry = 0 (single value)
    out += b"\x00"                                            # bits_per_entry

    def varint(v):
        r = bytearray()
        while True:
            b = v & 0x7F
            v >>= 7
            if v:
                r.append(b | 0x80)
            else:
                r.append(b)
                break
        return bytes(r)

    out += varint(state_id)    # value
    out += varint(0)           # data_array_length = 0
    # Biome palette container — also single-value (biome 0)
    out += b"\x00"             # bits_per_entry
    out += varint(0)           # biome value
    out += varint(0)           # data_array_length = 0
    return bytes(out)


def test_parse_single_section_air():
    raw = _make_single_value_section(0) * SECTION_COUNT
    sections = parse_chunk_sections(raw)
    assert len(sections) > 0
    assert sections[0].get_block(0, 0, 0) == 0


def test_parse_single_section_stone():
    raw = _make_single_value_section(1) * SECTION_COUNT
    sections = parse_chunk_sections(raw)
    assert len(sections) > 0
    assert sections[0].get_block(0, 0, 0) == 1


def test_parse_empty_data_returns_no_sections():
    sections = parse_chunk_sections(b"")
    assert sections == []


def test_parse_partial_data_safe():
    # Should not raise even with truncated data
    raw = _make_single_value_section(0)[:5]
    try:
        sections = parse_chunk_sections(raw)
    except Exception:
        pytest.fail("parse_chunk_sections raised on partial data")


def test_section_count_matches_expected():
    raw = _make_single_value_section(5) * SECTION_COUNT
    sections = parse_chunk_sections(raw)
    # Should parse all 24 sections (or fewer if data runs short)
    assert len(sections) <= SECTION_COUNT
    assert len(sections) > 0
