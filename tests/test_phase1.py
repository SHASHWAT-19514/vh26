from fastapi.testclient import TestClient
from abhedya.app import app

def test_health():
    with TestClient(app) as c:
        r=c.get('/api/health'); assert r.status_code==200; assert r.json()['status']=='ok'

def test_frontend_and_routes():
    with TestClient(app) as c:
        assert c.get('/').status_code==200
        assert c.get('/static/manus-routes.json').json()['routes'][0]['path']=='/'
