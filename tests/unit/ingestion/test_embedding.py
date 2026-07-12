import pytest
from contexts.knowledge_ingestion.domain.value_objects import Embedding
from shared.domain.errors import ValidationError


def test_embedding_accepts_1024():
    e = Embedding(tuple(0.0 for _ in range(1024)))
    assert len(e.vector) == 1024


def test_embedding_rejects_wrong_dimension():
    with pytest.raises(ValidationError):
        Embedding(tuple(0.0 for _ in range(512)))
