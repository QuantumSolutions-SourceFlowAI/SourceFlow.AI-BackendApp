from fastapi.testclient import TestClient

from sfplatform.app import app


def test_health_ok():
    c = TestClient(app)
    r = c.get("/health", headers={"X-Tenant-Id": "1"})
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "tenant_id": 1}


def test_default_tenant_when_header_absent():
    c = TestClient(app)
    r = c.get("/health")
    assert r.json()["tenant_id"] == 1
