"""
Server Ping — query a server's status without logging in.

Usage:
    python examples/server_ping.py play.hypixel.net
    python examples/server_ping.py localhost 25565
"""

import sys
import json
from mcpycore import MinecraftClient


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 25565

    print(f"Pinging {host}:{port}…")
    try:
        info = MinecraftClient.ping(host, port, timeout=5.0)
    except Exception as e:
        print(f"Failed: {e}")
        return

    desc = info.get("description", "")
    if isinstance(desc, dict):
        desc = desc.get("text", json.dumps(desc))

    players = info.get("players", {})
    version = info.get("version", {})

    print(f"  MOTD:     {desc}")
    print(f"  Players:  {players.get('online', '?')} / {players.get('max', '?')}")
    print(f"  Version:  {version.get('name', '?')} (protocol {version.get('protocol', '?')})")

    sample = players.get("sample", [])
    if sample:
        names = ", ".join(p["name"] for p in sample[:10])
        print(f"  Online:   {names}")


if __name__ == "__main__":
    main()
