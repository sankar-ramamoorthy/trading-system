"""CLI tests for read-only market context snapshot workflows."""

from uuid import uuid4

from typer.testing import CliRunner

from trading_system.app.cli import app
from trading_system.infrastructure.json.repositories import build_json_repositories
from trading_system.services.trade_planning_service import TradePlanningService


runner = CliRunner()


def test_import_context_from_file_and_show_snapshot(tmp_path) -> None:
    """The CLI imports and displays one stored context snapshot."""
    store_path = tmp_path / "store.json"
    context_path = _write_context_file(tmp_path)
    repositories = build_json_repositories(store_path)
    trade_plan_id = _create_plan(repositories)

    imported = runner.invoke(
        app,
        [
            "import-context",
            str(context_path),
            "--target-type",
            "trade-plan",
            "--target-id",
            str(trade_plan_id),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert imported.exit_code == 0
    lines = _lines(imported.output)
    snapshot_id = lines[0].split(": ")[1]
    assert lines[0].startswith("market_context_snapshot_id: ")
    assert "context_type: price_snapshot" in imported.output
    assert "target_type: TradePlan" in imported.output
    assert f"target_id: {trade_plan_id}" in imported.output

    shown = runner.invoke(
        app,
        ["show-context", snapshot_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert shown.exit_code == 0
    assert _lines(shown.output)[0] == f"Market context snapshot {snapshot_id}"
    assert "source: local-file" in shown.output
    assert '"symbol": "AAPL"' in shown.output


def test_list_context_by_instrument_and_target(tmp_path) -> None:
    """The CLI lists snapshots by instrument and linked target."""
    store_path = tmp_path / "store.json"
    context_path = _write_context_file(tmp_path)
    repositories = build_json_repositories(store_path)
    trade_plan_id = _create_plan(repositories)
    plan = repositories.plans.get(trade_plan_id)
    instrument_id = repositories.ideas.get(plan.trade_idea_id).instrument_id
    runner.invoke(
        app,
        [
            "import-context",
            str(context_path),
            "--target-type",
            "trade-plan",
            "--target-id",
            str(trade_plan_id),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    by_instrument = runner.invoke(
        app,
        ["list-context", "--instrument-id", str(instrument_id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    by_target = runner.invoke(
        app,
        [
            "list-context",
            "--target-type",
            "trade-plan",
            "--target-id",
            str(trade_plan_id),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert by_instrument.exit_code == 0
    assert by_target.exit_code == 0
    assert _lines(by_instrument.output)[0].startswith("MARKET_CONTEXT_SNAPSHOT_ID")
    assert str(instrument_id) in by_instrument.output
    assert str(trade_plan_id) in by_target.output


def test_list_context_empty_state_and_filter_validation(tmp_path) -> None:
    """Context list output has stable empty and validation messages."""
    store_path = tmp_path / "store.json"

    empty = runner.invoke(
        app,
        ["list-context", "--instrument-id", str(uuid4())],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    invalid = runner.invoke(
        app,
        ["list-context"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert empty.exit_code == 0
    assert empty.output == "No market context snapshots found.\n"
    assert invalid.exit_code != 0
    assert "Provide either --instrument-id or --target-type with --target-id" in invalid.output


def test_import_context_rejects_missing_target(tmp_path) -> None:
    """Context imports report missing linked records clearly."""
    store_path = tmp_path / "store.json"
    context_path = _write_context_file(tmp_path)

    result = runner.invoke(
        app,
        [
            "import-context",
            str(context_path),
            "--target-type",
            "trade-plan",
            "--target-id",
            str(uuid4()),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "Trade plan does not exist for context target" in result.output


def _write_context_file(tmp_path):
    context_path = tmp_path / "context.json"
    context_path.write_text(
        """
        {
          "context_type": "price_snapshot",
          "observed_at": "2026-04-26T16:00:00+00:00",
          "payload": {
            "symbol": "AAPL",
            "last": "185.25"
          }
        }
        """,
        encoding="utf-8",
    )
    return context_path


def _create_plan(repositories):
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
    return planning.approve_trade_plan(plan.id).id


def _lines(output: str) -> list[str]:
    return output.rstrip().splitlines()
