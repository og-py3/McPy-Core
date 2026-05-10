"""
Unit tests for MinecraftClient that do not require a real server.
Tests focus on version wiring, dispatch table, event system, and state.
"""

import pytest
import warnings

from mcpycore import MinecraftClient, OfflineAuth
from mcpycore.versions import (
    PROTOCOL_1_20_4, PROTOCOL_1_21_1, PROTOCOL_1_21_4,
    PROTOCOL_1_21_11, PROTOCOL_LATEST, SNAPSHOT_BASE,
    get_clientbound_id,
)


def make_client(protocol=PROTOCOL_LATEST) -> MinecraftClient:
    return MinecraftClient("localhost", auth=OfflineAuth("TestBot"), protocol_version=protocol)


# ── Construction ──────────────────────────────────────────────────────────────

def test_client_default_protocol():
    c = make_client()
    assert c.protocol_version == PROTOCOL_LATEST


def test_client_custom_protocol():
    c = make_client(PROTOCOL_1_20_4)
    assert c.protocol_version == PROTOCOL_1_20_4


def test_client_repr_unauthenticated():
    c = make_client()
    r = repr(c)
    assert "localhost" in r
    assert "unauthenticated" in r


def test_client_version_name():
    c = make_client(PROTOCOL_1_21_1)
    assert "1.21.1" in c.version_name


def test_client_version_name_latest():
    c = make_client(PROTOCOL_LATEST)
    assert "1.21.11" in c.version_name


def test_client_snapshot_warns():
    snap = SNAPSHOT_BASE | 0x100
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        c = MinecraftClient("localhost", protocol_version=snap)
        assert len(w) == 1
        assert "snapshot" in str(w[0].message).lower()


def test_client_initial_position():
    c = make_client()
    assert c.position == (0.0, 0.0, 0.0)


def test_client_initial_health():
    c = make_client()
    assert c.health == 20.0
    assert c.food == 20


def test_client_initial_game_mode():
    c = make_client()
    assert c.game_mode == 0


def test_client_is_survival():
    c = make_client()
    assert c.is_survival
    assert not c.is_creative


def test_client_initial_world():
    from mcpycore.world import World
    c = make_client()
    assert isinstance(c.world, World)


def test_client_initial_entities():
    from mcpycore.entity import EntityManager
    c = make_client()
    assert isinstance(c.entities, EntityManager)


def test_client_initial_inventory():
    from mcpycore.player import PlayerInventory
    c = make_client()
    assert isinstance(c.inventory, PlayerInventory)


def test_client_initial_tab_list():
    from mcpycore.player import TabList
    c = make_client()
    assert isinstance(c.tab_list, TabList)


def test_client_boss_bars_empty():
    c = make_client()
    assert c.boss_bars == {}


# ── Event system ─────────────────────────────────────────────────────────────

def test_event_registration_and_fire():
    c = make_client()
    results = []

    @c.on("test_event")
    def handler(val):
        results.append(val)

    c.emit("test_event", 42)
    assert results == [42]


def test_event_multiple_handlers():
    c = make_client()
    calls = []

    @c.on("foo")
    def h1(): calls.append(1)

    @c.on("foo")
    def h2(): calls.append(2)

    c.emit("foo")
    assert calls == [1, 2]


def test_event_no_handlers_does_not_raise():
    c = make_client()
    c.emit("nonexistent_event", "data")


def test_event_handler_exception_does_not_crash():
    c = make_client()

    @c.on("err")
    def bad(x):
        raise RuntimeError("oops")

    # Should print error but not raise
    c.emit("err", 1)


def test_event_args_passed():
    c = make_client()
    received = []

    @c.on("multi_arg")
    def h(a, b, c):
        received.append((a, b, c))

    c.emit("multi_arg", 1, 2, 3)
    assert received == [(1, 2, 3)]


# ── Dispatch table ────────────────────────────────────────────────────────────

def test_dispatch_table_built():
    c = make_client()
    assert len(c._play_handlers) > 0


def test_dispatch_table_has_keep_alive():
    c = make_client()
    pid = get_clientbound_id("keep_alive", PROTOCOL_LATEST)
    assert pid in c._play_handlers


def test_dispatch_table_has_chunk_data():
    c = make_client()
    pid = get_clientbound_id("chunk_data", PROTOCOL_LATEST)
    assert pid in c._play_handlers


def test_dispatch_table_has_set_health():
    c = make_client()
    pid = get_clientbound_id("set_health", PROTOCOL_LATEST)
    assert pid in c._play_handlers


def test_dispatch_table_has_disconnect():
    c = make_client()
    pid = get_clientbound_id("disconnect", PROTOCOL_LATEST)
    assert pid in c._play_handlers


def test_dispatch_table_differs_by_version():
    c1 = make_client(PROTOCOL_1_20_4)
    c2 = make_client(PROTOCOL_1_21_11)
    # The packet IDs differ between 1.20.4 and 1.21.11
    assert set(c1._play_handlers.keys()) != set(c2._play_handlers.keys())


def test_dispatch_table_1_21_has_transfer():
    c = make_client(PROTOCOL_1_21_1)
    pid = get_clientbound_id("transfer", PROTOCOL_1_21_1)
    assert pid in c._play_handlers


def test_dispatch_table_1_20_4_no_transfer():
    c = make_client(PROTOCOL_1_20_4)
    pid = get_clientbound_id("transfer", PROTOCOL_1_20_4)
    assert pid is None   # packet doesn't exist in 1.20.4


def test_dispatch_unknown_packet_silent():
    """Unknown packet IDs should be silently ignored."""
    c = make_client()
    from mcpycore.packets.packet import PacketBuffer
    buf = PacketBuffer()
    c._dispatch_play(0xFE, buf)   # not a real packet ID


# ── Server ID helpers ─────────────────────────────────────────────────────────

def test_send_sb_patches_packet_id():
    c = make_client()
    from mcpycore.packets.play.clientbound import KeepAlive
    from mcpycore.packets.play.serverbound import KeepAliveSB
    pkt = KeepAliveSB(keep_alive_id=42)
    original_id = pkt.__class__.packet_id
    # Don't actually send (no connection), just check _sb_id works
    pid = c._sb_id("keep_alive")
    assert pid is not None
    assert isinstance(pid, int)


# ── Inventory integration ─────────────────────────────────────────────────────

def test_inventory_held_slot_change():
    c = make_client()
    c.inventory.held_slot = 3
    assert c.inventory.held_slot == 3


def test_boss_bar_tracking():
    import uuid
    from mcpycore.packets.play.boss_bar import BossBar, ACTION_ADD, ACTION_REMOVE
    c = make_client()
    uid = uuid.uuid4()
    bar = BossBar(boss_uuid=uid, action=ACTION_ADD, title="Boss!", health=1.0)
    c.boss_bars[uid] = bar
    assert uid in c.boss_bars
    c.boss_bars.pop(uid)
    assert uid not in c.boss_bars
