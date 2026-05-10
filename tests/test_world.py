"""Tests for World and Chunk data structures."""

import pytest
from mcpycore.world import World, Chunk, BlockPos


def test_chunk_get_set_block():
    chunk = Chunk(chunk_x=5, chunk_z=-3)
    chunk.set_block(0, 64, 0, 1)  # stone
    assert chunk.get_block(0, 64, 0) == 1
    assert chunk.get_block(1, 64, 0) == 0  # air by default


def test_chunk_is_air():
    chunk = Chunk(chunk_x=0, chunk_z=0)
    assert chunk.is_air(0, 64, 0)
    chunk.set_block(0, 64, 0, 9)  # water
    assert not chunk.is_air(0, 64, 0)


def test_chunk_world_coords():
    chunk = Chunk(chunk_x=3, chunk_z=-2)
    assert chunk.world_x(0) == 48
    assert chunk.world_x(15) == 63
    assert chunk.world_z(0) == -32
    assert chunk.world_z(15) == -17


def test_world_add_get_remove_chunk():
    world = World()
    chunk = Chunk(chunk_x=0, chunk_z=0)
    world.add_chunk(chunk)
    assert world.get_chunk(0, 0) is chunk
    world.remove_chunk(0, 0)
    assert world.get_chunk(0, 0) is None


def test_world_get_block_state():
    world = World()
    chunk = Chunk(chunk_x=0, chunk_z=0)
    chunk.set_block(5, 64, 5, 2)  # grass block
    world.add_chunk(chunk)

    assert world.get_block_state(5, 64, 5) == 2
    assert world.get_block_state(6, 64, 6) == 0
    # unloaded chunk
    assert world.get_block_state(16, 64, 0) is None


def test_world_set_block_state():
    world = World()
    chunk = Chunk(chunk_x=0, chunk_z=0)
    world.add_chunk(chunk)

    world.set_block_state(3, 70, 7, 5)
    assert world.get_block_state(3, 70, 7) == 5


def test_world_set_block_state_unloaded_chunk():
    world = World()
    # Should not raise even if chunk isn't loaded
    world.set_block_state(100, 64, 100, 3)


def test_world_len():
    world = World()
    assert len(world) == 0
    world.add_chunk(Chunk(0, 0))
    world.add_chunk(Chunk(1, 0))
    assert len(world) == 2


def test_world_clear():
    world = World()
    world.add_chunk(Chunk(0, 0))
    world.add_chunk(Chunk(1, 1))
    world.clear()
    assert len(world) == 0


def test_blockpos_chunk_coords():
    pos = BlockPos(25, 64, -5)
    cx, cz = pos.chunk_coords()
    assert cx == 1
    assert cz == -1


def test_blockpos_relative():
    pos = BlockPos(25, 64, -5)
    rx, y, rz = pos.relative()
    assert rx == 9
    assert y == 64
    assert rz == 11


def test_blockpos_add():
    a = BlockPos(1, 64, 1)
    b = BlockPos(2, 0, -1)
    assert a + b == BlockPos(3, 64, 0)


def test_world_loaded_chunks():
    world = World()
    chunks = [Chunk(i, 0) for i in range(5)]
    for c in chunks:
        world.add_chunk(c)
    loaded = world.loaded_chunks()
    assert len(loaded) == 5
