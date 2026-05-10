"""
TCP connection layer with optional zlib compression and AES/CFB8 encryption.

Handles raw socket I/O, packet framing, compression, and encryption
without knowing anything about packet semantics.
"""

from __future__ import annotations

import socket
import zlib
import threading
from typing import Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from mcpycore.utils.datatypes import read_varint, write_varint, varint_from_bytes
from mcpycore.packets.packet import Packet, PacketBuffer
from mcpycore import exceptions as exc


class Connection:
    """
    Low-level TCP connection to a Minecraft server.

    Features:
    - VarInt-framed packet reading and writing
    - Optional zlib compression (threshold-based, as per protocol)
    - Optional AES-128/CFB8 encryption after login handshake
    - Thread-safe sending via an internal lock
    """

    def __init__(self, host: str, port: int, timeout: float = 30.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

        self._sock: socket.socket | None = None
        self._send_lock = threading.Lock()

        self._compression_threshold: int = -1  # -1 = disabled

        self._encryptor = None
        self._decryptor = None

        self._recv_buf = bytearray()

    # ── Connection lifecycle ──────────────────────────────────────────────────

    def connect(self) -> None:
        """Open the TCP socket and connect to the server."""
        try:
            self._sock = socket.create_connection(
                (self.host, self.port), timeout=self.timeout
            )
            self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError as e:
            raise exc.ConnectionError(f"Cannot connect to {self.host}:{self.port} — {e}") from e

    def close(self) -> None:
        """Close the socket gracefully."""
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._sock.close()
            self._sock = None

    @property
    def is_connected(self) -> bool:
        return self._sock is not None

    # ── Encryption ────────────────────────────────────────────────────────────

    def enable_encryption(self, shared_secret: bytes) -> None:
        """
        Enable AES-128/CFB8 encryption with *shared_secret* as both key and IV.
        Must be called after EncryptionResponse is sent.
        """
        cipher_enc = Cipher(
            algorithms.AES(shared_secret),
            modes.CFB8(shared_secret),
            backend=default_backend(),
        )
        cipher_dec = Cipher(
            algorithms.AES(shared_secret),
            modes.CFB8(shared_secret),
            backend=default_backend(),
        )
        self._encryptor = cipher_enc.encryptor()
        self._decryptor = cipher_dec.decryptor()

    # ── Compression ───────────────────────────────────────────────────────────

    def set_compression(self, threshold: int) -> None:
        """Enable compression for packets whose uncompressed length ≥ threshold."""
        self._compression_threshold = threshold

    # ── Sending ───────────────────────────────────────────────────────────────

    def send_packet(self, packet: Packet) -> None:
        """Frame and send a packet, applying compression/encryption as configured."""
        payload_buf = PacketBuffer()
        payload_buf.write_varint(packet.packet_id)
        packet.encode(payload_buf)
        payload = payload_buf.getvalue()

        if self._compression_threshold >= 0:
            raw = self._build_compressed(payload)
        else:
            raw = write_varint(len(payload)) + payload

        if self._encryptor is not None:
            raw = self._encryptor.update(raw)

        with self._send_lock:
            self._raw_send(raw)

    def send_raw(self, data: bytes) -> None:
        """Send raw bytes (pre-framed, pre-encrypted)."""
        if self._encryptor is not None:
            data = self._encryptor.update(data)
        with self._send_lock:
            self._raw_send(data)

    def _build_compressed(self, payload: bytes) -> bytes:
        """Build a compression-framed packet from uncompressed payload."""
        if len(payload) >= self._compression_threshold:
            compressed = zlib.compress(payload)
            data_length = write_varint(len(payload))
            packet_data = data_length + compressed
        else:
            packet_data = write_varint(0) + payload
        return write_varint(len(packet_data)) + packet_data

    def _raw_send(self, data: bytes) -> None:
        if not self._sock:
            raise exc.ConnectionError("Not connected")
        try:
            self._sock.sendall(data)
        except OSError as e:
            raise exc.ConnectionError(f"Send failed: {e}") from e

    # ── Receiving ─────────────────────────────────────────────────────────────

    def read_packet_raw(self) -> tuple[int, PacketBuffer]:
        """
        Block until a full packet arrives.

        Returns (packet_id, PacketBuffer positioned after the packet_id).
        Applies decryption and decompression transparently.
        """
        # 1. Read the outer length VarInt
        length = self._read_varint_from_socket()

        # 2. Read the packet body
        body = self._read_exactly(length)

        # 3. Decompress if needed
        if self._compression_threshold >= 0:
            body = self._decompress(body)

        # 4. Parse packet_id and return buffer
        buf = PacketBuffer(body)
        packet_id = buf.read_varint()
        return packet_id, buf

    def _read_varint_from_socket(self) -> int:
        """Read one VarInt byte-by-byte from the socket (with decryption)."""
        result = 0
        for shift in range(0, 35, 7):
            raw = self._recv_byte()
            byte = raw[0]
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
        else:
            raise exc.ProtocolError("VarInt too large (> 5 bytes)")
        return result

    def _recv_byte(self) -> bytes:
        if not self._sock:
            raise exc.ConnectionError("Not connected")
        try:
            raw = self._sock.recv(1)
        except OSError as e:
            raise exc.ConnectionError(f"Receive failed: {e}") from e
        if not raw:
            raise exc.ConnectionError("Connection closed by server")
        if self._decryptor is not None:
            raw = self._decryptor.update(raw)
        return raw

    def _read_exactly(self, n: int) -> bytes:
        """Read exactly n (possibly encrypted) bytes from the socket."""
        buf = b""
        while len(buf) < n:
            if not self._sock:
                raise exc.ConnectionError("Not connected")
            try:
                chunk = self._sock.recv(n - len(buf))
            except OSError as e:
                raise exc.ConnectionError(f"Receive failed: {e}") from e
            if not chunk:
                raise exc.ConnectionError("Connection closed by server")
            if self._decryptor is not None:
                chunk = self._decryptor.update(chunk)
            buf += chunk
        return buf

    def _decompress(self, body: bytes) -> bytes:
        """Strip the data-length VarInt and decompress if non-zero."""
        data_length, consumed = varint_from_bytes(body)
        payload = body[consumed:]
        if data_length == 0:
            return payload
        decompressed = zlib.decompress(payload)
        if len(decompressed) != data_length:
            raise exc.ProtocolError(
                f"Decompressed length mismatch: expected {data_length}, got {len(decompressed)}"
            )
        return decompressed
