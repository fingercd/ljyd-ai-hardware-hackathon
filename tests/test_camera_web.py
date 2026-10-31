import http.client
import json
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from scripts import camera_web


class CameraWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), camera_web.Handler)
        cls.server.camera_port = None
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()

    def request(self, method, path, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def headers(self):
        return {'Origin': f'http://127.0.0.1:{self.server.server_port}',
                'X-Camera-Token': camera_web.TOKEN}

    def test_page_and_unauthorized_capture(self):
        self.assertIn('摄像头工作台'.encode(), self.request('GET', '/')[1])
        self.assertEqual(self.request('POST', '/capture')[0], 403)
        headers = self.headers()
        headers['Origin'] = 'https://example.com'
        self.assertEqual(self.request('POST', '/capture', headers)[0], 403)

    def test_success_and_failure_do_not_fabricate(self):
        with patch.object(camera_web, 'capture', return_value=b'actual-image'):
            self.assertEqual(self.request('POST', '/capture', self.headers()), (200, b'actual-image'))
        with patch.object(camera_web, 'capture', side_effect=ValueError('board absent')):
            status, body = self.request('POST', '/capture', self.headers())
            self.assertEqual(status, 503)
            self.assertIn(b'board absent', body)

    def test_device_status_without_opening_serial(self):
        with patch('serial.tools.list_ports.comports', return_value=[]):
            status, body = self.request('GET', '/devices')
            self.assertEqual(status, 200)
            self.assertFalse(json.loads(body)['ready'])
            self.assertIn('USB', json.loads(body)['message'])

    def test_device_status_matches_only_board_and_requires_unique_port(self):
        targets = [SimpleNamespace(device=name, vid=0x1A86, pid=0x55D3,
                                   description='CH343') for name in ('COM3', 'COM4')]
        bluetooth = SimpleNamespace(device='COM5', vid=None, pid=None,
                                    description='Bluetooth')
        with patch('serial.tools.list_ports.comports', return_value=[targets[0], bluetooth]):
            state = camera_web.device_status()
            self.assertTrue(state['ready'])
            self.assertEqual([p['device'] for p in state['ports']], ['COM3'])
        with patch('serial.tools.list_ports.comports', return_value=targets):
            self.assertFalse(camera_web.device_status()['ready'])
            self.assertTrue(camera_web.device_status('COM4')['ready'])
            self.assertFalse(camera_web.device_status('COM5')['ready'])

    def test_busy(self):
        with camera_web.LOCK:
            self.assertEqual(self.request('POST', '/capture', self.headers())[0], 409)


if __name__ == '__main__':
    unittest.main()
