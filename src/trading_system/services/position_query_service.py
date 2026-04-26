"""Read-only workflows for persisted position retrieval."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.idea import TradeIdea
from trading_system.domain.trading.lifecycle import LifecycleEvent
from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.domain.trading.order_intent import OrderIntent
from trading_system.domain.trading.plan import TradePlan
from trading_system.domain.trading.position import Position
from trading_system.domain.trading.review import TradeReview
from trading_system.ports.repositories import (
    FillRepository,
    LifecycleEventRepository,
    MarketContextSnapshotRepository,
    OrderIntentRepository,
    PositionRepository,
    TradeIdeaRepository,
    TradePlanRepository,
    TradeReviewRepository,
)


@dataclass(frozen=True)
class PositionDetail:
    """Composite read model for inspecting a persisted position."""

    position: Position
    trade_plan: TradePlan
    trade_idea: TradeIdea
    order_intents: list[OrderIntent]
    fills: list[Fill]
    review: TradeReview | None
    realized_pnl: Decimal | None
    market_context_snapshots: list[MarketContextSnapshot]


class PositionQueryService:
    """Coordinates read-only position retrieval without persistence details."""

    def __init__(
        self,
        position_repository: PositionRepository,
        plan_repository: TradePlanRepository,
        idea_repository: TradeIdeaRepository,
        order_intent_repository: OrderIntentRepository,
        fill_repository: FillRepository,
        review_repository: TradeReviewRepository,
        lifecycle_event_repository: LifecycleEventRepository,
        market_context_snapshot_repository: MarketContextSnapshotRepository,
    ) -> None:
        self._positions = position_repository
        self._plans = plan_repository
        self._ideas = idea_repository
        self._order_intents = order_intent_repository
        self._fills = fill_repository
        self._reviews = review_repository
        self._lifecycle_events = lifecycle_event_repository
        self._market_context_snapshots = market_context_snapshot_repository

    def list_positions(
        self,
        lifecycle_state: str | None = None,
        purpose: str | None = None,
        has_review: bool | None = None,
        sort: Literal["oldest", "newest"] = "oldest",
    ) -> list[Position]:
        """Return persisted positions with exact filters and chronological sorting."""
        positions = self._positions.list_all()
        if lifecycle_state is not None:
            positions = [
                position
                for position in positions
                if position.lifecycle_state == lifecycle_state
            ]
        if purpose is not None:
            positions = [position for position in positions if position.purpose == purpose]
        if has_review is not None:
            positions = [
                position
                for position in positions
                if (self._reviews.get_by_position_id(position.id) is not None) == has_review
            ]
        return sorted(
            positions,
            key=lambda position: position.opened_at,
            reverse=sort == "newest",
        )

    def get_position_detail(self, position_id: UUID) -> PositionDetail:
        """Return a position with linked plan, idea, fills, and review."""
        position = self._positions.get(position_id)
        if position is None:
            raise ValueError("Position does not exist.")

        plan = self._plans.get(position.trade_plan_id)
        if plan is None:
            raise ValueError("Trade plan does not exist for position.")

        idea = self._ideas.get(plan.trade_idea_id)
        if idea is None:
            raise ValueError("Trade idea does not exist for position.")

        fills = sorted(
            self._fills.list_by_position_id(position.id),
            key=lambda fill: fill.filled_at,
        )
        order_intents = sorted(
            self._order_intents.list_by_trade_plan_id(position.trade_plan_id),
            key=lambda order_intent: order_intent.created_at,
        )
        review = self._reviews.get_by_position_id(position.id)
        market_context_snapshots = sorted(
            self._market_context_snapshots.list_by_target("Position", position.id),
            key=lambda snapshot: snapshot.captured_at,
        )
        return PositionDetail(
            position=position,
            trade_plan=plan,
            trade_idea=idea,
            order_intents=order_intents,
            fills=fills,
            review=review,
            realized_pnl=_calculate_realized_pnl(position, fills),
            market_context_snapshots=market_context_snapshots,
        )

    def get_position_timeline(self, position_id: UUID) -> list[LifecycleEvent]:
        """Return lifecycle events for a position in chronological order."""
        if self._positions.get(position_id) is None:
            raise ValueError("Position does not exist.")

        events = self._lifecycle_events.list_by_entity("Position", position_id)
        return sorted(events, key=lambda event: event.occurred_at)


def _calculate_realized_pnl(
    position: Position,
    fills: list[Fill],
) -> Decimal | None:
    """Compute realized P&L for the current closed-position execution slice."""
    if position.lifecycle_state != "closed":
        return None

    buy_cost = sum(
        (fill.quantity * fill.price for fill in fills if fill.side.lower() == "buy"),
        start=Decimal("0"),
    )
    sell_proceeds = sum(
        (fill.quantity * fill.price for fill in fills if fill.side.lower() == "sell"),
        start=Decimal("0"),
    )
    return sell_proceeds - buy_cost
