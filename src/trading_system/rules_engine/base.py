"""Base protocol for deterministic rule implementations."""

from typing import Protocol

from trading_system.domain.rules.violation import Violation
from trading_system.domain.trading.plan import TradePlan


class DeterministicRule(Protocol):
    """A simple auditable rule evaluated against a trade plan."""

    def evaluate(self, plan: TradePlan) -> tuple[bool, list[Violation]]:
        """Return pass/fail and violations for the supplied trade plan."""
        ...
