"""Typer command-line entrypoint for local trading workflows."""

from uuid import uuid4

import typer

from trading_system.domain.rules.rule import Rule
from trading_system.infrastructure.memory.repositories import (
    InMemoryLifecycleEventRepository,
    InMemoryPositionRepository,
    InMemoryRuleEvaluationRepository,
    InMemoryTradeIdeaRepository,
    InMemoryTradePlanRepository,
    InMemoryTradeThesisRepository,
    InMemoryViolationRepository,
)
from trading_system.rules_engine.implementations.risk_defined_rule import RiskDefinedRule
from trading_system.services.position_service import PositionService
from trading_system.services.rule_service import RuleService
from trading_system.services.trade_planning_service import TradePlanningService

app = typer.Typer(help="Structured discretionary trading system.")


@app.command()
def version() -> None:
    """Print the scaffold version."""
    typer.echo("trading-system 0.1.0")


@app.command("demo-planned-trade")
def demo_planned_trade() -> None:
    """Run the planned trade workflow against in-memory repositories."""
    ideas = InMemoryTradeIdeaRepository()
    theses = InMemoryTradeThesisRepository()
    plans = InMemoryTradePlanRepository()
    positions = InMemoryPositionRepository()
    lifecycle_events = InMemoryLifecycleEventRepository()
    evaluations = InMemoryRuleEvaluationRepository()
    violations = InMemoryViolationRepository()

    planning = TradePlanningService(ideas, theses, plans)
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
    approved_plan = planning.approve_trade_plan(plan.id)

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
    position_service = PositionService(
        plan_repository=plans,
        idea_repository=ideas,
        position_repository=positions,
        lifecycle_event_repository=lifecycle_events,
    )
    position = position_service.open_position_from_plan(approved_plan.id)

    typer.echo(
        "Created planned trade workflow: "
        f"idea={idea.id} thesis={thesis.id} plan={approved_plan.id} "
        f"approval_state={approved_plan.approval_state} "
        f"evaluations={len(rule_results)} violations={len(violations.items)} "
        f"position={position.id} lifecycle_events={len(lifecycle_events.items)}"
    )


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
