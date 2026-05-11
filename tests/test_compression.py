"""Tests for CompressionManager."""
from __future__ import annotations

import zlib
import pytest

from mcpycore.compression.compression import CompressionManager
from mcpycore.protocol.serializers.buffer import PacketBuffer


# ── Initial state ─────────────────────────────────────────────────────────────

def test_disabled_by_default():
    c = CompressionManager()
    assert not c.enabled
    assert c.threshold == -1


def test_enable():
    c = CompressionManager()
    c.set_threshold(256)
    assert c.enabled
    assert c.threshold == 256


def test_disable():
    c = CompressionManager()
    c.set_threshold(256)
    c.disable()
    assert not c.enabled


# ── Uncompressed framing ──────────────────────────────────────────────────────

def test_uncompressed_compress_decompress():
    c = CompressionManager()
    payload = b"\x01\x02\x03\x04"
    framed = c.compress(0x24, payload)

    # Parse frame: [length varint][packet_id varint][payload]
    buf = PacketBuffer.from_bytes(framed)
    length = buf.read_varint()
    inner = buf.read_bytes(length)
    # Decompress (disabled) = inner unchanged
    raw = c.decompress(inner)
    inner_buf = PacketBuffer.from_bytes(raw)
    pid = inner_buf.read_varint()
    assert pid == 0x24
    assert inner_buf.remaining() == payload


# ── Compressed framing ────────────────────────────────────────────────────────

def test_compress_large_payload():
    c = CompressionManager()
    c.set_threshold(16)
    payload = b"A" * 200   # above threshold — should compress
    framed = c.compress(0x00, payload)

    # Parse outer frame
    buf = PacketBuffer.from_bytes(framed)
    packet_length = buf.read_varint()
    inner = buf.read_bytes(packet_length)

    # decompress
    raw = c.decompress(inner)
    inner_buf = PacketBuffer.from_bytes(raw)
    pid = inner_buf.read_varint()
    assert pid == 0x00
    assert inner_buf.remaining() == payload


def test_compress_small_payload_not_compressed():
    c = CompressionManager()
    c.set_threshold(1024)
    payload = b"\x01\x02"   # below threshold — should NOT compress
    framed = c.compress(0x01, payload)

    buf = PacketBuffer.from_bytes(framed)
    packet_length = buf.read_varint()
    inner = buf.read_bytes(packet_length)
    raw = c.decompress(inner)
    inner_buf = PacketBuffer.from_bytes(raw)
    pid = inner_buf.read_varint()
    assert pid == 0x01
    assert inner_buf.remaining() == payload


def test_decompress_length_mismatch_raises():
    c = CompressionManager()
    c.set_threshold(16)
    # Build a corrupted compressed payload
    raw = b"AAAABBBBCCCCDDDDEEEE"
    compressed = zlib.compress(raw)
    buf = PacketBuffer()
    buf.write_varint(len(raw) + 999)   # wrong data_length
    buf._write_raw(compressed)
    with pytest.raises(ValueError, match="mismatch"):
        c.decompress(buf.getvalue())


def test_threshold_exactly_at_boundary():
    c = CompressionManager()
    c.set_threshold(10)
    # Exactly at threshold = should compress
    payload = b"X" * 10
    framed = c.compress(0x01, payload)
    buf = PacketBuffer.from_bytes(framed)
    length = buf.read_varint()
    inner = buf.read_bytes(length)
    raw = c.decompress(inner)
    assert raw is not None


def test_repr_enabled():
    c = CompressionManager()
    c.set_threshold(256)
    assert "enabled" in repr(c)
    assert "256" in repr(c)


def test_repr_disabled():
    c = CompressionManager()
    assert "disabled" in repr(c)


def test_roundtrip_many_packet_ids():
    c = CompressionManager()
    c.set_threshold(16)
    for pid in [0x00, 0x01, 0x24, 0x7F, 0xFF]:
        payload = b"hello world" * 10
        framed = c.compress(pid, payload)
        buf = PacketBuffer.from_bytes(framed)
        length = buf.read_varint()
        inner = buf.read_bytes(length)
        raw = c.decompress(inner)
        inner_buf = PacketBuffer.from_bytes(raw)
        assert inner_buf.read_varint() == pid
        assert inner_buf.remaining() == payload
