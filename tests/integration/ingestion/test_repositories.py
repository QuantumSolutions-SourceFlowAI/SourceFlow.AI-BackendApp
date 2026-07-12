import pytest
from sqlalchemy import text

from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.knowledge_ingestion.domain.chunk import Chunk
from contexts.knowledge_ingestion.domain.document import Document
from contexts.knowledge_ingestion.domain.enums import DocumentStatus
from contexts.knowledge_ingestion.domain.value_objects import Embedding
from contexts.knowledge_ingestion.infrastructure.chunk_repository import SqlAlchemyChunkRepository
from contexts.knowledge_ingestion.infrastructure.document_repository import SqlAlchemyDocumentRepository
from shared.application.tenant_context import TenantId


@pytest.fixture()
def chatbot_id(db_session):
    db_session.execute(text(
        "INSERT INTO chatbot (tenant_id, name, tone, status) "
        "VALUES (1, 'IngestRepoBot', 'formal', 'no_documents')"))
    db_session.commit()
    cid = db_session.execute(text("SELECT id FROM chatbot WHERE name='IngestRepoBot'")).scalar()
    yield ChatbotId(cid)
    db_session.execute(text("DELETE FROM chatbot WHERE id=:i"), {"i": cid})
    db_session.commit()


def test_document_add_update_and_ready_flag(db_session, chatbot_id):
    repo = SqlAlchemyDocumentRepository(db_session)
    doc = repo.add(Document(id=None, tenant_id=TenantId(1), chatbot_id=chatbot_id,
                            file_name="d.pdf", size_bytes=10, status=DocumentStatus.PROCESSING))
    db_session.commit()
    assert doc.id is not None
    assert repo.has_ready_document(TenantId(1), chatbot_id) is False
    doc.mark_processed()
    repo.update(doc)
    db_session.commit()
    assert repo.has_ready_document(TenantId(1), chatbot_id) is True


def test_update_is_tenant_scoped(db_session, chatbot_id):
    repo = SqlAlchemyDocumentRepository(db_session)
    saved = repo.add(Document(id=None, tenant_id=TenantId(1), chatbot_id=chatbot_id,
                              file_name="d.pdf", size_bytes=10, status=DocumentStatus.PROCESSING))
    db_session.commit()
    # attempt to update the same document id but under a different tenant
    intruder = Document(id=saved.id, tenant_id=TenantId(999), chatbot_id=chatbot_id,
                        file_name="hacked.pdf", size_bytes=999, status=DocumentStatus.READY)
    repo.update(intruder)
    db_session.commit()
    fetched = repo.get(TenantId(1), saved.id)
    assert fetched is not None
    assert fetched.status == DocumentStatus.PROCESSING  # unchanged


def test_chunk_save_persists_vectors(db_session, chatbot_id):
    doc_repo = SqlAlchemyDocumentRepository(db_session)
    doc = doc_repo.add(Document(id=None, tenant_id=TenantId(1), chatbot_id=chatbot_id,
                               file_name="d.pdf", size_bytes=10, status=DocumentStatus.PROCESSING))
    db_session.commit()
    chunk_repo = SqlAlchemyChunkRepository(db_session)
    chunks = [Chunk(text="hola", position=0, embedding=Embedding(tuple(0.1 for _ in range(1024))))]
    chunk_repo.save_chunks(TenantId(1), doc.id, chunks)
    db_session.commit()
    count = db_session.execute(text("SELECT count(*) FROM chunk WHERE document_id=:d"),
                               {"d": doc.id.value}).scalar()
    assert count == 1
