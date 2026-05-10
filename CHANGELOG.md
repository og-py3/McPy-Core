# Changelog

All notable changes to Mcpycore are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.4.0] — 2026-05-10

### Fixed — Bugs

- **Dead code removed in `OfflineAuth.get_profile()`** — A discarded `uuid.uuid3()`
  call was computed before the correct MD5-based offline UUID, consuming CPU and
  misleading readers into thinking `uuid3()` was part of the algorithm.  Removed.

- **`ConnectionError` no longer shadows the Python built-in** — The exception class
  is now named `McpycoreConnectionError`.  A `ConnectionError` alias is kept for
  backward compatibility, but importing it will still shadow the built-in at the
  call site — prefer `McpycoreConnectionError` in new code.

- **`_send_sb` now sets the packet ID on the instance, not the class** — Previously
  `pkt.__class__.packet_id = pid` mutated the class-level attribute, meaning all
  future instances of that packet type would inherit the patched ID and concurrent
  sends could interfere.  Changed to `pkt.packet_id = pid` (instance attribute
  shadows the class attribute safely).

- **`_configuration_state` no longer uses hardcoded packet IDs** — The configuration
  state handler now resolves all packet IDs through the same version registry used
  by the play state, via the new `get_config_clientbound_id()` /
  `get_config_serverbound_id()` functions.  The previous hardcoded values
  (0x03 for FinishConfiguration, 0x0D/0x0E for SelectKnownPacks) were correct for
  some versions but silently wrong for others.

- **Packet ID collision in play registry corrected** — `entity_position`,
  `entity_position_and_rotation`, and `entity_rotation` each shared an ID with
  `merchant_offers` at every supported protocol version, causing the merchant
  offers events to be silently dropped from the dispatch table.  The entity
  movement packet IDs have been corrected (each shifted up by one slot to match
  the actual Minecraft protocol — e.g., `entity_position` moves from 0x2C → 0x2D
  at protocol 764).  All downstream IDs (player_abilities, player_chat_message,
  combat_death, player_info_update, player_position_and_look, etc.) have been
  updated accordingly.

- **Handler exceptions now use `logging.exception()` instead of `print()`** — Library
  code must not write to stdout.  All `print(f"[Mcpycore] Handler error …")` calls
  replaced with `logger.exception(…)`, which captures the full traceback and
  routes through the caller's logging configuration.

- **`auth` parameter now has an explicit type annotation** — Previously typed as
  implicit `Any`; now `Union[OfflineAuth, MicrosoftAuth, None]`.

### Added

- **`get_config_clientbound_id()` / `get_config_serverbound_id()`** in `versions.py` —
  Version-aware lookup functions for configuration-state packet IDs, backed by
  a new `_CONFIG_CB` / `_CONFIG_SB` registry covering all supported versions.

- **`verify_registry(protocol=None)`** in `versions.py` — Scans the clientbound play
  registry for packet ID collisions at one or all stable protocol versions and
  returns a structured report.  Useful for catching future regressions when adding
  new protocol versions.

- **Collision warning in `build_id_to_name()`** — If two packet names resolve to the
  same ID, a `logging.warning()` is emitted rather than silently overwriting.

- **Collision warning in `_build_play_dispatch()`** — Same guard applied when
  building the client's live dispatch table at startup.

- **`McpycoreConnectionError`** as the canonical exception name (with
  `ConnectionError` alias for backward compatibility).

- **`_send_cfg_sb()` helper on `MinecraftClient`** — Sends a configuration-state
  serverbound packet with the version-correct ID, mirroring `_send_sb()` for the
  play state.

- **Configuration-state keep-alive handling** — The client now responds to
  `config_keep_alive` pings during the configuration phase, preventing server
  timeouts on servers that send them.

- **`events` module explicitly listed in `__all__`** (it was imported but omitted).

- **`McpycoreConnectionError` exported from the top-level package** in `__all__`.

