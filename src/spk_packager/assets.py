from __future__ import annotations

from pathlib import Path
import struct
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def placeholder_png(size: int) -> bytes:
    if size <= 0 or size > 4096:
        raise ValueError("icon size is out of range")
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            slash = abs((x + y) - (size - 1)) <= max(1, size // 24)
            if slash:
                rgba = (224, 151, 32, 255)
            else:
                base = 34 + ((x ^ y) % 10)
                rgba = (base, base, base, 255)
            rows.extend(rgba)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return PNG_SIGNATURE + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + _chunk(b"IEND", b"")


def write_placeholder_icon(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(placeholder_png(size))


def png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise ValueError("not a PNG with an IHDR header")
    return struct.unpack(">II", data[16:24])
