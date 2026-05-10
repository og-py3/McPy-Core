"""Client-side tab-list (player list) state."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class TabListEntry:
    """One player entry in the tab list."""
    player_uuid: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    display_name: str | None = None
    game_mode: int = 0
    latency: int = 0
    listed: bool = True

    @property
    def ping_category(self) -> str:
        if self.latency < 0:
            return "no-connection"
        if self.latency < 150:
            return "excellent"
        if self.latency < 300:
            return "good"
        if self.latency < 600:
            return "medium"
        if self.latency < 1000:
            return "bad"
        return "very-bad"

    def __repr__(self) -> str:
        return f"TabListEntry({self.name!r}, ping={self.latency}ms)"


class TabList:
    """
    Tracks all players shown in the tab list.
    Updated by PlayerInfoUpdate / PlayerInfoRemove packets.
    """

    def __init__(self) -> None:
        self._entries: dict[uuid.UUID, TabListEntry] = {}
        self.header: str = ""
        self.footer: str = ""

    def add_or_update(self, entry: TabListEntry) -> None:
        self._entries[entry.player_uuid] = entry

    def remove(self, player_uuid: uuid.UUID) -> None:
        self._entries.pop(player_uuid, None)

    def get(self, player_uuid: uuid.UUID) -> TabListEntry | None:
        return self._entries.get(player_uuid)

    def by_name(self, name: str) -> TabListEntry | None:
        for entry in self._entries.values():
            if entry.name == name:
                return entry
        return None

    def all_players(self) -> list[TabListEntry]:
        return sorted(self._entries.values(), key=lambda e: e.name.lower())

    def online_count(self) -> int:
        return len([e for e in self._entries.values() if e.listed])

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[TabListEntry]:
        return iter(self._entries.values())

    def __repr__(self) -> str:
        return f"TabList({len(self)} players)"
