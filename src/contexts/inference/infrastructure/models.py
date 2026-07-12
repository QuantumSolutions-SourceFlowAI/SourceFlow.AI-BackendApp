from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from contexts.inference.domain.enums import Sender
from sfplatform.db import Base


class ConversationModel(Base):
    __tablename__ = "conversation"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chatbot_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    started_at: Mapped["DateTime"] = mapped_column(DateTime, nullable=False)


class MessageModel(Base):
    __tablename__ = "message"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    conversation_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sender: Mapped[Sender] = mapped_column(
        Enum(Sender, name="message_sender", values_callable=lambda e: [m.value for m in e]))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_grounded: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MessageSourceModel(Base):
    __tablename__ = "message_source"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chunk_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
