"""Trade idea entity defining what the trade is."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class TradeIdea:
    """Represents an opportunity before thesis, plan, or execution."""

    instrument_id: UUID
    playbook_id: UUID
    purpose: str
    direction: str
    horizon: str
    status: str = "draft"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid4)
