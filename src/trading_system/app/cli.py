"""Typer command-line entrypoint for local trading workflows."""

from datetime import datetime
from decimal import Decimal
import os
from pathlib import Path
from uuid import UUID, uuid4

import typer

from trading_system.domain.rules.rule import Rule
from trading_system.infrastructure.json.repositories import build_json_repositories
from trading_system.rules_engine.implementations.risk_defined_rule import RiskDefinedRule
from trading_system.services.fill_service import FillService
from trading_system.services.position_query_service import PositionQueryService
from trading_system.services.position_service import PositionService
from trading_system.services.review_service import ReviewService
from trading_system.services.rule_service import RuleService
from trading_system.services.trade_planning_service import TradePlanningService

app = typer.Typer(help="Structured discretionary trading system.")


@app.command()
def version() -> None:
    """Print the scaffold version."""
    typer.echo("trading-system 0.1.0")


@app.command("demo-planned-trade")
def demo_planned_trade() -> None:
    """Run the full Milestone 1 workflow against durable JSON repositories."""
    repositories = build_json_repositories(_json_store_path())
    ideas = repositories.ideas
    theses = repositories.theses
    plans = repositories.plans
    positions = repositories.positions
    fills = repositories.fills
    lifecycle_events = repositories.lifecycle_events
    reviews = repositories.reviews
    evaluations = repositories.evaluations
    violations = repositories.violations

    planning = TradePlanningService(ideas, theses, plans)
    typer.echo("Milestone 1 demo: planned trade -> execution -> review")
    typer.echo(f"JSON store: {repositories.store_path}")
    typer.echo("")

    idea = planning.create_trade_idea(
        instrument_id=uuid4(),
        playbook_id=uuid4(),
        purpose="swing",
        direction="long",
        horizon="days_to_weeks",
    )
    typer.echo(f"1. Created trade idea: {idea.id}")

    thesis = planning.create_trade_thesis(
        trade_idea_id=idea.id,
        reasoning="Example discretionary setup.",
    )
    typer.echo(f"2. Created trade thesis: {thesis.id}")

    plan = planning.create_trade_plan(
        trade_idea_id=idea.id,
        trade_thesis_id=thesis.id,
        entry_criteria="Breakout confirmation.",
        invalidation="Close below setup low.",
        risk_model="Defined stop and max loss.",
    )
    typer.echo(f"3. Created trade plan: {plan.id}")

    approved_plan = planning.approve_trade_plan(plan.id)
    typer.echo(f"4. Approved plan: approval_state={approved_plan.approval_state}")

    risk_rule = Rule(
        code="risk_defined",
        name="Risk defined",
        description="Trade plans must define risk before execution.",
    )
    rule_service = RuleService(
        plan_repository=plans,
        evaluation_repository=evaluations,
        violation_repository=violations,
        rules=[(risk_rule, RiskDefinedRule(risk_rule))],
    )
    rule_results = rule_service.evaluate_trade_plan_rules(approved_plan.id)
    passed_count = sum(1 for result in rule_results if result.passed)
    typer.echo(
        "5. Evaluated deterministic rules: "
        f"{passed_count}/{len(rule_results)} passed, "
        f"violations={sum(1 for result in rule_results if not result.passed)}"
    )

    position_service = PositionService(
        plan_repository=plans,
        idea_repository=ideas,
        position_repository=positions,
        lifecycle_event_repository=lifecycle_events,
    )
    position = position_service.open_position_from_plan(approved_plan.id)
    typer.echo(
        "6. Opened position: "
        f"{position.id} state={position.lifecycle_state}"
    )

    fill_service = FillService(
        position_repository=positions,
        fill_repository=fills,
        lifecycle_event_repository=lifecycle_events,
    )
    entry_fill = fill_service.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25.50"),
        notes="Demo manual entry fill.",
    )
    position_after_entry = positions.get(position.id)
    if position_after_entry is None:
        raise RuntimeError("Position disappeared after entry fill persistence.")
    typer.echo(
        "7. Recorded entry fill: "
        f"{entry_fill.quantity} @ {entry_fill.price}; "
        f"open_quantity={position_after_entry.current_quantity}"
    )

    exit_fill = fill_service.record_manual_fill(
        position_id=position.id,
        side="sell",
        quantity=Decimal("100"),
        price=Decimal("27.00"),
        notes="Demo manual exit fill.",
    )
    position_after_exit = positions.get(position.id)
    if position_after_exit is None:
        raise RuntimeError("Position disappeared after exit fill persistence.")
    typer.echo(
        "8. Recorded exit fill: "
        f"{exit_fill.quantity} @ {exit_fill.price}; "
        f"open_quantity={position_after_exit.current_quantity}"
    )
    typer.echo(
        "9. Position closed from fills: "
        f"state={position_after_exit.lifecycle_state} "
        f"closed_at={position_after_exit.closed_at}"
    )

    review_service = ReviewService(
        position_repository=positions,
        review_repository=reviews,
        lifecycle_event_repository=lifecycle_events,
    )
    review = review_service.create_trade_review(
        position_id=position.id,
        summary="Demo review: followed the plan and exited completely.",
        what_went_well="Entry and exit were recorded against the planned trade.",
        what_went_poorly="Review details are placeholders for the demo.",
        lessons_learned=["Keep execution records tied to the original plan."],
        follow_up_actions=["Replace demo values with real review input."],
        rating=4,
    )
    typer.echo(
        "10. Created trade review: "
        f"{review.id} rating={review.rating} summary={review.summary!r}"
    )

    typer.echo("")
    typer.echo(
        "Final summary: "
        f"plan={approved_plan.id}, "
        f"approval_state={approved_plan.approval_state}, "
        f"rule_evaluations={len(rule_results)}, "
        f"violations={sum(1 for result in rule_results if not result.passed)}, "
        "fills=2, "
        f"open_quantity={position_after_exit.current_quantity}, "
        f"position_state={position_after_exit.lifecycle_state}, "
        f"review={review.id}, "
        "lifecycle_events=5"
    )


