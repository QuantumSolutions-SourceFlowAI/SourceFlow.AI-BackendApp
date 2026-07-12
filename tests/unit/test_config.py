import os

from sfplatform.config import Settings


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    s = Settings()
    assert s.database_url.startswith("postgresql+psycopg://")
    assert s.retrieval_top_k == 4
    assert s.similarity_threshold == 0.4
    assert s.chunk_size_tokens == 800
