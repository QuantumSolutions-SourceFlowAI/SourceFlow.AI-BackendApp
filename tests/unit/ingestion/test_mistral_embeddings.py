from unittest.mock import MagicMock

from contexts.knowledge_ingestion.infrastructure.mistral_embeddings import MistralEmbeddingProvider


def _fake_response(n_vectors):
    resp = MagicMock()
    resp.data = [MagicMock(embedding=[0.0] * 1024) for _ in range(n_vectors)]
    resp.usage = MagicMock(total_tokens=42)
    return resp


def test_embed_returns_embeddings_and_records_tokens():
    provider = MistralEmbeddingProvider(api_key="x", model="mistral-embed")
    provider._client = MagicMock()
    provider._client.embeddings.create.return_value = _fake_response(2)

    result = provider.embed(["a", "b"])
    assert len(result) == 2
    assert len(result[0].vector) == 1024
    assert provider.last_tokens == 42
