"""Rule evaluation entity recording deterministic rule outcomes."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class RuleEvaluation:
    """The result of evaluating one rule against one target entity."""

    rule_id: UUID
    entity_type: str
    entity_id: UUID
    passed: bool
    details: str | None = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid4)
