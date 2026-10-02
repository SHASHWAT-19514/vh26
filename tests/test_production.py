from fastapi.testclient import TestClient
import abhedya.app as app_module


def test_health_and_readiness_contract():
    with TestClient(app_module.app) as client:
        health=client.get('/api/health')
        assert health.status_code==200
        assert health.json()['status']=='ok'
        ready=client.get('/api/ready')
        assert ready.status_code==200
        assert ready.json()['status']=='ready'
        assert health.headers.get('x-content-type-options')=='nosniff'
        assert health.headers.get('x-request-id')


def test_api_key_gate_when_configured():
    previous=app_module.API_KEY
    app_module.API_KEY='test-production-key-012345678901234567890'
    try:
        with TestClient(app_module.app) as client:
            denied=client.get('/api/metrics')
            assert denied.status_code==401
            assert denied.json()['error']['code']=='AUTH_REQUIRED'
            allowed=client.get('/api/metrics',headers={'X-API-Key':app_module.API_KEY})
            assert allowed.status_code==200
    finally:
        app_module.API_KEY=previous
