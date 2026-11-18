from fastapi.testclient import TestClient


def test_generated_contract_and_observation(tmp_path):
    from fastapi import FastAPI
    from models.manager.product.http_api import router
    from models.manager.product.interventions import InterventionStore
    async def auth(request):
        return 'fixture-subject'
    candidates = [
        {'id': 'a', 'kind': 'reflection', 'text': 'fixture', 'probability': 0.5},
        {'id': 'b', 'kind': 'none', 'text': '', 'probability': 0.5},
    ]
    store = InterventionStore(str(tmp_path / 'fixture.db'), lambda _: candidates, draw=lambda: 0.1)
    app = FastAPI()
    app.include_router(router(store, auth, b'x' * 32))
    client = TestClient(app)
    body = {'delivery_id': '12345678-1234-1234-1234-123456789012', 'context': {
        'time_band': 'day', 'language': 'en', 'desired_state': 'calm', 'source': 'daily_home'}}
    response = client.post('/manager/decisions', json=body)
    assert response.status_code == 200
    decision = response.json()
    assert decision['backend'] == 'manager-v1'
    assert decision['policy_version'] == 'manager-generated-v1'
    assert decision['context'] == body['context']
    assert decision['chosen'] in decision['candidates']
    assert decision['assigned_probability'] == decision['chosen']['probability']
    assert decision['outcome_window_end'] == decision['decision_point_at'] + 1800
    assert client.post('/manager/decisions', json=body).json() == decision
    assert client.post('/manager/observations', json={
        'delivery_id': body['delivery_id'], 'event': 'saved',
        'observed_at': decision['decision_point_at']}).json() == {
            'delivery_id': body['delivery_id'], 'accepted': True}
    assert client.delete('/manager/evidence').json() == {'deleted': True}
    assert client.post('/manager/decisions', json=body).status_code == 410
