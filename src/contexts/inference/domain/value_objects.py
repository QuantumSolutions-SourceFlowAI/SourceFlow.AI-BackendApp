from dataclasses import dataclass

from shared.domain.identity import IntId


class ConversationId(IntId):
    pass


@dataclass(frozen=True)
class Answer:
    text: str
    grounded: bool
