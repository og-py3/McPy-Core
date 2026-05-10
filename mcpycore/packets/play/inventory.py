"""
Inventory / container packets (clientbound and serverbound).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from mcpycore.packets.packet import Packet, PacketBuffer


@dataclass
class ItemStack:
    """A single item slot in an inventory."""
    present: bool = False
    item_id: int = 0
    count: int = 0
    # components / nbt omitted — available in raw_data
    raw_data: bytes = b""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ItemStack":
        stack = cls()
        stack.present = buf.read_bool()
        if stack.present:
            stack.item_id = buf.read_varint()
            stack.count = buf.read_ubyte()
            stack.raw_data = buf.remaining()
        return stack

    def __repr__(self) -> str:
        if not self.present:
            return "ItemStack(empty)"
        return f"ItemStack(id={self.item_id}, count={self.count})"


@dataclass
class SetContainerContent(Packet):
    """
    Clientbound 0x13 (1.20.4) — Send full inventory state.
    The exact ID varies; see versions.py registry.
    """
    packet_id = 0x13

    window_id: int = 0
    state_id: int = 0
    slots: list[ItemStack] = field(default_factory=list)
    carried_item: ItemStack = field(default_factory=ItemStack)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SetContainerContent":
        pkt = cls()
        pkt.window_id = buf.read_ubyte()
        pkt.state_id = buf.read_varint()
        count = buf.read_varint()
        for _ in range(count):
            present = buf.read_bool()
            if present:
                item_id = buf.read_varint()
                item_count = buf.read_ubyte()
                pkt.slots.append(ItemStack(present=True, item_id=item_id, count=item_count))
            else:
                pkt.slots.append(ItemStack(present=False))
        # carried item
        present = buf.read_bool()
        if present:
            item_id = buf.read_varint()
            item_count = buf.read_ubyte()
            pkt.carried_item = ItemStack(present=True, item_id=item_id, count=item_count)
        return pkt


@dataclass
class SetContainerSlot(Packet):
    """Clientbound — update a single inventory slot."""
    packet_id = 0x15

    window_id: int = 0
    state_id: int = 0
    slot: int = 0
    item: ItemStack = field(default_factory=ItemStack)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SetContainerSlot":
        pkt = cls()
        pkt.window_id = buf.read_byte()
        pkt.state_id = buf.read_varint()
        pkt.slot = buf.read_short()
        present = buf.read_bool()
        if present:
            item_id = buf.read_varint()
            count = buf.read_ubyte()
            pkt.item = ItemStack(present=True, item_id=item_id, count=count)
        return pkt


@dataclass
class OpenScreen(Packet):
    """Clientbound — open a container UI."""
    packet_id = 0x31

    window_id: int = 0
    window_type: int = 0  # 0=generic_9x1 … see wiki
    title: str = ""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "OpenScreen":
        pkt = cls()
        pkt.window_id = buf.read_varint()
        pkt.window_type = buf.read_varint()
        pkt.title = buf.read_string()
        return pkt


@dataclass
class CloseContainer(Packet):
    """Serverbound — player closes a container."""
    packet_id = 0x0F

    window_id: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_ubyte(self.window_id)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "CloseContainer":
        pkt = cls()
        pkt.window_id = buf.read_ubyte()
        return pkt


@dataclass
class ClickContainer(Packet):
    """Serverbound — player clicks a slot in a container."""
    packet_id = 0x0E

    window_id: int = 0
    state_id: int = 0
    slot: int = 0
    button: int = 0
    mode: int = 0  # 0=click, 1=shift_click, 2=number_key, …
    changed_slots: list[tuple[int, ItemStack]] = field(default_factory=list)
    carried_item: ItemStack = field(default_factory=ItemStack)

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_ubyte(self.window_id)
        buf.write_varint(self.state_id)
        buf.write_short(self.slot)
        buf.write_byte(self.button)
        buf.write_varint(self.mode)
        buf.write_varint(len(self.changed_slots))
        for slot_num, item in self.changed_slots:
            buf.write_short(slot_num)
            buf.write_bool(item.present)
            if item.present:
                buf.write_varint(item.item_id)
                buf.write_ubyte(item.count)
        buf.write_bool(self.carried_item.present)
        if self.carried_item.present:
            buf.write_varint(self.carried_item.item_id)
            buf.write_ubyte(self.carried_item.count)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ClickContainer":
        pkt = cls()
        pkt.window_id = buf.read_ubyte()
        pkt.state_id = buf.read_varint()
        pkt.slot = buf.read_short()
        pkt.button = buf.read_byte()
        pkt.mode = buf.read_varint()
        count = buf.read_varint()
        for _ in range(count):
            slot_num = buf.read_short()
            present = buf.read_bool()
            if present:
                item_id = buf.read_varint()
                item_count = buf.read_ubyte()
                pkt.changed_slots.append((slot_num, ItemStack(True, item_id, item_count)))
            else:
                pkt.changed_slots.append((slot_num, ItemStack()))
        present = buf.read_bool()
        if present:
            pkt.carried_item = ItemStack(True, buf.read_varint(), buf.read_ubyte())
        return pkt


@dataclass
class SetHeldItem(Packet):
    """Clientbound — change the player's hotbar selection."""
    packet_id = 0x53

    slot: int = 0   # 0-8

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SetHeldItem":
        pkt = cls()
        pkt.slot = buf.read_byte()
        return pkt


@dataclass
class SetHeldItemSB(Packet):
    """Serverbound — player changes their hotbar slot."""
    packet_id = 0x2F

    slot: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_short(self.slot)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SetHeldItemSB":
        pkt = cls()
        pkt.slot = buf.read_short()
        return pkt
