from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from contexts.inference.application.ports import HistoryMessage, HistoryTurn, RetrievedChunk
from contexts.inference.domain.enums import Sender
from contexts.inference.infrastructure.models import (
    ConversationModel, MessageModel, MessageSourceModel)
from contexts.knowledge_ingestion.infrastructure.models import ChunkModel, DocumentModel


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def start(self, tenant_id: int, chatbot_id: int) -> int:
        conv = ConversationModel(tenant_id=tenant_id, chatbot_id=chatbot_id,
                                 started_at=datetime.now(timezone.utc))
        self._s.add(conv)
        self._s.flush()
        return conv.id

    def get_or_start(self, tenant_id: int, chatbot_id: int, conversation_id: int | None) -> int:
        if conversation_id is None:
            return self.start(tenant_id, chatbot_id)
        found = self._s.scalar(select(ConversationModel.id).where(
            ConversationModel.id == conversation_id,
            ConversationModel.tenant_id == tenant_id,
            ConversationModel.chatbot_id == chatbot_id))
        return conversation_id if found else self.start(tenant_id, chatbot_id)

    def save_turn(self, tenant_id: int, conversation_id: int, question: str,
                  answer_text: str, grounded: bool, tokens_used: int,
                  citations: list[RetrievedChunk]) -> int:
        self._s.add(MessageModel(tenant_id=tenant_id, conversation_id=conversation_id,
                                 sender=Sender.CUSTOMER, content=question))
        assistant = MessageModel(tenant_id=tenant_id, conversation_id=conversation_id,
                                 sender=Sender.ASSISTANT, content=answer_text,
                                 answer_text=answer_text, answer_grounded=grounded,
                                 tokens_used=tokens_used)
        self._s.add(assistant)
        self._s.flush()
        for c in citations:
            self._s.add(MessageSourceModel(message_id=assistant.id, chunk_id=c.chunk_id))
        return assistant.id

    def recent_history(self, tenant_id: int, conversation_id: int,
                       limit: int = 10) -> list[HistoryTurn]:
        rows = self._s.execute(
            select(MessageModel.sender, MessageModel.content)
            .where(MessageModel.tenant_id == tenant_id,
                   MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.id.desc())
            .limit(limit)
        ).all()
        return [
            HistoryTurn(role="user" if sender == Sender.CUSTOMER else "assistant", text=content)
            for sender, content in reversed(rows)
        ]

    def latest_conversation_id(self, tenant_id: int, chatbot_id: int) -> int | None:
        return self._s.scalar(
            select(ConversationModel.id)
            .where(ConversationModel.tenant_id == tenant_id,
                   ConversationModel.chatbot_id == chatbot_id)
            .order_by(ConversationModel.id.desc())
            .limit(1)
        )

    def conversation_messages(self, tenant_id: int,
                              conversation_id: int) -> list[HistoryMessage]:
        rows = self._s.execute(
            select(MessageModel.id, MessageModel.sender, MessageModel.content,
                   MessageModel.answer_grounded)
            .where(MessageModel.tenant_id == tenant_id,
                   MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.id.asc())
        ).all()
        messages: list[HistoryMessage] = []
        for msg_id, sender, content, grounded in rows:
            role = "user" if sender == Sender.CUSTOMER else "assistant"
            is_grounded = bool(grounded)
            source = self._first_source(msg_id) if role == "assistant" and is_grounded else None
            messages.append(HistoryMessage(message_id=msg_id, role=role, text=content,
                                           grounded=is_grounded, source=source))
        return messages

    def _first_source(self, message_id: int) -> str | None:
        row = self._s.execute(
            select(DocumentModel.file_name, ChunkModel.text_content)
            .select_from(MessageSourceModel)
            .join(ChunkModel, ChunkModel.id == MessageSourceModel.chunk_id)
            .join(DocumentModel, DocumentModel.id == ChunkModel.document_id)
            .where(MessageSourceModel.message_id == message_id)
            .order_by(MessageSourceModel.id.asc())
            .limit(1)
        ).first()
        if row is None:
            return None
        file_name, text_content = row
        return f"{file_name}: {text_content[:200]}"
