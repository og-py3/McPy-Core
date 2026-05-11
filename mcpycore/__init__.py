"""
McPy-Core — Professional async-first Minecraft Java Edition protocol library.

Supports Minecraft 1.20.2 → 1.21.11 (protocols 764–775) + snapshot builds.

Quick start::

    import asyncio
    from mcpycore import MinecraftClient
    from mcpycore.events.emitter import Events

    async def main():
        client = MinecraftClient(
            host="play.example.com",
            username="BotName",
            debug=True,
        )

        @client.event
        async def on_connect(c):
            print(f"Connected! version={c.version_name}")

        @client.event
        async def on_chat(message, sender):
            print(f"[{sender}] {message}")
            await client.send_chat(f"Echo: {message}")

        @client.event
        async def on_disconnect(reason):
            print(f"Disconnected: {reason}")

        await client.start()

    asyncio.run(main())
"""

from mcpycore.client.client import MinecraftClient
from mcpycore.client.connection import (
    PlayerProfile, OfflineProfile, LoginError, ConnectionError,
)
from mcpycore.client.reconnect import (
    ReconnectPolicy, NoReconnect, FixedDelay,
    ExponentialBackoff, InfiniteRetry,
)
from mcpycore.events.emitter import AsyncEventEmitter, Events
from mcpycore.protocol.packets.base import Packet, packet
from mcpycore.protocol.registry.registry import PacketRegistry, Direction, global_registry
from mcpycore.protocol.serializers.buffer import PacketBuffer
from mcpycore.protocol.serializers.nbt import (
    parse_nbt, nbt_to_dict,
    NBTTag, NBTCompound, NBTList, NBTInt, NBTString,
    TAG_COMPOUND, TAG_INT, TAG_STRING,
)
from mcpycore.protocol.states.machine import State, ProtocolStateMachine
from mcpycore.protocol.versions.base import (
    VersionAdapter,
    PROTOCOL_1_20_2, PROTOCOL_1_20_4, PROTOCOL_1_20_6,
    PROTOCOL_1_21, PROTOCOL_1_21_1, PROTOCOL_1_21_2, PROTOCOL_1_21_4,
    PROTOCOL_1_21_5, PROTOCOL_1_21_11,
    PROTOCOL_LATEST, SNAPSHOT_BASE,
    version_name, is_snapshot, nearest_stable, ALL_STABLE_PROTOCOLS,
)
from mcpycore.crypto.encryption import EncryptionManager
from mcpycore.compression.compression import CompressionManager
from mcpycore.debug.inspector import PacketInspector
from mcpycore.utils.logging import setup_logging, get_logger
from mcpycore.utils.metrics import MetricsCollector

__version__      = "1.0.0"
__author__       = "McPy-Core Contributors"
__license__      = "MIT"
__mc_versions__  = "1.20.2 – 1.21.11"
__protocols__    = "764 – 775 + snapshots"
__python_min__   = "3.12"

__all__ = [
    # Client
    "MinecraftClient",
    "PlayerProfile",
    "OfflineProfile",
    "LoginError",
    "ConnectionError",
    # Reconnect policies
    "ReconnectPolicy",
    "NoReconnect",
    "FixedDelay",
    "ExponentialBackoff",
    "InfiniteRetry",
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
    # Versions
    "VersionAdapter",
    "PROTOCOL_1_20_2", "PROTOCOL_1_20_4", "PROTOCOL_1_20_6",
    "PROTOCOL_1_21", "PROTOCOL_1_21_1", "PROTOCOL_1_21_2",
    "PROTOCOL_1_21_4", "PROTOCOL_1_21_5", "PROTOCOL_1_21_11",
    "PROTOCOL_LATEST", "SNAPSHOT_BASE",
    "version_name", "is_snapshot", "nearest_stable", "ALL_STABLE_PROTOCOLS",
    # Infrastructure
    "EncryptionManager",
    "CompressionManager",
    "PacketInspector",
    "setup_logging",
    "get_logger",
    "MetricsCollector",
]
