# McPy-Core Architecture

## Overview

McPy-Core is built as a layered stack. Each layer has a single responsibility and communicates only with the layer directly above or below it.

```
┌────────────────────────────────────────────────────────┐
│                    User Code / Bots                    │
├────────────────────────────────────────────────────────┤
│               MinecraftClient (client/)                │
│  - Event-driven high-level API                         │
│  - Reconnect policy                                    │
│  - Extension loader                                    │
│  - Metrics collector                                   │
├────────────────────────────────────────────────────────┤
│               Connection (client/)                     │
│  - Handshake → Login → Configuration → Play lifecycle  │
│  - Online/offline auth                                 │
├────────────────────────────────────────────────────────┤
│          Protocol Layer (protocol/)                    │
│  ┌────────────┐ ┌───────────────┐ ┌─────────────────┐ │
│  │  Packets   │ │ State Machine │ │ Packet Registry │ │
│  │  (base.py) │ │ (machine.py)  │ │ (registry.py)   │ │
│  └────────────┘ └───────────────┘ └─────────────────┘ │
│  ┌────────────┐ ┌───────────────┐ ┌─────────────────┐ │
│  │Serializers │ │    Versions   │ │   Dispatcher    │ │
│  │ buffer/nbt │ │  v1_20/v1_21  │ │  (handlers/)    │ │
│  └────────────┘ └───────────────┘ └─────────────────┘ │
├────────────────────────────────────────────────────────┤
│            Network Layer (network/)                    │
│  AsyncStream — asyncio framing + crypto + compression  │
├────────────────────────────────────────────────────────┤
│          Support Services                              │
│  ┌──────────────┐ ┌───────────────┐ ┌──────────────┐  │
│  │EncryptionMgr │ │CompressionMgr │ │PacketInspect │  │
│  │ (crypto/)    │ │ (compression/)│ │  (debug/)    │  │
│  └──────────────┘ └───────────────┘ └──────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## PacketBuffer

Central abstraction for all protocol I/O.

- **Write mode** — build outgoing packet payloads
- **Read mode** — parse received packet payloads
- Never reads from a socket directly; that's AsyncStream's job

```python
# Writing
buf = PacketBuffer()
buf.write_varint(42)
buf.write_string("hello")
data = buf.flush()

# Reading
buf = PacketBuffer.from_bytes(data)
n   = buf.read_varint()
s   = buf.read_string()
```

---

## Packet System

Packets are plain Python classes inheriting from `Packet`.

The `@packet` decorator:
1. Sets `_packet_id`, `_state`, `_direction`, `_version_min`, `_version_max` on the class
2. Registers the class in the `PacketRegistry`

```python
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

## Protocol State Machine

Enforces legal state transitions:

```
HANDSHAKING ─→ STATUS
             ─→ LOGIN ─→ CONFIGURATION ─→ PLAY
                       ─→ PLAY (pre-1.20.2)
```

`ProtocolStateMachine.transition(State.PLAY)` raises `InvalidTransition` if the move is not allowed, preventing silent protocol desynchronisation.

---

## AsyncStream

Sits between the socket and the Connection layer.

**Framing** (Minecraft wire format):
```
[Packet Length: VarInt]
[Data Length: VarInt]   ← only when compression enabled; 0 = not compressed
[Data: bytes]           ← optionally zlib compressed
                        ← AES-128-CFB8 encrypted on the wire
```

**APIs:**
- `await stream.read_packet() → (packet_id: int, buf: PacketBuffer)`
- `await stream.write_packet(packet_id: int, payload: bytes)`
- `stream.enable_encryption(shared_secret: bytes)`
- `stream.enable_compression(threshold: int)`

---

## Event System

`AsyncEventEmitter` is a fully async event bus:

- All handlers may be `async def` or plain `def`
- Handlers are invoked in registration order
- Exceptions in handlers are caught and logged (never propagate to the packet loop)
- One-shot handlers via `once()`
- Middleware chain via `use()` — can suppress events by returning `False`
- Wildcard listeners via `on("*", handler)`

---

## Version Adapters

Minecraft changes packet IDs between protocol versions. McPy-Core handles this with two-level lookup tables:

```
CB_IDS[protocol_version]["keep_alive"] → int
SB_IDS[protocol_version]["chat_message"] → int
```

When a protocol is not in the table (e.g. an unknown snapshot), the nearest lower known version is used as a fallback.

Adapters live in:
- `protocol/versions/v1_20/packets.py` — protocols 764, 765, 766
- `protocol/versions/v1_21/packets.py` — protocols 767–775

---

## Encryption (AES-128-CFB8)

Enabled after `EncryptionResponse` is acknowledged:

1. Client generates 16-byte shared secret
2. Client encrypts it with the server's RSA public key → sends in `EncryptionResponse`
3. `stream.enable_encryption(shared_secret)` switches both reader and writer to AES-128-CFB8
4. All subsequent bytes on the wire are symmetrically encrypted

The IV equals the shared secret (Minecraft's design choice).

---

## Compression

Enabled after `SetCompression` packet:

- Packets ≥ threshold bytes → zlib compressed
- Packets < threshold → sent uncompressed with `Data Length = 0`
- `CompressionManager` handles all framing; `AsyncStream` does not need to know the details

---

## Extension System

Extensions are Python modules with a `setup(client)` function:

```
load_extension(name)
  → importlib.import_module(name)
  → module.setup(client)   (awaited if async)

unload_extension(name)
  → module.teardown(client)  (if defined)
  → del sys.modules[name]
```

---

## Design Principles

1. **Contract-first packets** — every packet has `encode()` + `decode()` for symmetry
2. **AsyncStream is protocol-agnostic** — it only frames, encrypts, and compresses; it knows nothing about packet semantics
3. **Event-driven** — the packet loop emits events; business logic lives in handlers, not in the loop
4. **Loose coupling** — layers communicate through well-defined interfaces; no globals except `global_registry`
5. **Explicit over implicit** — IDs, states, and directions are always spelled out; no magic inference
6. **Fail loudly** — `InvalidTransition`, `BufferUnderrun`, `LoginError` are raised immediately rather than silently degrading