@app.command("list-positions")
def list_positions(
    state: str | None = typer.Option(
        None,
        "--state",
        help="Filter positions by lifecycle state, such as open or closed.",
    ),
) -> None:
    """List persisted positions from the local JSON store."""
    query_service = _position_query_service()
    positions = query_service.list_positions(lifecycle_state=state)
    if not positions:
        typer.echo("No positions found.")
        return

    typer.echo("POSITION_ID | STATE | PURPOSE | QTY | OPENED_AT | CLOSED_AT")
    for position in positions:
        typer.echo(
            " | ".join(
                [
                    str(position.id),
                    position.lifecycle_state,
                    position.purpose,
                    str(position.current_quantity),
                    position.opened_at.isoformat(),
                    _format_optional_datetime(position.closed_at),
                ]
            )
        )


@app.command("show-position")
def show_position(position_id: str) -> None:
    """Show a persisted position with linked plan, idea, fills, and review."""
    query_service = _position_query_service()
    try:
        detail = query_service.get_position_detail(_parse_uuid(position_id))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    position = detail.position
    plan = detail.trade_plan
    idea = detail.trade_idea

    typer.echo(f"Position {position.id}")
    typer.echo(f"state: {position.lifecycle_state}")
    typer.echo(f"purpose: {position.purpose}")
    typer.echo(f"instrument_id: {position.instrument_id}")
    typer.echo(f"trade_plan_id: {position.trade_plan_id}")
    typer.echo(f"current_quantity: {position.current_quantity}")
    typer.echo(f"average_entry_price: {position.average_entry_price}")
    typer.echo(f"opened_at: {position.opened_at.isoformat()}")
    typer.echo(f"closed_at: {_format_optional_datetime(position.closed_at)}")
    typer.echo("")
    typer.echo("Trade plan")
    typer.echo(f"id: {plan.id}")
    typer.echo(f"approval_state: {plan.approval_state}")
    typer.echo(f"entry_criteria: {plan.entry_criteria}")
    typer.echo(f"invalidation: {plan.invalidation}")
    typer.echo(f"risk_model: {plan.risk_model}")
    typer.echo("")
    typer.echo("Trade idea")
    typer.echo(f"id: {idea.id}")
    typer.echo(f"purpose: {idea.purpose}")
    typer.echo(f"direction: {idea.direction}")
    typer.echo(f"horizon: {idea.horizon}")
    typer.echo(f"instrument_id: {idea.instrument_id}")
    typer.echo("")
    typer.echo("Fills")
    if detail.fills:
        for fill in detail.fills:
            typer.echo(
                f"{fill.filled_at.isoformat()} | {fill.side} | "
                f"{fill.quantity} @ {fill.price} | source={fill.source} | "
                f"id={fill.id}"
            )
    else:
        typer.echo("No fills found.")
    typer.echo("")
    typer.echo("Review")
    if detail.review is None:
        typer.echo("No review found.")
    else:
        typer.echo(f"id: {detail.review.id}")
        typer.echo(f"rating: {detail.review.rating}")
        typer.echo(f"summary: {detail.review.summary}")


@app.command("show-position-timeline")
def show_position_timeline(position_id: str) -> None:
    """Show lifecycle events for a persisted position."""
    query_service = _position_query_service()
    try:
        events = query_service.get_position_timeline(_parse_uuid(position_id))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if not events:
        typer.echo("No lifecycle events found.")
        return

    typer.echo("OCCURRED_AT | EVENT_TYPE | ENTITY_TYPE | NOTE")
    for event in events:
        typer.echo(
            " | ".join(
                [
                    event.occurred_at.isoformat(),
                    event.event_type,
                    event.entity_type,
                    event.note,
                ]
            )
        )


def _json_store_path() -> Path:
    """Return the configured local JSON persistence path."""
    configured = os.environ.get("TRADING_SYSTEM_STORE_PATH")
    if configured:
        return Path(configured)
    return Path(".trading-system") / "store.json"


def _position_query_service() -> PositionQueryService:
    """Build a position query service from JSON repositories."""
    repositories = build_json_repositories(_json_store_path())
    return PositionQueryService(
        position_repository=repositories.positions,
        plan_repository=repositories.plans,
        idea_repository=repositories.ideas,
        fill_repository=repositories.fills,
        review_repository=repositories.reviews,
        lifecycle_event_repository=repositories.lifecycle_events,
    )


def _parse_uuid(value: str) -> UUID:
    """Parse a CLI UUID argument with a clear Typer error."""
    try:
        return UUID(value)
    except ValueError as exc:
        raise typer.BadParameter("must be a valid UUID") from exc


def _format_optional_datetime(value: datetime | None) -> str:
    """Format optional datetime values for CLI output."""
    return "" if value is None else value.isoformat()


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
