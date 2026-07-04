"""
Packet ID tables for Minecraft 1.7.x and 1.8.x.

Sources:
  https://wiki.vg/index.php?title=Protocol&oldid=7368   (1.8 / protocol 47)
  https://wiki.vg/index.php?title=Protocol&oldid=6003   (1.7.10 / protocol 5)

Keep-alive ID type: INT (4 bytes, big-endian) in both 1.7 and 1.8.
Login Success UUID: sent as a plain string (not 16 raw bytes).
"""
from __future__ import annotations

# ── 1.8 clientbound Play IDs ──────────────────────────────────────────────────
_CB_47: dict[str, int] = {
    "keep_alive":                0x00,
    "login":                     0x01,   # Join Game
    "chat_message":              0x02,
    "time_update":               0x03,
    "entity_equipment":          0x04,
    "spawn_position":            0x05,
    "update_health":             0x06,
    "respawn":                   0x07,
    "player_position_and_look":  0x08,
    "held_item_change":          0x09,
    "use_bed":                   0x0A,
    "entity_animation":          0x0B,
    "spawn_player":              0x0C,
    "collect_item":              0x0D,
    "spawn_object":              0x0E,
    "spawn_mob":                 0x0F,
    "spawn_painting":            0x10,
    "spawn_experience_orb":      0x11,
    "entity_velocity":           0x12,
    "destroy_entities":          0x13,
    "entity_relative_move":      0x15,
    "entity_look":               0x16,
    "entity_look_and_move":      0x17,
    "entity_teleport":           0x18,
    "entity_head_look":          0x19,
    "entity_status":             0x1A,
    "attach_entity":             0x1B,
    "entity_metadata":           0x1C,
    "entity_effect":             0x1D,
    "remove_entity_effect":      0x1E,
    "set_experience":            0x1F,
    "entity_properties":         0x20,
    "chunk_data":                0x21,
    "multi_block_change":        0x22,
    "block_update":              0x23,
    "block_action":              0x24,
    "block_break_animation":     0x25,
    "explosion":                 0x27,
    "effect":                    0x28,
    "sound_effect":              0x29,
    "change_game_state":         0x2B,
    "open_window":               0x2D,
    "close_window":              0x2E,
    "set_slot":                  0x2F,
    "window_items":              0x30,
    "confirm_transaction":       0x32,
    "update_sign":               0x33,
    "map_data":                  0x34,
    "update_block_entity":       0x35,
    "statistics":                0x37,
    "player_list_item":          0x38,
    "player_abilities":          0x39,
    "tab_complete":              0x3A,
    "scoreboard_objective":      0x3B,
    "update_score":              0x3C,
    "display_scoreboard":        0x3D,
    "teams":                     0x3E,
    "plugin_message":            0x3F,
    "disconnect":                0x40,
    "server_difficulty":         0x41,
    "combat_event":              0x42,
    "camera":                    0x43,
    "world_border":              0x44,
    "title":                     0x45,
    "player_list_header_footer": 0x48,
    "resource_pack_send":        0x48,
    # Convenience aliases used by the dispatcher
    "remove_entities":           0x13,   # alias for destroy_entities
    "chunk_unload":              0x21,   # handled via chunk_data
    "system_chat_message":       0x02,   # alias for chat_message
    "set_health":                0x06,   # alias for update_health
}

# ── 1.8 serverbound Play IDs ──────────────────────────────────────────────────
_SB_47: dict[str, int] = {
    "keep_alive":                0x00,
    "chat_message":              0x01,
    "use_entity":                0x02,
    "player_on_ground":          0x03,
    "move_player_pos":           0x04,
    "move_player_rot":           0x05,
    "move_player_pos_rot":       0x06,
    "player_position_and_look":  0x06,
    "player_action":             0x07,
    "player_block_placement":    0x08,
    "held_item_change":          0x09,
    "swing_arm":                 0x0A,
    "entity_action":             0x0B,
    "steer_vehicle":             0x0C,
    "close_window":              0x0D,
    "click_window":              0x0E,
    "confirm_transaction":       0x0F,
    "creative_inventory_action": 0x10,
    "update_sign":               0x12,
    "player_abilities":          0x13,
    "tab_complete":              0x14,
    "client_information":        0x15,
    "client_settings":           0x15,
    "client_status":             0x16,
    "plugin_message":            0x17,
}

# 1.7.x (protocols 4 and 5) — same play IDs as 1.8 for our purposes.
_CB_4 = dict(_CB_47)
_CB_5 = dict(_CB_47)
_SB_4 = dict(_SB_47)
_SB_5 = dict(_SB_47)

# ── Public tables ─────────────────────────────────────────────────────────────

CB_IDS: dict[int, dict[str, int]] = {
    4:  _CB_4,
    5:  _CB_5,
    47: _CB_47,
}

SB_IDS: dict[int, dict[str, int]] = {
    4:  _SB_4,
    5:  _SB_5,
    47: _SB_47,
}
