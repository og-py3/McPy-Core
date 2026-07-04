# Changelog

All notable changes to McPy-Core are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [Semantic Versioning](https://semver.org/).

---

## [2.0.0] — 2026-07-04

### Breaking Changes
- `_cb()` / `_sb()` in `MinecraftClient` now use the full adapter table
  (`protocol.versions.adapters`) instead of only the v1_21 packet tables.
  This is transparent unless you subclassed and called the private helpers.
- `_on_keep_alive()` now uses version-aware wire types (INT / VarInt / Long).
  Bots connecting to 1.7–1.8 servers will no longer send the wrong type.
- `LoginError` and `ConnectionError` have been moved to
  `mcpycore.client.connection` (still re-exported from `mcpycore`).

### Added
- **Full protocol coverage** — every Java Edition protocol from 1.7.2
  (protocol 4) through 1.21.11 (protocol 775):
  - `mcpycore/protocol/versions/v1_8/packets.py`   — protocols 4, 5, 47
  - `mcpycore/protocol/versions/v1_12/packets.py`  — protocols 107–340
  - `mcpycore/protocol/versions/v1_16/packets.py`  — protocols 393–754
  - `mcpycore/protocol/versions/v1_17/packets.py`  — protocols 755–763
- **Feature-flag helpers** in `base.py`:
  - `has_configuration_state(protocol)` — True for 764+
  - `has_long_keepalive(protocol)` — True for 335+ (1.12+)
  - `has_varint_keepalive(protocol)` — True for 107–316 (1.9–1.11)
  - `has_uuid_in_login_start(protocol)` — True for 762+
  - `has_optional_uuid_in_login_start(protocol)` — True for 761
  - `uses_legacy_login_success_string_uuid(protocol)` — True for 4–47
  - `version_name(protocol)` — human-readable string for every known protocol
  - `is_snapshot(protocol)` — True for protocols ≥ SNAPSHOT_BASE
  - `nearest_stable(protocol)` — closest stable protocol
  - `ALL_STABLE_PROTOCOLS` — sorted tuple of all stable protocol ints
- **Humanized anti-bot joining** (`mcpycore.humanize`):
  - `HumanizeConfig` dataclass — configurable per-step delay ranges, look-angle
    spread, settle-on-spawn, AuthMe/auto-login, generic regex chat triggers.
  - `Humanizer` class — injected into `Connection` and `MinecraftClient`;
    adds asyncio.sleep jitter at every protocol phase (pre-handshake,
    pre-login, post-login, configuration settle, keep-alive ACK, teleport
    confirm, post-spawn micro-rotation).
  - `Humanizer.build_chat_handlers()` — returns async callables wired into
    the client's chat events for AuthMe and custom plugin bypass.
  - Supported anti-bot plugins: AuthMe, xAuth, LoginSecurity, EasyAntiBot,
    NuVotifier digit CAPTCHAs, custom regex triggers.
- **Multi-language bridge** (`mcpycore.bridge`):
  - `BridgeServer` — WebSocket server (JSON protocol) that wraps a full
    `MinecraftClient` per connection so bots can be driven from any language.
  - CLI: `python -m mcpycore.bridge --port 25580` or `mcpycore-bridge`.
- **Language SDKs** (`sdks/`):
  - JavaScript / TypeScript — npm package `mcpy-core-js`
  - Java — Maven artifact `io.mcpycore:mcpy-core-java`
  - Go — module `github.com/og-py3/McPy-Core/sdks/go`
  - Rust — crate `mcpy-core`
  - C# / .NET — NuGet package `McPyCore`
- **Updated adapters** — `protocol.versions.adapters.get_cb_ids` /
  `get_sb_ids` now cover all four new era modules with nearest-lower fallback
  for patch versions not explicitly listed.
- **`OfflineProfile`** — helper that derives the correct offline-mode UUID
  using the same algorithm as the Minecraft server.
- `__version__` bumped to `2.0.0`.

### Fixed
- `_connect_once()` now passes `humanizer` to `Connection`.
- `_on_position()` skips `confirm_teleportation` for protocols < 107
  (1.7/1.8 have no teleport confirmation packet).
- `_on_chat()` handles all per-era message formats (1.7–1.20+).
- `send_chat()` omits timestamp/salt/signature fields for protocols < 759.
- Configuration state `FinishConfiguration` / `SelectKnownPacks` IDs
  are now selected per protocol range (764–765 vs 766+).
- Broken GitHub URL in `pyproject.toml` (`your-org/mcpy-core` →
  `og-py3/McPy-Core`).
- `classifiers` updated: Python 3.11 added, status bumped to Production/Stable.
- `_build_handlers()` deduplicates packet IDs so aliased event names
  (e.g. `set_health` / `update_health`) don't overwrite each other.

### Dependencies
- `websockets>=11.0` added (required for the bridge; optional for pure
  protocol usage).

---

## [1.0.0] — 2025-01-01

### Added
- Initial release.
- Async Minecraft Java Edition protocol client for 1.20.2–1.21.11.
- Online-mode (Microsoft auth) and offline-mode support.
- Event-driven API with `AsyncEventEmitter`.
- Packet compression (zlib) and encryption (AES-128-CFB8).
- ReconnectPolicy with ExponentialBackoff.
- Extension / plugin loader.
- Packet inspector and metrics collector.
