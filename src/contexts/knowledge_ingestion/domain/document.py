from dataclasses import dataclass

from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.knowledge_ingestion.domain.enums import DocumentStatus
from contexts.knowledge_ingestion.domain.value_objects import DocumentId
from shared.application.tenant_context import TenantId


@dataclass
class Document:
    id: DocumentId | None
    tenant_id: TenantId
    chatbot_id: ChatbotId
    file_name: str
    size_bytes: int
    status: DocumentStatus = DocumentStatus.PROCESSING

    def mark_processed(self) -> None:
        self.status = DocumentStatus.READY

    def mark_error(self) -> None:
        self.status = DocumentStatus.ERROR
