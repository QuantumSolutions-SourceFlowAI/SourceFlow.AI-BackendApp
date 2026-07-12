from dataclasses import dataclass

from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.chatbots.infrastructure.repository import SqlAlchemyChatbotRepository
from contexts.inference.application.ports import HistoryMessage
from contexts.inference.application.rag_service import RagService
from contexts.inference.infrastructure.conversation_repository import ConversationRepository
from shared.application.tenant_context import TenantContext
from shared.domain.errors import NotFoundError


@dataclass(frozen=True)
class ChatResult:
    conversation_id: int
    message_id: int
    answer: str
    grounded: bool
    source: str | None


class Chat:
    def __init__(self, session, rag: RagService) -> None:
        self._session = session
        self._rag = rag

    def execute(self, ctx: TenantContext, chatbot_id: int, question: str,
                conversation_id: int | None) -> ChatResult:
        bot = SqlAlchemyChatbotRepository(self._session).get(ctx.tenant_id, ChatbotId(chatbot_id))
        if bot is None:
            raise NotFoundError("Chatbot no encontrado")
        conv_repo = ConversationRepository(self._session)
        conv_id = conv_repo.get_or_start(ctx.tenant_id.value, chatbot_id, conversation_id)
        history = conv_repo.recent_history(ctx.tenant_id.value, conv_id, 10)
        result = self._rag.answer_question(
            ctx.tenant_id, ChatbotId(chatbot_id), bot.tone, question, bot.purpose, history)
        msg_id = conv_repo.save_turn(
            ctx.tenant_id.value, conv_id, question, result.answer.text,
            result.answer.grounded, result.tokens_used, result.citations)
        return ChatResult(conversation_id=conv_id, message_id=msg_id,
                          answer=result.answer.text, grounded=result.answer.grounded,
                          source=result.source_snapshot)


@dataclass(frozen=True)
class ChatHistoryResult:
    conversation_id: int | None
    messages: list[HistoryMessage]


class GetChatHistory:
    def __init__(self, session) -> None:
        self._session = session

    def execute(self, ctx: TenantContext, chatbot_id: int) -> ChatHistoryResult:
        bot = SqlAlchemyChatbotRepository(self._session).get(ctx.tenant_id, ChatbotId(chatbot_id))
        if bot is None:
            raise NotFoundError("Chatbot no encontrado")
        conv_repo = ConversationRepository(self._session)
        conv_id = conv_repo.latest_conversation_id(ctx.tenant_id.value, chatbot_id)
        if conv_id is None:
            return ChatHistoryResult(conversation_id=None, messages=[])
        messages = conv_repo.conversation_messages(ctx.tenant_id.value, conv_id)
        return ChatHistoryResult(conversation_id=conv_id, messages=messages)
