from sqlalchemy import delete
from sqlalchemy.orm import Session

from contexts.knowledge_ingestion.domain.chunk import Chunk
from contexts.knowledge_ingestion.domain.value_objects import DocumentId
from contexts.knowledge_ingestion.infrastructure.models import ChunkModel
from shared.application.tenant_context import TenantId


class SqlAlchemyChunkRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def save_chunks(self, tenant_id: TenantId, document_id: DocumentId,
                    chunks: list[Chunk]) -> None:
        for c in chunks:
            assert c.embedding is not None, "chunk must be embedded before saving"
            self._s.add(ChunkModel(
                tenant_id=tenant_id.value, document_id=document_id.value,
                text_content=c.text, position=c.position,
                embedding_vector=list(c.embedding.vector)))

    def delete_for_document(self, tenant_id: TenantId, document_id: DocumentId) -> None:
        self._s.execute(delete(ChunkModel).where(
            ChunkModel.tenant_id == tenant_id.value,
            ChunkModel.document_id == document_id.value))
