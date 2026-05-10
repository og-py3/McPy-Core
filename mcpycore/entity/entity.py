"""Entity data model and manager."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Entity:
    """Represents a tracked entity in the world."""

    entity_id: int
    entity_uuid: uuid.UUID
    entity_type: int

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0

    vel_x: float = 0.0
    vel_y: float = 0.0
    vel_z: float = 0.0

    on_ground: bool = True
    health: float | None = None

    metadata: dict = field(default_factory=dict)

    # ── Computed helpers ──────────────────────────────────────────────────────

    @property
    def position(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z

    def distance_to(self, other: "Entity") -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return (dx * dx + dy * dy + dz * dz) ** 0.5

    def apply_relative_move(self, dx: int, dy: int, dz: int) -> None:
        """Apply a relative movement delta (as encoded in EntityPosition packets)."""
        self.x += dx / 4096.0
        self.y += dy / 4096.0
        self.z += dz / 4096.0

    def __repr__(self) -> str:
        return (
            f"Entity(id={self.entity_id}, type={self.entity_type}, "
            f"pos=({self.x:.1f}, {self.y:.1f}, {self.z:.1f}))"
        )


class EntityManager:
    """
    Tracks all entities in the current world.

    Updated automatically by the client when spawn/move/remove packets arrive.
    Users can iterate or look up entities as needed.
    """

    def __init__(self) -> None:
        self._entities: dict[int, Entity] = {}

    def add(self, entity: Entity) -> None:
        self._entities[entity.entity_id] = entity

    def remove(self, entity_id: int) -> Entity | None:
        return self._entities.pop(entity_id, None)

    def get(self, entity_id: int) -> Entity | None:
        return self._entities.get(entity_id)

    def get_by_uuid(self, entity_uuid: uuid.UUID) -> Entity | None:
        for e in self._entities.values():
            if e.entity_uuid == entity_uuid:
                return e
        return None

    def all(self) -> list[Entity]:
        return list(self._entities.values())

    def nearby(self, x: float, y: float, z: float, radius: float) -> list[Entity]:
        """Return all entities within *radius* blocks of the given coordinates."""
        result: list[Entity] = []
        r2 = radius * radius
        for e in self._entities.values():
            dx = e.x - x
            dy = e.y - y
            dz = e.z - z
            if dx * dx + dy * dy + dz * dz <= r2:
                result.append(e)
        return result

    def clear(self) -> None:
        self._entities.clear()

    def __len__(self) -> int:
        return len(self._entities)

    def __contains__(self, entity_id: int) -> bool:
        return entity_id in self._entities

    def __iter__(self):
        return iter(self._entities.values())
