"""Tests for local JSON-backed durable persistence."""

from decimal import Decimal
import json
from uuid import uuid4

import pytest

from trading_system.domain.rules.rule import Rule
from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.order_intent import (
    OrderIntent,
    OrderIntentStatus,
    OrderSide,
    OrderType,
)
from trading_system.infrastructure.json.repositories import (
    JsonPersistenceError,
    build_json_repositories,
)
from trading_system.rules_engine.implementations.risk_defined_rule import RiskDefinedRule
from trading_system.services.fill_service import FillService
from trading_system.services.position_service import PositionService
from trading_system.services.review_service import ReviewService
from trading_system.services.rule_service import RuleService
from trading_system.services.trade_planning_service import TradePlanningService


def test_trade_plan_update_survives_repository_reload(tmp_path) -> None:
    """Plan approval state persists after recreating JSON repositories."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
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
        supporting_evidence=["volume expansion"],
    )
    plan = planning.create_trade_plan(
        trade_idea_id=idea.id,
        trade_thesis_id=thesis.id,
        entry_criteria="Breakout confirmation.",
        invalidation="Close below setup low.",
        targets=["first target"],
        risk_model="Defined stop and max loss.",
    )

    approved = planning.approve_trade_plan(plan.id)
    reloaded = build_json_repositories(store_path)

    assert reloaded.ideas.get(idea.id) == idea
    assert reloaded.theses.get(thesis.id) == thesis
    assert reloaded.plans.get(plan.id) == approved


def test_position_fill_review_and_lifecycle_survive_repository_reload(tmp_path) -> None:
    """Position state, fills, review, and lifecycle details persist."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
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
    approved = planning.approve_trade_plan(plan.id)
    position_service = PositionService(
        plan_repository=repositories.plans,
        idea_repository=repositories.ideas,
        position_repository=repositories.positions,
        lifecycle_event_repository=repositories.lifecycle_events,
    )
    position = position_service.open_position_from_plan(approved.id)
    fill_service = FillService(
        position_repository=repositories.positions,
        fill_repository=repositories.fills,
        lifecycle_event_repository=repositories.lifecycle_events,
        order_intent_repository=repositories.order_intents,
    )
    entry_fill = fill_service.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25.50"),
        notes="Manual entry.",
    )
    closing_fill = fill_service.record_manual_fill(
        position_id=position.id,
        side="sell",
        quantity=Decimal("100"),
        price=Decimal("27"),
        notes="Manual exit.",
    )
    review_service = ReviewService(
        position_repository=repositories.positions,
        review_repository=repositories.reviews,
        lifecycle_event_repository=repositories.lifecycle_events,
    )
    review = review_service.create_trade_review(
        position_id=position.id,
        summary="Followed the plan.",
        what_went_well="Entry and risk were clear.",
        what_went_poorly="Exit could be cleaner.",
        lessons_learned=["Keep records tied to the plan."],
        follow_up_actions=["Review exit checklist."],
        tags=["missed-exit"],
        rating=4,
        process_score=5,
        setup_quality=4,
        execution_quality=3,
        exit_quality=2,
    )

    reloaded = build_json_repositories(store_path)
    persisted_position = reloaded.positions.get(position.id)

    assert persisted_position is not None
    assert persisted_position.lifecycle_state == "closed"
    assert persisted_position.current_quantity == Decimal("0")
    assert persisted_position.closed_at == closing_fill.filled_at
    assert persisted_position.closing_fill_id == closing_fill.id
    assert reloaded.fills.get(entry_fill.id) == entry_fill
    assert reloaded.fills.get(closing_fill.id) == closing_fill
    assert reloaded.reviews.get(review.id) == review
    assert reloaded.reviews.get_by_position_id(position.id) == review

    raw_events = reloaded.lifecycle_events._store.read()["lifecycle_events"]
    close_events = [
        event
        for event in raw_events.values()
        if event["event_type"] == "POSITION_CLOSED"
    ]
    assert len(close_events) == 1
    assert close_events[0]["details"]["closing_fill_id"] == str(closing_fill.id)
    assert close_events[0]["details"]["current_quantity"] == "0"


