"""Decode a real CAMFRAME serial capture; never manufactures a missing image."""
from __future__ import annotations
import argparse
import base64
import json
from pathlib import Path
import re


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload, metadata = decode_capture(args.capture.read_bytes())
    import cv2
    import numpy as np
    yuv = np.frombuffer(payload, dtype=np.uint8).reshape(metadata["height"], metadata["width"], 2)
    mode = cv2.COLOR_YUV2BGR_UYVY if metadata["fourcc"] == "UYVY" else cv2.COLOR_YUV2BGR_YUY2
    bgr = cv2.cvtColor(yuv, mode)
    args.output.mkdir(parents=True, exist_ok=True)
    image_path = args.output / "camera-native.png"
    cv2.imencode(".png", bgr)[1].tofile(str(image_path))
    (args.output / "camera.raw").write_bytes(payload)
    (args.output / "frame-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({"image": str(image_path), **metadata}, ensure_ascii=False))


if __name__ == "__main__":
    main()
