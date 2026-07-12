from dataclasses import dataclass

from contexts.chatbots.domain.enums import Tone
from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.inference.application.ports import (
    HistoryTurn, LlmProvider, RetrievedChunk, Retriever)
from contexts.inference.domain.value_objects import Answer
from sfplatform.config import get_settings
from shared.application.tenant_context import TenantId


@dataclass(frozen=True)
class RagResult:
    answer: Answer
    citations: list[RetrievedChunk]
    tokens_used: int
    source_snapshot: str | None


class RagService:
    def __init__(self, embeddings, retriever: Retriever, llm: LlmProvider) -> None:
        self._embeddings = embeddings
        self._retriever = retriever
        self._llm = llm

    def answer_question(self, tenant_id: TenantId, chatbot_id: ChatbotId,
                        tone: Tone, question: str, purpose: str,
                        history: list[HistoryTurn]) -> RagResult:
        settings = get_settings()
        q_emb = self._embeddings.embed_one(question)
        tokens = self._embeddings.last_tokens
        hits = self._retriever.retrieve(tenant_id, chatbot_id, q_emb,
                                        settings.retrieval_top_k, settings.similarity_threshold)
        text, source, gen_tokens = self._llm.generate(
            question, [h.text for h in hits], tone, purpose, history)
        tokens += gen_tokens
        if source == "docs" and hits:
            snapshot = f"{hits[0].file_name}: {hits[0].text[:200]}"
            return RagResult(Answer(text, True), hits, tokens, snapshot)
        return RagResult(Answer(text, False), [], tokens, None)
