from dataclasses import dataclass

from contexts.chatbots.domain.enums import ChatbotStatus, Tone
from contexts.chatbots.domain.value_objects import ChatbotId
from shared.application.tenant_context import TenantId
from shared.domain.errors import ValidationError


@dataclass
class Chatbot:
    id: ChatbotId | None
    tenant_id: TenantId
    name: str
    tone: Tone
    status: ChatbotStatus = ChatbotStatus.NO_DOCUMENTS
    purpose: str = ""

    def rename(self, new_name: str) -> None:
        if not new_name or not new_name.strip():
            raise ValidationError("Chatbot name cannot be empty")
        self.name = new_name.strip()

    def change_tone(self, tone: Tone) -> None:
        self.tone = tone

    def change_purpose(self, text: str) -> None:
        if len(text) > 2000:
            raise ValidationError("El propósito no puede superar los 2000 caracteres")
        self.purpose = text.strip()

    def mark_ready(self) -> None:
        self.status = ChatbotStatus.READY

    def mark_no_documents(self) -> None:
        self.status = ChatbotStatus.NO_DOCUMENTS
