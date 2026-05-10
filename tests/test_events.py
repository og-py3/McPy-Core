"""Tests for the events constants module."""

import pytest
from mcpycore import events
from mcpycore.events import (
    EVT_CONNECTED, EVT_DISCONNECT, EVT_CHAT, EVT_HEALTH,
    EVT_POSITION, EVT_SPAWN_ENTITY, EVT_BLOCK_UPDATE,
    EVT_CHUNK_LOAD, EVT_CHUNK_UNLOAD, EVT_BOSS_BAR,
    EVT_TITLE, EVT_SUBTITLE, EVT_ACTION_BAR,
    EVT_INVENTORY_UPDATE, EVT_SLOT_UPDATE, EVT_PLAYER_LIST_UPDATE,
    EVT_SOUND, EVT_DEATH, EVT_TRANSFER, EVT_RESPAWN,
    ALL_EVENTS,
)


def test_all_events_are_strings():
    for evt in ALL_EVENTS:
        assert isinstance(evt, str), f"{evt!r} is not a string"


def test_all_events_non_empty():
    for evt in ALL_EVENTS:
        assert len(evt) > 0


def test_all_events_no_duplicates():
    assert len(ALL_EVENTS) == len(set(ALL_EVENTS)), "Duplicate event names found"


def test_core_events_present():
    core = [
        EVT_CONNECTED, EVT_DISCONNECT, EVT_CHAT, EVT_HEALTH,
        EVT_POSITION, EVT_SPAWN_ENTITY, EVT_BLOCK_UPDATE,
    ]
    for evt in core:
        assert evt in ALL_EVENTS


def test_new_events_present():
    new_evts = [
        EVT_CHUNK_LOAD, EVT_CHUNK_UNLOAD, EVT_BOSS_BAR,
        EVT_TITLE, EVT_SUBTITLE, EVT_ACTION_BAR,
        EVT_INVENTORY_UPDATE, EVT_SLOT_UPDATE,
        EVT_PLAYER_LIST_UPDATE, EVT_SOUND, EVT_DEATH,
        EVT_TRANSFER, EVT_RESPAWN,
    ]
    for evt in new_evts:
        assert evt in ALL_EVENTS


def test_event_constant_values():
    assert EVT_CONNECTED == "connected"
    assert EVT_DISCONNECT == "disconnect"
    assert EVT_CHAT == "chat_message"
    assert EVT_HEALTH == "set_health"
    assert EVT_POSITION == "position"
    assert EVT_SPAWN_ENTITY == "spawn_entity"
    assert EVT_BLOCK_UPDATE == "block_update"
    assert EVT_BOSS_BAR == "boss_bar"
    assert EVT_TITLE == "title"
    assert EVT_SOUND == "sound_effect"
    assert EVT_DEATH == "combat_death"
    assert EVT_TRANSFER == "transfer"


def test_event_handler_registration():
    """Simulate registering and firing events without a real client."""
    from collections import defaultdict
    handlers = defaultdict(list)
    received = []

    def make_on(handlers):
        def on(event):
            def dec(fn):
                handlers[event].append(fn)
                return fn
            return dec
        return on

    def emit(event, *args):
        for h in handlers.get(event, []):
            h(*args)

    on = make_on(handlers)

    @on(EVT_CHAT)
    def on_chat(pkt):
        received.append(pkt)

    emit(EVT_CHAT, "hello")
    assert received == ["hello"]


def test_multiple_handlers_same_event():
    from collections import defaultdict
    handlers = defaultdict(list)
    results = []

    def on(event):
        def dec(fn):
            handlers[event].append(fn)
            return fn
        return dec

    def emit(event, *args):
        for h in handlers.get(event, []):
            h(*args)

    @on(EVT_HEALTH)
    def h1(pkt): results.append(("h1", pkt))

    @on(EVT_HEALTH)
    def h2(pkt): results.append(("h2", pkt))

    emit(EVT_HEALTH, "data")
    assert len(results) == 2
    assert results[0] == ("h1", "data")
    assert results[1] == ("h2", "data")
