"""Service workflows for planned discretionary trades."""

from uuid import UUID

from trading_system.domain.trading.idea import TradeIdea
from trading_system.domain.trading.plan import TradePlan
from trading_system.domain.trading.thesis import TradeThesis
from trading_system.ports.repositories import (
    TradeIdeaRepository,
    TradePlanRepository,
    TradeThesisRepository,
)


class TradePlanningService:
    """Coordinates idea, thesis, plan, and approval workflows."""

    def __init__(
        self,
        idea_repository: TradeIdeaRepository,
        thesis_repository: TradeThesisRepository,
        plan_repository: TradePlanRepository,
    ) -> None:
        self._ideas = idea_repository
        self._theses = thesis_repository
        self._plans = plan_repository

    def create_trade_idea(
        self,
        instrument_id: UUID,
        playbook_id: UUID,
        purpose: str,
        direction: str,
        horizon: str,
    ) -> TradeIdea:
        """Create and persist a trade idea."""
        idea = TradeIdea(
            instrument_id=instrument_id,
            playbook_id=playbook_id,
            purpose=purpose,
            direction=direction,
            horizon=horizon,
        )
        self._ideas.add(idea)
        return idea

    def create_trade_thesis(
        self,
        trade_idea_id: UUID,
        reasoning: str,
        supporting_evidence: list[str] | None = None,
        risks: list[str] | None = None,
        disconfirming_signals: list[str] | None = None,
    ) -> TradeThesis:
        """Create and persist a thesis linked to an existing idea."""
        if self._ideas.get(trade_idea_id) is None:
            raise ValueError("Trade idea does not exist.")

        thesis = TradeThesis(
            trade_idea_id=trade_idea_id,
            reasoning=reasoning,
            supporting_evidence=list(supporting_evidence or []),
            risks=list(risks or []),
            disconfirming_signals=list(disconfirming_signals or []),
        )
        self._theses.add(thesis)
        return thesis

    def create_trade_plan(
        self,
        trade_idea_id: UUID,
        trade_thesis_id: UUID,
        entry_criteria: str,
        invalidation: str,
        targets: list[str] | None = None,
        risk_model: str | None = None,
        sizing_assumptions: str | None = None,
    ) -> TradePlan:
        """Create and persist a trade plan linked to an idea and thesis."""
        if self._ideas.get(trade_idea_id) is None:
            raise ValueError("Trade idea does not exist.")

        thesis = self._theses.get(trade_thesis_id)
        if thesis is None:
            raise ValueError("Trade thesis does not exist.")
        if thesis.trade_idea_id != trade_idea_id:
            raise ValueError("Trade thesis is not linked to the trade idea.")

        plan = TradePlan(
            trade_idea_id=trade_idea_id,
            trade_thesis_id=trade_thesis_id,
            entry_criteria=entry_criteria,
            invalidation=invalidation,
            targets=list(targets or []),
            risk_model=risk_model,
            sizing_assumptions=sizing_assumptions,
        )
        self._plans.add(plan)
        return plan

    def approve_trade_plan(self, trade_plan_id: UUID) -> TradePlan:
        """Move an existing trade plan into approved state."""
        plan = self._plans.get(trade_plan_id)
        if plan is None:
            raise ValueError("Trade plan does not exist.")

        plan.approval_state = "approved"
        self._plans.update(plan)
        return plan
