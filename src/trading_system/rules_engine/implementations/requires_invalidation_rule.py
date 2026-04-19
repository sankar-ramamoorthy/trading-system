"""Example deterministic rule requiring invalidation criteria."""

from trading_system.domain.rules.rule import Rule
from trading_system.domain.rules.violation import Violation
from trading_system.domain.trading.plan import TradePlan


class RequiresInvalidationRule:
    """Checks that a trade plan defines how the idea is invalidated."""

    def __init__(self, rule: Rule) -> None:
        self.rule = rule

    def evaluate(self, plan: TradePlan) -> tuple[bool, list[Violation]]:
        """Return pass/fail and any resulting violations."""
        if plan.invalidation.strip():
            return True, []

        return False, [
            Violation(
                rule_id=self.rule.id,
                message="Trade plan must define invalidation before approval.",
            )
        ]
