"""In-memory repository implementations for narrow workflow tests."""

from uuid import UUID

from trading_system.domain.rules.rule_evaluation import RuleEvaluation
from trading_system.domain.rules.violation import Violation
from trading_system.domain.trading.idea import TradeIdea
from trading_system.domain.trading.plan import TradePlan
from trading_system.domain.trading.thesis import TradeThesis


class InMemoryTradeIdeaRepository:
    """Stores trade ideas in memory for local workflows."""

    def __init__(self) -> None:
        self.items: dict[UUID, TradeIdea] = {}

    def add(self, idea: TradeIdea) -> None:
        """Persist a trade idea."""
        self.items[idea.id] = idea

    def get(self, idea_id: UUID) -> TradeIdea | None:
        """Return a trade idea by identity."""
        return self.items.get(idea_id)


class InMemoryTradeThesisRepository:
    """Stores trade theses in memory for local workflows."""

    def __init__(self) -> None:
        self.items: dict[UUID, TradeThesis] = {}

    def add(self, thesis: TradeThesis) -> None:
        """Persist a trade thesis."""
        self.items[thesis.id] = thesis

    def get(self, thesis_id: UUID) -> TradeThesis | None:
        """Return a trade thesis by identity."""
        return self.items.get(thesis_id)


class InMemoryTradePlanRepository:
    """Stores trade plans in memory for local workflows."""

    def __init__(self) -> None:
        self.items: dict[UUID, TradePlan] = {}

    def add(self, plan: TradePlan) -> None:
        """Persist a trade plan."""
        self.items[plan.id] = plan

    def get(self, plan_id: UUID) -> TradePlan | None:
        """Return a trade plan by identity."""
        return self.items.get(plan_id)

    def update(self, plan: TradePlan) -> None:
        """Persist changes to a trade plan."""
        self.items[plan.id] = plan


class InMemoryRuleEvaluationRepository:
    """Stores rule evaluation artifacts in memory."""

    def __init__(self) -> None:
        self.items: dict[UUID, RuleEvaluation] = {}

    def add(self, evaluation: RuleEvaluation) -> None:
        """Persist a rule evaluation."""
        self.items[evaluation.id] = evaluation


class InMemoryViolationRepository:
    """Stores rule violations in memory."""

    def __init__(self) -> None:
        self.items: dict[UUID, Violation] = {}

    def add(self, violation: Violation) -> None:
        """Persist a rule violation."""
        self.items[violation.id] = violation
