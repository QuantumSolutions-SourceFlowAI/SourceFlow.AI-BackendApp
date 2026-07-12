from dataclasses import dataclass

from shared.domain.errors import ValidationError
from shared.domain.identity import IntId

EMBEDDING_DIM = 1024


class DocumentId(IntId):
    pass


@dataclass(frozen=True)
class Embedding:
    vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.vector) != EMBEDDING_DIM:
            raise ValidationError(f"Embedding must have {EMBEDDING_DIM} dimensions, got {len(self.vector)}")
