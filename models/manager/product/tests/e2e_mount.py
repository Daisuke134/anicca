"""Local real HTTP smoke: Python product + actual Express mount, no provider effects."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

proxy = Path(sys.argv[1]).resolve()
env = dict(os.environ, MANAGER_SERVICE_TOKEN=secrets.token_hex(32),
           MANAGER_PSEUDONYM_KEY=secrets.token_hex(32),
           PROXY_AUTH_JWT_SECRET=secrets.token_hex(32),
           MANAGER_PRODUCT_URL='http://127.0.0.1:18792')
def encode(value):
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')
header = encode({'alg': 'HS256', 'typ': 'JWT'})
payload = encode({'sub': 'local-fixture', 'exp': time.time() + 300})
unsigned = header + '.' + payload
signature = base64.urlsafe_b64encode(hmac.new(env['PROXY_AUTH_JWT_SECRET'].encode(),
    unsigned.encode(), hashlib.sha256).digest()).decode().rstrip('=')
token = unsigned + '.' + signature
with tempfile.TemporaryDirectory() as tmp:
    env['MANAGER_STORE_PATH'] = tmp + '/cases.db'
    code = """import express from 'express';
import manager from './src/routes/manager.js';
const app = express(); app.use(express.json()); app.use('/manager', manager);
app.listen(18793, '127.0.0.1');"""
    processes = [
        subprocess.Popen([sys.executable, '-m', 'uvicorn',
            'models.manager.product.http_api:app_from_env', '--factory',
            '--host', '127.0.0.1', '--port', '18792'], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
        subprocess.Popen(['node', '--input-type=module', '-e', code],
            cwd=proxy / 'apps/api', env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
    ]
    try:
        import httpx
        for _ in range(100):
            try:
                if (httpx.get('http://127.0.0.1:18793/manager/health', trust_env=False).status_code == 401
                    and httpx.get('http://127.0.0.1:18792/manager/health', trust_env=False).status_code == 401):
                    break
            except httpx.ConnectError:
                pass
            time.sleep(.1)
        else:
            raise RuntimeError('local boot failed')
        print('Boot: uvicorn product service :18792 + Express production manager router :18793')
        for method, path, body, expected in [
            ('GET', 'health', None, '200'),
            ('POST', 'decisions', {'delivery_id': '12345678-1234-1234-1234-123456789012',
             'context': {'time_band': 'day', 'language': 'en', 'desired_state': 'calm',
                         'source': 'daily_home'}}, '503')]:
            args = ['curl', '--noproxy', '*', '-sS', '-w', '\nHTTP %{http_code}\n', '-X', method,
                    '--config', '-', 'http://127.0.0.1:18793/manager/' + path]
            if body:
                args += ['--data', json.dumps(body)]
            print('curl -X', method, '/manager/' + path, '(ephemeral auth via stdin; omitted)')
            result = subprocess.run(args, input='header = "Authorization: Bearer ' + token +
                '"\nheader = "Content-Type: application/json"\n',
                text=True, capture_output=True, check=True)
            print(result.stdout)
            assert 'HTTP ' + expected in result.stdout
        processes[0].terminate()
        processes[0].wait()
        response = httpx.get('http://127.0.0.1:18793/manager/health', trust_env=False,
                             headers={'Authorization': 'Bearer ' + token})
        assert response.status_code == 503
        print('Upstream stopped: HTTP 503; no fallback')
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
            process.wait()
