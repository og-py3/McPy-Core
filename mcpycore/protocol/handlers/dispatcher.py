"""
PacketDispatcher — routes incoming raw packets to typed handler functions.

Middleware support allows transforming or suppressing packets before dispatch.

Usage::

    dispatcher = PacketDispatcher(registry, protocol=767)

    @dispatcher.register(State.PLAY, Direction.CLIENTBOUND, 0x24)
    async def on_keep_alive(packet_id, buf, conn):
        ka_id = buf.read_long()
        ...

    # Or register from a class:
    dispatcher.register_handler_class(MyHandlers())

    # Dispatch a packet:
    await dispatcher.dispatch(packet_id, buf, conn)
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Callable, Coroutine

from mcpycore.protocol.registry.registry import PacketRegistry, Direction
from mcpycore.protocol.serializers.buffer import PacketBuffer
from mcpycore.protocol.states.machine import State

log = logging.getLogger(__name__)

Handler = Callable[..., Coroutine]
Middleware = Callable[..., Coroutine | bool]


class PacketDispatcher:
    """
    Routes packets to registered async handlers with optional middleware.

    Handlers have signature::

        async def handler(packet_id: int, buf: PacketBuffer, *extra) -> None

    Middleware has signature::

        async def middleware(packet_id: int, buf: PacketBuffer, *extra) -> bool | None

    Returning ``False`` from middleware suppresses the packet.
    """

    def __init__(
        self,
        registry: PacketRegistry | None = None,
        protocol: int = 775,
    ) -> None:
        self._registry = registry
        self._protocol = protocol
        self._handlers: dict[int, list[Handler]] = {}
        self._middleware: list[Middleware] = []

    # ── Registration ──────────────────────────────────────────────────────

    def register(
        self,
        packet_id: int,
        handler: Handler | None = None,
    ):
        """
        Register a handler for *packet_id*.

        Can be used as a decorator or direct call::

            @dispatcher.register(0x24)
            async def handle_keepalive(pid, buf): ...

            dispatcher.register(0x24, handle_keepalive)
        """
        if handler is None:
            def decorator(fn: Handler) -> Handler:
                self._handlers.setdefault(packet_id, []).append(fn)
                return fn
            return decorator
        self._handlers.setdefault(packet_id, []).append(handler)
        return handler

    def unregister(self, packet_id: int, handler: Handler) -> bool:
        lst = self._handlers.get(packet_id, [])
        if handler in lst:
            lst.remove(handler)
            return True
        return False

    def use(self, fn: Middleware) -> Middleware:
        """Add a middleware function."""
        self._middleware.append(fn)
        return fn

    def register_handler_class(self, obj: Any) -> None:
        """
        Register all methods named ``handle_0x<id>`` on *obj*.

        Example::

            class Handlers:
                async def handle_0x24(self, pid, buf): ...

            dispatcher.register_handler_class(Handlers())
        """
        for attr in dir(obj):
            if attr.startswith("handle_0x"):
                try:
                    pid = int(attr[len("handle_"):], 16)
                    method = getattr(obj, attr)
                    self.register(pid, method)
                except ValueError:
                    pass

    # ── Dispatch ──────────────────────────────────────────────────────────

    async def dispatch(self, packet_id: int, buf: PacketBuffer, *extra: Any) -> None:
        """Run all registered handlers for *packet_id*."""
        # Run middleware
        for mw in self._middleware:
            result = mw(packet_id, buf, *extra)
            if inspect.isawaitable(result):
                result = await result
            if result is False:
                return

        handlers = self._handlers.get(packet_id, [])
        for handler in handlers:
            try:
                result = handler(packet_id, buf, *extra)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                log.exception("Handler error for packet 0x%02X: %s", packet_id, exc)

    # ── Inspection ────────────────────────────────────────────────────────

    @property
    def registered_ids(self) -> list[int]:
        return sorted(self._handlers.keys())

    def handler_count(self, packet_id: int) -> int:
        return len(self._handlers.get(packet_id, []))

    def __repr__(self) -> str:
        return f"PacketDispatcher({len(self._handlers)} packet IDs)"
