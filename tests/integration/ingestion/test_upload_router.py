import io

from sqlalchemy import text

from sfplatform.db import SessionLocal


def _chatbot_id():
    with SessionLocal() as s:
        s.execute(text("INSERT INTO chatbot (tenant_id,name,tone,status) "
                       "VALUES (1,'UploadBot','formal','no_documents') ON CONFLICT DO NOTHING"))
        s.commit()
        return s.execute(text("SELECT id FROM chatbot WHERE name='UploadBot'")).scalar()


def _other_tenant_chatbot_id():
    with SessionLocal() as s:
        tenant_id = s.execute(text(
            "SELECT id FROM tenant WHERE business_name='OtherTenant Inc'")).scalar()
        if tenant_id is None:
            tenant_id = s.execute(text(
                "INSERT INTO tenant (business_name, status) "
                "VALUES ('OtherTenant Inc','active') RETURNING id")).scalar()
        s.execute(text(
            "INSERT INTO chatbot (tenant_id,name,tone,status) "
            "VALUES (:tid,'OtherTenantUploadBot','formal','no_documents') "
            "ON CONFLICT DO NOTHING"), {"tid": tenant_id})
        s.commit()
        return s.execute(text(
            "SELECT id FROM chatbot WHERE name='OtherTenantUploadBot'")).scalar()


def _minimal_pdf() -> bytes:
    # a tiny valid-enough PDF header; extraction may yield empty but upload must accept it
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


def test_upload_pdf_accepted(client, monkeypatch):
    # stub the queue so no real Celery/Redis is needed
    import contexts.knowledge_ingestion.interfaces.router as r
    monkeypatch.setattr(r.CeleryIngestionQueue, "enqueue", lambda self, *a, **k: None)
    cid = _chatbot_id()
    files = {"file": ("doc.pdf", io.BytesIO(_minimal_pdf()), "application/pdf")}
    resp = client.post(f"/chatbots/{cid}/documents", files=files)
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "processing"


def test_reject_non_pdf(client):
    cid = _chatbot_id()
    files = {"file": ("doc.txt", io.BytesIO(b"hello"), "text/plain")}
    resp = client.post(f"/chatbots/{cid}/documents", files=files)
    assert resp.status_code == 422
    assert "Solo se admiten archivos PDF de hasta 5 MB" in resp.text


def test_upload_nonexistent_chatbot_returns_404(client):
    files = {"file": ("doc.pdf", io.BytesIO(_minimal_pdf()), "application/pdf")}
    resp = client.post("/chatbots/999999/documents", files=files)
    assert resp.status_code == 404


def test_upload_to_other_tenants_chatbot_returns_404(client):
    cid = _other_tenant_chatbot_id()
    files = {"file": ("doc.pdf", io.BytesIO(_minimal_pdf()), "application/pdf")}
    resp = client.post(f"/chatbots/{cid}/documents", files=files)
    assert resp.status_code == 404


def test_list_documents_returns_uploaded(client, monkeypatch):
    import contexts.knowledge_ingestion.interfaces.router as r
    monkeypatch.setattr(r.CeleryIngestionQueue, "enqueue", lambda self, *a, **k: None)
    cid = _chatbot_id()
    files = {"file": ("listed.pdf", io.BytesIO(_minimal_pdf()), "application/pdf")}
    up = client.post(f"/chatbots/{cid}/documents", files=files)
    assert up.status_code == 201, up.text

    resp = client.get(f"/chatbots/{cid}/documents")
    assert resp.status_code == 200, resp.text
    docs = resp.json()
    assert any(d["file_name"] == "listed.pdf" and d["status"] == "processing" for d in docs)
    assert all({"id", "file_name", "size_bytes", "status"} <= set(d) for d in docs)


def test_list_documents_nonexistent_chatbot_returns_404(client):
    resp = client.get("/chatbots/999999/documents")
    assert resp.status_code == 404


def test_list_documents_of_other_tenant_returns_404(client):
    cid = _other_tenant_chatbot_id()
    resp = client.get(f"/chatbots/{cid}/documents")
    assert resp.status_code == 404


def test_upload_commits_document_before_enqueue(client, monkeypatch):
    # the enqueue callback must see the document row already committed and
    # visible from a completely separate session/connection
    import contexts.knowledge_ingestion.interfaces.router as r

    visible_from_other_session = {}

    def fake_enqueue(self, document_id, tenant_id, file_path):
        with SessionLocal() as other:
            row = other.execute(
                text("SELECT status FROM document WHERE id=:id"),
                {"id": document_id},
            ).fetchone()
        visible_from_other_session["row"] = row

    monkeypatch.setattr(r.CeleryIngestionQueue, "enqueue", fake_enqueue)
    cid = _chatbot_id()
    files = {"file": ("doc.pdf", io.BytesIO(_minimal_pdf()), "application/pdf")}
    resp = client.post(f"/chatbots/{cid}/documents", files=files)
    assert resp.status_code == 201, resp.text
    assert visible_from_other_session["row"] is not None
