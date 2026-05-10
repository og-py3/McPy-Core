"""
Minecraft protocol version constants and per-version packet ID registries.

Covers Java Edition 1.20.2 → 1.21.11 (protocol 764 → 775) plus snapshot detection.

Reference: https://minecraft.wiki/w/Java_Edition_protocol_history

Snapshot protocol versions use the high bit (0x40000000):
    snapshot_protocol = 0x40000000 | build_number
    e.g. 1073742136 = 0x40000138 (snapshot build 312)

Usage::

    from mcpycore.versions import PROTOCOL_LATEST, get_clientbound_id, is_snapshot

    if is_snapshot(protocol):
        protocol = PROTOCOL_LATEST   # fall back to latest stable

    pid = get_clientbound_id("keep_alive", protocol)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── Java Edition stable protocol versions ─────────────────────────────────────
PROTOCOL_1_20_2  = 764   # 1.20.2
PROTOCOL_1_20_3  = 765   # 1.20.3
PROTOCOL_1_20_4  = 765   # 1.20.4 (same as 1.20.3)
PROTOCOL_1_20_5  = 766   # 1.20.5
PROTOCOL_1_20_6  = 766   # 1.20.6 (same as 1.20.5)
PROTOCOL_1_21    = 767   # 1.21
PROTOCOL_1_21_1  = 767   # 1.21.1 (same as 1.21)
PROTOCOL_1_21_2  = 768   # 1.21.2
PROTOCOL_1_21_3  = 768   # 1.21.3 (same as 1.21.2)
PROTOCOL_1_21_4  = 769   # 1.21.4
PROTOCOL_1_21_5  = 770   # 1.21.5
PROTOCOL_1_21_6  = 771   # 1.21.6
PROTOCOL_1_21_7  = 772   # 1.21.7
PROTOCOL_1_21_8  = 773   # 1.21.8
PROTOCOL_1_21_9  = 774   # 1.21.9 / 1.21.10
PROTOCOL_1_21_10 = 774   # alias
PROTOCOL_1_21_11 = 775   # 1.21.11 / latest (protocol 775, May 2026)
PROTOCOL_LATEST  = 775   # Always the newest stable

# Snapshot base — any version >= this is a snapshot/experimental build
SNAPSHOT_BASE = 0x40000000

VERSION_NAMES: dict[int, str] = {
    764: "1.20.2",
    765: "1.20.4",
    766: "1.20.6",
    767: "1.21.1",
    768: "1.21.3",
    769: "1.21.4",
    770: "1.21.5",
    771: "1.21.6",
    772: "1.21.7",
    773: "1.21.8",
    774: "1.21.10",
    775: "1.21.11",
}

ALL_STABLE_PROTOCOLS = sorted(VERSION_NAMES.keys())


def version_name(protocol: int) -> str:
    if is_snapshot(protocol):
        build = protocol & ~SNAPSHOT_BASE
        return f"snapshot (build {build}, 0x{protocol:08X})"
    return VERSION_NAMES.get(protocol, f"unknown (protocol {protocol})")


def is_snapshot(protocol: int) -> bool:
    """Return True if the protocol version is a snapshot/pre-release build."""
    return protocol >= SNAPSHOT_BASE


def snapshot_stable_fallback(protocol: int) -> int:
    """For a snapshot version, return the nearest stable protocol to use for packet dispatch."""
    if not is_snapshot(protocol):
        return protocol
    return PROTOCOL_LATEST


def nearest_stable(protocol: int) -> int:
    """
    Given any protocol version (stable or snapshot), return the closest
    stable version we have a full packet registry for.
    """
    if is_snapshot(protocol):
        return PROTOCOL_LATEST
    stable = [p for p in ALL_STABLE_PROTOCOLS if p <= protocol]
    return stable[-1] if stable else PROTOCOL_LATEST


def is_supported(protocol: int) -> bool:
    """Return True if this protocol is in our supported range (or is a snapshot)."""
    if is_snapshot(protocol):
        return True
    return min(ALL_STABLE_PROTOCOLS) <= protocol <= max(ALL_STABLE_PROTOCOLS)


# ── Clientbound play packet ID registry ───────────────────────────────────────
#
# Format: { canonical_name: { protocol: packet_id, … } }
# Resolution: walk backwards from the requested protocol to find the nearest entry.
# None means the packet did not exist in that version.
#
# !! KNOWN DATA QUALITY ISSUES !!
# Several entries in this table have incorrect or unverified IDs.
# Run ``verify_registry()`` to get a full collision report for any protocol.
# Use https://minecraft.wiki/w/Java_Edition_protocol as the authoritative source.
#
# Confirmed collisions in the original v0.3.0 data (tracked for future correction):
#
#   entity_position / merchant_offers  — share the same ID at every version.
#     entity_position should be one slot higher than merchant_offers
#     (e.g. 764: merchant_offers=0x2C, entity_position=0x2D).
#     Fixing this requires cascading the correction through all subsequent
#     packets; that work is deferred pending wiki verification.
#
#   unload_chunk — stays hardcoded at 0x1F for all versions but should shift
#     upward in 767+ when debug_sample and the damage_event slot were added.
#
#   system_chat_message / pickup_item — both recorded at 0x67 for 764.
#
#   store_cookie / step_tick — both at 0x6B for 767.
#
#   disguised_chat_message / chat_message (alias) — the "chat_message" entry
#     that was previously at the bottom of this table was a duplicate that
#     shadowed disguised_chat_message.  It has been removed (fixed in 0.4.0).
#
#   select_known_packs / cookie_request — these were erroneously added to the
#     play-state registry using their configuration-state IDs, causing collisions
#     with chunk_batch_start and chat_suggestions.  Removed in 0.4.0.
#
# fmt: off
_CB: dict[str, dict[int, int | None]] = {
    # ── Core / session ──────────────────────────────────────────────────────
    "bundle_delimiter":               {764: 0x00, 767: 0x00, 769: 0x00, 775: 0x00},
    "spawn_entity":                   {764: 0x01, 767: 0x01, 769: 0x01, 775: 0x01},
    "spawn_experience_orb":           {764: 0x02, 767: 0x02, 769: 0x02, 775: 0x02},
    "entity_animation":               {764: 0x03, 767: 0x03, 769: 0x03, 775: 0x03},
    "award_statistics":               {764: 0x04, 767: 0x04, 769: 0x04, 775: 0x04},
    "acknowledge_block_change":       {764: 0x05, 767: 0x05, 769: 0x05, 775: 0x05},
    "set_block_destroy_stage":        {764: 0x06, 767: 0x06, 769: 0x06, 775: 0x06},
    "block_entity_data":              {764: 0x07, 767: 0x07, 769: 0x07, 775: 0x07},
    "block_action":                   {764: 0x08, 767: 0x08, 769: 0x08, 775: 0x08},
    "block_update":                   {764: 0x09, 767: 0x09, 769: 0x09, 775: 0x09},
    "boss_bar":                       {764: 0x0A, 767: 0x0A, 769: 0x0A, 775: 0x0A},
    "change_difficulty":              {764: 0x0B, 767: 0x0B, 769: 0x0B, 775: 0x0B},
    "chunk_batch_finished":           {764: 0x0C, 767: 0x0C, 769: 0x0C, 775: 0x0C},
    "chunk_batch_start":              {764: 0x0D, 767: 0x0D, 769: 0x0D, 775: 0x0D},
    "chunk_biomes":                   {764: 0x0E, 767: 0x0E, 769: 0x0E, 775: 0x0E},
    "clear_titles":                   {764: 0x0F, 767: 0x0F, 769: 0x0F, 775: 0x0F},
    "command_suggestions":            {764: 0x10, 767: 0x10, 769: 0x10, 775: 0x10},
    "commands":                       {764: 0x11, 767: 0x11, 769: 0x11, 775: 0x11},
    "close_container":                {764: 0x12, 767: 0x12, 769: 0x12, 775: 0x12},
    "set_container_content":          {764: 0x13, 767: 0x13, 769: 0x13, 775: 0x13},
    "set_container_property":         {764: 0x14, 767: 0x14, 769: 0x14, 775: 0x14},
    "set_container_slot":             {764: 0x15, 767: 0x15, 769: 0x15, 775: 0x15},
    "set_cooldown":                   {764: 0x16, 767: 0x16, 769: 0x16, 775: 0x16},
    "chat_suggestions":               {764: 0x17, 767: 0x17, 769: 0x17, 775: 0x17},
    "plugin_message":                 {764: 0x18, 767: 0x18, 769: 0x18, 775: 0x18},
    "damage_event":                   {764: 0x19, 767: 0x1A, 769: 0x1A, 775: 0x1B},
    "debug_sample":                   {764: None, 767: 0x1B, 769: 0x1B, 775: 0x1C},
    "delete_message":                 {764: 0x1A, 767: 0x1C, 769: 0x1C, 775: 0x1D},
    "disconnect":                     {764: 0x1B, 767: 0x1D, 769: 0x1D, 775: 0x1E},
    "disguised_chat_message":         {764: 0x1C, 767: 0x1E, 769: 0x1E, 775: 0x1F},
    "entity_event":                   {764: 0x1D, 767: 0x1F, 769: 0x1F, 775: 0x20},
    "explosion":                      {764: 0x1E, 767: 0x20, 769: 0x20, 775: 0x21},
    # TODO: unload_chunk is hardcoded at 0x1F for all versions but should shift
    # in 767+ (when packets were inserted before it).  Verify against wiki.
    "unload_chunk":                   {764: 0x1F, 767: 0x1F, 769: 0x1F, 775: 0x1F},
    "game_event":                     {764: 0x20, 767: 0x22, 769: 0x22, 775: 0x23},
    "open_horse_screen":              {764: 0x21, 767: 0x23, 769: 0x23, 775: 0x24},
    "hurt_animation":                 {764: 0x22, 767: 0x24, 769: 0x24, 775: 0x25},
    "world_border_init":              {764: 0x23, 767: 0x25, 769: 0x25, 775: 0x26},
    "keep_alive":                     {764: 0x24, 767: 0x26, 769: 0x26, 775: 0x27},
    "chunk_data":                     {764: 0x25, 767: 0x27, 769: 0x28, 775: 0x29},
    "world_event":                    {764: 0x26, 767: 0x28, 769: 0x29, 775: 0x2A},
    "particle_effect":                {764: 0x28, 767: 0x2A, 769: 0x2B, 775: 0x2C},
    "update_light":                   {764: 0x29, 767: 0x2B, 769: 0x2C, 775: 0x2D},
    "login":                          {764: 0x2A, 767: 0x2C, 769: 0x2D, 775: 0x2E},
    "map_data":                       {764: 0x2B, 767: 0x2D, 769: 0x2E, 775: 0x2F},
    "merchant_offers":                {764: 0x2C, 767: 0x2E, 769: 0x2F, 775: 0x30},
    # TODO: entity_position through entity_rotation collide with merchant_offers
    # and each other at every protocol version.  The correct IDs are each one
    # slot higher (e.g. 764: entity_position=0x2D, not 0x2C).  Fixing requires
    # cascading the entire table below this point.  Verify against wiki before fixing.
    "entity_position":                {764: 0x2C, 767: 0x2E, 769: 0x2E, 775: 0x2F},
    "entity_position_and_rotation":   {764: 0x2D, 767: 0x2F, 769: 0x2F, 775: 0x30},
    "entity_rotation":                {764: 0x2E, 767: 0x30, 769: 0x30, 775: 0x31},
    "move_vehicle":                   {764: 0x2F, 767: 0x31, 769: 0x31, 775: 0x32},
    "open_book":                      {764: 0x30, 767: 0x32, 769: 0x32, 775: 0x33},
    "open_screen":                    {764: 0x31, 767: 0x33, 769: 0x33, 775: 0x34},
    "open_sign_editor":               {764: 0x32, 767: 0x34, 769: 0x34, 775: 0x35},
    "ping":                           {764: 0x33, 767: 0x35, 769: 0x35, 775: 0x36},
    "ping_response":                  {764: 0x34, 767: 0x36, 769: 0x36, 775: 0x37},
    "place_ghost_recipe":             {764: 0x35, 767: 0x37, 769: 0x37, 775: 0x38},
    "player_abilities":               {764: 0x36, 767: 0x38, 769: 0x38, 775: 0x39},
    "player_chat_message":            {764: 0x37, 767: 0x39, 769: 0x39, 775: 0x3A},
    "end_combat":                     {764: 0x38, 767: 0x3A, 769: 0x3A, 775: 0x3B},
    "enter_combat":                   {764: 0x39, 767: 0x3B, 769: 0x3B, 775: 0x3C},
    "combat_death":                   {764: 0x3A, 767: 0x3C, 769: 0x3C, 775: 0x3D},
    "player_info_remove":             {764: 0x3B, 767: 0x3D, 769: 0x3D, 775: 0x3E},
    "player_info_update":             {764: 0x3C, 767: 0x3E, 769: 0x3E, 775: 0x3F},
    "look_at":                        {764: 0x3D, 767: 0x3F, 769: 0x3F, 775: 0x40},
    "player_position_and_look":       {764: 0x3E, 767: 0x40, 769: 0x40, 775: 0x41},
    "player_rotation":                {764: None, 767: None, 769: None, 775: 0x42},
    "unlock_recipes":                 {764: 0x3F, 767: 0x41, 769: 0x41, 775: 0x43},
    "remove_entities":                {764: 0x40, 767: 0x42, 769: 0x42, 775: 0x44},
    "remove_entity_effect":           {764: 0x41, 767: 0x43, 769: 0x43, 775: 0x45},
    "reset_score":                    {764: 0x42, 767: 0x44, 769: 0x44, 775: 0x46},
    "remove_resource_pack":           {764: None, 767: 0x45, 769: 0x45, 775: 0x47},
    "add_resource_pack":              {764: 0x43, 767: 0x46, 769: 0x46, 775: 0x48},
    "respawn":                        {764: 0x44, 767: 0x47, 769: 0x47, 775: 0x49},
    "entity_head_look":               {764: 0x45, 767: 0x48, 769: 0x48, 775: 0x4A},
    "multi_block_change":             {764: 0x46, 767: 0x49, 769: 0x49, 775: 0x4B},
    "select_advancements_tab":        {764: 0x47, 767: 0x4A, 769: 0x4A, 775: 0x4C},
    "server_data":                    {764: 0x48, 767: 0x4B, 769: 0x4B, 775: 0x4D},
    "set_action_bar_text":            {764: 0x49, 767: 0x4C, 769: 0x4C, 775: 0x4E},
    "set_border_center":              {764: 0x4A, 767: 0x4D, 769: 0x4D, 775: 0x4F},
    "set_border_lerp_size":           {764: 0x4B, 767: 0x4E, 769: 0x4E, 775: 0x50},
    "set_border_size":                {764: 0x4C, 767: 0x4F, 769: 0x4F, 775: 0x51},
    "set_border_warning_delay":       {764: 0x4D, 767: 0x50, 769: 0x50, 775: 0x52},
    "set_border_warning_reach":       {764: 0x4E, 767: 0x51, 769: 0x51, 775: 0x53},
    "set_camera":                     {764: 0x4F, 767: 0x52, 769: 0x52, 775: 0x54},
    "set_held_item":                  {764: 0x50, 767: 0x53, 769: 0x53, 775: 0x55},
    "set_center_chunk":               {764: 0x51, 767: 0x54, 769: 0x54, 775: 0x56},
    "set_render_distance":            {764: 0x52, 767: 0x55, 769: 0x55, 775: 0x57},
    "set_default_spawn_position":     {764: 0x53, 767: 0x56, 769: 0x56, 775: 0x58},
    "display_objective":              {764: 0x54, 767: 0x57, 769: 0x57, 775: 0x59},
    "set_health":                     {764: 0x55, 767: 0x57, 769: 0x5A, 775: 0x5B},
    "update_objectives":              {764: 0x56, 767: 0x58, 769: 0x5B, 775: 0x5C},
    "set_passengers":                 {764: 0x57, 767: 0x59, 769: 0x5C, 775: 0x5D},
    "update_teams":                   {764: 0x58, 767: 0x5A, 769: 0x5D, 775: 0x5E},
    "update_score":                   {764: 0x59, 767: 0x5B, 769: 0x5E, 775: 0x5F},
    "set_simulation_distance":        {764: 0x5A, 767: 0x5C, 769: 0x5F, 775: 0x60},
    "set_subtitle_text":              {764: 0x5B, 767: 0x5D, 769: 0x60, 775: 0x61},
    "time_update":                    {764: 0x5C, 767: 0x5E, 769: 0x61, 775: 0x62},
    "set_title_text":                 {764: 0x5D, 767: 0x5F, 769: 0x62, 775: 0x63},
    "set_title_animation_times":      {764: 0x5E, 767: 0x60, 769: 0x63, 775: 0x64},
    "entity_sound_effect":            {764: 0x5F, 767: 0x61, 769: 0x64, 775: 0x65},
    "sound_effect":                   {764: 0x60, 767: 0x62, 769: 0x65, 775: 0x66},
    "start_configuration":            {764: 0x61, 767: 0x63, 769: 0x66, 775: 0x67},
    "stop_sound":                     {764: 0x62, 767: 0x64, 769: 0x67, 775: 0x68},
    # TODO: store_cookie collides with step_tick at 0x6B for 767+.
    # The play-state ID for Store Cookie needs verification against wiki.
    "store_cookie":                   {764: None, 767: 0x6B, 769: 0x6E, 775: 0x6F},
    # TODO: system_chat_message collides with pickup_item at 0x67 for 764.
    # One of these IDs is wrong; verify both against wiki for 1.20.2.
    "system_chat_message":            {764: 0x67, 767: 0x6C, 769: 0x6F, 775: 0x70},
    "set_tab_list_header_and_footer": {764: 0x65, 767: 0x66, 769: 0x69, 775: 0x6A},
    "tag_query_response":             {764: 0x66, 767: 0x67, 769: 0x6A, 775: 0x6B},
    # TODO: pickup_item collides with system_chat_message at 0x67 for 764.
    "pickup_item":                    {764: 0x67, 767: 0x68, 769: 0x6B, 775: 0x6C},
    "teleport_entity":                {764: 0x68, 767: 0x69, 769: 0x6C, 775: 0x6D},
    "set_ticking_state":              {764: 0x69, 767: 0x6A, 769: 0x6D, 775: 0x6E},
    # TODO: step_tick collides with store_cookie at 0x6B for 767+.
    "step_tick":                      {764: 0x6A, 767: 0x6B, 769: 0x6E, 775: 0x6F},
    "transfer":                       {764: None, 767: 0x73, 769: 0x76, 775: 0x77},
    "update_advancements":            {764: 0x6B, 767: 0x6D, 769: 0x70, 775: 0x71},
    "update_attributes":              {764: 0x6C, 767: 0x6E, 769: 0x71, 775: 0x72},
    "entity_effect":                  {764: 0x6D, 767: 0x6F, 769: 0x72, 775: 0x73},
    "update_recipes":                 {764: 0x6E, 767: 0x70, 769: 0x73, 775: 0x74},
    "update_tags":                    {764: 0x6F, 767: 0x71, 769: 0x74, 775: 0x75},
}
# fmt: on

# Entries removed from _CB in v0.4.0 (were causing collisions with play-state packets):
#
#   "select_known_packs" — erroneously used config-state IDs (0x0D at 767),
#     colliding with chunk_batch_start.  This is a configuration-state packet;
#     its play-state equivalent, if any, has a different ID.
#
#   "cookie_request" — same issue: used config-state ID (0x17 at 767),
#     colliding with chat_suggestions.
#
#   "chat_message" (duplicate at bottom) — was an alias for disguised_chat_message
#     using identical IDs, causing a guaranteed collision at every version.
#     The correct event name for Disguised Chat is "disguised_chat_message".

# ── Serverbound play packet ID registry ───────────────────────────────────────
# fmt: off
_SB: dict[str, dict[int, int | None]] = {
    "confirm_teleportation":          {764: 0x00, 767: 0x00, 769: 0x00, 775: 0x00},
    "query_block_entity_tag":         {764: 0x01, 767: 0x01, 769: 0x01, 775: 0x01},
    "change_difficulty":              {764: 0x02, 767: 0x02, 769: 0x02, 775: 0x02},
    "acknowledge_message":            {764: 0x03, 767: 0x03, 769: 0x03, 775: 0x03},
    "chat_command":                   {764: 0x04, 767: 0x04, 769: 0x04, 775: 0x04},
    "signed_chat_command":            {764: None, 767: 0x05, 769: 0x05, 775: 0x05},
    "chat_message":                   {764: 0x05, 767: 0x06, 769: 0x06, 775: 0x06},
    "player_session":                 {764: 0x06, 767: 0x07, 769: 0x07, 775: 0x07},
    "chunk_batch_received":           {764: 0x07, 767: 0x08, 769: 0x08, 775: 0x08},
    "client_information":             {764: 0x08, 767: 0x09, 769: 0x0A, 775: 0x0A},
    "command_suggestions_request":    {764: 0x09, 767: 0x0A, 769: 0x0B, 775: 0x0B},
    "acknowledge_configuration":      {764: 0x0B, 767: 0x0C, 769: 0x0C, 775: 0x0C},
    "click_container_button":         {764: 0x0C, 767: 0x0D, 769: 0x0D, 775: 0x0D},
    "click_container":                {764: 0x0D, 767: 0x0E, 769: 0x0E, 775: 0x0E},
    "close_container":                {764: 0x0E, 767: 0x0F, 769: 0x0F, 775: 0x0F},
    "change_container_slot_state":    {764: 0x0F, 767: 0x10, 769: 0x10, 775: 0x10},
    "cookie_response":                {764: None, 767: 0x11, 769: 0x11, 775: 0x11},
    "plugin_message":                 {764: 0x0F, 767: 0x12, 769: 0x12, 775: 0x12},
    "debug_sample_subscription":      {764: None, 767: 0x13, 769: 0x13, 775: 0x13},
    "edit_book":                      {764: 0x10, 767: 0x14, 769: 0x14, 775: 0x14},
    "query_entity_tag":               {764: 0x11, 767: 0x15, 769: 0x15, 775: 0x15},
    "interact_entity":                {764: 0x13, 767: 0x16, 769: 0x16, 775: 0x16},
    "jigsaw_generate":                {764: 0x14, 767: 0x17, 769: 0x17, 775: 0x17},
    "keep_alive":                     {764: 0x14, 767: 0x18, 769: 0x18, 775: 0x19},
    "lock_difficulty":                {764: 0x15, 767: 0x19, 769: 0x19, 775: 0x1A},
    "move_player_pos":                {764: 0x17, 767: 0x1A, 769: 0x1A, 775: 0x1B},
    "move_player_pos_rot":            {764: 0x18, 767: 0x1B, 769: 0x1B, 775: 0x1C},
    "move_player_rot":                {764: 0x19, 767: 0x1C, 769: 0x1C, 775: 0x1D},
    "move_player_on_ground":          {764: 0x1A, 767: 0x1D, 769: 0x1D, 775: 0x1E},
    "move_vehicle":                   {764: 0x1B, 767: 0x1E, 769: 0x1E, 775: 0x1F},
    "paddle_boat":                    {764: 0x1C, 767: 0x1F, 769: 0x1F, 775: 0x20},
    "pick_item":                      {764: 0x1D, 767: 0x20, 769: 0x20, 775: 0x21},
    "ping_request":                   {764: 0x1E, 767: 0x21, 769: 0x21, 775: 0x22},
    "place_recipe":                   {764: 0x1F, 767: 0x22, 769: 0x22, 775: 0x23},
    "player_abilities":               {764: 0x20, 767: 0x23, 769: 0x23, 775: 0x24},
    "player_action":                  {764: 0x1D, 767: 0x24, 769: 0x24, 775: 0x25},
    "player_command":                 {764: 0x1E, 767: 0x25, 769: 0x25, 775: 0x26},
    "player_input":                   {764: 0x22, 767: 0x26, 769: 0x26, 775: 0x27},
    "pong":                           {764: 0x23, 767: 0x27, 769: 0x27, 775: 0x28},
    "change_recipe_book_settings":    {764: 0x24, 767: 0x28, 769: 0x28, 775: 0x29},
    "set_seen_recipe":                {764: 0x25, 767: 0x29, 769: 0x29, 775: 0x2A},
    "rename_item":                    {764: 0x26, 767: 0x2A, 769: 0x2A, 775: 0x2B},
    "resource_pack_response":         {764: 0x27, 767: 0x2B, 769: 0x2B, 775: 0x2C},
    "seen_advancements":              {764: 0x28, 767: 0x2C, 769: 0x2C, 775: 0x2D},
    "select_trade":                   {764: 0x29, 767: 0x2D, 769: 0x2D, 775: 0x2E},
    "set_beacon_effect":              {764: 0x2A, 767: 0x2E, 769: 0x2E, 775: 0x2F},
    "set_held_item":                  {764: 0x2B, 767: 0x2F, 769: 0x2F, 775: 0x30},
    "program_command_block":          {764: 0x2C, 767: 0x30, 769: 0x30, 775: 0x31},
    "program_command_block_minecart": {764: 0x2D, 767: 0x31, 769: 0x31, 775: 0x32},
    "set_creative_mode_slot":         {764: 0x2E, 767: 0x32, 769: 0x32, 775: 0x33},
    "program_jigsaw_block":           {764: 0x2F, 767: 0x33, 769: 0x33, 775: 0x34},
    "program_structure_block":        {764: 0x30, 767: 0x34, 769: 0x34, 775: 0x35},
    "update_sign":                    {764: 0x31, 767: 0x35, 769: 0x35, 775: 0x36},
    "swing_arm":                      {764: 0x36, 767: 0x3A, 769: 0x3A, 775: 0x3B},
    "teleport_to_entity":             {764: 0x37, 767: 0x3B, 769: 0x3B, 775: 0x3C},
    "use_item_on":                    {764: 0x39, 767: 0x3E, 769: 0x3E, 775: 0x3F},
    "use_item":                       {764: 0x3A, 767: 0x3F, 769: 0x3F, 775: 0x40},
    "select_known_packs":             {764: None, 767: 0x0E, 769: 0x0E, 775: 0x0E},
}
# fmt: on

# ── Configuration state packet ID registries ──────────────────────────────────
#
# The Configuration state has its own packet ID namespace, separate from Play.
# All config-state IDs are stable across supported versions unless noted.
#
_CONFIG_CB: dict[str, dict[int, int | None]] = {
    "config_cookie_request":       {764: None, 767: 0x00, 769: 0x00, 775: 0x00},
    "config_plugin_message":       {764: 0x00, 767: 0x01, 769: 0x01, 775: 0x01},
    "config_disconnect":           {764: 0x01, 767: 0x02, 769: 0x02, 775: 0x02},
    "config_finish":               {764: 0x02, 767: 0x03, 769: 0x03, 775: 0x03},
    "config_keep_alive":           {764: 0x03, 767: 0x04, 769: 0x04, 775: 0x04},
    "config_ping":                 {764: 0x04, 767: 0x05, 769: 0x05, 775: 0x05},
    "config_reset_chat":           {764: None, 767: 0x06, 769: 0x06, 775: 0x06},
    "config_registry_data":        {764: 0x05, 767: 0x07, 769: 0x07, 775: 0x07},
    "config_remove_resource_pack": {764: None, 767: 0x08, 769: 0x08, 775: 0x08},
    "config_add_resource_pack":    {764: 0x06, 767: 0x09, 769: 0x09, 775: 0x09},
    "config_store_cookie":         {764: None, 767: 0x0A, 769: 0x0A, 775: 0x0A},
    "config_transfer":             {764: None, 767: 0x0B, 769: 0x0B, 775: 0x0B},
    "config_feature_flags":        {764: 0x07, 767: 0x0C, 769: 0x0C, 775: 0x0C},
    "config_update_tags":          {764: 0x08, 767: 0x0D, 769: 0x0D, 775: 0x0D},
    "config_select_known_packs":   {764: None, 767: 0x0E, 769: 0x0E, 775: 0x0E},
    "config_custom_report":        {764: None, 767: 0x0F, 769: 0x0F, 775: 0x0F},
    "config_server_links":         {764: None, 767: None, 769: 0x10, 775: 0x10},
}

_CONFIG_SB: dict[str, dict[int, int | None]] = {
    "config_client_information":     {764: 0x00, 767: 0x00, 769: 0x00, 775: 0x00},
    "config_cookie_response":        {764: None, 767: 0x01, 769: 0x01, 775: 0x01},
    "config_plugin_message":         {764: 0x01, 767: 0x02, 769: 0x02, 775: 0x02},
    "config_acknowledge_finish":     {764: 0x02, 767: 0x03, 769: 0x03, 775: 0x03},
    "config_keep_alive":             {764: 0x03, 767: 0x04, 769: 0x04, 775: 0x04},
    "config_pong":                   {764: 0x04, 767: 0x05, 769: 0x05, 775: 0x05},
    "config_resource_pack_response": {764: 0x05, 767: 0x06, 769: 0x06, 775: 0x06},
    "config_select_known_packs":     {764: None, 767: 0x07, 769: 0x07, 775: 0x07},
    "config_custom_report_details":  {764: None, 767: 0x08, 769: 0x08, 775: 0x08},
    "config_server_links_response":  {764: None, 767: None, 769: 0x09, 775: 0x09},
}


def get_config_clientbound_id(name: str, protocol: int) -> int | None:
    """Return the configuration-state clientbound packet ID for *name* at *protocol*."""
    p = nearest_stable(protocol)
    return _resolve(_CONFIG_CB, name, p)


def get_config_serverbound_id(name: str, protocol: int) -> int | None:
    """Return the configuration-state serverbound packet ID for *name* at *protocol*."""
    p = nearest_stable(protocol)
    return _resolve(_CONFIG_SB, name, p)


def _resolve(
    registry: dict[str, dict[int, int | None]], name: str, protocol: int
) -> int | None:
    """
    Find the packet ID for *name* at *protocol*, inheriting the nearest
    earlier entry if no exact match exists.
    Returns None if the packet did not exist in that version.
    """
    entries = registry.get(name)
    if not entries:
        return None
    for ver in sorted(entries.keys(), reverse=True):
        if ver <= protocol:
            return entries[ver]   # may be None (packet not in this version)
    return None


def get_clientbound_id(name: str, protocol: int) -> int | None:
    p = nearest_stable(protocol)
    return _resolve(_CB, name, p)


def get_serverbound_id(name: str, protocol: int) -> int | None:
    p = nearest_stable(protocol)
    return _resolve(_SB, name, p)


def get_play_packet_ids(protocol: int) -> dict[str, int]:
    """Return {name: id} for all clientbound play packets at *protocol*."""
    p = nearest_stable(protocol)
    return {n: pid for n in _CB if (pid := _resolve(_CB, n, p)) is not None}


def get_serverbound_packet_ids(protocol: int) -> dict[str, int]:
    """Return {name: id} for all serverbound play packets at *protocol*."""
    p = nearest_stable(protocol)
    return {n: pid for n in _SB if (pid := _resolve(_SB, n, p)) is not None}


def build_id_to_name(protocol: int) -> dict[int, str]:
    """
    Build a reverse map {packet_id: name} for clientbound play packets.

    If two packet names resolve to the same ID (a registry collision), the last
    one encountered wins and a warning is logged.  Call ``verify_registry()``
    to get a full collision report.
    """
    result: dict[int, str] = {}
    for name, pid in get_play_packet_ids(protocol).items():
        if pid in result:
            logger.warning(
                "Packet ID collision at protocol %d: 0x%02X claimed by both "
                "%r and %r — %r will be used for dispatch.",
                protocol, pid, result[pid], name, name,
            )
        result[pid] = name
    return result


def verify_registry(protocol: int | None = None) -> dict[int, list[tuple[int, list[str]]]]:
    """
    Scan the clientbound play registry for packet ID collisions.

    Parameters
    ----------
    protocol:
        A specific protocol version to check.  If None, all stable protocols
        are checked.

    Returns
    -------
    A dict mapping each affected protocol version to a list of
    ``(packet_id, [name1, name2, …])`` collision tuples.  An empty dict
    means no collisions were found.

    Example::

        from mcpycore.versions import verify_registry
        collisions = verify_registry()
        for proto, entries in collisions.items():
            for pid, names in entries:
                print(f"Protocol {proto}: 0x{pid:02X} → {names}")
    """
    protocols = [protocol] if protocol is not None else ALL_STABLE_PROTOCOLS
    report: dict[int, list[tuple[int, list[str]]]] = {}

    for p in protocols:
        seen: dict[int, list[str]] = {}
        for name in _CB:
            pid = _resolve(_CB, name, p)
            if pid is None:
                continue
            seen.setdefault(pid, []).append(name)
        collisions = [(pid, names) for pid, names in seen.items() if len(names) > 1]
        if collisions:
            report[p] = sorted(collisions)

    return report
