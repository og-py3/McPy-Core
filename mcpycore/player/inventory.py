"""
Client-side inventory state manager.

Slot layout mirrors the Minecraft player inventory:
  0       — crafting result
  1–4     — crafting input (2×2)
  5–8     — armour (head, chest, legs, feet)
  9–35    — main inventory (3 rows × 9)
  36–44   — hotbar (9 slots)
  45      — offhand
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from mcpycore.packets.play.inventory import ItemStack

SLOT_CRAFTING_RESULT = 0
SLOT_CRAFTING_INPUT  = slice(1, 5)
SLOT_ARMOUR          = slice(5, 9)
SLOT_MAIN            = slice(9, 36)
SLOT_HOTBAR          = slice(36, 45)
SLOT_OFFHAND         = 45
TOTAL_SLOTS          = 46


class PlayerInventory:
    """
    Tracks the player's full 46-slot inventory.

    Attributes
    ----------
    held_slot : int
        Currently selected hotbar slot (0–8).
    slots : list[ItemStack]
        All 46 slots indexed per Minecraft spec.
    """

    def __init__(self) -> None:
        self.slots: list[ItemStack] = [ItemStack() for _ in range(TOTAL_SLOTS)]
        self.held_slot: int = 0

    # ── Slot access ───────────────────────────────────────────────────────────

    def get(self, index: int) -> ItemStack:
        if 0 <= index < TOTAL_SLOTS:
            return self.slots[index]
        raise IndexError(f"Invalid slot {index} (0–{TOTAL_SLOTS - 1})")

    def set(self, index: int, item: ItemStack) -> None:
        if 0 <= index < TOTAL_SLOTS:
            self.slots[index] = item
        else:
            raise IndexError(f"Invalid slot {index}")

    def set_all(self, items: list[ItemStack]) -> None:
        """Replace all slots from a SetContainerContent packet."""
        for i, item in enumerate(items[:TOTAL_SLOTS]):
            self.slots[i] = item

    # ── Convenience views ─────────────────────────────────────────────────────

    @property
    def hotbar(self) -> list[ItemStack]:
        return self.slots[36:45]

    @property
    def held_item(self) -> ItemStack:
        return self.slots[36 + self.held_slot]

    @property
    def armour(self) -> list[ItemStack]:
        return self.slots[5:9]

    @property
    def offhand(self) -> ItemStack:
        return self.slots[SLOT_OFFHAND]

    def non_empty(self) -> Iterator[tuple[int, ItemStack]]:
        """Yield (index, item) for every non-empty slot."""
        for i, slot in enumerate(self.slots):
            if slot.present:
                yield i, slot

    def count_item(self, item_id: int) -> int:
        """Total count of a specific item across all slots."""
        return sum(s.count for s in self.slots if s.present and s.item_id == item_id)

    def find_item(self, item_id: int) -> list[int]:
        """Return slot indices containing *item_id*."""
        return [i for i, s in enumerate(self.slots) if s.present and s.item_id == item_id]

    # ── State ─────────────────────────────────────────────────────────────────

    def clear(self) -> None:
        self.slots = [ItemStack() for _ in range(TOTAL_SLOTS)]

    def __repr__(self) -> str:
        filled = sum(1 for s in self.slots if s.present)
        return f"PlayerInventory({filled}/{TOTAL_SLOTS} slots filled, held={self.held_slot})"
