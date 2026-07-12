from dataclasses import dataclass
from typing import Protocol

from contexts.chatbots.domain.enums import Tone
from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.knowledge_ingestion.domain.value_objects import Embedding
from shared.application.tenant_context import TenantId


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    file_name: str
    text: str
    similarity: float


@dataclass(frozen=True)
class HistoryTurn:
    role: str  # "user" | "assistant"
    text: str


@dataclass(frozen=True)
class HistoryMessage:
    message_id: int
    role: str  # "user" | "assistant"
    text: str
    grounded: bool
    source: str | None


class Retriever(Protocol):
    def retrieve(self, tenant_id: TenantId, chatbot_id: ChatbotId,
                 query_embedding: Embedding, top_k: int, threshold: float) -> list[RetrievedChunk]: ...


class LlmProvider(Protocol):
    def generate(self, question: str, context_blocks: list[str], tone: Tone,
                 purpose: str, history: list["HistoryTurn"]) -> tuple[str, str, int]: ...
