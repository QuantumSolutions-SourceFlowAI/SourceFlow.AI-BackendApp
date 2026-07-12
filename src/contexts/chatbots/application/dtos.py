from dataclasses import dataclass

from contexts.chatbots.domain.chatbot import Chatbot


@dataclass(frozen=True)
class ChatbotView:
    id: int
    name: str
    tone: str
    status: str
    purpose: str

    @staticmethod
    def of(bot: Chatbot) -> "ChatbotView":
        return ChatbotView(id=bot.id.value, name=bot.name, tone=bot.tone.value,
                           status=bot.status.value, purpose=bot.purpose)
