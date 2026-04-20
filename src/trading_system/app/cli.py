"""Typer command-line entrypoint for local trading workflows."""

from decimal import Decimal
from uuid import uuid4

import typer

from trading_system.domain.rules.rule import Rule
from trading_system.infrastructure.memory.repositories import (
    InMemoryFillRepository,
    InMemoryLifecycleEventRepository,
    InMemoryPositionRepository,
    InMemoryRuleEvaluationRepository,
    InMemoryTradeIdeaRepository,
    InMemoryTradePlanRepository,
    InMemoryTradeReviewRepository,
    InMemoryTradeThesisRepository,
    InMemoryViolationRepository,
)
from trading_system.rules_engine.implementations.risk_defined_rule import RiskDefinedRule
from trading_system.services.fill_service import FillService
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
    """Run the full Milestone 1 workflow against in-memory repositories."""
    ideas = InMemoryTradeIdeaRepository()
    theses = InMemoryTradeThesisRepository()
    plans = InMemoryTradePlanRepository()
    positions = InMemoryPositionRepository()
    fills = InMemoryFillRepository()
    lifecycle_events = InMemoryLifecycleEventRepository()
    reviews = InMemoryTradeReviewRepository()
    evaluations = InMemoryRuleEvaluationRepository()
    violations = InMemoryViolationRepository()

    planning = TradePlanningService(ideas, theses, plans)
    typer.echo("Milestone 1 demo: planned trade -> execution -> review")
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
        f"violations={len(violations.items)}"
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
    typer.echo(
        "7. Recorded entry fill: "
        f"{entry_fill.quantity} @ {entry_fill.price}; "
        f"open_quantity={position.current_quantity}"
    )

    exit_fill = fill_service.record_manual_fill(
        position_id=position.id,
        side="sell",
        quantity=Decimal("100"),
        price=Decimal("27.00"),
        notes="Demo manual exit fill.",
    )
    typer.echo(
        "8. Recorded exit fill: "
        f"{exit_fill.quantity} @ {exit_fill.price}; "
        f"open_quantity={position.current_quantity}"
    )
    typer.echo(
        "9. Position closed from fills: "
        f"state={position.lifecycle_state} closed_at={position.closed_at}"
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
        f"violations={len(violations.items)}, "
        f"fills={len(fills.items)}, "
        f"open_quantity={position.current_quantity}, "
        f"position_state={position.lifecycle_state}, "
        f"review={review.id}, "
        f"lifecycle_events={len(lifecycle_events.items)}"
    )


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
