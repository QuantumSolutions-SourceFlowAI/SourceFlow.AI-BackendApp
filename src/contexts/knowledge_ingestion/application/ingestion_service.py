from sqlalchemy.orm import Session

from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.chatbots.infrastructure.repository import SqlAlchemyChatbotRepository
from contexts.knowledge_ingestion.domain.chunk import Chunk
from contexts.knowledge_ingestion.domain.value_objects import DocumentId
from contexts.knowledge_ingestion.infrastructure.chunk_repository import SqlAlchemyChunkRepository
from contexts.knowledge_ingestion.infrastructure.chunker import chunk_text
from contexts.knowledge_ingestion.infrastructure.document_repository import SqlAlchemyDocumentRepository
from sfplatform.config import get_settings
from shared.application.tenant_context import TenantId


def process_document(session: Session, document_id: int, tenant_id: int,
                     extracted_text: str, embedding_provider) -> None:
    settings = get_settings()
    doc_repo = SqlAlchemyDocumentRepository(session)
    chunk_repo = SqlAlchemyChunkRepository(session)
    chatbot_repo = SqlAlchemyChatbotRepository(session)
    tid = TenantId(tenant_id)
    did = DocumentId(document_id)
    doc = doc_repo.get(tid, did)
    if doc is None:
        return
    try:
        pieces = chunk_text(extracted_text, settings.chunk_size_tokens, settings.chunk_overlap_tokens)
        if not pieces:
            raise ValueError("No extractable text")
        embeddings = embedding_provider.embed(pieces)
        chunks = [Chunk(text=t, position=i, embedding=e)
                  for i, (t, e) in enumerate(zip(pieces, embeddings, strict=True))]
        chunk_repo.delete_for_document(tid, did)
        chunk_repo.save_chunks(tid, did, chunks)
        doc.mark_processed()
        doc_repo.update(doc)
        _set_chatbot_ready(chatbot_repo, tid, doc.chatbot_id)
    except Exception:
        session.rollback()
        doc.mark_error()
        doc_repo.update(doc)


def _set_chatbot_ready(chatbot_repo: SqlAlchemyChatbotRepository, tenant_id: TenantId,
                       chatbot_id: ChatbotId) -> None:
    bot = chatbot_repo.get(tenant_id, chatbot_id)
    if bot:
        bot.mark_ready()
        chatbot_repo.update(bot)
