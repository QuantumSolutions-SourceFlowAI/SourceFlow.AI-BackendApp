import pytest
from contexts.chatbots.domain.chatbot import Chatbot
from contexts.chatbots.domain.enums import ChatbotStatus, Tone
from shared.application.tenant_context import TenantId
from shared.domain.errors import ValidationError


def _bot():
    return Chatbot(id=None, tenant_id=TenantId(1), name="Ventas", tone=Tone.FORMAL,
                   status=ChatbotStatus.NO_DOCUMENTS)


def test_new_bot_starts_no_documents():
    assert _bot().status is ChatbotStatus.NO_DOCUMENTS


def test_rename_changes_name():
    b = _bot()
    b.rename("Soporte")
    assert b.name == "Soporte"


def test_rename_rejects_empty():
    b = _bot()
    with pytest.raises(ValidationError):
        b.rename("   ")


def test_change_tone():
    b = _bot()
    b.change_tone(Tone.SALES)
    assert b.tone is Tone.SALES


def test_mark_ready_and_back():
    b = _bot()
    b.mark_ready()
    assert b.status is ChatbotStatus.READY
    b.mark_no_documents()
    assert b.status is ChatbotStatus.NO_DOCUMENTS


def test_purpose_defaults_to_empty_string():
    assert _bot().purpose == ""


def test_change_purpose_strips_whitespace():
    bot = _bot()
    bot.change_purpose("  Asistente del curso de software  ")
    assert bot.purpose == "Asistente del curso de software"


def test_change_purpose_rejects_over_2000_chars():
    bot = _bot()
    with pytest.raises(ValidationError):
        bot.change_purpose("x" * 2001)
