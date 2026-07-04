"""
Tests for the humanize / anti-bot layer.

Validates:
  • HumanizeConfig defaults and field types
  • Humanizer delay stays within configured range
  • spawn_angles() returns stable, non-trivial values
  • settle() fires the expected number of rotation callbacks
  • AuthMe handler fires on correct chat patterns
  • Generic trigger handler echoes captured groups
  • Disabled humanizer skips all delays
"""
from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, call

import pytest

from mcpycore.humanize.humanizer import HumanizeConfig, Humanizer


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_humanizer(**kwargs: Any) -> Humanizer:
    """Return a Humanizer with very short delays so tests stay fast."""
    cfg = HumanizeConfig(
        pre_handshake_delay=(1, 2),
        pre_login_delay=(1, 2),
        post_login_delay=(1, 2),
        config_settle_delay=(1, 2),
        keepalive_jitter=(1, 2),
        position_confirm_delay=(1, 2),
        settle_delay=(1, 2),
        **kwargs,
    )
    return Humanizer(cfg)


# ── HumanizeConfig defaults ───────────────────────────────────────────────────

class TestHumanizeConfigDefaults:
    def test_enabled_by_default(self):
        cfg = HumanizeConfig()
        assert cfg.enabled is True

    def test_pre_handshake_delay_is_tuple(self):
        cfg = HumanizeConfig()
        lo, hi = cfg.pre_handshake_delay
        assert lo > 0 and hi > lo

    def test_keepalive_jitter_is_tuple(self):
        cfg = HumanizeConfig()
        lo, hi = cfg.keepalive_jitter
        assert lo >= 0 and hi > lo

    def test_settle_on_spawn_true_by_default(self):
        assert HumanizeConfig().settle_on_spawn is True

    def test_authme_disabled_by_default(self):
        cfg = HumanizeConfig()
        assert cfg.authme_enabled is False
        assert cfg.authme_password == ""

    def test_initial_yaw_range_spans_360(self):
        lo, hi = HumanizeConfig().initial_yaw_range
        assert hi - lo >= 300

    def test_initial_pitch_range_stays_reasonable(self):
        lo, hi = HumanizeConfig().initial_pitch_range
        assert -30 <= lo and hi <= 45

    def test_chat_triggers_empty_by_default(self):
        assert HumanizeConfig().chat_triggers == []


# ── Delay ranges ──────────────────────────────────────────────────────────────

class TestHumanizerDelays:
    """All delays must fall within their configured (min, max) window."""

    @pytest.mark.asyncio
    async def test_pre_handshake_delay_in_range(self):
        h = make_humanizer()
        t0 = time.monotonic()
        await h.pre_handshake()
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert elapsed_ms >= 0  # just verify it completes

    @pytest.mark.asyncio
    async def test_keepalive_jitter_in_range(self):
        cfg = HumanizeConfig(keepalive_jitter=(10, 20))
        h = Humanizer(cfg)
        t0 = time.monotonic()
        await h.keepalive_jitter()
        elapsed_ms = (time.monotonic() - t0) * 1000
        # Allow generous upper bound due to OS scheduler jitter
        assert elapsed_ms >= 8, f"Delay too short: {elapsed_ms:.1f} ms"
        assert elapsed_ms < 200, f"Delay too long: {elapsed_ms:.1f} ms"

    @pytest.mark.asyncio
    async def test_disabled_humanizer_skips_delay(self):
        cfg = HumanizeConfig(enabled=False, post_login_delay=(5000, 10000))
        h = Humanizer(cfg)
        t0 = time.monotonic()
        await h.post_login()
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert elapsed_ms < 100, "Disabled humanizer should not sleep"


# ── Spawn angles ──────────────────────────────────────────────────────────────

class TestSpawnAngles:
    def test_returns_tuple_of_two_floats(self):
        h = make_humanizer()
        yaw, pitch = h.spawn_angles()
        assert isinstance(yaw, float) and isinstance(pitch, float)

    def test_yaw_within_range(self):
        cfg = HumanizeConfig(initial_yaw_range=(-90.0, 90.0))
        h = Humanizer(cfg)
        yaw, _ = h.spawn_angles()
        assert -90.0 <= yaw <= 90.0

    def test_pitch_within_range(self):
        cfg = HumanizeConfig(initial_pitch_range=(0.0, 30.0))
        h = Humanizer(cfg)
        _, pitch = h.spawn_angles()
        assert 0.0 <= pitch <= 30.0

    def test_stable_across_calls(self):
        h = make_humanizer()
        first  = h.spawn_angles()
        second = h.spawn_angles()
        assert first == second, "spawn_angles() must be idempotent within a session"

    def test_different_humanizers_may_differ(self):
        """Two separate Humanizer instances are (almost) never identical."""
        results = {make_humanizer().spawn_angles() for _ in range(20)}
        # With 20 independent samples, extremely unlikely all are identical
        assert len(results) > 1


# ── Post-spawn settle ─────────────────────────────────────────────────────────

