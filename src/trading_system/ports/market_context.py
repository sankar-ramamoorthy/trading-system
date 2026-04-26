"""Ports for read-only market context source adapters."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class ImportedMarketContext:
    """Validated context input loaded from an external source."""

    context_type: str
    observed_at: datetime
    payload: dict[str, Any]


class MarketContextImportSource(Protocol):
    """Boundary for explicit user-invoked context imports."""

    def load(self) -> ImportedMarketContext:
        """Load one market context document."""
        ...
