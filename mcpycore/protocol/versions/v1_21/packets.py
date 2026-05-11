"""
Packet ID tables for Minecraft 1.21.x (protocols 767–775).

CB_IDS[protocol][name] = clientbound_packet_id
SB_IDS[protocol][name] = serverbound_packet_id

IDs for protocols 770–775 are estimated from the 769 baseline with
incremental offsets observed in the Minecraft protocol changelog.
Clearly documented so contributors can update from wiki.vg.
"""
from __future__ import annotations

# ── Clientbound IDs ───────────────────────────────────────────────────────────
#   Source: https://wiki.vg/Protocol (1.21 / 1.21.1 = protocol 767)

_CB_767 = {
    "bundle_delimiter":             0x00,
    "spawn_entity":                 0x01,
    "entity_animation":             0x03,
    "block_changed_ack":            0x05,
    "block_update":                 0x09,
    "boss_bar":                     0x0A,
    "system_chat_message":          0x6D,
    "chat_message":                 0x1C,
    "clear_titles":                 0x0E,
    "chunk_data":                   0x27,
    "chunk_batch_finished":         0x0D,
    "chunk_batch_start":            0x0C,
    "combat_death":                 0x38,
    "debug_sample":                 0x6C,
    "disconnect":                   0x1D,
    "entity_position":              0x2C,
    "entity_position_and_rotation": 0x2D,
    "entity_rotation":              0x2E,
    "explosion":                    0x1F,
    "game_event":                   0x22,
    "hurt_animation":               0x23,
    "keep_alive":                   0x26,
    "login":                        0x2B,
    "player_abilities":             0x36,
    "player_info_update":           0x3E,
    "player_info_remove":           0x3B,
    "player_position_and_look":     0x40,
    "remove_entities":              0x42,
    "respawn":                      0x47,
    "select_known_packs":           0x70,
    "set_action_bar_text":          0x4D,
    "set_container_content":        0x13,
    "set_container_slot":           0x15,
    "set_health":                   0x57,
    "set_held_item":                0x53,
    "set_subtitle_text":            0x62,
    "set_tab_list_header_and_footer": 0x68,
    "set_title_text":               0x63,
    "set_title_animation_times":    0x64,
    "sound_effect":                 0x65,
    "entity_sound_effect":          0x19,
    "stop_sound":                   0x66,
    "time_update":                  0x5E,
    "transfer":                     0x74,
    "unload_chunk":                 0x21,
    "update_objectives":            0x58,
    "update_score":                 0x5C,
    "reset_score":                  0x43,
    "update_teams":                 0x5F,
    "open_screen":                  0x31,
    "spawn_experience_orb":         0x02,
    "damage_event":                 0x18,
    "display_objective":            0x4E,
    "player_look_at":               0x3D,
    "world_event":                  0x25,
}

# 1.21.2 / 1.21.3 = protocol 768 — minor shifts
_CB_768 = {**_CB_767, **{
    "keep_alive":                   0x26,
    "player_position_and_look":     0x40,
    "set_health":                   0x57,
    "chunk_data":                   0x27,
    "disconnect":                   0x1D,
    "login":                        0x2B,
}}

# 1.21.4 = protocol 769
_CB_769 = {**_CB_768, **{
    "keep_alive":                   0x26,
    "player_position_and_look":     0x40,
    "set_health":                   0x5A,
    "chunk_data":                   0x29,
    "disconnect":                   0x1F,
    "login":                        0x2D,
    "transfer":                     0x77,
    "set_container_content":        0x15,
    "set_container_slot":           0x17,
    "player_info_update":           0x40,
    "player_info_remove":           0x3D,
    "respawn":                      0x49,
    "remove_entities":              0x44,
    "time_update":                  0x60,
    "update_objectives":            0x5A,
    "update_score":                 0x5E,
    "update_teams":                 0x61,
    "set_held_item":                0x55,
    "set_title_text":               0x65,
    "set_subtitle_text":            0x64,
    "set_action_bar_text":          0x4F,
    "set_title_animation_times":    0x66,
    "stop_sound":                   0x68,
    "sound_effect":                 0x67,
    "tab_list_header_footer":       0x6A,
    "system_chat_message":          0x70,
    "reset_score":                  0x45,
    "display_objective":            0x50,
}}

