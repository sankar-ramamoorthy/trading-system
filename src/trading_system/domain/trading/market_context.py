"""Read-only market context snapshots used for planning and review support."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True)
class MarketContextSnapshot:
    """A timestamped, non-canonical snapshot of external market context."""

    instrument_id: UUID
    context_type: str
    source: str
    observed_at: datetime
    payload: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    target_type: str | None = None
    target_id: UUID | None = None
    source_ref: str | None = None
    captured_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate the snapshot boundary without interpreting context meaning."""
        if not self.context_type.strip():
            raise ValueError("Context type is required.")
        if not self.source.strip():
            raise ValueError("Context source is required.")
        if (self.target_type is None) != (self.target_id is None):
            raise ValueError("Target type and target id must be provided together.")
