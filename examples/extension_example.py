"""
extension_example.py — Demonstrates the McPy-Core extension/plugin system.

Extensions are ordinary Python modules with a setup(client) function.
This example creates a temporary in-memory extension and loads it dynamically.

Usage:
    python examples/extension_example.py <host> [port] [username]
"""
from __future__ import annotations

import asyncio
import sys
import types


def build_extension_module(name: str) -> types.ModuleType:
    """Create an in-memory extension module."""
    mod = types.ModuleType(name)

    async def setup(client) -> None:
        print(f"[Extension:{name}] Loaded! Registering handlers…")

        @client.on("connect")
        async def on_connect(c):
            print(f"[Extension:{name}] on_connect fired — version={c.version_name}")

        @client.on("health")
        async def on_health(health, food, sat):
            if health <= 10:
                print(f"[Extension:{name}] Low health warning: {health:.1f}/20")

        @client.on("chat")
        async def on_chat(msg, sender):
            print(f"[Extension:{name}] Chat intercepted: {msg!r}")

    async def teardown(client) -> None:
        print(f"[Extension:{name}] Unloaded — cleaning up")

    mod.setup = setup
    mod.teardown = teardown
    return mod


async def main(host: str, port: int, username: str) -> None:
    from mcpycore import MinecraftClient
    from mcpycore.utils.logging import setup_logging
    import sys as _sys

    setup_logging("INFO")

    client = MinecraftClient(host=host, port=port, username=username)

    # Register an extension module in sys.modules so the loader can find it
    ext_module = build_extension_module("demo_extension")
    _sys.modules["demo_extension"] = ext_module
    client.load_extension("demo_extension")

    print(f"Loaded extensions: {client.extensions.loaded}")

    @client.event
    async def on_disconnect(reason: str):
        print(f"Disconnected: {reason}")

    await client.start()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <host> [port] [username]")
        sys.exit(1)
    asyncio.run(main(
        sys.argv[1],
        int(sys.argv[2]) if len(sys.argv) > 2 else 25565,
        sys.argv[3] if len(sys.argv) > 3 else "ExtBot",
    ))
