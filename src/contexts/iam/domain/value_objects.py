import re
from dataclasses import dataclass

from shared.domain.errors import ValidationError
from shared.domain.identity import IntId

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserId(IntId):
    pass


@dataclass(frozen=True)
class Email:
    address: str

    def __post_init__(self) -> None:
        if not _EMAIL_RE.match(self.address):
            raise ValidationError(f"Invalid email: {self.address!r}")
