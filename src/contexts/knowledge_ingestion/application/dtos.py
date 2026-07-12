from dataclasses import dataclass

from contexts.knowledge_ingestion.domain.document import Document


@dataclass(frozen=True)
class DocumentView:
    id: int
    file_name: str
    size_bytes: int
    status: str

    @staticmethod
    def of(doc: Document) -> "DocumentView":
        return DocumentView(id=doc.id.value, file_name=doc.file_name,
                            size_bytes=doc.size_bytes, status=doc.status.value)
