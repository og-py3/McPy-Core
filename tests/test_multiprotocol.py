"""
Tests for multi-protocol support — all eras 1.7.2 → 1.21.11.

Validates:
  • version_name() lookup for every protocol constant
  • feature flags per era
  • CB/SB packet tables present and non-empty for every supported protocol
  • adapter get_cb_ids / get_sb_ids fallback for unknown protocols
"""
from __future__ import annotations

import pytest

from mcpycore.protocol.versions.base import (
    version_name,
    has_configuration_state,
    has_long_keepalive,
    has_varint_keepalive,
    has_uuid_in_login_start,
    has_optional_uuid_in_login_start,
    uses_legacy_login_success_string_uuid,
    PROTOCOL_1_7_2,
    PROTOCOL_1_8,
    PROTOCOL_1_9,
    PROTOCOL_1_12,
    PROTOCOL_1_12_2,
    PROTOCOL_1_16_5,
    PROTOCOL_1_17,
    PROTOCOL_1_19,
    PROTOCOL_1_19_3,
    PROTOCOL_1_19_4,
    PROTOCOL_1_20_1,
    PROTOCOL_1_20_2,
    PROTOCOL_1_21,
    PROTOCOL_1_21_11,
    PROTOCOL_LATEST,
    ALL_STABLE_PROTOCOLS,
    nearest_stable,
    is_snapshot,
)
from mcpycore.protocol.versions.adapters import (
    get_cb_ids,
    get_sb_ids,
    list_supported_protocols,
)


# ── version_name ──────────────────────────────────────────────────────────────

class TestVersionName:
    def test_1_7_2(self):
        assert "1.7" in version_name(PROTOCOL_1_7_2)

    def test_1_8(self):
        assert "1.8" in version_name(PROTOCOL_1_8)

    def test_1_12_2(self):
        assert "1.12" in version_name(PROTOCOL_1_12_2)

    def test_1_20_2(self):
        assert "1.20" in version_name(PROTOCOL_1_20_2)

    def test_1_21_11(self):
        assert "1.21" in version_name(PROTOCOL_1_21_11)

    def test_latest(self):
        name = version_name(PROTOCOL_LATEST)
        assert isinstance(name, str) and len(name) > 0

    def test_unknown_snapshot(self):
        name = version_name(9999)
        assert isinstance(name, str)
        assert "snapshot" in name.lower() or "9999" in name

    def test_all_stable_have_names(self):
        for proto in ALL_STABLE_PROTOCOLS:
            name = version_name(proto)
            assert isinstance(name, str) and len(name) > 0, f"No name for protocol {proto}"


# ── Feature flags ─────────────────────────────────────────────────────────────

class TestFeatureFlags:

    # Configuration state (1.20.2+ / 764+)
    def test_no_configuration_1_8(self):
        assert not has_configuration_state(PROTOCOL_1_8)

    def test_no_configuration_1_20_1(self):
        assert not has_configuration_state(PROTOCOL_1_20_1)

    def test_has_configuration_1_20_2(self):
        assert has_configuration_state(PROTOCOL_1_20_2)

    def test_has_configuration_1_21_11(self):
        assert has_configuration_state(PROTOCOL_1_21_11)

    # Long keep-alive (1.12+ / 335+)
    def test_no_long_keepalive_1_8(self):
        assert not has_long_keepalive(PROTOCOL_1_8)

    def test_no_long_keepalive_1_9(self):
        assert not has_long_keepalive(PROTOCOL_1_9)

    def test_has_long_keepalive_1_12(self):
        assert has_long_keepalive(PROTOCOL_1_12)

    def test_has_long_keepalive_1_21(self):
        assert has_long_keepalive(PROTOCOL_1_21)

    # VarInt keep-alive (1.9–1.11 / 107–316)
    def test_varint_keepalive_1_9(self):
        assert has_varint_keepalive(PROTOCOL_1_9)

    def test_no_varint_keepalive_1_8(self):
        assert not has_varint_keepalive(PROTOCOL_1_8)

    def test_no_varint_keepalive_1_12(self):
        assert not has_varint_keepalive(PROTOCOL_1_12)

    # UUID in LoginStart
    def test_no_uuid_in_login_start_1_8(self):
        assert not has_uuid_in_login_start(PROTOCOL_1_8)

    def test_no_uuid_in_login_start_1_19(self):
        assert not has_uuid_in_login_start(PROTOCOL_1_19)

    def test_optional_uuid_1_19_3(self):
        assert has_optional_uuid_in_login_start(PROTOCOL_1_19_3)

    def test_uuid_in_login_start_1_19_4(self):
        assert has_uuid_in_login_start(PROTOCOL_1_19_4)

    def test_uuid_in_login_start_latest(self):
        assert has_uuid_in_login_start(PROTOCOL_LATEST)

    # Legacy login success
    def test_legacy_login_success_1_7(self):
        assert uses_legacy_login_success_string_uuid(PROTOCOL_1_7_2)

    def test_legacy_login_success_1_8(self):
        assert uses_legacy_login_success_string_uuid(PROTOCOL_1_8)

    def test_no_legacy_login_success_1_9(self):
        assert not uses_legacy_login_success_string_uuid(PROTOCOL_1_9)


