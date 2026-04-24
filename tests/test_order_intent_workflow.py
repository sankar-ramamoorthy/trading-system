"""Tests for narrow order-intent creation and linked fills."""

from decimal import Decimal
from uuid import uuid4

import pytest

from trading_system.domain.rules.rule import Rule
from trading_system.domain.rules.rule_evaluation import RuleEvaluation
from trading_system.domain.trading.order_intent import OrderIntentStatus, OrderSide, OrderType
from trading_system.infrastructure.memory.repositories import (
    InMemoryFillRepository,
    InMemoryLifecycleEventRepository,
    InMemoryOrderIntentRepository,
    InMemoryPositionRepository,
    InMemoryRuleEvaluationRepository,
    InMemoryTradeIdeaRepository,
    InMemoryTradePlanRepository,
    InMemoryTradeThesisRepository,
    InMemoryViolationRepository,
)
from trading_system.rules_engine.implementations.risk_defined_rule import RiskDefinedRule
from trading_system.services.create_order_intent_service import CreateOrderIntentService
from trading_system.services.fill_service import FillService
from trading_system.services.position_service import PositionService
from trading_system.services.rule_service import RuleService
from trading_system.services.trade_planning_service import TradePlanningService


def test_cannot_create_order_intent_from_missing_plan() -> None:
    """Order intent creation requires an existing trade plan."""
    workflow = _workflow()

    with pytest.raises(ValueError, match="Trade plan does not exist"):
        workflow.order_intents.create_order_intent(
            trade_plan_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            limit_price=Decimal("25.50"),
        )


def test_cannot_create_order_intent_from_unapproved_plan() -> None:
    """Order intent creation is gated by plan approval."""
    workflow = _workflow()
    idea = workflow.planning.create_trade_idea(
        instrument_id=uuid4(),
        playbook_id=uuid4(),
        purpose="swing",
        direction="long",
        horizon="days_to_weeks",
    )
    thesis = workflow.planning.create_trade_thesis(
        trade_idea_id=idea.id,
        reasoning="Setup has a catalyst.",
    )
    plan = workflow.planning.create_trade_plan(
        trade_idea_id=idea.id,
        trade_thesis_id=thesis.id,
        entry_criteria="Breakout confirmation.",
        invalidation="Close below setup low.",
        risk_model="Defined stop.",
    )

    with pytest.raises(ValueError, match="must be approved"):
        workflow.order_intents.create_order_intent(
            trade_plan_id=plan.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            limit_price=Decimal("25.50"),
        )


def test_cannot_create_order_intent_without_rule_evaluations() -> None:
    """Order intent creation requires persisted rule evaluation artifacts."""
    workflow = _workflow()
    plan = workflow.create_approved_plan()

    with pytest.raises(ValueError, match="persisted passing rule evaluations"):
        workflow.order_intents.create_order_intent(
            trade_plan_id=plan.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            limit_price=Decimal("25.50"),
        )


def test_cannot_create_order_intent_when_any_evaluation_failed() -> None:
    """Order intent creation is rejected if any persisted evaluation failed."""
    workflow = _workflow()
    plan = workflow.create_approved_plan()
    workflow.evaluations.add(
        RuleEvaluation(
            rule_id=uuid4(),
            entity_type="TradePlan",
            entity_id=plan.id,
            passed=True,
        )
    )
    workflow.evaluations.add(
        RuleEvaluation(
            rule_id=uuid4(),
            entity_type="TradePlan",
            entity_id=plan.id,
            passed=False,
            details="Risk missing.",
        )
    )

    with pytest.raises(ValueError, match="failed rule evaluations"):
        workflow.order_intents.create_order_intent(
            trade_plan_id=plan.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            limit_price=Decimal("25.50"),
        )


def test_can_create_order_intent_from_approved_plan_with_passing_evaluations() -> None:
    """Order intent creation persists a narrow execution intent and event."""
    workflow = _workflow()
    plan = workflow.create_approved_plan()
    workflow.evaluate_rules(plan.id)

    order_intent = workflow.order_intents.create_order_intent(
        trade_plan_id=plan.id,
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("100"),
        limit_price=Decimal("25.50"),
        notes="First entry.",
    )

    assert workflow.order_intent_repository.get(order_intent.id) == order_intent
    assert order_intent.status == OrderIntentStatus.CREATED
    events = workflow.lifecycle_events.list_by_entity("OrderIntent", order_intent.id)
    assert len(events) == 1
    assert events[0].event_type == "ORDER_INTENT_CREATED"
    assert events[0].details["trade_plan_id"] == str(plan.id)


