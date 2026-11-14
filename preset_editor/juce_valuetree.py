"""
Pure Python implementation of the JUCE ValueTree binary format.

Based directly on the JUCE C++ framework source code:
- modules/juce_core/streams/juce_InputStream.cpp
- modules/juce_core/streams/juce_OutputStream.cpp
- modules/juce_core/containers/juce_Variant.cpp
- modules/juce_data_structures/values/juce_ValueTree.cpp
"""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple, Union


class VarMarker(IntEnum):
    INT = 1
    BOOL_TRUE = 2
    BOOL_FALSE = 3
    DOUBLE = 4
    STRING = 5
    INT64 = 6
    ARRAY = 7
    BINARY = 8
    UNDEFINED = 9


@dataclass
class JuceVar:
    """Represents a typed JUCE variant (juce::var)."""
    marker: VarMarker
    value: Any

    @classmethod
    def void(cls) -> "JuceVar":
        return cls(marker=VarMarker.UNDEFINED, value=None)

    @classmethod
    def from_python(cls, val: Any) -> "JuceVar":
        if isinstance(val, JuceVar):
            return val
        if val is None:
            return cls.void()
        if isinstance(val, bool):
            return cls(marker=VarMarker.BOOL_TRUE if val else VarMarker.BOOL_FALSE, value=val)
        if isinstance(val, int):
            if -0x80000000 <= val <= 0x7FFFFFFF:
                return cls(marker=VarMarker.INT, value=val)
            return cls(marker=VarMarker.INT64, value=val)
        if isinstance(val, float):
            return cls(marker=VarMarker.DOUBLE, value=val)
        if isinstance(val, str):
            return cls(marker=VarMarker.STRING, value=val)
        if isinstance(val, (bytes, bytearray)):
            return cls(marker=VarMarker.BINARY, value=bytes(val))
        if isinstance(val, list):
            return cls(marker=VarMarker.ARRAY, value=[cls.from_python(item) for item in val])
        raise TypeError(f"Unsupported python value for JuceVar: {type(val)} ({val})")

    def to_serializable(self) -> Any:
        """Converts to a JSON-serializable representation."""
        if self.marker in (VarMarker.BOOL_TRUE, VarMarker.BOOL_FALSE):
            return bool(self.value)
        if self.marker == VarMarker.BINARY:
            return {"__bytes__": self.value.hex()}
        if self.marker == VarMarker.ARRAY:
            return [item.to_serializable() if isinstance(item, JuceVar) else item for item in self.value]
        return self.value


