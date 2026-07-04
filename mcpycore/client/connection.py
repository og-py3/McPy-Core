"""
Connection — handles the full Minecraft protocol handshake → login → play lifecycle.

Supports every Minecraft Java Edition protocol from 1.7.2 (protocol 4) through
1.21.11 (protocol 775) plus snapshot builds.

Version-specific behaviour is controlled by feature flags from
``mcpycore.protocol.versions.base``:
  • ``has_configuration_state``      — 1.20.2+ adds a Configuration phase
  • ``has_uuid_in_login_start``      — 1.19.4+ Login Start includes UUID
  • ``has_optional_uuid_in_login_start`` — 1.19.3 uses optional UUID bool
  • ``has_long_keepalive``           — 1.12+ keep-alive ID is a Long
  • ``has_varint_keepalive``         — 1.9–1.11 keep-alive ID is a VarInt
  • ``uses_legacy_login_success_string_uuid`` — 1.7/1.8 UUID as string
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import struct
import urllib.request
import uuid
from typing import TYPE_CHECKING

from mcpycore.compression.compression import CompressionManager
from mcpycore.crypto.encryption import EncryptionManager
from mcpycore.network.stream import AsyncStream, StreamError
from mcpycore.protocol.serializers.buffer import PacketBuffer
from mcpycore.protocol.states.machine import State, ProtocolStateMachine
from mcpycore.protocol.versions.base import (
    version_name,
    has_configuration_state,
    has_uuid_in_login_start,
    has_optional_uuid_in_login_start,
    has_long_keepalive,
    has_varint_keepalive,
    uses_legacy_login_success_string_uuid,
)

if TYPE_CHECKING:
    from mcpycore.humanize.humanizer import Humanizer

log = logging.getLogger(__name__)


# ── Exceptions ────────────────────────────────────────────────────────────────

class ConnectionError(Exception):
    """Raised when the connection fails to establish or is lost."""


class LoginError(ConnectionError):
    """Raised when login is rejected by the server."""


# ── Player profiles ───────────────────────────────────────────────────────────

class PlayerProfile:
    """Holds the authenticated player identity for online-mode connections."""

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
    """
    Offline-mode profile — connects to servers with online-mode disabled.

    UUID is derived deterministically from the username using the same
    algorithm the Minecraft server uses for offline players.
    """

    def __init__(self, username: str) -> None:
        offline_uid = uuid.uuid3(uuid.NAMESPACE_DNS, f"OfflinePlayer:{username}")
        super().__init__(username, player_uuid=offline_uid)


# ── Connection ────────────────────────────────────────────────────────────────

class Connection:
    """
    Manages one full Minecraft connection lifecycle.

    Supports every protocol era:
      1.7.x  (4–5)   : handshake → login → play (INT keep-alive)
      1.8.x  (47)    : handshake → login → play (INT keep-alive)
      1.9–1.11 (107–316): handshake → login → play (VarInt keep-alive)
      1.12–1.19 (335–763): handshake → login → play (Long keep-alive)
      1.20.2+ (764+) : handshake → login → configuration → play (Long keep-alive)
    """

    def __init__(
        self,
        host: str,
        port: int = 25565,
        profile: PlayerProfile | None = None,
        protocol_version: int = 775,
        timeout: float = 30.0,
        humanizer: "Humanizer | None" = None,
    ) -> None:
        self.host = host
        self.port = port
        self.profile = profile or OfflineProfile("McPyCoreBot")
        self.protocol_version = protocol_version
        self.timeout = timeout
        self._humanizer = humanizer

        self._stream: AsyncStream | None = None
        self.state_machine = ProtocolStateMachine(on_transition=self._on_state_change)

        # Populated after successful play login
        self.entity_id: int = 0
        self.game_mode: int = 0

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Open TCP connection and complete the full protocol handshake."""
        log.info(
            "Connecting to %s:%d  protocol=%d (%s)",
            self.host, self.port,
            self.protocol_version, version_name(self.protocol_version),
        )
        self._stream = await AsyncStream.open(self.host, self.port, self.timeout)

        if self._humanizer:
            await self._humanizer.pre_handshake()

        await self._handshake()

        if self._humanizer:
            await self._humanizer.pre_login()

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
            raise ConnectionError("Not connected — call connect() first")
        return self._stream

    async def read_packet(self) -> tuple[int, PacketBuffer]:
        return await self.stream.read_packet()

    async def write_packet(self, packet_id: int, payload: bytes = b"") -> None:
        await self.stream.write_packet(packet_id, payload)

    @property
    def is_connected(self) -> bool:
        return self._stream is not None and not self._stream.is_closed

    # ── Handshake ─────────────────────────────────────────────────────────

    async def _handshake(self) -> None:
        """
        Send the Handshake packet (0x00 in HANDSHAKING state) and move to LOGIN.

        Format is identical across all protocol versions.
        """
        buf = PacketBuffer()
        buf.write_varint(self.protocol_version)
        buf.write_string(self.host)
        buf.write_ushort(self.port)
        buf.write_varint(2)  # next_state = 2 (LOGIN)
        await self.stream.write_packet(0x00, buf.flush())
        log.debug("Handshake sent")

    # ── Login ─────────────────────────────────────────────────────────────

    async def _login(self) -> None:
        """
        Drive the LOGIN state.

        Sends LoginStart, handles optional Encryption + Compression,
        then reads LoginSuccess and routes to the correct next state.
        """
        self.state_machine.transition(State.LOGIN)
        await self._send_login_start()

        while True:
            packet_id, buf = await self.read_packet()

            if packet_id == 0x00:               # CB: Login Disconnect
                reason = _try_read_string(buf)
                raise LoginError(f"Login rejected by server: {reason}")

            elif packet_id == 0x01:             # CB: Encryption Request
                if not self.profile.access_token:
                    raise LoginError(
                        "Server requires online-mode authentication. "
                        "Provide a valid Microsoft access_token to PlayerProfile."
                    )
                await self._handle_encryption(buf)

            elif packet_id == 0x02:             # CB: Login Success
                await self._handle_login_success(buf)
                break

            elif packet_id == 0x03:             # CB: Set Compression
                threshold = buf.read_varint()
                self.stream.compression.set_threshold(threshold)
                log.debug("Compression enabled, threshold=%d", threshold)

            elif packet_id == 0x04:             # CB: Login Plugin Request (1.13+)
                msg_id = buf.read_varint()
                _channel = buf.read_string()    # drain channel name
                buf.remaining()                 # drain payload
                # Respond with "not understood"
                resp = PacketBuffer()
                resp.write_varint(msg_id)
                resp.write_bool(False)
                await self.stream.write_packet(0x02, resp.flush())

            else:
                buf.remaining()                 # drain unknown packets

    def _build_login_start(self) -> PacketBuffer:
        """
        Build the SB LoginStart packet (0x00 in LOGIN state).

        UUID field behaviour by protocol:
          < 761  : just [string: username]
          761    : [string: username, bool: hasUUID, uuid]
          762+   : [string: username, uuid]
        """
        ls = PacketBuffer()
        ls.write_string(self.profile.username)

        if has_uuid_in_login_start(self.protocol_version):          # 762+
            ls.write_uuid(self.profile.player_uuid)
        elif has_optional_uuid_in_login_start(self.protocol_version):  # 761
            ls.write_bool(True)
            ls.write_uuid(self.profile.player_uuid)
        # else: < 761 — username only

        return ls

    async def _send_login_start(self) -> None:
        ls = self._build_login_start()
        await self.stream.write_packet(0x00, ls.flush())
        log.debug("LoginStart sent (user=%s)", self.profile.username)

    async def _handle_login_success(self, buf: PacketBuffer) -> None:
        """Read LoginSuccess and transition to the next state."""
        if uses_legacy_login_success_string_uuid(self.protocol_version):
            # 1.7/1.8: [string: uuid, string: username]
            _uuid_str = buf.read_string()
            _username = buf.read_string()
        else:
            # 1.9+: [uuid (16 bytes), string: username, ...]
            try:
                _server_uuid = buf.read_uuid()
            except Exception:
                pass
            try:
                _username = buf.read_string()
            except Exception:
                pass
            buf.remaining()  # drain properties (1.19.1+) and other fields

        log.debug("LoginSuccess received — user=%s", self.profile.username)

        if self._humanizer:
            await self._humanizer.post_login()

        if has_configuration_state(self.protocol_version):
            await self._configuration()
        else:
            self.state_machine.transition(State.PLAY)
            log.info("Entered PLAY state (protocol %d — no configuration phase)",
                     self.protocol_version)

    # ── Encryption ────────────────────────────────────────────────────────

    async def _handle_encryption(self, buf: PacketBuffer) -> None:
        """
        Handle the CB Encryption Request packet and send Encryption Response.

        Performs Mojang session auth before activating AES-128-CFB8.
        """
        from mcpycore.crypto.encryption import EncryptionManager

        server_id_bytes = buf.read_string().encode("ascii")
        pub_key_len = buf.read_varint()
        pub_key_der  = buf.read_bytes(pub_key_len)
        verify_token_len = buf.read_varint()
        verify_token    = buf.read_bytes(verify_token_len)

        # Generate 16-byte shared secret
        shared_secret = os.urandom(16)

        # RSA-encrypt shared secret and verify token
        enc_mgr = EncryptionManager()
        enc_secret = enc_mgr.rsa_encrypt(pub_key_der, shared_secret)
        enc_verify  = enc_mgr.rsa_encrypt(pub_key_der, verify_token)

        # Compute server hash for session auth
        server_hash = _compute_server_hash(server_id_bytes, shared_secret, pub_key_der)

        # Authenticate with Mojang
        await self._mojang_join(server_hash)

        # Send Encryption Response
        er = PacketBuffer()
        er.write_varint(len(enc_secret))
        er._write_raw(enc_secret)
        er.write_varint(len(enc_verify))
        er._write_raw(enc_verify)
        await self.stream.write_packet(0x01, er.flush())

        # Activate encryption
        self.stream.encryption.enable(shared_secret)
        log.debug("Encryption activated")

    async def _mojang_join(self, server_hash: str) -> None:
        """POST to Mojang's session server to authenticate."""
        payload = json.dumps({
            "accessToken":     self.profile.access_token,
            "selectedProfile": str(self.profile.player_uuid).replace("-", ""),
            "serverId":        server_hash,
        }).encode()
        req = urllib.request.Request(
            "https://sessionserver.mojang.com/session/minecraft/join",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        await asyncio.get_event_loop().run_in_executor(
            None, urllib.request.urlopen, req
        )

    # ── Configuration (1.20.2+) ───────────────────────────────────────────

    async def _configuration(self) -> None:
        """
        Handle the CONFIGURATION state (protocol 764 / Minecraft 1.20.2+).

        Packets in this state use different IDs than the play state.
        We handle FinishConfiguration, SelectKnownPacks, and drain the rest.
        """
        self.state_machine.transition(State.CONFIGURATION)
        log.debug("Entered CONFIGURATION state")

        # Determine version-specific IDs for this state
        cb_finish, sb_finish, cb_known_packs, sb_known_packs = \
            _config_packet_ids(self.protocol_version)

        # Send ClientInformation (SB 0x00)
        ci = PacketBuffer()
        ci.write_string("en_us")
        ci.write_byte(10)        # view_distance
        ci.write_varint(0)       # chat_mode (enabled)
        ci.write_bool(True)      # chat_colors
        ci.write_ubyte(0x7F)     # skin_parts (all enabled)
        ci.write_varint(1)       # main_hand (right)
        ci.write_bool(False)     # text_filtering
        ci.write_bool(True)      # allow_listing
        await self.stream.write_packet(0x00, ci.flush())

        if self._humanizer:
            await self._humanizer.config_settle()

        while True:
            packet_id, buf = await self.read_packet()

            if packet_id == cb_finish:          # FinishConfiguration (CB)
                await self.stream.write_packet(sb_finish)
                log.debug("Configuration finished")
                break

            elif packet_id == 0x00:             # Disconnect (CB) in config
                reason = _try_read_string(buf)
                raise LoginError(f"Disconnected in configuration: {reason}")

            elif packet_id == cb_known_packs:   # SelectKnownPacks (CB)
                # Respond with empty list of known packs
                resp = PacketBuffer()
                resp.write_varint(0)
                await self.stream.write_packet(sb_known_packs, resp.flush())

            else:
                buf.remaining()                 # drain: registry data, plugin msgs, etc.

        self.state_machine.transition(State.PLAY)
        log.info("Entered PLAY state")

    # ── Keep-alive helpers (called by MinecraftClient) ────────────────────

    def keepalive_id_type(self) -> str:
        """
        Return the keep-alive ID wire type for this protocol version.

        Returns one of ``'int'``, ``'varint'``, or ``'long'``.
        """
        if has_long_keepalive(self.protocol_version):
            return "long"
        if has_varint_keepalive(self.protocol_version):
            return "varint"
        return "int"   # 1.7 / 1.8

    def read_keepalive_id(self, buf: PacketBuffer) -> int:
        """Read a keep-alive ID from *buf* using the correct type for this version."""
        t = self.keepalive_id_type()
        if t == "long":
            return buf.read_long()
        if t == "varint":
            return buf.read_varint()
        return buf.read_int()

    def write_keepalive_id(self, buf: PacketBuffer, ka_id: int) -> None:
        """Write a keep-alive ID into *buf* using the correct type for this version."""
        t = self.keepalive_id_type()
        if t == "long":
            buf.write_long(ka_id)
        elif t == "varint":
            buf.write_varint(ka_id)
        else:
            buf.write_int(ka_id)

    # ── State callbacks ───────────────────────────────────────────────────

    def _on_state_change(self, old: State, new: State) -> None:
        log.debug("Protocol state: %s → %s", old.value, new.value)

    def __repr__(self) -> str:
        return (
            f"Connection({self.host}:{self.port}, "
            f"protocol={self.protocol_version}, "
            f"state={self.state_machine.current.value}, "
            f"connected={self.is_connected})"
        )


# ── Private helpers ───────────────────────────────────────────────────────────

def _compute_server_hash(
    server_id: bytes,
    shared_secret: bytes,
    pub_key_der: bytes,
) -> str:
    """Compute the Minecraft server hash for Mojang session auth."""
    sha1 = hashlib.sha1()
    sha1.update(server_id)
    sha1.update(shared_secret)
    sha1.update(pub_key_der)
    digest = int.from_bytes(sha1.digest(), byteorder="big", signed=True)
    return format(digest, "x")


def _try_read_string(buf: PacketBuffer) -> str:
    """Read a string from *buf*, returning raw bytes on failure."""
    try:
        return buf.read_string()
    except Exception:
        return repr(bytes(buf.remaining()))


def _config_packet_ids(protocol: int) -> tuple[int, int, int, int]:
    """
    Return (cb_finish, sb_finish, cb_known_packs, sb_known_packs)
    for the configuration state at the given protocol version.

    These IDs shift slightly between 1.20.2 and 1.21.x.
    """
    if protocol >= 767:
        # 1.21+  (verified against wiki.vg)
        return (0x03, 0x03, 0x0E, 0x0F)
    if protocol >= 766:
        # 1.20.5 / 1.20.6
        return (0x03, 0x03, 0x0E, 0x0F)
    # 764–765 (1.20.2 – 1.20.4)
    return (0x03, 0x03, 0x0D, 0x0E)
