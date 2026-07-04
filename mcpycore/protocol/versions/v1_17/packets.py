"""
Packet ID tables for Minecraft 1.17.x – 1.19.x.

Sources:
  https://wiki.vg/index.php?title=Protocol&oldid=16918  (1.17  / protocol 755)
  https://wiki.vg/index.php?title=Protocol&oldid=17879  (1.18.2 / protocol 758)
  https://wiki.vg/index.php?title=Protocol&oldid=18375  (1.19  / protocol 759)
  https://wiki.vg/index.php?title=Protocol&oldid=18242  (1.19.3 / protocol 761)
  https://wiki.vg/index.php?title=Protocol&oldid=18375  (1.19.4 / protocol 762)
  https://wiki.vg/index.php?title=Protocol&oldid=18375  (1.20.1 / protocol 763)

Keep-alive ID type: Long (8 bytes) for all versions in this file.
"""
from __future__ import annotations

# ── 1.17 / 1.17.1 clientbound (755–756) ─────────────────────────────────────
_CB_755: dict[str, int] = {
    "spawn_entity":              0x00,
    "spawn_experience_orb":      0x01,
    "animation":                 0x06,
    "block_update":              0x0C,
    "boss_bar":                  0x0D,
    "chat_message":              0x0F,
    "chunk_data":                0x22,
    "disconnect":                0x1A,
    "entity_position":           0x29,
    "entity_position_and_rotation": 0x2A,
    "entity_rotation":           0x2B,
    "explosion":                 0x1C,
    "game_event":                0x1F,
    "keep_alive":                0x21,
    "login":                     0x26,
    "player_abilities":          0x32,
    "player_position_and_look":  0x38,
    "player_list_item":          0x36,
    "remove_entities":           0x3A,
    "respawn":                   0x3D,
    "set_health":                0x52,
    "update_health":             0x52,
    "sound_effect":              0x50,
    "time_update":               0x58,
    "title":                     0x59,
    "set_action_bar_text":       0x41,
    "unload_chunk":              0x1D,
    "update_objectives":         0x53,
    "update_score":              0x56,
    "update_teams":              0x55,
    "world_border":              0x3E,
    "chunk_batch_finished":      0x21,   # alias
    "system_chat_message":       0x0F,   # alias
}

_CB_756 = dict(_CB_755)

# ── 1.18 / 1.18.2 clientbound (757–758) ─────────────────────────────────────
_CB_757: dict[str, int] = dict(_CB_755)   # packet IDs stable from 1.17→1.18

_CB_758 = dict(_CB_757)

# ── 1.19 clientbound (759) ────────────────────────────────────────────────────
_CB_759: dict[str, int] = {
    **_CB_755,
    "disconnect":                0x19,
    "keep_alive":                0x20,
    "login":                     0x26,
    "player_position_and_look":  0x36,
    "respawn":                   0x3B,
    "set_health":                0x52,
    "update_health":             0x52,
    "chat_message":              0x30,
    "system_chat_message":       0x62,
    "remove_entities":           0x38,
    "unload_chunk":              0x1D,
    "chunk_data":                0x22,
    "time_update":               0x58,
}

_CB_760 = dict(_CB_759)

# ── 1.19.3 clientbound (761) ─────────────────────────────────────────────────
_CB_761: dict[str, int] = {
    **_CB_759,
    "disconnect":                0x17,
    "keep_alive":                0x1F,
    "login":                     0x24,
    "player_position_and_look":  0x34,
    "respawn":                   0x3C,
    "set_health":                0x4E,
    "update_health":             0x4E,
    "chat_message":              0x1C,
    "system_chat_message":       0x60,
    "remove_entities":           0x3A,
    "unload_chunk":              0x1D,
    "chunk_data":                0x21,
}

# ── 1.19.4 clientbound (762) ─────────────────────────────────────────────────
_CB_762: dict[str, int] = {
    **_CB_761,
    "disconnect":                0x1A,
    "keep_alive":                0x23,
    "login":                     0x28,
    "player_position_and_look":  0x3C,
    "respawn":                   0x41,
    "set_health":                0x55,
    "update_health":             0x55,
    "chat_message":              0x1C,
    "system_chat_message":       0x64,
    "remove_entities":           0x40,
    "unload_chunk":              0x1F,
    "chunk_data":                0x25,
    "block_update":              0x09,
}

# ── 1.20.1 clientbound (763) ─────────────────────────────────────────────────
_CB_763: dict[str, int] = dict(_CB_762)   # 1.20.1 kept same IDs as 1.19.4

# ── Serverbound Play IDs ──────────────────────────────────────────────────────

_SB_755: dict[str, int] = {
    "confirm_teleportation":     0x00,
    "chat_message":              0x03,
    "client_information":        0x05,
    "client_settings":           0x05,
    "keep_alive":                0x0F,
    "move_player_pos":           0x11,
    "move_player_pos_rot":       0x12,
    "move_player_rot":           0x13,
    "player_action":             0x1B,
    "player_position_and_look":  0x12,
    "swing_arm":                 0x2C,
    "use_item":                  0x2E,
    "use_item_on":               0x2E,
    "close_window":              0x09,
    "click_window":              0x08,
    "held_item_change":          0x25,
    "set_held_item":             0x25,
    "entity_action":             0x1C,
    "tab_complete":              0x06,
    "player_abilities":          0x19,
}

_SB_756 = dict(_SB_755)
_SB_757 = dict(_SB_755)
_SB_758 = dict(_SB_755)

_SB_759: dict[str, int] = {
    **_SB_755,
    "keep_alive":                0x11,
    "chat_message":              0x04,   # chat signing in 1.19
    "move_player_pos":           0x13,
    "move_player_pos_rot":       0x14,
    "move_player_rot":           0x15,
    "player_position_and_look":  0x14,
    "swing_arm":                 0x2F,
}

_SB_760 = dict(_SB_759)

_SB_761: dict[str, int] = {
    **_SB_759,
    "keep_alive":                0x0F,
    "chat_message":              0x05,
    "move_player_pos":           0x13,
    "move_player_pos_rot":       0x14,
    "move_player_rot":           0x15,
    "player_position_and_look":  0x14,
}

_SB_762: dict[str, int] = {
    **_SB_761,
    "keep_alive":                0x15,
    "chat_message":              0x05,
    "confirm_teleportation":     0x00,
    "move_player_pos":           0x14,
    "move_player_pos_rot":       0x15,
    "move_player_rot":           0x16,
    "player_position_and_look":  0x15,
    "swing_arm":                 0x33,
}

_SB_763 = dict(_SB_762)

# ── Public tables ─────────────────────────────────────────────────────────────

CB_IDS: dict[int, dict[str, int]] = {
    755: _CB_755,
    756: _CB_756,
    757: _CB_757,
    758: _CB_758,
    759: _CB_759,
    760: _CB_760,
    761: _CB_761,
    762: _CB_762,
    763: _CB_763,
}

SB_IDS: dict[int, dict[str, int]] = {
    755: _SB_755,
    756: _SB_756,
    757: _SB_757,
    758: _SB_758,
    759: _SB_759,
    760: _SB_760,
    761: _SB_761,
    762: _SB_762,
    763: _SB_763,
}