def test_full_durable_workflow_persists_rule_artifacts(tmp_path) -> None:
    """The full Milestone 1 workflow persists core objects and rule artifacts."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
    idea = planning.create_trade_idea(
        instrument_id=uuid4(),
        playbook_id=uuid4(),
        purpose="swing",
        direction="long",
        horizon="days_to_weeks",
    )
    thesis = planning.create_trade_thesis(
        trade_idea_id=idea.id,
        reasoning="Example discretionary setup.",
    )
    plan = planning.create_trade_plan(
        trade_idea_id=idea.id,
        trade_thesis_id=thesis.id,
        entry_criteria="Breakout confirmation.",
        invalidation="Close below setup low.",
        risk_model="Defined stop and max loss.",
    )
    approved = planning.approve_trade_plan(plan.id)
    rule = Rule(
        code="risk_defined",
        name="Risk defined",
        description="Trade plans must define risk before execution.",
    )
    rule_service = RuleService(
        plan_repository=repositories.plans,
        evaluation_repository=repositories.evaluations,
        violation_repository=repositories.violations,
        rules=[(rule, RiskDefinedRule(rule))],
    )
    evaluations = rule_service.evaluate_trade_plan_rules(approved.id)
    position_service = PositionService(
        plan_repository=repositories.plans,
        idea_repository=repositories.ideas,
        position_repository=repositories.positions,
        lifecycle_event_repository=repositories.lifecycle_events,
    )
    position = position_service.open_position_from_plan(approved.id)
    fill_service = FillService(
        position_repository=repositories.positions,
        fill_repository=repositories.fills,
        lifecycle_event_repository=repositories.lifecycle_events,
        order_intent_repository=repositories.order_intents,
    )
    fill_service.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25.50"),
    )
    fill_service.record_manual_fill(
        position_id=position.id,
        side="sell",
        quantity=Decimal("100"),
        price=Decimal("27"),
    )
    review_service = ReviewService(
        position_repository=repositories.positions,
        review_repository=repositories.reviews,
        lifecycle_event_repository=repositories.lifecycle_events,
    )
    review = review_service.create_trade_review(
        position_id=position.id,
        summary="Demo review.",
        what_went_well="Followed the plan.",
        what_went_poorly="Placeholder review.",
    )

    reloaded = build_json_repositories(store_path)
    raw = reloaded.lifecycle_events._store.read()

    assert reloaded.plans.get(plan.id).approval_state == "approved"
    assert reloaded.positions.get(position.id).lifecycle_state == "closed"
    assert reloaded.reviews.get_by_position_id(position.id) == review
    assert reloaded.evaluations.get(evaluations[0].id) == evaluations[0]
    assert len(raw["fills"]) == 2
    assert len(raw["lifecycle_events"]) == 5
    assert raw["violations"] == {}


def test_invalid_json_store_raises_clear_error(tmp_path) -> None:
    """Invalid JSON is reported instead of being silently replaced."""
    store_path = tmp_path / "store.json"
    store_path.write_text("{not valid json", encoding="utf-8")
    repositories = build_json_repositories(store_path)

    with pytest.raises(JsonPersistenceError, match="invalid"):
        repositories.ideas.get(uuid4())


def test_fill_can_round_trip_independently(tmp_path) -> None:
    """Fill repository preserves decimal and datetime fields."""
    store_path = tmp_path / "store.json"
    fill = Fill(
        position_id=uuid4(),
        side="buy",
        quantity=Decimal("12.5"),
        price=Decimal("101.25"),
        notes="Partial fill.",
    )
    build_json_repositories(store_path).fills.add(fill)

    assert build_json_repositories(store_path).fills.get(fill.id) == fill


def test_order_intent_can_round_trip_independently(tmp_path) -> None:
    """Order intent repository preserves enum and price fields."""
    store_path = tmp_path / "store.json"
    order_intent = OrderIntent(
        trade_plan_id=uuid4(),
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("12.5"),
        limit_price=Decimal("101.25"),
        stop_price=Decimal("99.50"),
        status=OrderIntentStatus.CREATED,
        notes="Partial entry.",
    )
    build_json_repositories(store_path).order_intents.add(order_intent)

    assert build_json_repositories(store_path).order_intents.get(order_intent.id) == order_intent


def test_order_intent_canceled_status_can_round_trip_independently(tmp_path) -> None:
    """Order intent repository preserves the canceled status enum value."""
    store_path = tmp_path / "store.json"
    order_intent = OrderIntent(
        trade_plan_id=uuid4(),
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("12.5"),
        status=OrderIntentStatus.CANCELED,
    )
    build_json_repositories(store_path).order_intents.add(order_intent)

    assert build_json_repositories(store_path).order_intents.get(order_intent.id) == order_intent


def test_order_intent_update_survives_repository_reload(tmp_path) -> None:
    """Order intent updates persist after recreating JSON repositories."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    order_intent = OrderIntent(
        trade_plan_id=uuid4(),
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("12.5"),
        status=OrderIntentStatus.CREATED,
    )
    repositories.order_intents.add(order_intent)
    updated_order_intent = OrderIntent(
        id=order_intent.id,
        trade_plan_id=order_intent.trade_plan_id,
        symbol=order_intent.symbol,
        side=order_intent.side,
        order_type=order_intent.order_type,
        quantity=order_intent.quantity,
        limit_price=order_intent.limit_price,
        stop_price=order_intent.stop_price,
        status=OrderIntentStatus.CANCELED,
        created_at=order_intent.created_at,
        notes=order_intent.notes,
    )

    repositories.order_intents.update(updated_order_intent)

    assert build_json_repositories(store_path).order_intents.get(order_intent.id) == updated_order_intent

