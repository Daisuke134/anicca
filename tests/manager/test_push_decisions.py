import tempfile
import unittest
from models.manager.product.interventions import InterventionStore

class PushTests(unittest.TestCase):
    def test_state_and_replay(self):
        calls = []
        def generate(context):
            calls.append(context)
            return [dict(id='a', kind='action', text=context['push_state']['profile']['goal'], probability=.9), dict(id='b', kind='none', text='', probability=.1)]
        with tempfile.TemporaryDirectory() as root:
            store = InterventionStore(root + '/db', generate, draw=lambda: 0)
            context = dict(time_band='morning', language='en', desired_state='calm', source='notification')
            outputs = []
            for user, goal in [('one', 'Rest'), ('two', 'Focus')]:
                state = dict(profile={'goal': goal}, recent_reactions=[], local_day='2026-11-17', slot='09:00')
                result = store.decide_push(user, '00000000-0000-4000-8000-000000000001', context, state)
                self.assertEqual(result, store.decide_push(user, result['delivery_id'], context, state))
                outputs.append(result['chosen']['text'])
            self.assertEqual(outputs, ['Rest', 'Focus'])
            self.assertEqual(len(calls), 2)
            print('same slot: user one=Rest; user two=Focus; replay generations=0')

    def test_http_service_auth_batch_and_app_isolation(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from models.manager.product.http_api import router
        async def app_auth(request):
            return 'app-user'
        async def sender_auth(request):
            return request.headers.get('authorization') == 'Bearer test-only'
        with tempfile.TemporaryDirectory() as root:
            store = InterventionStore(root + '/db', lambda c: [dict(id='a', kind='action', text=c['push_state']['profile']['goal'], probability=.9), dict(id='b', kind='none', text='', probability=.1)], draw=lambda: 0)
            app = FastAPI()
            app.include_router(router(store, app_auth, b'x' * 32, sender_auth))
            client = TestClient(app)
            items = [dict(subject=user, delivery_id='00000000-0000-4000-8000-000000000001', context=dict(time_band='morning', language='en', desired_state='calm', source='notification'), push_state=dict(profile={'goal': goal}, recent_reactions=[], local_day='2026-11-17', slot='09:00')) for user, goal in [('one', 'Rest'), ('two', 'Focus')]]
            self.assertEqual(client.post('/manager/push-decisions', json={'decisions': items}).status_code, 401)
            headers = {'authorization': 'Bearer test-only'}
            response = client.post('/manager/push-decisions', json={'decisions': items}, headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
            records = response.json()['decisions']
            self.assertEqual([r['chosen']['text'] for r in records], ['Rest', 'Focus'])
            self.assertEqual(response.json(), client.post('/manager/push-decisions', json={'decisions': items}, headers=headers).json())
            for record in records:
                self.assertEqual(record['assigned_probability'], .9)
                self.assertEqual(record['backend'], 'manager-v1')
                self.assertTrue(record['policy_version'])
            items[0]['push_state']['slot'] = '99:99'
            self.assertEqual(client.post('/manager/push-decisions', json={'decisions': items}, headers=headers).status_code, 422)
            self.assertEqual(client.post('/manager/push-decisions', json={'decisions': []}, headers=headers).status_code, 422)
