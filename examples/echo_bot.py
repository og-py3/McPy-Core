"""
Echo Bot — connects to a server and echoes every chat message back.

Demonstrates: chat, health, entities, inventory, tab list, boss bars, titles.

Usage:
    python examples/echo_bot.py localhost 25565 EchoBot
    python examples/echo_bot.py play.example.com          # port 25565, name EchoBot
"""

import sys
from mcpycore import MinecraftClient, OfflineAuth
from mcpycore.events import (
    EVT_CONNECTED, EVT_CHAT, EVT_SYSTEM, EVT_HEALTH,
    EVT_SPAWN_ENTITY, EVT_DISCONNECT, EVT_PLAYER_LIST_UPDATE,
    EVT_BOSS_BAR, EVT_TITLE, EVT_SUBTITLE, EVT_ACTION_BAR,
    EVT_INVENTORY_UPDATE, EVT_TRANSFER, EVT_RESPAWN,
    EVT_CHUNK_LOAD, EVT_CHUNK_UNLOAD,
)


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 25565
    username = sys.argv[3] if len(sys.argv) > 3 else "EchoBot"

    client = MinecraftClient(host, port=port, auth=OfflineAuth(username))

    @client.on(EVT_CONNECTED)
    def on_connected(c):
        print(f"[EchoBot] Connected as {c.profile.username} | {c.version_name}")
        print(f"[EchoBot] Position: {c.position}")
        print(f"[EchoBot] Game mode: {c.game_mode}")

    @client.on(EVT_CHAT)
    def on_chat(packet):
        msg = getattr(packet, "message", str(packet))
        sender = getattr(packet, "sender", "unknown")
        print(f"[CHAT] {sender}: {msg}")
        if client.profile and sender != str(client.profile.player_uuid):
            client.send_chat(f"Echo: {msg}")

    @client.on(EVT_SYSTEM)
    def on_system(packet):
        content = getattr(packet, "content", str(packet))
        print(f"[SYS] {content}")

    @client.on(EVT_HEALTH)
    def on_health(packet):
        print(
            f"[HP] {packet.health:.1f}/20  "
            f"Food={packet.food}/20  Sat={packet.food_saturation:.1f}"
        )
        if packet.health <= 0:
            print("[!] Died — respawning…")
            client.respawn()

    @client.on(EVT_SPAWN_ENTITY)
    def on_entity(entity):
        print(f"[ENTITY] Spawned: {entity}")

    @client.on(EVT_PLAYER_LIST_UPDATE)
    def on_tab(pkt):
        print(f"[TAB] {client.tab_list.online_count()} players online")

    @client.on(EVT_BOSS_BAR)
    def on_boss(pkt):
        if pkt.is_add:
            print(f"[BOSS] {pkt.title!r}  {pkt.health*100:.0f}%")
        elif pkt.is_remove:
            print(f"[BOSS] Removed {pkt.boss_uuid}")

    @client.on(EVT_TITLE)
    def on_title(pkt):
        print(f"[TITLE] {pkt.text}")

    @client.on(EVT_SUBTITLE)
    def on_sub(pkt):
        print(f"[SUBTITLE] {pkt.text}")

    @client.on(EVT_ACTION_BAR)
    def on_ab(pkt):
        print(f"[ACTIONBAR] {pkt.text}")

    @client.on(EVT_INVENTORY_UPDATE)
    def on_inv(pkt):
        filled = sum(1 for s in pkt.slots if s.present)
        print(f"[INV] {filled}/{len(pkt.slots)} slots filled")

    @client.on(EVT_CHUNK_LOAD)
    def on_chunk_load(chunk):
        pass  # quiet; uncomment to debug: print(f"[CHUNK] Loaded {chunk}")

    @client.on(EVT_CHUNK_UNLOAD)
    def on_chunk_unload(cx, cz):
        pass

    @client.on(EVT_TRANSFER)
    def on_transfer(host, port):
        print(f"[TRANSFER] Server redirected to {host}:{port}")

    @client.on(EVT_RESPAWN)
    def on_respawn(pkt):
        print("[RESPAWN] Dimension changed / respawned")

    @client.on(EVT_DISCONNECT)
    def on_disconnect(reason):
        print(f"[-] Disconnected: {reason}")

    print(f"Connecting to {host}:{port} as {username}…")
    try:
        client.connect()
        client.run()
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
