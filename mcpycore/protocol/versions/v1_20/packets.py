"""
Packet ID tables for Minecraft 1.20.x (protocols 764–766).

Source: https://wiki.vg/index.php?title=Protocol&oldid=18375 (1.20.4 = 765)
        https://wiki.vg/index.php?title=Protocol&oldid=18242 (1.20.2 = 764)
"""
from __future__ import annotations

# ── Clientbound IDs ───────────────────────────────────────────────────────────

_CB_764 = {
    "bundle_delimiter":             0x00,
    "spawn_entity":                 0x01,
    "entity_animation":             0x03,
    "block_update":                 0x09,
    "boss_bar":                     0x0A,
    "chat_message":                 0x1C,
    "system_chat_message":          0x67,
    "chunk_data":                   0x25,
    "chunk_batch_finished":         0x0B,
    "chunk_batch_start":            0x0A,
    "combat_death":                 0x36,
    "disconnect":                   0x1B,
    "entity_position":              0x2A,
    "entity_position_and_rotation": 0x2B,
    "entity_rotation":              0x2C,
    "explosion":                    0x1D,
    "game_event":                   0x20,
    "hurt_animation":               0x21,
    "keep_alive":                   0x24,
    "login":                        0x29,
    "player_abilities":             0x34,
    "player_info_update":           0x3C,
    "player_info_remove":           0x39,
    "player_position_and_look":     0x3E,
    "remove_entities":              0x40,
    "respawn":                      0x45,
    "set_action_bar_text":          0x4B,
    "set_container_content":        0x12,
    "set_container_slot":           0x14,
    "set_health":                   0x55,
    "set_held_item":                0x51,
    "set_subtitle_text":            0x5F,
    "set_tab_list_header_and_footer": 0x65,
    "set_title_text":               0x60,
    "set_title_animation_times":    0x61,
    "sound_effect":                 0x62,
    "entity_sound_effect":          0x17,
    "stop_sound":                   0x63,
    "time_update":                  0x5C,
    "unload_chunk":                 0x1F,
    "update_objectives":            0x56,
    "update_score":                 0x5A,
    "reset_score":                  0x41,
    "update_teams":                 0x5D,
    "open_screen":                  0x2F,
    "damage_event":                 0x16,
    "display_objective":            0x4C,
    "world_event":                  0x23,
    "spawn_experience_orb":         0x02,
    "clear_titles":                 0x0C,
}

# 1.20.4 = protocol 765 (same as 1.20.3)
_CB_765 = {**_CB_764, **{
    # Minor adjustments for 1.20.3/1.20.4
    "set_health":                   0x55,
    "system_chat_message":          0x67,
}}

# 1.20.5/1.20.6 = protocol 766
_CB_766 = {**_CB_765, **{
    "keep_alive":                   0x24,
    "chunk_data":                   0x25,
    "player_position_and_look":     0x3E,
    "set_health":                   0x55,
    "disconnect":                   0x1B,
    "login":                        0x29,
    "chunk_batch_finished":         0x0C,   # slight shift in 1.20.5
    "select_known_packs":           0x6D,   # new in 1.20.5
}}

# ── Serverbound IDs ───────────────────────────────────────────────────────────

_SB_764 = {
    "confirm_teleportation":    0x00,
    "chat_command":             0x04,
    "chat_message":             0x05,
    "client_status":            0x07,
    "client_information":       0x08,
    "close_container":          0x0C,
    "click_container":          0x0B,
    "interact_entity":          0x13,
    "keep_alive":               0x14,
    "move_player_pos":          0x17,
    "move_player_pos_rot":      0x18,
    "move_player_rot":          0x19,
    "move_player_on_ground":    0x1A,
    "player_abilities":         0x20,
    "player_action":            0x1D,
    "player_command":           0x1E,
    "set_held_item":            0x2B,
    "set_creative_mode_slot":   0x2C,
    "swing_arm":                0x36,
    "use_item_on":              0x39,
    "use_item":                 0x3A,
    "chunk_batch_received":     0x06,
}

_SB_765 = {**_SB_764}   # same as 764

_SB_766 = {**_SB_765, **{
    # 1.20.5 adds select_known_packs serverbound
    "select_known_packs":       0x0E,
    "acknowledge_config":       0x0B,
    "chat_command":             0x04,
    "client_status":            0x08,
    "client_information":       0x09,
    "keep_alive":               0x18,
    "move_player_pos":          0x1A,
    "move_player_pos_rot":      0x1B,
    "move_player_rot":          0x1C,
    "swing_arm":                0x3A,
    "interact_entity":          0x16,
    "player_action":            0x20,
    "player_command":           0x21,
    "use_item_on":              0x3D,
    "use_item":                 0x3E,
    "set_held_item":            0x2F,
    "set_creative_mode_slot":   0x30,
}}

# ── Public tables ─────────────────────────────────────────────────────────────

CB_IDS: dict[int, dict[str, int]] = {
    764: _CB_764,
    765: _CB_765,
    766: _CB_766,
}

SB_IDS: dict[int, dict[str, int]] = {
    764: _SB_764,
    765: _SB_765,
    766: _SB_766,
}
