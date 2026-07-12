from sqlalchemy import text

from sfplatform.db import SessionLocal


def test_seed_creates_default_tenant():
    with SessionLocal() as s:
        row = s.execute(text("SELECT business_name, status FROM tenant WHERE id = 1")).first()
    assert row is not None
    assert row.status == "active"
