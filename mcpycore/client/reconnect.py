"""
ReconnectPolicy — pluggable reconnection strategies.

Usage::

    policy = ExponentialBackoff(max_attempts=5, base_delay=1.0, max_delay=60.0)

    async with policy.session(client) as session:
        await session.run()
"""
from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


class ReconnectPolicy(ABC):
    """Abstract base for reconnect strategies."""

    @abstractmethod
    async def wait(self, attempt: int) -> bool:
        """
        Called before each reconnect attempt.

        Parameters
        ----------
        attempt : int
            Zero-based attempt number.

        Returns
        -------
        bool
            True to proceed with reconnect, False to give up.
        """

    def on_success(self) -> None:
        """Called after a successful connection. Reset internal state."""


class NoReconnect(ReconnectPolicy):
    """Never reconnect — raise on disconnect."""

    async def wait(self, attempt: int) -> bool:
        return False


class FixedDelay(ReconnectPolicy):
    """Reconnect with a fixed delay between attempts."""

    def __init__(self, delay: float = 3.0, max_attempts: int = 5) -> None:
        self.delay = delay
        self.max_attempts = max_attempts

    async def wait(self, attempt: int) -> bool:
        if attempt >= self.max_attempts:
            log.warning("Max reconnect attempts (%d) reached", self.max_attempts)
            return False
        log.info("Reconnecting in %.1fs (attempt %d/%d)…",
                 self.delay, attempt + 1, self.max_attempts)
        await asyncio.sleep(self.delay)
        return True


class ExponentialBackoff(ReconnectPolicy):
    """
    Reconnect with exponential back-off plus optional jitter.

    Delay formula: ``min(base * 2^attempt, max_delay) + jitter``
    """

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        max_attempts: int | None = None,
        jitter: bool = True,
    ) -> None:
        self.base_delay  = base_delay
        self.max_delay   = max_delay
        self.max_attempts = max_attempts
        self.jitter      = jitter
        self._attempt    = 0

    async def wait(self, attempt: int) -> bool:
        if self.max_attempts is not None and attempt >= self.max_attempts:
            log.warning("Max reconnect attempts (%d) reached", self.max_attempts)
            return False
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        if self.jitter:
            delay += random.uniform(0, delay * 0.25)
        log.info("Reconnecting in %.1fs (attempt %d)…", delay, attempt + 1)
        await asyncio.sleep(delay)
        return True

    def on_success(self) -> None:
        self._attempt = 0


class InfiniteRetry(ReconnectPolicy):
    """Retry indefinitely with exponential back-off."""

    def __init__(self, base_delay: float = 2.0, max_delay: float = 120.0) -> None:
        self.base_delay = base_delay
        self.max_delay  = max_delay

    async def wait(self, attempt: int) -> bool:
        delay = min(self.base_delay * (2 ** min(attempt, 10)), self.max_delay)
        log.info("Reconnecting in %.1fs (attempt %d)…", delay, attempt + 1)
        await asyncio.sleep(delay)
        return True
