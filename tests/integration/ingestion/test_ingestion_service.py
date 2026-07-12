from sqlalchemy import text

from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.knowledge_ingestion.application.ingestion_service import process_document
from contexts.knowledge_ingestion.domain.chunk import Chunk
from contexts.knowledge_ingestion.domain.document import Document
from contexts.knowledge_ingestion.domain.enums import DocumentStatus
from contexts.knowledge_ingestion.domain.value_objects import Embedding
from contexts.knowledge_ingestion.infrastructure.chunk_repository import SqlAlchemyChunkRepository
from contexts.knowledge_ingestion.infrastructure.document_repository import SqlAlchemyDocumentRepository
from sfplatform.db import SessionLocal
from shared.application.tenant_context import TenantId


class FakeEmbeddings:
    last_tokens = 7
    def embed(self, texts):
        return [Embedding(tuple(0.05 for _ in range(1024))) for _ in texts]
    def embed_one(self, text):
        return self.embed([text])[0]


def _make_chatbot_and_doc(session):
    session.execute(text("INSERT INTO chatbot (tenant_id, name, tone, status) "
                         "VALUES (1,'IngestSvcBot','formal','no_documents') "
                         "ON CONFLICT (tenant_id, name) DO NOTHING"))
    cid = session.execute(text("SELECT id FROM chatbot WHERE name='IngestSvcBot'")).scalar()
    repo = SqlAlchemyDocumentRepository(session)
    doc = repo.add(Document(id=None, tenant_id=TenantId(1), chatbot_id=ChatbotId(cid),
                            file_name="d.pdf", size_bytes=10, status=DocumentStatus.PROCESSING))
    session.commit()
    return cid, doc.id


def test_process_document_success_sets_ready_and_chatbot_ready():
    with SessionLocal() as s:
        cid, doc_id = _make_chatbot_and_doc(s)
    # raw text simulated (extraction is monkeypatched via plain text bytes path)
    with SessionLocal() as s:
        process_document(s, doc_id.value, tenant_id=1,
                         extracted_text="hola mundo catalogo precios",
                         embedding_provider=FakeEmbeddings())
        s.commit()
    with SessionLocal() as s:
        dstatus = s.execute(text("SELECT status FROM document WHERE id=:i"),
                            {"i": doc_id.value}).scalar()
        cstatus = s.execute(text("SELECT status FROM chatbot WHERE id=:i"), {"i": cid}).scalar()
        nchunks = s.execute(text("SELECT count(*) FROM chunk WHERE document_id=:i"),
                            {"i": doc_id.value}).scalar()
    assert dstatus == "ready"
    assert cstatus == "ready"
    assert nchunks >= 1


def test_process_document_empty_text_sets_error():
    with SessionLocal() as s:
        _, doc_id = _make_chatbot_and_doc(s)
    with SessionLocal() as s:
        process_document(s, doc_id.value, tenant_id=1, extracted_text="   ",
                         embedding_provider=FakeEmbeddings())
        s.commit()
    with SessionLocal() as s:
        dstatus = s.execute(text("SELECT status FROM document WHERE id=:i"),
                            {"i": doc_id.value}).scalar()
    assert dstatus == "error"


def test_process_document_failure_after_delete_preserves_existing_chunks(monkeypatch):
    with SessionLocal() as s:
        _, doc_id = _make_chatbot_and_doc(s)
        chunk_repo = SqlAlchemyChunkRepository(s)
        chunk_repo.save_chunks(TenantId(1), doc_id, [
            Chunk(text="original chunk", position=0,
                 embedding=Embedding(tuple(0.01 for _ in range(1024))))])
        s.commit()

    def boom(self, *args, **kwargs):
        raise RuntimeError("simulated failure after delete_for_document")

    monkeypatch.setattr(SqlAlchemyChunkRepository, "save_chunks", boom)

    with SessionLocal() as s:
        process_document(s, doc_id.value, tenant_id=1,
                         extracted_text="hola mundo catalogo precios",
                         embedding_provider=FakeEmbeddings())
        s.commit()

    with SessionLocal() as s:
        dstatus = s.execute(text("SELECT status FROM document WHERE id=:i"),
                            {"i": doc_id.value}).scalar()
        rows = s.execute(text("SELECT text_content FROM chunk WHERE document_id=:i"),
                         {"i": doc_id.value}).all()
    assert dstatus == "error"
    assert [r[0] for r in rows] == ["original chunk"]
