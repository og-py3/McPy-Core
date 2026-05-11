"""Tests for protocol state machine, packet registry, and version tables."""
from __future__ import annotations

import pytest

from mcpycore.protocol.states.machine import State, ProtocolStateMachine, InvalidTransition
from mcpycore.protocol.registry.registry import PacketRegistry, Direction
from mcpycore.protocol.packets.base import Packet, packet
from mcpycore.protocol.versions.base import (
    version_name, is_snapshot, nearest_stable, SNAPSHOT_BASE,
    ALL_STABLE_PROTOCOLS, PROTOCOL_LATEST,
    PROTOCOL_1_20_2, PROTOCOL_1_21, PROTOCOL_1_21_11,
)
from mcpycore.protocol.versions.adapters import get_cb_ids, get_sb_ids


# ── State Machine ─────────────────────────────────────────────────────────────

def test_initial_state():
    sm = ProtocolStateMachine()
    assert sm.current == State.HANDSHAKING


def test_valid_transition_to_login():
    sm = ProtocolStateMachine()
    sm.transition(State.LOGIN)
    assert sm.current == State.LOGIN


def test_valid_transition_to_status():
    sm = ProtocolStateMachine()
    sm.transition(State.STATUS)
    assert sm.current == State.STATUS


def test_valid_full_lifecycle():
    sm = ProtocolStateMachine()
    sm.transition(State.LOGIN)
    sm.transition(State.CONFIGURATION)
    sm.transition(State.PLAY)
    assert sm.current == State.PLAY


def test_invalid_transition_raises():
    sm = ProtocolStateMachine()
    with pytest.raises(InvalidTransition):
        sm.transition(State.PLAY)


def test_invalid_from_play():
    sm = ProtocolStateMachine()
    sm.transition(State.LOGIN)
    sm.transition(State.PLAY)
    with pytest.raises(InvalidTransition):
        sm.transition(State.LOGIN)


def test_force_transition():
    sm = ProtocolStateMachine()
    sm.force(State.PLAY)
    assert sm.current == State.PLAY


def test_transition_callback():
    transitions = []
    sm = ProtocolStateMachine(on_transition=lambda old, new: transitions.append((old, new)))
    sm.transition(State.LOGIN)
    sm.transition(State.PLAY)
    assert transitions[0] == (State.HANDSHAKING, State.LOGIN)
    assert transitions[1] == (State.LOGIN, State.PLAY)


def test_history_tracking():
    sm = ProtocolStateMachine()
    sm.transition(State.LOGIN)
    sm.transition(State.CONFIGURATION)
    sm.transition(State.PLAY)
    assert sm.history == [State.HANDSHAKING, State.LOGIN, State.CONFIGURATION, State.PLAY]


def test_is_in():
    sm = ProtocolStateMachine()
    assert sm.is_in(State.HANDSHAKING)
    assert not sm.is_in(State.PLAY)


def test_repr():
    sm = ProtocolStateMachine()
    assert "HANDSHAKING" in repr(sm).upper() or "handshaking" in repr(sm)


def test_state_equality():
    sm = ProtocolStateMachine()
    assert sm == State.HANDSHAKING


# ── Packet Registry ───────────────────────────────────────────────────────────

def test_register_and_lookup():
    reg = PacketRegistry("test")

    class FakePkt(Packet):
        pass

    reg.register(State.PLAY, Direction.CLIENTBOUND, 0x24, FakePkt)
    result = reg.get(State.PLAY, Direction.CLIENTBOUND, 0x24)
    assert result is FakePkt


def test_lookup_missing():
    reg = PacketRegistry("test")
    assert reg.get(State.PLAY, Direction.CLIENTBOUND, 0xFF) is None


def test_version_filtered_lookup():
    reg = PacketRegistry("test")

    class PktOld(Packet):
        pass

    class PktNew(Packet):
        pass

    reg.register(State.PLAY, Direction.CLIENTBOUND, 0x01, PktOld, version_min=764, version_max=766)
    reg.register(State.PLAY, Direction.CLIENTBOUND, 0x01, PktNew, version_min=767)

    assert reg.get(State.PLAY, Direction.CLIENTBOUND, 0x01, protocol=765) is PktOld
    assert reg.get(State.PLAY, Direction.CLIENTBOUND, 0x01, protocol=767) is PktNew


def test_get_id():
    reg = PacketRegistry("test")

    class FakePkt(Packet):
        pass

    reg.register(State.PLAY, Direction.CLIENTBOUND, 0x10, FakePkt)
    state, direction, pid = reg.get_id(FakePkt)
    assert state == State.PLAY
    assert direction == Direction.CLIENTBOUND
    assert pid == 0x10


def test_len():
    reg = PacketRegistry("test")

    class A(Packet):
        pass
    class B(Packet):
        pass

    reg.register(State.PLAY, Direction.CLIENTBOUND, 0x01, A)
    reg.register(State.PLAY, Direction.CLIENTBOUND, 0x02, B)
    assert len(reg) == 2