def test_fill_service_accepts_valid_linked_order_intent() -> None:
    """Manual fills can link to an order intent on the same trade plan."""
    workflow = _workflow()
    plan = workflow.create_approved_plan()
    workflow.evaluate_rules(plan.id)
    position = workflow.positions.open_position_from_plan(plan.id)
    order_intent = workflow.order_intents.create_order_intent(
        trade_plan_id=plan.id,
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("100"),
        limit_price=Decimal("25.50"),
    )

    fill = workflow.fills.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25.50"),
        order_intent_id=order_intent.id,
    )

    assert fill.order_intent_id == order_intent.id


def test_fill_service_rejects_mismatched_order_intent_plan() -> None:
    """Manual fills cannot link an order intent from a different plan."""
    workflow = _workflow()
    first_plan = workflow.create_approved_plan()
    second_plan = workflow.create_approved_plan()
    workflow.evaluate_rules(first_plan.id)
    workflow.evaluate_rules(second_plan.id)
    first_position = workflow.positions.open_position_from_plan(first_plan.id)
    first_intent = workflow.order_intents.create_order_intent(
        trade_plan_id=first_plan.id,
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("100"),
        limit_price=Decimal("25.50"),
    )
    second_intent = workflow.order_intents.create_order_intent(
        trade_plan_id=second_plan.id,
        symbol="MSFT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("100"),
        limit_price=Decimal("25.50"),
    )

    with pytest.raises(ValueError, match="same trade plan"):
        workflow.fills.record_manual_fill(
            position_id=first_position.id,
            side="buy",
            quantity=Decimal("100"),
            price=Decimal("25.50"),
            order_intent_id=second_intent.id,
        )

    valid_fill = workflow.fills.record_manual_fill(
        position_id=first_position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25.50"),
        order_intent_id=first_intent.id,
    )
    assert valid_fill.order_intent_id == first_intent.id


class _Workflow:
    def __init__(self) -> None:
        self.idea_repository = InMemoryTradeIdeaRepository()
        self.thesis_repository = InMemoryTradeThesisRepository()
        self.plan_repository = InMemoryTradePlanRepository()
        self.position_repository = InMemoryPositionRepository()
        self.fill_repository = InMemoryFillRepository()
        self.order_intent_repository = InMemoryOrderIntentRepository()
        self.lifecycle_events = InMemoryLifecycleEventRepository()
        self.evaluations = InMemoryRuleEvaluationRepository()
        self.violations = InMemoryViolationRepository()
        self.planning = TradePlanningService(
            self.idea_repository,
            self.thesis_repository,
            self.plan_repository,
        )
        self.positions = PositionService(
            plan_repository=self.plan_repository,
            idea_repository=self.idea_repository,
            position_repository=self.position_repository,
            lifecycle_event_repository=self.lifecycle_events,
        )
        self.order_intents = CreateOrderIntentService(
            plan_repository=self.plan_repository,
            order_intent_repository=self.order_intent_repository,
            evaluation_repository=self.evaluations,
            lifecycle_event_repository=self.lifecycle_events,
        )
        self.fills = FillService(
            position_repository=self.position_repository,
            fill_repository=self.fill_repository,
            lifecycle_event_repository=self.lifecycle_events,
            order_intent_repository=self.order_intent_repository,
        )

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
        return self.planning.approve_trade_plan(plan.id)

    def evaluate_rules(self, trade_plan_id) -> None:
        rule = Rule(
            code="risk_defined",
            name="Risk defined",
            description="Trade plans must define risk before execution.",
        )
        RuleService(
            plan_repository=self.plan_repository,
            evaluation_repository=self.evaluations,
            violation_repository=self.violations,
            rules=[(rule, RiskDefinedRule(rule))],
        ).evaluate_trade_plan_rules(trade_plan_id)


def _workflow() -> _Workflow:
    return _Workflow()
