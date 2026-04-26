"""Typer command-line entrypoint for local trading workflows."""

from datetime import datetime
from decimal import Decimal
import json
import os
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import typer

from trading_system.domain.rules.rule import Rule
from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.domain.trading.order_intent import OrderIntent, OrderSide, OrderType
from trading_system.domain.trading.review import TradeReview
from trading_system.infrastructure.json.repositories import (
    JsonRepositorySet,
    build_json_repositories,
)
from trading_system.infrastructure.json.market_context_source import (
    JsonMarketContextImportSource,
)
from trading_system.services.cancel_order_intent_service import CancelOrderIntentService
from trading_system.rules_engine.implementations.risk_defined_rule import RiskDefinedRule
from trading_system.services.create_order_intent_service import CreateOrderIntentService
from trading_system.services.fill_service import FillService
from trading_system.services.market_context_service import (
    MarketContextImportService,
    MarketContextQueryService,
)
from trading_system.services.position_query_service import PositionQueryService
from trading_system.services.position_service import PositionService
from trading_system.services.review_query_service import ReviewQueryService
from trading_system.services.review_service import ReviewService
from trading_system.services.rule_service import RuleService
from trading_system.services.trade_planning_service import TradePlanningService
from trading_system.services.trade_query_service import TradeQueryService

app = typer.Typer(help="Structured discretionary trading system.")
ListSortOrder = Literal["oldest", "newest"]
ContextTargetOption = Literal["trade-plan", "position", "trade-review"]


@app.command()
def version() -> None:
    """Print the scaffold version."""
    typer.echo("trading-system 0.1.0")


@app.command("demo-planned-trade")
def demo_planned_trade() -> None:
    """Run the full Milestone 1 workflow against durable JSON repositories."""
    repositories = _repositories()
    ideas = repositories.ideas
    theses = repositories.theses
    plans = repositories.plans
    positions = repositories.positions
    order_intents = repositories.order_intents
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

    rule_results = _rule_service(repositories).evaluate_trade_plan_rules(approved_plan.id)
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
    order_intent_service = CreateOrderIntentService(
        plan_repository=plans,
        order_intent_repository=order_intents,
        evaluation_repository=evaluations,
        lifecycle_event_repository=lifecycle_events,
    )
    order_intent = order_intent_service.create_order_intent(
        trade_plan_id=approved_plan.id,
        symbol="DEMO",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("100"),
        limit_price=Decimal("25.50"),
        notes="Demo order intent before manual fill entry.",
    )
    typer.echo(
        "6. Created order intent: "
        f"{order_intent.id} status={order_intent.status.value}"
    )
    position = position_service.open_position_from_plan(approved_plan.id)
    typer.echo(
        "7. Opened position: "
        f"{position.id} state={position.lifecycle_state}"
    )

    fill_service = FillService(
        position_repository=positions,
        fill_repository=fills,
        lifecycle_event_repository=lifecycle_events,
        order_intent_repository=order_intents,
    )
    entry_fill = fill_service.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25.50"),
        notes="Demo manual entry fill.",
        order_intent_id=order_intent.id,
    )
    position_after_entry = positions.get(position.id)
    if position_after_entry is None:
        raise RuntimeError("Position disappeared after entry fill persistence.")
    typer.echo(
        "8. Recorded entry fill: "
        f"{entry_fill.quantity} @ {entry_fill.price}; "
        f"open_quantity={position_after_entry.current_quantity}"
    )

    exit_fill = fill_service.record_manual_fill(
        position_id=position.id,
        side="sell",
        quantity=Decimal("100"),
        price=Decimal("27.00"),
        notes="Demo manual exit fill.",
        order_intent_id=order_intent.id,
    )
    position_after_exit = positions.get(position.id)
    if position_after_exit is None:
        raise RuntimeError("Position disappeared after exit fill persistence.")
    typer.echo(
        "9. Recorded exit fill: "
        f"{exit_fill.quantity} @ {exit_fill.price}; "
        f"open_quantity={position_after_exit.current_quantity}"
    )
    typer.echo(
        "10. Position closed from fills: "
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
        "11. Created trade review: "
        f"{review.id} rating={review.rating} summary={review.summary!r}"
    )

    typer.echo("")
    typer.echo(
        "Final summary: "
        f"plan={approved_plan.id}, "
        f"order_intent={order_intent.id}, "
        f"approval_state={approved_plan.approval_state}, "
        f"rule_evaluations={len(rule_results)}, "
        f"violations={sum(1 for result in rule_results if not result.passed)}, "
        "fills=2, "
        f"open_quantity={position_after_exit.current_quantity}, "
        f"position_state={position_after_exit.lifecycle_state}, "
        f"review={review.id}, "
        "lifecycle_events=6"
    )


@app.command("create-trade-idea")
def create_trade_idea(
    instrument_id: str = typer.Option(..., "--instrument-id"),
    playbook_id: str = typer.Option(..., "--playbook-id"),
    purpose: str = typer.Option(..., "--purpose"),
    direction: str = typer.Option(..., "--direction"),
    horizon: str = typer.Option(..., "--horizon"),
) -> None:
    """Create and persist a trade idea."""
    repositories = _repositories()
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
    idea = _run_service(
        lambda: planning.create_trade_idea(
            instrument_id=_parse_uuid(instrument_id),
            playbook_id=_parse_uuid(playbook_id),
            purpose=purpose,
            direction=direction,
            horizon=horizon,
        )
    )
    typer.echo(f"trade_idea_id: {idea.id}")
    typer.echo(f"status: {idea.status}")
    typer.echo(f"purpose: {idea.purpose}")
    typer.echo(f"direction: {idea.direction}")
    typer.echo(f"horizon: {idea.horizon}")


