"""
chat_bot.py — Echo bot with command prefix.

Features:
- Echo messages starting with ! back to chat
- Respond to !pos with current position
- Respond to !ping with latency
- Respond to !health with health/food status

Usage:
    python examples/chat_bot.py <host> [port] [username]
"""
from __future__ import annotations

import asyncio
import sys
import time

from mcpycore import MinecraftClient
from mcpycore.events.emitter import Events
from mcpycore.utils.logging import setup_logging


PREFIX = "!"


class ChatBot:
    def __init__(self, client: MinecraftClient) -> None:
        self.client = client
        self._last_ping: float = 0.0
        self._latency_ms: float = 0.0
        self._register_handlers()

    def _register_handlers(self) -> None:
        c = self.client

        @c.event
        async def on_connect(client: MinecraftClient) -> None:
            print(f"[+] Connected as {client.profile.username} ({client.version_name})")

        @c.event
        async def on_spawn(x: float, y: float, z: float) -> None:
            await asyncio.sleep(1.0)
            await c.send_chat(f"McPy-Core bot online! Type {PREFIX}help")

        @c.event
        async def on_chat(message: str, sender) -> None:
            if not message.startswith(PREFIX):
                return
            command = message[len(PREFIX):].strip().lower()
            await self._handle_command(command, str(sender))

        @c.event
        async def on_system_chat(content: str, overlay: bool) -> None:
            if not overlay:
                print(f"[System] {content}")

        @c.event
        async def on_health(health: float, food: int, sat: float) -> None:
            if health <= 0:
                await asyncio.sleep(2.0)
                await c.respawn()

        @c.event
        async def on_keepalive(latency: float) -> None:
            self._latency_ms = latency

        @c.event
        async def on_disconnect(reason: str) -> None:
            print(f"[-] Disconnected: {reason}")

    async def _handle_command(self, command: str, sender: str) -> None:
        c = self.client
        parts = command.split(maxsplit=1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "help":
            await c.send_chat(f"Commands: {PREFIX}pos {PREFIX}ping {PREFIX}health {PREFIX}echo <msg>")

        elif cmd == "pos":
            x, y, z = c.position
            await c.send_chat(f"Position: ({x:.1f}, {y:.1f}, {z:.1f})")

        elif cmd == "ping":
            await c.send_chat(f"Latency: {self._latency_ms:.1f}ms")

        elif cmd == "health":
            await c.send_chat(
                f"Health: {c.health:.1f}/20 | Food: {c.food}/20 | Sat: {c.food_saturation:.1f}"
            )

        elif cmd == "echo":
            if args:
                await c.send_chat(args)

        elif cmd == "metrics":
            r = c.metrics.report()
            await c.send_chat(
                f"Packets: in={r['packets_in']} out={r['packets_out']} "
                f"uptime={r['uptime_s']:.0f}s"
            )

        elif cmd == "sneak":
            await c.sneak(True)
            await asyncio.sleep(2.0)
            await c.sneak(False)

        else:
            await c.send_chat(f"Unknown command: {PREFIX}{cmd}")


async def main(host: str, port: int, username: str) -> None:
    setup_logging(level="INFO")
    client = MinecraftClient(host=host, port=port, username=username)
    ChatBot(client)
    await client.start()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <host> [port] [username]")
        sys.exit(1)
    asyncio.run(main(
        sys.argv[1],
        int(sys.argv[2]) if len(sys.argv) > 2 else 25565,
        sys.argv[3] if len(sys.argv) > 3 else "ChatBot",
    ))
