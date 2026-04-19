"""Repository interfaces for domain persistence boundaries."""

from typing import Protocol
from uuid import UUID

from trading_system.domain.trading.idea import TradeIdea
from trading_system.domain.trading.plan import TradePlan
from trading_system.domain.trading.position import Position
from trading_system.domain.trading.review import TradeReview
from trading_system.domain.trading.thesis import TradeThesis


class TradeIdeaRepository(Protocol):
    """Persistence boundary for trade ideas."""

    def add(self, idea: TradeIdea) -> None:
        """Persist a trade idea."""
        ...

    def get(self, idea_id: UUID) -> TradeIdea | None:
        """Return a trade idea by identity."""
        ...


class TradeThesisRepository(Protocol):
    """Persistence boundary for trade thesis records."""

    def add(self, thesis: TradeThesis) -> None:
        """Persist a trade thesis."""
        ...


class TradePlanRepository(Protocol):
    """Persistence boundary for trade plans."""

    def add(self, plan: TradePlan) -> None:
        """Persist a trade plan."""
        ...

    def get(self, plan_id: UUID) -> TradePlan | None:
        """Return a trade plan by identity."""
        ...


class PositionRepository(Protocol):
    """Persistence boundary for positions."""

    def add(self, position: Position) -> None:
        """Persist a position."""
        ...


class TradeReviewRepository(Protocol):
    """Persistence boundary for trade reviews."""

    def add(self, review: TradeReview) -> None:
        """Persist a trade review."""
        ...
