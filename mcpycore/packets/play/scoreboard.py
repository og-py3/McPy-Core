"""Scoreboard-related packets (clientbound play)."""

from __future__ import annotations

from dataclasses import dataclass, field

from mcpycore.packets.packet import Packet, PacketBuffer

# UpdateObjective modes
OBJECTIVE_CREATE = 0
OBJECTIVE_REMOVE = 1
OBJECTIVE_UPDATE = 2

# Display slots
DISPLAY_LIST        = 0
DISPLAY_SIDEBAR     = 1
DISPLAY_BELOW_NAME  = 2
# 3–18: sidebar for each team colour

# Score action
SCORE_SET    = 0
SCORE_REMOVE = 1

# UpdateTeams modes
TEAM_CREATE       = 0
TEAM_REMOVE       = 1
TEAM_UPDATE       = 2
TEAM_ADD_PLAYERS  = 3
TEAM_REMOVE_PLAYERS = 4


@dataclass
class UpdateObjectives(Packet):
    """0x56 — Create / update / remove a scoreboard objective."""
    packet_id = 0x56

    objective_name: str = ""
    mode: int = OBJECTIVE_CREATE
    value: str = ""      # display name (JSON text), only for CREATE/UPDATE
    type_: int = 0       # 0=integer, 1=hearts

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "UpdateObjectives":
        pkt = cls()
        pkt.objective_name = buf.read_string()
        pkt.mode = buf.read_byte()
        if pkt.mode in (OBJECTIVE_CREATE, OBJECTIVE_UPDATE):
            pkt.value  = buf.read_string()
            pkt.type_  = buf.read_varint()
        return pkt


@dataclass
class DisplayObjective(Packet):
    """0x54 — Set which objective to display in a given slot."""
    packet_id = 0x54

    position: int = DISPLAY_SIDEBAR
    score_name: str = ""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "DisplayObjective":
        pkt = cls()
        pkt.position   = buf.read_varint()
        pkt.score_name = buf.read_string()
        return pkt


@dataclass
class UpdateScore(Packet):
    """0x59 — Set / update a player's score on an objective."""
    packet_id = 0x59

    entity_name: str = ""
    objective_name: str = ""
    value: int = 0
    display_name: str | None = None
    number_format: int | None = None

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "UpdateScore":
        pkt = cls()
        pkt.entity_name    = buf.read_string()
        pkt.objective_name = buf.read_string()
        pkt.value          = buf.read_varint()
        has_display = buf.read_bool()
        if has_display:
            pkt.display_name = buf.read_string()
        has_format = buf.read_bool()
        if has_format:
            pkt.number_format = buf.read_varint()
        return pkt


@dataclass
class ResetScore(Packet):
    """0x42 — Remove a player's score from an objective."""
    packet_id = 0x42

    entity_name: str = ""
    objective_name: str | None = None

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ResetScore":
        pkt = cls()
        pkt.entity_name = buf.read_string()
        has_obj = buf.read_bool()
        if has_obj:
            pkt.objective_name = buf.read_string()
        return pkt


@dataclass
class UpdateTeams(Packet):
    """0x58 — Create / update / remove a scoreboard team."""
    packet_id = 0x58

    team_name: str = ""
    mode: int = TEAM_CREATE
    display_name: str = ""
    friendly_flags: int = 0
    name_tag_visibility: str = "always"
    collision_rule: str = "always"
    team_color: int = 0
    team_prefix: str = ""
    team_suffix: str = ""
    members: list[str] = field(default_factory=list)

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "UpdateTeams":
        pkt = cls()
        pkt.team_name = buf.read_string()
        pkt.mode = buf.read_byte()

        if pkt.mode in (TEAM_CREATE, TEAM_UPDATE):
            pkt.display_name        = buf.read_string()
            pkt.friendly_flags      = buf.read_byte()
            pkt.name_tag_visibility = buf.read_string()
            pkt.collision_rule      = buf.read_string()
            pkt.team_color          = buf.read_varint()
            pkt.team_prefix         = buf.read_string()
            pkt.team_suffix         = buf.read_string()

        if pkt.mode in (TEAM_CREATE, TEAM_ADD_PLAYERS, TEAM_REMOVE_PLAYERS):
            count = buf.read_varint()
            pkt.members = [buf.read_string() for _ in range(count)]

        return pkt