# 1.21.5 through 1.21.11 (protocols 770–775) — use 769 as base
# IDs are estimated; update from wiki.vg as official releases land.
_CB_770 = {**_CB_769, **{
    "keep_alive":                   0x27,
    "chunk_data":                   0x29,
    "player_position_and_look":     0x41,
    "set_health":                   0x5B,
    "disconnect":                   0x20,
    "transfer":                     0x77,
}}
_CB_771 = _CB_770
_CB_772 = _CB_770
_CB_773 = _CB_770
_CB_774 = _CB_770
_CB_775 = _CB_770   # 1.21.11 — same as 1.21.10 baseline

# ── Serverbound IDs ───────────────────────────────────────────────────────────

_SB_767 = {
    "confirm_teleportation":    0x00,
    "query_block_nbt":          0x01,
    "change_difficulty":        0x02,
    "acknowledge_message":      0x03,
    "chat_command":             0x04,
    "signed_chat_command":      0x04,
    "chat_message":             0x05,
    "player_session":           0x06,
    "chunk_batch_received":     0x07,
    "client_status":            0x08,
    "client_information":       0x09,
    "command_suggestions":      0x0A,
    "acknowledge_config":       0x0B,
    "click_container_button":   0x0C,
    "click_container":          0x0D,
    "close_container":          0x0E,
    "slot_changed_during_serverside_inventory": 0x0F,
    "send_packet_data":         0x10,
    "interact_entity":          0x13,
    "jigsaw_generate":          0x14,
    "keep_alive":               0x18,
    "lock_difficulty":          0x19,
    "move_player_pos":          0x1A,
    "move_player_pos_rot":      0x1B,
    "move_player_rot":          0x1C,
    "move_player_on_ground":    0x1D,
    "move_vehicle":             0x1E,
    "paddle_boat":              0x1F,
    "pick_item":                0x20,
    "ping_request":             0x21,
    "place_recipe":             0x22,
    "player_abilities":         0x23,
    "player_action":            0x24,
    "player_command":           0x25,
    "player_input":             0x26,
    "pong":                     0x27,
    "change_recipe_book_settings": 0x28,
    "set_seen_recipe":          0x29,
    "rename_item":              0x2A,
    "resource_pack":            0x2B,
    "seen_advancements":        0x2C,
    "select_trade":             0x2D,
    "set_beacon":               0x2E,
    "set_held_item":            0x2F,
    "program_minecart_command_block": 0x30,
    "set_creative_mode_slot":   0x31,
    "program_jigsaw_block":     0x32,
    "program_structure_block":  0x33,
    "update_sign":              0x34,
    "swing_arm":                0x3A,
    "teleport_to_entity":       0x3B,
    "use_item_on":              0x3C,
    "use_item":                 0x3D,
}

_SB_768 = {**_SB_767, **{
    "keep_alive":               0x18,
    "move_player_pos":          0x1A,
    "move_player_pos_rot":      0x1B,
    "move_player_rot":          0x1C,
    "swing_arm":                0x3A,
}}

_SB_769 = {**_SB_768, **{
    "keep_alive":               0x19,
    "move_player_pos":          0x1B,
    "move_player_pos_rot":      0x1C,
    "move_player_rot":          0x1D,
    "swing_arm":                0x3B,
    "player_action":            0x25,
    "player_command":           0x26,
    "interact_entity":          0x14,
    "use_item_on":              0x3D,
    "use_item":                 0x3E,
    "set_held_item":            0x30,
    "set_creative_mode_slot":   0x32,
    "chat_message":             0x06,
    "chat_command":             0x04,
    "client_status":            0x09,
    "client_information":       0x0A,
    "close_container":          0x0F,
    "click_container":          0x0E,
}}

_SB_770 = {**_SB_769, **{
    "keep_alive":               0x19,
    "move_player_pos":          0x1C,
    "move_player_pos_rot":      0x1C,
    "move_player_rot":          0x1E,
    "swing_arm":                0x3C,
}}
_SB_771 = _SB_770
_SB_772 = _SB_770
_SB_773 = _SB_770
_SB_774 = _SB_770
_SB_775 = _SB_770

# ── Public tables ─────────────────────────────────────────────────────────────

CB_IDS: dict[int, dict[str, int]] = {
    767: _CB_767,
    768: _CB_768,
    769: _CB_769,
    770: _CB_770,
    771: _CB_771,
    772: _CB_772,
    773: _CB_773,
    774: _CB_774,
    775: _CB_775,
}

SB_IDS: dict[int, dict[str, int]] = {
    767: _SB_767,
    768: _SB_768,
    769: _SB_769,
    770: _SB_770,
    771: _SB_771,
    772: _SB_772,
    773: _SB_773,
    774: _SB_774,
    775: _SB_775,
}
