"""Tests for Entity and EntityManager."""

import uuid
import pytest
from mcpycore.entity import Entity, EntityManager


def make_entity(eid=1, x=0.0, y=64.0, z=0.0, etype=0):
    return Entity(
        entity_id=eid,
        entity_uuid=uuid.uuid4(),
        entity_type=etype,
        x=x, y=y, z=z,
    )


def test_entity_position():
    e = make_entity(x=10.0, y=64.0, z=-5.0)
    assert e.position == (10.0, 64.0, -5.0)


def test_entity_apply_relative_move():
    e = make_entity(x=0.0, y=64.0, z=0.0)
    e.apply_relative_move(4096, 0, -4096)  # +1 block in X, -1 block in Z
    assert e.x == pytest.approx(1.0)
    assert e.y == pytest.approx(64.0)
    assert e.z == pytest.approx(-1.0)


def test_entity_distance_to():
    a = make_entity(eid=1, x=0.0, y=0.0, z=0.0)
    b = make_entity(eid=2, x=3.0, y=4.0, z=0.0)
    assert a.distance_to(b) == pytest.approx(5.0)


def test_manager_add_get():
    mgr = EntityManager()
    e = make_entity(eid=42)
    mgr.add(e)
    assert mgr.get(42) is e


def test_manager_remove():
    mgr = EntityManager()
    e = make_entity(eid=10)
    mgr.add(e)
    removed = mgr.remove(10)
    assert removed is e
    assert mgr.get(10) is None


def test_manager_get_by_uuid():
    mgr = EntityManager()
    uid = uuid.uuid4()
    e = Entity(entity_id=5, entity_uuid=uid, entity_type=1)
    mgr.add(e)
    assert mgr.get_by_uuid(uid) is e
    assert mgr.get_by_uuid(uuid.uuid4()) is None


def test_manager_nearby():
    mgr = EntityManager()
    mgr.add(make_entity(eid=1, x=0, y=64, z=0))
    mgr.add(make_entity(eid=2, x=5, y=64, z=0))
    mgr.add(make_entity(eid=3, x=100, y=64, z=0))

    near = mgr.nearby(0, 64, 0, radius=10)
    ids = {e.entity_id for e in near}
    assert 1 in ids
    assert 2 in ids
    assert 3 not in ids


def test_manager_all():
    mgr = EntityManager()
    for i in range(5):
        mgr.add(make_entity(eid=i))
    assert len(mgr.all()) == 5


def test_manager_len_contains():
    mgr = EntityManager()
    e = make_entity(eid=7)
    mgr.add(e)
    assert len(mgr) == 1
    assert 7 in mgr
    assert 99 not in mgr


def test_manager_clear():
    mgr = EntityManager()
    for i in range(3):
        mgr.add(make_entity(eid=i))
    mgr.clear()
    assert len(mgr) == 0


def test_manager_iter():
    mgr = EntityManager()
    for i in range(4):
        mgr.add(make_entity(eid=i))
    count = sum(1 for _ in mgr)
    assert count == 4
