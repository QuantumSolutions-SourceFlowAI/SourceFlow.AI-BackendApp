from dataclasses import dataclass, field

from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.inference.domain.message import Message
from contexts.inference.domain.value_objects import ConversationId
from shared.application.tenant_context import TenantId


@dataclass
class Conversation:
    id: ConversationId | None
    tenant_id: TenantId
    chatbot_id: ChatbotId
    messages: list[Message] = field(default_factory=list)

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
