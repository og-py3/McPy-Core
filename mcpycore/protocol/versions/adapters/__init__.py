"""Version adapter registry — maps protocol numbers to ID tables."""
from __future__ import annotations

from mcpycore.protocol.versions.v1_20.packets import CB_IDS as CB_1_20, SB_IDS as SB_1_20
from mcpycore.protocol.versions.v1_21.packets import CB_IDS as CB_1_21, SB_IDS as SB_1_21


def get_cb_ids(protocol: int) -> dict[str, int]:
    """Return the clientbound ID table for *protocol*, or nearest known."""
    all_cb = {**CB_1_20, **CB_1_21}
    if protocol in all_cb:
        return all_cb[protocol]
    # Fall back to the nearest lower protocol
    candidates = sorted((p for p in all_cb if p <= protocol), reverse=True)
    if candidates:
        return all_cb[candidates[0]]
    return all_cb[min(all_cb)]


def get_sb_ids(protocol: int) -> dict[str, int]:
    """Return the serverbound ID table for *protocol*, or nearest known."""
    all_sb = {**SB_1_20, **SB_1_21}
    if protocol in all_sb:
        return all_sb[protocol]
    candidates = sorted((p for p in all_sb if p <= protocol), reverse=True)
    if candidates:
        return all_sb[candidates[0]]
    return all_sb[min(all_sb)]


__all__ = ["get_cb_ids", "get_sb_ids"]
