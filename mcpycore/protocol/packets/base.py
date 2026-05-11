"""
Packet base class and @packet registration decorator.

Every Minecraft packet inherits from Packet and is decorated with @packet
to auto-register itself in the global PacketRegistry.

Usage::

    from mcpycore.protocol.packets.base import Packet, packet
    from mcpycore.protocol.states.machine import State
    from mcpycore.protocol.registry.registry import Direction

    @packet(packet_id=0x00, state=State.LOGIN, direction=Direction.SERVERBOUND)
    class LoginStart(Packet):
        username: str = ""
        player_uuid: Optional[uuid.UUID] = None

        def encode(self) -> bytes:
            buf = PacketBuffer()
            buf.write_string(self.username)
            buf.write_optional_uuid(self.player_uuid)
            return buf.flush()

        @classmethod
        def decode(cls, buf: PacketBuffer) -> "LoginStart":
            pkt = cls()
            pkt.username = buf.read_string()
            pkt.player_uuid = buf.read_optional_uuid()
            return pkt
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from mcpycore.protocol.serializers.buffer import PacketBuffer


class Packet:
    """
    Abstract base class for all Minecraft protocol packets.

    Subclasses must implement:
    - ``encode(self) -> bytes``      (if the packet is ever sent)
    - ``decode(cls, buf) -> Packet`` (if the packet is ever received)

    Class attributes set by ``@packet``::

        _packet_id:  int                     — wire ID
        _state:      str                     — protocol state name
        _direction:  str                     — "serverbound" or "clientbound"
        _version_min: int | None             — first supported protocol
        _version_max: int | None             — last supported protocol (None=open)
        _registered: bool                   — set to True after registration
    """

    _packet_id:   ClassVar[int]        = -1
    _state:       ClassVar[str]        = ""
    _direction:   ClassVar[str]        = ""
    _version_min: ClassVar[int | None] = None
    _version_max: ClassVar[int | None] = None
    _registered:  ClassVar[bool]       = False

    def encode(self) -> bytes:
        """Encode this packet to raw payload bytes (excluding length and ID)."""
        raise NotImplementedError(f"{self.__class__.__name__}.encode() not implemented")

    @classmethod
    def decode(cls, buf: "PacketBuffer") -> "Packet":
        """Decode a packet from *buf* and return a populated instance."""
        raise NotImplementedError(f"{cls.__name__}.decode() not implemented")

    # ── Convenience ──────────────────────────────────────────────────────

    @classmethod
    def packet_id(cls) -> int:
        return cls._packet_id

    @classmethod
    def state(cls) -> str:
        return cls._state

    @classmethod
    def direction(cls) -> str:
        return cls._direction

    @classmethod
    def is_serverbound(cls) -> bool:
        return cls._direction == "serverbound"

    @classmethod
    def is_clientbound(cls) -> bool:
        return cls._direction == "clientbound"

    @classmethod
    def supports_version(cls, protocol: int) -> bool:
        lo = cls._version_min
        hi = cls._version_max
        if lo is not None and protocol < lo:
            return False
        if hi is not None and protocol > hi:
            return False
        return True

    def __repr__(self) -> str:
        attrs = {
            k: v for k, v in vars(self).items()
            if not k.startswith("_")
        }
        parts = ", ".join(f"{k}={v!r}" for k, v in attrs.items())
        return f"{self.__class__.__name__}({parts})"


# ── @packet decorator ─────────────────────────────────────────────────────────

def packet(
    packet_id: int,
    state: str,
    direction: str = "clientbound",
    version_min: int | None = None,
    version_max: int | None = None,
    registry: Any = None,
):
    """
    Decorator that registers a Packet subclass in the packet registry.

    Parameters
    ----------
    packet_id:
        Numeric packet ID (e.g. ``0x00``).
    state:
        Protocol state name — use ``mcpycore.protocol.states.machine.State.*``.
    direction:
        ``"clientbound"`` (server→client) or ``"serverbound"`` (client→server).
    version_min:
        Minimum protocol version this packet applies to (inclusive).
    version_max:
        Maximum protocol version this packet applies to (inclusive, ``None`` = open).
    registry:
        PacketRegistry to register into. Defaults to the global registry.

    Example::

        @packet(packet_id=0x00, state=State.LOGIN, direction=Direction.SERVERBOUND)
        class LoginStart(Packet):
            ...
    """
    from mcpycore.protocol.registry.registry import global_registry

    target_registry = registry if registry is not None else global_registry

    def decorator(cls: type) -> type:
        if not (inspect.isclass(cls) and issubclass(cls, Packet)):
            raise TypeError(f"@packet must decorate a Packet subclass, got {cls}")
        cls._packet_id   = packet_id
        cls._state       = state
        cls._direction   = direction
        cls._version_min = version_min
        cls._version_max = version_max
        cls._registered  = True
        target_registry.register(
            state=state,
            direction=direction,
            packet_id=packet_id,
            cls=cls,
            version_min=version_min,
            version_max=version_max,
        )
        return cls

    return decorator
