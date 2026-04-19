"""Tests for the planned discretionary trade workflow."""

from uuid import uuid4

import pytest

from trading_system.domain.rules.rule import Rule
from trading_system.infrastructure.memory.repositories import (
    InMemoryRuleEvaluationRepository,
    InMemoryTradeIdeaRepository,
    InMemoryTradePlanRepository,
    InMemoryTradeThesisRepository,
    InMemoryViolationRepository,
)
from trading_system.rules_engine.implementations.risk_defined_rule import RiskDefinedRule
from trading_system.services.rule_service import RuleService
from trading_system.services.trade_planning_service import TradePlanningService


def test_plan_approval_changes_approval_state() -> None:
    """A draft plan can be approved through the planning service."""
    planning, _, _, plans = _planning_service()
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

    assert approved.approval_state == "approved"
    assert plans.get(plan.id).approval_state == "approved"


def test_trade_plan_cannot_be_created_when_thesis_reference_is_missing() -> None:
    """A plan requires a valid idea and thesis reference."""
    planning, _, _, _ = _planning_service()
    idea = planning.create_trade_idea(
        instrument_id=uuid4(),
        playbook_id=uuid4(),
        purpose="swing",
        direction="long",
        horizon="days_to_weeks",
    )

    with pytest.raises(ValueError, match="Trade thesis does not exist"):
        planning.create_trade_plan(
            trade_idea_id=idea.id,
            trade_thesis_id=uuid4(),
            entry_criteria="Breakout confirmation.",
            invalidation="Close below setup low.",
        )


def test_trade_plan_cannot_be_evaluated_when_plan_reference_is_missing() -> None:
    """Rule evaluation requires an existing approved plan."""
    _, _, _, plans = _planning_service()
    evaluations = InMemoryRuleEvaluationRepository()
    violations = InMemoryViolationRepository()
    risk_rule = _risk_rule()
    rule_service = RuleService(
        plan_repository=plans,
        evaluation_repository=evaluations,
        violation_repository=violations,
        rules=[(risk_rule, RiskDefinedRule(risk_rule))],
    )

    with pytest.raises(ValueError, match="Trade plan does not exist"):
        rule_service.evaluate_trade_plan_rules(uuid4())


def test_risk_defined_passes_when_risk_model_is_present() -> None:
    """The risk_defined rule passes when a plan has a risk model."""
    planning, _, _, plans = _planning_service()
    plan = _approved_plan(planning, risk_model="Defined stop and max loss.")
    evaluations = InMemoryRuleEvaluationRepository()
    violations = InMemoryViolationRepository()
    risk_rule = _risk_rule()
    rule_service = RuleService(
        plan_repository=plans,
        evaluation_repository=evaluations,
        violation_repository=violations,
        rules=[(risk_rule, RiskDefinedRule(risk_rule))],
    )

    results = rule_service.evaluate_trade_plan_rules(plan.id)

    assert len(results) == 1
    assert results[0].passed is True
    assert results[0].rule_id == risk_rule.id
    assert results[0].entity_id == plan.id
    assert len(evaluations.items) == 1
    assert len(violations.items) == 0


def test_risk_defined_fails_when_risk_model_is_absent() -> None:
    """The risk_defined rule fails and persists a violation when risk is absent."""
    planning, _, _, plans = _planning_service()
    plan = _approved_plan(planning, risk_model=None)
    evaluations = InMemoryRuleEvaluationRepository()
    violations = InMemoryViolationRepository()
    risk_rule = _risk_rule()
    rule_service = RuleService(
        plan_repository=plans,
        evaluation_repository=evaluations,
        violation_repository=violations,
        rules=[(risk_rule, RiskDefinedRule(risk_rule))],
    )

    results = rule_service.evaluate_trade_plan_rules(plan.id)

    assert len(results) == 1
    assert results[0].passed is False
    assert results[0].details == "Trade plan must define risk before opening a position."
    assert len(evaluations.items) == 1
    assert len(violations.items) == 1


def test_unapproved_plan_cannot_be_evaluated() -> None:
    """Rule evaluation is only valid after plan approval."""
    planning, _, _, plans = _planning_service()
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
    risk_rule = _risk_rule()
    rule_service = RuleService(
        plan_repository=plans,
        evaluation_repository=InMemoryRuleEvaluationRepository(),
        violation_repository=InMemoryViolationRepository(),
        rules=[(risk_rule, RiskDefinedRule(risk_rule))],
    )

    with pytest.raises(ValueError, match="must be approved"):
        rule_service.evaluate_trade_plan_rules(plan.id)


def _planning_service() -> tuple[
    TradePlanningService,
    InMemoryTradeIdeaRepository,
    InMemoryTradeThesisRepository,
    InMemoryTradePlanRepository,
]:
    ideas = InMemoryTradeIdeaRepository()
    theses = InMemoryTradeThesisRepository()
    plans = InMemoryTradePlanRepository()
    return TradePlanningService(ideas, theses, plans), ideas, theses, plans


def _approved_plan(
    planning: TradePlanningService,
    risk_model: str | None,
):
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
        risk_model=risk_model,
    )
    return planning.approve_trade_plan(plan.id)


def _risk_rule() -> Rule:
    return Rule(
        code="risk_defined",
        name="Risk defined",
        description="Trade plans must define risk before execution.",
    )
