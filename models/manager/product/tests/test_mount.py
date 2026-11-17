from fastapi.testclient import TestClient
from models.manager.product.http_api import create_app


def test_prior_is_explicit_and_fails_closed(tmp_path):
    app = create_app(str(tmp_path / 'cases.db'), b'x' * 32, 'test-service-token')
    client = TestClient(app)
    headers = {'Authorization': 'Bearer test-service-token', 'X-Manager-Subject': 'account1'}
    assert client.get('/manager/health').status_code == 401
    assert client.get('/manager/health', headers=headers).json()['default_backend'] == 'prior'
    body = {'delivery_id': '12345678-1234-1234-1234-123456789012', 'context': {'time_band': 'day', 'language': 'en', 'desired_state': 'calm', 'source': 'daily_home'}}
    response = client.post('/manager/decisions', json=body, headers=headers)
    assert response.status_code == 503
    assert response.json()['detail']['backend'] == 'prior'
    assert client.post('/manager/decisions', content='{', headers=headers).status_code == 422
