"""World and chunk data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple


class BlockPos(NamedTuple):
    """An immutable (x, y, z) block coordinate."""
    x: int
    y: int
    z: int

    def __add__(self, other: "BlockPos") -> "BlockPos":
        return BlockPos(self.x + other.x, self.y + other.y, self.z + other.z)

    def chunk_coords(self) -> tuple[int, int]:
        """Return the (chunk_x, chunk_z) this block belongs to."""
        return self.x >> 4, self.z >> 4

    def relative(self) -> tuple[int, int, int]:
        """Return block coordinates relative to its chunk (0-15, y, 0-15)."""
        return self.x & 15, self.y, self.z & 15


@dataclass
class Chunk:
    """
    A 16×(world height)×16 column of block data.

    Block state IDs are stored in a flat dict keyed by relative (x, y, z).
    Unparsed sections are kept as raw bytes and parsed lazily if needed.
    """

    chunk_x: int
    chunk_z: int

    # block_state_id keyed by (rx, y, rz) within the chunk
    blocks: dict[tuple[int, int, int], int] = field(default_factory=dict)

    # raw chunk data (for advanced users who want to parse sections themselves)
    raw_data: bytes = b""

    def get_block(self, rx: int, y: int, rz: int) -> int:
        """Return the block state ID at relative position (rx, y, rz). 0 = air."""
        return self.blocks.get((rx, y, rz), 0)

    def set_block(self, rx: int, y: int, rz: int, state_id: int) -> None:
        self.blocks[(rx, y, rz)] = state_id

    def is_air(self, rx: int, y: int, rz: int) -> bool:
        return self.get_block(rx, y, rz) == 0

    def world_x(self, rx: int) -> int:
        return self.chunk_x * 16 + rx

    def world_z(self, rz: int) -> int:
        return self.chunk_z * 16 + rz

    def __repr__(self) -> str:
        return f"Chunk(x={self.chunk_x}, z={self.chunk_z}, blocks={len(self.blocks)})"


class World:
    """
    Tracks the loaded chunks and provides block lookups.

    Updated by the client as ChunkData and BlockUpdate packets arrive.
    Chunks outside the view distance are automatically removed when
    UnloadChunk packets arrive.
    """

    def __init__(self) -> None:
        self._chunks: dict[tuple[int, int], Chunk] = {}
        self.time_of_day: int = 0
        self.world_age: int = 0
        self.dimension: str = "minecraft:overworld"

    # ── Chunk management ──────────────────────────────────────────────────────

    def add_chunk(self, chunk: Chunk) -> None:
        self._chunks[(chunk.chunk_x, chunk.chunk_z)] = chunk

    def remove_chunk(self, chunk_x: int, chunk_z: int) -> Chunk | None:
        return self._chunks.pop((chunk_x, chunk_z), None)

    def get_chunk(self, chunk_x: int, chunk_z: int) -> Chunk | None:
        return self._chunks.get((chunk_x, chunk_z))

    def loaded_chunks(self) -> list[Chunk]:
        return list(self._chunks.values())

    # ── Block access ──────────────────────────────────────────────────────────

    def get_block_state(self, x: int, y: int, z: int) -> int | None:
        """
        Return the block state ID at world coordinates (x, y, z).
        Returns None if the chunk is not loaded.
        """
        chunk = self._chunks.get((x >> 4, z >> 4))
        if chunk is None:
            return None
        return chunk.get_block(x & 15, y, z & 15)

    def set_block_state(self, x: int, y: int, z: int, state_id: int) -> None:
        """Update a single block (from BlockUpdate packets)."""
        chunk = self._chunks.get((x >> 4, z >> 4))
        if chunk is not None:
            chunk.set_block(x & 15, y, z & 15, state_id)

    def is_block_loaded(self, x: int, y: int, z: int) -> bool:
        return (x >> 4, z >> 4) in self._chunks

    def clear(self) -> None:
        self._chunks.clear()

    def __len__(self) -> int:
        return len(self._chunks)

    def __repr__(self) -> str:
        return f"World(chunks={len(self._chunks)}, time={self.time_of_day})"
