"""CLI tests for read-only persisted position retrieval."""

from decimal import Decimal
from uuid import uuid4

from typer.testing import CliRunner

from trading_system.app.cli import app
from trading_system.domain.rules.rule import Rule
from trading_system.domain.trading.order_intent import OrderSide, OrderType
from trading_system.infrastructure.json.repositories import build_json_repositories
from trading_system.rules_engine.implementations.risk_defined_rule import RiskDefinedRule
from trading_system.services.cancel_order_intent_service import CancelOrderIntentService
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
    lines = _lines(result.output)
    assert lines[0] == "POSITION_ID | STATE | PURPOSE | QTY | REALIZED_PNL | OPENED_AT | CLOSED_AT"
    columns = lines[1].split(" | ")
    assert columns[0] == str(position_id)
    assert columns[1] == "closed"
    assert columns[4] == "150.00"
    assert columns[5]
    assert columns[6]


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


def test_list_positions_can_filter_by_purpose_review_and_sort(tmp_path) -> None:
    """Position lists support purpose, review flags, and newest sorting."""
    store_path = tmp_path / "store.json"
    reviewed_position_id = _seed_closed_position(store_path, purpose="swing")
    repositories = build_json_repositories(store_path)
    open_position_id = _open_position(repositories, purpose="day_trade")

    reviewed = runner.invoke(
        app,
        ["list-positions", "--purpose", "swing", "--has-review"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    unreviewed = runner.invoke(
        app,
        ["list-positions", "--no-review", "--sort", "newest"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert reviewed.exit_code == 0
    assert str(reviewed_position_id) in reviewed.output
    assert str(open_position_id) not in reviewed.output
    assert unreviewed.exit_code == 0
    assert _lines(unreviewed.output)[1].split(" | ")[0] == str(open_position_id)


def test_list_positions_formats_optional_values_for_open_positions(tmp_path) -> None:
    """Open positions use N/A and blank cells consistently in list output."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    position_id = _open_position(repositories)

    result = runner.invoke(
        app,
        ["list-positions"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    row = next(line for line in _lines(result.output)[1:] if line.startswith(str(position_id)))
    columns = row.split(" | ")
    assert columns[1] == "open"
    assert columns[4] == "N/A"
    assert row.endswith(" |")


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
    assert _lines(result.output)[0] == f"Position {position_id}"
    _assert_in_order(
        result.output,
        f"Position {position_id}",
        "Trade plan",
        "Trade idea",
        "Order intents",
        "Fills",
        "Review",
    )
    assert "realized_pnl: 150.00" in result.output
    assert "order_intent_id:" in result.output
    assert "limit_price: 25.50" in result.output
    assert "fill_id:" in result.output
    assert "side: buy" in result.output
    assert "price: 25.50" in result.output
    assert "side: sell" in result.output
    assert "price: 27" in result.output
    assert "summary: Followed the plan." in result.output


def test_show_position_displays_canceled_order_intent_status(tmp_path) -> None:
    """Position detail surfaces canceled order intents through existing read views."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    position_id = _open_position(repositories)
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
    CancelOrderIntentService(
        order_intent_repository=repositories.order_intents,
        lifecycle_event_repository=repositories.lifecycle_events,
    ).cancel_order_intent(order_intent.id)

    result = runner.invoke(
        app,
        ["show-position", str(position_id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert "status: canceled" in result.output


def test_show_position_uses_explicit_optional_values_in_show_output(tmp_path) -> None:
    """Open positions use explicit optional formatting in show output."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    position_id = _open_position(repositories)

    result = runner.invoke(
        app,
        ["show-position", str(position_id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert f"Position {position_id}" in result.output
    assert "average_entry_price: N/A" in result.output
    assert "realized_pnl: N/A" in result.output
    assert "closed_at: N/A" in result.output
    assert "Review\nstatus: No review found." in result.output


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
    assert _lines(result.output)[0] == "OCCURRED_AT | EVENT_TYPE | ENTITY_TYPE | NOTE"
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


def test_list_trade_theses_reads_persisted_store(tmp_path) -> None:
    """The thesis list command shows linked idea context and plan count."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    _open_position(repositories)
    thesis = repositories.theses.list_all()[0]
    idea = repositories.ideas.get(thesis.trade_idea_id)

    result = runner.invoke(
        app,
        ["list-trade-theses"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    lines = _lines(result.output)
    assert lines[0] == (
        "TRADE_THESIS_ID | TRADE_IDEA_ID | PURPOSE | DIRECTION | PLAN_COUNT | "
        "TRADE_IDEA_CREATED_AT"
    )
    assert lines[1].split(" | ") == [
        str(thesis.id),
        str(idea.id),
        idea.purpose,
        idea.direction,
        "1",
        idea.created_at.isoformat(),
    ]


def test_list_trade_theses_can_filter_and_sort(tmp_path) -> None:
    """The thesis list command supports exact filters, has-plan, and newest sort."""
    store_path = tmp_path / "store.json"
    reviewed_position_id = _seed_closed_position(store_path, purpose="swing", direction="long")
    repositories = build_json_repositories(store_path)
    thesis_without_plan_id = _create_trade_idea_and_thesis(
        repositories,
        purpose="day_trade",
        direction="short",
    )
    listed = runner.invoke(
        app,
        ["list-trade-theses", "--purpose", "day_trade", "--direction", "short"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    has_plan = runner.invoke(
        app,
        ["list-trade-theses", "--has-plan", "--sort", "newest"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert reviewed_position_id is not None
    assert listed.exit_code == 0
    assert str(thesis_without_plan_id) in listed.output
    assert " | 0 | " in listed.output
    assert has_plan.exit_code == 0
    assert str(thesis_without_plan_id) not in has_plan.output
    assert " | 1 | " in _lines(has_plan.output)[1]


def test_show_trade_thesis_includes_linked_trade_idea_and_plans(tmp_path) -> None:
    """The thesis detail command uses the canonical section order."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    _open_position(repositories)
    thesis = repositories.theses.list_all()[0]
    plan = repositories.plans.list_all()[0]

    result = runner.invoke(
        app,
        ["show-trade-thesis", str(thesis.id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert _lines(result.output)[0] == f"Trade thesis {thesis.id}"
    _assert_in_order(
        result.output,
        f"Trade thesis {thesis.id}",
        "Trade idea",
        "Trade plans",
    )
    assert "reasoning: Setup has a clear catalyst." in result.output
    assert f"trade_plan_id: {plan.id}" in result.output
    assert "approval_state: approved" in result.output


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
    lines = _lines(result.output)
    assert lines[0] == (
        "TRADE_REVIEW_ID | POSITION_ID | TRADE_PLAN_ID | PURPOSE | DIRECTION | "
        "RATING | PROCESS_SCORE | SETUP_QUALITY | EXECUTION_QUALITY | "
        "EXIT_QUALITY | TAGS | SUMMARY | REVIEWED_AT"
    )
    columns = lines[1].split(" | ")
    assert columns[0] == str(review_id)
    assert columns[1] == str(position_id)
    assert columns[3] == "swing"
    assert columns[4] == "long"
    assert columns[5] == ""
    assert columns[6] == ""
    assert columns[7] == ""
    assert columns[8] == ""
    assert columns[9] == ""
    assert columns[10] == ""
    assert columns[11] == "Followed the plan."
    assert columns[12]


def test_list_trade_reviews_can_filter_and_sort(tmp_path) -> None:
    """The review list command supports exact filters and newest sorting."""
    store_path = tmp_path / "store.json"
    first_position_id = _seed_closed_position(
        store_path,
        purpose="swing",
        direction="long",
        rating=4,
        tags=["missed-exit", "risk-management"],
        process_score=5,
        setup_quality=4,
        execution_quality=3,
        exit_quality=2,
    )
    second_position_id = _seed_closed_position(
        store_path,
        purpose="day_trade",
        direction="short",
        rating=2,
        tags=["missed-exit"],
        process_score=3,
        setup_quality=2,
        execution_quality=2,
        exit_quality=1,
    )
    repositories = build_json_repositories(store_path)
    first_review_id = repositories.reviews.get_by_position_id(first_position_id).id
    second_review_id = repositories.reviews.get_by_position_id(second_position_id).id

    filtered = runner.invoke(
        app,
        [
            "list-trade-reviews",
            "--rating",
            "4",
            "--purpose",
            "swing",
            "--direction",
            "long",
            "--tag",
            "risk_management",
            "--process-score",
            "5",
            "--setup-quality",
            "4",
            "--execution-quality",
            "3",
            "--exit-quality",
            "2",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    newest = runner.invoke(
        app,
        ["list-trade-reviews", "--sort", "newest"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert filtered.exit_code == 0
    assert str(first_review_id) in filtered.output
    assert str(second_review_id) not in filtered.output
    assert newest.exit_code == 0
    assert _lines(newest.output)[1].split(" | ")[0] == str(second_review_id)


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
    assert _lines(result.output)[0] == f"Trade review {review_id}"
    _assert_in_order(
        result.output,
        f"Trade review {review_id}",
        "Position",
        "Trade plan",
        "Trade idea",
    )
    assert f"position_id: {position_id}" in result.output
    assert "rating: N/A" in result.output
    assert "process_score: N/A" in result.output
    assert "setup_quality: N/A" in result.output
    assert "execution_quality: N/A" in result.output
    assert "exit_quality: N/A" in result.output
    assert "tags: None" in result.output
    assert "summary: Followed the plan." in result.output
    assert "what_went_well: Entry was clear." in result.output
    assert "what_went_poorly: Exit was late." in result.output
    assert "state: closed" in result.output
    assert "realized_pnl: 150.00" in result.output
    assert "purpose: swing" in result.output
    assert "direction: long" in result.output


def test_list_trade_ideas_reads_persisted_store(tmp_path) -> None:
    """The idea list command uses the canonical output shape."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    _open_position(repositories)
    idea = repositories.ideas.list_all()[0]

    result = runner.invoke(
        app,
        ["list-trade-ideas"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    lines = _lines(result.output)
    assert lines[0] == "TRADE_IDEA_ID | STATUS | PURPOSE | DIRECTION | HORIZON | CREATED_AT"
    assert lines[1].split(" | ") == [
        str(idea.id),
        idea.status,
        idea.purpose,
        idea.direction,
        idea.horizon,
        idea.created_at.isoformat(),
    ]


def test_list_trade_ideas_can_filter_and_sort(tmp_path) -> None:
    """The idea list command supports exact filters and newest sorting."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    first_id = _open_position(repositories, purpose="swing", direction="long")
    second_id = _open_position(repositories, purpose="day_trade", direction="short")
    filtered = runner.invoke(
        app,
        [
            "list-trade-ideas",
            "--purpose",
            "day_trade",
            "--direction",
            "short",
            "--status",
            "draft",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    newest = runner.invoke(
        app,
        ["list-trade-ideas", "--sort", "newest"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert first_id is not None
    assert filtered.exit_code == 0
    assert "day_trade" in filtered.output
    assert "swing" not in filtered.output
    assert newest.exit_code == 0
    newest_idea = max(repositories.ideas.list_all(), key=lambda idea: idea.created_at)
    assert _lines(newest.output)[1].split(" | ")[0] == str(newest_idea.id)


def test_list_trade_plans_reads_persisted_store(tmp_path) -> None:
    """The plan list command uses the canonical output shape."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    _open_position(repositories)
    plan = repositories.plans.list_all()[0]

    result = runner.invoke(
        app,
        ["list-trade-plans"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    lines = _lines(result.output)
    assert lines[0] == (
        "TRADE_PLAN_ID | APPROVAL_STATE | TRADE_IDEA_ID | TRADE_THESIS_ID | CREATED_AT"
    )
    assert lines[1].split(" | ") == [
        str(plan.id),
        plan.approval_state,
        str(plan.trade_idea_id),
        str(plan.trade_thesis_id),
        plan.created_at.isoformat(),
    ]


def test_list_trade_plans_can_filter_and_sort(tmp_path) -> None:
    """The plan list command supports approval-state filtering and newest sorting."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    _open_position(repositories)
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
    idea = planning.create_trade_idea(
        instrument_id=uuid4(),
        playbook_id=uuid4(),
        purpose="swing",
        direction="short",
        horizon="days_to_weeks",
    )
    thesis = planning.create_trade_thesis(
        trade_idea_id=idea.id,
        reasoning="Second setup.",
    )
    draft_plan = planning.create_trade_plan(
        trade_idea_id=idea.id,
        trade_thesis_id=thesis.id,
        entry_criteria="Breakdown confirmation.",
        invalidation="Close back above setup high.",
        risk_model="Defined stop and max loss.",
    )

    filtered = runner.invoke(
        app,
        ["list-trade-plans", "--approval-state", "approved"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    newest = runner.invoke(
        app,
        ["list-trade-plans", "--sort", "newest"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert filtered.exit_code == 0
    assert str(draft_plan.id) not in filtered.output
    assert newest.exit_code == 0
    assert _lines(newest.output)[1].split(" | ")[0] == str(draft_plan.id)


def test_show_trade_plan_uses_canonical_section_order(tmp_path) -> None:
    """The plan detail command renders sections in the canonical order."""
    store_path = tmp_path / "store.json"
    position_id = _seed_closed_position(store_path)
    repositories = build_json_repositories(store_path)
    trade_plan_id = repositories.positions.get(position_id).trade_plan_id

    result = runner.invoke(
        app,
        ["show-trade-plan", str(trade_plan_id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert _lines(result.output)[0] == f"Trade plan {trade_plan_id}"
    _assert_in_order(
        result.output,
        f"Trade plan {trade_plan_id}",
        "Trade idea",
        "Trade thesis",
        "Rule evaluations",
        "Order intents",
        "Positions",
    )
    assert "approval_state: approved" in result.output
    assert "rule_evaluation_id:" in result.output
    assert "order_intent_id:" in result.output
    assert "position_id:" in result.output


def test_show_trade_plan_displays_canceled_order_intent_status(tmp_path) -> None:
    """Trade plan detail surfaces canceled order intents through the existing section."""
    store_path = tmp_path / "store.json"
    position_id = _seed_closed_position(store_path)
    repositories = build_json_repositories(store_path)
    trade_plan_id = repositories.positions.get(position_id).trade_plan_id
    order_intent = repositories.order_intents.list_by_trade_plan_id(trade_plan_id)[0]
    CancelOrderIntentService(
        order_intent_repository=repositories.order_intents,
        lifecycle_event_repository=repositories.lifecycle_events,
    ).cancel_order_intent(order_intent.id)

    result = runner.invoke(
        app,
        ["show-trade-plan", str(trade_plan_id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert "status: canceled" in result.output


def test_list_read_commands_use_consistent_empty_states(tmp_path) -> None:
    """Read-side list commands use stable empty-state wording."""
    store_path = tmp_path / "store.json"

    assert runner.invoke(
        app,
        ["list-trade-ideas"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    ).output == "No trade ideas found.\n"
    assert runner.invoke(
        app,
        ["list-trade-plans"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    ).output == "No trade plans found.\n"
    assert runner.invoke(
        app,
        ["list-trade-theses"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    ).output == "No trade theses found.\n"
    assert runner.invoke(
        app,
        ["list-trade-reviews"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    ).output == "No trade reviews found.\n"
    assert runner.invoke(
        app,
        ["list-positions"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    ).output == "No positions found.\n"


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


def test_show_trade_plan_and_thesis_reject_invalid_uuid(tmp_path) -> None:
    """Trade plan and thesis detail commands report invalid UUID arguments clearly."""
    store_path = tmp_path / "store.json"

    plan_result = runner.invoke(
        app,
        ["show-trade-plan", "not-a-uuid"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    thesis_result = runner.invoke(
        app,
        ["show-trade-thesis", "not-a-uuid"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert plan_result.exit_code != 0
    assert "must be a valid UUID" in plan_result.output
    assert thesis_result.exit_code != 0
    assert "must be a valid UUID" in thesis_result.output


def test_show_trade_plan_and_thesis_reject_missing_records(tmp_path) -> None:
    """Trade plan and thesis detail commands report missing records clearly."""
    store_path = tmp_path / "store.json"

    plan_result = runner.invoke(
        app,
        ["show-trade-plan", str(uuid4())],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    thesis_result = runner.invoke(
        app,
        ["show-trade-thesis", str(uuid4())],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert plan_result.exit_code != 0
    assert "Trade plan does not exist" in plan_result.output
    assert thesis_result.exit_code != 0
    assert "Trade thesis does not exist" in thesis_result.output


def _seed_closed_position(
    store_path,
    *,
    purpose: str = "swing",
    direction: str = "long",
    rating: int | None = None,
    tags: list[str] | None = None,
    process_score: int | None = None,
    setup_quality: int | None = None,
    execution_quality: int | None = None,
    exit_quality: int | None = None,
) -> object:
    repositories = build_json_repositories(store_path)
    position_id = _open_position(
        repositories,
        purpose=purpose,
        direction=direction,
    )
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
        rating=rating,
        tags=tags,
        process_score=process_score,
        setup_quality=setup_quality,
        execution_quality=execution_quality,
        exit_quality=exit_quality,
    )
    return position_id


def _open_position(
    repositories,
    *,
    purpose: str = "swing",
    direction: str = "long",
) -> object:
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
    idea = planning.create_trade_idea(
        instrument_id=uuid4(),
        playbook_id=uuid4(),
        purpose=purpose,
        direction=direction,
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


def _create_trade_idea_and_thesis(
    repositories,
    *,
    purpose: str,
    direction: str,
) -> object:
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
    idea = planning.create_trade_idea(
        instrument_id=uuid4(),
        playbook_id=uuid4(),
        purpose=purpose,
        direction=direction,
        horizon="days_to_weeks",
    )
    thesis = planning.create_trade_thesis(
        trade_idea_id=idea.id,
        reasoning="Unplanned thesis.",
    )
    return thesis.id


def _lines(output: str) -> list[str]:
    return output.rstrip().splitlines()


def _assert_in_order(output: str, *markers: str) -> None:
    indices = [output.index(marker) for marker in markers]
    assert indices == sorted(indices)
