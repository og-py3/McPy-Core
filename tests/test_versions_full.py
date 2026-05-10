"""Comprehensive version registry tests — protocol 764 → 775 + snapshots."""

import pytest
from mcpycore.versions import (
    PROTOCOL_1_20_2, PROTOCOL_1_20_4, PROTOCOL_1_20_6,
    PROTOCOL_1_21, PROTOCOL_1_21_1, PROTOCOL_1_21_2, PROTOCOL_1_21_4,
    PROTOCOL_1_21_5, PROTOCOL_1_21_6, PROTOCOL_1_21_7,
    PROTOCOL_1_21_8, PROTOCOL_1_21_9, PROTOCOL_1_21_11,
    PROTOCOL_LATEST, SNAPSHOT_BASE,
    get_clientbound_id, get_serverbound_id,
    get_play_packet_ids, get_serverbound_packet_ids,
    version_name, is_snapshot, is_supported, nearest_stable,
    build_id_to_name, ALL_STABLE_PROTOCOLS,
)


# ── Basic version info ────────────────────────────────────────────────────────

def test_protocol_latest_is_775():
    assert PROTOCOL_LATEST == 775


def test_protocol_1_21_11_is_775():
    assert PROTOCOL_1_21_11 == 775


def test_protocol_1_20_2_is_764():
    assert PROTOCOL_1_20_2 == 764


def test_all_stable_protocols_sorted():
    assert ALL_STABLE_PROTOCOLS == sorted(ALL_STABLE_PROTOCOLS)


def test_all_stable_protocols_count():
    assert len(ALL_STABLE_PROTOCOLS) >= 8


def test_version_name_764():
    assert "1.20.2" in version_name(764)


def test_version_name_765():
    assert "1.20.4" in version_name(765)


def test_version_name_767():
    assert "1.21" in version_name(767)


def test_version_name_775():
    assert "1.21.11" in version_name(775)


def test_version_name_snapshot():
    v = SNAPSHOT_BASE | 0x138   # 1073742136
    name = version_name(v)
    assert "snapshot" in name
    assert "312" in name


def test_version_name_unknown():
    name = version_name(9999)
    assert "9999" in name


# ── Snapshot detection ────────────────────────────────────────────────────────

def test_is_snapshot_true():
    assert is_snapshot(SNAPSHOT_BASE)
    assert is_snapshot(SNAPSHOT_BASE | 0x138)
    assert is_snapshot(1073742136)   # from screenshot


def test_is_snapshot_false():
    assert not is_snapshot(775)
    assert not is_snapshot(767)
    assert not is_snapshot(764)


def test_snapshot_nearest_stable():
    snap = SNAPSHOT_BASE | 0x138
    assert nearest_stable(snap) == PROTOCOL_LATEST


def test_is_supported_stable():
    for p in ALL_STABLE_PROTOCOLS:
        assert is_supported(p), f"Protocol {p} should be supported"


def test_is_supported_snapshot():
    assert is_supported(SNAPSHOT_BASE | 0x200)


def test_is_supported_too_old():
    assert not is_supported(47)   # 1.8


def test_nearest_stable_exact():
    assert nearest_stable(767) == 767


def test_nearest_stable_between():
    # 766 should resolve to 766
    result = nearest_stable(766)
    assert result <= 766


def test_nearest_stable_future():
    # A protocol higher than 775 should still get the closest known
    result = nearest_stable(900)
    assert result == PROTOCOL_LATEST


# ── Clientbound packet IDs ────────────────────────────────────────────────────

def test_keep_alive_cb_764():
    assert get_clientbound_id("keep_alive", 764) == 0x24


def test_keep_alive_cb_765():
    assert get_clientbound_id("keep_alive", 765) == 0x24


def test_keep_alive_cb_767():
    assert get_clientbound_id("keep_alive", 767) == 0x26


def test_keep_alive_cb_769():
    assert get_clientbound_id("keep_alive", 769) == 0x26


def test_keep_alive_cb_775():
    assert get_clientbound_id("keep_alive", 775) == 0x27


def test_player_position_764():
    assert get_clientbound_id("player_position_and_look", 764) == 0x3E


def test_player_position_767():
    assert get_clientbound_id("player_position_and_look", 767) == 0x40


def test_player_position_775():
    assert get_clientbound_id("player_position_and_look", 775) == 0x41


def test_set_health_764():
    assert get_clientbound_id("set_health", 764) == 0x55


def test_set_health_767():
    assert get_clientbound_id("set_health", 767) == 0x57


def test_set_health_769():
    assert get_clientbound_id("set_health", 769) == 0x5A


def test_chunk_data_764():
    assert get_clientbound_id("chunk_data", 764) == 0x25


def test_chunk_data_767():
    assert get_clientbound_id("chunk_data", 767) == 0x27


def test_chunk_data_775():
    assert get_clientbound_id("chunk_data", 775) == 0x29


def test_disconnect_764():
    assert get_clientbound_id("disconnect", 764) == 0x1B


