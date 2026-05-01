"""User-facing setup pattern referenced by trade ideas."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Playbook:
    """A named trade setup pattern used to classify trade ideas."""

    slug: str
    name: str
    description: str | None = None
    id: UUID = field(default_factory=uuid4)
