"""
Inventory Viewer — connects and prints the player's full inventory.

Usage:
    python examples/inventory_viewer.py <host> [port] [username]
    python examples/inventory_viewer.py localhost 25565 InvBot
"""

import sys
import time

from mcpycore import MinecraftClient, OfflineAuth
from mcpycore.events import (
    EVT_CONNECTED, EVT_INVENTORY_UPDATE, EVT_SLOT_UPDATE,
    EVT_HELD_ITEM_CHANGE, EVT_DISCONNECT,
)


SLOT_LABELS = {
    0: "crafting result",
    **{i: f"crafting {i}" for i in range(1, 5)},
    5: "helmet", 6: "chestplate", 7: "leggings", 8: "boots",
    **{i: f"main {i-9}" for i in range(9, 36)},
    **{i: f"hotbar {i-36}" for i in range(36, 45)},
    45: "offhand",
}


def print_inventory(inv) -> None:
    print("\n──── Inventory ─────────────────────────────────────────")
    for i, slot in enumerate(inv.slots):
        if slot.present:
            label = SLOT_LABELS.get(i, f"slot {i}")
            marker = " ◄" if i == 36 + inv.held_slot else ""
            print(f"  [{i:2d}] {label:20s}  item_id={slot.item_id}  x{slot.count}{marker}")
    filled = sum(1 for s in inv.slots if s.present)
    print(f"────  {filled} / {len(inv.slots)} slots  ──────────────────────────────")


def main():
    host     = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port     = int(sys.argv[2]) if len(sys.argv) > 2 else 25565
    username = sys.argv[3] if len(sys.argv) > 3 else "InvBot"

    client = MinecraftClient(host, port=port, auth=OfflineAuth(username))

    @client.on(EVT_CONNECTED)
    def on_connected(c):
        print(f"[+] Connected as {c.profile.username} | {c.version_name}")
        print("    Waiting for inventory data…")

    @client.on(EVT_INVENTORY_UPDATE)
    def on_inv(pkt):
        print_inventory(client.inventory)

    @client.on(EVT_SLOT_UPDATE)
    def on_slot(pkt):
        label = SLOT_LABELS.get(pkt.slot, f"slot {pkt.slot}")
        if pkt.item.present:
            print(f"  [SLOT] {label}: item_id={pkt.item.item_id}  x{pkt.item.count}")
        else:
            print(f"  [SLOT] {label}: (empty)")

    @client.on(EVT_HELD_ITEM_CHANGE)
    def on_held(pkt):
        print(f"  [HELD] Active slot → {pkt.slot}")

    @client.on(EVT_DISCONNECT)
    def on_dc(reason):
        print(f"[-] Disconnected: {reason}")

    print(f"Connecting to {host}:{port} as {username}…")
    try:
        client.connect()
        client.run()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
