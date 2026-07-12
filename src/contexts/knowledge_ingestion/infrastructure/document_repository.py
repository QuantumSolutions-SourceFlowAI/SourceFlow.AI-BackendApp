from sqlalchemy import select
from sqlalchemy.orm import Session

from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.knowledge_ingestion.domain.document import Document
from contexts.knowledge_ingestion.domain.enums import DocumentStatus
from contexts.knowledge_ingestion.domain.value_objects import DocumentId
from contexts.knowledge_ingestion.infrastructure.models import DocumentModel
from shared.application.tenant_context import TenantId


def _to_domain(m: DocumentModel) -> Document:
    return Document(id=DocumentId(m.id), tenant_id=TenantId(m.tenant_id),
                    chatbot_id=ChatbotId(m.chatbot_id), file_name=m.file_name,
                    size_bytes=m.size_bytes, status=DocumentStatus(m.status))


class SqlAlchemyDocumentRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, doc: Document) -> Document:
        m = DocumentModel(tenant_id=doc.tenant_id.value, chatbot_id=doc.chatbot_id.value,
                          file_name=doc.file_name, size_bytes=doc.size_bytes, status=doc.status)
        self._s.add(m)
        self._s.flush()
        doc.id = DocumentId(m.id)
        return doc

    def get(self, tenant_id: TenantId, document_id: DocumentId) -> Document | None:
        m = self._s.scalar(select(DocumentModel).where(
            DocumentModel.id == document_id.value,
            DocumentModel.tenant_id == tenant_id.value))
        return _to_domain(m) if m else None

    def update(self, doc: Document) -> None:
        m = self._s.scalar(select(DocumentModel).where(
            DocumentModel.id == doc.id.value,
            DocumentModel.tenant_id == doc.tenant_id.value))
        if m:
            m.status = doc.status

    def has_ready_document(self, tenant_id: TenantId, chatbot_id: ChatbotId) -> bool:
        return self._s.scalar(select(DocumentModel.id).where(
            DocumentModel.tenant_id == tenant_id.value,
            DocumentModel.chatbot_id == chatbot_id.value,
            DocumentModel.status == DocumentStatus.READY)) is not None

    def list_by_chatbot(self, tenant_id: TenantId,
                        chatbot_id: ChatbotId) -> list[Document]:
        rows = self._s.scalars(select(DocumentModel).where(
            DocumentModel.tenant_id == tenant_id.value,
            DocumentModel.chatbot_id == chatbot_id.value,
        ).order_by(DocumentModel.id)).all()
        return [_to_domain(m) for m in rows]
