"""
packet_inspector.py — Live packet sniffer / inspector CLI.

Connects to a server and prints every received packet in real-time,
with optional hex dump mode.

Usage:
    python examples/packet_inspector.py <host> [port] [username] [--hex]

Examples:
    python examples/packet_inspector.py localhost
    python examples/packet_inspector.py play.hypixel.net 25565 Inspector --hex
"""
from __future__ import annotations

import asyncio
import sys
from collections import Counter

from mcpycore import MinecraftClient
from mcpycore.debug.inspector import _CB_NAMES
from mcpycore.events.emitter import Events
from mcpycore.protocol.serializers.buffer import PacketBuffer
from mcpycore.utils.logging import setup_logging


class InspectorBot:
    def __init__(self, client: MinecraftClient, hex_dump: bool = False) -> None:
        self.client = client
        self.hex_dump = hex_dump
        self._packet_counts: Counter[int] = Counter()
        self._register()

    def _register(self) -> None:
        c = self.client

        @c.event
        async def on_connect(client: MinecraftClient) -> None:
            print(f"\n[INSPECTOR] Connected to {client.host}:{client.port}")
            print(f"[INSPECTOR] Version: {client.version_name}")
            print("[INSPECTOR] Watching all packets… (Ctrl-C to stop)\n")

        @c.event
        async def on_packet(packet_id: int, buf: PacketBuffer) -> None:
            self._packet_counts[packet_id] += 1
            name = _CB_NAMES.get(packet_id, "?")
            data = buf.getvalue()
            line = f"[RECV] 0x{packet_id:02X}  {name:<35} {len(data):>5}B"
            print(line)
            if self.hex_dump and len(data) > 0:
                self._hexdump(data[:128])
                if len(data) > 128:
                    print(f"       ... ({len(data) - 128} more bytes)")

        @c.event
        async def on_disconnect(reason: str) -> None:
            print(f"\n[INSPECTOR] Disconnected: {reason}")
            self._print_summary()

    def _hexdump(self, data: bytes) -> None:
        for i in range(0, len(data), 16):
            chunk = data[i : i + 16]
            hex_p   = " ".join(f"{b:02X}" for b in chunk)
            ascii_p = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            print(f"       {i:04X}  {hex_p:<48}  {ascii_p}")

    def _print_summary(self) -> None:
        print("\n[INSPECTOR] ─── Packet Summary ───")
        for pid, count in self._packet_counts.most_common(20):
            name = _CB_NAMES.get(pid, "unknown")
            print(f"  0x{pid:02X}  {name:<35} {count:>5}x")
        print(f"[INSPECTOR] Total unique packet types: {len(self._packet_counts)}")
        print(f"[INSPECTOR] Total packets received:    {sum(self._packet_counts.values())}")


async def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <host> [port] [username] [--hex]")
        sys.exit(1)

    host     = sys.argv[1]
    port     = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 25565
    username = next((a for a in sys.argv[3:] if not a.startswith("-")), "Inspector")
    hex_dump = "--hex" in sys.argv

    setup_logging(level="WARNING")   # suppress debug noise

    client = MinecraftClient(host=host, port=port, username=username)
    InspectorBot(client, hex_dump=hex_dump)

    try:
        await client.start()
    except KeyboardInterrupt:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
