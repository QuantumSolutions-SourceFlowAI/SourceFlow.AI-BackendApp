from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from contexts.chatbots.domain.chatbot import Chatbot
from contexts.chatbots.domain.enums import ChatbotStatus, Tone
from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.chatbots.infrastructure.models import ChatbotModel
from shared.application.tenant_context import TenantId


def _to_domain(m: ChatbotModel) -> Chatbot:
    return Chatbot(id=ChatbotId(m.id), tenant_id=TenantId(m.tenant_id), name=m.name,
                   tone=Tone(m.tone), status=ChatbotStatus(m.status), purpose=m.purpose)


class SqlAlchemyChatbotRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, bot: Chatbot) -> Chatbot:
        m = ChatbotModel(tenant_id=bot.tenant_id.value, name=bot.name,
                         tone=bot.tone, status=bot.status, purpose=bot.purpose)
        self._s.add(m)
        self._s.flush()
        bot.id = ChatbotId(m.id)
        return bot

    def get(self, tenant_id: TenantId, chatbot_id: ChatbotId) -> Chatbot | None:
        m = self._s.scalar(select(ChatbotModel).where(
            ChatbotModel.id == chatbot_id.value,
            ChatbotModel.tenant_id == tenant_id.value))
        return _to_domain(m) if m else None

    def list(self, tenant_id: TenantId) -> list[Chatbot]:
        rows = self._s.scalars(select(ChatbotModel).where(
            ChatbotModel.tenant_id == tenant_id.value).order_by(ChatbotModel.id)).all()
        return [_to_domain(m) for m in rows]

    def exists_name(self, tenant_id: TenantId, name: str) -> bool:
        return self._s.scalar(select(ChatbotModel.id).where(
            ChatbotModel.tenant_id == tenant_id.value,
            ChatbotModel.name == name)) is not None

    def update(self, bot: Chatbot) -> None:
        m = self._s.scalar(select(ChatbotModel).where(
            ChatbotModel.id == bot.id.value,
            ChatbotModel.tenant_id == bot.tenant_id.value))
        if m:
            m.name, m.tone, m.status, m.purpose = bot.name, bot.tone, bot.status, bot.purpose

    def delete(self, tenant_id: TenantId, chatbot_id: ChatbotId) -> None:
        self._s.execute(delete(ChatbotModel).where(
            ChatbotModel.id == chatbot_id.value,
            ChatbotModel.tenant_id == tenant_id.value))
