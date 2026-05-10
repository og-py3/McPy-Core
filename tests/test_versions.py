"""Tests for the multi-version packet ID registry."""

import pytest
from mcpycore.versions import (
    PROTOCOL_1_20_2, PROTOCOL_1_20_4, PROTOCOL_1_20_6,
    PROTOCOL_1_21, PROTOCOL_1_21_1, PROTOCOL_1_21_2, PROTOCOL_1_21_4,
    PROTOCOL_LATEST,
    get_clientbound_id, get_serverbound_id,
    get_play_packet_ids, get_serverbound_packet_ids,
    version_name, is_supported,
)


# ── Version name helpers ──────────────────────────────────────────────────────

def test_version_name_known():
    assert version_name(765) == "1.20.4"
    assert version_name(767) == "1.21.1"
    assert version_name(769) == "1.21.4"


def test_version_name_unknown():
    result = version_name(9999)
    assert "9999" in result


def test_protocol_latest_is_775():
    assert PROTOCOL_LATEST == 775


# ── Keep-alive packet ID shifts ───────────────────────────────────────────────

def test_keep_alive_cb_1_20_4():
    assert get_clientbound_id("keep_alive", PROTOCOL_1_20_4) == 0x24


def test_keep_alive_cb_1_21():
    assert get_clientbound_id("keep_alive", PROTOCOL_1_21_1) == 0x26


def test_keep_alive_sb_1_20_4():
    assert get_serverbound_id("keep_alive", PROTOCOL_1_20_4) == 0x14


def test_keep_alive_sb_1_21():
    assert get_serverbound_id("keep_alive", PROTOCOL_1_21_1) == 0x18


# ── Transfer packet (1.21+ only) ─────────────────────────────────────────────

def test_transfer_not_in_1_20_4():
    assert get_clientbound_id("transfer", PROTOCOL_1_20_4) is None


def test_transfer_exists_in_1_21():
    pid = get_clientbound_id("transfer", PROTOCOL_1_21_1)
    assert pid is not None
    assert pid == 0x73


# ── Select Known Packs (1.21+ only) ──────────────────────────────────────────

def test_select_known_packs_not_in_1_20_4():
    assert get_clientbound_id("select_known_packs", PROTOCOL_1_20_4) is None


def test_select_known_packs_in_1_21():
    pid = get_clientbound_id("select_known_packs", PROTOCOL_1_21_1)
    assert pid is not None


# ── Chunk data shifts ─────────────────────────────────────────────────────────

def test_chunk_data_1_20_4():
    assert get_clientbound_id("chunk_data", PROTOCOL_1_20_4) == 0x25


def test_chunk_data_1_21():
    assert get_clientbound_id("chunk_data", PROTOCOL_1_21_1) == 0x27


# ── Player position and look shifts ──────────────────────────────────────────

def test_player_position_1_20_4():
    assert get_clientbound_id("player_position_and_look", PROTOCOL_1_20_4) == 0x3E


def test_player_position_1_21():
    assert get_clientbound_id("player_position_and_look", PROTOCOL_1_21_1) == 0x40


# ── Set health shifts ─────────────────────────────────────────────────────────

def test_set_health_1_20_4():
    assert get_clientbound_id("set_health", PROTOCOL_1_20_4) == 0x55


def test_set_health_1_21():
    assert get_clientbound_id("set_health", PROTOCOL_1_21_1) == 0x57


# ── Version inheritance (1.20.3 inherits 1.20.2 entries) ─────────────────────

def test_inherits_from_previous_version():
    # PROTOCOL_1_20_6 = 766, not explicitly in registry for all packets
    # but should inherit from 765 entries
    pid_764 = get_clientbound_id("keep_alive", 764)
    pid_766 = get_clientbound_id("keep_alive", 766)
    assert pid_764 is not None
    assert pid_766 is not None


# ── get_play_packet_ids returns a dict ────────────────────────────────────────

def test_get_play_packet_ids_1_20_4():
    ids = get_play_packet_ids(PROTOCOL_1_20_4)
    assert "keep_alive" in ids
    assert "chunk_data" in ids
    assert "player_position_and_look" in ids
    # Transfer should not be present in 1.20.4
    assert "transfer" not in ids


def test_get_play_packet_ids_1_21():
    ids = get_play_packet_ids(PROTOCOL_1_21_1)
    assert "keep_alive" in ids
    assert "transfer" in ids
    assert "select_known_packs" in ids


def test_get_serverbound_packet_ids_1_21():
    ids = get_serverbound_packet_ids(PROTOCOL_1_21_1)
    assert "keep_alive" in ids
    assert "move_player_pos_rot" in ids


# ── is_supported ─────────────────────────────────────────────────────────────

def test_is_supported_known_version():
    assert is_supported(PROTOCOL_1_20_4)
    assert is_supported(PROTOCOL_1_21_1)


def test_is_supported_unknown_version():
    assert not is_supported(100)   # way too old
    assert not is_supported(9999)  # way too new


# ── Swing arm serverbound shift ───────────────────────────────────────────────

def test_swing_arm_1_20_4():
    assert get_serverbound_id("swing_arm", PROTOCOL_1_20_4) == 0x36


def test_swing_arm_1_21():
    assert get_serverbound_id("swing_arm", PROTOCOL_1_21_1) == 0x3A


# ── Confirm teleportation stays at 0x00 ──────────────────────────────────────

def test_confirm_teleportation_stable():
    assert get_serverbound_id("confirm_teleportation", PROTOCOL_1_20_4) == 0x00
    assert get_serverbound_id("confirm_teleportation", PROTOCOL_1_21_1) == 0x00
