import base64
import unittest
from scripts.camera_frame_decode import decode_capture, fnv1a


class CameraFrameProtocolTests(unittest.TestCase):
    def make_capture(self):
        payload = bytes([128, 80, 128, 80])
        header = f'CAMFRAME_BEGIN w=2 h=1 fourcc=59565955 bytes=4 fnv1a={fnv1a(payload):08x}\n'
        return header.encode() + b'CAMDATA:' + base64.b64encode(payload) + b'\nCAMFRAME_END\n'

    def test_valid_payload(self):
        data, metadata = decode_capture(self.make_capture())
        self.assertEqual(data, bytes([128, 80, 128, 80]))
        self.assertEqual(metadata['fourcc'], 'UYVY')

    def test_no_header(self):
        with self.assertRaises(ValueError):
            decode_capture(b'normal boot log only')

    def test_no_end(self):
        with self.assertRaises(ValueError):
            decode_capture(self.make_capture().replace(b'CAMFRAME_END', b'incomplete'))

    def test_length_mismatch(self):
        with self.assertRaises(ValueError):
            decode_capture(self.make_capture().replace(b'bytes=4', b'bytes=5'))

    def test_checksum_mismatch(self):
        raw = self.make_capture()
        start = raw.index(b'fnv1a=') + len(b'fnv1a=')
        with self.assertRaises(ValueError):
            decode_capture(raw[:start] + b'00000000' + raw[start+8:])


if __name__ == '__main__':
    unittest.main()
