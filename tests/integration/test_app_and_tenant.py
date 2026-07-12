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


def test_healthz_has_no_tenant_dependency():
    c = TestClient(app)
    r = c.get("/healthz")  # sin header X-Tenant-Id
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_cors_preflight_allows_configured_origin(monkeypatch):
    # Rebuild an app whose settings allow a known origin.
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://frontend.example.net")
    from sfplatform.app import create_app
    from sfplatform.config import get_settings
    get_settings.cache_clear()
    local_app = create_app()
    c = TestClient(local_app)
    r = c.options(
        "/chatbots",
        headers={
            "Origin": "https://frontend.example.net",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == "https://frontend.example.net"
    get_settings.cache_clear()
