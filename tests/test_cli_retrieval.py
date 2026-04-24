"""CLI tests for read-only persisted position retrieval."""

from decimal import Decimal
from uuid import uuid4

from typer.testing import CliRunner

from trading_system.app.cli import app
from trading_system.domain.rules.rule import Rule
from trading_system.domain.trading.order_intent import OrderSide, OrderType
from trading_system.infrastructure.json.repositories import build_json_repositories
from trading_system.rules_engine.implementations.risk_defined_rule import RiskDefinedRule
from trading_system.services.create_order_intent_service import CreateOrderIntentService
from trading_system.services.fill_service import FillService
from trading_system.services.position_service import PositionService
from trading_system.services.review_service import ReviewService
from trading_system.services.rule_service import RuleService
from trading_system.services.trade_planning_service import TradePlanningService


runner = CliRunner()


def test_list_positions_reads_persisted_store(tmp_path) -> None:
    """The list command shows persisted positions."""
    store_path = tmp_path / "store.json"
    position_id = _seed_closed_position(store_path)

    result = runner.invoke(
        app,
        ["list-positions"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert str(position_id) in result.output
    assert "closed" in result.output
    assert "POSITION_ID | STATE | PURPOSE" in result.output
    assert "REALIZED_PNL" in result.output
    assert "150.00" in result.output


def test_list_positions_can_filter_closed_state(tmp_path) -> None:
    """The list command filters by lifecycle state."""
    store_path = tmp_path / "store.json"
    closed_position_id = _seed_closed_position(store_path)
    repositories = build_json_repositories(store_path)
    open_position_id = _open_position(repositories)

    result = runner.invoke(
        app,
        ["list-positions", "--state", "closed"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert str(closed_position_id) in result.output
    assert str(open_position_id) not in result.output


def test_show_position_includes_fills_and_review(tmp_path) -> None:
    """The show command includes linked records."""
    store_path = tmp_path / "store.json"
    position_id = _seed_closed_position(store_path)

    result = runner.invoke(
        app,
        ["show-position", str(position_id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert f"Position {position_id}" in result.output
    assert "Trade plan" in result.output
    assert "Trade idea" in result.output
    assert "Order intents" in result.output
    assert "limit | 100 | AAPL | status=created" in result.output
    assert "Fills" in result.output
    assert "buy | 100 @ 25.50" in result.output
    assert "sell | 100 @ 27" in result.output
    assert "realized_pnl: 150.00" in result.output
    assert "Review" in result.output
    assert "summary: Followed the plan." in result.output


def test_show_position_timeline_outputs_lifecycle_events(tmp_path) -> None:
    """The timeline command shows lifecycle events in order."""
    store_path = tmp_path / "store.json"
    position_id = _seed_closed_position(store_path)

    result = runner.invoke(
        app,
        ["show-position-timeline", str(position_id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert "OCCURRED_AT | EVENT_TYPE | ENTITY_TYPE | NOTE" in result.output
    assert "POSITION_OPENED" in result.output
    assert result.output.index("POSITION_OPENED") < result.output.index(
        "FILL_RECORDED"
    )
    assert result.output.index("FILL_RECORDED") < result.output.index(
        "POSITION_CLOSED"
    )


def test_show_position_rejects_invalid_uuid(tmp_path) -> None:
    """The show command reports invalid UUID arguments clearly."""
    store_path = tmp_path / "store.json"

    result = runner.invoke(
        app,
        ["show-position", "not-a-uuid"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "must be a valid UUID" in result.output


def test_show_position_rejects_missing_position(tmp_path) -> None:
    """The show command reports missing positions clearly."""
    store_path = tmp_path / "store.json"

    result = runner.invoke(
        app,
        ["show-position", str(uuid4())],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "Position does not exist" in result.output


def test_list_trade_reviews_reads_persisted_store(tmp_path) -> None:
    """The review list command shows persisted reviews with trade context."""
    store_path = tmp_path / "store.json"
    position_id = _seed_closed_position(store_path)
    review_id = build_json_repositories(store_path).reviews.get_by_position_id(position_id).id

    result = runner.invoke(
        app,
        ["list-trade-reviews"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert "TRADE_REVIEW_ID | POSITION_ID | TRADE_PLAN_ID" in result.output
    assert str(review_id) in result.output
    assert str(position_id) in result.output
    assert "swing" in result.output
    assert "long" in result.output
    assert "Followed the plan." in result.output


def test_show_trade_review_includes_linked_trade_context(tmp_path) -> None:
    """The review detail command shows structured review and trade context."""
    store_path = tmp_path / "store.json"
    position_id = _seed_closed_position(store_path)
    review_id = build_json_repositories(store_path).reviews.get_by_position_id(position_id).id

    result = runner.invoke(
        app,
        ["show-trade-review", str(review_id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert f"Trade review {review_id}" in result.output
    assert f"position_id: {position_id}" in result.output
    assert "summary: Followed the plan." in result.output
    assert "what_went_well: Entry was clear." in result.output
    assert "what_went_poorly: Exit was late." in result.output
    assert "Position" in result.output
    assert "state: closed" in result.output
    assert "realized_pnl: 150.00" in result.output
    assert "Trade idea" in result.output
    assert "purpose: swing" in result.output
    assert "direction: long" in result.output


def test_list_trade_reviews_empty_state(tmp_path) -> None:
    """The review list command reports a clear empty state."""
    store_path = tmp_path / "store.json"

    result = runner.invoke(
        app,
        ["list-trade-reviews"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert "No trade reviews found." in result.output


def test_show_trade_review_rejects_invalid_uuid(tmp_path) -> None:
    """The review detail command reports invalid UUID arguments clearly."""
    store_path = tmp_path / "store.json"

    result = runner.invoke(
        app,
        ["show-trade-review", "not-a-uuid"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "must be a valid UUID" in result.output


def _seed_closed_position(store_path) -> object:
    repositories = build_json_repositories(store_path)
    position_id = _open_position(repositories)
    fill_service = FillService(
        position_repository=repositories.positions,
        fill_repository=repositories.fills,
        lifecycle_event_repository=repositories.lifecycle_events,
        order_intent_repository=repositories.order_intents,
    )
    trade_plan_id = repositories.positions.get(position_id).trade_plan_id
    order_intent = CreateOrderIntentService(
        plan_repository=repositories.plans,
        order_intent_repository=repositories.order_intents,
        evaluation_repository=repositories.evaluations,
        lifecycle_event_repository=repositories.lifecycle_events,
    ).create_order_intent(
        trade_plan_id=trade_plan_id,
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("100"),
        limit_price=Decimal("25.50"),
    )
    fill_service.record_manual_fill(
        position_id=position_id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25.50"),
        order_intent_id=order_intent.id,
    )
    fill_service.record_manual_fill(
        position_id=position_id,
        side="sell",
        quantity=Decimal("100"),
        price=Decimal("27"),
        order_intent_id=order_intent.id,
    )
    review_service = ReviewService(
        position_repository=repositories.positions,
        review_repository=repositories.reviews,
        lifecycle_event_repository=repositories.lifecycle_events,
    )
    review_service.create_trade_review(
        position_id=position_id,
        summary="Followed the plan.",
        what_went_well="Entry was clear.",
        what_went_poorly="Exit was late.",
    )
    return position_id


def _open_position(repositories) -> object:
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
    rule = Rule(
        code="risk_defined",
        name="Risk defined",
        description="Trade plans must define risk before execution.",
    )
    RuleService(
        plan_repository=repositories.plans,
        evaluation_repository=repositories.evaluations,
        violation_repository=repositories.violations,
        rules=[(rule, RiskDefinedRule(rule))],
    ).evaluate_trade_plan_rules(approved.id)
    position_service = PositionService(
        plan_repository=repositories.plans,
        idea_repository=repositories.ideas,
        position_repository=repositories.positions,
        lifecycle_event_repository=repositories.lifecycle_events,
    )
    return position_service.open_position_from_plan(approved.id).id
