"""
Packet ID tables for Minecraft 1.9.x – 1.12.x.

Sources:
  https://wiki.vg/index.php?title=Protocol&oldid=7617   (1.9  / protocol 107)
  https://wiki.vg/index.php?title=Protocol&oldid=7368   (1.12 / protocol 335)
  https://wiki.vg/index.php?title=Protocol&oldid=7368   (1.12.2 / protocol 340)

Keep-alive ID type:
  1.9 – 1.11 (107–316) : VarInt
  1.12+       (335+)   : Long (8 bytes)
"""
from __future__ import annotations

# ── 1.9 / 1.9.4 clientbound (107–110) ────────────────────────────────────────
_CB_107: dict[str, int] = {
    "spawn_entity":              0x00,
    "spawn_experience_orb":      0x01,
    "animation":                 0x06,
    "block_update":              0x0B,
    "boss_bar":                  0x0C,
    "chat_message":              0x0F,
    "chunk_data":                0x20,
    "disconnect":                0x1A,
    "entity_position":           0x25,
    "entity_position_and_rotation": 0x26,
    "entity_rotation":           0x27,
    "explosion":                 0x1C,
    "game_event":                0x1E,
    "keep_alive":                0x1F,
    "login":                     0x23,
    "player_abilities":          0x2B,
    "player_position_and_look":  0x2E,
    "remove_entities":           0x31,
    "respawn":                   0x33,
    "set_health":                0x44,
    "update_health":             0x44,
    "set_slot":                  0x16,
    "sound_effect":              0x48,
    "time_update":               0x44,
    "title":                     0x45,
    "unload_chunk":              0x1D,
    "update_objectives":         0x3D,
    "update_score":              0x42,
    "update_teams":              0x41,
    "world_border":              0x35,
    "player_list_item":          0x2D,
    "chunk_batch_finished":      0x1F,  # alias
    "system_chat_message":       0x0F,  # alias
}

# 1.9.1–1.9.4 same IDs
_CB_108 = dict(_CB_107)
_CB_109 = dict(_CB_107)
_CB_110 = dict(_CB_107)

# 1.10 (210) — same IDs as 1.9.4
_CB_210 = dict(_CB_107)

# 1.11 (315–316) — same IDs as 1.9/1.10
_CB_315 = dict(_CB_107)
_CB_316 = dict(_CB_107)

# ── 1.12 clientbound (335) ────────────────────────────────────────────────────
_CB_335: dict[str, int] = {
    **_CB_107,
    "player_position_and_look":  0x2F,   # shifted
    "set_health":                0x41,
    "update_health":             0x41,
    "remove_entities":           0x32,
    "respawn":                   0x33,
    "keep_alive":                0x1F,
    "login":                     0x23,
    "unload_chunk":              0x1D,
    "chunk_data":                0x20,
    "block_update":              0x0B,
    "disconnect":                0x1A,
    "chat_message":              0x0F,
    "title":                     0x48,
    "sound_effect":              0x4D,
    "time_update":               0x44,
    "world_border":              0x35,
}

_CB_338 = dict(_CB_335)
_CB_340 = dict(_CB_335)

# ── Serverbound Play IDs ──────────────────────────────────────────────────────

_SB_107: dict[str, int] = {
    "confirm_teleportation":     0x00,
    "chat_message":              0x02,
    "client_information":        0x04,
    "client_settings":           0x04,
    "keep_alive":                0x0B,
    "move_player_pos":           0x0C,
    "move_player_pos_rot":       0x0D,
    "move_player_rot":           0x0E,
    "player_action":             0x13,
    "player_position_and_look":  0x0D,
    "swing_arm":                 0x1A,
    "use_item":                  0x1C,
    "use_item_on":               0x1C,
    "close_window":              0x08,
    "click_window":              0x07,
    "entity_action":             0x14,
    "held_item_change":          0x17,
    "creative_inventory_action": 0x18,
    "tab_complete":              0x01,
    "set_held_item":             0x17,
}

_SB_108 = dict(_SB_107)
_SB_109 = dict(_SB_107)
_SB_110 = dict(_SB_107)
_SB_210 = dict(_SB_107)
_SB_315 = dict(_SB_107)
_SB_316 = dict(_SB_107)

_SB_335: dict[str, int] = {
    **_SB_107,
    "keep_alive":                0x0B,
    "move_player_pos":           0x0C,
    "move_player_pos_rot":       0x0D,
}

_SB_338 = dict(_SB_335)
_SB_340 = dict(_SB_335)

# ── Public tables ─────────────────────────────────────────────────────────────

CB_IDS: dict[int, dict[str, int]] = {
    107: _CB_107,
    108: _CB_108,
    109: _CB_109,
    110: _CB_110,
    210: _CB_210,
    315: _CB_315,
    316: _CB_316,
    335: _CB_335,
    338: _CB_338,
    340: _CB_340,
}

SB_IDS: dict[int, dict[str, int]] = {
    107: _SB_107,
    108: _SB_108,
    109: _SB_109,
    110: _SB_110,
    210: _SB_210,
    315: _SB_315,
    316: _SB_316,
    335: _SB_335,
    338: _SB_338,
    340: _SB_340,
}
