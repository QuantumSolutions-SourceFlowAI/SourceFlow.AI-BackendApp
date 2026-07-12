import pytest
from sqlalchemy import text

from contexts.chatbots.domain.chatbot import Chatbot
from contexts.chatbots.domain.enums import ChatbotStatus, Tone
from contexts.chatbots.infrastructure.repository import SqlAlchemyChatbotRepository
from shared.application.tenant_context import TenantId


@pytest.fixture(autouse=True)
def _clean(db_session):
    db_session.execute(text("DELETE FROM chatbot WHERE name LIKE 'RepoTest%'"))
    db_session.commit()


def _bot(name="RepoTest Bot"):
    return Chatbot(id=None, tenant_id=TenantId(1), name=name, tone=Tone.FORMAL,
                   status=ChatbotStatus.NO_DOCUMENTS)


def test_add_and_get(db_session):
    repo = SqlAlchemyChatbotRepository(db_session)
    saved = repo.add(_bot())
    db_session.commit()
    assert saved.id is not None
    fetched = repo.get(TenantId(1), saved.id)
    assert fetched is not None
    assert fetched.name == "RepoTest Bot"


def test_exists_name_is_tenant_scoped(db_session):
    repo = SqlAlchemyChatbotRepository(db_session)
    repo.add(_bot("RepoTest Unique"))
    db_session.commit()
    assert repo.exists_name(TenantId(1), "RepoTest Unique") is True
    assert repo.exists_name(TenantId(999), "RepoTest Unique") is False


def test_list_only_returns_tenant_rows(db_session):
    repo = SqlAlchemyChatbotRepository(db_session)
    repo.add(_bot("RepoTest A"))
    db_session.commit()
    names = [b.name for b in repo.list(TenantId(1))]
    assert "RepoTest A" in names
    assert repo.list(TenantId(999)) == []


def test_update_is_tenant_scoped(db_session):
    repo = SqlAlchemyChatbotRepository(db_session)
    saved = repo.add(_bot("RepoTest Scoped"))
    db_session.commit()
    # attempt to update the same chatbot id but under a different tenant
    from contexts.chatbots.domain.chatbot import Chatbot
    from contexts.chatbots.domain.enums import ChatbotStatus, Tone
    from shared.application.tenant_context import TenantId
    intruder = Chatbot(id=saved.id, tenant_id=TenantId(999), name="Hacked",
                       tone=Tone.SALES, status=ChatbotStatus.READY)
    repo.update(intruder)
    db_session.commit()
    fetched = repo.get(TenantId(1), saved.id)
    assert fetched is not None
    assert fetched.name == "RepoTest Scoped"  # unchanged


def test_purpose_round_trips(db_session):
    from contexts.chatbots.domain.chatbot import Chatbot
    from contexts.chatbots.domain.enums import Tone
    from contexts.chatbots.infrastructure.repository import SqlAlchemyChatbotRepository
    from shared.application.tenant_context import TenantId

    repo = SqlAlchemyChatbotRepository(db_session)
    bot = Chatbot(id=None, tenant_id=TenantId(1), name="PurposeBot", tone=Tone.FRIENDLY,
                  purpose="Soporte del curso")
    saved = repo.add(bot)
    db_session.flush()

    fetched = repo.get(TenantId(1), saved.id)
    assert fetched.purpose == "Soporte del curso"

    fetched.change_purpose("Nuevo propósito")
    repo.update(fetched)
    db_session.flush()
    assert repo.get(TenantId(1), saved.id).purpose == "Nuevo propósito"

    db_session.rollback()
