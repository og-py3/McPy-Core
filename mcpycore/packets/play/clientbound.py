"""Server → Client packets during the Play state (Minecraft 1.20.x – 1.21.11)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from mcpycore.packets.packet import Packet, PacketBuffer


@dataclass
class BundleDelimiter(Packet):
    """0x00 — Delimiter for a bundle of packets."""
    packet_id = 0x00

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "BundleDelimiter":
        return cls()


@dataclass
class SpawnEntity(Packet):
    """0x01 — Spawn an entity."""
    packet_id = 0x01

    entity_id: int = 0
    entity_uuid: uuid.UUID = field(default_factory=uuid.uuid4)
    entity_type: int = 0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    pitch: int = 0
    yaw: int = 0
    head_yaw: int = 0
    data: int = 0
    vel_x: int = 0
    vel_y: int = 0
    vel_z: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SpawnEntity":
        pkt = cls()
        pkt.entity_id = buf.read_varint()
        pkt.entity_uuid = buf.read_uuid()
        pkt.entity_type = buf.read_varint()
        pkt.x = buf.read_double()
        pkt.y = buf.read_double()
        pkt.z = buf.read_double()
        pkt.pitch = buf.read_ubyte()
        pkt.yaw = buf.read_ubyte()
        pkt.head_yaw = buf.read_ubyte()
        pkt.data = buf.read_varint()
        pkt.vel_x = buf.read_short()
        pkt.vel_y = buf.read_short()
        pkt.vel_z = buf.read_short()
        return pkt


@dataclass
class EntityAnimation(Packet):
    """0x03 — Play an entity animation (swing arm, take damage, etc.)."""
    packet_id = 0x03

    entity_id: int = 0
    animation: int = 0  # 0=swing main, 1=take dmg, 2=leave bed, 3=swing off, 4=crit, 5=magic crit

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "EntityAnimation":
        pkt = cls()
        pkt.entity_id = buf.read_varint()
        pkt.animation = buf.read_ubyte()
        return pkt


@dataclass
class BlockUpdate(Packet):
    """0x09 — Update a single block in the world."""
    packet_id = 0x09

    x: int = 0
    y: int = 0
    z: int = 0
    block_state_id: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "BlockUpdate":
        pkt = cls()
        pkt.x, pkt.y, pkt.z = buf.read_position()
        pkt.block_state_id = buf.read_varint()
        return pkt


@dataclass
class ChatMessage(Packet):
    """0x1C — Chat message from a player."""
    packet_id = 0x1C

    sender: uuid.UUID = field(default_factory=uuid.uuid4)
    index: int = 0
    message_signature: bytes | None = None
    message: str = ""
    timestamp: int = 0
    salt: int = 0
    unsigned_content: str | None = None
    filter_type: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ChatMessage":
        pkt = cls()
        pkt.sender = buf.read_uuid()
        pkt.index = buf.read_varint()
        has_sig = buf.read_bool()
        pkt.message_signature = buf.read_bytes(256) if has_sig else None
        pkt.message = buf.read_string()
        pkt.timestamp = buf.read_long()
        pkt.salt = buf.read_long()
        # Skip last seen messages
        num_seen = buf.read_varint()
        for _ in range(num_seen):
            buf.read_uuid()
            buf.read_bytes(256)
        has_unsigned = buf.read_bool()
        pkt.unsigned_content = buf.read_string() if has_unsigned else None
        pkt.filter_type = buf.read_varint()
        return pkt


@dataclass
class Disconnect(Packet):
    """0x1D — Server disconnects the client."""
    packet_id = 0x1D

    reason: str = ""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "Disconnect":
        pkt = cls()
        pkt.reason = buf.read_string()
        return pkt


@dataclass
class EntityPosition(Packet):
    """0x2C — Relative entity position update."""
    packet_id = 0x2C

    entity_id: int = 0
    delta_x: int = 0
    delta_y: int = 0
    delta_z: int = 0
    on_ground: bool = False

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "EntityPosition":
        pkt = cls()
        pkt.entity_id = buf.read_varint()
        pkt.delta_x = buf.read_short()
        pkt.delta_y = buf.read_short()
        pkt.delta_z = buf.read_short()
        pkt.on_ground = buf.read_bool()
        return pkt


@dataclass
class EntityPositionAndRotation(Packet):
    """0x2D — Combined position and rotation update."""
    packet_id = 0x2D

    entity_id: int = 0
    delta_x: int = 0
    delta_y: int = 0
    delta_z: int = 0
    yaw: int = 0
    pitch: int = 0
    on_ground: bool = False

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "EntityPositionAndRotation":
        pkt = cls()
        pkt.entity_id = buf.read_varint()
        pkt.delta_x = buf.read_short()
        pkt.delta_y = buf.read_short()
        pkt.delta_z = buf.read_short()
        pkt.yaw = buf.read_ubyte()
        pkt.pitch = buf.read_ubyte()
        pkt.on_ground = buf.read_bool()
        return pkt


@dataclass
class EntityRotation(Packet):
    """0x2E — Entity rotation-only update."""
    packet_id = 0x2E

    entity_id: int = 0
    yaw: int = 0
    pitch: int = 0
    on_ground: bool = False

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "EntityRotation":
        pkt = cls()
        pkt.entity_id = buf.read_varint()
        pkt.yaw = buf.read_ubyte()
        pkt.pitch = buf.read_ubyte()
        pkt.on_ground = buf.read_bool()
        return pkt


@dataclass
class KeepAlive(Packet):
    """0x24 — Server keep-alive probe (must be echoed back)."""
    packet_id = 0x24

    keep_alive_id: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "KeepAlive":
        pkt = cls()
        pkt.keep_alive_id = buf.read_long()
        return pkt


@dataclass
class ChunkDataAndUpdateLight(Packet):
    """0x25 — Full chunk column data plus light levels."""
    packet_id = 0x25

    chunk_x: int = 0
    chunk_z: int = 0
    raw_data: bytes = b""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ChunkDataAndUpdateLight":
        pkt = cls()
        pkt.chunk_x = buf.read_int()
        pkt.chunk_z = buf.read_int()
        pkt.raw_data = buf.remaining()
        return pkt


@dataclass
class ParticleEffect(Packet):
    """0x28 — Spawn a particle effect in the world."""
    packet_id = 0x28

    particle_id: int = 0
    long_distance: bool = False
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    offset_z: float = 0.0
    max_speed: float = 0.0
    count: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ParticleEffect":
        pkt = cls()
        pkt.particle_id = buf.read_varint()
        pkt.long_distance = buf.read_bool()
        pkt.x = buf.read_double()
        pkt.y = buf.read_double()
        pkt.z = buf.read_double()
        pkt.offset_x = buf.read_float()
        pkt.offset_y = buf.read_float()
        pkt.offset_z = buf.read_float()
        pkt.max_speed = buf.read_float()
        pkt.count = buf.read_int()
        return pkt


@dataclass
class PlayerAbilities(Packet):
    """0x36 — Server updates player ability flags."""
    packet_id = 0x36

    flags: int = 0  # bit 0=invulnerable, 1=flying, 2=allow_flying, 3=instant_build
    flying_speed: float = 0.05
    fov_modifier: float = 0.1

    @property
    def invulnerable(self) -> bool:
        return bool(self.flags & 0x01)

    @property
    def flying(self) -> bool:
        return bool(self.flags & 0x02)

    @property
    def allow_flying(self) -> bool:
        return bool(self.flags & 0x04)

    @property
    def creative_mode(self) -> bool:
        return bool(self.flags & 0x08)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "PlayerAbilities":
        pkt = cls()
        pkt.flags = buf.read_byte()
        pkt.flying_speed = buf.read_float()
        pkt.fov_modifier = buf.read_float()
        return pkt


@dataclass
class PlayerPositionAndLook(Packet):
    """0x3E — Synchronise player position/look from server."""
    packet_id = 0x3E

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    flags: int = 0
    teleport_id: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "PlayerPositionAndLook":
        pkt = cls()
        pkt.x = buf.read_double()
        pkt.y = buf.read_double()
        pkt.z = buf.read_double()
        pkt.yaw = buf.read_float()
        pkt.pitch = buf.read_float()
        pkt.flags = buf.read_byte()
        pkt.teleport_id = buf.read_varint()
        return pkt


@dataclass
class SetHealth(Packet):
    """0x55 — Server updates health, food, and saturation."""
    packet_id = 0x55

    health: float = 20.0
    food: int = 20
    food_saturation: float = 5.0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SetHealth":
        pkt = cls()
        pkt.health = buf.read_float()
        pkt.food = buf.read_varint()
        pkt.food_saturation = buf.read_float()
        return pkt


@dataclass
class SystemChatMessage(Packet):
    """0x67 — System / server-sent chat or notification message."""
    packet_id = 0x67

    content: str = ""
    overlay: bool = False

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SystemChatMessage":
        pkt = cls()
        pkt.content = buf.read_string()
        pkt.overlay = buf.read_bool()
        return pkt


@dataclass
class TimeUpdate(Packet):
    """0x5C — World age and time-of-day."""
    packet_id = 0x5C

    world_age: int = 0
    time_of_day: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "TimeUpdate":
        pkt = cls()
        pkt.world_age = buf.read_long()
        pkt.time_of_day = buf.read_long()
        return pkt


@dataclass
class UnloadChunk(Packet):
    """0x1F — Server instructs the client to unload a chunk column."""
    packet_id = 0x1F

    chunk_z: int = 0
    chunk_x: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "UnloadChunk":
        pkt = cls()
        pkt.chunk_z = buf.read_int()
        pkt.chunk_x = buf.read_int()
        return pkt


@dataclass
class Login(Packet):
    """0x2C — Login play packet, sent on entering the Play state."""
    packet_id = 0x2C

    entity_id: int = 0
    is_hardcore: bool = False
    game_mode: int = 0
    previous_game_mode: int = -1
    dimension_count: int = 0
    dimension_name: str = "minecraft:overworld"
    hashed_seed: int = 0
    max_players: int = 20
    view_distance: int = 10
    simulation_distance: int = 10
    reduced_debug_info: bool = False
    enable_respawn_screen: bool = True
    is_debug: bool = False
    is_flat: bool = False
    has_last_death: bool = False
    portal_cooldown: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "Login":
        pkt = cls()
        pkt.entity_id = buf.read_int()
        pkt.is_hardcore = buf.read_bool()
        pkt.game_mode = buf.read_ubyte()
        pkt.previous_game_mode = buf.read_byte()
        # drain remaining — registry codec + dimensions + NBT are complex
        # we only need entity_id and game_mode for client state
        buf.remaining()
        return pkt


@dataclass
class Respawn(Packet):
    """0x47 — Server triggers a respawn or dimension change."""
    packet_id = 0x47

    game_mode: int = 0
    previous_game_mode: int = -1
    is_debug: bool = False
    is_flat: bool = False
    has_last_death: bool = False
    portal_cooldown: int = 0

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "Respawn":
        pkt = cls()
        # Drain — the full packet has dimension codec NBT; we extract
        # game mode from a known offset (byte after dimension name string)
        data = buf.remaining()
        pkt.game_mode = 0   # safe default; accurate parse requires codec
        return pkt


@dataclass
class GameEvent(Packet):
    """0x22 — A game event (rain, game mode change, demo, credits, etc.)."""
    packet_id = 0x22

    event_id: int = 0
    value: float = 0.0

    # Common event IDs
    NO_RESPAWN_BLOCK = 0
    BEGIN_RAINING    = 1
    END_RAINING      = 2
    CHANGE_GAME_MODE = 3
    WIN_GAME         = 4
    DEMO_EVENT       = 5
    ARROW_HIT_PLAYER = 6
    RAIN_LEVEL       = 7
    THUNDER_LEVEL    = 8
    PLAY_PUFFERFISH  = 9
    GUARDIAN_ELDER   = 10
    IMMEDIATE_RESPAWN = 11

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "GameEvent":
        pkt = cls()
        pkt.event_id = buf.read_ubyte()
        pkt.value = buf.read_float()
        return pkt
