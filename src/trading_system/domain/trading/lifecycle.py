"""Lifecycle event entity for recording meaningful state changes."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class LifecycleEvent:
    """An auditable event describing what changed and why."""

    entity_id: UUID
    entity_type: str
    event_type: str
    note: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid4)
