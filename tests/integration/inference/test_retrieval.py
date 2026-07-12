from sqlalchemy import text

from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.inference.infrastructure.retrieval import PgVectorRetriever
from contexts.knowledge_ingestion.domain.value_objects import Embedding
from shared.application.tenant_context import TenantId


class FakeEmbeddings:
    last_tokens = 3
    def __init__(self, vec):
        self._vec = vec
    def embed(self, texts):
        return [Embedding(tuple(self._vec)) for _ in texts]
    def embed_one(self, text):
        return Embedding(tuple(self._vec))


def _seed_chunk(db_session, chatbot_id, vec):
    db_session.execute(text("INSERT INTO document (tenant_id,chatbot_id,file_name,size_bytes,status) "
                            "VALUES (1,:c,'src.pdf',10,'ready') RETURNING id"), {"c": chatbot_id})
    did = db_session.execute(text("SELECT id FROM document WHERE chatbot_id=:c ORDER BY id DESC LIMIT 1"),
                             {"c": chatbot_id}).scalar()
    db_session.execute(text("INSERT INTO chunk (tenant_id,document_id,text_content,position,embedding_vector) "
                            "VALUES (1,:d,'el precio es 100 soles',0,:v)"),
                       {"d": did, "v": str(list(vec))})
    db_session.commit()


def test_retrieve_returns_similar_chunk_above_threshold(db_session):
    db_session.execute(text("INSERT INTO chatbot (tenant_id,name,tone,status) "
                            "VALUES (1,'RetrBot','formal','ready')"))
    cid = db_session.execute(text("SELECT id FROM chatbot WHERE name='RetrBot'")).scalar()
    vec = [0.1] * 1024
    _seed_chunk(db_session, cid, vec)

    retriever = PgVectorRetriever(db_session, FakeEmbeddings(vec))
    hits = retriever.retrieve(TenantId(1), ChatbotId(cid),
                              FakeEmbeddings(vec).embed_one("precio"), top_k=4, threshold=0.75)
    assert len(hits) == 1
    assert hits[0].similarity >= 0.75
    assert hits[0].file_name == "src.pdf"

    # orthogonal query -> below threshold -> filtered out
    ortho = [0.0] * 1024
    ortho[0] = 1.0
    hits2 = retriever.retrieve(TenantId(1), ChatbotId(cid),
                               Embedding(tuple(ortho)), top_k=4, threshold=0.75)
    assert hits2 == []


def test_retrieve_excludes_other_tenant_and_chatbot(db_session):
    """Regression test: verify isolation of chunks by tenant_id and chatbot_id in pgvector retrieval."""
    # Setup: Create chatbot X for tenant 1
    db_session.execute(text("INSERT INTO chatbot (tenant_id,name,tone,status) "
                            "VALUES (1,'RetrBotX','formal','ready') ON CONFLICT DO NOTHING"))
    cid_x = db_session.execute(text("SELECT id FROM chatbot WHERE name='RetrBotX'")).scalar()

    # Create a second chatbot Y for tenant 1 (different name to avoid conflict)
    db_session.execute(text("INSERT INTO chatbot (tenant_id,name,tone,status) "
                            "VALUES (1,'RetrBotY','formal','ready') ON CONFLICT DO NOTHING"))
    cid_y = db_session.execute(text("SELECT id FROM chatbot WHERE name='RetrBotY'")).scalar()

    # Create a second tenant
    tenant2_id = db_session.execute(text(
        "SELECT id FROM tenant WHERE business_name='TestTenant2'")).scalar()
    if tenant2_id is None:
        tenant2_id = db_session.execute(text(
            "INSERT INTO tenant (business_name, status) "
            "VALUES ('TestTenant2','active') RETURNING id")).scalar()

    # Create a chatbot Z for tenant 2
    db_session.execute(text("INSERT INTO chatbot (tenant_id,name,tone,status) "
                            "VALUES (:tid,'RetrBotZ','formal','ready') ON CONFLICT DO NOTHING"),
                      {"tid": tenant2_id})
    cid_z = db_session.execute(text("SELECT id FROM chatbot WHERE name='RetrBotZ'")).scalar()

    # Seed identical vector for all chunks (high similarity)
    vec = [0.1] * 1024

    # Chunk A: belongs to (tenant 1, chatbot X) - should be retrieved
    db_session.execute(text("INSERT INTO document (tenant_id,chatbot_id,file_name,size_bytes,status) "
                            "VALUES (1,:c,'chunk_a.pdf',10,'ready')"), {"c": cid_x})
    doc_a_id = db_session.execute(text("SELECT id FROM document WHERE file_name='chunk_a.pdf'")).scalar()
    db_session.execute(text("INSERT INTO chunk (tenant_id,document_id,text_content,position,embedding_vector) "
                            "VALUES (1,:d,'chunk A content',0,:v)"),
                      {"d": doc_a_id, "v": str(list(vec))})

    # Chunk B: same vector but belongs to (tenant 1, chatbot Y) - should be excluded
    db_session.execute(text("INSERT INTO document (tenant_id,chatbot_id,file_name,size_bytes,status) "
                            "VALUES (1,:c,'chunk_b.pdf',10,'ready')"), {"c": cid_y})
    doc_b_id = db_session.execute(text("SELECT id FROM document WHERE file_name='chunk_b.pdf'")).scalar()
    db_session.execute(text("INSERT INTO chunk (tenant_id,document_id,text_content,position,embedding_vector) "
                            "VALUES (1,:d,'chunk B content',0,:v)"),
                      {"d": doc_b_id, "v": str(list(vec))})

    # Chunk C: same vector but belongs to (tenant 2, chatbot Z) - should be excluded
    db_session.execute(text("INSERT INTO document (tenant_id,chatbot_id,file_name,size_bytes,status) "
                            "VALUES (:tid,:c,'chunk_c.pdf',10,'ready')"),
                      {"tid": tenant2_id, "c": cid_z})
    doc_c_id = db_session.execute(text("SELECT id FROM document WHERE file_name='chunk_c.pdf'")).scalar()
    db_session.execute(text("INSERT INTO chunk (tenant_id,document_id,text_content,position,embedding_vector) "
                            "VALUES (:tid,:d,'chunk C content',0,:v)"),
                      {"tid": tenant2_id, "d": doc_c_id, "v": str(list(vec))})

    db_session.commit()

    # Retrieve for tenant 1, chatbot X
    retriever = PgVectorRetriever(db_session, FakeEmbeddings(vec))
    hits = retriever.retrieve(TenantId(1), ChatbotId(cid_x),
                             FakeEmbeddings(vec).embed_one("query"), top_k=10, threshold=0.5)

    # Assert: only chunk A is returned
    assert len(hits) == 1, f"Expected 1 hit, got {len(hits)}"
    assert hits[0].file_name == "chunk_a.pdf"
    assert hits[0].text == "chunk A content"
    assert hits[0].similarity >= 0.5