@app.command("create-trade-thesis")
def create_trade_thesis(
    trade_idea_id: str = typer.Argument(...),
    reasoning: str = typer.Option(..., "--reasoning"),
    supporting_evidence: list[str] = typer.Option(
        None,
        "--supporting-evidence",
        help="Repeat to add multiple supporting evidence items.",
    ),
    risks: list[str] = typer.Option(
        None,
        "--risk",
        help="Repeat to add multiple risks.",
    ),
    disconfirming_signals: list[str] = typer.Option(
        None,
        "--disconfirming-signal",
        help="Repeat to add multiple disconfirming signals.",
    ),
) -> None:
    """Create and persist a trade thesis."""
    repositories = _repositories()
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
    thesis = _run_service(
        lambda: planning.create_trade_thesis(
            trade_idea_id=_parse_uuid(trade_idea_id),
            reasoning=reasoning,
            supporting_evidence=supporting_evidence,
            risks=risks,
            disconfirming_signals=disconfirming_signals,
        )
    )
    typer.echo(f"trade_thesis_id: {thesis.id}")
    typer.echo(f"trade_idea_id: {thesis.trade_idea_id}")
    typer.echo(f"reasoning: {thesis.reasoning}")
    typer.echo(f"supporting_evidence_count: {len(thesis.supporting_evidence)}")
    typer.echo(f"risks_count: {len(thesis.risks)}")
    typer.echo(f"disconfirming_signals_count: {len(thesis.disconfirming_signals)}")


@app.command("create-trade-plan")
def create_trade_plan(
    trade_idea_id: str = typer.Option(..., "--trade-idea-id"),
    trade_thesis_id: str = typer.Option(..., "--trade-thesis-id"),
    entry_criteria: str = typer.Option(..., "--entry-criteria"),
    invalidation: str = typer.Option(..., "--invalidation"),
    targets: list[str] = typer.Option(
        None,
        "--target",
        help="Repeat to add multiple targets.",
    ),
    risk_model: str | None = typer.Option(None, "--risk-model"),
    sizing_assumptions: str | None = typer.Option(None, "--sizing-assumptions"),
) -> None:
    """Create and persist a trade plan."""
    repositories = _repositories()
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
    plan = _run_service(
        lambda: planning.create_trade_plan(
            trade_idea_id=_parse_uuid(trade_idea_id),
            trade_thesis_id=_parse_uuid(trade_thesis_id),
            entry_criteria=entry_criteria,
            invalidation=invalidation,
            targets=targets,
            risk_model=risk_model,
            sizing_assumptions=sizing_assumptions,
        )
    )
    typer.echo(f"trade_plan_id: {plan.id}")
    typer.echo(f"approval_state: {plan.approval_state}")
    typer.echo(f"trade_idea_id: {plan.trade_idea_id}")
    typer.echo(f"trade_thesis_id: {plan.trade_thesis_id}")
    typer.echo(f"targets_count: {len(plan.targets)}")


@app.command("approve-trade-plan")
def approve_trade_plan(trade_plan_id: str) -> None:
    """Approve a persisted trade plan."""
    repositories = _repositories()
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
    plan = _run_service(lambda: planning.approve_trade_plan(_parse_uuid(trade_plan_id)))
    typer.echo(f"trade_plan_id: {plan.id}")
    typer.echo(f"approval_state: {plan.approval_state}")


@app.command("evaluate-trade-plan-rules")
def evaluate_trade_plan_rules(trade_plan_id: str) -> None:
    """Run deterministic rules for one approved trade plan."""
    evaluations = _run_service(
        lambda: _rule_service(_repositories()).evaluate_trade_plan_rules(
            _parse_uuid(trade_plan_id)
        )
    )
    typer.echo(f"trade_plan_id: {trade_plan_id}")
    typer.echo(f"rule_evaluations: {len(evaluations)}")
    typer.echo(f"passed: {sum(1 for evaluation in evaluations if evaluation.passed)}")
    typer.echo(
        f"failed: {sum(1 for evaluation in evaluations if not evaluation.passed)}"
    )
    for evaluation in evaluations:
        typer.echo(
            f"{evaluation.evaluated_at.isoformat()} | passed={evaluation.passed} | "
            f"rule_id={evaluation.rule_id} | details={evaluation.details or ''}"
        )


@app.command("create-order-intent")
def create_order_intent(
    trade_plan_id: str = typer.Option(..., "--trade-plan-id"),
    symbol: str = typer.Option(..., "--symbol"),
    side: OrderSide = typer.Option(..., "--side"),
    order_type: OrderType = typer.Option(..., "--order-type"),
    quantity: str = typer.Option(..., "--quantity"),
    limit_price: str | None = typer.Option(None, "--limit-price"),
    stop_price: str | None = typer.Option(None, "--stop-price"),
    notes: str | None = typer.Option(None, "--notes"),
) -> None:
    """Create and persist an order intent from an approved trade plan."""
    repositories = _repositories()
    order_intent = _run_service(
        lambda: CreateOrderIntentService(
            plan_repository=repositories.plans,
            order_intent_repository=repositories.order_intents,
            evaluation_repository=repositories.evaluations,
            lifecycle_event_repository=repositories.lifecycle_events,
        ).create_order_intent(
            trade_plan_id=_parse_uuid(trade_plan_id),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=_parse_decimal(quantity),
            limit_price=None if limit_price is None else _parse_decimal(limit_price),
            stop_price=None if stop_price is None else _parse_decimal(stop_price),
            notes=notes,
        )
    )
    _echo_order_intent(order_intent)