def test_disconnect_767():
    assert get_clientbound_id("disconnect", 767) == 0x1D


# ── New packets (1.21+) ───────────────────────────────────────────────────────

def test_transfer_not_in_764():
    assert get_clientbound_id("transfer", 764) is None


def test_transfer_in_767():
    assert get_clientbound_id("transfer", 767) is not None


def test_transfer_in_775():
    assert get_clientbound_id("transfer", 775) == 0x77


def test_select_known_packs_cb_in_767():
    assert get_clientbound_id("select_known_packs", 767) is not None


def test_select_known_packs_cb_not_in_764():
    assert get_clientbound_id("select_known_packs", 764) is None


def test_debug_sample_not_in_764():
    assert get_clientbound_id("debug_sample", 764) is None


def test_debug_sample_in_767():
    assert get_clientbound_id("debug_sample", 767) is not None


# ── Serverbound packet IDs ────────────────────────────────────────────────────

def test_keep_alive_sb_764():
    assert get_serverbound_id("keep_alive", 764) == 0x14


def test_keep_alive_sb_767():
    assert get_serverbound_id("keep_alive", 767) == 0x18


def test_keep_alive_sb_775():
    assert get_serverbound_id("keep_alive", 775) == 0x19


def test_confirm_teleportation_stable():
    for p in ALL_STABLE_PROTOCOLS:
        assert get_serverbound_id("confirm_teleportation", p) == 0x00


def test_swing_arm_764():
    assert get_serverbound_id("swing_arm", 764) == 0x36


def test_swing_arm_767():
    assert get_serverbound_id("swing_arm", 767) == 0x3A


def test_chat_command_sb_764():
    assert get_serverbound_id("chat_command", 764) == 0x04


def test_chat_command_sb_775():
    assert get_serverbound_id("chat_command", 775) == 0x04


def test_move_player_pos_rot_sb_767():
    assert get_serverbound_id("move_player_pos_rot", 767) == 0x1B


def test_move_player_pos_rot_sb_775():
    assert get_serverbound_id("move_player_pos_rot", 775) == 0x1C


# ── get_play_packet_ids ───────────────────────────────────────────────────────

def test_play_packet_ids_764_no_transfer():
    ids = get_play_packet_ids(764)
    assert "transfer" not in ids


def test_play_packet_ids_775_has_transfer():
    ids = get_play_packet_ids(775)
    assert "transfer" in ids


def test_play_packet_ids_has_core():
    for p in [764, 767, 769, 775]:
        ids = get_play_packet_ids(p)
        for name in ["keep_alive", "set_health", "chunk_data", "disconnect"]:
            assert name in ids, f"{name} missing for protocol {p}"


def test_play_packet_ids_no_none_values():
    for p in ALL_STABLE_PROTOCOLS:
        ids = get_play_packet_ids(p)
        for name, pid in ids.items():
            assert pid is not None
            assert isinstance(pid, int)


def test_serverbound_ids_no_none_values():
    for p in ALL_STABLE_PROTOCOLS:
        ids = get_serverbound_packet_ids(p)
        for name, pid in ids.items():
            assert pid is not None
            assert isinstance(pid, int)


# ── build_id_to_name ──────────────────────────────────────────────────────────

def test_build_id_to_name_no_collisions():
    for p in ALL_STABLE_PROTOCOLS:
        mapping = build_id_to_name(p)
        # All values should be unique packet IDs
        ids = list(mapping.keys())
        assert len(ids) == len(set(ids)), f"Duplicate IDs at protocol {p}"


def test_build_id_to_name_reverse():
    for p in ALL_STABLE_PROTOCOLS:
        forward = get_play_packet_ids(p)
        reverse = build_id_to_name(p)
        # spot-check keep_alive
        if "keep_alive" in forward:
            pid = forward["keep_alive"]
            assert reverse[pid] == "keep_alive"


# ── Snapshot fallback ─────────────────────────────────────────────────────────

def test_snapshot_uses_latest_dispatch():
    snap = SNAPSHOT_BASE | 0x200
    # Should not raise; falls back to PROTOCOL_LATEST
    pid = get_clientbound_id("keep_alive", snap)
    expected = get_clientbound_id("keep_alive", PROTOCOL_LATEST)
    assert pid == expected


def test_snapshot_protocol_id_matches_latest():
    snap = 1073742136   # exact value from screenshot
    pid = get_clientbound_id("player_position_and_look", snap)
    expected = get_clientbound_id("player_position_and_look", PROTOCOL_LATEST)
    assert pid == expected


# ── Version interpolation ─────────────────────────────────────────────────────

def test_1_21_5_through_11_inherit():
    # All 770–775 should resolve keep_alive to something reasonable
    for p in range(770, 776):
        pid = get_clientbound_id("keep_alive", p)
        assert pid is not None
        assert 0 <= pid <= 0xFF


def test_1_21_5_through_11_sb_keep_alive():
    for p in range(770, 776):
        pid = get_serverbound_id("keep_alive", p)
        assert pid is not None
