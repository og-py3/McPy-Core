# McPy-Core

**Professional async-first Minecraft Java Edition protocol library.**

**By Haripriyan**
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Protocol](https://img.shields.io/badge/MC%20protocol-764–775-green.svg)](https://wiki.vg/Protocol)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

McPy-Core is a clean, scalable, production-quality Minecraft protocol framework for Python 3.12+. Build bots, automation tools, custom clients, protocol research tools, and servers with a modern async API.

```python
import asyncio
from mcpycore import MinecraftClient

async def main():
    client = MinecraftClient("play.example.com", username="BotName")

    @client.event
    async def on_chat(message, sender):
        print(f"[{sender}] {message}")
        if message == "ping":
            await client.send_chat("pong!")

    await client.start()

asyncio.run(main())
```

---

## Features

| Feature | Details |
|---|---|
| **Async-first** | Built on `asyncio` — no threads, no blocking calls |
| **Event-driven API** | `@client.event` decorators or `client.on(event, handler)` |
| **Multi-version** | Minecraft 1.20.2 → 1.21.11 (protocols 764–775 + snapshots) |
| **Packet system** | Typed packets with `@packet` decorator + auto-registration |
| **Encryption** | AES-128-CFB8 (online & offline mode) |
| **Compression** | zlib with configurable threshold |
| **Reconnect policies** | Fixed delay, exponential back-off, infinite retry |
| **Extension system** | Plugin modules with `setup()` / `teardown()` |
| **Packet inspector** | Real-time `[RECV]`/`[SEND]` logging + hex dump |
| **Metrics** | Latency tracking, packet counters, uptime |
| **NBT parser** | All 13 tag types, nested compounds, `nbt_to_dict()` |
| **Strong typing** | Full type hints throughout |
| **Test suite** | 200+ tests with zero external dependencies |

---

## Installation

```bash
pip install mcpy-core
```

Or from source:

```bash
git clone https://github.com/your-org/mcpy-core.git
cd mcpy-core
pip install -e ".[dev]"
```

**Requirements:** Python 3.12+, `cryptography`

---

## Quick Examples

### Server status ping (no login required)

```python
from examples.server_status import ping
import asyncio

data = asyncio.run(ping("play.hypixel.net"))
print(data["version"]["name"])        # "Paper 1.21.1"
print(data["players"]["online"])      # 45000
print(f"{data['latency_ms']}ms")
```

### Position + movement

```python
@client.event
async def on_spawn(x, y, z):
    print(f"Spawned at ({x:.1f}, {y:.1f}, {z:.1f})")
    await client.move(x + 5, y, z)
    await client.look(yaw=90.0, pitch=-20.0)
```

### Auto-reconnect

```python
from mcpycore.client.reconnect import ExponentialBackoff

client = MinecraftClient(
    "play.example.com",
    reconnect_policy=ExponentialBackoff(base_delay=1.0, max_delay=60.0),
)
```

### Custom packets

```python
from mcpycore import Packet, packet, PacketBuffer, State
from mcpycore.protocol.registry.registry import Direction

@packet(packet_id=0x05, state=State.PLAY, direction=Direction.SERVERBOUND)
class ChatMessage(Packet):
    message: str = ""

    def encode(self) -> bytes:
        buf = PacketBuffer()
        buf.write_string(self.message)
        return buf.flush()
```

### Extensions / plugins

```python
# greet_extension.py
async def setup(client):
    @client.on("spawn")
    async def on_spawn(x, y, z):
        await client.send_chat("Hello from my extension!")

async def teardown(client):
    print("Extension unloaded")
```

```python
client.load_extension("greet_extension")
client.unload_extension("greet_extension")
```

---

## Project Structure

```
mcpycore/
├── client/
│   ├── client.py       ← MinecraftClient — high-level async API
│   ├── connection.py   ← TCP handshake → login → play lifecycle
│   └── reconnect.py    ← Reconnect policy hierarchy
├── protocol/
│   ├── packets/
│   │   └── base.py     ← Packet base + @packet decorator
│   ├── serializers/
│   │   ├── buffer.py   ← PacketBuffer (all primitives)
│   │   └── nbt.py      ← NBT parser
│   ├── registry/
│   │   └── registry.py ← PacketRegistry (version-aware)
│   ├── states/
│   │   └── machine.py  ← Protocol state machine
│   ├── handlers/
│   │   └── dispatcher.py ← PacketDispatcher + middleware
│   └── versions/
│       ├── base.py     ← VersionAdapter + version constants
│       ├── v1_20/      ← ID tables for protocols 764–766
│       └── v1_21/      ← ID tables for protocols 767–775
├── network/
│   └── stream.py       ← AsyncStream (framing/crypto/compression)
├── events/
│   └── emitter.py      ← AsyncEventEmitter + Events constants
├── crypto/
│   └── encryption.py   ← EncryptionManager (AES-128-CFB8)
├── compression/
│   └── compression.py  ← CompressionManager (zlib)
├── debug/
│   └── inspector.py    ← PacketInspector (debug logging)
├── extensions/
│   └── loader.py       ← ExtensionLoader (plugin system)
└── utils/
    ├── logging.py      ← Structured colour logging
    └── metrics.py      ← MetricsCollector
tests/                  ← pytest suite (200+ tests)
examples/               ← Runnable example scripts
docs/                   ← quickstart.md, architecture.md
```

---

## Supported Versions

| Minecraft Version | Protocol |
|---|---|
| 1.20.2 | 764 |
| 1.20.4 | 765 |
| 1.20.6 | 766 |
| 1.21 / 1.21.1 | 767 |
| 1.21.2 / 1.21.3 | 768 |
| 1.21.4 | 769 |
| 1.21.5–1.21.11 | 770–775 |
| Snapshots | Auto-fallback to nearest stable |

---

## Testing

```bash
pytest tests/ -v
```

The suite covers: `PacketBuffer`, NBT, events, compression, encryption, state machine, registry, dispatcher, client, and metrics.

---

## Documentation

- [`docs/quickstart.md`](docs/quickstart.md) — getting started guide
- [`docs/architecture.md`](docs/architecture.md) — design overview and layer diagram

---

## License

MIT
