"""CLI tests for read-only market context snapshot workflows."""

from uuid import uuid4
from decimal import Decimal

from typer.testing import CliRunner

from trading_system.app.cli import app
from trading_system.infrastructure.json.repositories import build_json_repositories
from trading_system.services.fill_service import FillService
from trading_system.services.position_service import PositionService
from trading_system.services.review_service import ReviewService
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


def test_show_trade_plan_renders_linked_context_metadata_without_payload(tmp_path) -> None:
    """Trade plan detail embeds linked market context metadata."""
    store_path = tmp_path / "store.json"
    context_path = _write_context_file(tmp_path)
    repositories = build_json_repositories(store_path)
    trade_plan_id = _create_plan(repositories)
    imported = _import_context(
        store_path,
        context_path,
        target_type="trade-plan",
        target_id=trade_plan_id,
    )
    snapshot_id = _lines(imported.output)[0].split(": ")[1]

    shown = runner.invoke(
        app,
        ["show-trade-plan", str(trade_plan_id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert shown.exit_code == 0
    assert "Market context" in shown.output
    assert f"market_context_snapshot_id: {snapshot_id}" in shown.output
    assert "context_type: price_snapshot" in shown.output
    assert "source_ref:" in shown.output
    assert '"symbol": "AAPL"' not in shown.output


def test_show_position_and_review_render_linked_context_metadata(tmp_path) -> None:
    """Position and review details embed their own linked market context metadata."""
    store_path = tmp_path / "store.json"
    context_path = _write_context_file(tmp_path)
    repositories = build_json_repositories(store_path)
    trade_plan_id = _create_plan(repositories)
    position = PositionService(
        plan_repository=repositories.plans,
        idea_repository=repositories.ideas,
        position_repository=repositories.positions,
        lifecycle_event_repository=repositories.lifecycle_events,
    ).open_position_from_plan(trade_plan_id)
    fill_service = FillService(
        position_repository=repositories.positions,
        fill_repository=repositories.fills,
        lifecycle_event_repository=repositories.lifecycle_events,
        order_intent_repository=repositories.order_intents,
    )
    fill_service.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("10"),
        price=Decimal("20"),
    )
    fill_service.record_manual_fill(
        position_id=position.id,
        side="sell",
        quantity=Decimal("10"),
        price=Decimal("22"),
    )
    review = ReviewService(
        position_repository=repositories.positions,
        review_repository=repositories.reviews,
        lifecycle_event_repository=repositories.lifecycle_events,
    ).create_trade_review(
        position_id=position.id,
        summary="Followed the plan.",
        what_went_well="Entry was clear.",
        what_went_poorly="Exit was late.",
    )
    position_import = _import_context(
        store_path,
        context_path,
        target_type="position",
        target_id=position.id,
    )
    review_import = _import_context(
        store_path,
        context_path,
        target_type="trade-review",
        target_id=review.id,
    )
    position_snapshot_id = _lines(position_import.output)[0].split(": ")[1]
    review_snapshot_id = _lines(review_import.output)[0].split(": ")[1]

    shown_position = runner.invoke(
        app,
        ["show-position", str(position.id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    shown_review = runner.invoke(
        app,
        ["show-trade-review", str(review.id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert shown_position.exit_code == 0
    assert f"market_context_snapshot_id: {position_snapshot_id}" in shown_position.output
    assert review_snapshot_id not in shown_position.output
    assert shown_review.exit_code == 0
    assert f"market_context_snapshot_id: {review_snapshot_id}" in shown_review.output
    assert position_snapshot_id not in shown_review.output


def test_detail_views_render_empty_context_section(tmp_path) -> None:
    """Detail commands show a stable empty market context section."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    trade_plan_id = _create_plan(repositories)

    shown = runner.invoke(
        app,
        ["show-trade-plan", str(trade_plan_id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert shown.exit_code == 0
    assert "Market context\nNo market context snapshots found." in shown.output


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


def _import_context(store_path, context_path, *, target_type: str, target_id):
    return runner.invoke(
        app,
        [
            "import-context",
            str(context_path),
            "--target-type",
            target_type,
            "--target-id",
            str(target_id),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )


def _lines(output: str) -> list[str]:
    return output.rstrip().splitlines()
