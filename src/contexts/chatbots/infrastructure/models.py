from sqlalchemy import BigInteger, Enum, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from contexts.chatbots.domain.enums import ChatbotStatus, Tone
from sfplatform.db import Base


class ChatbotModel(Base):
    __tablename__ = "chatbot"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_chatbots_tenant_id_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    tone: Mapped[Tone] = mapped_column(Enum(Tone, name="chatbot_tone", values_callable=lambda e: [m.value for m in e]))
    status: Mapped[ChatbotStatus] = mapped_column(
        Enum(ChatbotStatus, name="chatbot_status", values_callable=lambda e: [m.value for m in e]))
    purpose: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
