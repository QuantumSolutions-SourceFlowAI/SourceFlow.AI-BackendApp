from sqlalchemy import text
from sqlalchemy.orm import Session

from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.inference.application.ports import RetrievedChunk
from contexts.knowledge_ingestion.domain.value_objects import Embedding
from shared.application.tenant_context import TenantId


class PgVectorRetriever:
    def __init__(self, session: Session, embedding_provider) -> None:
        self._s = session
        self._embeddings = embedding_provider

    def retrieve(self, tenant_id: TenantId, chatbot_id: ChatbotId,
                 query_embedding: Embedding, top_k: int, threshold: float) -> list[RetrievedChunk]:
        qvec = str(list(query_embedding.vector))
        rows = self._s.execute(text("""
            SELECT c.id, c.document_id, d.file_name, c.text_content,
                   1 - (c.embedding_vector <=> :qvec) AS similarity
            FROM chunk c
            JOIN document d ON d.id = c.document_id
            WHERE c.tenant_id = :tid AND d.chatbot_id = :cid
            ORDER BY c.embedding_vector <=> :qvec
            LIMIT :k
        """), {"qvec": qvec, "tid": tenant_id.value, "cid": chatbot_id.value, "k": top_k}).all()
        return [RetrievedChunk(chunk_id=r[0], document_id=r[1], file_name=r[2],
                               text=r[3], similarity=float(r[4]))
                for r in rows if float(r[4]) >= threshold]
