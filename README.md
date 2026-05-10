# Mcpycore

A modern Python library for connecting to and interacting with Minecraft Java Edition servers.

**Supported versions:** Minecraft **1.20.2 → 1.21.11** (protocol 764–775) + snapshot builds

Inspired by [PyCraft](https://github.com/ammaraskar/pyCraft) but rebuilt from scratch for modern Python and modern Minecraft.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)

---

## Features

- **Full multi-version support** — 1.20.2 through 1.21.11, plus experimental snapshot detection
- Version-aware packet ID registry — one codebase handles all supported versions
- Full handshake → login → configuration → play lifecycle
- AES-128/CFB8 encryption (online-mode servers)
- zlib compression (threshold-based, as per protocol)
- Microsoft account auth (Device Code flow — no browser automation needed)
- Offline / cracked-server auth
- Event-driven API: `@client.on("event")` — no subclassing required
- World tracking: loaded chunks, block state lookup
- Entity tracking: spawn, movement, nearby queries
- Player actions: chat, move, swing, attack, interact, sneak, sprint, use item
- Inventory, tab-list, boss bar, scoreboard, title, and sound tracking
- Server status ping (no login required)
- 1.21+ Transfer packet support (server-to-server redirects)
- Registry collision detection via `verify_registry()`

---

## Installation

```bash
pip install mcpycore
```

Or install from source:

```bash
git clone https://github.com/youruser/mcpycore
cd mcpycore
pip install -e .
```

**Requirements:** Python 3.10+, `cryptography`, `requests`

---

## Quick Start

### Offline bot (cracked server)

```python
from mcpycore import MinecraftClient, OfflineAuth

client = MinecraftClient("localhost", auth=OfflineAuth("CoolBot"))

@client.on("connected")
def on_connected(c):
    print(f"Connected as {c.profile.username} — {c.version_name}")
    print(f"Position: {c.position}")

@client.on("chat_message")
def on_chat(packet):
    print(f"Chat: {packet.message}")

@client.on("system_message")
def on_system(packet):
    print(f"System: {packet.content}")

@client.on("set_health")
def on_health(packet):
    print(f"Health: {packet.health}/20  Food: {packet.food}/20")

client.connect()
client.run()
```

### Microsoft / online-mode server

```python
from mcpycore import MinecraftClient
from mcpycore.authentication import MicrosoftAuth
from mcpycore.versions import PROTOCOL_1_21_4

auth = MicrosoftAuth()   # prints a device code URL — visit it to log in
client = MinecraftClient(
    "play.example.com",
    auth=auth,
    protocol_version=PROTOCOL_1_21_4,
)

@client.on("connected")
def ready(c):
    c.send_chat("Hello from Mcpycore!")

client.connect()
client.run()
```

### Server status ping (no login)

```python
from mcpycore import MinecraftClient

info = MinecraftClient.ping("play.hypixel.net")
print(info["description"])
print(f"{info['players']['online']} / {info['players']['max']} players online")
```

---

## Version Compatibility

### Supported Protocol Versions

| Constant | Minecraft Version | Protocol | Notes |
|---|---|---|---|
| `PROTOCOL_1_20_2` | 1.20.2 | 764 | First version with Configuration state |
| `PROTOCOL_1_20_4` | 1.20.3 / 1.20.4 | 765 | Same protocol as 1.20.3 |
| `PROTOCOL_1_20_6` | 1.20.5 / 1.20.6 | 766 | Same protocol as 1.20.5 |
| `PROTOCOL_1_21` | 1.21 | 767 | SelectKnownPacks introduced |
| `PROTOCOL_1_21_1` | 1.21.1 | 767 | Same protocol as 1.21 |
| `PROTOCOL_1_21_2` | 1.21.2 | 768 | |
| `PROTOCOL_1_21_3` | 1.21.3 | 768 | Same protocol as 1.21.2 |
| `PROTOCOL_1_21_4` | 1.21.4 | 769 | |
| `PROTOCOL_1_21_5` | 1.21.5 | 770 | |
| `PROTOCOL_1_21_6` | 1.21.6 | 771 | |
| `PROTOCOL_1_21_7` | 1.21.7 | 772 | |
| `PROTOCOL_1_21_8` | 1.21.8 | 773 | |
| `PROTOCOL_1_21_10` | 1.21.9 / 1.21.10 | 774 | Same protocol as 1.21.9 |
| `PROTOCOL_1_21_11` | 1.21.11 | 775 | **Latest stable** |
| `PROTOCOL_LATEST` | 1.21.11 | 775 | Always points to newest stable |

### Snapshot Support

Any protocol version `>= 0x40000000` is a snapshot/pre-release build.
Mcpycore automatically falls back to the nearest stable version for packet dispatch
and issues a `UserWarning`:

```python
from mcpycore.versions import is_snapshot, nearest_stable

snapshot_proto = 0x40000200          # hypothetical snapshot
print(is_snapshot(snapshot_proto))   # True
print(nearest_stable(snapshot_proto))  # 775 (1.21.11)
```

### Feature Availability by Version

| Feature | 1.20.2 (764) | 1.21+ (767+) | 1.21.2+ (768+) |
|---|---|---|---|
| Configuration state | ✓ | ✓ | ✓ |
| Encryption (online mode) | ✓ | ✓ | ✓ |
| zlib compression | ✓ | ✓ | ✓ |
| SelectKnownPacks handshake | — | ✓ | ✓ |
| Transfer packet | — | ✓ | ✓ |
| Cookie request/store | — | ✓ | ✓ |
| Projectile power packet | — | — | ✓ |
| Player rotation (separate) | — | — | 1.21.11+ |

### Registry Collision Detection

Use `verify_registry()` to check for packet ID conflicts in the registry:

```python
from mcpycore.versions import verify_registry

collisions = verify_registry()   # check all protocols
for proto, entries in collisions.items():
    for pid, names in entries:
        print(f"Protocol {proto}: 0x{pid:02X} → {names}")

# Or check a specific version:
collisions = verify_registry(protocol=769)
```

---

## Multi-Version Usage

```python
from mcpycore import MinecraftClient, OfflineAuth
from mcpycore.versions import PROTOCOL_1_20_4, PROTOCOL_LATEST, version_name

# Connect to a 1.20.4 server
client_old = MinecraftClient("old.server.net", auth=OfflineAuth("Bot"),
                              protocol_version=PROTOCOL_1_20_4)

# Connect to a 1.21.11 server (default — latest)
client_new = MinecraftClient("new.server.net", auth=OfflineAuth("Bot"),
                              protocol_version=PROTOCOL_LATEST)

print(version_name(PROTOCOL_LATEST))   # "1.21.11"
print(client_new.version_name)         # "1.21.11"
```

---

## Player Actions

```python
client.move_to(100.0, 64.0, -200.0, yaw=90.0)
client.look_at(yaw=0.0, pitch=-30.0)
client.send_chat("Hello!")
client.send_chat("/gamemode creative")
client.attack_entity(entity_id=42)
client.interact_entity(entity_id=42, hand=0)
client.swing_arm(hand=0)        # 0=main, 1=off
client.use_item(hand=0)
client.use_item_on_block(x=0, y=64, z=0, face=1)
client.dig_block(x=0, y=64, z=0)
client.drop_item(drop_stack=False)
client.start_sneaking()
client.stop_sneaking()
client.start_sprinting()
client.stop_sprinting()
client.set_held_slot(0)          # 0–8
client.close_container()
client.respawn()                 # after death
```

---

## World & Entity Access

```python
# Block state at world coords (None if chunk not loaded)
state_id = client.world.get_block_state(100, 64, -200)

# All loaded chunks
for chunk in client.world.loaded_chunks():
    print(chunk)

# Entities within 16 blocks
nearby = client.entities.nearby(client.x, client.y, client.z, radius=16)
for entity in nearby:
    print(entity)

# Look up by ID or UUID
entity = client.entities.get(entity_id=42)
x, y, z = client.position
```

---

## Events Reference

| Constant | String | Arguments | Description |
|---|---|---|---|
| `EVT_CONNECTED` | `"connected"` | `client` | Login complete, play state entered |
| `EVT_DISCONNECT` | `"disconnect"` | `reason: str` | Kicked or connection lost |
| `EVT_POSITION` | `"position"` | `x, y, z, yaw, pitch` | Server-synced player position |
| `EVT_HEALTH` | `"set_health"` | `SetHealth` packet | Health/food/saturation update |
| `EVT_CHAT` | `"chat_message"` | `ChatMessage` packet | Player chat message |
| `EVT_SYSTEM` | `"system_message"` | `SystemChatMessage` packet | Server/system message |
| `EVT_BLOCK_UPDATE` | `"block_update"` | `BlockUpdate` packet | Single block changed |
| `EVT_CHUNK_LOAD` | `"chunk_load"` | `Chunk` object | Chunk fully loaded |
| `EVT_CHUNK_UNLOAD` | `"chunk_unload"` | `chunk_x, chunk_z` | Chunk unloaded |
| `EVT_SPAWN_ENTITY` | `"spawn_entity"` | `Entity` object | Entity spawned |
| `EVT_ENTITY_MOVE` | `"entity_move"` | `Entity` object | Entity position/rotation updated |
| `EVT_REMOVE_ENTITY` | `"remove_entities"` | list of IDs | Entities removed |
| `EVT_RESPAWN` | `"respawn"` | packet | Player respawned/dimension changed |
| `EVT_TRANSFER` | `"transfer"` | `host: str, port: int` | 1.21+ server redirect |
| `EVT_BOSS_BAR` | `"boss_bar"` | `BossBar` packet | Boss bar add/update/remove |
| `EVT_TITLE` | `"title"` | `SetTitleText` packet | Title text set |
| `EVT_INVENTORY_UPDATE` | `"set_container_content"` | packet | Full inventory state |
| `EVT_DEATH` | `"combat_death"` | raw bytes | Player death |

Use typed constants from `mcpycore.events` to avoid typos:

```python
from mcpycore.events import EVT_CHAT, EVT_HEALTH, EVT_BOSS_BAR

@client.on(EVT_CHAT)
def on_chat(pkt): ...
```

---

## Packet Reference

All packets are typed dataclasses under `mcpycore.packets`:

```
mcpycore.packets.login               — Handshake / login state
mcpycore.packets.status              — Server list ping
mcpycore.packets.play                — Main game protocol
mcpycore.packets.play.configuration  — Configuration state (1.20.2+)
mcpycore.packets.play.inventory      — Container / inventory packets
mcpycore.packets.play.boss_bar       — Boss bar packets
mcpycore.packets.play.title          — Title / subtitle / action bar
mcpycore.packets.play.player_list    — Tab list packets
mcpycore.packets.play.scoreboard     — Scoreboard packets
mcpycore.packets.play.sound          — Sound effect packets
mcpycore.packets.play.clientbound_1_21 — New 1.21+ packets (Transfer, Cookie, etc.)
```

Send any packet directly:

```python
from mcpycore.packets.play import SwingArm
client._conn.send_packet(SwingArm(hand=0))
```

---

## Logging

Mcpycore uses Python's standard `logging` module under the `mcpycore` logger hierarchy.
Enable debug output in your application:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Examples

```bash
# Echo bot — echoes player chat back to the server
python examples/echo_bot.py localhost 25565 BotName

# Server ping — query server info without logging in
python examples/server_ping.py play.hypixel.net

# Position tracker — print live position every 2 seconds
python examples/position_tracker.py localhost 25565 TrackerBot

# Chat logger — log all chat and system messages to a file
python examples/chat_logger.py localhost 25565 LoggerBot

# Inventory viewer — print inventory contents
python examples/inventory_viewer.py localhost 25565 InvBot
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

The packet ID registry in `mcpycore/versions.py` is the single place to update when Mojang shifts packet IDs in a new release.  After updating, run `verify_registry()` to catch any collisions before releasing.

---

## License

MIT — see [LICENSE](LICENSE).
