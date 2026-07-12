from mistralai.client import Mistral

from contexts.knowledge_ingestion.domain.value_objects import Embedding


class MistralEmbeddingProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = Mistral(api_key=api_key)
        self._model = model
        self.last_tokens = 0

    def embed(self, texts: list[str]) -> list[Embedding]:
        resp = self._client.embeddings.create(model=self._model, inputs=texts)
        self.last_tokens = getattr(getattr(resp, "usage", None), "total_tokens", 0) or 0
        return [Embedding(tuple(float(x) for x in item.embedding)) for item in resp.data]

    def embed_one(self, text: str) -> Embedding:
        return self.embed([text])[0]
