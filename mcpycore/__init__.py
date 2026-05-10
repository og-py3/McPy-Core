"""
Mcpycore — The ultimate Python library for Minecraft Java Edition servers.

Supports Minecraft 1.20.2 → 1.21.11 (protocol 764 → 775) plus snapshot builds.

Quick start::

    from mcpycore import MinecraftClient, OfflineAuth
    from mcpycore.versions import PROTOCOL_LATEST

    client = MinecraftClient("play.example.com", auth=OfflineAuth("Bot"),
                             protocol_version=PROTOCOL_LATEST)

    @client.on("chat_message")
    def on_chat(pkt):
        print(pkt.message)

    client.connect()
    client.run()
"""

from mcpycore.client import MinecraftClient
from mcpycore.authentication import OfflineAuth, MicrosoftAuth
from mcpycore.exceptions import (
    McpycoreError,
    McpycoreConnectionError,
    ConnectionError,          # backward-compatible alias for McpycoreConnectionError
    AuthenticationError,
    PacketError,
    ProtocolError,
    LoginKickError,
    PlayKickError,
)
from mcpycore.versions import (
    PROTOCOL_1_20_2, PROTOCOL_1_20_3, PROTOCOL_1_20_4,
    PROTOCOL_1_20_5, PROTOCOL_1_20_6,
    PROTOCOL_1_21, PROTOCOL_1_21_1,
    PROTOCOL_1_21_2, PROTOCOL_1_21_3, PROTOCOL_1_21_4,
    PROTOCOL_1_21_5, PROTOCOL_1_21_6, PROTOCOL_1_21_7,
    PROTOCOL_1_21_8, PROTOCOL_1_21_9, PROTOCOL_1_21_10,
    PROTOCOL_1_21_11,
    PROTOCOL_LATEST, SNAPSHOT_BASE,
    version_name, is_snapshot, is_supported, nearest_stable,
)
from mcpycore import events

__version__ = "0.4.0"
__mc_versions__ = "1.20.2 – 1.21.11"
__protocols__ = "764 – 775 + snapshots"

__all__ = [
    # Core
    "MinecraftClient",
    # Auth
    "OfflineAuth",
    "MicrosoftAuth",
    # Exceptions
    "McpycoreError",
    "McpycoreConnectionError",
    "ConnectionError",          # backward-compatible alias
    "AuthenticationError",
    "PacketError",
    "ProtocolError",
    "LoginKickError",
    "PlayKickError",
    # Version constants
    "PROTOCOL_1_20_2", "PROTOCOL_1_20_3", "PROTOCOL_1_20_4",
    "PROTOCOL_1_20_5", "PROTOCOL_1_20_6",
    "PROTOCOL_1_21", "PROTOCOL_1_21_1",
    "PROTOCOL_1_21_2", "PROTOCOL_1_21_3", "PROTOCOL_1_21_4",
    "PROTOCOL_1_21_5", "PROTOCOL_1_21_6", "PROTOCOL_1_21_7",
    "PROTOCOL_1_21_8", "PROTOCOL_1_21_9", "PROTOCOL_1_21_10",
    "PROTOCOL_1_21_11",
    "PROTOCOL_LATEST", "SNAPSHOT_BASE",
    "version_name", "is_snapshot", "is_supported", "nearest_stable",
    # Events module
    "events",
]
