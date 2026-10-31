"""One photo from the existing camera-only firmware; never flashes a device."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time

from scripts.camera_frame_decode import save_capture

ROOT = Path(__file__).resolve().parents[1]
TARGET_USB = (0x1A86, 0x55D3)


def select_port(ports, requested=None):
    matches = [port for port in ports if (port.vid, port.pid) == TARGET_USB
               and (requested is None or port.device.lower() == requested.lower())]
    if len(matches) != 1:
        raise ValueError("Expected exactly one matching CH343 board (1A86:55D3). "
                         "Run --list and specify --port COMx; Bluetooth ports are not this board.")
    return matches[0].device


def receive_frame(stream, log, timeout=180.0):
    """Receiver is already open before one ordinary RTS reset; no BOOT pulse."""
    stream.reset_input_buffer()
    stream.rts = True
    try:
        time.sleep(0.1)
    finally:
        stream.rts = False
    deadline = time.monotonic() + timeout
    raw = bytearray()
    while time.monotonic() < deadline:
        data = stream.read(4096)
        if not data:
            continue
        log.write(data)
        log.flush()
        raw.extend(data)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("Unexpected serial volume; stopped without accepting an image.")
        if b"CAMFRAME_END" in raw:
            return bytes(raw)
        if b"CAMDIAG_STOP" in raw:
            raise ValueError("Camera diagnostic stopped without a complete frame; inspect the local log.")
    raise TimeoutError(f"No complete camera frame within {timeout:g} seconds. "
                       "Check the cable, camera wiring and installed camera diagnostic firmware. "
                       "No automatic retry or flash was performed.")


def main():
    parser = argparse.ArgumentParser(description="拍摄一张 BF3901 照片；普通复位一次，不烧录、不擦除。")
    parser.add_argument("--port", help="目标板串口，例如 COM3；默认自动匹配唯一 CH343")
    parser.add_argument("--list", action="store_true", help="只列出串口，不打开、不复位")
    args = parser.parse_args()

    import serial
    from serial.tools import list_ports

    ports = list(list_ports.comports())
    if args.list:
        for port in ports:
            usb = f"{port.vid:04X}:{port.pid:04X}" if port.vid is not None and port.pid is not None else "-"
            print(f"{port.device}\t{usb}\t{port.description}")
        return 0

    stream = serial.Serial()
    try:
        port = select_port(ports, args.port)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        output = ROOT / "artifacts" / f"camera-photo-{stamp}"
        log_path = ROOT / "logs" / f"camera-photo-{stamp}.bin"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        stream.port, stream.baudrate, stream.timeout = port, 115200, 0.2
        stream.bytesize, stream.parity, stream.stopbits = serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE
        stream.xonxoff, stream.rtscts, stream.dsrdtr = False, False, False
        stream.dtr, stream.rts = False, False
        print(f"{port}: 接收器就绪后将普通复位一次。请保持镜头稳定，等待约几十秒。", flush=True)
        stream.open()
        with log_path.open("xb") as log:
            raw = receive_frame(stream, log)
        result = save_capture(raw, output)
        print("拍照成功：完整帧和校验通过。")
        print(json.dumps({**result, "serial_log": str(log_path)}, ensure_ascii=False, indent=2))
        return 0
    except (serial.SerialException, OSError, ValueError) as error:
        print(f"拍照失败：{error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("已取消接收，串口将关闭。相机可能仍会完成本次单帧输出。", file=sys.stderr)
        return 130
    finally:
        stream.close()


if __name__ == "__main__":
    sys.exit(main())
