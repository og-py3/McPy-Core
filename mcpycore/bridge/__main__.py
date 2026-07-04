"""
CLI entry point for the McPy-Core bridge server.

Usage::

    python -m mcpycore.bridge
    python -m mcpycore.bridge --host 0.0.0.0 --port 25580
    mcpycore-bridge --port 25580          # if installed via pip
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from mcpycore.bridge.server import BridgeServer


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="McPy-Core WebSocket bridge — connect bots from any language",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--host", default="0.0.0.0",    help="Bind address")
    p.add_argument("--port", type=int, default=25580, help="WebSocket port")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    server = BridgeServer(host=args.host, port=args.port)
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
