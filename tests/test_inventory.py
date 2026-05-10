"""Tests for inventory management and inventory packets."""

import pytest
from mcpycore.player.inventory import PlayerInventory, TOTAL_SLOTS
from mcpycore.packets.play.inventory import ItemStack, SetContainerSlot


# ── ItemStack ─────────────────────────────────────────────────────────────────

def test_itemstack_empty_repr():
    s = ItemStack()
    assert "empty" in repr(s)


def test_itemstack_present_repr():
    s = ItemStack(present=True, item_id=5, count=64)
    assert "5" in repr(s)
    assert "64" in repr(s)


def test_itemstack_defaults():
    s = ItemStack()
    assert not s.present
    assert s.item_id == 0
    assert s.count == 0


# ── PlayerInventory ───────────────────────────────────────────────────────────

def test_inventory_initial_state():
    inv = PlayerInventory()
    assert len(inv.slots) == TOTAL_SLOTS
    assert all(not s.present for s in inv.slots)


def test_inventory_set_and_get():
    inv = PlayerInventory()
    item = ItemStack(present=True, item_id=10, count=5)
    inv.set(9, item)
    assert inv.get(9).item_id == 10
    assert inv.get(9).count == 5


def test_inventory_get_empty_slot():
    inv = PlayerInventory()
    s = inv.get(0)
    assert not s.present


def test_inventory_invalid_index_get():
    inv = PlayerInventory()
    with pytest.raises(IndexError):
        inv.get(100)


def test_inventory_invalid_index_set():
    inv = PlayerInventory()
    with pytest.raises(IndexError):
        inv.set(100, ItemStack())


def test_inventory_set_all():
    inv = PlayerInventory()
    items = [ItemStack(present=True, item_id=i, count=1) for i in range(TOTAL_SLOTS)]
    inv.set_all(items)
    for i in range(TOTAL_SLOTS):
        assert inv.get(i).item_id == i


def test_inventory_set_all_truncates():
    inv = PlayerInventory()
    items = [ItemStack(present=True, item_id=1, count=1) for _ in range(100)]
    inv.set_all(items)
    assert len(inv.slots) == TOTAL_SLOTS


def test_inventory_hotbar():
    inv = PlayerInventory()
    for i in range(9):
        inv.set(36 + i, ItemStack(present=True, item_id=i + 1, count=1))
    hotbar = inv.hotbar
    assert len(hotbar) == 9
    assert hotbar[0].item_id == 1


def test_inventory_held_item_default():
    inv = PlayerInventory()
    assert not inv.held_item.present


def test_inventory_held_item_set():
    inv = PlayerInventory()
    inv.held_slot = 2
    inv.set(38, ItemStack(present=True, item_id=50, count=1))  # slot 36+2
    assert inv.held_item.item_id == 50


def test_inventory_offhand():
    inv = PlayerInventory()
    inv.set(45, ItemStack(present=True, item_id=99, count=1))
    assert inv.offhand.item_id == 99


def test_inventory_armour_slots():
    inv = PlayerInventory()
    assert len(inv.armour) == 4


def test_inventory_non_empty():
    inv = PlayerInventory()
    inv.set(9, ItemStack(present=True, item_id=1, count=1))
    inv.set(10, ItemStack(present=True, item_id=2, count=64))
    non_empty = list(inv.non_empty())
    assert len(non_empty) == 2


def test_inventory_count_item():
    inv = PlayerInventory()
    inv.set(9, ItemStack(present=True, item_id=5, count=32))
    inv.set(10, ItemStack(present=True, item_id=5, count=16))
    inv.set(11, ItemStack(present=True, item_id=6, count=64))
    assert inv.count_item(5) == 48
    assert inv.count_item(6) == 64
    assert inv.count_item(7) == 0


def test_inventory_find_item():
    inv = PlayerInventory()
    inv.set(15, ItemStack(present=True, item_id=3, count=1))
    inv.set(20, ItemStack(present=True, item_id=3, count=1))
    found = inv.find_item(3)
    assert 15 in found
    assert 20 in found
    assert len(found) == 2


def test_inventory_find_item_not_found():
    inv = PlayerInventory()
    assert inv.find_item(999) == []


def test_inventory_clear():
    inv = PlayerInventory()
    inv.set(9, ItemStack(present=True, item_id=1, count=1))
    inv.clear()
    assert not inv.get(9).present


def test_inventory_repr():
    inv = PlayerInventory()
    inv.set(9, ItemStack(present=True, item_id=1, count=1))
    r = repr(inv)
    assert "1/" in r


def test_held_slot_change():
    inv = PlayerInventory()
    inv.held_slot = 4
    assert inv.held_slot == 4


# ── TabList ───────────────────────────────────────────────────────────────────

def test_tablist_add_and_get():
    import uuid
    from mcpycore.player.player_list import TabList, TabListEntry
    tl = TabList()
    uid = uuid.uuid4()
    entry = TabListEntry(player_uuid=uid, name="Alice", latency=50)
    tl.add_or_update(entry)
    found = tl.get(uid)
    assert found is not None
    assert found.name == "Alice"


def test_tablist_remove():
    import uuid
    from mcpycore.player.player_list import TabList, TabListEntry
    tl = TabList()
    uid = uuid.uuid4()
    tl.add_or_update(TabListEntry(player_uuid=uid, name="Bob"))
    tl.remove(uid)
    assert tl.get(uid) is None


def test_tablist_by_name():
    import uuid
    from mcpycore.player.player_list import TabList, TabListEntry
    tl = TabList()
    uid = uuid.uuid4()
    tl.add_or_update(TabListEntry(player_uuid=uid, name="Charlie"))
    e = tl.by_name("Charlie")
    assert e is not None
    assert e.player_uuid == uid


def test_tablist_by_name_not_found():
    from mcpycore.player.player_list import TabList
    tl = TabList()
    assert tl.by_name("Nobody") is None


def test_tablist_len():
    import uuid
    from mcpycore.player.player_list import TabList, TabListEntry
    tl = TabList()
    for i in range(5):
        tl.add_or_update(TabListEntry(player_uuid=uuid.uuid4(), name=f"P{i}"))
    assert len(tl) == 5


def test_tablist_all_players_sorted():
    import uuid
    from mcpycore.player.player_list import TabList, TabListEntry
    tl = TabList()
    tl.add_or_update(TabListEntry(player_uuid=uuid.uuid4(), name="Zara"))
    tl.add_or_update(TabListEntry(player_uuid=uuid.uuid4(), name="Alice"))
    tl.add_or_update(TabListEntry(player_uuid=uuid.uuid4(), name="Mike"))
    players = tl.all_players()
    names = [p.name for p in players]
    assert names == sorted(names, key=str.lower)


def test_tablist_online_count():
    import uuid
    from mcpycore.player.player_list import TabList, TabListEntry
    tl = TabList()
    tl.add_or_update(TabListEntry(player_uuid=uuid.uuid4(), name="A", listed=True))
    tl.add_or_update(TabListEntry(player_uuid=uuid.uuid4(), name="B", listed=False))
    assert tl.online_count() == 1


def test_ping_category():
    from mcpycore.player.player_list import TabListEntry
    import uuid
    e = TabListEntry(player_uuid=uuid.uuid4(), name="X", latency=50)
    assert e.ping_category == "excellent"
    e.latency = 200
    assert e.ping_category == "good"
    e.latency = 400
    assert e.ping_category == "medium"
    e.latency = 800
    assert e.ping_category == "bad"
    e.latency = 2000
    assert e.ping_category == "very-bad"
    e.latency = -1
    assert e.ping_category == "no-connection"
