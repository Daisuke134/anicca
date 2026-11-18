import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from models.manager.product.http_api import router


class UploadTest(unittest.TestCase):
    def test_offline_restart_online_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'store'
            queue = Path(directory) / 'queue.json'
            body = {'record_id': 'a' * 64, 'record': {
                'delivery_id': 'simulated-delivery-001', 'backend': 'local_rule',
                'fallback': True, 'decision_point_at': '2026-11-17T00:00:00Z',
                'candidate_ids': ['fixture-item'],
                'stimulus': {'message_id': 'fixture-item',
                             'assigned_probability': 0.125, 'policy_version': 'fixture-v1'}}}
            queue.write_text(json.dumps(body))
            # Actual connection refusal; durable queue is untouched.
            import httpx
            with self.assertRaises(httpx.ConnectError):
                httpx.post('http://127.0.0.1:1/manager/decision-records', json=body, trust_env=False)
            print('OFFLINE: connection refused; durable queue retained')
            async def authenticate(request):
                return 'synthetic-test-subject'
            app = FastAPI()
            app.include_router(router(SimpleNamespace(path=path), authenticate, bytes(32)))
            with TestClient(app) as client:
                pending = json.loads(queue.read_text())  # restart reload
                for _ in range(2):  # ACK lost, followed by replay
                    response = client.post('/manager/decision-records', json=pending)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json(), {'accepted': True, 'record_id': body['record_id']})
                queue.unlink()  # only after matching ACK
                invalid = dict(body, record_id='b' * 64, record=dict(body['record'], stimulus=dict(body['record']['stimulus'], assigned_probability=0)))
                self.assertEqual(client.post('/manager/decision-records', json=invalid).status_code, 422)
            lines = Path(str(path) + '.decision-records.jsonl').read_text().splitlines()
            self.assertEqual(len(lines), 1)
            row = json.loads(lines[0])
            self.assertEqual(row['delivery_id'], body['record']['delivery_id'])
            self.assertEqual(row['stimulus']['assigned_probability'], 0.125)
            print('ONLINE: HTTP 200 twice, matching ACK; store lines=1')
            print('STORE:', lines[0])


class StoreTest(unittest.TestCase):
    def test_concurrent_replays_and_fallback(self):
        from concurrent.futures import ThreadPoolExecutor
        from models.manager.product.decision_records import ingest
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'records.jsonl'
            body = {'record_id': 'b' * 64, 'record': {
                'delivery_id': 'fixture', 'backend': 'local_rule', 'fallback': False,
                'stimulus': {'assigned_probability': 0.3, 'message_id': 'item', 'policy_version': 'v1'}}}
            with ThreadPoolExecutor(max_workers=8) as workers:
                list(workers.map(lambda _: ingest(path, 'fixture-owner', body), range(20)))
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0]['fallback'])
            for index, event in enumerate(('shown', 'notification_opened', 'saved', 'skipped', 'thumbs_up', 'thumbs_down')):
                ingest(path, 'fixture-owner', {'record_id': str(index) * 64,
                       'record': {'delivery_id': 'fixture', 'event': event, 'observed_at': '2026-11-17T00:00:00Z'}})
            self.assertEqual(len(path.read_text().splitlines()), 7)


if __name__ == '__main__':
    unittest.main()
