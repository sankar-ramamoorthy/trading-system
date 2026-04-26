"""Tests for read-only market context import and query workflows."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from trading_system.infrastructure.memory.repositories import (
    InMemoryFillRepository,
    InMemoryLifecycleEventRepository,
    InMemoryMarketContextSnapshotRepository,
    InMemoryOrderIntentRepository,
    InMemoryPositionRepository,
    InMemoryTradeIdeaRepository,
    InMemoryTradePlanRepository,
    InMemoryTradeReviewRepository,
    InMemoryTradeThesisRepository,
)
from trading_system.ports.market_context import ImportedMarketContext
from trading_system.services.fill_service import FillService
from trading_system.services.market_context_service import (
    MarketContextImportService,
    MarketContextQueryService,
)
from trading_system.services.position_service import PositionService
from trading_system.services.review_service import ReviewService
from trading_system.services.trade_planning_service import TradePlanningService


def test_import_context_with_explicit_instrument() -> None:
    """Unlinked context snapshots require and preserve an explicit instrument."""
    workflow = _Workflow()
    instrument_id = uuid4()

    snapshot = workflow.import_service.import_context(
        _Source(),
        source="local-file",
        source_ref="context.json",
        instrument_id=instrument_id,
    )

    assert snapshot.instrument_id == instrument_id
    assert snapshot.target_type is None
    assert snapshot.target_id is None
    assert workflow.query_service.get_snapshot(snapshot.id) == snapshot


def test_import_context_derives_instrument_from_trade_plan_target() -> None:
    """Trade plan context is linked without duplicating canonical trade meaning."""
    workflow = _Workflow()
    plan_id = workflow.create_approved_plan()
    plan = workflow.plans.get(plan_id)
    idea = workflow.ideas.get(plan.trade_idea_id)

    snapshot = workflow.import_service.import_context(
        _Source(),
        source="local-file",
        target_type="TradePlan",
        target_id=plan_id,
    )

    assert snapshot.instrument_id == idea.instrument_id
    assert snapshot.target_type == "TradePlan"
    assert snapshot.target_id == plan_id
    assert workflow.query_service.list_by_target("TradePlan", plan_id) == [snapshot]


def test_import_context_derives_instrument_from_position_and_review_targets() -> None:
    """Position and review context resolve through existing lifecycle records."""
    workflow = _Workflow()
    plan_id = workflow.create_approved_plan()
    position_id = workflow.open_position(plan_id)
    review_id = workflow.close_and_review(position_id)
    position = workflow.positions.get(position_id)

    position_snapshot = workflow.import_service.import_context(
        _Source(context_type="price_snapshot"),
        source="local-file",
        target_type="Position",
        target_id=position_id,
    )
    review_snapshot = workflow.import_service.import_context(
        _Source(context_type="calendar"),
        source="local-file",
        target_type="TradeReview",
        target_id=review_id,
    )

    assert position_snapshot.instrument_id == position.instrument_id
    assert review_snapshot.instrument_id == position.instrument_id
    assert workflow.query_service.list_by_instrument_id(position.instrument_id) == [
        position_snapshot,
        review_snapshot,
    ]


def test_import_context_rejects_missing_or_mismatched_targets() -> None:
    """Context links must point to existing records and matching instruments."""
    workflow = _Workflow()
    plan_id = workflow.create_approved_plan()

    with pytest.raises(ValueError, match="Trade plan does not exist"):
        workflow.import_service.import_context(
            _Source(),
            source="local-file",
            target_type="TradePlan",
            target_id=uuid4(),
        )

    with pytest.raises(ValueError, match="Instrument id does not match"):
        workflow.import_service.import_context(
            _Source(),
            source="local-file",
            instrument_id=uuid4(),
            target_type="TradePlan",
            target_id=plan_id,
        )


def test_import_context_does_not_mutate_canonical_trade_records() -> None:
    """Context import stores support data without altering trade state."""
    workflow = _Workflow()
    plan_id = workflow.create_approved_plan()
    plan_before = workflow.plans.get(plan_id)

    workflow.import_service.import_context(
        _Source(),
        source="local-file",
        target_type="TradePlan",
        target_id=plan_id,
    )

    assert workflow.plans.get(plan_id) == plan_before
    assert workflow.positions.list_all() == []


class _Source:
    def __init__(self, context_type: str = "price_snapshot") -> None:
        self._context_type = context_type

    def load(self) -> ImportedMarketContext:
        return ImportedMarketContext(
            context_type=self._context_type,
            observed_at=datetime(2026, 4, 26, 16, 0, tzinfo=UTC),
            payload={"symbol": "AAPL", "last": "185.25"},
        )


class _Workflow:
    def __init__(self) -> None:
        self.ideas = InMemoryTradeIdeaRepository()
        self.theses = InMemoryTradeThesisRepository()
        self.plans = InMemoryTradePlanRepository()
        self.positions = InMemoryPositionRepository()
        self.order_intents = InMemoryOrderIntentRepository()
        self.fills = InMemoryFillRepository()
        self.lifecycle_events = InMemoryLifecycleEventRepository()
        self.reviews = InMemoryTradeReviewRepository()
        self.snapshots = InMemoryMarketContextSnapshotRepository()
        self.planning = TradePlanningService(self.ideas, self.theses, self.plans)
        self.import_service = MarketContextImportService(
            snapshot_repository=self.snapshots,
            plan_repository=self.plans,
            position_repository=self.positions,
            review_repository=self.reviews,
            idea_repository=self.ideas,
        )
        self.query_service = MarketContextQueryService(self.snapshots)

    def create_approved_plan(self):
        idea = self.planning.create_trade_idea(
            instrument_id=uuid4(),
            playbook_id=uuid4(),
            purpose="swing",
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
        return self.planning.approve_trade_plan(plan.id).id

    def open_position(self, plan_id):
        return PositionService(
            plan_repository=self.plans,
            idea_repository=self.ideas,
            position_repository=self.positions,
            lifecycle_event_repository=self.lifecycle_events,
        ).open_position_from_plan(plan_id).id

    def close_and_review(self, position_id):
        fill_service = FillService(
            position_repository=self.positions,
            fill_repository=self.fills,
            lifecycle_event_repository=self.lifecycle_events,
            order_intent_repository=self.order_intents,
        )
        fill_service.record_manual_fill(
            position_id=position_id,
            side="buy",
            quantity=Decimal("100"),
            price=Decimal("25.50"),
        )
        fill_service.record_manual_fill(
            position_id=position_id,
            side="sell",
            quantity=Decimal("100"),
            price=Decimal("27"),
        )
        return ReviewService(
            position_repository=self.positions,
            review_repository=self.reviews,
            lifecycle_event_repository=self.lifecycle_events,
        ).create_trade_review(
            position_id=position_id,
            summary="Followed the plan.",
            what_went_well="Entry was clear.",
            what_went_poorly="Exit was late.",
        ).id