def test_fill_with_order_intent_id_can_round_trip(tmp_path) -> None:
    """Fill repository preserves optional order-intent linkage."""
    store_path = tmp_path / "store.json"
    fill = Fill(
        position_id=uuid4(),
        side="buy",
        quantity=Decimal("12.5"),
        price=Decimal("101.25"),
        order_intent_id=uuid4(),
        notes="Linked fill.",
    )
    build_json_repositories(store_path).fills.add(fill)

    assert build_json_repositories(store_path).fills.get(fill.id) == fill


def test_json_read_methods_survive_repository_reload(tmp_path) -> None:
    """Read-side repository methods return persisted matching records."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
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
    approved = planning.approve_trade_plan(plan.id)
    position_service = PositionService(
        plan_repository=repositories.plans,
        idea_repository=repositories.ideas,
        position_repository=repositories.positions,
        lifecycle_event_repository=repositories.lifecycle_events,
    )
    position = position_service.open_position_from_plan(approved.id)
    other_position = PositionService(
        plan_repository=repositories.plans,
        idea_repository=repositories.ideas,
        position_repository=repositories.positions,
        lifecycle_event_repository=repositories.lifecycle_events,
    ).open_position_from_plan(approved.id)
    fill_service = FillService(
        position_repository=repositories.positions,
        fill_repository=repositories.fills,
        lifecycle_event_repository=repositories.lifecycle_events,
        order_intent_repository=repositories.order_intents,
    )
    fill = fill_service.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25.50"),
    )
    fill_service.record_manual_fill(
        position_id=other_position.id,
        side="buy",
        quantity=Decimal("10"),
        price=Decimal("25.50"),
    )

    reloaded = build_json_repositories(store_path)

    assert {item.id for item in reloaded.positions.list_all()} == {
        position.id,
        other_position.id,
    }
    assert reloaded.fills.list_by_position_id(position.id) == [fill]
    events = reloaded.lifecycle_events.list_by_entity("Position", position.id)
    assert [event.event_type for event in events] == [
        "POSITION_OPENED",
        "FILL_RECORDED",
    ]
    assert reloaded.evaluations.list_by_entity("TradePlan", approved.id) == []


def test_trade_review_repository_list_all_survives_reload(tmp_path) -> None:
    """Review repository list methods return persisted reviews after reload."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
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
    approved = planning.approve_trade_plan(plan.id)
    position = PositionService(
        plan_repository=repositories.plans,
        idea_repository=repositories.ideas,
        position_repository=repositories.positions,
        lifecycle_event_repository=repositories.lifecycle_events,
    ).open_position_from_plan(approved.id)
    fill_service = FillService(
        position_repository=repositories.positions,
        fill_repository=repositories.fills,
        lifecycle_event_repository=repositories.lifecycle_events,
        order_intent_repository=repositories.order_intents,
    )
    fill_service.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25.50"),
    )
    fill_service.record_manual_fill(
        position_id=position.id,
        side="sell",
        quantity=Decimal("100"),
        price=Decimal("27"),
    )
    review = ReviewService(
        position_repository=repositories.positions,
        review_repository=repositories.reviews,
        lifecycle_event_repository=repositories.lifecycle_events,
    ).create_trade_review(
        position_id=position.id,
        summary="Reloadable review.",
        what_went_well="Entry was disciplined.",
        what_went_poorly="Exit timing slipped.",
    )

    reloaded = build_json_repositories(store_path)

    assert reloaded.reviews.get(review.id) == review
    assert reloaded.reviews.list_all() == [review]


