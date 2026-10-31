"""Local web interface for the existing single-frame camera diagnostic firmware."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import threading
import webbrowser

from scripts.camera_capture import TARGET_USB, receive_frame, select_port
from scripts.camera_frame_decode import decode_capture, frame_png

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(__file__).with_name('camera_web.html')
LOCK = threading.Lock()
TOKEN = secrets.token_urlsafe(32)


def device_status(port_name=None):
    from serial.tools import list_ports
    ports = list(list_ports.comports())
    targets = [p for p in ports if (p.vid, p.pid) == TARGET_USB]
    try:
        selected = select_port(ports, port_name)
    except ValueError:
        if not targets:
            message = '未检测到 CH343 开发板串口。请检查主板 USB 数据线和接口；亮灯不代表数据已连接。'
        else:
            message = '目标串口不唯一或指定端口不匹配，请在启动命令后加 --port COMx。'
        ready = False
    else:
        message = f'已检测到 {selected} 开发板；尚未打开串口。'
        ready = True
    return {'ports': [{'device': p.device, 'description': p.description} for p in targets],
            'ready': ready, 'message': message}


class Camera:
    def __init__(self, port_name=None):
        self.port_name = port_name
        self.stream = None
        self.error = ''

    def status(self):
        state = device_status(self.port_name)
        opened = (self.stream is not None and self.stream.is_open
                  and any(p['device'] == self.stream.port for p in state['ports']))
        detected = state['ready']
        state['ready'] = detected and opened
        state['opened'] = opened
        if opened:
            state['message'] = f'{self.stream.port} 串口已打开（115200），可以拍照。'
        elif self.error:
            state['message'] = self.error
        elif detected:
            state['message'] = '串口未连接，请点击“重新连接串口”。'
        return state

    def connect(self):
        import serial
        from serial.tools import list_ports
        try:
            port = select_port(list(list_ports.comports()), self.port_name)
            self.close()
            stream = serial.Serial()
            stream.port, stream.baudrate, stream.timeout = port, 115200, 0.2
            stream.dtr, stream.rts = False, False
            self.stream = stream
            stream.open()
            self.error = ''
        except (serial.SerialException, OSError, ValueError) as exc:
            self.close()
            self.error = f'打开串口失败：{exc}'
        return self.status()

    def capture(self):
        import serial
        if not self.status()['ready']:
            if not self.connect()['ready']:
                raise ValueError(self.error)
        log_path = ROOT / 'logs' / f'camera-web-{datetime.now():%Y%m%d-%H%M%S-%f}.bin'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with log_path.open('xb') as log:
                raw = receive_frame(self.stream, log)
            payload, metadata = decode_capture(raw)
            self.error = ''
            return frame_png(payload, metadata)
        except (serial.SerialException, OSError):
            self.close()
            raise
        except (ValueError, TimeoutError) as exc:
            lines = log_path.read_bytes().decode('utf-8', errors='replace').splitlines()
            diagnostic = '; '.join(line for line in lines if 'CAMDIAG_ERROR' in line)
            self.error = f"{diagnostic or str(exc)}；原始日志：{log_path}"
            raise ValueError(self.error) from exc

    def close(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None


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
        if self.path == '/devices':
            data = json.dumps(self.server.camera.status(), ensure_ascii=False).encode('utf-8')
            self.send_data(200, data, 'application/json; charset=utf-8')
            return
        if self.path != '/':
            self.send_error(404)
            return
        self.send_data(200, PAGE.read_bytes(), 'text/html; charset=utf-8')

    def do_POST(self):
        expected_origin = f'http://127.0.0.1:{self.server.server_port}'
        if (self.path not in ('/capture', '/connect') or self.headers.get('Origin') != expected_origin
                or not secrets.compare_digest(self.headers.get('X-Camera-Token', ''), TOKEN)):
            self.send_error(403)
            return
        if not LOCK.acquire(blocking=False):
            self.send_data(409, '相机正在采集，请等待完成。'.encode(), 'text/plain; charset=utf-8')
            return
        try:
            try:
                if self.path == '/connect':
                    data = json.dumps(self.server.camera.connect(), ensure_ascii=False).encode('utf-8')
                    self.send_data(200, data, 'application/json; charset=utf-8')
                    return
                data = self.server.camera.capture()
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
    server.camera = Camera(args.port)
    print(server.camera.connect()['message'], flush=True)
    url = f'http://127.0.0.1:{server.server_port}/#{TOKEN}'
    print('网页仅在本机访问。停止服务请在此窗口按 Ctrl+C。', flush=True)
    print('串口默认打开；打开串口可能复位设备。拍照时普通复位一次；录像为低帧率，无声音。', flush=True)
    print(f'如果浏览器没有自动打开，请访问：{url}', flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止。')
    finally:
        server.server_close()
        server.camera.close()


if __name__ == '__main__':
    main()
