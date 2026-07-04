"""
Packet ID tables for Minecraft 1.13.x – 1.16.x.

Sources:
  https://wiki.vg/index.php?title=Protocol&oldid=14204  (1.13  / protocol 393)
  https://wiki.vg/index.php?title=Protocol&oldid=15023  (1.14  / protocol 477)
  https://wiki.vg/index.php?title=Protocol&oldid=16681  (1.15  / protocol 573)
  https://wiki.vg/index.php?title=Protocol&oldid=16067  (1.16  / protocol 735)
  https://wiki.vg/index.php?title=Protocol&oldid=16918  (1.16.5 / protocol 754)

Keep-alive ID type: Long (8 bytes) for all versions in this file.
"""
from __future__ import annotations

# ── 1.13 clientbound (393) ────────────────────────────────────────────────────
_CB_393: dict[str, int] = {
    "spawn_entity":              0x00,
    "spawn_experience_orb":      0x01,
    "animation":                 0x06,
    "block_update":              0x0B,
    "boss_bar":                  0x0C,
    "chat_message":              0x0E,
    "chunk_data":                0x22,
    "disconnect":                0x1A,
    "entity_position":           0x28,
    "entity_position_and_rotation": 0x29,
    "entity_rotation":           0x2A,
    "explosion":                 0x1E,
    "game_event":                0x20,
    "keep_alive":                0x21,
    "login":                     0x25,
    "player_abilities":          0x2E,
    "player_position_and_look":  0x32,
    "player_list_item":          0x30,
    "remove_entities":           0x35,
    "respawn":                   0x38,
    "set_health":                0x44,
    "update_health":             0x44,
    "sound_effect":              0x4D,
    "time_update":               0x4A,
    "unload_chunk":              0x1F,
    "update_objectives":         0x45,
    "update_score":              0x48,
    "update_teams":              0x47,
    "title":                     0x4B,
    "world_border":              0x38,
    "chunk_batch_finished":      0x21,   # alias
    "system_chat_message":       0x0E,   # alias
    "block_changed_ack":         0x0B,   # alias
}

_CB_401 = dict(_CB_393)
_CB_404 = dict(_CB_393)

# ── 1.14 clientbound (477) ────────────────────────────────────────────────────
_CB_477: dict[str, int] = {
    **_CB_393,
    "login":                     0x26,
    "player_position_and_look":  0x35,
    "chunk_data":                0x22,
    "keep_alive":                0x21,
    "set_health":                0x49,
    "update_health":             0x49,
    "respawn":                   0x3A,
    "remove_entities":           0x37,
    "sound_effect":              0x4D,
    "time_update":               0x4E,
    "update_objectives":         0x49,
    "update_score":              0x4C,
    "unload_chunk":              0x1F,
    "disconnect":                0x1A,
    "chat_message":              0x0E,
}

_CB_480 = dict(_CB_477)
_CB_485 = dict(_CB_477)
_CB_490 = dict(_CB_477)
_CB_498 = dict(_CB_477)

# ── 1.15 clientbound (573) ────────────────────────────────────────────────────
_CB_573: dict[str, int] = {
    **_CB_477,
    "disconnect":                0x1B,
    "keep_alive":                0x21,
    "login":                     0x26,
    "player_position_and_look":  0x35,
    "set_health":                0x49,
    "update_health":             0x49,
}

_CB_575 = dict(_CB_573)
_CB_578 = dict(_CB_573)

# ── 1.16 clientbound (735 / 736) ─────────────────────────────────────────────
_CB_735: dict[str, int] = {
    **_CB_573,
    "disconnect":                0x1A,
    "keep_alive":                0x21,
    "login":                     0x26,
    "player_position_and_look":  0x36,
    "respawn":                   0x3B,
    "set_health":                0x4E,
    "update_health":             0x4E,
    "chat_message":              0x0E,
    "remove_entities":           0x38,
    "unload_chunk":              0x1C,
    "chunk_data":                0x22,
    "time_update":               0x4E,
    "update_objectives":         0x4E,
    "update_score":              0x4D,
    "sound_effect":              0x50,
    "title":                     0x4F,
    "world_border":              0x3E,
}