@app.command("cancel-order-intent")
def cancel_order_intent(order_intent_id: str) -> None:
    """Cancel a persisted order intent."""
    repositories = _repositories()
    order_intent = _run_service(
        lambda: CancelOrderIntentService(
            order_intent_repository=repositories.order_intents,
            lifecycle_event_repository=repositories.lifecycle_events,
        ).cancel_order_intent(_parse_uuid(order_intent_id))
    )
    _echo_order_intent(order_intent)


@app.command("open-position")
def open_position(trade_plan_id: str) -> None:
    """Open a position from an approved trade plan."""
    repositories = _repositories()
    position = _run_service(
        lambda: PositionService(
            plan_repository=repositories.plans,
            idea_repository=repositories.ideas,
            position_repository=repositories.positions,
            lifecycle_event_repository=repositories.lifecycle_events,
        ).open_position_from_plan(_parse_uuid(trade_plan_id))
    )
    typer.echo(f"position_id: {position.id}")
    typer.echo(f"trade_plan_id: {position.trade_plan_id}")
    typer.echo(f"lifecycle_state: {position.lifecycle_state}")
    typer.echo(f"current_quantity: {position.current_quantity}")


@app.command("record-fill")
def record_fill(
    position_id: str = typer.Option(..., "--position-id"),
    side: str = typer.Option(..., "--side"),
    quantity: str = typer.Option(..., "--quantity"),
    price: str = typer.Option(..., "--price"),
    notes: str | None = typer.Option(None, "--notes"),
    order_intent_id: str | None = typer.Option(None, "--order-intent-id"),
) -> None:
    """Record a manual fill for one position."""
    repositories = _repositories()
    fill = _run_service(
        lambda: FillService(
            position_repository=repositories.positions,
            fill_repository=repositories.fills,
            lifecycle_event_repository=repositories.lifecycle_events,
            order_intent_repository=repositories.order_intents,
        ).record_manual_fill(
            position_id=_parse_uuid(position_id),
            side=side,
            quantity=_parse_decimal(quantity),
            price=_parse_decimal(price),
            notes=notes,
            order_intent_id=None
            if order_intent_id is None
            else _parse_uuid(order_intent_id),
        )
    )
    position = repositories.positions.get(fill.position_id)
    if position is None:
        raise RuntimeError("Position disappeared after fill persistence.")
    typer.echo(f"fill_id: {fill.id}")
    typer.echo(f"position_id: {fill.position_id}")
    typer.echo(f"side: {fill.side}")
    typer.echo(f"quantity: {fill.quantity}")
    typer.echo(f"price: {fill.price}")
    typer.echo(
        "order_intent_id: "
        f"{'' if fill.order_intent_id is None else fill.order_intent_id}"
    )
    typer.echo(f"position_state: {position.lifecycle_state}")
    typer.echo(f"open_quantity: {position.current_quantity}")


@app.command("create-trade-review")
def create_trade_review(
    position_id: str = typer.Option(..., "--position-id"),
    summary: str = typer.Option(..., "--summary"),
    what_went_well: str = typer.Option(..., "--what-went-well"),
    what_went_poorly: str = typer.Option(..., "--what-went-poorly"),
    lessons_learned: list[str] = typer.Option(
        None,
        "--lesson",
        help="Repeat to add multiple lessons learned.",
    ),
    follow_up_actions: list[str] = typer.Option(
        None,
        "--follow-up-action",
        help="Repeat to add multiple follow-up actions.",
    ),
    rating: int | None = typer.Option(None, "--rating"),
) -> None:
    """Create one immutable review for a closed position."""
    repositories = _repositories()
    review = _run_service(
        lambda: ReviewService(
            position_repository=repositories.positions,
            review_repository=repositories.reviews,
            lifecycle_event_repository=repositories.lifecycle_events,
        ).create_trade_review(
            position_id=_parse_uuid(position_id),
            summary=summary,
            what_went_well=what_went_well,
            what_went_poorly=what_went_poorly,
            lessons_learned=lessons_learned,
            follow_up_actions=follow_up_actions,
            rating=rating,
        )
    )
    _echo_trade_review(review)


@app.command("list-trade-ideas")
def list_trade_ideas(
    purpose: str | None = typer.Option(None, "--purpose"),
    direction: str | None = typer.Option(None, "--direction"),
    status: str | None = typer.Option(None, "--status"),
    sort: ListSortOrder = typer.Option("oldest", "--sort"),
) -> None:
    """List persisted trade ideas from the local JSON store."""
    ideas = _trade_query_service().list_trade_ideas(
        purpose=purpose,
        direction=direction,
        status=status,
        sort=sort,
    )
    if not ideas:
        typer.echo("No trade ideas found.")
        return

    typer.echo("TRADE_IDEA_ID | STATUS | PURPOSE | DIRECTION | HORIZON | CREATED_AT")
    for idea in ideas:
        typer.echo(
            " | ".join(
                [
                    str(idea.id),
                    idea.status,
                    idea.purpose,
                    idea.direction,
                    idea.horizon,
                    idea.created_at.isoformat(),
                ]
            )
        )


