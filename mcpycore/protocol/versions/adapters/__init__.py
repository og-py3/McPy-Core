"""
Version adapter registry — maps every known protocol number to its packet ID tables.

Lookup order:
  1. Exact protocol match.
  2. Nearest lower protocol in the table (graceful fallback for minor patches).
  3. Lowest known table entry (absolute last resort).
"""
from __future__ import annotations

from mcpycore.protocol.versions.v1_8.packets   import CB_IDS as CB_1_8,  SB_IDS as SB_1_8
from mcpycore.protocol.versions.v1_12.packets  import CB_IDS as CB_1_12, SB_IDS as SB_1_12
from mcpycore.protocol.versions.v1_16.packets  import CB_IDS as CB_1_16, SB_IDS as SB_1_16
from mcpycore.protocol.versions.v1_17.packets  import CB_IDS as CB_1_17, SB_IDS as SB_1_17
from mcpycore.protocol.versions.v1_20.packets  import CB_IDS as CB_1_20, SB_IDS as SB_1_20
from mcpycore.protocol.versions.v1_21.packets  import CB_IDS as CB_1_21, SB_IDS as SB_1_21

# Merge all tables in chronological order so later entries override earlier ones
# for duplicate keys (there are none — each era has unique protocol numbers).
_ALL_CB: dict[int, dict[str, int]] = {
    **CB_1_8,
    **CB_1_12,
    **CB_1_16,
    **CB_1_17,
    **CB_1_20,
    **CB_1_21,
}

_ALL_SB: dict[int, dict[str, int]] = {
    **SB_1_8,
    **SB_1_12,
    **SB_1_16,
    **SB_1_17,
    **SB_1_20,
    **SB_1_21,
}

_SORTED_CB_PROTOCOLS = sorted(_ALL_CB.keys())
_SORTED_SB_PROTOCOLS = sorted(_ALL_SB.keys())


def _nearest(protocol: int, sorted_keys: list[int]) -> int:
    """Return the closest key ≤ *protocol*, or the minimum key as fallback."""
    best = sorted_keys[0]
    for p in sorted_keys:
        if p <= protocol:
            best = p
        else:
            break
    return best


def get_cb_ids(protocol: int) -> dict[str, int]:
    """Return the clientbound play-state ID table for *protocol*."""
    if protocol in _ALL_CB:
        return _ALL_CB[protocol]
    return _ALL_CB[_nearest(protocol, _SORTED_CB_PROTOCOLS)]


def get_sb_ids(protocol: int) -> dict[str, int]:
    """Return the serverbound play-state ID table for *protocol*."""
    if protocol in _ALL_SB:
        return _ALL_SB[protocol]
    return _ALL_SB[_nearest(protocol, _SORTED_SB_PROTOCOLS)]


def list_supported_protocols() -> list[int]:
    """Return all protocol numbers that have an exact entry in the tables."""
    return sorted(_ALL_CB.keys())


__all__ = ["get_cb_ids", "get_sb_ids", "list_supported_protocols"]