# ── Adapter tables ────────────────────────────────────────────────────────────

class TestAdapterTables:

    def test_supported_protocols_non_empty(self):
        protocols = list_supported_protocols()
        assert len(protocols) > 10

    def test_supported_protocols_sorted(self):
        protocols = list_supported_protocols()
        assert protocols == sorted(protocols)

    def test_covers_1_7(self):
        assert PROTOCOL_1_7_2 in list_supported_protocols()

    def test_covers_1_8(self):
        assert PROTOCOL_1_8 in list_supported_protocols()

    def test_covers_1_12_2(self):
        assert PROTOCOL_1_12_2 in list_supported_protocols()

    def test_covers_latest(self):
        assert PROTOCOL_LATEST in list_supported_protocols()

    @pytest.mark.parametrize("proto", [
        PROTOCOL_1_7_2,   # 4
        PROTOCOL_1_8,     # 47
        PROTOCOL_1_9,     # 107
        PROTOCOL_1_12,    # 335
        PROTOCOL_1_12_2,  # 340
        PROTOCOL_1_16_5,  # 754
        PROTOCOL_1_17,    # 755
        PROTOCOL_1_19,    # 759
        PROTOCOL_1_20_1,  # 763
        PROTOCOL_1_20_2,  # 764
        PROTOCOL_1_21_11, # 775
    ])
    def test_cb_table_non_empty(self, proto):
        table = get_cb_ids(proto)
        assert len(table) > 5, f"CB table empty for protocol {proto}"

    @pytest.mark.parametrize("proto", [
        PROTOCOL_1_7_2,
        PROTOCOL_1_8,
        PROTOCOL_1_9,
        PROTOCOL_1_12,
        PROTOCOL_1_12_2,
        PROTOCOL_1_16_5,
        PROTOCOL_1_17,
        PROTOCOL_1_19,
        PROTOCOL_1_20_1,
        PROTOCOL_1_20_2,
        PROTOCOL_1_21_11,
    ])
    def test_sb_table_non_empty(self, proto):
        table = get_sb_ids(proto)
        assert len(table) > 5, f"SB table empty for protocol {proto}"

    @pytest.mark.parametrize("proto", [
        PROTOCOL_1_7_2,
        PROTOCOL_1_8,
        PROTOCOL_1_9,
        PROTOCOL_1_12_2,
        PROTOCOL_1_17,
        PROTOCOL_1_19_4,
        PROTOCOL_LATEST,
    ])
    def test_cb_has_keep_alive(self, proto):
        table = get_cb_ids(proto)
        assert "keep_alive" in table, f"No keep_alive in CB table for protocol {proto}"

    @pytest.mark.parametrize("proto", [
        PROTOCOL_1_7_2,
        PROTOCOL_1_8,
        PROTOCOL_1_9,
        PROTOCOL_1_12_2,
        PROTOCOL_1_17,
        PROTOCOL_1_19_4,
        PROTOCOL_LATEST,
    ])
    def test_sb_has_keep_alive(self, proto):
        table = get_sb_ids(proto)
        assert "keep_alive" in table, f"No keep_alive in SB table for protocol {proto}"

    def test_fallback_unknown_protocol_above_max(self):
        """Unknown protocol ≥ max should fall back to the highest known table."""
        table = get_cb_ids(99999)
        assert len(table) > 0

    def test_fallback_unknown_protocol_between_known(self):
        """Protocol 400 (between 393 and 401 in v1_16) should fall back gracefully."""
        table = get_cb_ids(400)
        assert len(table) > 0

    def test_fallback_unknown_protocol_below_min(self):
        """Protocol 1 (below 1.7.2 = 4) should fall back to lowest known table."""
        table = get_cb_ids(1)
        assert len(table) > 0


# ── nearest_stable / is_snapshot ─────────────────────────────────────────────

class TestVersionHelpers:

    def test_nearest_stable_exact(self):
        assert nearest_stable(PROTOCOL_1_8) == PROTOCOL_1_8

    def test_nearest_stable_snapshot(self):
        # SNAPSHOT_BASE = 0x40000000; use a real snapshot protocol number
        snap = 0x40000000 + 1
        result = nearest_stable(snap)
        assert result in ALL_STABLE_PROTOCOLS

    def test_is_snapshot_false_for_stable(self):
        assert not is_snapshot(PROTOCOL_1_21_11)

    def test_is_snapshot_true_for_high_number(self):
        assert is_snapshot(0x40000000 + 1)

    def test_all_stable_protocols_ordered(self):
        assert list(ALL_STABLE_PROTOCOLS) == sorted(ALL_STABLE_PROTOCOLS)

    def test_all_stable_protocols_contains_expected(self):
        for proto in [
            PROTOCOL_1_7_2, PROTOCOL_1_8, PROTOCOL_1_9,
            PROTOCOL_1_12_2, PROTOCOL_1_16_5, PROTOCOL_1_17,
            PROTOCOL_1_19, PROTOCOL_1_20_2, PROTOCOL_1_21_11,
        ]:
            assert proto in ALL_STABLE_PROTOCOLS, f"Missing {proto} from ALL_STABLE_PROTOCOLS"
