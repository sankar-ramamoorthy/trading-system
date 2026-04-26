"""Tests for read-only trade review retrieval workflows."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from trading_system.domain.rules.rule_evaluation import RuleEvaluation
from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.infrastructure.memory.repositories import (
    InMemoryFillRepository,
    InMemoryMarketContextSnapshotRepository,
    InMemoryPositionRepository,
    InMemoryTradeIdeaRepository,
    InMemoryTradePlanRepository,
    InMemoryTradeReviewRepository,
    InMemoryTradeThesisRepository,
)
from trading_system.services.fill_service import FillService
from trading_system.services.position_service import PositionService
from trading_system.services.review_query_service import ReviewQueryService
from trading_system.services.review_service import ReviewService
from trading_system.services.trade_planning_service import TradePlanningService


def test_list_trade_reviews_returns_reviews_in_reviewed_order() -> None:
    """Review list items are ordered by review timestamp."""
    workflow = _Workflow()
    first_review = workflow.create_closed_review("First review.")
    second_review = workflow.create_closed_review("Second review.")

    items = workflow.query.list_trade_reviews()

    assert [item.review.id for item in items] == [first_review.id, second_review.id]
    assert items[0].trade_idea.purpose == "swing"
    assert items[0].trade_idea.direction == "long"


def test_list_trade_reviews_supports_exact_filters_and_sort_modes() -> None:
    """Review list filters by linked idea context, rating, and chronology."""
    workflow = _Workflow()
    first_review = workflow.create_closed_review(
        "First review.",
        purpose="swing",
        direction="long",
        rating=4,
        tags=["missed-exit", "risk-management"],
    )
    second_review = workflow.create_closed_review(
        "Second review.",
        purpose="day_trade",
        direction="short",
        rating=2,
        tags=["missed-exit"],
    )
    second_review.reviewed_at = first_review.reviewed_at + timedelta(seconds=1)

    filtered = workflow.query.list_trade_reviews(
        rating=4,
        purpose="swing",
        direction="long",
        tags=["missed_exit"],
    )

    assert [item.review.id for item in filtered] == [first_review.id]
    assert [item.review.id for item in workflow.query.list_trade_reviews(tags=["missed-exit"])] == [
        first_review.id,
        second_review.id,
    ]
    assert [item.review.id for item in workflow.query.list_trade_reviews(tags=["missed-exit", "risk-management"])] == [
        first_review.id,
    ]
    assert [item.review.id for item in workflow.query.list_trade_reviews(sort="newest")] == [
        second_review.id,
        first_review.id,
    ]


def test_get_trade_review_detail_returns_linked_trade_context() -> None:
    """Review detail includes linked position, plan, idea, and realized P&L."""
    workflow = _Workflow()
    review = workflow.create_closed_review("Followed the plan.")

    detail = workflow.query.get_trade_review_detail(review.id)

    assert detail.review == review
    assert detail.position.trade_plan_id == detail.trade_plan.id
    assert detail.trade_plan.trade_idea_id == detail.trade_idea.id
    assert detail.trade_idea.purpose == "swing"
    assert detail.realized_pnl == Decimal("150.00")


def test_get_trade_review_detail_includes_only_linked_market_context() -> None:
    """Review detail returns context snapshots linked to that review only."""
    workflow = _Workflow()
    review = workflow.create_closed_review("Followed the plan.")
    position = workflow.positions.get(review.position_id)
    older = workflow.add_market_context_snapshot(
        instrument_id=position.instrument_id,
        target_type="TradeReview",
        target_id=review.id,
        captured_at=datetime(2026, 4, 1, tzinfo=UTC),
    )
    newer = workflow.add_market_context_snapshot(
        instrument_id=position.instrument_id,
        target_type="TradeReview",
        target_id=review.id,
        captured_at=datetime(2026, 4, 2, tzinfo=UTC),
    )
    workflow.add_market_context_snapshot(
        instrument_id=position.instrument_id,
        target_type="Position",
        target_id=position.id,
        captured_at=datetime(2026, 4, 3, tzinfo=UTC),
    )

    detail = workflow.query.get_trade_review_detail(review.id)

    assert detail.market_context_snapshots == [older, newer]


def test_get_trade_review_detail_rejects_missing_review() -> None:
    """Review detail requires an existing trade review."""
    workflow = _Workflow()

    with pytest.raises(ValueError, match="Trade review does not exist"):
        workflow.query.get_trade_review_detail(uuid4())


class _Workflow:
    def __init__(self) -> None:
        self.ideas = InMemoryTradeIdeaRepository()
        self.theses = InMemoryTradeThesisRepository()
        self.plans = InMemoryTradePlanRepository()
        self.positions = InMemoryPositionRepository()
        self.fills = InMemoryFillRepository()
        self.reviews = InMemoryTradeReviewRepository()
        self.market_context_snapshots = InMemoryMarketContextSnapshotRepository()
        self.planning = TradePlanningService(self.ideas, self.theses, self.plans)
        self.position_service = PositionService(
            plan_repository=self.plans,
            idea_repository=self.ideas,
            position_repository=self.positions,
            lifecycle_event_repository=_NoOpLifecycleEventRepository(),
        )
        self.fill_service = FillService(
            position_repository=self.positions,
            fill_repository=self.fills,
            lifecycle_event_repository=_NoOpLifecycleEventRepository(),
            order_intent_repository=_NoOpOrderIntentRepository(),
        )
        self.review_service = ReviewService(
            position_repository=self.positions,
            review_repository=self.reviews,
            lifecycle_event_repository=_NoOpLifecycleEventRepository(),
        )
        self.query = ReviewQueryService(
            review_repository=self.reviews,
            position_repository=self.positions,
            plan_repository=self.plans,
            idea_repository=self.ideas,
            fill_repository=self.fills,
            market_context_snapshot_repository=self.market_context_snapshots,
        )

    def create_closed_review(
        self,
        summary: str,
        *,
        purpose: str = "swing",
        direction: str = "long",
        rating: int | None = None,
        tags: list[str] | None = None,
    ):
        idea = self.planning.create_trade_idea(
            instrument_id=uuid4(),
            playbook_id=uuid4(),
            purpose=purpose,
            direction=direction,
            horizon="days_to_weeks",
        )
        thesis = self.planning.create_trade_thesis(
            trade_idea_id=idea.id,
            reasoning="Setup has a clear catalyst.",
        )
        plan = self.planning.create_trade_plan(
            trade_idea_id=idea.id,
            trade_thesis_id=thesis.id,
            entry_criteria="Breakout confirmation.",
            invalidation="Close below setup low.",
            risk_model="Defined stop and max loss.",
        )
        approved = self.planning.approve_trade_plan(plan.id)
        position = self.position_service.open_position_from_plan(approved.id)
        self.fill_service.record_manual_fill(
            position_id=position.id,
            side="buy",
            quantity=Decimal("100"),
            price=Decimal("25.50"),
        )
        self.fill_service.record_manual_fill(
            position_id=position.id,
            side="sell",
            quantity=Decimal("100"),
            price=Decimal("27.00"),
        )
        return self.review_service.create_trade_review(
            position_id=position.id,
            summary=summary,
            what_went_well="Entry was clean.",
            what_went_poorly="Exit could be faster.",
            rating=rating,
            tags=tags,
        )

    def add_market_context_snapshot(
        self,
        *,
        instrument_id,
        target_type: str,
        target_id,
        captured_at: datetime,
    ) -> MarketContextSnapshot:
        snapshot = MarketContextSnapshot(
            instrument_id=instrument_id,
            target_type=target_type,
            target_id=target_id,
            context_type="price_snapshot",
            source="test",
            observed_at=captured_at,
            captured_at=captured_at,
            payload={"symbol": "AAPL"},
        )
        self.market_context_snapshots.add(snapshot)
        return snapshot


class _NoOpLifecycleEventRepository:
    def add(self, event) -> None:
        self._last_event = event

    def list_by_entity(self, entity_type, entity_id) -> list:
        return []


class _NoOpOrderIntentRepository:
    def get(self, order_intent_id):
        return None
