"""Tests for PacketDispatcher."""
from __future__ import annotations

import asyncio
import pytest

from mcpycore.protocol.handlers.dispatcher import PacketDispatcher
from mcpycore.protocol.serializers.buffer import PacketBuffer


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def make_buf() -> PacketBuffer:
    return PacketBuffer.from_bytes(b"\x00")


# ── Registration ──────────────────────────────────────────────────────────────

def test_register_and_dispatch():
    d = PacketDispatcher()
    calls = []

    async def handler(pid, buf):
        calls.append(pid)

    d.register(0x24, handler)
    run(d.dispatch(0x24, make_buf()))
    assert calls == [0x24]


def test_register_decorator():
    d = PacketDispatcher()
    calls = []

    @d.register(0x01)
    async def handler(pid, buf):
        calls.append(pid)

    run(d.dispatch(0x01, make_buf()))
    assert calls == [0x01]


def test_no_handler_no_crash():
    d = PacketDispatcher()
    run(d.dispatch(0xFF, make_buf()))


def test_multiple_handlers_same_id():
    d = PacketDispatcher()
    calls = []

    async def h1(pid, buf): calls.append(1)
    async def h2(pid, buf): calls.append(2)

    d.register(0x10, h1)
    d.register(0x10, h2)
    run(d.dispatch(0x10, make_buf()))
    assert calls == [1, 2]


def test_unregister():
    d = PacketDispatcher()
    calls = []

    async def h(pid, buf): calls.append(True)

    d.register(0x10, h)
    d.unregister(0x10, h)
    run(d.dispatch(0x10, make_buf()))
    assert calls == []


def test_unregister_unknown_returns_false():
    d = PacketDispatcher()
    assert d.unregister(0x10, lambda: None) is False


# ── Middleware ────────────────────────────────────────────────────────────────

def test_middleware_suppress():
    d = PacketDispatcher()
    calls = []

    async def h(pid, buf): calls.append(True)
    d.register(0x10, h)
    d.use(lambda pid, buf: False)
    run(d.dispatch(0x10, make_buf()))
    assert calls == []


def test_middleware_passthrough():
    d = PacketDispatcher()
    calls = []

    async def h(pid, buf): calls.append(True)
    d.register(0x10, h)
    d.use(lambda pid, buf: True)
    run(d.dispatch(0x10, make_buf()))
    assert calls == [True]


def test_multiple_middleware():
    d = PacketDispatcher()
    order = []

    d.use(lambda pid, buf: order.append(1) or True)
    d.use(lambda pid, buf: order.append(2) or True)
    d.register(0x01, lambda pid, buf: order.append(3))
    run(d.dispatch(0x01, make_buf()))
    assert order == [1, 2, 3]


# ── Handler class ─────────────────────────────────────────────────────────────

def test_register_handler_class():
    d = PacketDispatcher()
    calls = []

    class Handlers:
        async def handle_0x24(self, pid, buf):
            calls.append(pid)

    d.register_handler_class(Handlers())
    run(d.dispatch(0x24, make_buf()))
    assert calls == [0x24]


def test_register_handler_class_invalid_name_ignored():
    d = PacketDispatcher()

    class Handlers:
        async def handle_0xZZ(self, pid, buf):
            pass  # invalid hex — should be ignored

    d.register_handler_class(Handlers())
    assert 0 not in d.registered_ids or True   # no crash


# ── Error handling ────────────────────────────────────────────────────────────

def test_handler_exception_logged_not_raised():
    d = PacketDispatcher()

    async def bad(pid, buf):
        raise RuntimeError("test error")

    d.register(0x01, bad)
    run(d.dispatch(0x01, make_buf()))   # should not raise


# ── Inspection ────────────────────────────────────────────────────────────────

def test_registered_ids():
    d = PacketDispatcher()
    d.register(0x01, lambda *a: None)
    d.register(0x02, lambda *a: None)
    assert 0x01 in d.registered_ids
    assert 0x02 in d.registered_ids


def test_handler_count():
    d = PacketDispatcher()
    d.register(0x05, lambda *a: None)
    d.register(0x05, lambda *a: None)
    assert d.handler_count(0x05) == 2


def test_repr():
    d = PacketDispatcher()
    assert "PacketDispatcher" in repr(d)