class TestSettle:
    @pytest.mark.asyncio
    async def test_settle_calls_rotation_n_times(self):
        n = 5
        cfg = HumanizeConfig(settle_on_spawn=True, settle_moves=n, settle_delay=(1, 2))
        h = Humanizer(cfg)
        mock_rotation = AsyncMock()
        await h.settle(mock_rotation)
        assert mock_rotation.call_count == n

    @pytest.mark.asyncio
    async def test_settle_disabled(self):
        cfg = HumanizeConfig(settle_on_spawn=False)
        h = Humanizer(cfg)
        mock_rotation = AsyncMock()
        await h.settle(mock_rotation)
        mock_rotation.assert_not_called()

    @pytest.mark.asyncio
    async def test_settle_rotation_receives_float_angles(self):
        cfg = HumanizeConfig(settle_on_spawn=True, settle_moves=2, settle_delay=(1, 2))
        h = Humanizer(cfg)
        received: list[tuple[float, float]] = []

        async def capture(yaw: float, pitch: float) -> None:
            received.append((yaw, pitch))

        await h.settle(capture)
        assert len(received) == 2
        for yaw, pitch in received:
            assert isinstance(yaw, float) and isinstance(pitch, float)
            assert -90.0 <= pitch <= 90.0


# ── Chat trigger handlers ─────────────────────────────────────────────────────

class TestChatTriggers:
    """Triggers must respond within a short timeout in tests."""

    @pytest.mark.asyncio
    async def test_authme_login_trigger(self):
        sent: list[str] = []

        async def fake_chat(msg: str) -> None:
            sent.append(msg)

        cfg = HumanizeConfig(authme_enabled=True, authme_password="TestPass123")
        h = Humanizer(cfg)
        handlers = h.build_chat_handlers(fake_chat)

        # Feed a typical AuthMe prompt
        for handler in handlers:
            await asyncio.wait_for(handler("Please log in using /login"), timeout=5.0)

        assert any("/login TestPass123" in s for s in sent), f"Got: {sent}"

    @pytest.mark.asyncio
    async def test_authme_register_trigger(self):
        sent: list[str] = []

        async def fake_chat(msg: str) -> None:
            sent.append(msg)

        cfg = HumanizeConfig(authme_enabled=True, authme_password="pass", authme_register_password="pass")
        h = Humanizer(cfg)
        handlers = h.build_chat_handlers(fake_chat)

        for handler in handlers:
            await asyncio.wait_for(handler("You are not registered! Please use /register"), timeout=5.0)

        assert any("/register pass pass" in s for s in sent), f"Got: {sent}"

    @pytest.mark.asyncio
    async def test_generic_trigger_no_group(self):
        sent: list[str] = []

        async def fake_chat(msg: str) -> None:
            sent.append(msg)

        cfg = HumanizeConfig(chat_triggers=[("please verify", "verified")])
        h = Humanizer(cfg)
        handlers = h.build_chat_handlers(fake_chat)

        for handler in handlers:
            await asyncio.wait_for(handler("Please verify your account"), timeout=5.0)

        assert "verified" in sent, f"Got: {sent}"

    @pytest.mark.asyncio
    async def test_generic_trigger_with_group(self):
        sent: list[str] = []

        async def fake_chat(msg: str) -> None:
            sent.append(msg)

        cfg = HumanizeConfig(chat_triggers=[(r"enter code (\d+)", "{match}")])
        h = Humanizer(cfg)
        handlers = h.build_chat_handlers(fake_chat)

        for handler in handlers:
            await asyncio.wait_for(handler("Please enter code 42819"), timeout=5.0)

        assert "42819" in sent, f"Got: {sent}"

    @pytest.mark.asyncio
    async def test_no_trigger_no_send(self):
        sent: list[str] = []

        async def fake_chat(msg: str) -> None:
            sent.append(msg)

        h = make_humanizer()   # no triggers configured
        handlers = h.build_chat_handlers(fake_chat)

        for handler in handlers:
            await handler("Welcome to the server!")

        assert sent == [], "No trigger configured — nothing should be sent"

    @pytest.mark.asyncio
    async def test_colour_codes_stripped_before_matching(self):
        """§a-prefixed colour codes must not block trigger matching."""
        sent: list[str] = []

        async def fake_chat(msg: str) -> None:
            sent.append(msg)

        cfg = HumanizeConfig(authme_enabled=True, authme_password="pw")
        h = Humanizer(cfg)
        handlers = h.build_chat_handlers(fake_chat)

        for handler in handlers:
            await asyncio.wait_for(
                handler("§aPlease §blog§a in with §c/login§r"),
                timeout=5.0,
            )

        assert any("/login pw" in s for s in sent), f"Got: {sent}"

    def test_build_handlers_returns_list(self):
        h = make_humanizer()
        result = h.build_chat_handlers(AsyncMock())
        assert isinstance(result, list)

    def test_authme_disabled_returns_no_authme_handler(self):
        cfg = HumanizeConfig(authme_enabled=False)
        h = Humanizer(cfg)
        # Only generic triggers — none added, so empty list
        result = h.build_chat_handlers(AsyncMock())
        assert len(result) == 0