@app.command("list-trade-theses")
def list_trade_theses(
    purpose: str | None = typer.Option(None, "--purpose"),
    direction: str | None = typer.Option(None, "--direction"),
    has_plan: bool = typer.Option(False, "--has-plan"),
    sort: ListSortOrder = typer.Option("oldest", "--sort"),
) -> None:
    """List persisted trade theses with linked idea context and plan counts."""
    theses = _trade_query_service().list_trade_theses(
        purpose=purpose,
        direction=direction,
        has_plan=True if has_plan else None,
        sort=sort,
    )
    if not theses:
        typer.echo("No trade theses found.")
        return

    typer.echo(
        "TRADE_THESIS_ID | TRADE_IDEA_ID | PURPOSE | DIRECTION | PLAN_COUNT | "
        "TRADE_IDEA_CREATED_AT"
    )
    for item in theses:
        typer.echo(
            " | ".join(
                [
                    str(item.trade_thesis.id),
                    str(item.trade_idea.id),
                    item.trade_idea.purpose,
                    item.trade_idea.direction,
                    str(item.plan_count),
                    item.trade_idea.created_at.isoformat(),
                ]
            )
        )


@app.command("show-trade-thesis")
def show_trade_thesis(trade_thesis_id: str) -> None:
    """Show a persisted trade thesis with linked trade idea and trade plans."""
    detail = _run_service(
        lambda: _trade_query_service().get_trade_thesis_detail(
            _parse_uuid(trade_thesis_id)
        )
    )
    thesis = detail.trade_thesis

    _echo_section(
        "Trade thesis",
        [
            ("trade_idea_id", thesis.trade_idea_id),
            ("reasoning", thesis.reasoning),
            ("supporting_evidence", _format_string_list(thesis.supporting_evidence)),
            ("risks", _format_string_list(thesis.risks)),
            ("disconfirming_signals", _format_string_list(thesis.disconfirming_signals)),
        ],
        heading_value=thesis.id,
    )
    _echo_section(
        "Trade idea",
        [
            ("id", detail.trade_idea.id),
            ("status", detail.trade_idea.status),
            ("instrument_id", detail.trade_idea.instrument_id),
            ("playbook_id", detail.trade_idea.playbook_id),
            ("purpose", detail.trade_idea.purpose),
            ("direction", detail.trade_idea.direction),
            ("horizon", detail.trade_idea.horizon),
            ("created_at", detail.trade_idea.created_at.isoformat()),
        ],
    )
    _echo_collection_section(
        "Trade plans",
        "No trade plans found.",
        [
            [
                ("trade_plan_id", plan.id),
                ("approval_state", plan.approval_state),
                ("trade_idea_id", plan.trade_idea_id),
                ("entry_criteria", plan.entry_criteria),
                ("invalidation", plan.invalidation),
                ("created_at", plan.created_at.isoformat()),
            ]
            for plan in detail.trade_plans
        ],
    )


@app.command("list-trade-plans")
def list_trade_plans(
    approval_state: str | None = typer.Option(None, "--approval-state"),
    sort: ListSortOrder = typer.Option("oldest", "--sort"),
) -> None:
    """List persisted trade plans from the local JSON store."""
    plans = _trade_query_service().list_trade_plans(
        approval_state=approval_state,
        sort=sort,
    )
    if not plans:
        typer.echo("No trade plans found.")
        return

    typer.echo(
        "TRADE_PLAN_ID | APPROVAL_STATE | TRADE_IDEA_ID | TRADE_THESIS_ID | CREATED_AT"
    )
    for plan in plans:
        typer.echo(
            " | ".join(
                [
                    str(plan.id),
                    plan.approval_state,
                    str(plan.trade_idea_id),
                    str(plan.trade_thesis_id),
                    plan.created_at.isoformat(),
                ]
            )
        )


@app.command("show-trade-plan")
def show_trade_plan(trade_plan_id: str) -> None:
    """Show a persisted trade plan with linked upstream and downstream records."""
    query_service = _trade_query_service()
    detail = _run_service(
        lambda: query_service.get_trade_plan_detail(_parse_uuid(trade_plan_id))
    )
    plan = detail.trade_plan

    _echo_section(
        "Trade plan",
        [
            ("approval_state", plan.approval_state),
            ("trade_idea_id", plan.trade_idea_id),
            ("trade_thesis_id", plan.trade_thesis_id),
            ("entry_criteria", plan.entry_criteria),
            ("invalidation", plan.invalidation),
            ("targets", _format_string_list(plan.targets)),
            ("risk_model", _format_optional_text(plan.risk_model)),
            ("sizing_assumptions", _format_optional_text(plan.sizing_assumptions)),
            ("created_at", plan.created_at.isoformat()),
        ],
        heading_value=plan.id,
    )
    _echo_section(
        "Trade idea",
        [
            ("id", detail.trade_idea.id),
            ("status", detail.trade_idea.status),
            ("instrument_id", detail.trade_idea.instrument_id),
            ("playbook_id", detail.trade_idea.playbook_id),
            ("purpose", detail.trade_idea.purpose),
            ("direction", detail.trade_idea.direction),
            ("horizon", detail.trade_idea.horizon),
            ("created_at", detail.trade_idea.created_at.isoformat()),
        ],
    )
    _echo_section(
        "Trade thesis",
        [
            ("id", detail.trade_thesis.id),
            ("trade_idea_id", detail.trade_thesis.trade_idea_id),
            ("reasoning", detail.trade_thesis.reasoning),
            (
                "supporting_evidence",
                _format_string_list(detail.trade_thesis.supporting_evidence),
            ),
            ("risks", _format_string_list(detail.trade_thesis.risks)),
            (
                "disconfirming_signals",
                _format_string_list(detail.trade_thesis.disconfirming_signals),
            ),
        ],
    )
    _echo_collection_section(
        "Rule evaluations",
        "No rule evaluations found.",
        [
            [
                ("rule_evaluation_id", evaluation.id),
                ("rule_id", evaluation.rule_id),
                ("passed", evaluation.passed),
                ("details", _format_optional_text(evaluation.details)),
                ("evaluated_at", evaluation.evaluated_at.isoformat()),
            ]
            for evaluation in detail.rule_evaluations
        ],
    )
    _echo_collection_section(
        "Order intents",
        "No order intents found.",
        [
            [
                ("order_intent_id", order_intent.id),
                ("status", order_intent.status.value),
                ("symbol", order_intent.symbol),
                ("side", order_intent.side.value),
                ("order_type", order_intent.order_type.value),
                ("quantity", order_intent.quantity),
                ("limit_price", _format_optional_decimal(order_intent.limit_price)),
                ("stop_price", _format_optional_decimal(order_intent.stop_price)),
                ("notes", _format_optional_text(order_intent.notes)),
                ("created_at", order_intent.created_at.isoformat()),
            ]
            for order_intent in detail.order_intents
        ],
    )
    _echo_collection_section(
        "Positions",
        "No positions found.",
        [
            [
                ("position_id", position.id),
                ("state", position.lifecycle_state),
                ("current_quantity", position.current_quantity),
                ("opened_at", position.opened_at.isoformat()),
                ("closed_at", _format_optional_show_datetime(position.closed_at)),
            ]
            for position in detail.positions
        ],
    )
    _echo_market_context_section(detail.market_context_snapshots)


