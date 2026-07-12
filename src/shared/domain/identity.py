from dataclasses import dataclass

from shared.domain.errors import ValidationError


@dataclass(frozen=True)
class IntId:
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or isinstance(self.value, bool):
            raise ValidationError("Id value must be an int")
        if self.value <= 0:
            raise ValidationError("Id value must be a positive integer")
