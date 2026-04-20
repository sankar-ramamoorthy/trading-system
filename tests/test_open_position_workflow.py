"""Tests for opening a position from an approved trade plan."""

from uuid import uuid4

import pytest

from trading_system.infrastructure.memory.repositories import (
    InMemoryLifecycleEventRepository,
    InMemoryPositionRepository,
    InMemoryTradeIdeaRepository,
    InMemoryTradePlanRepository,
    InMemoryTradeThesisRepository,
)
from trading_system.services.position_service import PositionService
from trading_system.services.trade_planning_service import TradePlanningService


def test_opening_position_from_approved_plan_succeeds() -> None:
    """An approved trade plan can become an open position."""
    planning, position_service, ideas, plans, positions, lifecycle_events = (
        _workflow_services()
    )
    instrument_id = uuid4()
    plan = _approved_plan(planning, instrument_id=instrument_id, purpose="swing")

    position = position_service.open_position_from_plan(plan.id)

    assert position.trade_plan_id == plan.id
    assert position.instrument_id == instrument_id
    assert position.purpose == "swing"
    assert position.lifecycle_state == "open"
    assert position.opened_at is not None
    assert position.closed_at is None
    assert positions.get(position.id) == position
    assert plans.get(plan.id) == plan
    assert ideas.get(plan.trade_idea_id) is not None

    events = list(lifecycle_events.items.values())
    assert len(events) == 1
    assert events[0].entity_id == position.id
    assert events[0].entity_type == "Position"
    assert events[0].event_type == "POSITION_OPENED"


def test_opening_position_from_unapproved_plan_fails() -> None:
    """A draft trade plan cannot become a position."""
    planning, position_service, _, _, positions, lifecycle_events = _workflow_services()
    idea = planning.create_trade_idea(
        instrument_id=uuid4(),
        playbook_id=uuid4(),
        purpose="swing",
        direction="long",
        horizon="days_to_weeks",
    )
    thesis = planning.create_trade_thesis(
        trade_idea_id=idea.id,
        reasoning="Setup has a clear catalyst.",
    )
    plan = planning.create_trade_plan(
        trade_idea_id=idea.id,
        trade_thesis_id=thesis.id,
        entry_criteria="Breakout confirmation.",
        invalidation="Close below setup low.",
        risk_model="Defined stop and max loss.",
    )

    with pytest.raises(ValueError, match="must be approved"):
        position_service.open_position_from_plan(plan.id)

    assert len(positions.items) == 0
    assert len(lifecycle_events.items) == 0


def test_opening_position_from_missing_plan_fails() -> None:
    """A position requires an existing trade plan."""
    _, position_service, _, _, positions, lifecycle_events = _workflow_services()

    with pytest.raises(ValueError, match="Trade plan does not exist"):
        position_service.open_position_from_plan(uuid4())

    assert len(positions.items) == 0
    assert len(lifecycle_events.items) == 0


def _workflow_services() -> tuple[
    TradePlanningService,
    PositionService,
    InMemoryTradeIdeaRepository,
    InMemoryTradePlanRepository,
    InMemoryPositionRepository,
    InMemoryLifecycleEventRepository,
]:
    ideas = InMemoryTradeIdeaRepository()
    theses = InMemoryTradeThesisRepository()
    plans = InMemoryTradePlanRepository()
    positions = InMemoryPositionRepository()
    lifecycle_events = InMemoryLifecycleEventRepository()
    planning = TradePlanningService(ideas, theses, plans)
    position_service = PositionService(
        plan_repository=plans,
        idea_repository=ideas,
        position_repository=positions,
        lifecycle_event_repository=lifecycle_events,
    )
    return planning, position_service, ideas, plans, positions, lifecycle_events


def _approved_plan(
    planning: TradePlanningService,
    instrument_id,
    purpose: str,
):
    idea = planning.create_trade_idea(
        instrument_id=instrument_id,
        playbook_id=uuid4(),
        purpose=purpose,
        direction="long",
        horizon="days_to_weeks",
    )
    thesis = planning.create_trade_thesis(
        trade_idea_id=idea.id,
        reasoning="Setup has a clear catalyst.",
    )
    plan = planning.create_trade_plan(
        trade_idea_id=idea.id,
        trade_thesis_id=thesis.id,
        entry_criteria="Breakout confirmation.",
        invalidation="Close below setup low.",
        risk_model="Defined stop and max loss.",
    )
    return planning.approve_trade_plan(plan.id)
