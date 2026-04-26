"""In-memory repository implementations for narrow workflow tests."""

from uuid import UUID

from trading_system.domain.rules.rule_evaluation import RuleEvaluation
from trading_system.domain.rules.violation import Violation
from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.idea import TradeIdea
from trading_system.domain.trading.lifecycle import LifecycleEvent
from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.domain.trading.order_intent import OrderIntent
from trading_system.domain.trading.plan import TradePlan
from trading_system.domain.trading.position import Position
from trading_system.domain.trading.review import TradeReview
from trading_system.domain.trading.thesis import TradeThesis


class InMemoryTradeIdeaRepository:
    """Stores trade ideas in memory for local workflows."""

    def __init__(self) -> None:
        self.items: dict[UUID, TradeIdea] = {}

    def add(self, idea: TradeIdea) -> None:
        """Persist a trade idea."""
        self.items[idea.id] = idea

    def get(self, idea_id: UUID) -> TradeIdea | None:
        """Return a trade idea by identity."""
        return self.items.get(idea_id)

    def list_all(self) -> list[TradeIdea]:
        """Return all trade ideas."""
        return list(self.items.values())


class InMemoryTradeThesisRepository:
    """Stores trade theses in memory for local workflows."""

    def __init__(self) -> None:
        self.items: dict[UUID, TradeThesis] = {}

    def add(self, thesis: TradeThesis) -> None:
        """Persist a trade thesis."""
        self.items[thesis.id] = thesis

    def get(self, thesis_id: UUID) -> TradeThesis | None:
        """Return a trade thesis by identity."""
        return self.items.get(thesis_id)

    def list_all(self) -> list[TradeThesis]:
        """Return all trade theses."""
        return list(self.items.values())


class InMemoryTradePlanRepository:
    """Stores trade plans in memory for local workflows."""

    def __init__(self) -> None:
        self.items: dict[UUID, TradePlan] = {}

    def add(self, plan: TradePlan) -> None:
        """Persist a trade plan."""
        self.items[plan.id] = plan

    def get(self, plan_id: UUID) -> TradePlan | None:
        """Return a trade plan by identity."""
        return self.items.get(plan_id)

    def update(self, plan: TradePlan) -> None:
        """Persist changes to a trade plan."""
        self.items[plan.id] = plan

    def list_all(self) -> list[TradePlan]:
        """Return all trade plans."""
        return list(self.items.values())


class InMemoryPositionRepository:
    """Stores positions in memory for local workflows."""

    def __init__(self) -> None:
        self.items: dict[UUID, Position] = {}

    def add(self, position: Position) -> None:
        """Persist a position."""
        self.items[position.id] = position

    def get(self, position_id: UUID) -> Position | None:
        """Return a position by identity."""
        return self.items.get(position_id)

    def update(self, position: Position) -> None:
        """Persist changes to a position."""
        self.items[position.id] = position

    def list_all(self) -> list[Position]:
        """Return all positions."""
        return list(self.items.values())


class InMemoryFillRepository:
    """Stores manual fills in memory for local workflows."""

    def __init__(self) -> None:
        self.items: dict[UUID, Fill] = {}

    def add(self, fill: Fill) -> None:
        """Persist a manual fill."""
        self.items[fill.id] = fill

    def list_by_position_id(self, position_id: UUID) -> list[Fill]:
        """Return fills for a position."""
        return [fill for fill in self.items.values() if fill.position_id == position_id]


class InMemoryOrderIntentRepository:
    """Stores order intents in memory for local workflows."""

    def __init__(self) -> None:
        self.items: dict[UUID, OrderIntent] = {}

    def add(self, order_intent: OrderIntent) -> None:
        """Persist an order intent."""
        self.items[order_intent.id] = order_intent

    def get(self, order_intent_id: UUID) -> OrderIntent | None:
        """Return an order intent by identity."""
        return self.items.get(order_intent_id)

    def update(self, order_intent: OrderIntent) -> None:
        """Persist changes to an order intent."""
        self.items[order_intent.id] = order_intent

    def list_by_trade_plan_id(self, trade_plan_id: UUID) -> list[OrderIntent]:
        """Return order intents linked to a trade plan."""
        return [
            order_intent
            for order_intent in self.items.values()
            if order_intent.trade_plan_id == trade_plan_id
        ]


