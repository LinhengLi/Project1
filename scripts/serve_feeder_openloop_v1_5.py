"""Loopback-only local playback server. Run from any directory, Ctrl+C to stop."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    print('http://127.0.0.1:8765/experiments/feeder_openloop_v1_5/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8765),partial(SimpleHTTPRequestHandler,directory=str(ROOT))).serve_forever()
