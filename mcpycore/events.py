"""
Event name constants for use with ``@client.on(event)`` decorators.

Using these constants instead of raw strings prevents typos and enables
IDE auto-completion.

Example::

    from mcpycore.events import EVT_CHAT, EVT_HEALTH

    @client.on(EVT_CHAT)
    def on_chat(pkt): ...

    @client.on(EVT_HEALTH)
    def on_health(pkt): ...
"""

# ── Session ───────────────────────────────────────────────────────────────────
EVT_CONNECTED   = "connected"
"""Fired after login and configuration completes. Arg: ``client``."""

EVT_DISCONNECT  = "disconnect"
"""Fired when kicked or connection drops. Arg: ``reason: str``."""

EVT_RESPAWN     = "respawn"
"""Fired when the player respawns (dies or changes dimension). Arg: packet."""

EVT_TRANSFER    = "transfer"
"""Fired on 1.21+ Transfer packet. Args: ``host: str, port: int``."""

# ── Player state ──────────────────────────────────────────────────────────────
EVT_POSITION    = "position"
"""Server-synced position. Args: ``x, y, z, yaw, pitch``."""

EVT_HEALTH      = "set_health"
"""Health/food/saturation update. Arg: ``SetHealth`` packet."""

EVT_ABILITIES   = "player_abilities"
"""Flying/ability flags changed. Arg: packet."""

EVT_GAME_EVENT  = "game_event"
"""Game mode change, rain start/stop, etc. Arg: packet."""

# ── Chat & messages ───────────────────────────────────────────────────────────
EVT_CHAT        = "chat_message"
"""Player chat message. Arg: ``ChatMessage`` packet."""

EVT_SYSTEM      = "system_message"
"""System / server broadcast. Arg: ``SystemChatMessage`` packet."""

EVT_ACTION_BAR  = "action_bar"
"""Action bar text update. Arg: ``SetActionBarText`` packet."""

# ── Title ─────────────────────────────────────────────────────────────────────
EVT_TITLE       = "title"
"""Title text set. Arg: ``SetTitleText`` packet."""

EVT_SUBTITLE    = "subtitle"
"""Subtitle text set. Arg: ``SetSubtitleText`` packet."""

EVT_CLEAR_TITLE = "clear_titles"
"""Titles cleared. Arg: ``ClearTitles`` packet."""

# ── World ─────────────────────────────────────────────────────────────────────
EVT_BLOCK_UPDATE   = "block_update"
"""Single block changed. Arg: ``BlockUpdate`` packet."""

EVT_MULTI_BLOCK    = "multi_block_change"
"""Multiple blocks changed at once. Arg: packet."""

EVT_CHUNK_LOAD     = "chunk_load"
"""Chunk fully loaded. Arg: ``Chunk`` object."""

EVT_CHUNK_UNLOAD   = "chunk_unload"
"""Chunk unloaded. Args: ``chunk_x: int, chunk_z: int``."""

EVT_TIME_UPDATE    = "time_update"
"""World time tick. Arg: packet."""

EVT_EXPLOSION      = "explosion"
"""Explosion occurred. Arg: packet."""

EVT_WORLD_EVENT    = "world_event"
"""Block/world sound/particle event. Arg: packet."""

# ── Entities ──────────────────────────────────────────────────────────────────
EVT_SPAWN_ENTITY   = "spawn_entity"
"""Entity spawned. Arg: ``Entity`` object."""

EVT_ENTITY_MOVE    = "entity_move"
"""Entity position/rotation updated. Arg: ``Entity`` object."""

EVT_REMOVE_ENTITY  = "remove_entities"
"""Entities removed. Arg: list of entity IDs."""

EVT_ENTITY_EFFECT  = "entity_effect"
"""Potion effect applied to entity. Arg: packet."""

# ── Inventory ─────────────────────────────────────────────────────────────────
EVT_INVENTORY_OPEN   = "open_screen"
"""Container opened. Arg: ``OpenScreen`` packet."""

EVT_INVENTORY_UPDATE = "set_container_content"
"""Full inventory state received. Arg: ``SetContainerContent`` packet."""

EVT_SLOT_UPDATE      = "set_container_slot"
"""Single slot updated. Arg: ``SetContainerSlot`` packet."""

EVT_HELD_ITEM_CHANGE = "set_held_item"
"""Server changed held item. Arg: ``SetHeldItem`` packet."""

# ── Tab list ──────────────────────────────────────────────────────────────────
EVT_PLAYER_LIST_UPDATE = "player_info_update"
"""Tab-list entries updated. Arg: ``PlayerInfoUpdate`` packet."""

EVT_PLAYER_LIST_REMOVE = "player_info_remove"
"""Players removed from tab list. Arg: ``PlayerInfoRemove`` packet."""

EVT_TAB_HEADER_FOOTER  = "tab_header_footer"
"""Tab list header/footer updated. Arg: ``SetTabListHeaderAndFooter`` packet."""

# ── Boss bar ──────────────────────────────────────────────────────────────────
EVT_BOSS_BAR = "boss_bar"
"""Boss bar add/update/remove. Arg: ``BossBar`` packet."""

# ── Scoreboard ────────────────────────────────────────────────────────────────
EVT_SCOREBOARD_OBJECTIVE = "update_objectives"
"""Scoreboard objective created/updated/removed. Arg: packet."""

EVT_SCOREBOARD_SCORE     = "update_score"
"""Score updated. Arg: packet."""

EVT_SCOREBOARD_DISPLAY   = "display_objective"
"""Display slot changed. Arg: packet."""

EVT_SCOREBOARD_TEAM      = "update_teams"
"""Team created/updated/removed. Arg: packet."""

# ── Sound ─────────────────────────────────────────────────────────────────────
EVT_SOUND        = "sound_effect"
"""Sound played at position. Arg: ``SoundEffect`` packet."""

EVT_ENTITY_SOUND = "entity_sound_effect"
"""Sound played on entity. Arg: ``EntitySoundEffect`` packet."""

EVT_STOP_SOUND   = "stop_sound"
"""Sound stopped. Arg: ``StopSound`` packet."""

# ── Combat ────────────────────────────────────────────────────────────────────
EVT_DEATH       = "combat_death"
"""Player death. Arg: packet."""

EVT_HURT        = "hurt_animation"
"""Player hurt animation. Arg: packet."""

EVT_DAMAGE      = "damage_event"
"""Damage event on entity. Arg: packet."""

ALL_EVENTS = [v for k, v in globals().items() if k.startswith("EVT_")]
