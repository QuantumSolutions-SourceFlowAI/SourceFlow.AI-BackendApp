from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject:
    """Marker base for immutable, equality-by-value objects."""


class Entity:
    """Base for entities: identity-based equality delegated to subclasses."""


class AggregateRoot(Entity):
    """Marker base for aggregate roots."""
