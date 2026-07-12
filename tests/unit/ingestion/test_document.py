from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.knowledge_ingestion.domain.document import Document
from contexts.knowledge_ingestion.domain.enums import DocumentStatus
from shared.application.tenant_context import TenantId


def _doc():
    return Document(id=None, tenant_id=TenantId(1), chatbot_id=ChatbotId(1),
                    file_name="catalogo.pdf", size_bytes=1000,
                    status=DocumentStatus.PROCESSING)


def test_mark_processed():
    d = _doc()
    d.mark_processed()
    assert d.status is DocumentStatus.READY


def test_mark_error():
    d = _doc()
    d.mark_error()
    assert d.status is DocumentStatus.ERROR
