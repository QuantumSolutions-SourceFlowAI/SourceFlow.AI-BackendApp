from sqlalchemy import inspect, text

from sfplatform.db import SessionLocal, engine


def test_core_tables_exist():
    expected = {
        "tenant", "users", "chatbot", "document", "chunk",
        "conversation", "message", "message_source",
        "answer_feedback", "answer_cache", "token_consumption",
        "plan", "subscription",
    }
    with SessionLocal() as s:
        rows = s.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        ).scalars().all()
    assert expected.issubset(set(rows))


def test_chunk_vector_dimension_is_1024():
    with SessionLocal() as s:
        row = s.execute(text("SELECT atttypmod FROM pg_attribute "
                             "WHERE attrelid='chunk'::regclass AND attname='embedding_vector'")).scalar()
    assert row == 1024


def test_chatbot_has_unique_tenant_name_constraint():
    inspector = inspect(engine)
    constraints = inspector.get_unique_constraints("chatbot")
    names = {c["name"] for c in constraints}
    assert "uq_chatbots_tenant_id_name" in names
    matching = next(c for c in constraints if c["name"] == "uq_chatbots_tenant_id_name")
    assert set(matching["column_names"]) == {"tenant_id", "name"}
