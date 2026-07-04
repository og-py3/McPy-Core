"""
VersionAdapter — base class for protocol version adapters.

Supports every Minecraft Java Edition protocol from 1.7.2 (protocol 4)
through 1.21.11 (protocol 775), plus snapshot builds (0x40000000+).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcpycore.protocol.registry.registry import PacketRegistry


class VersionAdapter(ABC):
    """Protocol version adapter base class."""

    PROTOCOL_VERSION: int = 0
    NAME: str = ""

    @abstractmethod
    def build_registry(self) -> "PacketRegistry":
        """Return a PacketRegistry for this version."""

    def is_snapshot(self) -> bool:
        return self.PROTOCOL_VERSION >= 0x40000000

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(protocol={self.PROTOCOL_VERSION}, name={self.NAME!r})"


# ── 1.7.x ─────────────────────────────────────────────────────────────────────
PROTOCOL_1_7_2  = 4
PROTOCOL_1_7_6  = 5
PROTOCOL_1_7_10 = 5

# ── 1.8.x ─────────────────────────────────────────────────────────────────────
PROTOCOL_1_8    = 47
PROTOCOL_1_8_9  = 47

# ── 1.9.x ─────────────────────────────────────────────────────────────────────
PROTOCOL_1_9    = 107
PROTOCOL_1_9_1  = 108
PROTOCOL_1_9_2  = 109
PROTOCOL_1_9_4  = 110

# ── 1.10.x ────────────────────────────────────────────────────────────────────
PROTOCOL_1_10   = 210

# ── 1.11.x ────────────────────────────────────────────────────────────────────
PROTOCOL_1_11   = 315
PROTOCOL_1_11_2 = 316

# ── 1.12.x ────────────────────────────────────────────────────────────────────
PROTOCOL_1_12   = 335
PROTOCOL_1_12_1 = 338
PROTOCOL_1_12_2 = 340

# ── 1.13.x ────────────────────────────────────────────────────────────────────
PROTOCOL_1_13   = 393
PROTOCOL_1_13_1 = 401
PROTOCOL_1_13_2 = 404

# ── 1.14.x ────────────────────────────────────────────────────────────────────
PROTOCOL_1_14   = 477
PROTOCOL_1_14_1 = 480
PROTOCOL_1_14_2 = 485
PROTOCOL_1_14_3 = 490
PROTOCOL_1_14_4 = 498

# ── 1.15.x ────────────────────────────────────────────────────────────────────
PROTOCOL_1_15   = 573
PROTOCOL_1_15_1 = 575
PROTOCOL_1_15_2 = 578

# ── 1.16.x ────────────────────────────────────────────────────────────────────
PROTOCOL_1_16   = 735
PROTOCOL_1_16_1 = 736
PROTOCOL_1_16_2 = 751
PROTOCOL_1_16_3 = 753
PROTOCOL_1_16_4 = 754
PROTOCOL_1_16_5 = 754

# ── 1.17.x ────────────────────────────────────────────────────────────────────
PROTOCOL_1_17   = 755
PROTOCOL_1_17_1 = 756

# ── 1.18.x ────────────────────────────────────────────────────────────────────
PROTOCOL_1_18   = 757
PROTOCOL_1_18_1 = 757
PROTOCOL_1_18_2 = 758

# ── 1.19.x ────────────────────────────────────────────────────────────────────
PROTOCOL_1_19   = 759
PROTOCOL_1_19_1 = 760
PROTOCOL_1_19_2 = 760
PROTOCOL_1_19_3 = 761
PROTOCOL_1_19_4 = 762

# ── 1.20.x ────────────────────────────────────────────────────────────────────
PROTOCOL_1_20   = 763
PROTOCOL_1_20_1 = 763
PROTOCOL_1_20_2 = 764
PROTOCOL_1_20_3 = 765
PROTOCOL_1_20_4 = 765
PROTOCOL_1_20_5 = 766
PROTOCOL_1_20_6 = 766

# ── 1.21.x ────────────────────────────────────────────────────────────────────
PROTOCOL_1_21    = 767
PROTOCOL_1_21_1  = 767
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

PROTOCOL_LATEST = PROTOCOL_1_21_11
SNAPSHOT_BASE   = 0x40000000

# ── Lookup table ──────────────────────────────────────────────────────────────

_VERSION_NAMES: dict[int, str] = {
    4: "1.7.2",
    5: "1.7.10",
    47: "1.8.9",
    107: "1.9",
    108: "1.9.1",
    109: "1.9.2",
    110: "1.9.4",
    210: "1.10",
    315: "1.11",
    316: "1.11.2",
    335: "1.12",
    338: "1.12.1",
    340: "1.12.2",
    393: "1.13",
    401: "1.13.1",
    404: "1.13.2",
    477: "1.14",
    480: "1.14.1",
    485: "1.14.2",
    490: "1.14.3",
    498: "1.14.4",
    573: "1.15",
    575: "1.15.1",
    578: "1.15.2",
    735: "1.16",
    736: "1.16.1",
    751: "1.16.2",
    753: "1.16.3",
    754: "1.16.5",
    755: "1.17",
    756: "1.17.1",
    757: "1.18.1",
    758: "1.18.2",
    759: "1.19",
    760: "1.19.2",
    761: "1.19.3",
    762: "1.19.4",
    763: "1.20.1",
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


def version_name(protocol: int) -> str:
    """Return a human-readable string for a protocol version number."""
    if protocol >= SNAPSHOT_BASE:
        return f"snapshot-{protocol - SNAPSHOT_BASE:#06x} (protocol {protocol})"
    return _VERSION_NAMES.get(protocol, f"unknown-{protocol}")


def is_snapshot(protocol: int) -> bool:
    return protocol >= SNAPSHOT_BASE


def nearest_stable(protocol: int) -> int:
    """Return the nearest known stable protocol for a snapshot/unknown version."""
    if not is_snapshot(protocol):
        return protocol
    return PROTOCOL_LATEST


ALL_STABLE_PROTOCOLS: list[int] = sorted(_VERSION_NAMES.keys())


# ── Feature flags by era ──────────────────────────────────────────────────────

def has_configuration_state(protocol: int) -> bool:
    """True for 1.20.2+ (protocol 764+): login → configuration → play."""
    return protocol >= 764


def has_varint_keepalive(protocol: int) -> bool:
    """True for 1.9–1.11 where Keep Alive uses VarInt id (not int/long)."""
    return 107 <= protocol <= 316


def has_long_keepalive(protocol: int) -> bool:
    """True for 1.12+ where Keep Alive uses a Long id."""
    return protocol >= 335


def has_uuid_in_login_start(protocol: int) -> bool:
    """True for 1.19.4+ (762+): Login Start includes UUID field."""
    return protocol >= 762


def has_optional_uuid_in_login_start(protocol: int) -> bool:
    """True for 1.19.3 (761): Login Start includes optional UUID bool+uuid."""
    return protocol == 761


def has_chat_signing(protocol: int) -> bool:
    """True for 1.19 (759–760): requires signed chat messages."""
    return 759 <= protocol <= 760


def uses_legacy_login_success_string_uuid(protocol: int) -> bool:
    """True for 1.7.x–1.8.x: Login Success sends UUID as string, not bytes."""
    return protocol <= 47


# ── Adapter registry ──────────────────────────────────────────────────────────

_ADAPTERS: dict[int, type[VersionAdapter]] = {}


def register_adapter(cls: type[VersionAdapter]) -> type[VersionAdapter]:
    """Decorator to register a VersionAdapter."""
    _ADAPTERS[cls.PROTOCOL_VERSION] = cls
    return cls


def get_adapter(protocol: int) -> type[VersionAdapter] | None:
    if is_snapshot(protocol):
        protocol = nearest_stable(protocol)
    return _ADAPTERS.get(protocol)
