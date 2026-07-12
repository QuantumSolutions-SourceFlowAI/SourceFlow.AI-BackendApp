from sqlalchemy import text

from sfplatform.db import SessionLocal


def test_pgvector_extension_available():
    with SessionLocal() as session:
        session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        session.commit()
        row = session.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        ).first()
        assert row is not None
