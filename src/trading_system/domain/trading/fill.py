"""Manual fill facts recorded during the initial implementation phase."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Fill:
    """A manually entered execution fact linked to a position."""

    position_id: UUID
    quantity: Decimal
    price: Decimal
    side: str
    order_intent_id: UUID | None = None
    filled_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    notes: str | None = None
    source: str = "manual"
    id: UUID = field(default_factory=uuid4)
