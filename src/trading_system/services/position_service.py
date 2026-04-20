"""Service stubs for position lifecycle workflows."""

from uuid import UUID

from trading_system.domain.trading.lifecycle import LifecycleEvent
from trading_system.domain.trading.position import Position
from trading_system.ports.repositories import (
    LifecycleEventRepository,
    PositionRepository,
    TradeIdeaRepository,
    TradePlanRepository,
)


class PositionService:
    """Coordinates position workflows without persistence details."""

    def __init__(
        self,
        plan_repository: TradePlanRepository,
        idea_repository: TradeIdeaRepository,
        position_repository: PositionRepository,
        lifecycle_event_repository: LifecycleEventRepository,
    ) -> None:
        self._plans = plan_repository
        self._ideas = idea_repository
        self._positions = position_repository
        self._lifecycle_events = lifecycle_event_repository

    def open_position_from_plan(self, trade_plan_id: UUID) -> Position:
        """Open a position from an approved trade plan."""
        plan = self._plans.get(trade_plan_id)
        if plan is None:
            raise ValueError("Trade plan does not exist.")
        if plan.approval_state != "approved":
            raise ValueError("Trade plan must be approved before opening a position.")

        idea = self._ideas.get(plan.trade_idea_id)
        if idea is None:
            raise ValueError("Trade idea does not exist.")

        position = Position(
            trade_plan_id=plan.id,
            instrument_id=idea.instrument_id,
            purpose=idea.purpose,
            lifecycle_state="open",
        )
        self._positions.add(position)
        self._lifecycle_events.add(
            LifecycleEvent(
                entity_id=position.id,
                entity_type="Position",
                event_type="POSITION_OPENED",
                note=f"Opened position from trade plan {plan.id}.",
            )
        )
        return position
