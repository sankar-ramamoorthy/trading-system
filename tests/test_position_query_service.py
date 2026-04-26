"""Tests for read-only position retrieval workflows."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from trading_system.domain.rules.rule_evaluation import RuleEvaluation
from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.lifecycle import LifecycleEvent
from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.domain.trading.order_intent import OrderSide, OrderType
from trading_system.domain.trading.position import Position
from trading_system.infrastructure.memory.repositories import (
    InMemoryFillRepository,
    InMemoryLifecycleEventRepository,
    InMemoryMarketContextSnapshotRepository,
    InMemoryOrderIntentRepository,
    InMemoryPositionRepository,
    InMemoryRuleEvaluationRepository,
    InMemoryTradeIdeaRepository,
    InMemoryTradePlanRepository,
    InMemoryTradeReviewRepository,
    InMemoryTradeThesisRepository,
)
from trading_system.services.create_order_intent_service import CreateOrderIntentService
from trading_system.services.fill_service import FillService
from trading_system.services.position_query_service import PositionQueryService
from trading_system.services.position_service import PositionService
from trading_system.services.review_service import ReviewService
from trading_system.services.trade_planning_service import TradePlanningService


def test_list_positions_can_filter_by_lifecycle_state() -> None:
    """Position lists can be filtered by open or closed state."""
    workflow = _workflow()
    open_position = workflow.open_position()
    closed_position = workflow.open_position()
    workflow.fill_service.record_manual_fill(
        position_id=closed_position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("20"),
    )
    workflow.fill_service.record_manual_fill(
        position_id=closed_position.id,
        side="sell",
        quantity=Decimal("100"),
        price=Decimal("22"),
    )

    assert [position.id for position in workflow.query.list_positions()] == [
        open_position.id,
        closed_position.id,
    ]
    assert [position.id for position in workflow.query.list_positions("open")] == [
        open_position.id
    ]
    assert [position.id for position in workflow.query.list_positions("closed")] == [
        closed_position.id
    ]


def test_list_positions_supports_purpose_review_filters_and_sort_modes() -> None:
    """Position lists can filter by purpose, review state, and sort newest first."""
    workflow = _workflow()
    reviewed_position = workflow.open_position(purpose="swing")
    unreviewed_position = workflow.open_position(purpose="day_trade")
    workflow.fill_service.record_manual_fill(
        position_id=reviewed_position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("20"),
    )
    workflow.fill_service.record_manual_fill(
        position_id=reviewed_position.id,
        side="sell",
        quantity=Decimal("100"),
        price=Decimal("22"),
    )
    workflow.review_service.create_trade_review(
        position_id=reviewed_position.id,
        summary="Reviewed trade.",
        what_went_well="Entry was clear.",
        what_went_poorly="Exit was late.",
    )

    assert [position.id for position in workflow.query.list_positions(purpose="swing")] == [
        reviewed_position.id
    ]
    assert [position.id for position in workflow.query.list_positions(has_review=True)] == [
        reviewed_position.id
    ]
    assert [
        position.id
        for position in workflow.query.list_positions(has_review=False, sort="newest")
    ] == [unreviewed_position.id]


def test_get_position_detail_returns_linked_records() -> None:
    """Position detail includes linked idea, plan, order intents, fills, and review."""
    workflow = _workflow()
    position = workflow.open_position()
    order_intent = workflow.create_order_intent(position.trade_plan_id)
    first_fill = workflow.fill_service.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("50"),
        price=Decimal("20"),
        order_intent_id=order_intent.id,
    )
    second_fill = workflow.fill_service.record_manual_fill(
        position_id=position.id,
        side="sell",
        quantity=Decimal("50"),
        price=Decimal("22"),
    )
    review = workflow.review_service.create_trade_review(
        position_id=position.id,
        summary="Followed the plan.",
        what_went_well="Entry was clear.",
        what_went_poorly="Exit was late.",
    )

    detail = workflow.query.get_position_detail(position.id)

    assert detail.position.id == position.id
    assert detail.trade_plan.id == position.trade_plan_id
    assert detail.trade_idea.id == detail.trade_plan.trade_idea_id
    assert detail.order_intents == [order_intent]
    assert detail.fills == [first_fill, second_fill]
    assert detail.review == review
    assert detail.realized_pnl == Decimal("100")


def test_get_position_detail_includes_only_linked_market_context() -> None:
    """Position detail returns context snapshots linked to that position only."""
    workflow = _workflow()
    position = workflow.open_position()
    older = workflow.add_market_context_snapshot(
        instrument_id=position.instrument_id,
        target_type="Position",
        target_id=position.id,
        captured_at=datetime(2026, 4, 1, tzinfo=UTC),
    )
    newer = workflow.add_market_context_snapshot(
        instrument_id=position.instrument_id,
        target_type="Position",
        target_id=position.id,
        captured_at=datetime(2026, 4, 2, tzinfo=UTC),
    )
    workflow.add_market_context_snapshot(
        instrument_id=position.instrument_id,
        target_type="TradePlan",
        target_id=position.trade_plan_id,
        captured_at=datetime(2026, 4, 3, tzinfo=UTC),
    )

    detail = workflow.query.get_position_detail(position.id)

    assert detail.market_context_snapshots == [older, newer]


def test_get_position_detail_computes_realized_pnl_for_multiple_buys() -> None:
    """Closed positions compute realized P&L from total buy cost and sell proceeds."""
    workflow = _workflow()
    position = workflow.open_position()
    workflow.fill_service.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("40"),
        price=Decimal("10"),
    )
    workflow.fill_service.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("60"),
        price=Decimal("12"),
    )
    workflow.fill_service.record_manual_fill(
        position_id=position.id,
        side="sell",
        quantity=Decimal("100"),
        price=Decimal("15"),
    )

    detail = workflow.query.get_position_detail(position.id)

    assert detail.realized_pnl == Decimal("380")


def test_get_position_detail_returns_none_realized_pnl_for_open_position() -> None:
    """Open positions do not report realized P&L."""
    workflow = _workflow()
    position = workflow.open_position()
    workflow.fill_service.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("20"),
    )

    detail = workflow.query.get_position_detail(position.id)

    assert detail.realized_pnl is None


def test_get_position_detail_rejects_missing_position() -> None:
    """Position detail requires an existing position."""
    workflow = _workflow()

    with pytest.raises(ValueError, match="Position does not exist"):
        workflow.query.get_position_detail(uuid4())


def test_position_timeline_is_ordered_by_occurred_at() -> None:
    """Timeline events are returned in chronological order."""
    workflow = _workflow()
    position = workflow.open_position()
    earlier = position.opened_at - timedelta(days=1)
    later = position.opened_at + timedelta(days=1)
    workflow.lifecycle_events.add(
        LifecycleEvent(
            entity_id=position.id,
            entity_type="Position",
            event_type="LATER",
            note="Later event.",
            occurred_at=later,
        )
    )
    workflow.lifecycle_events.add(
        LifecycleEvent(
            entity_id=position.id,
            entity_type="Position",
            event_type="EARLIER",
            note="Earlier event.",
            occurred_at=earlier,
        )
    )

    events = workflow.query.get_position_timeline(position.id)

    assert [event.event_type for event in events] == [
        "EARLIER",
        "POSITION_OPENED",
        "LATER",
    ]


class _Workflow:
    def __init__(self) -> None:
        self.ideas = InMemoryTradeIdeaRepository()
        self.theses = InMemoryTradeThesisRepository()
        self.plans = InMemoryTradePlanRepository()
        self.positions = InMemoryPositionRepository()
        self.fills = InMemoryFillRepository()
        self.order_intents = InMemoryOrderIntentRepository()
        self.lifecycle_events = InMemoryLifecycleEventRepository()
        self.reviews = InMemoryTradeReviewRepository()
        self.market_context_snapshots = InMemoryMarketContextSnapshotRepository()
        self.evaluations = InMemoryRuleEvaluationRepository()
        self.planning = TradePlanningService(self.ideas, self.theses, self.plans)
        self.position_service = PositionService(
            plan_repository=self.plans,
            idea_repository=self.ideas,
            position_repository=self.positions,
            lifecycle_event_repository=self.lifecycle_events,
        )
        self.fill_service = FillService(
            position_repository=self.positions,
            fill_repository=self.fills,
            lifecycle_event_repository=self.lifecycle_events,
            order_intent_repository=self.order_intents,
        )
        self.order_intent_service = CreateOrderIntentService(
            plan_repository=self.plans,
            order_intent_repository=self.order_intents,
            evaluation_repository=self.evaluations,
            lifecycle_event_repository=self.lifecycle_events,
        )
        self.review_service = ReviewService(
            position_repository=self.positions,
            review_repository=self.reviews,
            lifecycle_event_repository=self.lifecycle_events,
        )
        self.query = PositionQueryService(
            position_repository=self.positions,
            plan_repository=self.plans,
            idea_repository=self.ideas,
            order_intent_repository=self.order_intents,
            fill_repository=self.fills,
            review_repository=self.reviews,
            lifecycle_event_repository=self.lifecycle_events,
            market_context_snapshot_repository=self.market_context_snapshots,
        )

    def open_position(self, *, purpose: str = "swing") -> Position:
        idea = self.planning.create_trade_idea(
            instrument_id=uuid4(),
            playbook_id=uuid4(),
            purpose=purpose,
            direction="long",
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
        self.evaluations.add(
            RuleEvaluation(
                rule_id=uuid4(),
                entity_type="TradePlan",
                entity_id=approved.id,
                passed=True,
            )
        )
        return self.position_service.open_position_from_plan(approved.id)

    def create_order_intent(self, trade_plan_id):
        return self.order_intent_service.create_order_intent(
            trade_plan_id=trade_plan_id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("50"),
            limit_price=Decimal("20"),
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


def _workflow() -> _Workflow:
    return _Workflow()
