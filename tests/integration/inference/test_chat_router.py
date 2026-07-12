from sqlalchemy import text

from contexts.inference.application.ports import RetrievedChunk
from contexts.inference.interfaces import router as chat_router_mod
from sfplatform.db import SessionLocal


class FakeEmbeddings:
    last_tokens = 4
    def embed_one(self, q):
        from contexts.knowledge_ingestion.domain.value_objects import Embedding
        return Embedding(tuple(0.1 for _ in range(1024)))
    def embed(self, texts):
        return [self.embed_one(t) for t in texts]


class HitRetriever:
    """Fakes a retrieval hit against a real chunk row (message_source.chunk_id
    is FK-constrained to chunk.id, so the citation must point at a real row)."""
    def __init__(self, chunk_id):
        self._chunk_id = chunk_id
    def retrieve(self, *a, **k):
        return [RetrievedChunk(self._chunk_id, 1, "catalogo.pdf", "el precio es 100 soles", 0.95)]


class NoHitRetriever:
    def retrieve(self, *a, **k):
        return []


class FakeLlm:
    """Returns a fixed (text, source, tokens); records the history it received."""
    def __init__(self, text="El precio es 100 soles.", source="docs"):
        self._text = text
        self._source = source
        self.last_history = None
    def generate(self, question, blocks, tone, purpose, history):
        self.last_history = history
        return (self._text, self._source, 15)


def _chatbot():
    with SessionLocal() as s:
        # tenant_id+name is unique (see migration 0002); clean up before each
        # test so the two tests in this module don't collide on 'ChatBot'.
        s.execute(text("DELETE FROM chatbot WHERE name='ChatBot'"))
        s.execute(text("INSERT INTO chatbot (tenant_id,name,tone,status,purpose) "
                       "VALUES (1,'ChatBot','friendly','ready','Soporte de ventas')"))
        s.commit()
        return s.execute(text("SELECT id FROM chatbot WHERE name='ChatBot'")).scalar()


def _chatbot_b():
    with SessionLocal() as s:
        # distinct name from _chatbot()'s 'ChatBot' so both fixtures can coexist
        # under the (tenant_id, name) unique constraint; clean up before each test.
        s.execute(text("DELETE FROM chatbot WHERE name='ChatBotB'"))
        s.execute(text("INSERT INTO chatbot (tenant_id,name,tone,status,purpose) "
                       "VALUES (1,'ChatBotB','friendly','ready','')"))
        s.commit()
        return s.execute(text("SELECT id FROM chatbot WHERE name='ChatBotB'")).scalar()


def _seed_chunk(chatbot_id):
    """Insert a real document+chunk row so a citation can reference a valid chunk_id."""
    with SessionLocal() as s:
        s.execute(text("INSERT INTO document (tenant_id,chatbot_id,file_name,size_bytes,status) "
                       "VALUES (1,:c,'catalogo.pdf',10,'ready')"), {"c": chatbot_id})
        did = s.execute(text("SELECT id FROM document WHERE chatbot_id=:c ORDER BY id DESC LIMIT 1"),
                       {"c": chatbot_id}).scalar()
        s.execute(text("INSERT INTO chunk (tenant_id,document_id,text_content,position,embedding_vector) "
                       "VALUES (1,:d,'el precio es 100 soles',0,:v)"),
                  {"d": did, "v": str([0.1] * 1024)})
        s.commit()
        return s.execute(text("SELECT id FROM chunk WHERE document_id=:d"), {"d": did}).scalar()


