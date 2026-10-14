#!/usr/bin/env python3
"""Isolated E2E servers. No existing DB, credentials or tracked Next.js build directory is used."""
import fcntl
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
env = os.environ.copy()
child = None
stopping = False


def stop(*_):
    # Never wait inside the signal callback: run() may already own Popen's
    # waitpid lock. Re-entering wait() here deadlocks teardown.
    global stopping
    stopping = True
    if child and child.poll() is None:
        child.terminate()


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)


def run(command, cwd):
    global child
    if stopping:
        raise SystemExit(0)
    child = subprocess.Popen(command, cwd=cwd, env=env)
    deadline = None
    while True:
        if stopping and deadline is None:
            deadline = time.monotonic() + 10
        if deadline is not None and time.monotonic() >= deadline:
            child.kill()
        try:
            code = child.wait(timeout=0.5)
            break
        except subprocess.TimeoutExpired:
            continue
    if stopping:
        raise SystemExit(0)
    if code:
        raise SystemExit(code)


if sys.argv[1] == 'backend':
    with tempfile.TemporaryDirectory(prefix='gps-e2e-db-') as temporary:
        env.update(PYTHONPATH=str(ROOT), DATABASE_URL=f'sqlite:///{temporary}/app.db',
                   APP_ENV='test', AGENT_LLM_ENABLED='false', LANGFUSE_TRACING_ENABLED='false',
                   LANGCHAIN_TRACING_V2='false', LANGSMITH_TRACING='false', LANGCHAIN_API_KEY='', LANGSMITH_API_KEY='',
                   OPENAI_API_KEY='', GOOGLE_API_KEY='', LANGFUSE_PUBLIC_KEY='', LANGFUSE_SECRET_KEY='',
                   AUTH_SECRET_KEY='local-synthetic-e2e-only-not-a-real-secret',
                   SERVICE_POINTS_FILE=str(ROOT / 'fixtures/service_points.demo.json'))
        run([str(ROOT / '.venv/bin/python'), '-m', 'uvicorn', 'src.main:app',
             '--host', '127.0.0.1', '--port', '18000',
             '--access-log' if env.get('GPS_E2E_ACCESS_LOG') == '1' else '--no-access-log'], temporary)
elif sys.argv[1] == 'frontend':
    # Separate build output plus an exclusive lock prevents two E2E builders colliding.
    key = hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]
    with open(f'/tmp/gps-e2e-{key}.lock', 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Another GPS E2E production server already owns this checkout.')
        env.update(NEXT_DIST_DIR='.next-gps-e2e', API_PROXY_TARGET='http://127.0.0.1:18000',
                   NEXT_PUBLIC_API_URL='', NEXT_TELEMETRY_DISABLED='1', NEXT_TSCONFIG_PATH='tsconfig.e2e.json')
        next_bin = str(ROOT / 'frontend/node_modules/next/dist/bin/next')
        run(['node', next_bin, 'build'], ROOT / 'frontend')
        run(['node', next_bin, 'start', '-H', '127.0.0.1', '-p', '13000'], ROOT / 'frontend')
else:
    raise SystemExit('Usage: gps-e2e-server.py backend|frontend')
