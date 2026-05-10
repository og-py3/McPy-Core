"""
Minimal NBT (Named Binary Tag) reader.

Supports reading the NBT tags used in Minecraft's protocol data
(chunk sections, block entities, entity metadata, etc.).

Reference: https://minecraft.wiki/w/NBT_format
"""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass, field
from typing import Any

# ── Tag type IDs ──────────────────────────────────────────────────────────────
TAG_END        = 0
TAG_BYTE       = 1
TAG_SHORT      = 2
TAG_INT        = 3
TAG_LONG       = 4
TAG_FLOAT      = 5
TAG_DOUBLE     = 6
TAG_BYTE_ARRAY = 7
TAG_STRING     = 8
TAG_LIST       = 9
TAG_COMPOUND   = 10
TAG_INT_ARRAY  = 11
TAG_LONG_ARRAY = 12

TAG_NAMES = {
    0: "TAG_End", 1: "TAG_Byte", 2: "TAG_Short", 3: "TAG_Int",
    4: "TAG_Long", 5: "TAG_Float", 6: "TAG_Double", 7: "TAG_Byte_Array",
    8: "TAG_String", 9: "TAG_List", 10: "TAG_Compound",
    11: "TAG_Int_Array", 12: "TAG_Long_Array",
}


class NBTTag:
    """Base class for all NBT tags."""
    tag_id: int = 0
    name: str = ""
    value: Any = None

    def __repr__(self) -> str:
        return f"{TAG_NAMES.get(self.tag_id, '?')}({self.name!r}: {self.value!r})"


@dataclass
class NBTEnd(NBTTag):
    tag_id: int = TAG_END


@dataclass
class NBTByte(NBTTag):
    tag_id: int = TAG_BYTE
    name: str = ""
    value: int = 0


@dataclass
class NBTShort(NBTTag):
    tag_id: int = TAG_SHORT
    name: str = ""
    value: int = 0


@dataclass
class NBTInt(NBTTag):
    tag_id: int = TAG_INT
    name: str = ""
    value: int = 0


@dataclass
class NBTLong(NBTTag):
    tag_id: int = TAG_LONG
    name: str = ""
    value: int = 0


@dataclass
class NBTFloat(NBTTag):
    tag_id: int = TAG_FLOAT
    name: str = ""
    value: float = 0.0


@dataclass
class NBTDouble(NBTTag):
    tag_id: int = TAG_DOUBLE
    name: str = ""
    value: float = 0.0


@dataclass
class NBTByteArray(NBTTag):
    tag_id: int = TAG_BYTE_ARRAY
    name: str = ""
    value: bytes = b""


@dataclass
class NBTString(NBTTag):
    tag_id: int = TAG_STRING
    name: str = ""
    value: str = ""


@dataclass
class NBTList(NBTTag):
    tag_id: int = TAG_LIST
    name: str = ""
    element_type: int = 0
    value: list = field(default_factory=list)


@dataclass
class NBTCompound(NBTTag):
    tag_id: int = TAG_COMPOUND
    name: str = ""
    value: dict = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        tag = self.value.get(key)
        if tag is None:
            return default
        return tag.value if hasattr(tag, "value") else tag


@dataclass
class NBTIntArray(NBTTag):
    tag_id: int = TAG_INT_ARRAY
    name: str = ""
    value: list = field(default_factory=list)


@dataclass
class NBTLongArray(NBTTag):
    tag_id: int = TAG_LONG_ARRAY
    name: str = ""
    value: list = field(default_factory=list)


# ── Reader ────────────────────────────────────────────────────────────────────

class NBTReader:
    """Read NBT data from a bytes buffer."""

    def __init__(self, data: bytes) -> None:
        self._buf = io.BytesIO(data)

    def read(self) -> NBTTag:
        """Read one top-level NBT tag (typically a TAG_Compound)."""
        return self._read_tag()

    def _read_tag(self, type_id: int | None = None, named: bool = True) -> NBTTag:
        if type_id is None:
            type_id = self._read_ubyte()
        if type_id == TAG_END:
            return NBTEnd()
        name = self._read_string() if named else ""
        return self._read_payload(type_id, name)

    def _read_payload(self, type_id: int, name: str) -> NBTTag:
        if type_id == TAG_BYTE:
            return NBTByte(name=name, value=self._read_byte())
        if type_id == TAG_SHORT:
            return NBTShort(name=name, value=self._read_short())
        if type_id == TAG_INT:
            return NBTInt(name=name, value=self._read_int())
        if type_id == TAG_LONG:
            return NBTLong(name=name, value=self._read_long())
        if type_id == TAG_FLOAT:
            return NBTFloat(name=name, value=self._read_float())
        if type_id == TAG_DOUBLE:
            return NBTDouble(name=name, value=self._read_double())
        if type_id == TAG_BYTE_ARRAY:
            length = self._read_int()
            return NBTByteArray(name=name, value=self._buf.read(length))
        if type_id == TAG_STRING:
            return NBTString(name=name, value=self._read_string())
        if type_id == TAG_LIST:
            element_type = self._read_ubyte()
            count = self._read_int()
            items = [self._read_payload(element_type, "") for _ in range(count)]
            return NBTList(name=name, element_type=element_type, value=items)
        if type_id == TAG_COMPOUND:
            children: dict[str, NBTTag] = {}
            while True:
                child = self._read_tag()
                if child.tag_id == TAG_END:
                    break
                children[child.name] = child
            return NBTCompound(name=name, value=children)
        if type_id == TAG_INT_ARRAY:
            count = self._read_int()
            values = list(struct.unpack(f">{count}i", self._buf.read(4 * count)))
            return NBTIntArray(name=name, value=values)
        if type_id == TAG_LONG_ARRAY:
            count = self._read_int()
            values = list(struct.unpack(f">{count}q", self._buf.read(8 * count)))
            return NBTLongArray(name=name, value=values)
        raise ValueError(f"Unknown NBT tag type: {type_id}")

    def _read_ubyte(self) -> int:
        return self._buf.read(1)[0]

    def _read_byte(self) -> int:
        return struct.unpack(">b", self._buf.read(1))[0]

    def _read_short(self) -> int:
        return struct.unpack(">h", self._buf.read(2))[0]

    def _read_ushort(self) -> int:
        return struct.unpack(">H", self._buf.read(2))[0]

    def _read_int(self) -> int:
        return struct.unpack(">i", self._buf.read(4))[0]

    def _read_long(self) -> int:
        return struct.unpack(">q", self._buf.read(8))[0]

    def _read_float(self) -> float:
        return struct.unpack(">f", self._buf.read(4))[0]

    def _read_double(self) -> float:
        return struct.unpack(">d", self._buf.read(8))[0]

    def _read_string(self) -> str:
        length = self._read_ushort()
        return self._buf.read(length).decode("utf-8")


def parse_nbt(data: bytes) -> NBTTag:
    """Parse NBT from raw bytes and return the root tag."""
    return NBTReader(data).read()


def nbt_to_dict(tag: NBTTag) -> Any:
    """Recursively convert NBT tags to plain Python objects."""
    if isinstance(tag, NBTCompound):
        return {k: nbt_to_dict(v) for k, v in tag.value.items()}
    if isinstance(tag, NBTList):
        return [nbt_to_dict(v) for v in tag.value]
    if isinstance(tag, (NBTIntArray, NBTLongArray, NBTByteArray)):
        return tag.value
    if hasattr(tag, "value"):
        return tag.value
    return None