def test_chat_returns_grounded_answer_with_source(client, monkeypatch):
    cid = _chatbot()
    chunk_id = _seed_chunk(cid)
    monkeypatch.setattr(chat_router_mod, "build_embeddings", lambda: FakeEmbeddings())
    monkeypatch.setattr(chat_router_mod, "build_retriever", lambda session, emb: HitRetriever(chunk_id))
    monkeypatch.setattr(chat_router_mod, "build_llm", lambda: FakeLlm(source="docs"))
    r = client.post(f"/chatbots/{cid}/chat", json={"question": "¿Cuál es el precio?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["grounded"] is True
    assert body["answer"] == "El precio es 100 soles."
    assert body["source"].startswith("catalogo.pdf")
    # persisted assistant message with tokens and a citation row
    with SessionLocal() as s:
        cnt = s.execute(text("SELECT count(*) FROM message_source ms JOIN message m ON m.id=ms.message_id "
                             "WHERE m.id=:mid"), {"mid": body["message_id"]}).scalar()
    assert cnt == 1


def test_chat_greeting_is_conversational_and_ungrounded(client, monkeypatch):
    cid = _chatbot()
    monkeypatch.setattr(chat_router_mod, "build_embeddings", lambda: FakeEmbeddings())
    monkeypatch.setattr(chat_router_mod, "build_retriever", lambda session, emb: NoHitRetriever())
    monkeypatch.setattr(chat_router_mod, "build_llm",
                        lambda: FakeLlm(text="¡Hola! ¿En qué te ayudo?", source="chat"))
    r = client.post(f"/chatbots/{cid}/chat", json={"question": "hola"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["grounded"] is False
    assert body["source"] is None
    assert body["answer"] == "¡Hola! ¿En qué te ayudo?"


def test_chat_general_knowledge_fallback_is_ungrounded_but_answers(client, monkeypatch):
    cid = _chatbot()
    monkeypatch.setattr(chat_router_mod, "build_embeddings", lambda: FakeEmbeddings())
    monkeypatch.setattr(chat_router_mod, "build_retriever", lambda session, emb: NoHitRetriever())
    monkeypatch.setattr(chat_router_mod, "build_llm",
                        lambda: FakeLlm(text="En general, Git es un control de versiones.", source="general"))
    r = client.post(f"/chatbots/{cid}/chat", json={"question": "¿qué es git?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["grounded"] is False
    assert body["answer"].startswith("En general")


def test_chat_passes_prior_history_to_llm(client, monkeypatch):
    cid = _chatbot()
    fake_llm = FakeLlm(text="ok", source="chat")
    monkeypatch.setattr(chat_router_mod, "build_embeddings", lambda: FakeEmbeddings())
    monkeypatch.setattr(chat_router_mod, "build_retriever", lambda session, emb: NoHitRetriever())
    monkeypatch.setattr(chat_router_mod, "build_llm", lambda: fake_llm)

    r1 = client.post(f"/chatbots/{cid}/chat", json={"question": "hola"})
    conv_id = r1.json()["conversation_id"]
    assert fake_llm.last_history == []  # first turn: no prior history

    client.post(f"/chatbots/{cid}/chat", json={"question": "¿y ahora?", "conversation_id": conv_id})
    # second turn sees the two messages from the first turn, in order
    assert [(t.role, t.text) for t in fake_llm.last_history] == [
        ("user", "hola"), ("assistant", "ok")]


def test_chat_continues_existing_conversation(client, monkeypatch):
    cid = _chatbot()
    chunk_id = _seed_chunk(cid)
    monkeypatch.setattr(chat_router_mod, "build_embeddings", lambda: FakeEmbeddings())
    monkeypatch.setattr(chat_router_mod, "build_retriever", lambda session, emb: HitRetriever(chunk_id))
    monkeypatch.setattr(chat_router_mod, "build_llm", lambda: FakeLlm(source="docs"))

    r1 = client.post(f"/chatbots/{cid}/chat", json={"question": "¿Cuál es el precio?"})
    assert r1.status_code == 200, r1.text
    conv_id = r1.json()["conversation_id"]

    r2 = client.post(f"/chatbots/{cid}/chat",
                     json={"question": "¿Y el envío?", "conversation_id": conv_id})
    assert r2.status_code == 200, r2.text
    assert r2.json()["conversation_id"] == conv_id

    with SessionLocal() as s:
        cnt = s.execute(text("SELECT count(*) FROM message WHERE conversation_id=:c"),
                        {"c": conv_id}).scalar()
    assert cnt == 4


def test_chat_conversation_id_of_other_chatbot_starts_new_conversation(client, monkeypatch):
    cid_a = _chatbot()
    chunk_id = _seed_chunk(cid_a)
    cid_b = _chatbot_b()
    monkeypatch.setattr(chat_router_mod, "build_embeddings", lambda: FakeEmbeddings())
    monkeypatch.setattr(chat_router_mod, "build_retriever", lambda session, emb: HitRetriever(chunk_id))
    monkeypatch.setattr(chat_router_mod, "build_llm", lambda: FakeLlm(source="docs"))

    r1 = client.post(f"/chatbots/{cid_a}/chat", json={"question": "¿Cuál es el precio?"})
    assert r1.status_code == 200, r1.text
    conv_id_a = r1.json()["conversation_id"]

    r2 = client.post(f"/chatbots/{cid_b}/chat",
                     json={"question": "hola", "conversation_id": conv_id_a})
    assert r2.status_code == 200, r2.text
    conv_id_b = r2.json()["conversation_id"]
    assert conv_id_b != conv_id_a

    with SessionLocal() as s:
        cnt_a = s.execute(text("SELECT count(*) FROM message WHERE conversation_id=:c"),
                          {"c": conv_id_a}).scalar()
    assert cnt_a == 2


def test_chat_history_returns_prior_messages_with_source(client, monkeypatch):
    cid = _chatbot()
    chunk_id = _seed_chunk(cid)
    monkeypatch.setattr(chat_router_mod, "build_embeddings", lambda: FakeEmbeddings())
    monkeypatch.setattr(chat_router_mod, "build_retriever", lambda session, emb: HitRetriever(chunk_id))
    monkeypatch.setattr(chat_router_mod, "build_llm", lambda: FakeLlm(source="docs"))
    client.post(f"/chatbots/{cid}/chat", json={"question": "¿Cuál es el precio?"})

    r = client.get(f"/chatbots/{cid}/chat/history")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["conversation_id"] is not None
    assert [(m["role"], m["text"]) for m in body["messages"]] == [
        ("user", "¿Cuál es el precio?"),
        ("assistant", "El precio es 100 soles."),
    ]
    assert body["messages"][1]["grounded"] is True
    assert body["messages"][1]["source"].startswith("catalogo.pdf")
    assert body["messages"][0]["source"] is None


def test_chat_history_greeting_has_null_source(client, monkeypatch):
    cid = _chatbot()
    monkeypatch.setattr(chat_router_mod, "build_embeddings", lambda: FakeEmbeddings())
    monkeypatch.setattr(chat_router_mod, "build_retriever", lambda session, emb: NoHitRetriever())
    monkeypatch.setattr(chat_router_mod, "build_llm",
                        lambda: FakeLlm(text="¡Hola!", source="chat"))
    client.post(f"/chatbots/{cid}/chat", json={"question": "hola"})

    r = client.get(f"/chatbots/{cid}/chat/history")
    body = r.json()
    assert body["messages"][1]["role"] == "assistant"
    assert body["messages"][1]["grounded"] is False
    assert body["messages"][1]["source"] is None


def test_chat_history_empty_when_no_conversation(client):
    cid = _chatbot()
    r = client.get(f"/chatbots/{cid}/chat/history")
    assert r.status_code == 200, r.text
    assert r.json() == {"conversation_id": None, "messages": []}


def test_chat_history_unknown_chatbot_is_404(client):
    r = client.get("/chatbots/999999/chat/history")
    assert r.status_code == 404
