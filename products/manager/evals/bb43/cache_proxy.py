#!/usr/bin/env python3
"""Checkpointing OpenAI-compatible proxy for BehaviorBench runs (Issue #43).

Sits between behaviorbench_eval (--api-base http://127.0.0.1:PORT/v1) and
llama-server. Every successful /v1/chat/completions response is appended to a
JSONL cache keyed by sha256(request body). A rerun after a crash replays cached
answers instantly, so the evaluator's own all-or-nothing batch becomes
resumable. Upstream errors are retried with backoff and are never cached.
"""
import hashlib, json, os, sys, threading, time, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = int(sys.argv[1]); UPSTREAM = sys.argv[2].rstrip('/'); CACHE = sys.argv[3]
REQ_TIMEOUT = float(os.environ.get('PROXY_REQ_TIMEOUT', '600'))
RETRIES = int(os.environ.get('PROXY_RETRIES', '6'))
lock = threading.Lock(); cache = {}; stats = {'hit': 0, 'miss': 0, 'err': 0}
if os.path.exists(CACHE):
    with open(CACHE) as f:
        for line in f:
            try:
                r = json.loads(line); cache[r['k']] = r['resp']
            except Exception:
                pass  # torn last line after a kill: ignore
print(f'cache loaded {len(cache)}', flush=True)

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body):
        b = json.dumps(body).encode(); self.send_response(code)
        self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path.startswith('/stats'):
            return self._send(200, dict(stats, cached=len(cache)))
        try:
            with urllib.request.urlopen(UPSTREAM + self.path, timeout=10) as r:
                return self._send(r.status, json.loads(r.read()))
        except Exception as e:
            return self._send(502, {'error': str(e)})
    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        req = json.loads(raw)
        k = hashlib.sha256(json.dumps(req, sort_keys=True).encode()).hexdigest()
        with lock:
            hit = cache.get(k)
        if hit is not None:
            stats['hit'] += 1; return self._send(200, hit)
        last = None
        for a in range(RETRIES):
            try:
                rq = urllib.request.Request(UPSTREAM + self.path, data=raw, headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(rq, timeout=REQ_TIMEOUT) as r:
                    resp = json.loads(r.read())
                if not resp.get('choices'):
                    raise RuntimeError('no choices')
                with lock:
                    cache[k] = resp
                    with open(CACHE, 'a') as f:
                        f.write(json.dumps({'k': k, 'resp': resp}) + '\n'); f.flush(); os.fsync(f.fileno())
                stats['miss'] += 1
                return self._send(200, resp)
            except Exception as e:
                last = e; stats['err'] += 1; time.sleep(min(60, 5 * 2 ** a))
        return self._send(502, {'error': f'upstream failed after {RETRIES}: {last}'})

ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
