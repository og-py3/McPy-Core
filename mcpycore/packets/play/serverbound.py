"""Client → Server packets during the Play state (Minecraft 1.20.x – 1.21.11)."""

from __future__ import annotations

from dataclasses import dataclass

from mcpycore.packets.packet import Packet, PacketBuffer


@dataclass
class ConfirmTeleportation(Packet):
    """0x00 — Acknowledge a server-requested teleport."""
    packet_id = 0x00

    teleport_id: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_varint(self.teleport_id)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ConfirmTeleportation":
        pkt = cls()
        pkt.teleport_id = buf.read_varint()
        return pkt


@dataclass
class ChatCommand(Packet):
    """0x04 — Execute a slash command."""
    packet_id = 0x04

    command: str = ""
    timestamp: int = 0
    salt: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_string(self.command)
        buf.write_long(self.timestamp)
        buf.write_long(self.salt)
        buf.write_varint(0)  # no argument signatures
        buf.write_bool(False)  # signed preview

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ChatCommand":
        pkt = cls()
        pkt.command = buf.read_string()
        pkt.timestamp = buf.read_long()
        pkt.salt = buf.read_long()
        return pkt


@dataclass
class ChatMessageSB(Packet):
    """0x05 — Player sends a chat message."""
    packet_id = 0x05

    message: str = ""
    timestamp: int = 0
    salt: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_string(self.message)
        buf.write_long(self.timestamp)
        buf.write_long(self.salt)
        buf.write_bool(False)  # no signature
        buf.write_varint(0)   # last seen messages count

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ChatMessageSB":
        pkt = cls()
        pkt.message = buf.read_string()
        pkt.timestamp = buf.read_long()
        pkt.salt = buf.read_long()
        return pkt


@dataclass
class ClientInformation(Packet):
    """0x08 — Client settings such as locale, view distance, and skin parts."""
    packet_id = 0x08

    locale: str = "en_us"
    view_distance: int = 10
    chat_mode: int = 0         # 0=enabled, 1=commands only, 2=hidden
    chat_colors: bool = True
    displayed_skin_parts: int = 0x7F
    main_hand: int = 1         # 0=left, 1=right
    enable_text_filtering: bool = False
    allow_listing: bool = True

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_string(self.locale)
        buf.write_byte(self.view_distance)
        buf.write_varint(self.chat_mode)
        buf.write_bool(self.chat_colors)
        buf.write_ubyte(self.displayed_skin_parts)
        buf.write_varint(self.main_hand)
        buf.write_bool(self.enable_text_filtering)
        buf.write_bool(self.allow_listing)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ClientInformation":
        pkt = cls()
        pkt.locale = buf.read_string()
        pkt.view_distance = buf.read_byte()
        pkt.chat_mode = buf.read_varint()
        pkt.chat_colors = buf.read_bool()
        pkt.displayed_skin_parts = buf.read_ubyte()
        pkt.main_hand = buf.read_varint()
        pkt.enable_text_filtering = buf.read_bool()
        pkt.allow_listing = buf.read_bool()
        return pkt


@dataclass
class InteractEntity(Packet):
    """0x13 — Player interacts with (right-clicks) an entity."""
    packet_id = 0x13

    entity_id: int = 0
    interaction_type: int = 0  # 0=interact, 1=attack, 2=interact_at
    target_x: float | None = None
    target_y: float | None = None
    target_z: float | None = None
    hand: int | None = None
    sneaking: bool = False

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_varint(self.entity_id)
        buf.write_varint(self.interaction_type)
        if self.interaction_type == 2 and self.target_x is not None:
            buf.write_float(self.target_x)
            buf.write_float(self.target_y or 0.0)
            buf.write_float(self.target_z or 0.0)
        if self.interaction_type in (0, 2) and self.hand is not None:
            buf.write_varint(self.hand)
        buf.write_bool(self.sneaking)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "InteractEntity":
        pkt = cls()
        pkt.entity_id = buf.read_varint()
        pkt.interaction_type = buf.read_varint()
        if pkt.interaction_type == 2:
            pkt.target_x = buf.read_float()
            pkt.target_y = buf.read_float()
            pkt.target_z = buf.read_float()
        if pkt.interaction_type in (0, 2):
            pkt.hand = buf.read_varint()
        pkt.sneaking = buf.read_bool()
        return pkt


@dataclass
class KeepAliveSB(Packet):
    """0x14 — Client echoes the keep-alive ID sent by server."""
    packet_id = 0x14

    keep_alive_id: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_long(self.keep_alive_id)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "KeepAliveSB":
        pkt = cls()
        pkt.keep_alive_id = buf.read_long()
        return pkt


@dataclass
class MovePlayerPos(Packet):
    """0x17 — Player position update (no rotation)."""
    packet_id = 0x17

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    on_ground: bool = True

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_double(self.x)
        buf.write_double(self.y)
        buf.write_double(self.z)
        buf.write_bool(self.on_ground)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "MovePlayerPos":
        pkt = cls()
        pkt.x = buf.read_double()
        pkt.y = buf.read_double()
        pkt.z = buf.read_double()
        pkt.on_ground = buf.read_bool()
        return pkt


