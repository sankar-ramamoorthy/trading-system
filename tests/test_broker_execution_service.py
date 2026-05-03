"""Tests for simulated paper broker execution workflows."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from trading_system.domain.rules.rule import Rule
from trading_system.domain.trading.broker_order import BrokerOrderStatus
from trading_system.domain.trading.order_intent import OrderSide, OrderType
from trading_system.infrastructure.broker import SimulatedPaperBrokerClient
from trading_system.infrastructure.memory.repositories import (
    InMemoryBrokerOrderRepository,
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
from trading_system.services.broker_execution_service import BrokerExecutionService
from trading_system.services.broker_query_service import BrokerQueryService
from trading_system.services.cancel_order_intent_service import CancelOrderIntentService
from trading_system.services.create_order_intent_service import CreateOrderIntentService
from trading_system.services.fill_service import FillService
from trading_system.services.position_service import PositionService
from trading_system.services.rule_service import RuleService
from trading_system.services.trade_planning_service import TradePlanningService


def test_cannot_submit_missing_or_canceled_order_intent() -> None:
    """Broker submission requires an existing active order intent."""
    workflow = _workflow()

    with pytest.raises(ValueError, match="Order intent does not exist"):
        workflow.broker_execution.submit_paper_order(uuid4(), uuid4())

    plan = workflow.create_approved_and_evaluated_plan()
    position = workflow.positions.open_position_from_plan(plan.id)
    order_intent = workflow.create_order_intent(plan.id)
    workflow.cancel_order_intents.cancel_order_intent(order_intent.id)

    with pytest.raises(ValueError, match="Canceled order intent"):
        workflow.broker_execution.submit_paper_order(order_intent.id, position.id)


def test_cannot_submit_against_missing_closed_or_mismatched_position() -> None:
    """Broker submission is anchored to an existing open matching position."""
    workflow = _workflow()
    first_plan = workflow.create_approved_and_evaluated_plan()
    second_plan = workflow.create_approved_and_evaluated_plan()
    first_position = workflow.positions.open_position_from_plan(first_plan.id)
    second_position = workflow.positions.open_position_from_plan(second_plan.id)
    order_intent = workflow.create_order_intent(first_plan.id)

    with pytest.raises(ValueError, match="Position does not exist"):
        workflow.broker_execution.submit_paper_order(order_intent.id, uuid4())

    with pytest.raises(ValueError, match="same trade plan"):
        workflow.broker_execution.submit_paper_order(order_intent.id, second_position.id)

    workflow.fills.record_manual_fill(
        position_id=first_position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25"),
    )
    exit_intent = workflow.create_order_intent(first_plan.id, side=OrderSide.SELL)
    broker_order = workflow.broker_execution.submit_paper_order(
        exit_intent.id,
        first_position.id,
    )
    workflow.broker_execution.sync_paper_order(
        broker_order.id,
        simulated_fill_price=Decimal("27"),
    )

    next_intent = workflow.create_order_intent(first_plan.id)
    with pytest.raises(ValueError, match="open local position"):
        workflow.broker_execution.submit_paper_order(next_intent.id, first_position.id)


def test_cannot_submit_duplicate_broker_order_for_one_order_intent() -> None:
    """Milestone 11 allows one broker order per order intent."""
    workflow = _workflow()
    plan = workflow.create_approved_and_evaluated_plan()
    position = workflow.positions.open_position_from_plan(plan.id)
    order_intent = workflow.create_order_intent(plan.id)

    workflow.broker_execution.submit_paper_order(order_intent.id, position.id)

    with pytest.raises(ValueError, match="already has a broker order"):
        workflow.broker_execution.submit_paper_order(order_intent.id, position.id)


def test_successful_submit_stores_broker_order_and_lifecycle_event() -> None:
    """Paper submission stores local broker metadata and an audit event."""
    workflow = _workflow()
    plan = workflow.create_approved_and_evaluated_plan()
    position = workflow.positions.open_position_from_plan(plan.id)
    order_intent = workflow.create_order_intent(plan.id)

    broker_order = workflow.broker_execution.submit_paper_order(
        order_intent.id,
        position.id,
    )

    assert workflow.broker_orders.get(broker_order.id) == broker_order
    assert broker_order.status == BrokerOrderStatus.SUBMITTED
    assert broker_order.provider == "simulated"
    assert broker_order.provider_order_id == f"sim-{order_intent.id}"
    events = workflow.lifecycle_events.list_by_entity("BrokerOrder", broker_order.id)
    assert [event.event_type for event in events] == ["BROKER_ORDER_SUBMITTED"]


def test_sync_records_broker_fill_and_updates_position_quantity() -> None:
    """A synced broker fill creates one linked local fill and updates position."""
    workflow = _workflow()
    plan = workflow.create_approved_and_evaluated_plan()
    position = workflow.positions.open_position_from_plan(plan.id)
    order_intent = workflow.create_order_intent(plan.id)
    broker_order = workflow.broker_execution.submit_paper_order(
        order_intent.id,
        position.id,
    )

    result = workflow.broker_execution.sync_paper_order(
        broker_order.id,
        simulated_fill_price=Decimal("25.50"),
    )

    persisted_position = workflow.position_repository.get(position.id)
    assert result.broker_order.status == BrokerOrderStatus.FILLED
    assert result.fill.order_intent_id == order_intent.id
    assert result.fill.broker_order_id == broker_order.id
    assert result.fill.source == "broker:simulated"
    assert persisted_position.current_quantity == Decimal("100")
    assert workflow.fills_repository.list_by_broker_order_id(broker_order.id) == [
        result.fill
    ]
    assert [
        event.event_type
        for event in workflow.lifecycle_events.list_by_entity("BrokerOrder", broker_order.id)
    ] == ["BROKER_ORDER_SUBMITTED", "BROKER_ORDER_FILLED"]


def test_repeated_sync_is_idempotent() -> None:
    """Repeated syncs return the existing fill without creating duplicates."""
    workflow = _workflow()
    plan = workflow.create_approved_and_evaluated_plan()
    position = workflow.positions.open_position_from_plan(plan.id)
    order_intent = workflow.create_order_intent(plan.id)
    broker_order = workflow.broker_execution.submit_paper_order(
        order_intent.id,
        position.id,
    )

    first = workflow.broker_execution.sync_paper_order(
        broker_order.id,
        simulated_fill_price=Decimal("25.50"),
    )
    second = workflow.broker_execution.sync_paper_order(
        broker_order.id,
        simulated_fill_price=Decimal("26.00"),
    )

    assert second.fill == first.fill
    assert workflow.fills_repository.list_by_broker_order_id(broker_order.id) == [
        first.fill
    ]
    assert workflow.position_repository.get(position.id).current_quantity == Decimal("100")


def test_broker_fill_can_close_position_through_existing_fill_logic() -> None:
    """Broker-imported reducing fills can close a local position."""
    workflow = _workflow()
    plan = workflow.create_approved_and_evaluated_plan()
    position = workflow.positions.open_position_from_plan(plan.id)
    workflow.fills.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25"),
    )
    exit_intent = workflow.create_order_intent(plan.id, side=OrderSide.SELL)
    broker_order = workflow.broker_execution.submit_paper_order(
        exit_intent.id,
        position.id,
    )

    result = workflow.broker_execution.sync_paper_order(
        broker_order.id,
        simulated_fill_price=Decimal("27"),
    )

    persisted_position = workflow.position_repository.get(position.id)
    assert result.position_state == "closed"
    assert result.open_quantity == Decimal("0")
    assert persisted_position.lifecycle_state == "closed"
    assert persisted_position.closing_fill_id == result.fill.id


def test_query_lists_broker_orders_with_filters() -> None:
    """Broker query service lists local broker orders with exact filters."""
    workflow = _workflow()
    first_plan = workflow.create_approved_and_evaluated_plan()
    second_plan = workflow.create_approved_and_evaluated_plan()
    first_position = workflow.positions.open_position_from_plan(first_plan.id)
    second_position = workflow.positions.open_position_from_plan(second_plan.id)
    first_intent = workflow.create_order_intent(first_plan.id)
    second_intent = workflow.create_order_intent(second_plan.id)
    first_order = workflow.broker_execution.submit_paper_order(
        first_intent.id,
        first_position.id,
    )
    second_order = workflow.broker_execution.submit_paper_order(
        second_intent.id,
        second_position.id,
    )
    workflow.broker_execution.cancel_paper_order(second_order.id)

    assert workflow.broker_query.list_broker_orders(provider="simulated") == [
        first_order,
        workflow.broker_orders.get(second_order.id),
    ]
    assert workflow.broker_query.list_broker_orders(
        status=BrokerOrderStatus.SUBMITTED
    ) == [first_order]
    assert workflow.broker_query.list_broker_orders(
        position_id=second_position.id
    ) == [workflow.broker_orders.get(second_order.id)]
    assert workflow.broker_query.list_broker_orders(
        order_intent_id=first_intent.id
    ) == [first_order]


def test_cancel_submitted_broker_order_emits_event_and_blocks_sync() -> None:
    """Canceling a submitted simulated order creates a terminal broker order."""
    workflow = _workflow()
    plan = workflow.create_approved_and_evaluated_plan()
    position = workflow.positions.open_position_from_plan(plan.id)
    order_intent = workflow.create_order_intent(plan.id)
    broker_order = workflow.broker_execution.submit_paper_order(
        order_intent.id,
        position.id,
    )

    canceled = workflow.broker_execution.cancel_paper_order(broker_order.id)

    assert canceled.status == BrokerOrderStatus.CANCELED
    assert workflow.broker_orders.get(broker_order.id) == canceled
    events = workflow.lifecycle_events.list_by_entity("BrokerOrder", broker_order.id)
    assert [event.event_type for event in events] == [
        "BROKER_ORDER_SUBMITTED",
        "BROKER_ORDER_CANCELED",
    ]
    with pytest.raises(ValueError, match="cannot be synced"):
        workflow.broker_execution.sync_paper_order(
            broker_order.id,
            simulated_fill_price=Decimal("25.50"),
        )
    assert workflow.fills_repository.list_by_broker_order_id(broker_order.id) == []


def test_reject_submitted_broker_order_records_reason_and_blocks_sync() -> None:
    """Rejecting a submitted simulated order records the rejection reason."""
    workflow = _workflow()
    plan = workflow.create_approved_and_evaluated_plan()
    position = workflow.positions.open_position_from_plan(plan.id)
    order_intent = workflow.create_order_intent(plan.id)
    broker_order = workflow.broker_execution.submit_paper_order(
        order_intent.id,
        position.id,
    )

    rejected = workflow.broker_execution.reject_paper_order(
        broker_order.id,
        reason="Simulated risk rejection.",
    )

    assert rejected.status == BrokerOrderStatus.REJECTED
    events = workflow.lifecycle_events.list_by_entity("BrokerOrder", broker_order.id)
    assert [event.event_type for event in events] == [
        "BROKER_ORDER_SUBMITTED",
        "BROKER_ORDER_REJECTED",
    ]
    assert events[1].details["reason"] == "Simulated risk rejection."
    with pytest.raises(ValueError, match="cannot be synced"):
        workflow.broker_execution.sync_paper_order(
            broker_order.id,
            simulated_fill_price=Decimal("25.50"),
        )


def test_cannot_cancel_or_reject_filled_broker_order() -> None:
    """Filled broker orders cannot move to another terminal status."""
    workflow = _workflow()
    plan = workflow.create_approved_and_evaluated_plan()
    position = workflow.positions.open_position_from_plan(plan.id)
    order_intent = workflow.create_order_intent(plan.id)
    broker_order = workflow.broker_execution.submit_paper_order(
        order_intent.id,
        position.id,
    )
    workflow.broker_execution.sync_paper_order(
        broker_order.id,
        simulated_fill_price=Decimal("25.50"),
    )

    with pytest.raises(ValueError, match="Only submitted broker orders"):
        workflow.broker_execution.cancel_paper_order(broker_order.id)
    with pytest.raises(ValueError, match="Only submitted broker orders"):
        workflow.broker_execution.reject_paper_order(
            broker_order.id,
            reason="Too late.",
        )


class _Workflow:
    def __init__(self) -> None:
        self.idea_repository = InMemoryTradeIdeaRepository()
        self.thesis_repository = InMemoryTradeThesisRepository()
        self.plan_repository = InMemoryTradePlanRepository()
        self.position_repository = InMemoryPositionRepository()
        self.fills_repository = InMemoryFillRepository()
        self.order_intent_repository = InMemoryOrderIntentRepository()
        self.broker_orders = InMemoryBrokerOrderRepository()
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
        self.cancel_order_intents = CancelOrderIntentService(
            order_intent_repository=self.order_intent_repository,
            lifecycle_event_repository=self.lifecycle_events,
        )
        self.fills = FillService(
            position_repository=self.position_repository,
            fill_repository=self.fills_repository,
            lifecycle_event_repository=self.lifecycle_events,
            order_intent_repository=self.order_intent_repository,
        )
        self.broker_execution = BrokerExecutionService(
            order_intent_repository=self.order_intent_repository,
            position_repository=self.position_repository,
            broker_order_repository=self.broker_orders,
            fill_repository=self.fills_repository,
            lifecycle_event_repository=self.lifecycle_events,
            broker_client=SimulatedPaperBrokerClient(),
        )
        self.broker_query = BrokerQueryService(
            broker_order_repository=self.broker_orders,
            order_intent_repository=self.order_intent_repository,
            position_repository=self.position_repository,
            fill_repository=self.fills_repository,
        )

    def create_approved_and_evaluated_plan(self):
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
        approved = self.planning.approve_trade_plan(plan.id)
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
        ).evaluate_trade_plan_rules(approved.id)
        return approved

    def create_order_intent(
        self,
        trade_plan_id: UUID,
        side: OrderSide = OrderSide.BUY,
    ):
        return self.order_intents.create_order_intent(
            trade_plan_id=trade_plan_id,
            symbol="AAPL",
            side=side,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            limit_price=Decimal("25.50"),
        )


def _workflow() -> _Workflow:
    return _Workflow()
