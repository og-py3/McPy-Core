"""
McPy-Core — professional async-first Minecraft Java Edition protocol library.

Supports every Java Edition protocol from 1.7.2 (protocol 4) through 1.21.11
(protocol 775), plus snapshot builds.  Available for Python, JavaScript/
TypeScript, Java, Go, Rust, and C# via the WebSocket bridge (see
``mcpycore.bridge`` and the ``sdks/`` directory).

Quick start (Python)::

    import asyncio
    from mcpycore import MinecraftClient, HumanizeConfig

    async def main():
        client = MinecraftClient(
            host="play.example.com",
            username="BotName",
            protocol_version=775,          # 1.21.11 — change to match your server
            humanize=HumanizeConfig(       # anti-bot timing + auto-login bypass
                authme_enabled=True,
                authme_password="s3cret",
            ),
        )

        @client.event
        async def on_connect(c):
            print(f"Connected!  version={c.version_name}")

        @client.event
        async def on_chat(message, sender):
            print(f"[{sender}] {message}")

        await client.start()

    asyncio.run(main())

Multi-language usage::

    # Start the bridge first:
    #   python -m mcpycore.bridge --port 25580
    #
    # Then connect from any language SDK (see sdks/ directory).
"""
from __future__ import annotations

# ── High-level client ─────────────────────────────────────────────────────────
from mcpycore.client.client import MinecraftClient
from mcpycore.client.connection import (
    Connection,
    PlayerProfile,
    OfflineProfile,
    LoginError,
    ConnectionError,
)
from mcpycore.client.reconnect import (
    ReconnectPolicy,
    NoReconnect,
    FixedDelay,
    ExponentialBackoff,
    InfiniteRetry,
)

# ── Anti-bot / humanize ───────────────────────────────────────────────────────
from mcpycore.humanize.humanizer import HumanizeConfig, Humanizer

# ── Events ────────────────────────────────────────────────────────────────────
from mcpycore.events.emitter import AsyncEventEmitter, Events

# ── Protocol primitives ───────────────────────────────────────────────────────
from mcpycore.protocol.packets.base import Packet, packet
from mcpycore.protocol.registry.registry import PacketRegistry, Direction, global_registry
from mcpycore.protocol.serializers.buffer import PacketBuffer
from mcpycore.protocol.serializers.nbt import (
    parse_nbt,
    nbt_to_dict,
    NBTTag,
    NBTCompound,
    NBTList,
    NBTInt,
    NBTString,
    TAG_COMPOUND,
    TAG_INT,
    TAG_STRING,
)
from mcpycore.protocol.states.machine import State, ProtocolStateMachine
from mcpycore.protocol.versions.adapters import (
    get_cb_ids,
    get_sb_ids,
    list_supported_protocols,
)

# ── Version constants — every supported Java Edition version ──────────────────
from mcpycore.protocol.versions.base import (
    # 1.7.x
    PROTOCOL_1_7_2,
    PROTOCOL_1_7_6,
    PROTOCOL_1_7_10,
    # 1.8.x
    PROTOCOL_1_8,
    PROTOCOL_1_8_9,
    # 1.9.x
    PROTOCOL_1_9,
    PROTOCOL_1_9_1,
    PROTOCOL_1_9_2,
    PROTOCOL_1_9_4,
    # 1.10.x
    PROTOCOL_1_10,
    # 1.11.x
    PROTOCOL_1_11,
    PROTOCOL_1_11_2,
    # 1.12.x
    PROTOCOL_1_12,
    PROTOCOL_1_12_1,
    PROTOCOL_1_12_2,
    # 1.13.x
    PROTOCOL_1_13,
    PROTOCOL_1_13_1,
    PROTOCOL_1_13_2,
    # 1.14.x
    PROTOCOL_1_14,
    PROTOCOL_1_14_1,
    PROTOCOL_1_14_2,
    PROTOCOL_1_14_3,
    PROTOCOL_1_14_4,
    # 1.15.x
    PROTOCOL_1_15,
    PROTOCOL_1_15_1,
    PROTOCOL_1_15_2,
    # 1.16.x
    PROTOCOL_1_16,
    PROTOCOL_1_16_1,
    PROTOCOL_1_16_2,
    PROTOCOL_1_16_3,
    PROTOCOL_1_16_4,
    PROTOCOL_1_16_5,
    # 1.17.x
    PROTOCOL_1_17,
    PROTOCOL_1_17_1,
    # 1.18.x
    PROTOCOL_1_18,
    PROTOCOL_1_18_1,
    PROTOCOL_1_18_2,
    # 1.19.x
    PROTOCOL_1_19,
    PROTOCOL_1_19_1,
    PROTOCOL_1_19_2,
    PROTOCOL_1_19_3,
    PROTOCOL_1_19_4,
    # 1.20.x
    PROTOCOL_1_20,
    PROTOCOL_1_20_1,
    PROTOCOL_1_20_2,
    PROTOCOL_1_20_3,
    PROTOCOL_1_20_4,
    PROTOCOL_1_20_5,
    PROTOCOL_1_20_6,
    # 1.21.x
    PROTOCOL_1_21,
    PROTOCOL_1_21_1,
    PROTOCOL_1_21_2,
    PROTOCOL_1_21_3,
    PROTOCOL_1_21_4,
    PROTOCOL_1_21_5,
    PROTOCOL_1_21_6,
    PROTOCOL_1_21_7,
    PROTOCOL_1_21_8,
    PROTOCOL_1_21_9,
    PROTOCOL_1_21_10,
    PROTOCOL_1_21_11,
    # Helpers
    PROTOCOL_LATEST,
    SNAPSHOT_BASE,
    VersionAdapter,
    version_name,
    is_snapshot,
    nearest_stable,
    ALL_STABLE_PROTOCOLS,
    has_configuration_state,
    has_long_keepalive,
    has_varint_keepalive,
    has_uuid_in_login_start,
)

