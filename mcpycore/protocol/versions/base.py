"""
VersionAdapter — base class for protocol version adapters.

Each supported Minecraft version provides a subclass that declares:
- Packet ID overrides for packets whose IDs changed in that version
- Additional packets that only exist in that version
- Removed packets (if any)

The adapter is consulted when resolving a packet class or packet ID
for a specific protocol version.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcpycore.protocol.registry.registry import PacketRegistry


class VersionAdapter(ABC):
    """
    Protocol version adapter.

    Subclasses declare all version-specific packet ID overrides.
    """

    #: Numeric protocol version (e.g. 767 for 1.21.1)
    PROTOCOL_VERSION: int = 0
    #: Human-readable version name (e.g. "1.21.1")
    NAME: str = ""

    @abstractmethod
    def build_registry(self) -> "PacketRegistry":
        """
        Return a PacketRegistry populated with all packets for this version.

        Typically builds on top of the global_registry and applies overrides.
        """

    def is_snapshot(self) -> bool:
        return self.PROTOCOL_VERSION >= 0x40000000

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(protocol={self.PROTOCOL_VERSION}, name={self.NAME!r})"


# ── Version constant pool ─────────────────────────────────────────────────────

PROTOCOL_1_20_2  = 764
PROTOCOL_1_20_3  = 765
PROTOCOL_1_20_4  = 765    # same protocol as 1.20.3
PROTOCOL_1_20_5  = 766
PROTOCOL_1_20_6  = 766    # same protocol as 1.20.5
PROTOCOL_1_21    = 767
PROTOCOL_1_21_1  = 767    # same protocol as 1.21
PROTOCOL_1_21_2  = 768
PROTOCOL_1_21_3  = 768
PROTOCOL_1_21_4  = 769
PROTOCOL_1_21_5  = 770
PROTOCOL_1_21_6  = 771
PROTOCOL_1_21_7  = 772
PROTOCOL_1_21_8  = 773
PROTOCOL_1_21_9  = 774
PROTOCOL_1_21_10 = 775
PROTOCOL_1_21_11 = 775
PROTOCOL_LATEST  = PROTOCOL_1_21_11

SNAPSHOT_BASE = 0x40000000


def version_name(protocol: int) -> str:
    """Return a human-readable string for a protocol version number."""
    if protocol >= SNAPSHOT_BASE:
        snap_num = protocol - SNAPSHOT_BASE
        return f"snapshot-{snap_num:#06x} (protocol {protocol})"
    table = {
        764: "1.20.2",
        765: "1.20.4",
        766: "1.20.6",
        767: "1.21.1",
        768: "1.21.3",
        769: "1.21.4",
        770: "1.21.5",
        771: "1.21.6",
        772: "1.21.7",
        773: "1.21.8",
        774: "1.21.9",
        775: "1.21.11",
    }
    return table.get(protocol, f"unknown-{protocol}")


def is_snapshot(protocol: int) -> bool:
    return protocol >= SNAPSHOT_BASE


def nearest_stable(protocol: int) -> int:
    """Return the nearest known stable protocol for a snapshot/unknown version."""
    if not is_snapshot(protocol):
        return protocol
    return PROTOCOL_LATEST


ALL_STABLE_PROTOCOLS = sorted({
    764, 765, 766, 767, 768, 769, 770, 771, 772, 773, 774, 775,
})


# ── Registry of known adapters ────────────────────────────────────────────────

_ADAPTERS: dict[int, type[VersionAdapter]] = {}


def register_adapter(cls: type[VersionAdapter]) -> type[VersionAdapter]:
    """Decorator to register a VersionAdapter for its PROTOCOL_VERSION."""
    _ADAPTERS[cls.PROTOCOL_VERSION] = cls
    return cls


def get_adapter(protocol: int) -> type[VersionAdapter] | None:
    """Return the adapter for *protocol*, or None if not found."""
    if is_snapshot(protocol):
        protocol = nearest_stable(protocol)
    return _ADAPTERS.get(protocol)
