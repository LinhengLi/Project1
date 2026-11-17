"""Persistent loopback-only archive server and double-click launcher."""
import argparse
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT=Path(__file__).resolve().parent
URL='http://127.0.0.1:8870/'

def ready():
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(URL,timeout=1) as r:return '研究可视化档案' in r.read().decode('utf-8')
    except Exception:return False

def main():
    p=argparse.ArgumentParser();p.add_argument('--serve',action='store_true');p.add_argument('--no-browser',action='store_true');args=p.parse_args()
    if args.serve:
        ThreadingHTTPServer(('127.0.0.1',8870),partial(SimpleHTTPRequestHandler,directory=str(ROOT))).serve_forever();return
    if not ready():
        options={}
        if os.name=='nt':
            options['creationflags']=subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS
        with (ROOT/'service.log').open('ab') as log:
            subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--serve'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,cwd=ROOT,**options)
        for _ in range(30):
            if ready():break
            time.sleep(.2)
        else:raise SystemExit('Archive server failed; inspect service.log or port 8870.')
    print(URL,flush=True)
    if not args.no_browser:webbrowser.open(URL)

if __name__=='__main__':main()
