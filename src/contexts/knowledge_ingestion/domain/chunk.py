from dataclasses import dataclass

from contexts.knowledge_ingestion.domain.value_objects import Embedding


@dataclass
class Chunk:
    text: str
    position: int
    embedding: Embedding | None = None
