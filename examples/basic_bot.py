"""
basic_bot.py — Minimal McPy-Core bot example.

Connects to a server, logs all events, keeps itself alive.

Usage:
    python examples/basic_bot.py <host> [port] [username]
"""
from __future__ import annotations

import asyncio
import sys

from mcpycore import MinecraftClient
from mcpycore.client.reconnect import ExponentialBackoff
from mcpycore.events.emitter import Events
from mcpycore.utils.logging import setup_logging


async def main(host: str, port: int = 25565, username: str = "McPyCoreBot") -> None:
    setup_logging(level="DEBUG")

    client = MinecraftClient(
        host=host,
        port=port,
        username=username,
        reconnect_policy=ExponentialBackoff(base_delay=2.0, max_delay=30.0, max_attempts=5),
        debug=True,
    )

    @client.event
    async def on_connect(c: MinecraftClient) -> None:
        print(f"[+] Connected to {c.host}:{c.port} as {c.profile.username}")
        print(f"    Version: {c.version_name}")

    @client.event
    async def on_spawn(x: float, y: float, z: float) -> None:
        print(f"[+] Spawned at ({x:.1f}, {y:.1f}, {z:.1f})")

    @client.event
    async def on_chat(message: str, sender) -> None:
        print(f"[Chat] {sender}: {message}")

    @client.event
    async def on_system_chat(content: str, overlay: bool) -> None:
        if not overlay:
            print(f"[System] {content}")

    @client.event
    async def on_health(health: float, food: int, saturation: float) -> None:
        print(f"[Health] HP={health:.1f} Food={food} Sat={saturation:.1f}")
        if health <= 0:
            await asyncio.sleep(1.0)
            await client.respawn()

    @client.event
    async def on_keepalive(latency_ms: float) -> None:
        print(f"[KeepAlive] Latency: {latency_ms:.1f}ms")

    @client.event
    async def on_disconnect(reason: str) -> None:
        print(f"[-] Disconnected: {reason}")

    @client.event
    async def on_error(exc: Exception) -> None:
        print(f"[!] Error: {exc}")

    @client.event
    async def on_login(entity_id: int, game_mode: int) -> None:
        modes = {0: "Survival", 1: "Creative", 2: "Adventure", 3: "Spectator"}
        print(f"[+] Login: entity_id={entity_id}, mode={modes.get(game_mode, game_mode)}")

    await client.start()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <host> [port] [username]")
        sys.exit(1)
    host     = sys.argv[1]
    port     = int(sys.argv[2]) if len(sys.argv) > 2 else 25565
    username = sys.argv[3] if len(sys.argv) > 3 else "McPyCoreBot"
    asyncio.run(main(host, port, username))
