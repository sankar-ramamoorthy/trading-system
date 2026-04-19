"""Rule entity describing an explicit deterministic discipline rule."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Rule:
    """A named deterministic rule that can be evaluated and audited."""

    code: str
    name: str
    description: str
    active: bool = True
    id: UUID = field(default_factory=uuid4)