class InMemoryLifecycleEventRepository:
    """Stores lifecycle events in memory for local workflows."""

    def __init__(self) -> None:
        self.items: dict[UUID, LifecycleEvent] = {}

    def add(self, event: LifecycleEvent) -> None:
        """Persist a lifecycle event."""
        self.items[event.id] = event

    def list_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> list[LifecycleEvent]:
        """Return lifecycle events for an entity."""
        return sorted(
            [
                event
                for event in self.items.values()
                if event.entity_type == entity_type and event.entity_id == entity_id
            ],
            key=lambda event: event.occurred_at,
        )


class InMemoryTradeReviewRepository:
    """Stores trade reviews in memory for local workflows."""

    def __init__(self) -> None:
        self.items: dict[UUID, TradeReview] = {}

    def add(self, review: TradeReview) -> None:
        """Persist a trade review."""
        self.items[review.id] = review

    def get(self, review_id: UUID) -> TradeReview | None:
        """Return a trade review by identity."""
        return self.items.get(review_id)

    def get_by_position_id(self, position_id: UUID) -> TradeReview | None:
        """Return the review for a position, if one exists."""
        for review in self.items.values():
            if review.position_id == position_id:
                return review
        return None

    def list_all(self) -> list[TradeReview]:
        """Return all trade reviews."""
        return list(self.items.values())


class InMemoryMarketContextSnapshotRepository:
    """Stores read-only market context snapshots in memory."""

    def __init__(self) -> None:
        self.items: dict[UUID, MarketContextSnapshot] = {}

    def add(self, snapshot: MarketContextSnapshot) -> None:
        """Persist a market context snapshot."""
        self.items[snapshot.id] = snapshot

    def get(self, snapshot_id: UUID) -> MarketContextSnapshot | None:
        """Return a market context snapshot by identity."""
        return self.items.get(snapshot_id)

    def list_by_instrument_id(self, instrument_id: UUID) -> list[MarketContextSnapshot]:
        """Return snapshots for one instrument."""
        return sorted(
            [
                snapshot
                for snapshot in self.items.values()
                if snapshot.instrument_id == instrument_id
            ],
            key=lambda snapshot: snapshot.captured_at,
        )

    def list_by_target(
        self,
        target_type: str,
        target_id: UUID,
    ) -> list[MarketContextSnapshot]:
        """Return snapshots linked to one planning or review target."""
        return sorted(
            [
                snapshot
                for snapshot in self.items.values()
                if snapshot.target_type == target_type and snapshot.target_id == target_id
            ],
            key=lambda snapshot: snapshot.captured_at,
        )


class InMemoryRuleEvaluationRepository:
    """Stores rule evaluation artifacts in memory."""

    def __init__(self) -> None:
        self.items: dict[UUID, RuleEvaluation] = {}

    def add(self, evaluation: RuleEvaluation) -> None:
        """Persist a rule evaluation."""
        self.items[evaluation.id] = evaluation

    def list_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> list[RuleEvaluation]:
        """Return persisted evaluations for one domain entity."""
        return [
            evaluation
            for evaluation in self.items.values()
            if evaluation.entity_type == entity_type and evaluation.entity_id == entity_id
        ]


class InMemoryViolationRepository:
    """Stores rule violations in memory."""

    def __init__(self) -> None:
        self.items: dict[UUID, Violation] = {}

    def add(self, violation: Violation) -> None:
        """Persist a rule violation."""
        self.items[violation.id] = violation
