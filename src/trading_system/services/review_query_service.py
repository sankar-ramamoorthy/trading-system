"""Read-only workflows for persisted trade review retrieval."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.idea import TradeIdea
from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.domain.trading.plan import TradePlan
from trading_system.domain.trading.position import Position
from trading_system.domain.trading.review import TradeReview
from trading_system.ports.repositories import (
    FillRepository,
    MarketContextSnapshotRepository,
    PositionRepository,
    TradeIdeaRepository,
    TradePlanRepository,
    TradeReviewRepository,
)


@dataclass(frozen=True)
class TradeReviewListItem:
    """Compact read model for listing persisted trade reviews."""

    review: TradeReview
    position: Position
    trade_plan: TradePlan
    trade_idea: TradeIdea


@dataclass(frozen=True)
class TradeReviewDetail:
    """Composite read model for inspecting one persisted trade review."""

    review: TradeReview
    position: Position
    trade_plan: TradePlan
    trade_idea: TradeIdea
    realized_pnl: Decimal | None
    market_context_snapshots: list[MarketContextSnapshot]


class ReviewQueryService:
    """Coordinates read-only trade review retrieval without persistence details."""

    def __init__(
        self,
        review_repository: TradeReviewRepository,
        position_repository: PositionRepository,
        plan_repository: TradePlanRepository,
        idea_repository: TradeIdeaRepository,
        fill_repository: FillRepository,
        market_context_snapshot_repository: MarketContextSnapshotRepository,
    ) -> None:
        self._reviews = review_repository
        self._positions = position_repository
        self._plans = plan_repository
        self._ideas = idea_repository
        self._fills = fill_repository
        self._market_context_snapshots = market_context_snapshot_repository

    def list_trade_reviews(
        self,
        rating: int | None = None,
        purpose: str | None = None,
        direction: str | None = None,
        sort: Literal["oldest", "newest"] = "oldest",
    ) -> list[TradeReviewListItem]:
        """Return persisted trade reviews with exact filters and chronological sorting."""
        items = [
            self._build_list_item(review)
            for review in self._reviews.list_all()
        ]
        if rating is not None:
            items = [item for item in items if item.review.rating == rating]
        if purpose is not None:
            items = [item for item in items if item.trade_idea.purpose == purpose]
        if direction is not None:
            items = [item for item in items if item.trade_idea.direction == direction]
        return sorted(
            items,
            key=lambda item: item.review.reviewed_at,
            reverse=sort == "newest",
        )

    def get_trade_review_detail(self, review_id: UUID) -> TradeReviewDetail:
        """Return one trade review with linked position, plan, and idea records."""
        review = self._reviews.get(review_id)
        if review is None:
            raise ValueError("Trade review does not exist.")

        position, plan, idea = self._load_linked_records(review)
        fills = sorted(
            self._fills.list_by_position_id(position.id),
            key=lambda fill: fill.filled_at,
        )
        market_context_snapshots = sorted(
            self._market_context_snapshots.list_by_target("TradeReview", review.id),
            key=lambda snapshot: snapshot.captured_at,
        )
        return TradeReviewDetail(
            review=review,
            position=position,
            trade_plan=plan,
            trade_idea=idea,
            realized_pnl=_calculate_realized_pnl(position, fills),
            market_context_snapshots=market_context_snapshots,
        )

    def _build_list_item(self, review: TradeReview) -> TradeReviewListItem:
        """Build a compact list item with linked trade context."""
        position, plan, idea = self._load_linked_records(review)
        return TradeReviewListItem(
            review=review,
            position=position,
            trade_plan=plan,
            trade_idea=idea,
        )

    def _load_linked_records(
        self,
        review: TradeReview,
    ) -> tuple[Position, TradePlan, TradeIdea]:
        """Load the position, plan, and idea linked to a trade review."""
        position = self._positions.get(review.position_id)
        if position is None:
            raise ValueError("Position does not exist for trade review.")

        plan = self._plans.get(position.trade_plan_id)
        if plan is None:
            raise ValueError("Trade plan does not exist for trade review.")

        idea = self._ideas.get(plan.trade_idea_id)
        if idea is None:
            raise ValueError("Trade idea does not exist for trade review.")

        return position, plan, idea


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