@app.command("list-trade-reviews")
def list_trade_reviews(
    rating: int | None = typer.Option(None, "--rating"),
    purpose: str | None = typer.Option(None, "--purpose"),
    direction: str | None = typer.Option(None, "--direction"),
    sort: ListSortOrder = typer.Option("oldest", "--sort"),
) -> None:
    """List persisted trade reviews from the local JSON store."""
    reviews = _review_query_service().list_trade_reviews(
        rating=rating,
        purpose=purpose,
        direction=direction,
        sort=sort,
    )
    if not reviews:
        typer.echo("No trade reviews found.")
        return

    typer.echo(
        "TRADE_REVIEW_ID | POSITION_ID | TRADE_PLAN_ID | PURPOSE | DIRECTION | "
        "RATING | SUMMARY | REVIEWED_AT"
    )
    for item in reviews:
        typer.echo(
            " | ".join(
                [
                    str(item.review.id),
                    str(item.position.id),
                    str(item.trade_plan.id),
                    item.trade_idea.purpose,
                    item.trade_idea.direction,
                    "" if item.review.rating is None else str(item.review.rating),
                    item.review.summary,
                    item.review.reviewed_at.isoformat(),
                ]
            )
        )


@app.command("show-trade-review")
def show_trade_review(trade_review_id: str) -> None:
    """Show a persisted trade review with linked trade context."""
    detail = _run_service(
        lambda: _review_query_service().get_trade_review_detail(
            _parse_uuid(trade_review_id)
        )
    )
    review = detail.review

    _echo_section(
        "Trade review",
        [
            ("position_id", review.position_id),
            ("trade_plan_id", detail.trade_plan.id),
            ("rating", _format_optional_show_value(review.rating)),
            ("reviewed_at", review.reviewed_at.isoformat()),
            ("summary", review.summary),
            ("what_went_well", review.what_went_well),
            ("what_went_poorly", review.what_went_poorly),
            ("lessons_learned", _format_string_list(review.lessons_learned)),
            ("follow_up_actions", _format_string_list(review.follow_up_actions)),
        ],
        heading_value=review.id,
    )
    _echo_section(
        "Position",
        [
            ("id", detail.position.id),
            ("state", detail.position.lifecycle_state),
            ("realized_pnl", _format_optional_decimal(detail.realized_pnl)),
        ],
    )
    _echo_section(
        "Trade plan",
        [
            ("id", detail.trade_plan.id),
            ("approval_state", detail.trade_plan.approval_state),
        ],
    )
    _echo_section(
        "Trade idea",
        [
            ("id", detail.trade_idea.id),
            ("purpose", detail.trade_idea.purpose),
            ("direction", detail.trade_idea.direction),
            ("horizon", detail.trade_idea.horizon),
        ],
    )
    _echo_market_context_section(detail.market_context_snapshots)


@app.command("list-positions")
def list_positions(
    state: str | None = typer.Option(
        None,
        "--state",
        help="Filter positions by lifecycle state, such as open or closed.",
    ),
    purpose: str | None = typer.Option(None, "--purpose"),
    has_review: bool | None = typer.Option(None, "--has-review/--no-review"),
    sort: ListSortOrder = typer.Option("oldest", "--sort"),
) -> None:
    """List persisted positions from the local JSON store."""
    query_service = _position_query_service()
    positions = query_service.list_positions(
        lifecycle_state=state,
        purpose=purpose,
        has_review=has_review,
        sort=sort,
    )
    if not positions:
        typer.echo("No positions found.")
        return

    typer.echo(
        "POSITION_ID | STATE | PURPOSE | QTY | REALIZED_PNL | OPENED_AT | CLOSED_AT"
    )
    for position in positions:
        detail = query_service.get_position_detail(position.id)
        typer.echo(
            " | ".join(
                [
                    str(position.id),
                    position.lifecycle_state,
                    position.purpose,
                    str(position.current_quantity),
                    _format_optional_decimal(detail.realized_pnl),
                    position.opened_at.isoformat(),
                    _format_optional_datetime(position.closed_at),
                ]
            )
        )


