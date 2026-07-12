from pathlib import Path

from contexts.knowledge_ingestion.application.ingestion_service import process_document
from contexts.knowledge_ingestion.domain.value_objects import DocumentId
from contexts.knowledge_ingestion.infrastructure.document_repository import SqlAlchemyDocumentRepository
from contexts.knowledge_ingestion.infrastructure.mistral_embeddings import MistralEmbeddingProvider
from contexts.knowledge_ingestion.infrastructure.pdf_extractor import extract_text
from sfplatform.celery_app import celery_app
from sfplatform.config import get_settings
from sfplatform.db import SessionLocal
from shared.application.tenant_context import TenantId


@celery_app.task(name="ingest_document")
def ingest_document_task(document_id: int, tenant_id: int, file_path: str) -> None:
    settings = get_settings()
    path = Path(file_path)
    try:
        raw = path.read_bytes()
        text = extract_text(raw)
        provider = MistralEmbeddingProvider(settings.mistral_api_key, settings.embedding_model)
        with SessionLocal() as session:
            process_document(session, document_id, tenant_id, text, provider)
            session.commit()
    except Exception:
        _mark_error(document_id, tenant_id)
    finally:
        path.unlink(missing_ok=True)


def _mark_error(document_id: int, tenant_id: int) -> None:
    with SessionLocal() as session:
        repo = SqlAlchemyDocumentRepository(session)
        doc = repo.get(TenantId(tenant_id), DocumentId(document_id))
        if doc is not None:
            doc.mark_error()
            repo.update(doc)
            session.commit()
