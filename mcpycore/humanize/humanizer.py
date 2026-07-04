"""
mcpycore.humanize.humanizer — anti-bot-detection timing and behaviour layer.

Makes every phase of the connection look exactly like a real human player:

  • Randomised TCP-to-handshake delay      (network RTT jitter)
  • Randomised handshake-to-login delay    (client loading screen)
  • Randomised configuration settle time  (resource-pack / world download)
  • Natural, non-zero spawn look angles   (no one spawns staring at 0°/0°)
  • Jittered keep-alive responses         (human reaction time variance)
  • Optional post-spawn micro-movement    (a real player always wiggles)
  • Auto-detect & respond to common anti-bot chat challenges:
      AuthMe  : /login <pass> / /register <pass> <pass>
      NuVotifier / EasyAntiBot : digit / text CAPTCHAs
      Custom  : configurable trigger→response pairs
"""
from __future__ import annotations

import asyncio
import random
import re
from dataclasses import dataclass, field
from typing import Callable, Awaitable


# ── Config dataclass ──────────────────────────────────────────────────────────

@dataclass
class HumanizeConfig:
    """
    All timing parameters are (min_ms, max_ms) tuples.
    Set ``enabled=False`` to disable the entire layer with zero overhead.
    """

    enabled: bool = True

    # Connection-phase delays (milliseconds)
    pre_handshake_delay:    tuple[float, float] = (80,  350)
    pre_login_delay:        tuple[float, float] = (120, 600)
    post_login_delay:       tuple[float, float] = (600, 2400)   # loading screen
    config_settle_delay:    tuple[float, float] = (200, 900)    # config state

    # Play-phase delays (milliseconds)
    keepalive_jitter:       tuple[float, float] = (5,   180)    # extra delay before ACK
    position_confirm_delay: tuple[float, float] = (15,  120)

    # Spawn look angles (degrees) — none of these should be exactly 0
    initial_yaw_range:   tuple[float, float] = (-179.0, 180.0)
    initial_pitch_range: tuple[float, float] = (-15.0,  25.0)

    # Post-spawn micro-movement
    settle_on_spawn: bool = True
    settle_moves: int = 3                       # how many micro-rotations
    settle_delay: tuple[float, float] = (300, 900)

    # Auto-login (AuthMe, FastLogin, etc.)
    authme_enabled:  bool = False
    authme_password: str  = ""
    authme_register_password: str = ""          # left empty → re-use authme_password

    # Generic chat-trigger → response pairs
    # Each entry: (trigger_pattern, response_template)
    # In the response, {match} is replaced with the first regex group (useful
    # for digit CAPTCHAs where the bot has to echo a number).
    chat_triggers: list[tuple[str, str]] = field(default_factory=list)


# ── Humanizer class ───────────────────────────────────────────────────────────

