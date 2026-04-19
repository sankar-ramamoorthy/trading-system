"""Canonical tradable identity owned by the trading system."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Instrument:
    """A tradable instrument referenced by ideas, plans, and positions."""

    symbol: str
    name: str | None = None
    id: UUID = field(default_factory=uuid4)
