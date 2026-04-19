"""Trade review entity for post-trade assessment."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class TradeReview:
    """A structured review of process quality and outcome."""

    position_id: UUID
    summary: str
    lessons: list[str] = field(default_factory=list)
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid4)