class Humanizer:
    """
    Wraps a :class:`HumanizeConfig` and exposes helpers that the Connection
    and Client layers call at each protocol phase.
    """

    def __init__(self, config: HumanizeConfig | None = None) -> None:
        self.config = config or HumanizeConfig()
        self._spawned = False
        self._spawn_yaw   = 0.0
        self._spawn_pitch = 0.0

    # ── Phase delays ──────────────────────────────────────────────────────

    async def pre_handshake(self) -> None:
        """Called right after TCP connects, before the Handshake packet."""
        await self._delay(self.config.pre_handshake_delay)

    async def pre_login(self) -> None:
        """Called just before sending LoginStart."""
        await self._delay(self.config.pre_login_delay)

    async def post_login(self) -> None:
        """
        Called after LoginSuccess — simulates the client loading the world.
        This is the most important delay: anti-bot systems flag bots that
        enter the play state instantly after login.
        """
        await self._delay(self.config.post_login_delay)

    async def config_settle(self) -> None:
        """Called inside the Configuration state between packets."""
        await self._delay(self.config.config_settle_delay)

    async def keepalive_jitter(self) -> None:
        """Added before echoing a keep-alive packet back to the server."""
        await self._delay(self.config.keepalive_jitter)

    async def position_confirm(self) -> None:
        """Added before confirming a server-sent position."""
        await self._delay(self.config.position_confirm_delay)

    # ── Spawn angles ──────────────────────────────────────────────────────

    def spawn_angles(self) -> tuple[float, float]:
        """
        Return (yaw, pitch) that look natural on first spawn.
        Result is stable within a session — calling twice returns the same pair.
        """
        if not self._spawned:
            lo_y, hi_y = self.config.initial_yaw_range
            lo_p, hi_p = self.config.initial_pitch_range
            self._spawn_yaw   = random.uniform(lo_y, hi_y)
            self._spawn_pitch = random.uniform(lo_p, hi_p)
            self._spawned = True
        return self._spawn_yaw, self._spawn_pitch

    # ── Chat-trigger / anti-bot bypass ────────────────────────────────────

    def build_chat_handlers(
        self,
        send_chat: Callable[[str], Awaitable[None]],
    ) -> list[Callable[[str], Awaitable[None]]]:
        """
        Return a list of async callables suitable for wiring into the client's
        chat event.  Each callable receives the raw chat string and fires a
        response if it recognises a pattern.

        Usage in MinecraftClient::

            for handler in humanizer.build_chat_handlers(client.send_chat):
                client.on("system_chat", handler)
                client.on("chat", lambda msg, _uuid: handler(msg))
        """
        handlers: list[Callable[[str], Awaitable[None]]] = []

        if self.config.authme_enabled and self.config.authme_password:
            password     = self.config.authme_password
            reg_password = self.config.authme_register_password or password
            handlers.append(_make_authme_handler(send_chat, password, reg_password))

        for pattern, response_tpl in self.config.chat_triggers:
            handlers.append(_make_trigger_handler(send_chat, pattern, response_tpl))

        return handlers

    # ── Micro-movement (post-spawn settle) ────────────────────────────────

    async def settle(
        self,
        send_rotation: Callable[[float, float], Awaitable[None]],
    ) -> None:
        """
        Perform a few small look-angle adjustments after spawn to mimic a
        human "looking around" after loading in.

        *send_rotation* is ``async def(yaw, pitch) -> None``.
        """
        if not self.config.settle_on_spawn:
            return
        yaw, pitch = self.spawn_angles()
        for _ in range(self.config.settle_moves):
            await self._delay(self.config.settle_delay)
            yaw   += random.gauss(0, 6.0)      # small random drift
            pitch += random.gauss(0, 3.0)
            pitch  = max(-90.0, min(90.0, pitch))
            await send_rotation(yaw, pitch)

    # ── Internal ──────────────────────────────────────────────────────────

    async def _delay(self, range_ms: tuple[float, float]) -> None:
        if not self.config.enabled:
            return
        lo, hi = range_ms
        secs = random.uniform(lo, hi) / 1000.0
        await asyncio.sleep(secs)


# ── Chat-trigger factories ────────────────────────────────────────────────────

def _make_authme_handler(
    send_chat: Callable[[str], Awaitable[None]],
    password: str,
    reg_password: str,
) -> Callable[[str], Awaitable[None]]:
    """
    Handles AuthMe, xAuth, LoginSecurity, and similar plugins.

    Detects:
      • /login prompt  → sends /login <password>
      • /register prompt → sends /register <password> <password>
    """
    _LOGIN_RE    = re.compile(r"/login|please log|type your password|do /login", re.I)
    _REGISTER_RE = re.compile(r"/register|you are not registered|please register", re.I)

    async def handler(msg: str) -> None:
        clean = re.sub(r"§.", "", msg)          # strip colour codes
        if _REGISTER_RE.search(clean):
            await asyncio.sleep(random.uniform(0.6, 2.0))
            await send_chat(f"/register {reg_password} {reg_password}")
        elif _LOGIN_RE.search(clean):
            await asyncio.sleep(random.uniform(0.6, 1.8))
            await send_chat(f"/login {password}")

    return handler


def _make_trigger_handler(
    send_chat: Callable[[str], Awaitable[None]],
    pattern: str,
    response_tpl: str,
) -> Callable[[str], Awaitable[None]]:
    """Generic regex-trigger → response handler (e.g. digit CAPTCHAs)."""
    compiled = re.compile(pattern, re.I)

    async def handler(msg: str) -> None:
        clean = re.sub(r"§.", "", msg)
        m = compiled.search(clean)
        if m:
            first_group = m.group(1) if m.lastindex else ""
            response = response_tpl.replace("{match}", first_group)
            await asyncio.sleep(random.uniform(0.8, 2.5))
            await send_chat(response)

    return handler
