"""ChatLLMGenerator + create_app(generator=...) wiring.

A local stub chat endpoint returns different candidates per desired_state,
so two different synthetic users provably receive different generated words
through the real store and the real HTTP app — no catalog anywhere.
"""
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

from fastapi.testclient import TestClient

from models.manager.product.http_api import create_app
from models.manager.product.interventions import ChatLLMGenerator, InterventionStore

WORDS = {'calm': 'Breathe out slowly; this minute is not a verdict on you.',
         'confidence': 'You have already survived every worst day so far.'}


class StubChat(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        prompt = body['messages'][0]['content']
        state = 'confidence' if 'confidence' in prompt else 'calm'
        payload = {'candidates': [
            {'id': 'a', 'kind': 'reflection', 'text': WORDS[state], 'probability': 0.85},
            {'id': 'b', 'kind': 'none', 'text': '', 'probability': 0.15}]}
        out = json.dumps({'choices': [{'message': {'content': json.dumps(payload)}}]}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args):
        pass


def stub_url():
    server = HTTPServer(('127.0.0.1', 0), StubChat)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{server.server_port}'


def context(state):
    return {'time_band': 'morning', 'language': 'en', 'desired_state': state,
            'source': 'daily_home'}


def test_two_users_get_different_generated_words(tmp_path):
    store = InterventionStore(str(tmp_path / 'cases.db'),
                              ChatLLMGenerator(stub_url(), 'stub-model'),
                              draw=lambda: 0.1)
    calm = store.decide('user-calm', str(uuid.uuid4()), context('calm'))
    conf = store.decide('user-conf', str(uuid.uuid4()), context('confidence'))
    assert calm['chosen']['text'] == WORDS['calm']
    assert conf['chosen']['text'] == WORDS['confidence']
    assert calm['chosen']['text'] != conf['chosen']['text']
    assert calm['generator_model'] == 'stub-model'
    assert calm['backend'] == 'manager-v1'


def test_app_with_generator_serves_decisions(tmp_path):
    app = create_app(str(tmp_path / 'cases.db'), b'x' * 32, 'svc-token',
                     generator=ChatLLMGenerator(stub_url(), 'stub-model'),
                     sender_token='sender-token')
    client = TestClient(app)
    headers = {'Authorization': 'Bearer svc-token', 'X-Manager-Subject': 'account1'}
    health = client.get('/manager/health', headers=headers).json()
    assert health['generation_available'] is True
    assert health['generator_model'] == 'stub-model'
    body = {'delivery_id': str(uuid.uuid4()), 'context': context('calm')}
    response = client.post('/manager/decisions', json=body, headers=headers)
    assert response.status_code == 200
    decision = response.json()
    assert decision['backend'] == 'manager-v1'
    assert decision['chosen']['text'] in WORDS.values() or decision['chosen']['kind'] == 'none'
    # Push-decision route stays closed to app tokens, opens to the sender token.
    push = {'decisions': [{'subject': 'account1', 'delivery_id': str(uuid.uuid4()),
                           'context': {'time_band': 'morning', 'language': 'en',
                                       'desired_state': 'calm', 'source': 'notification'},
                           'push_state': {'profile': {}, 'recent_reactions': [],
                                          'local_day': '2026-11-17', 'slot': '09:00'}}]}
    assert client.post('/manager/push-decisions', json=push, headers=headers).status_code == 401
    sender = {'Authorization': 'Bearer sender-token'}
    pushed = client.post('/manager/push-decisions', json=push, headers=sender)
    assert pushed.status_code == 200
    # The app-level store draws randomly; a model "none" (no-send) decision
    # is a legitimate outcome, so accept either a generated word or no-send.
    chosen = pushed.json()['decisions'][0]['chosen']
    assert chosen['text'] in WORDS.values() or chosen['kind'] == 'none'
