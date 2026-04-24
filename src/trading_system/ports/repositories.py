"""Repository interfaces for domain persistence boundaries."""

from typing import Protocol
from uuid import UUID

from trading_system.domain.rules.rule_evaluation import RuleEvaluation
from trading_system.domain.rules.violation import Violation
from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.idea import TradeIdea
from trading_system.domain.trading.lifecycle import LifecycleEvent
from trading_system.domain.trading.order_intent import OrderIntent
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

    def list_all(self) -> list[TradeIdea]:
        """Return all trade ideas."""
        ...


class TradeThesisRepository(Protocol):
    """Persistence boundary for trade thesis records."""

    def add(self, thesis: TradeThesis) -> None:
        """Persist a trade thesis."""
        ...

    def get(self, thesis_id: UUID) -> TradeThesis | None:
        """Return a trade thesis by identity."""
        ...


class TradePlanRepository(Protocol):
    """Persistence boundary for trade plans."""

    def add(self, plan: TradePlan) -> None:
        """Persist a trade plan."""
        ...

    def get(self, plan_id: UUID) -> TradePlan | None:
        """Return a trade plan by identity."""
        ...

    def update(self, plan: TradePlan) -> None:
        """Persist changes to a trade plan."""
        ...

    def list_all(self) -> list[TradePlan]:
        """Return all trade plans."""
        ...


class PositionRepository(Protocol):
    """Persistence boundary for positions."""

    def add(self, position: Position) -> None:
        """Persist a position."""
        ...

    def get(self, position_id: UUID) -> Position | None:
        """Return a position by identity."""
        ...

    def update(self, position: Position) -> None:
        """Persist changes to a position."""
        ...

    def list_all(self) -> list[Position]:
        """Return all positions."""
        ...


class FillRepository(Protocol):
    """Persistence boundary for manual fill facts."""

    def add(self, fill: Fill) -> None:
        """Persist a manual fill."""
        ...

    def list_by_position_id(self, position_id: UUID) -> list[Fill]:
        """Return fills for a position."""
        ...


class OrderIntentRepository(Protocol):
    """Persistence boundary for execution intent records."""

    def add(self, order_intent: OrderIntent) -> None:
        """Persist an order intent."""
        ...

    def get(self, order_intent_id: UUID) -> OrderIntent | None:
        """Return an order intent by identity."""
        ...

    def list_by_trade_plan_id(self, trade_plan_id: UUID) -> list[OrderIntent]:
        """Return order intents linked to a trade plan."""
        ...


class LifecycleEventRepository(Protocol):
    """Persistence boundary for auditable lifecycle events."""

    def add(self, event: LifecycleEvent) -> None:
        """Persist a lifecycle event."""
        ...

    def list_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> list[LifecycleEvent]:
        """Return lifecycle events for an entity."""
        ...


class TradeReviewRepository(Protocol):
    """Persistence boundary for trade reviews."""

    def add(self, review: TradeReview) -> None:
        """Persist a trade review."""
        ...

    def get(self, review_id: UUID) -> TradeReview | None:
        """Return a trade review by identity."""
        ...

    def get_by_position_id(self, position_id: UUID) -> TradeReview | None:
        """Return the review for a position, if one exists."""
        ...

    def list_all(self) -> list[TradeReview]:
        """Return all trade reviews."""
        ...


class RuleEvaluationRepository(Protocol):
    """Persistence boundary for deterministic rule evaluation artifacts."""

    def add(self, evaluation: RuleEvaluation) -> None:
        """Persist a rule evaluation."""
        ...

    def list_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> list[RuleEvaluation]:
        """Return persisted evaluations for one domain entity."""
        ...


class ViolationRepository(Protocol):
    """Persistence boundary for rule violations."""

    def add(self, violation: Violation) -> None:
        """Persist a rule violation."""
        ...
