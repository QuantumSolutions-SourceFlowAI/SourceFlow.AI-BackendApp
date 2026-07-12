class DomainError(Exception):
    """Base class for all domain-level errors."""


class ValidationError(DomainError):
    """A value object or field failed validation."""


class InvariantViolation(DomainError):
    """An aggregate invariant was violated."""


class NotFoundError(DomainError):
    """A requested aggregate/entity was not found."""
