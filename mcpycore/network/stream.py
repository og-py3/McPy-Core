"""
AsyncStream — low-level async TCP stream with framing, encryption, and compression.

Wraps asyncio.StreamReader / StreamWriter and adds:
- Minecraft packet framing (VarInt-prefixed length)
- Transparent AES-128/CFB8 encryption via EncryptionManager
- Transparent zlib compression via CompressionManager
- Configurable timeouts
- Graceful disconnection
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from mcpycore.compression.compression import CompressionManager
from mcpycore.crypto.encryption import EncryptionManager
from mcpycore.protocol.serializers.buffer import PacketBuffer

log = logging.getLogger(__name__)


class StreamError(Exception):
    """Raised on unrecoverable stream errors."""


class StreamClosedError(StreamError):
    """Raised when an operation is attempted on a closed stream."""


class AsyncStream:
    """
    Framing + crypto + compression layer over asyncio streams.

    Do not construct directly — use ``AsyncStream.open()``::

        stream = await AsyncStream.open("mc.example.com", 25565, timeout=15.0)

        # Read one packet:
        packet_id, buf = await stream.read_packet()

        # Send a packet:
        await stream.write_packet(0x00, payload_bytes)

        await stream.close()
    """

    MAX_PACKET_SIZE = 2_097_152  # 2 MiB

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        timeout: float = 30.0,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._timeout = timeout
        self._closed = False
        self.encryption = EncryptionManager()
        self.compression = CompressionManager()
        self._recv_buf = bytearray()   # accumulates decrypted bytes

    # ── Factory ───────────────────────────────────────────────────────────

    @classmethod
    async def open(
        cls,
        host: str,
        port: int,
        timeout: float = 30.0,
    ) -> "AsyncStream":
        """Open a TCP connection and return a configured AsyncStream."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise StreamError(f"Connection to {host}:{port} timed out after {timeout}s")
        except OSError as exc:
            raise StreamError(f"Failed to connect to {host}:{port}: {exc}") from exc
        return cls(reader, writer, timeout=timeout)

    # ── Low-level read ─────────────────────────────────────────────────────

    async def _read_exactly(self, n: int) -> bytes:
        """Read exactly *n* raw bytes from the socket (with decryption)."""
        self._assert_open()
        chunks = []
        remaining = n
        while remaining > 0:
            try:
                chunk = await asyncio.wait_for(
                    self._reader.read(remaining),
                    timeout=self._timeout,
                )
            except asyncio.TimeoutError:
                raise StreamError("Read timed out")
            if not chunk:
                raise StreamClosedError("Connection closed by remote")
            if self.encryption.enabled:
                chunk = self.encryption.decrypt(chunk)
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    async def _read_varint(self) -> int:
        """Read a VarInt one byte at a time from the stream."""
        result = 0
        shift = 0
        while True:
            byte = (await self._read_exactly(1))[0]
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7
            if shift >= 35:
                raise StreamError("VarInt too large in stream")
        if result & 0x80000000:
            result -= 0x100000000
        return result

    # ── Packet I/O ────────────────────────────────────────────────────────

    async def read_packet(self) -> tuple[int, PacketBuffer]:
        """
        Read one complete packet from the stream.

        Returns ``(packet_id, PacketBuffer)`` where the buffer is positioned
        just after the packet ID, ready for field decoding.
        """
        self._assert_open()

        # Read packet length
        packet_length = await self._read_varint()
        if packet_length <= 0 or packet_length > self.MAX_PACKET_SIZE:
            raise StreamError(f"Invalid packet length: {packet_length}")

        # Read packet data
        raw = await self._read_exactly(packet_length)

        # Decompress if needed
        raw = self.compression.decompress(raw)

        # Parse packet ID
        buf = PacketBuffer.from_bytes(raw)
        packet_id = buf.read_varint()

        return packet_id, buf

    async def write_packet(self, packet_id: int, payload: bytes = b"") -> None:
        """
        Write one packet to the stream.

        Handles compression and framing automatically.
        """
        self._assert_open()
        framed = self.compression.compress(packet_id, payload)
        if self.encryption.enabled:
            framed = self.encryption.encrypt(framed)
        self._writer.write(framed)
        try:
            await asyncio.wait_for(self._writer.drain(), timeout=self._timeout)
        except asyncio.TimeoutError:
            raise StreamError("Write timed out")

    async def write_raw(self, data: bytes) -> None:
        """Write raw bytes (bypasses framing — for handshake-level use only)."""
        self._assert_open()
        if self.encryption.enabled:
            data = self.encryption.encrypt(data)
        self._writer.write(data)
        await self._writer.drain()

    # ── Packet iterator ───────────────────────────────────────────────────

    async def packets(self) -> AsyncIterator[tuple[int, PacketBuffer]]:
        """Async generator yielding ``(packet_id, buf)`` until the stream closes."""
        while not self._closed:
            try:
                yield await self.read_packet()
            except StreamClosedError:
                break

    # ── Crypto / compression enablement ───────────────────────────────────

    def enable_encryption(self, shared_secret: bytes) -> None:
        """Switch the stream to AES-128-CFB8 mode."""
        self.encryption.enable(shared_secret)
        log.debug("Encryption enabled")

    def enable_compression(self, threshold: int) -> None:
        """Enable zlib compression for this stream."""
        self.compression.set_threshold(threshold)
        log.debug("Compression enabled (threshold=%d)", threshold)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def close(self) -> None:
        """Gracefully close the stream."""
        if self._closed:
            return
        self._closed = True
        try:
            self._writer.close()
            await self._writer.wait_closed()
        except Exception:
            pass
        log.debug("Stream closed")

    @property
    def is_closed(self) -> bool:
        return self._closed

    @property
    def remote_address(self) -> tuple[str, int] | None:
        try:
            return self._writer.get_extra_info("peername")
        except Exception:
            return None

    def _assert_open(self) -> None:
        if self._closed:
            raise StreamClosedError("Stream is closed")

    def __repr__(self) -> str:
        addr = self.remote_address
        enc  = "encrypted" if self.encryption.enabled else "plain"
        comp = f"compressed(t={self.compression.threshold})" if self.compression.enabled else "uncompressed"
        return f"AsyncStream({addr}, {enc}, {comp})"