@app.command("show-position")
def show_position(position_id: str) -> None:
    """Show a persisted position with linked plan, idea, fills, and review."""
    query_service = _position_query_service()
    detail = _run_service(lambda: query_service.get_position_detail(_parse_uuid(position_id)))
    position = detail.position
    plan = detail.trade_plan
    idea = detail.trade_idea

    _echo_section(
        "Position",
        [
            ("state", position.lifecycle_state),
            ("instrument_id", position.instrument_id),
            ("trade_plan_id", position.trade_plan_id),
            ("purpose", position.purpose),
            ("current_quantity", position.current_quantity),
            ("average_entry_price", _format_optional_decimal(position.average_entry_price)),
            ("realized_pnl", _format_optional_decimal(detail.realized_pnl)),
            ("opened_at", position.opened_at.isoformat()),
            ("closed_at", _format_optional_show_datetime(position.closed_at)),
        ],
        heading_value=position.id,
    )
    _echo_section(
        "Trade plan",
        [
            ("id", plan.id),
            ("approval_state", plan.approval_state),
            ("entry_criteria", plan.entry_criteria),
            ("invalidation", plan.invalidation),
            ("risk_model", _format_optional_text(plan.risk_model)),
        ],
    )
    _echo_section(
        "Trade idea",
        [
            ("id", idea.id),
            ("purpose", idea.purpose),
            ("direction", idea.direction),
            ("horizon", idea.horizon),
            ("instrument_id", idea.instrument_id),
        ],
    )
    _echo_collection_section(
        "Order intents",
        "No order intents found.",
        [
            [
                ("order_intent_id", order_intent.id),
                ("status", order_intent.status.value),
                ("symbol", order_intent.symbol),
                ("side", order_intent.side.value),
                ("order_type", order_intent.order_type.value),
                ("quantity", order_intent.quantity),
                ("limit_price", _format_optional_decimal(order_intent.limit_price)),
                ("stop_price", _format_optional_decimal(order_intent.stop_price)),
                ("created_at", order_intent.created_at.isoformat()),
            ]
            for order_intent in detail.order_intents
        ],
    )
    _echo_collection_section(
        "Fills",
        "No fills found.",
        [
            [
                ("fill_id", fill.id),
                ("order_intent_id", _format_optional_show_value(fill.order_intent_id)),
                ("side", fill.side),
                ("quantity", fill.quantity),
                ("price", fill.price),
                ("source", fill.source),
                ("notes", _format_optional_text(fill.notes)),
                ("filled_at", fill.filled_at.isoformat()),
            ]
            for fill in detail.fills
        ],
    )
    if detail.review is None:
        _echo_section("Review", [("status", "No review found.")])
    else:
        _echo_section(
            "Review",
            [
                ("id", detail.review.id),
                ("rating", _format_optional_show_value(detail.review.rating)),
                ("summary", detail.review.summary),
            ],
        )
    _echo_market_context_section(detail.market_context_snapshots)


@app.command("show-position-timeline")
def show_position_timeline(position_id: str) -> None:
    """Show lifecycle events for a persisted position."""
    query_service = _position_query_service()
    events = _run_service(lambda: query_service.get_position_timeline(_parse_uuid(position_id)))
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


@app.command("import-context")
def import_context(
    file: Path = typer.Argument(...),
    instrument_id: str | None = typer.Option(None, "--instrument-id"),
    target_type: ContextTargetOption | None = typer.Option(None, "--target-type"),
    target_id: str | None = typer.Option(None, "--target-id"),
    source: str = typer.Option("local-file", "--source"),
) -> None:
    """Import one read-only market context snapshot from a local JSON file."""
    repositories = _repositories()
    snapshot = _run_service(
        lambda: MarketContextImportService(
            snapshot_repository=repositories.market_context_snapshots,
            plan_repository=repositories.plans,
            position_repository=repositories.positions,
            review_repository=repositories.reviews,
            idea_repository=repositories.ideas,
        ).import_context(
            JsonMarketContextImportSource(file),
            source=source,
            source_ref=str(file),
            instrument_id=None if instrument_id is None else _parse_uuid(instrument_id),
            target_type=None if target_type is None else _context_target_type(target_type),
            target_id=None if target_id is None else _parse_uuid(target_id),
        )
    )
    _echo_context_snapshot_result(snapshot)


@app.command("copy-context")
def copy_context(
    snapshot_id: str,
    target_type: ContextTargetOption = typer.Option(..., "--target-type"),
    target_id: str = typer.Option(..., "--target-id"),
) -> None:
    """Copy an existing context snapshot to a planning or review target."""
    repositories = _repositories()
    snapshot = _run_service(
        lambda: MarketContextImportService(
            snapshot_repository=repositories.market_context_snapshots,
            plan_repository=repositories.plans,
            position_repository=repositories.positions,
            review_repository=repositories.reviews,
            idea_repository=repositories.ideas,
        ).copy_context_to_target(
            _parse_uuid(snapshot_id),
            target_type=_context_target_type(target_type),
            target_id=_parse_uuid(target_id),
        )
    )
    _echo_context_snapshot_result(snapshot)


