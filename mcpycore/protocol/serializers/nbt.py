"""
NBT (Named Binary Tag) parser and writer.

Supports all 13 tag types defined by the Minecraft NBT spec.
Reference: https://wiki.vg/NBT
"""
from __future__ import annotations

import struct
from typing import Any

from mcpycore.protocol.serializers.buffer import PacketBuffer


# ── Tag type constants ────────────────────────────────────────────────────────

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
    TAG_END:        "TAG_End",
    TAG_BYTE:       "TAG_Byte",
    TAG_SHORT:      "TAG_Short",
    TAG_INT:        "TAG_Int",
    TAG_LONG:       "TAG_Long",
    TAG_FLOAT:      "TAG_Float",
    TAG_DOUBLE:     "TAG_Double",
    TAG_BYTE_ARRAY: "TAG_ByteArray",
    TAG_STRING:     "TAG_String",
    TAG_LIST:       "TAG_List",
    TAG_COMPOUND:   "TAG_Compound",
    TAG_INT_ARRAY:  "TAG_IntArray",
    TAG_LONG_ARRAY: "TAG_LongArray",
}


# ── Tag classes ───────────────────────────────────────────────────────────────

class NBTTag:
    __slots__ = ("name", "value")
    tag_id: int = -1

    def __init__(self, name: str = "", value: Any = None) -> None:
        self.name = name
        self.value = value

    def get(self, key: str, default: Any = None) -> Any:
        if isinstance(self.value, dict):
            tag = self.value.get(key)
            if tag is None:
                return default
            if isinstance(tag, NBTTag):
                return tag.value
            return tag
        return default

    def __repr__(self) -> str:
        name = TAG_NAMES.get(self.tag_id, f"TAG_{self.tag_id}")
        return f"{name}({self.name!r}: {self.value!r})"


class NBTEnd(NBTTag):
    tag_id = TAG_END
    def __init__(self) -> None:
        super().__init__("", None)


class NBTByte(NBTTag):
    tag_id = TAG_BYTE

class NBTShort(NBTTag):
    tag_id = TAG_SHORT

class NBTInt(NBTTag):
    tag_id = TAG_INT

class NBTLong(NBTTag):
    tag_id = TAG_LONG

class NBTFloat(NBTTag):
    tag_id = TAG_FLOAT

class NBTDouble(NBTTag):
    tag_id = TAG_DOUBLE

class NBTString(NBTTag):
    tag_id = TAG_STRING

class NBTByteArray(NBTTag):
    tag_id = TAG_BYTE_ARRAY

class NBTIntArray(NBTTag):
    tag_id = TAG_INT_ARRAY

class NBTLongArray(NBTTag):
    tag_id = TAG_LONG_ARRAY


class NBTList(NBTTag):
    tag_id = TAG_LIST
    def __init__(self, name: str = "", value: list | None = None, elem_type: int = TAG_END) -> None:
        super().__init__(name, value or [])
        self.elem_type = elem_type


class NBTCompound(NBTTag):
    tag_id = TAG_COMPOUND

    def __init__(self, name: str = "", value: dict | None = None) -> None:
        super().__init__(name, value or {})


_TAG_CLASS = {
    TAG_END:        NBTEnd,
    TAG_BYTE:       NBTByte,
    TAG_SHORT:      NBTShort,
    TAG_INT:        NBTInt,
    TAG_LONG:       NBTLong,
    TAG_FLOAT:      NBTFloat,
    TAG_DOUBLE:     NBTDouble,
    TAG_BYTE_ARRAY: NBTByteArray,
    TAG_STRING:     NBTString,
    TAG_LIST:       NBTList,
    TAG_COMPOUND:   NBTCompound,
    TAG_INT_ARRAY:  NBTIntArray,
    TAG_LONG_ARRAY: NBTLongArray,
}


# ── Reader ────────────────────────────────────────────────────────────────────

class NBTReader:
    """Stateful NBT reader backed by raw bytes."""

    def __init__(self, data: bytes) -> None:
        self._d = data
        self._p = 0

    def _u(self, fmt: str, size: int) -> Any:
        val = struct.unpack_from(fmt, self._d, self._p)[0]
        self._p += size
        return val

    def _read_name(self) -> str:
        length = self._u(">H", 2)
        name = self._d[self._p : self._p + length].decode("utf-8")
        self._p += length
        return name

    def _read_payload(self, tag_id: int) -> Any:
        if tag_id == TAG_BYTE:
            return self._u(">b", 1)
        if tag_id == TAG_SHORT:
            return self._u(">h", 2)
        if tag_id == TAG_INT:
            return self._u(">i", 4)
        if tag_id == TAG_LONG:
            return self._u(">q", 8)
        if tag_id == TAG_FLOAT:
            return self._u(">f", 4)
        if tag_id == TAG_DOUBLE:
            return self._u(">d", 8)
        if tag_id == TAG_BYTE_ARRAY:
            n = self._u(">i", 4)
            data = bytes(self._d[self._p : self._p + n])
            self._p += n
            return data
        if tag_id == TAG_STRING:
            n = self._u(">H", 2)
            s = self._d[self._p : self._p + n].decode("utf-8")
            self._p += n
            return s
        if tag_id == TAG_LIST:
            elem_type = self._u(">B", 1)
            count = self._u(">i", 4)
            items = []
            for _ in range(count):
                if elem_type == TAG_END:
                    break
                elem_cls = _TAG_CLASS.get(elem_type, NBTTag)
                elem = elem_cls()
                elem.value = self._read_payload(elem_type)
                items.append(elem)
            # Return the plain list; the outer compound handler wraps it in NBTList
            return items
        if tag_id == TAG_COMPOUND:
            children: dict[str, NBTTag] = {}
            while True:
                child_id = self._u(">B", 1)
                if child_id == TAG_END:
                    break
                child_name = self._read_name()
                cls = _TAG_CLASS.get(child_id)
                if cls is None:
                    raise ValueError(f"Unknown NBT tag ID {child_id}")
                tag = cls(name=child_name)
                tag.value = self._read_payload(child_id)
                children[child_name] = tag
            return children
        if tag_id == TAG_INT_ARRAY:
            n = self._u(">i", 4)
            return [self._u(">i", 4) for _ in range(n)]
        if tag_id == TAG_LONG_ARRAY:
            n = self._u(">i", 4)
            return [self._u(">q", 8) for _ in range(n)]
        raise ValueError(f"Unknown NBT tag ID: {tag_id}")

    def read(self) -> NBTTag:
        """Read one complete named tag from the stream."""
        tag_id = self._u(">B", 1)
        if tag_id == TAG_END:
            return NBTEnd()
        cls = _TAG_CLASS.get(tag_id)
        if cls is None:
            raise ValueError(f"Unknown NBT tag type: {tag_id}")
        name = self._read_name()
        tag = cls(name=name)
        tag.value = self._read_payload(tag_id)
        return tag


# ── Public API ────────────────────────────────────────────────────────────────

def parse_nbt(data: bytes) -> NBTTag:
    """Parse the first NBT tag from *data*."""
    return NBTReader(data).read()


def nbt_to_dict(tag: NBTTag) -> Any:
    """
    Recursively convert an NBT tag tree to plain Python objects.

    Compound → dict, List → list, scalars → int/float/str/bytes.
    """
    if isinstance(tag, NBTCompound):
        return {k: nbt_to_dict(v) for k, v in tag.value.items()}
    if isinstance(tag, NBTList):
        return [nbt_to_dict(item) for item in tag.value]
    if isinstance(tag, NBTEnd):
        return None
    return tag.value
