"""
server_status.py — Query a Minecraft server's status (MOTD, version, player count)
                   without logging in.

Uses the Status protocol state — no account required.

Usage:
    python examples/server_status.py <host> [port]
"""
from __future__ import annotations

import asyncio
import json
import sys
import time

from mcpycore.network.stream import AsyncStream
from mcpycore.protocol.serializers.buffer import PacketBuffer


async def ping(host: str, port: int = 25565, timeout: float = 10.0) -> dict:
    """
    Send a Minecraft status request and return the JSON response.

    Returns a dict with keys: version, players, description, latency_ms
    """
    stream = await AsyncStream.open(host, port, timeout=timeout)

    try:
        # Handshake → Status
        buf = PacketBuffer()
        buf.write_varint(763)           # protocol_version (any works for status)
        buf.write_string(host)
        buf.write_ushort(port)
        buf.write_varint(1)             # next_state = 1 (status)
        await stream.write_packet(0x00, buf.flush())

        # Status Request
        await stream.write_packet(0x00, b"")

        # Status Response
        packet_id, buf = await stream.read_packet()
        if packet_id != 0x00:
            raise RuntimeError(f"Expected status response (0x00), got 0x{packet_id:02X}")
        response_json = buf.read_string()

        # Ping
        t0 = time.monotonic()
        ping_buf = PacketBuffer()
        ping_buf.write_long(int(t0 * 1000))
        await stream.write_packet(0x01, ping_buf.flush())

        ping_id, ping_buf = await stream.read_packet()
        latency_ms = (time.monotonic() - t0) * 1000

        data = json.loads(response_json)
        data["latency_ms"] = round(latency_ms, 1)
        return data

    finally:
        await stream.close()


def print_status(host: str, port: int, data: dict) -> None:
    version  = data.get("version", {})
    players  = data.get("players", {})
    desc     = data.get("description", {})

    # MOTD can be str or {"text": "..."}
    if isinstance(desc, dict):
        motd = desc.get("text", "") or desc.get("translate", "")
    else:
        motd = str(desc)

    # Strip colour codes
    import re
    motd = re.sub(r"§.", "", motd).strip()

    print(f"\n{'='*50}")
    print(f"  Server:   {host}:{port}")
    print(f"  MOTD:     {motd}")
    print(f"  Version:  {version.get('name', '?')} (protocol {version.get('protocol', '?')})")
    print(f"  Players:  {players.get('online', '?')}/{players.get('max', '?')}")
    if players.get("sample"):
        names = [p.get("name", "") for p in players["sample"][:5]]
        print(f"  Online:   {', '.join(names)}")
    print(f"  Latency:  {data.get('latency_ms', '?')}ms")
    print(f"{'='*50}\n")


async def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <host> [port]")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 25565

    print(f"Pinging {host}:{port}…")
    try:
        data = await ping(host, port)
        print_status(host, port, data)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
