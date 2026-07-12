from contexts.chatbots.application.ports import ChatbotRepository
from contexts.chatbots.domain.chatbot import Chatbot
from contexts.chatbots.domain.enums import ChatbotStatus, Tone
from contexts.chatbots.domain.value_objects import ChatbotId
from shared.application.tenant_context import TenantContext
from shared.domain.errors import InvariantViolation, NotFoundError, ValidationError


class CreateChatbot:
    def __init__(self, repo: ChatbotRepository) -> None:
        self._repo = repo

    def execute(self, ctx: TenantContext, name: str, tone: Tone, purpose: str = "") -> Chatbot:
        stripped_name = name.strip()
        if not stripped_name:
            raise ValidationError("Chatbot name cannot be empty")
        if self._repo.exists_name(ctx.tenant_id, stripped_name):
            raise InvariantViolation("Ya existe un chatbot con ese nombre")
        bot = Chatbot(id=None, tenant_id=ctx.tenant_id, name=stripped_name, tone=tone,
                      status=ChatbotStatus.NO_DOCUMENTS)
        bot.change_purpose(purpose)
        return self._repo.add(bot)


class ListChatbots:
    def __init__(self, repo: ChatbotRepository) -> None:
        self._repo = repo

    def execute(self, ctx: TenantContext) -> list[Chatbot]:
        return self._repo.list(ctx.tenant_id)


class UpdateChatbot:
    """Handles rename and/or tone change (HU-01 rename, HU-10 tone)."""

    def __init__(self, repo: ChatbotRepository) -> None:
        self._repo = repo

    def execute(self, ctx: TenantContext, chatbot_id: int, name: str | None,
                tone: Tone | None, purpose: str | None = None) -> Chatbot:
        bot = self._repo.get(ctx.tenant_id, ChatbotId(chatbot_id))
        if bot is None:
            raise NotFoundError("Chatbot no encontrado")
        if name is not None:
            if name.strip() != bot.name and self._repo.exists_name(ctx.tenant_id, name.strip()):
                raise InvariantViolation("Ya existe un chatbot con ese nombre")
            bot.rename(name)
        if tone is not None:
            bot.change_tone(tone)
        if purpose is not None:
            bot.change_purpose(purpose)
        self._repo.update(bot)
        return bot


class DeleteChatbot:
    def __init__(self, repo: ChatbotRepository) -> None:
        self._repo = repo

    def execute(self, ctx: TenantContext, chatbot_id: int) -> None:
        self._repo.delete(ctx.tenant_id, ChatbotId(chatbot_id))
