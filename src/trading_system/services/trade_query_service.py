"""Read-only workflows for persisted trade idea and trade plan retrieval."""

from dataclasses import dataclass
from uuid import UUID

from trading_system.domain.rules.rule_evaluation import RuleEvaluation
from trading_system.domain.trading.idea import TradeIdea
from trading_system.domain.trading.order_intent import OrderIntent
from trading_system.domain.trading.plan import TradePlan
from trading_system.domain.trading.position import Position
from trading_system.domain.trading.thesis import TradeThesis
from trading_system.ports.repositories import (
    OrderIntentRepository,
    PositionRepository,
    RuleEvaluationRepository,
    TradeIdeaRepository,
    TradePlanRepository,
    TradeThesisRepository,
)


@dataclass(frozen=True)
class TradePlanDetail:
    """Composite read model for inspecting a persisted trade plan."""

    trade_plan: TradePlan
    trade_idea: TradeIdea
    trade_thesis: TradeThesis
    rule_evaluations: list[RuleEvaluation]
    order_intents: list[OrderIntent]
    positions: list[Position]


class TradeQueryService:
    """Coordinates read-only trade idea and plan retrieval."""

    def __init__(
        self,
        idea_repository: TradeIdeaRepository,
        thesis_repository: TradeThesisRepository,
        plan_repository: TradePlanRepository,
        evaluation_repository: RuleEvaluationRepository,
        order_intent_repository: OrderIntentRepository,
        position_repository: PositionRepository,
    ) -> None:
        self._ideas = idea_repository
        self._theses = thesis_repository
        self._plans = plan_repository
        self._evaluations = evaluation_repository
        self._order_intents = order_intent_repository
        self._positions = position_repository

    def list_trade_ideas(self) -> list[TradeIdea]:
        """Return persisted trade ideas ordered by creation time."""
        return sorted(self._ideas.list_all(), key=lambda idea: idea.created_at)

    def list_trade_plans(self) -> list[TradePlan]:
        """Return persisted trade plans ordered by creation time."""
        return sorted(self._plans.list_all(), key=lambda plan: plan.created_at)

    def get_trade_plan_detail(self, trade_plan_id: UUID) -> TradePlanDetail:
        """Return a trade plan with linked idea, thesis, and downstream records."""
        plan = self._plans.get(trade_plan_id)
        if plan is None:
            raise ValueError("Trade plan does not exist.")

        idea = self._ideas.get(plan.trade_idea_id)
        if idea is None:
            raise ValueError("Trade idea does not exist for trade plan.")

        thesis = self._theses.get(plan.trade_thesis_id)
        if thesis is None:
            raise ValueError("Trade thesis does not exist for trade plan.")

        evaluations = sorted(
            self._evaluations.list_by_entity("TradePlan", plan.id),
            key=lambda evaluation: evaluation.evaluated_at,
        )
        order_intents = sorted(
            self._order_intents.list_by_trade_plan_id(plan.id),
            key=lambda order_intent: order_intent.created_at,
        )
        positions = sorted(
            [
                position
                for position in self._positions.list_all()
                if position.trade_plan_id == plan.id
            ],
            key=lambda position: position.opened_at,
        )
        return TradePlanDetail(
            trade_plan=plan,
            trade_idea=idea,
            trade_thesis=thesis,
            rule_evaluations=evaluations,
            order_intents=order_intents,
            positions=positions,
        )
