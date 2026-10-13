import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_create_order(client):
    headers = {"Authorization": "Bearer token", "Idempotency-Key": "key-123"}
    res = client.post('/orders', json={"items": [{"qty": 2}], "address": "Campus"}, headers=headers)
    assert res.status_code == 201
    assert 'Location' in res.headers

def test_idempotent_repeat(client):
    headers = {"Authorization": "Bearer token", "Idempotency-Key": "key-123"}
    res1 = client.post('/orders', json={"items": [{"qty": 2}], "address": "Campus"}, headers=headers)
    res2 = client.post('/orders', json={"items": [{"qty": 2}], "address": "Campus"}, headers=headers)
    assert res1.get_json()['id'] == res2.get_json()['id']

def test_validation_failure(client):
    headers = {"Authorization": "Bearer token"}
    res = client.post('/orders', json={"items": [{"qty": 0}]}, headers=headers)
    assert res.status_code == 422
    assert res.get_json()['type'] == 'validation-error'

def test_missing_resource(client):
    headers = {"Authorization": "Bearer token"}
    res = client.get('/orders/nonexistent', headers=headers)
    assert res.status_code == 404