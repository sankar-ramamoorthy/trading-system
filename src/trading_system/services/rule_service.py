"""Service stubs for deterministic rule evaluation workflows."""

from uuid import UUID

from trading_system.domain.rules.rule import Rule
from trading_system.domain.rules.rule_evaluation import RuleEvaluation
from trading_system.domain.rules.violation import Violation
from trading_system.ports.repositories import (
    RuleEvaluationRepository,
    TradePlanRepository,
    ViolationRepository,
)
from trading_system.rules_engine.base import DeterministicRule


class RuleService:
    """Coordinates rule evaluation workflows without persistence details."""

    def __init__(
        self,
        plan_repository: TradePlanRepository,
        evaluation_repository: RuleEvaluationRepository,
        violation_repository: ViolationRepository,
        rules: list[tuple[Rule, DeterministicRule]],
    ) -> None:
        self._plans = plan_repository
        self._evaluations = evaluation_repository
        self._violations = violation_repository
        self._rules = list(rules)

    def evaluate_rules_for_entity(
        self,
        entity_type: str,
        entity_id: object,
    ) -> list[RuleEvaluation]:
        """Evaluate deterministic rules for a scoped domain entity."""
        if entity_type != "TradePlan":
            raise ValueError("Only TradePlan rule evaluation is implemented.")
        if not isinstance(entity_id, UUID):
            raise TypeError("entity_id must be a UUID.")
        return self.evaluate_trade_plan_rules(entity_id)

    def evaluate_trade_plan_rules(self, trade_plan_id: UUID) -> list[RuleEvaluation]:
        """Evaluate configured deterministic rules for an approved trade plan."""
        plan = self._plans.get(trade_plan_id)
        if plan is None:
            raise ValueError("Trade plan does not exist.")
        if plan.approval_state != "approved":
            raise ValueError("Trade plan must be approved before rule evaluation.")

        evaluations: list[RuleEvaluation] = []
        for rule, implementation in self._rules:
            passed, violations = implementation.evaluate(plan)
            evaluation = RuleEvaluation(
                rule_id=rule.id,
                entity_type="TradePlan",
                entity_id=plan.id,
                passed=passed,
                details=None if passed else _format_violation_details(violations),
            )
            self._evaluations.add(evaluation)
            for violation in violations:
                self._violations.add(violation)
            evaluations.append(evaluation)

        return evaluations


def _format_violation_details(violations: list[Violation]) -> str | None:
    """Create a compact audit detail string for failed evaluations."""
    if not violations:
        return None
    return "; ".join(violation.message for violation in violations)
