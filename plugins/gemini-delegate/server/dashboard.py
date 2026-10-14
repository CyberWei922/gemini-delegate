"""Read-only, loopback-only task monitor shared by local plugin processes."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
from socketserver import TCPServer
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from host_tools import FileLock, atomic_replace, detached_flags, process_alive

TERMINAL = {'completed', 'failed', 'cancelled', 'interrupted'}
CHILDREN = []


class LoopbackServer(ThreadingHTTPServer):
    def server_bind(self):
        # HTTPServer normally reverse-resolves its bind address for a display
        # name. A loopback-only monitor must also start when DNS is unavailable.
        TCPServer.server_bind(self)
        self.server_name = '127.0.0.1'
        self.server_port = self.server_address[1]


def public_task(data):
    keys = ('id', 'title', 'status', 'model', 'workspace', 'created_at',
            'started_at', 'agy_started_at', 'finished_at', 'updated_at',
            'elapsed_seconds', 'input_parts', 'attempts', 'usage', 'error', 'applied_at',
            'owner_pid', 'result_preview', 'result_truncated')
    task = {k: data[k] for k in keys if k in data}
    task.setdefault('title', '历史任务 · ' + str(data.get('id', '')))
    value = data.get('result')
    if isinstance(value, dict) and 'files' in value and data.get('changes'):
        value = {'summary': value.get('summary'),
                 'files': [f.get('path') for f in value['files']]}
    if 'result' in data:
        encoded = json.dumps(value, ensure_ascii=False) if value is not None else ''
        task['result_preview'] = encoded[:4000]
        task['result_truncated'] = len(encoded) > 4000
    else:
        task.setdefault('result_preview', '')
        task.setdefault('result_truncated', False)
    task['changes'] = [{k: c[k] for k in ('path', 'artifact') if k in c}
                       for c in data.get('changes', [])]
    if task.get('status') not in TERMINAL and task.get('owner_pid'):
        if not process_alive(task['owner_pid']):
            task['status'] = 'interrupted'
    return task


def read_tasks(state, workspace=None, limit=200):
    tasks = []
    for root in (Path(state) / 'jobs').glob('*'):
        if not root.is_dir() or root.is_symlink():
            continue
        for name in ('progress.json', 'metadata.json'):
            path = root / name
            if path.is_symlink():
                continue
            try:
                task = public_task(json.loads(path.read_text(encoding='utf-8')))
            except (OSError, ValueError, TypeError):
                continue
            if not workspace or task.get('workspace') == workspace:
                tasks.append(task)
            break
    tasks.sort(key=lambda t: t.get('created_at', 0), reverse=True)
    return tasks[:limit]


def ensure_dashboard(state):
    state = Path(state).resolve()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    config = state / 'dashboard.json'
    with FileLock(state / 'dashboard.lock') as lock:
        lock.acquire(blocking=True, timeout=20)
        try:
            old = json.loads(config.read_text(encoding='utf-8'))
            if old.get('state') == str(state):
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(old['url'] + '&health=1', timeout=1) as r:
                    health = json.load(r)
                if health.get('service') == 'gemini-delegate-monitor':
                    return old['url']
        except (OSError, ValueError, KeyError, urllib.error.URLError):
            pass
        token = secrets.token_urlsafe(32)
        config.unlink(missing_ok=True)
        with (state / 'dashboard.log').open('ab') as log:
            os.chmod(log.name, 0o600)
            process = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), '--state', str(state)],
                stdin=subprocess.PIPE, stdout=log, stderr=log, **detached_flags())
            CHILDREN.append(process)
            process.stdin.write(token.encode())
            process.stdin.close()
        # Cold interpreter/library startup on hosted macOS runners can exceed
        # five seconds. This affects only the explicitly requested monitor.
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('Task monitor failed to start; see dashboard.log')
            try:
                ready = json.loads(config.read_text(encoding='utf-8'))
                if ready.get('token') == token:
                    return ready['url']
            except (OSError, ValueError):
                pass
            time.sleep(0.05)
        process.terminate()
        process.wait(timeout=3)
        raise RuntimeError('Task monitor startup timed out')


def serve(state, token):
    state = Path(state).resolve()
    html = Path(__file__).resolve().parents[1] / 'assets' / 'monitor.html'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            parsed = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            host = '127.0.0.1:' + str(self.server.server_port)
            origin = self.headers.get('Origin')
            if self.headers.get('Host') != host or (origin and origin != 'http://' + host):
                self.send_error(403)
                return
            if not secrets.compare_digest(query.get('token', [''])[0], token):
                self.send_error(403)
                return
            if parsed.path not in ('/', '/api/tasks'):
                self.send_error(404)
                return
            if query.get('health') == ['1']:
                payload = json.dumps({'service': 'gemini-delegate-monitor'}).encode()
                kind = 'application/json'
            elif parsed.path == '/api/tasks':
                payload = json.dumps({'tasks': read_tasks(state), 'now': time.time()},
                                     ensure_ascii=False).encode()
                kind = 'application/json'
            else:
                payload = html.read_bytes()
                kind = 'text/html'
            self.send_response(200)
            self.send_header('Content-Type', kind + '; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(payload)

    server = LoopbackServer(('127.0.0.1', 0), Handler)
    config = state / 'dashboard.json'
    data = {'state': str(state), 'pid': os.getpid(), 'token': token,
            'url': 'http://127.0.0.1:' + str(server.server_port) + '/?token=' + token}
    temporary = config.with_suffix('.tmp')
    temporary.write_text(json.dumps(data), encoding='utf-8')
    temporary.chmod(0o600)
    atomic_replace(temporary, config)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', required=True)
    args = parser.parse_args()
    token = sys.stdin.read(256).strip()
    if len(token) < 32:
        raise SystemExit('Missing monitor token')
    serve(args.state, token)
