"""Local web interface for the existing single-frame camera diagnostic firmware."""
from __future__ import annotations

import argparse
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import threading
import webbrowser

from scripts.camera_capture import receive_frame, select_port
from scripts.camera_frame_decode import decode_capture, frame_png

PAGE = Path(__file__).with_name('camera_web.html')
LOCK = threading.Lock()
TOKEN = secrets.token_urlsafe(32)


def capture(port_name):
    import serial
    from serial.tools import list_ports
    port = select_port(list(list_ports.comports()), port_name)
    stream = serial.Serial()
    stream.port, stream.baudrate, stream.timeout = port, 115200, 0.2
    stream.dtr, stream.rts = False, False
    try:
        stream.open()
        raw = receive_frame(stream, io.BytesIO())
        payload, metadata = decode_capture(raw)
        return frame_png(payload, metadata)
    finally:
        stream.close()


class Handler(BaseHTTPRequestHandler):
    def send_data(self, status, data, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != '/':
            self.send_error(404)
            return
        self.send_data(200, PAGE.read_bytes(), 'text/html; charset=utf-8')

    def do_POST(self):
        expected_origin = f'http://127.0.0.1:{self.server.server_port}'
        if (self.path != '/capture' or self.headers.get('Origin') != expected_origin
                or not secrets.compare_digest(self.headers.get('X-Camera-Token', ''), TOKEN)):
            self.send_error(403)
            return
        if not LOCK.acquire(blocking=False):
            self.send_data(409, '相机正在采集，请等待完成。'.encode(), 'text/plain; charset=utf-8')
            return
        try:
            try:
                data = capture(self.server.camera_port)
            except Exception as exc:
                self.send_data(503, f'采集失败：{exc}'.encode('utf-8'), 'text/plain; charset=utf-8')
                return
            self.send_data(200, data, 'image/png')
        finally:
            LOCK.release()

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description='本机 BF3901 网页拍照和低帧率录像')
    parser.add_argument('--port', help='开发板串口，例如 COM3；默认自动选择')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.camera_port = args.port
    url = f'http://127.0.0.1:{server.server_port}/#{TOKEN}'
    print('网页仅在本机访问。停止服务请在此窗口按 Ctrl+C。', flush=True)
    print('每次采集将普通复位开发板一次；录像为低帧率，无声音。', flush=True)
    print(f'如果浏览器没有自动打开，请访问：{url}', flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止。')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
