"""
PacketInspector — developer debug logging for packet I/O.

When enabled, every sent and received packet is logged with:
- Direction (SEND / RECV)
- Packet ID (hex)
- Packet name (if known)
- Payload size
- Optional hex dump

Usage::

    inspector = PacketInspector(enabled=True, hex_dump=True)
    inspector.log_recv(0x26, buf)
    inspector.log_send(0x14, payload)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcpycore.protocol.serializers.buffer import PacketBuffer

log = logging.getLogger("mcpycore.inspector")


# ── Packet name tables (common play-state IDs for reference) ──────────────────

_CB_NAMES: dict[int, str] = {
    0x00: "BundleDelimiter",
    0x01: "SpawnEntity",
    0x03: "EntityAnimation",
    0x1D: "Disconnect",
    0x22: "GameEvent",
    0x24: "KeepAlive",
    0x25: "ChunkData",
    0x27: "Login",
    0x2C: "EntityPosition",
    0x2D: "EntityPositionAndRotation",
    0x2E: "EntityRotation",
    0x36: "PlayerAbilities",
    0x3E: "PlayerPositionAndLook",
    0x47: "Respawn",
    0x55: "SetHealth",
    0x5C: "TimeUpdate",
    0x67: "SystemChatMessage",
}

_SB_NAMES: dict[int, str] = {
    0x00: "ConfirmTeleportation",
    0x04: "ChatCommand",
    0x05: "ChatMessage",
    0x08: "ClientInformation",
    0x13: "InteractEntity",
    0x14: "KeepAlive",
    0x17: "MovePlayerPos",
    0x18: "MovePlayerPosRot",
    0x19: "MovePlayerRot",
    0x1D: "PlayerAction",
    0x1E: "PlayerCommand",
    0x36: "SwingArm",
    0x3A: "UseItem",
}


def _hexdump(data: bytes, bytes_per_line: int = 16) -> str:
    lines = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i : i + bytes_per_line]
        hex_part  = " ".join(f"{b:02X}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"  {i:04X}  {hex_part:<{bytes_per_line * 3}}  {ascii_part}")
    return "\n".join(lines)


class PacketInspector:
    """
    Logs packet I/O for debugging.

    Parameters
    ----------
    enabled:
        Master on/off switch.
    hex_dump:
        If True, include a full hex dump of each packet payload.
    max_dump_bytes:
        Maximum payload bytes to hex-dump (prevents huge log output).
    """

    def __init__(
        self,
        enabled: bool = False,
        hex_dump: bool = False,
        max_dump_bytes: int = 256,
    ) -> None:
        self.enabled = enabled
        self.hex_dump = hex_dump
        self.max_dump_bytes = max_dump_bytes
        self._recv_count = 0
        self._send_count = 0

    def log_recv(self, packet_id: int, buf: "PacketBuffer") -> None:
        if not self.enabled:
            return
        self._recv_count += 1
        name = _CB_NAMES.get(packet_id, "unknown")
        data = buf.getvalue()
        size = len(data)
        log.debug("[RECV] 0x%02X %-35s %5d bytes", packet_id, name, size)
        if self.hex_dump and size > 0:
            dump_data = data[:self.max_dump_bytes]
            log.debug("\n%s%s", _hexdump(dump_data),
                      f"\n  ... ({size - len(dump_data)} more bytes)" if size > self.max_dump_bytes else "")

    def log_send(self, packet_id: int, payload: bytes) -> None:
        if not self.enabled:
            return
        self._send_count += 1
        name = _SB_NAMES.get(packet_id, "unknown")
        size = len(payload)
        log.debug("[SEND] 0x%02X %-35s %5d bytes", packet_id, name, size)
        if self.hex_dump and size > 0:
            dump_data = payload[:self.max_dump_bytes]
            log.debug("\n%s%s", _hexdump(dump_data),
                      f"\n  ... ({size - len(dump_data)} more bytes)" if size > self.max_dump_bytes else "")

    def log_event(self, event: str, *args) -> None:
        if not self.enabled:
            return
        log.debug("[EVENT] %-30s %s", event, args)

    @property
    def stats(self) -> dict[str, int]:
        return {"recv": self._recv_count, "send": self._send_count}

    def reset_stats(self) -> None:
        self._recv_count = 0
        self._send_count = 0

    def __repr__(self) -> str:
        return f"PacketInspector(enabled={self.enabled}, hex_dump={self.hex_dump})"
