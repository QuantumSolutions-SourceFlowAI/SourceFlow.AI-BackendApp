from pathlib import Path

from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.knowledge_ingestion.application.ports import ChatbotLookup, DocumentRepository, IngestionQueue
from contexts.knowledge_ingestion.domain.document import Document
from contexts.knowledge_ingestion.domain.enums import DocumentStatus
from sfplatform.config import get_settings
from shared.application.tenant_context import TenantContext
from shared.domain.errors import NotFoundError, ValidationError

MAX_PDF_BYTES = 5 * 1024 * 1024
_PDF_MESSAGE = "Solo se admiten archivos PDF de hasta 5 MB"


def _tmp_path(document_id: int) -> Path:
    upload_dir = Path(get_settings().upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir / f"sourceflow_doc_{document_id}.pdf"


class UploadDocument:
    def __init__(self, repo: DocumentRepository, chatbot_repo: ChatbotLookup,
                queue: IngestionQueue) -> None:
        self._repo = repo
        self._chatbot_repo = chatbot_repo
        self._queue = queue

    def execute(self, ctx: TenantContext, chatbot_id: int, file_name: str,
                content_type: str, data: bytes) -> Document:
        if content_type != "application/pdf" or not file_name.lower().endswith(".pdf"):
            raise ValidationError(_PDF_MESSAGE)
        if len(data) > MAX_PDF_BYTES:
            raise ValidationError(_PDF_MESSAGE)
        bot = self._chatbot_repo.get(ctx.tenant_id, ChatbotId(chatbot_id))
        if bot is None:
            raise NotFoundError("Chatbot not found")
        doc = self._repo.add(Document(
            id=None, tenant_id=ctx.tenant_id, chatbot_id=ChatbotId(chatbot_id),
            file_name=file_name, size_bytes=len(data), status=DocumentStatus.PROCESSING))
        _tmp_path(doc.id.value).write_bytes(data)
        return doc

    def enqueue(self, ctx: TenantContext, doc: Document) -> None:
        # Call only after the caller has committed the transaction that
        # persisted `doc`, so a worker picking up the task immediately
        # is guaranteed to see the document row.
        self._queue.enqueue(doc.id.value, ctx.tenant_id.value, str(_tmp_path(doc.id.value)))


class ListDocuments:
    def __init__(self, repo: DocumentRepository, chatbot_repo: ChatbotLookup) -> None:
        self._repo = repo
        self._chatbot_repo = chatbot_repo

    def execute(self, ctx: TenantContext, chatbot_id: int) -> list[Document]:
        bot = self._chatbot_repo.get(ctx.tenant_id, ChatbotId(chatbot_id))
        if bot is None:
            raise NotFoundError("Chatbot not found")
        return self._repo.list_by_chatbot(ctx.tenant_id, ChatbotId(chatbot_id))
