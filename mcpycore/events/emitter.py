"""
AsyncEventEmitter — the event bus powering McPy-Core's handler system.

Supports both coroutine and plain-function handlers with optional
one-shot registration, wildcard listeners, and middleware hooks.

Usage::

    emitter = AsyncEventEmitter()

    @emitter.on("chat")
    async def handle_chat(message: str) -> None:
        print(f"Chat: {message}")

    # Or with plain functions:
    emitter.on("join", lambda player: print(f"{player} joined"))

    # Fire an event:
    await emitter.emit("chat", "Hello, world!")
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from collections import defaultdict
from typing import Any, Callable

log = logging.getLogger(__name__)


class AsyncEventEmitter:
    """
    Async-first event emitter.

    Handlers may be:
    - ``async def handler(*args, **kwargs)`` — awaited directly
    - ``def handler(*args, **kwargs)`` — called in thread pool via ``loop.run_in_executor``

    Wild-card listeners registered under ``"*"`` receive every event.
    """

    def __init__(self) -> None:
        self._listeners:  dict[str, list[Callable]] = defaultdict(list)
        self._once:       dict[str, list[Callable]] = defaultdict(list)
        self._middleware: list[Callable] = []
        self._error_handler: Callable | None = None

    # ── Registration ──────────────────────────────────────────────────────

    def on(self, event: str, handler: Callable | None = None):
        """
        Register a persistent listener.

        Can be used as a decorator or as a direct call::

            @emitter.on("chat")
            async def on_chat(msg): ...

            emitter.on("chat", on_chat)
        """
        if handler is None:
            def decorator(fn: Callable) -> Callable:
                self._listeners[event].append(fn)
                return fn
            return decorator
        self._listeners[event].append(handler)
        return handler

    def once(self, event: str, handler: Callable | None = None):
        """Register a one-shot listener (removed after first fire)."""
        if handler is None:
            def decorator(fn: Callable) -> Callable:
                self._once[event].append(fn)
                return fn
            return decorator
        self._once[event].append(handler)
        return handler

    def off(self, event: str, handler: Callable) -> bool:
        """Remove a listener. Returns True if it was found and removed."""
        for bucket in (self._listeners, self._once):
            lst = bucket.get(event, [])
            if handler in lst:
                lst.remove(handler)
                return True
        return False

    def remove_all(self, event: str | None = None) -> None:
        """Remove all listeners for *event*, or all events if None."""
        if event is None:
            self._listeners.clear()
            self._once.clear()
        else:
            self._listeners.pop(event, None)
            self._once.pop(event, None)

    def use_middleware(self, fn: Callable) -> None:
        """
        Register middleware that runs before every event handler.

        Signature: ``async def middleware(event, *args, **kwargs) -> bool``
        Return False to suppress the event.
        """
        self._middleware.append(fn)

    def on_error(self, handler: Callable) -> None:
        """
        Register a global error handler.

        Called when any listener raises an exception.
        Signature: ``async def handler(event, exc, *args)``
        """
        self._error_handler = handler

    # ── Emission ──────────────────────────────────────────────────────────

    async def emit(self, event: str, *args: Any, **kwargs: Any) -> list[Any]:
        """
        Fire *event*, calling all registered listeners.

        Returns a list of results from each handler.
        """
        # Run middleware
        for mw in self._middleware:
            try:
                result = mw(event, *args, **kwargs)
                if inspect.isawaitable(result):
                    result = await result
                if result is False:
                    return []
            except Exception as exc:
                log.warning("Middleware error for %r: %s", event, exc)

        handlers = (
            list(self._listeners.get(event, []))
            + list(self._listeners.get("*", []))
        )

        # Collect and drain one-shot handlers
        once_handlers = list(self._once.pop(event, []))
        handlers.extend(once_handlers)

        results = []
        for handler in handlers:
            try:
                result = handler(*args, **kwargs)
                if inspect.isawaitable(result):
                    result = await result
                results.append(result)
            except Exception as exc:
                log.exception("Error in handler for %r: %s", event, exc)
                if self._error_handler:
                    try:
                        err_result = self._error_handler(event, exc, *args)
                        if inspect.isawaitable(err_result):
                            await err_result
                    except Exception:
                        pass

        return results

    def emit_sync(self, event: str, *args: Any, **kwargs: Any) -> None:
        """
        Fire event from a synchronous context.

        Schedules the emission as an asyncio task if a loop is running,
        otherwise calls all plain-function handlers directly.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.emit(event, *args, **kwargs))
        except RuntimeError:
            # No running loop — call sync handlers directly
            for handler in self._listeners.get(event, []):
                if not inspect.iscoroutinefunction(handler):
                    try:
                        handler(*args, **kwargs)
                    except Exception as exc:
                        log.warning("Handler error for %r: %s", event, exc)

    # ── Inspection ────────────────────────────────────────────────────────

    def listener_count(self, event: str) -> int:
        return len(self._listeners.get(event, [])) + len(self._once.get(event, []))

    def all_events(self) -> list[str]:
        return list(set(list(self._listeners) + list(self._once)))

    def __repr__(self) -> str:
        total = sum(len(v) for v in self._listeners.values())
        return f"AsyncEventEmitter({len(self._listeners)} events, {total} listeners)"


# ── Well-known event names ────────────────────────────────────────────────────

class Events:
    """String constants for all built-in McPy-Core events."""
    # Lifecycle
    CONNECT       = "connect"
    DISCONNECT    = "disconnect"
    RECONNECT     = "reconnect"
    ERROR         = "error"

    # Protocol
    PACKET        = "packet"          # raw: fired for every received packet
    PACKET_SEND   = "packet_send"     # fired before every sent packet

    # Login / join
    LOGIN         = "login"
    SPAWN         = "spawn"
    RESPAWN       = "respawn"

    # Chat
    CHAT          = "chat"
    SYSTEM_CHAT   = "system_chat"

    # Keep-alive
    KEEPALIVE     = "keepalive"

    # Health / food
    HEALTH        = "health"
    DEATH         = "death"

    # World
    CHUNK_LOAD    = "chunk_load"
    CHUNK_UNLOAD  = "chunk_unload"
    BLOCK_UPDATE  = "block_update"
    EXPLOSION     = "explosion"
    TIME_UPDATE   = "time_update"

    # Entities
    SPAWN_ENTITY    = "spawn_entity"
    ENTITY_MOVE     = "entity_move"
    REMOVE_ENTITIES = "remove_entities"
    ENTITY_EFFECT   = "entity_effect"

    # Player
    POSITION        = "position"
    ABILITIES       = "abilities"
    GAME_MODE       = "game_mode"

    # Inventory
    INVENTORY       = "inventory"
    SLOT_UPDATE     = "slot_update"

    # UI
    TITLE           = "title"
    SUBTITLE        = "subtitle"
    ACTION_BAR      = "action_bar"
    BOSS_BAR        = "boss_bar"

    # Tab list
    PLAYER_LIST     = "player_list"
    TAB_HEADER      = "tab_header"

    # Sound
    SOUND           = "sound"

    # Transfer (1.21+)
    TRANSFER        = "transfer"

    # Combat
    HURT            = "hurt"
    DAMAGE          = "damage"
