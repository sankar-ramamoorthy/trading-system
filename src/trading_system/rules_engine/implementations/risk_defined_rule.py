"""Example deterministic rule requiring a defined risk model."""

from trading_system.domain.rules.rule import Rule
from trading_system.domain.rules.violation import Violation
from trading_system.domain.trading.plan import TradePlan


class RiskDefinedRule:
    """Checks that a trade plan has an explicit risk model."""

    def __init__(self, rule: Rule) -> None:
        self.rule = rule

    def evaluate(self, plan: TradePlan) -> tuple[bool, list[Violation]]:
        """Return pass/fail and any resulting violations."""
        if plan.risk_model:
            return True, []

        return False, [
            Violation(
                rule_id=self.rule.id,
                message="Trade plan must define risk before opening a position.",
            )
        ]