class JuceInputStream:
    """Stream reader implementing JUCE InputStream binary conventions."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    @property
    def remaining(self) -> int:
        return len(self.data) - self.pos

    def read_byte(self) -> int:
        if self.pos >= len(self.data):
            return 0
        b = self.data[self.pos]
        self.pos += 1
        return b

    def read_bytes(self, num_bytes: int) -> bytes:
        chunk = self.data[self.pos : self.pos + num_bytes]
        self.pos += len(chunk)
        return chunk

    def read_string(self) -> str:
        """Reads a null-terminated UTF-8 string."""
        start = self.pos
        null_idx = self.data.find(b"\x00", start)
        if null_idx == -1:
            self.pos = len(self.data)
            return self.data[start:].decode("utf-8", errors="replace")
        self.pos = null_idx + 1
        return self.data[start:null_idx].decode("utf-8", errors="replace")

    def read_compressed_int(self) -> int:
        """
        Reads a variable-length compressed integer as implemented in
        InputStream::readCompressedInt().
        """
        size_byte = self.read_byte()
        if size_byte == 0:
            return 0

        num_bytes = size_byte & 0x7F
        if num_bytes > 4:
            raise ValueError(f"Corrupt stream: compressed int length {num_bytes} > 4")

        raw = self.read_bytes(num_bytes)
        if len(raw) < num_bytes:
            raise EOFError("Unexpected EOF while reading compressed integer bytes")

        num = int.from_bytes(raw, "little", signed=False)
        return -num if (size_byte & 0x80) else num

    def read_int32(self) -> int:
        raw = self.read_bytes(4)
        if len(raw) < 4:
            raise EOFError("Unexpected EOF reading int32")
        return struct.unpack("<i", raw)[0]

    def read_int64(self) -> int:
        raw = self.read_bytes(8)
        if len(raw) < 8:
            raise EOFError("Unexpected EOF reading int64")
        return struct.unpack("<q", raw)[0]

    def read_double(self) -> float:
        raw = self.read_bytes(8)
        if len(raw) < 8:
            raise EOFError("Unexpected EOF reading double")
        return struct.unpack("<d", raw)[0]


class JuceOutputStream:
    """Stream writer implementing JUCE OutputStream binary conventions."""

    def __init__(self):
        self.buf = bytearray()

    def write_byte(self, byte_val: int) -> None:
        self.buf.append(byte_val & 0xFF)

    def write_bytes(self, data: bytes) -> None:
        self.buf.extend(data)

    def write_string(self, text: str) -> None:
        """Writes a null-terminated UTF-8 string."""
        self.buf.extend(text.encode("utf-8") + b"\x00")

    def write_compressed_int(self, value: int) -> None:
        """
        Writes a variable-length compressed integer as implemented in
        OutputStream::writeCompressedInt().
        """
        if value == 0:
            self.write_byte(0)
            return

        un = -value if value < 0 else value
        bytes_data = bytearray()
        while un > 0:
            bytes_data.append(un & 0xFF)
            un >>= 8

        num_bytes = len(bytes_data)
        header = num_bytes
        if value < 0:
            header |= 0x80

        self.write_byte(header)
        self.write_bytes(bytes_data)

    def write_int32(self, val: int) -> None:
        self.write_bytes(struct.pack("<i", val))

    def write_int64(self, val: int) -> None:
        self.write_bytes(struct.pack("<q", val))

    def write_double(self, val: float) -> None:
        self.write_bytes(struct.pack("<d", val))

    def get_bytes(self) -> bytes:
        return bytes(self.buf)


def read_juce_var(stream: JuceInputStream) -> Optional[JuceVar]:
    """Reads a juce::var from stream according to var::readFromStream()."""
    num_bytes = stream.read_compressed_int()
    if num_bytes <= 0:
        return None

    marker_val = stream.read_byte()
    try:
        marker = VarMarker(marker_val)
    except ValueError:
        # Unknown marker, skip payload
        payload = stream.read_bytes(num_bytes - 1)
        return JuceVar(marker=VarMarker.UNDEFINED, value=payload)

    if marker == VarMarker.INT:
        return JuceVar(marker, stream.read_int32())
    if marker == VarMarker.BOOL_TRUE:
        return JuceVar(marker, True)
    if marker == VarMarker.BOOL_FALSE:
        return JuceVar(marker, False)
    if marker == VarMarker.DOUBLE:
        return JuceVar(marker, stream.read_double())
    if marker == VarMarker.STRING:
        # String is stored as UTF-8 bytes including trailing null terminator
        raw = stream.read_bytes(num_bytes - 1)
        if raw.endswith(b"\x00"):
            raw = raw[:-1]
        return JuceVar(marker, raw.decode("utf-8", errors="replace"))
    if marker == VarMarker.INT64:
        return JuceVar(marker, stream.read_int64())
    if marker == VarMarker.ARRAY:
        # Array payload is preceded by compressed count of items
        count = stream.read_compressed_int()
        items = [read_juce_var(stream) for _ in range(count)]
        return JuceVar(marker, items)
    if marker == VarMarker.BINARY:
        return JuceVar(marker, stream.read_bytes(num_bytes - 1))
    if marker == VarMarker.UNDEFINED:
        return JuceVar(marker, None)

    # Fallback
    stream.read_bytes(num_bytes - 1)
    return JuceVar(marker, None)


def write_juce_var(stream: JuceOutputStream, var: Optional[JuceVar]) -> None:
    """Writes a juce::var to stream according to var::writeToStream()."""
    if var is None:
        stream.write_compressed_int(0)
        return

    m = var.marker
    if m == VarMarker.INT:
        stream.write_compressed_int(5)
        stream.write_byte(VarMarker.INT)
        stream.write_int32(int(var.value))
    elif m in (VarMarker.BOOL_TRUE, VarMarker.BOOL_FALSE):
        stream.write_compressed_int(1)
        stream.write_byte(VarMarker.BOOL_TRUE if var.value else VarMarker.BOOL_FALSE)
    elif m == VarMarker.DOUBLE:
        stream.write_compressed_int(9)
        stream.write_byte(VarMarker.DOUBLE)
        stream.write_double(float(var.value))
    elif m == VarMarker.STRING:
        raw = str(var.value).encode("utf-8") + b"\x00"
        stream.write_compressed_int(len(raw) + 1)
        stream.write_byte(VarMarker.STRING)
        stream.write_bytes(raw)
    elif m == VarMarker.INT64:
        stream.write_compressed_int(9)
        stream.write_byte(VarMarker.INT64)
        stream.write_int64(int(var.value))
    elif m == VarMarker.ARRAY:
        sub = JuceOutputStream()
        items = var.value or []
        sub.write_compressed_int(len(items))
        for item in items:
            write_juce_var(sub, item if isinstance(item, JuceVar) else JuceVar.from_python(item))
        arr_data = sub.get_bytes()
        stream.write_compressed_int(1 + len(arr_data))
        stream.write_byte(VarMarker.ARRAY)
        stream.write_bytes(arr_data)
    elif m == VarMarker.BINARY:
        data = bytes(var.value or b"")
        stream.write_compressed_int(1 + len(data))
        stream.write_byte(VarMarker.BINARY)
        stream.write_bytes(data)
    elif m == VarMarker.UNDEFINED:
        stream.write_compressed_int(1)
        stream.write_byte(VarMarker.UNDEFINED)
    else:
        stream.write_compressed_int(0)


@dataclass
class ValueTreeNode:
    """Represents a node in a JUCE ValueTree."""
    tag: str
    properties: List[Tuple[str, Optional[JuceVar]]] = field(default_factory=list)
    children: List["ValueTreeNode"] = field(default_factory=list)

    def get_property_var(self, name: str) -> Optional[JuceVar]:
        for k, v in self.properties:
            if k == name:
                return v
        return None

    def get_property(self, name: str, default: Any = None) -> Any:
        v = self.get_property_var(name)
        if v is None:
            return default
        return v.value

    def set_property(self, name: str, value: Any, marker: Optional[VarMarker] = None) -> None:
        """Sets or replaces a property on this node."""
        if marker is not None:
            new_var = JuceVar(marker=marker, value=value)
        else:
            # Preserve existing marker if present
            existing = self.get_property_var(name)
            if existing is not None:
                # If existing is string, format value as string
                if existing.marker == VarMarker.STRING:
                    str_val = "true" if value is True else ("false" if value is False else str(value))
                    new_var = JuceVar(marker=VarMarker.STRING, value=str_val)
                elif existing.marker in (VarMarker.BOOL_TRUE, VarMarker.BOOL_FALSE):
                    new_var = JuceVar(marker=VarMarker.BOOL_TRUE if value else VarMarker.BOOL_FALSE, value=bool(value))
                elif existing.marker == VarMarker.DOUBLE:
                    new_var = JuceVar(marker=VarMarker.DOUBLE, value=float(value))
                elif existing.marker in (VarMarker.INT, VarMarker.INT64):
                    new_var = JuceVar(marker=existing.marker, value=int(value))
                else:
                    new_var = JuceVar.from_python(value)
            else:
                new_var = JuceVar.from_python(value)

        for i, (k, _) in enumerate(self.properties):
            if k == name:
                self.properties[i] = (name, new_var)
                return
        self.properties.append((name, new_var))

    def delete_property(self, name: str) -> bool:
        for i, (k, _) in enumerate(self.properties):
            if k == name:
                del self.properties[i]
                return True
        return False

    def find_child(self, tag: str) -> Optional["ValueTreeNode"]:
        for child in self.children:
            if child.tag == tag:
                return child
        return None

    def find_all_children(self, tag: str) -> List["ValueTreeNode"]:
        return [c for c in self.children if c.tag == tag]

    def to_dict(self) -> Dict[str, Any]:
        """Converts node to a clean dictionary representation."""
        props = {}
        for k, v in self.properties:
            props[k] = v.to_serializable() if v is not None else None
        return {
            "tag": self.tag,
            "properties": props,
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValueTreeNode":
        tag = data.get("tag", "")
        props_data = data.get("properties", {})
        properties = []
        for k, v in props_data.items():
            if k == "isFavorite":
                var = JuceVar(marker=VarMarker.BOOL_TRUE if v else VarMarker.BOOL_FALSE, value=bool(v))
            elif isinstance(v, bool):
                var = JuceVar(marker=VarMarker.STRING, value="true" if v else "false")
            elif isinstance(v, (int, float)):
                var = JuceVar(marker=VarMarker.STRING, value=str(v))
            else:
                var = JuceVar.from_python(v)
            properties.append((k, var))
        children = [cls.from_dict(c) for c in data.get("children", [])]
        return cls(tag=tag, properties=properties, children=children)


def read_value_tree(stream_or_bytes: Union[JuceInputStream, bytes]) -> Optional[ValueTreeNode]:
    """Deserializes a JUCE ValueTree from binary data or input stream."""
    stream = stream_or_bytes if isinstance(stream_or_bytes, JuceInputStream) else JuceInputStream(stream_or_bytes)
    tag = stream.read_string()
    if not tag:
        return None

    num_props = stream.read_compressed_int()
    properties: List[Tuple[str, Optional[JuceVar]]] = []
    for _ in range(num_props):
        prop_name = stream.read_string()
        prop_val = read_juce_var(stream)
        properties.append((prop_name, prop_val))

    num_children = stream.read_compressed_int()
    children: List[ValueTreeNode] = []
    for _ in range(num_children):
        child = read_value_tree(stream)
        if child is not None:
            children.append(child)

    return ValueTreeNode(tag=tag, properties=properties, children=children)


def write_value_tree(node: Optional[ValueTreeNode], stream: Optional[JuceOutputStream] = None) -> bytes:
    """Serializes a JUCE ValueTree to binary data."""
    is_root = stream is None
    if stream is None:
        stream = JuceOutputStream()

    if node is None:
        stream.write_string("")
        stream.write_compressed_int(0)
        stream.write_compressed_int(0)
    else:
        stream.write_string(node.tag)
        stream.write_compressed_int(len(node.properties))
        for name, var in node.properties:
            stream.write_string(name)
            write_juce_var(stream, var)
        stream.write_compressed_int(len(node.children))
        for child in node.children:
            write_value_tree(child, stream)

    return stream.get_bytes() if is_root else b""