_CB_736 = dict(_CB_735)

# ── 1.16.2 clientbound (751) ─────────────────────────────────────────────────
_CB_751: dict[str, int] = {
    **_CB_735,
    "disconnect":                0x1A,
    "keep_alive":                0x21,
    "login":                     0x26,
    "player_position_and_look":  0x36,
    "set_health":                0x4E,
    "update_health":             0x4E,
}

_CB_753 = dict(_CB_751)
_CB_754: dict[str, int] = dict(_CB_751)

# ── Serverbound Play IDs ──────────────────────────────────────────────────────

_SB_393: dict[str, int] = {
    "confirm_teleportation":     0x00,
    "chat_message":              0x02,
    "client_information":        0x04,
    "client_settings":           0x04,
    "keep_alive":                0x0E,
    "move_player_pos":           0x10,
    "move_player_pos_rot":       0x11,
    "move_player_rot":           0x12,
    "player_action":             0x18,
    "player_position_and_look":  0x11,
    "swing_arm":                 0x2A,
    "use_item":                  0x2C,
    "use_item_on":               0x2C,
    "close_window":              0x09,
    "click_window":              0x08,
    "held_item_change":          0x21,
    "set_held_item":             0x21,
    "entity_action":             0x19,
    "tab_complete":              0x05,
}

_SB_401 = dict(_SB_393)
_SB_404 = dict(_SB_393)

_SB_477: dict[str, int] = {
    **_SB_393,
    "keep_alive":                0x0F,
    "chat_message":              0x03,
    "move_player_pos":           0x11,
    "move_player_pos_rot":       0x12,
    "move_player_rot":           0x13,
    "player_position_and_look":  0x12,
    "swing_arm":                 0x2B,
}

_SB_480 = dict(_SB_477)
_SB_485 = dict(_SB_477)
_SB_490 = dict(_SB_477)
_SB_498 = dict(_SB_477)

_SB_573: dict[str, int] = {
    **_SB_477,
    "keep_alive":                0x0F,
    "chat_message":              0x03,
    "move_player_pos":           0x11,
    "move_player_pos_rot":       0x12,
    "move_player_rot":           0x13,
    "player_position_and_look":  0x12,
}

_SB_575 = dict(_SB_573)
_SB_578 = dict(_SB_573)

_SB_735: dict[str, int] = {
    **_SB_573,
    "keep_alive":                0x10,
    "chat_message":              0x03,
    "move_player_pos":           0x12,
    "move_player_pos_rot":       0x13,
    "move_player_rot":           0x14,
    "player_position_and_look":  0x13,
    "swing_arm":                 0x2C,
}

_SB_736 = dict(_SB_735)
_SB_751 = dict(_SB_735)
_SB_753 = dict(_SB_735)
_SB_754 = dict(_SB_735)

# ── Public tables ─────────────────────────────────────────────────────────────

CB_IDS: dict[int, dict[str, int]] = {
    393: _CB_393,
    401: _CB_401,
    404: _CB_404,
    477: _CB_477,
    480: _CB_480,
    485: _CB_485,
    490: _CB_490,
    498: _CB_498,
    573: _CB_573,
    575: _CB_575,
    578: _CB_578,
    735: _CB_735,
    736: _CB_736,
    751: _CB_751,
    753: _CB_753,
    754: _CB_754,
}

SB_IDS: dict[int, dict[str, int]] = {
    393: _SB_393,
    401: _SB_401,
    404: _SB_404,
    477: _SB_477,
    480: _SB_480,
    485: _SB_485,
    490: _SB_490,
    498: _SB_498,
    573: _SB_573,
    575: _SB_575,
    578: _SB_578,
    735: _SB_735,
    736: _SB_736,
    751: _SB_751,
    753: _SB_753,
    754: _SB_754,
}
