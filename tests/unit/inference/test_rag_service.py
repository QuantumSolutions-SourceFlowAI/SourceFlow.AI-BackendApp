from contexts.chatbots.domain.enums import Tone
from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.inference.application.ports import RetrievedChunk
from contexts.inference.application.rag_service import RagService
from contexts.knowledge_ingestion.domain.value_objects import Embedding
from shared.application.tenant_context import TenantId


class FakeEmbeddings:
    last_tokens = 5
    def embed_one(self, text):
        return Embedding(tuple(0.1 for _ in range(1024)))
    def embed(self, texts):
        return [self.embed_one(t) for t in texts]


class NoHitRetriever:
    def retrieve(self, *a, **k):
        return []


class OneHitRetriever:
    def retrieve(self, *a, **k):
        return [RetrievedChunk(1, 1, "catalogo.pdf", "el precio es 100", 0.9)]


class SpyLlm:
    """Records the call and returns a configurable (text, source, tokens)."""
    def __init__(self, source="docs", text="respuesta"):
        self.called = False
        self.last_history = None
        self.last_purpose = None
        self._source = source
        self._text = text
    def generate(self, question, context_blocks, tone, purpose, history):
        self.called = True
        self.last_history = history
        self.last_purpose = purpose
        return (self._text, self._source, 20)


def test_docs_source_with_hit_is_grounded_with_citation():
    llm = SpyLlm(source="docs")
    svc = RagService(FakeEmbeddings(), OneHitRetriever(), llm)
    res = svc.answer_question(TenantId(1), ChatbotId(1), Tone.FORMAL, "algo?", "Soporte", [])
    assert res.answer.grounded is True
    assert res.answer.text == "respuesta"
    assert res.citations[0].file_name == "catalogo.pdf"
    assert res.source_snapshot.startswith("catalogo.pdf:")
    assert res.tokens_used == 25  # 5 embed + 20 gen


def test_llm_is_always_called_even_without_hits():
    llm = SpyLlm(source="chat", text="¡Hola!")
    svc = RagService(FakeEmbeddings(), NoHitRetriever(), llm)
    res = svc.answer_question(TenantId(1), ChatbotId(1), Tone.FORMAL, "hola", "Soporte", [])
    assert llm.called is True
    assert res.answer.grounded is False
    assert res.answer.text == "¡Hola!"
    assert res.citations == []
    assert res.source_snapshot is None


def test_general_source_with_hits_is_not_grounded():
    llm = SpyLlm(source="general")
    svc = RagService(FakeEmbeddings(), OneHitRetriever(), llm)
    res = svc.answer_question(TenantId(1), ChatbotId(1), Tone.FORMAL, "algo?", "Soporte", [])
    assert res.answer.grounded is False
    assert res.citations == []
    assert res.source_snapshot is None


def test_docs_source_without_hits_degrades_to_ungrounded():
    llm = SpyLlm(source="docs")
    svc = RagService(FakeEmbeddings(), NoHitRetriever(), llm)
    res = svc.answer_question(TenantId(1), ChatbotId(1), Tone.FORMAL, "algo?", "Soporte", [])
    assert res.answer.grounded is False
    assert res.citations == []


def test_purpose_and_history_are_forwarded_to_llm():
    from contexts.inference.application.ports import HistoryTurn
    llm = SpyLlm(source="docs")
    svc = RagService(FakeEmbeddings(), OneHitRetriever(), llm)
    hist = [HistoryTurn("user", "hola"), HistoryTurn("assistant", "¡Hola!")]
    svc.answer_question(TenantId(1), ChatbotId(1), Tone.FORMAL, "precio?", "MiDominio", hist)
    assert llm.last_purpose == "MiDominio"
    assert llm.last_history == hist