def test_trade_review_without_new_review_metadata_loads_defaults(tmp_path) -> None:
    """Older review records without tags or scores remain readable."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
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
    position = PositionService(
        plan_repository=repositories.plans,
        idea_repository=repositories.ideas,
        position_repository=repositories.positions,
        lifecycle_event_repository=repositories.lifecycle_events,
    ).open_position_from_plan(planning.approve_trade_plan(plan.id).id)
    fill_service = FillService(
        position_repository=repositories.positions,
        fill_repository=repositories.fills,
        lifecycle_event_repository=repositories.lifecycle_events,
        order_intent_repository=repositories.order_intents,
    )
    fill_service.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25.50"),
    )
    fill_service.record_manual_fill(
        position_id=position.id,
        side="sell",
        quantity=Decimal("100"),
        price=Decimal("27"),
    )
    review = ReviewService(
        position_repository=repositories.positions,
        review_repository=repositories.reviews,
        lifecycle_event_repository=repositories.lifecycle_events,
    ).create_trade_review(
        position_id=position.id,
        summary="Old review.",
        what_went_well="Entry was disciplined.",
        what_went_poorly="Exit timing slipped.",
    )
    raw = json.loads(store_path.read_text(encoding="utf-8"))
    del raw["trade_reviews"][str(review.id)]["tags"]
    raw["trade_reviews"][str(review.id)].pop("process_score", None)
    raw["trade_reviews"][str(review.id)].pop("setup_quality", None)
    raw["trade_reviews"][str(review.id)].pop("execution_quality", None)
    raw["trade_reviews"][str(review.id)].pop("exit_quality", None)
    store_path.write_text(json.dumps(raw), encoding="utf-8")

    persisted = build_json_repositories(store_path).reviews.get(review.id)
    assert persisted.tags == []
    assert persisted.process_score is None
    assert persisted.setup_quality is None
    assert persisted.execution_quality is None
    assert persisted.exit_quality is None


def test_trade_thesis_repository_list_all_survives_reload(tmp_path) -> None:
    """Thesis repository list methods return persisted theses after reload."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
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
        supporting_evidence=["volume expansion"],
    )

    reloaded = build_json_repositories(store_path)

    assert reloaded.theses.get(thesis.id) == thesis
    assert reloaded.theses.list_all() == [thesis]
