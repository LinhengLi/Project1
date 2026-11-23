"""Serve the archive locally; keep the console visible for diagnostics."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import socket
import threading
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8870/'

def ready():
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(URL, timeout=2) as response:
            return '研究可视化档案' in response.read().decode('utf-8')
    except Exception:
        return False

def open_browser():
    try:
        if os.name == 'nt':
            os.startfile(URL)
        else:
            webbrowser.open(URL)
    except Exception as error:
        print(f'Cannot open browser: {error}\nOpen manually: {URL}', flush=True)

class ArchiveServer(ThreadingHTTPServer):
    allow_reuse_address = False
    def server_bind(self):
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if ready():
        print(f'Existing archive service: {URL}', flush=True)
        if not args.no_browser and not args.serve:
            open_browser()
        return
    server = ArchiveServer(('127.0.0.1', 8870), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
    print(f'Archive ready: {URL}\nKeep this window open. Press Ctrl+C to stop.', flush=True)
    if not args.no_browser and not args.serve:
        threading.Timer(0.5, open_browser).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
