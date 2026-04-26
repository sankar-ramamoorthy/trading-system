"""CLI tests for explicit write commands and upstream read commands."""

from uuid import uuid4

from typer.testing import CliRunner

from trading_system.app.cli import app


runner = CliRunner()


def test_cli_end_to_end_workflow_without_demo_command(tmp_path) -> None:
    """The explicit CLI commands can create, execute, and review a trade."""
    store_path = tmp_path / "store.json"
    instrument_id = str(uuid4())
    playbook_id = str(uuid4())

    create_idea = runner.invoke(
        app,
        [
            "create-trade-idea",
            "--instrument-id",
            instrument_id,
            "--playbook-id",
            playbook_id,
            "--purpose",
            "swing",
            "--direction",
            "long",
            "--horizon",
            "days_to_weeks",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert create_idea.exit_code == 0
    idea_id = _field(create_idea.output, "trade_idea_id")

    create_thesis = runner.invoke(
        app,
        [
            "create-trade-thesis",
            idea_id,
            "--reasoning",
            "Setup has a catalyst.",
            "--supporting-evidence",
            "Trend is intact.",
            "--risk",
            "Gap risk.",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert create_thesis.exit_code == 0
    thesis_id = _field(create_thesis.output, "trade_thesis_id")

    create_plan = runner.invoke(
        app,
        [
            "create-trade-plan",
            "--trade-idea-id",
            idea_id,
            "--trade-thesis-id",
            thesis_id,
            "--entry-criteria",
            "Breakout confirmation.",
            "--invalidation",
            "Close below setup low.",
            "--risk-model",
            "Defined stop and max loss.",
            "--target",
            "Prior highs.",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert create_plan.exit_code == 0
    plan_id = _field(create_plan.output, "trade_plan_id")

    approve_plan = runner.invoke(
        app,
        ["approve-trade-plan", plan_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert approve_plan.exit_code == 0
    assert "approval_state: approved" in approve_plan.output

    evaluate_plan = runner.invoke(
        app,
        ["evaluate-trade-plan-rules", plan_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert evaluate_plan.exit_code == 0
    assert "passed: 1" in evaluate_plan.output

    create_order_intent = runner.invoke(
        app,
        [
            "create-order-intent",
            "--trade-plan-id",
            plan_id,
            "--symbol",
            "AAPL",
            "--side",
            "buy",
            "--order-type",
            "limit",
            "--quantity",
            "100",
            "--limit-price",
            "25.50",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert create_order_intent.exit_code == 0
    order_intent_id = _field(create_order_intent.output, "order_intent_id")

    open_position = runner.invoke(
        app,
        ["open-position", plan_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert open_position.exit_code == 0
    position_id = _field(open_position.output, "position_id")

    record_entry_fill = runner.invoke(
        app,
        [
            "record-fill",
            "--position-id",
            position_id,
            "--side",
            "buy",
            "--quantity",
            "100",
            "--price",
            "25.50",
            "--order-intent-id",
            order_intent_id,
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert record_entry_fill.exit_code == 0
    assert f"order_intent_id: {order_intent_id}" in record_entry_fill.output
    assert "position_state: open" in record_entry_fill.output

    record_exit_fill = runner.invoke(
        app,
        [
            "record-fill",
            "--position-id",
            position_id,
            "--side",
            "sell",
            "--quantity",
            "100",
            "--price",
            "27.00",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert record_exit_fill.exit_code == 0
    assert "position_state: closed" in record_exit_fill.output

    create_review = runner.invoke(
        app,
        [
            "create-trade-review",
            "--position-id",
            position_id,
            "--summary",
            "Followed the plan.",
            "--what-went-well",
            "Entry was clean.",
            "--what-went-poorly",
            "Exit could have been faster.",
            "--lesson",
            "Keep size aligned with plan.",
            "--follow-up-action",
            "Review execution notes before entry.",
            "--tag",
            "Risk Management",
            "--tag",
            "risk_management",
            "--rating",
            "4",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert create_review.exit_code == 0
    assert "trade_review_id:" in create_review.output
    assert "rating: 4" in create_review.output
    assert "tags: risk-management" in create_review.output

    show_plan = runner.invoke(
        app,
        ["show-trade-plan", plan_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert show_plan.exit_code == 0
    assert _lines(show_plan.output)[0] == f"Trade plan {plan_id}"
    assert "approval_state: approved" in show_plan.output
    assert "Rule evaluations" in show_plan.output
    assert "Order intents" in show_plan.output
    assert "Positions" in show_plan.output
    assert "rule_evaluation_id:" in show_plan.output
    assert "order_intent_id:" in show_plan.output
    assert "position_id:" in show_plan.output

    list_ideas = runner.invoke(
        app,
        ["list-trade-ideas", "--purpose", "swing", "--direction", "long"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert list_ideas.exit_code == 0
    assert _lines(list_ideas.output)[0] == (
        "TRADE_IDEA_ID | STATUS | PURPOSE | DIRECTION | HORIZON | CREATED_AT"
    )
    assert idea_id in list_ideas.output

    list_plans = runner.invoke(
        app,
        ["list-trade-plans", "--approval-state", "approved"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert list_plans.exit_code == 0
    assert _lines(list_plans.output)[0] == (
        "TRADE_PLAN_ID | APPROVAL_STATE | TRADE_IDEA_ID | TRADE_THESIS_ID | CREATED_AT"
    )
    assert plan_id in list_plans.output

    show_position = runner.invoke(
        app,
        ["show-position", position_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert show_position.exit_code == 0
    assert _lines(show_position.output)[0] == f"Position {position_id}"
    assert "realized_pnl: 150.00" in show_position.output
    assert "order_intent_id:" in show_position.output
    assert "fill_id:" in show_position.output

    list_theses = runner.invoke(
        app,
        ["list-trade-theses", "--has-plan", "--sort", "newest"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert list_theses.exit_code == 0
    assert _lines(list_theses.output)[0] == (
        "TRADE_THESIS_ID | TRADE_IDEA_ID | PURPOSE | DIRECTION | PLAN_COUNT | "
        "TRADE_IDEA_CREATED_AT"
    )
    assert thesis_id in list_theses.output

    show_thesis = runner.invoke(
        app,
        ["show-trade-thesis", thesis_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert show_thesis.exit_code == 0
    assert _lines(show_thesis.output)[0] == f"Trade thesis {thesis_id}"
    assert "Trade plans" in show_thesis.output
    assert f"trade_plan_id: {plan_id}" in show_thesis.output

    list_reviews = runner.invoke(
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
            "risk-management",
            "--sort",
            "newest",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert list_reviews.exit_code == 0
    assert "Followed the plan." in list_reviews.output

    filtered_positions = runner.invoke(
        app,
        ["list-positions", "--has-review", "--purpose", "swing", "--sort", "newest"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert filtered_positions.exit_code == 0
    assert position_id in filtered_positions.output


def test_cli_rejects_invalid_uuid_for_write_commands(tmp_path) -> None:
    """Write commands surface clear UUID validation errors."""
    store_path = tmp_path / "store.json"

    result = runner.invoke(
        app,
        ["approve-trade-plan", "not-a-uuid"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "must be a valid UUID" in result.output


def test_create_order_intent_surfaces_missing_rule_evaluations(tmp_path) -> None:
    """Order intent creation reports service-layer gating errors clearly."""
    store_path = tmp_path / "store.json"
    instrument_id = str(uuid4())
    playbook_id = str(uuid4())

    create_idea = runner.invoke(
        app,
        [
            "create-trade-idea",
            "--instrument-id",
            instrument_id,
            "--playbook-id",
            playbook_id,
            "--purpose",
            "swing",
            "--direction",
            "long",
            "--horizon",
            "days_to_weeks",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    idea_id = _field(create_idea.output, "trade_idea_id")

    create_thesis = runner.invoke(
        app,
        [
            "create-trade-thesis",
            idea_id,
            "--reasoning",
            "Setup has a catalyst.",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    thesis_id = _field(create_thesis.output, "trade_thesis_id")

    create_plan = runner.invoke(
        app,
        [
            "create-trade-plan",
            "--trade-idea-id",
            idea_id,
            "--trade-thesis-id",
            thesis_id,
            "--entry-criteria",
            "Breakout confirmation.",
            "--invalidation",
            "Close below setup low.",
            "--risk-model",
            "Defined stop and max loss.",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    plan_id = _field(create_plan.output, "trade_plan_id")

    runner.invoke(
        app,
        ["approve-trade-plan", plan_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    result = runner.invoke(
        app,
        [
            "create-order-intent",
            "--trade-plan-id",
            plan_id,
            "--symbol",
            "AAPL",
            "--side",
            "buy",
            "--order-type",
            "limit",
            "--quantity",
            "100",
            "--limit-price",
            "25.50",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "persisted passing rule evaluations" in result.output


def test_record_fill_accepts_missing_order_intent_id(tmp_path) -> None:
    """Manual fill recording works without a linked order intent."""
    store_path = tmp_path / "store.json"
    plan_id = _seed_approved_and_evaluated_plan(store_path)

    open_position = runner.invoke(
        app,
        ["open-position", plan_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    position_id = _field(open_position.output, "position_id")

    result = runner.invoke(
        app,
        [
            "record-fill",
            "--position-id",
            position_id,
            "--side",
            "buy",
            "--quantity",
            "50",
            "--price",
            "10",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert "order_intent_id:" in result.output
    assert "position_state: open" in result.output


def test_cancel_order_intent_command_updates_status(tmp_path) -> None:
    """The cancel command persists canceled status using compact write output."""
    store_path = tmp_path / "store.json"
    plan_id = _seed_approved_and_evaluated_plan(store_path)

    create_order_intent = runner.invoke(
        app,
        [
            "create-order-intent",
            "--trade-plan-id",
            plan_id,
            "--symbol",
            "AAPL",
            "--side",
            "buy",
            "--order-type",
            "limit",
            "--quantity",
            "100",
            "--limit-price",
            "25.50",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    order_intent_id = _field(create_order_intent.output, "order_intent_id")

    result = runner.invoke(
        app,
        ["cancel-order-intent", order_intent_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert f"order_intent_id: {order_intent_id}" in result.output
    assert f"trade_plan_id: {plan_id}" in result.output
    assert "status: canceled" in result.output


def test_cancel_order_intent_rejects_invalid_uuid(tmp_path) -> None:
    """The cancel command reports invalid UUID arguments clearly."""
    store_path = tmp_path / "store.json"

    result = runner.invoke(
        app,
        ["cancel-order-intent", "not-a-uuid"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "must be a valid UUID" in result.output


def test_cancel_order_intent_rejects_missing_record(tmp_path) -> None:
    """The cancel command reports missing order intents clearly."""
    store_path = tmp_path / "store.json"

    result = runner.invoke(
        app,
        ["cancel-order-intent", str(uuid4())],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "Order intent does not exist." in result.output


def _seed_approved_and_evaluated_plan(store_path) -> str:
    instrument_id = str(uuid4())
    playbook_id = str(uuid4())
    create_idea = runner.invoke(
        app,
        [
            "create-trade-idea",
            "--instrument-id",
            instrument_id,
            "--playbook-id",
            playbook_id,
            "--purpose",
            "swing",
            "--direction",
            "long",
            "--horizon",
            "days_to_weeks",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    idea_id = _field(create_idea.output, "trade_idea_id")
    create_thesis = runner.invoke(
        app,
        [
            "create-trade-thesis",
            idea_id,
            "--reasoning",
            "Setup has a catalyst.",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    thesis_id = _field(create_thesis.output, "trade_thesis_id")
    create_plan = runner.invoke(
        app,
        [
            "create-trade-plan",
            "--trade-idea-id",
            idea_id,
            "--trade-thesis-id",
            thesis_id,
            "--entry-criteria",
            "Breakout confirmation.",
            "--invalidation",
            "Close below setup low.",
            "--risk-model",
            "Defined stop and max loss.",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    plan_id = _field(create_plan.output, "trade_plan_id")
    runner.invoke(
        app,
        ["approve-trade-plan", plan_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    runner.invoke(
        app,
        ["evaluate-trade-plan-rules", plan_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    return plan_id


def _field(output: str, name: str) -> str:
    prefix = f"{name}: "
    for line in output.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    raise AssertionError(f"Field {name!r} not found in output:\n{output}")


def _lines(output: str) -> list[str]:
    return output.rstrip().splitlines()
