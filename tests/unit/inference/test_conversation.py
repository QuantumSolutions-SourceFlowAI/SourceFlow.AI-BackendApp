from contexts.chatbots.domain.value_objects import ChatbotId
from contexts.inference.domain.conversation import Conversation
from contexts.inference.domain.enums import Sender
from contexts.inference.domain.message import Message
from contexts.inference.domain.value_objects import Answer
from shared.application.tenant_context import TenantId


def test_add_message_appends():
    conv = Conversation(id=None, tenant_id=TenantId(1), chatbot_id=ChatbotId(1), messages=[])
    conv.add_message(Message(content="hola", sender=Sender.CUSTOMER))
    conv.add_message(Message(content="respuesta", sender=Sender.ASSISTANT,
                             answer=Answer(text="respuesta", grounded=True), tokens_used=12))
    assert len(conv.messages) == 2
    assert conv.messages[1].answer.grounded is True


def test_recent_history_returns_turns_in_order():
    from sqlalchemy import text as sql_text

    from contexts.inference.application.ports import HistoryTurn
    from contexts.inference.infrastructure.conversation_repository import ConversationRepository
    from sfplatform.db import SessionLocal

    with SessionLocal() as s:
        repo = ConversationRepository(s)
        conv_id = repo.start(1, 1)
        repo.save_turn(1, conv_id, "hola", "¡Hola!", False, 5, [])
        repo.save_turn(1, conv_id, "¿precio?", "Cuesta 100.", True, 12, [])
        s.commit()

        history = repo.recent_history(1, conv_id, limit=10)
        assert history == [
            HistoryTurn("user", "hola"),
            HistoryTurn("assistant", "¡Hola!"),
            HistoryTurn("user", "¿precio?"),
            HistoryTurn("assistant", "Cuesta 100."),
        ]

        # empty conversation → empty history
        empty_conv = repo.start(1, 1)
        s.commit()
        assert repo.recent_history(1, empty_conv, limit=10) == []

        s.execute(sql_text("DELETE FROM message WHERE conversation_id IN (:a, :b)"),
                  {"a": conv_id, "b": empty_conv})
        s.execute(sql_text("DELETE FROM conversation WHERE id IN (:a, :b)"),
                  {"a": conv_id, "b": empty_conv})
        s.commit()


def test_conversation_messages_returns_ordered_with_source_and_latest_id():
    from sqlalchemy import text as sql_text

    from contexts.inference.application.ports import RetrievedChunk
    from contexts.inference.infrastructure.conversation_repository import ConversationRepository
    from sfplatform.db import SessionLocal

    with SessionLocal() as s:
        # message_source.chunk_id references a real chunk, so seed document + chunk.
        s.execute(sql_text(
            "INSERT INTO document (tenant_id,chatbot_id,file_name,size_bytes,status) "
            "VALUES (1,1,'catalogo.pdf',10,'ready')"))
        did = s.execute(sql_text(
            "SELECT id FROM document WHERE file_name='catalogo.pdf' ORDER BY id DESC LIMIT 1")).scalar()
        s.execute(sql_text(
            "INSERT INTO chunk (tenant_id,document_id,text_content,position,embedding_vector) "
            "VALUES (1,:d,'el precio es 100 soles',0,:v)"), {"d": did, "v": str([0.1] * 1024)})
        chunk_id = s.execute(sql_text("SELECT id FROM chunk WHERE document_id=:d"), {"d": did}).scalar()

        repo = ConversationRepository(s)
        conv = repo.start(1, 1)
        repo.save_turn(1, conv, "hola", "¡Hola!", False, 5, [])  # greeting → no citation
        repo.save_turn(1, conv, "¿precio?", "Cuesta 100.", True, 12,
                       [RetrievedChunk(chunk_id, did, "catalogo.pdf", "el precio es 100 soles", 0.9)])
        s.commit()

        msgs = repo.conversation_messages(1, conv)
        assert [(m.role, m.text, m.grounded) for m in msgs] == [
            ("user", "hola", False),
            ("assistant", "¡Hola!", False),
            ("user", "¿precio?", False),
            ("assistant", "Cuesta 100.", True),
        ]
        assert msgs[0].source is None  # user
        assert msgs[1].source is None  # ungrounded assistant
        assert msgs[3].source == "catalogo.pdf: el precio es 100 soles"
        assert msgs[0].message_id < msgs[3].message_id

        assert repo.latest_conversation_id(1, 1) == conv

        # cleanup
        s.execute(sql_text(
            "DELETE FROM message_source WHERE message_id IN "
            "(SELECT id FROM message WHERE conversation_id=:c)"), {"c": conv})
        s.execute(sql_text("DELETE FROM message WHERE conversation_id=:c"), {"c": conv})
        s.execute(sql_text("DELETE FROM chunk WHERE id=:c"), {"c": chunk_id})
        s.execute(sql_text("DELETE FROM conversation WHERE id=:c"), {"c": conv})
        s.execute(sql_text("DELETE FROM document WHERE id=:d"), {"d": did})
        s.commit()


def test_latest_conversation_id_none_when_no_conversation():
    from contexts.inference.infrastructure.conversation_repository import ConversationRepository
    from sfplatform.db import SessionLocal

    with SessionLocal() as s:
        repo = ConversationRepository(s)
        assert repo.latest_conversation_id(1, 999999) is None
