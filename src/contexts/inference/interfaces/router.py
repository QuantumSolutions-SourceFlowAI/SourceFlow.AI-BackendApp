from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from contexts.inference.application.rag_service import RagService
from contexts.inference.application.use_cases import Chat, GetChatHistory
from contexts.inference.infrastructure.mistral_llm import MistralLlmProvider
from contexts.inference.infrastructure.retrieval import PgVectorRetriever
from contexts.knowledge_ingestion.infrastructure.mistral_embeddings import MistralEmbeddingProvider
from sfplatform.config import get_settings
from sfplatform.db import get_session
from sfplatform.middleware import get_tenant_context
from shared.application.tenant_context import TenantContext

router = APIRouter(prefix="/chatbots/{chatbot_id}", tags=["chat"])


class ChatBody(BaseModel):
    question: str
    conversation_id: int | None = None


# Seams overridable in tests:
def build_embeddings():
    s = get_settings()
    return MistralEmbeddingProvider(s.mistral_api_key, s.embedding_model)


def build_retriever(session, embeddings):
    return PgVectorRetriever(session, embeddings)


def build_llm():
    s = get_settings()
    return MistralLlmProvider(s.mistral_api_key, s.generation_model)


@router.post("/chat")
def chat(chatbot_id: int, body: ChatBody,
         ctx: TenantContext = Depends(get_tenant_context),
         session: Session = Depends(get_session)) -> dict:
    embeddings = build_embeddings()
    rag = RagService(embeddings, build_retriever(session, embeddings), build_llm())
    result = Chat(session, rag).execute(ctx, chatbot_id, body.question, body.conversation_id)
    session.commit()
    return {"conversation_id": result.conversation_id, "message_id": result.message_id,
            "answer": result.answer, "grounded": result.grounded, "source": result.source}


@router.get("/chat/history")
def chat_history(chatbot_id: int,
                 ctx: TenantContext = Depends(get_tenant_context),
                 session: Session = Depends(get_session)) -> dict:
    result = GetChatHistory(session).execute(ctx, chatbot_id)
    return {
        "conversation_id": result.conversation_id,
        "messages": [
            {"message_id": m.message_id, "role": m.role, "text": m.text,
             "grounded": m.grounded, "source": m.source}
            for m in result.messages
        ],
    }
