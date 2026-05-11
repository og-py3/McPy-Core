"""
PacketRegistry — maps (state, direction, packet_id) tuples to Packet classes.

Supports version-aware lookup with a configurable fallback strategy.
A module-level singleton ``global_registry`` is used by the @packet decorator.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from mcpycore.protocol.packets.base import Packet


class Direction:
    """Packet direction constants."""
    SERVERBOUND = "serverbound"
    CLIENTBOUND = "clientbound"


class RegistryEntry:
    """One registered packet mapping."""

    __slots__ = ("state", "direction", "packet_id", "cls", "version_min", "version_max")

    def __init__(
        self,
        state: str,
        direction: str,
        packet_id: int,
        cls: type,
        version_min: int | None,
        version_max: int | None,
    ) -> None:
        self.state       = state
        self.direction   = direction
        self.packet_id   = packet_id
        self.cls         = cls
        self.version_min = version_min
        self.version_max = version_max

    def matches_version(self, protocol: int) -> bool:
        if self.version_min is not None and protocol < self.version_min:
            return False
        if self.version_max is not None and protocol > self.version_max:
            return False
        return True


class PacketRegistry:
    """
    Central packet registry.

    All registrations are keyed by ``(state, direction, packet_id)``.
    When multiple classes share the same key (different versions), the
    one with the widest version range matching the query wins.
    """

    def __init__(self, name: str = "default") -> None:
        self.name = name
        # key → list[RegistryEntry] (may have multiple versions per ID)
        self._entries: dict[tuple[str, str, int], list[RegistryEntry]] = {}
        # reverse map for quick type → (state, direction, id) lookup
        self._reverse: dict[type, tuple[str, str, int]] = {}

    def register(
        self,
        state: str,
        direction: str,
        packet_id: int,
        cls: type,
        version_min: int | None = None,
        version_max: int | None = None,
    ) -> None:
        """Register a Packet class."""
        key = (state, direction, packet_id)
        entry = RegistryEntry(state, direction, packet_id, cls, version_min, version_max)
        self._entries.setdefault(key, []).append(entry)
        self._reverse[cls] = key

    def get(
        self,
        state: str,
        direction: str,
        packet_id: int,
        protocol: int | None = None,
    ) -> type | None:
        """
        Look up a Packet class by state/direction/id.

        If *protocol* is given, only entries matching that version are
        considered. The highest-priority (most recently registered) entry wins.
        """
        key = (state, direction, packet_id)
        entries = self._entries.get(key)
        if not entries:
            return None
        if protocol is None:
            return entries[-1].cls
        for entry in reversed(entries):
            if entry.matches_version(protocol):
                return entry.cls
        return None

    def get_id(self, cls: type) -> tuple[str, str, int] | None:
        """Return (state, direction, packet_id) for a registered Packet class."""
        return self._reverse.get(cls)

    def all_entries(self) -> Iterator[RegistryEntry]:
        for entries in self._entries.values():
            yield from entries

    def entries_for_state(self, state: str, direction: str | None = None) -> list[RegistryEntry]:
        result = []
        for (s, d, _), entries in self._entries.items():
            if s == state and (direction is None or d == direction):
                result.extend(entries)
        return result

    def __contains__(self, key: tuple[str, str, int]) -> bool:
        return key in self._entries

    def __len__(self) -> int:
        return sum(len(v) for v in self._entries.values())

    def __repr__(self) -> str:
        return f"PacketRegistry({self.name!r}, {len(self._entries)} ids, {len(self)} entries)"


# ── Module-level singleton ────────────────────────────────────────────────────

global_registry = PacketRegistry(name="global")
