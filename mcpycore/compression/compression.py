"""
CompressionManager — zlib-based packet compression.

Once enabled (threshold ≥ 0), packets whose uncompressed payload exceeds
the threshold are compressed with zlib; smaller packets send a VarInt 0
for the data length field and remain uncompressed.

Wire format (compressed state):
  [Packet Length VarInt]
  [Data Length VarInt]    ← 0 means "not compressed"
  [Data]                  ← compressed if Data Length > 0, else raw
"""
from __future__ import annotations

import zlib

from mcpycore.protocol.serializers.buffer import PacketBuffer


class CompressionManager:
    """
    Manages optional zlib compression for one connection.

    Usage::

        comp = CompressionManager()
        comp.set_threshold(256)     # enable; compress packets ≥ 256 bytes

        outgoing = comp.compress(raw_payload)
        payload  = comp.decompress(incoming_packet_data)
    """

    def __init__(self) -> None:
        self._threshold: int = -1    # -1 = disabled

    @property
    def enabled(self) -> bool:
        return self._threshold >= 0

    @property
    def threshold(self) -> int:
        return self._threshold

    def set_threshold(self, threshold: int) -> None:
        """
        Enable compression.  Packets whose uncompressed length >= *threshold*
        are compressed.  Set to -1 to disable.
        """
        self._threshold = threshold

    def disable(self) -> None:
        self._threshold = -1

    def compress(self, packet_id: int, payload: bytes) -> bytes:
        """
        Wrap a packet for the wire with optional compression.

        Returns the full framed bytes:
          [Packet Length][Data Length][Data]
        """
        # Build the raw packet: [packet_id VarInt][payload]
        id_buf = PacketBuffer()
        id_buf.write_varint(packet_id)
        raw = id_buf.getvalue() + payload

        out = PacketBuffer()

        if not self.enabled:
            # Uncompressed framing: [length][packet_id][payload]
            out.write_varint(len(raw))
            out._write_raw(raw)
        else:
            if len(raw) >= self._threshold:
                # Compress
                compressed = zlib.compress(raw)
                data_len_buf = PacketBuffer()
                data_len_buf.write_varint(len(raw))   # uncompressed length
                framed = data_len_buf.getvalue() + compressed
            else:
                # Below threshold — send uncompressed
                data_len_buf = PacketBuffer()
                data_len_buf.write_varint(0)           # 0 = not compressed
                framed = data_len_buf.getvalue() + raw

            out.write_varint(len(framed))
            out._write_raw(framed)

        return out.getvalue()

    def decompress(self, data: bytes) -> bytes:
        """
        Decompress an incoming packet payload (after packet length is stripped).

        In compressed state, data starts with [Data Length VarInt][payload].
        Returns the raw (uncompressed) [packet_id][payload] bytes.
        """
        if not self.enabled:
            return data

        buf = PacketBuffer.from_bytes(data)
        data_length = buf.read_varint()

        remaining = buf.remaining()

        if data_length == 0:
            # Not compressed
            return remaining
        else:
            decompressed = zlib.decompress(remaining)
            if len(decompressed) != data_length:
                raise ValueError(
                    f"Decompressed length mismatch: expected {data_length}, "
                    f"got {len(decompressed)}"
                )
            return decompressed

    def __repr__(self) -> str:
        if self.enabled:
            return f"CompressionManager(enabled, threshold={self._threshold})"
        return "CompressionManager(disabled)"
