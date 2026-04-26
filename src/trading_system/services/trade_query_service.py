"""Read-only workflows for persisted trade idea, thesis, and plan retrieval."""

from dataclasses import dataclass
from typing import Literal, TypeVar
from uuid import UUID

from trading_system.domain.rules.rule_evaluation import RuleEvaluation
from trading_system.domain.trading.idea import TradeIdea
from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.domain.trading.order_intent import OrderIntent
from trading_system.domain.trading.plan import TradePlan
from trading_system.domain.trading.position import Position
from trading_system.domain.trading.thesis import TradeThesis
from trading_system.ports.repositories import (
    MarketContextSnapshotRepository,
    OrderIntentRepository,
    PositionRepository,
    RuleEvaluationRepository,
    TradeIdeaRepository,
    TradePlanRepository,
    TradeThesisRepository,
)


SortOrder = Literal["oldest", "newest"]
T = TypeVar("T")


@dataclass(frozen=True)
class TradeThesisListItem:
    """Compact read model for listing persisted trade theses."""

    trade_thesis: TradeThesis
    trade_idea: TradeIdea
    plan_count: int


@dataclass(frozen=True)
class TradeThesisDetail:
    """Composite read model for inspecting one persisted trade thesis."""

    trade_thesis: TradeThesis
    trade_idea: TradeIdea
    trade_plans: list[TradePlan]


@dataclass(frozen=True)
class TradePlanDetail:
    """Composite read model for inspecting a persisted trade plan."""

    trade_plan: TradePlan
    trade_idea: TradeIdea
    trade_thesis: TradeThesis
    rule_evaluations: list[RuleEvaluation]
    order_intents: list[OrderIntent]
    positions: list[Position]
    market_context_snapshots: list[MarketContextSnapshot]


class TradeQueryService:
    """Coordinates read-only trade idea, thesis, and plan retrieval."""

    def __init__(
        self,
        idea_repository: TradeIdeaRepository,
        thesis_repository: TradeThesisRepository,
        plan_repository: TradePlanRepository,
        evaluation_repository: RuleEvaluationRepository,
        order_intent_repository: OrderIntentRepository,
        position_repository: PositionRepository,
        market_context_snapshot_repository: MarketContextSnapshotRepository,
    ) -> None:
        self._ideas = idea_repository
        self._theses = thesis_repository
        self._plans = plan_repository
        self._evaluations = evaluation_repository
        self._order_intents = order_intent_repository
        self._positions = position_repository
        self._market_context_snapshots = market_context_snapshot_repository

    def list_trade_ideas(
        self,
        purpose: str | None = None,
        direction: str | None = None,
        status: str | None = None,
        sort: SortOrder = "oldest",
    ) -> list[TradeIdea]:
        """Return persisted trade ideas with exact filters and chronological sorting."""
        ideas = self._ideas.list_all()
        if purpose is not None:
            ideas = [idea for idea in ideas if idea.purpose == purpose]
        if direction is not None:
            ideas = [idea for idea in ideas if idea.direction == direction]
        if status is not None:
            ideas = [idea for idea in ideas if idea.status == status]
        return _sort_items(ideas, key=lambda idea: idea.created_at, sort=sort)

    def list_trade_theses(
        self,
        purpose: str | None = None,
        direction: str | None = None,
        has_plan: bool | None = None,
        sort: SortOrder = "oldest",
    ) -> list[TradeThesisListItem]:
        """Return persisted trade theses with linked idea context and plan counts."""
        ideas_by_id = {idea.id: idea for idea in self._ideas.list_all()}
        plans = self._plans.list_all()
        plan_counts: dict[UUID, int] = {}
        for plan in plans:
            plan_counts[plan.trade_thesis_id] = plan_counts.get(plan.trade_thesis_id, 0) + 1

        items: list[TradeThesisListItem] = []
        for thesis in self._theses.list_all():
            idea = ideas_by_id.get(thesis.trade_idea_id)
            if idea is None:
                raise ValueError("Trade idea does not exist for trade thesis.")

            item = TradeThesisListItem(
                trade_thesis=thesis,
                trade_idea=idea,
                plan_count=plan_counts.get(thesis.id, 0),
            )
            if purpose is not None and item.trade_idea.purpose != purpose:
                continue
            if direction is not None and item.trade_idea.direction != direction:
                continue
            if has_plan is not None and (item.plan_count > 0) != has_plan:
                continue
            items.append(item)

        return _sort_items(
            items,
            key=lambda item: item.trade_idea.created_at,
            sort=sort,
        )

    def get_trade_thesis_detail(self, trade_thesis_id: UUID) -> TradeThesisDetail:
        """Return a trade thesis with linked idea and downstream plans."""
        thesis = self._theses.get(trade_thesis_id)
        if thesis is None:
            raise ValueError("Trade thesis does not exist.")

        idea = self._ideas.get(thesis.trade_idea_id)
        if idea is None:
            raise ValueError("Trade idea does not exist for trade thesis.")

        trade_plans = _sort_items(
            [
                plan
                for plan in self._plans.list_all()
                if plan.trade_thesis_id == thesis.id
            ],
            key=lambda plan: plan.created_at,
            sort="oldest",
        )
        return TradeThesisDetail(
            trade_thesis=thesis,
            trade_idea=idea,
            trade_plans=trade_plans,
        )

    def list_trade_plans(
        self,
        approval_state: str | None = None,
        sort: SortOrder = "oldest",
    ) -> list[TradePlan]:
        """Return persisted trade plans with exact filters and chronological sorting."""
        plans = self._plans.list_all()
        if approval_state is not None:
            plans = [plan for plan in plans if plan.approval_state == approval_state]
        return _sort_items(plans, key=lambda plan: plan.created_at, sort=sort)

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

        evaluations = _sort_items(
            self._evaluations.list_by_entity("TradePlan", plan.id),
            key=lambda evaluation: evaluation.evaluated_at,
            sort="oldest",
        )
        order_intents = _sort_items(
            self._order_intents.list_by_trade_plan_id(plan.id),
            key=lambda order_intent: order_intent.created_at,
            sort="oldest",
        )
        positions = _sort_items(
            [
                position
                for position in self._positions.list_all()
                if position.trade_plan_id == plan.id
            ],
            key=lambda position: position.opened_at,
            sort="oldest",
        )
        market_context_snapshots = _sort_items(
            self._market_context_snapshots.list_by_target("TradePlan", plan.id),
            key=lambda snapshot: snapshot.captured_at,
            sort="oldest",
        )
        return TradePlanDetail(
            trade_plan=plan,
            trade_idea=idea,
            trade_thesis=thesis,
            rule_evaluations=evaluations,
            order_intents=order_intents,
            positions=positions,
            market_context_snapshots=market_context_snapshots,
        )


def _sort_items(items: list[T], *, key, sort: SortOrder) -> list[T]:
    """Return a deterministic chronological sort order."""
    return sorted(items, key=key, reverse=sort == "newest")