def test_contains():
    reg = PacketRegistry("test")

    class A(Packet):
        pass

    reg.register(State.PLAY, Direction.CLIENTBOUND, 0x05, A)
    assert (State.PLAY, Direction.CLIENTBOUND, 0x05) in reg


def test_entries_for_state():
    reg = PacketRegistry("test")

    class A(Packet):
        pass
    class B(Packet):
        pass

    reg.register(State.PLAY, Direction.CLIENTBOUND, 0x01, A)
    reg.register(State.LOGIN, Direction.CLIENTBOUND, 0x02, B)
    entries = reg.entries_for_state(State.PLAY)
    assert len(entries) == 1


# ── @packet decorator ─────────────────────────────────────────────────────────

def test_packet_decorator_registers():
    test_registry = PacketRegistry("decorator_test")

    @packet(packet_id=0xAB, state=State.PLAY, direction=Direction.SERVERBOUND, registry=test_registry)
    class TestPacket(Packet):
        pass

    assert TestPacket._packet_id == 0xAB
    assert TestPacket._state == State.PLAY
    assert TestPacket._direction == Direction.SERVERBOUND
    assert TestPacket._registered is True
    result = test_registry.get(State.PLAY, Direction.SERVERBOUND, 0xAB)
    assert result is TestPacket


def test_packet_decorator_wrong_type():
    test_registry = PacketRegistry("t")
    with pytest.raises(TypeError):
        @packet(0x00, State.PLAY, registry=test_registry)
        class NotAPacket:
            pass


def test_packet_class_methods():
    class MyPkt(Packet):
        _packet_id   = 0x42
        _state       = State.PLAY
        _direction   = Direction.CLIENTBOUND
        _version_min = 767
        _version_max = None

    assert MyPkt.packet_id() == 0x42
    assert MyPkt.state() == State.PLAY
    assert MyPkt.is_clientbound()
    assert not MyPkt.is_serverbound()
    assert MyPkt.supports_version(767)
    assert MyPkt.supports_version(775)
    assert not MyPkt.supports_version(766)


# ── Version tables ────────────────────────────────────────────────────────────

def test_version_name_stable():
    assert "1.20.2" in version_name(764)
    assert "1.21.1" in version_name(767)
    assert "1.21.11" in version_name(775)


def test_version_name_snapshot():
    name = version_name(SNAPSHOT_BASE | 0x100)
    assert "snapshot" in name


def test_version_name_unknown():
    assert "9999" in version_name(9999)


def test_is_snapshot_true():
    assert is_snapshot(SNAPSHOT_BASE)
    assert is_snapshot(SNAPSHOT_BASE | 0xFF)


def test_is_snapshot_false():
    assert not is_snapshot(775)
    assert not is_snapshot(764)


def test_nearest_stable_exact():
    assert nearest_stable(767) == 767


def test_nearest_stable_snapshot():
    snap = SNAPSHOT_BASE | 0x300
    assert nearest_stable(snap) == PROTOCOL_LATEST


def test_all_stable_protocols_sorted():
    assert ALL_STABLE_PROTOCOLS == sorted(ALL_STABLE_PROTOCOLS)


def test_all_stable_protocols_at_least_eight():
    assert len(ALL_STABLE_PROTOCOLS) >= 8


def test_protocol_latest():
    assert PROTOCOL_LATEST == 775


def test_cb_ids_v1_20():
    ids = get_cb_ids(764)
    assert "keep_alive" in ids
    assert "chunk_data" in ids
    assert "disconnect" in ids
    assert "set_health" in ids


def test_cb_ids_v1_21():
    ids = get_cb_ids(767)
    assert "keep_alive" in ids
    assert "transfer" in ids
    assert "select_known_packs" in ids


def test_cb_ids_1_21_11():
    ids = get_cb_ids(775)
    assert "keep_alive" in ids
    assert "transfer" in ids


def test_sb_ids_v1_20():
    ids = get_sb_ids(764)
    assert "keep_alive" in ids
    assert "chat_command" in ids
    assert "swing_arm" in ids
    assert "confirm_teleportation" in ids


def test_sb_ids_v1_21():
    ids = get_sb_ids(767)
    assert "keep_alive" in ids
    assert "move_player_pos_rot" in ids


def test_ids_differ_between_versions():
    cb764 = get_cb_ids(764)
    cb767 = get_cb_ids(767)
    # keep_alive moved between versions
    assert cb764["keep_alive"] != cb767["keep_alive"]


def test_fallback_for_unknown_protocol():
    # Protocol 763 is unknown — should fall back to 764
    ids = get_cb_ids(763)
    assert isinstance(ids, dict)
    assert "keep_alive" in ids


def test_confirm_teleportation_always_0x00():
    for proto in ALL_STABLE_PROTOCOLS:
        sb = get_sb_ids(proto)
        assert sb.get("confirm_teleportation") == 0x00
