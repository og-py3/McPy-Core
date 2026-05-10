"""Title, subtitle, action bar, and animation packets (clientbound play)."""

from __future__ import annotations

from dataclasses import dataclass

from mcpycore.packets.packet import Packet, PacketBuffer


@dataclass
class SetTitleText(Packet):
    """0x5D — Display a title on the player's screen."""
    packet_id = 0x5D

    title_json: str = ""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SetTitleText":
        pkt = cls()
        pkt.title_json = buf.read_string()
        return pkt

    @property
    def text(self) -> str:
        import json
        try:
            data = json.loads(self.title_json)
            if isinstance(data, dict):
                return data.get("text", self.title_json)
            return str(data)
        except Exception:
            return self.title_json


@dataclass
class SetSubtitleText(Packet):
    """0x5B — Display a subtitle below the title."""
    packet_id = 0x5B

    subtitle_json: str = ""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SetSubtitleText":
        pkt = cls()
        pkt.subtitle_json = buf.read_string()
        return pkt

    @property
    def text(self) -> str:
        import json
        try:
            data = json.loads(self.subtitle_json)
            if isinstance(data, dict):
                return data.get("text", self.subtitle_json)
            return str(data)
        except Exception:
            return self.subtitle_json


@dataclass
class SetActionBarText(Packet):
    """0x49 — Display text in the action bar (above hotbar)."""
    packet_id = 0x49

    text_json: str = ""

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SetActionBarText":
        pkt = cls()
        pkt.text_json = buf.read_string()
        return pkt

    @property
    def text(self) -> str:
        import json
        try:
            data = json.loads(self.text_json)
            if isinstance(data, dict):
                return data.get("text", self.text_json)
            return str(data)
        except Exception:
            return self.text_json


@dataclass
class SetTitleAnimationTimes(Packet):
    """0x5E — Set fade-in, stay, fade-out ticks for the title."""
    packet_id = 0x5E

    fade_in: int = 10
    stay: int = 70
    fade_out: int = 20

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "SetTitleAnimationTimes":
        pkt = cls()
        pkt.fade_in  = buf.read_int()
        pkt.stay     = buf.read_int()
        pkt.fade_out = buf.read_int()
        return pkt


@dataclass
class ClearTitles(Packet):
    """0x0F — Clear the current title/subtitle from the screen."""
    packet_id = 0x0F

    reset: bool = False

    @classmethod
    def decode(cls, buf: PacketBuffer) -> "ClearTitles":
        pkt = cls()
        pkt.reset = buf.read_bool()
        return pkt
