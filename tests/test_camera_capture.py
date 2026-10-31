import base64
import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.camera_capture import receive_frame, select_port
from scripts.camera_frame_decode import decode_capture, fnv1a, frame_png
import struct
import zlib


class CameraCommandTests(unittest.TestCase):
    def test_unique_target_selected_not_bluetooth(self):
        ports = [SimpleNamespace(device="COM3", vid=0x1A86, pid=0x55D3),
                 SimpleNamespace(device="COM5", vid=None, pid=None)]
        self.assertEqual(select_port(ports), "COM3")
        with self.assertRaises(ValueError):
            select_port(ports, "COM5")

    def test_ambiguous_target_requires_port(self):
        ports = [SimpleNamespace(device=name, vid=0x1A86, pid=0x55D3) for name in ("COM3", "COM4")]
        with self.assertRaises(ValueError):
            select_port(ports)
        self.assertEqual(select_port(ports, "com4"), "COM4")

    @patch("scripts.camera_capture.time.sleep")
    def test_single_reset_and_capture(self, sleep):
        class Stream:
            def reset_input_buffer(self):
                self.cleared = True

            def read(self, size):
                return b"CAMFRAME_END\n"

        stream, log = Stream(), io.BytesIO()
        self.assertEqual(receive_frame(stream, log), b"CAMFRAME_END\n")
        self.assertTrue(stream.cleared)
        self.assertFalse(stream.rts)
        sleep.assert_called_once_with(0.1)
        self.assertEqual(log.getvalue(), b"CAMFRAME_END\n")
        with self.assertRaises(ValueError):
            decode_capture(log.getvalue())  # A bare marker is not an accepted photo.

    @patch("scripts.camera_capture.time.sleep")
    def test_timeout_does_not_retry(self, sleep):
        stream = SimpleNamespace(reset_input_buffer=lambda: None)
        with self.assertRaises(TimeoutError):
            receive_frame(stream, io.BytesIO(), timeout=0)
        self.assertFalse(stream.rts)
        sleep.assert_called_once_with(0.1)

    def test_png_native_black_and_white_both_formats(self):
        for fourcc, payload in (("UYVY", bytes([128, 16, 128, 235])),
                                ("YUYV", bytes([16, 128, 235, 128]))):
            code = int.from_bytes(fourcc.encode(), "little")
            capture = (f"CAMFRAME_BEGIN w=2 h=1 fourcc={code:08x} bytes=4 fnv1a={fnv1a(payload):08x}\n".encode()
                       + b"CAMDATA:" + base64.b64encode(payload) + b"\nCAMFRAME_END\n")
            data, metadata = decode_capture(capture)
            png = frame_png(data, metadata)
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", png[16:24]), (2, 1))
            length = struct.unpack(">I", png[33:37])[0]
            self.assertEqual(png[37:41], b"IDAT")
            self.assertEqual(zlib.decompress(png[41:41 + length]), b"\x00\x00\x00\x00\xff\xff\xff")


if __name__ == "__main__":
    unittest.main()
