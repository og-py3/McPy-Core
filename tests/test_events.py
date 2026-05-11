"""Tests for AsyncEventEmitter."""
from __future__ import annotations

import asyncio
import pytest

from mcpycore.events.emitter import AsyncEventEmitter, Events


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── Basic emission ────────────────────────────────────────────────────────────

def test_emit_async_handler():
    emitter = AsyncEventEmitter()
    received = []

    async def handler(val):
        received.append(val)

    emitter.on("test", handler)
    run(emitter.emit("test", 42))
    assert received == [42]


def test_emit_sync_handler():
    emitter = AsyncEventEmitter()
    received = []

    emitter.on("test", lambda v: received.append(v))
    run(emitter.emit("test", "hello"))
    assert received == ["hello"]


def test_emit_no_handlers():
    emitter = AsyncEventEmitter()
    results = run(emitter.emit("ghost_event", 1, 2, 3))
    assert results == []


def test_emit_multiple_handlers():
    emitter = AsyncEventEmitter()
    calls = []

    async def h1(): calls.append(1)
    async def h2(): calls.append(2)

    emitter.on("e", h1)
    emitter.on("e", h2)
    run(emitter.emit("e"))
    assert calls == [1, 2]


def test_emit_returns_results():
    emitter = AsyncEventEmitter()

    async def handler():
        return "result"

    emitter.on("e", handler)
    results = run(emitter.emit("e"))
    assert results == ["result"]


def test_emit_multiple_args():
    emitter = AsyncEventEmitter()
    received = []

    async def handler(a, b, c):
        received.append((a, b, c))

    emitter.on("e", handler)
    run(emitter.emit("e", 1, 2, 3))
    assert received == [(1, 2, 3)]


# ── Decorator registration ────────────────────────────────────────────────────

def test_on_decorator():
    emitter = AsyncEventEmitter()
    calls = []

    @emitter.on("chat")
    async def on_chat(msg):
        calls.append(msg)

    run(emitter.emit("chat", "hello"))
    assert calls == ["hello"]


# ── Once (one-shot) ───────────────────────────────────────────────────────────

def test_once_fires_once():
    emitter = AsyncEventEmitter()
    calls = []

    emitter.once("e", lambda: calls.append(1))
    run(emitter.emit("e"))
    run(emitter.emit("e"))
    assert calls == [1]


def test_once_decorator():
    emitter = AsyncEventEmitter()
    calls = []

    @emitter.once("ping")
    async def handler():
        calls.append(True)

    run(emitter.emit("ping"))
    run(emitter.emit("ping"))
    assert len(calls) == 1


# ── Remove ────────────────────────────────────────────────────────────────────

def test_off_removes_handler():
    emitter = AsyncEventEmitter()
    calls = []

    def h(): calls.append(True)
    emitter.on("e", h)
    emitter.off("e", h)
    run(emitter.emit("e"))
    assert calls == []


def test_off_unknown_handler_returns_false():
    emitter = AsyncEventEmitter()
    assert emitter.off("e", lambda: None) is False


def test_remove_all_specific():
    emitter = AsyncEventEmitter()
    calls = []
    emitter.on("a", lambda: calls.append("a"))
    emitter.on("b", lambda: calls.append("b"))
    emitter.remove_all("a")
    run(emitter.emit("a"))
    run(emitter.emit("b"))
    assert calls == ["b"]


def test_remove_all_global():
    emitter = AsyncEventEmitter()
    calls = []
    emitter.on("a", lambda: calls.append("a"))
    emitter.on("b", lambda: calls.append("b"))
    emitter.remove_all()
    run(emitter.emit("a"))
    run(emitter.emit("b"))
    assert calls == []


# ── Wildcard ──────────────────────────────────────────────────────────────────

def test_wildcard_receives_all():
    emitter = AsyncEventEmitter()
    received = []

    emitter.on("*", lambda *a: received.append(a))
    run(emitter.emit("chat", "hello"))
    run(emitter.emit("join", "player"))
    assert len(received) == 2


# ── Middleware ────────────────────────────────────────────────────────────────

def test_middleware_can_suppress():
    emitter = AsyncEventEmitter()
    calls = []
    emitter.on("e", lambda: calls.append(True))
    emitter.use_middleware(lambda event, *a: False)
    run(emitter.emit("e"))
    assert calls == []


def test_middleware_passes_through():
    emitter = AsyncEventEmitter()
    calls = []
    emitter.on("e", lambda: calls.append(True))
    emitter.use_middleware(lambda event, *a: True)
    run(emitter.emit("e"))
    assert calls == [True]


# ── Error handling ────────────────────────────────────────────────────────────

def test_handler_exception_does_not_crash():
    emitter = AsyncEventEmitter()

    async def bad():
        raise RuntimeError("oops")

    emitter.on("e", bad)
    run(emitter.emit("e"))   # should not raise


def test_error_handler_called():
    emitter = AsyncEventEmitter()
    errors = []

    async def bad():
        raise ValueError("test error")

    async def on_error(event, exc, *a):
        errors.append((event, type(exc).__name__))

    emitter.on("e", bad)
    emitter.on_error(on_error)
    run(emitter.emit("e"))
    assert errors == [("e", "ValueError")]


# ── Inspection ────────────────────────────────────────────────────────────────

def test_listener_count():
    emitter = AsyncEventEmitter()
    emitter.on("e", lambda: None)
    emitter.on("e", lambda: None)
    assert emitter.listener_count("e") == 2


def test_all_events():
    emitter = AsyncEventEmitter()
    emitter.on("chat", lambda: None)
    emitter.on("join", lambda: None)
    events = emitter.all_events()
    assert "chat" in events
    assert "join" in events


def test_repr():
    emitter = AsyncEventEmitter()
    emitter.on("e", lambda: None)
    assert "AsyncEventEmitter" in repr(emitter)


# ── Events constants ──────────────────────────────────────────────────────────

def test_events_constants_are_strings():
    for attr in dir(Events):
        if not attr.startswith("_"):
            val = getattr(Events, attr)
            assert isinstance(val, str)


def test_events_no_empty():
    for attr in dir(Events):
        if not attr.startswith("_"):
            val = getattr(Events, attr)
            assert len(val) > 0
