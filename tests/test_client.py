"""Unit tests for MinecraftClient (no real server required)."""
from __future__ import annotations

import asyncio
import warnings
import pytest

from mcpycore.client.client import MinecraftClient
from mcpycore.client.reconnect import NoReconnect, FixedDelay, ExponentialBackoff, InfiniteRetry
from mcpycore.events.emitter import Events
from mcpycore.protocol.versions.base import (
    PROTOCOL_LATEST, PROTOCOL_1_20_2, PROTOCOL_1_21_11, SNAPSHOT_BASE,
)


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def make_client(**kw) -> MinecraftClient:
    defaults = dict(host="localhost", username="TestBot", protocol_version=PROTOCOL_LATEST)
    defaults.update(kw)
    return MinecraftClient(**defaults)


# ── Construction ──────────────────────────────────────────────────────────────

def test_default_protocol():
    c = make_client()
    assert c.protocol_version == PROTOCOL_LATEST


def test_custom_protocol():
    c = make_client(protocol_version=PROTOCOL_1_20_2)
    assert c.protocol_version == PROTOCOL_1_20_2


def test_version_name():
    c = make_client(protocol_version=767)
    assert "1.21" in c.version_name


def test_version_name_latest():
    c = make_client(protocol_version=775)
    assert "1.21.11" in c.version_name


def test_username_stored():
    c = make_client(username="Alice")
    assert c.profile.username == "Alice"


def test_not_connected_initially():
    c = make_client()
    assert not c.is_connected


def test_initial_health():
    c = make_client()
    assert c.health == 20.0
    assert c.food == 20


def test_initial_position():
    c = make_client()
    assert c.position == (0.0, 0.0, 0.0)


def test_initial_game_mode():
    c = make_client()
    assert c.game_mode == 0


def test_not_creative_by_default():
    c = make_client()
    assert not c.is_creative


def test_debug_flag():
    c = make_client(debug=True)
    assert c.debug
    assert c.inspector.enabled


def test_repr():
    c = make_client()
    r = repr(c)
    assert "localhost" in r
    assert "TestBot" in r


# ── Event system ──────────────────────────────────────────────────────────────

def test_event_decorator():
    c = make_client()
    received = []

    @c.event
    async def on_chat(message, sender):
        received.append(message)

    run(c.events.emit(Events.CHAT, "hello", "uuid"))
    assert received == ["hello"]


def test_event_decorator_wrong_name():
    c = make_client()
    with pytest.raises(ValueError, match="on_"):
        @c.event
        def not_prefixed():
            pass


def test_on_direct():
    c = make_client()
    received = []
    c.on(Events.HEALTH, lambda h, f, s: received.append(h))
    run(c.events.emit(Events.HEALTH, 10.0, 20, 5.0))
    assert received == [10.0]


def test_once_fires_once():
    c = make_client()
    calls = []
    c.once(Events.CONNECT, lambda *a: calls.append(1))
    run(c.events.emit(Events.CONNECT))
    run(c.events.emit(Events.CONNECT))
    assert calls == [1]


def test_multiple_handlers_same_event():
    c = make_client()
    calls = []
    c.on("e", lambda: calls.append(1))
    c.on("e", lambda: calls.append(2))
    run(c.events.emit("e"))
    assert calls == [1, 2]


# ── Snapshot warning ──────────────────────────────────────────────────────────

def test_snapshot_does_not_crash():
    snap = SNAPSHOT_BASE | 0x100
    c = make_client(protocol_version=snap)
    assert c.protocol_version == snap


# ── Reconnect policies ────────────────────────────────────────────────────────

def test_no_reconnect_policy():
    policy = NoReconnect()
    assert run(policy.wait(0)) is False


def test_fixed_delay_allows_retry():
    policy = FixedDelay(delay=0.001, max_attempts=3)
    assert run(policy.wait(0)) is True
    assert run(policy.wait(1)) is True
    assert run(policy.wait(2)) is True
    assert run(policy.wait(3)) is False


def test_exponential_backoff_unlimited():
    policy = ExponentialBackoff(base_delay=0.001, max_delay=0.01, jitter=False)
    for i in range(5):
        assert run(policy.wait(i)) is True


def test_exponential_backoff_max_attempts():
    policy = ExponentialBackoff(base_delay=0.001, max_delay=0.01, max_attempts=2, jitter=False)
    assert run(policy.wait(0)) is True
    assert run(policy.wait(1)) is True
    assert run(policy.wait(2)) is False


def test_infinite_retry():
    policy = InfiniteRetry(base_delay=0.001, max_delay=0.01)
    for i in range(10):
        assert run(policy.wait(i)) is True


# ── Inspector / metrics ───────────────────────────────────────────────────────

def test_inspector_disabled_by_default():
    c = make_client()
    assert not c.inspector.enabled


def test_inspector_enabled_with_debug():
    c = make_client(debug=True)
    assert c.inspector.enabled


def test_metrics_exist():
    c = make_client()
    assert c.metrics is not None


def test_metrics_report():
    c = make_client()
    r = c.metrics.report()
    assert "packets_in" in r
    assert "uptime_s" in r


# ── Internal helpers ──────────────────────────────────────────────────────────

def test_cb_id_lookup():
    c = make_client(protocol_version=767)
    pid = c._cb("keep_alive")
    assert pid is not None
    assert isinstance(pid, int)


def test_sb_id_lookup():
    c = make_client(protocol_version=767)
    pid = c._sb("keep_alive")
    assert pid is not None
    assert isinstance(pid, int)


def test_handlers_dict_built():
    c = make_client()
    assert len(c._handlers) > 0


def test_handler_for_keep_alive_exists():
    c = make_client()
    pid = c._cb("keep_alive")
    assert pid in c._handlers


def test_handler_for_position_exists():
    c = make_client()
    pid = c._cb("player_position_and_look")
    assert pid in c._handlers
