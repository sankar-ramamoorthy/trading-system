"""Position entity representing the system's interpretation of a holding."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class Position:
    """A holding that originates from a trade plan, not directly from an idea."""

    trade_plan_id: UUID
    instrument_id: UUID
    purpose: str
    lifecycle_state: str = "open"
    opened_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)
