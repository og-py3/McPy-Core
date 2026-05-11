"""
Connection — handles the full Minecraft protocol handshake → login → play lifecycle.

Wraps AsyncStream with protocol-aware login sequencing.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import uuid
from typing import TYPE_CHECKING

from mcpycore.network.stream import AsyncStream, StreamError
from mcpycore.protocol.serializers.buffer import PacketBuffer
from mcpycore.protocol.states.machine import State, ProtocolStateMachine
from mcpycore.protocol.versions.base import version_name, is_snapshot, nearest_stable

log = logging.getLogger(__name__)


class ConnectionError(Exception):
    """Raised when the connection fails to establish or is lost."""


class LoginError(ConnectionError):
    """Raised when login is rejected by the server."""


class PlayerProfile:
    """Holds the authenticated player identity."""

    def __init__(
        self,
        username: str,
        player_uuid: uuid.UUID | None = None,
        access_token: str | None = None,
    ) -> None:
        self.username = username
        self.player_uuid = player_uuid or uuid.uuid3(uuid.NAMESPACE_DNS, username)
        self.access_token = access_token

    def __repr__(self) -> str:
        return f"PlayerProfile({self.username!r}, uuid={self.player_uuid})"


class OfflineProfile(PlayerProfile):
    """Offline-mode profile (no authentication)."""

    def __init__(self, username: str) -> None:
        uid = uuid.uuid3(uuid.UUID("OfflinePlayer" + username, version=3)
                         if False else uuid.NAMESPACE_DNS, f"OfflinePlayer:{username}")
        super().__init__(username, player_uuid=uid)


class Connection:
    """
    Manages one full Minecraft connection lifecycle.

    Handles: handshake → login (with optional encryption) →
    configuration → play packet dispatch.
    """

    def __init__(
        self,
        host: str,
        port: int = 25565,
        profile: PlayerProfile | None = None,
        protocol_version: int = 775,
        timeout: float = 30.0,
    ) -> None:
        self.host = host
        self.port = port
        self.profile = profile or OfflineProfile("McPyCoreBot")
        self.protocol_version = protocol_version
        self.timeout = timeout

        self._stream: AsyncStream | None = None
        self.state_machine = ProtocolStateMachine(on_transition=self._on_state_change)

        # After login success, expose these
        self.entity_id: int = 0
        self.game_mode: int = 0

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Open TCP and complete handshake → login → configuration."""
        log.info("Connecting to %s:%d (protocol %d / %s)",
                 self.host, self.port, self.protocol_version,
                 version_name(self.protocol_version))
        self._stream = await AsyncStream.open(self.host, self.port, self.timeout)
        await self._handshake()
        await self._login()

    async def disconnect(self) -> None:
        """Gracefully close the connection."""
        if self._stream and not self._stream.is_closed:
            await self._stream.close()
        log.info("Disconnected from %s:%d", self.host, self.port)

    # ── Stream accessors ──────────────────────────────────────────────────

    @property
    def stream(self) -> AsyncStream:
        if self._stream is None:
            raise ConnectionError("Not connected")
        return self._stream

    async def read_packet(self) -> tuple[int, PacketBuffer]:
        return await self.stream.read_packet()

    async def write_packet(self, packet_id: int, payload: bytes = b"") -> None:
        await self.stream.write_packet(packet_id, payload)

    @property
    def is_connected(self) -> bool:
        return self._stream is not None and not self._stream.is_closed

    # ── Protocol sequence ─────────────────────────────────────────────────

    async def _handshake(self) -> None:
        buf = PacketBuffer()
        buf.write_varint(self.protocol_version)
        buf.write_string(self.host)
        buf.write_ushort(self.port)
        buf.write_varint(2)   # next_state = 2 (login)
        await self.stream.write_packet(0x00, buf.flush())
        self.state_machine.transition(State.LOGIN)
        log.debug("Handshake sent")

    async def _login(self) -> None:
        # Send LoginStart
        buf = PacketBuffer()
        buf.write_string(self.profile.username)
        buf.write_uuid(self.profile.player_uuid)
        await self.stream.write_packet(0x00, buf.flush())
        log.debug("LoginStart sent as %r", self.profile.username)

        while True:
            packet_id, buf = await self.read_packet()

            if packet_id == 0x00:
                reason = buf.read_string()
                raise LoginError(f"Disconnected during login: {reason}")

            elif packet_id == 0x01:
                await self._handle_encryption(buf)

            elif packet_id == 0x02:
                # Login success
                uid = buf.read_uuid()
                username = buf.read_string()
                self.profile.player_uuid = uid
                self.profile.username = username
                # Drain properties array
                count = buf.read_varint()
                for _ in range(count):
                    buf.read_string()   # name
                    buf.read_string()   # value
                    if buf.read_bool(): # has_signature
                        buf.read_string()
                # Ack
                await self.stream.write_packet(0x03)
                log.info("Login success: %s (%s)", username, uid)
                await self._configuration()
                break

            elif packet_id == 0x03:
                threshold = buf.read_varint()
                self.stream.enable_compression(threshold)
                log.debug("Compression enabled (threshold=%d)", threshold)

            elif packet_id == 0x04:
                # Plugin message request — respond with unsupported
                msg_id = buf.read_varint()
                resp = PacketBuffer()
                resp.write_varint(msg_id)
                resp.write_bool(False)
                await self.stream.write_packet(0x02, resp.flush())

    async def _handle_encryption(self, buf: PacketBuffer) -> None:
        from mcpycore.crypto.encryption import EncryptionManager
        server_id = buf.read_string()
        pub_key = buf.read_byte_array()
        verify_token = buf.read_byte_array()

        enc = self.stream.encryption
        shared_secret = enc.generate_shared_secret()

        # Session join (online mode)
        server_hash = enc.compute_server_hash(server_id, pub_key)
        await self._join_session(server_hash)

        # Send EncryptionResponse
        resp = PacketBuffer()
        resp.write_byte_array(enc.encrypt_rsa(pub_key, shared_secret))
        resp.write_byte_array(enc.encrypt_rsa(pub_key, verify_token))
        await self.stream.write_packet(0x01, resp.flush())
        self.stream.enable_encryption(shared_secret)
        log.debug("Encryption handshake complete")

    async def _join_session(self, server_hash: str) -> None:
        """POST to Mojang session server for online-mode auth."""
        import urllib.request, json
        if not self.profile.access_token:
            return  # offline mode — skip
        payload = json.dumps({
            "accessToken": self.profile.access_token,
            "selectedProfile": str(self.profile.player_uuid).replace("-", ""),
            "serverId": server_hash,
        }).encode()
        req = urllib.request.Request(
            "https://sessionserver.mojang.com/session/minecraft/join",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        await asyncio.get_event_loop().run_in_executor(None, urllib.request.urlopen, req)

    async def _configuration(self) -> None:
        """Handle the configuration state (1.20.2+)."""
        self.state_machine.transition(State.CONFIGURATION)

        # Send ClientInformation
        ci = PacketBuffer()
        ci.write_string("en_us")
        ci.write_byte(10)        # view_distance
        ci.write_varint(0)       # chat_mode
        ci.write_bool(True)      # chat_colors
        ci.write_ubyte(0x7F)     # skin_parts
        ci.write_varint(1)       # main_hand
        ci.write_bool(False)     # text_filtering
        ci.write_bool(True)      # allow_listing
        await self.stream.write_packet(0x00, ci.flush())

        while True:
            packet_id, buf = await self.read_packet()

            if packet_id == 0x03:     # FinishConfiguration
                await self.stream.write_packet(0x03)
                break
            elif packet_id == 0x00:   # CB Disconnect
                raise LoginError(f"Disconnected in configuration: {buf.read_string()}")
            elif packet_id == 0x0D:   # SelectKnownPacks → empty response
                await self.stream.write_packet(0x0E, PacketBuffer().flush())
            # All other config packets (registry data, plugin msgs) — drain
            else:
                buf.remaining()

        self.state_machine.transition(State.PLAY)
        log.info("Entered play state")

    def _on_state_change(self, old: State, new: State) -> None:
        log.debug("State transition: %s → %s", old.value, new.value)

    def __repr__(self) -> str:
        return (
            f"Connection({self.host}:{self.port}, "
            f"state={self.state_machine.current.value}, "
            f"connected={self.is_connected})"
        )
