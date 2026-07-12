from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from contexts.chatbots.infrastructure.repository import SqlAlchemyChatbotRepository
from contexts.knowledge_ingestion.application.dtos import DocumentView
from contexts.knowledge_ingestion.application.use_cases import ListDocuments, UploadDocument
from contexts.knowledge_ingestion.infrastructure.document_repository import SqlAlchemyDocumentRepository
from sfplatform.db import get_session
from sfplatform.middleware import get_tenant_context
from shared.application.tenant_context import TenantContext

router = APIRouter(prefix="/chatbots/{chatbot_id}/documents", tags=["documents"])


class CeleryIngestionQueue:
    def enqueue(self, document_id: int, tenant_id: int, file_path: str) -> None:
        from contexts.knowledge_ingestion.infrastructure.celery_tasks import ingest_document_task
        ingest_document_task.delay(document_id, tenant_id, file_path)


@router.post("", status_code=201)
async def upload(chatbot_id: int, file: UploadFile,
                 ctx: TenantContext = Depends(get_tenant_context),
                 session: Session = Depends(get_session)) -> dict:
    data = await file.read()
    use_case = UploadDocument(SqlAlchemyDocumentRepository(session),
                              SqlAlchemyChatbotRepository(session), CeleryIngestionQueue())
    doc = use_case.execute(ctx, chatbot_id, file.filename or "", file.content_type or "", data)
    session.commit()
    use_case.enqueue(ctx, doc)
    return {"id": doc.id.value, "file_name": doc.file_name, "status": doc.status.value}


@router.get("")
def list_documents(chatbot_id: int,
                   ctx: TenantContext = Depends(get_tenant_context),
                   session: Session = Depends(get_session)) -> list[dict]:
    use_case = ListDocuments(SqlAlchemyDocumentRepository(session),
                             SqlAlchemyChatbotRepository(session))
    docs = use_case.execute(ctx, chatbot_id)
    return [DocumentView.of(d).__dict__ for d in docs]
