"""
Structured logging setup for McPy-Core.

Provides a consistent, colourised log format across all modules.

Usage::

    from mcpycore.utils.logging import get_logger, setup_logging

    setup_logging(level="DEBUG")
    log = get_logger(__name__)
    log.info("Connected to server")
"""
from __future__ import annotations

import logging
import sys
from typing import Literal


# ── Colour codes ──────────────────────────────────────────────────────────────

_RESET   = "\x1b[0m"
_BOLD    = "\x1b[1m"
_GREY    = "\x1b[38;5;245m"
_CYAN    = "\x1b[36m"
_GREEN   = "\x1b[32m"
_YELLOW  = "\x1b[33m"
_RED     = "\x1b[31m"
_MAGENTA = "\x1b[35m"

_LEVEL_COLOURS = {
    logging.DEBUG:    _GREY,
    logging.INFO:     _GREEN,
    logging.WARNING:  _YELLOW,
    logging.ERROR:    _RED,
    logging.CRITICAL: _MAGENTA,
}


class ColourFormatter(logging.Formatter):
    """Log formatter with ANSI colour codes."""

    FMT = "[{asctime}] [{levelname:<8}] {name}: {message}"

    def format(self, record: logging.LogRecord) -> str:
        colour = _LEVEL_COLOURS.get(record.levelno, _RESET)
        record.levelname = f"{colour}{record.levelname}{_RESET}"
        record.name      = f"{_CYAN}{record.name}{_RESET}"
        return logging.Formatter(self.FMT, style="{", datefmt="%H:%M:%S").format(record)


class PlainFormatter(logging.Formatter):
    FMT = "[{asctime}] [{levelname:<8}] {name}: {message}"

    def format(self, record: logging.LogRecord) -> str:
        return logging.Formatter(self.FMT, style="{", datefmt="%H:%M:%S").format(record)


def setup_logging(
    level: str | int = "INFO",
    colour: bool = True,
    handler: logging.Handler | None = None,
) -> None:
    """
    Configure root logging for McPy-Core.

    Call once at application startup::

        from mcpycore.utils.logging import setup_logging
        setup_logging(level="DEBUG")
    """
    root = logging.getLogger("mcpycore")
    root.setLevel(level)

    if not root.handlers:
        h = handler or logging.StreamHandler(sys.stdout)
        fmt = ColourFormatter() if colour else PlainFormatter()
        h.setFormatter(fmt)
        root.addHandler(h)
        root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'mcpycore' namespace."""
    if not name.startswith("mcpycore"):
        name = f"mcpycore.{name}"
    return logging.getLogger(name)
