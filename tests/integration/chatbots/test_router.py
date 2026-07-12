from sqlalchemy import text

from sfplatform.db import SessionLocal


def _cleanup():
    with SessionLocal() as s:
        s.execute(text("DELETE FROM chatbot WHERE name LIKE 'ApiTest%'"))
        s.commit()


def test_create_list_rename_delete(client):
    _cleanup()
    r = client.post("/chatbots", json={"name": "ApiTest Ventas", "tone": "formal"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "no_documents"
    bot_id = body["id"]

    r = client.get("/chatbots")
    assert any(b["id"] == bot_id for b in r.json())

    r = client.put(f"/chatbots/{bot_id}", json={"name": "ApiTest Soporte", "tone": "sales"})
    assert r.status_code == 200
    assert r.json()["name"] == "ApiTest Soporte"
    assert r.json()["tone"] == "sales"

    r = client.delete(f"/chatbots/{bot_id}")
    assert r.status_code == 204


def test_duplicate_name_rejected(client):
    _cleanup()
    client.post("/chatbots", json={"name": "ApiTest Dup", "tone": "formal"})
    r = client.post("/chatbots", json={"name": "ApiTest Dup", "tone": "formal"})
    assert r.status_code == 409
    assert "Ya existe un chatbot con ese nombre" in r.text


def test_create_with_blank_name_rejected(client):
    _cleanup()
    r = client.post("/chatbots", json={"name": "   ", "tone": "formal"})
    assert r.status_code == 422


def test_create_and_update_with_purpose(client):
    _cleanup()
    r = client.post("/chatbots", json={"name": "ApiTest Purpose", "tone": "formal",
                                       "purpose": "Bot del curso de software"})
    assert r.status_code == 201, r.text
    assert r.json()["purpose"] == "Bot del curso de software"
    bot_id = r.json()["id"]

    r = client.put(f"/chatbots/{bot_id}", json={"purpose": "Nuevo dominio"})
    assert r.status_code == 200, r.text
    assert r.json()["purpose"] == "Nuevo dominio"

    r = client.get("/chatbots")
    got = next(b for b in r.json() if b["id"] == bot_id)
    assert got["purpose"] == "Nuevo dominio"