@dataclass
class MovePlayerPosRot(Packet):
    """0x18 — Player position + rotation update."""
    packet_id = 0x18

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    on_ground: bool = True

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_double(self.x)
        buf.write_double(self.y)
        buf.write_double(self.z)
        buf.write_float(self.yaw)
        buf.write_float(self.pitch)
        buf.write_bool(self.on_ground)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "MovePlayerPosRot":
        pkt = cls()
        pkt.x = buf.read_double()
        pkt.y = buf.read_double()
        pkt.z = buf.read_double()
        pkt.yaw = buf.read_float()
        pkt.pitch = buf.read_float()
        pkt.on_ground = buf.read_bool()
        return pkt


@dataclass
class MovePlayerRot(Packet):
    """0x19 — Player rotation-only update."""
    packet_id = 0x19

    yaw: float = 0.0
    pitch: float = 0.0
    on_ground: bool = True

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_float(self.yaw)
        buf.write_float(self.pitch)
        buf.write_bool(self.on_ground)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "MovePlayerRot":
        pkt = cls()
        pkt.yaw = buf.read_float()
        pkt.pitch = buf.read_float()
        pkt.on_ground = buf.read_bool()
        return pkt


@dataclass
class PlayerAction(Packet):
    """0x1D — Player digs, drops item, releases projectile, etc."""
    packet_id = 0x1D

    status: int = 0
    x: int = 0
    y: int = 0
    z: int = 0
    face: int = 0
    sequence: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_varint(self.status)
        buf.write_position(self.x, self.y, self.z)
        buf.write_varint(self.face)
        buf.write_varint(self.sequence)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "PlayerAction":
        pkt = cls()
        pkt.status = buf.read_varint()
        pkt.x, pkt.y, pkt.z = buf.read_position()
        pkt.face = buf.read_varint()
        pkt.sequence = buf.read_varint()
        return pkt


@dataclass
class PlayerCommand(Packet):
    """0x1E — Sneaking, sprinting, horse jump, leave bed, etc."""
    packet_id = 0x1E

    entity_id: int = 0
    action_id: int = 0  # 0=start_sneak, 1=stop_sneak, 2=leave_bed, 3=start_sprint, 4=stop_sprint
    jump_boost: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_varint(self.entity_id)
        buf.write_varint(self.action_id)
        buf.write_varint(self.jump_boost)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "PlayerCommand":
        pkt = cls()
        pkt.entity_id = buf.read_varint()
        pkt.action_id = buf.read_varint()
        pkt.jump_boost = buf.read_varint()
        return pkt


@dataclass
class SetCreativeModeSlot(Packet):
    """0x2C — Set an inventory slot in creative mode."""
    packet_id = 0x2C

    slot: int = 0
    item_present: bool = False
    item_id: int = 0
    item_count: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_short(self.slot)
        buf.write_bool(self.item_present)
        if self.item_present:
            buf.write_varint(self.item_id)
            buf.write_byte(self.item_count)
            buf.write_varint(0)  # no components

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SetCreativeModeSlot":
        pkt = cls()
        pkt.slot = buf.read_short()
        pkt.item_present = buf.read_bool()
        if pkt.item_present:
            pkt.item_id = buf.read_varint()
            pkt.item_count = buf.read_byte()
        return pkt


@dataclass
class SwingArm(Packet):
    """0x36 — Client swings the player's arm."""
    packet_id = 0x36

    hand: int = 0  # 0=main, 1=off

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_varint(self.hand)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SwingArm":
        pkt = cls()
        pkt.hand = buf.read_varint()
        return pkt


@dataclass
class UseItem(Packet):
    """0x3A — Client uses the held item (right-click in air)."""
    packet_id = 0x3A

    hand: int = 0
    sequence: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_varint(self.hand)
        buf.write_varint(self.sequence)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "UseItem":
        pkt = cls()
        pkt.hand = buf.read_varint()
        pkt.sequence = buf.read_varint()
        return pkt


@dataclass
class SetHeldItemSB(Packet):
    """0x2B — Player changes the active hotbar slot (0–8)."""
    packet_id = 0x2B

    slot: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_short(self.slot)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SetHeldItemSB":
        pkt = cls()
        pkt.slot = buf.read_short()
        return pkt


@dataclass
class ClientStatus(Packet):
    """0x? — Client status: respawn (0) or stats request (1)."""
    packet_id = 0x07

    action_id: int = 0   # 0=perform respawn, 1=request stats

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_varint(self.action_id)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ClientStatus":
        pkt = cls()
        pkt.action_id = buf.read_varint()
        return pkt


@dataclass
class UseItemOn(Packet):
    """0x39 — Player right-clicks on a block face."""
    packet_id = 0x39

    hand: int = 0
    x: int = 0
    y: int = 0
    z: int = 0
    face: int = 0
    cursor_x: float = 0.5
    cursor_y: float = 0.5
    cursor_z: float = 0.5
    inside_block: bool = False
    sequence: int = 0

    def encode(self, buf: PacketBuffer) -> None:
        buf.write_varint(self.hand)
        buf.write_position(self.x, self.y, self.z)
        buf.write_varint(self.face)
        buf.write_float(self.cursor_x)
        buf.write_float(self.cursor_y)
        buf.write_float(self.cursor_z)
        buf.write_bool(self.inside_block)
        buf.write_varint(self.sequence)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "UseItemOn":
        pkt = cls()
        pkt.hand = buf.read_varint()
        pkt.x, pkt.y, pkt.z = buf.read_position()
        pkt.face = buf.read_varint()
        pkt.cursor_x = buf.read_float()
        pkt.cursor_y = buf.read_float()
        pkt.cursor_z = buf.read_float()
        pkt.inside_block = buf.read_bool()
        pkt.sequence = buf.read_varint()
        return pkt
