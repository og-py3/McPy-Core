# Contributing to Mcpycore

Thank you for your interest in contributing!

## Getting Started

```bash
git clone https://github.com/youruser/mcpycore
cd mcpycore
pip install -e ".[dev]"
```

## Running Tests

```bash
python -m pytest tests/ -v
```

All 76+ tests must pass before submitting a pull request.

## Adding Packet Support

1. Create the packet class in `mcpycore/packets/play/clientbound.py` or `serverbound.py`
2. Add the packet ID to `mcpycore/versions.py` for each affected version
3. Register the handler in `MinecraftClient._register_play_handlers()`
4. Add a decode test in `tests/test_packets.py`

## Packet ID Registry

When Minecraft updates change packet IDs, update `mcpycore/versions.py`:

```python
_CLIENTBOUND_REGISTRY: dict[str, dict[int, int]] = {
    "keep_alive": {764: 0x24, 765: 0x24, 767: 0x26, 769: 0x26},
    #             ^^^^ add new protocol version and its packet ID here
}
```

## Protocol Reference

- [Minecraft Wiki Protocol](https://minecraft.wiki/w/Java_Edition_protocol)
- [wiki.vg (archived)](https://wiki.vg/Protocol)

## Code Style

- Python 3.10+ only — use union types (`X | Y`), `match`, structural pattern matching where helpful
- All packets are typed dataclasses with `encode()` + `decode()` methods
- No magic numbers in packet handlers — use named constants

## Pull Request Checklist

- [ ] Tests pass (`python -m pytest tests/ -v`)
- [ ] New packets have decode tests
- [ ] `versions.py` updated if packet IDs changed
- [ ] README updated if user-facing API changed
