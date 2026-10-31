"""Decode a real CAMFRAME serial capture; never manufactures a missing image."""
from __future__ import annotations
import argparse
import base64
import json
from pathlib import Path
import re
import struct
import zlib


def fnv1a(data: bytes) -> int:
    value = 2166136261
    for byte in data:
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value


def decode_capture(raw: bytes):
    header = re.search(rb"CAMFRAME_BEGIN w=(\d+) h=(\d+) fourcc=([0-9a-fA-F]+) bytes=(\d+) fnv1a=([0-9a-fA-F]+)", raw)
    if not header:
        raise ValueError("No real camera frame header in serial capture")
    ending = raw.find(b"CAMFRAME_END", header.end())
    if ending < 0:
        raise ValueError("Frame is incomplete: end marker absent")
    width, height = int(header[1]), int(header[2])
    expected_bytes, expected_hash = int(header[4]), int(header[5], 16)
    if width <= 0 or height <= 0 or width % 2 or expected_bytes != width * height * 2:
        raise ValueError("Unexpected YUV422 frame dimensions/length")
    chunks = re.findall(rb"CAMDATA:([A-Za-z0-9+/=]+)", raw[header.end():ending])
    payload = b"".join(base64.b64decode(chunk, validate=True) for chunk in chunks)
    if len(payload) != expected_bytes or fnv1a(payload) != expected_hash:
        raise ValueError("Frame length/checksum mismatch; no image accepted")
    fourcc = int(header[3], 16).to_bytes(4, "little").decode("ascii")
    if fourcc not in ("UYVY", "YUYV"):
        raise ValueError(f"Unsupported actual camera format: {fourcc!r}")
    return payload, {"width": width, "height": height, "fourcc": fourcc,
                     "bytes": len(payload), "fnv1a": f"{expected_hash:08x}",
                     "source": "real_camera_serial_capture"}


def frame_png(payload: bytes, metadata: dict) -> bytes:
    """Native-size RGB PNG, BT.601 limited-range YUV422; no extra packages."""
    width, height = metadata["width"], metadata["height"]
    rows = bytearray()
    for row in range(height):
        rows.append(0)  # PNG filter: none
        for offset in range(row * width * 2, (row + 1) * width * 2, 4):
            a, b, c, d = payload[offset:offset + 4]
            u, y0, v, y1 = (a, b, c, d) if metadata["fourcc"] == "UYVY" else (b, a, d, c)
            for y in (y0, y1):
                luminance = 298 * max(0, y - 16)
                for value in (luminance + 409 * (v - 128),
                              luminance - 100 * (u - 128) - 208 * (v - 128),
                              luminance + 516 * (u - 128)):
                    rows.append(max(0, min(255, (value + 128) >> 8)))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def save_capture(raw: bytes, output: Path) -> dict:
    payload, metadata = decode_capture(raw)
    png = frame_png(payload, metadata)
    output.mkdir(parents=True, exist_ok=True)
    image_path = output / "camera-native.png"
    image_path.write_bytes(png)
    (output / "camera.raw").write_bytes(payload)
    (output / "frame-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {"image": str(image_path), **metadata}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(save_capture(args.capture.read_bytes(), args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