@app.command("list-context")
def list_context(
    instrument_id: str | None = typer.Option(None, "--instrument-id"),
    target_type: ContextTargetOption | None = typer.Option(None, "--target-type"),
    target_id: str | None = typer.Option(None, "--target-id"),
    context_type: str | None = typer.Option(None, "--context-type"),
    source: str | None = typer.Option(None, "--source"),
    observed_from: str | None = typer.Option(None, "--observed-from"),
    observed_to: str | None = typer.Option(None, "--observed-to"),
    captured_from: str | None = typer.Option(None, "--captured-from"),
    captured_to: str | None = typer.Option(None, "--captured-to"),
) -> None:
    """List stored read-only market context snapshots."""
    query_service = _market_context_query_service()
    snapshots = _run_service(
        lambda: _list_context_snapshots(
            query_service,
            instrument_id=instrument_id,
            target_type=target_type,
            target_id=target_id,
            context_type=context_type,
            source=source,
            observed_from=observed_from,
            observed_to=observed_to,
            captured_from=captured_from,
            captured_to=captured_to,
        )
    )
    if not snapshots:
        typer.echo("No market context snapshots found.")
        return

    typer.echo(
        "MARKET_CONTEXT_SNAPSHOT_ID | INSTRUMENT_ID | TARGET_TYPE | TARGET_ID | "
        "CONTEXT_TYPE | SOURCE | OBSERVED_AT | CAPTURED_AT"
    )
    for snapshot in snapshots:
        typer.echo(
            " | ".join(
                [
                    str(snapshot.id),
                    str(snapshot.instrument_id),
                    _format_optional_text(snapshot.target_type),
                    "" if snapshot.target_id is None else str(snapshot.target_id),
                    snapshot.context_type,
                    snapshot.source,
                    snapshot.observed_at.isoformat(),
                    snapshot.captured_at.isoformat(),
                ]
            )
        )


@app.command("show-context")
def show_context(snapshot_id: str) -> None:
    """Show one stored read-only market context snapshot."""
    snapshot = _run_service(
        lambda: _market_context_query_service().get_snapshot(_parse_uuid(snapshot_id))
    )
    _echo_section(
        "Market context snapshot",
        [
            ("instrument_id", snapshot.instrument_id),
            ("target_type", _format_optional_text(snapshot.target_type)),
            ("target_id", _format_optional_show_value(snapshot.target_id)),
            ("context_type", snapshot.context_type),
            ("source", snapshot.source),
            ("source_ref", _format_optional_text(snapshot.source_ref)),
            ("observed_at", snapshot.observed_at.isoformat()),
            ("captured_at", snapshot.captured_at.isoformat()),
            ("payload", json.dumps(snapshot.payload, sort_keys=True)),
        ],
        heading_value=snapshot.id,
    )


def _repositories() -> JsonRepositorySet:
    """Build JSON repositories over the configured store path."""
    return build_json_repositories(_json_store_path())


def _json_store_path() -> Path:
    """Return the configured local JSON persistence path."""
    configured = os.environ.get("TRADING_SYSTEM_STORE_PATH")
    if configured:
        return Path(configured)
    return Path(".trading-system") / "store.json"


def _position_query_service() -> PositionQueryService:
    """Build a position query service from JSON repositories."""
    repositories = _repositories()
    return PositionQueryService(
        position_repository=repositories.positions,
        plan_repository=repositories.plans,
        idea_repository=repositories.ideas,
        order_intent_repository=repositories.order_intents,
        fill_repository=repositories.fills,
        review_repository=repositories.reviews,
        lifecycle_event_repository=repositories.lifecycle_events,
        market_context_snapshot_repository=repositories.market_context_snapshots,
    )


def _trade_query_service() -> TradeQueryService:
    """Build a trade query service from JSON repositories."""
    repositories = _repositories()
    return TradeQueryService(
        idea_repository=repositories.ideas,
        thesis_repository=repositories.theses,
        plan_repository=repositories.plans,
        evaluation_repository=repositories.evaluations,
        order_intent_repository=repositories.order_intents,
        position_repository=repositories.positions,
        market_context_snapshot_repository=repositories.market_context_snapshots,
    )


def _review_query_service() -> ReviewQueryService:
    """Build a trade review query service from JSON repositories."""
    repositories = _repositories()
    return ReviewQueryService(
        review_repository=repositories.reviews,
        position_repository=repositories.positions,
        plan_repository=repositories.plans,
        idea_repository=repositories.ideas,
        fill_repository=repositories.fills,
        market_context_snapshot_repository=repositories.market_context_snapshots,
    )


def _market_context_query_service() -> MarketContextQueryService:
    """Build a market context query service from JSON repositories."""
    repositories = _repositories()
    return MarketContextQueryService(
        snapshot_repository=repositories.market_context_snapshots,
    )


def _rule_service(repositories: JsonRepositorySet) -> RuleService:
    """Build the deterministic rule service used by CLI workflows."""
    rule = Rule(
        code="risk_defined",
        name="Risk defined",
        description="Trade plans must define risk before execution.",
    )
    return RuleService(
        plan_repository=repositories.plans,
        evaluation_repository=repositories.evaluations,
        violation_repository=repositories.violations,
        rules=[(rule, RiskDefinedRule(rule))],
    )


def _parse_uuid(value: str) -> UUID:
    """Parse a CLI UUID argument with a clear Typer error."""
    try:
        return UUID(value)
    except ValueError as exc:
        raise typer.BadParameter("must be a valid UUID") from exc


def _parse_decimal(value: str) -> Decimal:
    """Parse a CLI decimal argument with a clear Typer error."""
    try:
        return Decimal(value)
    except Exception as exc:
        raise typer.BadParameter("must be a valid decimal") from exc


