from fastapi.testclient import TestClient
from sqlalchemy import text

from sfplatform.app import app
from sfplatform.db import SessionLocal


def _seed_tenant_2():
    with SessionLocal() as s:
        exists = s.execute(text("SELECT 1 FROM tenant WHERE id=2")).first()
        if not exists:
            s.execute(text("INSERT INTO tenant (business_name,status) VALUES ('Tenant Two','active')"))
            s.commit()


def test_chatbot_created_by_tenant1_not_visible_to_tenant2():
    _seed_tenant_2()
    c1 = TestClient(app, headers={"X-Tenant-Id": "1"})
    c2 = TestClient(app, headers={"X-Tenant-Id": "2"})

    c1.post("/chatbots", json={"name": "IsolationBot", "tone": "formal"})
    names_t2 = [b["name"] for b in c2.get("/chatbots").json()]
    assert "IsolationBot" not in names_t2
