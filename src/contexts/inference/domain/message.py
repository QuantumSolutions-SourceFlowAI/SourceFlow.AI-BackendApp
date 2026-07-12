from dataclasses import dataclass

from contexts.inference.domain.enums import Sender
from contexts.inference.domain.value_objects import Answer


@dataclass
class Message:
    content: str
    sender: Sender
    answer: Answer | None = None
    tokens_used: int | None = None
