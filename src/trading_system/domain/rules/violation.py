"""Violation entity describing a failed deterministic rule."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Violation:
    """An auditable rule failure tied to a rule evaluation."""

    rule_id: UUID
    message: str
    severity: str = "error"
    id: UUID = field(default_factory=uuid4)