def _parse_optional_context_datetime(value: str | None) -> datetime | None:
    """Parse optional ISO datetime filters with a clear Typer error."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("must be a valid ISO datetime") from exc


def _context_target_type(value: ContextTargetOption) -> str:
    """Map CLI target names to canonical domain type labels."""
    return {
        "trade-plan": "TradePlan",
        "position": "Position",
        "trade-review": "TradeReview",
    }[value]


def _list_context_snapshots(
    query_service: MarketContextQueryService,
    *,
    instrument_id: str | None,
    target_type: ContextTargetOption | None,
    target_id: str | None,
    context_type: str | None,
    source: str | None,
    observed_from: str | None,
    observed_to: str | None,
    captured_from: str | None,
    captured_to: str | None,
):
    """Resolve optional context list filters."""
    if target_type is None or target_id is None:
        if target_type is not None or target_id is not None:
            raise ValueError("Target type and target id must be provided together.")
    return query_service.list_snapshots(
        instrument_id=None if instrument_id is None else _parse_uuid(instrument_id),
        target_type=None if target_type is None else _context_target_type(target_type),
        target_id=None if target_id is None else _parse_uuid(target_id),
        context_type=context_type,
        source=source,
        observed_from=_parse_optional_context_datetime(observed_from),
        observed_to=_parse_optional_context_datetime(observed_to),
        captured_from=_parse_optional_context_datetime(captured_from),
        captured_to=_parse_optional_context_datetime(captured_to),
    )


def _format_optional_datetime(value: datetime | None) -> str:
    """Format optional datetime values for CLI output."""
    return "" if value is None else value.isoformat()


def _format_optional_decimal(value: Decimal | None) -> str:
    """Format optional decimal values for CLI output."""
    return "N/A" if value is None else str(value)


def _format_optional_text(value: str | None) -> str:
    """Format optional text values for CLI output."""
    return "" if value is None else value


def _format_optional_show_datetime(value: datetime | None) -> str:
    """Format optional datetime values for show output."""
    return "N/A" if value is None else value.isoformat()


def _format_optional_show_value(value: object | None) -> str:
    """Format optional generic values for show output."""
    return "N/A" if value is None else str(value)


def _format_string_list(values: list[str]) -> str:
    """Format repeated string fields for CLI output."""
    if not values:
        return ""
    return "; ".join(values)


def _run_service(func):
    """Run a service call and translate domain errors into CLI output."""
    try:
        return func()
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


def _echo_field_lines(fields: list[tuple[str, object]]) -> None:
    """Print field/value pairs with normalized CLI formatting."""
    for name, value in fields:
        typer.echo(f"{name}: {value}")


def _echo_section(
    title: str,
    fields: list[tuple[str, object]],
    heading_value: object | None = None,
) -> None:
    """Print one titled section with normalized spacing."""
    if heading_value is None:
        typer.echo(title)
    else:
        typer.echo(f"{title} {heading_value}")
    _echo_field_lines(fields)
    typer.echo("")


def _echo_collection_section(
    title: str,
    empty_message: str,
    items: list[list[tuple[str, object]]],
) -> None:
    """Print one titled collection section using field-only item rows."""
    typer.echo(title)
    if not items:
        typer.echo(empty_message)
        typer.echo("")
        return
    for index, item_fields in enumerate(items):
        _echo_field_lines(item_fields)
        if index != len(items) - 1:
            typer.echo("")
    typer.echo("")


def _echo_market_context_section(snapshots: list[MarketContextSnapshot]) -> None:
    """Print embedded market context snapshot metadata without payloads."""
    _echo_collection_section(
        "Market context",
        "No market context snapshots found.",
        [
            [
                ("market_context_snapshot_id", snapshot.id),
                ("context_type", snapshot.context_type),
                ("source", snapshot.source),
                ("source_ref", _format_optional_text(snapshot.source_ref)),
                ("observed_at", snapshot.observed_at.isoformat()),
                ("captured_at", snapshot.captured_at.isoformat()),
            ]
            for snapshot in snapshots
        ],
    )


def _echo_context_snapshot_result(snapshot: MarketContextSnapshot) -> None:
    """Print a compact market context result for command chaining."""
    typer.echo(f"market_context_snapshot_id: {snapshot.id}")
    typer.echo(f"instrument_id: {snapshot.instrument_id}")
    typer.echo(f"context_type: {snapshot.context_type}")
    typer.echo(f"source: {snapshot.source}")
    typer.echo(f"observed_at: {snapshot.observed_at.isoformat()}")
    typer.echo(f"captured_at: {snapshot.captured_at.isoformat()}")
    typer.echo(f"target_type: {_format_optional_text(snapshot.target_type)}")
    typer.echo(f"target_id: {_format_optional_show_value(snapshot.target_id)}")


def _echo_order_intent(order_intent: OrderIntent) -> None:
    """Print a compact order intent result for command chaining."""
    typer.echo(f"order_intent_id: {order_intent.id}")
    typer.echo(f"trade_plan_id: {order_intent.trade_plan_id}")
    typer.echo(f"status: {order_intent.status.value}")
    typer.echo(f"symbol: {order_intent.symbol}")
    typer.echo(f"side: {order_intent.side.value}")
    typer.echo(f"order_type: {order_intent.order_type.value}")
    typer.echo(f"quantity: {order_intent.quantity}")
    typer.echo(f"limit_price: {_format_optional_decimal(order_intent.limit_price)}")
    typer.echo(f"stop_price: {_format_optional_decimal(order_intent.stop_price)}")


def _echo_trade_review(review: TradeReview) -> None:
    """Print a compact trade review result for command chaining."""
    typer.echo(f"trade_review_id: {review.id}")
    typer.echo(f"position_id: {review.position_id}")
    typer.echo(f"rating: {'' if review.rating is None else review.rating}")
    typer.echo(f"summary: {review.summary}")
    typer.echo(
        f"lessons_learned_count: {len(review.lessons_learned)}"
    )
    typer.echo(
        f"follow_up_actions_count: {len(review.follow_up_actions)}"
    )


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
