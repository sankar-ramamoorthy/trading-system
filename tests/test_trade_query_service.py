"""Tests for read-only trade idea, thesis, and plan retrieval workflows."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from trading_system.domain.trading.idea import TradeIdea
from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.domain.trading.plan import TradePlan
from trading_system.domain.trading.thesis import TradeThesis
from trading_system.infrastructure.memory.repositories import (
    InMemoryMarketContextSnapshotRepository,
    InMemoryOrderIntentRepository,
    InMemoryPositionRepository,
    InMemoryRuleEvaluationRepository,
    InMemoryTradeIdeaRepository,
    InMemoryTradePlanRepository,
    InMemoryTradeThesisRepository,
)
from trading_system.services.trade_query_service import TradeQueryService


def test_list_trade_ideas_supports_exact_filters_and_sort_modes() -> None:
    """Idea listing applies exact filters and deterministic oldest/newest sorting."""
    workflow = _Workflow()
    base = datetime(2026, 4, 1, tzinfo=UTC)
    oldest = workflow.add_trade_idea(
        purpose="swing",
        direction="long",
        status="draft",
        created_at=base,
    )
    middle = workflow.add_trade_idea(
        purpose="swing",
        direction="short",
        status="approved",
        created_at=base + timedelta(days=1),
    )
    newest = workflow.add_trade_idea(
        purpose="day_trade",
        direction="long",
        status="draft",
        created_at=base + timedelta(days=2),
    )

    assert workflow.query.list_trade_ideas(
        purpose="swing",
        direction="long",
        status="draft",
    ) == [oldest]
    assert [idea.id for idea in workflow.query.list_trade_ideas(sort="newest")] == [
        newest.id,
        middle.id,
        oldest.id,
    ]


def test_in_memory_trade_thesis_repository_list_all_returns_all_items() -> None:
    """In-memory thesis repositories expose list_all for read-side queries."""
    repository = InMemoryTradeThesisRepository()
    first = TradeThesis(trade_idea_id=uuid4(), reasoning="First thesis.")
    second = TradeThesis(trade_idea_id=uuid4(), reasoning="Second thesis.")

    repository.add(first)
    repository.add(second)

    assert repository.list_all() == [first, second]


def test_list_trade_theses_orders_by_linked_trade_idea_creation_time() -> None:
    """Thesis listing uses linked trade-idea timestamps for chronological ordering."""
    workflow = _Workflow()
    base = datetime(2026, 4, 1, tzinfo=UTC)
    newer_idea = workflow.add_trade_idea(created_at=base + timedelta(days=2))
    older_idea = workflow.add_trade_idea(created_at=base)
    older_thesis = workflow.add_trade_thesis(trade_idea_id=older_idea.id)
    newer_thesis = workflow.add_trade_thesis(trade_idea_id=newer_idea.id)

    items = workflow.query.list_trade_theses()

    assert [item.trade_thesis.id for item in items] == [older_thesis.id, newer_thesis.id]
    assert [item.trade_thesis.id for item in workflow.query.list_trade_theses(sort="newest")] == [
        newer_thesis.id,
        older_thesis.id,
    ]


def test_list_trade_theses_supports_exact_filters_and_plan_flag() -> None:
    """Thesis listing filters by linked idea context and whether plans exist."""
    workflow = _Workflow()
    base = datetime(2026, 4, 1, tzinfo=UTC)
    swing_long = workflow.add_trade_idea(
        purpose="swing",
        direction="long",
        created_at=base,
    )
    swing_short = workflow.add_trade_idea(
        purpose="swing",
        direction="short",
        created_at=base + timedelta(days=1),
    )
    idea_without_plan = workflow.add_trade_idea(
        purpose="day_trade",
        direction="long",
        created_at=base + timedelta(days=2),
    )
    thesis_with_plan = workflow.add_trade_thesis(trade_idea_id=swing_long.id)
    second_thesis = workflow.add_trade_thesis(trade_idea_id=swing_short.id)
    thesis_without_plan = workflow.add_trade_thesis(trade_idea_id=idea_without_plan.id)
    workflow.add_trade_plan(
        trade_idea_id=swing_long.id,
        trade_thesis_id=thesis_with_plan.id,
        approval_state="approved",
        created_at=base + timedelta(days=3),
    )
    workflow.add_trade_plan(
        trade_idea_id=swing_short.id,
        trade_thesis_id=second_thesis.id,
        approval_state="draft",
        created_at=base + timedelta(days=4),
    )

    assert [item.trade_thesis.id for item in workflow.query.list_trade_theses(purpose="swing")] == [
        thesis_with_plan.id,
        second_thesis.id,
    ]
    assert [
        item.trade_thesis.id
        for item in workflow.query.list_trade_theses(direction="long", has_plan=True)
    ] == [thesis_with_plan.id]
    assert [
        item.trade_thesis.id
        for item in workflow.query.list_trade_theses(purpose="day_trade", has_plan=False)
    ] == [thesis_without_plan.id]


def test_get_trade_thesis_detail_includes_linked_trade_idea_and_trade_plans() -> None:
    """Thesis detail returns the linked trade idea and downstream trade plans."""
    workflow = _Workflow()
    idea = workflow.add_trade_idea()
    thesis = workflow.add_trade_thesis(trade_idea_id=idea.id)
    first_plan = workflow.add_trade_plan(trade_idea_id=idea.id, trade_thesis_id=thesis.id)
    second_plan = workflow.add_trade_plan(
        trade_idea_id=idea.id,
        trade_thesis_id=thesis.id,
        created_at=first_plan.created_at + timedelta(hours=1),
    )

    detail = workflow.query.get_trade_thesis_detail(thesis.id)

    assert detail.trade_thesis == thesis
    assert detail.trade_idea == idea
    assert detail.trade_plans == [first_plan, second_plan]


def test_list_trade_plans_supports_exact_filters_and_sort_modes() -> None:
    """Plan listing filters by approval state and supports oldest/newest ordering."""
    workflow = _Workflow()
    idea = workflow.add_trade_idea()
    first_thesis = workflow.add_trade_thesis(trade_idea_id=idea.id)
    second_thesis = workflow.add_trade_thesis(trade_idea_id=idea.id)
    base = datetime(2026, 4, 1, tzinfo=UTC)
    approved = workflow.add_trade_plan(
        trade_idea_id=idea.id,
        trade_thesis_id=first_thesis.id,
        approval_state="approved",
        created_at=base,
    )
    draft = workflow.add_trade_plan(
        trade_idea_id=idea.id,
        trade_thesis_id=second_thesis.id,
        approval_state="draft",
        created_at=base + timedelta(days=1),
    )

    assert workflow.query.list_trade_plans(approval_state="approved") == [approved]
    assert [plan.id for plan in workflow.query.list_trade_plans(sort="newest")] == [
        draft.id,
        approved.id,
    ]


def test_get_trade_plan_detail_includes_only_linked_market_context() -> None:
    """Plan detail returns context snapshots linked to that trade plan only."""
    workflow = _Workflow()
    idea = workflow.add_trade_idea()
    thesis = workflow.add_trade_thesis(trade_idea_id=idea.id)
    plan = workflow.add_trade_plan(trade_idea_id=idea.id, trade_thesis_id=thesis.id)
    older = workflow.add_market_context_snapshot(
        instrument_id=idea.instrument_id,
        target_type="TradePlan",
        target_id=plan.id,
        captured_at=datetime(2026, 4, 1, tzinfo=UTC),
    )
    newer = workflow.add_market_context_snapshot(
        instrument_id=idea.instrument_id,
        target_type="TradePlan",
        target_id=plan.id,
        captured_at=datetime(2026, 4, 2, tzinfo=UTC),
    )
    workflow.add_market_context_snapshot(
        instrument_id=idea.instrument_id,
        target_type="Position",
        target_id=uuid4(),
        captured_at=datetime(2026, 4, 3, tzinfo=UTC),
    )

    detail = workflow.query.get_trade_plan_detail(plan.id)

    assert detail.market_context_snapshots == [older, newer]


def test_get_trade_thesis_detail_rejects_missing_thesis() -> None:
    """Thesis detail requires an existing persisted thesis."""
    workflow = _Workflow()

    with pytest.raises(ValueError, match="Trade thesis does not exist"):
        workflow.query.get_trade_thesis_detail(uuid4())


class _Workflow:
    def __init__(self) -> None:
        self.ideas = InMemoryTradeIdeaRepository()
        self.theses = InMemoryTradeThesisRepository()
        self.plans = InMemoryTradePlanRepository()
        self.evaluations = InMemoryRuleEvaluationRepository()
        self.order_intents = InMemoryOrderIntentRepository()
        self.positions = InMemoryPositionRepository()
        self.market_context_snapshots = InMemoryMarketContextSnapshotRepository()
        self.query = TradeQueryService(
            idea_repository=self.ideas,
            thesis_repository=self.theses,
            plan_repository=self.plans,
            evaluation_repository=self.evaluations,
            order_intent_repository=self.order_intents,
            position_repository=self.positions,
            market_context_snapshot_repository=self.market_context_snapshots,
        )

    def add_trade_idea(
        self,
        *,
        purpose: str = "swing",
        direction: str = "long",
        status: str = "draft",
        created_at: datetime | None = None,
    ) -> TradeIdea:
        idea = TradeIdea(
            instrument_id=uuid4(),
            playbook_id=uuid4(),
            purpose=purpose,
            direction=direction,
            horizon="days_to_weeks",
            status=status,
            created_at=created_at or datetime.now(UTC),
        )
        self.ideas.add(idea)
        return idea

    def add_trade_thesis(self, *, trade_idea_id) -> TradeThesis:
        thesis = TradeThesis(
            trade_idea_id=trade_idea_id,
            reasoning="Setup has a clear catalyst.",
        )
        self.theses.add(thesis)
        return thesis

    def add_trade_plan(
        self,
        *,
        trade_idea_id,
        trade_thesis_id,
        approval_state: str = "draft",
        created_at: datetime | None = None,
    ) -> TradePlan:
        plan = TradePlan(
            trade_idea_id=trade_idea_id,
            trade_thesis_id=trade_thesis_id,
            entry_criteria="Breakout confirmation.",
            invalidation="Close below setup low.",
            risk_model="Defined stop and max loss.",
            approval_state=approval_state,
            created_at=created_at or datetime.now(UTC),
        )
        self.plans.add(plan)
        return plan

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
