"""CLI tests for explicit write commands and upstream read commands."""

from datetime import UTC, datetime
from decimal import Decimal
import json
from uuid import uuid4

from typer.testing import CliRunner

from trading_system.domain.trading.broker_order import BrokerOrderStatus
from trading_system.domain.trading.order_intent import OrderSide
from trading_system.app.cli import app
from trading_system.ports.broker import (
    BrokerOrderSnapshot,
    BrokerOrderSync,
    BrokerSubmission,
)


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
    assert create_review.exit_code == 0
    assert "trade_review_id:" in create_review.output
    assert "rating: 4" in create_review.output
    assert "process_score: 5" in create_review.output
    assert "setup_quality: 4" in create_review.output
    assert "execution_quality: 3" in create_review.output
    assert "exit_quality: 2" in create_review.output
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
            "--process-score",
            "5",
            "--setup-quality",
            "4",
            "--execution-quality",
            "3",
            "--exit-quality",
            "2",
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


def test_paper_order_commands_submit_sync_and_show_broker_order(tmp_path) -> None:
    """Paper broker CLI commands submit, sync, and display local metadata."""
    store_path = tmp_path / "store.json"
    plan_id = _seed_approved_and_evaluated_plan(store_path)
    open_position = runner.invoke(
        app,
        ["open-position", plan_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    position_id = _field(open_position.output, "position_id")
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

    submit = runner.invoke(
        app,
        [
            "submit-paper-order",
            order_intent_id,
            "--position-id",
            position_id,
            "--provider",
            "simulated",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert submit.exit_code == 0
    broker_order_id = _field(submit.output, "broker_order_id")
    assert f"order_intent_id: {order_intent_id}" in submit.output
    assert f"position_id: {position_id}" in submit.output
    assert "provider: simulated" in submit.output
    assert "status: submitted" in submit.output

    sync = runner.invoke(
        app,
        [
            "sync-paper-order",
            broker_order_id,
            "--simulated-fill-price",
            "25.50",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert sync.exit_code == 0
    assert "fill_id:" in sync.output
    assert f"broker_order_id: {broker_order_id}" in sync.output
    assert "source: broker:simulated" in sync.output
    assert "position_state: open" in sync.output
    assert "open_quantity: 100" in sync.output

    show = runner.invoke(
        app,
        ["show-broker-order", broker_order_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert show.exit_code == 0
    assert f"broker_order_id: {broker_order_id}" in show.output
    assert "provider: simulated" in show.output
    assert "status: filled" in show.output
    assert "ALPACA" not in show.output


def test_alpaca_paper_order_cli_submit_and_sync_without_simulated_price(
    tmp_path,
    monkeypatch,
) -> None:
    """Alpaca provider selection uses real paper-provider semantics in the CLI."""
    import trading_system.app.cli as cli

    monkeypatch.setattr(
        cli,
        "AlpacaPaperBrokerClient",
        _FakeAlpacaPaperBrokerClient,
    )
    store_path = tmp_path / "store.json"
    plan_id = _seed_approved_and_evaluated_plan(store_path)
    position_id = _open_position(store_path, plan_id)
    order_intent_id = _create_order_intent(store_path, plan_id)

    submit = runner.invoke(
        app,
        [
            "submit-paper-order",
            order_intent_id,
            "--position-id",
            position_id,
            "--provider",
            "alpaca",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert submit.exit_code == 0
    broker_order_id = _field(submit.output, "broker_order_id")
    assert "provider: alpaca" in submit.output
    assert "provider_order_id: alpaca-test-order" in submit.output

    sync = runner.invoke(
        app,
        ["sync-paper-order", broker_order_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert sync.exit_code == 0
    assert f"broker_order_id: {broker_order_id}" in sync.output
    assert "status: filled" in sync.output
    assert "fill_id:" in sync.output
    assert "source: broker:alpaca" in sync.output


def test_broker_reconciliation_cli_commands_for_alpaca(tmp_path, monkeypatch) -> None:
    """Alpaca sync and reconcile commands use fake broker clients in CLI tests."""
    import trading_system.app.cli as cli

    monkeypatch.setattr(
        cli,
        "AlpacaPaperBrokerClient",
        _FakeAlpacaPaperBrokerClient,
    )
    store_path = tmp_path / "store.json"
    plan_id = _seed_approved_and_evaluated_plan(store_path)
    position_id = _open_position(store_path, plan_id)
    order_intent_id = _create_order_intent(store_path, plan_id)
    submit = runner.invoke(
        app,
        [
            "submit-paper-order",
            order_intent_id,
            "--position-id",
            position_id,
            "--provider",
            "alpaca",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    broker_order_id = _field(submit.output, "broker_order_id")

    sync = runner.invoke(
        app,
        ["sync-broker-orders", "--provider", "alpaca"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert sync.exit_code == 0
    assert "provider: alpaca" in sync.output
    assert "synced_count: 1" in sync.output
    assert broker_order_id in sync.output
    assert "submitted | filled | true |" in sync.output

    reconcile = runner.invoke(
        app,
        ["reconcile-broker-orders", "--provider", "alpaca"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert reconcile.exit_code == 0
    assert "provider: alpaca" in reconcile.output
    assert "matched: 1" in reconcile.output
    assert "updated: 0" in reconcile.output
    assert "missing_remote: 0" in reconcile.output
    assert "broker_only: 1" in reconcile.output
    assert "status_mismatch: 0" in reconcile.output
    assert "fill_mismatch: 0" in reconcile.output


def test_broker_order_list_cancel_and_reject_commands(tmp_path) -> None:
    """Broker-order CLI commands expose filters and simulated terminal outcomes."""
    store_path = tmp_path / "store.json"
    first_plan_id = _seed_approved_and_evaluated_plan(store_path)
    second_plan_id = _seed_approved_and_evaluated_plan(store_path)
    first_position_id = _open_position(store_path, first_plan_id)
    second_position_id = _open_position(store_path, second_plan_id)
    first_order_intent_id = _create_order_intent(store_path, first_plan_id)
    second_order_intent_id = _create_order_intent(store_path, second_plan_id)
    first_broker_order_id = _submit_paper_order(
        store_path,
        first_order_intent_id,
        first_position_id,
    )
    second_broker_order_id = _submit_paper_order(
        store_path,
        second_order_intent_id,
        second_position_id,
    )

    list_all = runner.invoke(
        app,
        ["list-broker-orders", "--provider", "simulated"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert list_all.exit_code == 0
    assert _lines(list_all.output)[0] == (
        "BROKER_ORDER_ID | PROVIDER | STATUS | SYMBOL | SIDE | QUANTITY | "
        "POSITION_ID | ORDER_INTENT_ID | SUBMITTED_AT | UPDATED_AT"
    )
    assert first_broker_order_id in list_all.output
    assert second_broker_order_id in list_all.output

    cancel = runner.invoke(
        app,
        ["cancel-paper-order", first_broker_order_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert cancel.exit_code == 0
    assert f"broker_order_id: {first_broker_order_id}" in cancel.output
    assert "status: canceled" in cancel.output

    reject = runner.invoke(
        app,
        [
            "reject-paper-order",
            second_broker_order_id,
            "--reason",
            "Simulated rejection.",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert reject.exit_code == 0
    assert f"broker_order_id: {second_broker_order_id}" in reject.output
    assert "status: rejected" in reject.output

    canceled_only = runner.invoke(
        app,
        ["list-broker-orders", "--status", "canceled"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert canceled_only.exit_code == 0
    assert first_broker_order_id in canceled_only.output
    assert second_broker_order_id not in canceled_only.output

    sync_canceled = runner.invoke(
        app,
        [
            "sync-paper-order",
            first_broker_order_id,
            "--simulated-fill-price",
            "25.50",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert sync_canceled.exit_code != 0
    assert "cannot be synced" in sync_canceled.output


def test_show_broker_order_displays_linked_metadata(tmp_path) -> None:
    """Broker-order detail output includes linked fill and position metadata."""
    store_path = tmp_path / "store.json"
    plan_id = _seed_approved_and_evaluated_plan(store_path)
    position_id = _open_position(store_path, plan_id)
    order_intent_id = _create_order_intent(store_path, plan_id)
    broker_order_id = _submit_paper_order(
        store_path,
        order_intent_id,
        position_id,
    )
    sync = runner.invoke(
        app,
        [
            "sync-paper-order",
            broker_order_id,
            "--simulated-fill-price",
            "25.50",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    fill_id = _field(sync.output, "fill_id")

    show = runner.invoke(
        app,
        ["show-broker-order", broker_order_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert show.exit_code == 0
    assert "fill_count: 1" in show.output
    assert f"fill_ids: {fill_id}" in show.output
    assert "order_intent_status: created" in show.output
    assert "position_state: open" in show.output
    assert "open_quantity: 100" in show.output


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


def test_validate_store_command_reports_collection_counts(tmp_path) -> None:
    """The validate-store command reports local JSON store health."""
    store_path = tmp_path / "store.json"
    store_path.write_text(
        json.dumps(
            {
                "trade_ideas": {"one": {}},
                "trade_reviews": {"two": {}, "three": {}},
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["validate-store"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert f"store_path: {store_path}" in result.output
    assert "collections: trade_ideas,trade_theses,trade_plans" in result.output
    assert "broker_orders" in result.output
    assert "total_records: 3" in result.output
    assert "trade_ideas: 1" in result.output
    assert "trade_reviews: 2" in result.output


def test_validate_store_command_rejects_missing_store(tmp_path) -> None:
    """The validate-store command requires an existing store file."""
    store_path = tmp_path / "missing.json"

    result = runner.invoke(
        app,
        ["validate-store"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "JSON persistence store does not exist" in result.output


def test_backup_store_command_creates_timestamped_json_backup(tmp_path) -> None:
    """The backup-store command creates an inspectable JSON backup file."""
    store_path = tmp_path / "store.json"
    backup_dir = tmp_path / "backups"
    store_path.write_text('{"trade_ideas":{"one":{}}}', encoding="utf-8")

    result = runner.invoke(
        app,
        ["backup-store", "--output-dir", str(backup_dir)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    backups = list(backup_dir.glob("trading-system-store-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == store_path.read_text(
        encoding="utf-8"
    )
    assert f"backup_path: {backups[0]}" in result.output
    assert f"source_store_path: {store_path}" in result.output


def test_backup_store_command_rejects_invalid_store(tmp_path) -> None:
    """The backup-store command validates before writing a backup."""
    store_path = tmp_path / "store.json"
    backup_dir = tmp_path / "backups"
    store_path.write_text("{not valid json", encoding="utf-8")

    result = runner.invoke(
        app,
        ["backup-store", "--output-dir", str(backup_dir)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "JSON persistence store is invalid" in result.output
    assert not backup_dir.exists()


def test_restore_store_command_requires_overwrite_for_existing_store(tmp_path) -> None:
    """The restore-store command protects an existing configured store."""
    backup_path = tmp_path / "backup.json"
    store_path = tmp_path / "store.json"
    backup_path.write_text('{"trade_ideas":{"backup":{}}}', encoding="utf-8")
    store_path.write_text('{"trade_ideas":{"current":{}}}', encoding="utf-8")

    result = runner.invoke(
        app,
        ["restore-store", str(backup_path)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "Use --overwrite to replace it." in result.output
    assert json.loads(store_path.read_text(encoding="utf-8")) == {
        "trade_ideas": {"current": {}}
    }


def test_restore_store_command_replaces_store_with_overwrite(tmp_path) -> None:
    """The restore-store command restores a validated backup with overwrite."""
    backup_path = tmp_path / "backup.json"
    store_path = tmp_path / "store.json"
    backup_path.write_text('{"trade_ideas":{"backup":{}}}', encoding="utf-8")
    store_path.write_text('{"trade_ideas":{"current":{}}}', encoding="utf-8")

    result = runner.invoke(
        app,
        ["restore-store", str(backup_path), "--overwrite"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert f"restored_store_path: {store_path}" in result.output
    assert f"backup_path: {backup_path}" in result.output
    restored = json.loads(store_path.read_text(encoding="utf-8"))
    assert restored["trade_ideas"] == {"backup": {}}
    assert restored["trade_reviews"] == {}


def test_restore_store_command_rejects_invalid_backup(tmp_path) -> None:
    """The restore-store command validates backup JSON before replacement."""
    backup_path = tmp_path / "backup.json"
    store_path = tmp_path / "store.json"
    backup_path.write_text("{not valid json", encoding="utf-8")
    store_path.write_text('{"trade_ideas":{"current":{}}}', encoding="utf-8")

    result = runner.invoke(
        app,
        ["restore-store", str(backup_path), "--overwrite"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "JSON persistence store is invalid" in result.output
    assert json.loads(store_path.read_text(encoding="utf-8")) == {
        "trade_ideas": {"current": {}}
    }


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


def _open_position(store_path, plan_id: str) -> str:
    result = runner.invoke(
        app,
        ["open-position", plan_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert result.exit_code == 0
    return _field(result.output, "position_id")


def _create_order_intent(store_path, plan_id: str) -> str:
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
    assert result.exit_code == 0
    return _field(result.output, "order_intent_id")


def _submit_paper_order(
    store_path,
    order_intent_id: str,
    position_id: str,
) -> str:
    result = runner.invoke(
        app,
        [
            "submit-paper-order",
            order_intent_id,
            "--position-id",
            position_id,
            "--provider",
            "simulated",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    assert result.exit_code == 0
    return _field(result.output, "broker_order_id")


class _FakeAlpacaPaperBrokerClient:
    provider = "alpaca"

    def submit_order(self, order_intent, position):
        timestamp = datetime(2026, 5, 3, tzinfo=UTC)
        return BrokerSubmission(
            provider=self.provider,
            provider_order_id="alpaca-test-order",
            status=BrokerOrderStatus.SUBMITTED,
            submitted_at=timestamp,
            updated_at=timestamp,
        )

    def sync_order(self, broker_order_id, simulated_fill_price=None):
        assert broker_order_id == "alpaca-test-order"
        assert simulated_fill_price is None
        return BrokerOrderSync(
            status=BrokerOrderStatus.FILLED,
            updated_at=datetime(2026, 5, 3, tzinfo=UTC),
            fill_price=Decimal("25.50"),
        )

    def list_order_snapshots(self):
        timestamp = datetime(2026, 5, 3, tzinfo=UTC)
        return [
            BrokerOrderSnapshot(
                provider=self.provider,
                provider_order_id="alpaca-test-order",
                status=BrokerOrderStatus.FILLED,
                updated_at=timestamp,
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=Decimal("100"),
                fill_price=Decimal("25.50"),
            ),
            BrokerOrderSnapshot(
                provider=self.provider,
                provider_order_id="broker-only-order",
                status=BrokerOrderStatus.SUBMITTED,
                updated_at=timestamp,
                symbol="MSFT",
                side=OrderSide.BUY,
                quantity=Decimal("5"),
            ),
        ]


def _field(output: str, name: str) -> str:
    prefix = f"{name}: "
    for line in output.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    raise AssertionError(f"Field {name!r} not found in output:\n{output}")


def _lines(output: str) -> list[str]:
    return output.rstrip().splitlines()
