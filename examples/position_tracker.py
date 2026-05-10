"""
Position Tracker — connects and prints the player position every 2 seconds.

Usage:
    python examples/position_tracker.py localhost 25565 TrackerBot
"""

import sys
import threading
import time
from mcpycore import MinecraftClient, OfflineAuth


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 25565
    username = sys.argv[3] if len(sys.argv) > 3 else "TrackerBot"

    client = MinecraftClient(host, port=port, auth=OfflineAuth(username))

    @client.on("connected")
    def on_connected(c):
        print(f"Connected as {c.profile.username}")

        def print_position():
            while client._running:
                x, y, z = client.position
                chunks = len(client.world)
                entities = len(client.entities)
                print(
                    f"  pos=({x:.2f}, {y:.2f}, {z:.2f})  "
                    f"chunks={chunks}  entities={entities}  "
                    f"health={client.health:.1f}  food={client.food}"
                )
                time.sleep(2.0)

        t = threading.Thread(target=print_position, daemon=True)
        t.start()

    @client.on("disconnect")
    def on_disconnect(reason):
        print(f"Disconnected: {reason}")

    print(f"Connecting to {host}:{port} as {username}…")
    client.connect()
    client.run()


if __name__ == "__main__":
    main()
