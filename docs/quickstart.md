# McPy-Core Quick Start

## Installation

```bash
pip install mcpy-core
# or from source:
pip install -e .
```

**Requirements:** Python 3.12+, `cryptography`

---

## Your first bot

```python
import asyncio
from mcpycore import MinecraftClient

async def main():
    client = MinecraftClient(
        host="play.example.com",
        port=25565,
        username="MyBot",
    )

    @client.event
    async def on_connect(c):
        print(f"Connected! Position: {c.position}")

    @client.event
    async def on_chat(message, sender):
        print(f"[{sender}] {message}")
        if message.startswith("!echo "):
            await client.send_chat(message[6:])

    await client.start()

asyncio.run(main())
```

---

## Events

Register handlers with the `@client.event` decorator — name your function `on_<event>`:

```python
@client.event
async def on_connect(client):   ...

@client.event
async def on_spawn(x, y, z):   ...

@client.event
async def on_chat(message, sender_uuid):   ...

@client.event
async def on_health(health, food, saturation):   ...

@client.event
async def on_position(x, y, z, yaw, pitch):   ...

@client.event
async def on_disconnect(reason):   ...

@client.event
async def on_error(exc):   ...
```

Or register dynamically:

```python
from mcpycore.events.emitter import Events

client.on(Events.CHAT, my_handler)
client.once(Events.SPAWN, one_time_handler)
client.off(Events.CHAT, my_handler)
```

---

## Player actions

```python
# Chat
await client.send_chat("Hello, world!")
await client.send_chat("/gamemode creative")   # slash commands too

# Movement
await client.move(x=100.0, y=64.0, z=200.0, yaw=0.0, pitch=0.0)
await client.look(yaw=90.0, pitch=-30.0)

# Combat
await client.attack(entity_id=42)
await client.swing_arm()

# Items
await client.use_item(hand=0)          # 0=main, 1=off
await client.set_held_slot(3)          # hotbar slot 0-8

# Sneaking / sprinting
await client.sneak(True)
await asyncio.sleep(2)
await client.sneak(False)

await client.sprint(True)

# Respawn after death
await client.respawn()
```

---

## Reconnect policies

```python
from mcpycore.client.reconnect import (
    NoReconnect,          # never reconnect (default)
    FixedDelay,           # fixed pause between attempts
    ExponentialBackoff,   # exponential back-off + jitter
    InfiniteRetry,        # retry forever
)

client = MinecraftClient(
    host="play.example.com",
    reconnect_policy=ExponentialBackoff(
        base_delay=1.0,
        max_delay=60.0,
        max_attempts=10,
    ),
)
```

---

## Multi-version support

```python
from mcpycore import PROTOCOL_1_20_4, PROTOCOL_1_21_1, PROTOCOL_LATEST

client = MinecraftClient(
    host="old.server.com",
    protocol_version=PROTOCOL_1_20_4,  # 765
)
```

All packet IDs for 1.20.2–1.21.11 are built-in. For snapshots, the nearest stable ID table is used automatically.

---

## Debug mode

```python
client = MinecraftClient(host="...", debug=True)
```

This enables:
- Per-packet `[RECV]` / `[SEND]` log lines
- Optional hex dump: `client.inspector.hex_dump = True`

---

## Extensions / plugins

```python
# my_logger.py
async def setup(client):
    @client.on("chat")
    async def on_chat(msg, sender):
        with open("chat.log", "a") as f:
            f.write(f"{sender}: {msg}\n")

async def teardown(client):
    print("Logger unloaded")
```

```python
client.load_extension("my_logger")
client.unload_extension("my_logger")
client.reload_extension("my_logger")
```

---

## Custom packets

```python
from mcpycore import Packet, packet, PacketBuffer, State
from mcpycore.protocol.registry.registry import Direction

@packet(packet_id=0x00, state=State.LOGIN, direction=Direction.SERVERBOUND)
class LoginStart(Packet):
    username: str = ""

    def encode(self) -> bytes:
        buf = PacketBuffer()
        buf.write_string(self.username)
        return buf.flush()

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "LoginStart":
        pkt = cls()
        pkt.username = buf.read_string()
        return pkt
```

---

## Metrics

```python
report = client.metrics.report()
print(f"Packets in:  {report['packets_in']}")
print(f"Packets out: {report['packets_out']}")
print(f"Avg latency: {report['latency_avg_ms']}ms")
print(f"Uptime:      {report['uptime_s']}s")
```

---

## Running tests

```bash
cd mcpycore
pip install -e ".[dev]"
pytest tests/ -v
```
