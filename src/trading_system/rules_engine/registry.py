"""Small explicit registry for deterministic rule instances."""

from trading_system.rules_engine.base import DeterministicRule


class RuleRegistry:
    """Holds the deterministic rules active for a workflow."""

    def __init__(self, rules: list[DeterministicRule] | None = None) -> None:
        self._rules = list(rules or [])

    def register(self, rule: DeterministicRule) -> None:
        """Register one rule instance."""
        self._rules.append(rule)

    def all(self) -> list[DeterministicRule]:
        """Return registered rules in evaluation order."""
        return list(self._rules)