# ── Infrastructure ────────────────────────────────────────────────────────────
from mcpycore.crypto.encryption import EncryptionManager
from mcpycore.compression.compression import CompressionManager
from mcpycore.debug.inspector import PacketInspector
from mcpycore.utils.logging import setup_logging, get_logger
from mcpycore.utils.metrics import MetricsCollector

# ── Package metadata ──────────────────────────────────────────────────────────
__version__     = "2.0.0"
__author__      = "McPy-Core Contributors"
__license__     = "MIT"
__mc_versions__ = "1.7.2 – 1.21.11"
__protocols__   = "4 – 775 + snapshots"
__python_min__  = "3.11"

__all__ = [
    # Client
    "MinecraftClient",
    "Connection",
    "PlayerProfile",
    "OfflineProfile",
    "LoginError",
    "ConnectionError",
    # Reconnect
    "ReconnectPolicy",
    "NoReconnect",
    "FixedDelay",
    "ExponentialBackoff",
    "InfiniteRetry",
    # Humanize / anti-bot
    "HumanizeConfig",
    "Humanizer",
    # Events
    "AsyncEventEmitter",
    "Events",
    # Packets
    "Packet",
    "packet",
    "PacketBuffer",
    "PacketRegistry",
    "Direction",
    "global_registry",
    # NBT
    "parse_nbt",
    "nbt_to_dict",
    "NBTTag",
    "NBTCompound",
    "NBTList",
    "NBTInt",
    "NBTString",
    "TAG_COMPOUND",
    "TAG_INT",
    "TAG_STRING",
    # State machine
    "State",
    "ProtocolStateMachine",
    # Version adapter registry
    "get_cb_ids",
    "get_sb_ids",
    "list_supported_protocols",
    # Version constants — 1.7.x
    "PROTOCOL_1_7_2", "PROTOCOL_1_7_6", "PROTOCOL_1_7_10",
    # Version constants — 1.8.x
    "PROTOCOL_1_8", "PROTOCOL_1_8_9",
    # Version constants — 1.9.x
    "PROTOCOL_1_9", "PROTOCOL_1_9_1", "PROTOCOL_1_9_2", "PROTOCOL_1_9_4",
    # Version constants — 1.10–1.12
    "PROTOCOL_1_10",
    "PROTOCOL_1_11", "PROTOCOL_1_11_2",
    "PROTOCOL_1_12", "PROTOCOL_1_12_1", "PROTOCOL_1_12_2",
    # Version constants — 1.13–1.16
    "PROTOCOL_1_13", "PROTOCOL_1_13_1", "PROTOCOL_1_13_2",
    "PROTOCOL_1_14", "PROTOCOL_1_14_1", "PROTOCOL_1_14_2", "PROTOCOL_1_14_3", "PROTOCOL_1_14_4",
    "PROTOCOL_1_15", "PROTOCOL_1_15_1", "PROTOCOL_1_15_2",
    "PROTOCOL_1_16", "PROTOCOL_1_16_1", "PROTOCOL_1_16_2", "PROTOCOL_1_16_3",
    "PROTOCOL_1_16_4", "PROTOCOL_1_16_5",
    # Version constants — 1.17–1.19
    "PROTOCOL_1_17", "PROTOCOL_1_17_1",
    "PROTOCOL_1_18", "PROTOCOL_1_18_1", "PROTOCOL_1_18_2",
    "PROTOCOL_1_19", "PROTOCOL_1_19_1", "PROTOCOL_1_19_2", "PROTOCOL_1_19_3", "PROTOCOL_1_19_4",
    # Version constants — 1.20
    "PROTOCOL_1_20", "PROTOCOL_1_20_1",
    "PROTOCOL_1_20_2", "PROTOCOL_1_20_3", "PROTOCOL_1_20_4",
    "PROTOCOL_1_20_5", "PROTOCOL_1_20_6",
    # Version constants — 1.21
    "PROTOCOL_1_21", "PROTOCOL_1_21_1", "PROTOCOL_1_21_2", "PROTOCOL_1_21_3",
    "PROTOCOL_1_21_4", "PROTOCOL_1_21_5", "PROTOCOL_1_21_6", "PROTOCOL_1_21_7",
    "PROTOCOL_1_21_8", "PROTOCOL_1_21_9", "PROTOCOL_1_21_10", "PROTOCOL_1_21_11",
    # Version helpers
    "PROTOCOL_LATEST",
    "SNAPSHOT_BASE",
    "VersionAdapter",
    "version_name",
    "is_snapshot",
    "nearest_stable",
    "ALL_STABLE_PROTOCOLS",
    "has_configuration_state",
    "has_long_keepalive",
    "has_varint_keepalive",
    "has_uuid_in_login_start",
    # Infrastructure
    "EncryptionManager",
    "CompressionManager",
    "PacketInspector",
    "setup_logging",
    "get_logger",
    "MetricsCollector",
]
