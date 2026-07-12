from pathlib import Path

from sqlalchemy import text

from contexts.knowledge_ingestion.domain.value_objects import Embedding
from contexts.knowledge_ingestion.infrastructure import celery_tasks
from sfplatform.config import get_settings
from sfplatform.db import SessionLocal


class FakeEmbeddings:
    def __init__(self, *_args, **_kwargs) -> None:
        self.last_tokens = 7

    def embed(self, texts):
        return [Embedding(tuple(0.05 for _ in range(1024))) for _ in texts]

    def embed_one(self, text_):
        return self.embed([text_])[0]


def _make_chatbot_and_doc(name: str) -> tuple[int, int]:
    with SessionLocal() as s:
        s.execute(text("INSERT INTO chatbot (tenant_id,name,tone,status) "
                       "VALUES (1,:name,'formal','no_documents') ON CONFLICT DO NOTHING"),
                  {"name": name})
        s.commit()
        cid = s.execute(text("SELECT id FROM chatbot WHERE name=:name"), {"name": name}).scalar()
        doc_id = s.execute(text(
            "INSERT INTO document (tenant_id, chatbot_id, file_name, size_bytes, status) "
            "VALUES (1, :cid, 'd.pdf', 10, 'processing') RETURNING id"), {"cid": cid}).scalar()
        s.commit()
        return cid, doc_id


def _minimal_pdf() -> bytes:
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


def test_ingest_document_task_happy_path_marks_ready_and_persists_chunks(monkeypatch):
    monkeypatch.setattr(celery_tasks, "MistralEmbeddingProvider", lambda *a, **k: FakeEmbeddings())
    monkeypatch.setattr(celery_tasks, "extract_text", lambda raw: "hola mundo catalogo precios")

    _, doc_id = _make_chatbot_and_doc("CeleryTaskHappyBot")
    upload_dir = Path(get_settings().upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"sourceflow_doc_{doc_id}.pdf"
    file_path.write_bytes(_minimal_pdf())

    # Call the task directly (Celery Task.__call__ runs synchronously,
    # bypassing the broker) so this exercises the real production code path.
    celery_tasks.ingest_document_task(doc_id, 1, str(file_path))

    with SessionLocal() as s:
        status = s.execute(text("SELECT status FROM document WHERE id=:i"), {"i": doc_id}).scalar()
        nchunks = s.execute(text("SELECT count(*) FROM chunk WHERE document_id=:i"),
                            {"i": doc_id}).scalar()
    assert status == "ready"
    assert nchunks >= 1
    assert not file_path.exists(), "uploaded file must be unlinked after processing"


def test_ingest_document_task_missing_file_marks_error(monkeypatch):
    # Regression test for Fix 2: read_bytes()/extract_text() used to run
    # before process_document's try/except, so a missing or corrupt PDF
    # raised an exception that escaped the task entirely, leaving the
    # document (and the temp file) stranded in `processing` forever.
    monkeypatch.setattr(celery_tasks, "MistralEmbeddingProvider", lambda *a, **k: FakeEmbeddings())

    _, doc_id = _make_chatbot_and_doc("CeleryTaskErrBot")
    missing_path = Path(get_settings().upload_dir) / f"does_not_exist_{doc_id}.pdf"
    assert not missing_path.exists()

    celery_tasks.ingest_document_task(doc_id, 1, str(missing_path))

    with SessionLocal() as s:
        status = s.execute(text("SELECT status FROM document WHERE id=:i"), {"i": doc_id}).scalar()
        nchunks = s.execute(text("SELECT count(*) FROM chunk WHERE document_id=:i"),
                            {"i": doc_id}).scalar()
    assert status == "error"
    assert nchunks == 0
