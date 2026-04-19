"""Trade plan entity defining how a trade should be executed."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class TradePlan:
    """Execution plan tied to an idea and thesis."""

    trade_idea_id: UUID
    trade_thesis_id: UUID
    entry_criteria: str
    invalidation: str
    targets: list[str] = field(default_factory=list)
    risk_model: str | None = None
    sizing_assumptions: str | None = None
    approval_state: str = "draft"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid4)
