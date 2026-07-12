from typing import Protocol

from contexts.chatbots.domain.chatbot import Chatbot
from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.knowledge_ingestion.domain.chunk import Chunk
from contexts.knowledge_ingestion.domain.document import Document
from contexts.knowledge_ingestion.domain.value_objects import DocumentId, Embedding
from shared.application.tenant_context import TenantId


class EmbeddingProvider(Protocol):
    last_tokens: int
    def embed(self, texts: list[str]) -> list[Embedding]: ...
    def embed_one(self, text: str) -> Embedding: ...


class DocumentRepository(Protocol):
    def add(self, doc: Document) -> Document: ...
    def get(self, tenant_id: TenantId, document_id: DocumentId) -> Document | None: ...
    def update(self, doc: Document) -> None: ...
    def has_ready_document(self, tenant_id: TenantId, chatbot_id: ChatbotId) -> bool: ...
    def list_by_chatbot(self, tenant_id: TenantId,
                        chatbot_id: ChatbotId) -> list[Document]: ...


class ChunkRepository(Protocol):
    def save_chunks(self, tenant_id: TenantId, document_id: DocumentId,
                    chunks: list[Chunk]) -> None: ...
    def delete_for_document(self, tenant_id: TenantId, document_id: DocumentId) -> None: ...


class IngestionQueue(Protocol):
    def enqueue(self, document_id: int, tenant_id: int, file_path: str) -> None: ...


class ChatbotLookup(Protocol):
    def get(self, tenant_id: TenantId, chatbot_id: ChatbotId) -> Chatbot | None: ...
