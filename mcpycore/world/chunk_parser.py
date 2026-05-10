"""
Minecraft chunk section parser (1.18+ format).

Decodes the raw binary payload from ChunkDataAndUpdateLight packets into
individual block state IDs per position.

The 1.18+ chunk format uses "palette containers" for block states and biomes:
  - Each section is 16×16×16 blocks (4096 total)
  - A palette maps compact indices → block state IDs
  - Data is packed into a long array
  - bits_per_entry = 0  → single-value (all blocks are the same)
  - bits_per_entry 1–8 → indirect palette
  - bits_per_entry 9+  → direct (global palette IDs)

Reference: https://minecraft.wiki/w/Chunk_format#Chunk_Section_structure
"""

from __future__ import annotations

import math
import struct
from typing import Iterator

from mcpycore.utils.datatypes import varint_from_bytes

# Minecraft 1.18+ world: sections from Y=-64 to Y=320 → 24 sections
SECTION_COUNT = 24
SECTION_HEIGHT = 16
MIN_Y = -64


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    """Read a VarInt at *offset* in *data*. Returns (value, bytes_consumed)."""
    return varint_from_bytes(data, offset)


def _read_palette_container(data: bytes, offset: int, direct_bits: int) -> tuple[dict[int, int], int]:
    """
    Parse one palette container starting at *offset*.
    Returns ({section_index: block_state_id}, new_offset).
    *direct_bits* is the minimum bit width for the direct palette (15 for blocks, 6 for biomes).
    """
    bits_per_entry = data[offset]
    offset += 1

    if bits_per_entry == 0:
        # Single-value palette
        value, consumed = _read_varint(data, offset)
        offset += consumed
        data_len, consumed = _read_varint(data, offset)
        offset += consumed + data_len * 8   # skip empty long array
        return {"single": value}, offset

    elif bits_per_entry <= 8:
        # Indirect palette
        palette_len, consumed = _read_varint(data, offset)
        offset += consumed
        palette: list[int] = []
        for _ in range(palette_len):
            pid, consumed = _read_varint(data, offset)
            offset += consumed
            palette.append(pid)

        bits = max(bits_per_entry, 4)  # minimum 4 bits for blocks
        data_len, consumed = _read_varint(data, offset)
        offset += consumed
        longs = struct.unpack_from(f">{data_len}q", data, offset)
        offset += data_len * 8

        blocks = _unpack_longs(longs, bits, 4096)
        return {i: palette[idx] for i, idx in enumerate(blocks) if idx < len(palette)}, offset

    else:
        # Direct / global palette
        bits = direct_bits
        data_len, consumed = _read_varint(data, offset)
        offset += consumed
        longs = struct.unpack_from(f">{data_len}q", data, offset)
        offset += data_len * 8

        blocks = _unpack_longs(longs, bits, 4096)
        return {i: v for i, v in enumerate(blocks)}, offset


def _unpack_longs(longs: tuple[int, ...], bits: int, count: int) -> list[int]:
    """Unpack *count* values of *bits* width from a sequence of 64-bit signed longs."""
    mask = (1 << bits) - 1
    values_per_long = 64 // bits
    result: list[int] = []
    for lng in longs:
        # Treat as unsigned 64-bit
        if lng < 0:
            lng += 1 << 64
        for _ in range(values_per_long):
            if len(result) >= count:
                break
            result.append(lng & mask)
            lng >>= bits
    return result[:count]


class ChunkSection:
    """
    One 16×16×16 section of a chunk.
    Provides O(1) lookup of block state IDs by relative coordinates.
    """

    def __init__(self, block_count: int, blocks: dict[int, int]) -> None:
        self.block_count = block_count
        self._blocks = blocks   # index → state_id; "single" key for single-value
        self._single: int | None = None
        if "single" in blocks:
            self._single = blocks["single"]  # type: ignore[assignment]

    def get_block(self, rx: int, y: int, rz: int) -> int:
        """Return the block state ID at relative (rx, y, rz) within this section."""
        if self._single is not None:
            return self._single
        idx = (y & 0xF) * 256 + (rz & 0xF) * 16 + (rx & 0xF)
        return self._blocks.get(idx, 0)

    def __iter__(self) -> Iterator[tuple[int, int, int, int]]:
        """Yield (rx, ry, rz, state_id) for every non-air block."""
        if self._single is not None:
            if self._single != 0:
                for y in range(16):
                    for z in range(16):
                        for x in range(16):
                            yield x, y, z, self._single
            return
        for idx, state_id in self._blocks.items():
            if isinstance(idx, int) and state_id != 0:
                x = idx % 16
                z = (idx // 16) % 16
                y = idx // 256
                yield x, y, z, state_id

    def __repr__(self) -> str:
        return f"ChunkSection(blocks={self.block_count})"


def parse_chunk_sections(raw: bytes) -> list[ChunkSection]:
    """
    Parse the raw chunk payload from ChunkDataAndUpdateLight into a list of
    ChunkSection objects (one per 16-block-tall section, bottom to top).

    The number of sections is SECTION_COUNT (24 for 1.18+, Y=-64 to Y=320).
    """
    offset = 0
    sections: list[ChunkSection] = []

    for _ in range(SECTION_COUNT):
        if offset + 2 > len(raw):
            break

        # Block count (short)
        block_count = struct.unpack_from(">h", raw, offset)[0]
        offset += 2

        # Block state palette container
        try:
            blocks_dict, offset = _read_palette_container(raw, offset, 15)
        except (struct.error, IndexError):
            break

        # Biome palette container (skip — biomes stored separately)
        try:
            _biomes, offset = _read_palette_container(raw, offset, 6)
        except (struct.error, IndexError):
            sections.append(ChunkSection(block_count, blocks_dict))
            break

        sections.append(ChunkSection(block_count, blocks_dict))

    return sections


def section_to_world_y(section_index: int) -> int:
    """Convert a section index (0 = bottom) to the world Y coordinate of its base."""
    return MIN_Y + section_index * SECTION_HEIGHT


def world_y_to_section(y: int) -> tuple[int, int]:
    """
    Convert a world Y coordinate to (section_index, relative_y).
    section_index is 0 for the bottom-most section.
    """
    adjusted = y - MIN_Y
    return adjusted // SECTION_HEIGHT, adjusted % SECTION_HEIGHT
