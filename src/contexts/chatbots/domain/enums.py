from enum import Enum


class Tone(str, Enum):
    FORMAL = "formal"
    FRIENDLY = "friendly"
    SALES = "sales"


class ChatbotStatus(str, Enum):
    NO_DOCUMENTS = "no_documents"
    READY = "ready"