- **Python 3.13 classifier** added to `pyproject.toml`.

### Changed

- `__version__` bumped to `0.4.0`.
- README version table updated: `PROTOCOL_LATEST` now correctly shows 775 / 1.21.11
  (was incorrectly showing 767 / 1.21.1 in v0.3.0).
- README expanded with full version compatibility table, snapshot support docs,
  feature-availability matrix, and logging section.

---

## [0.3.0] — 2026-05-10

### Added
- **Full version coverage**: protocols 764 → 775 (Minecraft 1.20.2 → 1.21.11)
- **Snapshot support**: any protocol ≥ `0x40000000` is detected and warned about;
  packet dispatch falls back to the nearest stable version automatically
- **New packet modules**:
  - `packets/play/inventory.py` — SetContainerContent, SetContainerSlot, OpenScreen,
    CloseContainer, ClickContainer, SetHeldItem, SetHeldItemSB
  - `packets/play/boss_bar.py` — BossBar (add, remove, health, title, style, flags)
  - `packets/play/title.py` — SetTitleText, SetSubtitleText, SetActionBarText,
    SetTitleAnimationTimes, ClearTitles
  - `packets/play/sound.py` — SoundEffect, EntitySoundEffect, StopSound
  - `packets/play/player_list.py` — PlayerInfoUpdate, PlayerInfoRemove,
    SetTabListHeaderAndFooter
  - `packets/play/scoreboard.py` — UpdateObjectives, DisplayObjective, UpdateScore,
    ResetScore, UpdateTeams
- **NBT parser** (`utils/nbt.py`) — reads all 13 tag types including nested compounds
  and lists; `parse_nbt()` / `nbt_to_dict()` helpers
- **Chunk section parser** (`world/chunk_parser.py`) — decodes raw chunk payloads into
  16×16×16 `ChunkSection` objects using Minecraft's palette-container format (1.18+)
- **Player inventory tracking** (`player/inventory.py`) — 46-slot inventory,
  hotbar/armour/offhand views, item search and counting
- **Tab-list tracking** (`player/player_list.py`) — `TabList` / `TabListEntry`
  with ping categorisation and sorted player list
- **Events module** (`events.py`) — typed string constants for every event name
- **`versions.py`** additions:
  - `PROTOCOL_1_21_5` through `PROTOCOL_1_21_11` constants
  - `build_id_to_name()`, `ALL_STABLE_PROTOCOLS`, `is_snapshot()`,
    `nearest_stable()`, `snapshot_stable_fallback()`
- **New examples**: `chat_logger.py`, `inventory_viewer.py`
- **New client methods**: `look_at()`, `use_item_on_block()`, `dig_block()`,
  `drop_item()`, `set_held_slot()`, `close_container()`, `set_creative_slot()`,
  `respawn()`

### Changed
- `MinecraftClient` constructor now issues a `UserWarning` for snapshot protocols
- `pyproject.toml` bumped to `0.3.0`

---

## [0.2.0] — 2026-05-09

### Added
- Multi-version support: protocols 764–767 (1.20.2 → 1.21.1)
- `versions.py` packet ID registry with `get_clientbound_id()` / `get_serverbound_id()`
- 1.21+ packets: Transfer, CookieRequest, StoreCookie, DebugSample
- Configuration-state handling (SelectKnownPacks for 1.21+)
- GitHub-ready files: LICENSE (MIT), .gitignore, CONTRIBUTING.md

---

## [0.1.0] — 2026-05-08

### Added
- Initial release
- Full 1.20.4 protocol: VarInt framing, zlib compression, AES-128/CFB8 encryption
- `OfflineAuth` and `MicrosoftAuth` (Device Code flow)
- Event-driven API: `@client.on("event")`
- World tracking (chunks, block-state lookup)
- Entity tracking (spawn, move, nearby)
- Player actions: chat, move, attack, interact, sneak, sprint, use item
- Server status ping
- 76 tests
